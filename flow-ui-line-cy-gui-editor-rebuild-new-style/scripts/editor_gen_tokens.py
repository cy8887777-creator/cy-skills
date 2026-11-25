# -*- coding: utf-8 -*-
"""editor_gen_tokens — 片段 → 令牌/风格包 JSON 生成器（附加A 转化线）

覆盖转化管线中"值域扫描生成 design-system/style-blocks"一步的通用工具化（审查 A2）。
自动化部分：值域扫描登记（lint 过闸用）、四围栏骨架、正本最小集槽位清单。
AI 填写部分：语义槽取值（primary/bg/surface/…的真实色值）——工具从 --palette JSON 取；
未给的槽位写 TODO 占位并在结尾打印待填清单（直接跑 lint 会拦 TODO 色值，填完再验）。

用法：
  python editor_gen_tokens.py --pages <片段目录> --out-dir <intake目录> \\
    [--palette <语义槽.json>] [--colors <色映射.json>] [--ext-keys <扩展键.json>] \\
    [--title <项目名>] [--pack-id <包id>]

语义槽 JSON（--palette）示例：
  {"primary": "#1769E0", "bg": "#FFFFFF", "surface": "#FFFFFF", "text-primary": "#17202A",
   "text-secondary": "rgba(23,32,42,.45)", "border": "rgba(23,32,42,.07)",
   "success": "#00A2C7", "danger": "#D5383D", "warning": "#FFCA16",
   "font-body": "...", "radius-sm": "8px", "radius-md": "12px", "radius-lg": "16px", ...}
键名逐字照 assets/token-keys.json（minimum 键必须给全，否则产物 style-blocks 过不了 verify_blocks）。
"""
import argparse
import io
import json
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

ROOT = Path(__file__).parent.parent
MIN_SET_KEYS = ['primary', 'bg', 'surface', 'surface-alt', 'text-primary', 'text-secondary',
                'border', 'success', 'danger', 'warning', 'hero', 'nav', 'font-head', 'font-body',
                'font-num', 'size-title', 'size-head', 'size-body', 'size-caption', 'weight-head',
                'weight-body', 'line-height-head', 'line-height-body', 'radius-sm', 'radius-md',
                'radius-lg', 'space-1', 'space-2', 'space-3', 'space-4', 'size-ctl-sm',
                'size-ctl-md', 'size-ctl-lg', 'shadow-sm', 'shadow-md', 'border-width',
                'motion-duration-base', 'motion-easing-base']


