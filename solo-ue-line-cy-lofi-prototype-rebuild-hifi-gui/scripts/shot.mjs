// shot.mjs —— 分区截图（stage 相对坐标，clip 整数化；只供人工验收看，禁止当测试依据）
// 用法: node shot.mjs <page.html> <out.png> <x,y,w,h> [port=9224]
// 坐标相对 .stage 左上角。全页截图: x,y,w,h 传 0,0,-1,-1
// 坑：clip 必须整数且在 viewport 内，否则 captureScreenshot 返回 undefined
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';

const [page, out, rectArg, portArg] = process.argv.slice(2);
if (!page || !out || !rectArg) { console.error('用法: node shot.mjs <page.html> <out.png> <x,y,w,h> [port]'); process.exit(2); }
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
await new Promise(r => setTimeout(r, 2500));

const st = JSON.parse((await send('Runtime.evaluate', { returnByValue: true, expression: "JSON.stringify((()=>{const s=document.querySelector('.stage').getBoundingClientRect();return {x:Math.round(s.x),y:Math.round(s.y),w:Math.round(s.width),h:Math.round(s.height)}})())" })).result.result.value);
let [x, y, w, h] = rectArg.split(',').map(Number);
let clip;
if (w < 0) clip = { x: st.x, y: st.y, width: st.w, height: st.h };
else clip = { x: st.x + Math.round(x), y: st.y + Math.round(y), width: Math.round(w), height: Math.round(h) };
const shot = await send('Page.captureScreenshot', { format: 'png', clip: { ...clip, scale: 1 } });
if (!shot || !shot.result) { console.error('截图失败: clip 超出视口? ' + JSON.stringify(clip)); process.exit(1); }
fs.writeFileSync(out, Buffer.from(shot.result.data, 'base64'));
console.log('saved', out, JSON.stringify(clip));
ws.close(); process.exit(0);
