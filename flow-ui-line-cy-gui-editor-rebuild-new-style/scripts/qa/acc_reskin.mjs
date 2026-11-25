// acc_reskin.mjs — 换风回装核心回归（七项 + 页数不对称专项）
//
// 验什么（multi-style-spec.md §六 + §六.4 不对称，合并自 reskin-e2e/tools/acc_v2.mjs + acc_v2b.mjs）：
//   V0 初始态：左树节点数 = 原风格屏数
//   V1 切卡整套换：点注入风格卡后树换为注入风格段（节点数=注入屏数）、可见屏集合整体换域
//   V2 隔离：注入域按钮 computed 取到值；异风格屏全部 display:none（零渗漏）
//   V3 两域真点：注入域首个 goto 元素点击跳转成功；切回原风格后原域真点同样跳转成功
//   V4 curId 重映射：切卡不丢页位（切回后当前屏 = 原风格集同序屏）
//   V5 往返两轮：树节点数与域稳定性往返不漂移
//   V6 页数不对称专项：两风格屏数不等（如 5 vs 4）时上述全部照常通过（multi-style-spec §六.4）
//   V2b 两域 computed 对照（互不渗透）；PAGEERRORS 非空按 FAIL 计
//
// 怎么跑：
//   node acc_reskin.mjs <产物.html> [--out-dir <截图目录>]
//   产物 = 回装后的 index.html（含两张风格卡）；卡名/页 id 全部从产物受控块与 DOM 解析，不写死项目
// 输出：每项一行 [PASS]/[FAIL]（供 run_reskin_regression.py 汇总），exit 0=全过 / 1=有 FAIL / 2=环境不可用
//
// 依赖：playwright 三级探测（本地 require → PLAYWRIGHT_MODULE_PATH 环境变量 → npm 全局；conversion.md 客户环境降级同口径）；node ≥18；产物 file:// 直开（零网络）
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
  console.log('[FAIL] 依赖 playwright 三级探测全落空（' + tried.join(' → ') + '）——按 conversion.md 客户环境降级处理');
  process.exit(2);
}

// ---- 参数 ----
const argFile = process.argv[2];
if (!argFile || !fs.existsSync(argFile)) {
  console.log('[FAIL] 用法: node acc_reskin.mjs <产物.html> [--out-dir <截图目录>]；产物不存在: ' + (argFile || '缺'));
  process.exit(2);
}
let outDir = null;
const oi = process.argv.indexOf('--out-dir');
if (oi > 0 && process.argv[oi + 1]) outDir = process.argv[oi + 1];
if (!outDir) outDir = path.join(path.dirname(path.resolve(argFile)), 'qa-shots');
fs.mkdirSync(outDir, { recursive: true });

// ---- 产物解析：风格卡身份 + 各风格屏数（不写死项目） ----
const html = fs.readFileSync(argFile, 'utf-8');
function readPackNames() {
  const m = html.match(/<script[^>]*data-block=["']STYLE-PACK["'][^>]*>([\s\S]*?)<\/script>/i);
  if (!m) return [];
  try {
    const j = JSON.parse(m[1]);
    return (j.packs || [])
      .filter(p => !(p.builtin && p.builtin.id))  // 排除种子内置包（注入器同口径）
      .map(p => (p.identity && p.identity.styleName) || p.packId);
  } catch (e) { return []; }
}
const cardNames = readPackNames();
if (cardNames.length < 2) {
  console.log('[FAIL] 产物 STYLE-PACK 非内置包 <2（cards=' + JSON.stringify(cardNames) + '）——不是双风格回装产物，本回归不适用');
  process.exit(2);
}
const nameSrc = cardNames[0];   // 原风格（packs 顺序第一个非内置）
const nameInj = cardNames[1];   // 注入风格
function countScreens(sid) {
  const re = new RegExp('<section\\b[^>]*\\bdata-style-id="' + sid.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') + '"[^>]*>', 'g');
  return (html.match(re) || []).length;
}
let sidSrc = 'db-main'; // 原风格屏集合 id（注入器缺省回填值；多轮注入时以 DOM 首屏域校正）
{
  const m = html.match(/<section\b[^>]*\bclass="[^"]*\bscreen[^"]*"[^>]*\bdata-style-id="([^"]+)"/);
  if (m) sidSrc = m[1];
}
const sidInj = (html.match(new RegExp('data-style-id="(db-[A-Za-z0-9_-]+)"', 'g')) || [])
  .map(s => s.replace('data-style-id="', '').replace('"', ''))
  .find(x => x !== sidSrc) || '';
const nSrc = countScreens(sidSrc);
const nInj = sidInj ? countScreens(sidInj) : 0;
if (!sidInj || !nInj) {
  console.log('[FAIL] 产物内未找到第二风格屏集合（src=' + sidSrc + '#' + nSrc + '）——注入未完成或产物损坏');
  process.exit(2);
}
console.log('[INFO] 产物=' + path.resolve(argFile));
console.log('[INFO] 卡: 原风格"' + nameSrc + '"(' + sidSrc + '#' + nSrc + '屏) / 注入"' + nameInj + '"(' + sidInj + '#' + nInj + '屏)');
const asym = nSrc !== nInj;
console.log('[INFO] ' + (asym ? '页数不对称样本（' + nSrc + ' vs ' + nInj + '）——V6 专项生效' : '两风格页数相等——V6 输出 INFO 不计分'));

// ---- 浏览器 ----
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });
const errs = [];
page.on('pageerror', e => errs.push(String(e).slice(0, 90)));
await page.goto('file:///' + path.resolve(argFile).replace(/\\/g, '/'));
await page.waitForTimeout(1100);
// 项目弹窗（如"暂不绑定（仅浏览）"）尽力跳过，点不到不计 FAIL
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

