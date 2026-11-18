cd /root/aosp
echo "=== kernel/ top ==="
ls kernel/ 2>/dev/null
echo "=== kernel/platform/kernel-6.12 tree (depth 2) ==="
find kernel/platform/kernel-6.12 -maxdepth 2 -type d 2>/dev/null | head -15
echo "=== manifest refs to kernel ==="
grep -o 'path="kernel[^"]*"' .repo/manifests/default.xml 2>/dev/null | head -10
