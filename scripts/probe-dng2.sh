cd /root/aosp
echo "=== who depends on libdng_sdk ==="
grep -rn "libdng_sdk" --include=Android.bp --include=*.mk . 2>/dev/null | grep -v "external/dng_sdk" | head -10
echo "=== zuid_md5 def ==="
grep -rn "name: \"zuid_md5\"" --include=Android.bp . 2>/dev/null | head -2
