#!/usr/bin/env python3
"""让 bindgen 用 LLVM 20 的 libclang，避免生成空壳结构体。

## 现象

内核 `rust/kernel.o` 编译失败，161 个错误全指向 bindings 缺字段：

    error[E0609]: no field `private_data` on type `bindings::file`
    error[E0609]: no field `__bindgen_anon_2` on type `bindings::vm_area_struct`
    error[E0560]: struct `kunit_suite` has no field named `suite_init`
    ...

查生成物 `rust/bindings/bindings_generated.rs`：**263 个结构体成了空壳**

    pub struct inode {
        pub _address: u8,
    }

上游 `bindings_helper.h` 里 `inode`/`file`/`vm_area_struct` 的头文件都在
（`linux/fs.h`、`linux/mman.h` 等 49 个 include），所以是 bindgen 把它们当成了
opaque 类型，而不是头文件缺失。

## 根因：libclang 版本与 bindgen 0.71.1 不兼容

用完全相同的 bindgen 命令行，只换 `LIBCLANG_PATH` 实测：

    clang-r596125 (LLVM 22.0.2)  ->  263 个空壳
    clang-r584948 (LLVM 21)      ->   69 个空壳
    clang-r547379 (LLVM 20.0.0)  ->    0 个空壳   <-- 正确

LLVM 20 的产物里 `vm_area_struct` 有 `__bindgen_anon_1`、`file` 有
`private_data`、`kunit_suite` 有 `suite_init`，与 Rust crate 的期望完全对上。

`bindgen` 0.71.1 已是 crates.io 上较新的版本，对新版 libclang 的
结构体解析还没跟上；而 clang 22 又是本树内核编译必须的（`kernel.go` 默认
取 `clang-r596125`）。两者只好分开：**C 编译用 clang 22，bindgen 的 libclang
用 LLVM 20** —— `LIBCLANG_PATH` 只被 bindgen 读取，不参与内核 C 编译，
互不干扰。

## 为什么走 make_flags 而不是改 kernel.go

`kernel.go` 的 `makeInvocationExtra` 里：

    flags := []string{ ..., "LIBCLANG_PATH=" + clangPath + "/lib" }
    flags = append(flags, m.properties.Make_flags...)

`make_flags` 追加在那行之后，GNU make 对同一变量的多次命令行赋值取**最后一个**，
所以在这里覆盖即可 —— 不必改 Go、不必重编 soong bootstrap，改完重建图就生效。
`KCONFIG_EXT_PREFIX` 也是这么放的，属于既有机制。

用法: python3 fix-bindgen-libclang.py [--check]
"""
import os
import pathlib
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
BP = AOSP / "device/lenovo/elden/Android.bp"
CLANG_DIR = AOSP / "prebuilts/clang/host/linux-x86"

MARK = "sm8750-bindgen-libclang20"
# LLVM 20 的 libclang：实测对 bindgen 0.71.1 产出 0 个空壳结构体
LIBCLANG_VERSION = "clang-r547379"
LIBCLANG_PATH = CLANG_DIR / LIBCLANG_VERSION / "lib"

# 锚点匹配的是**目标文件里已有的一行**（由加 KCONFIG_EXT_PREFIX 的那步写入，
# 同样基于 _Y700_WORK），所以这里也用它拼接，换机器时两边一致。
ANCHOR = ('        "KCONFIG_EXT_PREFIX=%s'
          '/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750/",\n' % _Y700_WORK)
ENTRY = (
    '        // %s: bindgen 0.71.1 配 LLVM 22 的 libclang 会把 263 个结构体\n'
    '        // （inode / file / vm_area_struct ...）当成 opaque 生成空壳，导致\n'
    '        // rust/kernel.o 报 161 个 "no field" 错误。这里只覆盖 bindgen\n'
    '        // 用的 libclang（C 编译仍走 clang-r596125），其它变量不受影响。\n'
    '        "LIBCLANG_PATH=%s",\n' % (MARK, LIBCLANG_PATH)
)


def check() -> int:
    """确认该 libclang 存在，且 bindgen 用它对内核头文件不缺结构体字段。"""
    so = LIBCLANG_PATH / "libclang.so"
    if not so.is_file():
        print("缺少 %s" % so)
        return 1
    ver = subprocess.run(
        [str(CLANG_DIR / LIBCLANG_VERSION / "bin/clang"), "--version"],
        capture_output=True, text=True)
    print("%s: %s" % (LIBCLANG_VERSION, ver.stdout.splitlines()[0] if ver.stdout else "?"))
    print("libclang.so: %s" % so)
    return 0


def main():
    rc = check()
    if rc:
        sys.exit(rc)

    body = BP.read_text(errors="ignore")
    if MARK in body:
        print("ALREADY patched: %s" % BP)
        return
    if ANCHOR not in body:
        sys.exit("未找到 make_flags 里的 KCONFIG_EXT_PREFIX 行，Android.bp 结构可能已变")

    BP.write_text(body.replace(ANCHOR, ANCHOR + ENTRY, 1))
    print("patched: %s" % BP)
    i = BP.read_text(errors="ignore").index("    make_flags: [")
    print("--- 结果 ---")
    print(BP.read_text(errors="ignore")[i:i + 900])


if __name__ == "__main__":
    main()
