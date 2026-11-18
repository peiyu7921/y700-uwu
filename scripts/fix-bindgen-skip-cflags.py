#!/usr/bin/env python3
"""剔除 bindgen 的 libclang（LLVM 20）不认识的 clang-22 告警开关。

## 现象

    *** libclang (used by the Rust bindings generator 'bindgen')
    *** version does not match Clang's. This may be a problem.
    ***   libclang version: 20.0.0
    ***   Clang version:    22.0.2

    Unable to generate bindings: clang diagnosed error:
    error: unknown warning option '-Wno-default-const-init-unsafe' [-Wunknown-warning-option]
    error: unknown warning option '-Wno-unterminated-string-initialization'; did you mean
           '-Wno-nonportable-vector-initialization'? [-Wunknown-warning-option]
    make[3]: *** [.../rust/Makefile:336: rust/bindings/bindings_generated.rs] Error 1

## 原因

`scripts/fix-bindgen-libclang.py` 把 bindgen 的 libclang 换成 LLVM 20（因为 LLVM 22
会让 bindgen 生成 263 个空壳结构体），内核 C 编译仍用 clang 22。
`scripts/Makefile.extrawarn` 里

    KBUILD_CFLAGS += $(call cc-disable-warning, default-const-init-unsafe)
    KBUILD_CFLAGS += $(call cc-disable-warning, unterminated-string-initialization)

的 `cc-disable-warning` 是按**编译器 clang 22** 探测的，于是顺利展开成
`-Wno-default-const-init-unsafe` / `-Wno-unterminated-string-initialization`
进入 `c_flags`。bindgen 拿这串 flags 喂 libclang 20，后者不认识这两个选项；
而 `KBUILD_CFLAGS` 带 `-Werror`，告警变成错误，bindgen 直接放弃生成。

## 为什么补丁必须打在 `bindgen_c_flags_final`

`rust/Makefile` 里这段是两条分支：

    ifdef CONFIG_CC_IS_CLANG
    bindgen_c_flags = $(c_flags)          # 直接透传，不 filter
    else
    bindgen_skip_c_flags := ...
    bindgen_c_flags = $(filter-out $(bindgen_skip_c_flags), $(c_flags)) ...
    endif

本树 `CONFIG_CC_IS_CLANG=y`，走的是**第一条**——`bindgen_skip_c_flags` 那条
（GCC 专用）根本不执行。所以往 skip 列表里加项对本树无效，第一次就是这么踩空的。
两条分支的汇聚点是：

    bindgen_c_flags_final = $(bindgen_c_flags_lto) -fno-builtin -D__BINDGEN__

在这里 `filter-out` 才拦得住。`filter-out` 按词精确匹配、幂等。

## 附带清理

早期版本把跳过项加进了 GCC 分支的 `bindgen_skip_c_flags`（对本树无效）。
本脚本会把它一并移除，避免留下误导性的改动。

用法: python3 fix-bindgen-skip-cflags.py
"""
import os
import pathlib
import re
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

COMMON = pathlib.Path(_Y700_WORK + "/aosp/kernel/platform/kernel-6.12/common")
# vendor 树有独立的一份 rust/Makefile（同 inode 检查确认是两份文件，不是软链）：
# vendor 的 in-tree 构建（`sm8750:modules`）用 vendor 自己这份，只改 common 那份
# 会漏掉它，报错点仍是 vendor/lenovo/sm8750/rust/Makefile:356。
VENDOR = pathlib.Path(
    _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/vendor/lenovo/sm8750")
TARGETS = [COMMON / "rust/Makefile", VENDOR / "rust/Makefile"]

MARK = "sm8750-bindgen-skip-cflags"
FLAGS = "-Wno-default-const-init-unsafe -Wno-unterminated-string-initialization"

# 汇聚点：两条分支都最终落到这一行
OLD_FINAL = "bindgen_c_flags_final = $(bindgen_c_flags_lto) -fno-builtin -D__BINDGEN__\n"
NEW_FINAL = ((
    "# %s: 在汇聚点剔除两项。Clang 分支（CONFIG_CC_IS_CLANG=y，本树即是）的\n"
    "#     bindgen_c_flags = $(c_flags)\n"
    "# 是直接透传、不经过 bindgen_skip_c_flags 的，所以跳过项只在 else(GCC)\n"
    "# 分支里加，对本树无效。这两项由 scripts/Makefile.extrawarn 的\n"
    "# cc-disable-warning 按 clang 22 探测展开，而 bindgen 的 libclang 是\n"
    "# LLVM 20（见 scripts/fix-bindgen-libclang.py），不认识它们；KBUILD_CFLAGS\n"
    "# 带 -Werror，告警于是变成错误、bindgen 放弃生成。两者只是告警开关，\n"
    "# 剔掉不影响生成的绑定内容。filter-out 按词精确匹配且幂等。\n"
    "bindgen_c_flags_final = $(filter-out " + FLAGS + ","
    "$(bindgen_c_flags_lto)) -fno-builtin -D__BINDGEN__\n"
) % MARK)

old_skip_tail = (
    "\t--param=% --param asan-% -fno-isolate-erroneous-paths-dereference \\\n"
    "\t-Wno-default-const-init-unsafe -Wno-unterminated-string-initialization\n"
)
OLD_COMMENT = (
    "# sm8750-bindgen-skip-cflags: bindgen 的 libclang 是 LLVM 20（见 scripts/fix-bindgen-libclang.py），\n"
    "# 而 C 编译用 clang 22。下面两项由 scripts/Makefile.extrawarn 里\n"
    "# cc-disable-warning 按 clang 22 探测后展开，libclang 20 不认识；KBUILD_CFLAGS\n"
    "# 带 -Werror，于是告警变错误、bindgen 放弃生成。它们只是告警开关，剔掉不影响\n"
    "# 绑定内容。详见 scripts/fix-bindgen-skip-cflags.py。\n"
)

for MK in TARGETS:
    if not MK.is_file():
        print("跳过（不存在）: %s" % MK)
        continue
    body = MK.read_text(errors="ignore")
    before = body
    changed = False

    # 1) 主补丁：汇聚点加 filter-out
    if "bindgen_c_flags_final = $(filter-out " in body:
        print("[%s] 主补丁已存在" % MK.parent.parent.name)
    elif OLD_FINAL in body:
        body = body.replace(OLD_FINAL, NEW_FINAL, 1)
        changed = True
        print("[%s] 已打主补丁（bindgen_c_flags_final）" % MK.parent.parent.name)
    else:
        print("[%s] 未找到 bindgen_c_flags_final 原文，跳过" % MK.parent.parent.name)
        continue

    # 2) 清理旧版误加在 GCC 分支 skip 列表里的项
    if old_skip_tail in body:
        body = body.replace(
            old_skip_tail,
            "\t--param=% --param asan-% -fno-isolate-erroneous-paths-dereference\n", 1)
        changed = True
        print("[%s] 已移除旧版加在 GCC 分支 skip 列表里的项" % MK.parent.parent.name)

    # 3) 旧注释块也清掉，避免误导
    if OLD_COMMENT in body:
        body = body.replace(OLD_COMMENT, "", 1)
        changed = True

    if changed and body != before:
        MK.write_text(body)
        print("written: %s" % MK)
    else:
        print("[%s] 无改动" % MK.parent.parent.name)

print("--- 结果 ---")
for MK in TARGETS:
    if not MK.is_file():
        continue
    text = MK.read_text(errors="ignore")
    i = text.index("bindgen_c_flags_final")
    print("### %s" % MK)
    print(text[i:i + 200])
