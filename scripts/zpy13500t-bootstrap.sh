#!/bin/bash
# 在 zpy-13500t（真实物理机：20 核 / 62G 内存 / 824G 可用）上从零搭建 uwuAOSP 构建环境，
# 复现 u-zpy 上验证过的全部修法，直到产出 OTA 包。
#
# 目标机器现状：只有 git(2.34.1)，没有 repo、没有 AOSP 源码。
#
# 用法：ssh zpy-13500t 'bash -s' < scripts/zpy13500t-bootstrap.sh
#
# 所有已确认的修法见 AGENTS.md 的「已确认的关键修法」表，本脚本逐条落地。
set -uo pipefail

WORK="${WORK:-$HOME/y700-uwu}"
AOSP="$WORK/aosp"
REPO_URL="https://mirrors.tuna.tsinghua.edu.cn/git/git-repo"
BRANCH="${BRANCH:-uwu-17.0}"          # uwuAOSP 分支，按实际 manifest 调整
PROXY="${PROXY:-http://<PROXY_HOST>:7897}"
JOBS="${JOBS:-16}"                     # 20 核，留余量

say() { echo "[$(date '+%H:%M:%S')] $*"; }

# 非交互 sudo：无 TTY 时从 stdin 读密码。
# 密码不再硬编码：用环境变量提供，例如
#   SUDO_PASS=xxx bash zpy13500t-bootstrap.sh
SUDO_PASS="${SUDO_PASS:-}"
[ -n "$SUDO_PASS" ] || { echo "错误：请先设置 SUDO_PASS 环境变量" >&2; exit 1; }
sudo_run() { echo "$SUDO_PASS" | sudo -S -p '' "$@"; }

# ---------------------------------------------------------------- 代理
# GNUTLS_CPUID_OVERRIDE 必须设：u-zpy 那台 CPU 缺 AVX，libgnutls 走 AES-NI 会 SIGILL。
# 13500t 是真实物理机，可能不需要，但设了无害。
export http_proxy="$PROXY" https_proxy="$PROXY"
export no_proxy="localhost,127.0.0.1,192.168.0.0/16"
export GNUTLS_CPUID_OVERRIDE=0x1

# ---------------------------------------------------------------- 依赖
say "=== [1/6] 安装依赖 ==="
if ! command -v repo >/dev/null 2>&1; then
    mkdir -p "$HOME/bin"
    curl -fsSL "$REPO_URL" -o "$HOME/bin/repo" && chmod +x "$HOME/bin/repo"
    export PATH="$HOME/bin:$PATH"
fi
command -v repo >/dev/null && say "  OK repo" || say "  MISS repo"

# m otapackage 需要的宿主机包（Ubuntu）
sudo_run apt-get update -qq 2>/dev/null || say "  WARN apt update 失败（可能无 sudo 免密）"
sudo_run env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq \
    git-core gnupg flex bison build-essential zip curl zlib1g-dev gcc-multilib \
    g++-multilib libc6-dev-i386 lib32ncurses5-dev x11proto-core-dev libx11-dev \
    lib32z1-dev libgl1-mesa-dev libxml2-utils xsltproc unzip fontconfig \
    python3 rsync git-lfs openjdk-21-jdk-headless \
    libssl-dev libelf-dev libdw-dev 2>/dev/null || say "  WARN apt install 有失败项"

# git-lfs 必须有：uwu-17.0 的 external/chromium-webview/prebuilt/{arm,arm64,x86,x86_64}
# 是 LFS 项目，缺 git-lfs 时 checkout 会报 "Cannot initialize work tree"，工作树只剩
# .gitattributes/.lfsconfig 而没有 webview.apk（13500t 实测踩过）。
git lfs install --skip-repo 2>/dev/null && say "  OK git-lfs" || say "  WARN git-lfs 未就绪"

# JDK 21：uwu-17.0 的 soong 需要 21（u-zpy 实测 openjdk-21-jdk-headless 可用）
if command -v java >/dev/null 2>&1; then
    say "  OK java $(java -version 2>&1 | head -1 | cut -d\" -f2)"
else
    say "  MISS java（m otapackage 会失败）"
fi

