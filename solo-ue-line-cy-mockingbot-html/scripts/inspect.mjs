// inspect.mjs —— 产物质量自检：headless 渲染每板 HTML，程序断言换行/孤字/偏心/省略缺失/越界/双份渲染/对齐
// 用法：node inspect.mjs <port> <产物根> [--only 页面cid,…]
// 输出：<产物根>/inspect-report.json + 控制台摘要。两类问题：A=转换损失（该修）、B=墨刀稿自带（出报告给用户拍板）
// 注意：在 9225 的 Chrome 里另开 tab 加载产物（file://），跑完关 tab——不占墨刀 SPA 的 tab
import fs from 'node:fs';
import path from 'node:path';
import { connect, sleep } from './cdp.mjs';

const argv = process.argv.slice(2);
const PORT = argv[0], ROOT = path.resolve(argv[1]);
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1].split(',') : null;
if (!PORT || !ROOT || !fs.existsSync(path.join(ROOT, 'state.json'))) {
  console.error('用法: node inspect.mjs <port> <产物根> [--only 页面cid,…]'); process.exit(1);
}
const state = JSON.parse(fs.readFileSync(path.join(ROOT, 'state.json'), 'utf8'));

// ---------- 浏览器侧断言（渲染真值：文字 bbox / 折行 / 偏心 / 孤字 / nowrap 溢出） ----------
const PROBE = `(() => {
  const stage = document.querySelector('.stage');
  if (!stage) return { err: 'no stage' };
  const sr = stage.getBoundingClientRect();
  const texts = [];
  for (const el of stage.querySelectorAll('div')) {
    const t = el.childNodes.length && [...el.childNodes].every(x => x.nodeType === 3) ? el.textContent.trim() : '';
    if (!t) continue;
    const r = el.getBoundingClientRect(), cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize) || 16, lh0 = parseFloat(cs.lineHeight), lh = Number.isFinite(lh0) && lh0 > 0 ? lh0 : fs * 1.4;
    const rg = document.createRange(); rg.selectNodeContents(el);
    const tb = rg.getBoundingClientRect();
    const rects = [...rg.getClientRects()].filter(x => x.width > 0.5);
    // 行数用 bbox高÷行高：阿语连写脚本单行也会返回多段 rect，rects 数会误判折行；紧行高(lh<fs)时除数用 fs 防 Range 高 1.35fs 被算两行
    const lines = Math.max(1, Math.round(tb.height / Math.max(lh, fs)));
    texts.push({
      t: t.slice(0, 36),
      ws: cs.whiteSpace === 'normal' ? '' : cs.whiteSpace, ta: cs.textAlign, fs, lh: +lh.toFixed(1),
      x: +(r.x - sr.x).toFixed(1), y: +(r.y - sr.y).toFixed(1), w: +r.width.toFixed(1), h: +r.height.toFixed(1),
      tw: +tb.width.toFixed(1), th: +tb.height.toFixed(1), lines,
      eccH: +((r.right - tb.right) - (tb.left - r.left)).toFixed(1),   // 水平偏心：左留白-右留白（0=居中/贴边）
      eccV: +((r.bottom - tb.bottom) - (tb.top - r.top)).toFixed(1),   // 垂直偏心：上留白-下留白
      orphan: lines > 1 && rects[rects.length - 1].width < fs * 2.2,    // 折行后最后一行孤字/孤词
      ellip: cs.textOverflow === 'ellipsis',
      overW: cs.whiteSpace === 'nowrap' ? +(tb.width - r.width).toFixed(1) : 0,  // nowrap 下文字溢出框宽
      // 越界只看右/下（gen-html 已 clamp；左/上负坐标属稿子溢出画布的装饰，stage 裁剪视觉一致）
      overB: r.x - sr.x + r.width > sr.width + 1 || r.y - sr.y + r.height > sr.height + 1,
    });
  }
  return { board: { w: sr.width, h: sr.height }, texts };
})()`;

