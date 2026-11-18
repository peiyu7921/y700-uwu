#!/bin/bash
# One-shot fix for the Qualcomm DDK UAPI headers under uwu_kernel:
#   1. point TARGET_BOARD_KERNEL_HEADERS at device/lenovo/elden/kernel-headers
#      (config.mk requires each entry to end in "kernel-headers")
#   2. regenerate that directory as symlinks into the vendor UAPI trees
# Usage: fix-ddk-headers.sh <aosp-root>
set -uo pipefail
AOSP="${1:?usage: $0 <aosp-root>}"
DEV="$AOSP/device/lenovo/elden"
BC="$DEV/BoardConfig.mk"
K="$AOSP/kernel/platform/kernel-6.12/vendor/lenovo"
UM="$K/sm8750-modules/qcom/opensource"

[ -f "$BC" ] || { echo "MISSING $BC" >&2; exit 1; }

python3 - "$BC" <<'PY'
import io
import sys

path = sys.argv[1]
text = io.open(path, encoding="utf-8").read()

anchor = "# Vendor kernel UAPI headers."
new_block = """# Vendor kernel UAPI headers.
#
# The CAF audio/display/ipa/graphics userspace includes Qualcomm DDK UAPI (linux/msm_audio.h
# etc). uwu_kernel only runs Kbuild headers_install on kernel_dir (the GKI common tree), so
# those headers have to be supplied through DeviceKernelHeaderDirs(). config.mk requires each
# entry to end in "kernel-headers", so scripts/gen-kernel-headers.sh aggregates the DDK UAPI
# into device/lenovo/elden/kernel-headers.
TARGET_BOARD_KERNEL_HEADERS := device/lenovo/elden/kernel-headers
"""

if anchor in text:
    io.open(path, "w", encoding="utf-8", newline="\n").write(text[:text.find(anchor)] + new_block)
    print("BoardConfig.mk: replaced")
elif "TARGET_BOARD_KERNEL_HEADERS := device/lenovo/elden/kernel-headers" in text:
    print("BoardConfig.mk: already aggregated")
else:
    io.open(path, "a", encoding="utf-8", newline="\n").write("\n" + new_block)
    print("BoardConfig.mk: appended")
PY

HH="$DEV/kernel-headers"
rm -rf "$HH"
mkdir -p "$HH"
n=0
dup=0
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
    [ -d "$d" ] || { echo "  skip(missing) ${d#$AOSP/}"; continue; }
    while IFS= read -r f; do
        rel="${f#$d/}"
        mkdir -p "$HH/$(dirname "$rel")"
        if [ -e "$HH/$rel" ]; then
            dup=$((dup + 1))
        else
            ln -sf "$f" "$HH/$rel"
            n=$((n + 1))
        fi
    done < <(find "$d" -type f \( -name '*.h' -o -name '*.hpp' \) 2>/dev/null)
done

echo "linked: $n  duplicate-skipped: $dup"
[ -e "$HH/linux/msm_audio.h" ] && echo "msm_audio.h: OK" || echo "msm_audio.h: MISSING"
echo FIX_DDK_HEADERS_DONE
