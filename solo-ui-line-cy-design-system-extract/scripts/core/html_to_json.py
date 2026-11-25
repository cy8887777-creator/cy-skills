# -*- coding: utf-8 -*-
"""html_to_json.py — 从定案 design-system.html 派生 system-rules.json（机器可读规则版 · 正式）。
产物关系（v4.1 定案链路）：定案 HTML 为权威事实源，json 与 md 皆从 HTML 派生，
不一致以 HTML 为准回改；度量主源 = HTML 各章实物行（md 先行是旧思维，已废弃），
定案 md（若已存在）仅作 cross_check。本脚本只读 HTML（可选读 md 对账），不碰 work/ 中间产物。
输出 = out/system-rules.json（与 md/html 同一内容第三构造）。"""
import io, json, os, re, sys

from parse_common import (txt, sec, lis, parse_keyed_table, parse_swatches,
                          extract_metric_rows, metric_body, METRIC_TOKEN_RE)

FLOOR_PX = 11.0  # 字体档位下限（1x）——低于它的稿值不立档，并入最近可读档


def _font_below_floor(row):
    """font-size token 主值（1x）< 11px → True（输出规则第 8 句）"""
    tok = row.get("token", "")
    if not tok.startswith("--font-size"):
        return False
    m = re.match(r"([\d.]+)px", row.get("value", ""))
    return bool(m) and float(m.group(1)) < FLOOR_PX


def main_out(out_dir):
    return (os.path.join(out_dir, "design-system.html"),
            os.path.join(out_dir, "system-rules.json"))

def sec(html, sid):
    m = re.search(r'<section class="chapter" id="%s">(.*?)</section>' % sid, html, re.S)
    return m.group(1) if m else ""

def txt(s):
    return re.sub(r"<[^>]+>", "", s).replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").strip()

def lis(block):
    return [txt(x) for x in re.findall(r"<li>(.*?)</li>", block, re.S) if txt(x)]

