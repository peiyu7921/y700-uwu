#!/usr/bin/env python3
"""把 u-zpy 上验证过的内核树修法幂等地落到一棵全新的 AOSP 树上。

用法:
    python3 scripts/kernel-tree-fixes.py <AOSP 根目录>

约定目录（与 uwuAOSP 的 kernel_platform 布局一致）:
    <AOSP>/kernel/platform/kernel-6.12/common                  GKI 公共树
    <AOSP>/kernel/platform/kernel-6.12/vendor/lenovo/sm8750     vendor 内核树（in-tree 驱动）
    <AOSP>/kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules  DDK 外部模块
    <AOSP>/device/lenovo/elden                                 设备配置

每条修法都带 marker，重复执行不会叠加。全部修法都在 u-zpy 上逐条验证过，
根因见 AGENTS.md「已确认的关键修法」。
"""

import os
import re
import subprocess
import sys

MARK = {
    "kconfig": "sm8750-configfix",
    "datarmnet": "sm8750-datarmnet-fix",
    "dsp": "sm8750-dsp-fix",
    "eva": "sm8750-eva-fix",
    "socqcom": "sm8750-socqcom-fix",
    "mpam": "sm8750-mpam-fix",
    "audio": "sm8750-audio-fix",
    "camera": "sm8750-camera-fix",
}

OPENSOURCE = "sm8750-modules/qcom/opensource"


def read(path):
    with open(path, "r", errors="ignore") as fh:
        return fh.read()


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", errors="ignore") as fh:
        fh.write(text)


def prepend_once(path, marker, block):
    """在文件最前面插入 block（已存在则跳过）。"""
    if not os.path.exists(path):
        return False
    text = read(path)
    if marker in text:
        return False
    write(path, block + text)
    return True


# --------------------------------------------------------------- 1. vendor Kconfig
def fix_kconfig_ext(kp):
    """让 vendor Kconfig 可见，否则 olddefconfig 会静默丢掉全部 vendor CONFIG_*。

    GKI 的 common/Kconfig 末尾是 source "$(KCONFIG_EXT_PREFIX)Kconfig.ext"，
    只有配上 KCONFIG_EXT_PREFIX（device bp 的 make_flags）才有内容。

    除了 vendor 内核树（Kconfig.msm），DDK 模块树也自带 Kconfig（graphics-kernel、
    datarmnet 等 33 个），内核 Kconfig 从不 source 它们；缺了它们
    CONFIG_QCOM_KGSL_IDLE_TIMEOUT 之类的符号根本不存在，模块代码就会走进错误的
    #ifdef 分支（实测 graphics-kernel 出现 kgsl_pools / CONFIG_QCOM_KGSL_IDLE_TIMEOUT
    未定义）。
    """
    path = os.path.join(kp, "vendor/lenovo/sm8750/Kconfig.ext")
    lines = [
        "# %s: expose the vendor Kconfig tree to the GKI config so that vendor" % MARK["kconfig"],
        "# symbols (CONFIG_ARCH_SUN, CONFIG_EVA_*, CONFIG_CORESIGHT_*, ...) become known",
        "# symbols instead of being silently dropped by olddefconfig.",
        "# The DDK modules tree carries its own Kconfigs (graphics-kernel, datarmnet, ...),",
        "# which the kernel Kconfig never sources; without them CONFIG_QCOM_KGSL_* do not",
        "# exist and module code takes the wrong #ifdef branch.",
        'source "$(KCONFIG_EXT_PREFIX)Kconfig.msm"',
        "",
    ]
    mods_root = os.path.join(kp, "vendor/lenovo/sm8750-modules")
    kcs = []
    for dirpath, _dirnames, filenames in os.walk(mods_root):
        if "Kconfig" in filenames:
            kcs.append(os.path.relpath(os.path.join(dirpath, "Kconfig"), os.path.join(kp, "vendor/lenovo")))
    for rel in sorted(kcs):
        # Kconfig.ext 位于 vendor/lenovo/sm8750/ 下，所以模块树条目必须用
        # $(KCONFIG_EXT_PREFIX) 前缀（device bp 的 make_flags 给的是 <abs>/vendor/lenovo/sm8750/）
        # 再 ../ 回到 vendor/lenovo/。
        # 写成相对 "../vendor/lenovo/..." 只在 srctree=common 时成立；vendor 树自己作
        # srctree（in-tree `path:modules`）时会错位成 .../vendor/lenovo/vendor/lenovo/...，
        # 报 Kconfig.ext:N: can't open file "../vendor/lenovo/sm8750-modules/..."（13500t 实测）。
        lines.append('source "$(KCONFIG_EXT_PREFIX)../%s"' % rel.replace(os.sep, "/"))
    body = "\n".join(lines) + "\n"
    if os.path.exists(path) and read(path) == body:
        return False
    write(path, body)
    return True


