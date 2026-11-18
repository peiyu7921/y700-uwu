#!/usr/bin/env python3
"""恢复 external_modules 里 `path:modules` 的放行。

背景：r77 报 `"sm8750:modules" must be path, path:all, or path:kbuild`。当前代码的
分派逻辑（else 分支 `target = parts[1]`）本来就支持任意 target，真正缺的只是校验
白名单里的 `modules`。这个改动在更早会话里是未提交的工作区修改，被一次
`git checkout -- build/soong/kernel/kernel.go`（为回退语法错误的补丁）一并清掉了。
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

OLD = '\t\t\t\t\tif len(parts) > 2 || parts[0] == "" || (len(parts) == 2 && parts[1] != "kbuild" && parts[1] != "all") {\n\t\t\t\t\t\tctx.PropertyErrorf("modules.external_modules", "%q must be path, path:all, or path:kbuild", entry)'
NEW = '\t\t\t\t\tif len(parts) > 2 || parts[0] == "" || (len(parts) == 2 && parts[1] != "kbuild" && parts[1] != "all" && parts[1] != "modules") {\n\t\t\t\t\t\tctx.PropertyErrorf("modules.external_modules", "%q must be path, path:all, path:kbuild, or path:modules", entry)'

if NEW in text:
    print("already patched")
elif OLD in text:
    path.write_text(text.replace(OLD, NEW, 1))
    print("patched validation")
else:
    print("ANCHOR MISSING")
    sys.exit(1)

text = path.read_text(errors="ignore")
print("accepts modules:", 'parts[1] != "modules"' in text)
