import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const CHROME = 'C:/Program Files/Google/Chrome/Application/chrome.exe';
const OUT = 'C:/Users/admin/.claude/skills/design-system-generator/.design-audit/inspect-20261029';
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const profile = fs.mkdtempSync(path.join(process.env.TEMP, 'cdp-'));
const chrome = spawn(CHROME, [
  '--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--hide-scrollbars', '--force-device-scale-factor=1', '--remote-debugging-port=0',
  `--user-data-dir=${profile}`, 'about:blank'
], { stdio: ['ignore', 'ignore', 'pipe'] });

const wsUrl = await new Promise((res, rej) => {
  let buf = '';
  const t = setTimeout(() => rej(new Error('devtools url timeout')), 20000);
  chrome.stderr.on('data', (d) => {
    buf += String(d);
    const m = buf.match(/ws:\/\/[^\s]+/);
    if (m) { clearTimeout(t); res(m[0].trim()); }
  });
  chrome.on('exit', (c) => rej(new Error('chrome exited early: ' + c)));
});

const ws = new WebSocket(wsUrl);
await new Promise((res, rej) => { ws.onopen = res; ws.onerror = (e) => rej(new Error('ws error')); });
let mid = 0; const pend = new Map(); const evq = [];
ws.onmessage = (e) => {
  const m = JSON.parse(e.data);
  if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } else if (m.method) evq.push(m);
};
const send = (method, params = {}, sessionId) => new Promise((res, rej) => {
  const id = ++mid;
  pend.set(id, (m) => m.error ? rej(new Error(method + ' ' + JSON.stringify(m.error))) : res(m.result));
  ws.send(JSON.stringify({ id, method, params, ...(sessionId ? { sessionId } : {}) }));
});
async function waitEvent(method, sessionId, timeout = 30000) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    const i = evq.findIndex((m) => m.method === method && m.sessionId === sessionId);
    if (i >= 0) return evq.splice(i, 1)[0];
    await sleep(60);
  }
  throw new Error('event timeout: ' + method);
}

const { targetId } = await send('Target.createTarget', { url: 'about:blank' });
const { sessionId } = await send('Target.attachToTarget', { targetId, flatten: true });
await send('Page.enable', {}, sessionId);
await send('Runtime.enable', {}, sessionId);

async function inspect(url, name, dsf, probeExpr, clips) {
  await send('Page.navigate', { url }, sessionId);
  await waitEvent('Page.loadEventFired', sessionId);
  await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 900, deviceScaleFactor: dsf, mobile: false }, sessionId);
  await sleep(1000);
  const evalJs = async (expr) => (await send('Runtime.evaluate', { expression: expr, returnByValue: true }, sessionId)).result.value;
  const meta = await evalJs(probeExpr);
  // full page
  const full = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }, sessionId);
  fs.writeFileSync(path.join(OUT, `${name}-full.png`), Buffer.from(full.data, 'base64'));
  // selector clips
  for (const c of clips) {
    const r = await evalJs(`(()=>{const e=document.querySelector(${JSON.stringify(c.sel)});if(!e)return null;const b=e.getBoundingClientRect();const H=document.documentElement.scrollHeight;return{x:Math.max(0,b.left+scrollX-24),y:Math.max(0,b.top+scrollY-24),w:Math.min(b.width+48,1439),h:Math.min(b.height+48,14800)};})()`);
    if (!r) { console.log(`  [skip] ${name}/${c.label}: ${c.sel} not found`); continue; }
    try {
      const shot = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: r.x, y: r.y, width: r.w, height: r.h, scale: 1 } }, sessionId);
      fs.writeFileSync(path.join(OUT, `${name}-${c.label}.png`), Buffer.from(shot.data, 'base64'));
      console.log(`  [shot] ${name}/${c.label} ${Math.round(r.w)}x${Math.round(r.h)}`);
    } catch (e) { console.log(`  [fail] ${name}/${c.label}: ${e.message}`); }
  }
  console.log(`[done] ${name} pageHeight=${meta.pageHeight}`);
  return meta;
}

