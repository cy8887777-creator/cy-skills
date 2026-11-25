# -*- coding: utf-8 -*-
"""e2e_fixture — 正向测试项目的全部数据（run_e2e.py 的夹具库）。

产出一个最小但完整的工程目录：
  <root>/project.manifest.json
  <root>/intake/开工文档.md
  <root>/intake/selection-result.json   选型回传（4 风格跨 2 族，锁 skeletonTokens）
  <root>/intake/style-blocks.json       四受控块数据（族甲 2 包 + 族乙 2 包，组件 12 个）
  <root>/pages/工作台/接单列表.html      双族页面（db-a / db-b 两套内容容器）
  <root>/pages/钱包/我的钱包.html        同上
  <root>/qa/

键名纪律：所有 tokens 键逐字照 技能根/assets/token-keys.json（全小写连字符）。
最小集纪律：每个风格包 tokens 与选型 skeletonTokens 都带齐全部 minimum 键
（E-PACK-MINIMUM / E-LOCK-MINIMUM），值逐字一致。
"""

import json
import os
from pathlib import Path

SKILL_ROOT = Path(__file__).resolve().parents[2]

PROJECT_TITLE = '接单钱包工作台'
ACTIVE_PACK = 'pack-chenlan'

# ---------------------------------------------------------------- 正本键（供变异用例引用）
PACK_ORDER = ['pack-chenlan', 'pack-bohe', 'pack-dianzi', 'pack-meihong']
STYLE_NAMES = {
    'pack-chenlan': '晨蓝紧凑台',
    'pack-bohe': '薄荷舒展卡',
    'pack-dianzi': '靛紫治理台',
    'pack-meihong': '玫红醒目板',
}


def minimum_keys():
    """正本表（技能根/assets/token-keys.json）minimum=true 的键，按正本顺序。
    E-PACK-MINIMUM / E-LOCK-MINIMUM 的必含集合：包 tokens 与选型 skeletonTokens 都要带齐。"""
    data = json.loads((SKILL_ROOT / 'assets' / 'token-keys.json').read_text(encoding='utf-8-sig'))
    return [k['key'] for k in (data.get('keys') or [])
            if isinstance(k, dict) and k.get('minimum') is True and isinstance(k.get('key'), str)]


def _tokens(primary, radius_md, space_2, weight_head, shadow_md, *, accent_bg, surface_alt,
            text_primary, text_secondary, border_color, font_stack, font_head_stack,
            size_title, size_head, size_body, size_caption,
            radius_sm, radius_lg, space_1, space_3, space_4,
            ctl_sm, ctl_md, ctl_lg, shadow_sm, border_width,
            motion_duration, motion_easing, density, hero_color):
    """按正本表键名组装一个包的 tokens（minimum 全量 + 布局扩展键）。"""
    return {
        'primary': primary, 'bg': accent_bg, 'surface': '#ffffff', 'surface-alt': surface_alt,
        'text-primary': text_primary, 'text-secondary': text_secondary,
        'border': border_color, 'success': '#12b76a', 'danger': '#f04438', 'warning': '#f79009',
        'hero': hero_color, 'nav': '#ffffff',
        'font-head': font_head_stack, 'font-body': font_stack, 'font-num': 'Consolas, ui-monospace, monospace',
        'size-title': size_title, 'size-head': size_head, 'size-body': size_body, 'size-caption': size_caption,
        'weight-head': weight_head, 'weight-body': '400',
        'line-height-head': '1.5', 'line-height-body': '1.7',
        'radius-sm': radius_sm, 'radius-md': radius_md, 'radius-lg': radius_lg,
        'space-1': space_1, 'space-2': space_2, 'space-3': space_3, 'space-4': space_4,
        'size-ctl-sm': ctl_sm, 'size-ctl-md': ctl_md, 'size-ctl-lg': ctl_lg,
        'shadow-sm': shadow_sm, 'shadow-md': shadow_md, 'border-width': border_width,
        'motion-duration-base': motion_duration, 'motion-easing-base': motion_easing,
        'density': density,
    }


