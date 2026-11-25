#!/usr/bin/env node
/* verify-interactions — execute every interaction claim from the start-doc as a Playwright assertion.
 * Usage: node verify-interactions.mjs <deliverable.html> <start-doc.md> [--out qa/interactions.json]
 *                                                       [--shots qa/shots] [--allow-dom-fallback]
 *
 * Claim schema (start-doc §6): {"page","eid","action","steps","assert",
 *   "viewport":"desktop"(opt),"decorative":true(opt)}
 * steps: [["click",value=data-eid|CSS (sel: prefix forces CSS)],["fill",CSS,val],["goto",screenId],["wait",ms]]
 * assert: ["text:...","selector:X","gone:X","url:..."]
 *
 * Guarantees:
 *  - auto page-switch per claim's `page` (preview shows only .screen.on)
 *  - claims are reconciled: every parse failure counts as FAIL, never silently skipped
 *  - decorative claims are skipped and reported separately (not in exit count)
 *  - DOM click fallback is OFF by default (T06.1): a failed real click fails the step/claim.
 *    Opt in with --allow-dom-fallback; every fallback-assisted step marks the claim record
 *    with inputMode:'dom-fallback' so the report can tell synthetic from real input.
 *  - interactive claims (T06.1) with BOTH steps and assert empty fail with
 *    ruleId 'E-CLAIM-ASSERT-EMPTY' (interactivity adjudicated against the contract fence
 *    when present; fail-safe to interactive when the contract is missing/unparseable)
 *  - each failed claim gets a screenshot when --shots is given
 *  - T18 binding-guide auto-dismiss (2.0.1): file:// deliverables auto-open a
 *    「绑定本地文件」showModal() guide containing #bdSkip on EVERY new page (sessionStorage
 *    is per-tab, so it re-pops each page). The native modal blocks every click outside it,
 *    so click steps would time out → guaranteed false negatives (axis-B final review,
 *    挑刺1). After each navigation, before any claim work, the tool briefly polls for
 *    `dialog[open] #bdSkip` and, when present, really clicks #bdSkip (仅浏览) to close it.
 *    Idempotent: no dialog → silent no-op; nothing else on the page is touched.
 *    Related (same round): at tool-chosen narrow viewports the fixed right note panel
 *    (#notePanel, 300px, open by default) overlaps the device frame and intercepts
 *    element-center hit testing — after guide dismissal the tool closes it via its own
 *    real #npClose button, and the mobile viewport is 540→640 so the 375px frame fits
 *    inside the canvas area (214px sidebar + 375px frame + slack).
 *
 * Exit codes (T00-冻结单 §2 统一语义, T06.1 迁移): 0 = pass; 1 = check/assert failures
 *  (failure COUNT goes into the report, NOT the exit code — the old cap-250 convention is
 *  retired); 2 = usage / unreadable input / environment or tool error (playwright missing,
 *  chromium launch failure, start-doc without any claims).
 *
 * --out report carries the frozen C05 header (§2, 一字不改): kind:'verify', reportVersion:1,
 *  checkerVersion, station:'U5', phase:null, scope:[pageId]|null, inputDigest,
 *  inputs:[{path,sha256(raw file bytes, 含开工文档; HTML 必含)}], result:'passed'|'fail'|'error',
 *  findings:[{ruleId,file,line,page,eid,featureId,expected,actual,severity}], coverage,
 *  generatedAt — plus the per-claim `results` detail. */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const { pathToFileURL } = require('url');

const CHECKER_VERSION = 'verify-interactions/2.0.1-t06.1';
const STATION = 'U5';

function sha256File(p) {
  /* 冻结单 §2：摘要 = 文件原始字节 SHA-256，任何一端不得去 BOM/改换行 */
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}
function trySha256(p) { try { return sha256File(p); } catch (_) { return null; } }
function inputsDigest(inputs) {
  /* 冻结单 §2 bundle 规范化同构：SHA-256( Σ sorted(path + ':' + sha256hex + '\n') )；
     排序键 = path 的 UTF-8 字节序；哈希对原始字节，禁 mtime。 */
  const lines = inputs.map(i => Buffer.from(`${i.path}:${i.sha256}\n`, 'utf8'));
  lines.sort(Buffer.compare);
  return crypto.createHash('sha256').update(Buffer.concat(lines)).digest('hex');
}

