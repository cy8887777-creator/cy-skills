# -*- coding: utf-8 -*-
"""
把团队定稿的 Jam3a 术语表（21KB，EN/CN/AR，PM+同事拍板）转成技能可消费的干净资产。

策略（PM 2026-09-02 指令：团队表为准）：
  - terms_ar.json / 术语表.md  : 团队表 authoritative；内置 140 条仅作「缺口补充」（同 EN 键冲突以团队胜）
  - keep_latin.json            : 不可译清单（保留拉丁）+ 合规禁用词
  - 术语表_Jam3a团队定稿.md     : 原表复制（含全部备注/裁决，作 provenance，不供解析）

输出均落在 skills/mockingbot-ar-flat/references/，使技能自包含、不再依赖其他文件夹的表。
"""
import re, json, os

REF  = r"C:/Users/1/.workbuddy/skills/mockingbot-ar-flat/references"
TEAM = r"D:/workbuddy项目/Jam3a/8.13/Jam3a术语表_英-中-阿.md"
BUILTIN = os.path.join(REF, "术语表_内置140.md")   # 稳定源，构建脚本只读取、不写入

# 合规面向用户文案禁用阿语词（源表 §八 明确禁止）
BANNED_AR = ["قمار", "مراهنة", "رهان", "مقامرة"]

AR_RE = re.compile(r'[\u0600-\u06FF]')

def split_en(en):
    en = en.replace('**', '').replace('`', '')
    parts = re.split(r'\s*/\s*', en)
    out = []
    for p in parts:
        p = re.sub(r'\s*[（(].*?[）)]\s*', '', p).strip()  # 去除 (...) / （）
        p = p.strip()
        if p:
            out.append(p)
    return out

def norm_key(k):
    return re.sub(r'\s+', ' ', k.lower().strip())

def clean_ar(ar):
    return ar.replace('**', '').replace('`', '').strip()

def is_sep(cells):
    return all(re.fullmatch(r'[:\- ]*', c) for c in cells if c != '')

def is_header(cells):
    joined = ' '.join(cells)
    if not re.search(r'英文|中文|阿拉伯语|处理|阿语备注|风险|ID', joined):
        return False
    if any(AR_RE.search(c) for c in cells if c):   # 含阿语的是数据行，不是表头
        return False
    return True

# ---------- 解析团队表 ----------
out, cnmap, order = {}, {}, []
keep_latin, banned_en = set(), set()

def add(token, ar, cn):
    if not re.search(r'[A-Za-z]', token):   # 仅收录含拉丁字母的真英文键，过滤误入的备注/中文
        return
    if token in out:
        return
    out[token] = ar
    cnmap[token] = cn
    order.append(token)

cur_section = ""
with open(TEAM, encoding='utf-8') as f:
    lines = f.readlines()

cols = None
for line in lines:
    s = line.rstrip('\n')
    if s.startswith('## '):
        cur_section = s[3:].strip()
        cols = None
        continue
    if not s.strip().startswith('|'):
        continue
    cells = [c.strip() for c in s.strip().strip('|').split('|')]
    if is_sep(cells):
        continue   # 分隔行不清除 cols；列映射由上一个表头设定，直到下一个 `## ` 段标题才清
    if is_header(cells):
        cols = {}
        for idx, c in enumerate(cells):
            if '英文' in c: cols['en'] = idx
            elif '中文' in c: cols['cn'] = idx
            elif '阿拉伯语' in c or '阿语' in c: cols['ar'] = idx
            elif '处理' in c or '阿语备注' in c: cols['handle'] = idx
            elif '风险' in c: cols['risk'] = idx
            elif c.upper() == 'ID': cols['id'] = idx
        continue
    if cols is None:
        continue
    en_idx = cols.get('en')
    if en_idx is None or en_idx >= len(cells):
        continue
    en_raw = cells[en_idx]
    cn_idx = cols.get('cn')
    cn = cells[cn_idx] if (cn_idx is not None and cn_idx < len(cells)) else ''
    ar_idx = cols.get('ar')

    # §一 不可译清单：无 阿拉伯语 列 → 全部保留拉丁
    if ar_idx is None or ar_idx >= len(cells):
        for raw in split_en(en_raw):
            t = raw.strip()
            if re.search(r'[一-鿿]', t) or not re.search(r'[A-Za-z]', t):
                continue   # 跳过误入的备注/中文，只收真专有名词
            keep_latin.add(t)
        continue

    ar_raw = cells[ar_idx]
    if '🚫' in ar_raw:
        # 禁用词保留完整短语；仅按「空格/空格」拆（Stake / Staking），避免把 Daily/Weekly 拆成 Daily 误伤合法词
        for raw in re.split(r'\s+/\s+', en_raw.replace('**', '').replace('`', '')):
            raw = raw.strip()
            if raw:
                banned_en.add(raw)
        continue
    # 非权威别名（如 （Age Restriction））不入库
    if '（' in en_raw or '）' in en_raw:
        continue
    ar_clean = clean_ar(ar_raw)
    # 保留拉丁：含「保留」/ 译文为空 / 译文即原词 / 译文纯拉丁数字
    if ('保留' in ar_raw or ar_clean == '' or ar_clean == en_raw.strip()
            or re.fullmatch(r'[A-Za-z0-9 /.\-]+', ar_clean)):
        for tok in split_en(en_raw):
            keep_latin.add(tok)
        continue
    for tok in split_en(en_raw):
        add(tok, ar_clean, cn)

