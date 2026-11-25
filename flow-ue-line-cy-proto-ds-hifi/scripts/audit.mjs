#!/usr/bin/env node
// audit.mjs —— 代码审核终审（归零制）
// 用法: node audit.mjs <原型根> <dump目录> <产物根> <基准宽> <倍数...>
// 例:   node audit.mjs ./原型 ./产物/.gen/dumps ./产物 375 375 750
//       （倍数集含基准宽本身；每个倍数对应产物根/<倍数>\ 目录）
// 断言: 覆盖率｜.stage 容器与宽度｜字体路径深度｜素材本地引用（全量 matchAll）｜title｜内容溯源｜倍率数值
import fs from 'node:fs';
import path from 'node:path';

const a = process.argv.slice(2);
const exIdx = a.indexOf('--exclude');
let excludeExtra = exIdx !== -1 ? a[exIdx + 1].split(',').filter(Boolean) : [];
if (exIdx !== -1) a.splice(exIdx, 2);
const [PROTO, DUMPS, ROOT, baseStr, ...restW] = a;
const BASE = parseInt(baseStr, 10);
const widths = [BASE, ...restW.map(Number).filter(Number.isFinite)];
const problems = [];

if (!PROTO || !DUMPS || !ROOT || !Number.isFinite(BASE)) {
  console.error('用法: node audit.mjs <原型根> <dump目录> <产物根> <基准宽> <倍数...>');
  process.exit(1);
}
if (!fs.existsSync(PROTO)) problems.push(`原型根不存在: ${PROTO}`);
if (!fs.existsSync(DUMPS)) problems.push(`dump 目录不存在（先跑 content-dump；audit 按此路径读取内容清单）: ${DUMPS}`);
if (!fs.existsSync(ROOT)) problems.push(`产物根不存在: ${ROOT}`);
if (problems.length) { console.log('问题数: ' + problems.length); problems.forEach(p => console.log('  ✗ ' + p)); process.exit(2); }

const EXCL = new Set(['assets', 'fonts', 'node_modules', '.gen', ...excludeExtra]);
const walkRels = (dir, rel, out) => {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (EXCL.has(e.name) || e.name.startsWith('_') || e.name.startsWith('.') || /^\d+$/.test(e.name)) continue;
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walkRels(f, r, out);
    else if (e.name.endsWith('.html')) out.push(r);
  }
};

// 原型树 rel 基准
const proto = [];
walkRels(PROTO, '', proto);

// dump 内容清单
const dumps = {};
let dumpCount = 0;
(function walkD(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walkD(f, r);
    else if (e.name.endsWith('.txt')) { dumps[r.replace(/\.txt$/, '.html')] = fs.readFileSync(f, 'utf8'); dumpCount++; }
  }
})(DUMPS, '');
if (dumpCount === 0) problems.push(`dump 目录为空或不存在（内容溯源未执行）: ${DUMPS} —— 先跑 content-dump 生成内容清单`);
// dump 清单校验和（防清单被改动）：content-dump 生成 dumps-manifest.json
const manifestPath = path.join(DUMPS, 'dumps-manifest.json');
if (fs.existsSync(manifestPath)) {
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  for (const [relKey, meta] of Object.entries(manifest)) {
    const f = path.join(DUMPS, relKey);
    if (!fs.existsSync(f)) { problems.push(`清单被改动(缺失): dumps/${relKey}`); continue; }
    const bytes = fs.statSync(f).size;
    const lines = fs.readFileSync(f, 'utf8').split('\n').length;
    if (bytes !== meta.bytes || lines !== meta.lines) problems.push(`清单被改动(与盘点不符): dumps/${relKey} —— 重跑 content-dump 恢复`);
  }
} else {
  console.log('提示: dumps-manifest.json 不存在（旧版盘点产物），清单防改动校验跳过——重跑 content-dump 可启用');
}

// 各倍数树：标准 rel → 文件。目标宽目录允许两种命名（同名，或 basename 带 -<宽> 后缀；同名优先，两者并存报歧义）
const trees = {};
let checked = 0;
for (const w of widths) {
  trees[w] = new Map();
  const dir = path.join(ROOT, String(w));
  if (!fs.existsSync(dir)) { problems.push(`缺目录: 产物根/${w}\\`); continue; }
  (function walkT(dir, rel) {
    for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
      if (EXCL.has(e.name) || e.name.startsWith('_') || e.name.startsWith('.') || /^\d+$/.test(e.name)) continue;
      const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
      if (e.isDirectory()) walkT(f, r);
      else if (e.name.endsWith('.html')) {
        const isBase = w === BASE;
        const key = isBase ? r : (r.endsWith('-' + w + '.html') ? r.replace('-' + w + '.html', '.html') : r);
        if (trees[w].has(key)) problems.push(`命名歧义: ${w}\\${r} 与已登记页重复`);
        trees[w].set(key, f);
      }
    }
  })(dir, '');
}

// 断言 1：覆盖率（原型每页 × 每倍数 = 产物存在；反向查多余页）
for (const r of proto) for (const w of widths) if (!trees[w].has(r)) problems.push(`缺${w}: ${w}/${r}`);
for (const w of widths) for (const r of trees[w].keys()) if (!proto.includes(r)) problems.push(`多余(不在原型): ${w}/${r}`);

