#!/usr/bin/env node
/* verify-editor — editor-chain verifier for the deliverable HTML（T06.1 骨架）.
 * Usage: node verify-editor.mjs --html <deliverable.html> --suite mode|save|style [--out qa/editor-<suite>.json]
 *
 * T06.1 scope（本轮零浏览器，Playwright 不安装不启动）:
 *  - 冻结 C05 报告头（T00-冻结单 §2，一字不改，kind:'audit'）
 *  - 1 个纯 fs 冒烟用例：deliverable 以 class="screen" 声明屏幕（screen 壳件存在）
 *  - --suite 仅做校验与登记；mode/save/style 三套真实用例留待 T06.2（见下方 TODO，
 *    未实现前不产出任何链路结论，不冒充已验证）
 *
 * Exit codes（T00-冻结单 §2 统一语义）: 0 = pass; 1 = 检查失败;
 *   2 = 参数 / 文件不可读 / 环境错误。 */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const CHECKER_VERSION = 'verify-editor/0.1.0-t06.1';

const argv = process.argv.slice(2);
const USAGE = 'usage: node verify-editor.mjs --html <deliverable.html> --suite mode|save|style [--station U4|U5] [--kind audit|verify] [--out qa/editor-<suite>.json]';
const SUITES = ['mode', 'save', 'style'];
const STATIONS = ['U4', 'U5'];
const KINDS = ['audit', 'verify'];
const optVal = name => { const i = argv.indexOf(name); return i >= 0 ? argv[i + 1] : undefined; }; /* 本脚本无位置参数，--html 在 argv[0] 合法 */
const htmlPath = optVal('--html');
const suite = optVal('--suite');
const outArg = optVal('--out');
/* N3 修复：station/kind 参数化——U4 门禁要求 kind='verify' + station='U4' 的合法回执（state_check 校验），
   旧版写死 U5/audit 导致 U4 无产出器。默认 U5/audit 兼容既有调用。 */
const STATION = STATIONS.includes(optVal('--station')) ? optVal('--station') : 'U5';
const KIND = KINDS.includes(optVal('--kind')) ? optVal('--kind') : 'audit';

if (!htmlPath || String(htmlPath).startsWith('--') || !SUITES.includes(suite)) {
  console.error(USAGE);
  process.exit(2);
}

/* ---- 报告状态（先于读取声明，失败路径也能落 error 报告）---- */
const findings = [];
let html = null;
let screenDecl = 0;
let inputSha = null;
/* 种子 :root 静态默认值正本（从 assets/token-keys.json 派生，不手抄：有 default 的键 →
   --sp-<键名> 及其 default 值；正本表一变断言即随，与 verify_namespace 的 --sp-* 派生同构）。
   声明在前——writeReport 的失败路径也引用 coverage.seedTokens，不得晚于首次 writeReport 调用。 */
const ROOT_DIR = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..');
const SEED_TOKEN_DEFAULTS = (() => {
  const regPath = path.join(ROOT_DIR, 'assets', 'token-keys.json');
  let reg;
  try {
    reg = JSON.parse(fs.readFileSync(regPath, 'utf-8'));
  } catch (e) {
    console.error('verify-editor: token-keys.json 读取失败（种子默认值断言无法派生）: ' + regPath + ' — ' + (e.message || e));
    process.exit(2);
  }
  return (reg.keys || [])
    .filter(k => k && typeof k.key === 'string' && k.default != null)
    .map(k => ['--sp-' + k.key, String(k.default)]);
})();
let missingTokens = [];

function sha256File(p) {
  /* 冻结单 §2：摘要 = 文件原始字节 SHA-256，任何一端不得去 BOM/改换行 */
  return crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
}
function pushFinding(ruleId, extra) {
  /* §2 findings schema：{ruleId,file,line,page,eid,featureId,expected,actual,severity} */
  findings.push({ ruleId, file: htmlPath, line: null, page: null, eid: null, featureId: null, expected: null, actual: null, severity: 'error', ...extra });
}
function writeReport(result) {
  const out = outArg || `qa/editor-${suite}.json`;
  const inputs = [{ path: htmlPath, sha256: inputSha }];
  const digestLines = inputs.map(i => Buffer.from(`${i.path}:${i.sha256 ?? 'unreadable'}\n`, 'utf8')).sort(Buffer.compare);
  const inputDigest = crypto.createHash('sha256').update(Buffer.concat(digestLines)).digest('hex');
  const report = {
    kind: KIND,
    reportVersion: 1,
    checkerVersion: CHECKER_VERSION,
    station: STATION,
    phase: null,
    scope: null, /* TODO(T06.2): 解析契约 fence 后填 pageId 列表 */
    inputDigest,
    inputs, /* [{path, sha256(原始字节)}] */
    result, /* 'passed' | 'fail' | 'error' */
    findings,
    coverage: {
      suite,
      checksRun: 2,
      smoke: { name: 'screen-decl', passed: screenDecl > 0, hits: screenDecl },
      seedTokens: {
        name: 'seed-token-defaults',
        passed: findings.every(f => f.ruleId !== 'E-EDITOR-SEED-TOKEN-DEFAULTS'),
        checked: SEED_TOKEN_DEFAULTS.length,
        missing: missingTokens.map(([n]) => n),
      },
      casesPlannedT062: [suite], /* 本轮登记，未执行 */
    },
    generatedAt: new Date().toISOString(),
  };
  try {
    fs.mkdirSync(path.dirname(path.resolve(out)), { recursive: true });
    fs.writeFileSync(path.resolve(out), JSON.stringify(report, null, 2));
    console.error('report: ' + path.resolve(out));
  } catch (e) { console.error('FAIL cannot write report: ' + (e.message || e)); }
}

