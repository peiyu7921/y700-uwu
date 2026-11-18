#!/bin/bash
# Aggregate the Qualcomm DDK UAPI headers into a single dir named "kernel-headers".
#
# build/make/core/config.mk validates that every TARGET_BOARD_KERNEL_HEADERS entry ends in
# "kernel-headers", so the raw include/uapi dirs cannot be listed directly. uwu_kernel's
# generated_kernel_includes is a uwu_kernel_headers module, which also consumes
# DeviceKernelHeaderDirs() -- this aggregated directory is what we point that at.
#
# Usage: gen-kernel-headers.sh <aosp-root> <device-dir>
set -uo pipefail
AOSP="${1:?usage: $0 <aosp-root> <device-dir>}"
DEV="${2:?usage: $0 <aosp-root> <device-dir>}"
HH="$DEV/kernel-headers"
K="$AOSP/kernel/platform/kernel-6.12/vendor/lenovo"
UM="$K/sm8750-modules/qcom/opensource"

[ -d "$AOSP/kernel/platform/kernel-6.12" ] || { echo "MISSING kernel tree under $AOSP" >&2; exit 1; }
[ -d "$DEV" ] || { echo "MISSING device dir $DEV" >&2; exit 1; }

rm -rf "$HH"
mkdir -p "$HH"

n=0
skip=0
for d in \
    "$K/sm8750/include/uapi" \
    "$UM/audio-kernel/include/uapi/audio" \
    "$UM/camera-kernel/include/uapi" \
    "$UM/display-drivers/include/uapi" \
    "$UM/dsp-kernel/include/uapi" \
    "$UM/eva-kernel/include/uapi" \
    "$UM/graphics-kernel/include/uapi" \
    "$UM/securemsm-kernel/include/uapi" \
    "$UM/spu-kernel/include/uapi" \
    "$UM/synx-kernel/include/uapi" \
    "$UM/touch-drivers/include/uapi" \
    "$UM/video-driver/include/uapi"
do
    [ -d "$d" ] || { echo "  skip (missing) ${d#$AOSP/}"; continue; }
    while IFS= read -r f; do
        rel="${f#$d/}"
        mkdir -p "$HH/$(dirname "$rel")"
        if [ -e "$HH/$rel" ]; then
            skip=$((skip + 1))
        else
            ln -sf "$f" "$HH/$rel"
            n=$((n + 1))
        fi
    done < <(find "$d" -type f \( -name '*.h' -o -name '*.hpp' \) 2>/dev/null)
done

echo "linked: $n"
echo "duplicate-skipped: $skip"
ls "$HH/linux/msm_audio.h" >/dev/null 2>&1 && echo "msm_audio.h: OK" || echo "msm_audio.h: MISSING"
echo GEN_HEADERS_DONE
