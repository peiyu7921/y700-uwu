#!/usr/bin/env python3
"""注册 prebuilt_radio_image 模块类型，让 30 个 bootloader 固件分区能进 OTA。

## 现象

与参考版 OTA（`uwuAOSP-17.0.181-20261101-UNOFFICIAL-elden-signed.zip`）比对，
payload 里的分区数差 30 个：

    参考版：44 个分区（含 abl aop aop_config bluetooth cpucp ... xbl_ramdump）
    本树  ：14 个分区（只有 boot dtbo init_boot odm product recovery system
                        system_dlkm system_ext vbmeta vbmeta_system vendor
                        vendor_boot vendor_dlkm）

这 30 个正是 `vendor/lenovo/elden/radio/` 下的固件镜像，参考版把它们作为
独立分区打进 payload，本树因为生成不出 `RADIO/` 目录而在
`scripts/fix-ota-radio-partitions.py` 里被 `filter-out` 掉了。

## 根因链

`add_img_to_target_files.py:759` 的 `CheckAbOtaImages` 要求 `ab_partitions.txt`
里每个分区都能在 target_files 的 `IMAGES/` **或** `RADIO/` 下找到。30 个固件
分区没有对应镜像，于是报 `Failed to find abl.img`。

`RADIO/` 只在 `build/soong/filesystem/android_device.go:1178` 生成，条件是
`deviceProps.Radio_partition_names` 非空；而它来自
`AbOtaRadioPartitions` ← `AB_OTA_RADIO_PARTITIONS` ← 未设置。
`radioPartitionModuleNames()` 会把每个分区名当作 soong module 去解析，
拿不到就以分区名本身兜底。

所以缺的关键一环是：**没有对应的 soong module**。

## 为什么是「注册」而不是「另写实现」

`build/soong/filesystem/radio.go:53` 的 `PrebuiltRadioImgFactory()` 已经写好了，
上游注释原话：

    // TODO(soong-team): This module should be registered with the name
    // `prebuilt_radio_image`. If not, update the property error in
    // [androidDevice.checkRadioVersion]. Remove this TODO once the module type is
    // registered.

即上游本就打算注册它，只是还没做。本脚本补上这一行注册，属于按上游意图补全，
不是自创机制。

## 为什么不需要 unpack_tool

`prebuiltRadioImg.partitionFiles()` 只有在 `ab_ota_partitions` 非空时才调用
`unpack_tool`（那是「从一个合并的 radio.img 里拆分区」的场景）。
elden 的 `radio/` 是 30 个**独立** img 文件、没有合并的 `radio.img`，
所以每个分区一个 module、`ab_ota_partitions` 留空，`unpack_tool` 根本不会用到
—— 正好绕开树里缺失的 `vendor/google_devices/*/prebuilts/misc_bins/unpack.py`。

## 代价

改了 `build/soong` 属于 soong bootstrap 层，必须重编 `soong_build` 并重新生成
ninja 图；`filesystem` 包被 soong_build 静态链接，改一行也要全量重编 bootstrap。
这是本修法的固有成本，无法避免。

用法: python3 register-prebuilt-radio-image.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
FS = AOSP / "build/soong/filesystem/filesystem.go"

MARK = "sm8750-prebuilt-radio-image"
ANCHOR = '\tctx.RegisterModuleType("raw_binary", rawBinaryFactory)\n'
ENTRY = (
    "\t// %s: 上游 radio.go:53 的 PrebuiltRadioImgFactory 早已写好，但一直没注册\n"
    "\t// （radio.go 里的 TODO 原话就是 \"This module should be registered with the name\n"
    "\t// `prebuilt_radio_image`\"）。不注册则 bp 里写不出该模块，\n"
    "\t// AB_OTA_RADIO_PARTITIONS 也就没有对应 module 可解析，最终 RADIO/ 目录为空、\n"
    "\t// 30 个 bootloader 固件分区进不了 OTA。\n"
    "\tctx.RegisterModuleType(\"prebuilt_radio_image\", PrebuiltRadioImgFactory)\n" % MARK
)

body = FS.read_text(errors="ignore")
if MARK in body:
    print("ALREADY patched: %s" % FS)
    sys.exit(0)
if ANCHOR not in body:
    sys.exit("未找到 raw_binary 注册行，filesystem.go 结构可能已变")

FS.write_text(body.replace(ANCHOR, ANCHOR + ENTRY, 1))
print("patched: %s" % FS)
text = FS.read_text(errors="ignore")
i = text.index("func registerBuildComponents")
print("--- 结果 ---")
print(text[i:i + 1000])
