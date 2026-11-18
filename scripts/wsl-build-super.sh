#!/bin/bash
# Build only the dynamic-partition (super) image, with a deliberately low job count.
#
# History: wsl-extra-images.sh ran `m vendorbootimage superimage -j4` and got vendor_boot.img,
# then died in superimage with a WSL global OOM (dmesg: global_oom, Killed process ... (make)).
# At OOM time swap had only 1.8Mi in use, i.e. the kernel never got to page out before the
# allocation that killed it. So: fewer concurrent compilers, one target at a time, and a
# swap-friendly vm.swappiness for the duration of the build.
#
#   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root bash /mnt/d/.../scripts/wsl-build-super.sh
set -euo pipefail

export JOBS="${JOBS:-2}"
export LC_ALL=C
export LANG=C

# Only touches the running distro; resets on next WSL restart.
sysctl -w vm.swappiness=100 >/dev/null 2>&1 || true

SRC="${AOSP_DIR:-/root/aosp}"
cd "$SRC"

# shellcheck disable=SC1091
source build/envsetup.sh
lunch uwu_elden aosp_current user

LOG="/root/build-super-$(date +%Y%m%d-%H%M%S).log"
echo "== building superimage -j$JOBS (log: $LOG) =="
echo "== swappiness=$(cat /proc/sys/vm/swappiness) =="

m superimage -j"$JOBS" 2>&1 | tee "$LOG"

echo "== artifacts =="
ls -lh out/target/product/elden/super*.img 2>/dev/null || echo "(no super image)"
echo "== log: $LOG =="
