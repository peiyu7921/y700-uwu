#!/usr/bin/env python3
"""把 common 内核树里 vendor( sm8750 ) **缺失** 的文件补齐。

背景（13500t 换机复现连踩 6 轮才定位）：
  kernel_build/.config 这一步（olddefconfig）是用 **vendor 树作 srctree** 跑的
  （vendor/lenovo/sm8750/Makefile:712 → __sub-make），但那棵树只是 DDK 模块树，
  并不完整：
    - 顶层 Kconfig 缺失（连 git 里都没有：`git cat-file -e HEAD:Kconfig` 为空）
    - kernel/ 只有 8 项，缺 kernel/Kconfig.freezer
    - 缺 fs/ ipc/ security/ usr/ virt/ block/ crypto/ io_uring/ rust/ samples/ 等 16 个顶层项
    - 缺 scripts/basic/fixdep.c、scripts/kconfig/conf.c 等 61 个构建脚本
  于是 olddefconfig 会逐层报：
      can't find file Kconfig
      Kconfig:12: can't open file "kernel/Kconfig.freezer"
      Kconfig:16: can't open file "mm/Kconfig"
      make[3]: *** No rule to make target 'scripts/basic/fixdep.c'
  这些在 u-zpy 上都不缺，因为那棵树是"git checkout + 大量手工补齐"的产物
  （它的 12191 处未提交改动里就包含这些），从未脚本化 —— 所以换机器必然缺。

修法：从 common 树按 **只补缺** 的语义补齐（不覆盖 vendor 自己的定制，例如
Kconfig.msm、arch/arm64 下的 vendor 分支、drivers/soc/qcom/Kconfig 等）。

反面教训（别这么做）：
  - 整树 `cp -a common/. vendor/` 或 rsync 覆盖 → 把 GKI 定制盖到 vendor 上，
    olddefconfig 反而失败（scripts/kconfig 被覆盖后报 `Error 1`）。
  - 手工往 `out/soong/.intermediates/**/headers/usr/` 放头 → soong 每次重建会覆盖。

幂等：只补充缺失文件，已存在的跳过。
用法：python3 fix-vendor-tree-complete.py [AOSP 根目录]
"""
import os
import filecmp
import pathlib
import shutil
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else _Y700_WORK + "/aosp")
COMMON = AOSP / "kernel/platform/kernel-6.12/common"
VENDOR = AOSP / "kernel/platform/kernel-6.12/vendor/lenovo/sm8750"

if not COMMON.is_dir() or not VENDOR.is_dir():
    print("  skip: common 或 vendor 树不存在")
    sys.exit(0)

copied = 0
probes = ["Kconfig", "Kbuild", "mm/Kconfig", "kernel/Kconfig.freezer",
          "scripts/basic/fixdep.c", "scripts/kconfig/conf.c"]

for src in COMMON.rglob("*"):
    if not src.is_file():
        continue
    # 跳过 git 元数据与构建输出
    parts = src.relative_to(COMMON).parts
    if ".git" in parts or parts[0] == "out":
        continue
    dst = VENDOR.joinpath(*parts)
    if dst.exists():
        continue
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copy2(str(src), str(dst))
        copied += 1
    except Exception:
        pass

total = sum(1 for p in VENDOR.rglob("*") if p.is_file())
print("  补齐文件: %d   vendor 现有文件: %d" % (copied, total))
for probe in probes:
    print("    %-32s %s" % (probe, "ok" if (VENDOR / probe).is_file() else "缺"))
