// ui_audit — 编辑器版产物轻量机检走查（自包含，无引擎依赖）
// 凝练自主管线 walkthrough 机检核心探针的可自实现子集：对比度/字号下限/横向溢出/遮挡/断图。
// 用法：node ui_audit.mjs <产物index.html> [--out findings.json] [--screens id1,id2] [--min-contrast 4.5] [--password 12345678]
// 退出码：0=无 P1；1=存在 P1；2=用法或环境错误。
import path from 'node:path';
import fs from 'node:fs';
import { pathToFileURL } from 'node:url';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

/* playwright 三级探测（与 verify-interactions.mjs 同构） */
function loadPw() {
  const tryReq = p => { try { return require(p); } catch (_) { return null; } };
  let pw = tryReq('playwright');
  if (!pw && process.env.PLAYWRIGHT_MODULE_PATH) pw = tryReq(path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'playwright'));
  if (!pw) { const g = path.join(process.env.APPDATA || '', 'npm', 'node_modules'); pw = tryReq(path.join(g, 'playwright')); }
  if (!pw) { console.error('FAIL playwright not resolvable (local / PLAYWRIGHT_MODULE_PATH / npm global)——机检不可用，降级 AI 规则审全开并在交付说明声明'); process.exit(2); }
  return pw;
}

function arg(name, def) { const i = process.argv.indexOf('--' + name); return i > 0 ? process.argv[i + 1] : def; }
const DOC = arg('src') || process.argv[2];
if (!DOC) { console.error('usage: node ui_audit.mjs <产物index.html> [--out findings.json] [--screens id1,id2] [--min-contrast 4.5]'); process.exit(2); }
const OUT = arg('out') || '';
const MIN_CONTRAST = parseFloat(arg('min-contrast', '4.5'));
const PASSWORD = arg('password', '12345678');
const SCREENS = (arg('screens') || '').split(',').map(s => s.trim()).filter(Boolean);

/* ---------- 探针（在页面内执行） ---------- */
const AUDIT_FN = `
(async (MIN_CONTRAST) => {
  const sleep = ms => new Promise(r => setTimeout(r, ms));
  const findings = [];
  const selOf = el => {
    if (el.dataset && el.dataset.eid) return '[data-eid=' + el.dataset.eid + ']';
    let s = el.tagName ? el.tagName.toLowerCase() : 'node';
    if (el.id) s += '#' + el.id;
    let p = el.parentElement, depth = 0;
    while (p && p.classList && depth < 3) { if (p.dataset && p.dataset.screen) { s = '[data-screen=' + p.dataset.screen + '] ' + s; break; } p = p.parentElement; depth++; }
    return s;
  };
  /* 亮度的相对比值（WCAG 2.x） */
  const lum = (r, g, b) => {
    const f = v => { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
  };
  const parseRGB = str => { const m = str && str.match(/rgba?\\(([\\d.]+),\\s*([\\d.]+),\\s*([\\d.]+)(?:,\\s*([\\d.]+))?\\)/); return m ? [+m[1], +m[2], +m[3], m[4] === undefined ? 1 : +m[4]] : null; };
  const effBg = el => {
    let cur = el;
    while (cur && cur !== document.documentElement) {
      const st = getComputedStyle(cur);
      const bg = parseRGB(st.backgroundColor);
      if (bg && bg[3] > 0.85) return bg;
      cur = cur.parentElement;
    }
    return [255, 255, 255, 1];
  };
  const contrast = (fg, bg) => {
    const l1 = lum(fg[0], fg[1], fg[2]), l2 = lum(bg[0], bg[1], bg[2]);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };
  /* 文本叶元素（含直接非空文本） */
  const textEls = [];
  document.querySelectorAll('.screen.on *').forEach(el => {
    if (el.closest('script,style,noscript')) return;
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden' || parseFloat(st.opacity) < 0.15) return;
    const own = [...el.childNodes].filter(n => n.nodeType === 3 && n.textContent.trim()).length;
    if (own) textEls.push(el);
  });
  /* 1. 对比度探针 */
  for (const el of textEls) {
    const st = getComputedStyle(el);
    const fg = parseRGB(st.color); if (!fg) continue;
    const bg = effBg(el);
    const ratio = contrast(fg, bg);
    const px = parseFloat(st.fontSize);
    const bold = parseInt(st.fontWeight) >= 600 || st.fontWeight === 'bold';
    const large = px >= 24 || (px >= 18.66 && bold);
    const need = large ? 3 : MIN_CONTRAST;
    if (ratio < need) findings.push({ rule: 'contrast', severity: ratio < 3 ? 'P1' : 'P2', page: (el.closest('[data-screen]') || {}).dataset?.screen || '?', selector: selOf(el), evidence: '对比度 ' + ratio.toFixed(2) + ':1 < ' + need + ':1（' + px + 'px ' + (bold ? 'bold' : 'normal') + '）文本 "' + el.textContent.trim().slice(0, 18) + '"' });
  }
  /* 2. 字号下限 */
  for (const el of textEls) {
    const px = parseFloat(getComputedStyle(el).fontSize);
    if (px < 11) findings.push({ rule: 'font-size', severity: 'P2', page: (el.closest('[data-screen]') || {}).dataset?.screen || '?', selector: selOf(el), evidence: '字号 ' + px + 'px < 11px 下限，文本 "' + el.textContent.trim().slice(0, 18) + '"' });
  }
  /* 3. 横向溢出（横向滚动容器为合法设计，排除） */
  document.querySelectorAll('.screen.on *').forEach(el => {
    if (el.closest('script,style')) return;
    const st = getComputedStyle(el);
    if (st.display === 'none') return;
    if (/(auto|scroll)/.test(st.overflowX)) return;
    if (el.scrollWidth > el.clientWidth + 2 && el.clientWidth > 0) findings.push({ rule: 'overflow-x', severity: 'P1', page: (el.closest('[data-screen]') || {}).dataset?.screen || '?', selector: selOf(el), evidence: '横向溢出 ' + (el.scrollWidth - el.clientWidth) + 'px（scrollWidth ' + el.scrollWidth + ' > clientWidth ' + el.clientWidth + '）' });
  });
  /* 4. 交互元素遮挡 */
  const inter = document.querySelectorAll('.screen.on button, .screen.on a[href], .screen.on [data-on], .screen.on [data-eid]');
  const seen = new Set();
  inter.forEach(el => {
    if (seen.has(el)) return; seen.add(el);
    const st = getComputedStyle(el);
    if (st.display === 'none' || st.visibility === 'hidden') return;
    const r = el.getBoundingClientRect();
    if (r.width < 4 || r.height < 4) return;
    const cx = r.left + r.width / 2, cy = r.top + r.height / 2;
    if (cx < 0 || cy < 0 || cx > innerWidth || cy > innerHeight) return;
    const top = document.elementFromPoint(cx, cy);
    if (top && top !== el && !el.contains(top) && !top.contains(el)) {
      const st2 = getComputedStyle(top);
      if (st2.pointerEvents !== 'none') findings.push({ rule: 'occlusion', severity: 'P1', page: (el.closest('[data-screen]') || {}).dataset?.screen || '?', selector: selOf(el), evidence: '中心点被 ' + (top.tagName.toLowerCase() + (top.className ? '.' + String(top.className).split(' ')[0] : '')) + ' 遮挡' });
    }
  });
  /* 5. 断图 */
  document.querySelectorAll('.screen.on img').forEach(img => {
    if (img.complete && img.naturalWidth === 0) findings.push({ rule: 'broken-img', severity: 'P1', page: (img.closest('[data-screen]') || {}).dataset?.screen || '?', selector: selOf(img), evidence: '图片加载失败 src=' + (img.getAttribute('src') || '').slice(0, 60) });
  });
  await sleep(50);
  return findings;
})
`;

