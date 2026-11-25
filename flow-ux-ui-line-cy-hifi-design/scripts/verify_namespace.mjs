#!/usr/bin/env node
/* verify_namespace — V05-① 命名空间迁移校验器（四域定稿版）
 * Usage: node scripts/verify_namespace.mjs [--html assets/editor-seed.html]
 * 规则（namespace-spec.md「构建迁移校验」节）:
 *  1. CSS 声明区类选择器必须 ed- 开头或在豁免白名单（组件库类/④域豁免类/协议类）
 *  2. CSS 自定义属性声明必须 --ed- 开头或在变量白名单（页面令牌/--device；--style-* 属③域由规则3断言）
 *  3. STYLE_OWNED_VARS 数组与 --style-* 系零改动断言（皮肤引擎域，对照冻结基线）
 *  4. exit≠0 即 FAIL，逐条报（行号+词）
 * Exit: 0=PASS 1=FAIL 2=用法/环境错误
 */
import { createRequire } from 'module';
const require = createRequire(import.meta.url);
const fs = require('fs');
const path = require('path');

const argv = process.argv.slice(2);
const optVal = n => { const i = argv.indexOf(n); return i >= 0 ? argv[i + 1] : undefined; };
const root = path.resolve(path.dirname(new URL(import.meta.url).pathname.replace(/^\/(\w:)/, '$1')), '..');
const htmlPath = path.resolve(optVal('--html') || path.join(root, 'assets/editor-seed.html'));
if (!fs.existsSync(htmlPath)) { console.error('usage: node verify_namespace.mjs [--html <file>]'); process.exit(2); }

/* ===== 豁免白名单（四域定稿；来源=namespace-spec.md 四域分界表 + 基线 seed CSS 类全集 - S1/S2 改名集） ===== */
// ②页面域·组件库类与页面浮层/自由画布运行时类（fragments/build/design-tokens/chooser/free-editor 五方契约，250 个；2026-11-06 组件库扩全 B/C 档 +55）
const PAGE_CLASSES = new Set(('accent ad ad-main adpage adtop anim anim-back anim-in annotation-pin app appbar ar av avs rate slider tr fl stepper col carousel hsteps b badge bar bars bf bk bl bt btns bv bx ca carousel cal card card-b card-h cards cb cbox ch chip chips chk chks chrome cmt cmts copen col-b col-h col-item collapse crumb crumbs crumbx ct cur cx d dan danger dark dg dirty done dot down e empty end err err-tip et far feed fi filters flash flat flipped flow flw fnode form frow fs full grid gt h1 h2 h3 hb hero horiz hr hs hs-item ht ic imgbox in ipt idxbar idxwrap k kv kn kb l lb ld li list lnk m masonry maskcard menu mi mono n ni nm no notch note np num numkey ok on op ov-bar ov-body ov-mask ov-panel ov-x p pager passrow pf ph pi pill pimgs plain pop post pri proto-ov proto-result proto-sk pv-idx pv-name pv-tip r rb rdo req rd ri result ric ring rings rl row rt rv sb scr-head scr-name scr-note sd search sec sec-h segs sel sel-list selo sep sg shuffling sheet side sk skel sl slider sm soft sp st stat stats blk bubble chat dim dots fab fab-row grip ln mine si tabpane today wg statusbar steps stp sub sv sw sx t ta tabbar tag tags tb2 tbl tbl-foot tbl-wrap tcard tf th ti ti-in tint tiny tm tn tg tr tree tt tx unit up url val w warn who wire-toolbar x').split(' '));
// ④受控块契约域·豁免类：受控块消费的壳类 + 读写状态类（规范④域分界行，遗留项登记 V06）
const RUNTIME_CLASSES = new Set(('topbar tools tabs tb mini fld g2 acts hint inspector dbg palette canvas ' +
  'shownotes has-inspector is-hidden annotation-hover annotating has-annotation-card').split(' '));
// 预览协议域（并入豁免，规范四域分界节末段）
const PROTOCOL_CLASSES = new Set(['device', 'mobile', 'tablet', 'desktop', 'viewport', 'screen', 'free-canvas']);
// ②页面域·页面令牌（:root 基线 18 个）+ --sp-* 形态令牌（从正本表 assets/token-keys.json 派生，
// 不手抄：emits 里以 --sp- 开头的变量 + 有 default 的键对应的 --sp-<键名>）+ 协议变量
const BASE_PAGE_VARS = ('--bg --surface --line --line-2 --text --muted --muted-2 --soft --accent --accent-soft ' +
  '--ok --ok-soft --warn --warn-soft --danger --danger-soft --radius --shadow').split(' ');
