// token 管线验收（2026-11 键名统一批）。
// 覆盖：①build --style-blocks 构建最小产物（正本表每个键两包异值 + keyPattern 合规扩展键）；
// ②Chromium 里走运行时自身切换逻辑（StylePanel.applyPack）逐包应用，断言每个 emits 变量 == 包里的值；
// ③驼峰/下划线陷阱键不被运行时读取（verify_blocks 构建门禁拦陷阱键，故陷阱键由本测试注入产物副本的
//   STYLE-PACK 块——被测对象是运行时解析，不是构建门禁）；④扩展键生成 --sp-<键名>；⑤面板密度词；
// ⑥--active-pack overlay 静态设计令牌走正本键名；⑦build --check 页面命名检查（具名错误码）。
// 跑法：NODE_PATH=<npm 全局 node_modules> node tests/test_token_pipeline.cjs
const fs = require('fs'), path = require('path'), os = require('os'), cp = require('child_process');
const assert = require('assert');
const { pathToFileURL } = require('url');

const ROOT = path.resolve(__dirname, '..');
const FX = path.join(ROOT, 'scripts', 'fixtures', 'token-pipeline');
const PY = process.env.PYTHON || 'python';
const results = [];
const pass = (s) => { results.push(s); console.log('PASS', s); };

function run(args, opts) {
  const r = cp.spawnSync(PY, args, Object.assign({ encoding: 'utf8', cwd: ROOT,
    env: Object.assign({}, process.env, { PYTHONIOENCODING: 'utf-8' }) }, opts || {}));
  return r;
}

