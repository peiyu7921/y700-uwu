#!/bin/bash
# Build uwuAOSP 17 for elden inside WSL2 Ubuntu.
#
#   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root \
#       bash /mnt/d/projects/y700-uwu/scripts/wsl-build.sh
#
# 8 jobs: WSL capped at 20 GB so Windows keeps ~11 GB. -j12 crashed Windows;
# -j4/-j6 left the 10 cores underused (load 8.5 at -j6).
set -euo pipefail

export JOBS="${JOBS:-4}"
export LC_ALL=C
export LANG=C

SRC="${AOSP_DIR:-/root/aosp}"
cd "$SRC"

# shellcheck disable=SC1091
source build/envsetup.sh

# uwuAOSP uses breakfast, which expands to: lunch uwu_elden aosp_current <variant>
# (vendor/uwu/build/envsetup.sh: aosp_target_release=aosp_current). Using trunk_staging
# instead produced a different vendor-variant/prebuilt configuration and cascading
# soong errors that were never real bugs.
echo "== lunch uwu_elden aosp_current user =="
lunch uwu_elden aosp_current user

echo "== building with -j$JOBS =="
LOG="/root/build-$(date +%Y%m%d-%H%M%S).log"
# "bacon" only exists in LineageOS; uwuAOSP ships no build/tasks/bacon.mk. The device is
# A/B (AB_OTA_UPDATER := true), so otapackage is the target that produces the flashable zip.
# Scoped build: the host only has 31.6 GB, and Android 17's soong analysis alone peaks
# above 15 GB. Packaging a full OTA on top of that is what crashed Windows. Building just
# the key images still exercises every one of our fixes (framework overlay, HAL, sepolicy,
# vendor blobs) without the OTA packaging overhead.
m systemimage vendorimage bootimage -j"$JOBS" 2>&1 | tee "$LOG"

echo "== artifacts =="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
echo "== log: $LOG =="
