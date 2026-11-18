#!/usr/bin/env python3
"""让 gendwarfksyms 跳过「没有调试信息」的目标文件，而不是让构建失败。

## 现象

    error: gendwarfksyms: process_module: dwarf_get_units failed:
           no debugging information?
    make[3]: *** [.../common/rust/Makefile:512: rust/bindings.o] Error 1

## 为什么 bindings.o 没有调试信息

`rust/bindings/lib.rs` 只有两类内容：

    mod bindings_raw { include!(... bindings_generated.rs) }   // extern 声明（导入）
    mod bindings_helper { include!(... bindings_helpers_generated.rs) }
    pub use bindings_raw::*;
    pub const __ARCH_SPIN_LOCK_UNLOCKED: arch_spinlock_t = { ... };

全是**导入声明和常量**，没有任何 `#[no_mangle]` 函数定义。实测产物
`rust/bindings.o` 只有 992 字节、0 个 `.debug_*` 段、0 个导出符号 ——
就是个空壳，根本不产生代码。

## 为什么之前没暴露

`rust/Makefile` 给 `exports.o`、`compiler_builtins.o`、`build_error.o`、
`ffi.o`、`uapi.o` 都加了 `private skip_gendwarfksyms = 1`，偏偏 `bindings.o`
没有。上游大概没在「MODVERSIONS=y + GENDWARFKSYMS=y + 打开 Rust」这一组合下
构建过，所以这个疏漏一直没被触发。

## 修法

改 `scripts/gendwarfksyms/gendwarfksyms.c` 的 `process_module()`：**首个** CU
就取不到时视为「该模块无调试信息」，`break` 跳出（后续仍走
`generate_symtypes_and_versions`，输出为空即可），而不是 `error()` 退出。

只放宽「第一个 CU 就失败」这一种情况——若已有 CU 解析成功、后续某个 CU 失败，
仍按原样报错，不会掩盖真实问题。

与 `scripts/fix-gendwarfksyms-libdw.py` 的分工：那个补丁处理「有 DWARF 但
libdw 读不了 .debug_line」（体现在 `is_definition_private` 里）；本补丁处理
「压根没有 DWARF」（体现在 `process_module` 里）。

用法: python3 fix-gendwarfksyms-empty-object.py [--rebuild]
"""
import os
import pathlib
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

COMMON = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/common")
# vendor 树自带独立副本（见 fix-gendwarfksyms-libdw.py 的同名说明）
VENDOR = pathlib.Path(
    _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
SRC_LIST = [COMMON / "scripts/gendwarfksyms/gendwarfksyms.c",
            VENDOR / "scripts/gendwarfksyms/gendwarfksyms.c"]

MARK = "sm8750-gendwarfksyms-empty-object"
OLD = '''		res = dwarf_get_units(dbg, cu, &cu, NULL, NULL, &cudie, NULL);
		if (res < 0)
			error("dwarf_get_units failed: no debugging information?");
'''
NEW = '''		res = dwarf_get_units(dbg, cu, &cu, NULL, NULL, &cudie, NULL);
		if (res < 0) {
			/*
			 * %s: 不产生代码的目标文件（如 rust/bindings.o ——
			 * 只有 pub use 与 const，实测 992 字节、无 .debug_* 段、
			 * 无导出符号）本来就没有 .debug_info，dwarf_get_units
			 * 返回负值属正常情况，不该让整个构建停下。仅在「第一个
			 * CU 就取不到」时跳过；已有 CU 解析成功后再失败仍报错，
			 * 以免掩盖真实问题。详见
			 * scripts/fix-gendwarfksyms-empty-object.py。
			 */
			if (!cu)
				break;
			error("dwarf_get_units failed: no debugging information?");
		}
''' % MARK

for SRC in SRC_LIST:
    if not SRC.is_file():
        print("跳过（不存在）: %s" % SRC)
        continue
    body = SRC.read_text(errors="ignore")
    if MARK in body:
        print("ALREADY patched: %s" % SRC)
    elif OLD in body:
        SRC.write_text(body.replace(OLD, NEW, 1))
        print("patched: %s" % SRC)
    else:
        print("警告：%s 未找到 error 分支原文，跳过" % SRC)

if "--rebuild" in sys.argv:
    KB = pathlib.Path(
        _Y700_WORK + "/aosp/out/soong/.intermediates/device/lenovo/elden/kernel/"
        "android_arm64_armv8-a-branchprot_oryon/kernel_build")
    # make 会触发 oldconfig 交互（choice[1-2?]: 卡住），照 .cmd 手工重编+链接
    print("== 手工重编 gendwarfksyms ==")
    for cmd_file, out in (("scripts/gendwarfksyms/.gendwarfksyms.o.cmd",
                           "scripts/gendwarfksyms/gendwarfksyms.o"),
                          ("scripts/gendwarfksyms/.gendwarfksyms.cmd",
                           "scripts/gendwarfksyms/gendwarfksyms")):
        saved = (KB / cmd_file).read_text(errors="ignore").splitlines()[0]
        cmd = saved.split(" := ", 1)[1]
        r = subprocess.run(["bash", "-c", cmd], cwd=KB, capture_output=True, text=True)
        print("%s rc=%d" % (out, r.returncode))
        if r.returncode:
            print(r.stderr[-1500:])
            sys.exit(r.returncode)
    print("done")
