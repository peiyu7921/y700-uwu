#!/bin/bash
# 清空 out/ 后从零全量构建，产出 OTA。
#
# 与 server-ota-skipabi.sh 的区别：
#   - 那个是「增量」：只重跑 --soong-only 再 siso ninja otapackage，
#     前提是 out/ 里已有 bootstrap、kati 产物（build-*.ninja）和图。
#   - 本脚本是「全量」：out/ 被清空后，kati/soong bootstrap 也必须重做，
#     因此必须用 soong_ui.bash --make-mode 走完整流程，不能再 --soong-only。
#
# 关键点：
#   1. out/ 全清 → 之前所有增量修复的中间态（如 .siso_fs_state）一并消失，
#      不需要手动清理，也不会留下污染。
#   2. 源码树的修法（bindgen 软链、gendwarfksyms 补丁、rust/Makefile 补丁、
#      wlan variants override 与软链）全部**不在** out/ 内，不受影响。
#   3. SKIP_ABI_CHECKS=true：prebuilts/clang-tools 是空工作树、缺
#      header-abi-dumper，不跳过会成批失败（见 AGENTS.md）。
#   4. 不指定 ninja target：让 soong_ui 走默认 droid 目标，由它自己拼
#      combined ninja 并调用 siso。
#
# 用法：
#   bash ~/y700-uwu/scripts/server-full-rebuild.sh            # 清空并全量构建
#   KEEP_OUT=1 bash .../server-full-rebuild.sh                # 保留 out（只验证脚本）
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
LOG="$WORK/full-rebuild-$(date +%Y%m%d-%H%M%S).log"

cd "$AOSP" || exit 1
export OUT_DIR=out
export SKIP_ABI_CHECKS=true
export PATH="$AOSP/prebuilts/build-tools/linux-x86/bin:$AOSP/prebuilts/clang/host/linux-x86/clang-r596125/bin:$AOSP/prebuilts/kernel-build-tools/linux-x86/bin:$PATH"

echo "== 开始 $(date) =="
echo "AOSP=$AOSP"
echo "LOG=$LOG"

# 同时写 stdout 和日志：stdout 让后台作业能显示进度，日志便于事后查。
exec > >(tee -a "$LOG") 2>&1

echo "== 0) 环境 =="
free -g | head -2
df -h "$AOSP" | tail -1

if [ "${KEEP_OUT:-0}" != "1" ]; then
    echo "== 1) 清空 out/ =="
    if [ -d "$AOSP/out" ]; then
        echo "清空前: $(du -sh "$AOSP/out" 2>/dev/null | cut -f1)"
        rm -rf "$AOSP/out"
        echo "清空后: $(test -d "$AOSP/out" && echo '仍存在(异常)' || echo '已删除')"
    else
        echo "out/ 不存在，无需清理"
    fi
else
    echo "== 1) KEEP_OUT=1，跳过清空 =="
fi

echo "== 2) lunch =="
source build/envsetup.sh >/dev/null 2>&1
lunch uwu_elden aosp_current user >/dev/null 2>&1
echo "TARGET_PRODUCT=$TARGET_PRODUCT TARGET_BUILD_VARIANT=$TARGET_BUILD_VARIANT"

echo "== 3) 全量构建（bootstrap + kati + soong + ninja，全流程）=="
# 不加 --soong-only：out/ 已空，必须让 soong_ui 做完整 bootstrap
# 加 -k 让已知无害失败（apkcerts doublecheck 等）不中断
build/soong/soong_ui.bash --make-mode otapackage -j"$(nproc)"
rc=$?
echo "build rc=$rc"

echo "== 4) 产物 =="
ls -la --time-style=+%m-%d_%H:%M "$AOSP/out/target/product/elden/"*.zip 2>/dev/null
T="$AOSP/out/soong/.intermediates/build/soong/fsgen/uwu_elden_generated_device/android_arm64_armv8-a-branchprot_oryon/ota.zip"
if [ -f "$T" ]; then
    echo "fsgen ota.zip: $(stat -c %s "$T") B"
    cp -f "$T" "$AOSP/out/target/product/elden/uwu_elden-ota.zip"
    echo "已复制到 product/elden/uwu_elden-ota.zip"
    ls -la --time-style=+%m-%d_%H:%M "$AOSP/out/target/product/elden/uwu_elden-ota.zip"
    md5sum "$AOSP/out/target/product/elden/uwu_elden-ota.zip"
fi

echo "== 结束 $(date) rc=$rc =="
exit $rc
