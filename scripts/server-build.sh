#!/bin/bash
# Compile uwuAOSP 17 for elden on the remote server.
#   bash server-build.sh
set -euo pipefail

WORK="${WORK:-/home/zpy/y700-uwu}"
SRC="$WORK/aosp"
JOBS="${JOBS:-12}"

cd "$SRC"

# uwuAOSP resolves this through breakfast: lunch uwu_elden aosp_current <variant>.
# Using trunk_staging produces a different vendor/prebuilt configuration and cascading
# soong errors.
source build/envsetup.sh
lunch uwu_elden aosp_current user

LOG="$WORK/build-$(date +%Y%m%d-%H%M%S).log"
echo "== building -j$JOBS (log: $LOG) =="
m otapackage -j"$JOBS" 2>&1 | tee "$LOG"

echo "== artifacts =="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