# ---------- 合并内置 140 条（仅缺口补充，团队已存在的键跳过） ----------
with open(BUILTIN, encoding='utf-8') as f:
    blines = f.readlines()
bcols = None
for line in blines:
    s = line.rstrip('\n')
    if not s.strip().startswith('|'):
        continue
    cells = [c.strip() for c in s.strip().strip('|').split('|')]
    if is_sep(cells):
        continue   # 分隔行不清除 bcols；列映射由上一个表头设定
    joined = ' '.join(cells)
    if '中文' in joined and '英文' in joined and '阿拉伯语' in joined:
        bcols = {'cn': 0, 'en': 1, 'ar': 2}
        continue
    if bcols is None:
        continue
    cn = cells[0]
    en_raw = cells[1]
    ar_clean = clean_ar(cells[2])
    for tok in split_en(en_raw):
        if tok in out:        # 团队已定义 → 团队胜，跳过
            continue
        add(tok, ar_clean, cn)

banned_en.add("Age Restriction")   # 源表标注非权威，建议改 Age Verification

# ---------- 写出 ----------
terms_json = {tok: out[tok] for tok in order}
with open(os.path.join(REF, "terms_ar.json"), "w", encoding="utf-8") as f:
    json.dump(terms_json, f, ensure_ascii=False, indent=2)

keep = {
    "keep_latin": sorted(keep_latin),
    "banned_ar": BANNED_AR,
    "banned_en": sorted(banned_en),
}
with open(os.path.join(REF, "keep_latin.json"), "w", encoding="utf-8") as f:
    json.dump(keep, f, ensure_ascii=False, indent=2)

md = ["# Jam3a 术语表（中文 / 英文 / 阿拉伯语）— 团队定稿合并版",
      "",
      "> 权威源：`术语表_Jam3a团队定稿.md`（项目组同事+PM 2026-08-29 定稿）。",
      "> 本文件 = 团队表 authoritative + 内置 140 条缺口补充（同词冲突以团队胜）。",
      "> 供 `gen_ar_flat.mjs --terms` 直接消费（Markdown 三栏 `| 中文 | 英文 | 阿拉伯语 |`）。",
      "",
      "| 中文 | 英文 | 阿拉伯语 |",
      "| :--- | :--- | :--- |"]
for tok in order:
    md.append(f"| {cnmap[tok]} | {tok} | {out[tok]} |")
with open(os.path.join(REF, "术语表.md"), "w", encoding="utf-8") as f:
    f.write("\n".join(md) + "\n")

print(f"terms_ar.json  : {len(terms_json)} 条")
print(f"keep_latin     : {len(keep['keep_latin'])} 个  (+banned_ar {len(BANNED_AR)}, banned_en {len(keep['banned_en'])})")
print(f"覆盖示例       : Log In={out.get('Log In')}  Battle Pass={out.get('Battle Pass')}  Skin={out.get('Skin')}  Crew={out.get('Crew')}  Leaderboard={out.get('Leaderboard')}")
print("keep_latin 样本:", sorted(keep_latin)[:20])
