#!/bin/bash
# gendwarfksyms (used when CONFIG_MODVERSIONS is on) reads DWARF through the host libdw,
# which cannot decode zstd-compressed debug info. gki_defconfig enables
# CONFIG_DEBUG_INFO_COMPRESSED_ZSTD, so the uwu_kernel Kbuild fails with
#   gendwarfksyms: process_module: dwarf_get_units failed: no debugging information?
# Disable the compression through the uwu_kernel config overrides.
# Usage: no-debuginfo-compress.sh <Android.bp>
set -uo pipefail
p="${1:?usage: $0 <Android.bp>}"
[ -f "$p" ] || { echo "MISSING $p" >&2; exit 1; }
if grep -q 'DEBUG_INFO_COMPRESSED_NONE=y' "$p"; then
    echo "ALREADY_SET"
    exit 0
fi
sed -i 's|^        overrides: \[$|        overrides: [\n            "CONFIG_DEBUG_INFO_COMPRESSED_ZSTD=n",\n            "CONFIG_DEBUG_INFO_COMPRESSED_NONE=y",|' "$p"
if grep -q 'DEBUG_INFO_COMPRESSED_NONE=y' "$p"; then
    echo "COMPRESS_DISABLED"
else
    echo "WARN anchor not found" >&2
    exit 1
fi
