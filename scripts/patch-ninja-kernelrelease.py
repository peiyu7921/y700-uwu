#!/usr/bin/env python3
"""给 ninja 图里 kernel_modules 这条 rule 的 command 注入 KERNELRELEASE。

问题（u-zpy 与 13500t 都踩过，AGENTS.md 有记）：
  该 step 的 make 在 siso/localexec 环境下读不到
      $O/include/config/kernel.release
  → KERNELRELEASE 为空 → MODLIB 变成 `.../lib/modules//`（注意双斜杠）
  → make[3]: *** No rule to make target 'modules.builtin', needed by '.../modules_staging/lib/modules//modules.builtin'
  → kernel_modules.zip FAILED → otapackage 卡死。

为什么注入有效：
  make 的**命令行变量**优先级最高，压过 Makefile 里的
      KERNELRELEASE = $(call read-file, $(objtree)/include/config/kernel.release)
  所以 `... KERNELRELEASE=<version> modules_install` 能强制正确版本号。

为什么必须配套"直跑"：
  **ninja 图会被 soong_ui 在下次 `m` 时重新生成并覆盖**（实测注入后跑一次
  `m otapackage` 就归零）。所以正确顺序是：
      1) m otapackage      （生成/刷新 ninja 图；让它失败也没关系）
      2) 本脚本            （注入 KERNELRELEASE）
      3) siso ninja -k 0 -f out/combined-uwu_elden.ninja otapackage
         （**不要**再用 m —— 否则注入被覆盖）
  siso 直跑还有一个附带好处：它有自己的 deps 库，不会像那个 ninja 二进制那样
  在 kernel 的超大 deps 上写坏 `.ninja_deps`。

幂等：已注入则跳过。
用法：python3 patch-ninja-kernelrelease.py [AOSP 根目录] [--check]
"""
import os
import pathlib
import re
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("-")
                    else _Y700_WORK + "/aosp")
CHECK_ONLY = "--check" in sys.argv

RULE = "m.1-kernel_android_arm64_armv8-a-branchprot_oryon.kernel_modules"
REL = AOSP / ("out/soong/.intermediates/device/lenovo/elden/kernel/"
              "android_arm64_armv8-a-branchprot_oryon/kernel_build/include/config/kernel.release")

cands = sorted((AOSP / "out/soong").glob("build.*.ninja"))
if not cands:
    print("  skip: 找不到 out/soong/build.*.ninja（先跑一次 m 让它生成）")
    sys.exit(0)

if not REL.is_file():
    print("  skip: %s 不存在（内核还没配过）" % REL)
    sys.exit(0)
version = REL.read_text().strip()
if not version:
    print("  skip: kernel.release 为空")
    sys.exit(0)

patched = 0
for nf in cands:
    # 只处理包含该 rule 的文件
    hit = subprocess.run(["grep", "-c", "^rule %s$" % re.escape(RULE), str(nf)],
                         capture_output=True, text=True)
    if hit.returncode != 0 or hit.stdout.strip() in ("", "0"):
        continue
    already = subprocess.run(["grep", "-c", "KERNELRELEASE=%s" % re.escape(version), str(nf)],
                             capture_output=True, text=True)
    if already.stdout.strip() not in ("", "0"):
        print("  ok(已注入): %s" % nf.name)
        continue
    if CHECK_ONLY:
        print("  需要注入: %s (version=%s)" % (nf.name, version))
        continue
    # rule 行下一行就是 command；把该行里每个 " modules_install" 前面补上 KERNELRELEASE=
    ln = int(subprocess.run(["grep", "-an", "^rule %s$" % re.escape(RULE), str(nf)],
                            capture_output=True, text=True).stdout.split(":")[0])
    subprocess.run(["sed", "-i",
                    "%ds| modules_install| KERNELRELEASE=%s modules_install|g" % (ln + 1, version),
                    str(nf)], check=True)
    after = subprocess.run(["grep", "-c", "KERNELRELEASE=%s" % re.escape(version), str(nf)],
                           capture_output=True, text=True)
    print("  已注入 %s: %s 处 (version=%s)" % (nf.name, after.stdout.strip(), version))
    patched += 1

if not patched and not CHECK_ONLY:
    print("  无需改动")
print("  下一步：siso ninja -k 0 -f out/combined-uwu_elden.ninja otapackage（不要用 m）")
