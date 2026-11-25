"""
scripts/core/parse_common.py — 定案 HTML 解析公共模块（html_to_json / html_to_md 共用）

v4.0 抽取：两转换器的重复解析逻辑收拢于此，防"修一处漏同构一处"（standards 审查 S6）。
统一度量行解析：值判定 = b 含单位或纯数字（样张如「XX Aa 123」不算）；阴影行值在实物 style。
"""
import re

METRIC_TOKEN_RE = (r'--(?:font-size|weight|line-height|space|padding|stroke|'
                   r'opacity|radius|shadow|z)-[\w.-]+')


def txt(s):
    s = re.sub(r"<[^>]+>", "", s)
    return (s.replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&")
             .replace("&quot;", '"').strip())


def sec(html, sid):
    m = re.search(r'<section class="chapter" id="%s">(.*?)</section>' % sid, html, re.S)
    return m.group(1) if m else ""


def lis(block):
    return [txt(x) for x in re.findall(r"<li[^>]*>(.*?)</li>", block, re.S) if txt(x)]


def table_md(block):
    """HTML 表格 → md 表格文本；无表格返回 ''"""
    t = re.search(r"<table>(.*?)</table>", block, re.S)
    if not t:
        return ""
    head = [txt(c) for c in re.findall(r"<th[^>]*>(.*?)</th>", t.group(1), re.S)]
    rows = []
    for tr in re.findall(r"<tr>(.*?)</tr>", t.group(1), re.S):
        cells = [txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr, re.S)]
        if cells:
            rows.append(cells)
    if not head:
        head = ["列%d" % (i + 1) for i in range(len(rows[0]) if rows else 0)]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for r in rows:
        r = (r + [""] * len(head))[:len(head)]
        lines.append("| " + " | ".join(x.replace("|", "\\|") for x in r) + " |")
    return "\n".join(lines) + "\n"


def parse_keyed_table(block):
    """首格为 <code>token</code> 的表 → [{token, value, usage?, prohibition?}]"""
    rows = []
    for tr in re.findall(r"<tr><td><code>([^<]*)</code></td>(.*?)</tr>", block, re.S):
        cells = [txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr[1], re.S)]
        row = {"token": tr[0], "value": cells[0] if cells else ""}
        if len(cells) > 1:
            row["usage"] = cells[1]
        if len(cells) > 2 and cells[2] not in ("—", ""):
            row["prohibition"] = cells[2]
        rows.append(row)
    return rows


def parse_swatches(s5):
    """基础层色卡墙 → [(name, hex, usage)]"""
    out = []
    for m in re.finditer(r'<button class="swatch"[^>]*?data-hex="([^"]*)">(.*?)</button>', s5, re.S):
        seg = m.group(2)
        nm = re.search(r'<span class="nm">([^<]*)</span>', seg)
        hx = re.search(r'<span class="hx">(.*?)</span>', seg, re.S)
        if not nm:
            continue
        usage = txt(hx.group(1)) if hx else ""
        usage = re.sub(r"^#[0-9a-fA-F]{6}\s*·\s*", "", usage)
        out.append((nm.group(1), m.group(1), usage))
    return out


def _metric_value(win, text):
    """窗口 → (value, usage) 或 (None, None)。值判定通用化：b 含单位/纯数字才算值。"""
    bm = re.search(r"<b[^>]*>(.*?)</b>", win, re.S)
    bval = txt(bm.group(1)).strip() if bm else ""
    if bval and (re.search(r"px|%|ms\b", bval) or re.fullmatch(r"[\d.]+", bval)):
        rest = text.replace(bval, "", 1)
        return bval, re.sub(r"^[·\s]+", "", rest).strip()
    # b 是样张（如「XX Aa 123」）→ 从 text 剔除再匹配
    if bval:
        text = text.replace(bval, "", 1).strip()
    vm = re.search(r"([\d.]+(?:px|%|ms)?)\s*(（@2x\s*[\d.]+px）)?\s*·\s*(.*)", text)
    if vm:
        val = vm.group(1) + (("（@2x " + vm.group(2)[5:-1] + "）") if vm.group(2) else "")
        return val, vm.group(3).strip()
    # 头部裸数值（行高 1.45 / 透明度 0.15，无 · 分隔）
    hm = re.match(r"([\d.]+)\s*(.*)", text)
    if hm and not re.match(r"[\u4e00-\u9fff]", text[:1]):
        return hm.group(1), hm.group(2).strip()
    return None, None


def extract_metric_rows(body_all):
    """度量实物行解析（HTML 主源）。含阴影 style 值分支。→ [{token, value, usage}]"""
    rows, seen = [], set()
    for mm in re.finditer(r'<code[^>]*>(%s)</code>' % METRIC_TOKEN_RE, body_all):
        tok = mm.group(1)
        if tok in seen:
            continue
        nxt = re.search(r"<code[^>]*>--", body_all[mm.end():])
        win = body_all[mm.end(): mm.end() + (nxt.start() if nxt else 500)]
        text = txt(win).strip()
        if not text:
            continue
        if tok.startswith("--shadow-"):
            sm = re.search(r'box-shadow:\s*([^;"]+)', win)
            if sm:
                seen.add(tok)
                usage = re.split(r"\s{2,}|\s·\s", text, maxsplit=1)[0]
                usage = re.sub(r"^--[\w.-]+\s*", "", usage).strip()
                rows.append({"token": tok, "value": " ".join(sm.group(1).split()), "usage": usage})
            continue
        value, usage = _metric_value(win, text)
        if value:
            seen.add(tok)
            rows.append({"token": tok, "value": value, "usage": usage})
    return rows


def metric_body(html, sids=("s6", "s7", "s8", "s9", "s10")):
    return "".join(sec(html, s) for s in sids)
