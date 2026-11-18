#!/usr/bin/env python3
"""Bootstrap (c): 给 vendor Kbuild 里用 ccflags-y := 覆盖的补上 vendor include。

ccflags-y := 会把 kbuild 先前累积的 vendor include 全部丢弃，
导致 camera-kernel 等模块找不到 <linux/mem-buf.h>、<soc/qcom/minidump.h>。
"""
import os
import re
import sys

root = sys.argv[1].rstrip("/")
LINE = "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include"
n = 0

for dp, dn, fs in os.walk(root):
    dn[:] = [d for d in dn if d != ".git"]
    for f in fs:
        if f != "Kbuild":
            continue
        p = os.path.join(dp, f)
        s = open(p, errors="ignore").read()
        if not re.search(r"ccflags-y[ \t]*:=", s):
            continue
        if "vendor/lenovo/sm8750/include" in s:
            continue
        out, done = [], False
        for ln in s.split("\n"):
            out.append(ln)
            if ln.rstrip().endswith("\\"):
                continue
            if re.match(r"ccflags-y[ \t]*[:+]?=", ln) and not done:
                out.append(LINE)
                done = True
        if not done:
            out.insert(0, LINE)
        open(p, "w", errors="ignore").write("\n".join(out))
        n += 1

print("patched %d Kbuild" % n)