# --------------------------------------------------- 2. datarmnet / datarmnet-ext
def fix_datarmnet(kp):
    """datarmnet 系列只有 bazel 入口，缺顶层 Makefile；同时要一次性下发 include。"""
    base = os.path.join(kp, "vendor/lenovo/sm8750-modules/qcom/opensource")
    changed = []
    ext_dirs = ["aps", "mem", "perf", "shs", "wlan"]

    def subdir_block(extra):
        lines = [
            "# %s: shared include paths for the kbuild-based build" % MARK["datarmnet"],
            "OPE := $(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource",
        ]
        for d in ext_dirs:
            lines.append("subdir-ccflags-y += -I$(OPE)/datarmnet-ext/%s/include" % d)
            lines.append("subdir-ccflags-y += -I$(OPE)/datarmnet-ext/%s/include/uapi" % d)
            lines.append("subdir-ccflags-y += -I$(OPE)/datarmnet-ext/%s/include/uapi/linux" % d)
        lines.append("subdir-ccflags-y += -I$(OPE)/datarmnet/core")
        lines.append("subdir-ccflags-y += -I$(OPE)/dataipa/drivers/platform/msm/include")
        lines.append("subdir-ccflags-y += -I$(OPE)/dataipa/drivers/platform/msm/include/uapi")
        lines.append("")
        return "\n".join(lines + extra) + "\n"

    targets = {
        "datarmnet/Makefile": ["obj-y += core/"],
        "datarmnet-ext/Makefile": ["obj-y += aps/ mem/ offload/ perf/ perf_tether/ sch/"],
    }
    for rel, objs in targets.items():
        path = os.path.join(base, rel)
        text = subdir_block(objs)
        if os.path.exists(path) and MARK["datarmnet"] in read(path):
            continue
        write(path, text)
        changed.append(rel)

    # data-kernel 同样只有 bazel 入口，缺顶层 Makefile
    # （`No rule to make target .../data-kernel/Makefile` 会直接中止构建）。
    # 但它两个子模块在 elden 上都是门控关闭的：
    #   drivers/emac-dwc-eqos  仅 TARGET_BOARD_AUTO=true（Kconfig 符号 EMAC_DWC_EQOS 未定义）
    #   drivers/smem-mailbox   仅 sun/canoe/hamoa/chora/malabar（CONFIG_FEATURE_SMEM_MAILBOX=n）
    # 所以给空入口即可 —— 绝不能写 `obj-y += ./`，那会把当前目录当子目录无限递归。
    dk = os.path.join(base, "data-kernel/Makefile")
    if not os.path.exists(dk) or MARK["datarmnet"] + "-dk" not in read(dk):
        write(
            dk,
            "# %s-dk: only bazel entrypoints here; elden needs none of the subdrivers.\n"
            "# Both are gated off for elden: emac-dwc-eqos needs TARGET_BOARD_AUTO\n"
            "# (CONFIG_EMAC_DWC_EQOS unset) and smem-mailbox needs\n"
            "# sun/canoe/hamoa/chora/malabar (CONFIG_FEATURE_SMEM_MAILBOX=n).\n"
            "# An empty entry keeps kbuild from failing with 'No rule to make target\n"
            "# .../data-kernel/Makefile'; `obj-y += ./` here would recurse forever.\n"
            % MARK["datarmnet"]
        )
        changed.append("data-kernel/Makefile")

    # datarmnet/core 自身：ipa.h / msm_ipa.h / rmnet_mem.h / trace 路径
    core = os.path.join(base, "datarmnet/core/Kbuild")
    block = (
        "# %s: include paths + trace header path for the kbuild-based build\n"
        "# vendor root: <linux/ipc_logging.h>, <soc/qcom/...> live in sm8750/include\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet/core\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/include\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/include/uapi\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet-ext/mem\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet-ext/mem/include\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet-ext/mem/include/uapi\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet-ext/mem/include/uapi/linux\n"
        "# TRACE_INCLUDE_PATH is resolved relative to common/include/trace/ by define_trace.h\n"
        "ccflags-y += -DRMNET_TRACE_INCLUDE_PATH=../../../vendor/lenovo/sm8750-modules/qcom/opensource/datarmnet/core\n"
        % MARK["datarmnet"]
    )
    if prepend_once(core, MARK["datarmnet"], block):
        changed.append("datarmnet/core/Kbuild")
    return changed


