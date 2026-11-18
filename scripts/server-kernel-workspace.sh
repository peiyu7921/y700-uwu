#!/bin/bash
# Backfill the Kleaf kernel workspace on the remote server.
#
# The device tree builds the kernel from source via the legacy tasks/kernel.mk, which
# expects a full Kleaf workspace at kernel/platform/kernel-6.12/. `repo sync` only
# populates vendor/, so common/, build/, prebuilts/ and tools/ must be fetched separately.
#
# Revision notes (from kernel/manifest default.xml on common-android16-6.12):
#   build/kernel, kernel/prebuilts/build-tools  -> inherit <default revision="main-kernel-2025">
#   kernel/common                               -> revision="android16-6.12"
#   other platform/prebuilts/*                  -> follow the kernel line as well
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
KW="$AOSP/kernel/platform/kernel-6.12"

# 代理地址不写进仓库：用 PROXY_HOST 环境变量提供，未设置则直连。
if [ -n "${PROXY_HOST:-}" ]; then
    export http_proxy="http://${PROXY_HOST}:7897"
    export https_proxy=$http_proxy
fi
export no_proxy=localhost,127.0.0.1,192.168.0.0/16
export GNUTLS_CPUID_OVERRIDE=0x1

say() { echo "[$(date '+%H:%M:%S')] $*"; }

fetch() {
    name="$1"; dest="$2"; rev="$3"
    if [ -d "$KW/$dest/.git" ]; then
        say "ok      $dest"
        return 0
    fi
    say "fetch   $dest ($rev)"
    rm -rf "$KW/$dest"
    mkdir -p "$(dirname "$KW/$dest")"
    if git clone --depth 1 -b "$rev" "https://android.googlesource.com/$name" "$KW/$dest" 2>/dev/null; then
        return 0
    fi
    say "retry   $dest (default branch)"
    git clone --depth 1 "https://android.googlesource.com/$name" "$KW/$dest" || say "WARN: $dest failed"
}

say "=== kernel core ==="
fetch kernel/build                                  build/kernel                    main-kernel-2025
fetch kernel/common                                 common                          android16-6.12
fetch kernel/prebuilts/build-tools                  prebuilts/kernel-build-tools    main-kernel-2025

say "=== prebuilts ==="
fetch platform/prebuilts/build-tools                prebuilts/build-tools           main-kernel-2025
fetch platform/prebuilts/rust                       prebuilts/rust                  main-kernel-2025
fetch platform/prebuilts/clang/host/linux-x86       prebuilts/clang/host/linux-x86  main-kernel-2025
fetch platform/prebuilts/clang-tools                prebuilts/clang-tools           main-kernel-2025
fetch platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8 \
      prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8                     main-kernel-2025
fetch platform/system/tools/mkbootimg               tools/mkbootimg                 main-kernel-2025

say "=== bzlmod registry + rules ==="
for p in \
    bazelbuild-bazel-central-registry \
    bazel-skylib \
    bazel-contrib-bazel_features \
    bazelbuild-platforms \
    bazelbuild-rules_cc \
    bazelbuild-rules_license \
    bazelbuild-rules_pkg \
    bazelbuild-rules_python \
    bazelbuild-rules_rust \
    bazelbuild-rules_shell \
    libcap \
    libcap-ng \
    lz4 \
    pigz \
    toybox
do
    fetch "platform/external/$p" "external/$p" main-kernel-2025
done
fetch platform/external/python/absl-py external/python/absl-py main-kernel-2025

say "=== workspace linkfiles ==="
cd "$KW" || exit 1
[ -e MODULE.bazel ]     || ln -sfn build/kernel/kleaf/bzlmod/bazel.MODULE.bazel MODULE.bazel
[ -e WORKSPACE.bzlmod ] || ln -sfn build/kernel/kleaf/bzlmod/bazel.WORKSPACE.bzlmod WORKSPACE.bzlmod
mkdir -p tools
[ -e tools/bazel ]      || ln -sfn ../build/kernel/kleaf/bazel.sh tools/bazel

say "=== verification ==="
for f in MODULE.bazel WORKSPACE.bzlmod tools/bazel build/kernel common \
         prebuilts/rust/linux-x86/1.82.0.p2 \
         prebuilts/clang/host/linux-x86/clang-r536225; do
    if [ -e "$KW/$f" ]; then say "  OK   $f"; else say "  MISS $f"; fi
done

say "=== BACKFILL DONE ==="
