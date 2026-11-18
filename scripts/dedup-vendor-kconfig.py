#!/usr/bin/env python3
"""去掉 vendor 树内部 Kconfig 与 Kconfig.msm 的重复 source。

背景（r83）：vendor 树自身作为 srctree 构建时，`choice` 被解析两遍、
报 "choice value has a prompt outside its choice group" /
"choice member must have a prompt"。原因是同一条路径出现两次：

    Kconfig.msm:107          source "$(KCONFIG_EXT_PREFIX)drivers/soc/qcom/Kconfig"   # 绝对前缀
    drivers/soc/Kconfig:22   source "drivers/soc/qcom/Kconfig"                        # 相对 srctree

srctree=common 时两者是不同文件（各 GKI / vendor），没问题；srctree=vendor 时
两者指向同一文件 → 重复解析。

这里把「父级 Kconfig 里 source 子目录 Kconfig」这种重复行注释掉，符号不会丢：
Kconfig.msm 已经用绝对前缀 source 过同一份文件。
"""
import os
import pathlib
import re
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

V = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                 _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
MARK = "# sm8750-kconfig-dedup: also sourced via Kconfig.msm"

msm = (V / "Kconfig.msm").read_text(errors="ignore")
targets = re.findall(r'source "\$\(KCONFIG_EXT_PREFIX\)([^"]+)"', msm)
print("Kconfig.msm sources:", len(targets))

patched = []
for rel in targets:
    parent = pathlib.Path(rel).parent
    if str(parent) in (".", ""):
        continue
    kfile = V / parent / "Kconfig"
    if not kfile.is_file():
        continue
    text = kfile.read_text(errors="ignore")
    if MARK in text:
        continue

    changed = False
    out = []
    for line in text.splitlines():
        stripped = line.strip()
        # source "drivers/soc/qcom/Kconfig" 或 source "qcom/Kconfig"（相对当前目录）
        m = re.match(r'^source\s+"([^"]+)"\s*$', stripped)
        if m and MARK not in line:
            src = m.group(1)
            if src == rel or (not src.startswith("$(") and (parent / src).as_posix() == rel):
                out.append(MARK)
                out.append("# " + line)
                changed = True
                continue
        out.append(line)
    if changed:
        kfile.write_text("\n".join(out) + "\n")
        patched.append(str(kfile.relative_to(V)))

print("patched files:", len(patched))
for p in patched:
    print("  ", p)
