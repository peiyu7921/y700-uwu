#!/usr/bin/env python3
"""`:modules` 复用共享 O=，但备份并恢复 .config。

演进过程（都为实测）：
  r88 之前：共享 O= → vendor 全树能编出 201 个 .ko，但 vendor 的 Kconfig 在
            syncconfig 时重写共享 .config（只剩 2990 行、丢 CONFIG_MODULES），
            后续 `M=` 构建全报 "disabled CONFIG_MODULES"。
  r89      ：独立 O= → vendor 树单独 olddefconfig 后同样只剩 2990 行，
            缺 modules.builtin，modules_install 报
            "No rule to make target 'modules.builtin'"。

根本矛盾：vendor 树的 Kconfig 与 common 不同，任何以 vendor 为 srctree 的
make 都会重写 .config。所以这里回到共享 O=（能编出模块），但在前后做
备份/恢复，让 common 的配置不被破坏。
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

NEW = '''\t\t\t\t\t} else if len(parts) == 2 && parts[1] == "modules" {
\t\t\t\t\t\t// In-tree build of a vendor kernel tree: no M= (kbuild resolves it
\t\t\t\t\t\t// against the output dir after -C).
\t\t\t\t\t\t//
\t\t\t\t\t\t// The vendor Kconfig tree differs from common's, so this make WILL
\t\t\t\t\t\t// rewrite the shared .config via syncconfig (dropping CONFIG_MODULES,
\t\t\t\t\t\t// which breaks every later `M=` build). An isolated O= does not work
\t\t\t\t\t\t// either: the regenerated config has no modules.builtin. So keep the
\t\t\t\t\t\t// shared O= (that is what actually builds the vendor modules) and
\t\t\t\t\t\t// restore common's config afterwards.
\t\t\t\t\t\tcfgBackup := filepath.Join(buildRoot, ".config.common-bak")
\t\t\t\t\t\tcmd.Text("&& cp").Text(filepath.Join(buildRoot, ".config")).Text(cfgBackup)
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, "modules"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, moduleRoot, buildRoot, arch, fmt.Sprintf("INSTALL_MOD_PATH=%s INSTALL_MOD_STRIP=%s modules_install", topRelativePath(staging.String()), strip)))
\t\t\t\t\t\tcmd.Text("&& cp").Text(cfgBackup).Text(filepath.Join(buildRoot, ".config"))
\t\t\t\t\t\tcmd.Text("&&").Text(m.makeInvocation(ctx, source, buildRoot, arch, "olddefconfig"))'''

if NEW in text:
    print("already patched")
elif OLD in text:
    path.write_text(text.replace(OLD, NEW, 1))
    print("patched: :modules uses shared O= with .config backup/restore")
else:
    print("ANCHOR MISSING")
    sys.exit(1)

t = path.read_text(errors="ignore")
print("cfgBackup present:", "cfgBackup" in t)
