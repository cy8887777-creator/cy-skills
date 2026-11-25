#!/usr/bin/env node
// make-index.cjs —— 生成 _index.html 总导航（左树右平铺预览器，2026-09-17 用户拍板形态）
// 用法: node make-index.cjs <输出根目录> [manifest.json]
//   左侧：墨刀真实层级页面树（页面嵌套页面也挂 children 渲染为可展开节点）+ 搜索过滤
//   右侧：画布平铺墙——点页面 → 平铺该页全部画布（卡片定宽 320 居中）；文件夹点击只展开/收起子级
//   卡片 = 板名标签 + iframe 静态预览（懒加载）+ 透明遮罩：右侧不允许跳转，
//         点击卡片 = 新标签打开该画布 html（跳转交互在新标签页闭环）；弹窗被拦时退化为本页打开
//   缩放：适应（网格自适应宽，iframe 等比 scale）/ 100%（原始尺寸横向滚动）
//   不给 manifest → 退回磁盘扫描（卡片=目录下 html 文件，无页面分组）
const fs = require('fs');
const path = require('path');

const ROOT = process.argv[2];
const MANIFEST = process.argv[3];
if (!ROOT || !fs.existsSync(ROOT)) { console.error('用法: node make-index.cjs <输出根目录> [manifest.json]'); process.exit(1); }

const state = fs.existsSync(path.join(ROOT, 'state.json'))
  ? JSON.parse(fs.readFileSync(path.join(ROOT, 'state.json'), 'utf8')) : { done: {} };

const phStats = { empty: 0, failed: 0, partial: 0 };

// ---------- 板尺寸（boards/<cid>.json → page.board.w/h；缺失默认 375×812 手机板） ----------
const sizeCache = new Map();
function boardSize(cid) {
  if (sizeCache.has(cid)) return sizeCache.get(cid);
  let sz = { w: 375, h: 812 };
  try {
    const j = JSON.parse(fs.readFileSync(path.join(ROOT, 'boards', cid + '.json'), 'utf8'));
    if (j.page && j.page.board && j.page.board.w && j.page.board.h) sz = { w: j.page.board.w, h: j.page.board.h };
  } catch { /* json 缺失（已知 13 板）用默认 */ }
  sizeCache.set(cid, sz);
  return sz;
}

// ---------- 页面状态（空页/整页失败/板级失败 → 占位说明，不出卡片） ----------
function pageState(cid) {
  const d = state.done[cid];
  if (!d) return null;
  if (d.error) { phStats.failed++; return { kind: 'failed', note: String(d.error).slice(0, 80) }; }
  if ((d.failedBoards || []).length) { phStats.partial++; return { kind: 'partial', note: `${d.failedBoards.length} 板失败：` + d.failedBoards.map(b => b.name).join('、').slice(0, 60) }; }
  if (d.empty && !(d.boards || []).length) { phStats.empty++; return { kind: 'empty', note: '墨刀无画布（内容在子页面）' }; }
  return null;
}

// ---------- 树数据构建：节点 {t:'f'|'p', id, name, children|boards, ph} ----------
// 墨刀页面可嵌套页面（466 条子级 parent 指向 page）——页面也挂 children，树里渲染为可展开节点
let fid = 0;
function folder(name) { return { t: 'f', id: 'f' + (fid++), name, children: [] }; }
function pageNode(cid, name) {
  const d = state.done[cid];
  const boards = (d && d.boards || [])
    .filter(b => b.html && fs.existsSync(path.join(ROOT, b.html)))
    .map(b => {
      const sz = boardSize(b.cid);
      return { n: (d.boards.length === 1 ? '' : b.name), h: b.html.replace(/\\/g, '/'), w: sz.w, hh: sz.h };
    });
  return { t: 'p', id: 'p' + cid, cid, name, boards, ph: pageState(cid), children: [] };
}