SANS = 'Microsoft YaHei, PingFang SC, system-ui, sans-serif'
SERIF = 'Georgia, "Times New Roman", "Songti SC", serif'

PACKS = [
    {
        'packId': 'pack-chenlan', 'familyId': 'fam-a',
        'identity': {'styleId': 'wiki:chenlan', 'styleName': '晨蓝紧凑台', 'origin': 'wiki',
                     'mood': '清晨发单的高效感：直角硬朗、信息密集、蓝色主调'},
        'tokens': _tokens(
            primary='#2563eb', radius_md='6px', space_2='12px', weight_head='700',
            shadow_md='0 2px 6px rgba(22,34,58,.10)',
            accent_bg='#f2f6ff', surface_alt='#eaf1ff', text_primary='#16223a',
            text_secondary='#5b6b85', border_color='#d7e2f4',
            font_stack=SANS, font_head_stack=SANS,
            size_title='20px', size_head='16px', size_body='13px', size_caption='12px',
            radius_sm='4px', radius_lg='10px',
            space_1='8px', space_3='14px', space_4='18px',
            ctl_sm='28px', ctl_md='32px', ctl_lg='38px',
            shadow_sm='0 1px 2px rgba(37,99,235,.05)', border_width='2px',
            motion_duration='220ms', motion_easing='cubic-bezier(.3,.7,.4,1)',
            density='compact', hero_color='#1d4ed8'),
        'palettes': [
            {'paletteId': 'pal-brand', 'label': '品牌晨蓝',
             'swatches': ['#2563eb', '#f2f6ff', '#16223a', '#ffffff']},
            {'paletteId': 'pal-pine', 'label': '松绿',
             'swatches': ['#0f766e', '#f0faf8', '#12332f', '#ffffff']},
        ],
        'iconSet': 'lucide-line',
        'l2Overrides': [
            {'selector': '.kx-card', 'props': 'border-radius:var(--sp-radius-md);box-shadow:var(--sp-shadow-md)'},
        ],
    },
    {
        'packId': 'pack-bohe', 'familyId': 'fam-a',
        'identity': {'styleId': 'wiki:bohe', 'styleName': '薄荷舒展卡', 'origin': 'ai-generated',
                     'mood': '薄荷绿的呼吸感：大圆角、宽松留白、衬线标题'},
        'tokens': _tokens(
            primary='#0d9488', radius_md='18px', space_2='16px', weight_head='600',
            shadow_md='0 8px 24px -8px rgba(20,50,46,.14)',
            accent_bg='#f1faf8', surface_alt='#e6f6f3', text_primary='#143230',
            text_secondary='#587c76', border_color='#d3ece6',
            font_stack=SANS, font_head_stack=SERIF,
            size_title='21px', size_head='16px', size_body='13.5px', size_caption='12px',
            radius_sm='12px', radius_lg='24px',
            space_1='10px', space_3='22px', space_4='28px',
            ctl_sm='30px', ctl_md='36px', ctl_lg='44px',
            shadow_sm='0 1px 3px rgba(13,148,136,.06)', border_width='1px',
            motion_duration='320ms', motion_easing='cubic-bezier(.22,.9,.3,1)',
            density='loose', hero_color='#0f766e'),
        'palettes': [
            {'paletteId': 'pal-brand', 'label': '品牌薄荷',
             'swatches': ['#0d9488', '#f1faf8', '#143230', '#ffffff']},
            {'paletteId': 'pal-plum', 'label': '梅紫',
             'swatches': ['#7e22ce', '#faf5ff', '#2a1245', '#ffffff']},
        ],
        'iconSet': 'lucide-line',
        'l2Overrides': [
            {'selector': '.kx-btn', 'props': 'border-radius:var(--sp-radius-lg)'},
        ],
    },
    {
        'packId': 'pack-dianzi', 'familyId': 'fam-b',
        'identity': {'styleId': 'wiki:dianzi', 'styleName': '靛紫治理台', 'origin': 'ai-generated',
                     'mood': '治理后台的沉稳：适中圆角、分栏表格、靛紫主调'},
        'tokens': _tokens(
            primary='#6d28d9', radius_md='12px', space_2='12px', weight_head='650',
            shadow_md='0 4px 14px rgba(49,32,90,.12)',
            accent_bg='#f5f3ff', surface_alt='#ede9fe', text_primary='#1e1b3a',
            text_secondary='#6b6890', border_color='#e0dcf5',
            font_stack=SANS, font_head_stack=SANS,
            size_title='19px', size_head='15.5px', size_body='13px', size_caption='12px',
            radius_sm='8px', radius_lg='16px',
            space_1='8px', space_3='16px', space_4='22px',
            ctl_sm='28px', ctl_md='34px', ctl_lg='40px',
            shadow_sm='0 1px 2px rgba(109,40,217,.06)', border_width='1px',
            motion_duration='320ms', motion_easing='cubic-bezier(.4,.2,.2,1)',
            density='regular', hero_color='#4c1d95'),
        'palettes': [
            {'paletteId': 'pal-brand', 'label': '品牌靛紫',
             'swatches': ['#6d28d9', '#f5f3ff', '#1e1b3a', '#ffffff']},
            {'paletteId': 'pal-ember', 'label': '琥珀',
             'swatches': ['#b45309', '#fff8ee', '#3a2410', '#ffffff']},
        ],
        'iconSet': 'lucide-line',
        'l2Overrides': [
            {'selector': '.kx-input', 'props': 'background:var(--sp-surface-alt)'},
        ],
    },
    {
        'packId': 'pack-meihong', 'familyId': 'fam-b',
        'identity': {'styleId': 'wiki:meihong', 'styleName': '玫红醒目板', 'origin': 'ai-generated',
                     'mood': '活动大促的醒目：特圆胶囊、重字重、玫红主调'},
        'tokens': _tokens(
            primary='#db2777', radius_md='28px', space_2='14px', weight_head='800',
            shadow_md='0 10px 30px rgba(219,39,119,.16)',
            accent_bg='#fdf2f8', surface_alt='#fce7f3', text_primary='#3a0d24',
            text_secondary='#97697f', border_color='#f6d8e6',
            font_stack=SANS, font_head_stack=SERIF,
            size_title='22px', size_head='17px', size_body='14px', size_caption='12.5px',
            radius_sm='20px', radius_lg='36px',
            space_1='10px', space_3='18px', space_4='24px',
            ctl_sm='32px', ctl_md='38px', ctl_lg='46px',
            shadow_sm='0 1px 2px rgba(219,39,119,.08)', border_width='1px',
            motion_duration='260ms', motion_easing='cubic-bezier(.2,.8,.2,1)',
            density='compact', hero_color='#9d174d'),
        'palettes': [
            {'paletteId': 'pal-brand', 'label': '品牌玫红',
             'swatches': ['#db2777', '#fdf2f8', '#3a0d24', '#ffffff']},
            {'paletteId': 'pal-midnight', 'label': '深蓝夜',
             'swatches': ['#1d4ed8', '#eef4ff', '#101a33', '#ffffff']},
        ],
        'iconSet': 'lucide-line',
        'l2Overrides': [
            {'selector': '.kx-chip', 'props': 'border-radius:var(--sp-radius-lg);color:var(--muted)'},
        ],
    },
]


