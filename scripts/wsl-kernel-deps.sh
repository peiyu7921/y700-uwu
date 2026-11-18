set -e
cd /root/aosp/kernel/platform/kernel-6.12

ROOT=/root/aosp
export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

REV_DEFAULT=main-kernel-2025

# path -> project name (from kernel/manifest default.xml)
provide() {
    dest="$1"; name="$2"; rev="${3:-$REV_DEFAULT}"
    mkdir -p "$(dirname "$dest")"
    if [ -e "$dest" ]; then
        echo "exists: $dest"
        return
    fi
    # Prefer an existing copy at the AOSP tree root (cheap, no download).
    if [ -e "$ROOT/$dest" ]; then
        ln -sfn "$ROOT/$dest" "$dest"
        echo "linked: $dest -> $ROOT/$dest"
        return
    fi
    echo "cloning: $dest ($name @ $rev)"
    rm -rf "$dest" 2>/dev/null || true
    git clone --depth 1 -b "$rev" "https://android.googlesource.com/$name" "$dest" \
        || git clone --depth 1 "https://android.googlesource.com/$name" "$dest"
}

# bzlmod registry + rules that Kleaf's MODULE.bazel resolves against.
provide external/bazelbuild-bazel-central-registry platform/external/bazelbuild-bazel-central-registry
provide external/bazel-skylib                   platform/external/bazel-skylib
provide external/bazel-contrib-bazel_features   platform/external/bazel-contrib-bazel_features
provide external/bazelbuild-platforms           platform/external/bazelbuild-platforms
provide external/bazelbuild-rules_cc            platform/external/bazelbuild-rules_cc
provide external/bazelbuild-rules_license       platform/external/bazelbuild-rules_license
provide external/bazelbuild-rules_pkg           platform/external/bazelbuild-rules_pkg
provide external/bazelbuild-rules_python        platform/external/bazelbuild-rules_python
provide external/bazelbuild-rules_rust          platform/external/bazelbuild-rules_rust
provide external/bazelbuild-rules_shell         platform/external/bazelbuild-rules_shell

# Build-time helpers referenced by Kleaf.
provide external/libcap        platform/external/libcap
provide external/libcap-ng     platform/external/libcap-ng
provide external/lz4           platform/external/lz4
provide external/pigz          platform/external/pigz
provide external/toybox        platform/external/toybox
provide external/python/absl-py platform/external/python/absl-py
provide prebuilts/clang-tools  platform/prebuilts/clang-tools

echo "== external =="
ls external/ 2>/dev/null
