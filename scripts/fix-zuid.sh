set -e
cd /root/aosp
python3 - <<'PY'
def patch(path, name):
    s = open(path).read()
    old = '    name: "%s",\n' % name
    if old not in s:
        print(f"NOT FOUND: {name}"); return
    idx = s.index(old); block = s[idx:idx+300]; head = block.split('}')[0]
    if 'vendor_available' in head:
        print(f"{name}: already has vendor_available"); return
    s = s.replace(old, old + '    vendor_available: true,\n', 1)
    open(path,'w').write(s)
    print(f"{name}: added vendor_available")
patch('external/XMP-Toolkit-SDK/Android.bp', 'zuid_md5')
PY
sed -n '/name: "zuid_md5"/,+4p' external/XMP-Toolkit-SDK/Android.bp
