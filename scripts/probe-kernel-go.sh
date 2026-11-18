cd /root/aosp
echo "=== kernel.go 关键逻辑（路径期望） ==="
grep -nE "kernel/platform|kernel-6\.12|TARGET_KERNEL_SOURCE|KLEAF|bazel" vendor/uwu/build/soong/kernel/kernel.go 2>/dev/null | head -12
echo
echo "=== breakfast 函数定义 ==="
grep -A12 "^function breakfast" build/envsetup.sh 2>/dev/null | head -18
