// extract_en.mjs — 墨刀导出的原型 HTML：经 Chrome CDP 提取「英文画板」节点 → en_nodes.json（嵌套结构）
//
// 设计要点（已与 PM 验证的管线）：
//   • 连接已运行的 Chrome（由 SKILL.md「前置准备」启动，端口 9223），本脚本**不**负责启动浏览器。
//   • 选英文画板：CJK 字符数**最少**者（未必为 0，漏翻中文可能残留）；可选 --keywords 锁定、--screen 用 URL 参数直达。
//   • 嵌套 walk：记录 parent / depth / z-index / overflow / transform / cls / color / SVG，保留 DOM 树（方案 C）。
//   • 跳过 display:none / visibility:hidden / opacity≈0 的整棵子树；SVG 内部不深入。
//   • 缩放健康门：画板屏幕宽 < 80 拒绝；首次启动退化时重试（墨刀 fit-to-window 需时间响应）。
//   • 母版结构告警：节点数异常少时提示「疑似母版」。
//
// 用法：
//   node extract_en.mjs [--port 9223] [--pages all|1,2,3|引导页Onboarding,手机号登录Phone Login]
//                      [--screen <cid>] [--file <index.html 路径或 file:// URL>] [--keywords "Quests|..."]
//                      [--wait 5000] [--out en_nodes.json]
//
//   • 批次：--pages 支持「1-based 序号」「页面名（精确/包含匹配）」「all（默认全部）」。
//   • 精确定位（推荐）：--screen <cid> 配合 --file 用 URL 参数直达，避开不可靠的侧边栏点击。
import fs from 'fs';

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
const PORT = A.port || '9223';
const PAGES_ARG = A.pages || 'all';
const SCREEN = A.screen || '';
const FILE = A.file || '';
const KEYWORDS = A.keywords || '';
const WAIT = +(A.wait || 5000);
const OUT = A.out || 'en_nodes.json';

const WebSocket = globalThis.WebSocket;
const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const page = targets.find(t => t.type === 'page');
if (!page) throw new Error('未在 ' + PORT + ' 找到可调试页面，确认 Chrome 已开 --remote-debugging-port');
const ws = new WebSocket(page.webSocketDebuggerUrl);
let msgId = 0; const pending = new Map();
ws.addEventListener('message', ev => {
  const m = JSON.parse(ev.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
});
function send(method, params = {}) {
  return new Promise((resolve, reject) => {
    const id = ++msgId; pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout ' + method)); } }, 120000);
  });
}
await new Promise(r => ws.addEventListener('open', r, { once: true }));
async function evalJS(expr) {
  const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
  if (r.result && r.result.exceptionDetails) return { __error: (r.result.exceptionDetails.exception || {}).description || r.result.exceptionDetails.text };
  return r.result && r.result.result ? r.result.result.value : null;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));

// 0) 若指定 --screen，用 URL 参数直达（最稳）。--file 给出 index.html 位置。
if (SCREEN) {
  let base = FILE;
  if (!base) {
    const tg = (await send('Target.getTargets')).targetInfos || [];
    const cur = tg.find(t => t.type === 'page' && /index\.html/.test(t.url || ''));
    base = cur ? cur.url : '';
  }
  if (!base) throw new Error('--screen 需要配合 --file <index.html 路径> 或当前已打开该导出页');
  const url = base.replace(/(\?.*)?$/, '') + `?view_mode=device&screen=${SCREEN}`;
  console.log('  → 直达:', url);
  await send('Page.navigate', { url });
  await sleep(WAIT);
}

// 1) 读页面树（实时）
const GET_TREE = `(() => {
  return [...document.querySelectorAll('.rn-list-item[data-cid]')].map(el => {
    const nameEl = el.querySelector('.screen-name');
    const cid = el.getAttribute('data-cid') || '';
    return { cid, name: (nameEl ? nameEl.textContent : el.textContent).trim(),
             isFolder: el.classList.contains('rn-folder-item') || cid.includes('/') };
  }).filter(x => x.cid && !x.isFolder);
})()`;
const tree = (await evalJS(GET_TREE)) || [];
if (!tree.length) throw new Error('页面树为空：确认 Chrome 已加载墨刀导出 index.html');