# ------------------------------------------------------------------- 3. dsp-kernel
def fix_dsp(kp):
    """frpc-trusted-adsprpc: vendor include + 显式 trusted + trace 路径。

    elden 的 defconfig 里没有 CONFIG_ARCH_SUN（历史上靠 Android.mk 门控），
    走 DDK 的 Kbuild 路径时那段 ifeq 会失效，trusted 变体被静默编成非 trusted。
    """
    path = os.path.join(kp, "vendor/lenovo/sm8750-modules/qcom/opensource/dsp-kernel/Kbuild")
    block = (
        "# %s: vendor include path for the kbuild-based build\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include\n"
        "# %s: elden has no CONFIG_ARCH_SUN, so select the trusted variant explicitly\n"
        "ccflags-y += -DCONFIG_QCOM_FASTRPC_TRUSTED=1\n"
        "# %s: trace header path relative to common/include/trace\n"
        "ccflags-y += -DDSP_TRACE_INCLUDE_PATH=../../../vendor/lenovo/sm8750-modules/qcom/opensource/dsp-kernel/dsp\n"
        % (MARK["dsp"], MARK["dsp"], MARK["dsp"])
    )
    return prepend_once(path, MARK["dsp"], block)


# -------------------------------------------------------------- 3b. audio-kernel
def fix_audio(kp):
    """asoc/codecs/Kbuild 里的 `obj-y += ./` 是自引用：kbuild 把当前目录当子目录
    无限递归展开成 ./././…，最后在 bolero/.modules.order.cmd 上
    `missing separator` 报错。顶层 Kbuild 已经列了 asoc/codecs/，删掉自引用即可。
    """
    path = os.path.join(
        kp,
        "vendor/lenovo/sm8750-modules/qcom/opensource/audio-kernel/asoc/codecs/Kbuild",
    )
    if not os.path.exists(path):
        return []
    text = read(path)
    if MARK["audio"] in text:
        return []
    commented = (
        "# %s: `obj-y += ./` recurses into itself (./././...) and dies on\n"
        "# bolero/.modules.order.cmd with 'missing separator\x2e' The top-level Kbuild\n"
        "# already lists asoc/codecs/, so the self-reference is dropped.\n"
        "# obj-y += ./\n" % MARK["audio"]
    )
    new, n = re.subn(
        r"(?m)^[ \t]*obj-y[ \t]*\+=[ \t]*\./[ \t]*\n", commented, text
    )
    if not n:
        return []
    write(path, new)
    return ["audio-kernel/asoc/codecs/Kbuild"]


# ---------------------------------------------------------------- 3c. camera-kernel
def fix_camera(kp):
    """camera-kernel 的 CAMERA_KERNEL_ROOT 把 pwd、srctree、src、M 四段拼起来，
    在 M= 用绝对路径时被拼成 $O//abs/common//abs/vendor/...，kbuild 找不到
    config/camera_default.mk（`kernel_build//home/...` 那种路径）。$(src) 就是
    模块目录本身，直接用它。
    """
    path = os.path.join(
        kp,
        "vendor/lenovo/sm8750-modules/qcom/opensource/camera-kernel/Kbuild",
    )
    if not os.path.exists(path):
        return []
    text = read(path)
    if MARK["camera"] in text:
        return []
    new, n = re.subn(
        r"(?m)^CAMERA_KERNEL_ROOT[ \t]*=.*$",
        "# %s: pwd+srctree+src+M concatenated into an absolute path under M= builds\n"
        "CAMERA_KERNEL_ROOT=$(src)" % MARK["camera"],
        text,
        count=1,
    )
    if not n:
        return []
    write(path, new)
    return ["camera-kernel/Kbuild"]


