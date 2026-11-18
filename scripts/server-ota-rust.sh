#!/bin/bash
# 等 bindgen 装完 -> 验证 -> 重建 soong 图 -> 跑 otapackage。
#
# 背景：CONFIG_ASHMEM 是 6.12 的 Rust 实现（depends on SHMEM && RUST），
# 而 CONFIG_RUST 需要两件事同时成立：
#   1. RUST_IS_AVAILABLE —— 由 scripts/rust_is_available.sh 判定，
#      要求 RUSTC 与 BINDGEN 都能用，且 bindgen >= 0.69.5
#      （0.69.1 配 libclang >= 19.1 有已知 bug，rust-lang/rust-bindgen#2824）
#   2. !MODVERSIONS || GENDWARFKSYMS —— 已由 device bp 的
#      CONFIG_GENDWARFKSYMS=y 满足（scripts/fix-gendwarfksyms-rust.py）
#
# bindgen 走 prebuilts/build-tools/linux-x86/bin/ 里的符号链接进构建 PATH
# （kernel.go 的 makeInvocationExtra 会把这个目录放在 PATH 最前面）。
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
BINDGEN="${BINDGEN:-/home/zpy/.cargo-bindgen/bin/bindgen}"
LOG=$WORK/ota-rust-$(date +%Y%m%d-%H%M%S).log

exec > >(tee "$LOG") 2>&1

echo "== 1) 等 bindgen 装完 =="
for i in $(seq 1 120); do
    if ! pgrep -x cargo >/dev/null 2>&1; then
        echo "cargo 已退出（等待 $((i*10))s）"
        break
    fi
    sleep 10
done

echo "== 2) 验证 bindgen =="
"$BINDGEN" --version || { echo "bindgen 不可用，中止"; exit 1; }
BV=$("$BINDGEN" --version 2>/dev/null | sed -nE 's/.*bindgen ([0-9]+\.[0-9]+\.[0-9]+).*/\1/p')
echo "bindgen 版本: $BV"
ls -la "$AOSP/prebuilts/build-tools/linux-x86/bin/bindgen"

echo "== 3) 验证 rust_is_available =="
KB=$AOSP/out/soong/.intermediates/device/lenovo/elden/kernel/android_arm64_armv8-a-branchprot_oryon/kernel_build
CLANG=$AOSP/prebuilts/clang/host/linux-x86/clang-r596125
RUSTC=$AOSP/prebuilts/rust-toolchain/linux-x86/1.93.1/bin/rustc
cd "$KB" || exit 1
PATH="$AOSP/prebuilts/build-tools/linux-x86/bin:$AOSP/prebuilts/rust-toolchain/linux-x86/1.93.1/bin:$PATH" \
RUSTC="$RUSTC" BINDGEN=bindgen CC="$CLANG/bin/clang" \
LIBCLANG_PATH="$CLANG/lib" \
    bash "$AOSP/kernel/platform/kernel-6.12/common/scripts/rust_is_available.sh"
echo "rust_is_available rc=$?"

echo "== 4) 重建 soong 图（SKIP_ABI_CHECKS）=="
cd "$AOSP" || exit 1
export OUT_DIR=out
export SKIP_ABI_CHECKS=true
export PATH="$AOSP/prebuilts/build-tools/linux-x86/bin:$CLANG/bin:$AOSP/prebuilts/kernel-build-tools/linux-x86/bin:$PATH"
source build/envsetup.sh >/dev/null 2>&1
lunch uwu_elden aosp_current user >/dev/null 2>&1
build/soong/soong_ui.bash --make-mode --soong-only
echo "regen rc=$?"

echo "== 5) 确认 .config 里 ASHMEM/RUST/GENDWARFKSYMS =="
for k in CONFIG_RUST CONFIG_ASHMEM CONFIG_GENDWARFKSYMS CONFIG_MODVERSIONS CONFIG_RUST_IS_AVAILABLE; do
    printf '  %-32s ' "$k"
    grep -E "^(# )?${k}(=| is not set)" "$KB/.config" 2>/dev/null | head -1 || echo "(无条目)"
done

echo "== 6) 跑 otapackage =="
prebuilts/siso/linux-x86/siso ninja -k 0 -f out/combined-uwu_elden.ninja otapackage
echo "ota rc=$?"

echo "== 7) 产物 =="
ls -la --time-style=+%m-%d_%H:%M out/target/product/elden/*.zip 2>/dev/null
echo "== 结束 =="