let data;
if (MANIFEST) {
  const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
  const items = manifest.items || [];
  const byCid = new Map(items.map(it => [it.cid, it]));
  const roots = [];
  const nodes = new Map();
  for (const it of items) nodes.set(it.cid, it.type === 'folder' ? folder(it.name) : pageNode(it.cid, it.name));
  for (const it of items) {
    const n = nodes.get(it.cid);
    const p = it.parent && nodes.get(it.parent);
    if (p) p.children.push(n);   // 容器（folder 或 page）都挂 children——parent 指向 page 的 466 条不再甩顶层
    else roots.push(n);
  }
  const keep = (n) => n.t === 'p' ? !!(n.boards.length || n.ph || n.children.length) : !!n.children.length;
  const prune = (nodes2) => { const out = []; for (const n of nodes2) { if (n.t === 'f') n.children = prune(n.children); if (keep(n)) out.push(n); } return out; };
  data = prune(roots);
} else {
  // 磁盘扫描兼容：目录=文件夹，html=伪页面（单板）
  function walk(dir) {
    const out = [];
    for (const name of fs.readdirSync(dir).sort((a, b) => a.localeCompare(b, 'zh-Hans-CN'))) {
      if (name.startsWith('_') || name === 'assets' || name === 'boards') continue;
      const p = path.join(dir, name);
      const st = fs.statSync(p);
      if (st.isDirectory()) { const f = folder(name); f.children = walk(p); if (f.children.length) out.push(f); }
      else if (/\.html?$/i.test(name)) out.push({ t: 'p', id: 'd' + fid++, cid: '', name: name.replace(/\.html?$/i, ''), boards: [{ n: '', h: path.relative(ROOT, p).replace(/\\/g, '/'), w: 375, hh: 812 }], ph: null });
    }
    return out;
  }
  data = walk(ROOT);
}

// ---------- 统计 ----------
let boardCount = 0, pageCount = 0;
(function count(nodes) { for (const n of nodes) { if (n.t === 'p') { pageCount++; boardCount += n.boards.length; } count(n.children || []); } })(data);

const payload = JSON.stringify(data).replace(/</g, '\\u003c');

