# p2：服务器成品改动导出

来源机器：zpy-13500t（`/home/zpy/y700-uwu/aosp`）
导出日期：2026-11-18
导出方式：对各仓库 `git diff`（未跟踪文件用 `git add -N` 后取 diff）

## 基线

| 仓库 | 分支 | HEAD |
|---|---|---|
| `device/lenovo/elden` | `uwu-17.0` | `23dca5924910` |
| `vendor/lenovo/elden` | `uwu-17.0` | `48e8d2590658` |
| `kernel/platform/kernel-6.12/common` | `android16-6.12` | `793c58ba801e` |
| `kernel/platform/kernel-6.12/vendor/lenovo/sm8750` | `lineage-24.0` | `f18e104d89ad` |
| `kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules` | `lineage-24.0` | `ed996920087d` |

## 文件

| patch | 行数 | 目标目录 | 内容 |
|---|---|---|---|
| `device-elden.patch` | 904 | `aosp/device/lenovo/elden` | 6 个已跟踪文件的改动 |
| `device-elden-newfiles.patch` | 751 | `aosp/device/lenovo/elden` | 5 个新增清单文件 |
| `vendor-elden.patch` | 163 | `aosp/vendor/lenovo/elden` | `Android.bp` +155 行（30 个 `prebuilt_radio_image`） |
| `kernel-common.patch` | 78 | `.../kernel-6.12/common` | `rust/Makefile`、`scripts/gendwarfksyms/{dwarf,gendwarfksyms}.c` |
| `kernel-sm8750.patch` | 407 | `.../vendor/lenovo/sm8750` | 12 个改动（含 `arch/arm64/Kbuild`、`scripts/gendwarfksyms/*`） |
| `kernel-sm8750-rust.patch` | 550 | `.../vendor/lenovo/sm8750` | `rust/Makefile`（**新增文件**，git 未跟踪） |
| `kernel-sm8750-modules.patch` | 810 | `.../vendor/lenovo/sm8750-modules` | 50 个 Kbuild/Kconfig/源文件改动 |
| `kernel-wlan-variants.patch` | 356 | `.../vendor/lenovo/sm8750-modules` | `qcom/opensource/wlan/variants/`（4 个 Kbuild + 16 个软链） |

## 应用顺序

必须按此顺序，前一步是后一步的前提：

```bash
A=/path/to/aosp

# 1) device 已跟踪文件的改动
git -C $A/device/lenovo/elden        apply patches/p2/device-elden.patch
# 2) device 新增的清单文件
git -C $A/device/lenovo/elden        apply patches/p2/device-elden-newfiles.patch
# 3) vendor 的 30 个 radio 模块
git -C $A/vendor/lenovo/elden        apply patches/p2/vendor-elden.patch
# 4) GKI common 树的补丁
git -C $A/kernel/platform/kernel-6.12/common apply patches/p2/kernel-common.patch
# 5) vendor 内核树的补丁
git -C $A/kernel/platform/kernel-6.12/vendor/lenovo/sm8750 apply patches/p2/kernel-sm8750.patch
# 6) vendor 内核树的 rust/Makefile（新增文件）
git -C $A/kernel/platform/kernel-6.12/vendor/lenovo/sm8750 apply patches/p2/kernel-sm8750-rust.patch
# 7) vendor 模块树的补丁
git -C $A/kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules apply patches/p2/kernel-sm8750-modules.patch
# 8) wlan variants（含软链）
git -C $A/kernel/platform/kernel-6.12/vendor/lenovo/sm8750-modules apply patches/p2/kernel-wlan-variants.patch
```

## 注意事项

**1. `kernel-wlan-variants.patch` 含 16 个软链**

patch 里是 `new file mode 120000` + 内容 `../../qcacld-3.0/<dir>`。
`git apply` 能正确重建软链；但**用 `patch -p1` 不行**（它会把软链写成普通文件），必须用 `git apply`。

**2. `kernel-sm8750-rust.patch` 是整份新增文件**

`sm8750/rust/` 整个目录在 git HEAD 里不存在（浅克隆未包含），所以无法用普通 diff 表达。
该 patch 是 `--no-index` 风格的全量新增，内容与 `common/rust/Makefile` 相同（两者各 147 个文件、`diff -rq` 无差异）。

**3. 不含的内容**

- `device/lenovo/elden/kernel-headers/`（1.5 MB）：由 `scripts/gen-kernel-headers.sh` 生成
- `device/lenovo/elden/prebuilt_dtb/`（33 MB）：二进制，需单独传
- 各树的编译产物（`*.o` / `*.ko` / `*.cmd` / `modules.order` 等）：已清理，不进 patch

**4. 校验过**

8 个 patch 全部通过 `git apply --reverse --check`（rc=0，工作树已是改动后状态，反向能套用即证明完整捕获）；
`^Binary files` 计数全为 0，无二进制混入。

## 与脚本的关系

这些 patch 是「成品改动」，`scripts/` 里的脚本是「可重放修法」。
两者用途不同：
- **patch** 用于快速让另一棵树达到当前状态
- **脚本** 用于从干净源码重新推导，验证修法可复现（需配合 `Y700_WORK` 环境变量）