def style_registry():
    return {
        'schemaVersion': 1,
        'domBases': [
            {'domBaseId': 'db-a', 'note': '骨架甲：单列卡片流（移动端）', 'pages': ['orders', 'wallet']},
            {'domBaseId': 'db-b', 'note': '骨架乙：双栏治理台', 'pages': ['orders', 'wallet']},
        ],
        'families': [
            {'familyId': 'fam-a', 'domBaseId': 'db-a', 'label': '晨风接单族',
             'members': ['pack-chenlan', 'pack-bohe'], 'note': '同族两档：紧凑直角 / 舒展圆润'},
            {'familyId': 'fam-b', 'domBaseId': 'db-b', 'label': '暮色治理族',
             'members': ['pack-dianzi', 'pack-meihong'], 'note': '同族两档：适中分栏 / 特圆胶囊'},
        ],
    }


def component_pack():
    comps = [
        ('cp-stat-card', '统计卡',
         '<div class="card" data-eid="cp-stat-card"><div class="card-h"><span class="ct">今日接单</span></div>'
         '<div class="card-b"><b style="font-size:var(--sp-size-title);font-weight:var(--sp-weight-head)">128</b>'
         '<span style="color:var(--muted);font-size:var(--sp-size-caption)">较昨日 +12%</span></div></div>',
         ['primary', 'size-title', 'weight-head']),
        ('cp-btn-primary', '主按钮',
         '<span class="b pri" data-eid="cp-btn-primary">确认接单</span>', ['primary', 'radius-sm']),
        ('cp-btn-ghost', '次按钮',
         '<span class="b sec" data-eid="cp-btn-ghost">稍后处理</span>', ['radius-sm', 'border']),
        ('cp-list-row', '列表行',
         '<div class="li" data-eid="cp-list-row"><span class="av">单</span>'
         '<div class="lt"><b>订单 1024</b><small>1.2km · 预计 18 分钟</small></div>'
         '<span class="badge soft" style="color:var(--accent)">待接单</span></div>', ['primary', 'accent']),
        ('cp-form-field', '表单块',
         '<div class="form" data-eid="cp-form-field"><div class="fi"><div class="lb">备注</div>'
         '<div class="ipt" data-ph="选填">放前台即可</div></div></div>', ['radius-sm', 'surface-alt']),
        ('cp-card-base', '卡片容器',
         '<div class="card" data-eid="cp-card-base"><div class="card-h"><span class="ct">容器标题</span></div>'
         '<div class="card-b"><p>可拖入任意内容。</p></div></div>', ['radius-md', 'shadow-md']),
        ('cp-chip-tag', '标签胶囊',
         '<span class="tag" data-eid="cp-chip-tag">高峰时段</span>', ['radius-sm', 'soft']),
        ('cp-progress-row', '进度行',
         '<div class="li" data-eid="cp-progress-row" style="gap:var(--sp-space-2)">'
         '<span style="color:var(--muted);font-size:var(--sp-size-caption)">配送进度</span>'
         '<div class="segs" style="flex:1"><span class="sg on">接单</span><span class="sg on">取货</span>'
         '<span class="sg">送达</span></div></div>', ['space-2', 'accent']),
        ('cp-empty-state', '空状态',
         '<div class="card" data-eid="cp-empty-state"><div class="card-b" style="align-items:center;color:var(--muted)">'
         '<p>暂无新订单，去喝口水吧。</p></div></div>', ['muted', 'radius-md']),
        ('cp-search-bar', '搜索框',
         '<div class="ipt" data-eid="cp-search-bar" data-ph="搜订单号 / 地址">搜订单号 / 地址</div>',
         ['radius-sm', 'size-ctl-md']),
        ('cp-pager-bar', '分页条',
         '<div class="pager" data-eid="cp-pager-bar" style="display:flex;gap:var(--sp-space-2);justify-content:center">'
         '<span class="on">1</span><span>2</span><span>3</span></div>', ['space-2', 'accent']),
        ('cp-msg-bubble', '消息气泡',
         '<div class="note" data-eid="cp-msg-bubble" style="color:var(--text)">顾客备注：放前台即可，谢谢。</div>',
         ['soft', 'text-primary']),
    ]
    return {
        'schemaVersion': 1,
        'packFor': 'pack-chenlan',
        'components': [
            {'compId': cid, 'name': name, 'html': html, 'tokenRefs': refs}
            for cid, name, html, refs in comps
        ],
    }


