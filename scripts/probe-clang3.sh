cd /root/aosp/kernel/platform/kernel-6.12
echo "=== CLANG_VERSION definitions ==="
grep -rn "CLANG_VERSION" build/kernel/ 2>/dev/null | grep -v "\.bzl:.*#" | head -10
echo "=== VARS / config default ==="
grep -rn "r536225\|536225" build/kernel/ prebuilts/kernel-build-tools/ 2>/dev/null | head -5