# -------------------------------------------------------------------- 4. eva-kernel
def fix_eva(kp):
    """eva-kernel 需要 vendor include + 自己的 include/uapi/eva（media/msm_eva_private.h）。

    另外 synx_api.h 只出现在 CONFIG_ARCH_* 分支里，且那些行写的是
    -I$(EVA_ROOT)/../synx-kernel/...，而 EVA_ROOT 只由 DDK Makefile 的
    KBUILD_OPTIONS 传入 —— kbuild 路径拿不到，展开成空。elden 也不匹配那些
    CONFIG_ARCH_*，所以必须无条件补上真实路径。
    """
    base = os.path.join(kp, "vendor/lenovo/sm8750-modules/qcom/opensource/eva-kernel")
    block = (
        "# %s: include paths for the kbuild-based build\n"
        "OEVA := $(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/eva-kernel\n"
        "subdir-ccflags-y += -I$(OEVA)/include/uapi/eva\n"
        "subdir-ccflags-y += -I$(OEVA)/include/uapi\n"
        "subdir-ccflags-y += -I$(OEVA)/include\n"
        "subdir-ccflags-y += -I$(OEVA)/msm\n"
        "subdir-ccflags-y += -I$(OEVA)/msm/eva\n"
        "subdir-ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include\n" % MARK["eva"]
    )
    synx = (
        "# %s-synx: EVA_ROOT only comes from the DDK Makefile, which the kbuild path\n"
        "# does not use, so -I$(EVA_ROOT)/../synx-kernel/... expands to nothing. The\n"
        "# CONFIG_ARCH_* branches that carry it also never match elden.\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/synx-kernel/msm/synx\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/synx-kernel/include/uapi/synx/media\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750-modules/qcom/opensource/dsp-kernel/include\n"
        % MARK["eva"]
    )
    changed = []
    for rel in ("Kbuild", "msm/Kbuild"):
        if prepend_once(os.path.join(base, rel), MARK["eva"], block):
            changed.append("eva-kernel/" + rel)
    msm = os.path.join(base, "msm/Kbuild")
    if os.path.exists(msm):
        text = read(msm)
        if MARK["eva"] + "-synx" not in text:
            lines = text.split("\n")
            for i, ln in enumerate(lines):
                if ln.startswith("ccflags-y"):
                    lines.insert(i, synx)
                    break
            else:
                lines.insert(0, synx)
            write(msm, "\n".join(lines))
            if "eva-kernel/msm/Kbuild" not in changed:
                changed.append("eva-kernel/msm/Kbuild")
    return changed


# ------------------------------------------------------- 5. vendor 树（in-tree 驱动）
def fix_ccflags_override(kp):
    """vendor Kbuild 里写 `ccflags-y :=` 会把 kbuild 已经累积的 vendor include 全部
    丢掉，camera-kernel 等模块因此找不到 <linux/mem-buf.h>、<soc/qcom/minidump.h>，
    报 `ccflags-y :=` 覆盖补丁。修法：紧跟在第一条 ccflags-y 之后补回 vendor include。
    """
    root = os.path.join(kp, "vendor/lenovo/sm8750-modules")
    line = "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include"
    changed = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != ".git"]
        for name in filenames:
            if name != "Kbuild":
                continue
            path = os.path.join(dirpath, name)
            rel = os.path.relpath(path, kp)
            text = read(path)
            if not re.search(r"ccflags-y[ \t]*:=", text):
                continue
            if "vendor/lenovo/sm8750/include" in text:
                continue
            out, done = [], False
            for ln in text.split("\n"):
                out.append(ln)
                if ln.rstrip().endswith("\\"):
                    continue
                if re.match(r"ccflags-y[ \t]*[:+]?=", ln) and not done:
                    out.append(line)
                    done = True
            if not done:
                out.insert(0, line)
            write(path, "\n".join(out))
            changed.append(rel)
    return changed


