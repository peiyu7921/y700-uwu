#!/bin/bash
# One-shot pipeline: bootstrap deps -> repo sync -> vendor repos -> patches -> build.
# Launched in a single SSH session with nohup so it survives disconnection.
#
#   nohup bash ~/pipeline.sh > ~/pipeline.log 2>&1 &
#
# Everything is self-pulled on the server (no upload of the 222 GB tree).
set -euo pipefail

WORK="${WORK:-/home/zpy/y700-uwu}"
SRC="$WORK/aosp"
LOG="$WORK/pipeline.log"

say() { echo "[$(date '+%H:%M:%S')] $*"; }

say "=== [1/6] apt dependencies ==="
if ! command -v repo >/dev/null 2>&1 || ! java -version >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends \
        bc bison build-essential ccache curl file flex g++-multilib gcc-multilib \
        git git-lfs gnupg gperf imagemagick lib32readline-dev lib32z1-dev \
        libelf-dev liblz4-tool libsdl1.2-dev libssl-dev libxml2 libxml2-utils \
        lzop pngcrush python3 python-is-python3 repo rsync schedtool \
        squashfs-tools unzip xsltproc zip zlib1g-dev openjdk-21-jdk-headless
fi
say "java: $(java -version 2>&1 | head -1)"

say "=== [2/6] git identity ==="
git config --global user.name "elden builder"
git config --global user.email "builder@localhost"
git config --global http.postBuffer 524288000

say "=== [3/6] repo init ==="
mkdir -p "$SRC"
cd "$SRC"
if [ ! -d .repo ]; then
    repo init -u https://github.com/uwuAOSP/platform_manifests -b uwu-17.0 --git-lfs --depth=1
fi

say "=== [4/6] repo sync (large, ~222 GB) ==="
repo sync -c --no-tags --no-clone-bundle --force-sync -j8

say "=== [5/6] vendor repos + patches ==="
mkdir -p device/lenovo vendor/lenovo kernel/platform/kernel-6.12/vendor/lenovo

clone_if_missing() {
    url="$1"; dest="$2"; branch="$3"
    if [ -d "$dest/.git" ]; then say "exists: $dest"; return; fi
    git clone --depth 1 -b "$branch" "$url" "$dest"
}

clone_if_missing https://github.com/lunatellus/android_device_lenovo_elden.git \
    device/lenovo/elden uwu-17.0
clone_if_missing https://github.com/lunatellus/proprietary_vendor_lenovo_elden.git \
    vendor/lenovo/elden lineage-24.0
clone_if_missing https://github.com/lunatellus/platform_vendor_uwu.git \
    vendor/uwu uwu-17.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750.git \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750 lineage-24.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750-devicetrees.git \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-devicetrees lineage-24.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750-modules.git \
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules lineage-24.0

# Patches are copied into $WORK/patches by the launching step.
if [ -d "$WORK/patches" ]; then
    for p in "$WORK"/patches/*.patch; do
        [ -e "$p" ] || continue
        target=""
        case "$(basename "$p")" in
            elden-device-fixes.patch) target="device/lenovo/elden" ;;
            uwu-gapps-gate.patch)    target="vendor/uwu" ;;
        esac
        [ -z "$target" ] && continue
        say "applying $(basename "$p") -> $target"
        git -C "$target" am --3way "$p" 2>/dev/null || \
        git -C "$target" apply --3way "$p" || say "WARN: patch failed: $p"
    done
fi

say "=== [6/6] build ==="
source build/envsetup.sh
# uwuAOSP resolves to lunch uwu_elden aosp_current <variant> (see vendor/uwu/build/envsetup.sh).
lunch uwu_elden aosp_current user
m otapackage -j12 2>&1 | tee "$WORK/build-$(date +%Y%m%d-%H%M%S).log"

say "=== artifacts ==="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
say "=== PIPELINE DONE ==="
