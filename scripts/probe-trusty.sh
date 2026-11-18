cd /root/aosp
echo "=== trusty_cli bp ==="
sed -n '1,25p' system/core/trusty/trusty_cli/Android.bp
echo "=== who includes trusty ==="
grep -rn "trusty_cli\|libtrustystorage" --include=*.mk build/make/target/product/ device/ vendor/uwu/ 2>/dev/null | head -8
