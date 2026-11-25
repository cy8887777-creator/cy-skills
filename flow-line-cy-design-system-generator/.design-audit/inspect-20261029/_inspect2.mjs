import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'C:/Users/admin/.claude/skills/design-system-generator/.design-audit/inspect-20261029';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const profile = fs.mkdtempSync(path.join(process.env.TEMP, 'cdp2-'));
const chrome = spawn(CHROME, ['--headless=new','--disable-gpu','--no-first-run','--hide-scrollbars','--remote-debugging-port=0',`--user-data-dir=${profile}`,'about:blank'], { stdio: ['ignore','ignore','pipe'] });
const wsUrl = await new Promise((res, rej) => {
  let buf = ''; const t = setTimeout(() => rej(new Error('url timeout')), 20000);
  chrome.stderr.on('data', (d) => { buf += String(d); const m = buf.match(/ws:\/\/[^\s]+/); if (m) { clearTimeout(t); res(m[0].trim()); } });
});
const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = () => rej(new Error('ws')); });
let mid = 0; const pend = new Map(); const evq = [];
ws.onmessage = (e) => { const m = JSON.parse(e.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } else if (m.method) evq.push(m); };
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const id = ++mid;
  pend.set(id, (m) => m.error ? rej(new Error(method + ' ' + JSON.stringify(m.error))) : res(m.result));
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
async function waitEvent(method, sessionId, timeout = 30000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) { const i = evq.findIndex((m) => m.method === method && m.sessionId === sessionId); if (i >= 0) return evq.splice(i, 1)[0]; await sleep(50); }
  throw new Error('timeout ' + method);
}
const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);

async function open(url, dsf) {
  await send('Page.navigate', { url }, sessionId);
  await waitEvent('Page.loadEventFired', sessionId);
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: dsf, mobile: false }, sessionId);
  await sleep(800);
  return async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)).result.value;
}
async function shot(file, clip, scale) {
  const c = { x: clip.x, y: clip.y, width: clip.width ?? clip.w, height: clip.height ?? clip.h, scale: scale || 1 };
  const s = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: c }, sessionId);
  fs.writeFileSync(path.join(OUT, file), Buffer.from(s.data, 'base64'));
  console.log('[shot]', file, JSON.stringify(c));
}

// PRODUCT
const ev = await open('file:///C:/Users/admin/.claude/skills/design-system-generator/self-design/design-system.html', 1);
await shot('product-viewport.png', { x: 0, y: 0, width: 1440, height: 1000 }); // sidebar + hero first screen
const glassStage = await ev(`(()=>{const s=[...document.querySelectorAll('#s11 .comp-stage')].find(x=>x.textContent.includes('玻璃卡'));const b=s.getBoundingClientRect();return{x:b.left+scrollX-16,y:b.top+scrollY-16,w:b.width+32,h:b.height+32};})()`);
await shot('product-glass-zoom.png', glassStage, 2);
const focRect = await ev(`(()=>{const s=[...document.querySelectorAll('#s11 span')].find(x=>x.textContent.trim()==='已聚焦态');const b=s.getBoundingClientRect();return{x:b.left+scrollX-30,y:b.top+scrollY-30,w:b.width+60,h:b.height+60};})()`);
await shot('product-focus-zoom.png', focRect, 3);

// CASE
const ev2 = await open('file:///C:/Users/admin/.claude/skills/design-system-generator/data/case/design-system.case.html', 1);
await shot('case-viewport.png', { x: 0, y: 0, width: 1440, height: 1000 });
const phone = await ev2(`(()=>{const e=document.querySelector('[style*="width:375px;height:812px"]');const b=e.getBoundingClientRect();return{x:b.left+scrollX-16,y:b.top+scrollY-16,w:b.width+32,h:b.height+32};})()`);
await shot('case-phone-zoom.png', phone, 1);
const caseBtn = await ev2(`(()=>{const s=[...document.querySelectorAll('#s11 > div > div')].find(x=>x.textContent.includes('1. 按钮组'));const b=s.getBoundingClientRect();return{x:b.left+scrollX-16,y:b.top+scrollY-16,w:b.width+32,h:Math.min(b.height+32,3000)};})()`);
await shot('case-btn-card-zoom.png', caseBtn, 1);

try { await send('Browser.close'); } catch (e) {}
chrome.kill();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