function loadChromium() {
  const tryReq = p => { try { return require(p); } catch (_) { return null; } };
  let pw = tryReq('playwright');
  if (!pw && process.env.PLAYWRIGHT_MODULE_PATH)
    pw = tryReq(path.join(process.env.PLAYWRIGHT_MODULE_PATH, 'playwright'));
  if (!pw) {
    const g = path.join(process.env.APPDATA || '', 'npm', 'node_modules');
    pw = tryReq(path.join(g, 'playwright'));
  }
  if (!pw) throw new Error('playwright not resolvable (local / PLAYWRIGHT_MODULE_PATH / npm global / NODE_PATH)');
  return pw.chromium;
}

/* ---- T18 绑定引导关闭（2.0.1，轴B终审挑刺1）----
 * file: 协议产物首开自动弹「绑定本地文件」showModal() 引导（种子 editor-seed：
 * ensureBindingDialog，含 #bdSkip 按钮）；无绑定句柄时同一 context 每个新 page 都重现
 * （sessionStorage 按 tab 隔离），且原生模态浮层阻断页面一切命中点击 → 含点击步骤的
 * claim 必然超时假阴性。引导由 IndexedDB 异步链（loadHandle）弹出，故导航后做一次
 * 短轮询检测 `dialog[open] #bdSkip`，存在则真实点击 #bdSkip（走种子自身处理器：
 * 关闭 + 本页登记 binding-skipped），幂等可重复调用；无引导时静默放行。 */
async function dismissBindingGuide(page) {
  try {
    await page.waitForFunction(
      () => !!document.querySelector('dialog[open] #bdSkip'),
      null,
      { timeout: 1200, polling: 60 }
    );
  } catch (_) { return false; } /* 引导未出现（或页面已不可用）→ 正常路径，不触碰页面 */
  try {
    await page.locator('#bdSkip').first().click({ timeout: 2000 });
    console.log('  ⌄ T18 binding guide detected — auto-clicked #bdSkip (仅浏览模式，不触碰页面状态)');
    return true;
  } catch (_) { return false; }
}

/* ---- 画布命中适配：标注面板遮挡（2.0.1，修1实测第二层阻断）----
 * 工具自选窄视口下，右侧标注面板（#notePanel，固定 300px，预览态默认展开）盖住设备框
 * 溢出区，元素中心命中测试落到面板上 → locator.click 超时（与绑定引导相互独立的第二层
 * 假阴性源；540 实测 hit=ASIDE#notePanel）。真实用户遇到面板遮挡的设计内动作就是点面板
 * 自身的 ✕（#npClose，V03R-panel-fix 后可用）；工具同样只走真实 UI 路径收面板，
 * 面板不存在或已收起时静默放行，收起失败不阻断（交给 click 自身行为裁决）。 */
async function closeNotePanel(page) {
  try {
    const st = await page.evaluate(() => {
      const np = document.getElementById('notePanel');
      if (!np) return 'absent';
      const r = np.getBoundingClientRect();
      return (r.width > 0 && r.height > 0) ? 'open' : 'closed';
    });
    if (st !== 'open') return false;
    await page.locator('#npClose').first().click({ timeout: 2000 });
    return true;
  } catch (_) { return false; }
}

/* ---- claim extraction: only §6 fence blocks; whole-block parse first, then per-line ----
 * T06.1 放宽：`page` 即受理为 claim（steps/assert 双空不再落入 badLines，
 * 改由验证期以 E-CLAIM-ASSERT-EMPTY 判 fail）；除此之外的坏行口径与旧版一致。
 * T21 契约围栏（V05⑤）：§6 内出现 ```interaction-claims 围栏时**只**从这些围栏读声明——
 * 普通 ```json 一律视为说明性示例不再执行（结构性隔离，"示例务必删除"不再依赖自觉）；
 * 无 interaction-claims 围栏则回退旧口径（全文 ```json 均视为声明，向后兼容旧开工文档）。 */