def fix_vendor_tree(kp):
    """vendor/lenovo/sm8750 这棵树从没被 kbuild 走过，有多处只给 bazel 写的 bug。"""
    v = os.path.join(kp, "vendor/lenovo/sm8750")
    changed = []

    # (a) vendor 头文件树布局是 include/ 与 include/linux/ 两套：
    #     <soc/qcom/qcom_sdei.h> 落在 include/linux/soc/qcom/ 下。
    #     只加 *_include/linux_* 与跨树 vendor 根，绝不能对"已经是 -I 的同一个
    #     include/ 目录"再补 -idirafter —— 实测会让 clang 把该目录当 system 目录，
    #     改变 <linux/types.h> 的解析，kasan-checks.h 直接报 unknown type name 'bool'。
    vendorinc = (
        "# sm8750-vendorinc-fix: vendor headers live under include/ and include/linux/\n"
        "# Only the *_/include/linux_* root and the cross-tree vendor roots: adding\n"
        "# -idirafter for a dir that is ALREADY a -I dir (same include/ root) makes clang\n"
        "# treat it as a system dir and changes <linux/types.h> resolution\n"
        "# (empirical: unknown type name 'bool' in kasan-checks.h).\n"
        "subdir-ccflags-y += -idirafter $(abs_srctree)/include/linux\n"
        "subdir-ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
        "subdir-ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux\n"
    )
    for rel in ("drivers/Makefile", "net/Makefile"):
        if prepend_once(os.path.join(v, rel), "sm8750-vendorinc-fix", vendorinc):
            changed.append(rel)

    # (b) adsp_sleepmon.c 的 qcom_common.h 在 drivers/remoteproc
    soc = os.path.join(v, "drivers/soc/qcom/Makefile")
    block = (
        "# %s: qcom_common.h lives in drivers/remoteproc, vendor headers in include/\n"
        "ccflags-y += -I$(abs_srctree)/drivers/remoteproc\n"
        "ccflags-y += -I$(srctree)/drivers/remoteproc\n"
        "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/drivers/remoteproc\n"
        % MARK["socqcom"]
    )
    if prepend_once(soc, MARK["socqcom"], block):
        changed.append("drivers/soc/qcom/Makefile")

    # (c) mpam 自引用：mpam-objs 里不能出现 mpam.o 自己（Circular -> ld 失败）
    mpam = os.path.join(v, "drivers/soc/qcom/mpam/Makefile")
    if os.path.exists(mpam):
        text = read(mpam)
        if MARK["mpam"] not in text:
            text = text.replace(
                "mpam-objs += mpam.o mpam_rpmsg.o",
                "# %s: mpam.o cannot list itself in mpam-objs (circular, ld fails)\n"
                "mpam-objs += mpam_rpmsg.o" % MARK["mpam"],
            )
            write(mpam, text)
            changed.append("drivers/soc/qcom/mpam/Makefile")

    # (c) common_sources.bzl 里 bazel 现场生成的源文件，kbuild 路径需要先物化
    changed += materialize_generated_sources(v, kp)
    return changed


def materialize_generated_sources(v, kp):
    """按 common_sources.bzl 的 genrule/copy_file 把生成物先造出来。

    例：drivers/regulator/qti_fixed_regulator.c = fixed.c + fixed.diff
        （diff 里全是 #ifdef QTI_FIXED_REGULATOR 的 QTI 增强，CFLAGS 会打开）
    """
    bzl = os.path.join(v, "common_sources.bzl")
    if not os.path.exists(bzl):
        return []
    common = os.path.join(kp, "common")
    text = read(bzl)
    changed = []

    for m in re.finditer(r"native\.genrule\((.*?)\n    \)", text, re.S):
        block = m.group(1)
        src = re.search(r'"//common:([^"]+)"', block)
        diff = re.search(r':([^"]+\.diff)"', block)
        out = re.search(r'outs = \["([^"]+)"\]', block)
        if not (src and diff and out):
            continue
        s, d, o = src.group(1), diff.group(1), out.group(1)
        outp = os.path.join(v, o)
        if os.path.exists(outp):
            continue
        os.makedirs(os.path.dirname(outp), exist_ok=True)
        subprocess.run(
            ["patch", "--follow-symlinks", "-o", outp, "-i", os.path.join(v, d), os.path.join(common, s)],
            capture_output=True,
            text=True,
        )
        if os.path.exists(outp):
            changed.append(o)

    for m in re.finditer(r"copy_file\((.*?)\n    \)", text, re.S):
        block = m.group(1)
        src = re.search(r'src = "([^"]+)"', block)
        out = re.search(r'out = "([^"]+)"', block)
        if not (src and out):
            continue
        s, o = src.group(1), out.group(1)
        if s.startswith("//common:"):
            continue  # 由 genrule 分支处理
        if os.path.exists(os.path.join(v, o)) or not os.path.exists(os.path.join(v, s)):
            continue
        os.makedirs(os.path.dirname(os.path.join(v, o)), exist_ok=True)
        write(os.path.join(v, o), read(os.path.join(v, s)))
        changed.append(o)

    return changed


