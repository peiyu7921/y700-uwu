#!/usr/bin/env python3
"""给 synx-kernel 的 synx.c 补 <linux/of.h>。

synx.c 的 `synx_dt_get_array()` 用了 of_find_node_by_path /
of_property_count_elems_of_size / of_property_read_u32_array / of_node_put，
但文件里没有任何 <linux/of.h>，也没有经过其它头文件间接引入，于是整组报：

    error: call to undeclared function 'of_find_node_by_path'; ISO C99 ...
    error: incompatible integer to pointer conversion assigning to
           'struct device_node *'

同目录的 ipclite.c 是 include 了 <linux/of.h> 的，说明这是 synx.c 自己的疏漏
（上游靠别的头文件偶然带入，GKI 树里那层关系不存在）。

用法: python3 fix-synx-of-header.py <synx-kernel 目录>
"""

import os
import sys

MARK = "sm8750-synx-of"
INCLUDE = "#include <linux/of.h>"
# 插在 notifier.h 之后；synx.c 的 include 顺序本身不是字母序，就地即可
ANCHOR = "#include <linux/notifier.h>"

NOTE = """// {mark}: synx_dt_get_array() 用 of_find_node_by_path / of_property_* /
// of_node_put，但上游依赖别处间接带入 <linux/of.h>；GKI 树里没有那层
// 关系，于是全部报 undeclared function。同目录 ipclite.c 是直接 include 的。
""".format(mark=MARK)


def main():
    root = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    path = os.path.join(root, "msm/synx/synx.c")
    if not os.path.isfile(path):
        sys.exit("找不到 %s" % path)
    text = open(path, errors="ignore").read()

    if MARK in text:
        print("ALREADY %s" % path)
        return
    if INCLUDE in text:
        print("ALREADY (of.h 已在) %s" % path)
        return

    if ANCHOR in text:
        text = text.replace(ANCHOR, ANCHOR + "\n" + NOTE + INCLUDE, 1)
        how = "after notifier.h"
    else:
        # 退化：放在第一处 #include 之后
        idx = text.find("#include")
        if idx < 0:
            sys.exit("synx.c 里没有 #include，请人工检查")
        end = text.index("\n", idx) + 1
        text = text[:end] + NOTE + INCLUDE + "\n" + text[end:]
        how = "after first include"

    open(path, "w", errors="ignore").write(text)
    print("PATCHED %s (%s)" % (path, how))


if __name__ == "__main__":
    main()
