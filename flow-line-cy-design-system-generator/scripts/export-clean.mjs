#!/usr/bin/env node
// export-clean.mjs —— 决策链 → 纯净版设计系统（system-rules.md + design-system.html）
// 用法: node export-clean.mjs <chain.json> <输出目录>
// 纯净规则：零决策痕迹、零来源标注；章节 id/顺序/章名以 references/chapters.md 为唯一权威（14 章，与工作台预览一致）。
// 形态基准 = data/case/design-system.case.html：侧栏导航 + hero + 章节框架（ch-num/en/ch-intro）+ block 词汇表
// （spec-label/plain/swatches 点击复制色板/type-row 字阶行/comp-stage 组件舞台）——模板内置全套皮肤与骨架样式；
// overview 各章 HTML 必须使用这些原生类名（成文标准见 playbook 第九步「成文前必读」）。
import fs from 'node:fs';
import path from 'node:path';

const [, , chainFile, outDirArg] = process.argv;
if (!chainFile || !outDirArg) { console.error('用法: node export-clean.mjs <chain.json> <输出目录>'); process.exit(1); }
const chain = JSON.parse(fs.readFileSync(chainFile, 'utf8').replace(/^\uFEFF/, ''));
const outDir = path.resolve(outDirArg);
fs.mkdirSync(outDir, { recursive: true });

const CHAPTERS = [
  ['values', '设计价值观', 'VALUES', '为什么是这套风格——风格定义层的落锤与血统'],
  ['layout', '布局', 'LAYOUT', '页面的骨架：区域划分、栅格与导航形态'],
  ['density', '密度与多端', 'PLATFORMS', '基准端向、断点与信息密度基准'],
  ['rules', '设计要求', 'REQUIREMENTS', '通用设计要求 + 本项目实测沉淀'],
  ['color', '颜色', 'COLOR', '主色只有一个（靛蓝）；暖纸底 × 冷靛蓝的撞色策略；写样式只引用语义槽位'],
  ['type', '字体', 'TYPOGRAPHY', '衬线标题 × 无衬线正文 × 等宽标注的三轨体系'],
  ['spacing', '间距', 'SPACING', '4pt 网格：所有间距取 4 的倍数，禁魔法数值'],
  ['radius', '圆角', 'RADIUS', '四档圆角：标签 6 / 控件 8 / 卡片 10 / 徽标圆'],
  ['shadow', '阴影', 'SHADOW', '阴影全部带色相：柔影 / 彩色柔影 / focus 光环三档'],
  ['motion', '动效', 'MOTION', '200-300ms 的克制纪律：动效只服务于空间叙事'],
  ['component', '组件', 'COMPONENTS', '静玻璃五族：按钮 / 标签 / 输入 / 卡片 / 导航——玻璃纪律优先'],
  ['icon', '图标', 'ICONS', 'Feather 线性 2px：极简线性，与文档编辑风同源'],
  ['imagery', '图像与插画', 'IMAGERY', '无图策略：工作台为纯工具界面，氛围由 CSS 渐变承担'],
  ['bans', '设计禁令', 'PROHIBITIONS', '产出前逐条自查：概念禁令 / 具体禁令 / 无障碍红线'],
];

const ov = chain.overview || {};
const textOf = v => String(v || '').replace(/<[^>]*>/g, ' ').trim();
// 锁定判定：overview 有实质内容（剥掉 HTML 标签后仍有正文；占位符/空壳不算）
const missing = CHAPTERS.filter(([id]) => !ov[id] || textOf(ov[id]).length < 2);
if (missing.length) {
  console.error('未定稿章节: ' + missing.map(m => m[1]).join('、'));
  console.error('全部章节锁定后才能导出纯净版。');
  process.exit(2);
}

const date = new Date(Date.now() - new Date().getTimezoneOffset() * 60000).toISOString().slice(0, 10); // 本地日期

// ---------- system-rules.md ----------
let md = `# ${chain.project || '项目'}设计系统\n\n> v${chain.version || 1} · ${date} · 由原型画像与共创决策生成\n`;
for (const [id, zh, en] of CHAPTERS) {
  md += `\n## ${zh} ${en}\n\n${ov[id].trim()}\n`;
}
fs.writeFileSync(path.join(outDir, 'system-rules.md'), md);

