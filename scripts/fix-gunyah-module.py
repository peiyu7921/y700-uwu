#!/usr/bin/env python3
"""把 arch/arm64/gunyah 恢复成独立的 DDK 外部模块（`:kbuild`）。

r84 的 `kernel module gh_arm_drv.ko was not found`：清单要求 gh_arm_drv.ko
在 vendor_ramdisk 里，但 in-tree 的 `make modules` 不遍历 `arch/`，所以从不构建。

bazel 侧它是独立 ddk_module（modules.bzl: out=gh_arm_drv.ko,
srcs = gh_arm.c irq.c reset.c reset.h），所以这里：
  1. 恢复 arch/arm64/gunyah/Kbuild 的完整组成（gh_arm.o irq.o reset.o）；
  2. 清掉上一轮误加的 drivers/gunyah 复制品与 drivers/Makefile 的 obj-m；
  3. 在 device bp 的 external_modules 里加 "sm8750/arch/arm64/gunyah:kbuild"；
  4. 删除该目录里的陈旧编译产物（.o/.ko/.mod/.cmd），避免干扰 M= 构建。
"""
import os
import pathlib
import re
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

V = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
BP = pathlib.Path(_Y700_WORK + "/aosp/device/lenovo/elden/Android.bp")

# 1) Kbuild：完整组成 + vendor include
kbuild = V / "arch/arm64/gunyah/Kbuild"
kbuild.write_text(
    "# sm8750-gunyah-fix: modules.bzl builds gh_arm_drv.ko from\n"
    "#   arch/arm64/gunyah/{gh_arm,irq,reset}.c  (config CONFIG_GH_ARM64_DRV)\n"
    "# This tree is built as a DDK external module (`:kbuild`), so it needs the\n"
    "# vendor header roots on the include path.\n"
    "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
    "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux\n"
    "\n"
    "obj-m += gh_arm_drv.o\n"
    "gh_arm_drv-objs := gh_arm.o irq.o reset.o\n"
)
print("Kbuild written:", kbuild)

# 2) 清掉 drivers/gunyah 复制品与 drivers/Makefile 里的 obj-m
drv = V / "drivers/gunyah"
if drv.is_dir():
    for p in sorted(drv.rglob("*"), reverse=True):
        p.unlink() if p.is_file() else p.rmdir()
    drv.rmdir()
    print("removed drivers/gunyah")

mk = V / "drivers/Makefile"
body = mk.read_text(errors="ignore")
new = body.replace("\n# sm8750-gunyah-fix\nobj-m += gunyah/\n", "\n")
if new != body:
    mk.write_text(new)
    print("drivers/Makefile cleaned")

# 3) device bp：加 :kbuild 条目
bp = BP.read_text(errors="ignore")
entry = '            "sm8750/arch/arm64/gunyah:kbuild",\n'
if "sm8750/arch/arm64/gunyah:kbuild" in bp:
    print("Android.bp already has gunyah entry")
else:
    anchor = re.search(r'( *)"sm8750:modules",\n', bp)
    if not anchor:
        print("ANCHOR MISSING in Android.bp")
        sys.exit(1)
    bp = bp.replace(anchor.group(0), anchor.group(0) + entry, 1)
    BP.write_text(bp)
    print("Android.bp: added gunyah :kbuild entry")

# 4) 清陈旧产物
removed = 0
for pat in ("*.o", "*.ko", "*.mod", "*.mod.c", "*.cmd", ".??*.cmd"):
    for p in (V / "arch/arm64/gunyah").glob(pat):
        if p.is_file():
            p.unlink()
            removed += 1
print("stale artifacts removed:", removed)
