set -e
cd /root/aosp
python3 - <<'PY'
import re

def patch(path, name, add_line='    vendor_available: true,\n'):
    try:
        s = open(path).read()
    except FileNotFoundError:
        print(f"MISSING {path}")
        return
    old = '    name: "%s",\n' % name
    if old not in s:
        print(f"NAME NOT FOUND: {name} in {path}")
        return
    idx = s.index(old)
    block = s[idx:idx+400]
    head = block.split('}')[0]
    if 'vendor_available' in head:
        if 'vendor_available: false' in head:
            s = s[:idx] + block.replace('vendor_available: false', 'vendor_available: true', 1) + s[idx+400:]
            open(path,'w').write(s)
            print(f"{name}: vendor_available false -> true")
        else:
            print(f"{name}: already vendor_available")
        return
    s = s.replace(old, old + add_line, 1)
    open(path,'w').write(s)
    print(f"{name}: added vendor_available")

patch('external/libjxl/Android.bp', 'libjxl')
patch('external/skia/Android.bp', 'libskia_skcms')
patch('external/XMP-Toolkit-SDK/Android.bp', 'xmp_toolkit_sdk')
PY
echo "=== verify ==="
grep -A3 'name: "libjxl"' external/libjxl/Android.bp | head -4
grep -A3 'name: "libskia_skcms"' external/skia/Android.bp | head -4
grep -A3 'name: "xmp_toolkit_sdk"' external/XMP-Toolkit-SDK/Android.bp | head -4
