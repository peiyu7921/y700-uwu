#!/usr/bin/env python3
"""给 external_modules 的 `path:modules` 增加独立分支：in-tree 构建，不带 M=。

r78 的报错：`No rule to make target '../vendor/lenovo/sm8750/Makefile'`。
原因是 `modules` 落到了共享的 else 分支，那里传的是相对 `common` 的 M= 路径；
而这条路径又配合 `-C <moduleRoot>`（vendor 树自身作 srctree），kbuild 切到输出
目录后 M= 就解析不到了。

r75 日志里那条成功的命令是不带 M= 的 in-tree 构建：
    make -C <vendor 树> O=<kernel_build> ARCH=arm64 modules
    make -C <vendor 树> O=<kernel_build> ARCH=arm64 INSTALL_MOD_PATH=<staging> ... modules_install
这里照此单列一个分支。
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

ANCHOR = '\t\t\t\t\t} else {\n\t\t\t\t\t\tcommon := fmt.Sprintf("M=%s KERNEL_SRC=%s OUT_DIR=%s", moduleM, topRelativePath(source), topRelativePath(buildRoot))'
BRANCH = '''\t\t\t\t\t} else if len(parts) == 2 && parts[1] == "modules" {
\t\t\t\t\t\t// In-tree build of a vendor kernel tree: no M= (kbuild would resolve it
\t\t\t\t\t\t// against the output dir after -C chdir and fail).
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, "modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, fmt.Sprintf("INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", topRelativePath(staging.String()), strip)))
\t\t\t\t\t} else {
\t\t\t\t\t\tcommon := fmt.Sprintf("M=%s KERNEL_SRC=%s OUT_DIR=%s", moduleM, topRelativePath(source), topRelativePath(buildRoot))'''

if 'parts[1] == "modules" {\n' in text and 'In-tree build of a vendor kernel tree' in text:
    print("already patched")
elif ANCHOR in text:
    path.write_text(text.replace(ANCHOR, BRANCH, 1))
    print("patched modules branch")
else:
    print("ANCHOR MISSING")
    sys.exit(1)

t = path.read_text(errors="ignore")
print("branch present:", "In-tree build of a vendor kernel tree" in t)
print("mkdir insertions:", t.count('mkdir -p").Text(dir)'))
