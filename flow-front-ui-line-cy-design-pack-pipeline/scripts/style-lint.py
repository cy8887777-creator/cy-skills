#!/usr/bin/env python3
"""style-lint — 铺量伴随：tokens 外样式发明扫描（⑧，确定性）。

扫页面样式的 tokens 外字面量（hex 颜色 / font-size px 字面量 /
font-family 字符串），对照 tokens.ts 白名单——越界即报告。
栈适配（1009-16）：react=src/pages/*.tsx；vue=src/pages/**/*.vue
（SFC 的 <style> 块与 template 内联 style 属性按 CSS 规则抽取）。
**报告声明覆盖页数；所选栈目标页面数为零 = FAIL**——一份没检查任何
目标页的报告不得给门禁背书（实跑实证：Vue 工程 91 个 .vue 零覆盖，
报告仅来自 global.css）。
跨页漂移防线：tokens/组件库是唯一视觉真值，"组件库没有的样式 = 不
该出现"；本脚本把该契约从提示词变成可执行检查。

用法：python style-lint.py --src <工程>/src [--stack react|vue] [--tokens <tokens.ts>]
Exit 0 = 无越界；1 = 有越界或零覆盖。
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # 1012-06：拒账提示走 stderr，同 UTF-8 口径

HEX_RE = re.compile(r"#(?:[0-9a-fA-F]{3}|[0-9a-fA-F]{6}|[0-9a-fA-F]{8})\b")
FONTSIZE_RE = re.compile(
    # (?:px)? 不是 px? —— px? = "p"+可选"x"，裸数字 fontSize: 16 永远
    # 匹配不上（五轮评审实测抓出的经典正则错误）
    r'''fontSize\s*:\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?|text-\[(\d+(?:\.\d+)?)px\]''')
CSS_FONTSIZE_RE = re.compile(r'''font-size\s*:\s*(\d+(?:\.\d+)?)px''')
CSS_FAMILY_RE = re.compile(r'''font-family\s*:\s*([^;}]+)''')
FAMILY_RE = re.compile(r'''fontFamily\s*:\s*["']([^"']{2,60})["']''')
# 允许的非 tokens 颜色（语义色/继承，非"样式发明"）
COLOR_ALLOW = {"#000", "#000000", "#fff", "#ffffff", "#ffffff80",
               "transparent", "inherit", "currentcolor"}


def _strip_comments(text: str, css: bool = False) -> str:
    """去 // 与 /* */ 注释——注释里的数字/族名不得进白名单或被误报
    （七轮评审：注释中的 99 成为允许字号、注释 font-family 误报）。
    // 用负向后行排除 `://`——URL 中的 // 不是注释，误剥会把同行的
    真实违规一起吞掉（假阴性，双轴三轮抓出）。"""
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    if not css:
        text = re.sub(r"(?<!:)//[^\n]*", "", text)
    return text


def _family_violation(val: str, tok_vars: set[str],
                      prefix: str = "font-family") -> str | None:
    """font-family 值 → 违规文案或 None。var() 只豁免 **tokens 已
    定义的变量**（var(--invented-font) 这类未定义变量不获准——
    七轮评审反例）；var(--x, serif) 回退值剥离，只取变量名。"""
    if val.startswith("var("):
        var_name = val[len("var("):].split(",")[0].split(")")[0].strip()
        if var_name in tok_vars:
            return None  # tokens 定义的变量 = 合法消费
        return f"{prefix} {val} ——变量未在 tokens 定义"
    return (f"{prefix} 字面量 \"{val}\"——"
            "族由 styles.json/tokens 合同管，页面不得自写")


def collect_tokens(tokens_path: Path) -> tuple[set[str], set[str], set[str]]:
    """tokens.ts 白名单：hex 集合 + 字号集合 + CSS 变量名集合。

    字号提取限定 **fontSize 键的键值对**（值收、键名不收、
    lineHeight 等非字号键跳过、注释先剥——七轮评审：块内
    re.findall(\\d+) 把键名/注释/lineHeight 数字全收成了字号）。
    变量名集合供 var() 豁免白名单——var(--invented-font) 这类
    未定义变量不获准。"""
    hexes, sizes, css_vars = set(), set(), set()
    if not tokens_path.is_file():
        return hexes, sizes, css_vars
    text = _strip_comments(tokens_path.read_text(encoding="utf-8"))
    hexes = {m.group(0).lower() for m in HEX_RE.finditer(text)}
    # 变量名收集区分**定义 vs 引用**（八轮评审）：定义必带冒号
    # （--x: / 引号键 '--x': / :root 内 --x:），引用 var(--x) 后跟
    # 括号自然排除——负向后行 (?<!var\() 堵不住 var( --x ) 空格形态
    # （双轴四轮实测绕过），前看冒号才是结构化判据
    css_vars = {m.group(1) for m in
                re.finditer(r'''(--[\w-]+)\s*['"]?\s*:''', text)}
    # fontSize 块（一层嵌套）：解析键值对，值收、非字号键跳过
    for m in re.finditer(
            r'''fontSize\s*[=:]\s*\{((?:[^{}]|\{[^{}]*\})*)\}''',
            text, re.I | re.S):
        for kv in re.finditer(
                r'''["']?([\w-]+)["']?\s*[:=]\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?''',
                m.group(1)):
            key = kv.group(1).lower()
            if "height" in key or key in ("lh", "leading"):
                continue  # lineHeight/行高不是字号
            sizes.add(kv.group(2))
    for m in re.finditer(
            r'''fontSize\s*:\s*["']?(\d+(?:\.\d+)?)(?:px)?["']?''', text):
        sizes.add(m.group(1))
    return hexes, sizes, css_vars


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", required=True, help="工程 src 目录")
    ap.add_argument("--tokens", default=None,
                    help="tokens.ts 路径（默认 <src>/tokens.ts）")
    ap.add_argument("--stack", default="react", choices=["react", "vue"],
                    help="栈形态（决定页面文件通配，1009-16）")
    ap.add_argument("--out", default=None,
                    help="报告 JSON 路径（默认 <src>/../pipeline/"
                         "style-lint_report.json——1012-06 默认值必死："
                         "缺省不落报告则 record 无文件可校验）")
    args = ap.parse_args()
    src = Path(args.src)
    tokens = Path(args.tokens) if args.tokens else src / "tokens.ts"
    tok_hex, tok_size, tok_vars = collect_tokens(tokens)
    if not tok_hex and not tok_size and not tok_vars:
        print(f"style-lint: tokens 白名单为空（{tokens}）——先完成⑥"
              "提取设计系统，或 --tokens 显式指定")
        return 1

    violations: list[str] = []
    # rglob 递归（嵌套页面目录也要扫）；CSS 文件的字面量同管
    glob = "*.vue" if args.stack == "vue" else "*.tsx"
    pages = sorted((src / "pages").rglob(glob)) if (src / "pages").is_dir() \
        else sorted(src.rglob(glob))
    stylesheets = sorted(src.rglob("*.css"))
    if not pages:
        print(f"style-lint: 所选栈({args.stack})目标页面数为零——零覆盖"
              "报告不得给门禁背书（1009-16）")
        return 1
    for p in pages:
        if args.stack == "vue":
            # Vue SFC：<style> 块 + template 内联 style 属性 → CSS 形态
            raw = p.read_text(encoding="utf-8")
            parts = [m.group(1) for m in
                     re.finditer(r"<style[^>]*>(.*?)</style>", raw, re.S | re.I)]
            parts += [m.group(1).replace("&quot;", '"') for m in
                      re.finditer(r'style="([^"]*)"', raw)]
            text = _strip_comments("\n".join(parts), css=True)
            for m in HEX_RE.finditer(text):
                v = m.group(0).lower()
                if v not in tok_hex and v not in COLOR_ALLOW:
                    violations.append(f"{p.name}: 颜色 {v} 不在 tokens")
            for m in CSS_FONTSIZE_RE.finditer(text):
                if m.group(1) not in tok_size:
                    violations.append(
                        f"{p.name}: 字号 {m.group(1)}px 不在 tokens")
            for m in CSS_FAMILY_RE.finditer(text):
                v = _family_violation(m.group(1).strip(), tok_vars,
                                      prefix="css font-family")
                if v:
                    violations.append(f"{p.name}: {v}")
            continue
        text = _strip_comments(p.read_text(encoding="utf-8"))
        for m in HEX_RE.finditer(text):
            v = m.group(0).lower()
            if v not in tok_hex and v not in COLOR_ALLOW:
                violations.append(f"{p.name}: 颜色 {v} 不在 tokens")
        for m in FONTSIZE_RE.finditer(text):
            v = m.group(1) or m.group(2)
            if v not in tok_size:
                violations.append(f"{p.name}: 字号 {v}px 不在 tokens")
        for m in FAMILY_RE.finditer(text):
            v = _family_violation(m.group(1).strip(), tok_vars)
            if v:
                violations.append(f"{p.name}: {v}")
    for p in stylesheets:
        text = _strip_comments(p.read_text(encoding="utf-8"), css=True)
        for m in HEX_RE.finditer(text):
            v = m.group(0).lower()
            if v not in tok_hex and v not in COLOR_ALLOW:
                violations.append(f"{p.name}: css 颜色 {v} 不在 tokens")
        for m in CSS_FONTSIZE_RE.finditer(text):
            if m.group(1) not in tok_size:
                violations.append(
                    f"{p.name}: css 字号 {m.group(1)}px 不在 tokens")
        for m in CSS_FAMILY_RE.finditer(text):
            v = _family_violation(m.group(1).strip(), tok_vars,
                                  prefix="css font-family")
            if v:
                violations.append(f"{p.name}: {v}")

    exit_code = 1 if violations else 0
    # 1012-06：先写报告（内嵌 src_hash）→ 再 record（读盘校验）。
    # --out 默认必死（<src>/../pipeline/style-lint_report.json，与账本
    # 同目录）——此前 record 传空串无报告文件，原始输出无文件可引。
    out_path = (Path(args.out) if args.out
                else src.parent / "pipeline" / "style-lint_report.json")
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    from evidence_index import record, src_hash, RecordRejected  # noqa: E402
    src_h = src_hash(src) if src.exists() else "no-src"
    report = {"tool": "style-lint", "src_hash": src_h,
              "stack": args.stack, "tokens": str(tokens),
              "pages_scanned": len(pages), "stylesheets": len(stylesheets),
              "violations": violations[:200], "violation_count": len(violations),
              "exit_code": exit_code,
              "time": time.strftime("%Y-%m-%dT%H:%M:%S")}
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=1),
                        encoding="utf-8")
    try:
        record(src.parent / "pipeline" / "evidence_index.jsonl",
               "style-lint", str(src), src, [p.name for p in pages], {},
               exit_code, len(pages), str(out_path))
    except RecordRejected as exc:
        # 证据本体不可信：与主判定取或，禁静默（1012-06 定标点名①）
        print(f"style-lint: 证据拒账，exit 置 1——{exc}", file=sys.stderr)
        exit_code = 1
    except Exception:
        pass  # 索引 IO 失败不掩盖主判定（既有豁免语义）
    if violations:
        print(f"style-lint: {len(violations)} 处 tokens 外样式发明：")
        for v in violations[:40]:
            print("  -", v)
        return exit_code  # 1012-06：拒账时同为 1（取或）
    print(f"style-lint: {len(pages)} 页(stack={args.stack}) + "
          f"{len(stylesheets)} css 全部在 tokens 合同内 ✓")
    return exit_code  # 1012-06：无违规但拒账时 = 1（证据不可信不得背书）


if __name__ == "__main__":
    sys.exit(main())
