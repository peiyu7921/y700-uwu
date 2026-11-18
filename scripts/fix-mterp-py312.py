#!/usr/bin/env python3
"""gen_mterp.py 用了只有 Python 3.12+ 才合法的 f-string 写法（PEP 701）。

art/runtime/interpreter/mterp/gen_mterp.py 第 109 行：

    print(f"{">>" if j == i else "  "}{n:6}: {c}", file=sys.stderr)

f-string 的表达式里用了与外层相同的双引号。PEP 701 之前（也就是 Python 3.11
及以下），f-string 内部不能复用外层引号，于是：

    SyntaxError: f-string: expecting '}'

Ubuntu 22.04 的系统 python3 是 3.10，所以
//art/runtime:libart_mterp.arm64ng / .x86_64ng 的 mterp 生成步骤直接失败
（siso 日志里是 out/host/linux-x86/bin/sbox … gen_mterp.py, line 109）。

修法：把表达式内的双引号换成单引号，语义完全不变，且所有 Python 版本都合法。
幂等：已修过则跳过。

用法：
    python3 fix-mterp-py312.py [AOSP 根目录]
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else _Y700_WORK + "/aosp")
P = AOSP / "art/runtime/interpreter/mterp/gen_mterp.py"

OLD = 'print(f"{">>" if j == i else "  "}{n:6}: {c}", file=sys.stderr)'
NEW = 'print(f"{\'>>\' if j == i else \'  \'}{n:6}: {c}", file=sys.stderr)'

if not P.is_file():
    print("  skip: %s 不存在" % P)
    sys.exit(0)

src = P.read_text()
if NEW in src:
    print("  ok(已修): %s" % P.name)
    sys.exit(0)
if OLD not in src:
    print("  WARN 没找到目标行，需人工确认: %s" % P)
    sys.exit(0)

P.write_text(src.replace(OLD, NEW, 1))
print("  已修 %s: f-string 内层改用单引号（兼容 python3.10）" % P.name)
