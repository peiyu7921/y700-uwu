set -e
cd /root/aosp/kernel/platform/kernel-6.12

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

REV=main-kernel-2025

fetch_prebuilt() {
    dest="$1"; name="$2"
    if [ -d "$dest/.git" ]; then
        echo "repo ok: $dest"
        return
    fi
    if [ -L "$dest" ]; then
        echo "removing symlink: $dest -> $(readlink "$dest")"
        rm -f "$dest"
    elif [ -d "$dest" ]; then
        echo "moving aside: $dest -> $dest.aosp17"
        rm -rf "$dest.aosp17" 2>/dev/null || true
        mv "$dest" "$dest.aosp17"
    fi
    mkdir -p "$(dirname "$dest")"
    echo "== cloning $dest ($name @ $REV) =="
    git clone --depth 1 -b "$REV" "https://android.googlesource.com/$name" "$dest" 2>&1 | tail -2
}

# Same version-line mismatch as clang/build-tools: Kleaf pins exact toolchain paths.
fetch_prebuilt prebuilts/rust               platform/prebuilts/rust
fetch_prebuilt prebuilts/jdk/jdk11          platform/prebuilts/jdk/jdk11
fetch_prebuilt prebuilts/ndk-r26            toolchain/prebuilts/ndk/r26
fetch_prebuilt prebuilts/clang-tools        platform/prebuilts/clang-tools

echo "=== verify pinned paths ==="
ls -d prebuilts/rust/linux-x86/1.82.0.p2 2>&1 | head -2
ls -d prebuilts/jdk/jdk11 2>&1 | head -2
