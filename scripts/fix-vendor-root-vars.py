#!/usr/bin/env python3
"""给 vendor Kbuild 补上只由 DDK Makefile 的 KBUILD_OPTIONS 传进来的 *_ROOT 变量。

这些变量在 uwu 的 kbuild 路径（M=<abs dir> 或 in-tree modules）下永远为空，于是
Kbuild 里的

    include $(SPU_ROOT)/config/gki_spu.conf

展开成 `include /config/gki_spu.conf`，kbuild 直接报

    No rule to make target '/config/xxx.conf'

每类变量的根都能从 $(src) 推出（$(src) 是当前 Kbuild 所在目录）：

    $(src)        变量定义就在模块根的 Kbuild 里
    $(src)/..     定义在模块的子目录 Kbuild 里（如 synx-kernel/msm/）
    $(srctree)    指 GKI 公共树

**按变量粒度幂等**：逐个检查 `<VAR> :=` 是否已存在，只补缺的。这一点很重要 ——
有的变量可能已被 kernel-tree-fixes.py 或其他脚本补过，整文件级判断会重复定义。

用法: python3 fix-vendor-root-vars.py <kernel-6.12 目录或 opensource 目录>
"""

import os
import sys

MARK = "sm8750-rootpath-fix"

# 变量 -> 定义应落在哪个文件的哪个根表达式
FIXES = {
    # --- 模块根的 Kbuild ---
    "spu-kernel/Kbuild": {
        "SPU_ROOT": "$(src)",
    },
    "mmrm-driver/Kbuild": {
        "MMRM_ROOT": "$(src)",
    },
    "touch-drivers/Kbuild": {
        # TOUCH_ROOT 只在 Makefile / Android.mk 里定义，kbuild 读的是 Kbuild
        "TOUCH_ROOT": "$(src)",
    },
    "securemsm-kernel/Kbuild": {
        # SSG_MODULE_ROOT 只在 DDK Makefile 里定义
        "SSG_MODULE_ROOT": "$(src)",
    },
    "camera-kernel/Kbuild": {
        # KERNEL_ROOT 只用于 -I，指 GKI 树
        "KERNEL_ROOT": "$(srctree)",
    },
    # --- 子目录 Kbuild ---
    "synx-kernel/msm/Kbuild": {
        "SYNX_ROOT": "$(src)/..",
    },
    "eva-kernel/msm/Kbuild": {
        "EVA_ROOT": "$(src)/..",
    },
    "mmrm-driver/driver/Kbuild": {
        "MMRM_ROOT": "$(src)/..",
    },
    "mmrm-driver/vm/be/Kbuild": {
        "MMRM_ROOT": "$(src)/../..",
    },
    # video-driver 的两个子目录各自 `include $(VIDEO_ROOT)/config/sun_video.conf`，
    # 而 VIDEO_ROOT 只在 Makefile 里用 $(shell pwd) 定义，kbuild 路径读不到，
    # 于是展开成 include /config/sun_video.conf -> No rule to make target。
    "video-driver/video/Kbuild": {
        "VIDEO_ROOT": "$(src)/..",
    },
    "video-driver/msm_video/Kbuild": {
        "VIDEO_ROOT": "$(src)/..",
    },
}

HEADER = (
    "# {mark}: these only come from the DDK Makefile's KBUILD_OPTIONS,\n"
    "# which the kbuild path (M=<abs dir>) never passes; without them the\n"
    "# includes below collapse to '/config/...'.\n"
)


def defined(text, var):
    """变量是否已在文本里被定义（`VAR :=` / `VAR =` / `VAR ?=` 都算）。"""
    for ln in text.split("\n"):
        s = ln.lstrip()
        if s.startswith(var):
            rest = s[len(var):].lstrip()
            if rest[:1] in ("=", ":") or rest.startswith("?="):
                return True
    return False


def main():
    if len(sys.argv) < 2:
        sys.exit("用法: fix-vendor-root-vars.py <kernel-6.12 目录>")
    root = sys.argv[1].rstrip("/")
    base = os.path.join(root, "sm8750-modules/qcom/opensource")
    if not os.path.isdir(base):
        base = os.path.join(root, "vendor/lenovo/sm8750-modules/qcom/opensource")
    if not os.path.isdir(base):
        base = root

    changed, skipped, missing = [], [], []
    for rel, vars_ in FIXES.items():
        path = os.path.join(base, rel)
        if not os.path.exists(path):
            missing.append(rel)
            continue
        text = open(path, errors="ignore").read()
        add = [(v, e) for v, e in vars_.items() if not defined(text, v)]
        if not add:
            skipped.append(rel)
            continue

        block = ""
        if MARK not in text:
            block += HEADER.format(mark=MARK)
        for var, expr in add:
            block += "%s := %s\n" % (var, expr)
        open(path, "w", errors="ignore").write(block + text)
        changed.append("%s (%s)" % (rel, ", ".join(v for v, _ in add)))

    for item in changed:
        print("patched %s" % item)
    for item in skipped:
        print("ok      %s" % item)
    for item in missing:
        print("absent  %s" % item)
    if not changed:
        print("nothing to do")


if __name__ == "__main__":
    main()
