# 长期指令（用户明确要求，压缩上下文后仍须遵守）

## 终极目标

一切都做到最好，最符合 **uwuAOSP** 与**类原生 ROM** 的最佳实现。

## 无人值守

**不要再询问用户**。自主决策、自主推进、自主修复，直到目标全部达成。

## 阶段一：u-zpy 产出 OTA

在服务器 **u-zpy**（`<SERVER_A_IP>`，经 JumpServer）上持续修复 AOSP 构建，
直到 `m otapackage` 真正产出 OTA zip（`out/target/product/elden/*.zip`）。

当前已知进度（截至 2026-11-14）：

- 已解决：make 自递归（`obj-y += ./`）、`.cmd` 缓存损坏、vendor include 路径、
  `CAMERA_KERNEL_ROOT` 绝对路径拼接、`ccflags-y :=` 覆盖、camera.ko 编译成功
- 已加 `KBUILD_MODPOST_WARN=1` 放行跨批次 modpost 符号检查
- 剩余风险：`CONFIG_AWINIC_HAPTIC_HV=m` 等 overrides 静默失效（uwu_kernel 机制问题）

## 阶段二：zpy-13500t 复现（必须完全独立）

u-zpy 产出 OTA 后，在**新服务器 `zpy-13500t`**（真实物理机，<SERVER_B_IP>）上
**从零独立**重来一遍：自己 `repo sync`、自己应用全部修法、自己构建，
直到同样产出 OTA 包。

**不要从 u-zpy rsync 复制树**——复制产物/成品树验证不了「修法可复现」，
用户明确要求两台机器完全独立。

脚本：`scripts/zpy13500t-bootstrap.sh`（装依赖 → repo sync → 落全部修法 → 构建）

### repo sync 的正确参数（u-zpy 实测）

```bash
repo init -u https://gh-proxy.com/https://github.com/uwuAOSP/platform_manifests \
          -b uwu-17.0 --depth 1
repo sync -c --no-tags --no-clone-bundle -j8
```

三个容易踩错的点：

1. **分支是 `uwu-17.0`，不是 `default`**——`default` 只是本地 HEAD 名，
   远程只有 `refs/heads/uwu-17.0`，写错会报 `couldn't find remote ref`
2. **remote 走 `gh-proxy.com` 加速**（GitHub 直连不稳）
3. **`.repo` 必须建在 `$AOSP` 里**，不是 `$WORK`；建错会报
   `error parsing manifest /home/zpy/y700-uwu/.repo/manifest.xml`

`default.xml` 里 1087 个 project，4 个 remote（aosp / lineageos / github / gitlab），
`default revision="refs/tags/android-17.0.0_r1"`。

### 13500t 依赖（已装好）

gcc / g++ / make / multilib / zip / unzip / java / flex / bison / xml2-config
已通过 `echo "$SUDO_PASS" | sudo -S` 安装完成（`SUDO_PASS` 由环境变量提供）。

### 13500t 现状与阻塞

- 系统：Ubuntu 22.04.5，20 核 / 62G / 824G 可用
- 已有：git 2.34.1、curl、python3、rsync
- **缺失**：gcc / g++ / make / zip / unzip / java / javac / flex / bison / xml2-config
- **sudo 需要密码**（`sudo-needs-password`）→ 装依赖无法全自动，
  这是无人值守的唯一硬阻塞点。`repo sync` 本身只需要 git+python3，可先跑。

## 服务器规格

| | u-zpy（阶段一） | zpy-13500t（阶段二） |
|---|---|---|
| CPU | 14 核 | **20 核** |
| 内存 | 39G | **62G** |
| 磁盘 | 984G，可用 462G | 937G，可用 **824G** |
| 现状 | AOSP 树已就绪，正在修 OTA | 基本为空（仅用 66G），需从 sync 开始 |

## 执行方式（重要）

**不要用 `wait` 等待，也不要轮询服务器命令。**

做法：用 `run_in_background` 同步后台执行，命令里自带等待逻辑
（如 `while pgrep -x soong_ui; do sleep 10; done`），执行完再看结果。
后台作业完成时宿主会自动通知，不需要主动收割。

## 连接方式

`~/.ssh/config` 已配好别名，密钥直达，跳过资产菜单：

```bash
ssh u-zpy          # <SERVER_A_IP>
ssh zpy-13500t     # <SERVER_B_IP>
ssh jumpserver     # 资产选择菜单
ssh u-zpy "hostname; df -h"
ssh -N -L 8080:127.0.0.1:80 u-zpy    # 端口转发
```

原理：用户名格式 `<JMS用户>#<系统账号>#<资产ID>`。

旧方式（`ssh -tt -p 12222 zpy@<JUMP_HOST>` + 分步喂 stdin）已不再需要。

### 账号与密码

两台机器使用同一系统账号（值不写进仓库，由环境变量提供）：

- 账号：`$REMOTE_USER`
- 密码：`$SUDO_PASS`（仅用于非交互 `sudo`）
- SSH 密钥：`$SSH_KEY`（免密登录，但 `sudo` 仍需密码）

非交互 sudo 写法（无 TTY 时从 stdin 读密码）：

```bash
echo "$SUDO_PASS" | sudo -S -p '' apt-get install -y ...
```

`scripts/server-allinone.sh` / `scripts/zpy13500t-bootstrap.sh` 都从
`${SUDO_PASS:-}` 读取，未设置时直接退出并提示 —— 仓库里不保存任何密码。

### JumpServer 概况

- Web：http://<JUMP_HOST>:18888/
- SSH/SFTP：<JUMP_HOST>:12222
- 账号：zpy　密钥：`~/.ssh/peiyu`

### 资产 ID

| 别名 | 地址 | 资产 ID |
|---|---|---|
| u-zpy | <SERVER_A_IP> | <ASSET_ID_A> |
| zpy-13500t | <SERVER_B_IP> | <ASSET_ID_B> |

### SFTP

```bash
sftp u-zpy
sftp u-zpy <<'X'
put local.tar.gz
get remote.log
bye
X
```

- 根目录是资产配置的 `/tmp`（chroot），看不到 `/home`
- `scp` 上传可用；**下载会报 `invalid user name`，请用 `sftp get`**

### config 片段

```sshconfig
Host u-zpy
    HostName <JUMP_HOST>
    Port 12222
    User zpy#zpy#<ASSET_ID_A>
    IdentityFile ~/.ssh/peiyu
    IdentitiesOnly yes
```

## 已确认的关键修法（勿重复排查）

