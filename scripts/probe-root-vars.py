#!/usr/bin/env python3
"""排查 vendor Kbuild 里 $(X_ROOT) 变量的定义来源。

DDK 的 Makefile 通过 KBUILD_OPTIONS 传 *_ROOT；uwu 的 kbuild 路径（M=<abs>）
不经过那个 Makefile，变量就展开成空，于是出现 '/config/xxx.conf' 这种路径。
"""
import os
import re
import sys

root = sys.argv[1].rstrip("/")
uses = {}
defs = {}

for dirpath, dirnames, filenames in os.walk(root):
    dirnames[:] = [d for d in dirnames if d != ".git"]
    for name in filenames:
        if name not in ("Kbuild", "Makefile"):
            continue
        path = os.path.join(dirpath, name)
        rel = os.path.relpath(path, root)
        try:
            text = open(path, errors="ignore").read()
        except OSError:
            continue
        for var in re.findall(r"\$\(([A-Z_]+_ROOT)\)", text):
            uses.setdefault(var, set()).add(rel)
        for var in re.findall(r"(?m)^[ \t]*([A-Z_]+_ROOT)[ \t]*[:+?]?=", text):
            defs.setdefault(var, set()).add(rel)

for var in sorted(uses):
    u = sorted(uses[var])
    d = sorted(defs.get(var, ()))
    flag = "OK  " if d else "MISS"
    print("%s %-24s use=%s" % (flag, var, ",".join(u[:3])))
    if d:
        print("      def=%s" % ",".join(d[:3]))
