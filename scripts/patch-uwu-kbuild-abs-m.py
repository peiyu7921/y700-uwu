#!/usr/bin/env python3
"""修 `:kbuild` 分支的 M= 路径：必须是绝对路径。

实测（r87 后的手动重放）：

    make -C common O=<kernel_build> M=../vendor/lenovo/sm8750/arch/arm64/gunyah modules
    → ../vendor/lenovo/sm8750/arch/arm64/gunyah/Makefile: No such file or directory

`O=` 让 kbuild 切到输出目录，相对 `M=` 就按输出目录解析了。改成 `$PWD/...`
形式（`topRelativePath`），脚本内展开为 AOSP 根的绝对路径。
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

OLD = '''\t\t\t\t\tif len(parts) == 2 && parts[1] == "kbuild" {
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, source, buildRoot, arch, "M="+moduleM+" modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, source, buildRoot, arch, fmt.Sprintf("M=%s INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", moduleM, topRelativePath(staging.String()), strip)))'''

NEW = '''\t\t\t\t\tif len(parts) == 2 && parts[1] == "kbuild" {
\t\t\t\t\t\t// M= must be absolute: with O= set, kbuild chdirs into the output
\t\t\t\t\t\t// directory and a relative M= resolves against that instead of srctree
\t\t\t\t\t\t// ("No rule to make target '../vendor/.../Makefile'").
\t\t\t\t\t\tmoduleMAbs := topRelativePath(moduleRoot)
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, source, buildRoot, arch, "M="+moduleMAbs+" modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, source, buildRoot, arch, fmt.Sprintf("M=%s INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", moduleMAbs, topRelativePath(staging.String()), strip)))'''

if NEW in text:
    print("already patched")
elif OLD in text:
    path.write_text(text.replace(OLD, NEW, 1))
    print("patched: :kbuild uses absolute M=")
else:
    print("ANCHOR MISSING")
    sys.exit(1)

t = path.read_text(errors="ignore")
print("moduleMAbs present:", "moduleMAbs" in t)
