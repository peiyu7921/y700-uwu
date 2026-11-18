#!/usr/bin/env python3
"""给 mm-drivers 各子模块的 Kbuild 补 kbuild 路径下缺失的 include 与 *_ROOT。

背景：这几个模块只通过 DDK 的 Makefile 构建，KBUILD_OPTIONS 才提供
MSM_HFI_CORE_ROOT 等变量；uwu 的 kbuild 路径（M=<abs dir>）不经过那个
Makefile，于是
  include $(MSM_HFI_CORE_ROOT)/config/kalamammdrivers.conf
展开成 include /config/kalamammdrivers.conf，报 No rule to make target。
另外 GKI 的 common/include 里也有 linux/remoteproc/qcom_rproc.h，但没有
rproc_set_state，必须让 vendor 的 include 树排在前面。

用法: python3 fix-mm-drivers.py <AOSP 根目录>
"""

import os
import sys

MARK = "sm8750-mmdrivers-fix"

# 子目录 -> (该子目录里 _ROOT 变量名, 指向模块根的相对表达式, 自家 include 目录)
SUBS = {
    "hfi_core": ("MSM_HFI_CORE_ROOT", "$(src)/..", "inc"),
    "hw_fence": ("MSM_HW_FENCE_ROOT", "$(src)/..", "include"),
    "sync_fence": ("SYNC_FENCE_ROOT", "$(src)/..", "include"),
    "msm_ext_display": ("MSM_EXT_DISPLAY_ROOT", "$(src)/..", "include"),
}

VENDOR = "$(srctree)/../vendor/lenovo/sm8750"


def header(var, root, incdir):
    return "\n".join([
        "# %s: only the DDK Makefile passes %s via KBUILD_OPTIONS, so under" % (MARK, var),
        "# the kbuild path (M=<abs dir>) it is empty and the includes below collapse",
        "# to '/config/...'. Derive it from $(src) instead.",
        "%s := %s" % (var, root),
        "",
        "# %s: GKI common/include also ships linux/remoteproc/qcom_rproc.h, but without" % MARK,
        "# rproc_set_state; the vendor include tree has to win the search order.",
        "LINUXINCLUDE := -I%s/include $(LINUXINCLUDE)" % VENDOR,
        "subdir-ccflags-y += -I%s/include" % VENDOR,
        "subdir-ccflags-y += -I%s/include/linux" % VENDOR,
        "",
        "# %s: src/*.c includes headers from this module's %s/ tree" % (MARK, incdir),
        "subdir-ccflags-y += -I$(src)/%s" % incdir,
        "",
    ])


def main():
    aosp = os.path.abspath(sys.argv[1])
    base = os.path.join(
        aosp,
        "kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules/qcom/opensource/mm-drivers",
    )
    if not os.path.isdir(base):
        sys.exit("找不到 %s" % base)
    for sub, (var, root, incdir) in SUBS.items():
        path = os.path.join(base, sub, "Kbuild")
        if not os.path.exists(path):
            print("skip %s (no Kbuild)" % sub)
            continue
        text = open(path, errors="ignore").read()
        if MARK in text:
            print("ok   %s" % sub)
            continue
        open(path, "w", errors="ignore").write(header(var, root, incdir) + text)
        print("fixed %s" % sub)


if __name__ == "__main__":
    main()
