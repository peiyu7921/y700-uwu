#!/bin/bash
# Copy the locally-modified device/kernel/vendor repos into the synced AOSP tree
# inside WSL2.
#
#   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root \
#       bash /mnt/d/projects/y700-uwu/scripts/wsl-link.sh
#
# Copies instead of symlinking: /mnt/d is a 9p mount and the build reads these trees
# heavily, so keeping them on the WSL2 ext4 disk is much faster and avoids the
# filesystem quirks seen when git data lives on the Windows side.
set -euo pipefail

WIN=/mnt/d/projects/y700-uwu
SRC="${AOSP_DIR:-/root/aosp}"

cd "$SRC"

mkdir -p device/lenovo vendor/lenovo kernel/platform/kernel-6.12/vendor/lenovo

echo "== device tree =="
rsync -a --delete "$WIN/android_device_lenovo_elden/" device/lenovo/elden/

echo "== kernel =="
rsync -a --delete "$WIN/android_kernel_lenovo_sm8750/" \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750/
rsync -a --delete "$WIN/android_kernel_lenovo_sm8750-devicetrees/" \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-devicetrees/
rsync -a --delete "$WIN/android_kernel_lenovo_sm8750-modules/" \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules/

echo "== vendor blobs =="
rsync -a --delete "$WIN/proprietary_vendor_lenovo_elden/" vendor/lenovo/elden/

echo "== vendor/uwu (carries the WITH_GAPPS gate) =="
rsync -a --delete "$WIN/platform_vendor_uwu/" vendor/uwu/

echo "== done =="
ls -d device/lenovo/elden vendor/lenovo/elden vendor/uwu \
    kernel/platform/kernel-6.12/vendor/lenovo/*/ 2>/dev/null
