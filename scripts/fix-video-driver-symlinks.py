#!/usr/bin/env python3
"""补齐 video-driver 的 driver/ 符号链接（kbuild 路径必需）。

上游 `video-driver/Makefile` 的 `modules:` 目标在调 kbuild 之前先建链接：

    modules: $(VIDEO_GEN_PATH)
    ifeq ($(CONFIG_MSM_VIDC_ANDROID), m)
        ln -sf $(VIDEO_ROOT)/driver $(VIDEO_ROOT)/msm_video/driver
    else
        ln -sf $(VIDEO_ROOT)/driver $(VIDEO_ROOT)/video/driver
    endif
        $(MAKE) -C $(KERNEL_SRC) M=$(M) modules $(KBUILD_OPTIONS)
    ...（构建后 rm 掉）

两个子目录的 Kbuild 都按这个布局写路径：

    video/Kbuild:     VIDEO_DRIVER_ABS_PATH := $(VIDEO_ROOT)/video/driver
                      VIDEO_DRIVER_REL_PATH := ../video/driver
    msm_video/Kbuild: VIDEO_DRIVER_ABS_PATH := $(VIDEO_ROOT)/msm_video/driver
                      VIDEO_DRIVER_REL_PATH := ../msm_video/driver

而 uwu 的 kbuild 路径（in-tree `make modules` / `M=`）不经过那个 `modules:`
目标，于是：

  - `video/driver` 只留下构建残留的空目录骨架（git 不跟踪空目录）；
    kbuild 拼接 `$(src)/../video/driver/platform/sun/src/sun.o`，报
    `No rule to make target '.../video/../video/driver/platform/sun/src/sun.o'`
  - `msm_video/driver` 根本不存在，同样构建不了

修法：按上游语义建符号链接。两边都建 —— 无论 CONFIG_MSM_VIDC_ANDROID 取值
如何，顶层 Kbuild 只会 `obj-m +=` 其中一个子目录，另一个不被遍历。
链接用**相对**目标（`../driver`），树整体搬家后仍然有效；上游用的是绝对
路径，那是给一次性 DDK 构建用的。

用法: python3 fix-video-driver-symlinks.py <video-driver 目录>
"""

import os
import shutil
import sys

LINK = "driver"
TARGET = "../driver"          # 相对 video/ 或 msm_video/
SUBDIRS = ("video", "msm_video")


def real_files(path):
    """统计符号链接背后能看到的文件数（用于验证链接有效）。"""
    n = 0
    for _dp, _dn, fs in os.walk(path):
        n += len(fs)
    return n


def main():
    root = sys.argv[1].rstrip("/") if len(sys.argv) > 1 else "."
    src = os.path.join(root, LINK)
    if not os.path.isdir(src):
        sys.exit("找不到源目录 %s" % src)
    src_n = real_files(src)
    if src_n == 0:
        sys.exit("源目录 %s 是空的，树不完整" % src)

    changed = []
    for sub in SUBDIRS:
        holder = os.path.join(root, sub)
        if not os.path.isdir(holder):
            print("skip  %s（不存在）" % sub)
            continue
        link = os.path.join(holder, LINK)

        if os.path.islink(link):
            if os.readlink(link) == TARGET:
                print("ok    %s/%s -> %s" % (sub, LINK, TARGET))
                continue
            os.unlink(link)
        elif os.path.isdir(link):
            # 构建残留的空目录骨架：确认是空的才删，避免误伤真实源码
            n = real_files(link)
            if n != 0:
                print("KEEP  %s/%s 是非空真实目录（%d 个文件），跳过" % (sub, LINK, n))
                continue
            shutil.rmtree(link)
            print("rm    %s/%s（空目录骨架）" % (sub, LINK))
        elif os.path.exists(link):
            print("KEEP  %s/%s 是普通文件，跳过" % (sub, LINK))
            continue

        os.symlink(TARGET, link)
        changed.append("%s/%s -> %s" % (sub, LINK, TARGET))

    for c in changed:
        print("link  %s" % c)

    # 验证
    for sub in SUBDIRS:
        link = os.path.join(root, sub, LINK)
        if os.path.islink(link):
            print("check %s/%s: %d files" % (sub, LINK, real_files(link)))
    if not changed:
        print("nothing to do")


if __name__ == "__main__":
    main()
