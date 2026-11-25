"""
scripts/core/gen_components.py — 组件库章形态生成器（v4.0 · C 组）

架构地位：站④动作 1.5（gen_html 之后、agent 补全定案之前）。生成器产形态+枚举全量，
agent 只填占位推断值 / 不适用声明 / 校对实测数据。

用法（唯一）：python gen_components.py <项目out目录>

做什么：
  1. 解析 references/component-anatomy.md 字典（25 Web + 8 移动 = 33 类坑位）
  2. 读 work/normalized.json 的 components（实测，含来源标注）
  3. 逐字典类产出组卡：实测命中 → 完整卡（徽章=实测来源+实物行）；
     未命中 → 占位卡（虚线框 + "AI 补全待填"，字典典型变体/状态作提示）
  4. 坑位全量由代码保证（33 类必有一卡），agent 无从漏
  5. 直接改写 <out>/design-system.html 的 s11 组件全景重渲染区

实物渲染：首批 6 类模板（Button/Tag/Input/Card/Avatar/Tabs）用项目 CSS 变量渲染；
其余类出结构化规格卡（规格表形态）——agent 校对精调。渲染保形态，值精调归 agent。
"""
import io
import os
import re
import sys

from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
ANATOMY = ROOT / "references" / "component-anatomy.md"

# 首批实物渲染模板类
TEMPLATE_CLASSES = {"Button", "Tag", "Input", "Card", "Avatar", "Tabs"}

BADGE_EXTRACTED = ('<span style="margin-left:auto;font-size:10px;background:#2196F3;color:#fff;'
                   'border-radius:4px;padding:2px 8px;white-space:nowrap">{badge}</span>')
BADGE_AI = ('<span style="margin-left:auto;font-size:10px;background:#FB9C3C;color:#fff;'
            'border-radius:4px;padding:2px 8px;white-space:nowrap">AI 补全 · 待填</span>')
BADGE_NA = ('<span style="margin-left:auto;font-size:10px;background:var(--color-text-placeholder,#9CA3AF);color:#fff;'
            'border-radius:4px;padding:2px 8px;white-space:nowrap">声明不适用 · 待填原因</span>')


def parse_anatomy():
    """component-anatomy.md 两张 md 表 → [{cn, en, variants, states, specs, prohibition, mobile}]"""
    md = io.open(ANATOMY, encoding="utf-8").read()
    out = []
    segs = md.split("## 坑位字典")[1].split("## 坑位填充规则")[0]
    for seg, mobile in ((segs.split("### 移动端补充坑位")[0], False),
                        (segs.split("### 移动端补充坑位")[1], True)):
        for line in seg.split("\n"):
            line = line.strip()
            if not line.startswith("|") or set(line) <= {"|", "-", " "} or "组件" in line.split("|")[1]:
                continue
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) < 5:
                continue
            en_m = re.match(r"\*\*(\w+)[\s　]*([^*]*?)\*\*", cells[0])
            if not en_m:
                continue
            out.append({"en": en_m.group(1), "cn": en_m.group(2).strip() or en_m.group(1),
                        "variants": cells[1], "states": cells[2], "specs": cells[3],
                        "prohibition": cells[4], "mobile": mobile})
    return out


def card_shell(num, cn, en, badge_html, body, placeholder=False):
    border = "1px dashed var(--skin-line,#C9CED6)" if placeholder else "1px solid #E9ECF1"
    return ('<div style="border:%s;border-radius:16px;overflow:hidden;flex:1;min-width:460px;background:#fff">'
            '<div style="padding:12px 18px;background:#F6F7F9;border-bottom:1px solid #E9ECF1;'
            'display:flex;align-items:center;gap:8px"><b style="font-size:15px">%d. %s</b>'
            '<span style="font-size:11px;color:#979CA5">%s</span>%s</div>'
            '<div style="padding:16px 18px">%s</div></div>' % (border, num, cn, en, badge_html, body))


def spec_table(key_specs, fallback_specs=""):
    """key_specs（dict 或 str）→ 规格小表；空则用字典默认规格提示"""
    rows = []
    if isinstance(key_specs, dict) and key_specs:
        for k, v in key_specs.items():
            rows.append((k, str(v)))
    elif isinstance(key_specs, str) and key_specs.strip():
        rows.append(("规格", key_specs))
    if not rows:
        rows = [("待填", fallback_specs or "按本系统 token 推断")]
    lines = ["<table><thead><tr><th>项</th><th>规格</th></tr></thead><tbody>"]
    for k, v in rows:
        v = re.sub(r"<", "&lt;", v)
        lines.append("<tr><td><b>%s</b></td><td>%s</td></tr>" % (k, v))
    lines.append("</tbody></table>")
    return "".join(lines)


