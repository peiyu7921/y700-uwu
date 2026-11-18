#!/bin/bash
# The GKI AutoFDO profile (common/gki/<arch>/afdo/kernel.afdo) is not synced into this
# workspace. uwu_kernel looks it up by default; set autofdo_profile to "none" to disable,
# as documented in the uwu_kernel configuration reference.
# Usage: disable-afdo.sh <Android.bp>
set -uo pipefail
p="${1:?usage: $0 <Android.bp>}"
[ -f "$p" ] || { echo "MISSING $p" >&2; exit 1; }
if grep -q 'autofdo_profile' "$p"; then
    echo "ALREADY_SET"
    exit 0
fi
sed -i 's|^    image_name: "Image",$|    image_name: "Image",\n    // GKI AutoFDO profile is not part of this workspace; disabled per the\n    // uwu_kernel configuration reference.\n    autofdo_profile: "none",|' "$p"
if grep -q 'autofdo_profile' "$p"; then
    echo "AFDO_DISABLED"
else
    echo "WARN anchor not found" >&2
    exit 1
fi
