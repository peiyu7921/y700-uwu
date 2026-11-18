#!/bin/bash
# uwu_kernel runs Kbuild headers_install only on kernel_dir (the GKI common tree), so the
# Qualcomm DDK UAPI headers that the CAF audio/display/ipa/graphics HALs include
# (linux/msm_audio.h etc.) are not exported. generated_kernel_includes is a
# uwu_kernel_headers module, and that type also honours DeviceKernelHeaderDirs(), which comes
# from TARGET_BOARD_KERNEL_HEADERS -- so the vendor UAPI dirs are declared there.
# Usage: add-kernel-headers.sh <BoardConfig.mk>
set -uo pipefail
p="${1:?usage: $0 <BoardConfig.mk>}"
[ -f "$p" ] || { echo "MISSING $p" >&2; exit 1; }
if grep -q 'TARGET_BOARD_KERNEL_HEADERS' "$p"; then
    echo "ALREADY_SET"
    exit 0
fi

VB=kernel/platform/kernel-6.12/vendor/lenovo
UM=$VB/sm8750-modules/qcom/opensource
cat >> "$p" <<EOF

# Vendor kernel UAPI headers.
#
# uwu_kernel only runs Kbuild headers_install on kernel_dir (the GKI common tree), so the
# Qualcomm DDK UAPI that the CAF audio/display/ipa/graphics userspace includes is not
# exported. generated_kernel_includes is a uwu_kernel_headers module and also picks up
# DeviceKernelHeaderDirs(), i.e. this variable.
TARGET_BOARD_KERNEL_HEADERS := \
    $VB/sm8750/include/uapi \
    $UM/audio-kernel/include/uapi/audio \
    $UM/camera-kernel/include/uapi \
    $UM/display-drivers/include/uapi \
    $UM/dsp-kernel/include/uapi \
    $UM/eva-kernel/include/uapi \
    $UM/graphics-kernel/include/uapi \
    $UM/securemsm-kernel/include/uapi \
    $UM/spu-kernel/include/uapi \
    $UM/synx-kernel/include/uapi \
    $UM/touch-drivers/include/uapi \
    $UM/video-driver/include/uapi
EOF
grep -q 'TARGET_BOARD_KERNEL_HEADERS' "$p" && echo "HEADERS_ADDED" || { echo "WARN failed" >&2; exit 1; }