// 2) 解析 --pages 选择
let chosen = tree;
if (PAGES_ARG !== 'all') {
  const parts = PAGES_ARG.split(',').map(s => s.trim()).filter(Boolean);
  chosen = [];
  for (const p of parts) {
    if (/^\d+$/.test(p)) {
      const idx = +p - 1;
      if (tree[idx]) chosen.push(tree[idx]);
    } else {
      const hit = tree.find(t => t.name === p) || tree.find(t => t.name.includes(p));
      if (hit) chosen.push(hit);
    }
  }
  if (!chosen.length) throw new Error('--pages 未匹配到任何页面：' + PAGES_ARG);
} else if (SCREEN) {
  // --screen 模式下 --pages 通常留 all，但只取当前直达页
  chosen = tree.filter(t => t.cid === SCREEN);
  if (chosen.length > 1) chosen = [chosen[0]];   // 树里可能有重复 cid，仅取首个
  if (!chosen.length) console.log('  ⚠ --screen 指定页不在页面树，将仅提取当前直达画板');
}

// 3) 选英文画板 + 嵌套提取（与历史验证一致）
const PICK_AND_EXTRACT = `(() => {
  const cjk = s => ((s||'').match(/[\\u4e00-\\u9fff]/g) || []).length;
  const kw = ${JSON.stringify(KEYWORDS)};
  const kwRe = kw ? new RegExp(kw, 'i') : null;
  let cands = [...document.querySelectorAll('.group-list .tree-node.rResCanvas')].map(el => {
    const cid = el.getAttribute('data-cid') || '';
    const t = (el.textContent||'').slice(0, 400);
    const tds = [...el.querySelectorAll('[id^="text-dom-"]')];
    const td = tds.length;
    return { el, cid, w: el.offsetWidth, h: el.offsetHeight, td, cjk: cjk(t), txt: t };
  }).filter(c => !c.cid.includes('/') && c.w === 375 && c.h >= 600 && c.td > 0);
  if (!cands.length) return { err: 'no artboard candidate' };
  if (kwRe) { const f = cands.filter(c => kwRe.test(c.txt)); if (f.length) cands = f; }
  cands.sort((a, b) => (a.cjk - b.cjk) || (b.td - a.td));   // CJK 最少者即英文板（未必为 0）
  const chosen = cands[0];
  const vp = chosen.el;
  const brr = vp.getBoundingClientRect();
  const sx = vp.offsetWidth / (brr.width || 1), sy = vp.offsetHeight / (brr.height || 1);
  const boardW = vp.offsetWidth, boardH = vp.offsetHeight;
  if (brr.width < 80) return { error: 'board scale degenerate, screenW=' + brr.width.toFixed(1) };
  const baseUrl = location.href.replace(/index\\.html.*$/, '');
  const nodes = [];
  function walk(el, parentIdx, depth) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const visible = cs.display !== 'none' && cs.visibility !== 'hidden' && +(cs.opacity) > 0.01;
    if (!visible) return;                                  // 隐藏节点整棵子树跳过
    const dx = (r.x - brr.x) * sx, dy = (r.y - brr.y) * sy, dw = r.width * sx, dh = r.height * sy;
    const idx = nodes.length;
    const rec = { idx, parent: parentIdx, depth, tag: el.tagName.toLowerCase(),
      x: +dx.toFixed(1), y: +dy.toFixed(1), w: +dw.toFixed(1), h: +dh.toFixed(1),
      cls: (el.className || '').toString().slice(0, 80) };
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).map(n => n.textContent.trim()).join(' ');
    if (own) rec.text = own;
    const st = {};
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') st.bg = cs.backgroundColor;
    if (cs.backgroundImage && cs.backgroundImage !== 'none') st.bgi = cs.backgroundImage.slice(0, 300);
    if (cs.borderRadius && cs.borderRadius !== '0px') st.br = cs.borderRadius;
    if (cs.borderWidth && cs.borderWidth !== '0px') { st.bw = cs.borderWidth; st.bc = cs.borderColor; st.bs = cs.borderStyle; }
    if (cs.opacity && cs.opacity !== '1') st.op = cs.opacity;
    if (cs.color) st.clr = cs.color;                        // 所有节点抓 color（SVG fill=currentColor 继承）
    if (cs.zIndex && cs.zIndex !== 'auto') st.zi = cs.zIndex;
    if (cs.overflow && cs.overflow !== 'visible') st.ovf = cs.overflow;   // 父裁剪子（方案 C）
    if (cs.boxShadow && cs.boxShadow !== 'none') st.bsh = cs.boxShadow;
    if (cs.outlineWidth && cs.outlineWidth !== '0px') { st.ow = cs.outlineWidth; st.os = cs.outlineStyle; st.oc = cs.outlineColor; }
    if (cs.borderStyle && cs.borderStyle !== 'none' && cs.borderStyle !== 'solid') st.bst = cs.borderStyle;
    if (cs.filter && cs.filter !== 'none') st.flt = cs.filter;
    if (cs.clipPath && cs.clipPath !== 'none') st.cp = cs.clipPath;
    if (cs.mask && cs.mask !== 'none' && cs.mask !== '') st.mk = cs.mask;
    if (cs.transform && cs.transform !== 'none') st.tf = cs.transform;     // [B] 还原 transform（RTL 镜像用）
    if (rec.text) { st.fs = cs.fontSize; st.fw = cs.fontWeight; st.ta = cs.textAlign; st.lh = cs.lineHeight; st.ff = cs.fontFamily; }
    if (Object.keys(st).length) rec.st = st;
    const tag = el.tagName.toLowerCase();
    if (tag === 'svg') rec.svg = el.outerHTML;
    if (tag === 'img') rec.img = el.getAttribute('src') || '';
    nodes.push(rec);
    if (tag === 'svg') return;                              // svg 内部不再深入
    for (const c of el.children) walk(c, idx, depth + 1);
  }
  walk(vp, null, 0);
  return { scale: +sx.toFixed(3), screenW: +brr.width.toFixed(1), board: { w: boardW, h: boardH, cjk: chosen.cjk },
           pkgBase: baseUrl, nodes };
})()`;

