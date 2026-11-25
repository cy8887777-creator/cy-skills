// acc_covers.mjs — 封面供给链回归（面板卡缩略真图断言 + 切卡/真点回归）
//
// 验什么（multi-style-spec.md §八 封面供给 + 用户裁决 2026-11-23"面板卡缩略禁色板条降级"，
//         沉淀自 reskin-e2e/tools/acc_cover.mjs）：
//   C1 面板卡 img 断言：风格面板内每个非内置包一张真图（img.ed-sp-shot 数 = 卡数，data URI 真渲染有尺寸）
//   C2 零色板条：.ed-sp-palbar 数 = 0（出现色板条 = 封面链失败降级，硬 FAIL）
//   C3 切卡回归：点注入风格卡 → 左树节点数 = 注入风格屏数（封面注入不破坏 v2 屏集合组）
//   C4 新域真点：注入域首个 goto 元素点击跳转成功
//   C5 切回原风格：树节点数恢复 = 原风格屏数
//   C6 截图证据：打开抽屉拍面板（存 --out-dir）
//
// 怎么跑：
//   node acc_covers.mjs <产物.html> [--out-dir <截图目录>]
//   卡名/屏数从产物 STYLE-PACK 受控块与 DOM 解析，不写死项目
// 输出：[PASS]/[FAIL] 行（供 run_reskin_regression.py 汇总），exit 0=全过 / 1=有 FAIL / 2=环境不可用
//
// 依赖：playwright 三级探测（本地 → PLAYWRIGHT_MODULE_PATH → npm 全局，conversion.md 客户环境降级同口径）；node ≥18
import path from 'path';
import fs from 'fs';
import { createRequire } from 'module';
const require = createRequire(import.meta.url);

// ---- playwright 三级探测（本地 → PLAYWRIGHT_MODULE_PATH → npm 全局） ----
let chromium = null;
const tried = [];
try { ({ chromium } = require('playwright')); tried.push('本地'); } catch (e) { tried.push('本地×'); }
if (!chromium && process.env.PLAYWRIGHT_MODULE_PATH) {
  try { ({ chromium } = require(path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'playwright'))); tried.push('PLAYWRIGHT_MODULE_PATH'); } catch (e) { tried.push('PLAYWRIGHT_MODULE_PATH×'); }
}
if (!chromium) {
  const npmGlobal = path.join(process.env.APPDATA || path.join(process.env.HOME || '', '.npm-global'), 'npm', 'node_modules', 'playwright');
  try { ({ chromium } = require(npmGlobal)); tried.push('npm 全局'); } catch (e) { tried.push('npm 全局×'); }
}
if (!chromium) {
  console.log('[FAIL] 依赖 playwright 三级探测全落空（' + tried.join(' → ') + '）');
  process.exit(2);
}

// ---- 参数 ----
const argFile = process.argv[2];
if (!argFile || !fs.existsSync(argFile)) {
  console.log('[FAIL] 用法: node acc_covers.mjs <产物.html> [--out-dir <截图目录>]；产物不存在: ' + (argFile || '缺'));
  process.exit(2);
}
let outDir = null;
const oi = process.argv.indexOf('--out-dir');
if (oi > 0 && process.argv[oi + 1]) outDir = process.argv[oi + 1];
if (!outDir) outDir = path.join(path.dirname(path.resolve(argFile)), 'qa-shots');
fs.mkdirSync(outDir, { recursive: true });

