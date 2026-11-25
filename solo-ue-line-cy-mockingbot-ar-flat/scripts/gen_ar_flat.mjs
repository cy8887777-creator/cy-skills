// gen_ar_flat.mjs — 嵌套节点 + 术语表 → 阿拉伯语「矩阵式平铺版」HTML（无交互、评审可读）
//
// 管线（PM 2026-09-01 定序，已验证）：
//   载入嵌套节点 → ① 前置整删交互层（橙块/蓝闪，零误伤降级） → ② 术语表优先翻译
//   → ③ 嵌套递归 RTL 镜像 → ④ 阿语字体 + bidi 隔离 + 行盒防裁切 → ⑤ 矩阵平铺输出
//
// 用法：
//   node gen_ar_flat.mjs [--src en_nodes.json] [--terms 术语表.md|术语表.json]
//                        [--extra 额外覆盖.json] [--out ar_flat.html] [--title "标题"]
//
//   • --terms：PM 提供的术语对照表。支持两种格式：
//       - Markdown 三栏 `| 中文 | 英文 | 阿拉伯语 |` → 自动解析（EN 键小写化、"/" 切多值；CN 键直用）
//       - JSON `{ "English": "Arabic", ... }` 或 `{ "中文": "阿语" }` → 直接载入
//     术语表优先级最高（高于 --extra 与任何自动翻译）。
//   • --extra：项目/页面级补充覆盖（JSON `{ "原文": "阿语" }`），仅在术语表未覆盖时兜底。
//
// 专有名词（XP / EXP / GVG / PVP / LV / VIP / Ludo 等）**不翻译**，原样保留（G6）。
import fs from 'fs';
import { fileURLToPath } from 'node:url';

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith('--')) {
    const k = a.slice(2);
    const v = process.argv[i + 1];
    if (v === undefined || v.startsWith('--')) A[k] = true;
    else { A[k] = v; i++; }
  }
}
const SRC = A.src || 'en_nodes.json';
// 术语表默认指向技能内置 Jam3a 术语表（若存在）；--terms 可覆盖。PM 2026-09-02 整理进技能。
const TERMS_DEFAULT = fileURLToPath(new URL('../references/术语表.md', import.meta.url));
const TERMS = A.terms || (fs.existsSync(TERMS_DEFAULT) ? TERMS_DEFAULT : '');
const EXTRA = A.extra || '';
const OUT = A.out || 'ar_flat.html';
const TITLE = A.title || '墨刀原型 · 阿拉伯语平铺版';
// 暗色模式（G7）：--theme dark|light（默认 dark，阿语版默认暗色；--theme light 可选切亮色）；--palette 自定义配色（默认技能内置 Jam3a 暗色规范）
const THEME = String(A.theme || 'dark').toLowerCase();
const PAL_PATH = (typeof A.palette === 'string') ? A.palette
  : fileURLToPath(new URL('../references/dark-palette.json', import.meta.url));

