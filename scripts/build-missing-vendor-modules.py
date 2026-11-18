#!/usr/bin/env python3
"""按需构建设备清单里缺失的 vendor 模块（用 M= + CONFIG 覆盖）。

背景：`modules.load.vendor_dlkm` 列了 264 个模块，但 in-tree 全树构建只产出其中
一部分。缺的 12 个（mhi、cnss_*、ipam、gsim、qti_battery_charger 等）在源码树里
有定义，只是 `obj-$(CONFIG_X)` 的 CONFIG 未开启，kbuild 就跳过了它们。

这里对每个缺失模块：
  1. 在 vendor 模块树里找到定义 `<name>.o` 的 Makefile/Kbuild；
  2. 从该行提取 CONFIG 名；
  3. `make -C common O=<kernel_build> M=<abs dir> CONFIG_X=m modules`
     —— 命令行变量会覆盖 .config，让 `obj-$(CONFIG_X)` 变成 `obj-m`；
  4. 把产出的 .ko 复制到 modules_staging 的 updates/。
"""
import os
import pathlib
import re
import subprocess
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

A = pathlib.Path(_Y700_WORK + "/aosp")
KP = A / "kernel/platform/kernel-6.12"
VEND = KP / "vendor/lenovo"
BUILD = A / "out/soong/.intermediates/device/lenovo/elden/kernel/android_arm64_armv8-a-branchprot_oryon/kernel_build"
STAGING = A / "out/soong/.intermediates/device/lenovo/elden/kernel/android_arm64_armv8-a-branchprot_oryon/modules_staging"

MISSING = ["mhi", "cnss_prealloc", "cnss_nl", "cnss_utils", "cnss_plat_ipc_qmi_svc",
           "wlan_firmware_service", "ipam", "rmnet_mem", "gsim",
           "qti_battery_charger", "tmecom-intf_dlkm", "smem-mailbox"]

# 已知/推断的源码目录（前面诊断得到），未列出的靠 grep 兜底
KNOWN_DIRS = {
    "mhi": "sm8750/net/qrtr",
    "cnss_prealloc": "sm8750-modules/qcom/opensource/wlan/platform/cnss_prealloc",
    "cnss_utils": "sm8750-modules/qcom/opensource/wlan/platform/cnss_utils",
    "cnss_plat_ipc_qmi_svc": "sm8750-modules/qcom/opensource/wlan/platform/cnss_utils",
    "wlan_firmware_service": "sm8750-modules/qcom/opensource/wlan/platform/cnss_utils",
    "ipam": "sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/ipa",
    "rmnet_mem": "sm8750-modules/qcom/opensource/datarmnet-ext/mem",
    "gsim": "sm8750-modules/qcom/opensource/dataipa/drivers/platform/msm/gsi",
    "qti_battery_charger": "sm8750/drivers/power/supply",
}

MAKE = str(A / "prebuilts/build-tools/linux-x86/bin/make")
CLANG_BIN = str(A / "prebuilts/clang/host/linux-x86/clang-r596125/bin")
ENV = dict(os.environ)
ENV["PATH"] = ":".join([
    CLANG_BIN,
    str(A / "prebuilts/build-tools/linux-x86/bin"),
    str(A / "prebuilts/kernel-build-tools/linux-x86/bin"),
    str(A / "prebuilts/tools-lineage/linux-x86/bin"),
]) + ":" + ENV.get("PATH", "")


def find_config(mod: str, d: pathlib.Path):
    """在目录的 Makefile/Kbuild 里找 `<name>.o` 对应的 CONFIG。"""
    for fn in ("Kbuild", "Makefile"):
        p = d / fn
        if not p.exists():
            continue
        for line in p.read_text(errors="ignore").splitlines():
            m = re.match(r"\s*obj-\$\((\w+)\)\s*\+?=\s*(.*)", line)
            if m and re.search(r"(^|\s)%s\.o(\s|$)" % re.escape(mod), m.group(2)):
                return m.group(1)
    return None


def main():
    updates = STAGING / "lib/modules/6.12.96-4k-g153de33f91d6-dirty/updates"
    updates.mkdir(parents=True, exist_ok=True)
    ok, skipped = [], []

    for mod in MISSING:
        rel = KNOWN_DIRS.get(mod)
        if not rel:
            skipped.append((mod, "目录未知"))
            continue
        d = VEND / rel
        if not d.is_dir():
            skipped.append((mod, "目录不存在: %s" % rel))
            continue
        cfg = find_config(mod, d)
        flags = ["M=%s" % d, "ARCH=arm64", "LLVM=1", "LLVM_IAS=1",
                 "CC=clang", "LD=ld.lld", "CLANG_TRIPLE=aarch64-linux-gnu-",
                 "CROSS_COMPILE=aarch64-linux-gnu-"]
        if cfg:
            flags.append("%s=m" % cfg)
        cmd = [MAKE, "-j16", "-C", str(KP / "common"), "O=%s" % BUILD] + flags + ["modules"]
        r = subprocess.run(cmd, capture_output=True, text=True, env=ENV, cwd=str(A))
        built = list(d.rglob("%s.ko" % mod))
        if built:
            for b in built:
                subprocess.run(["cp", "-f", str(b), str(updates / b.name)], check=False)
            ok.append((mod, cfg or "-", built[0].name))
        else:
            tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
            skipped.append((mod, "构建未产出：%s %s" % (cfg or "-", tail[0][:100])))

    print("== 已补齐 ==")
    for m, c, f in ok:
        print("  %-26s %-28s %s" % (m, c, f))
    print("== 未补齐 ==")
    for m, why in skipped:
        print("  %-26s %s" % (m, why))
    print("updates 下 ko:", len(list(updates.glob("*.ko"))))


if __name__ == "__main__":
    main()
