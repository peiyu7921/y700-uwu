cd /root/aosp
source build/envsetup.sh >/dev/null 2>&1
echo "=== 可用 release ==="
grep -rh "aosp_current" build/release/*.mk build/release/**/*.mk 2>/dev/null | head -3
ls build/release/ 2>/dev/null | head -10
echo
echo "=== 尝试正确组合：uwu_elden aosp_current user ==="
lunch uwu_elden aosp_current user 2>&1 | tail -12