def scan_lengths(text):
    """按用途分桶扫 px 值（对齐 lint_tokens by_use 口径）。"""
    buckets = {'radius': set(), 'ctlsize': set(), 'space': set(), 'fontsize': set()}
    for m in re.finditer(r'([a-z-]+)\s*:\s*([^;{}"\'<]+)[;}"\']', text):
        prop, val = m.group(1), m.group(2)
        if prop in ('margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
                    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left', 'gap'):
            buckets['space'].update(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)px', val))
        elif prop == 'border-radius':
            buckets['radius'].update(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)px', val))
        elif prop == 'font-size':
            buckets['fontsize'].update(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)px', val))
        elif prop in ('width', 'height', 'min-width', 'min-height', 'max-width', 'max-height'):
            buckets['ctlsize'].update(float(x) for x in re.findall(r'(\d+(?:\.\d+)?)px', val))
    return buckets


def scan_shadows(text):
    return [re.sub(r'\s+', ' ', m.group(1)).strip().rstrip(';').lower()
            for m in re.finditer(r'box-shadow:\s*([^;{}]+)[;}]', text)]


def numkey(v):
    return str(v).rstrip('0').rstrip('.').replace('.', '-') if isinstance(v, float) else str(v)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True, help='片段目录（值域扫描面=全部 html 含内联 style）')
    ap.add_argument('--out-dir', required=True, help='输出目录（惯例=intake/）')
    ap.add_argument('--selection', help='选型回传 JSON（intake/selection-result.json）：直接消费 skeletonTokens '
                                         '填语义槽（选型→转化数据直通）；取第一个 selected，--palette 显式键优先')
    ap.add_argument('--palette', help='语义槽 JSON（键照 token-keys.json；不给=全部 TODO 占位）')
    ap.add_argument('--colors', help='色映射 JSON（转化器同名参数；用于提示核对）')
    ap.add_argument('--ext-keys', help='扩展键 JSON')
    ap.add_argument('--title', default='未命名转化项目')
    ap.add_argument('--pack-id', default='pack-converted')
    a = ap.parse_args()

    pages = Path(a.pages)
    # rglob 深扫（试点内伤#5）：convert 带 --groups 时片段落 pages/<组>/ 子目录，单层 glob 读到 0 片段静默产空壳
    texts = [p.read_text(encoding='utf-8') for p in sorted(pages.rglob('*.html'))
             if not p.name.startswith('zz-')]
    full = '\n'.join(texts)
    if not texts:
        print('FAIL 值域扫描读到 0 片段（--pages 目录无 html 或全为占位屏）')
        raise SystemExit(2)

    buckets = scan_lengths(full)
    shadows = scan_shadows(full)
    ext_keys = json.loads(Path(a.ext_keys).read_text(encoding='utf-8-sig')) if a.ext_keys else {}

    def _load_json(p, what):
        try:
            return json.loads(Path(p).read_text(encoding='utf-8-sig'))
        except Exception as e:
            print('FAIL %s 文件不可解析: %s | %s' % (what, p, e))
            raise SystemExit(2)

    palette = _load_json(a.palette, '语义槽 --palette') if a.palette else {}
    selection = _load_json(a.selection, '选型回传 --selection') if a.selection else None
    sel_meta = {}
    if selection:
        sel = None
        for g in (selection.get('audienceGroups') or []):
            picked = g.get('selected') or []
            if picked:
                sel = picked[0]
                break
        if not sel:
            print('FAIL selection-result.json 里没有任何 selected 候选')
            raise SystemExit(2)
        sk = sel.get('skeletonTokens') or {}
        for k, v in sk.items():
            palette.setdefault(k, v)  # selection 填槽；--palette 显式键不被覆盖
        sel_meta = {'styleId': sel.get('styleId', 'converted'),
                    'styleName': sel.get('styleName') or selection.get('project') or a.title,
                    'mood': sel.get('mood', 'TODO')}
        print('已消费选型回传：%s（%s）——skeletonTokens %d 键填槽' % (sel_meta['styleName'], sel_meta['styleId'], len(sk)))

    # ---- design-system-pilot（lint 值域登记）----
    ds = {
        'name': a.title + '（转化值域登记）',
        'direction': '转化线：值域登记供 lint_tokens 归因；语义槽见 STYLE-PACK',
        'tokens': {},
        'typography': {'fontFamily': palette.get('font-body', 'system-ui,sans-serif'),
                       'baseSize': 13, 'lineHeight': 1.5},
        'components': {},
    }
    todo = []
    for k in ('accent', 'bg', 'surface', 'text', 'muted', 'line', 'ok', 'warn', 'danger'):
        v = palette.get(k)
        if v:
            ds['tokens'][k] = v  # --palette 直通填语义槽（试点卡点#4：此前硬编码 TODO 且三道闸失明=静默产出全灭样式）
        else:
            ds['tokens'][k] = 'TODO-SEMANTIC'
            todo.append(k)
    for bucket, prefix in (('radius', 'radius-'), ('ctlsize', 'size-'), ('space', 'space-'), ('fontsize', 'font-')):
        for v in sorted(buckets[bucket]):
            ds['tokens'][f'{prefix}{numkey(v)}'] = f'{v:g}px'
    for i, sh in enumerate(dict.fromkeys(shadows)):
        ds['tokens'][f'shadow-lit-{i}'] = sh

    # ---- style-blocks 四围栏骨架 ----
    screens = []
    for p in sorted(pages.rglob('page-*.html')):
        m = re.search(r'data-screen="([\w-]+)"[^>]*data-name="([^"]*)"', p.read_text(encoding='utf-8'))
        if m:
            screens.append(m.group(1))
    style_keys = {}
    for k in MIN_SET_KEYS:
        if k in palette:
            style_keys[k] = palette[k]
        elif k in ('hero', 'nav'):
            continue  # 可缺省键（emits 有跟随逻辑），骨架不给
        else:
            style_keys[k] = 'TODO-MINIMUM'
            todo.append(k)
    style_keys.update(ext_keys)
    pal0 = [palette.get('primary', 'TODO'), palette.get('bg', 'TODO'),
            palette.get('text-primary', 'TODO'), palette.get('surface', 'TODO')]
    pack = {
        'STYLE-REGISTRY': {
            'schemaVersion': 1,
            'domBases': [{'domBaseId': 'db-main', 'note': '转化线骨架（源稿即骨架）', 'pages': screens}],
            'families': [{'familyId': 'fam-converted', 'domBaseId': 'db-main',
                          'label': a.title, 'members': [a.pack_id],
                          'note': '转化线：源稿即骨架'}],
        },
        'STYLE-PACK': {
            'schemaVersion': 1,
            'packs': [{
                'packId': a.pack_id, 'familyId': 'fam-converted',
                'identity': {'styleId': sel_meta.get('styleId', 'converted'),
                             'styleName': sel_meta.get('styleName', a.title),
                             'origin': 'ai-generated' if sel_meta.get('styleId', 'converted').startswith('gen:') else 'wiki',
                             'mood': sel_meta.get('mood', 'TODO-一句话情绪')},
                'tokens': style_keys,
                'palettes': [{'paletteId': 'pal-default', 'label': '品牌原色',
                              'swatches': pal0,
                              'hero': palette.get('primary'), 'line': palette.get('border'),
                              'muted': palette.get('text-secondary')}] +
                             [{'paletteId': f'pal-extra-{i}', 'label': f'TODO-配色{i}',
                               'swatches': ['TODO', 'TODO', 'TODO', 'TODO']}
                              for i in range(1, 4)],
                'iconSet': 'inline-svg',
                'l2Overrides': [],
            }],
        },
        'COMPONENT-PACK': {'schemaVersion': 1, 'packFor': a.pack_id, 'components': []},
        'STYLE-CONTRACT': {
            'schemaVersion': 1, 'domBaseId': 'db-main',
            'styleOrigin': {'styleId': 'converted', 'mood': 'TODO'},
            'pages': [{'pageId': s, 'form': '转化自源稿（骨架以源稿为准）',
                       'regions': [{'region': '整页', 'shape': 'source', 'count': 1}]} for s in screens],
            'motion': {'tier': 'c', 'tokens': {'duration': '150ms', 'easing': 'ease'}},
            'density': 'medium',
        },
    }

    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'design-system-converted.json').write_text(
        json.dumps(ds, ensure_ascii=False, indent=1), encoding='utf-8')
    (out / 'style-blocks.json').write_text(
        json.dumps(pack, ensure_ascii=False, indent=1), encoding='utf-8')
    print('已生成:', out / 'design-system-converted.json', '+', out / 'style-blocks.json')
    print('值域 tokens 叶:', len(ds['tokens']), '| shadow 登记:', len(set(shadows)),
          '| 屏:', len(screens), '| 扩展键:', len(ext_keys))
    if todo:
        print('待填语义槽（人工兜底清单：lint 归因会拦硬值；verify_blocks 不拦 TODO）:', ', '.join(todo))
    print('AI 待办：①语义槽真实值（对照账3）②palettes 同风格配色 4-5 套跨色相 ③COMPONENT-PACK 10-15 条组件'
          ' ④identity.mood 情绪词——骨架已就位，按本包 references/conversion.md 第 2 步口径填写')


if __name__ == '__main__':
    main()
