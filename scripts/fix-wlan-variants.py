#!/usr/bin/env python3
"""为 wlan 的 4 个芯片变体建立独立 kbuild 包装目录。

背景：设备 `modules.load.vendor_dlkm` 需要
  qca_cld3_peach.ko / qca_cld3_peach_v2.ko / qca_cld3_kiwi_v2.ko / qca_cld3_wcn7750.ko
bazel 侧每个变体是独立的 ddk_module（`wlan_qcacld3_modules.bzl`），用不同的
`MODNAME`/`WLAN_VARIANT` 编译同一套源码。kbuild 一条 `:kbuild` 只能产出一个模块，
所以为每个变体建一个薄包装目录，各自 include 真正的 `qcacld-3.0/Kbuild`。

已核实：
  - `qcacld-3.0/Kbuild:5327` → `obj-$(CONFIG_QCA_CLD_WLAN) += $(MODNAME).o`
  - `WLAN_ROOT` 可被外部覆盖（默认 `drivers/staging/qcacld-3.0`）
  - 变体目录是 `wlan/variants/<variant>/`，所以 `WLAN_ROOT` 是 `$(src)/../../qcacld-3.0`
    （两层 `..` 回到 `wlan/`；写成三层会跳到 `opensource/qcacld-3.0`，那里不存在）
  - QCA_CLD_WLAN_PROFILE 的名字是 `sun_gki_<variant>`（`_`→`-`），
    与 `configs/sun_gki_{peach,peach-v2,kiwi-v2,wcn7750}_defconfig` 一一对应
  - qcacld 用 `os_if`（在源码内），**不**依赖缺失的 `wlan/os/linux`
"""
import os
import pathlib
import re
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

KP = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12")
W = KP / "vendor/lenovo/sm8750-modules/qcom/opensource/wlan"
BP = pathlib.Path(_Y700_WORK + "/aosp/device/lenovo/elden/Android.bp")

# (variant, 模块名, defconfig profile)
VARIANTS = [
    ("peach",    "qca_cld3_peach",    "sun_gki_peach"),
    ("peach_v2", "qca_cld3_peach_v2", "sun_gki_peach-v2"),
    ("kiwi_v2",  "qca_cld3_kiwi_v2",  "sun_gki_kiwi-v2"),
    ("wcn7750",  "qca_cld3_wcn7750",  "sun_gki_wcn7750"),
]

