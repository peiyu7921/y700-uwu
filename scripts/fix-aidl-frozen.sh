set -e
cd /root/aosp
BP=system/hardware/interfaces/media/Android.bp

python3 - "$BP" <<'PY'
import sys
p = sys.argv[1]
lines = open(p).read().split('\n')
# module android.media.audio.eraser.types starts at line 374 (1-based); its frozen:true is at 408
target_name_line = 374 - 1
target_frozen_line = 408 - 1
assert 'android.media.audio.eraser.types' in lines[target_name_line], lines[target_name_line]
assert 'frozen: true' in lines[target_frozen_line], lines[target_frozen_line]
lines[target_frozen_line] = lines[target_frozen_line].replace('frozen: true', 'frozen: false')
open(p, 'w').write('\n'.join(lines))
print("patched eraser.types frozen -> false")
PY

echo "=== verify ==="
sed -n '374p;408p' "$BP"
