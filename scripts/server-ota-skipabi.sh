#!/bin/bash
# 带 SKIP_ABI_CHECKS=true 重建 soong 图，然后跑全量 otapackage。
#
# 为什么要 SKIP_ABI_CHECKS：
#   prebuilts/clang-tools/linux-x86/bin/header-abi-dumper 在本机不存在，
#   siso 在 schedule 阶段就报
#     "... , needed by <x>.sdump", missing and no known rule to make it
#   整体退出（连 -k 0 都到不了执行阶段）。
#   build/soong/cc/sabi.go:262 的 IsEnvTrue("SKIP_ABI_CHECKS") 会让 OutgoingTransition
#   直接返回 ""，于是 soong 根本不生成 sabi 变体与 abidiff 步骤。
#   它是纯 ABI 检查、不进产物，跳过无副作用。
#
# 为什么 regen 不带 target 参数：
#   之前 rebuild_kmod.sh 写 `--soong-only out/soong/build.ninja`，该名字不是本树的图
#   （本树是 build.uwu_elden.ninja），ninja 报 unknown target 使 rc=1 —— 图虽然写盘了，
#   但 rc 具有误导性。这里不指定 target，让 soong 走默认目标。
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
LOG=$WORK/ota-full-$(date +%Y%m%d-%H%M%S).log

cd "$AOSP" || exit 1
export OUT_DIR=out
export SKIP_ABI_CHECKS=true
export PATH="$AOSP/prebuilts/build-tools/linux-x86/bin:$AOSP/prebuilts/clang/host/linux-x86/clang-r596125/bin:$AOSP/prebuilts/kernel-build-tools/linux-x86/bin:$PATH"

exec > "$LOG" 2>&1

echo "== 开始 $(date) =="
source build/envsetup.sh >/dev/null 2>&1
lunch uwu_elden aosp_current user >/dev/null 2>&1
echo "== SKIP_ABI_CHECKS=$SKIP_ABI_CHECKS =="

echo "== 1) 重建 soong 图 =="
build/soong/soong_ui.bash --make-mode --soong-only
echo "regen rc=$?"
ls -la --time-style=+%H:%M out/soong/build.uwu_elden.ninja | awk '{print $5, $6, $7}'

echo "== 2) 跑 otapackage（-k 0 放行已知无害失败）=="
prebuilts/siso/linux-x86/siso ninja -k 0 -f out/combined-uwu_elden.ninja otapackage
echo "ota rc=$?"

echo "== 3) 产物 =="
ls -la --time-style=+%m-%d_%H:%M out/target/product/elden/*.zip 2>/dev/null
echo "== 结束 $(date) =="
