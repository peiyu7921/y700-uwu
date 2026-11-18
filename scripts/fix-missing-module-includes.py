#!/usr/bin/env python3
"""给缺失模块的源码目录补 vendor include 路径。

实测（mhi / net-qrtr）：
    ns.c:11: fatal error: 'linux/ipc_logging.h' file not found
    smd.c:41: error: call to undeclared function 'qcom_glink_is_wakeup'

都是 vendor include 树（`vendor/lenovo/sm8750/include/...`）里的头没在搜索路径上。
用 `-idirafter` 追加（放最后，避免遮蔽源码目录里的同名头，之前 reset.h 踩过）。
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

KP = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12")
VEND = KP / "vendor/lenovo"

DIRS = [
    "sm8750/net/qrtr",
    "sm8750-modules/qcom/opensource/wlan/platform/cnss_prealloc",
    "sm8750-modules/qcom/opensource/wlan/platform/cnss_utils",
    "sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/ipa",
    "sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/gsi",
    "sm8750/drivers/power/supply",
]

BLOCK = (
    "# sm8750-missingmod-fix: vendor include roots for this module\n"
    "subdir-ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
    "subdir-ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux\n"
    "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
    "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux\n"
)

changed, skipped = [], []
for rel in DIRS:
    d = VEND / rel
    if not d.is_dir():
        skipped.append((rel, "目录不存在"))
        continue
    touched = False
    for fn in ("Kbuild", "Makefile"):
        p = d / fn
        if not p.exists():
            continue
        t = p.read_text(errors="ignore")
        if "sm8750-missingmod-fix" in t:
            continue
        p.write_text(BLOCK + t)
        touched = True
    (changed if touched else skipped).append(
        (rel, "已补" if touched else "无 Makefile/Kbuild")
    )

print("== 已补 include ==")
for rel, s in changed:
    print("  ", rel, s)
print("== 跳过 ==")
for rel, s in skipped:
    print("  ", rel, s)
