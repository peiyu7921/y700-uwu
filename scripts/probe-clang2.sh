cd /root/aosp/kernel/platform/kernel-6.12
echo "=== where r536225 comes from ==="
grep -rn "r536225" build/kernel/ 2>/dev/null | head -5
echo "=== kleaf clang version var ==="
grep -rn "CLANG_VERSION\|clang_version" build/kernel/kleaf/impl/*.bzl 2>/dev/null | head -5