# ------------------------------------------------------------ 6. 设备 bp / 清理
def fix_kconfig_dedup(kp):
    """去掉 vendor 树内部 Kconfig 与 Kconfig.msm 的重复 source。

    srctree=common 时两者指向不同文件（各 GKI / vendor），没问题；
    srctree=vendor（`path:modules` 的 in-tree 构建）时指向同一文件，
    `choice` 会被解析两遍，报
      "choice value has a prompt outside its choice group" /
      "choice member must have a prompt"。
    符号不会丢：Kconfig.msm 已用绝对前缀 source 过同一份文件。
    """
    v = os.path.join(kp, "vendor/lenovo/sm8750")
    mark = "# sm8750-kconfig-dedup: also sourced via Kconfig.msm"
    msm = os.path.join(v, "Kconfig.msm")
    if not os.path.exists(msm):
        return []
    text = read(msm)
    targets = re.findall(r'source "\$\(KCONFIG_EXT_PREFIX\)([^"]+)"', text)

    changed = []
    for rel in targets:
        # 父级与祖父级的 Kconfig 都可能 source 同一子目录
        for depth in (1, 2):
            parent = os.path.dirname(rel)
            for _ in range(depth - 1):
                parent = os.path.dirname(parent)
            if parent in ("", "."):
                continue
            kfile = os.path.join(v, parent, "Kconfig")
            if not os.path.exists(kfile):
                continue
            body = read(kfile)
            if mark in body:
                continue
            out = []
            hit = False
            for line in body.splitlines():
                stripped = line.strip()
                m = re.match(r'^source\s+"([^"]+)"\s*$', stripped)
                if m and not m.group(1).startswith("$("):
                    src = m.group(1)
                    resolved = src if src.startswith(parent) else os.path.join(parent, src)
                    if os.path.normpath(resolved) == os.path.normpath(rel):
                        out.append(mark)
                        out.append("# " + line)
                        hit = True
                        continue
                out.append(line)
            if hit:
                write(kfile, "\n".join(out) + "\n")
                changed.append(os.path.join(parent, "Kconfig"))
    return changed


