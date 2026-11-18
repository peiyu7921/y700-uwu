set -e
cd /root/aosp
BP=external/libjxl/Android.bp
python3 - "$BP" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
old = '    name: "libjxl",\n    host_supported: true,\n    vendor_available: true,\n'
new = '    name: "libjxl",\n    host_supported: true,\n    vendor_available: false,\n'
if old in s:
    s = s.replace(old, new, 1)
    open(p, 'w').write(s)
    print("patched: vendor_available -> false")
elif 'vendor_available: false' in s:
    print("already patched")
else:
    print("PATTERN NOT FOUND")
PY
sed -n '/name: "libjxl"/,+4p' "$BP"
