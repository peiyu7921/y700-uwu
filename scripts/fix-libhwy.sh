set -e
cd /root/aosp
BP=external/google-highway/Android.bp
if grep -q "vendor_available" "$BP"; then
    echo "already patched"
else
    python3 - "$BP" <<'PY'
import sys, re
p = sys.argv[1]
s = open(p).read()
# add vendor_available: true right after the libhwy module's name line
s = s.replace('    name: "libhwy",\n', '    name: "libhwy",\n    vendor_available: true,\n', 1)
open(p, 'w').write(s)
PY
    echo "patched"
fi
sed -n '/name: "libhwy"/,+6p' "$BP"
