#!/bin/bash
# Sync uwuAOSP 17 inside the WSL2 Ubuntu distro.
#
#   MSYS_NO_PATHCONV=1 wsl.exe -d Ubuntu-24.04 -u root bash /mnt/d/projects/y700-uwu/scripts/wsl-sync.sh
#
# The tree lives on the WSL2 ext4 disk (D:\wsl\Ubuntu-24.04\ext4.vhdx), NOT on /mnt/d:
# the Windows-side mounts turn git's objects/ hooks/ directories into plain files and
# break every repo. WSL mirrored networking makes the host proxy usable at 127.0.0.1.
set -euo pipefail

export http_proxy="${http_proxy:-http://127.0.0.1:7897}"
export https_proxy="${https_proxy:-$http_proxy}"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export JOBS="${JOBS:-8}"

SRC="${AOSP_DIR:-/root/aosp}"

echo "== proxy: $http_proxy =="
git config --global user.name "elden builder"
git config --global user.email "builder@localhost"
git config --global http.postBuffer 524288000
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

mkdir -p "$SRC"
cd "$SRC"

if [ ! -d .repo ]; then
    echo "== repo init =="
    repo init \
        -u https://github.com/uwuAOSP/platform_manifests \
        -b uwu-17.0 \
        --git-lfs \
        --depth=1
fi

echo "== repo sync (-j$JOBS) =="
repo sync -c --no-tags --no-clone-bundle --force-sync -j"$JOBS"

echo "== sync done =="
df -h "$SRC"
du -sh "$SRC"
