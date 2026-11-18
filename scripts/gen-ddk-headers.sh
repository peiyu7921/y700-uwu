#!/bin/bash
# Aggregate every Qualcomm DDK UAPI header into one directory named "kernel-headers".
#
# Why this exists: uwu_kernel runs Kbuild headers_install only on kernel_dir (the GKI common
# tree), so the vendor UAPI that the CAF audio/display/ipa/graphics userspace includes
# (linux/msm_audio.h, linux/qti-smmu-proxy.h, ...) is not exported. generated_kernel_includes
# is a uwu_kernel_headers module and also consumes DeviceKernelHeaderDirs(), i.e.
# TARGET_BOARD_KERNEL_HEADERS -- but build/make/core/config.mk requires every such entry to
# end in "kernel-headers", hence this aggregation step.
#
# The DDK UAPI dirs are discovered automatically: enumerating them by hand misses nested ones
# such as securemsm-kernel/smmu-proxy/include/uapi, and every miss costs a full rebuild.
#
# Usage: gen-ddk-headers.sh <aosp-root>
set -uo pipefail
AOSP="${1:?usage: $0 <aosp-root>}"
DEV="$AOSP/device/lenovo/elden"
K="$AOSP/kernel/platform/kernel-6.12/vendor/lenovo"
HH="$DEV/kernel-headers"

[ -d "$K" ] || { echo "MISSING vendor kernel tree $K" >&2; exit 1; }
[ -d "$DEV" ] || { echo "MISSING device dir $DEV" >&2; exit 1; }

rm -rf "$HH"
mkdir -p "$HH"

n=0
dup=0
roots=0
while IFS= read -r d; do
    roots=$((roots + 1))
    # Almost every DDK tree keeps the UAPI root at include/uapi itself, so what lies below it
    # is exactly what userspace #includes: display/drm/sde_drm.h, display/media/x.h,
    # camera/xxx.h and so on. Collapsing those levels breaks the include paths.
    # audio-kernel is the one exception: its headers sit under include/uapi/audio and are
    # included as <linux/msm_audio.h>, so that "audio" level is pure packaging.
    root="$d"
    [ -d "$d/audio/linux" ] && root="$d/audio"
    while IFS= read -r f; do
        rel="${f#"$root"/}"
        mkdir -p "$HH/$(dirname "$rel")"
        if [ -e "$HH/$rel" ]; then
            dup=$((dup + 1))
        else
            ln -sf "$f" "$HH/$rel"
            n=$((n + 1))
        fi
    done < <(find "$root" -type f -name '*.h' 2>/dev/null)
done < <(find "$K" -type d -path '*/include/uapi' 2>/dev/null)

echo "uapi roots: $roots"
echo "linked: $n  duplicate-skipped: $dup"
for probe in linux/msm_audio.h linux/qti-smmu-proxy.h display/media/mmm_color_fmt.h display/drm/sde_drm.h; do
    if [ -e "$HH/$probe" ]; then echo "$probe: OK"; else echo "$probe: MISSING"; fi
done
echo GEN_DDK_HEADERS_DONE