const tokenKeysPath = path.join(root, 'assets', 'token-keys.json');
let SP_PAGE_VARS = [];
try {
  /* 兼容带 BOM 的 token-keys.json（Python 侧以 utf-8-sig 读取，JS 侧去 BOM 对齐） */
  const tokenKeys = JSON.parse(fs.readFileSync(tokenKeysPath, 'utf-8').replace(/^\uFEFF/, ''));
  const sp = new Set();
  for (const k of tokenKeys.keys || []) {
    if (!k || typeof k.key !== 'string') continue;
    for (const e of k.emits || []) {
      if (typeof e === 'string' && e.startsWith('--sp-')) sp.add(e);
    }
    if (k.default != null) sp.add('--sp-' + k.key);
  }
  SP_PAGE_VARS = [...sp];
} catch (e) {
  console.error('verify_namespace: token-keys.json 读取失败（--sp-* 白名单无法派生）: ' + tokenKeysPath);
  process.exit(2);
}
const PAGE_VARS = new Set([...BASE_PAGE_VARS, ...SP_PAGE_VARS]);
const PROTOCOL_VARS = new Set(['--device']);
/* 扩展参数通道（token-keys.json）：运行时按 keyPattern 生成 --sp-<键名>，只出现在运行时写入与
 * 页面/组件引用里；若被扫文本的 <style> 块声明了这类变量，凡符合正本 keyPattern 的一并放行。 */
const SP_EXTENSION_RE = /^--sp-[a-z][a-z0-9]*(-[a-z0-9]+)*$/;

const CLASS_WHITELIST = new Set([...PAGE_CLASSES, ...RUNTIME_CLASSES, ...PROTOCOL_CLASSES]);
const VAR_WHITELIST = new Set([...PAGE_VARS, ...PROTOCOL_VARS]);

const src = fs.readFileSync(htmlPath, 'utf-8');
const violations = [];

/* ---- 逐 <style> 块扫描（行号=全文行号） ---- */
const styleRe = /<style>([\s\S]*?)<\/style>/g;
let sm;
while ((sm = styleRe.exec(src))) {
  const cssRaw = sm[1];
  const css = cssRaw.replace(/\/\*[\s\S]*?\*\//g, '');
  const blockStartLine = src.slice(0, sm.index + 7).split(/\r?\n/).length; // <style> 结束所在行

  // 规则1：类选择器 ed- 前缀或白名单
  const clsRe = /\.([a-zA-Z][a-zA-Z0-9_-]*)/g;
  let cm;
  while ((cm = clsRe.exec(css))) {
    const name = cm[1];
    if (name.startsWith('ed-') || CLASS_WHITELIST.has(name)) continue;
    const line = blockStartLine + css.slice(0, cm.index).split('\n').length - 1;
    violations.push(`L${line} class .${name} 不带 ed- 前缀且不在四域豁免白名单`);
  }

  // 规则2：CSS 自定义属性声明 --ed- 前缀或白名单（--style-* 由规则3 断言零改动；
  // --sp-* 见正本表派生名单，扩展参数形态按 keyPattern 放行）
  const declRe = /(--[a-z][a-z0-9-]*)\s*:/g;
  let dm;
  while ((dm = declRe.exec(css))) {
    const v = dm[1];
    if (v.startsWith('--ed-') || v.startsWith('--style-') || VAR_WHITELIST.has(v) || SP_EXTENSION_RE.test(v)) continue;
    const line = blockStartLine + css.slice(0, dm.index).split('\n').length - 1;
    violations.push(`L${line} 变量声明 ${v} 不带 --ed- 前缀且不在页面令牌白名单`);
  }
}

/* ---- 规则3：皮肤引擎域零改动断言（冻结基线） ---- */
const sov = src.match(/var STYLE_OWNED_VARS\s*=\s*\[[^\]]*\]/);
const styleVars = src.match(/--style-[a-z-]*/g) || [];
const BASELINE_SOV = '["--accent", "--accent-soft", "--style-bg", "--style-surface", "--style-text", "--style-muted", "--style-line", "--style-soft", "--style-dark-bg", "--style-dark-surface", "--style-dark-text", "--style-dark-muted", "--style-dark-line"]';
if (!sov) violations.push('STYLE_OWNED_VARS 数组缺失（皮肤域被误伤）');
else {
  const cur = sov[0].slice(sov[0].indexOf('[')).replace(/\s+/g, '');
  if (cur !== BASELINE_SOV.replace(/\s+/g, '')) violations.push('STYLE_OWNED_VARS 与冻结基线不一致（③皮肤域必须零改动）');
}
/* 零改动=不新增/不改名：seed 里引用的 --style-* 必须都在 STYLE_OWNED_VARS 名单内（消费次数不封顶——
   组件 CSS 合法消费皮肤变量随扩全增长，2026-11-06 由次数断言改为集合断言）。
   --style-primary-text 例外登记：chooser L1 写在 roots 的派生变量（按当前配色推算的按钮文字色），
   非快照名单成员，规则表与组件 CSS 合法消费。 */
const OWNED_STYLE_VARS = JSON.parse(BASELINE_SOV).filter(v => v.startsWith('--style-')).concat(['--style-primary-text']);
const unknownStyle = [...new Set(styleVars)].filter(v => !OWNED_STYLE_VARS.includes(v));
if (unknownStyle.length) violations.push(`--style-* 引用了名单外变量：${unknownStyle.join(' ')}（③皮肤域零改动）`);

if (violations.length) {
  console.error(`verify_namespace: FAIL (${violations.length} violation(s))`);
  violations.forEach(v => console.error('  ' + v));
  process.exit(1);
}
console.log('verify_namespace: PASS — 类选择器/变量声明全部符合 ed- 命名空间或四域白名单；皮肤域零改动');
process.exit(0);
