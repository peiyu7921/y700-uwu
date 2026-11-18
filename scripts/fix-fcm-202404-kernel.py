#!/usr/bin/env python3
"""让 FCM 202404 也认可 6.12 内核，使 OTA 打包的 VINTF 校验通过。

## 现象

    RuntimeError: VINTF compatibility check failed
    ERROR: files are incompatible: Runtime info and framework compatibility matrix
    are incompatible: No kernel entry found for kernel version 6.12 at kernel FCM
    version 202404. The following kernel requirements are checked:
      Minimum LTS: 6.6.0, kernel FCM version: 202404

## 原因

`device/lenovo/elden/vintf/manifest_sun.xml` 声明 target-level="202404"（该文件来自
vendor blobs，Qualcomm 原厂是 Android 15 + 6.6 内核），而本树把内核换成了 GKI 6.12。

`hardware/interfaces/compatibility_matrices/Android.bp` 里：

    framework_compatibility_matrix.202404.xml  -> kernel_configs: ["kernel_config_v_6.6"]
    framework_compatibility_matrix.202504.xml  -> kernel_configs: ["kernel_config_b_6.12"]

于是 202404 这份 framework matrix 只带 6.6 的 kernel entry，而
`system/libvintf/KernelInfo.cpp:81` 先用

    if (mVersion.dropMinor() != minLts.dropMinor()) continue;

按主次版本号过滤，6.6 的 entry 全部被滤掉 -> kernelsForLevel 为空 ->
"No kernel entry found"。

## 修法

给 202404 的 kernel_configs 补上 kernel_config_b_6.12。

为什么不是别的做法：
  - 把 target-level 提到 202504：202504 的 framework matrix 有 88 个 HAL 要求
    （202404 是 83 个），device manifest 来自 vendor blobs、无法跟着改，
    会把问题从"缺 kernel entry"换成"缺 HAL"。
  - 只加 --skip_compatibility_check：能过，但只是绕过检查，产物与真机的
    framework/device 组合仍然没被验证过。

补 entry 之后 202404 同时含 6.6 与 6.12 两条，匹配是「或」语义
（KernelInfo.cpp:167 之后按 matrixKernelLevel 收集所有候选），
所以原来 6.6 的设备不受影响。matrixKernelLevel == kernelLevel(202404)，
不会被 :113 的 `matrixKernelLevel > kernelLevel` 过滤掉。

用法: python3 fix-fcm-202404-kernel.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

BP = pathlib.Path(_Y700_WORK + "/aosp/hardware/interfaces/compatibility_matrices/Android.bp")

MARK = "sm8750-fcm-202404-6.12"
TARGET = '''    name: "framework_compatibility_matrix.202404.xml",
    stem: "compatibility_matrix.202404.xml",
    srcs: [
        "compatibility_matrix.202404.xml",
    ],
    kernel_configs: [
        "kernel_config_v_6.6",
    ],'''
NEW = '''    name: "framework_compatibility_matrix.202404.xml",
    stem: "compatibility_matrix.202404.xml",
    srcs: [
        "compatibility_matrix.202404.xml",
    ],
    // %s: elden 的 device manifest 声明 target-level="202404"（来自 vendor blobs），
    // 但本树的内核是 GKI 6.12。AOSP 只在 202504 里注册了 kernel_config_b_6.12，
    // KernelInfo.cpp:81 按主次版本号过滤后，202404 没有任何 6.12 的 kernel entry，
    // ota_from_target_files 的 VINTF 校验因此报
    //   No kernel entry found for kernel version 6.12 at kernel FCM version 202404
    // 这里补上 6.12，202404 于是同时提供 6.6 与 6.12 两条（匹配置为「或」语义，
    // 不影响仍是 6.6 的设备）。详见 scripts/fix-fcm-202404-kernel.py。
    kernel_configs: [
        "kernel_config_v_6.6",
        "kernel_config_b_6.12",
    ],''' % MARK

body = BP.read_text(errors="ignore")

if MARK in body:
    print("ALREADY patched: %s" % BP)
    sys.exit(0)

if TARGET not in body:
    sys.exit("未找到 202404 的 module 定义原文，Android.bp 结构可能已变，请人工检查")

BP.write_text(body.replace(TARGET, NEW, 1))
print("patched: %s" % BP)
print("--- 结果 ---")
text = BP.read_text(errors="ignore")
start = text.index('name: "framework_compatibility_matrix.202404.xml"')
print(text[start - 5:start + 900])
