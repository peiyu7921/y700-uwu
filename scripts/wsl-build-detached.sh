#!/bin/bash
# Run a WSL build script detached from any interactive Reasonix session.
#
# Usage:
#   bash wsl-build-detached.sh [script-in-wsl]      # default: scripts/wsl-build.sh
#
# WSL2 tears the distro down when the last wsl.exe session exits, so `setsid`/`nohup` alone do
# not survive; this wrapper starts the build in the background and then holds a session open
# with `sleep infinity`. Launch it through PowerShell Start-Process so the wsl.exe running it
# is not a child of Reasonix either.
BUILD="${1:-/mnt/d/projects/y700-uwu/scripts/wsl-build.sh}"
LOG="${LOG:-/root/wsl-bg-build.log}"
cd /root/aosp || { echo "MISSING /root/aosp" >&2; exit 1; }
: > "$LOG"
echo "BUILD_SCRIPT=$BUILD" | tee -a "$LOG"
# ninja reads stdin to handle its interactive keys and exits as soon as stdin hits EOF. A
# detached process has no stdin at all, which is why the build printed "Starting ninja..." and
# then vanished. Feed it an endless empty stream instead.
setsid nohup bash -c "sleep infinity | bash $BUILD" >> "$LOG" 2>&1 &
echo "BUILD_PID=$!" | tee -a "$LOG"
echo BG_STARTED
exec sleep infinity