def render_demo(en, ks):
    """全 33 类实物渲染（项目 CSS 变量驱动，形态保真；值精调归 agent）"""
    P = "var(--color-action-primary, #2196F3)"
    INK = "var(--color-text-primary, #20252C)"
    SOFT = "var(--color-text-placeholder, #9CA3AF)"
    LINE = "var(--color-border, #E9ECF1)"
    DANGER = "var(--color-danger, #D44737)"
    OK = "var(--color-success, #4CAF50)"
    if en == "Button":
        return ('<span style="display:inline-flex;align-items:center;justify-content:center;padding:10px 22px;'
                'border-radius:999px;background:' + P + ';color:#fff;font-size:14px;font-weight:500">主按钮</span>'
                '<span style="display:inline-flex;align-items:center;padding:10px 22px;border-radius:999px;'
                'background:#fff;border:1px solid ' + LINE + ';color:' + INK + ';font-size:14px">次按钮</span>'
                '<span style="display:inline-flex;align-items:center;padding:10px 22px;border-radius:999px;'
                'color:' + P + ';font-size:14px">文字钮</span>')
    if en == "Tag":
        return ('<span style="padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;'
                'background:rgba(33,150,243,.12);color:' + P + '">品牌</span>'
                '<span style="padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;'
                'background:rgba(76,175,80,.12);color:' + OK + '">完成</span>'
                '<span style="padding:4px 12px;border-radius:999px;font-size:12px;font-weight:700;'
                'background:rgba(212,71,55,.12);color:' + DANGER + '">异常</span>')
    if en == "Input":
        return ('<span style="display:inline-flex;align-items:center;width:200px;height:40px;padding:0 12px;'
                'border-radius:8px;background:var(--color-bg-subtle,#F6F7F9);color:' + SOFT + ';'
                'font-size:13px">请输入内容</span>')
    if en == "Select":
        return ('<span style="display:inline-flex;align-items:center;justify-content:space-between;'
                'width:180px;height:40px;padding:0 12px;border-radius:8px;border:1px solid ' + LINE + ';'
                'font-size:13px;color:' + INK + '">已选项 <span style="color:' + SOFT + '">▾</span></span>')
    if en == "Checkbox":
        return ('<span style="width:20px;height:20px;border-radius:5px;background:' + P + ';color:#fff;'
                'display:inline-grid;place-items:center;font-size:13px;font-weight:700">✓</span>'
                '<span style="width:20px;height:20px;border-radius:5px;border:1.5px solid ' + LINE + ';'
                'display:inline-block"></span>')
    if en == "Radio":
        return ('<span style="width:20px;height:20px;border-radius:50%;border:5px solid ' + P + ';'
                'display:inline-block;background:#fff"></span>'
                '<span style="width:20px;height:20px;border-radius:50%;border:1.5px solid ' + LINE + ';'
                'display:inline-block"></span>')
    if en == "Switch":
        return ('<span style="width:44px;height:24px;border-radius:999px;background:' + P + ';'
                'display:inline-flex;align-items:center;justify-content:flex-end;padding:2px">'
                '<span style="width:20px;height:20px;border-radius:50%;background:#fff"></span></span>'
                '<span style="width:44px;height:24px;border-radius:999px;background:var(--color-border,'
                '#E9ECF1);display:inline-flex;align-items:center;padding:2px">'
                '<span style="width:20px;height:20px;border-radius:50%;background:#fff"></span></span>')
    if en == "Upload":
        return ('<span style="display:inline-grid;place-items:center;width:140px;height:80px;'
                'border:1.5px dashed ' + LINE + ';border-radius:8px;color:' + SOFT + ';font-size:12px">'
                '⬆ 上传</span>')
    if en == "Table":
        return ('<table style="border-collapse:collapse;font-size:11px"><tr>'
                '<th style="background:var(--color-bg-subtle,#F6F7F9);padding:4px 10px">列 A</th>'
                '<th style="background:var(--color-bg-subtle,#F6F7F9);padding:4px 10px">列 B</th></tr>'
                '<tr><td style="padding:4px 10px;border-bottom:1px solid ' + LINE + '">数据</td>'
                '<td style="padding:4px 10px;border-bottom:1px solid ' + LINE + '">数据</td></tr></table>')
    if en == "Card":
        return ('<div style="width:200px;border-radius:16px;background:#fff;'
                'box-shadow:var(--card-shadow,0 2px 8px rgba(0,0,0,.06));padding:12px">'
                '<div style="height:6px;width:60%;background:' + LINE + ';border-radius:3px"></div>'
                '<div style="height:6px;width:85%;background:var(--color-bg-subtle,#F6F7F9);'
                'border-radius:3px;margin-top:6px"></div></div>')
    if en == "List":
        return ('<span style="display:flex;align-items:center;gap:8px;width:220px;padding:10px 12px;'
                'border-bottom:1px solid ' + LINE + ';font-size:13px;color:' + INK + '">'
                '<span style="width:8px;height:8px;border-radius:2px;background:' + P + '"></span>'
                '列表行 <span style="margin-left:auto;color:' + SOFT + '">›</span></span>')
    if en == "Descriptions":
        return ('<span style="display:inline-block;font-size:12px">'
                '<span style="display:flex"><b style="width:56px;background:var(--color-bg-subtle,'
                '#F6F7F9);padding:3px 8px">字段</b><span style="padding:3px 8px;color:' + INK + '">值</span></span>'
                '<span style="display:flex"><b style="width:56px;background:var(--color-bg-subtle,'
                '#F6F7F9);padding:3px 8px">字段</b><span style="padding:3px 8px;color:' + INK + '">值</span></span></span>')
    if en == "Tabs":
        return ('<span style="display:inline-flex;gap:18px;font-size:14px">'
                '<b style="color:' + P + ';border-bottom:2px solid ' + P + ';padding-bottom:4px">选中</b>'
                '<span style="color:' + SOFT + '">未选</span></span>')
    if en == "Breadcrumb":
        return ('<span style="font-size:12px;color:' + SOFT + '">首页 / 列表 / '
                '<b style="color:' + INK + '">当前页</b></span>')
    if en == "Badge":
        return ('<span style="position:relative;display:inline-block;width:28px;height:28px;'
                'border-radius:8px;background:var(--color-bg-subtle,#F6F7F9)">'
                '<span style="position:absolute;top:-6px;right:-6px;min-width:18px;height:18px;'
                'border-radius:999px;background:' + DANGER + ';color:#fff;font-size:10px;'
                'text-align:center;line-height:18px;padding:0 4px">6</span></span>')
    if en == "Avatar":
        return ('<span style="width:44px;height:44px;border-radius:50%;display:inline-block;'
                'background:' + P + ';color:#fff;text-align:center;line-height:44px;font-size:14px">像</span>')
    if en == "Modal":
        return ('<div style="width:220px;border-radius:16px;background:#fff;box-shadow:0 10px 30px '
                'rgba(0,0,0,.18);padding:14px;text-align:center">'
                '<b style="font-size:13px;color:' + INK + '">确认操作？</b>'
                '<div style="display:flex;gap:10px;justify-content:center;margin-top:10px">'
                '<span style="padding:5px 16px;border-radius:999px;border:1px solid ' + LINE + ';'
                'font-size:12px">取消</span><span style="padding:5px 16px;border-radius:999px;'
                'background:' + P + ';color:#fff;font-size:12px">确认</span></div></div>')
    if en == "Drawer":
        return ('<div style="width:120px;height:90px;border-radius:12px 0 0 12px;background:#fff;'
                'box-shadow:-6px 0 20px rgba(0,0,0,.15);padding:10px;font-size:11px;color:' + INK + '">'
                '抽屉面板<br>菜单项…</div>')
    if en == "Toast":
        return ('<span style="display:inline-block;padding:8px 18px;border-radius:12px;'
                'background:rgba(32,37,44,.9);color:#fff;font-size:12px">已复制到剪贴板</span>')
    if en == "Alert":
        return ('<span style="display:inline-block;padding:8px 14px;border-radius:8px;font-size:12px;'
                'background:rgba(76,175,80,.12);color:' + OK + '">提示条内容</span>')
    if en == "Empty":
        return ('<span style="display:inline-grid;place-items:center;gap:6px;font-size:11px;color:' + SOFT + '">'
                '<span style="width:36px;height:36px;border-radius:8px;background:var(--color-bg-subtle,'
                '#F6F7F9);display:grid;place-items:center">▢</span>暂无内容'
                '<span style="padding:4px 14px;border-radius:999px;border:1px solid ' + LINE + ';'
                'color:' + P + '">去逛逛</span></span>')
    if en == "Loading":
        return ('<span style="display:inline-flex;gap:10px;align-items:center">'
                '<span style="width:22px;height:22px;border-radius:50%;border:3px solid ' + LINE + ';'
                'border-top-color:' + P + ';display:inline-block"></span>'
                '<span style="display:inline-block;width:80px;height:8px;border-radius:4px;'
                'background:linear-gradient(90deg,' + LINE + ' 50%,var(--color-bg-subtle,#F6F7F9) 50%)"></span></span>')
    if en == "Progress":
        return ('<span style="display:inline-block;width:160px;height:8px;border-radius:999px;'
                'background:var(--color-bg-subtle,#F6F7F9);overflow:hidden">'
                '<span style="display:block;width:62%;height:100%;border-radius:999px;background:' + P + '"></span></span>')
    if en == "Pagination":
        return ('<span style="display:inline-flex;gap:6px;font-size:12px">'
                '<span style="width:26px;height:26px;border-radius:6px;background:' + P + ';color:#fff;'
                'display:grid;place-items:center">1</span>'
                '<span style="width:26px;height:26px;border-radius:6px;border:1px solid ' + LINE + ';'
                'display:grid;place-items:center;color:' + INK + '">2</span>'
                '<span style="width:26px;height:26px;border-radius:6px;border:1px solid ' + LINE + ';'
                'display:grid;place-items:center;color:' + INK + '">3</span></span>')
    if en == "Menu":
        return ('<span style="display:inline-block;width:120px;font-size:12px;color:' + INK + '">'
                '<span style="display:block;padding:6px 10px;background:rgba(33,150,243,.08);'
                'color:' + P + ';font-weight:700;border-radius:6px">菜单项一</span>'
                '<span style="display:block;padding:6px 10px">菜单项二</span></span>')
    if en == "StatusBar":
        return ('<span style="display:inline-flex;justify-content:space-between;width:180px;'
                'font-size:12px;font-weight:600;color:' + INK + '"><b>9:41</b>'
                '<span>▮▮▮ ⌁ 87%</span></span>')
    if en == "NavBar":
        return ('<span style="display:inline-flex;align-items:center;gap:10px;width:220px;font-size:14px;'
                'color:' + INK + '"><b style="color:' + SOFT + '">‹</b>'
                '<b style="margin:0 auto">页面标题</b><span style="width:14px"></span></span>')
    if en == "TabBar":
        return ('<span style="display:inline-flex;gap:20px;font-size:10px;text-align:center;color:' + SOFT + '">'
                '<span style="display:grid;gap:2px;justify-items:center"><span style="width:18px;height:18px;'
                'background:' + SOFT + ';border-radius:5px"></span>首页</span>'
                '<span style="display:grid;gap:2px;justify-items:center;color:' + P + ';font-weight:700">'
                '<span style="width:18px;height:18px;background:' + P + ';border-radius:5px"></span>订单</span></span>')
    if en == "SearchBar":
        return ('<span style="display:inline-flex;align-items:center;gap:6px;width:200px;height:36px;'
                'padding:0 12px;border-radius:999px;background:var(--color-bg-subtle,#F6F7F9);'
                'color:' + SOFT + ';font-size:13px">⌕ 搜索订单 / 服务</span>')
    if en == "Segmented":
        return ('<span style="display:inline-flex;border-radius:999px;background:var(--color-bg-subtle,'
                '#F6F7F9);padding:3px;font-size:12px">'
                '<span style="padding:5px 16px;border-radius:999px;background:' + P + ';color:#fff;'
                'font-weight:700">全部</span><span style="padding:5px 16px;color:' + SOFT + '">进行中</span></span>')
    if en == "Stepper":
        return ('<span style="display:inline-flex;align-items:center;border:1px solid ' + LINE + ';'
                'border-radius:8px;font-size:13px;color:' + INK + '">'
                '<span style="padding:5px 12px;color:' + SOFT + '">−</span>'
                '<span style="padding:5px 14px;border-left:1px solid ' + LINE + ';'
                'border-right:1px solid ' + LINE + '">1</span>'
                '<span style="padding:5px 12px">+</span></span>')
    if en == "FAB":
        return ('<span style="width:52px;height:52px;border-radius:50%;background:' + P + ';color:#fff;'
                'display:inline-grid;place-items:center;font-size:24px;box-shadow:0 6px 16px '
                'rgba(33,150,243,.35)">＋</span>')
    if en == "Banner":
        return ('<span style="display:inline-block;width:240px;height:64px;border-radius:16px;'
                'background:linear-gradient(90deg,var(--color-action-primary,#2196F3),#61AFEF);'
                'color:#fff;font-size:12px;font-weight:700;display:inline-grid;place-items:center">'
                '运营横幅位</span>')
    return None


