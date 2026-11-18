#!/usr/bin/env python3
"""去掉 `choice` 块里选项的提示语。

现代 kconfig 报错：`choice value has a prompt outside its choice group`。
vendor 树 drivers/soc/qcom/Kconfig 里 DEBUG_SPINLOCK_BITE_ON_BUG /
DEBUG_SPINLOCK_PANIC_ON_BUG 两个 choice 选项写成 `bool "..."`，去掉提示语即可
（choice 本身已有 prompt，选项仍按 config 名区分）。
"""
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
text = path.read_text(errors="ignore")

PAIRS = [
    ('\t\tbool "Cause a Watchdog Bite on Spinlock bug"', "\t\tbool"),
    ('\t\tbool "Cause a Kernel Panic on Spinlock bug"', "\t\tbool"),
]

removed = 0
for old, new in PAIRS:
    if old in text:
        text = text.replace(old, new, 1)
        removed += 1

path.write_text(text)
print("prompts removed:", removed)
print("remaining choice prompts:", sum(1 for o, _ in PAIRS if o in text))