made = []
for variant, modname, profile in VARIANTS:
    d = W / "variants" / variant
    d.mkdir(parents=True, exist_ok=True)
    kb = d / "Kbuild"
    kb.write_text(
        "# sm8750-wlan-variant: 变体 %s 的 kbuild 包装（bazel 侧是独立 ddk_module）\n"
        "#\n"
        "# 路径必须 abspath：kbuild/make 会尝试重建 include 的目标，含 `..` 段的\n"
        "# 路径在拼接 objtree 前缀后变成 '../../../../../..//home/...'，make 认不出，\n"
        "# 于是报 No rule to make target '.../qcacld-3.0/configs/sun_gki_%s_defconfig'。\n"
        "#\n"
        "# WLAN_PLATFORM_ROOT 也必须给：qcacld-3.0/Kbuild 开头就 include\n"
        "# $(WLAN_PLATFORM_ROOT)/{cnss2,cnss_genl,cnss_prealloc,cnss_utils,icnss2}/\n"
        "# sun_gki_defconfig，而上游只在 wlan/platform/Makefile 与 Android.mk 里定义它。\n"
        "# 本变体由 device bp 的 external_modules 直接调用，不经过 wlan/Kbuild。\n"
        "#\n"
        "# 两个 BUILD_TOP 变量必须清空：qcacld-3.0/Kbuild:34-45 在 KERNEL_BUILD=n\n"
        "# 且 BUILD_TOP 非空时会做\n"
        "#   override WLAN_ROOT := $(BUILD_TOP_REL)/$(WLAN_ROOT)\n"
        "# 它假定 WLAN_ROOT 是相对 BUILD_TOP 的路径；本包装给的是绝对路径，\n"
        "# 于是被拼成 '../../../../../../../../..//home/...' —— 从 kernel_build 目录\n"
        "# 回溯到 aosp 的 9 级 '..' 再跟一个绝对路径，make 找不到该目标，报\n"
        "#   No rule to make target '.../configs/sun_gki_<variant>_defconfig'\n"
        "# envsetup.sh 会 export ANDROID_BUILD_TOP，所以这个分支在 soong 里必然命中。\n"
        "# 这两个变量在 wlan 树中只被那段 override 使用，清空是安全的；\n"
        "# unexport 保证 kbuild 递归的 sub-make 里也不会再出现。\n"
        "ANDROID_BUILD_TOP :=\n"
        "LINUX_BUILD_TOP :=\n"
        "unexport ANDROID_BUILD_TOP\n"
        "unexport LINUX_BUILD_TOP\n"
        "MODNAME := %s\n"
        "DEVNAME := %s\n"
        "WLAN_VARIANT := %s\n"
        "override CONFIG_QCA_CLD_WLAN := m\n"
        "# IPA 头路径：defconfig 里 CONFIG_IPA_OFFLOAD=y 会让 cmn/qdf/linux/src/\n"
        "# i_qdf_types.h:66 去 #include <linux/ipa.h>，而该头只在\n"
        "# qcacld-3.0/Kbuild:3843-3844 的 ccflags-$(CONFIG_IPA_OUT_OF_TREE) 里才被\n"
        "# 加入 include 路径（DATA_IPA_INC -> opensource/dataipa/drivers/platform/msm/include）。\n"
        "# defconfig 只设了 CONFIG_CNSS_OUT_OF_TREE=y，没设 IPA 这一项，于是头找不到。\n"
        "# 全 wlan 树中该变量仅被那两行引用，补上无其它副作用。\n"
        "override CONFIG_IPA_OUT_OF_TREE := y\n"
        "CONFIG_QCA_CLD_WLAN_PROFILE := %s\n"
        "WLAN_ROOT := $(abspath $(src)/../../qcacld-3.0)\n"
        "export WLAN_PLATFORM_ROOT := $(abspath $(src)/../../platform)\n"
        "ccflags-y += -idirafter $(abspath $(srctree)/../vendor/lenovo/sm8750/include)\n"
        "ccflags-y += -idirafter $(abspath $(srctree)/../vendor/lenovo/sm8750/include/linux)\n"
        "# 把 vendored 代码的既有告警降回告警，不让 -Werror 中断构建。\n"
        "#\n"
        "# 本树 CONFIG_WERROR=y，而 qcacld/core 是从 git 同步来的第三方代码，\n"
        "# 其中的告警（如 wlan_hdd_cfg80211.c:14847 的 -Wenum-compare、\n"
        "# wlan_hdd_hostapd.c:1112 的 -Wmissing-prototypes）在 clang 22 下会被\n"
        "# 升成错误。逐个改 vendored 源码不可维护 —— 1120 个 .c 会一个接一个\n"
        "# 冒出新告警。这里只关闭「告警转错误」，告警本身仍会打印，便于发现问题。\n"
        "ccflags-y += -Wno-error\n"
        "\n"
        "include $(WLAN_ROOT)/Kbuild\n"
        % (variant, variant, modname, variant, variant, profile)
    )
    made.append(str(kb.relative_to(KP)))

# device bp：为每个变体加 :kbuild 条目（插在 wlan:kbuild 之后）
bp = BP.read_text(errors="ignore")
added = []
anchor = '            "sm8750-modules/qcom/opensource/wlan:kbuild",\n'
for variant, _modname, _profile in VARIANTS:
    entry = '            "sm8750-modules/qcom/opensource/wlan/variants/%s:kbuild",\n' % variant
    if entry in bp:
        continue
    if anchor in bp:
        bp = bp.replace(anchor, anchor + entry, 1)
        anchor = anchor + entry
        added.append(variant)
BP.write_text(bp)

print("wrapper Kbuild 写入:", len(made))
for m in made:
    print("  ", m)
print("device bp 新增条目:", added or "(无，已存在)")