const PROBE_PRODUCT = `(() => {
  const cs = (e,p,s) => getComputedStyle(e,s||null).getPropertyValue(p);
  const q = (s) => document.querySelector(s);
  const glass = [...document.querySelectorAll('#s11 [style*="backdrop-filter"]')];
  const foc = [...document.querySelectorAll('#s11 span')].find(e => e.textContent.trim() === '已聚焦态');
  const h1 = q('.hero h1');
  const sl = q('.spec-label');
  return {
    pageHeight: document.documentElement.scrollHeight,
    grid: { size: cs(document.body,'background-size','::before'), bg: cs(document.body,'background-image','::before').slice(0,90), pos: cs(document.body,'position','::before'), z: cs(document.body,'z-index','::before') },
    sidebar: { bg: cs(q('.sidebar'),'background-color'), w: q('.sidebar').getBoundingClientRect().width, navCount: document.querySelectorAll('.nav a').length, first: q('.nav a').textContent.trim(), last: [...document.querySelectorAll('.nav a')].pop().textContent.trim() },
    hero: { tag: q('.hero-spec .tag') && q('.hero-spec .tag').textContent, metaCells: document.querySelectorAll('.hero-meta > div').length, metaKeys: [...document.querySelectorAll('.hero-meta .k')].map(e=>e.textContent), h1ff: cs(h1,'font-family'), h1size: cs(h1,'font-size'), serifInstalled: document.fonts.check('16px "Noto Serif SC"') },
    chNums: [...document.querySelectorAll('.ch-num')].map(e=>e.textContent.trim()).join(''),
    chNum: { strokeW: cs(q('.ch-num'),'-webkit-text-stroke-width'), strokeC: cs(q('.ch-num'),'-webkit-text-stroke-color'), fill: cs(q('.ch-num'),'color'), ff: cs(q('.ch-num'),'font-family') },
    chHeads: document.querySelectorAll('.ch-head').length,
    chIntros: document.querySelectorAll('.ch-intro').length,
    specLabel: { content: cs(sl,'content','::after'), h: cs(sl,'height','::after'), bg: cs(sl,'background-color','::after'), flex: cs(sl,'flex','::after') },
    swatch: { n: document.querySelectorAll('.swatch').length, tag: q('.swatch') && q('.swatch').tagName, cursor: q('.swatch') && cs(q('.swatch'),'cursor'), dataHex: q('.swatch') && q('.swatch').dataset.hex },
    ch11: {
      stages: document.querySelectorAll('#s11 .comp-stage').length,
      stageBgImg: cs(q('#s11 .comp-stage'),'background-image').slice(0,150),
      realButtons: document.querySelectorAll('#s11 button').length,
      realInputs: document.querySelectorAll('#s11 input, #s11 textarea, #s11 select').length,
      spanButtons: [...document.querySelectorAll('#s11 span')].filter(e => /^padding:\\s*7px 18px/.test(e.getAttribute('style')||'')).length,
      glassN: glass.length,
      glassInfo: glass.map(e => cs(e,'backdrop-filter') + ' | ' + cs(e,'background-color') + ' | ' + (e.textContent.trim().slice(0,14))),
      focBorder: foc ? cs(foc,'border-color') : 'n/a',
      focShadow: foc ? cs(foc,'box-shadow').slice(0,60) : 'n/a',
      tagchips: document.querySelectorAll('#s11 .tagchip').length
    },
    footer: !!q('footer'),
    title: document.title
  };
})()`;

const PROBE_CASE = `(() => {
  const cs = (e,p,s) => getComputedStyle(e,s||null).getPropertyValue(p);
  const q = (s) => document.querySelector(s);
  const glass = [...document.querySelectorAll('[style*="backdrop-filter"]')];
  return {
    pageHeight: document.documentElement.scrollHeight,
    grid: { size: cs(document.body,'background-size','::before'), bg: cs(document.body,'background-image','::before').slice(0,90) },
    sidebar: { bg: cs(q('.sidebar'),'background-color'), navCount: document.querySelectorAll('.nav a').length },
    heroMeta: [...document.querySelectorAll('.hero-meta .k')].map(e=>e.textContent),
    chapters: [...document.querySelectorAll('.ch-head h2')].map(h => h.childNodes[0].textContent.trim() + '/' + (h.querySelector('.en') && h.querySelector('.en').textContent)),
    ch11Cards: [...document.querySelectorAll('#s11 b')].filter(b => /^\\d+\\./.test(b.textContent.trim())).map(b => b.textContent.trim().slice(0,20)),
    ch11RealButtons: document.querySelectorAll('#s11 button').length,
    ch11RealInputs: document.querySelectorAll('#s11 input').length,
    tables: document.querySelectorAll('table').length,
    phones: document.querySelectorAll('[style*="width:375px;height:812px"]').length,
    footer: q('footer') ? q('footer').textContent.trim().slice(0,120) : null,
    motion: [...document.querySelectorAll('#s10 .motion-row')].length,
    assets: document.querySelectorAll('figure.thumb-cell').length,
    glassN: glass.length,
    fontDisplay: cs(q('.hero h1'),'font-family'),
    serifCheck: document.fonts.check('16px "Noto Sans SC"'),
    swatch: { n: document.querySelectorAll('.swatch').length, tag: q('.swatch') && q('.swatch').tagName, dataHex: q('.swatch') && q('.swatch').dataset.hex },
    title: document.title
  };
})()`;

const results = {};
results.product = await inspect('file:///C:/Users/admin/.claude/skills/design-system-generator/self-design/design-system.html', 'product', 1, PROBE_PRODUCT, [
  { label: 'top', sel: '.hero' },
  { label: 's1', sel: '#s1' },
  { label: 's5', sel: '#s5' },
  { label: 's11', sel: '#s11' },
  { label: 's14', sel: '#s14' }
]);
results.case = await inspect('file:///C:/Users/admin/.claude/skills/design-system-generator/data/case/design-system.case.html', 'case', 0.75, PROBE_CASE, [
  { label: 'top', sel: '.hero' },
  { label: 's2', sel: '#s2' },
  { label: 's11', sel: '#s11' },
  { label: 'footer', sel: 'footer.doc-footer' }
]);

fs.writeFileSync(path.join(OUT, 'probes.json'), JSON.stringify(results, null, 2));
console.log('PROBES=' + JSON.stringify(results));

try { await send('Browser.close'); } catch (e) {}
chrome.kill();
try { fs.rmSync(profile, { recursive: true, force: true }); } catch (e) {}
process.exit(0);
