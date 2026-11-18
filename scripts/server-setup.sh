#!/bin/bash
# One-shot build environment setup for the remote server (u-zpy, /home/zpy/y700-uwu).
#
# Runs entirely on the server: it pulls sources itself instead of receiving an upload.
#   bash server-setup.sh            # deps + repo sync + vendor repos
#   bash server-build.sh            # compile
set -euo pipefail

WORK="${WORK:-/home/zpy/y700-uwu}"
SRC="$WORK/aosp"

export DEBIAN_FRONTEND=noninteractive

echo "== [1/5] apt dependencies =="
if ! command -v repo >/dev/null 2>&1 || ! command -v java >/dev/null 2>&1; then
    sudo apt-get update
    sudo apt-get install -y --no-install-recommends \
        bc bison build-essential ccache curl file flex g++-multilib gcc-multilib \
        git git-lfs gnupg gperf imagemagick lib32readline-dev lib32z1-dev \
        libelf-dev liblz4-tool libsdl1.2-dev libssl-dev libxml2 libxml2-utils \
        lzop pngcrush python3 python-is-python3 repo rsync schedtool \
        squashfs-tools unzip xsltplus zip zlib1g-dev openjdk-21-jdk-headless 2>/dev/null || \
    sudo apt-get install -y --no-install-recommends \
        bc bison build-essential ccache curl file flex g++-multilib gcc-multilib \
        git git-lfs gnupg gperf imagemagick lib32readline-dev lib32z1-dev \
        libelf-dev liblz4-tool libsdl1.2-dev libssl-dev libxml2 libxml2-utils \
        lzop pngcrush python3 python-is-python3 repo rsync schedtool \
        squashfs-tools unzip xsltproc zip zlib1g-dev openjdk-21-jdk-headless
fi

echo "== [2/5] git identity =="
git config --global user.name "elden builder"
git config --global user.email "builder@localhost"
git config --global http.postBuffer 524288000
# Uncomment if this server needs the host proxy to reach GitHub/googlesource:
# git config --global http.proxy http://<proxy-host>:7897

echo "== [3/5] repo init =="
mkdir -p "$WORK"
cd "$WORK"
if [ ! -d "$SRC/.repo" ]; then
    mkdir -p "$SRC"
    cd "$SRC"
    repo init -u https://github.com/uwuAOSP/platform_manifests -b uwu-17.0 --git-lfs --depth=1
else
    cd "$SRC"
fi

echo "== [4/5] repo sync (~222 GB) =="
repo sync -c --no-tags --no-clone-bundle --force-sync -j8

echo "== [5/5] vendor repos the device tree needs =="
cd "$SRC"
mkdir -p device/lenovo vendor/lenovo kernel/platform/kernel-6.12/vendor/lenovo

clone_if_missing() {
    url="$1"; dest="$2"; branch="$3"
    if [ -d "$dest/.git" ]; then
        echo "exists: $dest"
    else
        git clone --depth 1 -b "$branch" "$url" "$dest"
    fi
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

echo "== setup done; tree at $SRC =="
df -h "$SRC" | tail -1