const out = [];
for (const p of chosen) {
  if (!SCREEN) {
    const click = await evalJS(`(() => {
      const n = document.querySelector('.rn-list-item[data-cid="${p.cid}"]');
      if (!n) return { ok: false };
      const t = n.querySelector('.screen-name') || n;
      ['mousedown','mouseup','click'].forEach(ev => t.dispatchEvent(new MouseEvent(ev, { bubbles: true, cancelable: true, view: window })));
      return { ok: true };
    })()`);
    if (!click || !click.ok) { console.log('  !! 页面节点缺失', p.name); out.push({ cid: p.cid, name: p.name, err: 'node missing' }); continue; }
    await sleep(WAIT);
  }
  // 缩放健康重试
  let data = null;
  for (let i = 0; i < 10; i++) {
    data = await evalJS(PICK_AND_EXTRACT);
    if (data && !data.__error && !data.error && data.screenW >= 80) break;
    console.log(`  [重试 ${i + 1}/10] screenW=${data && data.screenW} 退化，重设视口并等待…`);
    await send('Emulation.setDeviceMetricsOverride', { width: 1400, height: 1000, deviceScaleFactor: 1, mobile: false });
    await sleep(2500);
  }
  if (!data || data.__error) { console.log(`  !! ${p.name.slice(0,30)} -> ${(data && data.__error) || 'null'}`); out.push({ cid: p.cid, name: p.name, err: (data && data.__error) || 'null' }); continue; }
  if (data.error) { console.log(`  !! ${p.name.slice(0,30)} -> ${data.error}`); out.push({ cid: p.cid, name: p.name, err: data.error }); continue; }
  if (data.screenW < 80) { console.log(`  !! ${p.name.slice(0,30)} -> 缩放持续退化，拒绝提取`); out.push({ cid: p.cid, name: p.name, err: 'scale degenerate' }); continue; }
  const cnTexts = data.nodes.filter(x => x.text && /[\u4e00-\u9fff]/.test(x.text)).length;
  const flag = cnTexts > 0 ? `（含 ${cnTexts} 条中文，按漏翻中文直翻阿语处理）` : '';
  console.log(`  -> ${p.name.slice(0,34).padEnd(36)} board=${data.board.cjk != null ? data.board.cjk : '?'} nodes=${data.nodes.length} screenW=${data.screenW} scale=${data.scale}${flag}`);
  // 母版结构告警（G4）：内容页节点数异常少 → 疑似母版（元素抱团、难拆元素级）
  if (data.nodes.length < 20) console.log(`  ⚠ 疑似母版：节点数仅 ${data.nodes.length}，结构可能不可拆，回报 PM 而非硬解`);
  out.push({ cid: p.cid, name: p.name, board: data.board, scale: data.scale, screenW: data.screenW,
             pkgBase: data.pkgBase, nodes: data.nodes });
}

const meta = { port: PORT, generatedAt: new Date().toISOString(), note: '嵌套节点；parent=根时为 null；前置过滤/翻译/RTL 在 gen_ar_flat.mjs 完成' };
fs.writeFileSync(OUT, JSON.stringify({ meta, pages: out }, null, 2), 'utf8');
console.log('\n已写入:', OUT, '| 页数:', out.length);
ws.close(); process.exit(0);
