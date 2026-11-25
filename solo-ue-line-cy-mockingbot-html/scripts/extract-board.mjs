// extract-board.mjs —— 按 cid 直接提取墨刀画板 → 结构化 JSON（视图状态无关，含懒加载预滚）
// 用法：node extract-board.mjs <port> <cid> <out.json>
// 产物 schema：{ meta, page: { cid, name, board:{w,h}, pkgBase, nodes:[{idx,parent,depth,tag,x,y,w,h,name?,cls,text?,st?,svg?,img?}] } }
// 关键规则（踩坑固化）：
//   - 坐标 = getBoundingClientRect 换算回画板坐标系（rect×scale），transform 效果已含在内，生成时不再套 tf
//   - outline（选中描边）是查看器 UI，不映射
//   - 画板 screenW < 80 判缩放退化直接报错（窗口太小所致，重启大窗口 Chrome）
//   - 懒加载预滚：分批 scrollIntoView + 轮询 is-default-image 清零（headless 下也要滚）
import fs from 'node:fs';
import { connect, sleep, detectModel } from './cdp.mjs';
import { WAIT_BOARD, extractBoardPcanvas } from './pcanvas-extract.mjs';

const [, , PORT, CID, OUT] = process.argv;
if (!PORT || !CID || !OUT) { console.error('用法: node extract-board.mjs <port> <cid> <out.json>'); process.exit(1); }
const c = await connect(PORT);
const { evalJS } = c;

// ---------- 0) 查看器代际：pcanvas 模型走共享提取模块（2026-10-20） ----------
const MODEL = await detectModel(evalJS);
if (MODEL === 'pcanvas') {
  // 板未激活先点侧边栏条目（CLI 直提时多半没挂载/未激活）
  let ready = String(await evalJS(WAIT_BOARD(CID)));
  if (!ready.startsWith('READY')) {
    await evalJS(`(() => {
      const item = document.querySelector('.rn-list-item[data-cid="${CID}"]');
      if (!item) return 'NOT_FOUND';
      item.scrollIntoView({ block: 'center' });
      const r = item.getBoundingClientRect();
      const o = { bubbles: true, cancelable: true, view: window, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 };
      item.dispatchEvent(new MouseEvent('mousedown', o));
      item.dispatchEvent(new MouseEvent('mouseup', o));
      item.dispatchEvent(new MouseEvent('click', o));
      return 'OK';
    })()`);
    for (let i = 0; i < 10 && !ready.startsWith('READY'); i++) {
      await sleep(1200);
      ready = String(await evalJS(WAIT_BOARD(CID)));
    }
  }
  if (!ready.startsWith('READY')) { console.error('画板未就绪（' + ready + '）：cid=' + CID); c.close(); process.exit(1); }
  const r = await extractBoardPcanvas({ port: PORT, cid: CID, outJson: OUT, tool: 'mockingbot-to-html/extract-board.mjs' });
  if (!r || !r.ok) { console.error('提取失败:', JSON.stringify(r)); c.close(); process.exit(1); }
  const j = JSON.parse(fs.readFileSync(OUT, 'utf8'));
  const ns = j.page.nodes;
  console.log(JSON.stringify({ ok: true, cid: CID, model: 'pcanvas', board: r.board,
    nodes: ns.length, text: ns.filter(n => n.text).length, svg: ns.filter(n => n.svg).length,
    img: ns.filter(n => n.img).length, named: ns.filter(n => n.name).length }));
  c.close();
  process.exit(0);
}

// ---------- 1) 懒加载预滚（legacy 模型，原逻辑不动） ----------
const ROLL = `(() => {
  const b = [...document.querySelectorAll('.tree-node.rResCanvas')]
    .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(CID)})[0];
  if (!b) return -1;
  b.scrollIntoView({ block: 'center', inline: 'center' });
  const pend = b.querySelectorAll('.image-container.is-default-image');
  pend.forEach((el, i) => setTimeout(() => el.scrollIntoView({ block: 'center', inline: 'center' }), i * 60));
  return pend.length;
})()`;
let n = await evalJS(ROLL);
if (n === -1) { console.error('画板不在 DOM（未挂载）：cid=' + CID); c.close(); process.exit(1); }
for (let i = 0; i < 20 && n > 0; i++) {
  await sleep(1500);
  n = await evalJS(`(() => {
    const b = [...document.querySelectorAll('.tree-node.rResCanvas')]
      .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(CID)})[0];
    return b ? b.querySelectorAll('.image-container.is-default-image').length : 999;
  })()`);
}
await evalJS(ROLL);
await sleep(4000);

