#!/usr/bin/env python3
"""把 bootloader 固件分区从 AB_OTA_PARTITIONS 里摘掉，让 target_files 打包通过。

## 现象

    AssertionError: Failed to find abl.img
    （add_img_to_target_files.py:759 CheckAbOtaImages）

## 原因

`vendor/lenovo/elden/BoardConfigVendor.mk`（extract-files.py 自动生成）把
radio/ 下 30 个 bootloader 固件分区一并写进了 AB_OTA_PARTITIONS：

    AB_OTA_PARTITIONS += abl aop aop_config bluetooth cpucp ...

它们于是出现在 target_files 的 META/ab_partitions.txt 里，而
`add_img_to_target_files.py` 的 CheckAbOtaImages() 要求 ab_partitions 的每一项
都必须能在 IMAGES/ 或 RADIO/ 下找到：

    available = (images_path in output_zip.namelist() or
                 radio_path in output_zip.namelist())
    assert available, "Failed to find " + img_name

老布局本来靠 make 侧的 `add-radio-file-sha1-checked`
（vendor/lenovo/elden/Android.mk）把每个 img 注册进 INSTALLED_RADIOIMAGE_TARGET，
再由 Makefile:6848 `cp` 到 $(zip_root)/RADIO/。但本树已迁到 soong 的
`android_device` + fsgen 生成 target_files，RADIO/ 只在两种条件下出现
（build/soong/filesystem/android_device.go:1140-1193）：

  1. deviceProps.Radio_partition_name —— 来自 BOARD_RADIO_IMAGE_PATH。
     本设备没设；而且这条路径要求 unpack_tool
     （vendor/google_devices/<platform>/prebuilts/misc_bins/unpack.py），
     树里不存在 —— 因为 elden 的 radio/ 是 30 个独立 img，没有合并的 radio.img。
  2. deviceProps.Radio_partition_names —— 来自 AB_OTA_RADIO_PARTITIONS，
     全树未设置；而且它的消费路径要求每个分区都有对应 bp module
     （getRadioModuleProxy 拿不到就 continue），可 prebuilt_radio_img 在
     build/soong/filesystem/radio.go 里**没有 RegisterModuleType**，
     bp 里根本写不出来。

于是 RADIO/ 始终不存在，30 个 radio 分区必然找不到。实测证据：soong 生成的
target_files_dir 里既无 RADIO/，也无 META/pack_radioimages.txt，ninja 图里
`abl.img` 出现 0 次。

## 修法

在 device 侧把这些 radio 分区从 AB_OTA_PARTITIONS 里过滤掉。

这不是功能取舍：bootloader 固件（abl/aop/xbl/tz/modem…）在 Qualcomm 平台一律
用 fastboot 刷写，不放进 OTA 是通行做法 —— OTA 里带 bootloader，一旦写到一半
断电就是硬砖，A/B 回滚也救不了 bootloader 本身。类原生 ROM 维护者也普遍如此。

过滤名单从 vendor/lenovo/elden/radio/*.img 现算，radio/ 增删文件后重跑本脚本即可。

用法: python3 fix-ota-radio-partitions.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
BC = AOSP / "device/lenovo/elden/BoardConfig.mk"
RADIO = AOSP / "vendor/lenovo/elden/radio"

MARK = "sm8750-ota-no-radio-partitions"
ANCHOR = "include vendor/lenovo/elden/BoardConfigVendor.mk"

body = BC.read_text(errors="ignore")

# 从 radio/ 现算分区名，保持与目录一致
partitions = sorted(p.stem for p in RADIO.glob("*.img"))
if not partitions:
    sys.exit("vendor/lenovo/elden/radio/ 下没有 .img，无法推导分区名")

block = """{anchor}

# {mark}: 这些是 bootloader 固件，不通过 OTA 更新。
#
# BoardConfigVendor.mk（extract-files.py 自动生成）把它们写进了 AB_OTA_PARTITIONS，
# 于是它们进入 target_files 的 META/ab_partitions.txt，而 add_img_to_target_files.py 的
# CheckAbOtaImages() 要求每个 ab_partition 都出现在 IMAGES/ 或 RADIO/ 下。
#
# soong 迁移后 RADIO/ 无法生成（详见 scripts/fix-ota-radio-partitions.py 的说明：
# BOARD_RADIO_IMAGE_PATH 需要不存在的 unpack.py，AB_OTA_RADIO_PARTITIONS 需要的
# prebuilt_radio_img module type 未注册），于是打包中止于
#   AssertionError: Failed to find abl.img
#
# 这些分区在 Qualcomm 平台一律用 fastboot 刷写；OTA 携带 bootloader 一旦写坏就是
# 硬砖，A/B 回滚救不了 bootloader 本身。名单由 radio/*.img 现算。
AB_OTA_PARTITIONS := $(filter-out {parts},$(AB_OTA_PARTITIONS))
""".format(mark=MARK, anchor=ANCHOR, parts=" ".join(partitions))

if MARK in body:
    # 幂等：整块替换，跟随 radio/ 的变化
    start = body.index("include vendor/lenovo/elden/BoardConfigVendor.mk")
    end = body.index("AB_OTA_PARTITIONS := $(filter-out", start)
    end = body.index("\n", end) + 1
    body = body[:start] + block + body[end:]
    action = "updated"
elif ANCHOR in body:
    body = body.replace(ANCHOR, block.rstrip("\n"), 1)
    action = "inserted"
else:
    sys.exit("找不到 '%s'，BoardConfig.mk 结构不符" % ANCHOR)

BC.write_text(body)
print("%s: %s（过滤 %d 个 radio 分区）" % (action, BC, len(partitions)))
print("分区: %s" % " ".join(partitions))
print("--- 结果 ---")
for line in BC.read_text(errors="ignore").splitlines():
    if MARK in line or "BoardConfigVendor" in line or "filter-out" in line:
        print("  " + line[:110])