def style_contract():
    return {
        'schemaVersion': 1,
        'domBaseId': 'db-a',
        'styleOrigin': {'styleId': 'wiki:chenlan', 'mood': '清晨发单的高效感'},
        'pages': [
            {'pageId': 'orders', 'form': '列表枢纽',
             'regions': [{'region': '顶栏', 'shape': 'bar', 'count': 1},
                         {'region': '订单卡片流', 'shape': 'card', 'count': 4}]},
            {'pageId': 'wallet', 'form': '资产枢纽',
             'regions': [{'region': '余额横幅', 'shape': 'banner', 'count': 1},
                         {'region': '明细列表', 'shape': 'list', 'count': 6}]},
        ],
        'motion': {'tier': 'b',
                   'tokens': {'duration': '220ms', 'easing': 'cubic-bezier(.3,.7,.4,1)'}},
        'density': 'compact',
    }


def style_blocks():
    return {
        'STYLE-REGISTRY': style_registry(),
        'STYLE-PACK': {'schemaVersion': 1, 'packs': PACKS},
        'COMPONENT-PACK': component_pack(),
        'STYLE-CONTRACT': style_contract(),
    }


def selection_result():
    """选型回传：单受众组选中 4 风格（跨 2 族），skeletonTokens 带齐正本表全部 minimum 键
    （E-LOCK-MINIMUM：最小集选型必带、选定即锁），值逐字取自对应风格包 tokens。"""
    by_pack = {p['packId']: p for p in PACKS}
    mins = minimum_keys()
    selected = []
    for pid in PACK_ORDER:
        p = by_pack[pid]
        selected.append({
            'styleId': p['identity']['styleId'],
            'styleName': p['identity']['styleName'],
            'skeletonTokens': {k: p['tokens'][k] for k in mins},
        })
    return {
        'schemaVersion': 1,
        'status': 'selected',
        'audienceGroups': [{'group': '商家工作台', 'selected': selected}],
    }


