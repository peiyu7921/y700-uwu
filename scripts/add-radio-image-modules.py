#!/usr/bin/env python3
"""为 30 个 bootloader 固件分区建 prebuilt_radio_image 模块，并恢复 AB_OTA 配置。

## 背景

参考版 OTA 的 payload 有 **44 个分区**，本树只有 14 个，少的 30 个正是
`vendor/lenovo/elden/radio/` 下的固件镜像（abl/aop/modem/tz/xbl...）。
此前 `scripts/fix-ota-radio-partitions.py` 把它们从 `AB_OTA_PARTITIONS` 里
filter-out 掉，只是绕过了 `Failed to find abl.img`，并没有真正恢复。

## 修复链（三步，缺一不可）

1. **注册模块类型** —— `scripts/register-prebuilt-radio-image.py`（已完成）
   上游 `radio.go:53` 的 `PrebuiltRadioImgFactory` 早就写好，只是没注册。

2. **建模块**（本脚本）—— 每个分区一个 `prebuilt_radio_image`，`src` 指向
   `radio/<name>.img`。必须建在 `vendor/lenovo/elden/`：`paths.go:2243` 的
   `validatePath` 明确拒绝 `../` 与绝对路径，不能从 device 目录跨过来引用。

3. **恢复 AB_OTA 配置**（本脚本）——
   - `BoardConfig.mk`：去掉 filter-out，让 30 个分区回到 `AB_OTA_PARTITIONS`
   - `AB_OTA_RADIO_PARTITIONS` 列出这 30 个
   - `uwuRadio` soong config 把分区名映射到 `//vendor/lenovo/elden:<name>`
     （`radioPartitionModuleNames()` 读的正是这个映射；不设则退化为短名，
     而短名在 device 命名空间里解析不到）

## 为什么不需要 unpack.py

`prebuiltRadioImg.partitionFiles()` 只在 `ab_ota_partitions` 非空时才调用
`unpack_tool`。elden 的 `radio/` 是 30 个独立 img、没有合并的 radio.img，
所以每个模块的 `ab_ota_partitions` 留空，`unpack_tool` 永不触发
—— 正好绕开树里缺失的 `vendor/google_devices/*/prebuilts/misc_bins/unpack.py`。

## 不触发版本校验

`check_radio_versions --board_info_check` 只在设了 `Bootloader` 或
`Radio_partition_name`（单数）时才会去比对 `board-info.txt`。本方案用的是
`Radio_partition_names`（复数），不进入该分支；`board-info.txt` 也只有
`require board=...`，本就不含版本项。

用法: python3 add-radio-image-modules.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
RADIO = AOSP / "vendor/lenovo/elden/radio"
VBP = AOSP / "vendor/lenovo/elden/Android.bp"
BC = AOSP / "device/lenovo/elden/BoardConfig.mk"
DEVICE_MK = AOSP / "device/lenovo/elden/device.mk"

MARK = "sm8750-radio-image"


def partitions():
    ps = sorted(p.stem for p in RADIO.glob("*.img"))
    if not ps:
        sys.exit("%s 下没有 .img" % RADIO)
    return ps


def write_modules(ps):
    block = ["\n// %s: 30 个 bootloader 固件分区各自一个 prebuilt_radio_image 模块。" % MARK,
             "// 上游 radio.go:53 早就写好了工厂函数却没注册（见 scripts/register-prebuilt-radio-image.py），",
             "// 注册后每个分区一个模块，ab_ota_partitions 留空以免触发缺失的 unpack.py。",
             "// src 必须是相对路径：soong 的 validatePath 拒绝 ../ 与绝对路径。", ""]
    for p in ps:
        block.append("prebuilt_radio_image {")
        block.append('    name: "%s",' % p)
        block.append('    src: "radio/%s.img",' % p)
        block.append("}")
        block.append("")

    text = VBP.read_text(errors="ignore")
    if MARK in text:
        # 幂等：删掉旧的整段再重写，跟随 radio/ 增删
        start = text.index("\n// %s:" % MARK)
        text = text[:start] + "\n"
    VBP.write_text(text.rstrip("\n") + "\n" + "\n".join(block))
    print("vendor bp 追加 %d 个 prebuilt_radio_image 模块" % len(ps))


def fix_boardconfig(ps):
    text = BC.read_text(errors="ignore")
    # 去掉 fix-ota-radio-partitions.py 插入的 filter-out 整块
    if "sm8750-ota-no-radio-partitions" in text:
        start = text.index("# sm8750-ota-no-radio-partitions")
        end = text.index("AB_OTA_PARTITIONS := $(filter-out", start)
        end = text.index("\n", end) + 1
        text = text[:start] + text[end:]
        print("已移除旧的 filter-out 块")

    entry = (
        "\n# %s: 让 30 个固件分区真正进 OTA。\n"
        "# 上游 radio.go 的 prebuilt_radio_image 注册后，每个分区一个模块；\n"
        "# AB_OTA_RADIO_PARTITIONS 驱动 fsgen 把模块产物 cp 到 target_files/RADIO/，\n"
        "# CheckAbOtaImages 才找得到它们。详见 scripts/add-radio-image-modules.py。\n"
        "AB_OTA_RADIO_PARTITIONS := %s\n" % (MARK, " ".join(ps))
    )
    if MARK not in text:
        text = text.rstrip("\n") + "\n" + entry
        print("BoardConfig.mk 已设 AB_OTA_RADIO_PARTITIONS（%d 个）" % len(ps))
    BC.write_text(text)


def fix_vendor_map(ps):
    text = DEVICE_MK.read_text(errors="ignore")
    if MARK in text:
        print("device.mk 已有 uwuRadio 映射")
        return
    lines = ["\n# %s: 把分区名映射到 vendor 命名空间的模块全限定名。" % MARK,
             "# radioPartitionModuleNames() 读 VendorConfig(\"uwuRadio\")；",
             "# 不设会退化成短名，而短名在 device 命名空间解析不到。"]
    for p in ps:
        lines.append("$(call soong_config_set,uwuRadio,%s,//vendor/lenovo/elden:%s)" % (p, p))
    DEVICE_MK.write_text(text.rstrip("\n") + "\n" + "\n".join(lines) + "\n")
    print("device.mk 已设 %d 条 uwuRadio 映射" % len(ps))


def main():
    ps = partitions()
    write_modules(ps)
    fix_boardconfig(ps)
    fix_vendor_map(ps)
    print("--- 校验 ---")
    print("分区数: %d" % len(ps))
    print("  " + " ".join(ps))


if __name__ == "__main__":
    main()