// ---------- design-system.html（case 形态） ----------
const navLinks = CHAPTERS.map(([id, zh, en], i) => `<a href="#s${i + 1}"><span class="no">${String(i + 1).padStart(2, '0')}</span>${zh}<span class="en">${en}</span></a>`).join('');
const sections = CHAPTERS.map(([id, zh, en, intro], i) => `<section class="chapter" id="s${i + 1}"><div class="ch-head"><span class="ch-num">${String(i + 1).padStart(2, '0')}</span><div><h2>${zh}<span class="en">${en}</span></h2><p class="ch-intro">${intro}</p></div></div><div class="ch-body">${ov[id]}</div></section>`).join('\n');

const stepChosen = id => { const s = (chain.steps || []).find(x => x.id === id); return s && s.chosen ? String(s.chosen).replace(/（[^）]*）/g, '').replace(/·.*$/, '').trim().slice(0, 18) : '—'; };
const styleName = stepChosen('concept');
const baseName = stepChosen('compstyle') === '—' ? '静玻璃' : stepChosen('compstyle');

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${chain.project || '设计系统'} · 设计系统</title>
<style>
  /* ============ 文档皮肤（按项目气质重渲染：文档编辑风 × 靛蓝纸底 × 衬线标题） ============ */
  :root {
    --paper: #FAFAF7; --ink: #23283B; --ink-soft: #7C86A0; --line: #E2E6F2;
    --accent: #4C6FFF; --accent-deep: #3550C4; --accent-100: #EEF1FF; --accent-300: #8B9BFF;
    --ok: #3D8B6E; --ok-bg: #E6F4ED; --warn: #C77D1D; --warn-bg: #FDF3E5; --danger: #C75450; --danger-bg: #FBEAEA;
    --card: #ffffff;
    --skin-sidebar-bg: #23283B; --skin-sidebar-ink: #DEE5EC;
    --font-display: "Noto Serif SC", "Songti SC", serif;
    --sans: -apple-system, "PingFang SC", "Microsoft YaHei", sans-serif;
    --mono: "JetBrains Mono", "Cascadia Code", Consolas, "Microsoft YaHei", monospace;
    --space-1: 4px; --space-2: 8px; --space-3: 12px; --space-4: 16px; --space-6: 24px; --space-8: 32px; --space-12: 48px;
    --radius-sm: 6px; --radius-md: 8px; --radius-lg: 10px; --radius-full: 9999px;
    --shadow-md: 0 4px 16px rgba(35,40,59,.08);
    --font-size-body: 14px;
  }
  * { box-sizing: border-box; }
  html { scroll-behavior: smooth; }
  body { margin: 0; background: var(--paper); color: var(--ink); font-family: var(--sans); font-size: var(--font-size-body); line-height: 1.75; }
  /* 背景格纹（case 同款）：给玻璃 backdrop-filter 提供可模糊的纹理对象 */
  body::before { content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 0;
    background-image: linear-gradient(rgba(76,111,255,.045) 1px, transparent 1px), linear-gradient(90deg, rgba(76,111,255,.045) 1px, transparent 1px);
    background-size: 24px 24px; }

  .sidebar { position: fixed; top: 0; left: 0; bottom: 0; width: 256px; z-index: 10; background: var(--skin-sidebar-bg); color: var(--skin-sidebar-ink); display: flex; flex-direction: column; padding: var(--space-6) 0 var(--space-4); }
  .brand { display: flex; align-items: center; gap: var(--space-3); padding: 0 var(--space-6); }
  .brand-mark { width: 34px; height: 34px; flex: none; border-radius: var(--radius-sm); background: var(--accent); color: #fff; font-family: var(--mono); font-size: 13px; font-weight: 700; display: grid; place-items: center; letter-spacing: .5px; }
  .brand-name { font-family: var(--font-display); font-size: 16px; font-weight: 700; color: #fff; line-height: 1.3; }
  .brand-ver { font-family: var(--mono); font-size: 11px; color: #8b8e96; }
  .nav { margin-top: var(--space-6); flex: 1; overflow-y: auto; }
  .nav a { display: flex; align-items: baseline; gap: var(--space-2); padding: 6px var(--space-6); color: #9a9da5; text-decoration: none; font-size: 13px; border-left: 2px solid transparent; transition: color .15s, background .15s; }
  .nav a:hover { color: #fff; background: rgba(255,255,255,.04); }
  .nav a.on { color: #fff; border-left-color: var(--accent); background: rgba(255,255,255,.05); }
  .nav .no { font-family: var(--mono); font-size: 11px; color: #63666e; width: 20px; flex: none; }
  .nav a.on .no { color: var(--accent); }
  .nav .en { font-size: 10px; color: #55585f; margin-left: auto; letter-spacing: .04em; }
  .sidebar-meta { padding: var(--space-4) var(--space-6) 0; border-top: 1px solid rgba(255,255,255,.08); font-family: var(--mono); font-size: 10.5px; line-height: 1.9; color: #63666e; }
  .sidebar-meta b { color: #9a9da5; font-weight: 500; }

  main { margin-left: 256px; position: relative; z-index: 1; max-width: 1560px; padding: var(--space-12); }
  section.chapter { padding-top: var(--space-8); margin-bottom: var(--space-12); scroll-margin-top: var(--space-8); }

  .hero { padding: var(--space-6) 0 var(--space-10); animation: rise .6s ease-out both; }
  @keyframes rise { from { opacity: 0; transform: translateY(14px); } to { opacity: 1; transform: none; } }
  .hero-spec { display: flex; align-items: center; gap: var(--space-3); font-family: var(--mono); font-size: 11px; letter-spacing: .12em; color: var(--ink-soft); }
  .hero-spec .tag { background: var(--ink); color: var(--paper); padding: 2px 10px; border-radius: var(--radius-full); letter-spacing: .1em; }
  .hero h1 { font-family: var(--font-display); font-size: 46px; line-height: 1.25; font-weight: 700; margin: var(--space-4) 0 var(--space-2); }
  .hero .h1-en { font-family: var(--mono); font-size: 14px; color: var(--ink-soft); letter-spacing: .08em; }
  .hero p.lead { max-width: 640px; color: var(--ink-soft); margin-top: var(--space-4); }
  .hero-meta { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1px; background: var(--line); border: 1px solid var(--line); border-radius: var(--radius-md); overflow: hidden; margin-top: var(--space-8); font-size: 13px; }
  .hero-meta > div { background: var(--card); padding: var(--space-3) var(--space-4); }
  .hero-meta .k { font-family: var(--mono); font-size: 10px; letter-spacing: .1em; color: var(--ink-soft); display: block; }
  .hero-meta .v { font-weight: 600; margin-top: 2px; }

  .ch-head { display: flex; gap: var(--space-6); align-items: flex-start; border-top: 2px solid var(--ink); padding-top: var(--space-6); }
  .ch-num { font-family: var(--font-display); font-size: 64px; font-weight: 700; line-height: 1; color: transparent; -webkit-text-stroke: 1.5px var(--line); flex: none; }
  .ch-head h2 { margin: 0; font-family: var(--font-display); font-size: 30px; font-weight: 700; line-height: 1.3; }
  .ch-head .en { font-family: var(--mono); font-size: 12px; color: var(--ink-soft); letter-spacing: .14em; display: block; margin-top: 4px; }
  .ch-intro { color: var(--ink-soft); margin: var(--space-2) 0 0; max-width: 600px; font-size: 15px; }

  .block { margin-top: var(--space-8); }
  .spec-label { font-family: var(--mono); font-size: 10.5px; letter-spacing: .16em; color: var(--accent); display: flex; align-items: center; gap: var(--space-2); margin-bottom: var(--space-4); }
  .spec-label::after { content: ""; flex: 1; height: 1px; background: var(--line); }
  .block h3 { font-size: 18px; margin: var(--space-6) 0 var(--space-3); }
  .block p { margin: 0 0 var(--space-3); }
  .block p.note { font-size: 13.5px; color: var(--ink-soft); }
  code { font-family: var(--mono); font-size: .86em; background: var(--accent-100); padding: 1px 6px; border-radius: 6px; color: var(--accent-deep); }
  ul.plain { margin: 0; padding-left: 1.3em; }
  ul.plain li { margin-bottom: 6px; }
  ul.plain b { font-weight: 600; }

  .swatches { display: grid; grid-template-columns: repeat(auto-fill, minmax(118px, 1fr)); gap: var(--space-3); }
  .swatch { background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-md); padding: 8px; cursor: pointer; transition: transform .15s, box-shadow .15s; text-align: left; }
  .swatch:hover { transform: translateY(-2px); box-shadow: var(--shadow-md); }
  .swatch .chip { display: block; height: 64px; border-radius: 6px; border: 1px solid rgba(28,29,33,.10); }
  .swatch .nm { font-family: var(--mono); font-size: 10.5px; margin-top: 8px; display: block; }
  .swatch .hx { font-family: var(--mono); font-size: 10px; color: var(--ink-soft); display: block; }
  .sw-group { font-family: var(--mono); font-size: 11px; letter-spacing: .12em; color: var(--ink-soft); margin: var(--space-6) 0 var(--space-2); }
  .sw-group b { color: var(--ink); }
  .role-badge { display: inline-block; font-family: var(--mono); font-size: 9.5px; background: var(--skin-sidebar-bg); color: var(--skin-sidebar-ink); border-radius: var(--radius-full); padding: 1px 8px; margin-left: 6px; vertical-align: 1px; }

  .type-row { display: flex; align-items: baseline; gap: var(--space-4); padding: var(--space-3) 0; border-bottom: 1px dashed var(--line); }
  .type-row .meta { font-family: var(--mono); font-size: 10.5px; color: var(--ink-soft); width: 230px; flex: none; line-height: 1.7; }
  .type-row .meta b { color: var(--ink); font-weight: 600; }

  .space-ruler { display: flex; flex-direction: column; gap: var(--space-3); }
  .space-row { display: flex; align-items: center; gap: var(--space-4); font-family: var(--mono); font-size: 11px; color: var(--ink-soft); }
  .space-row .lbl { width: 220px; flex: none; }

  .radius-box { width: 108px; height: 84px; background: var(--card); border: 1.5px solid var(--line); display: grid; place-items: center; font-family: var(--mono); font-size: 11px; color: var(--ink-soft); text-align: center; }
  .shadow-card { width: 150px; height: 92px; background: var(--card); border-radius: var(--radius-lg); display: grid; place-items: center; font-family: var(--mono); font-size: 11px; color: var(--ink-soft); text-align: center; }

  .comp-stage { background: linear-gradient(135deg, #EEF1FF 0%, #EAF4EF 55%, #FDF3E5 100%); border: 1px solid var(--line); border-radius: var(--radius-md); padding: var(--space-6); display: flex; flex-wrap: wrap; gap: var(--space-4); align-items: center; }
  .comp-stage + .comp-stage { margin-top: var(--space-3); }
  .stage-lbl { width: 100%; font-family: var(--mono); font-size: 10.5px; letter-spacing: .1em; color: var(--ink-soft); margin-top: var(--space-2); }
  .btn { font-size: 14px; line-height: 20px; padding: 7px 18px; border-radius: var(--radius-md); border: 1px solid transparent; cursor: pointer; display: inline-block; margin: 0 8px 8px 0; }
  .btn-primary { background: rgba(76,111,255,.88); color: #fff; border-color: rgba(255,255,255,.38); box-shadow: 0 4px 12px rgba(76,111,255,.35); }
  .btn-default { background: rgba(255,255,255,.7); border-color: var(--accent); color: var(--accent); }
  .btn-text { background: transparent; color: var(--accent); }

  .tagchip { display: inline-block; font-size: 12px; padding: 2px 10px; border-radius: var(--radius-full); background: var(--accent-100); color: var(--accent-deep); }
  .tagchip.ok { background: var(--ok-bg); color: var(--ok); }
  .tagchip.warn { background: var(--warn-bg); color: var(--warn); }
  .tagchip.err { background: var(--danger-bg); color: var(--danger); }
  .icon-cell { display: inline-flex; flex-direction: column; align-items: center; gap: 4px; width: 60px; padding: 10px 4px; background: var(--card); border: 1px solid var(--line); border-radius: var(--radius-md); color: var(--accent); margin: 0 10px 10px 0; }
  .icon-cell s { text-decoration: none; font-family: var(--mono); font-size: 9.5px; color: var(--ink-soft); }
</style>
</head>
<body>

<aside class="sidebar">
  <div class="brand">
    <div class="brand-mark">DS</div>
    <div>
      <div class="brand-name">${chain.project || '设计系统'}</div>
      <div class="brand-ver">v${chain.version || 1} · SPEC</div>
    </div>
  </div>
  <nav class="nav">${navLinks}</nav>
  <div class="sidebar-meta"><b>生成</b> 原型画像 × 九段共创<br><b>定案</b> 用户逐项拍板<br><b>导出</b> ${date}</div>
</aside>

<main>
  <div class="hero">
    <div class="hero-spec"><span class="tag">SPEC SHEET</span><span>设计系统规范 · 共创生成产物</span></div>
    <h1>${chain.project || '设计系统'}</h1>
    <div class="h1-en">DESIGN SYSTEM · SPEC</div>
    <p class="lead">由原型画像与九段人机共创逐项生成——风格定义、令牌、组件、图标均经用户单选拍板，全部锁值有血统可溯。</p>
    <div class="hero-meta">
      <div><span class="k">VERSION</span><span class="v">v${chain.version || 1}</span></div>
      <div><span class="k">PLATFORM</span><span class="v">PC 1440 · 单端</span></div>
      <div><span class="k">STYLE</span><span class="v">${styleName}</span></div>
      <div><span class="k">BASE</span><span class="v">${baseName}</span></div>
    </div>
  </div>
  ${sections}
  <footer style="margin-top:var(--space-12);border-top:1px solid var(--line);padding-top:var(--space-4);color:var(--ink-soft);font-family:var(--mono);font-size:11px;line-height:1.9">v${chain.version || 1} · ${date} · 双产物体系：本页（人看 spec）+ system-rules.md（AI 读）· 由原型画像与九段人机共创生成，全部锁值经用户拍板</footer>
</main>

<script>
function copyHex(hex) {
  try { navigator.clipboard.writeText(hex); flash(hex); return; } catch (e) {}
  var i = document.createElement('input'); i.value = hex; document.body.appendChild(i); i.select();
  try { document.execCommand('copy'); } catch (e) {}
  document.body.removeChild(i); flash(hex);
}
function flash(hex) {
  var t = document.createElement('div'); t.textContent = '已复制 ' + hex;
  t.style.cssText = 'position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#23283B;color:#fff;padding:8px 18px;border-radius:999px;font-size:13px;z-index:99';
  document.body.appendChild(t); setTimeout(function(){ t.remove(); }, 1400);
}
document.querySelectorAll('.swatch').forEach(function (b) { b.addEventListener('click', function () { copyHex(b.dataset.hex); }); });
function copyCss(btn) {
  var root = btn.closest('.st-cell-root'); if (!root) return;
  var el = root.querySelector('.css-src > *'); if (!el) return;
  copyHex(el.getAttribute('style') || '');
}
document.querySelectorAll('.css-copy').forEach(function (b) { b.addEventListener('click', function () { copyCss(b); }); });
var secs = Array.prototype.slice.call(document.querySelectorAll('section.chapter'));
var links = Array.prototype.slice.call(document.querySelectorAll('.nav a'));
window.addEventListener('scroll', function () {
  var cur = 0;
  secs.forEach(function (s, i) { if (s.getBoundingClientRect().top < 120) cur = i; });
  links.forEach(function (l, i) { l.classList.toggle('on', i === cur); });
});
</script>
</body>
</html>`;
fs.writeFileSync(path.join(outDir, 'design-system.html'), html);

// ---------- 品牌污染扫描（复写方法论 self-check · extract 技能同款） ----------
// case 模板是"带答案的底稿"——复写漏网 = 案例品牌值残留。非零命中即 FAIL。
const POLLUTION = ['#2196F3', '#0D96FB', '#067AFA', '#90CAF9', '跑腿', '示例设计系统', '2026-10-14', 'v2.0.0', 'blue-500', 'blue-600', 'blue-700', 'gen_html', 'apply_skin'];
const hits = POLLUTION.filter(k => html.includes(k));
if (hits.length) {
  console.error('[FAIL] 品牌污染残留（案例值复写漏网）: ' + hits.join(' · '));
  process.exit(3);
}
console.log('[OK] 品牌污染扫描: 零残留');

console.log('纯净版已导出:');
console.log('  ' + path.join(outDir, 'system-rules.md'));
console.log('  ' + path.join(outDir, 'design-system.html'));
