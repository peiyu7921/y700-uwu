#!/usr/bin/env python3
"""给一个模块的所有 Kbuild 补 vendor include 根目录。

vendor 树把 <dt-bindings/...>、<linux/soc/qcom/...>、<soc/qcom/...> 都放在
sm8750/include/ 下；子目录的 Kbuild 是独立读的，所以必须逐层补。
统一用 subdir-ccflags-y，这样子目录里的源文件也能拿到。

用法: python3 add-vendor-include.py <模块目录> [--first] [--also-makefile]

  --first         额外把 vendor include 前置到 LINUXINCLUDE 最前面。
  --also-makefile 同时处理名为 Makefile 的入口文件。

  为什么需要 --also-makefile：kbuild 递归子目录时先找 Kbuild，找不到才用
  Makefile；很多 vendor 模块（如 wlan/platform/*）只有 Makefile。

  --first  额外把 vendor include 前置到 LINUXINCLUDE 最前面。

为什么需要 --first：有些头文件在 common/include 与 vendor/include 里**同名且
共用同一个 include guard**，但 common 版是瘦身后的 GKI 版。例如

    common/include/linux/soc/qcom/llcc-qcom.h   没有 LLCC_VIDDEC
    vendor/include/linux/soc/qcom/llcc-qcom.h   有   (第 78 行)

两者都是 `#ifndef __LLCC_QCOM__`，先命中的赢。而 LINUXINCLUDE 天然是
common 在前，所以 video-driver 编 venus_hfi.c 时报
`use of undeclared identifier 'LLCC_VIDDEC'`。

`subdir-ccflags-y` 追加在 LINUXINCLUDE 之后，改不了这个顺序，只能在
LINUXINCLUDE 上做前置。前置写法保留原值：

    LINUXINCLUDE := -I<vendor>/include $(LINUXINCLUDE)

因此不会丢掉 kbuild 默认的 arch/ 与 include/ 路径。

本脚本按 marker 幂等，且对已打过基础版补丁的文件也能补上 --first 部分。
"""

import os
import sys

MARK = "sm8750-vendorinc"
MARK_FIRST = "sm8750-vendorinc-first"
VENDOR = "$(srctree)/../vendor/lenovo/sm8750"

BASE_BLOCK = [
    "# %s: vendor headers (<dt-bindings/...>, <linux/soc/qcom/...>," % MARK,
    "# <soc/qcom/...>) all live under sm8750/include",
    "subdir-ccflags-y += -I%s/include" % VENDOR,
    "subdir-ccflags-y += -I%s/include/linux" % VENDOR,
    "",
]

FIRST_BLOCK = [
    "# %s: 这些头文件在 common/include 与 vendor/include 里同名且共用同一个" % MARK_FIRST,
    "# include guard，但 common 版是瘦身 GKI 版（如 llcc-qcom.h 缺 LLCC_VIDDEC），",
    "# 先命中的赢。subdir-ccflags-y 只能追加，改不了顺序，故在 LINUXINCLUDE 上前置。",
    "LINUXINCLUDE := -I%s/include $(LINUXINCLUDE)" % VENDOR,
    "",
]


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    first = "--first" in sys.argv
    also_mk = "--also-makefile" in sys.argv
    if not args:
        sys.exit("用法: add-vendor-include.py <模块目录> [--first] [--also-makefile]")
    mod = args[0].rstrip("/")
    if not os.path.isdir(mod):
        sys.exit("找不到 %s" % mod)

    names = ("Kbuild", "Makefile") if also_mk else ("Kbuild",)
    n_base = n_first = 0
    for dirpath, dirnames, filenames in os.walk(mod):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            # 同一目录同时有 Kbuild 与 Makefile 时，kbuild 只用 Kbuild，
            # 给 Makefile 打补丁是多余且容易误导的，跳过。
            if name == "Makefile" and "Kbuild" in filenames:
                continue
            if name not in names:
                continue
            path = os.path.join(dirpath, name)
            text = open(path, errors="ignore").read()
            orig = text

            # 基础块：subdir-ccflags-y
            if MARK not in text:
                text = "\n".join(BASE_BLOCK) + text
                n_base += 1

            # 前置块：即使基础块早已打过也要补
            if first and MARK_FIRST not in text:
                text = "\n".join(FIRST_BLOCK) + text
                n_first += 1

            if text != orig:
                open(path, "w", errors="ignore").write(text)

    print("patched %d entries (+%d with --first) under %s" % (n_base, n_first, mod))


if __name__ == "__main__":
    main()
