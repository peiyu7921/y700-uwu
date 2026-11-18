#!/usr/bin/env python3
"""只给两个做 `: >` 写入的辅助函数补 mkdir -p（uwu_kernel 插件）。

上一版给 4 个函数都插了 mkdir，其中 writeAllVendorModuleList / writeModuleBlocklist
的插入点落在命令链首，产生了 `&& &&` 的非法脚本。这里只改 writeModuleListFile 与
writeModuleLoadFile —— 它们的插入点紧邻已有的 `&& : >`，链式结构必然合法。

判定依据（r74/r75）：kernel_modules 这条规则里 `rm -rf modules_flat && mkdir -p
modules_flat` 只出现 1 次，而同族 4 条规则（kernel_modules / _recovery /
_vendor_dlkm / _vendor_ramdisk）都会往这个目录写列表文件，只有在写入时各自
确保目录存在，才不受执行顺序影响。
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

path = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else
                    _Y700_WORK + "/aosp/vendor/uwu/build/soong/kernel/kernel.go")
text = path.read_text(errors="ignore")
ADD = 'cmd.Text("&& mkdir -p").Text(dir)\n'

anchors = [
    # writeModuleLoadFile
    '\tpath := filepath.Join(dir, "modules.load."+name)\n\tcmd.Text("&& : >").Text(path)',
    # writeModuleListFile
    '\tpath := filepath.Join(dir, name)\n\tcmd.Text("&& : >").Text(path)',
]

changed = 0
for anchor in anchors:
    if ADD in anchor or (anchor + "\n" + ADD) in text:
        print("already:", anchor.splitlines()[0][:60])
        continue
    if anchor not in text:
        print("MISSING:", anchor.splitlines()[0][:60])
        continue
    first, second = anchor.split("\n")
    text = text.replace(anchor, first + "\n" + ADD + second, 1)
    changed += 1

path.write_text(text)
print("insertions:", changed, "| total:", text.count('mkdir -p").Text(dir)'))
