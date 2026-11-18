cd /root/aosp
echo "=== eraser 相关路径 ==="
find system/hardware/interfaces -type d -name "*eraser*" 2>/dev/null | head -5
echo "=== Android.bp 位置 ==="
find system/hardware/interfaces -name "Android.bp" -path "*eraser*" 2>/dev/null | head -3
echo "=== frozen 标记 ==="
for f in $(find system/hardware/interfaces -name "Android.bp" -path "*eraser*" 2>/dev/null); do
  echo "--- $f"; grep -n "frozen\|versions_with_info" "$f" | head -4
done
