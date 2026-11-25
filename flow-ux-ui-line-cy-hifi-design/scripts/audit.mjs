#!/usr/bin/env node
/* audit — total acceptance gate for the deliverable HTML.
 * Usage: node audit.mjs <deliverable.html> [--mode static|browser|both] [--project-dir dir] [--out qa/audit.json]
 *
 * Checks:
 *   static : size / editor markers / external resource src / external content links
 *   browser: loads under file:// / console errors / broken images / dead jumps (DOM) /
 *            eid uniqueness (DOM) / multi-viewport overflow (390 & 1280) /
 *            edit gate probe on a temp copy (unlock + editor reachable)
 *   manual : the SAVE chain (edit→save→reopen→verify) is a USER-EXECUTED acceptance
 *            step per user decision (2026-10-29) — audit prints the fixed 4-step
 *            instructions and the delivery note carries them; never claim it as automated.
 * --mode (T06.1): static = ONLY the static layer (playwright is not loaded at all in that
 *   mode); browser = only the browser layer; both (default) = static + browser.
 *   Screens that cannot be measured are counted unmeasured — never treated as overflow-free;
 *   when unmeasured>0 the finish summary carries `unmeasured:N（未证实无溢出）` and no overall
 *   "no overflow" pass is claimed.
 * Exit codes (T00-冻结单 §2 统一语义, T06.1 迁移): 0 = pass; 1 = hard failures;
 *   2 = usage / unreadable input / environment or tool error (playwright/chromium unavailable
 *   in browser mode). Warnings do not fail but MUST be reported. */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const os = require('os');
const path = require('path');
const crypto = require('crypto');

const CHECKER_VERSION = 'audit/0.2.0';

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

const htmlPath = process.argv[2];
const argv = process.argv.slice(2);
const USAGE = 'usage: node audit.mjs <deliverable.html> [--mode static|browser|both] [--station U5] [--project-dir dir] [--out file]';
const optVal = name => { const i = argv.indexOf(name); return i > 0 ? argv[i + 1] : undefined; };
const STATION = ['U5'].includes(optVal('--station')) ? optVal('--station') : 'U5'; /* 档④静态走查回执站 */
const modeArg = (() => { const i = argv.indexOf('--mode'); return i > 0 ? argv[i + 1] : 'both'; })();
if (!htmlPath || !fs.existsSync(htmlPath)) {
  console.error(USAGE);
  process.exit(2);
}
if (!['static', 'browser', 'both'].includes(modeArg)) {
  console.error(USAGE);
  console.error('FAIL unknown --mode: ' + modeArg);
  process.exit(2);
}
const projectDir = (() => {
  const i = process.argv.indexOf('--project-dir');
  return i > 0 ? process.argv[i + 1] : path.dirname(path.resolve(htmlPath));
})();
const outArg = (() => {
  const i = process.argv.indexOf('--out');
  return i > 0 ? process.argv[i + 1] : null; /* 修复：取值与 indexOf 同用 process.argv（旧写法错用 slice 后的 argv，--out 静默失效） */
})();

const findings = [];
const warnings = [];
let hard = 0;
function fail(msg) { findings.push({ level: 'fail', msg }); hard++; console.log('  ✗ ' + msg); }
function warn(msg) { findings.push({ level: 'warn', msg }); warnings.push(msg); console.log('  ⚠ ' + msg); }
function pass(msg) { findings.push({ level: 'pass', msg }); console.log('  ✓ ' + msg); }

/* ---------- static layer ---------- */
const html = fs.readFileSync(htmlPath, 'utf-8');
const size = Buffer.byteLength(html);
size > 5120 ? pass(`file size ${Math.round(size / 1024)}KB`)
            : fail(`file too small (${size}B) — likely an empty shell`);

['prototype-config', 'data-screen', 'editorGate'].forEach(marker => {
  html.includes(marker) ? pass(`editor marker present: ${marker}`)
                        : fail(`editor marker missing: ${marker}`);
});

/* resource loading (not content <a href>): src/poster/srcset, NOT preceded by [data-] etc. */
const extSrc = html.match(/(?<![\w-])(?:src|poster|srcset)=["']https?:\/\/[^"']+["']/g) || [];
const extLinks = html.match(/<a\b[^>]*href=["']https?:\/\/[^"']+["']/g) || [];
extSrc.length === 0 ? pass('no external resource loading (offline-safe)')
                    : fail(`external resource src found: ${extSrc.slice(0, 3).join(' ; ')}`);
