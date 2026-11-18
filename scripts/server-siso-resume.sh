#!/bin/bash
# 在 u-zpy 上续跑 otapackage —— 绕过 soong_ui，直接用 siso 跑 combined ninja 图。
#
# 为什么不用 `m otapackage`（即 server-resume.sh 的做法）：
#   soong_ui/kati 阶段在本树上会卡死（多次实测无进展），所以才有了"直跑已生成的
#   out/combined-uwu_elden.ninja"这条路径。ninja 图一旦由 soong_ui 生成过，后续增量
#   完全可以由 siso/ninja 独立驱动。
#
# 为什么必须 export OUT_DIR=out：
#   gen_build_prop.py:282 是
#       file.name.startswith(os.environ.get("OUT_DIR"))
#   而 OUT_DIR 是 soong_ui 注入的；直跑 siso/ninja 时它不存在 →
#       TypeError: startswith first arg must be str or a tuple of str, not NoneType
#   → //build/soong:odm-build.prop 失败 → 卡住 build.prop 及其下游。
#   实测：无该变量 rc=1；`OUT_DIR=out` 时 rc=0 并正常产出 build.prop。
#
# 为什么用 `siso ninja` 而不是 `prebuilts/build-tools/.../ninja`：
#   那个 ninja 二进制在 kernel 那批超大 deps 上写坏 .ninja_deps：
#       ninja: build stopped: Error writing to deps log: Numerical result out of range.
#   删掉 .ninja_deps 后在 //device/lenovo/elden:kernel Kernel source dependencies
#   处必然复现。siso 用自己的依赖库，没有这个问题。
#
# 为什么必须是 `-k 0`：
#   siso 的 -k 默认是 1（一个失败就整体退出，剩下上万 action 全不跑）。
#   -k 0 表示忽略失败继续，由最终 otapackage 目标决定成败。以下两类"失败"
#   是已知的、不阻塞产物的，必须靠 -k 0 放行：
#     1. header-abi-dumper 大批失败（clang-r596125 = LLVM 22.0.2 产出的 bitcode，
#        prebuilts/clang-tools 里的 dumper 是 LLVM 21.1.8，读不了新版 attribute：
#        `Unknown attribute kind (105)`）。纯 ABI 检查，不进产物。
#     2. apkcerts doublecheck（build/make/core/Makefile:799-814）：拿
#        `-soong-doublecheck.txt` 和 `-soong_apkcerts_file_with_soong_and_make_modules_removed.txt`
#        做 diff 的迁移校验。APKCERTS_FILE 实为 cat(make.txt, removed.txt)，doublecheck
#        不参与产物。两侧模块集合天然不同（含 *_test.apk vs 含 ANGLE.apk）。
#
# 为什么用 `script` + `sleep infinity |`：
#   siso 在非 tty 下不输出进度；script 分配 pty 才有实时进度和 FAILED 块。
#   setsid+nohup 下 stdin 是 /dev/null，pty 立即 EOF 会杀掉子进程，
#   所以用 `sleep infinity |` 维持一个永不结束的输入流。
#
# 用法（在服务器上）：
#   bash ~/y700-uwu/scripts/server-siso-resume.sh
# 或从本地：
#   ssh u-zpy 'bash ~/y700-uwu/scripts/server-siso-resume.sh'
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
NINJA_FILE="${NINJA_FILE:-out/combined-uwu_elden.ninja}"
TARGET="${TARGET:-otapackage}"
LOG="${LOG:-$WORK/siso-$(date +%Y%m%d-%H%M%S).log}"

SISO="$AOSP/prebuilts/siso/linux-x86/siso"
[ -x "$SISO" ] || { echo "找不到 siso: $SISO" >&2; exit 1; }

cd "$AOSP" || exit 1

# siso 的文件状态缓存会损坏（实测涨到 51 M）。损坏后的表现极有迷惑性：
# 正常的编译步骤被报成
#     err: flush <out>/xxx.jar.rsp local-ready: chtimes <out>/xxx.jar.rsp
# 于是 art.module.public.api.stubs.* 的 stubs.jar 从未生成，进而
#     cannot make progress due to previous N errors
# 让剩余上万 action 全部停摆。产物目录里能看到的证据是：只有 -stubs.srcjar，
# 没有 stubs.jar / .rsp；而手工 touch+chtimes 该目录完全正常，
# siso.INFO 里 rlimit.nofile=1048575、memory_limit=unlimited（排除 fd/内存）。
#
# 注意：缓存在正常增量运行中本来就会长到几十 MB，**大小不是损坏的判据**。
# 而且挪走它要付一次代价不小的代价（siso 需要重新评估全部 17 万个目标）。
# 所以这里默认「不动」，只有真的出现上面那组 flush/chtimes 假失败时，
# 才用 RESET_FS_STATE=1 显式重建一次：
#     RESET_FS_STATE=1 bash ~/y700-uwu/scripts/server-siso-resume.sh
if [ "${RESET_FS_STATE:-0}" = "1" ] && [ -f "$AOSP/out/.siso_fs_state" ]; then
    SZ=$(stat -c %s "$AOSP/out/.siso_fs_state" 2>/dev/null || echo 0)
    mv "$AOSP/out/.siso_fs_state" "$AOSP/out/.siso_fs_state.bak-$(date +%Y%m%d-%H%M%S)" \
        && echo "== 已按要求重建 .siso_fs_state（挪走 $((SZ/1048576)) MiB 旧缓存）=="
fi

# soong_ui 会注入这些；直跑时必须自己补齐（见文件头说明）
export OUT_DIR=out
export PATH="$AOSP/prebuilts/build-tools/linux-x86/bin:$AOSP/prebuilts/clang/host/linux-x86/clang-r596125/bin:$AOSP/prebuilts/kernel-build-tools/linux-x86/bin:$PATH"

echo "== siso resume: $TARGET =="
echo "== ninja: $NINJA_FILE =="
echo "== log:   $LOG =="
echo "== OUT_DIR=$OUT_DIR  -k 0（忽略不阻塞产物的失败）=="

setsid nohup bash -c \
    "export OUT_DIR=$OUT_DIR; sleep infinity | script -q -e -c \"$SISO ninja -k 0 -f $NINJA_FILE $TARGET\" $LOG" \
    > "$WORK/siso-resume.out" 2>&1 < /dev/null &

sleep 5
echo "== 已后台启动；进度用：=="
echo "   grep -oaE '\\[[0-9]+/[0-9]+\\]' $LOG | tail -1"
echo "== 等它结束可用：=="
echo "   while pgrep -x siso >/dev/null; do sleep 60; done"