// ---------- Node 侧断言（提取真值：div 级对齐/等距/双份渲染/越界——产物绝对布局=json 平移，不齐只能是稿子问题） ----------
function jsonChecks(bjson) {
  const j = JSON.parse(fs.readFileSync(bjson, 'utf8'));
  const ns = (j.page.nodes || []).filter(n => n.w > 0 && n.h > 0);
  const out = { misalign: [], dup: [], over: [] };
  // 同 y 带（±3px）≥3 个元素的组：top/center/bottom 三线任一共线即算对齐（设计里图标-文字常按中心线对齐，只查 top 会误报）
  const bands = [];
  for (const n of ns) {
    let hit = bands.find(g => Math.abs(g[0].y - n.y) < 3);
    if (!hit) { hit = []; bands.push(hit); }
    hit.push(n);
  }
  const spreadOf = (g, f) => { const vs = g.map(f); return Math.max(...vs) - Math.min(...vs); };
  for (const g of bands) if (g.length >= 3) {
    const sT = spreadOf(g, n => n.y), sC = spreadOf(g, n => n.y + n.h / 2), sB = spreadOf(g, n => n.y + n.h);
    const spread = Math.min(sT, sC, sB);
    if (spread > 2.5) out.misalign.push({ y: Math.min(...g.map(n => n.y)), spread: +spread.toFixed(1), items: g.map(n => ({ idx: n.idx, y: n.y, h: n.h, text: (n.text || '').slice(0, 12) })) });
  }
  // 同文本同位双份渲染（墨刀表格/文字双份渲染）
  const seen = new Map();
  for (const n of ns) {
    const t = String(n.text || '').trim();
    if (t.length < 2) continue;
    const key = t + '@' + Math.round(n.x / 4) + ',' + Math.round(n.y / 4);
    if (seen.has(key)) out.dup.push({ text: t.slice(0, 24), x: n.x, y: n.y });
    else seen.set(key, 1);
  }
  // 越界（json 真值：x+w 超画布）。纯色/图背景块延伸出画布会被 stage overflow:hidden 裁掉，无害——只报内容元素（带文字/图）越界
  const W = j.page.board.w, H = j.page.board.h;
  for (const n of ns) if (n.x + n.w > W + 1 || n.y + n.h > H + 1) {
    const hasContent = n.text || n.img || n.svg;
    if (hasContent) out.over.push({ idx: n.idx, text: (n.text || (n.img ? '[img]' : '[svg]')).slice(0, 12), x: n.x, y: n.y, w: n.w, h: n.h });
  }
  return { board: j.page.board, ...out };
}

// ---------- 主流程：开新 tab 逐板加载 ----------
const pages = Object.entries(state.done).filter(([cid, d]) => !only || only.includes(cid));
const jobs = [];
for (const [cid, d] of pages) for (const b of (d.boards || [])) if (b.json && b.html) jobs.push({ cid, label: d.dir.concat(d.name, b.name).join('/'), b });