// ---- 产物解析 ----
const html = fs.readFileSync(argFile, 'utf-8');
let packs = [];
{
  const m = html.match(/<script[^>]*data-block=["']STYLE-PACK["'][^>]*>([\s\S]*?)<\/script>/i);
  if (m) { try { packs = (JSON.parse(m[1]).packs || []).filter(p => !(p.builtin && p.builtin.id)); } catch (e) {} }
}
if (packs.length < 2) {
  console.log('[FAIL] 产物 STYLE-PACK 非内置包 <2——不是双风格回装产物，封面回归不适用');
  process.exit(2);
}
const nameSrc = (packs[0].identity && packs[0].identity.styleName) || packs[0].packId;
const nameInj = (packs[1].identity && packs[1].identity.styleName) || packs[1].packId;
const nPacks = packs.length;
function countScreens(sid) {
  const re = new RegExp('<section\\b[^>]*\\bdata-style-id="' + sid.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '"[^>]*>', 'g');
  return (html.match(re) || []).length;
}
let sidSrc = (html.match(/<section\b[^>]*\bclass="[^"]*\bscreen[^"]*"[^>]*\bdata-style-id="([^"]+)"/) || [])[1] || 'db-main';
const sidInj = (html.match(new RegExp('data-style-id="(db-[A-Za-z0-9_-]+)"', 'g')) || [])
  .map(s => s.replace('data-style-id="', '').replace('"', '')).find(x => x !== sidSrc) || '';
const nSrc = countScreens(sidSrc);
const nInj = sidInj ? countScreens(sidInj) : 0;
console.log('[INFO] 卡: "' + nameSrc + '"(' + sidSrc + '#' + nSrc + ') / "' + nameInj + '"(' + sidInj + '#' + nInj + ')；期待面板真图 ' + nPacks + ' 张');

// ---- 浏览器 ----
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
page.on('pageerror', e => errs.push(String(e).slice(0, 80)));
await page.goto('file:///' + path.resolve(argFile).replace(/\\/g, '/'));
await page.waitForTimeout(1100);
for (const label of ['暂不绑定（仅浏览）', '暂不绑定', '跳过', '以后再说']) {
  const b = await page.$(`text=${label}`);
  if (b) { await b.click().catch(() => {}); break; }
}
await page.waitForTimeout(400);

const results = [];
function judge(item, ok, detail) {
  results.push({ item, ok });
  console.log((ok ? '[PASS] ' : '[FAIL] ') + item + (detail ? ' — ' + detail : ''));
}
async function clickCard(kw) {
  const box = await page.evaluate((kw) => {
    const out = [];
    document.querySelectorAll('div,button,li').forEach(el => {
      const t = el.textContent || '';
      if (t.includes(kw) && t.length < 130 && el.offsetParent) {
        const r = el.getBoundingClientRect();
        if (r.width > 120 && r.height > 50) out.push({ x: r.x + r.width / 2, y: r.y + r.height / 2, w: r.width, h: r.height });
      }
    });
    out.sort((p, q) => (p.w * p.h) - (q.w * q.h));
    return out[0] || null;
  }, kw);
  if (!box) return false;
  await page.mouse.click(box.x, box.y);
  return true;
}
async function openDrawer() {
  await page.click('#btnStyle').catch(() => {});
  await page.waitForTimeout(900);
}
// 幂等开抽屉：#btnStyle 是 toggle，已开再点会关掉
async function ensureDrawer() {
  const open = await page.evaluate(() => {
    const cards = [...document.querySelectorAll('.ed-sp-card, img.ed-sp-shot, .ed-sp-list')];
    return cards.some(c => c.offsetParent || c.getBoundingClientRect().width > 0);
  });
  if (!open) {
    await page.click('#btnStyle').catch(() => {});
    await page.waitForTimeout(900);
  }
  await page.waitForTimeout(200);
}
async function openTab(id) {
  await page.evaluate((id) => {
    const t = [...document.querySelectorAll('#tabs .ed-tab')].find(x => x.getAttribute('data-go') === id);
    if (t) t.click();
  }, id);
  await page.waitForTimeout(600);
}
// 在指定风格屏集内找首个 goto 元素（先当前 on 屏，找不到遍历该风格屏集并切过去）再点击
async function gotoClickIn(sid) {
  const found = await page.evaluate((sid) => {
    const pick = (scr) => {
      for (const el of scr.querySelectorAll('[data-eid][data-on]')) {
        const raw = el.getAttribute('data-on') || '';
        const m = raw.match(/"goto":"([\w-]+)"/) || raw.match(/goto&quot;:&quot;([\w-]+)&quot;/);
        if (m) return { eid: el.getAttribute('data-eid'), target: m[1] };
      }
      return null;
    };
    const on = document.querySelector('#canvas .screen.on');
    if (on && (!sid || on.getAttribute('data-style-id') === sid)) {
      const g = pick(on);
      if (g) return { screen: on.getAttribute('data-screen'), opened: true, eid: g.eid, target: g.target };
    }
    for (const scr of [...document.querySelectorAll('#canvas .screen')]) {
      if (scr.getAttribute('data-style-id') !== sid) continue;
      const g = pick(scr);
      if (g) return { screen: scr.getAttribute('data-screen'), opened: false, eid: g.eid, target: g.target };
    }
    return null;
  }, sid);
  if (!found) return null;
  if (!found.opened) await openTab(found.screen);
  const clicked = await page.evaluate(() => {
    const on = document.querySelector('#canvas .screen.on');
    const el = on && on.querySelector('[data-eid][data-on]');
    if (el) { el.click(); return el.getAttribute('data-eid'); }
    return '';
  });
  return clicked ? { eid: clicked, target: found.target } : null;
}

try {
  // ---- C1/C2 封面断言（抽屉打开态） ----
  await openDrawer();
  const c1 = await page.evaluate(() => {
    const imgs = [...document.querySelectorAll('.ed-sp-card img.ed-sp-shot, img.ed-sp-shot')];
    const bars = [...document.querySelectorAll('.ed-sp-palbar')];
    const info = imgs.map(i => ({ src: (i.getAttribute('src') || '').slice(0, 24), w: i.clientWidth, h: i.clientHeight, visible: !!i.offsetParent }));
    return { imgCount: imgs.length, srcHeads: info.map(i => i.src), dims: info.map(i => i.w + 'x' + i.h), palbarCount: bars.length };
  });
  judge('C1 面板卡真图 img=' + nPacks + ' 张且真渲染有尺寸', c1.imgCount === nPacks && c1.dims.every(d => !d.startsWith('0x')),
    'img=' + c1.imgCount + ' src头=' + JSON.stringify(c1.srcHeads) + ' 尺寸=' + JSON.stringify(c1.dims));
  judge('C2 零色板条(禁降级红线)', c1.palbarCount === 0, 'palbar=' + c1.palbarCount);

  // ---- C3 切卡回归：封面注入不破坏屏集合组 ----
  const clicked = await clickCard(nameInj);
  await page.waitForTimeout(1500);
  const t1 = await page.evaluate(() => [...document.querySelectorAll('#tabs .ed-tab')].map(t => t.getAttribute('data-go')));
  judge('C3 切"' + nameInj + '"后树=' + nInj + '节点', clicked && t1.length === nInj, '树=' + t1.length);

  // ---- C4 新域真点 ----
  const g1 = await gotoClickIn(sidInj);
  await page.waitForTimeout(1400);
  const a1 = await page.evaluate(() => { const on = document.querySelector('#canvas .screen.on'); return on ? on.getAttribute('data-screen') : ''; });
  judge('C4 新域真点跳转', !!g1 && a1 === g1.target, g1 ? (g1.eid + ' → ' + a1 + '（期望 ' + g1.target + '）') : (sidInj + ' 屏集内无可点 goto 元素'));

  // ---- C5 切回原风格 ----
  await ensureDrawer();
  const back = await clickCard(nameSrc);
  await page.waitForTimeout(1500);
  const t2 = await page.evaluate(() => [...document.querySelectorAll('#tabs .ed-tab')].map(t => t.getAttribute('data-go')));
  judge('C5 切回"' + nameSrc + '"后树=' + nSrc + '节点', back && t2.length === nSrc, '树=' + t2.length);

  // ---- C6 截图证据（面板特写=整窗即可辨识两张卡缩略） ----
  await ensureDrawer();
  await page.screenshot({ path: path.join(outDir, 'acc-covers-panel.png') });
  judge('C6 截图证据', true, path.join(outDir, 'acc-covers-panel.png'));
  judge('PAGEERRORS 运行时零报错', errs.length === 0, errs.length ? JSON.stringify(errs) : '干净');
} catch (e) {
  judge('脚本执行异常', false, String(e).slice(0, 200));
}

await browser.close();
const fails = results.filter(r => !r.ok).length;
console.log('SUMMARY acc_covers: PASS=' + (results.length - fails) + ' FAIL=' + fails);
process.exit(fails ? 1 : 0);