def render_variant_rows(en, comp):
    """实测组件 → 变体实物行（st-cell-root 结构，复用产物现有复制 JS）"""
    variants = comp.get("variants") or []
    states = comp.get("states") or ["default"]
    if isinstance(states, str):
        states = [s.strip() for s in states.replace("·", ",").split(",") if s.strip()]
    demo = render_demo(en, comp.get("key_specs"))
    rows = []
    for vi, v in enumerate(variants[:4]):
        v = str(v)
        cells = []
        for st in states[:4]:
            st = str(st).strip() or "default"
            inner = demo or (f'<span style="font-size:12px;color:var(--ink-soft,#626A76)">实物待填（{v}）</span>')
            if st in ("pressed", "按下"):
                inner = (f'<span style="display:inline-block;transform:scale(.96);'
                         f'filter:brightness(.96)">{inner}</span>')
            cells.append(
                '<div class="st-cell-root" style="text-align:center;flex:1 1 0;min-width:max-content;max-width:100%">'
                '<div class="css-src" style="display:flex;align-items:center;justify-content:center;'
                'min-height:56px">' + inner + '</div>'
                '<div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:6px">'
                f'<span style="font-size:10px;color:#626A76;border:1px solid #E9ECF1;border-radius:4px;'
                f'padding:1px 6px">{st}</span>'
                '<button class="css-copy" title="复制该实物根元素的 CSS" style="font-size:10px;'
                'border:1px solid #E9ECF1;background:#fff;color:#626A76;border-radius:4px;'
                'padding:2px 8px;cursor:pointer;white-space:nowrap">⧉ 复制 CSS</button></div></div>')
        rows.append('<div style="margin-bottom:14px"><b style="font-size:13px">%s</b>'
                    '<div style="display:flex;gap:14px;flex-wrap:wrap;align-items:flex-end;margin-top:8px">%s</div></div>'
                    % (txt_short(v), "".join(cells)))
    if not rows:
        rows.append('<div style="font-size:12px;color:#979CA5">变体待填（字典参考：%s）</div>'
                    % txt_short(comp.get("_dict_variants", "")))
    return "".join(rows)


