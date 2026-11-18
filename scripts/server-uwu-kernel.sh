#!/bin/bash
# Server-side: switch the elden device tree from the legacy kernel.mk build to uwu_kernel
# (Soong), per https://uwuaosp.uwuniverse.org/docs/soong-only/uwu_kernel/
#
# Everything is generated on the host: kernel.bp is assembled from the CONFIG_* list that
# was extracted out of the kleaf config dict (vendor/lenovo/sm8750/configs/sun_perf.bzl).
set -uo pipefail

DEV="${DEV:-/home/zpy/y700-uwu/aosp/device/lenovo/elden}"
WORK="${WORK:-/home/zpy/y700-uwu}"
OV="$WORK/sun_perf_overrides.txt"

say() { echo "[$(date '+%H:%M:%S')] $*"; }

if [ ! -f "$OV" ]; then
    say "FATAL: $OV missing"
    exit 1
fi
if [ ! -d "$DEV" ]; then
    say "FATAL: $DEV missing"
    exit 1
fi

say "=== [1/4] kernel.bp ==="
{
    cat <<'HDR'
//
// SPDX-FileCopyrightText: The LineageOS Project
// SPDX-License-Identifier: Apache-2.0
//
// uwu_kernel for elden (Lenovo Legion Tab / TB322FC, Qualcomm Sun sm8750).
//
// The Sun kernel is a kleaf/DDK multi-repo layout, consumed here through Kbuild as
// described in https://uwuaosp.uwuniverse.org/docs/soong-only/uwu_kernel/ :
//
//   kernel/platform/kernel-6.12/common                        GKI kernel image
//   kernel/platform/kernel-6.12/vendor/lenovo/sm8750          vendor kernel modules
//   kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules  external DDK modules
//
// The vendor/DDK trees are built through the main kernel's M= mode (:kbuild).

uwu_kernel {
    name: "kernel",
    kernel_dir: "kernel/platform/kernel-6.12/common",
    kernel_arch: "arm64",
    image_name: "Image",
    config: {
        defconfig: "gki_defconfig",
        // CONFIG_* set carried over from the kleaf config dict
        // (vendor/lenovo/sm8750/configs/sun_perf.bzl) used by sun_perf.
        overrides: [
HDR
    sed 's/^/            "/; s/$/",/' "$OV"
    cat <<'TLR'
        ],
    },
    dtb: {
        enabled: true,
        qcom_merge: true,
        target: "dtbs",
        image_name: "dtb.img",
    },
    dtbo: {
        enabled: true,
        target: "dtbs",
        image_name: "dtbo.img",
        page_size: 4096,
    },
    modules: {
        enabled: true,
        external_module_root: "kernel/platform/kernel-6.12/vendor/lenovo",
        external_modules: [
            "sm8750:kbuild",
            "sm8750-modules/qcom/opensource/audio-kernel:kbuild",
            "sm8750-modules/qcom/opensource/bt-kernel:kbuild",
            "sm8750-modules/qcom/opensource/camera-kernel:kbuild",
            "sm8750-modules/qcom/opensource/dataipa:kbuild",
            "sm8750-modules/qcom/opensource/data-kernel:kbuild",
            "sm8750-modules/qcom/opensource/datarmnet:kbuild",
            "sm8750-modules/qcom/opensource/datarmnet-ext:kbuild",
            "sm8750-modules/qcom/opensource/display-drivers:kbuild",
            "sm8750-modules/qcom/opensource/dsp-kernel:kbuild",
            "sm8750-modules/qcom/opensource/eva-kernel:kbuild",
            "sm8750-modules/qcom/opensource/fingerprint:kbuild",
            "sm8750-modules/qcom/opensource/graphics-kernel:kbuild",
            "sm8750-modules/qcom/opensource/mm-drivers:kbuild",
            "sm8750-modules/qcom/opensource/mmrm-driver:kbuild",
            "sm8750-modules/qcom/opensource/securemsm-kernel:kbuild",
            "sm8750-modules/qcom/opensource/spu-kernel:kbuild",
            "sm8750-modules/qcom/opensource/synx-kernel:kbuild",
            "sm8750-modules/qcom/opensource/touch-drivers:kbuild",
            "sm8750-modules/qcom/opensource/video-driver:kbuild",
            "sm8750-modules/qcom/opensource/wlan:kbuild",
        ],
        auto_collect_deps: true,
        vendor_ramdisk_module_install_list: ["modules.include.vendor_ramdisk"],
        vendor_ramdisk_module_load_list: ["modules.load"],
        vendor_dlkm_module_install_list: ["modules.include.vendor_dlkm"],
        vendor_dlkm_module_load_list: ["modules.load.vendor_dlkm"],
        recovery_module_install_list: ["modules.include.recovery"],
        recovery_module_load_list: ["modules.load.recovery"],
    },
}
TLR
} > "$DEV/kernel.bp"
say "  kernel.bp: $(wc -l < "$DEV/kernel.bp") lines"