START_DOC = """# 接单钱包工作台 · 开工文档（1.0）

## 1. 业务定义
面向即时配送商家的接单与钱包管理移动端工作台。角色：商家店员（接单、改备注）、店长（看资产、提现）。
数据来源：订单中台与钱包服务的演示 mock 数据（真实感等级 B，可示意但禁 lorem ipsum）。

## 2. 站点地图与页面清单
| 页面 id | 页面名 | 片段路径 | 端型 | 完整度 |
|---|---|---|---|---|
| orders | 接单列表 | 工作台/接单列表.html | mobile | 核心 |
| wallet | 我的钱包 | 钱包/我的钱包.html | mobile | 核心 |

## 3. 核心流程
接单：接单列表 → 看单 → 立即接单（toast 反馈）。资产：去钱包 → 看余额 → 查明细。

## 4. 风格槽（1.0，已并入选中风格）
选中风格见 intake/selection-result.json：晨蓝紧凑台（族甲）、薄荷舒展卡（族甲·同族变体）、
靛紫治理台（族乙）、玫红醒目板（族乙·同族变体）。跨族多选：页面按族各放一套内容容器
（db-a 单列卡片流 / db-b 双栏治理台），产物内面板按族显隐。
动效档：b（220ms / cubic-bezier(.3,.7,.4,1) 基准，随包令牌）。

## 5. 真实感等级
B 档：订单、骑手、余额均为演示数据，但必须写业务上说得通的内容。

## 6. 交互声明
- orders：接单按钮 toast 反馈；顶栏「去钱包」goto wallet；备注表单 submit + loading。
- wallet：顶栏「回接单」goto orders；提现按钮 toast。

## 7. 质检方式
档②：主要页（orders、wallet 均为核心页）数据断言全量 + 截图走查。
"""

MANIFEST = {
    'project': PROJECT_TITLE,
    'workspace': '<ROOT>',
    'stations': {u: {'status': 'pending', 'evidence': ''} for u in
                 ('U1', 'U2', 'U3', 'U4', 'U5', 'U6')},
    'updatedAt': '2026-01-01T00:00:00+00:00',
}

# ---------------------------------------------------------------- 页面片段