// 逐页断言
const stripTags = c => c.replace(/<[^>]+>/g, ' ').replace(/\s+/g, '');
const extractFontSizes = c => [...c.matchAll(/font-size:\s*(\d+(?:\.\d+)?)px/g)].map(m => +m[1]).sort((x, y) => x - y);
const ROOT_ABS = path.resolve(ROOT);

for (const w of widths) {
  const factor = w / BASE;
  for (const [rel, file] of trees[w]) {
    const depth = rel.split('/').length - 1;
    const fontPrefix = '../'.repeat(depth) + 'fonts/';
    const c = fs.readFileSync(file, 'utf8');
    checked++;
    // .stage 容器 + 宽度
    if (!/<body>\s*<div class="stage">/.test(c) && !/<body>\s*\n?<div class="stage">/.test(c)) problems.push(`无stage: ${w}/${rel}`);
    const sm = c.match(/\.stage\{[^}]*?width:\s*(\d+(?:\.\d+)?)px/);
    if (!sm || +sm[1] !== w) problems.push(`stage宽错(应${w}): ${w}/${rel} = ${sm ? sm[1] : '未找到'}`);
    // title
    if (!/<title>/.test(c)) problems.push(`无title: ${w}/${rel}`);
    // 字体路径深度（单双引号都认）
    const urls = [...c.matchAll(/url\((['"])([^']*fonts\/[^'"]+)\1\)/g)].map(x => x[2]);
    for (const u of urls) if (!u.startsWith(fontPrefix)) { problems.push(`字体路径错(应${fontPrefix}): ${w}/${rel} → ${u}`); break; }
    // 引用分口径：.html 链接→死链/逃逸断言；其余→素材本地引用断言（全量遍历 src/href 与内联 url()）
    const fileDir = path.dirname(file);
    const refs = [
      ...[...c.matchAll(/(?:src|href)="([^"]+)"/g)].map(x => x[1]),
      ...[...c.matchAll(/url\((['"]?)([^)'"]+)\1\)/g)].map(x => x[2]),
    ];
    for (const ref of refs) {
      if (/^(data:|mailto:|#|javascript:)/i.test(ref)) continue;
      if (/^https?:/i.test(ref)) { problems.push(`外链(产物应自包含): ${w}/${rel} → ${ref}`); continue; }
      if (/^[A-Za-z]:[\\/]/.test(ref)) { problems.push(`引用为绝对路径: ${w}/${rel} → ${ref}`); continue; }
      const resolved = path.resolve(fileDir, ref);
      if (!resolved.startsWith(ROOT_ABS)) { problems.push(`引用逃逸产物根: ${w}/${rel} → ${ref}`); continue; }
      if (ref.endsWith('.html')) {
        if (!fs.existsSync(resolved)) problems.push(`死链: ${w}/${rel} → ${ref}`);
        continue;
      }
      if (!fs.existsSync(resolved)) { problems.push(`素材缺失: ${w}/${rel} → ${ref}`); }
    }
    // 内容溯源（仅基准树）：dump 文字行（剥坐标前缀后 ≥6 字）必须在页面中出现（文本节点或属性值皆可——占位文案常在 placeholder/value 属性里）
    const dump = dumps[rel];
    if (dump && w === BASE) {
      const pageText = stripTags(c);
      for (const line of dump.split('\n')) {
        const t = line.trim().replace(/^y=\s*-?\d+\s+x=\s*-?\d+\s+/, '').trim();
        if (t.length >= 6 && !t.startsWith('#') && !t.startsWith('---') && !t.startsWith('img ') && !t.startsWith('(bg)') && !pageText.includes(t.replace(/\s+/g, '')) && !c.includes(t.replace(/\s+/g, ''))) {
          problems.push(`内容缺失(溯源失败): ${w}/${rel} ← "${t.slice(0, 20)}"`);
          break;
        }
      }
    } else if (w === BASE && !dump) {
      problems.push(`缺dump(内容溯源未执行): ${rel}`);
    }
    // 倍率数值断言：目标树字号集合 ≈ 基准树同名页字号集合 × (w/BASE)（容差 max(0.5, 2%)）
    if (w !== BASE && trees[BASE].has(rel)) {
      const baseSizes = extractFontSizes(fs.readFileSync(trees[BASE].get(rel), 'utf8'));
      const targetSizes = extractFontSizes(c);
      const expected = baseSizes.map(v => +(v * factor).toFixed(2)).sort((x, y) => x - y);
      const actual = targetSizes.slice().sort((x, y) => x - y);
      if (expected.length && (expected.length !== actual.length || expected.some((v, i) => Math.abs(v - actual[i]) > Math.max(0.5, v * 0.02)))) {
        problems.push(`字号倍率不符(应×${factor}): ${w}/${rel} 基准[${baseSizes}] 目标[${actual}]`);
      }
    }
  }
}

// ---------- 产出（落产物根 .gen，不污染 CWD） ----------
const result = { widths, proto: proto.length, checked, problems };
const outDir = path.join(ROOT, '.gen');
fs.mkdirSync(outDir, { recursive: true });
fs.writeFileSync(path.join(outDir, 'audit-result.json'), JSON.stringify(result, null, 1));
console.log(`原型: ${proto.length}  断言文件: ${checked}  问题数: ${problems.length}`);
for (const p of problems) console.log('  ✗', p);
process.exit(problems.length ? 2 : 0);