function extractClaims(md) {
  const claims = [], badLines = [];
  const sectionRe = /##\s*6[^\n]*\n([\s\S]*?)(?=\n##\s|\s*$)/;
  const sec = md.match(sectionRe);
  if (!sec) console.warn('WARNING: §6 header not found in start-doc — scanning whole document for claims');
  const scope = sec ? sec[1] : md; // fall back to whole doc if §6 header missing
  let fence;
  if (/```interaction-claims\s*\n/.test(scope)) {
    fence = /```interaction-claims\s*([\s\S]*?)```/g;
    console.warn('interaction-claims fence detected: claims read ONLY from ```interaction-claims blocks; plain ```json blocks are treated as examples and NOT executed');
  } else {
    fence = /```json\s*([\s\S]*?)```/g; // legacy: plain ```json blocks (backward compatible)
  }
  let m, fenceCount = 0;
  const tryParse = t => { try { return JSON.parse(t); } catch (_) { return undefined; } };
  const claimish = o => o && typeof o === 'object' && !!(o.page || o.steps || o.assert || o.claimId || o.action);
  while ((m = fence.exec(scope))) {
    fenceCount += 1;
    const body = m[1];
    const whole = tryParse(body.trim());
    if (whole !== undefined) {
      if (Array.isArray(whole)) {
        whole.forEach((o, i) => {
          if (o && typeof o === 'object' && o.page) claims.push(o);
          else badLines.push(`array item ${i}: ` + JSON.stringify(o).slice(0, 80));
        });
      } else if (whole && typeof whole === 'object' && whole.page) {
        claims.push(whole);
      } else if (claimish(whole)) {
        badLines.push(body.trim().slice(0, 80));
      }
      continue;
    }
    let parsedAny = false;
    for (const line of body.split('\n')) {
      const t = line.trim().replace(/^-,?\s*/, '').replace(/,?$/, '');
      if (!t.startsWith('{')) continue;
      const o = tryParse(t);
      if (o && typeof o === 'object' && o.page) { claims.push(o); parsedAny = true; }
      else if (o && typeof o === 'object' && claimish(o)) { badLines.push(t.slice(0, 80)); parsedAny = true; }
      else if (t.includes('page')) { badLines.push(t.slice(0, 80)); parsedAny = true; } // looks like a claim, parse failed
    }
    if (!parsedAny) badLines.push('unparseable fence block: ' + body.trim().slice(0, 80));
  }
  return { claims, badLines, fenceCount };
}

/* ---- interactivity adjudication (for E-CLAIM-ASSERT-EMPTY) ----
 * contractFeatureKinds: featureId -> kind from the ```prototype-contract fence; null when absent/unparseable. */
function contractFeatureKinds(md) {
  const m = md.match(/```prototype-contract\s*([\s\S]*?)```/);
  if (!m) return null;
  try {
    const c = JSON.parse(m[1].trim());
    const map = new Map();
    for (const p of (c.pages || [])) for (const f of (p.features || [])) map.set(f.id, f.kind);
    return map;
  } catch (_) { return null; }
}
function claimIsInteractive(claim, kinds) {
  if (Array.isArray(claim.steps) && claim.steps.length) return true;
  if (!kinds) return true; // 无法反证 → 按交互声明处理（fail-safe）
  const ids = Array.isArray(claim.featureIds) ? claim.featureIds : [];
  if (!ids.length) return true; // 无 feature 锚点 → 无法反证
  return ids.some(id => kinds.get(id) === 'interactive');
}

const isMain = (() => {
  try { return !!process.argv[1] && import.meta.url === pathToFileURL(path.resolve(process.argv[1])).href; }
  catch (_) { return false; }
})();

