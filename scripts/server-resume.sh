#!/bin/bash
# Resume the uwuAOSP build on the server (u-zpy) with reduced parallelism and a visible log.
#
# Why -j8 instead of the -j12 that fix-build.sh used:
#   The -j12 run died at out/soong/.intermediates/packages/apps/Launcher3/Launcher3QuickStep/
#   android_common/dex/Launcher3QuickStep.jar -- the R8/d8 step -- with "Killed" in stderr.
#   At that moment swap was 7.9Gi/8.0Gi (full) and Mem used was 21Gi. dmesg had no OOM record,
#   so the SIGKILL came from siso's own localexec memory guard, not the kernel OOM killer.
#   Halving the parallel R8/d8 load keeps the same work off the swap limit.
#
# Why `script`:
#   soong_ui prints nothing at all when stdout is not a terminal. That is why the previous
#   build-<timestamp>.log stayed at 0 bytes even though the build ran for 20 minutes, and why
#   the only failure evidence ended up in out/siso_output. `script` allocates a pty so the
#   log gets real progress and the FAILED block.
#
# Why `sleep infinity |`:
#   script forwards stdin to the pty. Under setsid+nohup stdin is /dev/null, which makes the
#   pty see EOF immediately and kills the child. An endless empty stream keeps it open.
#
#   setsid nohup bash -c "sleep infinity | script -q -e -c 'm otapackage -j8' $LOG" &
set -uo pipefail

AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"
WORK="${WORK:-/home/zpy/y700-uwu}"
JOBS="${JOBS:-8}"
LOG=$WORK/build-j${JOBS}-$(date +%Y%m%d-%H%M%S).log

cd "$AOSP" || exit 1
# shellcheck disable=SC1091
source build/envsetup.sh >/dev/null 2>&1
lunch uwu_elden aosp_current user >/dev/null 2>&1

echo "== resume otapackage -j$JOBS =="
echo "== log: $LOG =="
script -q -e -c "m otapackage -j${JOBS}" "$LOG"
RC=$?
echo "== m exited with $RC =="
echo "== artifacts =="
ls -lh out/target/product/elden/*.img out/target/product/elden/*.zip 2>/dev/null || echo "(none)"
echo "== DONE rc=$RC =="
