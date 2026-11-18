#!/bin/bash
# Insert CONFIG_* lines at the top of the uwu_kernel `overrides` list in Android.bp.
# Usage: add-overrides.sh <Android.bp> "CONFIG_A=y" ["CONFIG_B=n" ...]
set -uo pipefail
p="${1:?usage: $0 <Android.bp> CONFIG...}"
shift
[ -f "$p" ] || { echo "MISSING $p" >&2; exit 1; }
[ "$#" -gt 0 ] || { echo "no overrides given" >&2; exit 1; }

python_bin=$(command -v python3 || command -v python || true)
[ -n "$python_bin" ] || { echo "no python" >&2; exit 1; }

"$python_bin" - "$p" "$@" <<'PY'
import sys

path, entries = sys.argv[1], sys.argv[2:]
text = open(path, encoding="utf-8").read()

missing = [e for e in entries if '"%s"' % e not in text]
if not missing:
    print("ALREADY_SET")
    sys.exit(0)

anchor = "        overrides: [\n"
if anchor not in text:
    print("WARN overrides anchor not found")
    sys.exit(1)

added = "".join('            "%s",\n' % e for e in missing)
open(path, "w", encoding="utf-8").write(text.replace(anchor, anchor + added, 1))
print("ADDED: " + ", ".join(missing))
PY