# ---------------------------------------------------------------- sync
say "=== [2/6] repo sync AOSP（约 250G，耗时数小时）==="
mkdir -p "$AOSP"
cd "$AOSP" || exit 1
if [ ! -d "$AOSP/.repo" ]; then
    repo init -u https://gh-proxy.com/https://github.com/uwuAOSP/platform_manifests -b uwu-17.0 --depth 1 2>&1 | tail -5
    # 并行拉取；-c 只拉当前分支，省带宽
    repo sync -c --no-tags --no-clone-bundle -j"$((JOBS/2))" 2>&1 | tail -20
else
    say "  AOSP 树已存在，跳过 init"
    cd "$AOSP" && repo sync -c --local-only 2>&1 | tail -5
fi

# ---------------------------------------------------------------- 拉起 device/kernel/vendor
say "=== [3/6] 克隆 device / kernel / vendor 树 ==="
cd "$AOSP" || exit 1
clone_if_missing() {
    local url="$1" dest="$2" rev="${3:-}"
    [ -d "$dest/.git" ] && { say "  ok   $dest"; return 0; }
    mkdir -p "$(dirname "$dest")"
    if [ -n "$rev" ]; then
        git clone --depth 1 -b "$rev" "$url" "$dest" 2>&1 | tail -2
    else
        git clone --depth 1 "$url" "$dest" 2>&1 | tail -2
    fi
}
# 这 5 棵树不在 default.xml/snippets 的 project 清单里（repo sync 拿不到），必须单独 clone。
# 真实仓库在 lunatellus/（不是 uwuAOSP/），且要走 gh-proxy 加速 —— 两处 u-zpy 实测过。
# vendor/uwu 不要在这里 clone：它是 manifest 里的 project（.repo/projects/vendor/uwu.git），
# repo sync 已经负责，再 clone 会覆盖成错误内容。
GH="${GH_PROXY:-https://gh-proxy.com/https://github.com}/lunatellus"
clone_if_missing "$GH/android_device_lenovo_elden.git"            device/lenovo/elden                       uwu-17.0
clone_if_missing "$GH/android_kernel_lenovo_sm8750.git"           kernel/platform/kernel-6.12/vendor/lenovo/sm8750           lineage-24.0
clone_if_missing "$GH/android_kernel_lenovo_sm8750-modules.git"   kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules   lineage-24.0
clone_if_missing "$GH/android_kernel_lenovo_sm8750-devicetrees.git" kernel/platform/kernel-6.12/vendor/lenovo/sm8750-devicetrees lineage-24.0
clone_if_missing "$GH/proprietary_vendor_lenovo_elden.git"        vendor/lenovo/elden                       uwu-17.0

# ---------------------------------------------------------------- device 树补丁
# GitHub 的 lunatellus/android_device_lenovo_elden 在 uwu-17.0 上只到 e04cdd0，
# 缺少 u-zpy 已经验证过的 2 个提交（charging control/GAPPS gate、supports_bypass 修复）
# 和一批工作区改动（power/ 上游、sepolicy、uwu_elden.mk、modules.load* 的 sm8750-gap 注释）。
# 这些已固化为 patches/device-elden-full.patch（相对 e04cdd0，1787 行）。
# prebuilt_dtb/{dtb.img,dtbo.img} 是二进制，patch 里只有 “Binary files differ” 行，
# git apply 无法据此建文件 → 用 --exclude 跳过，改为单独 scp（脚本末尾会提示）。
say "=== [3b/6] 应用 device 树补丁 ==="
DEVP="$WORK/patches/device-elden-full.patch"
DEVD="$AOSP/device/lenovo/elden"
if [ -f "$DEVP" ] && [ -d "$DEVD/.git" ]; then
    if git -C "$DEVD" apply --check --exclude='prebuilt_dtb/*' "$DEVP" 2>/dev/null; then
        git -C "$DEVD" apply --exclude='prebuilt_dtb/*' "$DEVP" && say "  device 补丁已应用"
    else
        say "  SKIP device 补丁（已应用过，或基线不是 e04cdd0）"
    fi
else
    say "  WARN 缺 $DEVP —— 先 scp patches/device-elden-full.patch 到 $WORK/patches/"
