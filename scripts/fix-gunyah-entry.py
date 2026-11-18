#!/usr/bin/env python3
"""把 gunyah 入口收敛到 Makefile 一处，并去掉对 CONFIG_GH_ARM64_DRV 的依赖。

r85 的 `kernel module gh_arm_drv.ko was not found`：
  - `arch/arm64/gunyah/` 里同时有 `Makefile`（`obj-$(CONFIG_GH_ARM64_DRV)`）和我上一轮
    写的 `Kbuild`（`obj-m`），两者都定义入口时行为不确定；
  - 实测 `.config` 里根本没有 `CONFIG_GH_ARM64_DRV`（overrides 写了 `=m` 但被
    olddefconfig 丢掉），所以 Makefile 的 `obj-$(CONFIG_GH_ARM64_DRV)` 永远为空；
  - `arch/` 不在 in-tree `make modules` 的 `drivers/ fs/ net/` 遍历集合里，只能靠
    `external_modules` 的 `:kbuild` 条目构建。

因此：删掉多余的 Kbuild，让 Makefile 用无条件 `obj-m`（与 datarmnet / mmrm 等
已跑通的 `:kbuild` 模块同形），并补 vendor include。
"""
import os
import pathlib

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

V = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
G = V / "arch/arm64/gunyah"

# 1) 删掉我上一轮写的 Kbuild（与 Makefile 冲突）
kb = G / "Kbuild"
if kb.exists():
    kb.unlink()
    print("removed conflicting Kbuild")

# 2) Makefile：无条件 obj-m + vendor include
mk = G / "Makefile"
body = mk.read_text(errors="ignore")
if "sm8750-gunyah-fix" in body:
    print("Makefile already patched")
else:
    new = body.replace(
        "obj-$(CONFIG_GH_ARM64_DRV) += gh_arm_drv.o",
        "# sm8750-gunyah-fix: .config has no CONFIG_GH_ARM64_DRV (the override is\n"
        "# dropped by olddefconfig), so gate on nothing; modules.bzl always builds it.\n"
        "obj-m += gh_arm_drv.o",
        1,
    )
    if "idirafter" not in new:
        new = new.replace(
            "ccflags-y += -I$(src)",
            "ccflags-y += -I$(src)\n"
            "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
            "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux",
            1,
        )
    mk.write_text(new)
    print("Makefile patched")

print("--- Makefile 前 10 行 ---")
print("\n".join(mk.read_text(errors="ignore").splitlines()[:10]))
