# y700-uwu — elden (Lenovo Legion Tab / TB322FC) uwuAOSP 17 自编译工作区

## 已完成的自修复

全部改动都在 device 树和 `vendor/uwu` 里，已各自 `git commit`（本地，未 push）。

### 1. 去掉 Google 套件
- `platform_vendor_uwu/config/pixel.mk`：`WITH_GMS` + `gms.mk` 收进 `WITH_GAPPS` 条件，未设置时默认 `true`（保持上游行为）
- `android_device_lenovo_elden/uwu_elden.mk`：`WITH_GAPPS := false`
- Pixel Clocks / GSans / Sounds / ThemePicker 不受影响

### 2. 充电电量控制无效
三个错误叠加，全部修掉：
- `device.mk` 的 `charging_path` 原本指向 `battery_maintenance20`，那是联想「保养模式 20%」限充，不是充电开关。改为 `charging_enable`（`POWER_SUPPLY_PROP_BATTERY_CHARGING_ENABLE`，1=允许充电 / 0=停止）
- `charging_enabled` / `charging_disabled` 值原本写成 `0` / `1`，与内核语义相反，改为 `1` / `0`
- `init/ueventd.qcom.rc` 原本只给 `battery_maintenance20` 配了 `0660 system system`，`charging_enable` 仍是 root-only，HAL（system 用户）写不进去；已补上
- 新增 `sepolicy/vendor/hal_lineage_health_default.te`，对 `sysfs_battery_supply` 显式授予 rw

### 3. 旁路充电
- `device.mk` 显式设 `charging_control_supports_bypass=true`（HAL 侧默认就是 true）
- 新增 `power/` 模块 `EldenPowerSettings`（system_ext privileged + platform 签名），「设置 → 电池 → Charging」里一个 Bypass charging 开关，通过 `vendor.lineage.health.IChargingControl.setChargingEnabled(false)` 实现：停充但继续从适配器取电
- 独立 package `org.lineageos.elden.powersettings`，不与现有 `EldenTouchSettings` 冲突
- 前提是 2 的节点配置正确，两者共用同一个 `charging_enable`

### 4. 手电筒不亮
静态链路核查结论：DTS（`elden-camera.dtsi` 的 led_flash_rear、pm8550 flash/torch/switch）、驱动（`CONFIG_LEDS_QTI_FLASH=m`，`leds-qti-flash.ko` 在 `modules.load.vendor_dlkm`）、vintf、电流上限校验**全部正常**，没有找到可静态修复的断点。

能做的已经补上：`ueventd.qcom.rc` 给 `led:torch_0..3` / `led:flash_0..3` / `led:switch_2` 加了 `brightness`、`flash_strobe` 权限（原本 root-only）。

如果刷入后仍不亮，需要真机日志定位：
```bash
adb shell dmesg | grep -iE "qti_flash|led_class|flash_led"     # 看 probe 是否成功
adb shell logcat -b all | grep -iE "torch|flashlight|camx"     # 看 camx 是否收到 setTorchMode
adb shell ls -lZ /sys/class/leds/led:torch_0/                  # 看节点是否存在、SELinux 标签
```

## 行尾（重要）

Windows 上 `core.autocrlf=true` 把所有仓库转成了 CRLF，在 Linux 容器里会让 `make` 的 `\` 续行失效。已对全部仓库执行：

```bash
git config core.autocrlf false
git rm --cached -r .
git reset --hard
```

现在工作树是 LF。**以后在这些仓库里改文件后，确保编辑器不要写回 CRLF。**

## 编译环境（Docker，非 WSL）

Docker Desktop 用的是 Hyper-V 后端（`WslEngineEnabled: false`），内存已从 8GB 调到 24GB（宿主 32GB），16 核可用。

镜像：`aosp-builder:17`（Ubuntu 24.04 + JDK 21 + AOSP 全部依赖）

- apt 走阿里云源；`openjdk-21` 的两个大包（45MB/79MB）在这条网络上从任何镜像都会断流，所以改为宿主代理下载 deb 放进 `docker/jdk/`，容器里 `dpkg -i` 安装
- 容器通过 `host.docker.internal:7897` 访问宿主代理（GitHub 直连会被重置）

### 重新构建镜像
```bash
docker build -t aosp-builder:17 docker/
```

### 全流程
```bash
cd /d/projects/y700-uwu

# 1. 同步源码（约 250GB，走代理）
MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/y700-uwu:/src" -w /src \
    aosp-builder:17 bash scripts/sync.sh

# 2. 把本地的 device/kernel/vendor 链进 AOSP 树
MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/y700-uwu:/src" -w /src \
    aosp-builder:17 bash scripts/link-device.sh

# 3. 编译（user 版）
MSYS_NO_PATHCONV=1 docker run --rm -v "D:/projects/y700-uwu:/src" -w /src \
    aosp-builder:17 bash scripts/build.sh
```

产物在 `aosp/out/target/product/elden/`。

## 目录

| 路径 | 内容 |
|---|---|
| `android_device_lenovo_elden/` | device 树（uwu-17.0），已改 |
| `platform_vendor_uwu/` | vendor/uwu（uwu-17.0），已改 |
| `proprietary_vendor_lenovo_elden/` | vendor blobs（2.6G） |
| `android_kernel_lenovo_sm8750/` | Qualcomm vendor 内核（msm-kernel 部分，依赖 AOSP common） |
| `android_kernel_lenovo_sm8750-devicetrees/` | DTS |
| `android_kernel_lenovo_sm8750-modules/` | 内核模块源码 |
| `elden-kernel/` | AnyKernel 打包脚本 |
| `docker/` | 构建镜像定义 + JDK deb |
| `scripts/` | sync / link / build |
| `aosp/` | repo sync 出来的 AOSP 树 |
| `SERVER.md` | 服务器（u-zpy）连接、代理、构建与踩坑 |
