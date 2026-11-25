// acc_render_diff — 渲染对账门：静态稿(基准) vs 注入后产物(新风格激活态) 逐屏计算样式差分
// 2026-11-24 定案（uni-ui 实测三连根因后固化）：机检/撞车/U2/回归全是机制回执，唯差分拦得住
// "选择器未命中/变量死/样式被压"类渲染退化（chips 竖排、hero 变深字均此类）。交付回执链硬项之一。
// 用法：node acc_render_diff.mjs --src <静态稿.html> --built <产物.html> --db db-<风格id> \
//        [--prefix <风格id>] [--out <report.json>] [--ignore-prop display]
// 屏配对：src data-screen="<id>" ↔ built data-screen="<prefix>-<id>"（prefix 缺省=--db 去 db- 前缀，
//   与注入器 <风格段>-<语义id> 前缀化规则同构）。
// 采样=从 .viewport 内容根起（壳包装不比对）、svg 子树跳过（sprite→内联合法转化）、旁批 aside 跳过
//   （旁批→data-note 属性化，子树内容合法消失）。每屏每侧采样上限 CAP=400 元素，触顶记入 report.truncated
//   （大屏截断=对账覆盖不全，console 明示，不算 FAIL 但使用方须知）。
// 对账=按单类聚合的值集（tag 兜底键管无类元素）：每类逐属性收集取值集合，双侧不一致=差异；
//   src 有此类 built 全无=类丢失 FAIL（anno 系除外=合法转 data-note）；built 独有类记 notice 不卡门。
// 前置（2026-11-24 standards 审查补）：产物须处于**新风格激活态**——state.domBaseId 存在且 ≠ --db 时拒报
//   （B 屏 var() 会消费原风格根变量=大面积假差异）；无 state 时尽力调 __spApplyStyleScreens 桥激活。
// 退出码：0=零差异；1=有差异/缺屏/丢类（FAIL）；2=playwright 不可用/目标打不开/前置不满足（按降级口径声明）。
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const path = require('path');
function loadChromium() {
  const tryReq = p => { try { return require(p); } catch (_) { return null; } };
  let pw = tryReq('playwright');
  if (!pw && process.env.PLAYWRIGHT_MODULE_PATH)
    pw = tryReq(path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'playwright'));
  if (!pw) {
    const g = path.join(process.env.APPDATA || '', 'npm', 'node_modules');
    pw = tryReq(path.join(g, 'playwright'));
  }
  if (!pw) return null;
  return pw.chromium;
}
function arg(name, def) {
  const i = process.argv.indexOf('--' + name);
  return i > 0 ? process.argv[i + 1] : def;
}
const SRC = arg('src') && path.resolve(arg('src'));
const BUILT = arg('built') && path.resolve(arg('built'));
const DB = arg('db');
const PREFIX = arg('prefix') || (DB || '').replace(/^db-/, '');
const OUT = arg('out') && path.resolve(arg('out'));
const IGNORE = new Set((arg('ignore-prop') || '').split(',').map(s => s.trim()).filter(Boolean));
const CAP = 400;
const PROPS = ['display', 'color', 'background-color', 'font-size', 'font-weight', 'border-radius', 'flex-direction', 'line-height'];
const LEGAL_LOST = new Set(['anno', 'anno-no']);              /* 旁批 aside.anno → data-note 合法转化 */
const BUILT_ONLY_OK = new Set(['app', 'anno-hidden']);        /* 编辑器内容容器/旁批态：built 侧合法新增 */
if (!SRC || !BUILT || !DB) {
  console.error('usage: node acc_render_diff.mjs --src <静态稿> --built <产物> --db db-<风格id> [--prefix <id>] [--out r.json] [--ignore-prop p1,p2]');
  process.exit(2);
}
for (const f of [SRC, BUILT]) if (!fs.existsSync(f)) {
  console.error('FAIL 目标文件不存在: ' + f);
  process.exit(2);
}
const chromium = loadChromium();
if (!chromium) {
  console.error('FAIL playwright 不可用（本地/PLAYWRIGHT_MODULE_PATH/npm 全局三级探测全空）——按 conversion.md 降级：逐屏渲染实看+交付说明声明"未做渲染差分"');
  process.exit(2);
}
const fileUrl = p => 'file:///' + encodeURI(p.replace(/\\/g, '/')).replace(/#/g, '%23');
const report = { src: SRC, built: BUILT, db: DB, screenCount: 0, missing: [], diffs: [], notices: [], truncated: [] };
let browser;
try {
  browser = await chromium.launch();
  const mkPage = async url => {
    const p = await browser.newPage({ viewport: { width: 1400, height: 900 } });
    try {
      await p.goto(url, { timeout: 30000 });
    } catch (e) {
      console.error('FAIL 目标打不开（检查路径与 file:// 可达性）: ' + url + ' —— ' + e.message);
      process.exit(2);
    }
    await p.waitForTimeout(1200);
    return p;
  };
  const showScreen = (page, sel) => page.evaluate(({ sel }) => {
    const el = document.querySelector(sel);
    if (!el) return false;
    document.querySelectorAll('section.screen').forEach(s => { s.style.display = 'none'; });
    el.style.display = 'block';
    return true;
  }, { sel });
  const sample = page => page.evaluate(({ cap, props }) => {
    const scr = [...document.querySelectorAll('section.screen')].find(s => s.style.display === 'block');
    if (!scr) return null;
    const root = scr.querySelector('.viewport') || scr;
    const all = [...root.querySelectorAll('*')]
      .filter(el => !el.closest('svg'))            /* sprite→内联合法转化 */
      .filter(el => !el.closest('aside.anno'));    /* 旁批→data-note 属性化，子树内容合法消失 */
    const els = all.slice(0, cap);
    const byClass = {}, byTag = {};
    els.forEach(el => {
      const c = getComputedStyle(el);
      const rec = {};
      for (const k of props) rec[k] = c[k];
      const cl = el.classList;
      if (cl && cl.length) [...cl].forEach(name => { (byClass[name] = byClass[name] || []).push(rec); });
      else (byTag[el.tagName.toLowerCase()] = byTag[el.tagName.toLowerCase()] || []).push(rec);
    });
    return { byClass, byTag, total: all.length, sampled: els.length };
  }, { cap: CAP, props: PROPS });
  const pSrc = await mkPage(fileUrl(SRC));
  const pBlt = await mkPage(fileUrl(BUILT));
  /* 前置：产物须处于新风格激活态（state.domBaseId 守门 + 无 state 时尽力调壳桥激活） */
  const st = await pBlt.evaluate(() => {
    const n = document.getElementById('prototype-style-state');
    try { return n ? JSON.parse(n.textContent) : null; } catch (e) { return null; }
  });
  if (st && st.domBaseId && st.domBaseId !== DB) {
    console.error('FAIL 前置不满足：产物当前激活风格 domBaseId=' + st.domBaseId + ' ≠ --db ' + DB +
      '——B 屏 var() 会消费原风格根变量产生大面积假差异。先切到新风格卡（或用 --active-pack=新风格 的产物）再跑对账门');
    process.exit(2);
  }
  if (!st || !st.domBaseId) {
    await pBlt.evaluate(pid => { if (window.__spApplyStyleScreens) window.__spApplyStyleScreens(pid); }, PREFIX);
    await pBlt.waitForTimeout(400);
  }
  const srcIds = await pSrc.evaluate(() => [...document.querySelectorAll('section.screen')].map(s => s.getAttribute('data-screen')));
  report.screenCount = srcIds.length;
  for (const id of srcIds) {
    const builtId = PREFIX ? PREFIX + '-' + id : id;
    const okS = await showScreen(pSrc, 'section.screen[data-screen="' + id + '"]');
    const okB = await showScreen(pBlt, 'section.screen[data-screen="' + builtId + '"]');
    if (!okS || !okB) {
      report.missing.push({ screen: id, builtId, side: (!okS && !okB) ? 'src+built' : (!okS ? 'src' : 'built') });
      continue;
    }
    await pSrc.waitForTimeout(120); await pBlt.waitForTimeout(120);
    const A = await sample(pSrc), B = await sample(pBlt);
    if (!A || !B) { report.missing.push({ screen: id, builtId, side: 'sample' }); continue; }
    if (A.total > CAP || B.total > CAP)
      report.truncated.push({ screen: id, srcSampled: A.sampled + '/' + A.total, builtSampled: B.sampled + '/' + B.total });
    const cmp = (ka, kb, kind, name) => {
      for (const key of new Set([...Object.keys(ka), ...Object.keys(kb)])) {
        const ra = ka[key], rb = kb[key];
        if (!ra) {
          if (kind === 'class' && BUILT_ONLY_OK.has(key)) continue;
          report.notices.push({ screen: id, kind, key, note: 'built 独有' });
          continue;
        }
        if (!rb) {
          if (kind === 'class' && LEGAL_LOST.has(key)) continue;
          report.diffs.push({ screen: id, kind, key, prop: 'presence', src: ra.length + '个', built: '0个' });
          continue;
        }
        if (ra.length !== rb.length)
          report.diffs.push({ screen: id, kind, key, prop: 'count', src: ra.length, built: rb.length });
        for (const k of PROPS) {
          if (IGNORE.has(k)) continue;
          const sa = [...new Set(ra.map(x => x[k]))].sort();
          const sb = [...new Set(rb.map(x => x[k]))].sort();
          if (JSON.stringify(sa) !== JSON.stringify(sb))
            report.diffs.push({ screen: id, kind, key, prop: k, src: sa.join('|'), built: sb.join('|') });
        }
      }
    };
    cmp(A.byClass, B.byClass, 'class');
    cmp(A.byTag, B.byTag, 'tag');
    if (report.diffs.length >= 200) { report.notices.push({ note: '差异 ≥200 条已截断——修一批重跑见余量' }); break; }
  }
  await browser.close();
} catch (e) {
  console.error('FAIL ' + e.message);
  process.exit(2);
}
if (OUT) fs.writeFileSync(OUT, JSON.stringify(report, null, 1), 'utf8');
const bad = report.diffs.length || report.missing.length;
console.log('屏数 ' + report.screenCount + ' | 差异 ' + report.diffs.length + ' | 缺屏 ' + report.missing.length +
  ' | notice ' + report.notices.length + ' | 截断屏 ' + report.truncated.length);
if (report.diffs.length) console.log('差异: ' + JSON.stringify(report.diffs.slice(0, 12)));
if (report.truncated.length) console.log('截断屏（覆盖不全，非 FAIL）: ' + JSON.stringify(report.truncated));
if (bad) { console.error('FAIL 渲染对账未过——逐条归因（选择器/变量/压种子类根因）后重跑，禁带差异交稿'); process.exit(1); }
console.log('PASS 渲染对账门：静态稿↔产物逐屏计算样式零差异（notice ' + report.notices.length + ' 条仅记录）');
