#!/usr/bin/env python3
"""启用那些「已经编译成功、但清单里被 sm8750-gap 注释掉」的 vendor_dlkm 模块。

## 背景

`modules.load.vendor_dlkm` / `modules.include.vendor_dlkm` 里有 102 行形如

    # sm8750-gap: camera.ko
    # sm8750-gap: cnss2.ko

的占位注释。这是早期这些模块还编译不出来时留下的。

与参考版 OTA（`uwuAOSP-17.0.181-20261101-UNOFFICIAL-elden-signed.zip`）逐分区比对后
确认：参考版的 `vendor_dlkm` 是 57,397,248 B、含 44 个分区，而本树只有 5,865,472 B。
差集里最要紧的一批，就是这 102 个被注释的模块 —— 其中 **38 个已经编译成功**、
就躺在 `kernel_modules.zip` 里，只是清单里没启用。

实证（38 个全部验证过）：

  - 全部存在于 kernel_modules.zip（321 个 .ko 内），缺失数 0
  - vermagic 统一为 `6.12.96-4k-g793c58ba801e-dirty`，与内核 Image 完全一致
  - 依赖闭包完整：所有「未入清单」的依赖（qts / ipclite / smcinvoke_dlkm /
    rmnet_ctl / qce50_dlkm / wlan_firmware_service / cnss_prealloc / cnss_utils /
    cnss_plat_ipc_qmi_svc）都在这 38 个之内；qcom_common 是 builtin
    （CONFIG_PCIE_QCOM_COMMON=y），不需要 .ko

这批模块覆盖 WiFi（cnss2 / cnss_nl / cnss_utils / cnss_prealloc /
cnss_plat_ipc_qmi_svc / wlan_firmware_service / icnss2）、相机（camera / msm-eva）、
触摸屏（atmel_mxt_ts / focaltech_fts / goodix_ts / st_fts / synx-driver）、
内存与网络加速（rmnet_*）、加密（qce50/qcedev/qcrypto/qrng/smcinvoke/
hdcp_qseecom/tz_log）、显示（msm_ext_display / msm_hw_fence / msm-mmrm）等。

## 为什么只启用「已编出的」

剩下 64 个（adsp_loader_dlkm、aw882xx_dlkm、btfmcodec、lpass_cdc_* 等，集中在
音频/蓝牙子系统）确实没有编译产物，启用它们只会让 `writeModuleListFile` 报
"module not found"。那属于另一批构建问题，不在本脚本范围内 —— 脚本天然幂等：
只处理在 ko 列表里出现过的模块，编不出来就一直保持注释。

## 用法

    python3 enable-vendor-dlkm-gaps.py [kernel_modules.zip]

zip 路径默认取构建中间产物；传 `-` 表示只读取当前已解出的 ko 目录
（`/tmp/kochk`）以避免重复解包。
"""
import os
import pathlib
import re
import subprocess
import sys
import tempfile
import zipfile

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(_Y700_WORK + "/aosp")
DEV = AOSP / "device/lenovo/elden"
LISTS = [DEV / "modules.load.vendor_dlkm", DEV / "modules.include.vendor_dlkm"]
DEFAULT_ZIP = (AOSP / "out/soong/.intermediates/device/lenovo/elden/kernel/"
               "android_arm64_armv8-a-branchprot_oryon/kernel_modules.zip")

MARK = "sm8750-enabled"
GAP_RE = re.compile(r"^#\s*sm8750-gap:\s*(\S+\.ko)\s*$")


def ko_names(zip_path: str) -> set:
    """取出 zip 里的 .ko 文件名集合。"""
    if zip_path == "-":
        d = pathlib.Path("/tmp/kochk")
        if not d.is_dir():
            sys.exit("指定了 - 但 /tmp/kochk 不存在")
        return {p.name for p in d.glob("*.ko")}
    p = pathlib.Path(zip_path)
    if not p.is_file():
        sys.exit("找不到 kernel_modules.zip: %s" % p)
    with zipfile.ZipFile(p) as zf:
        return {pathlib.PurePosixPath(n).name
                for n in zf.namelist() if n.endswith(".ko")}


def patch(path: pathlib.Path, have: set) -> tuple:
    """把能启用的 gap 行改成实际条目。返回 (新增启用数, 仍注释数)。"""
    lines = path.read_text(errors="ignore").splitlines()
    out, enabled, still = [], 0, 0
    for line in lines:
        m = GAP_RE.match(line)
        if not m:
            out.append(line)
            continue
        name = m.group(1)
        if name in have:
            # 去掉注释并用标记说明来源，便于日后审计
            out.append(name)
            out.append("# %s: %s 已编出，解除 sm8750-gap 注释" % (MARK, name))
            enabled += 1
        else:
            out.append(line)
            still += 1
    path.write_text("\n".join(out) + "\n")
    return enabled, still


def main():
    zpath = sys.argv[1] if len(sys.argv) > 1 else str(DEFAULT_ZIP)
    have = ko_names(zpath)
    print("ko 列表来源: %s（%d 个 .ko）" % (zpath, len(have)))

    total_en, total_still = 0, 0
    for lst in LISTS:
        if not lst.is_file():
            print("跳过（不存在）: %s" % lst)
            continue
        en, st = patch(lst, have)
        total_en += en
        total_still += st
        print("[%s] 启用 %d 个，仍注释 %d 个" % (lst.name, en, st))

    print("合计：启用 %d 个，仍注释 %d 个" % (total_en, total_still))
    if total_en == 0:
        print("（可能已启用过，或 ko 列表不含这些模块）")


if __name__ == "__main__":
    main()
