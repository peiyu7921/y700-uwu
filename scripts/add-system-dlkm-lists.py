#!/usr/bin/env python3
"""给 system_dlkm 分区补上模块清单，让已编出的 GKI 模块不再丢失。

## 现象

与参考版 OTA（`uwuAOSP-17.0.181-20261101-UNOFFICIAL-elden-signed.zip`）逐分区比对：

    分区           参考版           本树
    system_dlkm    8,429,568 B     348,160 B     <- 只有 4 个配置文件，无任何 .ko
    内含 .ko       90 个           0 个

`kernel.go:181` 的判定是：

    hasSystemDlkm := len(System_dlkm_module_install_list) > 0 &&
                     len(System_dlkm_module_load_list) > 0

本树 device bp 完全没设这两个属性，所以 system_dlkm 分区空转；同时
`kernel.go:193` 的 `System_dep` 也不会设置，vendor_dlkm 做 depmod 时看不到
system_dlkm 的模块依赖。

## 本树实际能装什么

解开参考版 system_dlkm 拿到 90 个模块名，与本树 kernel_modules.zip 的 321 个求交集：
**只有 6 个编出来了** —— 但它们全都没进任何清单（既不在 modules.load /
modules.load.recovery，也不在 modules.load.vendor_dlkm），是彻底的孤儿：

    aes-neon-blk.ko    50,256 B
    efivarfs.ko        55,112 B
    netfs.ko          329,376 B
    pstore_blk.ko      27,464 B
    pstore_zone.ko     44,448 B
    virtio_console.ko  74,848 B
    合计              581,504 B (567 KiB)

其余 84 个没编出，根因在内核配置而非清单：`CONFIG_ZRAM is not set`、
`CONFIG_ZSMALLOC` 未设置等（参考版带 zram.ko/zsmalloc.ko，本树没有）。
那属于 GKI defconfig 层面的差异，改它会触发全量重编，不在本脚本范围内。

## 为什么要单独建清单而不是塞进 vendor_dlkm

Android 的分区语义：system_dlkm 承载 **GKI 通用模块**（与具体 vendor 无关，
可跨设备共用），vendor_dlkm 承载设备专有模块。把这 6 个通用模块放进
vendor_dlkm 会让 OTA 结构偏离参考版，也不利于将来 GKI 升级。

## 加载顺序

`modules.load.system_dlkm` 的顺序即 insmod 顺序，依赖必须先于被依赖项：
`pstore_blk` 依赖 `pstore_zone`，所以 pstore_zone 排前面。

用法: python3 add-system-dlkm-lists.py [--check]
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
DEV = AOSP / "device/lenovo/elden"
BP = DEV / "Android.bp"

MARK = "sm8750-system-dlkm"

# 依赖优先：pstore_blk 需要 pstore_zone
MODULES = [
    "aes-neon-blk.ko",
    "efivarfs.ko",
    "netfs.ko",
    "pstore_zone.ko",
    "pstore_blk.ko",
    "virtio_console.ko",
]

HEADER = """# {mark}: system_dlkm 分区的模块清单。
#
# 这 6 个是 GKI 通用模块，参考版 OTA 的 system_dlkm 里也有同名模块；
# 在本树它们此前「编出来了但没进任何清单」，等于白编。
# 顺序即 insmod 顺序，pstore_blk 依赖 pstore_zone 故后者在前。
#
# 参考版该分区共 90 个模块，其余 84 个本树未编出 —— 根因在内核配置
# （CONFIG_ZRAM is not set、CONFIG_ZSMALLOC 未设置等），不是清单问题。
# 详见 scripts/add-system-dlkm-lists.py。
""".format(mark=MARK)

ANCHOR = '        recovery_module_load_list: ["device/lenovo/elden/modules.load.recovery"],\n'
ENTRY = (
    '        // %s: 补 system_dlkm 分区。kernel.go:181 要求 install/load 两个清单同时非空\n'
    '        // 才会启用该分区；此前两者皆未设置，导致 6 个已编出的 GKI 通用模块\n'
    '        // （aes-neon-blk / efivarfs / netfs / pstore_zone / pstore_blk / virtio_console）\n'
    '        // 既不在 system_dlkm 也不在任何其它清单，参考版 OTA 的 system_dlkm 里则有它们。\n'
    '        system_dlkm_module_install_list: ["device/lenovo/elden/modules.include.system_dlkm"],\n'
    '        system_dlkm_module_load_list: ["device/lenovo/elden/modules.load.system_dlkm"],\n' % MARK
)


def main():
    body = "\n".join([HEADER] + MODULES) + "\n"
    for name in ("modules.load.system_dlkm", "modules.include.system_dlkm"):
        p = DEV / name
        if p.is_file() and p.read_text(errors="ignore") == body:
            print("已存在且一致: %s" % p)
        else:
            p.write_text(body)
            print("写入: %s（%d 个模块）" % (p, len(MODULES)))

    text = BP.read_text(errors="ignore")
    if MARK in text:
        print("Android.bp 已配置 system_dlkm")
    elif ANCHOR in text:
        BP.write_text(text.replace(ANCHOR, ANCHOR + ENTRY, 1))
        print("Android.bp 已加入 system_dlkm_module_*_list")
    else:
        sys.exit("未找到 recovery_module_load_list 行，Android.bp 结构可能已变")

    print("--- 校验 ---")
    for name in ("modules.load.system_dlkm", "modules.include.system_dlkm"):
        p = DEV / name
        n = len([l for l in p.read_text().splitlines()
                 if l.endswith(".ko")])
        print("  %-34s %d 个模块" % (name, n))
    i = BP.read_text(errors="ignore").index("system_dlkm_module_install_list")
    print(BP.read_text(errors="ignore")[i - 120:i + 240])


if __name__ == "__main__":
    main()
