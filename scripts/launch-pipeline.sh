#!/bin/bash
# Launch the build pipeline on the remote server through JumpServer.
#
# JumpServer flow: SSH -> asset menu -> type asset id "1" -> real shell.
# Inputs must be paced, otherwise the menu swallows them before it renders.
#
# Everything (script, log, source tree) stays inside /home/zpy/y700-uwu so the home
# directory and the rest of the server are left untouched.
set -euo pipefail

SCRIPT="scripts/server-allinone.sh"
KEY="$USERPROFILE/.ssh/peiyu"
HOST="zpy@<JUMP_HOST>"
PORT=12222
WORK="${WORK:-/home/zpy/y700-uwu}"

B64=$(base64 -w0 "$SCRIPT")

{
    sleep 2
    printf '1\n'
    sleep 10
    # Clean up leftovers from earlier attempts (including my network test artifacts),
    # then drop the script in WORK. Nothing is left in the home directory.
    printf 'pkill -f "server-allinone" 2>/dev/null; cd %s 2>/dev/null && rm -rf rt speedtest ghspeed git-repo.tar.gz gt1 gt2 gt3 gittest t.tar.gz net.txt proxy.txt repo-mirror.txt init.log e.txt d.txt gitdiag.txt lib.txt g2.txt gn.txt py.txt try2.txt cpu.txt gitfix.txt g3.txt g4.txt 2>/dev/null; rm -f ~/server-allinone.sh ~/pipeline.log; mkdir -p %s\n' "$WORK" "$WORK"
    sleep 5
    printf "echo '%s' | base64 -d > %s/server-allinone.sh && chmod +x %s/server-allinone.sh && wc -c %s/server-allinone.sh\n" \
        "$B64" "$WORK" "$WORK" "$WORK"
    sleep 6
    # setsid detaches from the TTY; plain nohup ... & gets SIGTTOU-suspended when the
    # JumpServer session closes (observed: "[1]+ Stopped").
    printf 'cd %s && setsid nohup bash %s/server-allinone.sh > %s/pipeline.log 2>&1 < /dev/null & echo LAUNCHED\n' \
        "$WORK" "$WORK" "$WORK"
    sleep 4
    printf 'ps aux | grep "[s]erver-allinone" | head -2\n'
    sleep 6
    printf 'echo ---LOG---; tail -8 %s/pipeline.log 2>/dev/null\n' "$WORK"
    sleep 5
    printf 'exit\n'
    sleep 2
    printf 'q\n'
} | timeout 300 ssh -tt -i "$KEY" \
        -o StrictHostKeyChecking=no \
        -o NumberOfPasswordPrompts=0 \
        -o LogLevel=ERROR \
        -p "$PORT" "$HOST"