// ---------- 2) 提取 ----------
const PICK = `(() => {
  const vp = [...document.querySelectorAll('.tree-node.rResCanvas')]
    .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(CID)})[0];
  if (!vp) return { err: 'board gone' };
  const brr = vp.getBoundingClientRect();
  const sx = vp.offsetWidth / (brr.width || 1), sy = vp.offsetHeight / (brr.height || 1);
  // 同 batch.mjs：布局真值 offsetWidth 正常时放行（分组缩略容器里 transform 等比缩，rect×sx 换算有效）；仅布局也退化才拒
  if (vp.offsetWidth < 80 && brr.width < 80) return { error: 'board scale degenerate, screenW=' + brr.width.toFixed(1) };
  const baseUrl = location.href.replace(/index\\.html.*$/, '');
  const nodes = [];
  function walk(el, parentIdx, depth) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    const visible = cs.display !== 'none' && cs.visibility !== 'hidden' && +(cs.opacity) > 0.01;
    if (!visible) return;
    const dx = (r.x - brr.x) * sx, dy = (r.y - brr.y) * sy, dw = r.width * sx, dh = r.height * sy;
    const idx = nodes.length;
    const rec = { idx, parent: parentIdx, depth, tag: el.tagName.toLowerCase(),
      x: +dx.toFixed(1), y: +dy.toFixed(1), w: +dw.toFixed(1), h: +dh.toFixed(1),
      cls: (el.className || '').toString().slice(0, 80) };
    const nm = el.getAttribute('data-name') || el.getAttribute('title') || '';
    if (nm) rec.name = nm.slice(0, 80);
    const own = [...el.childNodes].filter(x => x.nodeType === 3 && x.textContent.trim()).map(x => x.textContent.trim()).join(' ');
    if (own) rec.text = own;
    const st = {};
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') st.bg = cs.backgroundColor;
    if (cs.backgroundImage && cs.backgroundImage !== 'none') st.bgi = cs.backgroundImage.slice(0, 500);
    if (cs.borderRadius && cs.borderRadius !== '0px') st.br = cs.borderRadius;
    if (cs.borderWidth && cs.borderWidth !== '0px') { st.bw = cs.borderWidth; st.bc = cs.borderColor; st.bs = cs.borderStyle; }
    if (cs.opacity && cs.opacity !== '1') st.op = cs.opacity;
    if (cs.color) st.clr = cs.color;
    if (cs.zIndex && cs.zIndex !== 'auto') st.zi = cs.zIndex;
    if (cs.overflow && cs.overflow !== 'visible') st.ovf = cs.overflow;
    if (cs.boxShadow && cs.boxShadow !== 'none') st.bsh = cs.boxShadow;
    if (cs.filter && cs.filter !== 'none') st.flt = cs.filter;
    if (cs.clipPath && cs.clipPath !== 'none') st.cp = cs.clipPath;
    if (cs.mask && cs.mask !== 'none' && cs.mask !== '') st.mk = cs.mask;
    if (cs.transform && cs.transform !== 'none') st.tf = cs.transform;
    if (rec.text) { st.fs = cs.fontSize; st.fw = cs.fontWeight; st.ta = cs.textAlign; st.lh = cs.lineHeight; st.ff = cs.fontFamily; }
    if (Object.keys(st).length) rec.st = st;
    const tag = rec.tag;
    if (tag === 'svg') rec.svg = el.outerHTML;
    if (tag === 'img') rec.img = el.getAttribute('src') || '';
    nodes.push(rec);
    if (tag === 'svg') return;
    for (const ch of el.children) walk(ch, idx, depth + 1);
  }
  walk(vp, null, 0);
  const cjk = (vp.textContent||'').match(/[\\u4e00-\\u9fff]/g);
  return { scale: +sx.toFixed(3), screenW: +brr.width.toFixed(1),
    board: { w: vp.offsetWidth, h: vp.offsetHeight, cjk: cjk ? cjk.length : 0 },
    name: (vp.closest('[data-cid],[data-name]')||{}).getAttribute?.('data-name') || vp.getAttribute('data-cid'),
    pkgBase: baseUrl, nodes };
})()`;
const data = await evalJS(PICK);
if (!data || data.err || data.error) { console.error('提取失败:', JSON.stringify(data)); c.close(); process.exit(1); }

const doc = {
  meta: { tool: 'mockingbot-to-html/extract-board.mjs', port: PORT, generatedAt: new Date().toISOString() },
  page: { cid: CID, name: data.name || CID, board: data.board, pkgBase: data.pkgBase, nodes: data.nodes },
};
fs.writeFileSync(OUT, JSON.stringify(doc, null, 1));
const ns = data.nodes;
console.log(JSON.stringify({ ok: true, cid: CID, name: data.name, board: data.board,
  nodes: ns.length, text: ns.filter(n => n.text).length, svg: ns.filter(n => n.svg).length,
  img: ns.filter(n => n.img).length, named: ns.filter(n => n.name).length }));
c.close();