PAGE_CSS = """
.kx-hero{background:var(--accent);color:var(--surface);border-radius:var(--sp-radius-lg);padding:var(--sp-space-4);margin-bottom:var(--sp-space-3)}
.kx-card{background:var(--surface);border:var(--sp-border-width,1px) solid var(--line);border-radius:var(--sp-radius-md);box-shadow:var(--sp-shadow-md);padding:var(--sp-space-3);display:flex;flex-direction:column;gap:var(--sp-space-2);color:var(--text)}
.kx-title{font-size:var(--sp-size-title);font-weight:var(--sp-weight-head);line-height:var(--sp-line-height-head);font-family:var(--sp-font-head);color:var(--text)}
.kx-sub{font-size:var(--sp-size-caption);color:var(--muted)}
.kx-body{font-size:var(--sp-size-body);line-height:var(--sp-line-height-body);font-weight:var(--sp-weight-body);color:var(--text)}
.kx-btn{min-height:var(--sp-size-ctl-lg);padding:0 var(--sp-space-3);border-radius:var(--sp-radius-md);background:var(--accent);color:var(--surface);font-weight:var(--sp-weight-head);display:flex;align-items:center;justify-content:center}
.kx-chip{height:var(--sp-size-ctl-sm);border-radius:var(--sp-radius-sm);background:var(--soft);color:var(--muted);display:flex;align-items:center;padding:0 var(--sp-space-2);font-size:var(--sp-size-caption)}
.kx-input{min-height:var(--sp-size-ctl-md);border:var(--sp-border-width,1px) solid var(--line);border-radius:var(--sp-radius-sm);background:var(--sp-surface-alt);color:var(--text);font-size:var(--sp-size-body);padding:0 var(--sp-space-2);display:flex;align-items:center}
.kx-row{display:flex;align-items:center;justify-content:space-between;gap:var(--sp-space-2);padding:var(--sp-space-2) 0;border-bottom:var(--sp-border-width,1px) solid var(--line)}
.kx-cols{display:flex;gap:var(--sp-space-3)}
.kx-col{flex:1;display:flex;flex-direction:column;gap:var(--sp-space-2);min-width:0}
.kx-ok{color:var(--ok)}.kx-danger{color:var(--danger)}
"""


def _orders_db_a():
    return (
        '<div class="app" data-dom-base="db-a" data-block="orders-main-a" data-eid="orders-root-a">'
        '<style>' + PAGE_CSS + '</style>'
        '<div class="appbar" data-block="appbar" data-eid="orders-appbar"><span class="t">接单列表</span>'
        '<span class="r" data-eid="orders-goto-wallet" data-on="{&quot;click&quot;:{&quot;goto&quot;:&quot;wallet&quot;}}">去钱包</span></div>'
        '<div class="kx-hero" data-block="hero" data-eid="orders-hero">'
        '<div class="kx-title" data-eid="orders-hero-title">今日待接 12 单</div>'
        '<div class="kx-sub" data-eid="orders-hero-sub">高峰时段 11:00–13:00，请保持在线</div></div>'
        '<div class="kx-card" data-block="card" data-eid="orders-card-1">'
        '<div class="kx-row"><span class="kx-body" data-eid="orders-o1-title">订单 #1024 · 三环内环线</span>'
        '<span class="kx-chip" data-eid="orders-o1-state">待接单</span></div>'
        '<div class="kx-sub" data-eid="orders-o1-note">1.2km · 预计 18 分钟送达 · 收货备注：放前台</div>'
        '<span class="kx-btn" data-eid="orders-o1-btn" data-on="{&quot;click&quot;:{&quot;toast&quot;:&quot;已接单：订单 #1024&quot;}}">立即接单</span></div>'
        '<div class="kx-card" data-block="card" data-eid="orders-card-2">'
        '<div class="kx-row"><span class="kx-body" data-eid="orders-o2-title">订单 #1025 · 望京西园</span>'
        '<span class="kx-chip" data-eid="orders-o2-state">待取货</span></div>'
        '<div class="kx-sub" data-eid="orders-o2-note">3.4km · 骑手小周已在店等待</div>'
        '<span class="kx-btn" data-eid="orders-o2-btn" data-on="{&quot;click&quot;:{&quot;toast&quot;:&quot;已通知骑手取货&quot;}}">催取货</span></div>'
        '<div class="kx-card" data-block="card" data-eid="orders-form-card">'
        '<div class="kx-sub" data-eid="orders-form-lb">备注给骑手</div>'
        '<div class="kx-input" data-eid="orders-form-ipt" data-ph="选填">放前台即可</div>'
        '<span class="kx-btn" data-eid="orders-form-btn" data-on="{&quot;click&quot;:{&quot;submit&quot;:{&quot;toast&quot;:&quot;备注已保存&quot;,&quot;loading&quot;:300}}}">保存备注</span></div>'
        '</div>'
    )


