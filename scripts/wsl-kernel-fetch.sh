set -e
cd /root/aosp/kernel/platform/kernel-6.12

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

ROOT=/root/aosp

clone() {
    url="$1"; dest="$2"; rev="$3"
    if [ -d "$dest/.git" ]; then
        echo "exists: $dest"
        return
    fi
    echo "== cloning $dest ($rev) =="
    rm -rf "$dest" 2>/dev/null || true
    git clone --depth 1 -b "$rev" "$url" "$dest"
}

# Branch names per kernel/manifest's default.xml on common-android16-6.12:
#   kernel/build  -> inherits <default revision="main-kernel-2025">
#   kernel/common -> revision="android16-6.12"
#   kernel/prebuilts/build-tools -> also inherits the default
clone https://android.googlesource.com/kernel/build               build/kernel                  main-kernel-2025
clone https://android.googlesource.com/kernel/common              common                        android16-6.12
clone https://android.googlesource.com/kernel/prebuilts/build-tools prebuilts/kernel-build-tools main-kernel-2025

link() {
    src="$1"; dest="$2"
    mkdir -p "$(dirname "$dest")"
    [ -e "$dest" ] && { echo "exists: $dest"; return; }
    ln -sfn "$src" "$dest"
    echo "linked $dest -> $src"
}

# Multi-GB toolchains already exist at the AOSP tree root; link instead of re-downloading.
link "$ROOT/prebuilts/clang/host/linux-x86" prebuilts/clang/host/linux-x86
link "$ROOT/prebuilts/build-tools"          prebuilts/build-tools
link "$ROOT/prebuilts/rust"                 prebuilts/rust
link "$ROOT/system/tools/mkbootimg"         tools/mkbootimg

# Kleaf expects the bazel wrapper at <workspace>/tools/bazel.
mkdir -p tools
if [ ! -e tools/bazel ]; then
    ln -sfn ../build/kernel/kleaf/bazel.sh tools/bazel
    echo "linked tools/bazel"
fi

echo "== workspace =="
ls
echo "== tools =="
ls -l tools/ 2>/dev/null
