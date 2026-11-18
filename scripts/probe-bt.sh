cd /root/aosp/kernel/platform/kernel-6.12
echo "=== build/kernel/build-tools ==="
ls -la build/kernel/build-tools 2>&1 | head -8
echo "=== is it a link? ==="
readlink -f build/kernel/build-tools 2>/dev/null
echo "=== does kernel/prebuilts/build-tools have sysroot? ==="
ls prebuilts/kernel-build-tools/ | head -10
echo "=== where is sysroot anywhere? ==="
find . -maxdepth 4 -name "sysroot" -type d 2>/dev/null | head -5
