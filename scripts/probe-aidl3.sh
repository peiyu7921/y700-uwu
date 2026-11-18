cd /root/aosp
BP=system/hardware/interfaces/media/aidl/Android.bp
echo "=== eraser.types 模块块 ==="
awk '/name: "android.media.audio.eraser.types"/,/^}/' "$BP" 2>/dev/null | head -25
echo "=== frozen 出现位置 ==="
grep -n "frozen" "$BP" 2>/dev/null | head -10
