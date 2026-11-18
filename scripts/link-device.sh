#!/bin/bash
# Wire the already-cloned device/kernel/vendor repos into the synced AOSP tree.
#
#   docker run --rm -it -v /d/projects/y700-uwu:/src -w /src aosp-builder:17 \
#       bash scripts/link-device.sh
#
# Symlinks keep a single copy of each repo, so edits made here are picked up by
# the build immediately. Re-run after every `repo sync`.
set -euo pipefail

cd /src/aosp

mkdir -p device/lenovo
mkdir -p vendor/lenovo
mkdir -p kernel/platform/kernel-6.12/vendor/lenovo

# device tree (uwu-17.0)
ln -sfn /src/android_device_lenovo_elden device/lenovo/elden

# vendor blobs
ln -sfn /src/proprietary_vendor_lenovo_elden vendor/lenovo/elden

# vendor/uwu carries the WITH_GAPPS gate, so our fork must win over the synced one
ln -sfn /src/platform_vendor_uwu vendor/uwu

# kernel pieces
ln -sfn /src/android_kernel_lenovo_sm8750 \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750
ln -sfn /src/android_kernel_lenovo_sm8750-devicetrees \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-devicetrees
ln -sfn /src/android_kernel_lenovo_sm8750-modules \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules

echo "== linked =="
ls -l device/lenovo/elden vendor/lenovo/elden vendor/uwu \
      kernel/platform/kernel-6.12/vendor/lenovo/
