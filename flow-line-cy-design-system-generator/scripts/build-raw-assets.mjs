#!/usr/bin/env node
// build-raw-assets.mjs —— 生成「原始素材」两个独立查看页（工作台顶栏右侧文字入口的目标页面）
// ① 原始组件库规范.html —— 每库一张风格样张卡：用各库官方主色与形态语言直接画出
//    按钮/标签/输入框/开关/迷你卡的实际视觉形态（纯 CSS 内联渲染，无代码无文档文本）
// ② 原始参考令牌库.html —— data/uupm 外部参考数据快照，全部可视化渲染：
//    色板=色块卡 · 字体=真实字样+字重档 · 图表=迷你图形示意 · 落地页=结构缩略块 · 介绍中文
// 用法: node build-raw-assets.mjs <输出目录>   或被 build-workbench.mjs 动态调用
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// ---------- 图表迷你示意（SVG；按中文图表名匹配） ----------
const SVG_C = { p: '#4C8DFF', p2: '#BBD4F5', o: '#F59E0B', g: '#34C77B', grid: '#E7EBF2' };
function chartSvg(type) {
  const t = String(type ?? '');
  const W = 132, H = 60;
  const open = `<svg viewBox="0 0 ${W} ${H}" style="width:${W}px;height:${H}px;flex-shrink:0">`;
  const close = '</svg>';
  const grid = `<rect x="0" y="0" width="${W}" height="${H}" fill="#FAFBFD" rx="6"/>` + [14, 28, 42].map(y => `<line x1="6" y1="${y}" x2="${W - 6}" y2="${y}" stroke="${SVG_C.grid}" stroke-width="1"/>`).join('');
  const pt = (x, y) => `${x},${y}`;
  if (/饼|环|部分与整体|占比|比例|份额/.test(t)) {
    return open + grid + `<circle cx="36" cy="30" r="20" fill="${SVG_C.p2}"/><path d="M36 30 L36 10 A20 20 0 0 1 54 36 Z" fill="${SVG_C.p}"/><path d="M36 30 L54 36 A20 20 0 0 1 40 49 Z" fill="${SVG_C.o}"/><circle cx="36" cy="30" r="11" fill="#FAFBFD"/>` + close;
  }
  if (/漏斗/.test(t)) {
    return open + grid + [[10, 22], [22, 16], [34, 10]].map((w, i) => `<rect x="${(W - w[0]) / 2}" y="${w[1]}" width="${w[0]}" height="8" rx="2" fill="${i === 0 ? SVG_C.p : i === 1 ? '#7FA9EF' : SVG_C.p2}"/>`).join('') + close;
  }
  if (/仪表|表盘|子弹|温度计|绩效|指标|大数字/.test(t)) {
    return open + grid + `<path d="M20 44 A40 40 0 0 1 112 44" fill="none" stroke="${SVG_C.p2}" stroke-width="10" stroke-linecap="round"/><path d="M20 44 A40 40 0 0 1 88 16" fill="none" stroke="${SVG_C.p}" stroke-width="10" stroke-linecap="round"/><circle cx="66" cy="44" r="3" fill="${SVG_C.o}"/>` + close;
  }
  if (/雷达|蜘蛛/.test(t)) {
    const cx = 66, cy = 30, R = 24;
    const poly = n => Array.from({ length: n }, (_, i) => { const a = Math.PI * 2 * i / n - Math.PI / 2; return pt(cx + R * Math.cos(a), cy + R * Math.sin(a)); }).join(' ');
    const val = Array.from({ length: 5 }, (_, i) => { const a = Math.PI * 2 * i / 5 - Math.PI / 2; const r = R * [0.9, 0.5, 0.75, 0.6, 0.4][i]; return pt(cx + r * Math.cos(a), cy + r * Math.sin(a)); }).join(' ');
    return open + grid + `<polygon points="${poly(5)}" fill="none" stroke="${SVG_C.p2}" stroke-width="1"/><polygon points="${val}" fill="${SVG_C.p}55" stroke="${SVG_C.p}" stroke-width="1.5"/>` + close;
  }
  if (/树图|旭日|冰柱|层级/.test(t)) {
    return open + grid + `<rect x="8" y="8" width="70" height="30" fill="${SVG_C.p}"/><rect x="80" y="8" width="44" height="30" fill="${SVG_C.p2}"/><rect x="8" y="40" width="46" height="14" fill="${SVG_C.o}"/><rect x="56" y="40" width="30" height="14" fill="#7FA9EF"/><rect x="88" y="40" width="36" height="14" fill="${SVG_C.p2}"/>` + close;
  }
  if (/瀑布|累计/.test(t)) {
    return open + grid + [[14, 34, 16], [38, 22, 18], [62, 28, 14], [86, 14, 20]].map((c, i) => `<rect x="${c[0]}" y="${c[1]}" width="${c[2]}" height="${48 - c[1]}" fill="${i === 3 ? SVG_C.g : SVG_C.p}"/>`).join('') + close;
  }
  if (/K线|蜡烛|股票|交易/.test(t)) {
    return open + grid + [[24, 12, 20], [56, 20, 16], [88, 10, 22]].map((c, i) => `<line x1="${c[0] + 6}" y1="${c[1] - 6}" x2="${c[0] + 6}" y2="${c[1] + c[2] + 6}" stroke="${i === 1 ? '#E05B5B' : SVG_C.g}" stroke-width="1.5"/><rect x="${c[0]}" y="${c[1]}" width="12" height="${c[2]}" fill="${i === 1 ? '#E05B5B' : SVG_C.g}" rx="1"/>`).join('') + close;
  }
  if (/地图|地理|填色/.test(t) && !/热力/.test(t)) {
    return open + grid + `<path d="M18 14 L44 10 L52 26 L38 40 L18 34 Z" fill="${SVG_C.p}"/><path d="M56 12 L86 8 L96 24 L72 34 L56 26 Z" fill="${SVG_C.p2}"/><path d="M30 44 L58 40 L70 52 L38 54 Z" fill="${SVG_C.o}"/>` + close;
  }
  if (/热力|强度|密度|矩阵/.test(t)) {
    const cells = [];
    for (let r = 0; r < 3; r++) for (let c = 0; c < 7; c++) {
      const o = [0.25, 0.5, 0.8, 0.45, 0.9, 0.35, 0.6][c] * (1 - r * 0.18);
      cells.push(`<rect x="${10 + c * 16}" y="${12 + r * 13}" width="13" height="10" rx="2" fill="${SVG_C.p}" opacity="${o.toFixed(2)}"/>`);
    }
    return open + grid + cells.join('') + close;
  }
  if (/散点|相关|分布/.test(t)) {
    const dots = [[18, 40], [30, 32], [38, 38], [48, 24], [58, 30], [66, 18], [78, 26], [88, 14], [100, 20], [44, 44], [72, 40]].map(p => `<circle cx="${p[0]}" cy="${p[1]}" r="3" fill="${SVG_C.p}"/>`).join('');
    return open + grid + dots + close;
  }
  if (/气泡/.test(t)) {
    return open + grid + `<circle cx="26" cy="38" r="5" fill="${SVG_C.p2}"/><circle cx="46" cy="26" r="9" fill="${SVG_C.p}"/><circle cx="72" cy="34" r="6" fill="${SVG_C.o}"/><circle cx="96" cy="20" r="11" fill="${SVG_C.p}"/>` + close;
  }
  if (/桑基|冲积|弦|流向|流程/.test(t)) {
    return open + grid + `<path d="M12 14 C50 14 80 30 120 30" stroke="${SVG_C.p}" stroke-width="9" fill="none" opacity="0.85"/><path d="M12 40 C50 40 80 38 120 44" stroke="${SVG_C.p2}" stroke-width="7" fill="none"/>` + close;
  }
  if (/时间线|排期|甘特|时长/.test(t)) {
    return open + grid + `<rect x="10" y="12" width="52" height="8" rx="4" fill="${SVG_C.p}"/><rect x="42" y="25" width="66" height="8" rx="4" fill="${SVG_C.p2}"/><rect x="70" y="38" width="46" height="8" rx="4" fill="${SVG_C.o}"/>` + close;
  }
  if (/箱线|小提琴|直方/.test(t)) {
    return open + grid + [[20, 18, 26], [52, 26, 18], [84, 14, 30]].map(b => `<rect x="${b[0]}" y="${b[1]}" width="20" height="${b[2]}" fill="none" stroke="${SVG_C.p}" stroke-width="2"/><line x1="${b[0]}" y1="${b[1] + b[2] / 2}" x2="${b[0] + 20}" y2="${b[1] + b[2] / 2}" stroke="${SVG_C.p}" stroke-width="2"/>`).join('') + close;
  }
  if (/面积/.test(t)) {
    return open + grid + `<path d="M8 46 L28 30 L48 38 L68 20 L88 28 L108 12 L108 50 L8 50 Z" fill="${SVG_C.p}33"/><path d="M8 46 L28 30 L48 38 L68 20 L88 28 L108 12" fill="none" stroke="${SVG_C.p}" stroke-width="2.5"/>` + close;
  }
  if (/堆叠/.test(t)) {
    return open + grid + [[16], [44], [72], [100]].map((x, i) => `<rect x="${x[0]}" y="${18 + i * 4}" width="16" height="14" fill="${SVG_C.p}"/><rect x="${x[0]}" y="${34 + i * 2}" width="16" height="8" fill="${SVG_C.p2}"/>`).join('') + close;
  }
  if (/柱|条形|排名|对比|表格/.test(t)) {
    return open + grid + [[12, 26], [38, 16], [64, 34], [90, 10]].map(b => `<rect x="${b[0]}" y="${b[1]}" width="18" height="${52 - b[1]}" rx="2" fill="${b[1] === 10 ? SVG_C.o : SVG_C.p}"/>`).join('') + close;
  }
  // 默认：折线
  return open + grid + `<polyline points="8,42 28,28 48,34 68,18 88,26 108,12" fill="none" stroke="${SVG_C.p}" stroke-width="2.5"/>` + close;
}
// ---------- 落地页结构缩略：区块类型识别 → 按类型画真实版式 ----------
const SECTYPES = [
  ['hero', '首屏', /hero|headline|video|banner/i],
  ['value', '价值点', /value|benefit|prop/i],
  ['compare', '对比表', /compar|table|versus/i],
  ['features', '特性组', /feature|key\b/i],
  ['proof', '证言', /testimonial|proof|review|quote/i],
  ['pricing', '定价', /pricing|plan|tier|price/i],
  ['form', '表单', /form|email|signup|capture|lead|subscribe/i],
  ['faq', '问答', /faq/i],
  ['steps', '步骤', /step|wizard|progress/i],
  ['notify', '通知', /waitlist|coming|notify|countdown/i],
  ['chapter', '章节', /chapter|story/i],
  ['gallery', '画廊', /gallery|logo|media|screenshot/i],
  ['cta', 'CTA', /cta|button|action\b/i],
  ['footer', '页脚', /footer|legal|copyright/i],
  ['text', '文本', /intro|problem|solution|descri|content|text|about|outline/i],
];
function secArt(type) {
  const CARD = 'background:#fff;border:1px solid #B9C9DE;border-radius:4px;';
  switch (type) {
    case 'hero': return '<div style="height:48px;background:#B9CBE4;border-radius:4px;position:relative;overflow:hidden"><div style="position:absolute;left:10px;top:12px;width:40%;height:7px;background:#31486E;border-radius:2px"></div><div style="position:absolute;left:10px;top:24px;width:30%;height:5px;background:#6E8CBB;border-radius:2px"></div><div style="position:absolute;left:10px;bottom:8px;width:24%;height:10px;background:#E8952F;border-radius:2px"></div><div style="position:absolute;right:10px;top:8px;width:40px;height:32px;background:#8FA9D9;border-radius:4px"></div></div>';
    case 'value': return '<div style="display:flex;gap:6px">' + [0, 1].map(() => '<div style="flex:1;background:#fff;border:1px solid #B9C9DE;border-radius:4px;padding:5px 7px"><div style="height:5px;width:55%;background:#7E9BC7;border-radius:2px;margin-bottom:4px"></div><div style="height:4px;width:92%;background:#C9D6EA;border-radius:2px;margin-bottom:3px"></div><div style="height:4px;width:75%;background:#DCE4F0;border-radius:2px"></div></div>').join('') + '</div>';
    case 'features': return '<div style="display:flex;gap:6px">' + [0, 1, 2].map(() => '<div style="flex:1;background:#fff;border:1px solid #B9C9DE;border-radius:4px;padding:5px 6px"><div style="width:13px;height:13px;background:#8FA9D9;border-radius:3px;margin-bottom:4px"></div><div style="height:4px;background:#7E9BC7;border-radius:2px;margin-bottom:3px"></div><div style="height:4px;width:68%;background:#DCE4F0;border-radius:2px"></div></div>').join('') + '</div>';
    case 'proof': return '<div style="display:flex;gap:6px">' + [0, 1].map((_, i) => '<div style="flex:1;background:#fff;border:1px solid #C4BCE4;border-radius:' + (i ? '8px 8px 2px 8px' : '8px 8px 2px 8px') + ';padding:5px 7px;display:flex;gap:5px"><div style="width:11px;height:11px;border-radius:99px;background:#8FA9D9;flex-shrink:0"></div><div style="flex:1;padding-top:1px"><div style="height:4px;background:#B9C2DE;border-radius:2px;margin-bottom:3px"></div><div style="height:4px;width:65%;background:#DDE1F0;border-radius:2px"></div></div></div>').join('') + '</div>';
    case 'pricing': return '<div style="display:flex;gap:6px;align-items:stretch">' + [0, 1, 2].map(i => '<div style="flex:1;background:#fff;' + (i === 1 ? 'border:2px solid #7E9BC7;' : 'border:1px solid #C9D6EA;') + 'border-radius:4px;padding:4px 5px"><div style="height:4px;width:50%;background:' + (i === 1 ? '#7E9BC7' : '#C9D6EA') + ';border-radius:2px;margin-bottom:3px"></div><div style="height:3px;background:#E0E7F2;border-radius:2px;margin-bottom:2px"></div><div style="height:3px;background:#E0E7F2;border-radius:2px;margin-bottom:2px"></div><div style="height:3px;width:65%;background:#E0E7F2;border-radius:2px"></div></div>').join('') + '</div>';
    case 'compare': return '<div style="border:1px solid #8FA9D9;border-radius:3px;overflow:hidden"><div style="display:flex;height:11px;background:#8FA9D9"><span style="flex:1.2;border-right:1px solid #fff"></span><span style="flex:1;border-right:1px solid #fff"></span><span style="flex:1"></span></div><div style="display:flex;height:10px;background:#fff"><span style="flex:1.2;border-right:1px solid #DCE4F0;border-bottom:1px solid #E9EEF5"></span><span style="flex:1;border-right:1px solid #DCE4F0;border-bottom:1px solid #E9EEF5"></span><span style="flex:1;border-bottom:1px solid #E9EEF5"></span></div><div style="display:flex;height:10px;background:#F7F9FC"><span style="flex:1.2;border-right:1px solid #DCE4F0"></span><span style="flex:1;border-right:1px solid #DCE4F0"></span><span style="flex:1"></span></div></div>';
    case 'form': return '<div style="background:#fff;border:1px solid #B9C9DE;border-radius:4px;padding:6px 8px;display:flex;flex-direction:column;gap:4px"><div style="height:9px;background:#F2F5F9;border:1px solid #B9C9DE;border-radius:2px"></div><div style="height:9px;background:#F2F5F9;border:1px solid #B9C9DE;border-radius:2px"></div><div style="height:11px;width:40%;background:#E8952F;border-radius:2px"></div></div>';
    case 'faq': return '<div style="display:flex;flex-direction:column;gap:4px">' + [0, 1, 2].map(() => '<div style="height:12px;background:#fff;border:1px solid #B9C9DE;border-radius:3px;display:flex;align-items:center;justify-content:space-between;padding:0 7px"><i style="width:55%;height:4px;background:#B7C9E8;border-radius:2px"></i><i style="font-size:10px;color:#7E9BC7;font-style:normal;line-height:1">+</i></div>').join('') + '</div>';
    case 'steps': return '<div style="display:flex;align-items:center;padding:2px 0">' + [0, 1, 2].map((_, i) => '<span style="display:flex;align-items:center"><i style="width:13px;height:13px;border-radius:99px;background:' + (i === 0 ? '#7E9BC7' : '#fff') + ';border:2px solid ' + (i === 0 ? '#7E9BC7' : '#C9D6EA') + ';box-sizing:border-box"></i><i style="width:16px;height:2px;background:#C9D6EA"></i></span>').join('') + '</div>';
    case 'gallery': return '<div style="display:flex;gap:6px">' + [0, 1, 2, 3].map((_, i) => '<div style="flex:1;height:24px;background:' + ['#8FA9D9', '#B7C9E8', '#7E9BC7', '#A9BFE0'][i] + ';border-radius:3px"></div>').join('') + '</div>';
    case 'notify': return '<div style="height:19px;background:#fff;border:1px solid #E8CFA0;border-radius:4px;display:flex;align-items:center;justify-content:space-between;padding:0 7px"><i style="width:32%;height:4px;background:#E8B366;border-radius:2px"></i><i style="width:18%;height:9px;background:#E8952F;border-radius:2px"></i></div>';
    case 'chapter': return '<div style="display:flex;gap:6px;align-items:center"><div style="flex:1;display:flex;flex-direction:column;gap:3px"><div style="height:5px;width:75%;background:#7E9BC7;border-radius:2px"></div><div style="height:4px;width:95%;background:#C9D6EA;border-radius:2px"></div></div><div style="width:28px;height:19px;background:#8FA9D9;border-radius:3px;flex-shrink:0"></div></div>';
    case 'cta': return '<div style="height:28px;background:#C9D6EA;border-radius:4px;display:flex;align-items:center;justify-content:center"><div style="width:46%;height:14px;background:#E8952F;border-radius:3px;display:flex;align-items:center;justify-content:center"><i style="width:55%;height:4px;background:rgba(255,255,255,.92);border-radius:2px"></i></div></div>';
    case 'footer': return '<div style="height:12px;background:#9AA7B8;border-radius:3px;display:flex;align-items:center;gap:6px;padding:0 8px"><i style="width:14%;height:3px;background:#fff;border-radius:2px"></i><i style="width:10%;height:3px;background:#C9D2DD;border-radius:2px"></i><i style="width:12%;height:3px;background:#C9D2DD;border-radius:2px"></i></div>';
    default: return '<div style="display:flex;flex-direction:column;gap:3px;padding:1px 0"><div style="height:5px;width:100%;background:#C9D2DD;border-radius:2px"></div><div style="height:5px;width:90%;background:#D5DBE4;border-radius:2px"></div><div style="height:5px;width:68%;background:#DDE2EA;border-radius:2px"></div></div>';
  }
}
function structStrip(orderText) {
  const parts = String(orderText ?? '').split(/\s*\d+\.\s*/).map(s => s.trim()).filter(Boolean).slice(0, 8);
  if (!parts.length) return '';
  const rows = parts.map(p => {
    let type = 'text', label = '文本';
    for (const [t, l, re] of SECTYPES) { if (re.test(p)) { type = t; label = l; break; } }
    return '<div class="ls-row"><span class="ls-n">' + esc(label) + '</span><div class="ls-a">' + secArt(type) + '</div></div>';
  }).join('');
  return '<div class="ls">' + rows + '</div>';
}

