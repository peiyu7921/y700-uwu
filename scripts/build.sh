#!/bin/bash
# Build uwuAOSP 17 for elden inside the build container.
#
#   docker run --rm -it -v /d/projects/y700-uwu:/src -w /src aosp-builder:17 \
#       bash scripts/build.sh
#
# Uses 12 jobs by default: 16 threads are available, but each clang/linker job
# peaks around 2 GB and the container has 24 GB.
set -euo pipefail

export JOBS="${JOBS:-12}"
export LC_ALL=C

cd /src/aosp

# shellcheck disable=SC1091
source build/envsetup.sh

lunch uwu_elden-user

echo "== building with -j$JOBS =="
m bacon -j"$JOBS" 2>&1 | tee "/src/build-$(date +%Y%m%d-%H%M%S).log"

echo "== artifacts =="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
