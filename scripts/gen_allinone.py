import base64
import pathlib

dev = base64.b64encode(pathlib.Path('scripts/elden-device-fixes.patch').read_bytes()).decode()
uwu = base64.b64encode(pathlib.Path('scripts/uwu-gapps-gate.patch').read_bytes()).decode()

header = '''#!/bin/bash
# Self-contained build pipeline for the remote server (u-zpy).
# Patches are embedded, so this file alone is enough:
#   nohup bash server-allinone.sh > ~/pipeline.log 2>&1 &
set -euo pipefail

WORK="${WORK:-/home/zpy/y700-uwu}"
SRC="$WORK/aosp"

say() { echo "[$(date '+%H:%M:%S')] $*"; }

# This host's CPU lacks AVX, and libgnutls30 takes an AES-NI path that then raises
# SIGILL -- which is why `git-remote-https died of signal 4` while curl (OpenSSL, with
# runtime CPU detection) worked fine. Override gnutls' CPUID probe to use baseline code.
export GNUTLS_CPUID_OVERRIDE=0x1

say "=== [1/6] apt dependencies ==="
# Non-interactive SSH has no TTY, so sudo must read the password from stdin.
# 密码不硬编码：用环境变量提供，例如 SUDO_PASS=xxx bash server-allinone.sh
SUDO_PASS="${SUDO_PASS:-}"
[ -n "$SUDO_PASS" ] || { echo "错误：请先设置 SUDO_PASS 环境变量" >&2; exit 1; }
sudo_run() { echo "$SUDO_PASS" | sudo -S -p '' "$@"; }

if ! command -v repo >/dev/null 2>&1 || ! java -version >/dev/null 2>&1; then
    sudo_run apt-get update -qq
    sudo_run apt-get install -y --no-install-recommends \\
        bc bison build-essential ccache curl file flex g++-multilib gcc-multilib \\
        git git-lfs gnupg gperf imagemagick lib32readline-dev lib32z1-dev \\
        libelf-dev liblz4-tool libsdl1.2-dev libssl-dev libxml2 libxml2-utils \\
        lzop pngcrush python3 python-is-python3 repo rsync schedtool \\
        squashfs-tools unzip xsltproc zip zlib1g-dev openjdk-21-jdk-headless
fi
say "java: $(java -version 2>&1 | head -1)"

say "=== [2/6] git identity + mirrors ==="
git config --global user.name "elden builder"
git config --global user.email "builder@localhost"
git config --global http.postBuffer 524288000
# Go through the LAN proxy (a Clash instance on the LAN) instead of mirrors:
# measured 29 MB/s through the proxy versus 46 KB/s direct and 257 KB/s via gh-proxy, so
# 222 GB takes ~2 hours instead of ~10 days.
# 代理地址不写进仓库：用 PROXY_HOST 环境变量提供，未设置则直连。
if [ -n "${PROXY_HOST:-}" ]; then
    export http_proxy="http://${PROXY_HOST}:7897"
    export https_proxy="$http_proxy"
fi
export no_proxy=localhost,127.0.0.1,192.168.0.0/16
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"
say "proxy: $http_proxy"

say "=== [3/6] repo init ==="
mkdir -p "$SRC"
cd "$SRC"
# Prefer the repo we fetched via curl (2.71) over the distro launcher (2.17): the old
# launcher re-clones git-repo through git, which is unusably slow on this AVX-less CPU.
REPO_BIN="./.repo/repo/repo"
[ -x "$REPO_BIN" ] || REPO_BIN="repo"
say "using repo: $REPO_BIN"

# Check .repo/manifests, not .repo: a previous failed run leaves an empty .repo
# directory behind, which would make this skip init and then fail at repo sync.
if [ ! -d .repo/manifests ]; then
    # Ubuntu 22.04's repo package predates --git-lfs; AOSP proper does not need LFS.
    repo init -u https://github.com/uwuAOSP/platform_manifests -b uwu-17.0 --depth=1
fi

say "=== [4/6] repo sync (~222 GB, this is the long part) ==="
"$REPO_BIN" sync -c --no-tags --no-clone-bundle --force-sync -j8

say "=== [5/6] vendor repos + embedded patches ==="
mkdir -p device/lenovo vendor/lenovo kernel/platform/kernel-6.12/vendor/lenovo

clone_if_missing() {
    url="$1"; dest="$2"; branch="$3"
    if [ -d "$dest/.git" ]; then say "exists: $dest"; return; fi
    git clone --depth 1 -b "$branch" "$url" "$dest"
}

clone_if_missing https://github.com/lunatellus/android_device_lenovo_elden.git \\
    device/lenovo/elden uwu-17.0
clone_if_missing https://github.com/lunatellus/proprietary_vendor_lenovo_elden.git \\
    vendor/lenovo/elden lineage-24.0
clone_if_missing https://github.com/lunatellus/platform_vendor_uwu.git \\
    vendor/uwu uwu-17.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750.git \\
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750 lineage-24.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750-devicetrees.git \\
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-devicetrees lineage-24.0
clone_if_missing https://github.com/lunatellus/android_kernel_lenovo_sm8750-modules.git \\
    kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules lineage-24.0

mkdir -p "$WORK/patches"
echo 'PATCH_DEV_B64' | base64 -d > "$WORK/patches/elden-device-fixes.patch"
echo 'PATCH_UWU_B64' | base64 -d > "$WORK/patches/uwu-gapps-gate.patch"

apply_patch() {
    target="$1"; p="$2"
    say "patch $(basename "$p") -> $target"
    git -C "$target" am --3way "$p" 2>/dev/null || \\
    git -C "$target" apply --3way "$p" 2>/dev/null || \\
    say "WARN: patch failed: $(basename "$p")"
}
apply_patch device/lenovo/elden "$WORK/patches/elden-device-fixes.patch"
apply_patch vendor/uwu           "$WORK/patches/uwu-gapps-gate.patch"

say "=== [6/6] build ==="
source build/envsetup.sh
# uwuAOSP resolves this to lunch uwu_elden aosp_current <variant>
# (vendor/uwu/build/envsetup.sh). Using trunk_staging breaks vendor/prebuilt config.
lunch uwu_elden aosp_current user
m otapackage -j12 2>&1 | tee "$WORK/build-$(date +%Y%m%d-%H%M%S).log"

say "=== artifacts ==="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
say "=== PIPELINE DONE ==="
'''

out = header.replace('PATCH_DEV_B64', dev).replace('PATCH_UWU_B64', uwu)
# write_bytes: the target is Linux, and CRLF breaks the shebang and `set -o pipefail`.
pathlib.Path('scripts/server-allinone.sh').write_bytes(out.encode())
print('generated scripts/server-allinone.sh', len(out), 'bytes (LF)')