def txt_short(s, n=60):
    s = re.sub(r"<[^>]+>", "", str(s))
    return s[:n] + ("…" if len(s) > n else "")


def gen_components_html(html, normalized):
    anatomy = parse_anatomy()
    comps = normalized.get("components", []) or []
    by_en = {}
    for c in comps:
        key = (c.get("name") or "").split()[0].rstrip("（")
        by_en[key.lower()] = c
    used = set()
    cards = []
    num = 0
    # 先按字典序出卡（实测命中填数据，未命中出占位）
    for d in anatomy:
        en = d["en"]
        comp = by_en.get(en.lower())
        if comp:
            used.add(en.lower())
            num += 1
            src = ((comp.get("key_specs") or {}).get("来源标注", "") if isinstance(comp.get("key_specs"), dict) else "")
            badge = BADGE_EXTRACTED.format(badge=txt_short(src, 40) or "已提取")
            comp = dict(comp)
            comp["_dict_variants"] = d["variants"]
            body = (render_variant_rows(en, comp) +
                    '<div style="margin-top:8px">%s</div>' % spec_table(comp.get("key_specs"), d["specs"]))
            if d["prohibition"] and d["prohibition"] != "—":
                body += ('<p style="font-size:12px;color:var(--color-danger,#B91C1C);margin:8px 0 0">禁令：%s</p>' % d["prohibition"])
            cards.append(card_shell(num, d["cn"], en, badge, body))
        else:
            num += 1
            body = ('<p style="font-size:12px;color:#979CA5;margin:0 0 8px">源材料未出现此组件——'
                    '按本系统 token 推断补全，或声明不适用（写明原因）。字典参考：变体 %s；状态 %s。</p>'
                    % (d["variants"], d["states"]))
            body += spec_table(None, d["specs"])
            cards.append(card_shell(num, d["cn"], en, BADGE_AI, body, placeholder=True))
    # 实测但字典外（复合/自定义组件）追加
    for key, comp in by_en.items():
        if key in used:
            continue
        num += 1
        src = ((comp.get("key_specs") or {}).get("来源标注", "") if isinstance(comp.get("key_specs"), dict) else "")
        badge = BADGE_EXTRACTED.format(badge=txt_short(src, 40) or "已提取")
        comp = dict(comp)
        comp["_dict_variants"] = ""
        cards.append(card_shell(num, comp.get("name", key), key, badge,
                                render_variant_rows(key, comp) + spec_table(comp.get("key_specs"))))
    inner = ('<div style="display:flex;flex-wrap:wrap;gap:18px;align-items:stretch">'
             + "".join(cards) + "</div>"
             + '<p class="note" style="margin-top:10px">组卡由 gen_components 按 33 类坑位字典自动枚举：'
               '实测组带数据，占位组由 agent 填推断值或声明不适用——禁空白坑位。</p>')
    block = ('<div class="block"><div class="spec-label">APPLICATION · 组件全景（%d 组 · 字典枚举）</div>%s</div>'
             % (num, inner))
    return block