/* ---- 读入 deliverable（不可读 = 环境错误，exit 2）---- */
try {
  html = fs.readFileSync(htmlPath, 'utf8');
  inputSha = sha256File(htmlPath);
} catch (e) {
  pushFinding('E-ENV-INPUT-UNREADABLE', { expected: 'deliverable readable', actual: String(e.message || e).slice(0, 200) });
  writeReport('error');
  console.error('FAIL cannot read deliverable: ' + htmlPath);
  process.exit(2);
}

/* ---- T06.1 冒烟用例（纯 fs，无浏览器）：屏幕壳件声明存在 ---- */
screenDecl = (html.match(/class="screen"/g) || []).length;
if (screenDecl > 0) {
  pushFinding('PASS-SMOKE-SCREEN-DECL', {
    expected: 'deliverable declares screens via class="screen"',
    actual: `class="screen" x ${screenDecl}`,
    severity: 'pass',
  });
  console.log('  ✓ smoke: class="screen" x ' + screenDecl);
} else {
  pushFinding('E-EDITOR-SMOKE-SCREEN', {
    expected: 'deliverable declares screens via class="screen"',
    actual: 'no class="screen" found',
    severity: 'fail',
  });
  console.log('  ✗ smoke: no class="screen" in deliverable');
}

/* ---- 种子 :root 静态默认值冒烟（纯 fs，对照 assets/token-keys.json 各键 default）----
   交付物内嵌 seed 的 :root；缺一条 = 页面在没有风格包时对应 var() 无静态兜底。
   全量断言（含既有键）：既防缺，也防"已有的值被改"。 */
const esc = s => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
missingTokens = SEED_TOKEN_DEFAULTS.filter(([name, val]) =>
  !new RegExp(esc(name) + '\\s*:\\s*' + esc(val) + '\\s*;').test(html));
if (missingTokens.length === 0) {
  pushFinding('PASS-SMOKE-SEED-TOKEN-DEFAULTS', {
    expected: 'deliverable :root carries every --sp-* static default (token-keys.json)',
    actual: SEED_TOKEN_DEFAULTS.length + ' defaults present',
    severity: 'pass',
  });
  console.log('  ✓ smoke: --sp-* static defaults x ' + SEED_TOKEN_DEFAULTS.length);
} else {
  pushFinding('E-EDITOR-SEED-TOKEN-DEFAULTS', {
    expected: 'deliverable :root carries every --sp-* static default (token-keys.json)',
    actual: 'missing/changed: ' + missingTokens.map(([n, v]) => n + '=' + v).join('; '),
    severity: 'fail',
  });
  console.log('  ✗ smoke: missing/changed --sp-* defaults: ' + missingTokens.map(([n]) => n).join(', '));
}

/* ---- T06.2 真实用例（本轮不实现；未实现前禁止假报通过）----
 * TODO(T06.2): suite=mode  — 编辑模式链路：#btnUnlock 解锁 → editor-locked 解除 → 编辑面板/inspector 可达（需浏览器）
 * TODO(T06.2): suite=save  — 保存链路：改字 → 保存 → 关闭重开 → 磁盘字节校验（需浏览器 + 临时副本；
 *                             人工验收四步按用户裁决 2026-10-29 在交付说明保留，自动化不冒充）
 * TODO(T06.2): suite=style — setStyle 链路：fText/fColor/fBg/fRadius/fPad/fWidth/fAlign/fStyle 内联写入与清除（需浏览器）
 * 上述用例接入后 coverage.checksRun 才允许 >1。 */
console.log(`  ◦ suite "${suite}": real cases are T06.2 (browser) — not run this round`);

const failedCount = findings.filter(f => f.severity === 'fail').length;
writeReport(failedCount > 0 ? 'fail' : 'passed');
console.log(`\nverify-editor[${suite}]: ${failedCount > 0 ? 'FAIL' : 'PASS'} — ${failedCount} failure(s) (smoke only; 3 real suites pending T06.2)`);
process.exit(failedCount > 0 ? 1 : 0);
