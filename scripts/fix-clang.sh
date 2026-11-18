set -e
cd /root/aosp/kernel/platform/kernel-6.12/prebuilts/clang/host

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

if [ -d linux-x86/.git ]; then
    echo "already a git repo: $(grep -m1 url linux-x86/.git/config 2>/dev/null)"
fi

if [ ! -e linux-x86.old ] && [ -d linux-x86 ]; then
    echo "== moving current linux-x86 aside =="
    mv linux-x86 linux-x86.old
fi

if [ ! -d linux-x86/.git ]; then
    echo "== cloning kernel-paired clang (main-kernel-2025) =="
    git clone --depth 1 -b main-kernel-2025 \
        https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86 \
        linux-x86 2>&1 | tail -3
fi

echo "=== clang versions now available ==="
ls -d linux-x86/clang-* 2>/dev/null | head -6
echo "=== r536225 present? ==="
ls -d linux-x86/clang-r536225 2>&1
