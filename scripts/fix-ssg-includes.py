#!/usr/bin/env python3
"""securemsm-kernel 的 kbuild 适配（两个独立幂等补丁）。

## 补丁 1：include 根 + vendor include 前置

上游 DDK 构建时，这些路径由 DDK Makefile 的 KBUILD_OPTIONS / SOCINCLUDE 传入；
kbuild 路径（M= 或 in-tree modules）不经过 DDK Makefile，于是：

  <linux/IClientEnv.h>   -> 缺 -I$(SSG_MODULE_ROOT)/include
  <linux/hdcp_qseecom.h> -> 缺 -I$(srctree)/../vendor/lenovo/sm8750/include
  <linux/msm_ion.h>      -> 缺 .../sm8750/include/uapi

另外必须**前置** vendor 的 include：common/include 里有一份 GKI 版
<linux/firmware/qcom/qcom_scm.h>（169 行），会先于 vendor 版（397 行）命中，
导致 tz_log.c 里的 qcom_scm_request_encrypted_log / register_qsee_log_buf /
get_tz_log_feat_id 等全部 "undeclared function"。

## 补丁 2：关掉 LA 专用测试模块组

上游：

    ifneq ($(CONFIG_DISABLE_TEST_MODULES), y)
        obj-m += tornado_mod.o seccam_test_driver.o ...
    endif

这个开关只由 DDK Makefile 传入，**没有 Kconfig 定义**，所以 kbuild 路径下恒为空，
整组测试模块都会被编出来。而它们：
  - 不在 device 的 modules.load / modules.include.* 清单里，编了也不安装；
  - seccam_test_driver 依赖 smmu-proxy/linux/qti-smmu-proxy.h，编译器看不到该目录。
把它们与 DDK 构建对齐关掉即可。

用法: python3 fix-ssg-includes.py <securemsm-kernel 目录>
"""

import os
import sys

MARK = "sm8750-ssg-includes-v4"
OLD_MARKS = ["sm8750-ssg-includes:", "sm8750-ssg-includes-v2:", "sm8750-ssg-includes-v3:"]

ANCHOR = "SSG_MODULE_ROOT := $(src)"
GATE = "CONFIG_DISABLE_TEST_MODULES := y"

# 写入的标记行之后，注释/追加行里通常出现的 token —— 用于界定旧块边界
_SSG_TOKENS = ("SSG_VENDOR", "LINUXINCLUDE", "SSG_MODULE_ROOT",
               "CONFIG_DISABLE_TEST_MODULES")

# 旧版删除逻辑不完整时留下的残骸（v2 的 LINUXINCLUDE += 四行，注意无尾斜杠）
LEFTOVER = ("\n                $(LINUXINCLUDE)\n"
            "LINUXINCLUDE += -I$(SSG_MODULE_ROOT)/include \\\n"
            "                -I$(SSG_MODULE_ROOT)/include/linux \\\n"
            "                -I$(SSG_MODULE_ROOT)/include/uapi\n")

BLOCK = """# {mark}: DDK Makefile 才会传这些 include 根，kbuild 路径下必须自己补，
# 否则 <linux/IClientEnv.h>（模块 include/）与 <linux/hdcp_qseecom.h>、
# <linux/msm_ion.h>（vendor include/ 与 uapi/）全部 not found。
SSG_VENDOR := $(srctree)/../vendor/lenovo/sm8750
# vendor include 必须前置：common/include 里的 <linux/firmware/qcom/qcom_scm.h>
# 是瘦身后的 GKI 版，缺 qcom_scm_request_encrypted_log 等 vendor 扩展声明。
LINUXINCLUDE := -I$(SSG_VENDOR)/include \\
                -I$(SSG_VENDOR)/include/linux \\
                -I$(SSG_VENDOR)/include/uapi \\
                $(LINUXINCLUDE)
LINUXINCLUDE += -I$(SSG_MODULE_ROOT)/include \\
                -I$(SSG_MODULE_ROOT)/include/linux \\
                -I$(SSG_MODULE_ROOT)/include/uapi
""".format(mark=MARK)

GATE_BLOCK = """# {mark}: CONFIG_DISABLE_TEST_MODULES 只由 DDK Makefile 传入、无 Kconfig 定义，
# kbuild 路径下恒为空，于是 LA 测试模块（tornado_mod / seccam_test_driver ...）
# 全被编出来。它们不在 modules.load 清单里、编了也不安装，且依赖只有在模块
# 子目录里才看得见的头文件。按 DDK 构建的语义显式关掉。
{gate}
""".format(mark=MARK, gate=GATE)


def drop_block(text, mark, verbose=True):
    """删掉以 '# <mark>' 开头的整块（mark 后的注释 + SSG 相关的续行）。

    逐行消费：从标记行开始，只要下一行是空行、注释，或含 SSG 相关 token
    就一起删；遇到其它行（如 `ifeq ($(TARGET_MACHINE), seraph)`）停止。
    """
    needle = "# %s" % mark
    if needle not in text:
        return text
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith(needle):
            j = i + 1
            while j < len(lines):
                ln = lines[j]
                if (ln.strip() == "" or ln.lstrip().startswith("#")
                        or any(tok in ln for tok in _SSG_TOKENS)):
                    j += 1
                else:
                    break
            if verbose:
                print("REMOVED block %s (%d lines)" % (mark, j - i))
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def main():
    root = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    path = os.path.join(root, "Kbuild")
    if not os.path.isfile(path):
        sys.exit("找不到 %s" % path)
    text = open(path, errors="ignore").read()

    # 1) 清掉历次旧块
    for old in OLD_MARKS:
        text = drop_block(text, old)

    # 2) 清掉旧逻辑留下的残骸
    if LEFTOVER in text:
        text = text.replace(LEFTOVER, "\n")
        print("REMOVED v2 leftover")

    # 3) 装本版补丁
    if MARK in text:
        print("ALREADY %s" % MARK)
    else:
        if ANCHOR not in text:
            sys.exit("缺少锚点 %r，请先跑 fix-vendor-root-vars.py" % ANCHOR)
        text = text.replace(ANCHOR, ANCHOR + "\n\n" + BLOCK + "\n" + GATE_BLOCK, 1)
        print("PATCHED %s" % MARK)

    # 4) 压掉多余空行（3 个以上连续空行 -> 2 个）
    while "\n\n\n\n" in text:
        text = text.replace("\n\n\n\n", "\n\n\n")

    open(path, "w", errors="ignore").write(text)
    print("gate: %s" % ("closed" if GATE in text else "OPEN (需检查)"))


if __name__ == "__main__":
    main()
