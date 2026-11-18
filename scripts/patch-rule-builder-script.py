#!/usr/bin/env python3
"""直接改已生成的 rule_builder 脚本：`:modules` 从“独立 O=”改为“共享 O= + .config 备份恢复”。

背景：
  - r89 的补丁用独立 O=（`kernel_build/vendor_modules_build`），实测该目录里
    `make olddefconfig` 会把 common 的 .config 裁成 2990 行、缺 modules.builtin，
    `modules_install` 直接失败。
  - r90 改成“共享 O= + 前后备份/恢复 .config”，但改的是 kernel.go，soong 需要
    重新 bootstrap 才能把它写进 rule_builder 脚本；而 siso bootstrap 反复死锁
    （soong_ui 在 futex_wait、siso 在 do_sys_pause），一直没能生成。
  - 因此这里直接改已生成的脚本，绕过 soong。

用法: patch-rule-builder-script.py <script.sh>
"""
import os
import pathlib
import re
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

p = pathlib.Path(sys.argv[1])
text = p.read_text(errors="ignore")

BUILD = _Y700_WORK + "/aosp/out/soong/.intermediates/device/lenovo/elden/kernel/android_arm64_armv8-a-branchprot_oryon/kernel_build"
VENDOR_OUT = BUILD + "/vendor_modules_build"
BAK = BUILD + "/.config.common-bak"

if "config.common-bak" in text:
    print("already patched")
    sys.exit(0)

# 1) 把 vendor 构建的 O= 指回共享目录
before = text.count(VENDOR_OUT)
text = text.replace(VENDOR_OUT, BUILD)

# 2) 在 vendor 的 `make ... modules` 之前插入备份，在 modules_install 之后插入恢复
#    定位：make ... -C <vendor> O=<BUILD> ... modules   （不含 modules_install 的那条）
pat_modules = re.compile(
    r"(make -j\d+ -C [^ ]*vendor/lenovo/sm8750 O=" + re.escape(BUILD) + r" [^&]*? )modules(?![_a-z])"
)
m = pat_modules.search(text)
if not m:
    print("ANCHOR MISSING: vendor modules 调用未找到")
    sys.exit(1)
text = text[:m.start()] + "cp " + BUILD + "/.config " + BAK + " && " + text[m.start():]

# 3) 在 vendor 的 modules_install 之后插入恢复 + 重新同步 common 的 auto.conf
pat_install = re.compile(
    r"(make -j\d+ -C [^ ]*vendor/lenovo/sm8750 O=" + re.escape(BUILD) + r" [^&]*modules_install)"
)
m2 = pat_install.search(text)
if not m2:
    print("ANCHOR MISSING: modules_install 未找到")
    sys.exit(1)
restore = (
    " && cp " + BAK + " " + BUILD + "/.config"
    " && make -j24 -C " + _Y700_WORK + "/aosp/kernel/platform/kernel-6.12/common O=" + BUILD
    + " ARCH=arm64 LLVM=1 LLVM_IAS=1 olddefconfig"
)
text = text[:m2.end()] + restore + text[m2.end():]

p.write_text(text)
print("patched rule_builder script")
print("  O= 替换处:", before)
print("  backup 已插入:", "config.common-bak" in text)