def main():
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("用法: python gen_components.py <项目out目录> [--force]", file=sys.stderr)
        return 2
    out_dir = sys.argv[1]
    html_path = os.path.join(out_dir, "design-system.html")
    norm_path = os.path.join(out_dir, "work", "normalized.json")
    if not os.path.exists(norm_path):
        norm_path = os.path.join(out_dir, "normalized.json")
    if not os.path.exists(html_path) or not os.path.exists(norm_path):
        print("[FAIL] 缺 %s 或 %s" % (html_path, norm_path), file=sys.stderr)
        return 2
    import json
    normalized = json.load(io.open(norm_path, encoding="utf-8"))
    html = io.open(html_path, encoding="utf-8").read()

    # 手工形态保护：定案 HTML 已含精细手工组卡（非生成器产出）时默认跳过——
    # 生成器模板形态是初稿/占位级，覆盖手工精修 = 破坏（2026-10-20 真案例事故）。--force 才覆盖
    if "gen_components" not in html and "--force" not in sys.argv:
        m_probe = re.search(r'组件全景（\d+ 组）', html)
        if m_probe and re.search(r'已提取 · \d+ 页|状态横排|结构复刻见', html):
            print("[skip] 检测到手工精修组件章（生成器产出会降级覆盖）；确认需要重建请加 --force")
            return 0
    new_block = gen_components_html(html, normalized)
    # 重渲染区：s11 的「组件全景」block → s11 的 USAGE block 之前
    m = re.search(r'<section class="chapter" id="s11">(.*?)</section>', html, re.S)
    if not m:
        print("[FAIL] HTML 无 s11 组件库章", file=sys.stderr)
        return 2
    s11 = m.group(1)
    i = s11.find('组件全景')
    if i < 0:
        print("[skip] s11 无「组件全景」区（形态不同构），未改动")
        return 0
    blk_start = s11.rfind('<div class="block">', 0, i)
    u = s11.find('<div class="block"><div class="spec-label">USAGE', i)
    if blk_start < 0 or u < 0:
        print("[skip] 组件全景区边界定位失败，未改动", file=sys.stderr)
        return 0
    s11_new = s11[:blk_start] + new_block + "\n" + s11[u:]
    html = html[:m.start(1)] + s11_new + html[m.end(1):]
    io.open(html_path, "w", encoding="utf-8", newline="\n").write(html)
    n_cards = new_block.count('border-radius:16px;overflow:hidden')
    print("[ok] 组件全景重渲染：%d 张组卡（含字典占位）" % n_cards)
    return 0


if __name__ == "__main__":
    sys.exit(main())
