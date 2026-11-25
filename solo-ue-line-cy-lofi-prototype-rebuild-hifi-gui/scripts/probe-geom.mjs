// probe-geom.mjs —— 几何实测探针：指定 data-idx 层列表的渲染盒（stage 相对坐标）+ 文字精确宽
// 用法: node probe-geom.mjs <page.html> <idx1,idx2,...> [port=9224]
// 用途：改版前拿现状、改版后核对；对齐/间距/居中全部用这里的数字算，不目测
import { pathToFileURL } from 'node:url';

const [page, idxArg, portArg] = process.argv.slice(2);
if (!page || !idxArg) { console.error('用法: node probe-geom.mjs <page.html> <idx,...> [port]'); process.exit(2); }
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
await send('Emulation.setDeviceMetricsOverride', { width: 423, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 2000));

const expr = `JSON.stringify((() => {
  const st = document.querySelector('.stage').getBoundingClientRect();
  const out = {};
  for (const i of ${JSON.stringify(idxArg.split(','))}) {
    const d = document.querySelector('[data-idx="' + i + '"]');
    if (!d) { out[i] = null; continue; }
    const cs = getComputedStyle(d);
    const b = d.getBoundingClientRect();
    const r = { display: cs.display, x: +(b.x - st.x).toFixed(1), y: +(b.y - st.y).toFixed(1), w: +b.width.toFixed(1), h: +b.height.toFixed(1) };
    // 文字精确渲染宽（Range 量字）——排间距/居中必须用它，层框宽 ≠ 文字宽
    for (const n of d.childNodes) {
      if (n.nodeType === 3 && n.textContent.trim()) {
        const rg = document.createRange(); rg.selectNodeContents(n);
        const rb = rg.getBoundingClientRect();
        r.textX = +(rb.x - st.x).toFixed(1); r.textW = +rb.width.toFixed(1);
        break;
      }
    }
    if (cs.fontSize) r.font = cs.fontSize + '/' + cs.fontWeight;
    out[i] = r;
  }
  return out;
})())`;
const res = await send('Runtime.evaluate', { returnByValue: true, expression: expr });
const data = JSON.parse(res.result.result.value);
for (const [k, v] of Object.entries(data)) console.log(k, v ? JSON.stringify(v) : '(缺失)');
ws.close(); process.exit(0);
