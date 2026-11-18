#!/usr/bin/env python3
"""保证内核 Rust 构建所需的 bindgen 就位且进入构建 PATH。

## 为什么需要它

CONFIG_ASHMEM 在 6.12 是 Rust 实现（`drivers/staging/android/ashmem*.rs`），
Kconfig 是 `depends on SHMEM && RUST`。而 `CONFIG_RUST` 要求
`scripts/rust_is_available.sh` 通过，该脚本同时检查 RUSTC 与 BINDGEN。

本机缺 bindgen 的根因：`prebuilts/clang-tools` 是**空工作树**
（bare repo `in-pack: 0`，repo sync 中断遗留），
所以 `prebuilts/clang-tools/linux-x86/bin/bindgen` 与
同目录的 `header-abi-dumper` 一起缺失。
`prebuilts/rust` 也没有 `linux-x86`，只有 `bootstrap`。
但 `prebuilts/rust-toolchain/linux-x86/1.93.1/bin/rustc` 是有的。

## 版本下限是 0.69.5，不是 min-tool-version.sh 里的 0.65.1

`min-tool-version.sh` 写 0.65.1，但 `rust_is_available.sh` 另有一段：
bindgen < 0.69.5 配 libclang >= 19.1 会因 rust-lang/rust-bindgen#2824
生成错误绑定，脚本直接拒绝。本机 clang-r596125 的 libclang 是 22.0.2，
所以必须 >= 0.69.5。实测 0.69.1 被拒、0.71.1 通过。

## 为什么链进 prebuilts/build-tools/linux-x86/bin/

`vendor/uwu/build/soong/kernel/kernel.go` 的 `makeInvocationExtra` 会构造

    PATH=<clang>/bin:prebuilts/build-tools/linux-x86/bin:<kernel-build-tools>/bin:...:$PATH

把该目录放在最前。kbuild 里 `BINDGEN = bindgen`（Makefile:524）并按名字查找，
所以只需让 `bindgen` 在这个目录里可见，不必改 device bp 或 kernel.go。

用法: python3 fix-rust-toolchain-bindgen.py [--install]
"""
import os
import pathlib
import shutil
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
CARGO_HOME = pathlib.Path(os.path.expanduser("~/.cargo-bindgen"))
BINDGEN = CARGO_HOME / "bin/bindgen"
PATH_DIR = AOSP / "prebuilts/build-tools/linux-x86/bin"
LINK = PATH_DIR / "bindgen"
RUSTC = AOSP / "prebuilts/rust-toolchain/linux-x86/1.93.1/bin/rustc"
CLANG = AOSP / "prebuilts/clang/host/linux-x86/clang-r596125"

MIN_VER = (0, 69, 5)
INSTALL_VER = "0.71.1"


def ver_of(binary):
    try:
        out = subprocess.run([str(binary), "--version"], capture_output=True,
                             text=True, timeout=60).stdout
    except Exception:
        return None
    for tok in out.split():
        parts = tok.split(".")
        if len(parts) == 3 and all(p.isdigit() for p in parts):
            return tuple(int(p) for p in parts)
    return None


def install():
    print("安装 bindgen-cli %s（首次约 10 分钟）" % INSTALL_VER)
    env = dict(os.environ)
    env["PATH"] = "%s:%s" % (RUSTC.parent, env.get("PATH", ""))
    env["LIBCLANG_PATH"] = str(CLANG / "lib")
    subprocess.run([str(RUSTC.parent / "cargo"), "install", "bindgen-cli",
                    "--version", INSTALL_VER, "--locked",
                    "--root", str(CARGO_HOME), "--force"], env=env, check=True)


def main():
    want_install = "--install" in sys.argv

    ver = ver_of(BINDGEN) if BINDGEN.exists() else None
    print("现有 bindgen: %s" % ((".".join(map(str, ver))) if ver else "无"))

    if ver is None or ver < MIN_VER:
        if not want_install:
            sys.exit("bindgen 缺失或低于 %s，加 --install 重新安装"
                     % ".".join(map(str, MIN_VER)))
        install()
        ver = ver_of(BINDGEN)
        if ver is None or ver < MIN_VER:
            sys.exit("安装后版本仍不达标: %s" % ver)

    print("bindgen 版本: %s（下限 %s）" % (
        ".".join(map(str, ver)), ".".join(map(str, MIN_VER))))

    PATH_DIR.mkdir(parents=True, exist_ok=True)
    if LINK.is_symlink() or LINK.exists():
        LINK.unlink()
    LINK.symlink_to(BINDGEN)
    print("已链接: %s -> %s" % (LINK, BINDGEN))

    # 构建时 kernel.go 会把该目录放进 PATH 最前，这里同步自检一次
    env = dict(os.environ)
    env["PATH"] = "%s:%s" % (PATH_DIR, env.get("PATH", ""))
    got = shutil.which("bindgen", path=env["PATH"])
    print("PATH 中可见: %s" % got)
    if not got:
        sys.exit("bindgen 未进入 PATH")


if __name__ == "__main__":
    main()
