#!/usr/bin/env python3
"""从 A/B OTA 的 payload.bin 里提取指定分区的完整镜像（流式，不整包读入内存）。

参考版 OTA 有 2.9 GB，直接 zipfile.read("payload.bin") 会一次性占满内存。
这里改为：定位 payload.bin 在 zip 内的数据偏移，然后只用 seek + 小块读取。

payload 结构（v2，full payload）：
    offset 0    : "CrAU" (4)
    offset 4    : version (uint64 BE, =2)
    offset 12   : manifest_size (uint64 BE)
    offset 20   : metadata_signature_size (uint32 BE)
    offset 24   : DeltaArchiveManifest (protobuf)
    ...         : metadata signature
    ...         : data blobs

PartitionUpdate:
    field 1  partition_name (string)
    field 8  operations     (repeated InstallOperation)
InstallOperation:
    field 1  type        (0 = REPLACE，data_offset/data_length 指向整段新数据)
    field 2  data_offset (uint64)
    field 3  data_length (uint64)

用法:
    python3 extract_payload_partition.py <ota.zip|payload.bin> <分区名> <输出文件>
"""
import bz2
import lzma
import struct
import sys
import zipfile

CHUNK = 4 << 20


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


def iter_fields(buf):
    i = 0
    n = len(buf)
    while i < n:
        try:
            tag, i = read_varint(buf, i)
        except Exception:
            return
        field, wt = tag >> 3, tag & 0x7
        if field == 0:
            return
        if wt == 0:
            v, i = read_varint(buf, i)
            yield field, wt, v
        elif wt == 2:
            ln, i = read_varint(buf, i)
            if i + ln > n:
                return
            yield field, wt, buf[i:i + ln]
            i += ln
        elif wt == 5:
            i += 4
        elif wt == 1:
            i += 8
        else:
            return


def payload_base(path):
    """返回 (文件路径, payload.bin 数据在文件内的起始偏移)。"""
    if path.lower().endswith(".zip"):
        with zipfile.ZipFile(path) as zf:
            info = zf.getinfo("payload.bin")
        # 本地文件头：签名(4) + ... + 文件名长度@26 + extra 长度@28，数据在 30+后
        with open(path, "rb") as fh:
            fh.seek(info.header_offset)
            head = fh.read(30)
        if head[:4] != b"PK\x03\x04":
            sys.exit("payload.bin 的本地文件头异常")
        fnlen = struct.unpack("<H", head[26:28])[0]
        extlen = struct.unpack("<H", head[28:30])[0]
        return path, info.header_offset + 30 + fnlen + extlen
    return path, 0


def main():
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    src, want, out_path = sys.argv[1], sys.argv[2], sys.argv[3]
    fpath, base = payload_base(src)

    with open(fpath, "rb") as fh:
        fh.seek(base)
        head = fh.read(24)
        if head[:4] != b"CrAU":
            sys.exit("不是 update payload（缺少 CrAU magic）")
        version = struct.unpack(">Q", head[4:12])[0]
        msize = struct.unpack(">Q", head[12:20])[0]
        sig_size = struct.unpack(">I", head[20:24])[0]
        manifest = fh.read(msize)

        data_start = base + 24 + msize + sig_size
        print("version=%d manifest=%d sig=%d data_start=%d"
              % (version, msize, sig_size, data_start))

        ops, found = [], False
        for f, w, pu in iter_fields(manifest):
            if f != 13 or w != 2:
                continue
            name = None
            cur = []
            for f2, w2, v2 in iter_fields(pu):
                if f2 == 1 and w2 == 2:
                    name = v2.decode("utf-8", "replace")
                elif f2 == 8 and w2 == 2:
                    op_type = off = ln = None
                    for f3, w3, v3 in iter_fields(v2):
                        if f3 == 1 and w3 == 0:
                            op_type = v3
                        elif f3 == 2 and w3 == 0:
                            off = v3
                        elif f3 == 3 and w3 == 0:
                            ln = v3
                    if off is not None and ln is not None:
                        cur.append((op_type, off, ln))
            if name == want:
                ops, found = cur, True
                break

        if not found:
            sys.exit("manifest 里没有分区 %r" % want)

        total = sum(ln for _, _, ln in ops)
        print("分区 %s: %d 个 operation，共 %d B（压缩块合计）"
              % (want, len(ops), total))

        done = 0
        with open(out_path, "wb") as out:
            for op_type, off, ln in ops:
                fh.seek(data_start + off)
                blob = fh.read(ln)
                if len(blob) != ln:
                    sys.exit("读取中断（期望 %d B，实得 %d B）" % (ln, len(blob)))
                if op_type == 8:            # REPLACE_XZ
                    blob = lzma.decompress(blob)
                elif op_type == 1:          # REPLACE_BZ
                    blob = bz2.decompress(blob)
                elif op_type != 0:          # REPLACE=0 是唯一允许的其它类型
                    sys.exit("不支持的 operation type=%r（只处理 REPLACE/REPLACE_BZ/REPLACE_XZ）"
                             % (op_type,))
                out.write(blob)
                done += len(blob)
        print("已写入 %s（解压后 %d B）" % (out_path, done))


if __name__ == "__main__":
    main()