/* ---- 色值工具（与运行时 softTint/hexToRgba2 输出格式对齐） ---- */
function rgbBytes(hex) {
  const m = /^#([0-9a-fA-F]{6})$/.exec(hex || '');
  if (!m) return null;
  const n = parseInt(m[1], 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}
function rgba(hex, a) {
  const b = rgbBytes(hex);
  return b ? ('rgba(' + b[0] + ',' + b[1] + ',' + b[2] + ',' + a + ')') : null;
}
function rgbCss(hex) {
  const b = rgbBytes(hex);
  return b ? ('rgb(' + b[0] + ', ' + b[1] + ', ' + b[2] + ')') : null;
}
const normFont = (s) => String(s || '').toLowerCase().replace(/["']/g, '').replace(/\s+/g, '');

/* ---- 断言清单：能从 assets/token-keys.json emits 推导的一律推导（不手抄） ---- */
const tk = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets', 'token-keys.json'), 'utf8').replace(/^\uFEFF/, ''));
const byKey = {};
for (const k of tk.keys) byKey[k.key] = k;
assert.ok(tk.keys.length >= 40 && byKey.density && Array.isArray(byKey.density.allowed), '正本表解析异常');

// chooser 内部映射（正本表无此对应，仅这三张小表为手抄）：
const PAGE_COLOR_VARS = { 'bg': '--bg', 'surface': '--surface', 'text-primary': '--text', 'text-secondary': '--muted', 'border': '--line' }; // 暗色分支重映射的五个页面色
const ROOT_VARS = { 'primary': '--accent', 'bg': '--style-bg', 'surface': '--style-surface', 'text-primary': '--style-text', 'text-secondary': '--style-muted', 'border': '--style-line' }; // paletteValues 根级槽位
const SCREEN_DERIVED = { 'radius-md': '--radius', 'shadow-md': '--shadow' }; // 微调基线通道（--radius/--shadow）

// emits 推导：--sp-* 与语义主色 → 屏级变量；-soft → 推算浅色；dark.fields → 暗色根变量
const SCREEN_VARS = {}, SOFT_EXPECT = {}, DARK_VARS = {};
for (const f of (byKey.dark && byKey.dark.fields) || []) DARK_VARS[f] = '--style-dark-' + f;
for (const k of tk.keys) {
  for (const e of k.emits || []) {
    if (typeof e !== 'string' || !e.startsWith('--')) continue;
    if (e === '--accent-soft') { SOFT_EXPECT[e] = { key: k.key, alpha: '0.1', where: 'root' }; continue; } // hexToRgba2(.1)
    if (e === '--accent') continue; // 根级，走 ROOT_VARS
    if (e.startsWith('--sp-')) { SCREEN_VARS[k.key] = e; continue; }
    if (e.endsWith('-soft')) { SOFT_EXPECT[e] = { key: k.key, alpha: '0.12', where: 'screen' }; continue; } // softTint(.12)
    if (PAGE_COLOR_VARS[k.key]) continue; // 暗色敏感页面色，按暗色映射单独断
    SCREEN_VARS[k.key] = e; // --ok/--danger/--warn 等语义主色
  }
}
assert.ok(Object.keys(SCREEN_VARS).length >= 25 && Object.keys(DARK_VARS).length === 5, 'emits 推导结果异常');
const DENSITY_WORDS = { compact: '紧凑', regular: '适中', loose: '舒展' };

/* ---- 注入防御陷阱（纵深防御自测；构建门禁拦非法键名，值级载荷由本测试注入产物副本专测运行时） ---- */
const TRAPS = {
  fontNumVal: 'Consolas} html{pwned-canonical', // 正本键通道：值含载荷 → cssSafe 丢弃 → 落 :root 基线（变量为空）
  extKey: 'evil-glow', extVal: 'red;body{pwned-ext', // 扩展键通道：同上，且不得生成 --sp-evil-glow
  l2Selector: '.card} body{pwned-l2', // l2Overrides 选择器含禁字符 → 整条跳过
  l2PropsVal: 'color:red;} body{pwned-props', // l2Overrides props 含 { }（; 保留语义）→ 整条跳过
  l2OkSelector: '.card-b', l2OkProps: 'color:var(--accent);letter-spacing:2px' // 合法条目（含分号）→ 正常应用，正向对照
};
const TRAP_DROP = { 'pk-b:font-num': true }; // 陷阱值被丢弃的键 → 断言变量为空而非包值

(async () => {
  const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'token-pipeline-'));
  const dirA = path.join(tmp, 'a'), dirB = path.join(tmp, 'b');
  fs.mkdirSync(dirA); fs.mkdirSync(dirB);
  const sbPath = path.join(FX, 'style-blocks.json');
  const sb = JSON.parse(fs.readFileSync(sbPath, 'utf8'));
  const packs = sb['STYLE-PACK'].packs;
  assert.equal(packs.length, 2, 'fixture 需两包');

  /* ---- ① 构建（运行时测试靶 + overlay 靶；各自独立目录防 AGENTS.md 项目冲突） ---- */
  let r = run(['scripts/build.py', '--pages', path.join(FX, 'pages-ok'), '--title', '令牌管线',
    '--output', path.join(dirA, 'product.html'), '--style-blocks', sbPath]);
  assert.equal(r.status, 0, 'build pipeline 失败: ' + (r.stdout || '') + (r.stderr || ''));
  pass('build.py --style-blocks 正式构建通过（verify_blocks 门禁 + 命名门禁）');
  r = run(['scripts/build.py', '--pages', path.join(FX, 'pages-ok'), '--title', '令牌管线',
    '--output', path.join(dirB, 'product.html'), '--style-blocks', sbPath, '--active-pack', 'pk-a']);
  assert.equal(r.status, 0, 'build --active-pack 失败: ' + (r.stdout || '') + (r.stderr || ''));

  /* ---- ⑥ overlay 静态设计令牌 = 正本键名读取 ---- */
  const overlayHtml = fs.readFileSync(path.join(dirB, 'product.html'), 'utf8');
  const pkA = packs[0].tokens;
  for (const needle of ['--accent:' + pkA['primary'], '--text:' + pkA['text-primary'], '--muted:' + pkA['text-secondary'],
    '--line:' + pkA['border'], '--radius:' + pkA['radius-md'], 'font-size:' + Number(parseFloat(pkA['size-body'])).toFixed(1) + 'px',
    'var(--sp-size-ctl-lg,' + Number(parseFloat(pkA['size-ctl-lg'])) + '.0px)']) {
    assert.ok(overlayHtml.includes(needle), 'overlay 静态令牌缺失: ' + needle);
  }
  pass('--active-pack overlay 静态设计令牌按正本键名（primary/text-primary/text-secondary/radius-md/size-body/size-ctl-lg）落盘');

  /* ---- ⑦ build --check 命名检查（具名错误码） ---- */
  const check = (target, extra) => run(['scripts/build.py', '--check', target].concat(extra || []));
  assert.equal(check(path.join(FX, 'pages-ok')).status, 0, '中文命名样例应 PASS');
  pass('build --check：中文分组/中文页面名样例 PASS');
  r = check(path.join(FX, 'pages-bad-group'));
  assert.equal(r.status, 1); assert.ok(r.stdout.includes('E-NAMING-GROUP'), r.stdout);
  pass('build --check：英文分组目录名 → E-NAMING-GROUP（exit 1）');
  r = check(path.join(FX, 'pages-bad-page'));
  assert.equal(r.status, 1); assert.ok(r.stdout.includes('E-NAMING-PAGE'), r.stdout);
  pass('build --check：英文页面显示名 → E-NAMING-PAGE（exit 1）');
  r = check(path.join(FX, 'pages-id-leak'));
  assert.equal(r.status, 0, '无风格块时不查编号泄漏');
  r = check(path.join(FX, 'pages-id-leak'), ['--style-blocks', sbPath]);
  assert.equal(r.status, 1); assert.ok(r.stdout.includes('E-NAMING-ID-LEAK'), r.stdout);
  pass('build --check --style-blocks：页头含内部编号 → E-NAMING-ID-LEAK（exit 1）');
  r = run(['scripts/build.py', '--pages', path.join(FX, 'pages-id-leak'), '--title', '泄漏', '--output', path.join(tmp, 'leak.html'), '--style-blocks', sbPath]);
  assert.equal(r.status, 1); assert.ok((r.stdout || '').includes('E-NAMING-ID-LEAK'), r.stdout);
  assert.ok(!fs.existsSync(path.join(tmp, 'leak.html')), '命名门禁失败不得产件');
  pass('正式构建：页头含内部编号 → E-NAMING-ID-LEAK 门禁拒绝且零产出');

  /* ---- lint_tokens 门禁接线：扩展参数变量需经 --style-blocks 进入已知集合（build.py formal_gate 同参） ---- */
  const lintBase = ['scripts/lint_tokens.py', path.join(FX, 'pages-ext'), '--design-system', path.join(ROOT, 'assets', 'design-system.json')];
  r = run(lintBase);
  assert.equal(r.status, 1, '页面引用扩展变量、未传风格包时应被拦（未知变量）');
  r = run(lintBase.concat(['--style-blocks', sbPath]));
  assert.equal(r.status, 0, '传风格包后扩展键 --sp-glass-blur 应放行: ' + (r.stdout || '') + (r.stderr || ''));
  pass('lint_tokens 门禁接线：build.py 带 --style-blocks 时传参，扩展键 --sp-<键名> 进已知集合放行（不传则拦）');

  /* ---- U2 项目模式命名检查（--project-dir / --check+--start-doc；U2 即拦，不等 U3 构建） ---- */
  const projOk = path.join(FX, 'project-ok'), projBad = path.join(FX, 'project-bad-naming');
  r = run(['scripts/build.py', '--project-dir', projOk, '--phase', 'incremental']);
  assert.equal(r.status, 0, 'U2 incremental 中文命名样例应 ready: ' + (r.stdout || '') + (r.stderr || ''));
  r = run(['scripts/build.py', '--project-dir', projOk, '--phase', 'final']);
  assert.equal(r.status, 0, 'U2 final 中文命名样例应 passed: ' + (r.stdout || '') + (r.stderr || ''));
  r = run(['scripts/build.py', '--project-dir', projOk, '--phase', 'final', '--style-blocks', sbPath]);
  assert.equal(r.status, 0, 'U2 final + 风格块（页头无编号）应 passed');
  pass('U2 项目检查：中文命名样例 incremental ready / final passed（含风格块无泄漏）');
  r = run(['scripts/build.py', '--project-dir', projBad, '--phase', 'incremental']);
  assert.equal(r.status, 1);
  assert.ok(r.stdout.includes('E-NAMING-GROUP'), r.stdout);
  assert.ok(r.stdout.includes('E-NAMING-PAGE'), r.stdout);
  r = run(['scripts/build.py', '--project-dir', projBad, '--phase', 'final']);
  assert.equal(r.status, 1);
  assert.ok(r.stdout.includes('E-NAMING-GROUP') && r.stdout.includes('E-NAMING-PAGE'), r.stdout);
  r = run(['scripts/build.py', '--project-dir', projBad, '--phase', 'final', '--style-blocks', sbPath]);
  assert.equal(r.status, 1);
  assert.ok(r.stdout.includes('E-NAMING-ID-LEAK'), r.stdout);
  pass('U2 项目检查：英文分组/英文页面名/页头内部编号 → E-NAMING-GROUP / E-NAMING-PAGE / E-NAMING-ID-LEAK 拦在 U2（exit 1，泄漏仅带风格块时查）');

  /* ---- ③ 陷阱键注入产物副本（专测运行时忽略行为） ---- */
  const prodPath = path.join(dirA, 'product.html');
  const trapHtml = (() => {
    let html = fs.readFileSync(prodPath, 'utf8');
    const marker = 'data-block="STYLE-PACK"';
    const i = html.indexOf(marker);
    assert.ok(i >= 0, '产物缺 STYLE-PACK 块');
    const start = html.indexOf('>', i) + 1;
    const end = html.indexOf('</script>', start);
    const block = JSON.parse(html.slice(start, end));
    const pkB = block.packs.find(p => p.packId === 'pk-b');
    Object.assign(pkB.tokens, {
      radiusMd: '33px', textSecondary: '#010203', space1: '99px', fontBody: 'Comic Sans MS', foo_bar: '3px',
      'font-num': TRAPS.fontNumVal, [TRAPS.extKey]: TRAPS.extVal
    });
    pkB.l2Overrides.push(
      { selector: TRAPS.l2Selector, props: 'color:red' },
      { selector: TRAPS.l2OkSelector, props: TRAPS.l2PropsVal },
      { selector: TRAPS.l2OkSelector, props: TRAPS.l2OkProps }
    );
    return html.slice(0, start) + JSON.stringify(block).replace(/</g, '\\u003c') + html.slice(end);
  })();
  const trapPath = path.join(dirA, 'product-trap.html');
  fs.writeFileSync(trapPath, trapHtml);

  /* ---- ② Playwright：运行时自身切换逻辑逐包断言 ---- */
  let library;
  for (const candidate of ['playwright', process.env.PLAYWRIGHT_MODULE_PATH,
    path.join(process.env.APPDATA || path.join(os.homedir(), 'AppData', 'Roaming'), 'npm', 'node_modules', 'playwright')].filter(Boolean)) {
    try { library = require(candidate); break; } catch (e) { /* next */ }
  }
  if (!library) { console.error('Playwright unavailable; set PLAYWRIGHT_MODULE_PATH or NODE_PATH'); process.exit(2); }
  const { chromium } = library;
  const browser = await chromium.launch({ headless: true });
  const ctx = await browser.newContext({ viewport: { width: 1600, height: 1100 } });
  const p = await ctx.newPage();
  const errors = [];
  p.on('pageerror', e => errors.push(e.message));
  await p.addInitScript(() => { window.showOpenFilePicker = async () => { throw new DOMException('QA: unbound', 'AbortError'); }; });
  await p.goto(pathToFileURL(trapPath).href);
  await p.waitForFunction(() => window.PROTO);
  await p.evaluate(() => { const b = [...document.querySelectorAll('dialog[open] button')].find(x => (x.textContent || '').includes('暂不绑定')); if (b) b.click(); });
  assert.equal(await p.evaluate(() => window.StylePanel.info().mode), 'registry', '面板应走风格登记块正式态');
  await p.locator('#btnEdit').click();
  await p.locator('#gatePassword').fill('12345678');
  await p.locator('#gateConfirm').click();
  await p.waitForFunction(() => PROTO.isUnlocked());
  const baselineAccent = (await p.evaluate(() => getComputedStyle(document.documentElement).getPropertyValue('--accent')).then(s => s.trim()));
  pass('产物解锁（编辑口令），面板正式态 registry；基线 --accent=' + baselineAccent);

  async function assertPack(packId) {
    const pack = packs.find(x => x.packId === packId);
    const t = pack.tokens;
    const rr = await p.evaluate(id => window.StylePanel.applyPack(id), packId);
    assert.ok(rr && rr.ok === true, 'applyPack(' + packId + ') 未成功: ' + JSON.stringify(rr));
    await p.waitForTimeout(400);
    const st = await p.evaluate(({ screenKeys, derivedKeys, rootKeys }) => {
      const scr = document.querySelector('#canvas .screen');
      const cs = getComputedStyle(scr);
      const root = getComputedStyle(document.documentElement);
      const read = (el, keys) => { const o = {}; for (const v of keys) o[v] = el.getPropertyValue(v).trim(); return o; };
      return {
        screen: read(cs, screenKeys),
        derived: read(cs, derivedKeys),
        root: read(root, rootKeys),
        fontFamily: cs.fontFamily, fontSize: cs.fontSize,
        heroBg: getComputedStyle(scr.querySelector('.hero')).backgroundColor,
        appbarBg: getComputedStyle(scr.querySelector('.appbar')).backgroundColor,
        cardBorderWidth: getComputedStyle(scr.querySelector('.card')).borderLeftWidth,
        cardVarAt: getComputedStyle(scr.querySelector('.card')).getPropertyValue('--sp-border-width').trim(),
        cardRuleBorder: (() => {
          const card = scr.querySelector('.card');
          let hit = null;
          for (const ss of document.styleSheets) {
            let rules; try { rules = ss.cssRules; } catch (e) { continue; }
            for (const r of rules) {
              if (r.selectorText && r.style && /var\(--sp-border-width/.test(r.style.getPropertyValue('border'))) {
                try { if (card.matches(r.selectorText)) hit = r.style.getPropertyValue('border'); } catch (e) { }
              }
            }
          }
          return hit;
        })(),
        uiStyle: document.documentElement.getAttribute('data-ui-style'),
        extVar: cs.getPropertyValue('--sp-glass-blur').trim(),
        camelRadiusMd: cs.getPropertyValue('--sp-radiusMd').trim(),
        invalidVar: cs.getPropertyValue('--sp-foo_bar').trim()
      };
    }, { screenKeys: Object.values(SCREEN_VARS).concat(Object.values(PAGE_COLOR_VARS))
        .concat(Object.entries(SOFT_EXPECT).filter(([, s]) => s.where === 'screen').map(([v]) => v)),
      derivedKeys: Object.values(SCREEN_DERIVED),
      rootKeys: Object.values(ROOT_VARS).concat(Object.values(DARK_VARS)).concat(['--accent-soft']) });
    for (const [key, varName] of Object.entries(SCREEN_VARS)) {
      const want = TRAP_DROP[packId + ':' + key] ? '' : String(t[key]);
      assert.equal(st.screen[varName], want, packId + ' 屏级 ' + varName + ' 期望 ' + want + ' 实得 ' + st.screen[varName]);
    }
    /* 页面五色：包带 dark 对象 → body.dark → 暗色映射（--sp-* 通道不动）；无 dark → 包亮色 */
    const dk = t.dark || {};
    const pageWant = t.dark
      ? { '--bg': dk.bg, '--surface': dk.surface, '--text': dk.text, '--muted': dk.muted, '--line': dk.line }
      : { '--bg': t['bg'], '--surface': t['surface'], '--text': t['text-primary'], '--muted': t['text-secondary'], '--line': t['border'] };
    for (const [key, varName] of Object.entries(PAGE_COLOR_VARS)) {
      assert.equal(st.screen[varName], String(pageWant[varName]),
        packId + ' 屏级 ' + varName + (t.dark ? '（暗色映射）' : '') + ' 期望 ' + pageWant[varName] + ' 实得 ' + st.screen[varName]);
    }
    for (const [key, varName] of Object.entries(SCREEN_DERIVED)) {
      assert.equal(st.derived[varName], String(t[key]), packId + ' ' + varName + ' 期望 ' + t[key] + ' 实得 ' + st.derived[varName]);
    }
    for (const [key, varName] of Object.entries(ROOT_VARS)) {
      assert.equal(st.root[varName], String(t[key]), packId + ' 根级 ' + varName + ' 期望 ' + t[key] + ' 实得 ' + st.root[varName]);
    }
    for (const [fld, varName] of Object.entries(DARK_VARS)) {
      assert.equal(st.root[varName], String(t.dark[fld]), packId + ' ' + varName + ' 期望 ' + t.dark[fld] + ' 实得 ' + st.root[varName]);
    }
    for (const [v, spec] of Object.entries(SOFT_EXPECT)) {
      const got = spec.where === 'root' ? st.root[v] : st.screen[v];
      assert.equal(got, rgba(t[spec.key], spec.alpha), packId + ' ' + v + ' 浅色推算（alpha ' + spec.alpha + '）');
    }
    assert.equal(normFont(st.fontFamily), normFont(t['font-body']), packId + ' 页面根 font-family 应为 font-body');
    assert.equal(st.fontSize, String(t['size-body']), packId + ' 页面根 font-size 应为 size-body');
    assert.equal(st.heroBg, rgbCss(t['hero']), packId + ' hero 横幅底色应为 hero 键');
    /* nav 键→导航条底色；包带 dark 对象时既有暗色规则把 appbar 压成暗表面色（body.dark 既有设计） */
    assert.equal(st.appbarBg, rgbCss(t.dark ? dk.surface : t['nav']),
      packId + ' appbar 底色应为 ' + (t.dark ? '暗表面色（dark 规则压过 nav）' : 'nav 键'));
    /* border-width 替代写死 1px：本环境 Chromium 对 <1px 边框做整像素取整（inline 0.5px 也计 1px），
       故非整数粗细断「继承值==包值 + 胜出规则消费 var(--sp-border-width)」两因子；整数粗细走计算值端到端断言 */
    assert.equal(st.cardVarAt, String(t['border-width']), packId + ' 卡片继承 --sp-border-width 应为 border-width 键');
    assert.ok(st.cardRuleBorder && st.cardRuleBorder.includes('var(--sp-border-width'),
      packId + ' 胜出的卡片规则应消费 var(--sp-border-width): ' + st.cardRuleBorder);
    if (parseFloat(t['border-width']) >= 1) {
      assert.equal(st.cardBorderWidth, String(t['border-width']), packId + ' 卡片计算边框粗细应为 border-width 键');
    }
    assert.equal(st.uiStyle, packId, packId + ' data-ui-style 未切换');
    assert.equal(st.extVar, String(t['glass-blur']), packId + ' 扩展键应生成 --sp-glass-blur 并透传');
    return st;
  }

  const stA = await assertPack('pk-a');
  pass('pk-a：正本表全部键的 emits 变量 == 包值（含 --sp-surface-alt/--ok|--danger|--warn 及 -soft/--sp-radius-*/--sp-shadow-*/--sp-border-width/--sp-font-num/--sp-grid-cols/--radius/--shadow），扩展键 --sp-glass-blur=7px，边框粗细替换写死 1px');
  const stB = await assertPack('pk-b');
  pass('pk-b：切换后同一断言集全部等于 pk-b 值（无上一包残留）');
  assert.notEqual(stB.screen['--muted'], '#010203', '驼峰键 textSecondary 不得被读取');
  assert.notEqual(stB.screen['--sp-radius-md'], '33px', '驼峰键 radiusMd 不得被读取');
  assert.notEqual(stB.screen['--sp-space-1'], '99px', '驼峰键 space1 不得被读取');
  assert.ok(!normFont(stB.fontFamily).includes('comicsans'), '驼峰键 fontBody 不得被读取');
  assert.equal(stB.camelRadiusMd, '', '驼峰键不得生成 --sp-<键名> 变量（--sp-radiusMd 应为空）');
  assert.equal(stB.invalidVar, '', '不合 keyPattern 的键（foo_bar）运行时忽略，不生成 --sp-foo_bar');
  pass('陷阱键：驼峰（radiusMd/textSecondary/space1/fontBody）与非法键（foo_bar）运行时一概不读、不猜、不生成变量');

  /* ---- 注入防御（cssSafe 纵深防御 + l2 选择器/props 过滤） ---- */
  const styleNodes = await p.evaluate(() =>
    ['prototype-style-override', 'prototype-style-l2', 'prototype-style-material']
      .map(id => { const n = document.getElementById(id); return n ? n.textContent : ''; }).join('\n'));
  for (const marker of ['pwned-canonical', 'pwned-ext', 'pwned-l2', 'pwned-props']) {
    assert.ok(!styleNodes.includes(marker), '注入载荷漏进覆盖样式: ' + marker);
  }
  assert.equal(await p.evaluate(() => getComputedStyle(document.querySelector('#canvas .screen'))
    .getPropertyValue('--sp-evil-glow').trim()), '', '注入载荷扩展键不得生成 --sp-evil-glow');
  assert.equal(stB.screen['--sp-font-num'], '', '注入载荷正本键（font-num）被 cssSafe 丢弃后应落 :root 基线（变量为空）');
  assert.ok(styleNodes.includes(TRAPS.l2OkProps), 'props 含分号的合法 l2 条目应正常应用（分号是声明分隔符，须保留）: ' + TRAPS.l2OkProps);
  pass('注入防御：正本键/扩展键值与 l2 props 含 ; } < 等载荷被过滤（props 整条跳过、分号语义保留），l2 非法选择器整条跳过，覆盖样式无载荷');

  /* ---- ⑤ 面板「风格令牌」行密度词 ---- */
  await p.evaluate(() => window.StylePanel.open());
  await p.waitForTimeout(200);
  const words = await p.evaluate(() => ({
    a: (document.querySelector('.ed-sp-card[data-pack="pk-a"] .ed-sp-tokens') || {}).textContent || '',
    b: (document.querySelector('.ed-sp-card[data-pack="pk-b"] .ed-sp-tokens') || {}).textContent || ''
  }));
  assert.ok(words.a.includes(DENSITY_WORDS[pkA['density']]), 'pk-a 面板密度词应为「' + DENSITY_WORDS[pkA['density']] + '」: ' + words.a);
  assert.ok(words.b.includes(DENSITY_WORDS[packs[1].tokens['density']]), 'pk-b 面板密度词应为「舒展」: ' + words.b);
  pass('面板「风格令牌」行：density 键优先（compact=紧凑 / loose=舒展），不出现键名或数值');

  /* ---- 恢复原方案（builtin 通道回归） ---- */
  const ro = await p.evaluate(() => window.StylePanel.restoreOriginal());
  assert.ok(ro && ro.ok === true, 'restoreOriginal 应成功: ' + JSON.stringify(ro));
  await p.waitForTimeout(300);
  const restored = await p.evaluate(() => ({
    accent: getComputedStyle(document.documentElement).getPropertyValue('--accent').trim(),
    uiStyle: document.documentElement.getAttribute('data-ui-style'),
    override: document.getElementById('prototype-style-override').textContent.length
  }));
  assert.equal(restored.accent, baselineAccent, '恢复后根 --accent 应回基线');
  assert.equal(restored.uiStyle, null, '恢复后应移除 data-ui-style');
  assert.equal(restored.override, 0, '恢复后 L1 覆盖节点应清空');
  pass('恢复原方案：builtin/原始方案通道不受键名统一影响（根色回基线、覆盖层卸载）');

  assert.equal(errors.length, 0, '页面运行时错误: ' + errors.join('\n'));
  pass('全程无浏览器运行时错误');

  console.log('\nRESULT: ' + results.length + '/' + results.length + ' PASS');
  fs.writeFileSync(path.join(tmp, 'verification-results.json'), JSON.stringify({ date: '2026-11-07', results }, null, 2));
  await browser.close();
})().catch(e => { console.error('FAIL', e && (e.stack || e.message) || e); process.exit(1); });
