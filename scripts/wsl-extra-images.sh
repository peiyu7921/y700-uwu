#!/bin/bash
# Build the remaining partition images for elden inside WSL.
#
# wsl-build.sh only targets systemimage/vendorimage/bootimage (a deliberate scope limit so
# OTA packaging does not exhaust the 20 GB WSL). The device is dynamic-partition + has a
# separate vendor_boot and dtbo partition, so those targets have to be built explicitly.
set -euo pipefail

cd /root/aosp

# shellcheck disable=SC1091
source build/envsetup.sh
lunch uwu_elden aosp_current user

m vendorbootimage superimage -j"${JOBS:-4}" 2>&1 | tee "/root/build-extra-$(date +%Y%m%d-%H%M%S).log"
