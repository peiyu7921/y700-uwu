#!/usr/bin/env python3
"""让 `path:modules` 的 in-tree 构建使用独立 O= 目录。

根因（r86）：`sm8750:modules` 的 in-tree 构建与 common 构建共用
`O=<...>/kernel_build`，而 vendor 树自己的 Kconfig 树会在 syncconfig 时
**重写同一份 .config**。实测被改写后只剩 2990 行 / 513 个 CONFIG_、连
`CONFIG_MODULES` 都没有，于是后续任何 `M=` 构建都报：

    *** The present kernel disabled CONFIG_MODULES. ***
    *** You cannot build or install external modules. ***

gh_arm_drv.ko（`sm8750/arch/arm64/gunyah:kbuild`）就是被这一点卡住的。

修法：vendor in-tree 构建用自己的输出目录（`kernel_build/vendor_modules_build`），
先从共享的 kernel_build 复制 .config 作为起点，再 olddefconfig/modules/
modules_install。staging 仍指向共享的 modules_staging，安装结果不变。
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

OLD = '''\t\t\t\t\t} else if len(parts) == 2 && parts[1] == "modules" {
\t\t\t\t\t\t// In-tree build of a vendor kernel tree: no M= (kbuild would resolve it
\t\t\t\t\t\t// against the output dir after -C chdir and fail).
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, "modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, fmt.Sprintf("INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", topRelativePath(staging.String()), strip)))'''

NEW = '''\t\t\t\t\t} else if len(parts) == 2 && parts[1] == "modules" {
\t\t\t\t\t\t// In-tree build of a vendor kernel tree.
\t\t\t\t\t\t// Two hard requirements discovered the hard way:
\t\t\t\t\t\t//  1. no M= (kbuild resolves it against the output dir after -C);
\t\t\t\t\t\t//  2. its own O= directory: the vendor Kconfig tree otherwise
\t\t\t\t\t\t//     rewrites the shared kernel_build/.config via syncconfig and
\t\t\t\t\t\t//     drops CONFIG_MODULES, which breaks every later `M=` build.
\t\t\t\t\t\tvendorOut := filepath.Join(buildRoot, "vendor_modules_build")
\t\t\t\t\t\tcmd.Text("&& mkdir -p").Text(vendorOut)
\t\t\t\t\t\tcmd.Text("&& cp").Text(filepath.Join(buildRoot, ".config")).Text(filepath.Join(vendorOut, ".config"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, vendorOut, arch, "olddefconfig"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, vendorOut, arch, "modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, vendorOut, arch, fmt.Sprintf("INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", topRelativePath(staging.String()), strip)))'''

if NEW in text:
    print("already patched")
elif OLD in text:
    path.write_text(text.replace(OLD, NEW, 1))
    print("patched: vendor :modules uses its own O=")
else:
    print("ANCHOR MISSING")
    sys.exit(1)

t = path.read_text(errors="ignore")
print("vendor_modules_build present:", "vendor_modules_build" in t)
