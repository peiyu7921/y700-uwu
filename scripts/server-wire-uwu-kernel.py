#!/usr/bin/env python3
"""Server-side: wire the elden device tree to uwu_kernel (Soong kernel build)."""
import os
import shutil

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

DEV = _Y700_WORK + "/aosp/device/lenovo/elden"

LEGACY_PREFIXES = (
    "TARGET_KERNEL_PLATFORM_TARGET",
    "TARGET_KERNEL_SOURCE",
    "TARGET_KERNEL_UNSAFE_DDK_HEADERS",
    "TARGET_KERNEL_VERSION",
    "BOARD_VENDOR_KERNEL_MODULES",
    "BOARD_VENDOR_RAMDISK_KERNEL_MODULES",
    "BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES",
    "BOOT_KERNEL_MODULES",
)

NEW_BLOCK = [
    "# uwu_kernel (Soong-based kernel build)",
    "#",
    "# The Sun tree is a kleaf/DDK multi-repo layout; it is consumed through Kbuild by the",
    "# uwu_kernel module declared in kernel.bp. Module install/load lists live in",
    "# modules.include.* / modules.load.* on the device tree.",
    "# See https://uwuaosp.uwuniverse.org/docs/soong-only/uwu_kernel/",
    "BOARD_USES_SOONG_KERNEL := true",
    "SOONG_KERNEL_MODULE := //device/lenovo/elden:kernel",
]


def migrate_board_config():
    path = os.path.join(DEV, "BoardConfig.mk")
    with open(path, encoding="utf-8") as fh:
        lines = fh.read().split("\n")

    if any("SOONG_KERNEL_MODULE" in ln for ln in lines):
        print("BoardConfig.mk: already migrated")
        return

    out = []
    inserted = False
    for ln in lines:
        if ln.strip() == "# Kernel modules" or ln.startswith(LEGACY_PREFIXES):
            if not inserted:
                out.extend(NEW_BLOCK)
                inserted = True
            continue
        out.append(ln)

    if not inserted:
        print("BoardConfig.mk: WARN legacy block not found")
        return

    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    print("BoardConfig.mk: migrated (%d legacy lines removed)" % (len(lines) - len(out) + len(NEW_BLOCK)))


def migrate_device_mk():
    path = os.path.join(DEV, "device.mk")
    with open(path, encoding="utf-8") as fh:
        text = fh.read()

    marker = "PRODUCT_PACKAGES += \\\n    kernel"
    if marker in text:
        print("device.mk: already migrated")
        return

    anchor = "# A/B\n$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/vabc_features.mk)"
    new = (
        "# Kernel (uwu_kernel, declared in kernel.bp and wired up in BoardConfig.mk)\n"
        "PRODUCT_PACKAGES += \\\n    kernel\n\n" + anchor
    )

    if anchor not in text:
        print("device.mk: WARN anchor not found")
        return

    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace(anchor, new, 1))
    print("device.mk: kernel package added")


def make_install_lists():
    pairs = [
        ("modules.load", "modules.include.vendor_ramdisk"),
        ("modules.load.vendor_dlkm", "modules.include.vendor_dlkm"),
        ("modules.load.recovery", "modules.include.recovery"),
    ]
    for src, dst in pairs:
        sp = os.path.join(DEV, src)
        dp = os.path.join(DEV, dst)
        if not os.path.exists(sp):
            print("WARN missing %s" % src)
            continue
        shutil.copyfile(sp, dp)
        print("%s: %d lines" % (dst, sum(1 for _ in open(dp, encoding="utf-8"))))


if __name__ == "__main__":
    migrate_board_config()
    migrate_device_mk()
    make_install_lists()
    print("UWU_WIRED_OK")
