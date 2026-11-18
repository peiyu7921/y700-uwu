cd /root/aosp
echo "=== uwu build tasks ==="
ls vendor/uwu/build/tasks/ 2>/dev/null
echo "=== bacon def ==="
grep -rn "bacon" vendor/uwu/build/ 2>/dev/null | head -5
echo "=== available make targets (sample) ==="
grep -rn "^.PHONY:.*bacon\|^bacon:" build/make/core/*.mk vendor/uwu/build/**/*.mk 2>/dev/null | head -5
