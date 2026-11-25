/* assert_runtime.cjs — e2e 正向流程的运行时断言（Playwright）。
 * 用法：node assert_runtime.cjs <成品.html>
 * 断言面：面板接口切包/切配色/跨族显隐、计算样式随包等于包值、
 *         风格卡「风格令牌」行互异、组件面板胶囊页签与拼图图标、页面树中文分组。
 * 退出：0 = 全部通过；1 = 有失败（逐条打印 预期 vs 实际）。
 */
'use strict';
const fs = require('fs');
const path = require('path');
const { createRequire } = require('module');

const target = process.argv[2];
if (!target || !fs.existsSync(target)) {
  console.error('usage: node assert_runtime.cjs <成品.html>');
  process.exit(2);
}

function loadPlaywright() {
  const tries = [];
  if (process.env.PLAYWRIGHT_MODULE_PATH) tries.push(process.env.PLAYWRIGHT_MODULE_PATH);
  tries.push(null);
  if (process.env.APPDATA) tries.push(path.join(process.env.APPDATA, 'npm', 'node_modules', 'playwright'));
  for (const t of tries) {
    try { return t ? createRequire(path.join(t, 'package.json'))('playwright') : require('playwright'); } catch (e) { /* next */ }
  }
  throw new Error('playwright 未找到（设 NODE_PATH 或 PLAYWRIGHT_MODULE_PATH）');
}

const results = [];
function check(name, ok, expect, actual) {
  results.push({ name, ok: !!ok, expect, actual });
  console.log((ok ? '[PASS] ' : '[FAIL] ') + name + '  预期: ' + expect + '  实际: ' + actual);
}

