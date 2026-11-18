cd /root/aosp/kernel/platform/kernel-6.12
echo "=== current clang dirs (via symlink to main tree) ==="
ls -d prebuilts/clang/host/linux-x86/clang-* 2>/dev/null | head -5
echo "=== is it a symlink? ==="
readlink -f prebuilts/clang/host/linux-x86
echo "=== what Kleaf expects ==="
grep -rn "clang-r536225" build/kernel/kleaf/*.bzl build/kernel/kleaf/**/*.bzl 2>/dev/null | head -3