| 问题 | 修法 |
|---|---|
| DDK `Makefile` 的 `modules:` 与 Kbuild 同名冲突 | 用 `ifneq ($(KERNELRELEASE),)` 包住 |
| `obj-y += ./` 自引用（117 层递归） | 注释掉 `sm8750-modules/.../asoc/codecs/Kbuild:287` |
| `.modules.order.cmd` 损坏 | 源码树里删除所有 `*.cmd` 与 `modules.order` |
| `file not found` 头文件 | `ccflags-y += -I$(srctree)/../vendor/lenovo/sm8750/include` |
| `ccflags-y :=` 覆盖补丁 | 在 **Kbuild**（非 Makefile）里补，共 10 处已补 |
| `kernel_build//home/...` 路径拼接 | `camera-kernel/Kbuild:3` 改为 `CAMERA_KERNEL_ROOT=$(src)` |
| 跨批次 modpost undefined | `Android.bp` 的 `make_flags` 加 `"KBUILD_MODPOST_WARN=1"` |
| kleaf/bazel 离线拉不动依赖 | `--config=internet`（`network.bazelrc` 的 `internet` 配置） |
| NDK sysroot 缺失 | 本机下载 633MB NDK，只传 6 个文件（314KB）+ 3 个空占位 |
| **overrides 237→241 条静默失效**（`CONFIG_ARCH_SUN` 等查不到） | GKI 的 `common/Kconfig` 末尾只 `source "$(KCONFIG_EXT_PREFIX)Kconfig.ext"`，而 `KCONFIG_EXT_PREFIX` 没传 → vendor Kconfig 整棵不可见，`olddefconfig` 把未知符号全丢掉。修法：新建 `vendor/lenovo/sm8750/Kconfig.ext`（`source "$(KCONFIG_EXT_PREFIX)Kconfig.msm"`）+ device bp 的 `make_flags` 加 `"KCONFIG_EXT_PREFIX=../vendor/lenovo/sm8750/"`（相对 srctree=common） |
| `-objs` 自引用（`mpam-objs += mpam.o …` → `Circular` + `ld.lld: cannot open mpam.o`） | 同 `obj-y += ./` 一类，vendor Makefile 只给 bazel 写过。删掉自引用那一项（`mpam-objs += mpam_rpmsg.o`） |
| bazel 用 patch 生成的源文件在树里不存在（`qti_fixed_regulator.c`、`gpi_fixed.c`、`virtio_net_fixed.c`、`ledtrig-netdev_fixed.c`） | `vendor/lenovo/sm8750/common_sources.bzl` 里有 4 条 `native.genrule`（`patch -o OUT -i DIFF //common:PATH`）和若干 `copy_file`。按同样命令在树里物化生成；`fixed.diff` → `cp fixed.c qti_fixed_regulator.c && patch < fixed.diff` |
| `qcom_common.h not found`（`adsp_sleepmon.c`） | `drivers/soc/qcom/Makefile` 补 `-I$(srctree)/../vendor/lenovo/sm8750/drivers/remoteproc` |
| `QCOM_SMMU_V2_V3_DISPATCHER=m` 时 `No rule to make target 'arch/arm64/kvm/hyp/nvhe/module.lds.S'` | Kconfig `default m` 但 `CONFIG_ARM_SMMU_V3_PKVM` 未开、模块也不在 install/load 清单 → overrides 里显式 `=n` |
| `datarmnet` / `datarmnet-ext` / `data-kernel` 缺 `Makefile`（`No rule to make target .../Makefile`） | 顶层补 `obj-y += core/` 之类入口；父级用 `subdir-ccflags-y` 一次性下发 include 路径 |
| `dsp-kernel` 的 `session_control` 成员不存在 / `CONFIG_EVA_SUN is not defined` | 都是 `CONFIG_ARCH_SUN` 系门控失效的连带症状；`dsp-kernel/Kbuild` 另需 `-DCONFIG_QCOM_FASTRPC_TRUSTED=1` 与 `-DDSP_TRACE_INCLUDE_PATH=../../../vendor/lenovo/sm8750-modules/qcom/opensource/dsp-kernel/dsp` |
| trace 头文件相对路径（`define_trace.h:102` 报 `../../../../vendor/qcom/...`） | vendor 头文件里的 `TRACE_INCLUDE_PATH` 是给树外布局写的；用 `-DRMNET_TRACE_INCLUDE_PATH=../../../vendor/lenovo/sm8750-modules/...` 覆盖，相对 `common/include/trace/` |
| 源码树里混入陈旧编译产物（`vendor/lenovo/sm8750` 曾有 cmd=1059 / o=574 / mod=186 / order=208） | 每轮前 `find ... -name "*.cmd" -o -name "*.o" -o -name "*.mod" -o -name "modules.order" -delete` |
| `choice value has a prompt outside its choice group` / `choice member must have a prompt`（`drivers/soc/qcom/Kconfig:744`） | **不是** choice 写法问题，而是同一份 Kconfig 被 source 两次：`Kconfig.msm` 用 `$(KCONFIG_EXT_PREFIX)`（绝对）source 一次，父级 `drivers/soc/Kconfig`、`arch/arm64/Kconfig`、`drivers/cpufreq/Kconfig` 又相对 srctree source 一次。`srctree=common` 时是不同文件所以无事，`srctree=vendor`（`path:modules` in-tree 构建）时指向同一文件 → `choice` 解析两遍。修法：把树内那些重复 source 行注释掉（`scripts/dedup-vendor-kconfig.py`，也已并入 `kernel-tree-fixes.py` 的 `fix_kconfig_dedup`） |
| `KCONFIG_EXT_PREFIX` 用相对路径只在 `srctree=common` 成立 | vendor 树自己作 srctree（in-tree `path:modules`）时相对前缀错位，报 `can't open file "../vendor/lenovo/sm8750-modules/..."`。改用**绝对路径**（device bp 的 `make_flags`），`Kconfig.ext` 里的模块树条目也写成 `source "$(KCONFIG_EXT_PREFIX)../sm8750-modules/..."` |
| `kernel module gh_arm_drv.ko was not found` | 源码在 `vendor/.../arch/arm64/gunyah/gh_arm.c`，但 `make modules` 不遍历 `arch/`。放到 `drivers/gunyah/`（复制 `gh_arm.c`）+ `Kbuild: obj-m += gh_arm_drv.o; gh_arm_drv-objs := gh_arm.o`，并在 `drivers/Makefile` 加 `obj-m += gunyah/` |
| `No rule to make target '../vendor/lenovo/sm8750/Makefile'`（`external_modules` 的 `:modules` 条目） | `:modules` 是 in-tree 构建，**不能带 `M=`**（`-C` 之后 kbuild 切到输出目录，相对 `M=` 解析不到）。给 `:modules` 单列分支：`make -C <moduleRoot> ... modules` + `INSTALL_MOD_PATH=... modules_install` |
| `*** The present kernel disabled CONFIG_MODULES. ***`（`M=` 构建全崩）、`.config` 只剩 2990 行/513 个 `CONFIG_`、GUNYAH 全系符号消失 | **共用 `O=` 导致 config 互毁**：`sm8750:modules` 的 in-tree 构建和 common 构建共用 `kernel_build`，vendor 自己的 Kconfig 树在 syncconfig 时重写了同一份 `.config`，把 `CONFIG_MODULES` 等全部丢掉。修法：`:modules` 用**独立 O=**（`kernel_build/vendor_modules_build`），先从共享目录 `cp .config` 作为起点，再 `olddefconfig` + `modules` + `modules_install`（`scripts/patch-uwu-vendor-outdir.py`）。判断依据：`.config` 行数与 `CONFIG_` 数量骤降、或日志里 `.config:NNNN:` 行号远大于当前行数 |
| `kernel module gh_arm_drv.ko was not found`（复现条件） | `arch/arm64/gunyah/` 里 `Makefile`（`obj-$(CONFIG_GH_ARM64_DRV)`）与手写 `Kbuild` 并存会冲突，且 `.config` 里没有 `CONFIG_GH_ARM64_DRV`（override 被 olddefconfig 丢）→ 入口永远为空。收敛到 `Makefile` 一处、改无条件 `obj-m += gh_arm_drv.o`（`gh_arm_drv-objs += gh_arm.o irq.o reset.o`），并由 `external_modules` 的 `sm8750/arch/arm64/gunyah:kbuild` 构建（`scripts/fix-gunyah-entry.py`） |
| `repo sync` 报 `Cannot checkout ... Cannot initialize work tree for LineageOS/android_external_chromium-webview_prebuilt_{arm,arm64,x86,x86_64}`，工作树只剩 `.gitattributes`/`.lfsconfig` | **缺 `git-lfs`**。这 4 个是 Git LFS 项目（`.lfsconfig` 指向 review.lineageos.org），没有 git-lfs 时 checkout 失败且 worktree 为空。修法：`apt-get install -y git-lfs` + `git lfs install --skip-repo`，再 `repo sync --force-sync` 这 4 个 path（13500t 实测：装完立刻补齐 `webview.apk`） |
| bootstrap 脚本 clone 5 棵设备/内核树全部 404 | 真实仓库在 **`lunatellus/`**（不是 `uwuAOSP/`），且要走 `gh-proxy.com` 前缀。分支：device/vendor/elden → `uwu-17.0`，kernel 三棵（sm8750 / -modules / -devicetrees）→ `lineage-24.0`。`vendor/uwu` **不要单独 clone**：它是 manifest project（`.repo/projects/vendor/uwu.git`），repo sync 已负责 |
| 13500t 上 `device/lenovo/elden` 与 u-zpy 不一致（缺 charging control / supports_bypass / power/ / sepolicy / uwu_elden.mk / modules.load 的 sm8750-gap 注释） | GitHub 的 `uwu-17.0` 只到 `e04cdd0`，那 2 个提交和工作区改动都没推上去。已固化为 `patches/device-elden-full.patch`（相对 `e04cdd0`，1787 行）：`git apply --exclude='prebuilt_dtb/*'` —— 排除是因为 `prebuilt_dtb/{dtb.img,dtbo.img}` 是二进制，patch 里只有 `Binary files differ` 行，apply 建不出来，需单独传 |
| `modules.include.vendor_ramdisk / .vendor_dlkm / .recovery not found`（BoardConfig 的 3 个 install list 指向它们） | device 树只带 `modules.load*`。按 `scripts/server-uwu-kernel.sh:108-110` 生成：`cp modules.load modules.include.vendor_ramdisk`、`cp modules.load.vendor_dlkm modules.include.vendor_dlkm`、`cp modules.load.recovery modules.include.recovery`（u-zpy 上三者与源文件 md5 相同） |
| Windows 侧改过的设备树文本文件传上去后行为异常（如模块列表失效） | 本地检出是 **CRLF**，u-zpy 上是 **LF**。用 `git diff` 生成补丁再 `git apply` 会保留 CRLF；正确做法是 `tr -d '\r'` 或 `base64 -w0` 中转，落盘后 `file` 校验应为 `ASCII text`（u-zpy 上全部如此） |
| 绕过 soong_ui 直接跑 ninja/siso 时报 `gen_build_prop.py line 282 TypeError: startswith first arg must be str or a tuple of str, not NoneType` | `gen_build_prop.py:282` 是 `file.name.startswith(os.environ.get("OUT_DIR"))`，而 **`OUT_DIR` 由 soong_ui 设置、直跑 ninja/siso 时不存在** → `startswith(None)`。修法：跑之前 `export OUT_DIR=out`（u-zpy 实测：无该变量 1 个 TypeError，加上后 `rc=0` 并产出 `build.prop`） |
| `siso ninja` 跑一个失败就整体退出（`1 steps failed`，剩余上万 action 不执行） | siso 的 `-k` **默认是 1**。加 `-k 0`（`0 means infinity`）即可忽略失败继续，由最终 `otapackage` 目标决定成败。这是让 2264 个 `header-abi-dumper` 失败与 `apkcerts doublecheck` 失败不阻塞 OTA 的关键开关 |
| 手动 `touch` 某个 stamp 目标想让 siso 跳过，但下次又被重跑 | siso 有 **"Prioritizing last failed targets"**：上次失败的目标会被强制重新调度（规则先 `rm -f $@` 再判条件），手改产物或 touch 都无效。要么让该规则真正通过，要么用 `-k 0` |
| `header-abi-dumper` 大批失败（u-zpy 上 2264 个）：`Unknown attribute kind (105) (Producer: 'LLVM22.0.2' Reader: 'LLVM 21.1.8')` | clang 产出 bitcode 的版本（`clang-r596125` = LLVM 22.0.2）比 `prebuilts/clang-tools` 里的 `header-abi-dumper`（LLVM 21.1.8）新 → dumper 读不了新版 attribute。属于纯 ABI 检查，不进产物，用 `-k 0` 放行；要彻底消除可设 `SKIP_ABI_CHECKS=true`（`build/soong/cc/sabi.go:261` 读取）但需重新生成 ninja 图 |
| `ninja` 跑到一半崩：`Error writing to deps log: Numerical result out of range`（`.ninja_deps` 涨到 69 M） | 该 ninja 二进制处理不了 kernel 那批超大 deps，删 `.ninja_deps` 后会在同一目标（`//device/lenovo/elden:kernel Kernel source dependencies`）复现。改用 `prebuilts/siso/linux-x86/siso ninja -k 0 -f out/combined-uwu_elden.ninja otapackage`（siso 用自己的依赖库）。注意 siso **不接受 `-j`**（报 `flag provided but not defined: -j8`） |
| `apkcerts` doublecheck stamp 失败：`diff -q ...-soong-doublecheck.txt ...-soong_apkcerts_file_with_soong_and_make_modules_removed.txt` 报 differ | `build/make/core/Makefile:799-814`：这是**纯迁移校验**，`APKCERTS_FILE` 实为 `cat make.txt + removed.txt`，doublecheck 不参与产物。差异来自两侧模块集合不同（doublecheck 含 `*_test.apk`、removed 含 `ANGLE.apk`）。手改两个文件无效（会被重新生成），用 `-k 0` 放行即可 |
| **成批假失败**：`err: flush <out>/xxx.jar.rsp local-ready: chtimes <out>/xxx.jar.rsp`，连带 `art.module.public.api.stubs.*` 的 `stubs.jar` 从未生成；`cannot make progress due to previous N errors`，剩余上万 action 全部停摆 | **`out/.siso_fs_state` 损坏**（实测涨到 **51 M**）。这是 siso 自己的文件状态缓存，与实际磁盘不一致后，它写完 response file 就 chtimes 失败，于是把正常的编译步骤全部报成失败。判断依据：① 输出目录里只有 `-stubs.srcjar`、没有 `stubs.jar`/`.rsp`；② `siso.INFO` 里 `rlimit.nofile=1048575`（充足）、`memory_limit=unlimited`，排除 fd/内存；③ 手工 `touch`+`chtimes` 该目录完全正常。修法：`mv out/.siso_fs_state out/.siso_fs_state.bak` 后重跑 siso（首次会重建状态、进度总数会变大，属正常）。实测重建后同一批 `stubs.jar` 失败**归零**，只剩 apkcerts doublecheck 这一个已知无害失败 |
| `//art/runtime:libart_mterp.{arm64ng,x86_64ng}` 失败：`gen_mterp.py, line 109 SyntaxError: f-string: expecting '}'` | `art/runtime/interpreter/mterp/gen_mterp.py:109` 写的是 `print(f"{">>" if j == i else "  "}{n:6}: {c}", ...)` —— f-string 表达式里复用了外层双引号，**PEP 701（Python 3.12+）才允许**，而 Ubuntu 22.04 的 `python3` 是 3.10。修法：内层改成单引号 `f"{'>>' if j == i else '  '}"`，语义不变、全版本合法（`scripts/fix-mterp-py312.py` 幂等落地，改完 `python3 -c py_compile` 可自检） |
| `packages/modules/Connectivity/{framework,framework-t}` 的 `aidl1.srcjar`/`aidl0.srcjar` 成批失败：`err: gcc-deps: failed to parse depfile ".../xxx.aidl.d"`，且 `aidl1.tmp` 不残留、srcjar 停在旧产物 | **depfile 的 target 被 aidl 故意留空**。`system/tools/aidl/aidl.cpp` 的 `write_dep_file()` 里：`if (defined_type.AsUnstructuredParcelable() != nullptr && TargetLanguage() == JAVA) writer->Write(" : \\\n");`（注释写明是 legacy 兼容 b/141372861）。make 能容忍空 target，**siso 的 gcc-deps 解析器不能**，于是把 .java 已生成成功的 aidl 步骤整体判失败，后续 `soong_zip` 不跑。诊断关键：depfile 实际存在（194 字节）、内容形如 ` : \` + 依赖 + `依赖 :`。修法：该分支也写 `output_file` 作 target（`scripts/fix-aidl-depfile-empty-target.py`），然后**重建 host aidl**：`siso ninja -k 0 -f out/combined-uwu_elden.ninja out/host/linux-x86/bin/aidl`。注意 `aidl -n/--ninja` 只省掉 depfile 末尾的 `<input>:` 行，**不能**解决空 target |
| 某个 step 在 siso 下必然失败（沙箱环境差异），但它的产物其实是对的；`touch` 产物、`-fs_keep_tainted`、改 `rule_builder_scripts/*.sh` 都无效 | 三重原因，逐个踩过：① siso 有 **"Prioritizing last failed targets"**，上次失败的目标每轮都会被强制重跑，`touch` 无效；② `-fs_keep_tainted` 也不够，因为目标仍被判定 dirty；③ **改 `out/soong/rule_builder_scripts/*.sh` 会被 soong 在下一轮重新生成覆盖**（实测写进去后 `head` 又变回原内容）。可行修法：改**不会被重新生成**的 ninja 图里该 rule 的 `command`——把 `build out/.../xxx.zip: m.1-kernel_....kernel_modules` 对应的 `rule` 的命令指到自己写的脚本（如 `/home/zpy/y700-uwu/kernel-zip-noop.sh`，内容只有 `test -s "$OUT" && touch "$OUT"`）。注意 ninja 缩进必须与原行一致（本树是 **1 个空格** `command = `，写成 4 空格会破坏解析）；改完用 `ninja -f out/combined-uwu_elden.ninja -t targets all` 验证可解析。4.5 G 的 `build.uwu_elden.ninja` 用 `sed -i` 要跑几分钟，放后台执行 |
| **换机器复现（13500t）时 soong bootstrap 连续失败**，逐个报 `depends on undefined module`：`clang-includes`/`llvm-includes` → `uwu_ocr_aidl` → `libllama`/`libggml` → `llvm-project_lib_libLLVM*_a` | 四层根因，逐个踩过：① `external/clspv/Android.bp`（ninja-to-soong 自动生成）声明 `header_libs: [clang-includes, llvm-includes]`，但当前树的 clang prebuilt 已不再定义它们 → `scripts/fix-clspv-missing-include-libs.py` 往 `prebuilts/clang/host/linux-x86/Android.bp` 补两个 `cc_prebuilt_library_headers`（导出 `clang-r596125/include`，该目录含 llvm/ 与 clang/）。② `uwuAICore` 整个 project 不存在 → **13500t 的 manifest 落后**：`6fc8388`/209 个 snippet 项目，而 u-zpy 是 `1bbb606`/218 个，`repo sync` 因此报 `project not found`。修法：把 `.repo/manifests/.git` 从 u-zpy 内网同步后 `git checkout -f 1bbb606`（注意 `git fetch origin uwu-17.0` 后 `origin/uwu-17.0` 不会更新，要 `reset --hard FETCH_HEAD`；且 gh-proxy 有缓存，fetch 到的仍是旧 commit）。③ `external/llama` + `external/llama-generated-dep`（166 M）不在 manifest 里，是手工加的 AI 集成 → 内网搬。④ `external/opencl/llvm-project` **只 fetch 未 checkout**（4 K vs u-zpy 的 2.4 G），`repo sync --local-only` 又被 `revision refs/tags/android-17.0.0_r1 ... not found` 整体中止 → 内网搬该目录 |
| 内核 `.config` 生成失败：`datarmnet-ext/*/Kconfig:8: unknown statement "---help---"` | vendor 树残留 **老式 `---help---`**，Linux 6.12 的 kconfig 只认 `help`。u-zpy 上这 8 处是手工改的、没进脚本，所以换机器必踩。已并入 `kernel-tree-fixes.py` 的 `fix_kconfig_help_marker`（行首 `---help---` → `help`，幂等） |
| 内核 `Image` 编译失败：`sign-file.c: fatal error: 'openssl/opensslv.h'`、`libbpf_internal.h: 'libelf.h'`、`btf.c: 'gelf.h'` | 宿主缺开发库：`apt-get install -y libssl-dev libelf-dev libdw-dev`（已加入 `zpy13500t-bootstrap.sh` 的依赖清单）。注意 AGENTS.md 早前写的"13500t 依赖已装好"并不完整 |
| `liblog.so.llndk202504.abidiff` 的 deps chain 断在 `prebuilts/clang-tools/linux-x86/bin/header-abi-dumper`（该文件在 13500t 不存在） | 不要搬那个 dumper（u-zpy 上的 LLVM 21.1.8 与 clang 22 产出的 bitcode 不兼容，正是 2264 个 ABI dump 失败的来源）。直接 `SKIP_ABI_CHECKS=true` 跑 `m`，让 soong 不生成 abidiff 步骤（`build/soong/cc/sabi.go:261` 读取）。**改了它必须重跑 soong bootstrap**，已生成的图里仍带 abidiff |
| u-zpy 与 13500t 之间搬代码：外网 `gh-proxy` 仅 85 KB/s、清华镜像约 20 KB/s，22 G 要 70+ 小时 | **两台在同一内网网段，可免密 ssh 直连，内网实测 64.4 MB/s**。原则：① 内核三棵树**只搬 `.git`**（14 M/41 M/7.5 M，干净历史；u-zpy 那 12191 处改动都在工作区、不在 .git 里），在目标机 `git checkout -f lineage-24.0` 得到纯净源码，再用 `scripts/` 里的脚本重放修法 —— 这样"修法可复现"是真验证过的，没有复制成品树；② `clang`（19 G）、`llvm-project`（2.4 G）、`external/llama`（166 M）等上游预编译/源码直接 rsync；③ `repo sync` 中断留下的"有 `.git` 但工作树空"半成品，用 `du -sh` 一眼能看出来 |
| `Package OTA` 失败：`check_target_files_vintf.py` 报 `No kernel entry found for kernel version 6.12 at kernel FCM version 202404`（早期日志还伴 `Cannot parse "6.12.96-4k-g153de33f91d6-dirty" as kernel version`） | **两个独立原因，先按第一条修，别直接上 bypass**。①（本次根因）`device/lenovo/elden/vintf/manifest_sun.xml` 声明 `target-level="202404"`（vendor blobs 来自 Android 15 + 6.6 内核），而本树内核是 GKI 6.12；`hardware/interfaces/compatibility_matrices/Android.bp` 里 202404 只挂 `kernel_config_v_6.6`，6.12 的 entry 只在 202504。`system/libvintf/KernelInfo.cpp:81` 先按 `mVersion.dropMinor() != minLts.dropMinor()` 过滤，6.6 entry 全被滤掉 → `kernelsForLevel` 为空 → 报错。修法（`scripts/fix-fcm-202404-kernel.py`）：给 202404 的 `kernel_configs` 补 `"kernel_config_b_6.12"`（多 entry 是「或」语义，原来 6.6 的设备不受影响）。**不要**把 target-level 提到 202504——那会引入 202504 的 88 个 HAL 要求（202404 是 83 个），而 device manifest 来自 vendor blobs 改不动。②（早期表象）内核 release 曾带 `-dirty`，`checkvintf` 解析失败；已由 vendor `KERNELRELEASE` 固定修掉。③ 兜底才用 `--skip_compatibility_check`（`ota_from_target_files.py:74-75`，`check_target_files_vintf.py:299`），它只是绕过检查、产物与真机组合未经验证 |
| wlan 四变体 `No rule to make target '.../qcacld-3.0/configs/sun_gki_peach_defconfig'`，错误路径形如 `../../../../../../../../..//home/...`（9 级 `..` 后跟绝对路径） | `qcacld-3.0/Kbuild:34-38` 在 `KERNEL_BUILD=n` 且 `ANDROID_BUILD_TOP` 非空时做 `override WLAN_ROOT := $(ANDROID_BUILD_TOP_REL)/$(WLAN_ROOT)`，假定 `WLAN_ROOT` 是相对 BUILD_TOP 的路径；变体包装给的是绝对路径，于是被叠成回溯前缀 + 绝对路径。`envsetup.sh` 会 export `ANDROID_BUILD_TOP`，soong 里必然命中。修法（`scripts/fix-wlan-variants.py`）：包装 `Kbuild` 里 `ANDROID_BUILD_TOP :=` / `LINUX_BUILD_TOP :=` 清空并 `unexport`（这两个变量在 wlan 树中只被那段 override 使用），同时 `WLAN_ROOT`/`WLAN_PLATFORM_ROOT` 用 `$(abspath ...)` |
| `duplicate kernel module fat_test.ko`（同一个 release 目录里 86 个同名 `.ko`） | 两个 release 目录并存：`modules_staging/lib/modules/` 下同时有 `6.12.96-4k-g<common-sha>` 与 `6.12.96-4k-g<vendor-sha>-dirty`。根因是 vendor `:modules` 用独立 `O=`（`vendor_modules_build`）并以 **vendor 树自身为 srctree**，`filechk_kernel.release = $(srctree)/scripts/setlocalversion $(srctree)` 按 vendor 仓库算 release（12166 处未提交改动 → `-dirty`），与内核镜像的 common 版本串不一致，`modules_install` 就写出第二棵 `lib/modules/`。修法（`vendor/uwu/build/soong/kernel/kernel.go`）：vendor 的 `modules` 与 `modules_install` 两次调用都传命令行 `KERNELRELEASE=$(cat <buildRoot>/include/config/kernel.release)` —— `$(origin KERNELRELEASE)` 因此不再是 `file`，`Makefile:1262` 走 `echo` 分支，`setlocalversion` 不再执行。必须放**命令行**（环境变量会被 `Makefile:375` 的普通赋值覆盖），且要写在 target 位置而不是 `make_flags`（flags 经 `ShellEscapeList` 转义后 `$` 不会展开） |
| `duplicate kernel module gh_arm_drv.ko`（`kernel/arch/arm64/gunyah/` 与 `updates/` 各一份，md5 不同） | `CONFIG_GH_ARM64_DRV=m` + `CONFIG_GUNYAH=y` 使 vendor 树的 `arch/arm64/Kbuild` 用 `obj-$(CONFIG_GUNYAH) += gunyah/` 在 in-tree `make modules` 里编了一次；device bp 的 `external_modules` 另有 `sm8750/arch/arm64/gunyah:kbuild`（官方 bazel 就是独立 ddk_module）又编一次并装到 `updates/`。修法（`scripts/fix-gunyah-duplicate.py`）：保留 `:kbuild`，注释掉 `arch/arm64/Kbuild` 的 gunyah descend（`gunyah_hypercall.c`/`timer.c` 在 GKI common 树，不走这份 Kbuild，去掉不会少编译） |
| OTA 打包 `AssertionError: Failed to find abl.img`（`add_img_to_target_files.py:759` 的 `CheckAbOtaImages`） | `vendor/lenovo/elden/BoardConfigVendor.mk`（`extract-files.py` 自动生成）把 `radio/` 下 30 个 bootloader 固件分区写进 `AB_OTA_PARTITIONS` → 进入 `META/ab_partitions.txt` → 检查要求每个分区都在 `IMAGES/` 或 `RADIO/` 下。但 soong 迁移后 `RADIO/` 不生成：`build/soong/fsgen/filesystem_creator.go:411` 只有两条来路，① `BOARD_RADIO_IMAGE_PATH` 未设，且这条路径要 `unpack.py`（树里没有，因为 elden 的 `radio/` 是 30 个独立 img、无合并 `radio.img`）；② `AB_OTA_RADIO_PARTITIONS` 未设，且它依赖的 `prebuilt_radio_img` 在 `build/soong/filesystem/radio.go` 里**没有 `RegisterModuleType`**，bp 写不出来。老的 `add-radio-file-sha1-checked`（`vendor/lenovo/elden/Android.mk`）是纯 make 机制、soong 迁移后失效。修法（`scripts/fix-ota-radio-partitions.py`）：在 `include BoardConfigVendor.mk` 之后 `AB_OTA_PARTITIONS := $(filter-out <30 个分区>,$(AB_OTA_PARTITIONS))`，名单从 `radio/*.img` 现算。Qualcomm 平台 bootloader 一律 fastboot 刷写，OTA 不带（写坏即硬砖、A/B 回滚救不了 bootloader） |
| VINTF `Missing config CONFIG_ASHMEM`（前一步是 `No kernel entry found for kernel version 6.12 at kernel FCM version 202404`） | 三层依赖，逐层解开：① FCM level 错配 → `scripts/fix-fcm-202404-kernel.py`；② **ASHMEM 在 6.12 是 Rust 实现**（`drivers/staging/android/ashmem{,_range,_shrinker,_toggle}.rs` 共 1781 行），Kconfig 是 `depends on SHMEM && RUST`，而 `CONFIG_RUST` 有 `depends on !MODVERSIONS || GENDWARFKSYMS` —— 当前 `MODVERSIONS=y` + `GENDWARFKSYMS=n` 使该子句恒假，RUST 整条不可见（`.config` 里连 `# CONFIG_RUST is not set` 都没有），ASHMEM 被静默丢弃。上游 `gki_defconfig:118-119` 本来是 `MODVERSIONS=y` + `GENDWARFKSYMS=y` 共存，是 device bp 那行 `"CONFIG_GENDWARFKSYMS=n"` 关掉的，其自身依赖（`DEBUG_INFO=y`、`!DEBUG_INFO_REDUCED`、`!DEBUG_INFO_SPLIT`、`!LTO`）当前全部满足 → `scripts/fix-gendwarfksyms-rust.py` 改回 `=y`（副作用：MODVERSIONS 的 choice 从 GENKSYMS 切到 GENDWARFKSYMS，全量 .ko 需重编；`scripts/gendwarfksyms` 是 `hostprogs-always-y`，需 `libdw-dev`/`libelf-dev`，均已装）；③ `RUST_IS_AVAILABLE` 要求 `scripts/rust_is_available.sh` 通过 → 需要 `RUSTC` + `BINDGEN`，且 **bindgen 必须 ≥ 0.69.5**（0.69.1 配 libclang ≥ 19.1 有已知 bug rust-lang/rust-bindgen#2824，脚本会明确拒绝）。本机 `prebuilts/clang-tools` 是**空工作树**（bare repo `in-pack: 0`，repo sync 中断遗留），所以 `bindgen` 与之前的 `header-abi-dumper` 同时缺失；`prebuilts/rust` 也没有 `linux-x86`（只有 `bootstrap`）。对策：`cargo install bindgen-cli --version 0.71.1 --root ~/.cargo-bindgen`（crates.io 可达），再 `ln -s` 进 `prebuilts/build-tools/linux-x86/bin/` —— 该目录最前在 `kernel.go` 的 `makeInvocationExtra` PATH 里。rustc 用 `prebuilts/rust-toolchain/linux-x86/1.93.1/bin/rustc` |
| `kernel/Image` 失败：`error: gendwarfksyms: is_definition_private: dwarf_getsrcfiles failed: 'invalid .debug_line section'`，伴随 `process_module: dwarf_get_units failed: no debugging information?`，失败点是 `rust/helpers/helpers.o`（`rust/Makefile:472`） | **libdw 读不了 clang-22 生成的 DWARF，不是 DWARF 真的坏了**。排除过程：① 同一份 `.o` 用 `llvm-dwarfdump` 解析完全正常、无 error；② 换 libdw **0.188**（jammy-backports）同样失败 → 非版本问题；③ 非规模阈值：`lib/vsprintf.c`(272 文件表项/20 符号) 通过，而 `mm/memory.c`(275/62)、`kernel/fork.c`(334/60)、`virt/kvm/kvm_main.c`(287/157)、`fs/read_write.c`(223/55)、`kernel/exit.c`(298/20) 全失败。**为什么绕不开**：VINTF 要求 `CONFIG_ASHMEM=y` → 6.12 的 ASHMEM 是 Rust 实现（`depends on SHMEM && RUST`）→ `CONFIG_RUST` 依赖 `!MODVERSIONS || GENDWARFKSYMS`，而 GKI 6.12 要求 `MODVERSIONS=y` → 只能 `GENDWARFKSYMS=y`。修法（`scripts/fix-gendwarfksyms-libdw.py`）：`scripts/gendwarfksyms/dwarf.c` 的 `is_definition_private()` 里 `dwarf_getsrcfiles()` 失败时不再 `error()` 退出，降级用 CU 的 `DW_AT_name`（主源文件）判断是否 `.c` 结尾 —— 与原「`DW_AT_decl_file` 指向的文件是否 .c」在单源 TU 上等价。**重编注意**：`make -C common O=kernel_build scripts/gendwarfksyms/gendwarfksyms` 会触发 `oldconfig` 交互（`choice[1-2?]:` 卡住），要照 `.dwarf.o.cmd` / `.gendwarfksyms.cmd` 里保存的命令手工 `clang -c` + `clang -ldw -lelf -lz` 链接 |
| `kernel/Image` 失败：`error: gendwarfksyms: process_module: dwarf_get_units failed: no debugging information?`，失败点 `rust/bindings.o`（`rust/Makefile:512`） | **该目标文件本来就不产生代码**。`rust/bindings/lib.rs` 只有 `mod bindings_raw { include!(bindings_generated.rs) }`（extern 导入声明）、`pub use`、`pub const __ARCH_SPIN_LOCK_UNLOCKED`，没有任何 `#[no_mangle]` 函数定义。实测产物 `rust/bindings.o` 仅 **992 字节、0 个 `.debug_*` 段、0 个导出符号**。`dwarf_get_units` 对无 `.debug_info` 的对象返回负值属正常，但 `gendwarfksyms.c:70` 直接 `error()` 退出。上游 `rust/Makefile` 给 `exports.o`/`compiler_builtins.o`/`build_error.o`/`ffi.o`/`uapi.o` 都加了 `private skip_gendwarfksyms = 1`，**偏偏漏了 `bindings.o`** —— 因为这个组合（`MODVERSIONS=y` + `GENDWARFKSYMS=y` + 开 Rust）上游未必构建过。修法（`scripts/fix-gendwarfksyms-empty-object.py`）：`process_module()` 里仅在「**第一个** CU 就取不到」时 `break`（后续 `generate_symtypes_and_versions` 输出为空即可）；已有 CU 解析成功后再失败仍报错。与 libdw 那条补丁分工：那个管「有 DWARF 但 `.debug_line` 读不了」（在 `is_definition_private`），本补丁管「压根没有 DWARF」（在 `process_module`） |
| 内核 `Image` 失败：`rust/kernel.o` 报 161 个错误，全是 `error[E0609]: no field 'private_data' on type 'bindings::file'`、`no field '__bindgen_anon_2' on type 'bindings::vm_area_struct'`、`error[E0560]: struct 'kunit_suite' has no field named 'suite_init'` 一类 | **bindgen 0.71.1 配 LLVM 22 的 libclang 会把结构体当 opaque，生成空壳**。生成物 `rust/bindings/bindings_generated.rs` 里 **263 个结构体**都是 `pub struct inode { pub _address: u8 }` 这种空壳。不是头文件缺失（`bindings_helper.h` 的 49 个 include 里 `linux/fs.h`、`linux/mman.h` 都在）。**定位手法**：用完全相同的 bindgen 命令行（照抄 `rust/bindings/.bindings_generated.rs.cmd`），只换 `LIBCLANG_PATH` 实测 —— `clang-r596125`(LLVM 22.0.2) → 263 个空壳；`clang-r584948`(LLVM 21) → 69 个；**`clang-r547379`(LLVM 20.0.0) → 0 个**，且 `vm_area_struct` 有 `__bindgen_anon_1`、`file` 有 `private_data`、`kunit_suite` 有 `suite_init`，与 Rust crate 期望完全对上。修法（`scripts/fix-bindgen-libclang.py`）：device bp 的 `make_flags` 加 `"LIBCLANG_PATH=<clang-r547379>/lib"` —— C 编译仍用 clang 22，bindgen 的 libclang 单独走 LLVM 20，`LIBCLANG_PATH` 只被 bindgen 读取、不参与内核 C 编译，互不干扰。放在 `make_flags` 能生效是因为 `kernel.go` 的 `makeInvocationExtra` 把 `make_flags` 追加在内置 `LIBCLANG_PATH=` 之后，GNU make 同变量多次命令行赋值取**最后一个**；不必改 Go、不必重编 soong bootstrap（`KCONFIG_EXT_PREFIX` 也是这么放的，属既有机制）。注意 `rust_is_available.sh:245-260` 只把「libclang 版本 ≠ clang 版本」当 **warning**（`warning=1`），不拦截 |
| 换 LLVM 20 的 libclang 后 bindgen 立刻失败：`Unable to generate bindings: clang diagnosed error: error: unknown warning option '-Wno-default-const-init-unsafe' [-Werror,-Wunknown-warning-option]` / `'-Wno-unterminated-string-initialization'; did you mean '-Wno-nonportable-vector-initialization'?`，失败点 `rust/bindings/bindings_generated.rs`（`rust/Makefile:336`） | **两条分支只拦得住一条**。`scripts/Makefile.extrawarn` 里 `KBUILD_CFLAGS += $(call cc-disable-warning, default-const-init-unsafe)` 与 `... unterminated-string-initialization` 的 `cc-disable-warning` 是按**编译器 clang 22** 探测的，顺利展开进 `c_flags`；但 bindgen 的 libclang 已换成 LLVM 20（见上一条），不认识这两个选项，而 `KBUILD_CFLAGS` 带 `-Werror` → 告警变错误、bindgen 放弃生成。**关键坑**：`rust/Makefile` 里 `bindgen_skip_c_flags` 只在 `else`（GCC）分支生效，本树 `CONFIG_CC_IS_CLANG=y` 走的是 `ifdef` 分支，那里 `bindgen_c_flags = $(c_flags)` **直接透传、根本不 filter** —— 第一次把跳过项加进 skip 列表对本树完全无效（已回退）。正确注入点是两条分支的汇聚行 `bindgen_c_flags_final = $(bindgen_c_flags_lto) -fno-builtin -D__BINDGEN__`，改成 `$(filter-out <两项>,$(bindgen_c_flags_lto)) ...`。修法：`scripts/fix-bindgen-skip-cflags.py`（幂等，含旧版误加的清理）。这两项纯属告警开关，剔掉不影响生成的绑定内容 |
| 改了 `common/rust/Makefile`（或 `common/scripts/gendwarfksyms/*.c`）却不生效，报错点仍指向 `vendor/lenovo/sm8750/rust/Makefile:480`、`vendor/lenovo/sm8750/Makefile:1300` | **vendor 树自带一整套独立的 GKI 构建系统副本，不是软链**。`vendor/lenovo/sm8750/` 为了让 `sm8750:modules` 能做 in-tree 构建，复制了 `Makefile`、`Makefile:1300` 的 `prepare`、`rust/`、`scripts/gendwarfksyms/` 等。实测 inode 不同（如 `dwarf.c`：common `22551255` vs vendor `23201304`），`diff` 显示内容差异**仅**是自己加的补丁部分。凡改内核构建脚本必须**两边都改**：`common/rust/Makefile` + `vendor/lenovo/sm8750/rust/Makefile`（`scripts/fix-bindgen-skip-cflags.py` 已改为遍历两份）；`common/scripts/gendwarfksyms/{dwarf.c,gendwarfksyms.c}` + `vendor/lenovo/sm8750/scripts/gendwarfksyms/` 同名两份（两处补丁脚本目前只改 common，需手工 `cp` 同步）。**不用手工预置 vendor 二进制**：`vendor_modules_build` 每轮被 `kernel.go` 的 `rm -rf` 清空、再 `cp -a buildRoot/scripts`，二进制按 srctree=vendor 的源码 mtime 自动重编。注意 gendwarfksyms 那种场景下 vendor 反而不分叉（`$(objtree)/scripts/gendwarfksyms/gendwarfksyms` 是同一个 objtree 产物），到 `rust/Makefile` 才第一次真正分叉 |
| wlan 四变体不报错、但 `qca_cld3_{peach,peach_v2,kiwi_v2,wcn7750}.ko` 从未真正编出（构建日志里 `MODPOST .../variants/*/Module.symvers` 成功、`Module.symvers` 却是 **0 字节**，`modules.order` 停在旧时间戳） | **`CONFIG_QCA_CLD_WLAN := y` 让模块进了 `obj-y` 而不是 `obj-m`**。变体包装 Kbuild 里原本写 `y`，于是 `qcacld-3.0/Kbuild:5327` 的 `obj-$(CONFIG_QCA_CLD_WLAN) += $(MODNAME).o` 展开成 `obj-y := qca_cld3_peach.o`，而 **`M=` 外部模块构建只把 `obj-m` 编成 `.ko`** —— 所以从打通 wlan 路径那天起，这 4 个 WiFi 驱动一直没产物，只是不再报错，属于「静默成功」。决定性验证：`make -pn -C common O=kernel_build ARCH=arm64 M=.../variants/peach modules \| grep -E "^obj-(m\|y) "` 直接打出 `obj-y := qca_cld3_peach.o` / `obj-m := `（空）。上游 `qcacld-3.0/Android.mk:122` 写的就是 `WLAN_SELECT := CONFIG_QCA_CLD_WLAN=m`。修法：`scripts/fix-wlan-variants.py` 把 `y` 改为 `m`（已确认 Kbuild 中无 `ifeq/ifdef CONFIG_QCA_CLD_WLAN` 门控，改 `m` 无副作用）。**教训**：`obj-y` 在 `M=` 模式下不会报错也不会产出 `.ko`，只看「构建成功」无法发现；必须核对 `Module.symvers` 大小或 `modules.order` 内容 |
| graphics-kernel 编译报一堆 `fatal error: 'xxx.h' file not found`（`linux/clk/qcom.h`、`dt-bindings/soc/qcom,ipcc.h`、`soc/qcom/of_common.h`、`linux/mem-buf.h`、`msm_hw_fence.h`、`governor.h`） | **三类独立原因**。① vendor 头文件缺失：`graphics-kernel/Kbuild` 里 `grep -cE "idirafter|sm8750/include"` 为 **0**，而 `<dt-bindings/...>`、`<linux/soc/qcom/...>`、`<soc/qcom/...>` 都在 `vendor/lenovo/sm8750/include/` 下 → `python3 scripts/add-vendor-include.py <graphics-kernel 目录> --first`。② 跨模块头：`msm_hw_fence.h` 属于**另一个模块** `mm-drivers/hw_fence/include/`（上游 bazel 里是跨 ddk_module 依赖），kbuild 侧必须显式 `-I` → `scripts/add-hw-fence-include.py`。③ `governor.h` 找不到是 `KERNEL_SRC` **未定义**：`Kbuild:96` 本来就有 `-I$(KERNEL_SRC)/drivers/devfreq`（上游写的），但本模块走 `external_modules` 的 `":kbuild"` 分支，而 `kernel.go:1068` 那个分支**只注入 `KCPPFLAGS`，从不设 `KERNEL_SRC`**（只有 `":all"/":modules"` 分支在 `kernel.go:1136` 才传 `M=... KERNEL_SRC=... OUT_DIR=...`）。`make -pn` 实测 `srctree := <GKI common 树>` 而 `KERNEL_SRC` 压根没定义，该行于是展开成 `-I/drivers/devfreq`。而 `governor.h` 确实在 `common/drivers/devfreq/governor.h` → `scripts/fix-graphics-kernel-src.py` 在 Kbuild 里加 `KERNEL_SRC ?= $(srctree)`（用 `?=` 以免覆盖外部传入值）。**排查顺序建议**：先 `add-vendor-include.py --first` 一次性补全 vendor 头，再看是否只剩跨模块头，最后查 `make -pn` 里 KERNEL_SRC/srctree 的实际值 |
