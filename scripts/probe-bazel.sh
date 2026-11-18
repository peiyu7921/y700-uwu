cd /root/aosp
echo "=== kernel/platform ==="
ls kernel/platform/ 2>/dev/null
echo "=== kernel-6.12 top ==="
ls kernel/platform/kernel-6.12/ 2>/dev/null | head -10
echo "=== tools ==="
ls kernel/platform/kernel-6.12/tools/ 2>/dev/null | head -5
echo "=== search bazel wrapper ==="
find kernel/platform/kernel-6.12 -maxdepth 2 -name "bazel*" 2>/dev/null | head -5
