#!/bin/bash
# Fold the uwu_kernel module block from kernel.bp into Android.bp (Soong only reads Android.bp).
# Usage: merge-uwu-bp.sh <device-dir>
set -uo pipefail
DEV="${1:-}"
if [ -z "$DEV" ] || [ ! -d "$DEV" ]; then
    echo "usage: $0 <device-dir>" >&2
    exit 2
fi
cd "$DEV" || exit 1
if [ ! -f kernel.bp ]; then
    if grep -q '^uwu_kernel {' Android.bp 2>/dev/null; then
        echo "ALREADY_MERGED"
        exit 0
    fi
    echo "MISSING kernel.bp" >&2
    exit 1
fi
sed -n '/^uwu_kernel {/,$p' kernel.bp >> Android.bp
rm -f kernel.bp
echo "MERGED_OK"
echo "configs: $(grep -c CONFIG_ Android.bp)"
echo "lines: $(wc -l < Android.bp)"
