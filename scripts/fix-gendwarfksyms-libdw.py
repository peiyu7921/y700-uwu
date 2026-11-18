#!/usr/bin/env python3
"""让 gendwarfksyms 在 libdw 读不了 .debug_line 时降级判断，而不是直接中止构建。

## 现象

编 `kernel/Image` 时失败：

    error: gendwarfksyms: is_definition_private: dwarf_getsrcfiles failed:
           'invalid .debug_line section'
    error: gendwarfksyms: process_module: dwarf_get_units failed:
           no debugging information?
    make[3]: *** [.../common/rust/Makefile:472: rust/helpers/helpers.o] Error 1

## 为什么必须让 gendwarfksyms 跑通（不能简单绕开）

三条约束连在一起：

  1. VINTF 校验要求 `CONFIG_ASHMEM=y`（`KernelInfo` 比对 FCM 的 kernel config）
  2. 6.12 的 ASHMEM 是 **Rust 实现**（`drivers/staging/android/ashmem*.rs`），
     Kconfig 是 `depends on SHMEM && RUST`
  3. `CONFIG_RUST` 依赖 `!MODVERSIONS || GENDWARFKSYMS`
     （`init/Kconfig:2023`），而 GKI 6.12 要求 `MODVERSIONS=y`
     （上游 gki_defconfig:118），所以只能让 `GENDWARFKSYMS=y`

关掉 MODVERSIONS 也能让 RUST 可见，但那偏离 GKI 6.12 规范，
且所有模块都要重编——代价更大。

## 根因：libdw 的局限，不是 DWARF 真损坏

实测（同一批 .o，同一套编译参数）：

  - `llvm-dwarfdump` 对全部文件解析正常，无 error
  - libdw：`lib/vsprintf.c` 通过，而 `kernel/fork.c`、`mm/memory.c`、
    `virt/kvm/kvm_main.c`、`fs/read_write.c`、`kernel/exit.c`、
    `rust/helpers/helpers.o` 全部报 `invalid .debug_line section`
  - 换 libdw 0.188（jammy-backports）同样失败，排除版本问题
  - 不是规模阈值：`vsprintf.c`(272 文件表项/20 符号) 过，
    `mm/memory.c`(275/62) 不过

即 clang-r596125 生成的 DWARF4 有 libdw 不接受之处，而 LLVM 自己的解析器接受。

## 修法

`scripts/gendwarfksyms/dwarf.c` 的 `is_definition_private()` 里，
`dwarf_getsrcfiles()` 失败时不再 `error()`（exit 1），而是退化为用
**CU 的 `DW_AT_name`（该编译单元的主源文件）** 判断扩展名。

语义等价：原逻辑是「取 DW_AT_decl_file 指向的文件名，看是否 .c 结尾」，
降级后用「CU 主文件名」，对 `helpers.c`、`fork.c` 这类单源文件 TU 完全一致。
方向也安全——判不出来时按原语义尽力判断，而不是让整个构建停下。

用法: python3 fix-gendwarfksyms-libdw.py [--rebuild]
"""
import os
import pathlib
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

COMMON = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/common")
# vendor 树自带一份独立的 scripts/gendwarfksyms/ 副本（不是软链，inode 不同）。
# `sm8750:modules` 的 in-tree 构建以 vendor 树为 srctree，编译的是**那份**，
# 只改 common 会让 vendor 侧仍报 invalid .debug_line。两份都打才完整。
VENDOR = pathlib.Path(
    _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
DWARF_C_LIST = [COMMON / "scripts/gendwarfksyms/dwarf.c",
                VENDOR / "scripts/gendwarfksyms/dwarf.c"]

MARK = "sm8750-gendwarfksyms-libdw-fallback"
OLD = '''	if (dwarf_getsrcfiles(&cudie, &files, NULL))
		error("dwarf_getsrcfiles failed: '%s'", dwarf_errmsg(-1));
'''
NEW = '''	/*
	 * %s: clang 生成的 DWARF4 里有 libdw 不接受之处（实测 libdw 0.186
	 * 与 0.188 都对 kernel/fork.c、rust/helpers/helpers.o 等报
	 * "invalid .debug_line section"，而 llvm-dwarfdump 解析同一批文件
	 * 完全正常）。重新生成的 DWARF 不该让构建停下，所以这里退化为用
	 * CU 的 DW_AT_name（该编译单元的主源文件）判断扩展名 —— 与原逻辑
	 * 「DW_AT_decl_file 指向的文件是否 .c」在单源文件 TU 上等价。
	 * 详见 scripts/fix-gendwarfksyms-libdw.py。
	 */
	if (dwarf_getsrcfiles(&cudie, &files, NULL)) {
		s = dwarf_diename(&cudie);
		if (!s)
			s = "";
		s = strrchr(s, '.');
		res = s && !strcmp(s, ".c");
		cache_set(&srcfile_cache, filenum, res);
		return !!res;
	}
''' % MARK

for DWARF_C in DWARF_C_LIST:
    if not DWARF_C.is_file():
        print("跳过（不存在）: %s" % DWARF_C)
        continue
    body = DWARF_C.read_text(errors="ignore")
    if MARK in body:
        print("ALREADY patched: %s" % DWARF_C)
    elif OLD in body:
        DWARF_C.write_text(body.replace(OLD, NEW, 1))
        print("patched: %s" % DWARF_C)
    else:
        print("警告：%s 未找到 error 分支原文，跳过" % DWARF_C)

if "--rebuild" in sys.argv:
    KB = pathlib.Path(
        _Y700_WORK + "/aosp/out/soong/.intermediates/device/lenovo/elden/kernel/"
        "android_arm64_armv8-a-branchprot_oryon/kernel_build")
    print("== 重编 gendwarfksyms ==")
    r = subprocess.run(
        ["make", "-C", str(COMMON), "O=%s" % KB, "scripts/gendwarfksyms/gendwarfksyms"],
        capture_output=True, text=True)
    print(r.stdout[-2000:])
    print(r.stderr[-2000:])
    sys.exit(r.returncode)
