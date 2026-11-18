cd /root/aosp
echo "=== kernel.go 大小 ==="
wc -l vendor/uwu/build/soong/kernel/kernel.go 2>/dev/null
echo "=== 关键路径字符串 ==="
grep -oE '"[^"]*kernel[^"]*"' vendor/uwu/build/soong/kernel/kernel.go 2>/dev/null | sort -u | head -15
echo "=== breakfast 定义位置 ==="
grep -rn "breakfast" build/envsetup.sh vendor/uwu/build/envsetup.sh 2>/dev/null | head -5
