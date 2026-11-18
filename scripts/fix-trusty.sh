set -e
cd /root/aosp
BP=vendor/uwu-stub/Android.bp
python3 - "$BP" <<'PY'
import sys
p = sys.argv[1]
s = open(p).read()
changed = False
for name in ("libtrustystorageinterface", "libtrustycliinterface"):
    old = '    name: "%s",\n' % name
    if old in s:
        # only add if not already vendor_available in that block
        idx = s.index(old)
        block = s[idx:idx+300]
        if "vendor_available" not in block.split("}")[0]:
            s = s.replace(old, old + '    vendor_available: true,\n', 1)
            changed = True
open(p, 'w').write(s)
print("patched" if changed else "already patched")
PY
sed -n '/name: "libtrustystorageinterface"/,+5p' "$BP"
sed -n '/name: "libtrustycliinterface"/,+4p' "$BP"
