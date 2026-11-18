#!/usr/bin/env python3
"""修 spu-kernel 的 include 路径（kbuild 布局适配）。

上游 Kbuild 写的是 bazel 布局下的相对路径：

    LINUXINCLUDE += -I$(srctree)/../../vendor/qcom/opensource/spu-kernel/include/uapi

kbuild 路径下 srctree=common，该相对路径解析到不存在的目录，于是：

  <linux/spcom.h>                -> 实际在 $(SPU_ROOT)/include/uapi/linux/
  <linux/remoteproc/qcom_spss.h> -> 实际在 vendor/lenovo/sm8750/include/

用法: python3 fix-spu-includes.py <spu-kernel 目录>
"""

import os
import sys

MARK = "sm8750-spu-inc-fix"

OLD = "LINUXINCLUDE += -I$(srctree)/../../vendor/qcom/opensource/spu-kernel/include/uapi"

NEW = """# {mark}: 上游写的是 bazel 布局下的相对路径
# -I$(srctree)/../../vendor/qcom/opensource/spu-kernel/include/uapi，
# kbuild 下（srctree=common）解析到不存在的目录，于是
# <linux/spcom.h>（模块 include/uapi/linux/）与
# <linux/remoteproc/qcom_spss.h>（vendor include/linux/remoteproc/）都找不到。
LINUXINCLUDE += -I$(SPU_ROOT)/include/uapi \\
                -I$(srctree)/../vendor/lenovo/sm8750/include \\
                -I$(srctree)/../vendor/lenovo/sm8750/include/linux
""".format(mark=MARK)

# 旧块删除时，哪些行算"本补丁的一部分"
CONTINUE_TOKENS = ("-I$(SPU_ROOT)/include/uapi", "LINUXINCLUDE",
                   "vendor/lenovo/sm8750/include")


def strip_prev(text):
    """删掉历次补丁写入的整块（标记注释 + 紧随的 LINUXINCLUDE 续行）。"""
    needle = "# %s" % MARK
    if needle not in text:
        return text, False
    lines = text.split("\n")
    out, i, removed = [], 0, False
    while i < len(lines):
        if lines[i].startswith(needle):
            j = i
            # 标记行本身及其后的注释/空行/含目标 -I 的行
            while j < len(lines) and (
                    lines[j].startswith(needle)
                    or lines[j].lstrip().startswith("#")
                    or lines[j].strip() == ""
                    or any(t in lines[j] for t in CONTINUE_TOKENS)):
                j += 1
            removed = True
            i = j
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out), removed


def main():
    root = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    path = os.path.join(root, "Kbuild")
    if not os.path.isfile(path):
        sys.exit("找不到 %s" % path)
    text = open(path, errors="ignore").read()

    text, removed = strip_prev(text)
    if removed:
        print("REMOVED previous block")

    if OLD in text:
        text = text.replace(OLD, NEW, 1)
        print("PATCHED from upstream line")
    elif "$(SPU_ROOT)/include/uapi" in text and \
            "$(srctree)/../vendor/lenovo/sm8750/include" in text:
        # 上游行已不在、但三个根都在：说明已应用过（或树已含本修法）
        if MARK not in text:
            text = text.replace(
                "LINUXINCLUDE += -I$(SPU_ROOT)/include/uapi",
                NEW + "\nLINUXINCLUDE += -I$(SPU_ROOT)/include/uapi", 1)
            print("REINSERTED block")
        else:
            print("ALREADY OK")
    else:
        # 干净树：找到 SPU_ROOT 定义，把块插在它后面第一个空行之后
        anchor = "SPU_ROOT := $(src)"
        if anchor not in text:
            sys.exit("找不到锚点 %r，请人工检查 %s" % (anchor, path))
        text = text.replace(anchor, anchor + "\n\n" + NEW, 1)
        print("INSERTED after anchor")

    open(path, "w", errors="ignore").write(text)
    print("roots: %d" % len([1 for t in ("$(SPU_ROOT)/include/uapi",
                                         "$(srctree)/../vendor/lenovo/sm8750/include",
                                         "vendor/lenovo/sm8750/include/linux")
                             if t in text]))


if __name__ == "__main__":
    main()
