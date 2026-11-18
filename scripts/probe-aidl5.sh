cd /root/aosp
BP=system/hardware/interfaces/media/Android.bp
for L in 159 300 408; do
  echo "=== line $L 所属模块 ==="
  sed -n "1,${L}p" "$BP" | grep -n "name: \"" | tail -1
done
echo "=== eraser.types 模块名所在行 ==="
grep -n 'name: "android.media.audio.eraser.types"' "$BP"