def fix_wlan_variants(kp, aosp):
    """为 wlan 的 4 个芯片变体建立 kbuild 包装目录。

    设备需要 qca_cld3_{peach,peach_v2,kiwi_v2,wcn7750}.ko；bazel 侧每个变体是
    独立的 ddk_module（不同 MODNAME/WLAN_VARIANT 编译同一套源码）。kbuild 一条
    `:kbuild` 只能产出一个模块，所以每个变体一个薄包装，各自 include 真正的
    `qcacld-3.0/Kbuild`。qcacld 用源码内的 `os_if`，不依赖缺失的 `wlan/os/linux`。
    """
    w = os.path.join(kp, "vendor/lenovo/sm8750-modules/qcom/opensource/wlan")
    if not os.path.isdir(os.path.join(w, "qcacld-3.0")):
        return []

    variants = [
        ("peach", "qca_cld3_peach", "sun_gki_peach"),
        ("peach_v2", "qca_cld3_peach_v2", "sun_gki_peach-v2"),
        ("kiwi_v2", "qca_cld3_kiwi_v2", "sun_gki_kiwi-v2"),
        ("wcn7750", "qca_cld3_wcn7750", "sun_gki_wcn7750"),
    ]

    changed = []
    for variant, modname, profile in variants:
        d = os.path.join(w, "variants", variant)
        os.makedirs(d, exist_ok=True)
        kb = os.path.join(d, "Kbuild")
        want = (
            "# sm8750-wlan-variant: 变体 %s 的 kbuild 包装（bazel 侧是独立 ddk_module）\n"
            "MODNAME := %s\nDEVNAME := %s\nWLAN_VARIANT := %s\n"
            "CONFIG_QCA_CLD_WLAN := y\nCONFIG_QCA_CLD_WLAN_PROFILE := %s\n"
            "WLAN_ROOT := $(src)/../../../qcacld-3.0\n"
            "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include\n"
            "ccflags-y += -idirafter $(srctree)/../vendor/lenovo/sm8750/include/linux\n"
            "\ninclude $(WLAN_ROOT)/Kbuild\n"
            % (variant, modname, variant, variant, profile)
        )
        if not os.path.exists(kb) or read(kb) != want:
            write(kb, want)
            changed.append("wlan/variants/%s/Kbuild" % variant)

    # device bp：为每个变体加 :kbuild 条目
    bp = os.path.join(aosp, "device/lenovo/elden/Android.bp")
    if os.path.exists(bp):
        text = read(bp)
        anchor = '            "sm8750-modules/qcom/opensource/wlan:kbuild",\n'
        for variant, _modname, _profile in variants:
            entry = '            "sm8750-modules/qcom/opensource/wlan/variants/%s:kbuild",\n' % variant
            if entry in text:
                continue
            if anchor in text:
                text = text.replace(anchor, anchor + entry, 1)
                anchor = anchor + entry
                changed.append("external_modules += wlan/variants/%s" % variant)
        write(bp, text)
    return changed


def fix_kconfig_help_marker(kp):
    """把老式 `---help---` 改成 `help`。

    Linux 6.12 的 kconfig 只认 `help`；vendor 树（datarmnet-ext 等）里残留的
    `---help---` 会让内核 .config 生成这一步直接失败：

        .. /datarmnet-ext/aps/Kconfig:8: syntax error
        .. /datarmnet-ext/aps/Kconfig:8: unknown statement "---help---"

    → kernel_build/.config FAILED → otapackage 一步都跑不了。
    u-zpy 上这 8 处是手工修过的，换机器复现时极易漏掉（13500t 实测踩到）。
    """
    import re as _re
    fixed = []
    for root in ("vendor/lenovo/sm8750", "vendor/lenovo/sm8750-modules"):
        base = os.path.join(kp, root)
        if not os.path.isdir(base):
            continue
        for dp, dn, fs in os.walk(base):
            dn[:] = [d for d in dn if d != ".git"]
            for f in fs:
                if f != "Kconfig":
                    continue
                p = os.path.join(dp, f)
                s = read(p)
                if "---help---" not in s:
                    continue
                new = _re.sub(r"(?m)^([ \t]*)---help---[ \t]*$", r"\1help", s)
                if new != s:
                    write(p, new)
                    fixed.append(os.path.relpath(p, kp))
    return fixed


