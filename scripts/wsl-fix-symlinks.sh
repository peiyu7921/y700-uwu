set -e
KROOT=/root/aosp/kernel/platform/kernel-6.12/vendor/lenovo
LIST=/mnt/d/projects/y700-uwu/scripts/symlinks.tsv

created=0
skipped=0

while IFS=$'\t' read -r repo path target; do
    [ -z "$repo" ] && continue
    [ -z "$path" ] && continue
    case "$repo" in
        android_kernel_lenovo_sm8750-modules) base="$KROOT/sm8750-modules" ;;
        android_kernel_lenovo_sm8750)         base="$KROOT/sm8750" ;;
        *) continue ;;
    esac

    f="$base/$path"
    if [ -L "$f" ]; then
        skipped=$((skipped+1))
        continue
    fi
    [ -e "$f" ] && rm -f "$f"
    mkdir -p "$(dirname "$f")"
    ln -s "$target" "$f"
    created=$((created+1))
done < "$LIST"

echo "symlinks created=$created already_ok=$skipped"

echo "=== spot check ==="
ls -l "$KROOT/sm8750-modules/nxp/opensource/driver/repo_paths.bzl"
ls -l "$KROOT/sm8750/scripts/dummy-tools/nm"
