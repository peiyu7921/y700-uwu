set -e
D=/root/aosp/kernel/platform/kernel-6.12/prebuilts/clang/host
if [ -d "$D/linux-x86.old" ]; then
    echo "removing $D/linux-x86.old (19G)"
    rm -rf "$D/linux-x86.old"
fi
echo "=== remaining ==="
ls -d "$D"/linux-x86* 2>/dev/null
echo "=== clang r536225 ok? ==="
ls -d "$D/linux-x86/clang-r536225" 2>&1
