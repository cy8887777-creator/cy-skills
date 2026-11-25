// editor_shoot_compare — 源稿 vs 构建产物 逐屏截图（对账用，附加A 转化线验收第 4 步）
// 用法：node editor_shoot_compare.mjs --src <静态稿> --built <产物html> --out <截图目录> --screens id1,id2,...
// 源稿按预览壳切屏（.screen classList）；产物按编辑器壳切屏（自动关 T18 引导弹窗与右侧标注面板）。
// 产物为代码+asset 形态（index.html + assets/）时字体随包，file:// 直开可测。
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const path = require('path');
const pwPath = path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'playwright');
const { chromium } = require(pwPath);

function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > 0 ? process.argv[i + 1] : def;
}
const SRC = arg('src');
const BUILT = arg('built');
const OUT = arg('out', 'qa');
const SCREENS = (arg('screens') || '').split(',').map(s => s.trim()).filter(Boolean);
if (!SRC || !BUILT || !SCREENS.length) {
  console.error('usage: node editor_shoot_compare.mjs --src <静态稿> --built <产物> --out <dir> --screens id1,id2');
  process.exit(2);
}
fs.mkdirSync(OUT, { recursive: true });
const fileUrl = (p) => 'file:///' + encodeURI(p.replace(/\\/g, '/')).replace(/^file:\/\/\//, '');

const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1200, height: 1000 } });

// ---- 源稿（预览壳：关旁批面板后 .device 截图）----
await page.goto(fileUrl(SRC));
await page.waitForTimeout(800);
await page.evaluate(() => { document.body.classList.remove('anno-open'); });
await page.waitForTimeout(200);
for (const sid of SCREENS) {
  await page.evaluate((id) => {
    document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.getAttribute('data-screen') === id));
  }, sid);
  await page.waitForTimeout(250);
  await page.locator('.screen.on .device').first().screenshot({ path: path.join(OUT, `src-${sid}.png`) });
  console.log('src', sid, 'ok');
}

// ---- 产物（编辑器壳：T18 引导弹窗 + notePanel 关掉；JS 切屏）----
await page.goto(fileUrl(BUILT));
await page.waitForTimeout(1000);
for (const sid of SCREENS) {
  await page.evaluate((id) => {
    const skip = document.querySelector('dialog[open] #bdSkip');
    if (skip) skip.click();
    const np = document.querySelector('#npClose');
    if (np && !document.getElementById('notePanel').hidden) np.click();
    document.querySelectorAll('.screen').forEach(s => s.classList.toggle('on', s.getAttribute('data-screen') === id));
    window.scrollTo(0, 0);
  }, sid);
  await page.waitForTimeout(350);
  await page.locator(`.screen.on .device`).first().screenshot({ path: path.join(OUT, `built-${sid}.png`) });
  console.log('built', sid, 'ok');
}
await browser.close();
console.log('done:', SCREENS.length, 'pairs →', OUT);