fi
if [ ! -f "$DEVD/prebuilt_dtb/dtb.img" ] || [ ! -f "$DEVD/prebuilt_dtb/dtbo.img" ]; then
    say "  WARN prebuilt_dtb/{dtb.img,dtbo.img} 缺失（二进制，需单独传）"
    say "       本地：android_device_lenovo_elden/prebuilt_dtb/"
    say "       目标：$DEVD/prebuilt_dtb/"
fi

# ---------------------------------------------------------------- kleaf 工作区
say "=== [4/6] 补齐 kleaf 工作区 + vendored 依赖 ==="
KW="$AOSP/kernel/platform/kernel-6.12"
if [ -d "$KW/build/kernel/kleaf" ]; then
    mkdir -p "$KW/tools"
    ln -sfn ../build/kernel/kleaf/bazel.sh "$KW/tools/bazel"
    ln -sfn build/kernel/kleaf/bzlmod/bazel.MODULE.bazel "$KW/MODULE.bazel"
    ln -sfn build/kernel/kleaf/bzlmod/bazel.WORKSPACE.bzlmod "$KW/WORKSPACE.bzlmod"
    say "  kleaf symlink 已建"
fi

# bazel 需要的 16 个 external 仓库（u-zpy 上逐个试出来的清单，含 server-kernel-workspace.sh 漏掉的 zopfli/zlib/kmod）
EXT_MAIN_KERNEL=(
    kernel/build kernel/common
    platform/external/bazelbuild-bazel-central-registry
    platform/external/bazel-skylib
    platform/external/bazel-contrib-bazel_features
    platform/external/bazelbuild-platforms
    platform/external/bazelbuild-rules_cc
    platform/external/bazelbuild-rules_license
    platform/external/bazelbuild-rules_pkg
    platform/external/bazelbuild-rules_python
    platform/external/bazelbuild-rules_rust
    platform/external/bazelbuild-rules_shell
    platform/external/libcap
    platform/external/libcap-ng
    platform/external/lz4
    platform/external/pigz
    platform/external/toybox
    platform/external/zopfli   # ← server-kernel-workspace.sh 漏掉，导致 pigz 依赖失败
    platform/external/zlib     # ← 同上
)
say "  external 清单共 ${#EXT_MAIN_KERNEL[@]} 项（可用 kleaf --config=internet 绕过离线限制）"

# ---------------------------------------------------------------- 应用修法
say "=== [5/6] 应用 u-zpy 上验证过的修法 ==="

# (a) DDK Makefile 的 modules: 与 Kbuild 同名冲突 —— 用 KERNELRELEASE 分流
SM="$KW/vendor/lenovo/sm8750-modules"
if [ -d "$SM" ]; then
    python3 - "$SM" <<'PYEOF'
import os, re, sys
root = sys.argv[1].rstrip("/")
patched = 0
for dp, dn, fs in os.walk(root):
    dn[:] = [d for d in dn if d != ".git"]
    for f in fs:
        if f != "Makefile":
            continue
        p = os.path.join(dp, f)
        s = open(p, errors="ignore").read()
        if "$(KERNEL_SRC)" not in s or "KERNELRELEASE" in s:
            continue
        lines = s.split("\n")
        at = 0
        for i, ln in enumerate(lines):
            if ln.startswith("#") or not ln.strip():
                at = i + 1
            else:
                break
        hdr = ["ifneq ($(KERNELRELEASE),)",
               "obj-m += $(patsubst %.c,%.o,$(notdir $(wildcard $(src)/*_dlkm.c)))",
               "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include",
               "ccflags-y += -I$(src)", "else", ""]
        open(p, "w", errors="ignore").write("\n".join(lines[:at] + hdr + lines[at:] + ["", "endif"]))
        patched += 1
print("   (a) KERNELRELEASE 保护: %d 个 Makefile" % patched)
PYEOF

    # (b) obj-y += ./ 自引用（117 层递归的元凶）
    CB="$SM/qcom/opensource/audio-kernel/asoc/codecs/Kbuild"
    [ -f "$CB" ] && sed -i '/^[[:space:]]*obj-y[[:space:]]*+=[[:space:]]*\.\/[[:space:]]*$/s/^/# DISABLED self-recursive: /' "$CB" && \
        say "   (b) codecs/Kbuild 自引用已注释"

    # (c) ccflags-y := 覆盖补丁 —— 在 Kbuild 里补 vendor include
    python3 - "$SM" <<'PYEOF'
