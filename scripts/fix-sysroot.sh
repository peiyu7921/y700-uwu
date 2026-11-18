set -e
cd /root/aosp/kernel/platform/kernel-6.12

export http_proxy=http://127.0.0.1:7897
export https_proxy=$http_proxy
git config --global http.proxy "$http_proxy"
git config --global https.proxy "$https_proxy"

P=prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8
if [ -d "$P/.git" ] || [ -d "$P/sysroot" ]; then
    echo "already present"
else
    mkdir -p "$(dirname "$P")"
    echo "== cloning $P =="
    git clone --depth 1 \
        https://android.googlesource.com/platform/prebuilts/gcc/linux-x86/host/x86_64-linux-glibc2.17-4.8 \
        "$P" 2>&1 | tail -3
fi

echo "=== verify sysroot link ==="
ls -l build/kernel/build-tools/sysroot
echo "=== target exists? ==="
ls "$P/sysroot" 2>&1 | head -5