def main():
    import sys as _sys
    if len(_sys.argv) != 2:
        print("用法: python html_to_json.py <项目out目录>", file=_sys.stderr)
        return 2
    HTML, DEST = main_out(_sys.argv[1])
    if not os.path.exists(HTML):
        print("[FAIL] 定案 HTML 不存在: %s——先完成站④第 1 步（gen_html + 补全定案）" % HTML, file=_sys.stderr)
        return 2
    h = io.open(HTML, encoding="utf-8").read()

    # ---------- meta ----------
    hero = re.search(r'<header class="hero">(.*?)</header>', h, re.S).group(1)
    system = txt(re.search(r"<h1>(.*?)</h1>", hero, re.S).group(1))
    en = txt(re.search(r'<div class="h1-en">(.*?)</div>', hero, re.S).group(1))
    version = re.search(r"v([\d.]+)", en).group(1)
    meta_kv = dict(re.findall(r'<span class="k">([^<]*)</span><span class="v">(.*?)</span>', hero, re.S))
    meta_kv = {txt(k): txt(v) for k, v in meta_kv.items()}

    # ---------- values（§01）----------
    s1 = sec(h, "s1")
    values = [(n, txt(d)) for n, d in re.findall(r"<li><b>([^<]+)</b>\s*——\s*([^<]*)</li>", s1)]

    # ---------- tokens ----------
    s5 = sec(h, "s5")
    primitive = [{"name": n, "value": v, "usage": u} for n, v, u in parse_swatches(s5)]
    def parse_table(block):
        rows = []
        for tr in re.findall(r"<tr><td><code>([^<]*)</code></td>(.*?)</tr>", block, re.S):
            cells = [txt(c) for c in re.findall(r"<td[^>]*>(.*?)</td>", tr[1], re.S)]
            rows.append({"token": tr[0], "value": cells[0] if cells else "",
                         **({"usage": cells[1]} if len(cells) > 1 else {}),
                         **({"prohibition": cells[2]} if len(cells) > 2 and cells[2] not in ("—", "") else {})})
        return rows
    semantic = parse_table(re.search(r'SEMANTIC · 语义层（\d+）</div>(.*?)</div>', s5, re.S).group(1))
    component_tokens = parse_table(re.search(r'COMPONENT · 组件层（\d+）</div>(.*?)</div>', s5, re.S).group(1))
    # 度量：主源 = HTML 各章实物行（v4 修正——md 先行是旧思维，首跑无 md 必崩）；
    # 定案 md（若已存在）仅作 cross_check 参考；标题兼容「度量（N）」「度量」两形态
    metric_dedup = [r for r in extract_metric_rows(metric_body(h))
                    if not _font_below_floor(r)]
    seen = {r["token"] for r in metric_dedup}
    # :root 全量补缺：只认 gen_html 渲染的块（特征 = build_css_vars 的「/* Metric */」
    # 英文段注释；手搓 HTML 的 :root 命名不同构，禁补——防异名变量混入规范档）
    _semcomp = {r["token"] for r in semantic} | {r["token"] for r in component_tokens}
    for blk in re.findall(r":root\s*\{([^{}]*)\}", h):
        if "/* Metric */" not in blk or "--skin-" in blk:
            continue
        for m in re.finditer(r'(--[\w.-]+)\s*:\s*([^;]+);', blk):
            tok = m.group(1)
            if tok in seen or tok in _semcomp or not re.fullmatch(METRIC_TOKEN_RE, tok):
                continue
            if tok.startswith("--font-size"):
                _v1x = re.match(r"[\d.]+", m.group(2).strip())
                if _v1x and float(_v1x.group(0)) < 11:
                    continue
            tok = m.group(1)
            if tok in seen or not re.fullmatch(METRIC_TOKEN_RE, tok):
                continue
            seen.add(tok)
            metric_dedup.append({"token": tok, "value": m.group(2).strip(),
                                 "usage": "（:root 载体）"})
    md_path = os.path.join(_sys.argv[1], "system-rules.md")
    if os.path.exists(md_path):
        md_text = io.open(md_path, encoding="utf-8").read()
        m54 = re.search(r"###\s*5\.4\s*度量（?\d*）?\s*\n(.*?)\n## 6\.", md_text, re.S)
        if m54:
            for tr in re.findall(r'\|\s*`(--[\w.-]+)`\s*\|\s*([^|]+)\|\s*([^|]+)\|', m54.group(1)):
                tok, val, usage = tr[0].strip(), tr[1].strip(), tr[2].strip()
                if tok in seen:
                    for r in metric_dedup:
                        if r["token"] == tok and r["value"] != val:
                            r["cross_check"] = "md 表值: %s" % val
                elif _font_below_floor({"token": tok, "value": val}):
                    continue
                else:
                    seen.add(tok)
                    metric_dedup.append({"token": tok, "value": val, "usage": usage,
                                         "source_note": "md 表补（HTML 无实物行载体）"})

    # ---------- components（§11 组卡：组名 + 徽章 + 组内规格行）----------
    s11 = sec(h, "s11")
    components = []
    for m in re.finditer(r'<b style="font-size:15px">(\d+)\. ([^<]+)</b>'
                         r'<span style="font-size:11px;color:#979CA5">(\w+)</span>.*?'
                         r'(?:<span style="[^"]*background:#2196[Ff]|<span style="[^"]*">([^<]*已提取[^<]*|[^<]*AI 补全[^<]*))</span>', s11):
        num, cn, en_name, badge = m.group(1), txt(m.group(2)), m.group(3), txt(m.group(4) or "")
        components.append({"name": en_name, "name_cn": cn, "source": badge})
    # 组内变体行（粗粒度：每组的实物行描述）
    comp_count_badge = re.findall(r'已提取[^<]*|AI 补全[^<]*', s11)

    # ---------- requirements（§04）/ prohibitions（§14）----------
    s4 = sec(h, "s4")
    def two_layers(sec_html):
        c = re.search(r'CONCEPTUAL[^<]*</div>\s*<ul class="plain">(.*?)</ul>', sec_html, re.S)
        p = re.search(r'SPECIFIC[^<]*</div>\s*(?:<ul class="plain">|<ol class="plain">)(.*?)</(?:ul|ol)>', sec_html, re.S)
        return lis(c.group(1)) if c else [], lis(p.group(1)) if p else []
    req_c, req_s = two_layers(s4)
    s14 = sec(h, "s14")
    pro_c, pro_s = two_layers(s14)
    a11y = re.search(r'A11Y · 无障碍红线[^<]*</div>\s*<ul class="plain">(.*?)</ul>', s14, re.S)
    a11y_rules = lis(a11y.group(1)) if a11y else []

    # ---------- contrast（§05 表）----------
    contrast = []
    ct = re.search(r'CONTRAST · 对比度实测[^<]*</div>\s*<table>(.*?)</table>', s5, re.S)
    if ct:
        for tr in re.findall(r"<tr><td>(.*?)</td><td>(.*?)</td><td[^>]*>(.*?)</td><td>(.*?)</td></tr>", ct.group(1), re.S):
            contrast.append({"pair": txt(tr[0]), "ratio": txt(tr[1]), "verdict": txt(tr[2]), "usage": txt(tr[3])})

    # ---------- changelog（§15 表）----------
    changelog = []
    for tr in re.findall(r"<tr><td>(v[\d.]+)</td><td>([\d-]+)</td><td>(.*?)</td></tr>", sec(h, "s15"), re.S):
        changelog.append({"version": tr[0], "date": tr[1], "change": txt(tr[2])})

    data = {
        "meta": {
            "system": system, "system_en": en.split("·")[0].strip(), "version": "v" + version,
            "source_of_truth": "design-system.html（定案版）",
            "note": "本 json 与 system-rules.md / design-system.html 为同一内容的三种构造，均从定案 HTML 派生；"
                    "原始提取数据（middle/normalized）为过程留物，见 work/，不属于交付物。",
            "extract_source": meta_kv.get("提取来源 SOURCE", ""), "extract_date": meta_kv.get("提取日期 DATE", ""),
            "token_total": meta_kv.get("TOKEN 总数", ""), "components": meta_kv.get("组件 COMPONENTS", ""),
        },
        "values": [{"name": n, "desc": d} for n, d in values],
        "tokens": {
            "primitive": primitive, "semantic": semantic, "component": component_tokens,
            "metric": metric_dedup,
            "count": len(primitive) + len(semantic) + len(component_tokens) + len(metric_dedup),
        },
        "components": components,
        "design_requirements": {"conceptual": req_c, "specific": req_s},
        "prohibitions": {"conceptual": pro_c, "specific": pro_s, "a11y_redlines": a11y_rules},
        "contrast": contrast,
        "assets": {"icon_library": "icons/（Lucide 线性整库，风格匹配判定见 HTML §12）",
                    "fonts": "system-spec/fonts/（Noto Sans SC + Inter 自托管 woff2）"},
        "changelog": changelog,
    }
    io.open(DEST, "w", encoding="utf-8", newline="\n").write(
        json.dumps(data, ensure_ascii=False, indent=2))
    print("[ok] system-rules.json 生成")
    print("  tokens: primitive %d / semantic %d / component %d / metric %d = %d"
          % (len(primitive), len(semantic), len(component_tokens), len(metric_dedup), data["tokens"]["count"]))
    print("  components 组: %d | values: %d | requirements: %d+%d | prohibitions: %d+%d+%d | contrast: %d"
          % (len(components), len(values), len(req_c), len(req_s), len(pro_c), len(pro_s), len(a11y_rules), len(contrast)))

if __name__ == "__main__":
    sys.exit(main())
