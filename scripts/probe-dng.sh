cd /root/aosp
echo "=== libdng_sdk block ==="
sed -n '175,215p' external/dng_sdk/Android.bp
echo "=== xmp_toolkit_sdk def ==="
grep -rn "name: \"xmp_toolkit_sdk\"" --include=Android.bp . 2>/dev/null | head -2