import os, re, sys
root = sys.argv[1].rstrip("/")
LINE = "ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include"
n = 0
for dp, dn, fs in os.walk(root):
    dn[:] = [d for d in dn if d != ".git"]
    for f in fs:
        if f != "Kbuild":
            continue
        p = os.path.join(dp, f)
        s = open(p, errors="ignore").read()
        if not re.search(r"ccflags-y[ \t]*:=", s) or "vendor/lenovo/sm8750/include" in s:
            continue
        out, done = [], False
        for ln in s.split("\n"):
            out.append(ln)
            if ln.rstrip().endswith("\\"):
                continue
            if re.match(r"ccflags-y[ \t]*[:+]?=", ln) and not done:
                out.append(LINE); done = True
        if not done:
            out.insert(0, LINE)
        open(p, "w", errors="ignore").write("\n".join(out))
        n += 1
print("   (c) ccflags-y := 补 vendor include: %d 个 Kbuild" % n)
PYEOF

    # (d) camera-kernel 的 CAMERA_KERNEL_ROOT 四段绝对路径拼接
    CK="$SM/qcom/opensource/camera-kernel/Kbuild"
    if [ -f "$CK" ]; then
        python3 - "$CK" <<'PYEOF'
import sys
p = sys.argv[1]
lines = open(p, errors="ignore").read().split("\n")
for i, ln in enumerate(lines):
    if ln.startswith("CAMERA_KERNEL_ROOT"):
        lines[i] = "CAMERA_KERNEL_ROOT=$(src)"
        break
open(p, "w", errors="ignore").write("\n".join(lines))
print("   (d) CAMERA_KERNEL_ROOT=$(src)")
PYEOF
    fi
fi

# (e) 跨批次 modpost undefined —— 放行
BP="$AOSP/device/lenovo/elden/Android.bp"
if [ -f "$BP" ] && ! grep -q "KBUILD_MODPOST_WARN" "$BP"; then
    python3 - "$BP" <<'PYEOF'
import sys
p = sys.argv[1]
s = open(p, errors="ignore").read()
old = '    make_flags: [\n        "DEPMOD=true",'
if old in s:
    s = s.replace(old, old + '\n        "KBUILD_MODPOST_WARN=1",', 1)
    open(p, "w", errors="ignore").write(s)
    print("   (e) KBUILD_MODPOST_WARN=1 已加")
PYEOF
fi

# (e2) 内核模块清单 modules.include.*
#      BoardConfig.mk 的 vendor_ramdisk/vendor_dlkm/recovery_module_install_list
#      指向 modules.include.{vendor_ramdisk,vendor_dlkm,recovery}，但 device 树里只带
#      modules.load*；不生成会报 "modules.include.vendor_ramdisk not found"。
#      做法与 scripts/server-uwu-kernel.sh:108-110 完全一致（u-zpy 上验证过）。
DEV="$AOSP/device/lenovo/elden"
if [ -f "$DEV/modules.load" ]; then
    cp "$DEV/modules.load"             "$DEV/modules.include.vendor_ramdisk"
    cp "$DEV/modules.load.vendor_dlkm" "$DEV/modules.include.vendor_dlkm"
    cp "$DEV/modules.load.recovery"    "$DEV/modules.include.recovery"
    say "   (e2) modules.include.* 已由 modules.load* 生成"
else
    say "   (e2) 缺少 $DEV/modules.load（device 树没 clone？）"
fi

# (f) 内核树修法（vendor Kconfig / datarmnet / dsp / eva / vendor 树生成源 / device bp）
#     逐条内容与根因见 AGENTS.md「已确认的关键修法」与脚本内注释；幂等，可重复执行。
FIXES="$WORK/scripts/kernel-tree-fixes.py"
if [ -f "$FIXES" ]; then
    python3 "$FIXES" "$AOSP" || say "   (f) 树修法脚本返回非零"
