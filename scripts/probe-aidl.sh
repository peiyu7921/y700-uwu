cd /root/aosp
echo "=== system/hardware/interfaces 是否干净 ==="
git -C system/hardware/interfaces status --short 2>&1 | head -5
echo "=== 当前 revision ==="
git -C system/hardware/interfaces log --oneline -1 2>&1
echo "=== frozen 标记 ==="
grep -rn "frozen" system/hardware/interfaces/media/aidl/android/media/audio/eraser/types/Android.bp 2>/dev/null | head -3
echo "=== 冻结的 API 版本目录 ==="
ls system/hardware/interfaces/media/aidl/aidl_api/android.media.audio.eraser.types/ 2>/dev/null