// tbl: line=行分隔 grid=全边框 zebra=斑马纹 · input: border=白底描边 fill=灰底无边框
// card: border/shadow/tonal · d: c=紧凑 n=标准 · inset=列表分隔线内缩 · widgets 对齐各库文档快照
const STYLES = [
  { id: 'weui', name: 'WeUI', group: '小程序生态', c: '#07C160', cd: '#06AD56', r: '8px', shape: 'pill', input: 'fill', card: 'border', d: 'n', note: '微信官方视觉语言 · 克制标准', end: '小程序 / H5', widgets: ['page', 'cells', 'dialog', 'toast', 'progress', 'badge', 'actionbar'] },
  { id: 'wechat-miniprogram', name: '微信小程序设计指南', group: '小程序生态', c: '#07C160', cd: '#06AD56', r: '8px', shape: 'pill', input: 'fill', card: 'border', d: 'n', note: '官方设计指南 · 与 WeUI 同源', end: '小程序', widgets: ['navbar', 'cells', 'toast', 'progress', 'tabbar'] },
  { id: 'vant', name: 'Vant', group: '移动 H5', c: '#1989FA', cd: '#0C7AD8', r: '4px', shape: 'round', input: 'border', card: 'border', d: 'n', note: '有赞移动组件 · 轻快规范', end: '移动 H5', widgets: ['cells', 'tabs', 'stepper', 'slider', 'rate', 'actionbar', 'badge'] },
  { id: 'antd-mobile', name: 'Ant Design Mobile', group: '移动 H5', c: '#1677FF', cd: '#0958D9', r: '4px', shape: 'round', input: 'border', card: 'border', d: 'n', note: '蚂蚁移动体系 · 干净利落', end: '移动 H5', widgets: ['tabbar', 'dialog', 'progress', 'stepper', 'badge', 'actionbar', 'cells'] },
  { id: 'varlet', name: 'Varlet', group: '移动 H5', c: '#3A7AFE', cd: '#2B62DB', r: '4px', shape: 'round', input: 'border', card: 'border', d: 'n', note: 'Material 风移动组件', end: '移动 H5', widgets: ['fab', 'cells', 'tabs', 'slider', 'rate', 'badge'] },
  { id: 'tdesign-mobile', name: 'TDesign Mobile', group: '移动 H5', c: '#0052D9', cd: '#0043B8', r: '6px', shape: 'round', input: 'border', card: 'border', d: 'n', note: '腾讯移动设计体系', end: '移动', widgets: ['navbar', 'cells', 'tabs', 'stepper', 'toast', 'badge', 'slider'] },
  { id: 'antd', name: 'Ant Design', group: 'PC / Web', c: '#1677FF', cd: '#0958D9', r: '6px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'n', note: '企业级设计语言 · 清晰高效', end: 'PC', widgets: ['navbar', 'table', 'pagination', 'breadcrumb', 'steps', 'tabs', 'banner', 'timeline', 'rate', 'stepper', 'badge', 'tree'] },
  { id: 'arco', name: 'Arco Design', group: 'PC / Web', c: '#165DFF', cd: '#0E42D2', r: '3px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'c', note: '字节跳动设计体系 · 紧凑直角感', end: 'PC', widgets: ['navbar', 'table', 'pagination', 'tabs', 'banner', 'slider', 'steps', 'timeline', 'badge'] },
  { id: 'element', name: 'Element Plus', group: 'PC / Web', c: '#409EFF', cd: '#337ECC', r: '4px', shape: 'round', tbl: 'grid', input: 'border', card: 'border', d: 'n', note: '饿了吗系 · 明快直接', end: 'PC', widgets: ['table', 'pagination', 'breadcrumb', 'dialog', 'slider', 'badge', 'rate', 'tabs'] },
  { id: 'naive-ui', name: 'Naive UI', group: 'PC / Web', c: '#18A058', cd: '#128A4B', r: '3px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'n', note: '图森未来 · 清爽绿色系', end: 'PC', widgets: ['table', 'dialog', 'rate', 'progress', 'tabs', 'badge'] },
  { id: 'shadcn-ui', name: 'shadcn/ui', group: 'PC / Web', c: '#18181B', cd: '#000000', r: '8px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'n', note: '黑白灰极简 · 组合优先', end: 'Web', widgets: ['navbar', 'table', 'dialog', 'badge', 'pagination', 'tabs', 'slider'] },
  { id: 'chakra-ui', name: 'Chakra UI', group: 'PC / Web', c: '#319795', cd: '#287B78', r: '6px', shape: 'round', input: 'fill', card: 'border', d: 'n', note: '青绿主色 · 无障碍友好', end: 'Web', widgets: ['tabs', 'slider', 'badge', 'toast', 'progress', 'stepper'] },
  { id: 'mantine', name: 'Mantine', group: 'PC / Web', c: '#228BE6', cd: '#1C7ED6', r: '8px', shape: 'round', tbl: 'line', input: 'fill', card: 'shadow', d: 'n', note: '蓝主色 · 组件齐全', end: 'Web', widgets: ['navbar', 'table', 'tabs', 'progress', 'pagination', 'banner'] },
  { id: 'heroui', name: 'HeroUI', group: 'PC / Web', c: '#006FEE', cd: '#0059BF', r: '10px', shape: 'round', input: 'fill', card: 'shadow', d: 'n', note: '亮蓝主色 · 柔影大圆角', end: 'Web', widgets: ['fab', 'tabs', 'badge', 'slider', 'progress', 'rate'] },
  { id: 'radix-themes', name: 'Radix Themes', group: 'PC / Web', c: '#6E56CF', cd: '#5B46A9', r: '8px', shape: 'round', input: 'border', card: 'border', d: 'n', note: '灰阶底层 · 紫罗兰点缀', end: 'Web', widgets: ['dialog', 'tabs', 'slider', 'badge'] },
  { id: 'fluent-2', name: 'Fluent 2', group: 'PC / Web', c: '#0078D4', cd: '#106EBE', r: '4px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'n', note: '微软官方设计系统', end: '跨端', widgets: ['breadcrumb', 'table', 'slider', 'dialog', 'badge'] },
  { id: 'carbon', name: 'IBM Carbon', group: 'PC / Web', c: '#0F62FE', cd: '#0353E9', r: '0px', shape: 'sharp', tbl: 'grid', input: 'border', card: 'border', d: 'c', note: '直角几何 · 企业理性', end: 'Web', widgets: ['table', 'pagination', 'tabs', 'breadcrumb', 'steps', 'banner'] },
  { id: 'hig-apple', name: 'Apple HIG', group: '系统设计规范', c: '#007AFF', cd: '#0066D6', r: '999px', shape: 'pill', input: 'fill', card: 'shadow', d: 'n', inset: true, note: 'iOS 原生 · 细腻通透', end: 'iOS', widgets: ['segmented', 'cells', 'tabbar', 'slider', 'rate', 'stepper'] },
  { id: 'harmonyos', name: 'HarmonyOS Design', group: '系统设计规范', c: '#0A59F7', cd: '#084AB0', r: '12px', shape: 'pill', input: 'fill', card: 'shadow', d: 'n', note: '鸿蒙原生 · 一致而不同', end: '鸿蒙', widgets: ['tabbar', 'dialog', 'slider', 'progress', 'badge', 'banner'] },
  { id: 'material3', name: 'Material Design 3', group: '系统设计规范', c: '#6750A4', cd: '#524383', r: '16px', shape: 'pill', input: 'fill', card: 'tonal', d: 'n', note: '谷歌基线 · 动态色彩大圆角', end: 'Android', widgets: ['fab', 'navbar', 'banner', 'tabs', 'rate', 'segmented'] },
  { id: 'daisyui', name: 'daisyUI', group: 'Tailwind 系', c: '#570DF8', cd: '#4A0BD0', r: '8px', shape: 'round', input: 'border', card: 'border', d: 'n', note: 'Tailwind 多主题 · 圆润活泼', end: 'Web', widgets: ['navbar', 'tabs', 'badge', 'progress', 'banner', 'stepper'] },
  { id: 'flowbite', name: 'Flowbite', group: 'Tailwind 系', c: '#1C64F2', cd: '#1A56DB', r: '8px', shape: 'round', tbl: 'line', input: 'border', card: 'border', d: 'n', note: 'Tailwind 组件与文档', end: 'Web', widgets: ['navbar', 'table', 'pagination', 'badge', 'banner', 'timeline'] },
  { id: 'preline', name: 'Preline UI', group: 'Tailwind 系', c: '#16A34A', cd: '#15803D', r: '8px', shape: 'round', input: 'border', card: 'border', d: 'n', note: '绿色主色 · 开源交互插件', end: 'Web', widgets: ['navbar', 'tabs', 'slider', 'badge', 'progress', 'timeline'] },
];
const GROUP_ORDER = ['小程序生态', '移动 H5', 'PC / Web', '系统设计规范', 'Tailwind 系'];
const NOT_COLLECTED = 'Tremor / Atlassian Design System / Untitled UI —— 尚未实质采集（仅登记官网出处），采集后补入';

// ---------- 组件形态画法（按库参数定形：表格样式/密度/输入风格/按钮形状/列表内缩） ----------
const WIDGETS = {
  navbar: s => `<div class="w-nav"><b>标题</b><span>链接一</span><span>链接二</span></div>`,
  tabbar: s => `<div class="w-tabbar"><i class="on">●<em>首页</em></i><i>○<em>分类</em></i><i>○<em>我的</em></i></div>`,
  tabs: s => `<div class="w-tabs"><span class="on">标签一</span><span>标签二</span><span>标签三</span></div>`,
  cells: s => `<div class="w-cells${s.inset ? ' inset' : ''}"><div><b>列表项</b><i>›</i></div><div><b>列表项</b><i>›</i></div></div>`,
  dialog: s => `<div class="w-dialog"><b>对话框标题</b><p>说明文字，两行以内。</p><div class="act"><span>取消</span><span class="p">确定</span></div></div>`,
  toast: s => `<div class="w-toast">操作成功</div>`,
  badge: s => `<div class="w-badge"><span class="ic">✉<u>8</u></span><span class="ic">♪<u class="dot"></u></span></div>`,
  progress: s => `<div class="w-prog"><i style="width:64%"></i></div>`,
  slider: s => `<div class="w-slider"><i class="f" style="width:40%"></i><i class="k" style="left:40%"></i></div>`,
  rate: s => `<div class="w-rate">★★★★<span>★</span></div>`,
  stepper: s => `<div class="w-step"><span>−</span><b>1</b><span>＋</span></div>`,
  fab: s => `<div class="w-fab" style="border-radius:${s.shape === 'pill' ? '16px' : '50%'}">＋</div>`,
  table: s => {
    const cls = 'w-tbl' + (s.tbl === 'grid' ? ' grid' : '') + (s.tbl === 'zebra' ? ' zebra' : '') + (s.d === 'c' ? ' c' : '');
    return `<div class="${cls}"><div class="r h"><span>名称</span><span>状态</span><span>操作</span></div><div class="r"><span>示例数据</span><span class="p">启用</span><span>编辑</span></div><div class="r"><span>示例数据</span><span class="d">停用</span><span>编辑</span></div></div>`;
  },
  breadcrumb: s => `<div class="w-bc">首页 / 列表 / <b>详情</b></div>`,
  pagination: s => `<div class="w-pg"><span>‹</span><b>1</b><span>2</span><span>3</span><span>›</span></div>`,
  segmented: s => `<div class="w-seg"><b>选项一</b><span>选项二</span><span>选项三</span></div>`,
  banner: s => `<div class="w-banner">提示：这是一条通知信息</div>`,
  steps: s => `<div class="w-steps"><i class="on">1</i><i class="on">2</i><i>3</i></div>`,
  timeline: s => `<div class="w-tl"><div class="tli"><i class="on"></i><div><b>节点一</b><span>已完成说明</span></div></div><div class="tli"><i></i><div><b>节点二</b><span>待处理说明</span></div></div></div>`,
  tree: s => `<div class="w-tree"><div class="ti"><i class="ar">▾</i><i class="bx on"></i><span>一级节点</span></div><div class="ti sub"><i class="bx"></i><span>子节点</span></div><div class="ti sub"><i class="bx on"></i><span>子节点</span></div></div>`,
  actionbar: s => `<div class="w-actbar"><span class="ab2">收藏</span><span class="ab1">加入购物车</span></div>`,
  page: s => `<div class="w-page"><div class="wp-nav"><b>标题</b><u></u></div><div class="wp-cell"><span>列表项</span><i>›</i></div><div class="wp-cell"><span>列表项</span><i>›</i></div><div class="wp-btn" style="background:var(--pc);border-radius:var(--rr)"></div></div>`,
};
const WIDGET_LABELS = { navbar: '导航栏', tabbar: '底部标签栏', tabs: '页签', cells: '列表组', dialog: '对话框', toast: '轻提示', badge: '徽标', progress: '进度条', slider: '滑块', rate: '评分', stepper: '步进器', fab: '悬浮按钮', table: '表格', breadcrumb: '面包屑', pagination: '分页', segmented: '分段控制', banner: '通知条', steps: '步骤条', timeline: '时间线', tree: '树形选择', actionbar: '底部操作条', page: '页面组合片段' };
// 每组件规格说明（人话行 + CSS 片段；{r}=库圆角 {c}=库主色，按库参数替换）
const WIDGET_SPECS = {
  navbar: { ls: ['高度 40px · 底部 1px 分隔线', '标题 12px/600 · 链接 11px 灰'], css: '.nav{display:flex;align-items:center;gap:12px;height:40px;border-bottom:1px solid #E4E9EF}\n.nav b{font-size:12px;font-weight:600}' },
  tabbar: { ls: ['顶部 1px 分隔线', '图标 13px + 文字 9px · 选中态主色'], css: '.tabbar{display:flex;border-top:1px solid #E4E9EF}\n.tabbar .on{color:{c}}' },
  tabs: s => ({ ls: ['底部 2px 指示条（选中）', '文字 12px · 未选中灰'], css: '.tabs .on{color:{c};border-bottom:2px solid {c};font-weight:600}' }),
  cells: s => ({ ls: ['行高约 38px · 内边距 9×12', s.inset ? '分隔线左内缩 13px（不顶格）' : '分隔线通栏'], css: '.cell{display:flex;justify-content:space-between;padding:9px 12px;border-bottom:1px solid #F0F2F5}' }),
  dialog: { ls: ['宽度 ≤320px · 圆角 10px', '遮罩 rgba(0,0,0,.4) · 确认钮主色'], css: '.dialog{max-width:320px;border-radius:10px;padding:12px 14px;box-shadow:0 4px 14px rgba(0,0,0,.08)}' },
  toast: { ls: ['高约 32px · 圆角 8px', '深色底 82% · 白字 11.5px'], css: '.toast{background:rgba(30,36,48,.82);color:#fff;border-radius:8px;padding:7px 16px}' },
  badge: s => ({ ls: ['容器 30×30 · 角标红底白字 8.5px', '容器底主色 10% 透明档'], css: '.badge-ic{width:30px;height:30px;border-radius:8px;background:{c}1F}\n.badge-n{position:absolute;top:-5px;right:-5px;background:#F53F3F}' }),
  progress: { ls: ['轨道高 7px · 圆角 99px', '填充为主色 · 64% 示例'], css: '.progress{height:7px;border-radius:99px;background:#EEF1F5}\n.progress i{background:{c}}' },
  slider: { ls: ['轨道高 5px · 把手 15px', '已填充段主色'], css: '.slider-track{height:5px;border-radius:99px;background:#EEF1F5}\n.slider-fill{background:{c}}' },
  rate: { ls: ['星 16px · 间距 2px', '选中主色 · 未选浅灰'], css: '.rate{color:{c};letter-spacing:2px}' },
  stepper: s => ({ ls: ['高约 30px · 三段式 −/值/＋', '边框 1px · 中段左右分隔线'], css: '.stepper{border:1px solid #E4E8EE;border-radius:8px}\n.stepper span{color:{c}}' }),
  fab: s => ({ ls: ['44×44 · ' + (s.shape === 'pill' ? '圆角 16px' : '正圆'), '投影 0 4px 10px · 主色底白图标'], css: '.fab{width:44px;height:44px;background:{c};box-shadow:0 4px 10px rgba(0,0,0,.18)}' }),
  table: s => ({ ls: ['三列网格 · 行密度 ' + (s.d === 'c' ? '紧凑（行高约 24px）' : '标准（行高约 30px）'), '表格样式：' + (s.tbl === 'grid' ? '全边框' : s.tbl === 'zebra' ? '斑马纹' : '行分隔浅线')], css: 'table{border-collapse:collapse}\ntd{padding:' + (s.d === 'c' ? '4px' : '7px') + ' 10px;border-bottom:1px solid #F0F2F5' + (s.tbl === 'grid' ? ';border-right:1px solid #F0F2F5' : '') + '}' }),
  breadcrumb: { ls: ['字号 11.5px · 分隔符 /', '当前页主色加粗'], css: '.bc b{color:{c};font-weight:500}' },
  pagination: s => ({ ls: ['页码块 26×26 · 圆角 ' + s.r, '当前页主色底白字'], css: '.pg b{background:{c};color:#fff;border-color:{c}}' }),
  segmented: { ls: ['容器灰底 2px 内衬', '选中白底浮起 · 文字主色'], css: '.seg b{background:#fff;color:{c};box-shadow:0 1px 3px rgba(0,0,0,.1)}' },
  banner: s => ({ ls: ['内边距 8×12 · 圆角 8px', '底主色 10% 透明档 · 文字主色'], css: '.banner{background:{c}1F;color:{c}}' }),
  steps: { ls: ['节点 22px 圆形 · 连线 1.5px', '已完成主色填充白字'], css: '.steps i.on{background:{c};border-color:{c};color:#fff}' },
  timeline: s => ({ ls: ['节点 9px + 外环 3px 主色 10%', '标题 11.5px / 说明 10px'], css: '.tl i{background:{c};box-shadow:0 0 0 3px {c}1F}' }),
  tree: s => ({ ls: ['复选框 13px 圆角 3px', '子级缩进 22px · 选中主色底白勾'], css: '.tree .bx.on{background:{c};border-color:{c}}' }),
  actionbar: s => ({ ls: ['主按钮 flex:1 · 次按钮 flex:.55', '圆角跟随库 · 高约 32px'], css: '.actbar .ab1{background:{c};color:#fff}' }),
  page: s => ({ ls: ['导航 + 列表 + 主按钮组合片段', '用于看库的整体密度与气质'], css: '/* 组合片段：按库规格拼装 */' }),
};

// ---------- CSV 解析 ----------
function parseCsv(text) {
  const rows = []; let row = [], cell = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else inQ = false; }
      else cell += ch;
    } else {
      if (ch === '"') inQ = true;
      else if (ch === ',') { row.push(cell); cell = ''; }
      else if (ch === '\n') { row.push(cell); cell = ''; rows.push(row); row = []; }
      else if (ch !== '\r') cell += ch;
    }
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(c => String(c).trim() !== ''));
}
const csvData = text => { const rows = parseCsv(text); const head = (rows.shift() || []).map(h => h.trim()); return rows.map(r => { const o = {}; head.forEach((h, i) => o[h] = (r[i] ?? '').trim()); return o; }); };

// ---------- 轻量 Markdown 渲染（品牌 DESIGN.md 原文展示用） ----------
function md2html(md) {
  const inline = s => esc(s)
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\*\*([^*]+)\*\*/g, '<b>$1</b>')
    .replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (m, t, u) => /^https?:/i.test(u) ? '<a href="' + esc(u) + '" target="_blank" rel="noreferrer">' + t + '</a>' : t);
  const lines = String(md).replace(/\r\n/g, '\n').split('\n');
  let h = '', list = null, table = null, code = null;
  const closeList = () => { if (list) { h += '</' + list + '>'; list = null; } };
  const closeTable = () => { if (table) { h += '</tbody></table>'; table = null; } };
  for (const raw of lines) {
    const line = raw.trimEnd();
    if (code !== null) { if (/^```/.test(line.trim())) { h += '<pre class="code">' + esc(code) + '</pre>'; code = null; } else code += line + '\n'; continue; }
    if (/^```/.test(line.trim())) { closeList(); closeTable(); code = ''; continue; }
    if (/^\s*\|/.test(line)) {
      closeList();
      const cells = line.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      if (cells.every(c => /^:?-{2,}:?$/.test(c) || c === '')) continue;
      if (!table) { table = true; h += '<table class="tbl"><thead><tr>' + cells.map(c => '<th>' + inline(c) + '</th>').join('') + '</tr></thead><tbody>'; }
      else h += '<tr>' + cells.map(c => '<td>' + inline(c) + '</td>').join('') + '</tr>';
      continue;
    }
    closeTable();
    if (!line.trim()) { closeList(); continue; }
    const hm = line.match(/^(#{1,6})\s+(.*)$/);
    if (hm) { closeList(); const lv = Math.min(hm[1].length + 3, 6); h += '<h' + lv + '>' + inline(hm[2]) + '</h' + lv + '>'; continue; }
    const lm = line.match(/^\s*[-*+]\s+(.*)$/) || line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (lm) { const ord = /^\s*\d/.test(line) ? 'ol' : 'ul'; if (list !== ord) { closeList(); h += '<' + ord + '>'; list = ord; } h += '<li>' + inline(lm[1]) + '</li>'; continue; }
    closeList(); h += '<p>' + inline(line) + '</p>';
  }
  if (code !== null) h += '<pre class="code">' + esc(code) + '</pre>';
  closeList(); closeTable();
  return h;
}

// ---------- 页面壳（Tab 切换 + 筛选） ----------
const PAGE_CSS = `
*{box-sizing:border-box} body{font-family:'PingFang SC','Microsoft YaHei',sans-serif;background:#F3F5F8;margin:0;color:#20252C}
.top{background:#1E2430;color:#E8ECF2;padding:14px 24px;display:flex;align-items:center;gap:14px;flex-wrap:wrap}
.top b{font-size:15px}.top .desc{font-size:12px;opacity:.72}
.backlink{margin-left:auto;font-size:12px;color:#8FB7E8;text-decoration:none;border:1px solid rgba(143,183,232,.4);padding:5px 12px;border-radius:99px}
.backlink:hover{color:#fff;border-color:#8FB7E8}
.tabrow{background:#1E2430;display:flex;gap:5px;padding:8px 24px 0;flex-wrap:wrap}
.tabrow button{border:0;background:rgba(255,255,255,.08);padding:8px 17px;font-size:12.5px;cursor:pointer;color:#B9C2CE;border-radius:9px 9px 0 0}
.tabrow button.on{background:#F3F5F8;color:#20252C;font-weight:600}
.toolbar{position:sticky;top:0;z-index:9;background:rgba(243,245,248,.96);padding:12px 24px;border-bottom:1px solid #E4E8EE;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
.toolbar input{flex:1;min-width:220px;max-width:420px;border:1px solid #D6DCE4;border-radius:9px;padding:8px 14px;font-size:13px;outline:none;background:#fff}
.toolbar input:focus{border-color:#4C8DFF}
.toolbar .cnt{font-size:12px;color:#7A828E}
main{padding:18px 24px 60px;max-width:1280px;margin:0 auto}
.grp{margin:26px 0 10px;display:flex;align-items:baseline;gap:10px}
.grp h2{font-size:15px;margin:0}.grp .gc{font-size:11px;color:#979CA5}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(340px,1fr));gap:14px}
.noting{font-size:11.5px;color:#979CA5;margin-top:8px}
/* 落地页结构缩略 */
.ls{display:flex;flex-direction:column;gap:4px;margin:9px 0 2px}
.ls-row{display:flex;gap:8px;align-items:flex-start}
.ls-n{width:42px;flex-shrink:0;font-size:9.5px;font-weight:600;color:#7A828E;text-align:right;line-height:1.4;padding-top:2px}
.ls-a{flex:1;min-width:0}
/* 品牌设计语言折叠卡 */
.dcard{background:#fff;border-radius:12px;border:1px solid #EAEDF2;box-shadow:0 2px 8px rgba(20,40,80,.05);overflow:hidden}
.dcard summary{cursor:pointer;list-style:none;display:flex;align-items:center;gap:8px;padding:11px 14px;font-size:12.5px;flex-wrap:wrap}
.dcard summary::-webkit-details-marker{display:none}
.dcard summary:hover{background:#F7F9FC}
.dcard summary:after{content:'展开 ▾';margin-left:auto;font-size:10px;color:#979CA5;flex-shrink:0}
.dcard[open] summary:after{content:'收起 ▴'}
.dcard .dsum{width:100%;padding:0;font-size:10.5px;color:#7A828E;line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;font-weight:400}
.dcard .libbadge{font-size:10px;background:#6E56CF;color:#fff;border-radius:99px;padding:2px 9px;flex-shrink:0;max-width:150px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.dcard .comp{font-weight:600;color:#20252C;word-break:break-all}
.dcard .fsize{font-size:9.5px;color:#B8BDC4;margin-left:2px;flex-shrink:0}
.dcard .sws{margin:0 0 0 auto;padding-right:10px}
.dcard .sw i{width:16px;height:16px;border-radius:4px}
.dcard .sw s{display:none}
.dbody{border-top:1px solid #F0F2F5;padding:12px 16px;font-size:12px;line-height:1.7;color:#3C4650;max-height:480px;overflow:auto}
.dbody h4,.dbody h5,.dbody h6{margin:14px 0 6px;color:#20252C}
.dbody h4{font-size:13.5px}.dbody h5{font-size:12.5px}.dbody h6{font-size:12px;color:#5B6470}
.dbody p{margin:6px 0}.dbody ul,.dbody ol{margin:6px 0;padding-left:20px}.dbody li{margin:3px 0}
.dbody code{background:#F0F3F7;border-radius:4px;padding:1px 5px;font-size:11px;font-family:Consolas,monospace;color:#1B66C9}
.dbody pre.code{background:#1E2430;color:#D7E3F4;border-radius:9px;padding:11px 13px;font-size:11px;overflow:auto;font-family:Consolas,monospace;line-height:1.55}
.dbody a{color:#1B66C9}
.stylecard{background:#fff;border-radius:14px;border:1px solid #EAEDF2;box-shadow:0 2px 8px rgba(20,40,80,.06);padding:16px 18px;overflow:hidden}
.schead{display:flex;align-items:center;gap:8px;margin-bottom:4px}
.schead .libname{font-size:14.5px;font-weight:700;color:#20252C}
.schead .endtag{font-size:10px;background:#F0F2F5;color:#7A828E;padding:2px 9px;border-radius:99px}
.schead .dot{width:11px;height:11px;border-radius:99px;flex-shrink:0}
.snote{font-size:11.5px;color:#7A828E;margin:2px 0 12px}
.sd{--pd:var(--pc);border:1px solid #EEF1F5;border-radius:12px;padding:14px 16px;background:#FCFDFE}
.sd-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.sd-row+.sd-row{margin-top:10px}
.sd-btn{display:inline-flex;align-items:center;justify-content:center;background:var(--pc);color:#fff;border-radius:var(--rr);padding:7px 18px;font-size:12.5px;font-weight:600;line-height:1}
.sd-btn:hover{background:var(--pd)}
.sd-btn2{display:inline-flex;align-items:center;justify-content:center;color:var(--pc);border:1.5px solid var(--pc);border-radius:var(--rr);padding:5.5px 16px;font-size:12.5px;font-weight:500;line-height:1;background:#fff}
.sd-chip{display:inline-flex;align-items:center;background:var(--pt);color:var(--pc);border-radius:var(--rr);padding:3.5px 11px;font-size:11px;font-weight:600}
.sd-input{flex:1;min-width:120px;display:inline-flex;align-items:center;height:32px;border:1px solid #D0D5DD;border-radius:var(--rr);background:#fff;padding:0 11px;font-size:12px;color:#98A2B3}
.sd-switch{width:40px;height:22px;border-radius:99px;background:var(--pc);position:relative;flex-shrink:0}
.sd-switch i{position:absolute;right:3px;top:3px;width:16px;height:16px;border-radius:99px;background:#fff;box-shadow:0 1px 3px rgba(0,0,0,.25)}
.sd-check{width:18px;height:18px;border-radius:var(--cr,4px);background:var(--pc);color:#fff;display:inline-flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0}
.sd-radio{width:18px;height:18px;border-radius:99px;border:5px solid var(--pc);background:#fff;flex-shrink:0}
.sd-card{flex:1;min-width:150px;display:flex;gap:9px;align-items:center;background:#fff;border:1px solid #E7EAF0;border-radius:calc(var(--rr) + 2px);padding:10px 12px;box-shadow:0 1px 4px rgba(20,40,80,.06)}
.sd-card .ic{width:32px;height:32px;border-radius:calc(var(--rr) - 1px);background:var(--pt);color:var(--pc);display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:700;flex-shrink:0}
.sd-card .tx{font-size:10.5px;color:#8A93A0;line-height:1.45}
.sd-card .tx b{display:block;font-size:11.5px;color:#20252C}
.sd-lab{font-size:10px;color:#B8BDC4;margin:12px 0 5px}
/* 各库代表组件画法 */
.w-nav{display:flex;align-items:center;gap:12px;border-bottom:1px solid #EDF0F4;font-size:12px;padding:7px 2px}
.w-nav b{color:#20252C;flex-shrink:0}.w-nav span{color:#8A93A0;font-size:11px}
.w-tabbar{display:flex;border-top:1px solid #EDF0F4;padding-top:6px}
.w-tabbar i{flex:1;text-align:center;font-style:normal;font-size:13px;color:#9AA3AE;display:flex;flex-direction:column;align-items:center;gap:1px}
.w-tabbar em{font-style:normal;font-size:9px}.w-tabbar i.on{color:var(--pc)}
.w-tabs{display:flex;gap:16px;border-bottom:2px solid #F0F2F5;font-size:12px}
.w-tabs span{padding:6px 0;color:#8A93A0}
.w-tabs .on{color:var(--pc);border-bottom:2px solid var(--pc);margin-bottom:-2px;font-weight:600}
.w-cells{background:#fff;border:1px solid #EDF0F4;border-radius:8px;overflow:hidden}
.w-cells>div{display:flex;justify-content:space-between;align-items:center;padding:9px 12px;font-size:12px;color:#20252C;border-bottom:1px solid #F4F6F9}
.w-cells>div:last-child{border-bottom:0}
.w-cells i{color:#C2C9D2;font-style:normal}
.w-dialog{border:1px solid #E7EAF0;border-radius:10px;padding:12px 14px;max-width:240px;background:#fff;box-shadow:0 4px 14px rgba(0,0,0,.08)}
.w-dialog b{font-size:12.5px;color:#20252C}
.w-dialog p{font-size:11px;color:#7A828E;margin:6px 0 10px;line-height:1.5}
.w-dialog .act{display:flex;justify-content:flex-end;gap:14px;font-size:12px;color:#8A93A0}
.w-dialog .act .p{color:var(--pc);font-weight:600}
.w-toast{display:inline-block;background:rgba(30,36,48,.82);color:#fff;font-size:11.5px;padding:7px 16px;border-radius:8px}
.w-badge .ic{position:relative;display:inline-flex;width:30px;height:30px;border-radius:8px;background:var(--pt);color:var(--pc);align-items:center;justify-content:center;font-size:13px;margin-right:10px}
.w-badge u{position:absolute;top:-5px;right:-5px;background:#F53F3F;color:#fff;font-size:8.5px;border-radius:99px;padding:1px 4px;text-decoration:none;line-height:1.3}
.w-badge u.dot{width:8px;height:8px;padding:0}
.w-prog{height:7px;background:#EEF1F5;border-radius:99px;overflow:hidden}
.w-prog i{display:block;height:100%;background:var(--pc);border-radius:99px}
.w-slider{position:relative;height:5px;background:#EEF1F5;border-radius:99px;margin:9px 0}
.w-slider .f{position:absolute;left:0;top:0;height:100%;background:var(--pc);border-radius:99px}
.w-slider .k{position:absolute;top:50%;transform:translate(-50%,-50%);width:15px;height:15px;border-radius:99px;background:var(--pc);box-shadow:0 1px 3px rgba(0,0,0,.25)}
.w-rate{color:var(--pc);font-size:16px;letter-spacing:2px}
.w-rate span{color:#D9DEE6}
.w-step{display:inline-flex;align-items:center;border:1px solid #E4E8EE;border-radius:8px;overflow:hidden;font-size:12px;background:#fff}
.w-step span{padding:5px 11px;color:var(--pc)}
.w-step b{padding:5px 13px;border-left:1px solid #EEF1F5;border-right:1px solid #EEF1F5;color:#20252C}
.w-fab{width:44px;height:44px;background:var(--pc);color:#fff;display:flex;align-items:center;justify-content:center;font-size:19px;box-shadow:0 4px 10px rgba(0,0,0,.18)}
.w-tbl{border:1px solid #E7EAF0;border-radius:8px;overflow:hidden;font-size:11px;background:#fff}
.w-tbl .r{display:grid;grid-template-columns:1.4fr 1fr 1fr;padding:7px 10px;border-bottom:1px solid #F4F6F9;color:#3C4650}
.w-tbl .r:last-child{border-bottom:0}
.w-tbl .r.h{background:#F7F9FC;color:#8A93A0;font-weight:600;font-size:10.5px}
.w-tbl .p{color:var(--pc)}.w-tbl .d{color:#B85C5C}
.w-bc{font-size:11.5px;color:#98A2B3}
.w-bc b{color:var(--pc);font-weight:500}
.w-pg{display:inline-flex;gap:6px;font-size:12px;align-items:center}
.w-pg span,.w-pg b{width:26px;height:26px;display:inline-flex;align-items:center;justify-content:center;border:1px solid #E4E8EE;border-radius:6px;color:#5B6470;background:#fff}
.w-pg b{background:var(--pc);color:#fff;border-color:var(--pc);font-weight:600}
.w-seg{display:inline-flex;background:#EEF1F5;border-radius:9px;padding:2px;font-size:11.5px}
.w-seg span{padding:4px 13px;color:#5B6470;border-radius:7px}
.w-seg b{padding:4px 13px;background:#fff;border-radius:7px;color:var(--pc);font-weight:600;box-shadow:0 1px 3px rgba(0,0,0,.1)}
.w-banner{background:var(--pt);color:var(--pc);font-size:11.5px;padding:8px 12px;border-radius:8px}
.w-steps{display:flex;align-items:center;font-size:11px}
.w-steps i{width:22px;height:22px;border-radius:99px;border:1.5px solid #D6DCE4;color:#98A2B3;display:flex;align-items:center;justify-content:center;font-style:normal;background:#fff;flex-shrink:0}
.w-steps i.on{border-color:var(--pc);background:var(--pc);color:#fff}
.w-steps i:not(:last-child)::after{content:'';width:22px;height:1.5px;background:#D6DCE4;margin:0 4px}
/* 表格样式变体与密度 */
.w-tbl .r{align-items:center}
.w-tbl.grid .r span{border-right:1px solid #EEF1F5;padding-right:8px}
.w-tbl.grid .r span:last-child{border-right:0}
.w-tbl.zebra .r:nth-child(odd):not(.h){background:#FAFBFD}
.w-tbl.c .r{padding:4px 10px}
.w-tbl.c .r.h{padding:5px 10px}
/* 列表分隔线内缩（iOS 风格） */
.w-cells.inset>div{position:relative;border-bottom:0}
.w-cells.inset>div:not(:last-child)::before{content:'';position:absolute;left:13px;right:0;bottom:0;border-bottom:1px solid #F4F6F9}
/* 灰底无边框输入 */
.sd-input.fill{background:#EEF1F5;border-color:transparent}
/* 新增画法：时间线 / 树形 / 操作条 / 页面组合片段 */
.w-tl .tli{display:flex;gap:9px}
.w-tl .tli i{width:9px;height:9px;border-radius:99px;background:var(--pc);margin-top:4px;flex-shrink:0;box-shadow:0 0 0 3px var(--pt)}
.w-tl .tli i:not(.on){background:#D6DCE4;box-shadow:none}
.w-tl .tli div b{font-size:11.5px;display:block;color:#20252C}
.w-tl .tli div span{font-size:10px;color:#8A93A0}
.w-tree .ti{display:flex;gap:6px;align-items:center;font-size:11.5px;padding:3px 0;color:#3C4650}
.w-tree .ti.sub{padding-left:22px}
.w-tree .ti .ar{font-style:normal;font-size:9px;color:#8A93A0;width:10px}
.w-tree .ti .bx{width:13px;height:13px;border:1.5px solid #C9D1DC;border-radius:3px;position:relative;flex-shrink:0}
.w-tree .ti .bx.on{background:var(--pc);border-color:var(--pc)}
.w-tree .ti .bx.on::after{content:'✓';position:absolute;inset:0;color:#fff;font-size:9px;display:flex;align-items:center;justify-content:center}
.w-actbar{display:flex;gap:8px}
.w-actbar .ab1{flex:1;text-align:center;background:var(--pc);color:#fff;font-size:12px;font-weight:600;border-radius:var(--rr);padding:8px}
.w-actbar .ab2{flex:.55;text-align:center;background:#fff;border:1.5px solid var(--pc);color:var(--pc);font-size:12px;border-radius:var(--rr);padding:7px}
.w-page{border:1px solid #E7EAF0;border-radius:10px;overflow:hidden;background:#fff}
.w-page .wp-nav{display:flex;justify-content:space-between;align-items:center;padding:7px 10px;border-bottom:1px solid #F0F2F5;font-size:11.5px;font-weight:600;color:#20252C}
.w-page .wp-nav u{width:26px;height:6px;background:#E3EBF7;border-radius:99px}
.w-page .wp-cell{display:flex;justify-content:space-between;padding:8px 10px;font-size:11px;border-bottom:1px solid #F7F9FB;color:#3C4650}
.w-page .wp-cell i{font-style:normal;color:#C2C9D2}
.w-page .wp-btn{margin:8px 10px 10px;height:20px}
.snap{margin-top:11px;font-size:10px;color:#B8BDC4;border-top:1px dashed #EEF1F5;padding-top:8px}
/* 组件页全宽卡 + 组件规格浮层 */
.grid.wide{display:flex;flex-direction:column;gap:18px}
.sd2{display:grid;grid-template-columns:1fr 1fr;gap:6px 20px;align-items:start}
@media(max-width:960px){.sd2{grid-template-columns:1fr}}
.wspec{position:relative;min-width:0;padding:5px 8px;margin:0 -8px;border-radius:8px}
.wspec:hover{background:#F5F9FF;outline:1px dashed #B9D3F5;outline-offset:-1px}
.wspec .sd-lab{margin:0 0 5px}
.wspec .pop{display:none;position:absolute;z-index:8;left:8px;top:calc(100% + 2px);width:330px;background:#1E2430;color:#D7E3F4;border-radius:9px;padding:10px 12px;font-size:11px;line-height:1.6;box-shadow:0 8px 24px rgba(0,0,0,.3);text-align:left}
.wspec:hover .pop{display:block}
.wspec .pop b{display:block;color:#8FB7E8;font-size:10px;letter-spacing:.08em;margin-bottom:4px}
.wspec .pop pre{margin:6px 0 0;background:#141922;border-radius:6px;padding:7px 9px;font-size:10px;font-family:Consolas,monospace;white-space:pre-wrap;word-break:break-word;color:#A8E0A8}
/* 原始图标库 */
.ilib-note{font-size:11px;color:#979CA5;background:#F7F9FB;border-radius:6px;padding:6px 10px;margin:4px 0 2px}
.iwall{display:flex;flex-wrap:wrap;gap:6px}
.ig{width:64px;padding:8px 4px 4px;background:#fff;border:1px solid #EDF0F4;border-radius:8px;display:flex;flex-direction:column;align-items:center;gap:3px}
.ig svg{width:22px;height:22px}
.ig u{font-size:8px;color:#979CA5;text-decoration:none;max-width:56px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.ig:hover{border-color:#4C8DFF;background:#F5F9FF}
.mini{background:#fff;border-radius:12px;border:1px solid #EAEDF2;box-shadow:0 2px 8px rgba(20,40,80,.05);padding:14px 16px;overflow:hidden}
.mini .mt{font-size:13.5px;font-weight:600;margin-bottom:2px;word-break:break-all}
.mini .mk{font-size:10.5px;color:#979CA5;margin-bottom:8px;word-break:break-all}
.tag{display:inline-block;font-size:10px;background:#F0F2F5;color:#7A828E;padding:2px 8px;border-radius:99px;margin:0 6px 4px 0}
.fld{font-size:11.5px;color:#5B6470;margin:5px 0;line-height:1.55}
.fld b{color:#3C4650;margin-right:5px;font-size:10.5px}
.fld .no{color:#B85C5C}
.fld2{margin:8px 0}
.fld2 b{display:block;font-size:10px;color:#8A93A0;font-weight:600;margin-bottom:2px}
.fld2 span{font-size:11.5px;color:#3C4650;line-height:1.55;display:block}
.sws{display:flex;gap:6px;margin:9px 0 4px;flex-wrap:wrap}
.sw{text-align:center}
.sw i{display:block;width:34px;height:34px;border-radius:8px;border:1px solid rgba(0,0,0,.08)}
.sw s{display:block;text-decoration:none;font-size:8.5px;color:#8A93A0;margin-top:3px;font-family:Consolas,monospace;max-width:44px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.tfhead{font-size:17px;font-weight:700}.tfbody{font-size:13px;color:#4A5560;margin-top:3px}
`;
const pageShell = (title, desc, tabsHtml, body) => `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>${esc(title)}</title><style>${PAGE_CSS}</style></head><body>
<div class="top"><b>${esc(title)}</b><span class="desc">${desc}</span><a class="backlink" href="./workbench.html">← 返回工作台</a></div>
<div class="tabrow" id="tabrow"><button class="on" data-sec="all">全部</button>${tabsHtml}</div>
<div class="toolbar"><input id="q" type="text" placeholder="筛选：输入关键词…"><span class="cnt">显示 <b id="cnt">-</b> 项</span></div>
<main>${body}</main>
<script>
(function(){
  var q=document.getElementById('q'),cnt=document.getElementById('cnt');
  var cards=[].slice.call(document.querySelectorAll('[data-card]'));
  var cur='all';
  function run(){
    var v=q.value.trim().toLowerCase(),n=0;
    cards.forEach(function(c){
      var sec=c.closest('.sec');
      var secOk=cur==='all'||(sec&&sec.dataset.sec===cur);
      var hit=secOk&&(!v||c.textContent.toLowerCase().indexOf(v)>=0);
      c.style.display=hit?'':'none'; if(hit)n++;
    });
    document.querySelectorAll('.sec').forEach(function(s){
      s.style.display=(cur==='all'||s.dataset.sec===cur)?'':'none';
    });
    cnt.textContent=n;
  }
  document.querySelectorAll('#tabrow button').forEach(function(b){
    b.addEventListener('click',function(){
      cur=b.dataset.sec;
      document.querySelectorAll('#tabrow button').forEach(function(x){x.classList.toggle('on',x===b);});
      run();
    });
  });
  q.addEventListener('input',run); run();
})();
</script></body></html>`;

// ---------- ① 原始组件库规范：每库一张真实视觉样张卡 ----------
function buildComponentsPage(skillRoot) {
  // 各库快照文档计数（对齐 data/component-styles 实际目录）
  const snapCounts = {};
  const csDir = path.join(skillRoot, 'data', 'component-styles');
  if (fs.existsSync(csDir)) {
    for (const d of fs.readdirSync(csDir)) {
      const dp = path.join(csDir, d);
      if (fs.statSync(dp).isDirectory()) snapCounts[d] = fs.readdirSync(dp).filter(f => f.toLowerCase().endsWith('.md') && f.toLowerCase() !== '_meta.md').length;
    }
  }
  const tabs = GROUP_ORDER.map((g, i) => {
    const n = STYLES.filter(s => s.group === g).length;
    return '<button data-sec="g' + i + '">' + esc(g) + ' · ' + n + '</button>';
  }).join('');
  let body = '';
  GROUP_ORDER.forEach((g) => {
    const libs = STYLES.filter(s => s.group === g); if (!libs.length) return;
    body += '<div class="sec" data-sec="g' + GROUP_ORDER.indexOf(g) + '"><div class="grp"><h2>' + esc(g) + '</h2><span class="gc">' + libs.length + ' 个库 · 全宽卡往下铺 · 每个组件悬停可看规格与 CSS</span></div><div class="grid wide">';
    for (const s of libs) {
      const btnR = s.shape === 'pill' ? '999px' : s.r;
      const vars = 'style="--pc:' + s.c + ';--pd:' + s.cd + ';--pt:' + s.c + '1F;--rr:' + btnR + ';--cr:' + (s.shape === 'sharp' ? '0px' : '4px') + '"';
      const inp = s.input === 'fill' ? '<span class="sd-input fill" style="flex:1.2">请输入内容…</span>' : '<span class="sd-input" style="flex:1.2">请输入内容…</span>';
      const baseHtml =
        '<div class="sd-row"><span class="sd-btn">主要按钮</span><span class="sd-btn2">次要按钮</span><span class="sd-chip">标签</span>' + inp + '</div>' +
        '<div class="sd-row" style="margin-top:10px"><span class="sd-check">✓</span><span class="sd-radio"></span><span class="sd-switch"><i></i></span></div>';
      const popHtml = (k) => {
        const def = WIDGET_SPECS[k]; if (!def) return '';
        const spec = typeof def === 'function' ? def(s) : def;
        const css = spec.css.replace(/\{r\}/g, s.r).replace(/\{c\}/g, s.c);
        return '<div class="pop"><b>规格说明 · ' + esc(WIDGET_LABELS[k] || k) + '</b>' + spec.ls.map(l => '<div>· ' + esc(l) + '</div>').join('') + '<pre>' + esc(css) + '</pre></div>';
      };
      const wHtml = (s.widgets || []).map(k => {
        const fn = WIDGETS[k]; if (!fn) return '';
        return '<div class="wspec"><div class="sd-lab" style="margin:0 0 5px">' + esc(WIDGET_LABELS[k] || k) + '</div>' + fn(s) + popHtml(k) + '</div>';
      }).join('');
      const snap = snapCounts[s.id] || 0;
      body += '<div class="stylecard" data-card>' +
        '<div class="schead"><span class="dot" style="background:' + s.c + '"></span><span class="libname">' + esc(s.name) + '</span><span class="endtag">' + esc(s.end) + '</span></div>' +
        '<div class="snote">' + esc(s.note) + ' · 主色 <span style="font-family:Consolas,monospace">' + s.c + '</span> · 圆角 ' + esc(s.r) + (s.tbl ? ' · 表格 ' + (s.tbl === 'grid' ? '全边框' : '行分隔') : '') + (s.d === 'c' ? ' · 紧凑密度' : '') + (s.input === 'fill' ? ' · 灰底输入' : '') + '</div>' +
        '<div class="sd sd2" ' + vars + '>' + baseHtml + wHtml + '</div>' +
        '<div class="snap">本库快照 ' + snap + ' 个组件文档 · 详细规范见 data/component-styles/' + esc(s.id) + '/ · 组件规格悬停可见</div></div>';
    }
    body += '</div></div>';
  });
  body += '<div class="noting">' + esc(NOT_COLLECTED) + '</div>';
  return pageShell('原始组件库规范', STYLES.length + ' 个组件库 · 全宽样张卡往下铺 · 形态按各库官方规格 · 悬停组件看规格与 CSS', tabs, body);
}

// ---------- ② 原始参考令牌库（全可视化 + 中文） ----------
const SW_FIELDS = [['Primary (Hex)', '主色'], ['Secondary (Hex)', '次色'], ['CTA (Hex)', 'CTA'], ['Background (Hex)', '底色'], ['Text (Hex)', '文字'], ['Border (Hex)', '边框']];
function buildTokensPage(skillRoot) {
  const uDir = path.join(skillRoot, 'data', 'uupm', 'zh'); // 中文版参考数据（由 scripts/uupm-zh.mjs 从英文原版沉淀）
  let body = '';
  let total = 0;
  const TABS_TOKENS = [['sec-color', '色板'], ['sec-type', '字体搭配'], ['sec-style', '风格基调'], ['sec-chart', '图表'], ['sec-landing', '落地页'], ['sec-products', '产品类型'], ['sec-ux', '体验准则'], ['sec-prompts', '提示词'], ['sec-stack', '技术栈']];
  const sec = (id, title, note, cardsHtml, n) => '<div class="sec" data-sec="' + id + '"><div class="grp"><h2>' + esc(title) + '</h2><span class="gc">' + n + ' 项 · ' + esc(note) + '</span></div><div class="grid">' + cardsHtml + '</div></div>';

  if (fs.existsSync(uDir)) {
    // 色板
    const cp = path.join(uDir, 'colors.csv');
    if (fs.existsSync(cp)) {
      const rows = csvData(fs.readFileSync(cp, 'utf8')); total += rows.length;
      body += sec('sec-color', '色板方向', 'colors.csv', rows.map(r => {
        const sws = SW_FIELDS.map(([k]) => r[k] ? '<span class="sw"><i style="background:' + esc(r[k]) + '"></i><s>' + esc(r[k]) + '</s></span>' : '').join('');
        return '<div class="mini" data-card><div class="mt">' + esc(r['Product Type'] || '') + '</div><div class="mk">' + esc(r['Keywords'] || '') + '</div><div class="sws">' + sws + '</div><div class="fld">' + esc(r['Notes'] || '') + '</div></div>';
      }).join(''), rows.length);
    }
    // 字体搭配（中文开源组 + 西文开源组，全部标授权）
    const tp = path.join(uDir, 'typography.csv');
    const tc = path.join(uDir, 'typography-cn.csv');
    const cnRows = fs.existsSync(tc) ? csvData(fs.readFileSync(tc, 'utf8')) : [];
    const enRows = fs.existsSync(tp) ? csvData(fs.readFileSync(tp, 'utf8')) : [];
    if (enRows.length || cnRows.length) {
      total += enRows.length + cnRows.length;
      const fontCard = o => {
        const head = esc(o.head || ''), bod = esc(o.bod || '');
        const headFam = (o.head || '').replace(/'/g, ''), bodFam = (o.bod || '').replace(/'/g, '');
        let wrow = '';
        if (o.weights && o.weights.length) {
          const wname = { '100': '极细', '200': '特细', '300': '细体', '400': '常规', '500': '中等', '600': '半粗', '700': '粗体', '800': '特粗', '900': '黑体' };
          wrow = '<div class="fld" style="margin-top:9px"><b>字重</b></div><div style="display:flex;gap:12px;flex-wrap:wrap;align-items:baseline">' +
            o.weights.map(w => '<span style="font-weight:' + w + ';font-size:15px;color:#20252C">Aa<span style="font-size:9.5px;color:#8A93A0;margin-left:3px;font-weight:400">' + w + (wname[w] || '') + '</span></span>').join('') + '</div>';
        }
        const lic = o.lic ? esc(o.lic) : (o.enLic ? 'Google Fonts 开源 · 免费可商用' : '');
        return '<div class="mini" data-card><div class="mt">' + esc(o.name || '') + '<span class="tag" style="margin-left:6px">' + esc(o.cat || '') + '</span></div>' +
          '<div style="margin:8px 0"><span class="tfhead" style="font-family:\'' + headFam + '\',' + 'serif">' + head + '</span><span class="tag" style="margin-left:8px">标题</span></div>' +
          '<div><span class="tfbody" style="font-family:\'' + bodFam + '\',' + 'sans-serif">' + bod + '</span><span class="tag" style="margin-left:8px">正文</span></div>' +
          wrow +
          (o.mood ? '<div class="fld"><b>气质</b>' + esc(o.mood) + '</div>' : '') +
          (o.best ? '<div class="fld"><b>适用</b>' + esc(o.best) + '</div>' : '') +
          (lic ? '<div style="margin-top:8px"><span class="tag" style="background:#E6F7EE;color:#16803C">✓ ' + lic + '</span></div>' : '') +
          (o.note ? '<div class="fld">' + esc(o.note) + '</div>' : '') +
          '</div>';
      };
      const cnCards = cnRows.map(r => fontCard({ name: r['Font Pairing Name'], cat: r['Category'], head: r['Heading Font'], bod: r['Body Font'], mood: r['Mood/Style Keywords'], best: r['Best For'], lic: r['License'], note: r['Notes'] })).join('');
      const enCards = enRows.map(r => {
        const url = r['Google Fonts URL'] || '';
        const weights = [...new Set([...url.matchAll(/:wght@([0-9;]+)/g)].flatMap(m => m[1].split(';')))].filter(Boolean).sort((a, b) => a - b);
        return fontCard({ name: r['Font Pairing Name'], cat: r['Category'], head: r['Heading Font'], bod: r['Body Font'], mood: r['Mood/Style Keywords'], best: r['Best For'], enLic: true, weights });
      }).join('');
      body += sec('sec-type', '字体搭配', '中文开源 ' + cnRows.length + ' 组 + 西文开源 ' + enRows.length + ' 组 · 全部免费可商用 · 含字重档（字号档这批参考数据源未收录）', cnCards + enCards, enRows.length + cnRows.length);
    }
    // 风格基调
    const sp = path.join(uDir, 'styles.csv');
    if (fs.existsSync(sp)) {
      const rows = csvData(fs.readFileSync(sp, 'utf8')); total += rows.length;
      body += sec('sec-style', '风格基调', 'styles.csv · 关键词与效果已 tag 化 · 适用/勿用双栏对照', rows.map(r => {
        const tags = (r['Keywords'] || '').split(/[,，]/).map(x => x.trim()).filter(Boolean);
        const fx = (r['Effects & Animation'] || '').split(/[,，/]/).map(x => x.trim()).filter(Boolean).slice(0, 4);
        return '<div class="mini" data-card><div class="mt">' + esc(r['Style Category'] || '') + '<span class="tag" style="margin-left:6px">' + esc(r['Type'] || '') + '</span></div>' +
          (tags.length ? '<div style="margin:7px 0 2px">' + tags.map(t => '<span class="tag">' + esc(t) + '</span>').join('') + '</div>' : '') +
          '<div class="fld"><b>主色系</b>' + esc(r['Primary Colors'] || '') + '</div>' +
          '<div class="fld"><b>辅色系</b>' + esc(r['Secondary Colors'] || '') + '</div>' +
          (fx.length ? '<div style="margin:8px 0 2px">' + fx.map(t => '<span class="tag" style="background:#E8F1FF;color:#1B66C9">' + esc(t) + '</span>').join('') + '</div>' : '') +
          '<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:10px">' +
          '<div style="background:#F2F9F4;border-radius:8px;padding:8px 10px"><div style="font-size:10px;color:#16803C;font-weight:600;margin-bottom:3px">✓ 适用</div><div style="font-size:11px;color:#3C4650;line-height:1.5">' + esc(r['Best For'] || '') + '</div></div>' +
          '<div style="background:#FDF3F3;border-radius:8px;padding:8px 10px"><div style="font-size:10px;color:#B85C5C;font-weight:600;margin-bottom:3px">✕ 勿用</div><div style="font-size:11px;color:#3C4650;line-height:1.5">' + esc(r['Do Not Use For'] || '') + '</div></div>' +
          '</div></div>';
      }).join(''), rows.length);
    }
    // 图表（可视化）
    const hp = path.join(uDir, 'charts.csv');
    if (fs.existsSync(hp)) {
      const rows = csvData(fs.readFileSync(hp, 'utf8')); total += rows.length;
      body += sec('sec-chart', '图表选型', 'charts.csv · 卡上图形即该图表类型的示意', rows.map(r => {
        const best = r['Best Chart Type'] || '';
        const svg = chartSvg(best);
        return '<div class="mini" data-card><div style="display:flex;gap:10px;align-items:flex-start"><div style="flex:1;min-width:0">' +
          '<div class="mt">' + esc(r['Data Type'] || '') + '</div><div class="mk">' + esc(r['Keywords'] || '') + '</div>' +
          '<div class="fld"><b>首选</b>' + esc(best) + '</div>' +
          '<div class="fld"><b>备选</b>' + esc(r['Secondary Options'] || '') + '</div></div>' + svg + '</div>' +
          '<div class="fld"><b>用色</b>' + esc(r['Color Guidance'] || '') + '</div></div>';
      }).join(''), rows.length);
    }
    // 落地页（结构缩略可视化）
    const lp = path.join(uDir, 'landing.csv');
    if (fs.existsSync(lp)) {
      const rows = csvData(fs.readFileSync(lp, 'utf8')); total += rows.length;
      body += sec('sec-landing', '落地页结构', 'landing.csv · 卡内为页面版式缩略（左标签=区块类型，右图形=该区块的真实版式）', rows.map(r => {
        const headKeys = Object.keys(r);
        const nameKey = headKeys.find(k => /pattern/i.test(k)) || headKeys[0];
        const orderKey = headKeys.find(k => /section/i.test(k) || /order/i.test(k)) || headKeys[1];
        return '<div class="mini" data-card><div class="mt">' + esc(r[nameKey] || '') + '</div><div class="mk">' + esc(r['Keywords'] || '') + '</div>' +
          structStrip(r[orderKey]) + '</div>';
      }).join(''), rows.length);
    }
    // 其余参考表（通用键值卡 + 中文）
    // 产品类型（专用：推荐风格 tag + 色彩焦点色条 + 考量）
    const COLOR_HEX = [['信任蓝', '#2563EB'], ['品牌蓝', '#2563EB'], ['蓝', '#2563EB'], ['强调', '#F97316'], ['橙', '#F97316'], ['成功', '#16A34A'], ['绿', '#16A34A'], ['深', '#0F172A'], ['暗', '#0F172A'], ['白', '#FFFFFF'], ['中性', '#64748B'], ['灰', '#64748B'], ['高端', '#111827'], ['黑', '#111111'], ['金', '#CA8A04'], ['专业', '#1E40AF'], ['青', '#0D9488'], ['红', '#DC2626'], ['粉', '#EC4899'], ['紫', '#7C3AED'], ['黄', '#EAB308'], ['大地', '#92400E'], ['自然', '#4D7C0F'], ['鲜', '#E11D48'], ['暖', '#F59E0B'], ['冷', '#0284C7'], ['浅', '#F1F5F9']];
    const pp = path.join(uDir, 'products.zh.csv');
    if (fs.existsSync(pp)) {
      const rows = csvData(fs.readFileSync(pp, 'utf8')); total += rows.length;
      body += sec('sec-products', '产品类型', 'products 中文版 · 推荐风格与色彩焦点直接标在卡上', rows.map(r => {
        const rec = (r['推荐风格'] || '').split(/[+＋]/).map(x => x.trim()).filter(Boolean);
        const focus = r['色彩焦点'] || '';
        const sws = COLOR_HEX.filter(([w]) => focus.includes(w)).slice(0, 6).map(([w, hex]) => '<span class="sw"><i style="background:' + hex + '"></i><s>' + esc(w) + '</s></span>').join('');
        return '<div class="mini" data-card><div class="mt">' + esc(r['产品类型'] || '') + '</div><div class="mk">' + esc(r['关键词'] || '') + '</div>' +
          (rec.length ? '<div style="margin:7px 0 2px">' + rec.map(t => '<span class="tag" style="background:#E8F1FF;color:#1B66C9">' + esc(t) + '</span>').join('') + '<span class="tag">推荐风格</span></div>' : '') +
          (sws ? '<div style="margin:7px 0 2px"><div style="font-size:10px;color:#8A93A0;margin-bottom:4px">色彩焦点</div><div class="sws" style="margin:0">' + sws + '</div></div>' : '') +
          (r['关键考量'] ? '<div class="fld"><b>关键考量</b>' + esc(r['关键考量']) + '</div>' : '') +
          (r['落地页模式'] && r['落地页模式'] !== '——' ? '<div class="fld"><b>落地页模式</b>' + esc(r['落地页模式']) + '</div>' : '') +
          '</div>';
      }).join(''), rows.length);
    }
    // 其余参考表（块级键值卡）
    // 体验准则（中文句级翻译版 · 专用渲染）
    const ux = path.join(uDir, 'ux-guidelines.zh.csv');
    if (fs.existsSync(ux)) {
      const rows = csvData(fs.readFileSync(ux, 'utf8')); total += rows.length;
      body += sec('sec-ux', '体验准则', 'ux-guidelines 中文版 · 每条 = 类别 + 准则 + 应该/不该 + 严重度', rows.map(r => {
        const sev = r['严重度'] === '高' ? '#B85C5C' : (r['严重度'] === '中' ? '#B45309' : '#7A828E');
        return '<div class="mini" data-card>' +
          '<div style="display:flex;align-items:center;gap:6px;margin-bottom:5px"><span class="tag" style="background:#E8F1FF;color:#1B66C9">' + esc(r['类别'] || '') + '</span><b style="font-size:13px;color:#20252C">' + esc(r['标题'] || '') + '</b><span class="tag" style="margin-left:auto;background:' + sev + '22;color:' + sev + ';margin-right:0">' + esc(r['严重度'] || '') + '</span></div>' +
          (r['平台'] && r['平台'] !== '全部' ? '<div style="margin-bottom:5px"><span class="tag">' + esc(r['平台']) + '</span></div>' : '') +
          '<p style="font-size:11.5px;color:#5B6470;margin:0 0 8px;line-height:1.55">' + esc(r['说明'] || '') + '</p>' +
          '<div style="display:flex;flex-direction:column;gap:3px">' +
          '<div style="font-size:11.5px;line-height:1.5"><b style="color:#16803C;font-weight:600">✓ </b>' + esc(r['应该'] || '') + '</div>' +
          '<div style="font-size:11.5px;line-height:1.5"><b style="color:#B85C5C;font-weight:600">✕ </b>' + esc(r['不该'] || '') + '</div>' +
          '</div></div>';
      }).join(''), rows.length);
    }
    // 提示词（英文原文 · 复制即用 + 中文风格名与说明）
    const PR_ZH = {
      'Minimalism & Swiss Style': ['极简主义 & 瑞士风（Minimalism & Swiss）', '留白与网格说话，去除一切多余装饰'],
      'Neumorphism': ['新拟物（Neumorphism）', '同色系凸凹浮雕质感，柔和 3D'],
      'Glassmorphism': ['玻璃拟态（Glassmorphism）', '磨砂玻璃半透明层，背景透出模糊光'],
      'Brutalism': ['粗野主义（Brutalism）', '原始粗粝、直角硬边、高饱和撞色'],
      '3D & Hyperrealism': ['3D 超写实（Hyperrealism）', '真实纹理与光照的沉浸式三维界面'],
      'Vibrant & Block-based': ['活力块面（Bold & Block-based）', '大色块分区、大字号、几何图形'],
      'Dark Mode (OLED)': ['深色模式（Dark Mode OLED）', '纯黑底省电，霓虹点缀'],
      'Accessible & Ethical': ['无障碍 & 伦理（Accessible & Ethical）', 'WCAG AAA 高对比、全键盘可达'],
      'Claymorphism': ['陶土拟态（Claymorphism）', '厚边框圆角的玩具感 3D'],
      'Aurora UI': ['极光 UI（Aurora UI）', '北极光式网格渐变流动背景'],
      'Retro-Futurism': ['复古未来（Retro-Futurism）', '霓虹配色、深黑底、80 年代 CRT 质感'],
      'Flat Design': ['扁平设计（Flat Design）', '无阴影无渐变，只用色块与线条'],
      'Skeuomorphism': ['拟物（Skeuomorphism）', '拟真材质纹理与 3D 纵深'],
      'Liquid Glass': ['液态玻璃（Liquid Glass）', '形变液体玻璃与彩虹渐变'],
      'Motion-Driven': ['动效驱动（Motion-Driven）', '滚动触发、视差与微交互'],
      'Micro-interactions': ['微交互（Micro-interactions）', '50~100ms 小动效与触觉反馈'],
      'Inclusive Design': ['包容设计（Inclusive Design）', '全人群可用的无障碍设计'],
      'Zero Interface': ['零界面（Zero Interface）', '语音优先、极简可见 UI'],
      'Soft UI Evolution': ['柔和 UI（Soft UI Evolution）', '新拟物改良版，对比度达标'],
      'Bento Grids': ['便当格（Bento Grids）', '模块化大小卡片网格布局'],
      'Neubrutalism': ['新粗野主义（Neubrutalism）', '硬黑边框、硬阴影、亮色'],
      'HUD / Sci-Fi FUI': ['HUD 科幻（Sci-Fi FUI）', '细线、霓虹青蓝、数据可视化'],
      'Pixel Art': ['像素风（Pixel Art）', '8-bit 像素化复古游戏感'],
    };
    const pr = path.join(uDir, 'prompts.csv');
    if (fs.existsSync(pr)) {
      const rows = csvData(fs.readFileSync(pr, 'utf8')); total += rows.length;
      body += sec('sec-prompts', '风格生成提示词', 'prompts 原文 · 每卡 = 中文风格说明 + 可整段复制给 AI 的英文提示词', rows.map(r => {
        const zh = PR_ZH[r['Style Category']] || [r['Style Category'], ''];
        return '<div class="mini" data-card><div class="mt">' + esc(zh[0]) + '</div>' +
          (zh[1] ? '<p style="font-size:11.5px;color:#5B6470;margin:4px 0 8px;line-height:1.55">' + esc(zh[1]) + '</p>' : '') +
          (r['AI Prompt Keywords (Copy-Paste Ready)'] ? '<div style="font-size:10px;color:#8A93A0;margin-bottom:3px">AI 提示词（英文原文 · 复制即用）</div><pre style="background:#1E2430;color:#D7E3F4;border-radius:8px;padding:10px 12px;font-size:11px;line-height:1.6;white-space:pre-wrap;word-break:break-word;font-family:Consolas,monospace;margin:0">' + esc(r['AI Prompt Keywords (Copy-Paste Ready)']) + '</pre>' : '') +
          (r['CSS/Technical Keywords'] ? '<div class="fld2" style="margin-top:8px"><b>关键 CSS / 技术要点</b><span style="font-family:Consolas,monospace;font-size:10.5px">' + esc(r['CSS/Technical Keywords']) + '</span></div>' : '') +
          '</div>';
      }).join(''), rows.length);
    }
    // 技术栈节已移除：Tailwind z-index/transition 等前端实现细节对设计系统产出环节无价值（数据保留在 zh/stack-html-tailwind.csv 备查）
  }
  if (!total) body = '<div class="noting">暂无参考数据。</div>';
  const tabs = TABS_TOKENS.filter(([id]) => body.indexOf('data-sec="' + id + '"') >= 0).map(([id, label]) => '<button data-sec="' + id + '">' + esc(label) + '</button>').join('');
  return pageShell('原始参考令牌库', '外部设计参考数据快照 · 全可视化渲染 · 共 ' + total + ' 项', tabs, body);
}

// ---------- ③ 品牌设计语言（awesome-design-md · DESIGN.md 原文） ----------
function buildDesignMdsPage(skillRoot) {
  const dDir = path.join(skillRoot, 'data', 'design-mds');
  const metaPath = path.join(dDir, '_meta.json');
  let meta = { brands: {}, groups: [] };
  try { meta = JSON.parse(fs.readFileSync(metaPath, 'utf8')); } catch (e) { /* 无数据时走空态 */ }
  let descZh = {};
  try { descZh = JSON.parse(fs.readFileSync(path.join(dDir, '_desc.zh.json'), 'utf8')); } catch (e) { /* 中文摘要映射可选 */ }
  const brands = fs.existsSync(dDir) ? fs.readdirSync(dDir).filter(d => fs.statSync(path.join(dDir, d)).isDirectory() && fs.existsSync(path.join(dDir, d, 'DESIGN.md'))).sort() : [];
  const groups = new Map();
  for (const b of brands) {
    const info = meta.brands[b] || { zh: b, group: '其他' };
    if (!groups.has(info.group)) groups.set(info.group, []);
    groups.get(info.group).push({ id: b, ...info });
  }
  const baseGroups = (meta.groups && meta.groups.length ? meta.groups : [...groups.keys()]).filter(g => groups.has(g));
  const groupNames = baseGroups.concat([...groups.keys()].filter(g => !baseGroups.includes(g))); // 上游新落「其他」组等也兜底展示
  const tabs = groupNames.map((g, i) => '<button data-sec="d' + i + '">' + esc(g) + ' · ' + groups.get(g).length + '</button>').join('');
  let body = '';
  groupNames.forEach((g) => {
    const list = groups.get(g);
    body += '<div class="sec" data-sec="d' + groupNames.indexOf(g) + '"><div class="grp"><h2>' + esc(g) + '</h2><span class="gc">' + list.length + ' 个品牌 · 该品牌设计语言的结构化分析（色板/字阶/间距/组件特征），供 AI 起手参照</span></div><div class="grid">';
    for (const d of list) {
      const raw = fs.readFileSync(path.join(dDir, d.id, 'DESIGN.md'), 'utf8').replace(/^\uFEFF/, '');
      // front matter：色板一瞥 + 品牌摘要（不展开即知气质）
      let fmScope = raw, desc = '';
      const fm = raw.match(/^---\n([\s\S]*?)\n---/);
      if (fm) {
        fmScope = fm[1];
        const dm = fm[1].match(/description:[ \t]*\|?[ \t]*\n?([\s\S]*?)(?=\n[a-zA-Z][a-zA-Z-]*:[ \t]|$)/);
        if (dm) desc = dm[1].split('\n').map(x => x.trim()).filter(Boolean).join(' ');
      }
      if (!desc) { const dm2 = raw.replace(/^---[\s\S]*?---/, '').match(/^[^\n#]{50,}/m); if (dm2) desc = dm2[0]; }
      desc = desc.replace(/\s+/g, ' ').trim().slice(0, 130);
      const hexes = [...new Set((fmScope.match(/#[0-9a-fA-F]{6}\b/g) || []).map(x => x.toUpperCase()))].slice(0, 8);
      const sws = hexes.map(x => '<span class="sw"><i style="background:' + x + '"></i></span>').join('');
      const size = raw.length;
      const dsum = desc ? '<div class="dsum">' + esc(desc) + '…</div>' : '';
      // front matter（结构化规格 YAML）与正文分离：正文从分析内容开始，规格以等宽块置顶
      let fmBlock = '';
      let bodyMd = raw;
      const fmM = raw.match(/^---\n([\s\S]*?)\n---\n?/);
      if (fmM) { fmBlock = '<div style="font-size:10px;color:#8A93A0;margin-bottom:4px">结构化规格（YAML front matter）</div><pre class="code" style="max-height:220px">' + esc(fmM[1]) + '</pre>'; bodyMd = raw.slice(fmM[0].length); }
      const zhDesc = (descZh[d.id] || '').trim();
      const enDesc = desc.replace(/\s+/g, ' ').trim();
      const showDesc = zhDesc || enDesc.slice(0, 130);
      const tip = enDesc ? ' title="' + esc(enDesc.slice(0, 200)) + '"' : '';
      body += '<details class="dcard" data-card><summary' + tip + '><span class="libbadge">' + esc(d.zh) + '</span><span class="comp">' + esc(d.id) + '</span><span class="fsize">' + (size > 1024 ? (size / 1024).toFixed(1) + 'KB' : size + 'B') + '</span>' + (sws ? '<span class="sws">' + sws + '</span>' : '') + (showDesc ? '<span class="dsum">' + esc(showDesc) + (zhDesc ? '' : '…') + '</span>' : '') + '</summary><div class="dbody">' + fmBlock + md2html(bodyMd) + '</div></details>';
    }
    body += '</div></div>';
  });
  if (!brands.length) body = '<div class="noting">暂无品牌设计语言快照 —— 运行 scripts/fetch-design-mds.mjs 采集。</div>';
  else body += '<div class="noting">来源：github.com/VoltAgent/awesome-design-md（MIT）· 第三方设计语言分析稿，非官方完整规范 —— 组件 API/交互规则请以组件库文档为准。</div>';
  return pageShell('品牌设计语言', brands.length + ' 个知名产品设计系统的分析文档（DESIGN.md）· 第二步风格定义与第三步令牌的参照原料', tabs, body);
}

// ---------- ④ 原始图标库（data/icons-json 各库合并 JSON 图标墙） ----------
// 数据源：scripts/build-icons-json.mjs 把散装 SVG 合并成的每库一个 JSON（icons: 键→完整 SVG）
const ICON_LIB_ZH = { tabler: 'Tabler 图标', phosphor: 'Phosphor 图标', heroicons: 'HeroIcons', 'material-symbols': 'Material Symbols', bootstrap: 'Bootstrap 图标', remixicon: 'Remix 图标', feather: 'Feather', boxicons: 'Boxicons', solar: 'Solar 图标', lucide: 'Lucide' };
// SVG 消毒：外部库文件不可信任——剥离脚本/事件属性/javascript 链接/foreignObject 后再内联进页面
const sanitizeSvg = s => String(s)
  .replace(/<script[\s\S]*?<\/script\s*>/gi, '')
  .replace(/<script[^>]*\/?>/gi, '')
  .replace(/<foreignObject[\s\S]*?<\/foreignObject\s*>/gi, '')
  .replace(/\son[a-z]+\s*=\s*("[^"]*"|'[^']*'|[^\s>]+)/gi, '')
  .replace(/((x|xml)?link:)?href\s*=\s*("|')\s*javascript:[^"']*\3/gi, '');
function buildIconsPage(skillRoot) {
  const jDir = path.join(skillRoot, 'data', 'icons-json');
  const libs = fs.existsSync(jDir) ? fs.readdirSync(jDir).filter(f => f.endsWith('.json') && f !== '_index.json')
    .map(f => {
      try { return { file: f, doc: JSON.parse(fs.readFileSync(path.join(jDir, f), 'utf8')) }; } catch (e) { return null; }
    }).filter(Boolean)
    .sort((a, b) => a.file.localeCompare(b.file)) : [];
  const tabs = libs.map((l, i) => '<button data-sec="i' + i + '">' + esc(ICON_LIB_ZH[l.doc.name] || l.doc.name) + '</button>').join('');
  let body = '';
  let totalIcons = 0;
  libs.forEach(({ doc }, li) => {
    const entries = Object.keys(doc.icons || {});
    const formOf = k => (doc.iconForms && doc.iconForms[k]) || '';
    // 线性/面性分类：优先用 iconForms 变体键（fill/solid/bold…），退回键名命中 fill/solid（bootstrap *-fill 等平铺变体）
    const isFill = k => /fill|solid|bold/i.test(formOf(k)) || /(^|-)(fill|solid|filled|bxs)(-|$)/i.test(k);
    const line = entries.filter(k => !isFill(k));
    const fill = entries.filter(isFill);
    const pick = (arr, n) => { if (arr.length <= n) return arr; const step = Math.ceil(arr.length / n); const out = []; for (let i = 0; i < arr.length && out.length < n; i += step) out.push(arr[i]); return out; };
    const titleOf = k => k.replace(/-(outline|solid|filled|bold|linear|regular)(-\d+)?$/, '').replace(/(^|-)(fill)(-|$)/g, '$1$3');
    const wall = arr => arr.map(k => {
      const svg = sanitizeSvg(doc.icons[k]);
      const name = titleOf(k);
      return '<span class="ig" data-card data-n="' + esc(k) + '" title="' + esc(name) + '">' + svg + '<u>' + esc(name) + '</u></span>';
    }).join('');
    const lineWall = wall(pick(line, 90));
    const fillWall = fill.length ? '<div class="sd-lab" style="margin-top:10px">面性 / Solid · 抽样 ' + Math.min(fill.length, 90) + ' / ' + fill.length + '</div><div class="iwall">' + wall(pick(fill, 90)) + '</div>' : '';
    const forms = doc.byForm ? Object.entries(doc.byForm).map(([k, v]) => k + ' ' + v).join(' · ') : '线性 ' + entries.length;
    totalIcons += doc.total || entries.length;
    body += '<div class="sec" data-sec="i' + li + '"><div class="grp"><h2>' + esc(ICON_LIB_ZH[doc.name] || doc.name) + '</h2><span class="gc">' + esc(forms) + ' · 授权 ' + esc(doc.license || '见库说明') + '</span></div>' +
      '<div class="ilib-note">绘画风格以本库官方规格为准 · 图标墙为抽样预览（筛选按图标名实时过滤） · 全量 ' + entries.length + ' 枚已打包在 data/icons-json/' + esc(doc.name) + '.json</div>' +
      '<div class="sd-lab" style="margin-top:6px">线性 / Outline · 抽样 ' + Math.min(line.length, 90) + ' / ' + line.length + '</div>' +
      '<div class="iwall">' + lineWall + '</div>' + fillWall + '</div>';
  });
  if (!libs.length) body = '<div class="noting">暂无图标库 —— 运行 scripts/build-icons-json.mjs 生成 data/icons-json 后自动出现在这里。</div>';
  const head = libs.length ? '<div class="grp" style="margin-top:0"><h2>打包汇总</h2><span class="gc">' + libs.length + ' 个库 · 约 ' + totalIcons + ' 枚图标已离线打包 · 均开源可商用（授权见各库）</span></div>' : '';
  return pageShell('原始图标库', libs.length + ' 个开源图标库已打包离线 · 图标墙按真实 SVG 渲染 · 共约 ' + totalIcons + ' 枚', tabs, head + body);
}

// ---------- 入口 ----------
export function buildRawAssets(skillRoot, outDir) {
  const files = [
    ['原始组件库规范.html', buildComponentsPage(skillRoot)],
    ['原始参考令牌库.html', buildTokensPage(skillRoot)],
    ['品牌设计语言.html', buildDesignMdsPage(skillRoot)],
    ['原始图标库.html', buildIconsPage(skillRoot)],
  ];
  for (const [name, html] of files) fs.writeFileSync(path.join(outDir, name), html);
  return files.map(([n]) => n);
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const outDir = path.resolve(process.argv[2] || process.cwd());
  fs.mkdirSync(outDir, { recursive: true });
  const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
  const made = buildRawAssets(skillRoot, outDir);
  console.log('原始素材页已生成: ' + made.map(n => path.join(outDir, n)).join(', '));
}
