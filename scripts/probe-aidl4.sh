cd /root/aosp
echo "=== 模块定义位置 ==="
grep -rln "android.media.audio.eraser.types" system/hardware/interfaces --include=Android.bp 2>/dev/null | head -5
echo "=== frozen 出现的所有 bp ==="
grep -rn "frozen: true" system/hardware/interfaces/media/ --include=Android.bp 2>/dev/null | head -8
