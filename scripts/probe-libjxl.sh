cd /root/aosp
echo "=== libhwy module block ==="
sed -n '30,70p' external/google-highway/Android.bp
echo "=== who needs libjxl in vendor ==="
grep -rn "libjxl" --include=Android.bp --include=*.mk device/ vendor/ hardware/ 2>/dev/null | head -10
