#!/usr/bin/env python3
"""把 scripts/ 里的 /home/zpy/y700-uwu 硬编码改成可用环境变量覆盖。

## 为什么需要

这些脚本是为服务器（zpy-13500t，工作区 `/home/zpy/y700-uwu`）写的，路径全是硬编码。
要在本机或其他机器上「从零重放修法」，必须能改根路径。

## 注入方式

**环境变量 + 默认值**，服务器行为完全不变：

    Y700_WORK   工作区根目录，默认 /home/zpy/y700-uwu
    Y700_AOSP   AOSP 树，   默认 $Y700_WORK/aosp

用法：

    # 服务器（不设变量，行为与以前一致）
    python3 fix-ota-radio-partitions.py

    # 本机/其他机器
    Y700_WORK=/mnt/d/projects/y700-uwu python3 fix-ota-radio-partitions.py

## 为什么每个脚本都自包含

本仓库的运行方式是「把脚本 scp/cat 到目标机 /tmp 再执行」，例如：

    ssh host "cat > /tmp/x.py" < scripts/x.py && ssh host "python3 /tmp/x.py"

脚本会被复制到 /tmp 独立运行，**拿不到同目录的公共模块**。
所以不能 `from paths import AOSP`，必须每个脚本内联两行解析代码。

## 改写规则

py：
    1. 确保有 `import os`
    2. 在 import 区之后插入
           _Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")
       并把出现的 `"/home/zpy/y700-uwu...` 改成 `_Y700_WORK + "/...`
       （单引号同理）
    3. 幂等：已含 `_Y700_WORK` 的跳过

sh：
    `WORK=/home/zpy/y700-uwu`      -> `WORK="${WORK:-/home/zpy/y700-uwu}"`
    `AOSP=/home/zpy/y700-uwu/aosp` -> `AOSP="${AOSP:-/home/zpy/y700-uwu/aosp}"`
    已经是 `${VAR:-...}` 形式的不动

用法：
    python3 parametrize-paths.py --dry-run     # 只报告将要改什么
    python3 parametrize-paths.py               # 落地
    python3 parametrize-paths.py --root DIR    # 改另一个 scripts 目录
"""
import pathlib
import re
import sys

DEFAULT_SCRIPTS = pathlib.Path(__file__).resolve().parent
HARDCODED = "/home/zpy/y700-uwu"
MARK = "_Y700_WORK"

# 在 import 区之后插入。（多行 import 之间插入会破坏语法，
# 所以统一插在「最后一个以 import/from 开头的顶层行」之后）
INJECT = (
    '\n'
    '# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，\n'
    '# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>\n'
    '{mark} = os.environ.get("Y700_WORK", "{hc}")\n'
).format(mark=MARK, hc=HARDCODED)


def inject_py(text):
    """返回 (新文本, 改了几处) 或 (None, 原因)。"""
    if MARK in text:
        return None, "已参数化"

    n = text.count('"%s' % HARDCODED) + text.count("'%s" % HARDCODED)
    if n == 0:
        return None, "无硬编码"

    # 1) 确保 import os
    if not re.search(r"^import os$", text, re.M):
        if re.search(r"^import ", text, re.M):
            text = re.sub(r"^import ", "import os\nimport ", text, count=1, flags=re.M)
        else:
            text = "import os\n" + text

    # 2) 先替换字面量，再插入定义行。
    #    顺序不能反：INJECT 自身含 "/home/zpy/y700-uwu" 字面量，
    #    先插入再替换会把默认值也改成自引用，得到
    #      _Y700_WORK = os.environ.get("Y700_WORK", _Y700_WORK + "/")
    #    这是本脚本第一版踩过的坑。
    text = text.replace('"%s' % HARDCODED, '%s + "/' % MARK)
    text = text.replace("'%s" % HARDCODED, "%s + '/" % MARK)

    # 3) 插入 _Y700_WORK 定义：放在「顶层」最后一个 import 行之后。
    #    必须只认列 0 起始的行，否则函数体内的 `import shutil` 会被选中，
    #    定义被插进函数中间 —— 本脚本第一版就是这么把
    #    link-wlan-variant-sources.py 改成 IndentationError 的。
    lines = text.splitlines(keepends=True)
    last_import = -1
    for i, ln in enumerate(lines):
        if ln[:1] in (" ", "\t") or not ln.strip():
            continue
        s = ln.strip()
        if s.startswith("import ") or (s.startswith("from ") and " import " in s):
            last_import = i
    if last_import < 0:
        return None, "找不到顶层 import 行"
    lines.insert(last_import + 1, INJECT)
    text = "".join(lines)
    return text, "%d 处" % n


SH_RULES = [
    (re.compile(r'^WORK=%s$' % re.escape(HARDCODED), re.M),
     'WORK="${WORK:-%s}"' % HARDCODED),
    (re.compile(r'^AOSP=%s/aosp$' % re.escape(HARDCODED), re.M),
     'AOSP="${AOSP:-%s/aosp}"' % HARDCODED),
    (re.compile(r'^DEV=%s/aosp/device/lenovo/elden$' % re.escape(HARDCODED), re.M),
     'DEV="${DEV:-%s/aosp/device/lenovo/elden}"' % HARDCODED),
]


def patch_sh(text):
    changed = 0
    for pat, repl in SH_RULES:
        text, n = pat.subn(repl, text)
        changed += n
    return text, changed


def main():
    dry = "--dry-run" in sys.argv
    root = DEFAULT_SCRIPTS
    if "--root" in sys.argv:
        root = pathlib.Path(sys.argv[sys.argv.index("--root") + 1])

    py_done = py_skip = 0
    sh_done = 0
    for p in sorted(root.glob("*.py")) + sorted(root.glob("*.sh")):
        if p.name == pathlib.Path(__file__).name:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError as e:
            print("读取失败 %s: %s" % (p.name, e))
            continue

        if p.suffix == ".py":
            new, info = inject_py(text)
            if new is None:
                if info != "无硬编码":
                    py_skip += 1
                continue
            if not dry:
                p.write_text(new)
            py_done += 1
            print("%-42s py  %s" % (p.name, info))
        else:
            new, n = patch_sh(text)
            if not n:
                continue
            if not dry:
                p.write_text(new)
            sh_done += 1
            print("%-42s sh  %d 处" % (p.name, n))

    print("---")
    print("py 改写 %d 个（跳过 %d），sh 改写 %d 个%s"
          % (py_done, py_skip, sh_done, "（dry-run，未写入）" if dry else ""))


if __name__ == "__main__":
    main()