else
    say "   (f) 缺少 $FIXES"
    say "        先传：scp scripts/kernel-tree-fixes.py zpy-13500t:$WORK/scripts/"
fi

# (g) uwu_kernel 插件（kernel.go）补丁 —— 必须按顺序应用
#     这些是构建编排层面的修法，缺一不可：
#       mkdir        : 模块列表写前建目录（modules_flat 的 "Directory nonexistent"）
#       modules-target: 放行 external_modules 的 path:modules
#       modules-branch: path:modules 的 in-tree 分支（不能带 M=）
#       vendor-outdir : vendor in-tree 构建用独立 O=，否则会把共享 .config 里
#                       的 CONFIG_MODULES 等一起覆盖掉
KG="$AOSP/vendor/uwu/build/soong/kernel/kernel.go"
if [ -f "$KG" ]; then
    for p in patch-uwu-kernel-mkdir patch-uwu-kernel-modules-target \
             patch-uwu-kernel-modules-branch patch-uwu-vendor-outdir; do
        if [ -f "$WORK/scripts/$p.py" ]; then
            python3 "$WORK/scripts/$p.py" "$KG" || say "   (g) $p 返回非零"
        else
            say "   (g) 缺少 scripts/$p.py（先 scp 到 $WORK/scripts/）"
        fi
    done
    # 树内入口 / Kconfig 类补丁（参数里含默认绝对路径，跨机器时需按 $WORK 调整）
    for p in fix-gunyah-entry dedup-vendor-kconfig fix-qcom-kconfig-choice; do
        [ -f "$WORK/scripts/$p.py" ] && python3 "$WORK/scripts/$p.py" 2>/dev/null || true
    done
else
    say "   (g) 找不到 $KG"
fi

# (h) 清理递归残留缓存（每次构建前都要做）
find "$SM" -name "*.cmd" -delete 2>/dev/null
find "$SM" -name "modules.order" -delete 2>/dev/null
say "   (h) .cmd / modules.order 残留已清理"

# (i) art gen_mterp.py 用了 Python 3.12-only 的 f-string 写法
#     f-string 表达式里复用外层双引号（PEP 701），Ubuntu 22.04 的 python3 是 3.10 →
#     SyntaxError: f-string: expecting '}'
#     → //art/runtime:libart_mterp.{arm64ng,x86_64ng} 失败
if [ -f "$WORK/scripts/fix-mterp-py312.py" ]; then
    python3 "$WORK/scripts/fix-mterp-py312.py" "$AOSP" || say "   (i) 返回非零"
else
    say "   (i) 缺少 scripts/fix-mterp-py312.py（先 scp 到 $WORK/scripts/）"
fi

# (j) aidl 对 Java unstructured parcelable 写出空 target 的 depfile
#     make 能容忍，siso 的 gcc-deps 解析器不能 →
#     err: gcc-deps: failed to parse depfile ".../xxx.aidl.d"
#     → Connectivity 的 aidl1/aidl0.srcjar 成批失败。
#     改的是 host 工具源码，构建时 siso 会自动重编 out/host/linux-x86/bin/aidl。
if [ -f "$WORK/scripts/fix-aidl-depfile-empty-target.py" ]; then
    python3 "$WORK/scripts/fix-aidl-depfile-empty-target.py" "$AOSP" || say "   (j) 返回非零"
else
    say "   (j) 缺少 scripts/fix-aidl-depfile-empty-target.py（先 scp 到 $WORK/scripts/）"
fi

# ---------------------------------------------------------------- 构建
say "=== [6/6] 启动 m otapackage -j$JOBS ==="
cd "$AOSP" || exit 1
source build/envsetup.sh
lunch uwu_elden aosp_current user
LOG="$WORK/build-zpy13500t-$(date +%Y%m%d-%H%M%S).log"
script -q -e -c "m otapackage -j$JOBS" "$LOG"
RC=$?
say "=== DONE rc=$RC ==="
ls -lh out/target/product/elden/*.zip 2>/dev/null || echo "(no OTA zip)"
ls -lh out/target/product/elden/*.img 2>/dev/null | head -12