async function main() {
  const argv = process.argv.slice(2);
  const htmlPath = argv[0];
  const docPath = argv[1];
  const USAGE = 'usage: node verify-interactions.mjs <deliverable.html> <start-doc.md> [--out qa/interactions.json] [--shots qa/shots] [--allow-dom-fallback]';
  if (!htmlPath || !docPath || String(htmlPath).startsWith('--') || String(docPath).startsWith('--')) {
    console.error(USAGE);
    process.exit(2);
  }
  const optVal = name => { const i = argv.indexOf(name); return i > 0 ? argv[i + 1] : undefined; };
  const allowDomFallback = argv.includes('--allow-dom-fallback');
  const outArg = optVal('--out') ?? 'qa/interactions.json';
  const shotsDir = optVal('--shots');

  /* ---- report state（声明先于 helpers，envExit 早退路径也能落一份 error 报告）---- */
  const findings = [];
  const results = [];
  const decorative = [];
  let skippedEmptyDisplay = 0;
  let domFallbackSteps = 0;
  const declaredInputs = [htmlPath, docPath];

  function pushFinding(ruleId, file, extra) {
    /* §2 findings schema：{ruleId,file,line,page,eid,featureId,expected,actual,severity} */
    findings.push({ ruleId, file, line: null, page: null, eid: null, featureId: null, expected: null, actual: null, severity: 'error', ...extra });
  }
  function writeReport(result) {
    if (!outArg) return;
    const inputs = declaredInputs.map(p => ({ path: p, sha256: trySha256(p) }));
    const scope = [...new Set(results.filter(r => !r.broken && r.page && r.page !== '?').map(r => r.page))].sort();
    const report = {
      kind: 'verify',
      reportVersion: 1,
      checkerVersion: CHECKER_VERSION,
      station: STATION,
      phase: null, /* verify 档不分增量/终验；T06.2 联调如需再接 */
      scope: scope.length ? scope : null,
      inputDigest: inputsDigest(inputs),
      inputs, /* [{path, sha256(原始字节)}]：HTML 必含 + 开工文档 */
      result, /* 'passed' | 'fail' | 'error' */
      findings,
      coverage: {
        claims: results.filter(r => !r.broken).length,
        badLines: results.filter(r => r.broken).length,
        total: results.length - decorative.length - skippedEmptyDisplay,
        passed: results.filter(r => r.passed === true).length,
        failed: results.filter(r => r.passed === false).length,
        decorative: decorative.length,
        skippedEmptyDisplay,
        domFallbackAllowed: allowDomFallback,
        domFallbackSteps,
      },
      generatedAt: new Date().toISOString(),
      results, /* 逐 claim 明细（含 inputMode / claimId / featureId / shot） */
    };
    try {
      fs.mkdirSync(path.dirname(path.resolve(outArg)), { recursive: true });
      fs.writeFileSync(path.resolve(outArg), JSON.stringify(report, null, 2));
      console.error('report: ' + path.resolve(outArg));
    } catch (e) { console.error('FAIL cannot write report: ' + (e.message || e)); }
  }
  function envExit(msg, ruleId = 'E-ENV-ERROR', file = null) {
    /* 2 = 参数/文件不可读/环境或工具错误 */
    console.error('FAIL ' + msg);
    pushFinding(ruleId, file, { expected: 'prerequisite satisfied', actual: String(msg).slice(0, 200) });
    writeReport('error');
    process.exit(2);
  }

  if (!fs.existsSync(htmlPath)) envExit('deliverable not found: ' + htmlPath, 'E-ENV-INPUT-MISSING', htmlPath);
  if (!fs.existsSync(docPath)) envExit('start-doc not found: ' + docPath, 'E-ENV-INPUT-MISSING', docPath);

  let chromium;
  try { chromium = loadChromium(); }
  catch (e) { envExit(e.message, 'E-ENV-PLAYWRIGHT'); }

  let md;
  try { md = fs.readFileSync(docPath, 'utf8'); }
  catch (e) { envExit('start-doc unreadable: ' + (e.message || e), 'E-ENV-INPUT-UNREADABLE', docPath); }

  const { claims, badLines } = extractClaims(md);
  if (!claims.length && !badLines.length) {
    envExit('no interaction claims found in start-doc §6 — nothing to verify', 'E-ENV-NO-CLAIMS', docPath);
  }
  badLines.forEach(t => claims.push({ page: '?', eid: '?', action: 'UNPARSEABLE CLAIM LINE: ' + t, broken: true }));

  const url = pathToFileURL(path.resolve(htmlPath)).href;
  let browser;
  try { browser = await chromium.launch(); }
  catch (e) { envExit('chromium launch failed: ' + String(e).split('\n')[0], 'E-ENV-CHROMIUM'); }

  const kinds = contractFeatureKinds(md);
  let shotN = 0;
  let page = null;

  for (const c of claims) {
    const rec = {
      claimId: c.claimId ?? null,
      page: c.page, eid: c.eid ?? null, action: c.action ?? null,
      featureId: (Array.isArray(c.featureIds) && c.featureIds[0]) || null,
      expect: c.expect ?? null,
      inputMode: 'real-input',
      passed: false, error: null,
    };
    if (c.broken) {
      rec.broken = true;
      rec.error = 'unparseable claim line';
      results.push(rec);
      console.log('  ✗ [' + rec.page + '] ' + rec.action);
      continue;
    }
    if (c.decorative) {
      rec.passed = null; rec.error = 'decorative (declared, skipped)';
      decorative.push(rec); results.push(rec);
      console.log('  ◦ [' + rec.page + '] ' + rec.action + ' — decorative (declared, skipped)');
      continue;
    }
    /* T06.1：交互声明 steps 与 assert 全空 → 该 claim fail（E-CLAIM-ASSERT-EMPTY）；
       纯 display 且双空 → 无可验证内容，按 skipped 登记不冒充通过 */
    if ((c.steps?.length ?? 0) === 0 && (c.assert?.length ?? 0) === 0) {
      if (claimIsInteractive(c, kinds)) {
        rec.error = 'interactive claim declares neither steps nor assert';
        rec.ruleId = 'E-CLAIM-ASSERT-EMPTY';
        pushFinding('E-CLAIM-ASSERT-EMPTY', docPath, {
          page: rec.page, eid: rec.eid, featureId: rec.featureId, severity: 'fail',
          expected: 'interactive claim declares steps or assert', actual: 'steps:0 assert:0',
        });
        results.push(rec);
        console.log('  ✗ [' + rec.page + '] ' + rec.action + ' — ' + rec.error);
      } else {
        rec.passed = null;
        rec.error = 'display claim with empty steps and assert — nothing to verify (skipped)';
        skippedEmptyDisplay += 1;
        results.push(rec);
        console.log('  ◦ [' + rec.page + '] ' + rec.action + ' — ' + rec.error);
      }
      continue;
    }
    if (c.viewport && !['mobile', 'desktop'].includes(c.viewport)) {
      rec.error = 'unknown viewport: ' + c.viewport;
      results.push(rec);
      console.log('  ✗ [' + rec.page + '] ' + rec.action + ' — ' + rec.error);
      continue;
    }
    /* 视口只需装下编辑器 chrome + 设备框（mobile 框固定 375 宽 / desktop 框 1200 宽），
       页面内容断言均发生在设备框内部，与真实移动/桌面体验等效；
       视口过窄会让画布 < 设备框宽，flex 居中溢出导致 hit-test 异常。
       2.0.1 实测：mobile 540 时画布区仅 326px < 375px 框宽，屏幕滑入右侧 300px 标注面板
       底下（元素中心命中落 ASIDE#notePanel → click 必超时）；mobile 提到 640（画布区
       426px ≥ 375px 框宽 + 51px 余量，框完全在画布区内），配合引导后收面板后命中畅通 */
    // 2026-11-19 25 屏全量实测：640 时左侧页面树出现滚动条，device 左缘元素（页内返回钮 x≈148）
    // 中心命中落 ASIDE.ed-sidepanel → real click 必超时（假阴性）。mobile 提到 800。
    const vp = c.viewport === 'desktop' ? { width: 1440, height: 900 } : { width: 800, height: 900 };
    try {
      page = await browser.newPage({ viewport: vp });
      await page.goto(url, { waitUntil: 'load' });
      await page.waitForTimeout(300);
      /* T18 绑定引导（2.0.1）：必须先关引导再切页/执行步骤——showModal 会同时阻断
         #tabs 页签点击与画布命中，且每个新 page 都会重现，故放在 newPage 之后最先处理；
         引导关闭后随即收起标注面板（真实 UI 路径 #npClose），解除窄视口画布命中遮挡 */
      await dismissBindingGuide(page);
      await closeNotePanel(page);
      /* auto page-switch: preview shows only .screen.on — use the runtime's nav tab.
         2.0.1：let —— claim 内 goto 步骤真实切屏后，作用域必须跟随导航（见下） */
      let screenId = await page.evaluate(pageField => {
        if (!pageField) return null;
        let el = document.querySelector(`[data-screen="${pageField}"]`);
        if (!el) {
          el = [...document.querySelectorAll('[data-name]')]
            .find(s => (s.getAttribute('data-name') || '') === pageField);
        }
        return el ? el.getAttribute('data-screen') : null;
      }, c.page);
      if (c.page && !screenId) throw new Error('unknown page: ' + c.page + ' (no matching data-screen/data-name)');
      if (screenId) {
        const tab = page.locator(`#tabs .ed-tab[data-go="${screenId}"]`).first();
        try { await tab.click({ timeout: 4000 }); }
        catch (_) {
          await page.evaluate(id => {
            if (typeof goTo === 'function') { goTo(id); return; }
            const t = document.querySelector(`[data-screen="${id}"]`);
            if (t) t.scrollIntoView({ behavior: 'instant', block: 'start' });
          }, screenId);
        }
        await page.waitForTimeout(250);
      }
      for (const step of (c.steps || [])) {
        const [op, a, b] = step;
        if (op === 'click') {
          const val = String(a);
          /* 2.0.1：click 可能触发页面跳转（data-on click.goto），后续步骤的作用域必须
             跟随运行时当前屏（.screen.on）——跨屏步骤序列（goto 列表→点卡片→点返回）
             若作用域钉死在 claim 起始屏，元素定位落空 → 8s 超时假阴性 */
          try {
            const cur = await page.evaluate(() => {
              const s = document.querySelector('.screen.on');
              return s ? s.getAttribute('data-screen') : null;
            });
            if (cur) screenId = cur;
          } catch (_) { /* 刷新失败沿用旧作用域 */ }
          const loc = (val === c.eid || !val || !val.startsWith('sel:'))
            ? page.locator(`[data-screen="${screenId}"] [data-eid="${val.replace(/^sel:/, '')}"]`).first()
            : page.locator(val.replace(/^sel:/, '')).first();
          /* 部分可见的元素不会被 Playwright 自动滚动，而其可点区可能被固定底栏遮挡——
             先滚到视口中央（模拟真实用户滑动），再做命中点击 */
          try {
            await page.evaluate(({ scr, val }) => {
              const root = scr ? document.querySelector(`[data-screen="${scr}"]`) : document;
              const el = root && root.querySelector(`[data-eid="${String(val).replace(/^sel:/, '')}"]`);
              if (el) el.scrollIntoView({ block: 'center' });
            }, { scr: screenId, val });
            await page.waitForTimeout(120);
          } catch (_) { /* 滚动失败不阻断，交给 click 自己处理 */ }
          try {
            await loc.click({ timeout: 8000 });
          } catch (clickErr) {
            if (!allowDomFallback) {
              /* T06.1：DOM 兜底默认关闭——真实点击失败即本步失败，不做原生 .click() 补救 */
              throw new Error('real click failed ('
                + String(clickErr && clickErr.message || clickErr).split('\n')[0].slice(0, 160)
                + '); DOM fallback disabled (pass --allow-dom-fallback to opt in)');
            }
            /* 兜底仅在 CLI 显式 --allow-dom-fallback 时执行；兜底触达步骤标 inputMode:'dom-fallback'。
               固定栏遮挡等编辑器渲染现象导致坐标命中失败时，原生 click 直触发元素
               （data-on 由预览态 document 级委托监听，冒泡触发，交互动作真实执行） */
            rec.inputMode = 'dom-fallback';
            domFallbackSteps += 1;
            await page.evaluate(({ scr, val }) => {
              const root = scr ? document.querySelector(`[data-screen="${scr}"]`) : document;
              const el = root && root.querySelector(String(val).startsWith('sel:') ? String(val).slice(4) : `[data-eid="${String(val).replace(/^sel:/, '')}"]`);
              if (!el) throw new Error('click fallback: element not found: ' + val);
              el.click();
            }, { scr: screenId, val });
          }
        } else if (op === 'fill') {
          await page.locator(String(a).replace(/^sel:/, '')).first().fill(String(b ?? ''));
        } else if (op === 'goto') {
          const tab = page.locator(`#tabs .ed-tab[data-go="${a}"]`).first();
          try { await tab.click({ timeout: 4000 }); }
          catch (_) {
            await page.evaluate(id => {
              if (typeof goTo === 'function') { goTo(id); return; }
              const t = document.querySelector(`[data-screen="${id}"]`);
              if (t) t.scrollIntoView({ behavior: 'instant', block: 'start' });
            }, a);
          }
          await page.waitForTimeout(250);
          /* 2.0.1：goto 已真实切屏，后续 click 的 data-screen 作用域必须跟随导航；
             否则跨屏步骤序列（goto 列表→点卡片→点返回）作用域钉死在 claim 起始屏，
             元素定位落空 → 8s 超时假阴性 */
          screenId = a;
        } else if (op === 'wait') {
          await page.waitForTimeout(Number(a) || 300);
        } else {
          throw new Error('unknown step op: ' + op);
        }
      }
      await page.waitForTimeout(250);
      for (const a of (c.assert || [])) {
        if (a.startsWith('selector:')) {
          await page.locator(a.slice('selector:'.length)).first().waitFor({ state: 'visible', timeout: 3000 });
        } else if (a.startsWith('gone:')) {
          await page.locator(a.slice('gone:'.length)).first().waitFor({ state: 'hidden', timeout: 3000 });
        } else if (a.startsWith('text:')) {
          /* visible=true: 全 DOM 多屏并存时，text= 的 first() 可能命中其他 display:none 屏里的同名文案，
             对其等可见性必然超时（假失败）。只认当前真实可见的匹配。 */
          await page.locator(`text=${a.slice('text:'.length)} >> visible=true`).first().waitFor({ timeout: 3000 });
        } else if (a.startsWith('url:')) {
          if (!page.url().includes(a.slice('url:'.length))) throw new Error('url mismatch');
        } else {
          throw new Error('unknown assert: ' + a);
        }
      }
      rec.passed = true;
      await page.close();
      page = null;
    } catch (e) {
      rec.error = String(e.message || e).split('\n')[0].slice(0, 240);
      /* failure evidence: screenshot the ACTUAL failed page (not a fresh first screen) */
      if (page && shotsDir) {
        try {
          fs.mkdirSync(path.resolve(shotsDir), { recursive: true });
          const safeEid = String(c.eid || 'claim').replace(/[\\/:*?"<>|]/g, '_');
          shotN += 1;
          const fname = `fail-${String(shotN).padStart(2, '0')}-${safeEid}.png`;
          await page.screenshot({ path: path.join(path.resolve(shotsDir), fname) });
          rec.shot = fname;
        } catch (_) { /* screenshot is best-effort */ }
      }
      if (page) { try { await page.close(); } catch (_) { } page = null; }
    }
    results.push(rec);
    const mark = rec.passed === true ? '  ✓ ' : (rec.passed === null ? '  ◦ ' : '  ✗ ');
    console.log(mark + `[${c.page}] ${c.action}` + (rec.error && rec.passed !== true ? ' — ' + rec.error : ''));
  }
  try { await browser.close(); } catch (_) { }

  /* ---- reconcile → findings → report → exit（0/1/2，失败数只进报告）---- */
  const failedRecs = results.filter(r => r.passed === false);
  for (const r of failedRecs) {
    if (r.ruleId) continue; /* E-CLAIM-ASSERT-EMPTY 已在命中点登记，不重复入 findings */
    pushFinding(r.broken ? 'E-CLAIM-UNPARSEABLE' : 'E-VERIFY-CLAIM-FAILED',
      r.broken ? docPath : htmlPath,
      {
        page: r.page, eid: r.eid, featureId: r.featureId, severity: 'fail',
        expected: r.broken ? 'claim parses per §6 schema' : (r.expect || 'claim steps+asserts all pass'),
        actual: r.error || 'failed',
      });
  }
  const failed = failedRecs.length;
  const passed = results.filter(r => r.passed === true).length;
  writeReport(failed > 0 ? 'fail' : 'passed');
  console.log(`\nreconciliation: ${passed} passed / ${failed} failed / ${decorative.length} decorative skipped / ${skippedEmptyDisplay} empty-display skipped (claims+badlines = ${results.length})`);
  console.log(`exit: ${failed > 0 ? 1 : 0} — ${failed} failure(s) recorded in report, not in exit code (冻结单 §2 统一语义)`);
  process.exit(failed > 0 ? 1 : 0);
}

if (isMain) {
  main().catch(e => { console.error('FAIL ' + String((e && e.stack) || e)); process.exit(2); });
}
export { extractClaims, contractFeatureKinds, claimIsInteractive, inputsDigest, sha256File, CHECKER_VERSION, STATION };
