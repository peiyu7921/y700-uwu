#!/usr/bin/env python3
"""极简 protobuf wire-format 解析：从 DeltaArchiveManifest 里抽出分区清单。

不依赖 .proto / protoc，只用 wire format 规则：
  tag = (field_number << 3) | wire_type
  wire_type 2 = length-delimited（string / bytes / 嵌套 message）
  wire_type 0 = varint

DeltaArchiveManifest:
  field 13 = repeated PartitionUpdate partitions
PartitionUpdate:
  field 1 = required string partition_name
  field 7 = optional PartitionInfo new_partition_info   (含 size 字段)
  field 8 = repeated InstallOperation operations          (数量反映差异块多少)

用法: python3 parse_payload_manifest.py <manifest.bin>
"""
import sys


def read_varint(buf, i):
    v = 0
    shift = 0
    while i < len(buf):
        b = buf[i]
        i += 1
        v |= (b & 0x7F) << shift
        if not b & 0x80:
            break
        shift += 7
    return v, i


def parse_fields(buf):
    """产出 (field_number, wire_type, value)，value 对 length-delimited 是 bytes。"""
    i = 0
    n = len(buf)
    while i < n:
        try:
            tag, i = read_varint(buf, i)
        except Exception:
            return
        field = tag >> 3
        wt = tag & 0x7
        if field == 0:
            return
        if wt == 0:                       # varint
            v, i = read_varint(buf, i)
            yield field, wt, v
        elif wt == 2:                     # length-delimited
            ln, i = read_varint(buf, i)
            if i + ln > n:
                return
            yield field, wt, buf[i:i + ln]
            i += ln
        elif wt == 5:                     # 32-bit
            i += 4
        elif wt == 1:                     # 64-bit
            i += 8
        else:
            return


def summarize(path):
    with open(path, "rb") as fh:
        buf = fh.read()
    parts = {}
    for field, wt, val in parse_fields(buf):
        if field != 13 or wt != 2:
            continue
        name = None
        nops = 0
        for f2, w2, v2 in parse_fields(val):
            if f2 == 1 and w2 == 2:
                name = v2.decode("utf-8", "replace")
            elif f2 == 8 and w2 == 2:
                nops += 1
        if name:
            parts[name] = nops
    return parts


if __name__ == "__main__":
    for path in sys.argv[1:]:
        ps = summarize(path)
        print("### %s  分区数=%d" % (path, len(ps)))
        for k in sorted(ps):
            print("  %-22s ops=%d" % (k, ps[k]))
