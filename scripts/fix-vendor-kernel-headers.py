#!/usr/bin/env python3
"""把 vendor 内核树的 uapi 头并入 TARGET_BOARD_KERNEL_HEADERS 指向的源树目录。

背景（13500t 换机复现时连踩两处）：
  BoardConfig.mk 里
      TARGET_BOARD_KERNEL_HEADERS := device/lenovo/elden/kernel-headers
  而 vendor/uwu 的 kernelHeadersModule.GenerateAndroidBuildActions 首先读
      ctx.DeviceConfig().DeviceKernelHeaderDirs()
  （= soong 的 productVariables.DeviceKernelHeaders，见 build/soong/android/config.go:2036），
  所以这个**源树目录**是 vendor 侧 uapi 头最稳定的落点。

  新机器上该目录只带 device 树自有的 9 个 audio 头，于是会出现：
      ar_osal_shmem_db.c: 'linux/msm_audio.h' file not found
      gr_adreno_info.h:   'display/media/mmm_color_fmt.h' file not found
  u-zpy 之所以没事，是它的 ar_osal/gralloc 早就编译过，增量构建直接跳过。

  注意：**不能**把 uapi 头塞到 out/soong/.intermediates/**/headers/usr/ 下——
  soong 每次构建都会重新生成那个目录，手工放进去的文件会被覆盖（实测两次）。
  另外从 u-zpy 复制 kernel/platform/kernel-6.12/out/bazel 也没用：里面全是指向
  u-zpy 绝对路径的沙箱软链，换机器后 10 万条全变断链，还会让 soong 报
  "FAILED: bootstrap blueprint"。

幂等：同名文件内容一致则跳过。
用法：python3 fix-vendor-kernel-headers.py [AOSP 根目录]
"""
import os
import filecmp
import pathlib
import shutil
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else _Y700_WORK + "/aosp")
VENDOR = AOSP / "kernel/platform/kernel-6.12/vendor/lenovo"
DEST = AOSP / "device/lenovo/elden/kernel-headers"

if not VENDOR.is_dir():
    print("  skip: %s 不存在" % VENDOR)
    sys.exit(0)

DEST.mkdir(parents=True, exist_ok=True)
uapi_dirs = sorted(d for d in VENDOR.rglob("uapi") if d.is_dir())

copied = skipped = 0
for src in uapi_dirs:
    for f in src.rglob("*"):
        if not f.is_file():
            continue
        dst = DEST / f.relative_to(src)
        if dst.is_file() and filecmp.cmp(str(f), str(dst), shallow=False):
            skipped += 1
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(f), str(dst))
        copied += 1

total = sum(1 for p in DEST.rglob("*") if p.is_file())
print("  uapi 目录: %d   新增/更新: %d   跳过(已相同): %d" % (len(uapi_dirs), copied, skipped))
print("  %s 现有 %d 个文件" % (DEST, total))
for probe in ("linux/msm_audio.h", "display/media/mmm_color_fmt.h", "msm_audio_calibration.h"):
    print("    %-40s %s" % (probe, "ok" if (DEST / probe).is_file() else "缺"))
