#!/usr/bin/env python3
"""补齐 clspv 依赖但当前树里缺失的 clang-includes / llvm-includes 模块。

现象（13500t 首次 soong bootstrap）：
    error: external/clspv/Android.bp:23:1: "clspv_lib_libclspv_core_a"
           depends on undefined module "clang-includes".
    error: ... depends on undefined module "llvm-includes".
→ soong bootstrap 失败，otapackage 一步都跑不了。

根因：
  external/clspv/Android.bp 是 ninja-to-soong **自动生成**的文件（头部写着
  "DO NOT MODIFY MANUALLY"），它声明了
      header_libs: ["SPIRV-Headers-includes", "clang-includes", "llvm-includes"]
  但当前树的 prebuilts/clang/host/linux-x86/Android.bp（676 行）里**已经不再定义**
  这两个 header lib（upstream 版本错配：clang prebuilt 与 clspv 生成文件不同步）。
  u-zpy 之所以能构建，是因为它一直在用**早先生成好的 ninja 图**，从未重新做过
  soong bootstrap，所以这个缺口被掩盖了。

修法取舍：
  不删 clspv 的依赖（那是它的真实需求，且该文件是自动生成的），而是在
  prebuilts/clang/host/linux-x86/Android.bp 末尾补两个 cc_prebuilt_library_headers，
  导出 clang-r596125/include（该目录同时含 llvm/ 与 clang/ 子目录，实测存在）。

幂等：已存在同名模块则跳过。
用法：python3 fix-clspv-missing-include-libs.py [AOSP 根目录] [clang 版本目录名]
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else _Y700_WORK + "/aosp")
VER = sys.argv[2] if len(sys.argv) > 2 else "clang-r596125"

CLANG_DIR = AOSP / "prebuilts/clang/host/linux-x86"
BP = CLANG_DIR / "Android.bp"

if not BP.is_file():
    print("  skip: %s 不存在" % BP)
    sys.exit(0)
if not (CLANG_DIR / VER / "include").is_dir():
    print("  WARN 找不到 %s/include，请传入正确的 clang 版本目录名" % (CLANG_DIR / VER))
    sys.exit(1)

src = BP.read_text(errors="ignore")
missing = [n for n in ("clang-includes", "llvm-includes")
           if 'name: "%s"' % n not in src]
if not missing:
    print("  ok(已存在): clang-includes / llvm-includes")
    sys.exit(0)

block = ["", "// --- 由 scripts/fix-clspv-missing-include-libs.py 追加 ---",
         "// external/clspv 的 header_libs 依赖这两个模块，但 upstream 的 clang prebuilt",
         "// 已不再提供；这里直接导出 %s/include（含 llvm/ 与 clang/ 子目录）。" % VER]
for name in missing:
    block += [
        "",
        "cc_prebuilt_library_headers {",
        '    name: "%s",' % name,
        "    vendor_available: true,",
        '    export_include_dirs: ["%s/include"],' % VER,
        '    apex_available: ["//apex_available:platform", "//apex_available:anyapex"],',
        "}",
    ]

BP.write_text(src.rstrip("\n") + "\n" + "\n".join(block) + "\n")
print("  已补模块: %s  (导出 %s/include)" % (", ".join(missing), VER))