// ===== 暗色模式（G7）· 色值映射 =====
// 规则来源：PM 2026-09-02 暗色规范截图（按钮/输入框组件色优先） + 《Jam3a_页面风格规范.md》§3 暗色模式 + §13.1 Token
// ① 组件级语义映射（2026-09-02 新增）：按钮/输入框等被识别为语义角色后，bg/clr/bc 优先走组件表，覆盖通用表
// ② 分属性上下文映射：同一亮色作背景/文字/边框时映射不同暗色（见 palette _meta.role_note）
// ③ 半透明色（rgba 带 alpha）不映射，保持原样（叠加层改色会破坏效果）
// ④ 未命中保持原色并进「未匹配清单」，供 PM 人工复核补表
// ⑤ 预览画布（body/外壳）恒定中性灰不随主题变，仅屏内 .stage/.screen 承载主题色
let PAL = null, PAL_ERR = '';
if (THEME === 'dark') {
  try {
    const raw = JSON.parse(fs.readFileSync(PAL_PATH, 'utf8'));
    const toMap = o => { const m = new Map(); for (const [k, v] of Object.entries(o || {})) { if (String(k).startsWith('_')) continue; const ck = colorKey(k); if (ck) m.set(ck, String(v)); } return m; };
    // G7-组件级语义色（2026-09-02）：按钮/输入框等按角色优先映射，覆盖通用 bg/clr/bc 表
    const compRoles = new Map();
    for (const [role, defs] of Object.entries(raw.components || {})) {
      if (String(role).startsWith('_')) continue;
      compRoles.set(role, { bg: toMap(defs.bg), clr: toMap(defs.clr), bc: toMap(defs.bc) });
    }
    PAL = {
      screen: (raw.page && raw.page.screen) || '#121212',
      bg: toMap(raw.bg), clr: toMap(raw.clr), bc: toMap(raw.bc),
      keep: new Set(((raw.keep && raw.keep.colors) || []).map(colorKey).filter(Boolean)),
      comp: compRoles
    };
  } catch (e) { PAL = null; PAL_ERR = e.message; }
}
// 色值归一化：hex(#abc/#aabbcc) / rgb() / rgba() → 'r,g,b'；无法解析返回 null
function colorKey(c) {
  const s = String(c == null ? '' : c).trim();
  let m = s.match(/^#([0-9a-f]{3})$/i);
  if (m) return [parseInt(m[1][0] + m[1][0], 16), parseInt(m[1][1] + m[1][1], 16), parseInt(m[1][2] + m[1][2], 16)].join(',');
  m = s.match(/^#([0-9a-f]{6})$/i);
  if (m) return [parseInt(m[1].slice(0, 2), 16), parseInt(m[1].slice(2, 4), 16), parseInt(m[1].slice(4, 6), 16)].join(',');
  m = s.match(/^rgba?\(\s*(\d+)[,\s]+(\d+)[,\s]+(\d+)/i);
  if (m) return [+m[1], +m[2], +m[3]].join(',');
  return null;
}
const HAS_ALPHA = c => /rgba\(/i.test(String(c));
const darkUnmatched = new Set();   // 未命中配色的色值，输出供人工复核
function darken(c, role, pal, compRole = null) {    // role: 'bg' | 'clr' | 'bc'；compRole: 组件角色（如 'button-primary'）
  if (!pal || c == null) return c;
  const s = String(c);
  if (HAS_ALPHA(s)) return c;                       // 半透明：不映射
  const ck = colorKey(s);
  if (!ck) return c;                                // 渐变/图片等：不映射
  if (pal.keep.has(ck)) return c;                   // 品牌/语义色：保持
  // G7-组件级语义色优先（2026-09-02）：按钮/输入框等被识别后优先走组件表
  if (compRole && pal.comp && pal.comp.has(compRole)) {
    const m = pal.comp.get(compRole)[role];
    if (m && m.has(ck)) return m.get(ck);
  }
  const map = pal[role];
  if (map && map.has(ck)) return map.get(ck);
  // G7-补（2026-09-02）：未知字面量按亮度启发式转暗色，避免亮色块在暗底刺眼/不可见
  // （原行为：保持原色+进未匹配清单 → 导致图标暗不可见、矩形框亮色孤岛）
  const [r,g,b] = ck.split(',').map(Number);
  const lum = 0.2126 * r + 0.7152 * g + 0.0722 * b;   // 相对亮度 Rec.601
  if (lum > 180) {  // 近白/浅色 → 暗面或暗底上的可见文字/描边
    darkUnmatched.add(ck);  // 仍记录供 PM 复核，但不再保持原亮色
    return role === 'clr' ? '#e8eaed' : role === 'bc' ? '#3a3a3a' : '#1e1e1e';
  }
  if (lum < 50) {   // 近黑 → 提亮为暗底上的可见文字/描边
    darkUnmatched.add(ck);
    return role === 'clr' ? '#c8c8c8' : role === 'bc' ? '#4a4a4a' : '#252525';
  }
  // 中间灰（lum 50-180）：已接近暗色系可接受范围，保持原色但记录
  darkUnmatched.add(ck);
  return c;
}
// 弹窗类页面不做暗色，保留原主题（PM 2026-09-02 规则：页面命名含「弹窗」或「Popup」）
const POPUP_RE = /弹窗|popup/i;
const isPopupPage = name => POPUP_RE.test(String(name || ''));

// G7-组件级语义色：按节点几何/结构/颜色启发式识别按钮、输入框等角色（2026-09-02）
function detectRole(idx, nodes, kids) {
  const n = nodes[idx]; const st = n.st || {};
  const children = kids.get(idx) || [];
  // 跳过交互热区/透明层/纯文本组件自身
  if (st.bg && /rgba\(255,\s*140,\s*25/i.test(st.bg)) return null;
  if (n.cls && /InteractionMark/i.test(n.cls)) return null;
  if (/wWrap|wRichText/.test(n.cls || '')) return null;

  // 收集后代：文本、图片、SVG
  const desc = []; const walk = i => { desc.push(nodes[i]); for (const c of (kids.get(i) || [])) walk(c); };
  for (const c of children) walk(c);
  const descHasText = desc.some(d => d.text);
  const hasImg = desc.some(d => d.img);
  const hasSvg = desc.some(d => d.svg);

  // G7-补：墨刀常见布局把按钮文字作为同级兄弟节点放在按钮矩形上方，需用几何包含关系补识别
  const siblings = (n.parent != null && kids.get(n.parent) || []).filter(i => i !== idx).map(i => nodes[i]);
  const containedText = siblings.find(s => {
    const sw = s.st && s.st.w ? +s.st.w : s.w;
    // 候选文字节点通常是 wRichText/text 且中心点在按钮矩形内
    if (!/wRichText|text/.test(s.cls || '')) return false;
    const scx = s.x + s.w / 2, scy = s.y + s.h / 2;
    return scx >= n.x && scx <= n.x + n.w && scy >= n.y && scy <= n.y + n.h && s.w <= n.w && s.h <= n.h;
  });
  const siblingTextNode = containedText;
  const hasText = descHasText || !!siblingTextNode;
  const firstTextColor = () => {
    const t = desc.find(d => d.text && d.st && d.st.clr) || siblingTextNode;
    return t ? colorKey(t.st.clr) : null;
  };

  const w = n.w, h = n.h;
  const br = parseFloat(st.br) || 0;
  const bgKey = st.bg ? colorKey(st.bg) : null;
  const hasBorder = st.bw && parseFloat(st.bw) > 0;

  const inSet = list => { if (!bgKey) return false; const s = new Set((list || []).map(colorKey).filter(Boolean)); return s.has(bgKey); };

  // 按钮：矩形、圆角、横向、仅含文本（不含图片/SVG）。支持文字在内部或作为同级兄弟
  const isButton = (n.cls && /wRect|wLr/.test(n.cls)) && br > 0 && w >= 80 && h >= 28 && h <= 90 && w / h >= 1.2 && hasText && !hasImg && !hasSvg;
  if (isButton) {
    // 危险按钮：红色系背景
    if (inSet(['#E64040','#FF5252','#D03030','#F46160','#EF5350','#E53935','#FF6B6B'])) return 'button-danger';
    // 主按钮禁用态：有边框 + 浅灰/白底
    if (hasBorder && inSet(['#F0F0F0','#FFFFFF','#FAFAFA','#F2F2F2','#E8E8E8','#DDDDDD','#EDEDED','#EFEFEF'])) return 'button-primary-disabled';
    // 禁用按钮：浅灰/白底 + 文字灰
    if (inSet(['#F0F0F0','#FFFFFF','#FAFAFA','#F2F2F2','#E8E8E8','#DDDDDD','#EEEEEE','#EDEDED','#EFEFEF'])) {
      const tk = firstTextColor();
      const grayText = new Set(['#999999','#A0A0A0','#808080','#666666','#BABABA','#BDC1C6','#DADCE0'].map(colorKey).filter(Boolean));
      if (tk && grayText.has(tk)) return 'button-disabled';
    }
    return 'button-primary';
  }

  // 输入框：有边框、横向矩形、仅含文本、高度适中
  if (hasBorder && w >= 180 && h >= 36 && h <= 90 && hasText && !hasImg && !hasSvg) {
    // 避免把带边框的按钮/标签误判：输入框通常较高或背景为浅/白色
    if (h >= 44 || inSet(['#FFFFFF','#FAFAFA','#F7F7F7','#F5F5F5','#F0F0F0','#F2F2F2','#E8E8E8'])) return 'input';
  }

  return null;
}

const data = JSON.parse(fs.readFileSync(SRC, 'utf8'));
const pages = Array.isArray(data.pages) ? data.pages : (Array.isArray(data) ? data : [data]);
const PKG_BASE = (data.meta && data.meta.pkgBase) || (pages[0] && pages[0].pkgBase) || '';

// ===== ① 前置整删：交互指示层 =====
const HOT_ORANGE = /rgba\(255,\s*140,\s*25,\s*0\.[0-9]+/i;   // 墨刀半透明橙热区签名
const HOT_BLUE_CLS = /InteractionMark|InteractionMarker|StyledInteraction/i;
const HOT_BLUE_SVG = /fill="#298DF8"/i;
function isHot(n) {
  const st = n.st || {};
  if (n.svg && HOT_BLUE_SVG.test(n.svg)) return 'blue-svg';
  if (n.cls && HOT_BLUE_CLS.test(n.cls)) return 'blue-cls';
  if (st.bg && HOT_ORANGE.test(st.bg) && !n.text) return 'orange';
  return null;
}
function hasContent(nodes, idx, kids) {
  const n = nodes[idx];
  if (n.text || n.img) return true;
  if (n.svg && !HOT_BLUE_SVG.test(n.svg)) return true;
  return (kids.get(idx) || []).some(c => hasContent(nodes, c, kids));
}

// ===== ② 术语表优先翻译 =====
const TERM_EN = Object.create(null), TERM_CN = Object.create(null);
if (TERMS) {
  let raw = fs.readFileSync(TERMS, 'utf8');
  if (/\.json$/i.test(TERMS)) {
    const j = JSON.parse(raw);
    for (const [k, v] of Object.entries(j)) {
      if (/[一-龥]/.test(k)) TERM_CN[k.trim()] = v;
      else TERM_EN[k.trim().toLowerCase()] = v;
    }
  } else {
    let n = 0;
    for (const line of raw.split(/\r?\n/)) {
      const m = line.match(/^\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|$/);
      if (!m) continue;
      const cn = m[1].trim(), en = m[2].trim(), ar = m[3].trim();
      if (cn === '中文' || cn.startsWith(':---') || ar === '阿拉伯语' || !ar) continue;
      TERM_CN[cn] = ar;
      for (const part of en.split('/')) { const k = part.trim().toLowerCase(); if (k) TERM_EN[k] = ar; }
      n++;
    }
    console.log(`术语表载入：${n} 条（EN 键 ${Object.keys(TERM_EN).length} · CN 键 ${Object.keys(TERM_CN).length}）`);
  }
}
const EXTRA_TR = EXTRA ? JSON.parse(fs.readFileSync(EXTRA, 'utf8')) : {};

// 不翻译：数字/符号/时间 + 专有名词缩写（XP/EXP/GVG/PVP/LV/VIP/Ludo 等）原样保留（G6）
const KEEP_RE = /^[\d\s.,:%/×+\-—–]+$/;
const PROPER_RE = /^(Ludo|LV\.|Lv\.|EXP|XP|GVG|PVP|VIP)\b/i;
const AR_RE = /[\u0600-\u06FF\u0750-\u077F\uFB50-\uFDFF\uFE70-\uFEFF]/;

// G5 译文长度系数校准（2026-09-02）：按字符类分别估算字宽，替代单一 0.55 经验值
// 阿语字母平均字宽 ≈ 0.52em（连写使实际更窄）；拉丁/数字/符号 ≈ 0.50em；空格 ≈ 0.28em
const W_AR = 0.52, W_LAT = 0.50, W_SPC = 0.28;
function estTextWidth(t, fs) {
  let u = 0;
  for (const ch of String(t)) {
    if (ch === ' ' || ch === '　' || ch === '\t') u += W_SPC;
    else if (AR_RE.test(ch)) u += W_AR;
    else if (/[A-Za-z0-9.,:;'"\-/\\()]/.test(ch)) u += W_LAT;
    else u += 0.5;                 // 其他符号兜底
  }
  return u * fs;
}

const trStat = { term: 0, extra: 0, keep: 0, miss: 0 };
const missList = [], keepList = [];
// G7-补（2026-09-02）：翻译键归一化——去除零宽字符/不换行连字符等不可见 Unicode，
// 避免原型工具注入的隐形格式符导致精确匹配失败（如 Matches\u200bdo\u200bnot 匹配不到 Matches do not）
function normKey(s) {
  return String(s).replace(/[\u200B-\u200F\uFEFF\u2060-\u2064\u202A-\u202E]/g, '')
    .replace(/[\u2010-\u2015]/g, '-')   // 各种连字符 → ASCII -
    .replace(/\u00A0/g, ' ')            // 不换行空格 → 空格
    .replace(/\s+/g, ' ').trim();       // 合并多余空白
}
function translate(t) {
  const s = String(t);
  if (KEEP_RE.test(s) || /^\d{1,2}:\d{2}$/.test(s) || PROPER_RE.test(s)) {
    // 修复(2026-09-02)：'GVG Match Started' 等真句子被 PROPER 前缀整句误保留 → 先查 extra，未提供才保留
    const nk0 = normKey(s);
    if (EXTRA_TR[s] || EXTRA_TR[nk0]) { trStat.extra++; return EXTRA_TR[s] || EXTRA_TR[nk0]; }
    trStat.keep++; keepList.push(s); return null;
  }
  const nk = normKey(s);
  // 修复(2026-09-02)：术语表 16 个词条（Ludo/Jackaroo/Carrom/Uno/XP/ELO/合规缩写等）的"阿语"栏
  // 填的是给人看的中文备注（"✅PM已定：不做音译…"），不是阿语译文——直接输出会把中文备注渲染进 UI。
  // 判据：阿语译文绝不含 CJK；含 CJK 即元备注 → 跳过该词条、按"保留原文不译"处理（备注语义本就是不译）。
  const CJK_RE = /[一-鿿]/;
  const termHit = TERM_CN[s] || TERM_CN[nk] || TERM_EN[s.toLowerCase()] || TERM_EN[nk.toLowerCase()];
  if (termHit && !CJK_RE.test(termHit)) { trStat.term++; return termHit; }
  if (termHit && CJK_RE.test(termHit)) { trStat.keep++; keepList.push(s); return null; }
  if (EXTRA_TR[s] || EXTRA_TR[nk]) { trStat.extra++; return EXTRA_TR[s] || EXTRA_TR[nk]; }
  trStat.miss++; missList.push(s); return null;
}

const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
function imgSrc(src) {
  if (!src) return '';
  if (/^(https?:|data:|file:)/.test(src)) return src;
  return (PKG_BASE || '') + src.replace(/^\.?\//, '');
}

// ===== ③ 嵌套递归 RTL 镜像 + 渲染 =====
function buildKids(nodes) {
  const kids = new Map();
  nodes.forEach(n => { if (n.parent != null) { if (!kids.has(n.parent)) kids.set(n.parent, []); kids.get(n.parent).push(n.idx); } });
  return kids;
}
function renderPage(pg) {
  const nodes = pg.nodes || [];
  const boardW = pg.board ? pg.board.w : 375;
  const kids = buildKids(nodes);
  // G7-组件级语义色：自顶向下计算每个节点继承的语义角色（自身识别到角色则覆盖父级）
  const roleMap = new Map();
  function inheritRole(i, parentRole) {
    const own = detectRole(i, nodes, kids);
    const role = own || parentRole;
    if (role) roleMap.set(i, role);
    for (const c of (kids.get(i) || [])) inheritRole(c, role);
  }
  if (nodes.length) inheritRole(0, null);
  // G7-补：墨刀常把按钮文字作为同级兄弟节点，需把几何上包含在按钮内的文字子树也标记为按钮角色
  for (const n of nodes) {
    const role = roleMap.get(n.idx);
    if (!role || !role.startsWith('button')) continue;
    const sibs = (n.parent != null && kids.get(n.parent) || []).filter(i => i !== n.idx).map(i => nodes[i]);
    for (const s of sibs) {
      if (/wRichText|wWrap|text/.test(s.cls || '') && s.x >= n.x - 1 && s.x + s.w <= n.x + n.w + 1 && s.y >= n.y - 1 && s.y + s.h <= n.y + n.h + 1) {
        const mark = i => { roleMap.set(i, role); for (const c of (kids.get(i) || [])) mark(c); };
        mark(s.idx);
      }
    }
  }
  // 暗色模式：弹窗类页面保留原主题，不套暗色（PM 2026-09-02 规则）
  const pal = (PAL && !isPopupPage(pg.name)) ? PAL : null;
  const skippedDark = !!(PAL && isPopupPage(pg.name));
  // 前置整删（整棵删除纯覆盖层；含真实内容则降级中和）
  const dropped = new Set(), neutralized = new Set();
  const hotStat = { 'blue-svg': 0, 'blue-cls': 0, orange: 0 };
  for (const n of nodes) {
    const kind = isHot(n); if (!kind) continue; hotStat[kind]++;
    if (hasContent(nodes, n.idx, kids)) neutralized.add(n.idx);
    else { (function mark(i) { dropped.add(i); for (const c of (kids.get(i) || [])) mark(c); })(n.idx); }
  }
  // G3 父级逐层高度适配：预翻译所有文本 → 估算换行增长高度 → 标记换行文本及其全部祖先
  const translated = new Map();
  for (const n of nodes) { if (n.text) translated.set(n.idx, translate(n.text) || n.text); }
  const parentOf = new Map();
  nodes.forEach(n => { if (n.parent != null) parentOf.set(n.idx, n.parent); });
  // G7-组件级语义色：向上查找最近祖先语义角色（覆盖按钮文字放在同级兄弟节点等情形）
  const roleOf = i => { let cur = i; while (cur != null) { if (roleMap.has(cur)) return roleMap.get(cur); cur = parentOf.get(cur); } return null; };
  const grownH = new Map(), affected = new Set();
  for (const n of nodes) {
    if (!n.text) continue;
    const out = translated.get(n.idx);
    if (!AR_RE.test(out)) continue;
    const st = n.st || {};
    const fs_ = parseFloat(st.fs) || 14;
    const lh = parseFloat(st.lh) || fs_ * 1.35;
    const estW = out.length * fs_ * 0.55;             // G3 增长触发沿用已验证常量（防裁切，不随 G5 变动）
    if (estW > n.w) {                                  // 译文超宽 → 换行，估算增长高度
      const lines = Math.max(1, Math.ceil(estW / n.w));
      grownH.set(n.idx, Math.max(n.h, lines * lh));
      let cur = n.idx; while (cur != null) { affected.add(cur); cur = parentOf.get(cur); }  // 向上标记所有祖先
    }
  }
  // G1 组合级整体镜像：纯几何组合（仅 div/矩形，无文本/无位图/无SVG）→ 整体 scaleX(-1) 一次
  // 三重护栏：① 子树下无文本/无位图/无SVG ⇒ 不镜像文字、不翻转照片、不翻转方向性图标；
  //          ② 须有 z-index ⇒ 原 per-child 也已建层叠上下文，G1 不改变层叠语义；
  //          ③ 仅取顶层候选（祖先不在候选内），避免嵌套双重翻转
  // 实测教训（2026-09-02）：SVG 图标大量有方向性（箭头/闪电/骰子点阵/Tab 图标），
  //   scaleX(-1) 整体翻后方向反转 + overflow 裁切区偏移 → 图标消失或变空白框。
  //   故 SVG 必须排除，只对真正的纯几何装饰组合做 G1。
  const g1Cand = new Set(), g1Set = new Set();
  const isPure = new Map();
  for (let i = nodes.length - 1; i >= 0; i--) {
    const ch = kids.get(i) || [];
    let pure = !nodes[i].text && !nodes[i].img && !nodes[i].svg;  // 叶子：无文本无位图无SVG
    if (ch.length) pure = pure && ch.every(c => isPure.get(c));
    isPure.set(i, pure);
  }
  for (let i = 0; i < nodes.length; i++) {
    const ch = kids.get(i) || [];
    if (ch.length && isPure.get(i) && (nodes[i].st && nodes[i].st.zi)) g1Cand.add(i);
  }
  for (const i of g1Cand) {                            // 仅取顶层（祖先不在候选内），避免嵌套双重翻转
    let cur = i, top = true;
    while ((cur = parentOf.get(cur)) != null) { if (g1Cand.has(cur)) { top = false; break; } }
    if (top) g1Set.add(i);
  }
  const overWidth = [];   // G2：译文超宽告警清单
  let svgCount = 0, textCount = 0, imgCount = 0;
  function render(idx, inG1 = false) {
    if (dropped.has(idx)) return '';
    const n = nodes[idx]; const st = n.st || {};
    const neu = neutralized.has(idx);
    const p = n.parent != null ? nodes[n.parent] : null;
    const rx = p ? +(n.x - p.x).toFixed(1) : n.x;
    const ry = p ? +(n.y - p.y).toFixed(1) : n.y;
    const containerW = p ? p.w : boardW;
    const flipped = inG1 || g1Set.has(idx);   // G1 后代标记，传给子节点 render
    // 修复(2026-09-02)：G1 顶层也要位置镜像 + scaleX(-1) 才等价于 RTL 镜像；
    // 仅 G1 后代(inG1)保持原相对位（内部图形已由祖先 scaleX(-1) 翻转）。
    // 旧逻辑 G1 顶层保持原位只翻内部 → 与镜像后的兄弟文字重叠（开关压字等 208 处）。
    const mx = +(inG1 ? rx : (containerW - rx - n.w)).toFixed(1);
    let s = `position:absolute;left:${mx}px;top:${ry}px;width:${n.w}px;height:${n.h}px;`;
    if (st.zi) s += `z-index:${st.zi};`;
    if (g1Set.has(idx)) s += `transform:scaleX(-1);transform-origin:center;`;  // G1：纯图形组合整体翻一次
    if (st.op) s += `opacity:${st.op};`;
    if (st.ovf) s += `overflow:${affected.has(idx) ? 'visible' : st.ovf};`;
    if (st.bg && !(neu && HOT_ORANGE.test(st.bg))) s += `background:${darken(st.bg, 'bg', pal, roleOf(idx))};`;
    if (st.bgi && !/devices/.test(st.bgi)) s += `background-image:${st.bgi};background-size:cover;background-position:center;`;
    if (st.br) s += `border-radius:${st.br};`;
    if (st.bw) s += `border:${st.bw} ${st.bs || 'solid'} ${darken(st.bc || '#ccc', 'bc', pal, roleOf(idx))};`;
    if (st.bsh) s += `box-shadow:${st.bsh};`;
    if (st.ow && st.os && st.os !== 'none') s += `outline:${st.ow} ${st.os} ${st.oc || '#000'};`;
    if (st.flt) s += `filter:${st.flt};`;
    if (st.cp) s += `clip-path:${st.cp};`;
    if (st.mk && !/url\(/.test(st.mk)) s += `mask:${st.mk};-webkit-mask:${st.mk};`;
    let inner = '';
    if (n.svg && !(neu && HOT_BLUE_SVG.test(n.svg))) {
      svgCount++; if (st.clr) s += `color:${darken(st.clr, 'clr', pal, roleOf(idx))};`;
      // G7-补：暗色模式下图标原色在 #121212 暗底不可见 → 强制亮化
      if (THEME === 'dark' && pal && !neu) s += `filter:brightness(0) invert(0.85);`;
      return `<div class="el ic" style="${s}">${n.svg}</div>`;
    }
    if (n.img) {
      imgCount++;
      // G7-补：暗色模式下图片图标原色不可见 → 强制亮化
      if (THEME === 'dark' && pal) s += `filter:brightness(0) invert(0.85);`;
      return `<div class="el im" style="${s}"><img src="${imgSrc(n.img)}" alt="" style="width:100%;height:100%;object-fit:cover;display:block"></div>`;
    }
    if (n.text) {
      textCount++;
      const out = translated.get(n.idx);   // 已在 G3 预翻译阶段算好（统计仅计一次）
      const fs_ = parseFloat(st.fs) || 14;
      const lh = parseFloat(st.lh) || fs_ * 1.35;
      const ar = AR_RE.test(out);
      const taMap = { left: 'right', right: 'left', start: 'end', end: 'start' };
      const ta = taMap[st.ta] || st.ta || 'right';
      s += `font-size:${fs_}px;font-weight:${st.fw || 400};line-height:${lh}px;color:${darken(st.clr || '#000', 'clr', pal, roleOf(idx))};`;
      s += ar
        ? `font-family:'Noto Sans Arabic','Segoe UI',Tahoma,sans-serif;`
        : `font-family:'Noto Sans SC','Noto Sans',sans-serif;direction:ltr;unicode-bidi:isolate;`;
      s += `text-align:${ta};white-space:pre-wrap;`;
      if (ar) s += `min-height:${grownH.has(n.idx) ? grownH.get(n.idx).toFixed(1) : Math.max(n.h, fs_ * 1.4).toFixed(1)}px;height:auto;`;
      inner += (ar && /[0-9A-Za-z]/.test(out))
        ? esc(out).replace(/([0-9A-Za-z][0-9A-Za-z\s.:/]*)/g, mm => `<bdi dir="ltr">${mm}</bdi>`)
        : esc(out);
      // G2 超宽检测（G5 校准）：估算译文宽 ≈ 字符类加权字宽之和，超出原宽 105% → 告警
      const estW = estTextWidth(out, fs_);
      if (ar && estW > n.w * 1.05) overWidth.push({ text: out.slice(0, 30), w: Math.round(estW), limit: n.w });
    }
    const ch = kids.get(idx) || [];
    inner += ch.map(c => render(c, flipped)).join('');
    return `<div class="el" style="${s}">${inner}</div>`;
  }
  const bodyHtml = nodes.length ? render(0) : '';
  const maxY = nodes.reduce((m, n) => {
    if (dropped.has(n.idx)) return m;
    const h = (n.text && grownH.has(n.idx)) ? grownH.get(n.idx) : n.h;   // G3：换行文本用增长后高度，舞台随之伸长
    return Math.max(m, n.y + h);
  }, pg.board ? pg.board.h : 812);
  return { bodyHtml, maxY, hotStat, dropped: dropped.size, neutralized: neutralized.size, svgCount, textCount, imgCount, overWidth, g1: g1Set.size, kept: nodes.length - dropped.size, skippedDark };
}

const cells = [];
let totEls = 0, totHot = 0, totSvg = 0, totTxt = 0, totImg = 0, totG1 = 0;
const allOver = [], darkSkippedPages = [];
for (let i = 0; i < pages.length; i++) {
  const pg = pages[i];
  const r = renderPage(pg);
  if (pg.err) {
    cells.push(`<div class="card"><div class="cap"><span class="idx">${i + 1}</span>${esc(pg.name || ('Page ' + (i + 1)))}</div><div class="stage"><div class="screen err">提取失败：${esc(pg.err)}</div></div></div>`);
    continue;
  }
  // 屏内主题底色（仅屏内承载主题色；预览画布外壳恒定中性灰，不随主题变）
  const screenBg = (PAL && !r.skippedDark) ? PAL.screen : '#fff';
  cells.push(
    `<div class="card">` +
      `<div class="cap"><span class="idx">${i + 1}</span>${esc(pg.name || ('Page ' + (i + 1)))}` +
        (r.skippedDark ? `<span class="tag-dark">原主题</span>` : '') + `</div>` +
      `<div class="stage" style="height:${r.maxY}px"><div class="screen" style="height:${r.maxY}px;background:${screenBg}">${r.bodyHtml}</div></div>` +
    `</div>`
  );
  totEls += r.kept; totHot += r.dropped; totSvg += r.svgCount; totTxt += r.textCount; totImg += r.imgCount; totG1 += r.g1;
  if (r.skippedDark) darkSkippedPages.push(pg.name || ('Page ' + (i + 1)));
  if (r.overWidth.length) allOver.push({ page: pg.name, items: r.overWidth });
}
const totalOver = allOver.reduce((m, o) => m + o.items.length, 0);

const html = `<!DOCTYPE html>
<html lang="zh" dir="ltr">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>${esc(TITLE)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#eceff1;color:#1a1a1a;font-family:'Noto Sans SC','Noto Sans',sans-serif;padding:24px 20px 48px}
  .wrap{margin:0 auto;padding:0 16px}
  header{border-bottom:1px solid #cfd8dc;padding-bottom:12px;margin-bottom:18px}
  h1{font-size:18px;font-weight:700}
  .sub{font-size:12px;color:#607d8b;margin-top:5px;line-height:1.8}
  .grid{display:grid;grid-template-columns:repeat(auto-fill,375px);gap:28px;justify-content:center;margin-top:6px}
  .card{display:flex;flex-direction:column;align-items:center;gap:8px}
  .cap{font-size:13px;color:#37474f;font-weight:600;text-align:center;width:100%;display:flex;align-items:center;justify-content:center;gap:6px}
  .cap .idx{display:inline-flex;align-items:center;justify-content:center;min-width:18px;height:18px;border-radius:50%;background:#eceff1;color:#90a4ae;font-size:10px;font-weight:700;padding:0 5px}
  .stage{position:relative;width:375px;background:#fff;border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.18)}
  .screen{position:relative;width:375px;display:block;background:#fff;overflow:hidden;direction:rtl}
  .el{position:absolute;unicode-bidi:isolate}
  .el.ic svg{width:100%;height:100%;display:block}
  .el.err{display:flex;align-items:center;justify-content:center;color:#c62828;font-size:12px;padding:20px;text-align:center}
  .tag-dark{font-size:10px;font-weight:700;color:#8a6d3b;background:#fff3cd;border:1px solid #ffeeba;border-radius:4px;padding:1px 5px}
  bdi{unicode-bidi:isolate}
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>${esc(TITLE)}</h1>
    <div class="sub">共 ${pages.length} 屏 · 画布 375 宽 · 矩阵式排布 · 单一自包含 HTML · 无交互<br>
    翻译：术语表命中 ${trStat.term} · 补充 ${trStat.extra} · 保留不译 ${trStat.keep} · 未命中 ${trStat.miss}${totalOver ? `<br>超宽告警 ${totalOver} 条（高频页清单见运行日志，供人工精简）` : ''}<br>
    交互层前置整删 · 嵌套 RTL 镜像 · 阿语 Noto Sans Arabic · 标题保留中文${THEME === 'dark' ? ' · <b>暗色模式</b>（弹窗页保留原主题）' : ''}</div>
  </header>
  <div class="grid">
${cells.join('\n')}
  </div>
</div>
</body>
</html>
`;

fs.writeFileSync(OUT, html, 'utf8');
console.log('已生成平铺版:', OUT, '| KB:', (html.length / 1024).toFixed(1));
console.log(`QC → 页面:${pages.length} 保留节点:${totEls} 交互整删:${totHot} 文本:${totTxt} SVG:${totSvg} 图片:${totImg} 组合镜像G1:${totG1}`);
console.log(`翻译统计 → 术语表命中 ${trStat.term} · 补充 ${trStat.extra} · 保留不译 ${trStat.keep} · 未命中 ${trStat.miss}`);
if (trStat.keep) console.log(`保留不译：[${[...new Set(keepList)].map(t => JSON.stringify(t)).join(', ')}]`);
if (missList.length) { console.log('!! 未命中清单（需补译）：'); for (const t of [...new Set(missList)]) console.log(`   ${JSON.stringify(t)}`); }
else console.log('未命中 0 条 —— 全部文案已处理');
if (allOver.length) {
  // 超宽「频率高页面」清单（PM 2026-09-02 answer #3）：按超宽条目数降序，供 PM 优先人工精简
  const freq = new Map();
  for (const { page, items } of allOver) freq.set(page, (freq.get(page) || 0) + items.length);
  const pageFreq = [...freq.entries()].map(([page, n]) => ({ page, n })).sort((a, b) => b.n - a.n);
  console.log('\n📊 超宽「频率高页面」清单（按超宽条目数降序，优先人工精简）：');
  for (const { page, n } of pageFreq) console.log(`   ${String(n).padStart(2)} 条  ·  ${page}`);
  console.log('\n⚠ 译文超宽明细（G2，建议精简或换行，供人工复核）：');
  for (const { page, items } of allOver) for (const it of items) console.log(`   [${page}] "${it.text}" 估算宽 ${it.w}px > 限 ${it.limit}px`);
}
// 暗色模式运行报告（G7）
if (THEME === 'dark') {
  if (PAL_ERR) console.log(`\n!! 暗色配色载入失败（${PAL_ERR}）→ 已退回原主题。检查 --palette 路径`);
  else {
    console.log(`\n暗色模式 → 配色:${PAL_PATH.split(/[\\/]/).pop()} · 屏内底 ${PAL.screen}`);
    if (darkSkippedPages.length) {
      console.log(`  弹窗页保留原主题 ${darkSkippedPages.length} 屏（命名含「弹窗/Popup」）：`);
      for (const p of darkSkippedPages) console.log(`     ${p}`);
    } else console.log('  无弹窗页，全部套用暗色');
  }
  if (darkUnmatched.size) {
    console.log(`\n⚠ 暗色未匹配色值 ${darkUnmatched.size} 个（已保持原色，建议人工复核后补进 dark-palette.json）：`);
    for (const ck of [...darkUnmatched]) {
      const [r, g, b] = ck.split(',').map(Number);
      console.log(`   rgb(${ck})  #${[r, g, b].map(v => v.toString(16).padStart(2, '0')).join('')}`);
    }
  } else if (PAL) console.log('  暗色色值全部命中配色表 ✓');
}