def _orders_db_b():
    return (
        '<div class="app" data-dom-base="db-b" data-block="orders-main-b" data-eid="orders-root-b">'
        '<style>' + PAGE_CSS + '</style>'
        '<div class="appbar" data-block="appbar" data-eid="orders-b-appbar"><span class="t">接单列表 · 治理台</span>'
        '<span class="r" data-eid="orders-b-goto-wallet" data-on="{&quot;click&quot;:{&quot;goto&quot;:&quot;wallet&quot;}}">去钱包</span></div>'
        '<div class="kx-cols" data-block="columns" data-eid="orders-b-cols">'
        '<div class="kx-col">'
        '<div class="kx-title" data-eid="orders-b-riders-title">运力面板</div>'
        '<div class="kx-card" data-eid="orders-b-rider-1"><div class="kx-row"><span class="kx-body">骑手小周 · 在店</span><span class="kx-ok">正常</span></div>'
        '<div class="kx-row"><span class="kx-body">骑手阿梅 · 配送中</span><span class="kx-chip">2 单在途</span></div></div>'
        '</div>'
        '<div class="kx-col">'
        '<div class="kx-title" data-eid="orders-b-abn-title">异常工单</div>'
        '<div class="kx-card" data-eid="orders-b-abn-1"><div class="kx-row"><span class="kx-body">订单 #0991 超时</span><span class="kx-danger">紧急</span></div>'
        '<div class="kx-row"><span class="kx-body">订单 #1002 地址变更</span><span class="kx-chip">待确认</span></div></div>'
        '</div></div></div>'
    )


def _wallet_db_a():
    return (
        '<div class="app" data-dom-base="db-a" data-block="wallet-main-a" data-eid="wallet-root-a">'
        '<style>' + PAGE_CSS + '</style>'
        '<div class="appbar" data-block="appbar" data-eid="wallet-appbar"><span class="t">我的钱包</span>'
        '<span class="r" data-eid="wallet-goto-orders" data-on="{&quot;click&quot;:{&quot;goto&quot;:&quot;orders&quot;}}">回接单</span></div>'
        '<div class="kx-hero" data-block="hero" data-eid="wallet-hero">'
        '<div class="kx-title" data-eid="wallet-hero-title">可提现 ¥2,048.50</div>'
        '<div class="kx-sub" data-eid="wallet-hero-sub">本周入账 ¥3,120 · 冻结 ¥96</div>'
        '<span class="kx-btn" data-eid="wallet-withdraw-btn" data-on="{&quot;click&quot;:{&quot;toast&quot;:&quot;提现申请已提交，1 个工作日内到账&quot;}}">申请提现</span></div>'
        '<div class="kx-card" data-block="card" data-eid="wallet-list-card">'
        '<div class="kx-title" data-eid="wallet-list-title">收支明细</div>'
        '<div class="kx-row"><span class="kx-body">订单 #1024 结算</span><span class="kx-ok">+12.50</span></div>'
        '<div class="kx-row"><span class="kx-body">订单 #1023 结算</span><span class="kx-ok">+9.80</span></div>'
        '<div class="kx-row"><span class="kx-body">平台服务费</span><span class="kx-danger">-3.20</span></div>'
        '<div class="kx-row"><span class="kx-body">提现 ¥500</span><span class="kx-sub">处理中</span></div>'
        '</div></div>'
    )


