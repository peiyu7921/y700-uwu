#!/usr/bin/env python3
"""给 graphics-kernel 补 mm-drivers/hw_fence/include 的 include 路径。

## 现象

wlan 打通后，构建推进到 graphics-kernel，报：

    graphics-kernel/kgsl_sync.c:215:10: fatal error: 'msm_hw_fence.h' file not found
      215 | #include <msm_hw_fence.h>
          |          ^~~~~~~~~~~~~~~~

## 根因

`msm_hw_fence.h` 实际在**另一个模块**里：

    sm8750-modules/qcom/opensource/mm-drivers/hw_fence/include/msm_hw_fence.h

而 `graphics-kernel/Kbuild` 的 include 只有 `$(KGSL_PATH)`、`$(KERNEL_SRC)/drivers/devfreq`
和 vendor 的 `sm8750/include`，没有跨模块引用 mm-drivers。

上游 bazel 里有 `modules_label(".../mm-drivers:...")` 这类跨模块依赖
（`wlan_qcacld3_modules.bzl` 里能看到同样的模式），kbuild 侧则需要显式加 `-I`。

## 为什么用 $(srctree) 而不是相对路径

本模块走的是 `M=` 外部模块构建，`$(srctree)` 指向 GKI common 树，
`$(srctree)/../vendor/lenovo/sm8750-modules/...` 能稳定定位，
与同文件里已有的两条 vendor include 写法保持一致；
用 `$(src)/../mm-drivers/...` 虽然也能通，但和既有风格不统一。

写法用 `subdir-ccflags-y`：graphics-kernel 的源码在根目录，
`ccflags-y` 也够用，但 `subdir-` 前缀能让将来新增的子目录一并继承。

用法: python3 add-hw-fence-include.py
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
HDR = (_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/"
       "sm8750-modules/qcom/opensource/mm-drivers/hw_fence/include/msm_hw_fence.h")

MARK = "sm8750-hw-fence-include"
ANCHOR = "subdir-ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include/linux\n"
ENTRY = (
    "# %s: kgsl_sync.c:215 会 #include <msm_hw_fence.h>，该头属于**另一个模块**\n"
    "# mm-drivers/hw_fence/include/（上游 bazel 里是跨 ddk_module 依赖，\n"
    "# kbuild 侧必须显式 -I）。用 $(srctree) 定位，与上面两条 vendor include 同风格。\n"
    "subdir-ccflags-y += "
    "-I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/mm-drivers/hw_fence/include\n"
    % MARK
)

if not pathlib.Path(HDR).is_file():
    sys.exit("msm_hw_fence.h 不存在，路径假设有误: %s" % HDR)

body = KB.read_text(errors="ignore")
if MARK in body:
    print("ALREADY patched: %s" % KB)
    sys.exit(0)
if ANCHOR not in body:
    sys.exit("未找到 vendor include 锚点行，Kbuild 结构可能已变")

KB.write_text(body.replace(ANCHOR, ANCHOR + ENTRY, 1))
print("patched: %s" % KB)
text = KB.read_text(errors="ignore")
i = text.index(MARK)
print("--- 结果 ---")
print(text[i - 200:i + 400])
