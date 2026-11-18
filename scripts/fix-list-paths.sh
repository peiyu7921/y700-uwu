#!/bin/bash
# uwu_kernel resolves module list files with android.PathForSource(), i.e. relative to the
# Android source root -- not to the module directory. Rewrite the bare filenames accordingly.
# Usage: fix-list-paths.sh <Android.bp>
set -uo pipefail
p="${1:?usage: $0 <Android.bp>}"
[ -f "$p" ] || { echo "MISSING $p" >&2; exit 1; }
sed -i \
    -e 's|\(_module_install_list: \["\)modules\.|\1device/lenovo/elden/modules.|g' \
    -e 's|\(_module_load_list: \["\)modules\.|\1device/lenovo/elden/modules.|g' \
    "$p"
echo "prefixed: $(grep -c 'device/lenovo/elden/modules' "$p")"
echo PATHS_FIXED