async function treeTabs() {
  return page.evaluate(() => [...document.querySelectorAll('#tabs .ed-tab')].map(t => t.getAttribute('data-go')));
}
async function curScreen() {
  return page.evaluate(() => {
    const on = document.querySelector('#canvas .screen.on');
    return on ? { id: on.getAttribute('data-screen'), sid: on.getAttribute('data-style-id') } : null;
  });
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
// 幂等开抽屉：#btnStyle 是 toggle，已开再点会关掉——先探卡元素可见再决定点不点
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
// 切到该风格屏集中第一个含可探针按钮的屏（隐藏屏 DOM 在，querySelector 照常工作）
async function openProbeTab(sid) {
  const id = await page.evaluate((sid) => {
    for (const scr of [...document.querySelectorAll('#canvas .screen')]) {
      if (scr.getAttribute('data-style-id') !== sid) continue;
      if (scr.querySelector('.pl-cta, .b-pri, button, [role="button"], .btn')) return scr.getAttribute('data-screen');
    }
    return null;
  }, sid);
  if (id) await openTab(id);
  return id;
}
// 在指定风格屏集内找首个 goto 元素：先试当前 on 屏，找不到遍历该风格屏集并 openTab 过去；返回后点击
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
  // ---- V0 初始态 ----
  const t0 = await treeTabs();
  judge('V0 初始树=' + nSrc + '节点(原风格段)', t0.length === nSrc, JSON.stringify(t0));

  // ---- 打开抽屉，切到注入风格 ----
  await ensureDrawer();
  const clicked = await clickCard(nameInj);
  await page.waitForTimeout(1600);

  // ---- V1 切卡整套换 ----
  const t1 = await treeTabs();
  const vis1 = await page.evaluate(() => [...document.querySelectorAll('#canvas .screen')]
    .filter(s => getComputedStyle(s).display !== 'none').map(s => s.getAttribute('data-style-id')));
  const injSeg = sidInj.replace(/^db-/, '');  // 树页 id 前缀=风格段（<风格段>-<语义id>）
  const visOk = vis1.length > 0 && vis1.every(x => x === sidInj);
  const treeSegOk = t1.length > 0 && t1.every(x => String(x).indexOf(injSeg + '-') === 0);
  judge('V1 切卡整套换(树=' + nInj + '节点注入段+可见屏全换 ' + sidInj + ')', clicked && t1.length === nInj && visOk && treeSegOk,
    '点卡=' + clicked + ' 树=' + JSON.stringify(t1) + ' 可见=' + JSON.stringify(vis1));

  // ---- V2 隔离：新域 computed + 异域全隐藏 ----
  const probe1 = await openProbeTab(sidInj);
  const cNew = await page.evaluate((sidInj) => {
    const scr = [...document.querySelectorAll('#canvas .screen')].find(s => s.getAttribute('data-screen') && s.getAttribute('data-style-id') === sidInj && getComputedStyle(s).display !== 'none');
    const btn = scr && scr.querySelector('.pl-cta, .b-pri, button, [role="button"], .btn');
    const hiddenOther = [...document.querySelectorAll('#canvas .screen')].filter(s => s.getAttribute('data-style-id') !== sidInj);
    const leak = hiddenOther.filter(s => getComputedStyle(s).display !== 'none').map(s => s.getAttribute('data-screen'));
    return { btnBg: btn ? getComputedStyle(btn).backgroundColor : '', leak };
  }, sidInj);
  const btnBgNew = cNew.btnBg;
  judge('V2 隔离(新域按钮computed取值+异域屏零可见)', !!btnBgNew && cNew.leak.length === 0,
    '探针屏=' + (probe1 || '无') + ' btnBg=' + btnBgNew + ' 渗漏可见异域屏=' + JSON.stringify(cNew.leak));

  // ---- V3a 注入域真点 ----
  const g1 = await gotoClickIn(sidInj);
  await page.waitForTimeout(1500);
  const a1 = await curScreen();
  judge('V3a 注入域真点跳转', !!g1 && !!a1 && a1.id === g1.target,
    g1 ? (g1.eid + ' → 目标=' + g1.target + ' 实际=' + (a1 ? a1.id : '无')) : (sidInj + ' 屏集内无可点 goto 元素'));

  // ---- V4 curId 重映射：记录注入域当前 index，切回原风格断言同序 ----
  const polIdx = await page.evaluate((sidInj) => {
    const on = document.querySelector('#canvas .screen.on');
    const list = [...document.querySelectorAll('#canvas .screen')].filter(s => s.getAttribute('data-style-id') === sidInj);
    return list.indexOf(on);
  }, sidInj);
  await ensureDrawer();
  const backClicked = await clickCard(nameSrc);
  await page.waitForTimeout(1600);
  const t2 = await treeTabs();
  const cur2 = await curScreen();
  const srcScreens = await page.evaluate((sidSrc) => [...document.querySelectorAll('#canvas .screen')]
    .filter(s => s.getAttribute('data-style-id') === sidSrc).map(s => s.getAttribute('data-screen')), sidSrc);
  const expected = srcScreens[Math.max(polIdx, 0)];
  judge('V4 切回树=' + nSrc + '节点+curId 重映射(注入index' + polIdx + '→原集同序)', backClicked && t2.length === nSrc && cur2 && cur2.id === expected,
    '点卡=' + backClicked + ' 树=' + t2.length + ' 当前=' + (cur2 ? cur2.id : '无') + ' 期望=' + expected);

  // ---- V3b 原域真点 ----
  const g2 = await gotoClickIn(sidSrc);
  await page.waitForTimeout(1500);
  const a2 = await curScreen();
  judge('V3b 原域真点跳转', !!g2 && !!a2 && a2.id === g2.target,
    g2 ? (g2.eid + ' → 目标=' + g2.target + ' 实际=' + (a2 ? a2.id : '无')) : (sidSrc + ' 屏集内无可点 goto 元素'));

  // ---- V2b 原域 computed 对照（两域取值必须不同=互不渗透） ----
  const probe2 = await openProbeTab(sidSrc);
  const cOld = await page.evaluate(() => {
    const on = document.querySelector('#canvas .screen.on');
    const btn = on && on.querySelector('.pl-cta, .b-pri, button, [role="button"], .btn');
    return btn ? getComputedStyle(btn).backgroundColor : '';
  });
  judge('V2b 两域按钮computed不同值(互不渗透)', !!cOld && !!btnBgNew && cOld !== btnBgNew,
    '原域=' + cOld + '(屏' + (probe2 || '?') + ') 注入域=' + btnBgNew);

  // ---- V5 往返两轮 ----
  let v5ok = true;
  const v5log = [];
  for (let i = 1; i <= 2; i++) {
    await ensureDrawer(); await clickCard(nameInj); await page.waitForTimeout(1400);
    const n1 = (await treeTabs()).length;
    const d1 = await curScreen();
    await ensureDrawer(); await clickCard(nameSrc); await page.waitForTimeout(1400);
    const n2 = (await treeTabs()).length;
    const d2 = await curScreen();
    const ok = n1 === nInj && n2 === nSrc && d1 && d1.sid === sidInj && d2 && d2.sid === sidSrc;
    if (!ok) v5ok = false;
    v5log.push('往返' + i + ': 注入树' + n1 + '/' + (d1 ? d1.sid : '?') + ' → 原树' + n2 + '/' + (d2 ? d2.sid : '?'));
  }
  judge('V5 往返两轮稳定', v5ok, v5log.join(' | '));

  // ---- V6 页数不对称专项 ----
  if (asym) {
    const asymOk = results.filter(r => /^(V1 |V4 |V5 )/.test(r.item)).every(r => r.ok);
    judge('V6 页数不对称专项(' + nSrc + ' vs ' + nInj + '，切卡/树/重映射/往返照常)', asymOk,
      'multi-style-spec §六.4：页数不对称是合法场景，以上切卡/树/重映射/往返全过即通过');
  } else {
    console.log('[INFO] V6 本产物两风格页数相等（非不对称样本），专项跳过不计分');
  }

  // ---- 截图证据 + PAGEERRORS ----
  await page.screenshot({ path: path.join(outDir, 'acc-reskin-final.png') });
  judge('PAGEERRORS 运行时零报错', errs.length === 0, errs.length ? JSON.stringify(errs) : '干净');
} catch (e) {
  judge('脚本执行异常', false, String(e).slice(0, 200));
}

await browser.close();
const fails = results.filter(r => !r.ok).length;
console.log('SUMMARY acc_reskin: PASS=' + (results.length - fails) + ' FAIL=' + fails + (asym ? ' (不对称样本 ' + nSrc + 'vs' + nInj + ')' : ''));
process.exit(fails ? 1 : 0);
