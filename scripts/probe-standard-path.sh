cd /root/aosp
echo "=== breakfast 命令存在吗 ==="
source build/envsetup.sh >/dev/null 2>&1
type breakfast 2>&1 | head -3
echo "=== roomservice / 内核处理逻辑 ==="
find vendor/uwu vendor/lineage -name "roomservice*.py" -o -name "*kernel*.sh" 2>/dev/null | head -5
echo "=== 谁处理 lineage.dependencies 的 kernel 类型 ==="
grep -rln '"type": "kernel"\|type.*kernel' vendor/uwu/build/ 2>/dev/null | head -3
echo "=== prebuilt kernel 存在吗 ==="
ls -d kernel/prebuilts/6.12/arm64 2>&1 | head -2
ls kernel/prebuilts/6.12/arm64/ 2>/dev/null | head -5
