#!/usr/bin/env python3
"""给 graphics-kernel 定义 KERNEL_SRC，让既有 include 行能正确展开。

## 现象

`msm_hw_fence.h` 修好后继续推进，报：

    graphics-kernel/governor_gpubw_mon.c:10:10: fatal error: 'governor.h' file not found
    graphics-kernel/governor_msm_adreno_tz.c:24:10: fatal error: 'governor.h' file not found
    graphics-kernel/kgsl_pwrscale.c: ...                      （同一头）

## 根因

`graphics-kernel/Kbuild:96` 本来就有这一行（上游写的，不是我加的）：

    ccflags-y += -I$(KGSL_PATH) -I$(KGSL_PATH)/include/linux \
                 -I$(KGSL_PATH)/include -I$(KERNEL_SRC)/drivers/devfreq

`governor.h` 确实存在于 GKI 树：

    common/drivers/devfreq/governor.h

但本模块走的是 `external_modules` 里的 `":kbuild"` 分支，而 `kernel.go:1068`
那个分支只注入 `KCPPFLAGS=-I<root>`，**从不设置 `KERNEL_SRC`**；
只有另一条 `":all"/":modules"` 分支（`kernel.go:1136`）才会传
`M=... KERNEL_SRC=... OUT_DIR=...`。

实测 `make -pn` 确认：`srctree := <GKI common 树>`，而 `KERNEL_SRC` 压根没有定义。
于是该行展开成 `-I/drivers/devfreq`（根目录下不存在），`governor.h` 必然找不到。

## 修法

在 Kbuild 里显式定义 `KERNEL_SRC := $(srctree)`。

`srctree` 在 `M=` 模式下已确认指向 GKI common 树，正是 `drivers/devfreq/governor.h`
所在的那棵；上游把 `KERNEL_SRC` 与 `srctree` 当同义词用（`":all"` 分支传的就是
`topRelativePath(source)`，而 `source` 就是 `kernel_dir`，即 common 树）。

定义放在文件较早位置，确保第 96 行用到时已生效；用 `?=` 避免覆盖别处可能传入的值。

用法: python3 fix-graphics-kernel-src.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

GK = pathlib.Path(
    _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/"
    "sm8750-modules/qcom/opensource/graphics-kernel")
KB = GK / "Kbuild"
HDR = (_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/common/"
       "drivers/devfreq/governor.h")

MARK = "sm8750-kernel-src"
# 放在 SPDX 行之后、任何 ccflags 之前，保证第 96 行用到时已定义
ANCHOR = "# SPDX-License-Identifier: GPL-2.0-only\n"
ENTRY = (
    "\n"
    "# %s: 本模块走 external_modules 的 \":kbuild\" 分支，而 kernel.go 那个分支\n"
    "# 只注入 KCPPFLAGS，**不传 KERNEL_SRC**（只有 \":all\"/\":modules\" 分支才传）。\n"
    "# 而 Kbuild 第 96 行的 ccflags 用了 -I$(KERNEL_SRC)/drivers/devfreq，\n"
    "# 未定义时展开成 -I/drivers/devfreq，导致 governor.h 找不到。\n"
    "# srctree 在 M= 模式下已确认指向 GKI common 树，正是该头所在处；\n"
    "# 用 ?= 以免覆盖外部传入的值。\n"
    "KERNEL_SRC ?= $(srctree)\n" % MARK
)

if not pathlib.Path(HDR).is_file():
    sys.exit("governor.h 不在预期位置，前提假设有误: %s" % HDR)

body = KB.read_text(errors="ignore")
if MARK in body:
    print("ALREADY patched: %s" % KB)
    sys.exit(0)
if ANCHOR not in body:
    sys.exit("未找到 SPDX 锚点，Kbuild 结构可能已变")

KB.write_text(body.replace(ANCHOR, ANCHOR + ENTRY, 1))
print("patched: %s" % KB)

text = KB.read_text(errors="ignore")
i = text.index(MARK)
print("--- 定义处 ---")
print(text[i - 80:i + 480])
j = text.index("-I$(KERNEL_SRC)/drivers/devfreq")
print("--- 该行现在能正确展开 ---")
print(text[j - 130:j + 40])
