#!/usr/bin/env python3
"""让 wlan 变体目录真正能解析源码：把空骨架子目录换成指向 qcacld-3.0 的软链。

## 现象

`CONFIG_QCA_CLD_WLAN` 改成 `override ... := m` 之后，wlan 终于进入真正的编译
（此前一直是「静默成功」），随即暴露出下一层问题：

    make[3]: *** No rule to make target
      '.../wlan/variants/peach/core/hdd/src/wlan_hdd_assoc.o', needed by ...

## 根因

`qcacld-3.0/Kbuild` 里的源码清单是**相对路径**：

    HDD_DIR     := core/hdd
    HDD_SRC_DIR := $(HDD_DIR)/src
    HDD_OBJS    := $(HDD_SRC_DIR)/wlan_hdd_assoc.o ...
    ...
    $(MODNAME)-y := $(OBJS)

在 `M=.../wlan/variants/peach` 模式下，`$(MODNAME)-y` 里的相对路径以**变体目录**
为基准解析，于是找 `variants/peach/core/hdd/src/wlan_hdd_assoc.o`。而实测：

    variants/peach/cmn         空实体目录（0 文件）
    variants/peach/components  空实体目录（0 文件）
    variants/peach/core        空实体目录（0 文件）
    variants/peach/os_if       空实体目录（0 文件）

真源码都在 `qcacld-3.0/` 下：

    qcacld-3.0/components  实体，559 文件
    qcacld-3.0/core        实体，625 文件
    qcacld-3.0/os_if       实体，75 文件
    qcacld-3.0/cmn         软链 -> ../qca-wifi-host-cmn（1304 文件）
    qcacld-3.0/.peach      软链 -> .            <- 上游的正解在这里

上游 `Android.mk:307` 是这么用的：

    LOCAL_SRC_DIR := .$(LOCAL_DEV_NAME)          # 例如 .peach
    KBUILD_OPTIONS := WLAN_ROOT=$(WLAN_BLD_DIR)/qcacld-3.0/$(LOCAL_SRC_DIR)

即上游把 `WLAN_ROOT` 指到 `qcacld-3.0/.peach`（软链回 `qcacld-3.0` 自身），
这样相对路径自然落在 `qcacld-3.0/` 下。而本树的变体包装目录是另起的
`wlan/variants/<v>/`，没有这层软链，于是相对路径落到了空骨架里。

## 修法

把 `variants/<v>/{cmn,components,core,os_if}` 换成指向
`qcacld-3.0/<同名>` 的相对软链。`qcacld-3.0/cmn` 本身是软链也没关系，
软链到软链由内核解析，`readlink -f` 已逐个验证过 4 个目标都有效。

只动这 4 个子目录，`variants/<v>/Kbuild`、`modules.order` 等文件保持原样。

## 注意

`wlan/variants/` 是 git 未跟踪目录（`git status` 显示 `?? qcom/opensource/wlan/variants/`），
所以软链不会被 git 覆盖；但也意味着**换机器/清理后需要重跑本脚本**，
它已幂等，重复执行只会在软链缺失时重建。

用法: python3 link-wlan-variant-sources.py
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

WLAN = pathlib.Path(
    _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/"
    "sm8750-modules/qcom/opensource/wlan")
QCACLD = WLAN / "qcacld-3.0"
VARIANTS = WLAN / "variants"

# 与 Kbuild 里相对路径前缀对应的四个目录
SUBDIRS = ["cmn", "components", "core", "os_if"]


def main():
    if not QCACLD.is_dir():
        sys.exit("qcacld-3.0 不存在: %s" % QCACLD)

    vdirs = sorted(p for p in VARIANTS.iterdir() if p.is_dir()) \
        if VARIANTS.is_dir() else []
    if not vdirs:
        sys.exit("没有任何变体目录")

    for vd in vdirs:
        made, kept = [], []
        for sub in SUBDIRS:
            target = QCACLD / sub
            if not target.exists():
                print("  [%s] 跳过 %-12s（qcacld-3.0/%s 不存在）"
                      % (vd.name, sub, sub))
                continue
            link = vd / sub
            # 链接位置是 wlan/variants/<v>/<sub>，往上两层即回到 wlan/，
            # 再进 qcacld-3.0/。写成三层会跳到 opensource/ 下（那里没有
            # qcacld-3.0），链接变成断链 —— 第一次就是这么写错的。
            want = pathlib.Path("../../qcacld-3.0") / sub

            if link.is_symlink():
                if pathlib.Path(link.readlink()) == want:
                    kept.append(sub)
                    continue
                link.unlink()
            elif link.is_dir():
                # 只在确认为空骨架时才删，避免误删真实内容
                ents = list(link.rglob("*"))
                files = [p for p in ents if p.is_file()]
                if files:
                    print("  [%s] 警告：%s 里有 %d 个文件，跳过不动"
                          % (vd.name, sub, len(files)))
                    continue
                import shutil
                shutil.rmtree(link)
            elif link.exists():
                print("  [%s] %s 不是目录，跳过" % (vd.name, sub))
                continue

            link.symlink_to(want)
            made.append(sub)

        print("[%s] 新建软链 %d 个 %s%s"
              % (vd.name, len(made), made,
                 "，已存在 %d 个" % len(kept) if kept else ""))

    print("--- 校验 ---")
    for vd in vdirs:
        for sub in SUBDIRS:
            link = vd / sub
            if not link.exists():
                print("  !! %s/%s 仍无效" % (vd.name, sub))
                continue
            probe = link / "hdd" / "src" if sub == "core" else None
            n = sum(1 for _ in link.rglob("*.c"))
            print("  %-22s -> %-40s %d 个 .c"
                  % ("%s/%s" % (vd.name, sub),
                     str(link.readlink()) if link.is_symlink() else "实体", n))


if __name__ == "__main__":
    main()