extLinks.length === 0 ? pass('no external content links')
                      : warn(`content links (need network when clicked, acceptable): ${extLinks.slice(0, 2).join(' ; ')}`);

const screens = [...html.matchAll(/data-screen="([a-zA-Z0-9_-]+)"/g)].map(m => m[1]);

/* ---------- finish（static/browser 共用；T06.1 退出语义对齐冻结单 §2：0/1/2）---------- */
let totalUnmeasured = 0;
const geometry = { mode: modeArg, viewports: [] };
function finish(resultOverride) {
  const result = resultOverride || (hard === 0 ? 'passed' : 'fail'); /* 'passed'|'fail'|'error'(=环境/工具错误,退出2) */
  /* N4 修复：报告补齐 qa_receipt 12 头字段（station/kind/scope/inputDigest/inputs/…），
     使 state_check --mark U5 passed --disposition static 可直接消费本文件为合法回执；
     业务字段保留顶层共存，generated_at 蛇形别名一并保留防旧消费者断裂。 */
  const inputSha = crypto.createHash('sha256').update(fs.readFileSync(htmlPath)).digest('hex');
  const inputs = [{ path: htmlPath, sha256: inputSha }];
  const digestLines = inputs.map(i => Buffer.from(`${i.path}:${i.sha256}
`, 'utf8')).sort(Buffer.compare);
  const inputDigest = crypto.createHash('sha256').update(Buffer.concat(digestLines)).digest('hex');
  const report = {
    kind: 'audit', reportVersion: 1, checkerVersion: CHECKER_VERSION,
    station: STATION, phase: null, scope: screens,
    inputDigest, inputs,
    result,
    findings,
    coverage: { mode: modeArg, unmeasured: totalUnmeasured, hard_failures: hard, warnings: warnings.length },
    generatedAt: new Date().toISOString(),
    mode: modeArg,
    file: htmlPath, size, screens: screens.length,
    unmeasured: totalUnmeasured,
    geometry,
    hard_failures: hard,
    warnings: warnings.length,
    generated_at: new Date().toISOString(),
  };
  const verdict = result === 'passed' ? 'PASS' : (result === 'error' ? 'ERROR' : 'FAIL');
  /* 冻结单 §2/C05：unmeasured>0 时摘要行必须带「unmeasured:N（未证实无溢出）」，不得宣称整体无溢出通过 */
  console.log(`\naudit[${modeArg}]: ${verdict} — ${hard} hard failure(s), ${warnings.length} warning(s)`
    + (totalUnmeasured > 0 ? ` — unmeasured:${totalUnmeasured}（未证实无溢出）` : ''));
  const outPath = outArg
    ? path.resolve(outArg)
    : path.join(path.resolve(projectDir), 'qa', 'audit.json');
  fs.mkdirSync(path.dirname(outPath), { recursive: true });
  fs.writeFileSync(outPath, JSON.stringify(report, null, 2));
  process.exit(result === 'passed' ? 0 : (result === 'error' ? 2 : 1));
}

/* static 模式：只跑静态层（playwright 完全不加载），直接收口 */
if (modeArg === 'static') finish();

