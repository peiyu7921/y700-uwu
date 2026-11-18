cd /root/aosp
source build/envsetup.sh >/dev/null 2>&1
echo "=== lunch --help ==="
lunch --help 2>&1 | head -20
echo "=== AndroidProducts.mk ==="
cat device/lenovo/elden/AndroidProducts.mk 2>&1 | head -10
echo "=== release config ==="
ls build/release/ 2>&1 | head -5
grep -rn "RELEASE_PLATFORM_VERSION\|PLATFORM_VERSION_CODENAME" build/make/core/version_defaults.mk 2>/dev/null | head -5