def _wallet_db_b():
    return (
        '<div class="app" data-dom-base="db-b" data-block="wallet-main-b" data-eid="wallet-root-b">'
        '<style>' + PAGE_CSS + '</style>'
        '<div class="appbar" data-block="appbar" data-eid="wallet-b-appbar"><span class="t">我的钱包 · 治理台</span>'
        '<span class="r" data-eid="wallet-b-goto-orders" data-on="{&quot;click&quot;:{&quot;goto&quot;:&quot;orders&quot;}}">回接单</span></div>'
        '<div class="kx-cols" data-block="columns" data-eid="wallet-b-cols">'
        '<div class="kx-col">'
        '<div class="kx-title" data-eid="wallet-b-balance-title">账户总览</div>'
        '<div class="kx-card" data-eid="wallet-b-balance-card">'
        '<div class="kx-row"><span class="kx-body">可提现</span><span class="kx-body">¥2,048.50</span></div>'
        '<div class="kx-row"><span class="kx-body">冻结中</span><span class="kx-chip">¥96.00</span></div></div>'
        '</div>'
        '<div class="kx-col">'
        '<div class="kx-title" data-eid="wallet-b-flow-title">流水监控</div>'
        '<div class="kx-card" data-eid="wallet-b-flow-card">'
        '<div class="kx-row"><span class="kx-body">今日入账</span><span class="kx-ok">¥3,120</span></div>'
        '<div class="kx-row"><span class="kx-body">今日支出</span><span class="kx-danger">¥3.20</span></div></div>'
        '</div></div></div>'
    )


def orders_fragment():
    return ('<section class="screen" data-screen="orders" data-name="接单列表">'
            '<div class="scr-head"><span class="scr-name">接单列表</span>'
            '<span class="scr-note">今日待处理的配送订单与状态流转</span></div>'
            '<div class="device mobile"><div class="notch"></div>'
            '<div class="statusbar"><span>9:41</span><span>5G</span></div>'
            '<div class="viewport">' + _orders_db_a() + _orders_db_b() +
            '</div></div></section>')


def wallet_fragment(note_override=None):
    note = note_override or '商家资产余额、收支明细与提现入口'
    return ('<section class="screen" data-screen="wallet" data-name="我的钱包">'
            '<div class="scr-head"><span class="scr-name">我的钱包</span>'
            '<span class="scr-note">' + note + '</span></div>'
            '<div class="device mobile"><div class="notch"></div>'
            '<div class="statusbar"><span>9:41</span><span>5G</span></div>'
            '<div class="viewport">' + _wallet_db_a() + _wallet_db_b() +
            '</div></div></section>')


def build_positive_project(root):
    """在 root 下写出正向工程目录；返回工程根路径（Path）。"""
    root = Path(os.path.abspath(str(root)))
    intake = os.path.join(root, 'intake')
    qa = os.path.join(root, 'qa')
    for d in (intake, qa,
              os.path.join(root, 'pages', '工作台'),
              os.path.join(root, 'pages', '钱包')):
        os.makedirs(d, exist_ok=True)

    def w(path, data):
        with open(path, 'w', encoding='utf-8', newline='\n') as f:
            if isinstance(data, str):
                f.write(data)
            else:
                json.dump(data, f, ensure_ascii=False, indent=2)
                f.write('\n')

    manifest = dict(MANIFEST)
    manifest['workspace'] = str(root)
    w(os.path.join(root, 'project.manifest.json'), manifest)
    w(os.path.join(intake, '开工文档.md'), START_DOC)
    w(os.path.join(intake, 'selection-result.json'), selection_result())
    w(os.path.join(intake, 'style-blocks.json'), style_blocks())
    w(os.path.join(root, 'pages', '工作台', '接单列表.html'), orders_fragment())
    w(os.path.join(root, 'pages', '钱包', '我的钱包.html'), wallet_fragment())
    return root
