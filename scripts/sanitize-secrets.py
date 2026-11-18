#!/usr/bin/env python3
"""把内网拓扑信息替换成占位符，让仓库可以公开推送。

## 为什么需要

`AGENTS.md` 与部分 `scripts/` 里有真实的内网地址、JumpServer 域名和资产 ID。
这些属于内部基础设施信息，推到公开仓库等于对外公布攻击面。

## 真实值放在哪里

真实值**不在本脚本里**，而在 `config/secrets.map`（已被 .gitignore 排除）：

    # 每行：真实值<TAB>占位符
    <内部IP一>\t<SERVER_A_IP>
    <内部IP二>\t<SERVER_B_IP>
    <跳板域名>\t<JUMP_HOST>
    <资产ID>\t<ASSET_ID_A>

这样脚本可以公开，真实值只在本地。没有该文件时脚本直接退出并说明。

生成模板：

    python3 sanitize-secrets.py --emit-template > config/secrets.map
    # 然后把占位符换成真实值，再执行
    python3 sanitize-secrets.py

## 幂等

已含占位符的文件不会被二次替换。

用法：
    python3 sanitize-secrets.py [--dry-run] [--emit-template]
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
MAP_FILE = ROOT / "config" / "secrets.map"

# 本脚本自身的规则表必须保存真实值（否则无法执行替换），
# 因此跳过自身，避免把规则表也改成占位符。
SELF = pathlib.Path(__file__).resolve()

TARGETS = [
    ROOT / "AGENTS.md",
    ROOT / "README.md",
] + sorted((ROOT / "scripts").glob("*.sh")) + sorted((ROOT / "scripts").glob("*.py"))

TEMPLATE = """\
# 脱敏映射表：真实值<TAB>占位符
# 本文件已被 .gitignore 排除，不会进仓库。
# 把下面的占位符替换成真实值后，运行 scripts/sanitize-secrets.py
<SERVER_A_IP>	<SERVER_A_IP>
<SERVER_B_IP>	<SERVER_B_IP>
<PROXY_HOST>	<PROXY_HOST>
<JUMP_HOST>	<JUMP_HOST>
<ASSET_ID_A>	<ASSET_ID_A>
<ASSET_ID_B>	<ASSET_ID_B>
"""


def load_rules():
    if not MAP_FILE.is_file():
        sys.exit(
            "缺少 %s\n"
            "先执行：python3 %s --emit-template > %s\n"
            "再把占位符换成真实值。" % (MAP_FILE, SELF.name, MAP_FILE)
        )
    rules = []
    for line in MAP_FILE.read_text(errors="ignore").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) != 2:
            continue
        real, ph = parts[0].strip(), parts[1].strip()
        # 占位符还没替换掉的条目跳过
        if not real or real.startswith("<"):
            continue
        rules.append((real, ph))
    if not rules:
        sys.exit("%s 里没有有效的映射条目（占位符还没换成真实值？）" % MAP_FILE)
    # 长值优先，避免部分匹配
    rules.sort(key=lambda x: -len(x[0]))
    return rules


def main():
    if "--emit-template" in sys.argv:
        sys.stdout.write(TEMPLATE)
        return

    rules = load_rules()
    dry = "--dry-run" in sys.argv
    total = 0
    touched = 0
    for p in TARGETS:
        if not p.is_file() or p.resolve() == SELF:
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        new = text
        n = 0
        for real, ph in rules:
            cnt = new.count(real)
            if cnt:
                new = new.replace(real, ph)
                n += cnt
        if n:
            touched += 1
            total += n
            print("%-46s %d 处" % (p.relative_to(ROOT), n))
            if not dry:
                p.write_text(new)
    print("---")
    print("%d 个文件，%d 处替换%s" % (touched, total, "（dry-run）" if dry else ""))


if __name__ == "__main__":
    main()