const newTab = await (await fetch(`http://127.0.0.1:${PORT}/json/new?about:blank`, { method: 'PUT' })).json();
const c = await connect(PORT, new RegExp(newTab.id.slice(0, 8)));
const report = [];
try {
  // 双保险防 file:// 缓存：禁网络缓存 + URL 版本串（否则 regen 后 navigate 仍读旧 DOM，越界/尺寸全误报）
  await c.send('Network.enable', {});
  await c.send('Network.setCacheDisabled', { cacheDisabled: true });
  for (let i = 0; i < jobs.length; i++) {
    const { label, b } = jobs[i];
    const url = 'file:///' + encodeURI(path.resolve(ROOT, b.html).replace(/\\/g, '/')).replace(/#/g, '%23') + '?v=' + Date.now();
    await c.send('Page.navigate', { url });
    await sleep(260);
    let probe = null;
    for (let k = 0; k < 8 && !probe; k++) { try { probe = await c.evalJS(PROBE); } catch { await sleep(300); } }
    if (!probe || probe.err) { report.push({ label, html: b.html, err: probe ? probe.err : 'probe fail' }); continue; }
    let jc = {};
    try { jc = jsonChecks(path.resolve(ROOT, b.json)); } catch (e) { jc = { err: String(e.message) }; }
    report.push({ label, html: b.html, ...probe, json: jc });
    if ((i + 1) % 12 === 0) console.log(`… [${i + 1}/${jobs.length}]`);
  }
} finally {
  await fetch(`http://127.0.0.1:${PORT}/json/close/${newTab.id}`).catch(() => {});
  c.close();
}
fs.writeFileSync(path.join(ROOT, 'inspect-report.json'), JSON.stringify(report, null, 1));

// ---------- 摘要（组件规范板单独分组——非 APP 页面，用户拍板不管，只列计数不进问题） ----------
const S = { boards: report.length, err: 0, texts: 0, wrap2: 0, orphan: 0, nowrapOver: 0, ellipMissing: 0, eccH: 0, eccV: 0, overStage: 0, jsonMisalign: 0, jsonDup: 0, jsonOver: 0 };
const Sc = { ...S };   // 组件规范板计数
const samples = { orphan: [], nowrapOver: [], ellipMissing: [], eccH: [], eccV: [], jsonMisalign: [], jsonDup: [], jsonOver: [] };
for (const r of report) {
  const spec = r.label.startsWith('组件规范');
  const T = spec ? Sc : S;
  if (r.err) { T.err++; continue; }
  T.texts += r.texts.length;
  for (const t of r.texts) {
    // 孤字只对「单行框意图」（渲染框高 ≤1.8×行高）算问题：多行文案区正常折行末行窄不是缺陷
    if (t.lines > 1 && !/pre/.test(t.ws) && t.h <= t.lh * 1.8) { T.wrap2++; if (t.orphan) { T.orphan++; if (!spec) samples.orphan.push(`${r.label} 「${t.t}」框${t.w}宽 字${t.tw}宽 fs${t.fs}`); } }
    if (t.overW > 2) { T.nowrapOver++; if (!spec) samples.nowrapOver.push(`${r.label} 「${t.t}」溢出${t.overW}px`); }
    if (Math.abs(t.eccH) > 6 && t.ta === 'center' && t.w > t.tw + 8) { T.eccH++; if (!spec) samples.eccH.push(`${r.label} 「${t.t}」偏${t.eccH}px`); }
    if (Math.abs(t.eccV) > 8 && t.h > t.th * 1.8) { T.eccV++; if (!spec) samples.eccV.push(`${r.label} 「${t.t}」框${t.h} 字${t.th} 偏${t.eccV}px`); }
    if (t.overB && (t.t || null)) { T.overStage++; if (!spec) samples.jsonOver.push(`${r.label} 「${t.t}」出画布`); }
  }
  if (r.json) {
    T.jsonMisalign += r.json.misalign?.length || 0;
    T.jsonDup += r.json.dup?.length || 0;
    T.jsonOver += r.json.over?.length || 0;
    if (!spec) {
      for (const m of (r.json.misalign || []).slice(0, 3)) samples.jsonMisalign.push(`${r.label} y≈${m.y} 三线高差${m.spread}px ×${m.items.length}`);
      for (const d of (r.json.dup || []).slice(0, 3)) samples.jsonDup.push(`${r.label} 「${d.text}」双份`);
      for (const o of (r.json.over || []).slice(0, 3)) samples.jsonOver.push(`${r.label} 「${o.text}」(${o.x},${o.y},${o.w}×${o.h}) 越界`);
    }
  }
}
console.log('===== 自检摘要（APP 页面 / 组件规范板） =====');
console.log(JSON.stringify({ app: S, spec: Sc }, null, 1));
for (const [k, arr] of Object.entries(samples)) if (arr.length) console.log(`\n-- ${k} 样例:\n  ` + arr.slice(0, 10).join('\n  '));
