#!/usr/bin/env python3
"""aidl 会给 Java unstructured parcelable 写出「空 target」的 depfile，siso 解析失败。

system/tools/aidl/aidl.cpp 的 write_dep_file()：

    if (defined_type.AsUnstructuredParcelable() != nullptr &&
        options.TargetLanguage() == Options::Language::JAVA) {
      // Legacy behavior. For parcelable declarations in Java, don't emit output file as
      // the dependency target. b/141372861
      writer->Write(" : \\\\n");              <-- target 留空
    } else {
      writer->Write("%s : \\\\n", output_file.c_str());
    }

空 target 是给 legacy make 兼容的（b/141372861），make 能容忍这种写法；但 siso 的
gcc-deps 解析器要求标准的 "target: dep1 dep2"，于是报

    err: gcc-deps: failed to parse depfile ".../android/net/nsd/OffloadServiceInfo.aidl.d"

把**本来已经成功**（.java 已生成）的 aidl 步骤整体判成失败，紧随其后的 soong_zip
不执行，aidl1.srcjar 停在旧产物上，下游 Java 目标全部受阻。实测 u-zpy 上表现为
packages/modules/Connectivity/{framework,framework-t} 的 12 个 aidl1/aidl0.srcjar 失败。

修法：这种情况下也把 output_file 写成 target。编译产物完全不变，只是 depfile 变成
标准格式，siso 能正常解析。

改完必须重建 host 端的 aidl：
    siso ninja -k 0 -f out/combined-uwu_elden.ninja out/host/linux-x86/bin/aidl

幂等：已修过则跳过。
用法：python3 fix-aidl-depfile-empty-target.py [AOSP 根目录]
"""
import os
import pathlib
import sys

# 工作区根路径：默认与服务器一致；换机器时用环境变量覆盖，
# 例如 Y700_WORK=/mnt/d/projects/y700-uwu python3 <本脚本>
_Y700_WORK = os.environ.get("Y700_WORK", "/home/zpy/y700-uwu")

AOSP = pathlib.Path(sys.argv[1] if len(sys.argv) > 1 else _Y700_WORK + "/aosp")
P = AOSP / "system/tools/aidl/aidl.cpp"

# Python 字面量 → 实际匹配的 C++ 源码文本：writer->Write(" : \\\n");
OLD = 'writer->Write(" : \\\\\\n");'
NEW = 'writer->Write("%s : \\\\\\n", output_file.c_str());'

if not P.is_file():
    print("  skip: %s 不存在" % P)
    sys.exit(0)

src = P.read_text(errors="ignore")
if NEW in src and OLD not in src:
    print("  ok(已修): %s" % P.name)
    sys.exit(0)
if OLD not in src:
    print("  WARN 没找到空 target 写法，需人工确认: %s" % P)
    sys.exit(0)

P.write_text(src.replace(OLD, NEW, 1))
print("  已修 %s: Java parcelable 也写 output_file 作 target（depfile 变标准格式）" % P.name)
print("  下一步：重建 host aidl —— siso ninja -f out/combined-uwu_elden.ninja out/host/linux-x86/bin/aidl")
