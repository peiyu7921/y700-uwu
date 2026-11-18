#!/usr/bin/env python3
"""恢复 CONFIG_GENDWARFKSYMS=y，让 CONFIG_RUST（进而 CONFIG_ASHMEM）可以被启用。

## 现象

OTA 打包最后一步 VINTF 校验：

    No compatible kernel requirement found (kernel FCM version = 202404).
    For kernel requirements at matrix level 202404, Kernel config errors:
        Missing config CONFIG_ASHMEM

## 原因链

1. `device/lenovo/elden/vintf/manifest_sun.xml` 声明 target-level="202404"，
   而 `kernel/configs/b/android-6.12/android-base.config:20` 要求 `CONFIG_ASHMEM=y`
2. 6.12 的 ashmem 是 Rust 实现（`drivers/staging/android/ashmem{,_range,_shrinker,_toggle}.rs`
   共 1781 行），Kconfig 硬依赖：
       config ASHMEM
           depends on SHMEM && RUST
3. `CONFIG_RUST`（init/Kconfig:2018）的依赖里有一条：
       depends on !MODVERSIONS || GENDWARFKSYMS
   当前 `.config` 是 `CONFIG_MODVERSIONS=y` + `# CONFIG_GENDWARFKSYMS is not set`，
   于是 `!MODVERSIONS || GENDWARFKSYMS` = `false || false` = false，RUST 永远不可见，
   ASHMEM 被静默丢弃（`.config` 里连 `# CONFIG_ASHMEM is not set` 都没有）
4. 上游 `gki_defconfig:118-119` 本来是 MODVERSIONS=y + GENDWARFKSYMS=y 共存，
   是 device bp 的 overrides 里那行 `"CONFIG_GENDWARFKSYMS=n"` 把它关掉的。
   GENDWARFKSYMS 自身的依赖（DEBUG_INFO=y、!DEBUG_INFO_REDUCED、
   !DEBUG_INFO_SPLIT、!LTO）在当前 .config 里全部满足。

## 修法

把 device bp 的 `"CONFIG_GENDWARFKSYMS=n"` 改为 `"CONFIG_GENDWARFKSYMS=y"`。

为什么不是别的做法：
  - 只装 bindgen 不够：RUST_IS_AVAILABLE 只是 RUST 的依赖之一，
    `!MODVERSIONS || GENDWARFKSYMS` 那条仍然否决。
  - 关掉 MODVERSIONS：vendor 模块与 GKI 的符号校验会失去保护，
    而且 gki_defconfig 上游就是要求 MODVERSIONS=y。
  - 改 android-base.config 删掉 ASHMEM 要求：只是骗过 VINTF 检查，
    内核实际没有 ashmem，运行时真用到就崩。

副作用：MODVERSIONS 的 choice 从 GENKSYMS 切到 GENDWARFKSYMS，
所有模块的符号版本改用 DWARF 计算，需重编全部 .ko。
`scripts/gendwarfksyms` 是 hostprogs-always-y，kbuild 会自行构建
（已验证可在本机编译：需要 libdw-dev / libelf-dev，均已装好）。

用法: python3 fix-gendwarfksyms-rust.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

BP = pathlib.Path(_Y700_WORK + "/aosp/device/lenovo/elden/Android.bp")

OLD = '            "CONFIG_GENDWARFKSYMS=n",\n'
NEW = (
    '            // sm8750-ashmem-rust: 上游 gki_defconfig:119 是 GENDWARFKSYMS=y，\n'
    '            // 这里原本覆盖成 n，导致 CONFIG_RUST 的\n'
    '            //   depends on !MODVERSIONS || GENDWARFKSYMS\n'
    '            // 恒为假（当前 MODVERSIONS=y），于是 RUST 不可见，\n'
    '            // 而 6.12 的 ASHMEM 是 Rust 实现（depends on SHMEM && RUST），\n'
    '            // 被静默丢弃 -> FCM 202404 的 kernel config 校验报\n'
    '            //   Missing config CONFIG_ASHMEM\n'
    '            // GENDWARFKSYMS 自身依赖（DEBUG_INFO=y、!DEBUG_INFO_REDUCED、\n'
    '            // !DEBUG_INFO_SPLIT、!LTO）当前全部满足。详见\n'
    '            // scripts/fix-gendwarfksyms-rust.py。\n'
    '            "CONFIG_GENDWARFKSYMS=y",\n'
)

body = BP.read_text(errors="ignore")

if "sm8750-ashmem-rust" in body:
    print("ALREADY patched: %s" % BP)
    sys.exit(0)

if OLD not in body:
    sys.exit("未找到 '%s'，Android.bp 结构可能已变，请人工检查" % OLD.strip())

BP.write_text(body.replace(OLD, NEW, 1))
print("patched: %s" % BP)
for i, line in enumerate(BP.read_text(errors="ignore").splitlines(), 1):
    if "GENDWARFKSYMS" in line:
        print("  %d: %s" % (i, line.strip()))
