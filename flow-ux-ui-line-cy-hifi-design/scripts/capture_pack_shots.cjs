/* capture_pack_shots.cjs — V05戊 换肤链截帧回填（pack.screenshot 生产件）
 * 用法：node scripts/capture_pack_shots.cjs <产物.html> [--quality N]
 * 流程：playwright 打开产物 → 跳绑定引导 → 口令解锁 → StylePanel.applyPack 逐包应用
 *   → 对当前页 .device 截帧（jpeg dataURL）→ 回填产物内 STYLE-PACK 围栏 packs[].screenshot。
 * 依赖：STYLE-PACK 受控块在产物内（build.py --style-blocks 注入）；口令=EDIT_PASSWORD（12345678）。
 * 前置：用户先点过一次「保存」或产物在可信目录？——不需要：回填直接改源文件（与编辑器保存同语义）。
 */
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const target = process.argv[2];
if (!target || !fs.existsSync(target)) {
  console.error('usage: node capture_pack_shots.cjs <产物.html> [--quality N]');
  process.exit(2);
}
const qArg = process.argv.indexOf('--quality');
const quality = qArg >= 0 ? parseInt(process.argv[qArg + 1], 10) || 50 : 50;
const PWD = process.env.PROTO_EDIT_PASSWORD || '12345678'; /* build.py 传 EDIT_PASSWORD 装配常量；单独跑缺省同值 */

function loadPlaywright() {
  /* 发现式复用（doctor.py 同口径）：PLAYWRIGHT_MODULE_PATH → 本地 require → npm 全局目录 */
  const tries = [];
  if (process.env.PLAYWRIGHT_MODULE_PATH) tries.push(process.env.PLAYWRIGHT_MODULE_PATH);
  tries.push(null);
  if (process.env.APPDATA) tries.push(path.join(process.env.APPDATA, 'npm', 'node_modules', 'playwright'));
  for (const t of tries) {
    try { return t ? createRequire(path.join(t, 'package.json'))('playwright') : require('playwright'); } catch (e) { /* next */ }
  }
  throw new Error('playwright 未找到（设置 PLAYWRIGHT_MODULE_PATH 指向已装 playwright 模块目录）');
}

(async () => {
  const { chromium } = loadPlaywright();
  const { pathToFileURL } = require('url');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  await page.goto(pathToFileURL(path.resolve(target)).href);
  await page.waitForFunction(() => window.PROTO && window.StylePanel, null, { timeout: 15000 });
  await page.waitForTimeout(400);
  await page.evaluate(() => { const b = [...document.querySelectorAll('dialog[open] button')].find(x => (x.textContent || '').includes('暂不绑定')); if (b) b.click(); });
  await page.locator('#btnEdit').click();
  await page.locator('#gatePassword').fill(PWD);
  await page.locator('#gateConfirm').click();
  await page.waitForFunction(() => window.PROTO.isUnlocked(), null, { timeout: 10000 });

  const packIds = await page.evaluate(() => {
    const m = document.querySelector('script[data-block="STYLE-PACK"]');
    if (!m) throw new Error('STYLE-PACK fence not found');
    return JSON.parse(m.textContent).packs.map(p => p.packId);
  });
  const shotOf = {};
  for (const packId of packIds) {
    const r = await page.evaluate(pid => window.StylePanel.applyPack(pid), packId);
    if (!r.ok) throw new Error('applyPack failed for ' + packId + ': ' + JSON.stringify(r));
    await page.waitForTimeout(350);
    const dev = page.locator('.screen.on .device').first();
    const buf = await dev.screenshot({ type: 'jpeg', quality });
    shotOf[packId] = 'data:image/jpeg;base64,' + buf.toString('base64');
    console.log('shot', packId, Math.round(shotOf[packId].length / 1024) + 'KB');
  }
  await page.evaluate(pid => window.StylePanel.restoreOriginal(), packIds[0]);
  await browser.close();
  if (errors.length) throw new Error('page errors: ' + errors.join(' | '));

  let html = fs.readFileSync(target, 'utf8');
  const re = /(<script type="application\/json" data-block="STYLE-PACK">)([\s\S]*?)(<\/script>)/;
  const m = html.match(re);
  if (!m) throw new Error('STYLE-PACK fence not found for backfill');
  const packs = JSON.parse(m[2]);
  let n = 0;
  packs.packs.forEach(p => { if (shotOf[p.packId]) { p.screenshot = shotOf[p.packId]; n++; } });
  html = html.replace(re, '$1' + JSON.stringify(packs).replace(/</g, '\\u003c') + '$3');
  fs.writeFileSync(target, html, 'utf8');
  console.log('shots OK -> screenshot backfilled ' + n + '/' + packIds.length + ': ' + Object.keys(shotOf).join(','));
})().catch(e => { console.error('FAIL:', e.message); process.exit(1); });
