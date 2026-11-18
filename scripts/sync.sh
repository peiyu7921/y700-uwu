#!/bin/bash
# Sync the uwuAOSP 17 tree inside the build container.
#
# The tree lives in an ext4 image (aosp.img) loop-mounted at /mnt/aosp rather than
# directly on the Windows bind mount. Reason: through this Hyper-V container's bind
# mount, git's `objects` and `hooks` directories were created as ordinary 1067-byte
# files, so every repo was an empty shell and sync failed with
# "Cannot initialize work tree".
#
# Requires --privileged for the loop mount:
#   MSYS_NO_PATHCONV=1 docker run --rm --privileged \
#       -v "D:/projects/y700-uwu:/src" -w /src aosp-builder:17 bash scripts/sync.sh
#
# The image is a real 300G file (NTFS does not keep it sparse).
set -euo pipefail

export http_proxy="${http_proxy:-http://host.docker.internal:7897}"
export https_proxy="${https_proxy:-$http_proxy}"
export HTTP_PROXY="$http_proxy"
export HTTPS_PROXY="$https_proxy"
export JOBS="${JOBS:-8}"

IMG="${AOSP_IMG:-/src/aosp.img}"
MNT="${AOSP_MNT:-/mnt/aosp}"
IMG_SIZE="${AOSP_IMG_SIZE:-300G}"

echo "== proxy: $http_proxy =="
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

if [ ! -f "$IMG" ]; then
    echo "== creating $IMG ($IMG_SIZE) =="
    truncate -s "$IMG_SIZE" "$IMG"
    mkfs.ext4 -q -m 0 "$IMG"
fi

mkdir -p "$MNT"
if ! mountpoint -q "$MNT"; then
    echo "== loop mounting $IMG at $MNT =="
    mount -o loop "$IMG" "$MNT"
fi

cd "$MNT"

if [ ! -d .repo ]; then
    echo "== repo init =="
    repo init \
        -u https://github.com/uwuAOSP/platform_manifests \
        -b uwu-17.0 \
        --git-lfs \
        --depth=1
fi

echo "== repo sync (-j$JOBS) =="
# -c        current branch only
# --no-tags skip tags (big win on a shallow tree)
# --no-clone-bundle avoids bundle fetches that break behind proxies
repo sync -c --no-tags --no-clone-bundle --force-sync -j"$JOBS"

echo "== sync done =="
df -h "$MNT"
du -sh "$MNT"
