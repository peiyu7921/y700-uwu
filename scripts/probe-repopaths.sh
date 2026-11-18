F=/root/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules/nxp/opensource/driver/repo_paths.bzl
echo "=== first 5 lines (with CR markers) ==="
head -5 "$F" | cat -A | head -8
echo "=== CR count ==="
grep -c $'\r' "$F" 2>/dev/null || echo 0