const doc = `<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<title>墨刀原型 · 总导航</title>
<style>
  * { box-sizing: border-box; }
  html, body { height: 100%; }
  body { font: 14px/1.6 system-ui, "Segoe UI", "Microsoft YaHei"; margin: 0; background: #F5F5F7; color: #1d1d1f; display: flex; overflow: hidden; }
  /* 左栏 */
  #side { width: 300px; min-width: 220px; max-width: 640px; background: #fff; border-right: 1px solid #e5e5ea; display: flex; flex-direction: column; }
  #dragbar { width: 5px; flex: none; cursor: col-resize; background: transparent; }
  #dragbar:hover, #dragbar.on { background: #c8c8d0; }
  #side .hd { padding: 12px 14px 8px; }
  #side h1 { font-size: 15px; margin: 0 0 8px; }
  #q { width: 100%; padding: 6px 10px; border: 1px solid #d5d5da; border-radius: 6px; font-size: 13px; outline: none; }
  #q:focus { border-color: #0066cc; }
  #tree { flex: 1; overflow: auto; padding: 4px 8px 20px; }
  #side .ft { padding: 8px 14px; border-top: 1px solid #e5e5ea; color: #86868b; font-size: 11.5px; line-height: 1.5; }
  .grp { margin: 1px 0; }
  .grp > .lbl { display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 3px 6px; border-radius: 5px; user-select: none; }
  .grp > .lbl:hover { background: #f2f2f7; }
  .grp > .lbl .tw { width: 12px; text-align: center; color: #86868b; font-size: 10px; transition: transform .12s; flex: none; }
  .grp.open > .lbl .tw { transform: rotate(90deg); }
  .grp .kids { display: none; margin-left: 20px; border-left: 1px solid #e0e0e6; padding-left: 6px; }
  .grp.open > .kids { display: block; }
  .pg { display: flex; align-items: center; gap: 5px; cursor: pointer; padding: 3px 6px; border-radius: 5px; user-select: none; }
  .pg:hover { background: #f2f2f7; }
  .pg.act { background: #e8f1fb; color: #0066cc; }
  .pg.grp { display: block; }   /* 页面嵌套页面：外层容器化（内装 lbl+kids，不吃 .pg 的 flex 横排） */
  .grp.act > .lbl, .grp > .lbl.act { background: #e8f1fb; color: #0066cc; }
  .pg .dot { width: 5px; height: 5px; border-radius: 50%; background: #34c759; flex: none; }
  .pg.ph-empty .dot { background: #c7c7cc; }
  .pg.ph-bad .dot { background: #ff3b30; }
  .pg .nm { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .pg .bc { color: #b0b0b5; font-size: 11px; flex: none; }
  mark { background: #ffe58f; border-radius: 2px; }
  /* 右栏 */
  #main { flex: 1; display: flex; flex-direction: column; min-width: 0; }
  #bar { display: flex; align-items: center; gap: 10px; padding: 10px 16px; background: #fff; border-bottom: 1px solid #e5e5ea; }
  #crumb { flex: 1; min-width: 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 500; }
  #zoom { display: flex; gap: 4px; }
  #zoom button { border: 1px solid #d5d5da; background: #fff; border-radius: 6px; padding: 3px 10px; cursor: pointer; font-size: 12.5px; }
  #zoom button.on { background: #0066cc; border-color: #0066cc; color: #fff; }
  #wall { flex: 1; overflow: auto; padding: 18px 20px 60px; }
  .sec { margin: 14px 0 10px; font-size: 13.5px; font-weight: 600; color: #3a3a3c; }
  .sec:first-child { margin-top: 0; }
  .sec .cnt { color: #86868b; font-weight: 400; font-size: 12px; margin-left: 6px; }
  .grid { display: flex; flex-wrap: wrap; justify-content: center; gap: 16px; }   /* 卡宽=各画布原尺寸（fit 模式统一 320），flex 流式换行居中 */
  .card { background: #fff; border: 1px solid #e5e5ea; border-radius: 10px; overflow: hidden; cursor: pointer; transition: box-shadow .15s, border-color .15s; position: relative; }
  .card:hover { border-color: #0066cc; box-shadow: 0 2px 12px rgba(0,102,204,.12); }
  .card .cap { display: flex; align-items: center; gap: 6px; padding: 6px 10px; border-bottom: 1px solid #f0f0f3; font-size: 12.5px; }
  .card .cap .bn { font-weight: 600; }
  .card .cap .tip { margin-left: auto; color: #86868b; font-size: 11.5px; }
  .card:hover .cap .tip { color: #0066cc; }
  .fbox { position: relative; background: #E9E9EF; }   /* 与产物 body 底色一致——padding 24px 衬边同色无缝 */
  .fbox .loadph { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: #b0b0b5; font-size: 12px; }
  .fbox iframe { position: absolute; left: 0; top: 0; border: 0; transform-origin: 0 0; background: #fff; }
  .card .open-mask { position: absolute; inset: 0; z-index: 2; }
  .card .go { position: absolute; right: 8px; top: 38px; z-index: 3; background: rgba(0,102,204,.85); color: #fff; border-radius: 6px; padding: 3px 8px; font-size: 11.5px; opacity: 0; transition: opacity .15s; pointer-events: none; }
  .card:hover .go { opacity: 1; }
  .wallph { color: #86868b; padding: 30px 6px; text-align: center; }
  .wallph .w { color: #c0392b; }
  #toast { position: fixed; left: 50%; bottom: 26px; transform: translateX(-50%); background: rgba(29,29,31,.86); color: #fff; padding: 8px 16px; border-radius: 8px; font-size: 13px; opacity: 0; transition: opacity .2s; pointer-events: none; z-index: 9; }
  #toast.show { opacity: 1; }
</style>
</head>
<body>
<div id="side">
  <div class="hd"><h1>墨刀原型 · 还原导航</h1><input id="q" placeholder="搜索页面名…"></div>
  <div id="tree"></div>
  <div class="ft">📄 ${boardCount} 画布 · 📑 ${pageCount} 页面${phStats.empty || phStats.failed || phStats.partial ? ` · 空页 ${phStats.empty} / 失败 ${phStats.failed} / 部分失败 ${phStats.partial}` : ''}<br>生成于 ${new Date().toLocaleString('zh-CN')} · 点击页面平铺画布 · 点击画布卡片 = 新标签打开</div>
</div>
<div id="dragbar" title="拖动调整宽度"></div>
<div id="main">
  <div id="bar"><div id="crumb">选择左侧页面</div>
    <div id="zoom"><button data-z="100" class="on">原尺寸</button><button data-z="fit">适应</button></div>
  </div>
  <div id="wall"><div class="wallph">左侧点击页面平铺其全部画布；文件夹点击只展开/收起子级</div></div>
</div>
<div id="toast"></div>
<script>
const DATA = ${payload};
const $ = (s) => document.querySelector(s);
const treeEl = $('#tree'), wallEl = $('#wall'), crumbEl = $('#crumb');
const openedPopupsBlocked = [];
let selId = null, zoom = '100';   // 默认原尺寸 1:1（用户拍板），fit 为可选缩小

// ---------- 左树 ----------
function hl(name, q) {
  if (!q) return esc(name);
  const i = name.toLowerCase().indexOf(q);
  if (i < 0) return esc(name);
  return esc(name.slice(0, i)) + '<mark>' + esc(name.slice(i, i + q.length)) + '</mark>' + esc(name.slice(i + q.length));
}
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/"/g, '&quot;');
function pageMatch(n, q) { return !q || n.name.toLowerCase().includes(q) || (n.boards || []).some(b => b.n && b.n.toLowerCase().includes(q)); }
function subtreeMatch(n, q) { return pageMatch(n, q) || (n.children || []).some(c => subtreeMatch(c, q)); }

function renderTree(q) {
  q = (q || '').trim().toLowerCase();
  treeEl.innerHTML = '';
  const build = (nodes, parent, path) => {
    for (const n of nodes) {
      if (!subtreeMatch(n, q)) continue;
      if (n.t === 'f') {
        // 文件夹：整行点击=打开/收起（不平铺子页面——2026-09-17 用户拍板）
        const g = document.createElement('div');
        g.className = 'grp' + (q ? ' open' : (path.length < 1 ? ' open' : ''));
        g.dataset.id = n.id;
        g.innerHTML = '<div class="lbl"><span class="tw">▶</span>📁 <span class="nm">' + hl(n.name, q) + '</span></div><div class="kids"></div>';
        g.querySelector('.lbl').addEventListener('click', () => g.classList.toggle('open'));
        parent.appendChild(g);
        build(n.children, g.querySelector('.kids'), path.concat(n.name));
      } else if (n.children.length) {
        // 页面嵌套页面：可展开——点名称=预览其画布，点箭头=开合子级
        const g = document.createElement('div');
        g.className = 'pg grp' + (n.id === selId ? ' act' : '') + (n.ph ? (n.ph.kind === 'empty' ? ' ph-empty' : ' ph-bad') : '');
        g.dataset.id = n.id;
        g.innerHTML = '<div class="lbl"><span class="tw">▶</span><span class="dot"></span><span class="nm">' + hl(n.name, q) + '</span>' + (n.boards.length > 1 ? '<span class="bc">' + n.boards.length + '</span>' : '') + '</div><div class="kids"></div>';
        const lbl = g.querySelector('.lbl');
        lbl.addEventListener('click', (e) => {
          if (e.target.closest('.tw')) { g.classList.toggle('open'); return; }
          select(n, g);
        });
        parent.appendChild(g);
        build(n.children, g.querySelector('.kids'), path.concat(n.name));
      } else {
        const d = document.createElement('div');
        d.className = 'pg' + (n.id === selId ? ' act' : '') + (n.ph ? (n.ph.kind === 'empty' ? ' ph-empty' : ' ph-bad') : '');
        d.dataset.id = n.id;
        d.innerHTML = '<span class="dot"></span><span class="nm">' + hl(n.name, q) + '</span>' + (n.boards.length > 1 ? '<span class="bc">' + n.boards.length + '</span>' : '');
        d.addEventListener('click', () => select(n, d));
        parent.appendChild(d);
      }
    }
  };
  build(DATA, treeEl, []);
}
function markActive(id) {
  selId = id;
  treeEl.querySelectorAll('.act').forEach(e => e.classList.remove('act'));
  const el = treeEl.querySelector('[data-id="' + id + '"]');
  if (el) { el.classList.add('act'); el.scrollIntoView({ block: 'nearest' }); }
}

// ---------- 右侧平铺 ----------
let io = null;
function setupIO() {
  if (io) io.disconnect();
  io = new IntersectionObserver((es) => {
    es.forEach((e) => { if (e.isIntersecting) { mountIframe(e.target); io.unobserve(e.target); } });
  }, { root: wallEl, rootMargin: '400px 0px' });
}
// 产物 body 有 padding:24px 衬边（单文件打开正常，塞等尺寸 iframe 会溢出出滚动条）——
// iframe 尺寸给足「画布+48」+ scrolling=no：跨环境一致（不依赖同源注入，file:// 双击打开也生效）
const PAD = 48;
function mountIframe(fbox) {
  if (fbox.dataset.loaded === '1') return;
  fbox.dataset.loaded = '1';
  const b = JSON.parse(fbox.dataset.b);
  const fr = document.createElement('iframe');
  fr.setAttribute('loading', 'lazy');
  fr.setAttribute('scrolling', 'no');
  fr.src = b.h;
  fr.style.width = (b.w + PAD) + 'px'; fr.style.height = (b.hh + PAD) + 'px';
  fbox.appendChild(fr);
  fbox.querySelector('.loadph')?.remove();
  scaleOne(fbox);
}
function scaleAll() { wallEl.querySelectorAll('.fbox[data-loaded="1"]').forEach(scaleOne); }
function scaleOne(fbox) {
  const fr = fbox.querySelector('iframe'); if (!fr) return;
  const b = JSON.parse(fbox.dataset.b);
  const iw = b.w + PAD, ih = b.hh + PAD;
  if (zoom === 'fit') {
    // 可选缩小模式：统一 320 卡宽，iframe 等比缩放
    const s = 320 / iw;
    fr.style.transform = 'scale(' + s + ')';
    fbox.style.width = '320px';
    fbox.style.height = Math.round(ih * s) + 'px';
  } else {
    // 默认原尺寸 1:1（2026-09-17 用户拍板：375 板就显示 375 宽，不缩放）
    fr.style.transform = 'scale(1)';
    fbox.style.width = iw + 'px';
    fbox.style.height = ih + 'px';
  }
}
function toast(msg) {
  const t = $('#toast'); t.textContent = msg; t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove('show'), 2200);
}
function openHtml(url) {
  const w = window.open(url, '_blank');
  if (!w) { toast('浏览器拦截了新标签，已在本页打开（后退可回导航）'); location.href = url; }
}
function card(b, pname) {
  const c = document.createElement('div');
  c.className = 'card';
  const label = b.n || pname;
  c.innerHTML = '<div class="cap"><span class="bn">' + esc(label) + '</span>' + (pname && b.n ? '<span class="tip">' + esc(pname) + '</span>' : '') + '<span class="tip">↗ 新标签打开</span></div>' +
    '<div class="fbox" data-loaded="0" data-b="' + esc(JSON.stringify(b)) + '" style="width:' + (b.w + 48) + 'px;height:' + (b.hh + 48) + 'px"><div class="loadph">滚动到此处加载预览…</div></div>' +
    '<div class="open-mask"></div><div class="go">↗ 新标签打开</div>';
  c.addEventListener('click', () => openHtml(b.h));
  io.observe(c.querySelector('.fbox'));
  return c;
}
function pageSection(n, parent, showTitle) {
  const wrap = document.createElement('div');
  if (showTitle) {
    const s = document.createElement('div');
    s.className = 'sec';
    s.innerHTML = esc(n.name) + '<span class="cnt">' + (n.boards.length ? n.boards.length + ' 画布' : '') + (n.ph ? ' · ' + (n.ph.kind === 'empty' ? '空页面' : '⚠ ' + esc(n.ph.note)) : '') + '</span>';
    wrap.appendChild(s);
  }
  if (n.boards.length) {
    const g = document.createElement('div'); g.className = 'grid';
    n.boards.forEach((b) => g.appendChild(card(b, n.name)));
    wrap.appendChild(g);
  } else if (!showTitle) {
    const s = document.createElement('div'); s.className = 'sec';
    s.innerHTML = esc(n.name) + '<span class="cnt">' + (n.ph ? (n.ph.kind === 'empty' ? '· 空页面（内容在子页面）' : '· <span class="w">⚠ ' + esc(n.ph.note) + '</span>') : '') + '</span>';
    wrap.appendChild(s);
  }
  parent.appendChild(wrap);
}
function select(n, el) {
  if (n.t !== 'p') return;   // 文件夹不再平铺（2026-09-17 用户拍板：点击=开合）
  markActive(n.id);
  location.hash = 'p=' + encodeURIComponent(n.id);
  setupIO();
  wallEl.innerHTML = '';
  crumbEl.textContent = n.name + (n.boards.length ? '（' + n.boards.length + ' 画布）' : '');
  pageSection(n, wallEl, false);
  if (!n.boards.length) {
    const d = document.createElement('div'); d.className = 'wallph';
    d.innerHTML = n.ph ? (n.ph.kind === 'empty' ? '墨刀无画布（内容在子页面）' : '<span class="w">⚠ ' + esc(n.ph.note) + '</span>') : '无画布';
    wallEl.appendChild(d);
  }
  wallEl.scrollTop = 0;
  scaleAll();
}

// ---------- 工具条 ----------
$('#q').addEventListener('input', (e) => renderTree(e.target.value));
document.querySelectorAll('#zoom button').forEach((btn) => btn.addEventListener('click', () => {
  zoom = btn.dataset.z;
  document.querySelectorAll('#zoom button').forEach(b => b.classList.toggle('on', b === btn));
  scaleAll();
}));

// ---------- hash 恢复 ----------
function findById(id) {
  let hit = null;
  (function walk(nodes) { for (const n of nodes) { if (n.id === id) { hit = n; return; } walk(n.children || []); } })(DATA);
  return hit;
}
(function restore() {
  const m = location.hash.match(/^#p=([^/]+)/);
  renderTree('');
  if (m) {
    const n = findById(decodeURIComponent(m[1]));
    if (n) { select(n, null); return; }
  }
})();

// 首次进入自动选第一个页面（有画布的）
(function autoFirst() {
  if (selId) return;
  let first = null;
  (function walk(nodes) { for (const n of nodes) { if (first) return; if (n.t === 'p' && n.boards.length) { first = n; return; } walk(n.children || []); } })(DATA);
  if (first) select(first, null);
})();

// ---------- 左栏拖拽调宽（localStorage 记忆） ----------
(function dragSide() {
  const side = document.querySelector('#side'), bar = document.querySelector('#dragbar');
  const saved = +localStorage.getItem('idx-side-w');
  if (saved >= 220 && saved <= 640) side.style.width = saved + 'px';
  let on = false, sx = 0, sw = 0;
  bar.addEventListener('mousedown', (e) => { on = true; sx = e.clientX; sw = side.getBoundingClientRect().width; bar.classList.add('on'); document.body.style.cursor = 'col-resize'; e.preventDefault(); });
  window.addEventListener('mousemove', (e) => {
    if (!on) return;
    side.style.width = Math.max(220, Math.min(640, Math.round(sw + e.clientX - sx))) + 'px';
    scaleAll();
  });
  window.addEventListener('mouseup', () => {
    if (!on) return;
    on = false; bar.classList.remove('on'); document.body.style.cursor = '';
    localStorage.setItem('idx-side-w', Math.round(side.getBoundingClientRect().width));
  });
})();
</script>
</body>
</html>`;
fs.writeFileSync(path.join(ROOT, '_index.html'), doc);
console.log(JSON.stringify({ ok: true, index: path.join(ROOT, '_index.html'), mode: MANIFEST ? 'manifest' : 'disk', pages: pageCount, boards: boardCount, ph: phStats }));