(async () => {
  const { chromium } = loadPlaywright();
  const { pathToFileURL } = require('url');
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage({ viewport: { width: 1600, height: 1100 } });
  const pageErrors = [];
  page.on('pageerror', e => pageErrors.push(String(e)));
  await page.goto(pathToFileURL(path.resolve(target)).href);
  await page.waitForFunction(() => window.PROTO && window.StylePanel, null, { timeout: 20000 });
  await page.waitForTimeout(400);
  await page.evaluate(() => {
    const b = [...document.querySelectorAll('dialog[open] button')].find(x => (x.textContent || '').includes('暂不绑定'));
    if (b) b.click();
  });

  // ---------- A0 解锁（口令分级 C 方案：换肤面板 5 API 免口令；编辑入口与 applyStyleConfig 走 editorAllowed——
  // 此步经 #btnEdit 进编辑态解锁，保证后续组件面板等编辑面断言可用；排查 P2-16 注释正名） ----------
  await page.locator('#btnEdit').click();
  await page.locator('#gatePassword').fill('12345678');
  await page.locator('#gateConfirm').click();
  await page.waitForFunction(() => window.PROTO.isUnlocked(), null, { timeout: 10000 });

  // ---------- A1 面板正式态 + 交付初始风格（--active-pack） ----------
  const info = await page.evaluate(() => window.StylePanel.info());
  check('A1 面板数据源=风格登记块', info.mode === 'registry', "mode==='registry'", JSON.stringify(info.mode));
  check('A1 族数=2', info.registry && info.registry.families === 2, 'families===2',
        info.registry ? String(info.registry.families) : String(info.registry));
  check('A1 包数=5（4 包 + 原始方案）', info.registry && info.registry.packs === 5, 'packs===5',
        info.registry ? String(info.registry.packs) : String(info.registry));
  check('A1 打开即应用选中风格', info.currentPackId === 'pack-chenlan', "currentPackId==='pack-chenlan'",
        String(info.currentPackId));

  // ---------- A2 同族内切包：计算样式 = 包 tokens 值，且随包变化 ----------
  const probe = await page.evaluate(() => {
    const packs = JSON.parse(document.querySelector('script[data-block="STYLE-PACK"]').textContent).packs;
    const out = {};
    const snap = () => {
      const card = document.querySelector('[data-dom-base="db-a"] .kx-card');
      const title = document.querySelector('[data-dom-base="db-a"] .kx-title');
      const cs = getComputedStyle(card), ct = getComputedStyle(title);
      return {
        radius: cs.borderRadius.trim(),
        padding: cs.paddingTop.trim(),
        borderWidth: cs.borderLeftWidth.trim(),
        shadow: card.style.length >= 0 ? getComputedStyle(card).getPropertyValue('--sp-shadow-md').trim() : '',
        fontSize: ct.fontSize.trim(),
        fontWeight: ct.fontWeight.trim(),
      };
    };
    for (const pid of ['pack-chenlan', 'pack-bohe']) {
      const r = window.StylePanel.applyPack(pid);
      if (!r.ok) throw new Error('applyPack failed: ' + JSON.stringify(r));
      out[pid] = snap();
    }
    return { snaps: out, tokens: Object.fromEntries(packs.map(p => [p.packId, p.tokens])) };
  });
  const tA = probe.tokens['pack-chenlan'], tB = probe.tokens['pack-bohe'];
  const sA = probe.snaps['pack-chenlan'], sB = probe.snaps['pack-bohe'];
  const pairs = [
    ['圆角 border-radius', 'radius', 'radius-md'],
    ['内边距 padding-top', 'padding', 'space-3'],
    ['边框粗细 border-left-width', 'borderWidth', 'border-width'],
    ['阴影 --sp-shadow-md', 'shadow', 'shadow-md'],
    ['字号 font-size(.kx-title)', 'fontSize', 'size-title'],
    ['字重 font-weight(.kx-title)', 'fontWeight', 'weight-head'],
  ];
  for (const [label, skey, tkey] of pairs) {
    const vA = String(tA[tkey]), vB = String(tB[tkey]);
    check('A2 晨蓝·' + label + ' = 包值', sA[skey] === vA, vA, sA[skey]);
    check('A2 薄荷·' + label + ' = 包值', sB[skey] === vB, vB, sB[skey]);
    check('A2 ' + label + ' 随包变化', sA[skey] !== sB[skey], vA + ' ≠ ' + vB, sA[skey] + ' vs ' + sB[skey]);
  }

  // ---------- A3 切配色版：主色/底色/文字色跟随 swatches ----------
  const pal = await page.evaluate(() => {
    const packs = JSON.parse(document.querySelector('script[data-block="STYLE-PACK"]').textContent).packs;
    const p = packs.find(x => x.packId === 'pack-chenlan');
    const rootVars = () => {
      const cs = getComputedStyle(document.documentElement);
      return { accent: cs.getPropertyValue('--accent').trim(),
               bg: cs.getPropertyValue('--style-bg').trim(),
               text: cs.getPropertyValue('--style-text').trim() };
    };
    const out = {};
    for (const pid of ['pal-pine', 'pal-brand']) {
      const r = window.StylePanel.applyPalette(pid, 'pack-chenlan');
      if (!r.ok) throw new Error('applyPalette failed: ' + JSON.stringify(r));
      out[pid] = rootVars();
    }
    return { snaps: out, palettes: Object.fromEntries(p.palettes.map(x => [x.paletteId, x.swatches])) };
  });
  for (const pid of ['pal-pine', 'pal-brand']) {
    const sw = pal.palettes[pid], got = pal.snaps[pid];
    check('A3 ' + pid + ' 主色 --accent', got.accent === sw[0], sw[0], got.accent);
    check('A3 ' + pid + ' 底色 --style-bg', got.bg === sw[1], sw[1], got.bg);
    check('A3 ' + pid + ' 文字色 --style-text', got.text === sw[2], sw[2], got.text);
  }
  check('A3 配色切换生效（松绿≠品牌晨蓝）', pal.snaps['pal-pine'].accent !== pal.snaps['pal-brand'].accent,
        '两版主色不同', pal.snaps['pal-pine'].accent + ' vs ' + pal.snaps['pal-brand'].accent);

  // ---------- A4 跨族切换：对应族容器显示，另一族隐藏 ----------
  const dom = await page.evaluate(async () => {
    const vis = () => {
      const a = [...document.querySelectorAll('#canvas [data-dom-base="db-a"]')];
      const b = [...document.querySelectorAll('#canvas [data-dom-base="db-b"]')];
      const disp = els => els.map(n => n.style.display || getComputedStyle(n).display);
      return { a: disp(a), b: disp(b) };
    };
    const out = {};
    for (const pid of ['pack-dianzi', 'pack-chenlan']) {
      const r = window.StylePanel.applyPack(pid);
      if (!r.ok) throw new Error('applyPack failed: ' + JSON.stringify(r));
      await new Promise(res => setTimeout(res, 120));
      out[pid] = vis();
    }
    return out;
  });
  check('A4 切到族乙（靛紫）→ 甲容器(db-a)隐藏',
        dom['pack-dianzi'].a.every(v => v === 'none'), '全部 display:none',
        JSON.stringify(dom['pack-dianzi'].a));
  check('A4 切到族乙（靛紫）→ 乙容器(db-b)显示',
        dom['pack-dianzi'].b.every(v => v !== 'none'), '全部可见',
        JSON.stringify(dom['pack-dianzi'].b));
  check('A4 切回族甲（晨蓝）→ 乙容器(db-b)隐藏',
        dom['pack-chenlan'].b.every(v => v === 'none'), '全部 display:none',
        JSON.stringify(dom['pack-chenlan'].b));
  check('A4 切回族甲（晨蓝）→ 甲容器(db-a)显示',
        dom['pack-chenlan'].a.every(v => v !== 'none'), '全部可见',
        JSON.stringify(dom['pack-chenlan'].a));

  // ---------- A5 面板风格卡「风格令牌」行互不相同 ----------
  await page.evaluate(() => window.StylePanel.open());
  await page.waitForSelector('#stylePanel .ed-sp-card[data-pack]', { timeout: 5000 });
  const tokenRows = await page.evaluate(() => {
    return [...document.querySelectorAll('#stylePanel .ed-sp-card[data-pack]')].map(c => ({
      pack: c.getAttribute('data-pack'),
      text: (c.querySelector('.ed-sp-tokens') || { textContent: '' }).textContent.replace(/^风格令牌/, '').trim(),
    }));
  });
  check('A5 风格卡数量=4', tokenRows.length === 4, '4 张卡', String(tokenRows.length) + ' 张');
  const uniq = new Set(tokenRows.map(x => x.text));
  check('A5 「风格令牌」行各不相同', uniq.size === tokenRows.length,
        tokenRows.length + ' 行互异', uniq.size + ' 行互异: ' + JSON.stringify(tokenRows.map(x => x.text)));
  await page.evaluate(() => { const b = document.querySelector('[data-sp-close]'); if (b) b.click(); });

  // ---------- A6 组件面板：胶囊页签 + 自定义组件拼图图标 ----------
  await page.waitForSelector('#libBody .ed-cl-switch', { timeout: 5000 });
  const sw6 = await page.evaluate(() => {
    const g = document.querySelector('#libBody [data-clgroup="general"]');
    const p = document.querySelector('#libBody [data-clgroup="project"]');
    return { gOn: g.classList.contains('on') && g.getAttribute('aria-selected') === 'true',
             pOn: p.classList.contains('on'), gText: g.textContent, pText: p.textContent };
  });
  check('A6 胶囊页签文案', sw6.gText === '通用组件' && sw6.pText === '本项目自定义组件',
        '通用组件 / 本项目自定义组件', sw6.gText + ' / ' + sw6.pText);
  check('A6 默认选中「通用组件」', sw6.gOn && !sw6.pOn, 'general on', JSON.stringify(sw6));
  const proj = await page.evaluate(() => {
    document.querySelector('#libBody [data-clgroup="project"]').click();
    const cards = [...document.querySelectorAll('#libBody .ed-cl-card')];
    return { count: cards.length,
             allPuzzle: cards.every(c => { const u = c.querySelector('.ed-cl-ic use'); return u && u.getAttribute('href') === '#cl-i-pk-puzzle'; }) };
  });
  check('A6 自定义组件数量=12', proj.count === 12, '12', String(proj.count));
  check('A6 自定义组件都是拼图图标', proj.allPuzzle, '全部 use#cl-i-pk-puzzle', String(proj.allPuzzle));
  const back = await page.evaluate(() => {
    document.querySelector('#libBody [data-clgroup="general"]').click();
    const cards = [...document.querySelectorAll('#libBody .ed-cl-card')];
    return { switchBack: !!document.querySelector('#libBody [data-clgroup="general"].on'),
             generalCards: cards.length };
  });
  check('A6 能切回「通用组件」', back.switchBack, 'general on', String(back.switchBack));

  // ---------- A7 页面树分组名是中文 ----------
  const groups = await page.evaluate(() =>
    [...document.querySelectorAll('#tabs .ed-tab-group-head')].map(h => h.textContent.trim()));
  const gnames = groups.map(g => g.replace(/^[▾▸]\s*/, ''));
  check('A7 页面树分组=工作台/钱包（中文）',
        gnames.length === 2 && gnames.includes('工作台') && gnames.includes('钱包'),
        "['工作台','钱包']", JSON.stringify(gnames));

  check('A8 无页面 JS 错误', pageErrors.length === 0, '0 个 pageerror',
        pageErrors.slice(0, 3).join(' | ') || '0 个');

  await browser.close();
  const bad = results.filter(r => !r.ok);
  console.log('\nsummary: ' + results.length + ' check(s): ' + (results.length - bad.length) +
              ' passed / ' + bad.length + ' failed — ' + (bad.length ? 'FAIL' : 'PASS'));
  process.exit(bad.length ? 1 : 0);
})().catch(e => { console.error('ERROR ' + (e && e.stack || e)); process.exit(2); });
