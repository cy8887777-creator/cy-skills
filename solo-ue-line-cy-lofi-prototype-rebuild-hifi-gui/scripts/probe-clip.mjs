// probe-clip.mjs —— 全页「显示不全」扫描（三维度，纯数字判定，不用视觉模型）
// A) svg/img 渲染盒超出带 overflow:hidden 的父层（=被裁切）
// A2) img 无 overflow 保护但超出自身盒
// B) 可见层越出 stage 画布边界
// C) 文字 scrollWidth 溢出
// 用法: node probe-clip.mjs <page.html> [port=9224]
// 输出清零 = 通过；唯一合法豁免：跑马灯文字层嵌在 overflow 窗口内、自身 bbox 越界（滚动原理）
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const [page, portArg] = process.argv.slice(2);
if (!page) { console.error('用法: node probe-clip.mjs <page.html> [port]'); process.exit(2); }
const PORT = +(portArg || 9224);
const url = pathToFileURL(page.replace(/\\/g, '/')).href;

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const ws = new WebSocket(targets.find(x => x.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', ev => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const i = ++id; pend.set(i, resolve); ws.send(JSON.stringify({ id: i, method, params }));
  setTimeout(() => { if (pend.has(i)) { pend.delete(i); reject(new Error('timeout ' + method)); } }, 20000);
});
await send('Page.enable');
// 视口必须 > 画布宽 + body padding 两侧（默认给 423×900；画布更宽的页面自行加大），否则 stage 被 flex 压缩、坐标全作废
await send('Emulation.setDeviceMetricsOverride', { width: 423, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 2000));

const res = await send('Runtime.evaluate', { returnByValue: true, expression: `JSON.stringify((() => {
  const stage = document.querySelector('.stage').getBoundingClientRect();
  const out = { clipped: [], outside: [], textOver: [] };
  for (const el of document.querySelectorAll('[data-idx] img, [data-idx] svg')) {
    const holder = el.closest('[data-idx]');
    const cs = getComputedStyle(holder);
    if (cs.display === 'none') continue;
    if (!/hidden|clip/.test(cs.overflow + cs.overflowX + cs.overflowY)) continue;
    const hb = holder.getBoundingClientRect(), eb = el.getBoundingClientRect();
    const over = { l: +(hb.left - eb.left).toFixed(1), r: +(eb.right - hb.right).toFixed(1),
      t: +(hb.top - eb.top).toFixed(1), b: +(eb.bottom - hb.bottom).toFixed(1) };
    if (over.l < -0.5 || over.r < -0.5 || over.t < -0.5 || over.b < -0.5)
      out.clipped.push({ idx: holder.dataset.idx, tag: el.tagName, over,
        holder: [+(hb.width).toFixed(0), +(hb.height).toFixed(0)], el: [+(eb.width).toFixed(1), +(eb.height).toFixed(1)] });
  }
  for (const im of document.querySelectorAll('[data-idx] img')) {
    const holder = im.closest('[data-idx]');
    if (getComputedStyle(holder).display === 'none') continue;
    const hb = holder.getBoundingClientRect(), eb = im.getBoundingClientRect();
    const over = { l: +(hb.left - eb.left).toFixed(1), r: +(eb.right - hb.right).toFixed(1),
      t: +(hb.top - eb.top).toFixed(1), b: +(eb.bottom - hb.bottom).toFixed(1) };
    if (over.l < -0.5 || over.r < -0.5 || over.t < -0.5 || over.b < -0.5)
      out.clipped.push({ idx: holder.dataset.idx, tag: 'IMG-noClip', over });
  }
  for (const d of document.querySelectorAll('.stage [data-idx]')) {
    const cs = getComputedStyle(d);
    if (cs.display === 'none' || +cs.opacity === 0) continue;
    const b = d.getBoundingClientRect();
    if (b.width === 0 && b.height === 0) continue;
    const x = +(b.x - stage.x).toFixed(1), y = +(b.y - stage.y).toFixed(1);
    if (x < -0.5 || y < -0.5 || x + b.width > stage.width + 0.5 || y + b.height > stage.height + 0.5)
      out.outside.push({ idx: d.dataset.idx, x, y, w: +b.width.toFixed(1), h: +b.height.toFixed(1) });
  }
  for (const d of document.querySelectorAll('[data-idx]')) {
    if (getComputedStyle(d).display === 'none') continue;
    const direct = [...d.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
    if (!direct) continue;
    if (getComputedStyle(d).whiteSpace === 'nowrap' && d.scrollWidth > d.clientWidth + 2)
      out.textOver.push({ idx: d.dataset.idx, cw: d.clientWidth, sw: d.scrollWidth, t: d.textContent.trim().slice(0, 20) });
  }
  return out;
})())` });
const data = JSON.parse(res.result.result.value);
console.log('== A. 图标被裁切（svg/img 超出 overflow:hidden 容器）==');
data.clipped.length ? data.clipped.forEach(c => console.log(`idx=${c.idx} [${c.tag}] 超出 l${c.over.l} r${c.over.r} t${c.over.t} b${c.over.b} 容器${c.holder || ''} 元素${c.el || ''}`)) : console.log('OK 无');
console.log('== B. 越出 stage 边界 ==');
data.outside.length ? data.outside.forEach(o => console.log(`idx=${o.idx} @${o.x},${o.y} ${o.w}×${o.h}`)) : console.log('OK 无');
console.log('== C. 文字溢出 ==');
data.textOver.length ? data.textOver.forEach(o => console.log(`idx=${o.idx} 「${o.t}」 框${o.cw} 实${o.sw}`)) : console.log('OK 无');
ws.close(); process.exit(0);
