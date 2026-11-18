#!/bin/bash
# Server-side: fetch only rust/linux-x86/1.82.0.p2 (the full prebuilts/rust repo is 2 GB
# and keeps dying with "GnuTLS recv error / early EOF" over this link), then resume build.
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
KW="$AOSP/kernel/platform/kernel-6.12"
P="$KW/prebuilts/rust"

# 代理地址不写进仓库：用 PROXY_HOST 环境变量提供，未设置则直连。
if [ -n "${PROXY_HOST:-}" ]; then
    export http_proxy="http://${PROXY_HOST}:7897"
    export https_proxy=$http_proxy
fi
export no_proxy=localhost,127.0.0.1,192.168.0.0/16
export GNUTLS_CPUID_OVERRIDE=0x1

say() { echo "[$(date '+%H:%M:%S')] $*"; }

say "=== [1/3] rust 1.82.0.p2 (sparse) ==="
if [ -d "$P/linux-x86/1.82.0.p2" ]; then
    say "already present"
else
    rm -rf "$P"
    mkdir -p "$KW/prebuilts"
    for attempt in 1 2 3; do
        say "attempt $attempt"
        rm -rf "$P"
        if git clone --filter=blob:none --sparse --depth 1 -b main-kernel-2025 \
                https://android.googlesource.com/platform/prebuilts/rust "$P"; then
            ( cd "$P" && git sparse-checkout set linux-x86/1.82.0.p2 ) && break
        fi
        sleep 10
    done
fi

if [ -d "$P/linux-x86/1.82.0.p2" ]; then
    say "  OK   rust/linux-x86/1.82.0.p2"
else
    say "  MISS rust/linux-x86/1.82.0.p2 -- giving up on this step"
fi

say "=== [2/3] kernel workspace sanity ==="
for f in MODULE.bazel WORKSPACE.bzlmod tools/bazel build/kernel common \
         prebuilts/clang/host/linux-x86/clang-r563880c; do
    [ -e "$KW/$f" ] && say "  OK   $f" || say "  MISS $f"
done

say "=== [3/3] resume build ==="
cd "$AOSP" || exit 1
source build/envsetup.sh
lunch uwu_elden aosp_current user
LOG="$WORK/build-$(date +%Y%m%d-%H%M%S).log"
m otapackage -j12 2>&1 | tee "$LOG"

say "=== artifacts ==="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || true
say "=== DONE ==="