def fix_device_bp(aosp):
    """make_flags 与 overrides。"""
    path = os.path.join(aosp, "device/lenovo/elden/Android.bp")
    if not os.path.exists(path):
        return []
    text = read(path)
    changed = []

    if "KBUILD_MODPOST_WARN" not in text:
        old = '    make_flags: [\n        "DEPMOD=true",'
        if old in text:
            text = text.replace(old, old + '\n        "KBUILD_MODPOST_WARN=1",', 1)
            changed.append("KBUILD_MODPOST_WARN=1")

    if "KCONFIG_EXT_PREFIX" not in text:
        old = '        "KBUILD_MODPOST_WARN=1",\n'
        if old in text:
            # 必须用绝对路径：vendor 树自身作 srctree（`path:modules` 的 in-tree 构建）时，
            # 相对前缀会错位，报 can't open file "../vendor/lenovo/sm8750-modules/..."。
            prefix = os.path.join(kp, "vendor/lenovo/sm8750") + "/"
            text = text.replace(old, old + '        "KCONFIG_EXT_PREFIX=%s",\n' % prefix, 1)
            changed.append("KCONFIG_EXT_PREFIX (absolute)")

    # gh_arm_drv.ko 在 arch/arm64/gunyah，不在 in-tree `make modules` 的遍历集合里，
    # 必须作为独立外部模块（`:kbuild`）构建，否则 install 清单校验报
    # "kernel module gh_arm_drv.ko was not found"。
    if "sm8750/arch/arm64/gunyah:kbuild" not in text:
        anchor = '            "sm8750:modules",\n'
        if anchor in text:
            text = text.replace(anchor, anchor + '            "sm8750/arch/arm64/gunyah:kbuild",\n', 1)
            changed.append("external_modules += gunyah:kbuild")

    # pKVM SMMUv2/3 nesting dispatcher：Kconfig default m，但 CONFIG_ARM_SMMU_V3_PKVM 未开、
    # 模块也不在 install/load 清单；它的 pkvm/hyp.lds 规则还需要 pKVM hyp 构建。
    if "QCOM_SMMU_V2_V3_DISPATCHER" not in text:
        anchor = '            "CONFIG_ARM_SMMU_SELFTEST=n",\n'
        if anchor in text:
            text = text.replace(
                anchor,
                anchor + '            "CONFIG_QCOM_SMMU_V2_V3_DISPATCHER=n",\n',
                1,
            )
            changed.append("CONFIG_QCOM_SMMU_V2_V3_DISPATCHER=n")

    write(path, text)
    return changed


def clean_stale_artifacts(kp):
    """源码树里混入的编译产物会制造假增量状态，每次构建前清掉。"""
    roots = [
        os.path.join(kp, "vendor/lenovo/sm8750"),
        os.path.join(kp, "vendor/lenovo/sm8750-modules"),
    ]
    pats = ("*.cmd", "*.o", "*.mod", "modules.order")
    removed = 0
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dp, _dn, fs in os.walk(root):
            for f in fs:
                if f.endswith((".cmd", ".o", ".mod")) or f == "modules.order":
                    try:
                        os.remove(os.path.join(dp, f))
                        removed += 1
                    except OSError:
                        pass
    return removed


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    flags = {a for a in sys.argv[1:] if a.startswith("--")}
    if len(args) != 1:
        sys.exit("用法: kernel-tree-fixes.py <AOSP 根目录> [--no-clean]")
    aosp = os.path.abspath(args[0])
    kp = os.path.join(aosp, "kernel/platform/kernel-6.12")
    if not os.path.isdir(os.path.join(kp, "vendor/lenovo/sm8750")):
        sys.exit("找不到 %s/vendor/lenovo/sm8750" % kp)

    steps = [
        ("vendor Kconfig.ext", lambda: fix_kconfig_ext(kp)),
        ("Kconfig 去重 (Kconfig.msm vs 树内 source)", lambda: fix_kconfig_dedup(kp)),
        ("datarmnet 系列", lambda: fix_datarmnet(kp)),
        ("dsp-kernel", lambda: fix_dsp(kp)),
        ("audio-kernel 自引用", lambda: fix_audio(kp)),
        ("camera-kernel 路径拼接", lambda: fix_camera(kp)),
        ("ccflags-y := 覆盖补 vendor include", lambda: fix_ccflags_override(kp)),
        ("eva-kernel", lambda: fix_eva(kp)),
        ("wlan 4 芯片变体", lambda: fix_wlan_variants(kp, aosp)),
        ("vendor 树驱动 + 生成源", lambda: fix_vendor_tree(kp)),
        ("Kconfig 老式 ---help--- → help", lambda: fix_kconfig_help_marker(kp)),
        ("device/lenovo/elden/Android.bp", lambda: fix_device_bp(aosp)),
    ]
    for name, fn in steps:
        result = fn()
        if isinstance(result, bool):
            result = ["applied"] if result else []
        print("[%s] %s" % ("patched" if result else "ok", name))
        for item in result or []:
            print("    - %s" % item)

    if "--no-clean" in flags:
        print("[clean] 跳过（--no-clean）")
    else:
        removed = clean_stale_artifacts(kp)
        print("[clean] 清除陈旧编译产物 %d 个" % removed)


if __name__ == "__main__":
    main()
