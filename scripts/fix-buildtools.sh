set -e
cd /root/aosp/kernel/platform/kernel-6.12

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

P=prebuilts/build-tools
if [ -L "$P" ]; then
    echo "removing symlink $P -> $(readlink "$P")"
    rm -f "$P"
fi
if [ -d "$P/.git" ]; then
    echo "already a real repo"
else
    rm -rf "$P" 2>/dev/null || true
    echo "== cloning $P (main-kernel-2025) =="
    git clone --depth 1 -b main-kernel-2025 \
        https://android.googlesource.com/platform/prebuilts/build-tools "$P" 2>&1 | tail -3
fi

echo "=== check the offending attribute source ==="
grep -n "supports_build_time_venv" "$P"/BUILD.bazel 2>/dev/null | head -3 || echo "(attribute gone)"
