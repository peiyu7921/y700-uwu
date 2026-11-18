#!/usr/bin/env python3
"""去掉 gunyah 在 in-tree 遍历里的第二次构建。

## 现象

    duplicate kernel module gh_arm_drv.ko

`modules_staging` 的同一个 release 目录下同时出现：

    kernel/arch/arm64/gunyah/gh_arm_drv.ko   <- vendor in-tree（make modules）
    updates/gh_arm_drv.ko                    <- external_modules 的 :kbuild 条目

## 原因

`vendor_modules_build/.config` 里有 `CONFIG_GH_ARM64_DRV=m`，且 `CONFIG_GUNYAH=y`，
所以 vendor 树自己的 `arch/arm64/Kbuild`：

    obj-$(CONFIG_GUNYAH)	+= gunyah/

会 descend 进 `arch/arm64/gunyah/`，命中 `obj-$(CONFIG_GH_ARM64_DRV) += gh_arm_drv.o`，
在 in-tree 这一次 `make modules` 里就编出来了。

而 device `Android.bp` 的 `external_modules` 里还有：

    "sm8750/arch/arm64/gunyah:kbuild",

这是 bazel 侧的独立 ddk_module（官方 elden 就是这么建的），走 `M=` 编译并装到
`updates/`。两侧都成功，于是展平时按 basename 判重失败。

## 修法

保留 `:kbuild`（与官方 ddk_module 同形，产物落在 `updates/`，也是 vendor 分区语义），
把 in-tree 的 descend 注释掉。gunyah/ 下的 `gunyah_hypercall.c` / `timer.c` 属于
GKI 的 common 树，不走 vendor 树的这份 `arch/arm64/Kbuild`，所以去掉后不会少编译
任何模块（`vendor_modules_build/modules.order` 里 gunyah 只有 gh_arm_drv.o 一条）。

用法: python3 fix-gunyah-duplicate.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

V = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
KB = V / "arch/arm64/Kbuild"

MARK = "sm8750-gunyah-kbuild-only"
TARGET = "obj-$(CONFIG_GUNYAH)\t+= gunyah/"
COMMENT = (
    "# %s: gunyah/ is built by the external_modules entry\n"
    "#   \"sm8750/arch/arm64/gunyah:kbuild\"\n"
    "# (the bazel build uses a separate ddk_module for it). Letting the in-tree descend\n"
    "# compile it as well installs gh_arm_drv.ko twice — once under kernel/ and once\n"
    "# under updates/ — and the kernel_modules flattening step aborts with\n"
    "#   duplicate kernel module gh_arm_drv.ko\n"
    "# Gunyah's gunyah_hypercall.c / timer.c live in the GKI common tree, not here, so\n"
    "# dropping this descend compiles nothing less.\n"
    "# obj-$(CONFIG_GUNYAH)\t+= gunyah/\n" % MARK
)

body = KB.read_text(errors="ignore")
if MARK in body:
    print("ALREADY patched: %s" % KB)
    sys.exit(0)

if TARGET in body:
    body = body.replace(TARGET, COMMENT, 1)
else:
    # 上游可能是空格或其它制表符组合，按行宽松匹配
    lines = body.splitlines(keepends=True)
    hit = False
    for i, line in enumerate(lines):
        if "CONFIG_GUNYAH" in line and "gunyah/" in line and line.lstrip().startswith("obj-"):
            lines[i] = COMMENT
            hit = True
            break
    if not hit:
        sys.exit("未找到 CONFIG_GUNYAH 的 descend 行，请人工检查 %s" % KB)
    body = "".join(lines)

KB.write_text(body)
print("patched: %s" % KB)
print("--- 结果 ---")
print(KB.read_text(errors="ignore"))