/* ---------- 主流程 ---------- */
const { chromium } = loadPw();
const fileUrl = p => 'file:///' + encodeURI(p.replace(/\\/g, '/')).replace(/^file:\/\/\//, '');
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 900, height: 1400 } });
await page.goto(fileUrl(path.resolve(DOC)), { waitUntil: 'networkidle', timeout: 60000 });
await page.waitForTimeout(1000);

/* 口令进入 */
const pwd = page.locator('input[type="password"]').first();
if (await pwd.isVisible().catch(() => false)) { await pwd.fill(PASSWORD); await page.keyboard.press('Enter'); await page.waitForTimeout(1200); }
/* 关 T18 绑定引导 + notePanel */
await page.evaluate(() => {
  const skip = document.querySelector('dialog[open] #bdSkip');
  if (skip) skip.click();
  const np = document.querySelector('#npClose');
  if (np && document.getElementById('notePanel') && !document.getElementById('notePanel').hidden) np.click();
});
await page.waitForTimeout(400);

/* 屏清单（默认排除占位屏：data-name 含「待迁移」——裁剪试点合法产物，不计正式 findings；--include-placeholders 开） */
let screens = SCREENS;
if (!screens.length) {
  const incPl = process.argv.includes('--include-placeholders');
  screens = await page.evaluate((inc) => [...document.querySelectorAll('.screen[data-screen]')]
    .filter(s => inc || !(s.getAttribute('data-name') || '').includes('待迁移'))
    .map(s => s.getAttribute('data-screen')), incPl);
  const skipped = await page.evaluate(() => [...document.querySelectorAll('.screen[data-name*="待迁移"]')].length);
  if (skipped && !incPl) console.log('已排除占位屏', skipped, '屏（--include-placeholders 可计入）');
}
console.log('屏数:', screens.length, '对比度阈值:', MIN_CONTRAST + ':1');

const all = [];
for (const sid of screens) {
  await page.evaluate((id) => {
    document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.getAttribute('data-screen') === id));
    window.scrollTo(0, 0);
  }, sid);
  await page.waitForTimeout(300);
  const f = await page.evaluate('(' + AUDIT_FN + ')(' + MIN_CONTRAST + ')');
  all.push(...f);
  const p1 = f.filter(x => x.severity === 'P1').length;
  console.log('  ' + sid + ': findings ' + f.length + '（P1 ' + p1 + '）');
}

const p1n = all.filter(x => x.severity === 'P1').length;
const summary = { screens: screens.length, total: all.length, P1: p1n, P2: all.length - p1n, findings: all };
if (OUT) { fs.writeFileSync(path.resolve(OUT), JSON.stringify(summary, null, 2), 'utf-8'); console.log('台账: ' + path.resolve(OUT)); }
console.log('汇总: findings ' + all.length + '（P1 ' + p1n + ' / P2 ' + (all.length - p1n) + '）');
console.log(p1n > 0 ? 'FAIL：存在 ' + p1n + ' 个 P1，修完复跑清零才准进转化' : 'PASS：机检无 P1');
await browser.close();
process.exit(p1n > 0 ? 1 : 0);

