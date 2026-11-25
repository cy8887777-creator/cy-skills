#!/usr/bin/env node
/* screenshot — capture every screen of the deliverable to qa/shots/ (U2 self-evidence + U5 visual walkthrough input)
 * Usage: node screenshot.mjs <deliverable.html> [--out qa/shots] [--viewport mobile|desktop|both]
 * Switches pages via the real nav tab (same path as verify-interactions), screenshots each page.
 * Exit = number of screens NOT captured. */
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
  if (!pw) throw new Error('playwright not resolvable');
  return pw.chromium;
}

const argv = process.argv.slice(2);
const htmlPath = argv[0];
if (!htmlPath || !fs.existsSync(htmlPath)) {
  console.error('usage: node screenshot.mjs <deliverable.html> [--out qa/shots] [--viewport mobile|desktop|both]');
  process.exit(2);
}
const outDir = (() => {
  const i = argv.indexOf('--out');
  if (i > 0 && argv[i + 1]) return argv[i + 1];
  if (i > 0) { console.error('FAIL --out requires a value'); process.exit(2); }
  return 'qa/shots';
})();
const vpArg = (() => {
  const i = argv.indexOf('--viewport');
  if (i > 0) {
    const v = argv[i + 1];
    if (!v || !['mobile', 'desktop', 'both'].includes(v)) {
      console.error('FAIL --viewport must be mobile|desktop|both, got: ' + v);
      process.exit(2);
    }
    return v;
  }
  return 'both';
})();
const VIEWPORTS = vpArg === 'both' ? [{ tag: 'mobile', width: 390, height: 844 }, { tag: 'desktop', width: 1280, height: 900 }]
  : vpArg === 'desktop' ? [{ tag: 'desktop', width: 1280, height: 900 }]
  : [{ tag: 'mobile', width: 390, height: 844 }];

(async () => {
  let chromium;
  try { chromium = loadChromium(); }
  catch (e) { console.error('FAIL ' + e.message); process.exit(2); }

  const url = require('url').pathToFileURL(path.resolve(htmlPath)).href;
  fs.mkdirSync(path.resolve(outDir), { recursive: true });
  const browser = await chromium.launch();
  const manifest = [];
  const missedList = [];
  let missed = 0;

  for (const vp of VIEWPORTS) {
    const context = await browser.newContext({ viewport: { width: vp.width, height: vp.height } });
    const page = await context.newPage();
    await page.goto(url, { waitUntil: 'load' });
    await page.waitForTimeout(600);
    const screens = await page.evaluate(() =>
      [...document.querySelectorAll('[data-screen]')].map(s => s.getAttribute('data-screen')));
    if (!screens.length) {
      console.error('FAIL no [data-screen] elements found — is this a deliverable of this skill?');
      await context.close(); await browser.close();
      process.exit(2);
    }
    for (const id of screens) {
      const tab = page.locator(`#tabs .ed-tab[data-go="${id}"]`).first();
      let switched = true;
      try { await tab.click({ timeout: 4000 }); }
      catch (_) {
        switched = await page.evaluate(sid => {
          if (typeof goTo === 'function') { goTo(sid); return true; }
          const t = document.querySelector(`[data-screen="${sid}"]`);
          if (t) { t.scrollIntoView({ behavior: 'instant', block: 'start' }); return true; }
          return false;
        }, id);
      }
      await page.waitForTimeout(400);
      /* verify the screen is actually visible — preview hides non-active screens,
       * so an un-switched fallback would photograph the wrong page as fake evidence */
      const visible = await page.evaluate(sid => {
        const s = document.querySelector(`[data-screen="${sid}"]`);
        return s && getComputedStyle(s).display !== 'none';
      }, id);
      if (!switched || !visible) {
        missed += 1;
        missedList.push({ screen: id, viewport: vp.tag, reason: 'screen not visible after switch attempt' });
        console.log('  ✗ ' + id + '@' + vp.tag + ' — not visible after switch attempt');
        continue;
      }
      const file = `${id}-${vp.tag}.png`;
      try {
        await page.screenshot({ path: path.join(path.resolve(outDir), file) });
        manifest.push({ screen: id, viewport: vp.tag, file });
        console.log('  ✓ ' + file);
      } catch (e) {
        missed += 1;
        missedList.push({ screen: id, viewport: vp.tag, reason: String(e).split('\n')[0] });
        console.log('  ✗ ' + id + '@' + vp.tag + ' — ' + String(e).split('\n')[0]);
      }
    }
    await context.close();
  }
  await browser.close();
  fs.writeFileSync(path.join(path.resolve(outDir), 'shots-manifest.json'),
    JSON.stringify({ deliverable: htmlPath, captured: manifest.length, missed,
                     missed_detail: missedList, generated_at: new Date().toISOString() }, null, 2));
  console.log(`\nscreenshots: ${manifest.length} captured, ${missed} missed → ${path.resolve(outDir)}`);
  process.exit(missed);
})();