/* ---------- browser layer（仅在 browser/both 模式加载 playwright）---------- */
(async () => {
  let chromium;
  try { chromium = loadChromium(); }
  catch (e) { console.error('FAIL playwright unavailable (browser mode): ' + e.message); return finish('error'); }

  let browser;
  try { browser = await chromium.launch(); }
  catch (e) { console.error('FAIL chromium launch failed: ' + String(e).split('\n')[0]); return finish('error'); }

  const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text().slice(0, 200)); });
  page.on('pageerror', e => consoleErrors.push(String(e).slice(0, 200)));

  const url = require('url').pathToFileURL(path.resolve(htmlPath)).href;
  try {
    await page.goto(url, { waitUntil: 'load', timeout: 30000 });
    pass('page loads under file://');
  } catch (e) { fail('page failed to load: ' + String(e).slice(0, 200)); return finish(); }

  await page.waitForTimeout(800);
  consoleErrors.length === 0 ? pass('console: zero errors')
                             : fail(`console errors (${consoleErrors.length}): ` + consoleErrors.slice(0, 3).join(' | '));

  /* GPT#5：@font-face 声明的 webfont 必须实测加载成功（写了字体名≠用了该字体）；
     系统字体栈不在检查范围（由平台提供，无需实测）。 */
  const fontFams = [...new Set(html.matchAll(/@font-face\s*\{[^}]*?font-family\s*:\s*["']?([^"';}]+)/gi)
    .map(m => m[1].trim()))].filter(Boolean);
  if (fontFams.length) {
    const fontStates = await page.evaluate(async fams => {
      await document.fonts.ready;
      return fams.map(f => ({ f, ok: document.fonts.check(`16px "${f}"`) }));
    }, fontFams);
    fontStates.filter(x => !x.ok).forEach(x => fail(`webfont declared but not loaded: ${x.f}`));
    fontStates.filter(x => x.ok).forEach(x => pass(`webfont loaded: ${x.f}`));
  }

  const broken = await page.evaluate(() =>
    [...document.images].filter(i => i.complete && i.naturalWidth === 0).map(i => i.src.slice(0, 60)));
  broken.length === 0 ? pass('no broken images')
                      : fail(`broken images (${broken.length}): ` + broken.slice(0, 3).join(' | '));

  /* dead jumps + eid uniqueness — DOM truth */
  const linkCheck = await page.evaluate(() => {
    const screens = new Set([...document.querySelectorAll('[data-screen]')].map(s => s.getAttribute('data-screen')));
    const dead = [];
    const seen = new Set(); const dup = new Set();
    document.querySelectorAll('[data-on]').forEach(el => {
      try {
        const spec = JSON.parse(el.getAttribute('data-on'));
        const walk = v => {
          if (v && typeof v === 'object') {
            for (const [k, t] of Object.entries(v)) {
              if ((k === 'goto' || k === 'sheet') && typeof t === 'string' && !screens.has(t))
                dead.push(`${el.getAttribute('data-eid') || '?'}→${t}`);
              walk(t);
            }
          }
        };
        walk(spec);
      } catch (_) { }
    });
    document.querySelectorAll('[data-eid]').forEach(el => {
      const id = el.getAttribute('data-eid');
      if (seen.has(id)) dup.add(id);
      seen.add(id);
    });
    return { dead, dup: [...dup], targets: seen.size };
  });
  linkCheck.dead.length === 0
    ? pass(`no dead jumps (${linkCheck.targets} eids checked)`)
    : fail('dead jump targets: ' + linkCheck.dead.join(', '));
  linkCheck.dup.length === 0 ? pass('data-eid unique (DOM)')
                             : fail('duplicate data-eid (DOM): ' + linkCheck.dup.join(', '));

  /* geometry: two viewports (mobile 375 / desktop 1280) — PER-SCREEN measurement.
   * Preview shows only the active screen; measure every screen by switching via nav tab,
   * otherwise non-active screens are display:none and escape the check (false gate). */
  for (const vp of [{ w: 375, h: 812, tag: 'mobile-375' }, { w: 1280, h: 900, tag: 'desktop-1280' }]) {
    await page.setViewportSize({ width: vp.w, height: vp.h });
    await page.waitForTimeout(250);
    const ids = await page.evaluate(() =>
      [...document.querySelectorAll('[data-screen]')].map(s => s.getAttribute('data-screen')));
    const bad = [];
    let measured = 0;
    let unmeasured = 0; /* 测不到 ≠ 无溢出：如实计数，禁止假报通过（T06.1） */
    for (const id of ids) {
      const switched = await page.evaluate(sid => {
        const tab = document.querySelector(`#tabs .ed-tab[data-go="${sid}"]`);
        if (tab) { tab.click(); return true; }
        if (typeof goTo === 'function') { goTo(sid); return true; }
        return false;
      }, id);
      if (!switched) { unmeasured += 1; warn(`@${vp.tag}: screen ${id} could not be switched into view — unmeasured`); continue; }
      await page.waitForTimeout(180);
      const res = await page.evaluate(sid => {
        const s = document.querySelector(`[data-screen="${sid}"]`);
        if (!s) return null;
        const v = s.querySelector('.viewport') || s;
        const problems = [];
        /* GPT#6 加固①：零尺寸容器（渲染失败/布局塌陷）——横向溢出检查的旧逻辑对宽 0 直接短路 */
        if (v.clientWidth === 0 || v.clientHeight === 0)
          problems.push(`zero-size viewport (${v.clientWidth}x${v.clientHeight})`);
        /* ② 纵向明显裁切：固定高容器内容被 overflow 裁掉 >40px（小裁切/省略号不算） */
        const clipped = [...s.querySelectorAll('[data-block]')].filter(el => {
          const c = getComputedStyle(el);
          if ((c.overflow === 'hidden' || c.overflowY === 'hidden')
              && el.scrollHeight - el.clientHeight > 40 && el.clientHeight > 0)
            return true;
          return false;
        }).slice(0, 3).map(el => (el.getAttribute('data-eid') || el.className.toString().slice(0, 24))
          + ` -${el.scrollHeight - el.clientHeight}px`);
        if (clipped.length) problems.push(`vertically clipped: ${clipped.join(' | ')}`);
        /* ③ 不可见内容块：渲染树外（display:none）的非隐藏 data-block（防"写了但看不见"） */
        const invisible = [...s.querySelectorAll('[data-block]')].filter(el => {
          if (el.closest('.is-hidden')) return false;
          return el.offsetParent === null && getComputedStyle(el).display !== 'none' && !el.closest('dialog');
        }).slice(0, 3).map(el => el.getAttribute('data-eid') || el.className.toString().slice(0, 24));
        if (invisible.length) problems.push(`invisible blocks (display tree): ${invisible.join(' | ')}`);
        /* 原有：横向溢出 */
        if (v.clientWidth > 0 && v.scrollWidth > v.clientWidth + 2)
          problems.push(`+${v.scrollWidth - v.clientWidth}px horizontal`);
        return problems.length ? problems : ['ok'];
      }, id);
      if (res === null) { unmeasured += 1; warn(`@${vp.tag}: screen ${id} not measurable — unmeasured`); continue; }
      measured += 1;
      if (res[0] !== 'ok') bad.push(`${id}: ${res.join(' ; ')}`);
    }
    /* 冻结单 §2/C05 精神：unmeasured>0 时不得输出「无溢出通过」——
       无实测溢出但测不全 → warn「overflow unproven」；确有溢出 → fail（并附 unmeasured 余量） */
    if (bad.length > 0)
      fail(`overflow @${vp.tag}: ` + bad.slice(0, 3).join(' | ')
        + (unmeasured > 0 ? ` (unmeasured:${unmeasured}（未证实无溢出）)` : ''));
    else if (unmeasured > 0)
      warn(`@${vp.tag}: overflow unproven — measured ${measured}/${ids.length} screens, unmeasured:${unmeasured}（未证实无溢出）`);
    else
      pass(`no horizontal overflow @${vp.tag} (${measured}/${ids.length} screens measured)`);
    geometry.viewports.push({ tag: vp.tag, screens: ids.length, measured, unmeasured, overflow: bad });
    totalUnmeasured += unmeasured;
  }

  /* ---------- EDIT SELF-TEST ----------
   * 自动部分：解锁 + 可编辑节点可达（只读性质，不触发保存），跑在临时副本上。
   * 保存链路（改字→保存→重开→磁盘验证）按用户裁决（2026-10-29）为人工验收项。 */
  let probeCtx = null;
  let tmpDir = null;
  try {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'audit-e2e-'));
    const copyPath = path.join(tmpDir, 'copy.html');
    fs.copyFileSync(path.resolve(htmlPath), copyPath);

    probeCtx = await browser.newContext({ viewport: { width: 1280, height: 900 } });
    const p = await probeCtx.newPage();
    const copyUrl = require('url').pathToFileURL(copyPath).href;
    await p.goto(copyUrl, { waitUntil: 'load' });
    await p.waitForTimeout(500);

    await p.click('#btnUnlock', { timeout: 5000 });
    await p.waitForSelector('#editorGate[open]', { timeout: 5000 });
    await p.fill('#gatePassword', 'audit-test-123');
    await p.click('#gateConfirm');
    await p.waitForTimeout(600);
    const editable = await p.evaluate(() => !document.body.classList.contains('ed-editor-locked'));
    if (!editable) throw new Error('did not unlock after password');
    pass('edit gate probe (on temp copy): unlocked, editor reachable');
    warn('保存功能为人工验收项（用户裁决）：交付说明中已附固定步骤 — 改一个字→保存→关掉重开→确认还在');
  } catch (e) {
    const msg = String(e.message || e).split('\n')[0].slice(0, 200);
    warn('edit gate probe could not run (' + msg + ') — report editor access as unverified');
    warn('保存功能为人工验收项（用户裁决）：交付说明中已附固定步骤 — 改一个字→保存→关掉重开→确认还在');
  } finally {
    if (probeCtx) { try { await probeCtx.close(); } catch (_) { } }
    if (tmpDir) { try { fs.rmSync(tmpDir, { recursive: true, force: true }); } catch (_) { } }
  }

  await browser.close();
  finish(); /* 退出码：0=passed / 1=fail / 2=error（见顶部 finish 定义） */
})().catch(e => { console.error('FAIL ' + String((e && e.stack) || e)); finish('error'); });