say "=== [2/4] modules.include.* (install lists) ==="
cp "$DEV/modules.load" "$DEV/modules.include.vendor_ramdisk"
cp "$DEV/modules.load.vendor_dlkm" "$DEV/modules.include.vendor_dlkm"
cp "$DEV/modules.load.recovery" "$DEV/modules.include.recovery"
ls -1 "$DEV"/modules.include.* | sed 's/^/  /'

say "=== [3/4] BoardConfig.mk ==="
python3 - "$DEV/BoardConfig.mk" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

old = """TARGET_KERNEL_PLATFORM_TARGET := sun_perf
TARGET_KERNEL_SOURCE := vendor/lenovo/sm8750
TARGET_KERNEL_UNSAFE_DDK_HEADERS := true
TARGET_KERNEL_VERSION := 6.12

# Kernel modules
BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE := $(DEVICE_PATH)/modules.blocklist
BOARD_VENDOR_KERNEL_MODULES_LOAD := $(strip $(shell cat $(DEVICE_PATH)/modules.load.vendor_dlkm))
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_BLOCKLIST_FILE := $(BOARD_VENDOR_KERNEL_MODULES_BLOCKLIST_FILE)
BOARD_VENDOR_RAMDISK_KERNEL_MODULES_LOAD := $(strip $(shell cat $(DEVICE_PATH)/modules.load))
BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD := $(strip $(shell cat $(DEVICE_PATH)/modules.load.recovery))
BOOT_KERNEL_MODULES := $(BOARD_VENDOR_RAMDISK_RECOVERY_KERNEL_MODULES_LOAD)"""

new = """# uwu_kernel (Soong-based kernel build)
#
# The Sun tree is a kleaf/DDK multi-repo layout; it is consumed through Kbuild by the
# uwu_kernel module declared in kernel.bp. Module install/load lists live in
# modules.include.* / modules.load.* on the device tree.
# See https://uwuaosp.uwuniverse.org/docs/soong-only/uwu_kernel/
BOARD_USES_SOONG_KERNEL := true
SOONG_KERNEL_MODULE := //device/lenovo/elden:kernel"""

if old in text:
    open(path, "w", encoding="utf-8").write(text.replace(old, new))
    print("  BoardConfig.mk: legacy block replaced")
elif "SOONG_KERNEL_MODULE" in text:
    print("  BoardConfig.mk: already migrated")
else:
    print("  WARN: legacy block not found in BoardConfig.mk")
PY

say "=== [4/4] device.mk ==="
python3 - "$DEV/device.mk" <<'PY'
import sys

path = sys.argv[1]
text = open(path, encoding="utf-8").read()

anchor = """# A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/vabc_features.mk)"""

new = """# Kernel (uwu_kernel — declared in kernel.bp, wired up in BoardConfig.mk)
PRODUCT_PACKAGES += \\
    kernel

# A/B
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota/vabc_features.mk)"""

if "PRODUCT_PACKAGES += \\\n    kernel" in text:
    print("  device.mk: already migrated")
elif anchor in text:
    open(path, "w", encoding="utf-8").write(text.replace(anchor, new, 1))
    print("  device.mk: kernel package added")
else:
    print("  WARN: anchor not found in device.mk")
PY

say "=== sanity ==="
grep -n "SOONG_KERNEL_MODULE\|BOARD_USES_SOONG_KERNEL" "$DEV/BoardConfig.mk" || true
grep -n -A1 "uwu_kernel — declared" "$DEV/device.mk" || true
ls -l "$DEV/kernel.bp" || true
say "=== DONE ==="
