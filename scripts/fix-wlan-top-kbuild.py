#!/usr/bin/env python3
"""给 wlan 顶层补 kbuild 聚合入口。

## 问题

上游 `qcom/opensource/wlan/` 顶层在 git 里只有四个子树，没有任何 Makefile /
Kbuild —— bazel 侧每个子模块都是独立 ddk_module：

    qcom/opensource/wlan/fw-api            (只提供头文件)
    qcom/opensource/wlan/platform          (cnss2 / icnss2 / cnss_genl / ...)
    qcom/opensource/wlan/qca-wifi-host-cmn (只提供源码+头文件)
    qcom/opensource/wlan/qcacld-3.0        (WLAN 驱动本体)

而 device `Android.bp` 的 external_modules 把 `wlan:kbuild` 当成一个 kbuild
单元，kbuild 在 M= 模式下找不到 Makefile/Kbuild，于是：

    make[3]: *** No rule to make target
      '.../sm8750-modules/qcom/opensource/wlan/Makefile'.  Stop.

## 为什么入口只遍历 platform/

- `platform/` 产出 load 清单需要的 cnss2.ko / icnss2.ko / cnss_genl.ko /
  cnss_prealloc.ko / cnss_utils.ko / wlan_firmware_service.ko /
  cnss_plat_ipc_qmi_svc.ko
- `qcacld-3.0` **已由 variants/{peach,peach_v2,kiwi_v2,wcn7750} 四个 kbuild
  各自独立构建**（同一套源码、不同 MODNAME），顶层若再遍历一次会重复产出
- `fw-api` / `qca-wifi-host-cmn` 只提供头文件与源码片段，由
  `qcacld-3.0/Kbuild` 内部引用，不构成独立模块

## 变量传递

`platform/Kbuild` 开头就 `include $(WLAN_PLATFORM_ROOT)/<mod>/sun_gki_defconfig`，
而上游只在 `platform/Makefile`（`$(shell pwd)`）和 `platform/Android.mk`
（`KBUILD_OPTIONS`）里定义它 —— kbuild 路径两者都不经过。所以顶层必须先把
`WLAN_PLATFORM_ROOT` 定义好。

**必须 export**：kbuild 递归进入子目录走的是 sub-make
（`scripts/Makefile.build` 里的 `$(MAKE) $(build)=$@`），是一次新的 make 进程，
未 export 的变量不会传下去，子目录里 `include $(WLAN_PLATFORM_ROOT)/...`
就会展开成 `include /icnss2/sun_gki_defconfig`。用 `:=` 让 `$(src)` 在顶层
立即展开成绝对路径，避免子进程里 `$(src)` 指向子目录。

用法: python3 fix-wlan-top-kbuild.py <wlan 目录>
"""

import os
import sys

MARK = "sm8750-wlan-top"

CONTENT = """# {mark}: 上游 wlan/ 顶层在 git 里只有 fw-api / platform /
# qca-wifi-host-cmn / qcacld-3.0 四个子树，没有任何构建入口（bazel 侧每个
# 子模块都是独立 ddk_module）。而 device Android.bp 的 external_modules 把
# "wlan:kbuild" 当成一个 kbuild 单元，于是报
#   No rule to make target '.../opensource/wlan/Makefile'
#
# 这里补一个聚合入口，只遍历 platform/：
#   - platform/ 产出 cnss2.ko / icnss2.ko / cnss_genl.ko / cnss_prealloc.ko /
#     cnss_utils.ko / wlan_firmware_service.ko / cnss_plat_ipc_qmi_svc.ko
#   - qcacld-3.0 由 variants/{{peach,peach_v2,kiwi_v2,wcn7750}} 四个 kbuild
#     各自独立构建（同一套源码、不同 MODNAME），顶层不能再遍历一次
#   - fw-api / qca-wifi-host-cmn 只提供头文件与源码片段，由
#     qcacld-3.0/Kbuild 内部引用，不构成独立模块
#
# WLAN_PLATFORM_ROOT 上游只在 platform/Makefile（$(shell pwd)）与
# platform/Android.mk（KBUILD_OPTIONS）里定义，kbuild 路径两者都不经过，
# 而 platform/Kbuild 一开头就要 include $(WLAN_PLATFORM_ROOT)/.../*.defconfig。
#
# 必须 export：platform/ 是被 sub-make 递归进去的（scripts/Makefile.build 的
# $(MAKE) $(build)=$@），未 export 的变量传不下去，子目录里就会展开成
#   include /icnss2/sun_gki_defconfig
# $(abspath ...) 让路径在顶层立即定死，避免子进程里 $(src) 指向子目录。
WLAN_ROOT := $(abspath $(src))
export WLAN_PLATFORM_ROOT := $(WLAN_ROOT)/platform

obj-m += platform/
""".format(mark=MARK)


def main():
    root = (sys.argv[1] if len(sys.argv) > 1 else ".").rstrip("/")
    if not os.path.isdir(os.path.join(root, "platform")):
        sys.exit("%s/platform 不存在，目录结构不符" % root)

    kb = os.path.join(root, "Kbuild")
    mk = os.path.join(root, "Makefile")

    for path in (kb, mk):
        if os.path.exists(path):
            text = open(path, errors="ignore").read()
            if MARK in text:
                print("ALREADY %s" % path)
                return
            if path == kb:
                sys.exit("%s 已存在但不含本修法标记，请人工检查" % path)

    with open(kb, "w", errors="ignore") as fh:
        fh.write(CONTENT)
    print("WROTE %s" % kb)

    # platform/Kbuild 依赖的 5 个 defconfig 必须都在，否则入口虽通但 config 缺失
    missing = []
    for m in ("cnss2", "cnss_genl", "cnss_prealloc", "cnss_utils", "icnss2"):
        p = os.path.join(root, "platform", m, "sun_gki_defconfig")
        if not os.path.exists(p):
            missing.append(m)
    if missing:
        print("WARN 缺 defconfig: %s" % ", ".join(missing))
    else:
        print("defconfigs: 5/5")


if __name__ == "__main__":
    main()
