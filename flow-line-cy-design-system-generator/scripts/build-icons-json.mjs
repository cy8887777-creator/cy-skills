#!/usr/bin/env node
// build-icons-json.mjs —— 把 data/icons/ 下 10 个开源图标库的散装 SVG
// 合并为 data/icons-json/<库名>.json（每库一个文件，格式对齐
// solo-img-line-cy-icon-provisioner/assets/icons-json 的惯例：
//   { name, license, total, byForm, generatedAt, source, icons: { <图标键>: <完整 SVG 字符串> }, iconForms: { <图标键>: <变体键> } }
// 变体（outline/fill/solid/bold…）通过图标键后缀与 iconForms 双重保留。
//
// 用法：node scripts/build-icons-json.mjs [iconsDir] [outDir]
//   默认 iconsDir = <skillRoot>/data/icons，outDir = <skillRoot>/data/icons-json
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const iconsDir = path.resolve(process.argv[2] || path.join(skillRoot, 'data', 'icons'));
const outDir = path.resolve(process.argv[3] || path.join(skillRoot, 'data', 'icons-json'));

// 这些库的顶层变体目录与文件名不互相编码（同名跨变体冲突），图标键需追加变体后缀；
// 其余库（boxicons bx-/bxs-、material-symbols *-fill、remixicon *-fill 等）文件名已自含变体。
const SUFFIX_LIBS = new Set(['solar', 'tabler', 'heroicons']);
const kebab = s => s.trim().replace(/\s+/g, '-').toLowerCase();
const svgFiles = dir => {
  const out = [];
  const walk = d => {
    for (const f of fs.readdirSync(d)) {
      const fp = path.join(d, f);
      if (fs.statSync(fp).isDirectory()) walk(fp);
      else if (f.toLowerCase().endsWith('.svg')) out.push(fp);
    }
  };
  walk(dir);
  return out;
};

fs.mkdirSync(outDir, { recursive: true });
const libs = fs.readdirSync(iconsDir).filter(d => {
  const dp = path.join(iconsDir, d);
  return fs.statSync(dp).isDirectory() && !d.startsWith('_');
}).sort();

const summary = [];
for (const lib of libs) {
  const libDir = path.join(iconsDir, lib);
  let meta = {};
  try { meta = JSON.parse(fs.readFileSync(path.join(libDir, '_meta.json'), 'utf8')); } catch { /* 无 meta 容错 */ }

  // 变体 = 库目录下的第一层子目录（无子目录则整库为单一线性变体）
  const variants = fs.readdirSync(libDir).filter(d => fs.statSync(path.join(libDir, d)).isDirectory());
  const icons = {};
  const iconForms = {};
  const byForm = {};
  let collisions = 0;
  for (const vDir of variants.length ? variants : ['']) {
    const form = vDir || meta.forms?.[0]?.key || 'linear';
    for (const fp of svgFiles(vDir ? path.join(libDir, vDir) : libDir)) {
      const stem = kebab(path.basename(fp, '.svg'));
      const key = SUFFIX_LIBS.has(lib) && vDir ? `${stem}-${kebab(vDir)}` : stem;
      if (icons[key] !== undefined) { collisions++; continue; } // 键冲突防覆盖（同名同变体）
      const svg = fs.readFileSync(fp, 'utf8');
      if (!svg.includes('<svg')) continue; // 非法内容跳过
      icons[key] = svg;
      iconForms[key] = form;
      byForm[form] = (byForm[form] || 0) + 1;
    }
  }

  const doc = {
    name: lib,
    license: meta.license || '见 data/icons-json/THIRD_PARTY_NOTICES.md',
    total: Object.keys(icons).length,
    byForm,
    source: meta.source || 'offline svg collection',
    generatedAt: new Date().toISOString(),
    icons,
    iconForms,
  };
  const outFile = path.join(outDir, `${lib}.json`);
  fs.writeFileSync(outFile, JSON.stringify(doc));
  const sizeMB = +(fs.statSync(outFile).size / 1048576).toFixed(2);
  summary.push({ lib, total: doc.total, byForm, collisions, sizeMB });
  console.log(`${lib}.json  ${doc.total} 枚  [${Object.entries(byForm).map(([k, v]) => k + ':' + v).join(' / ')}]  冲突跳过:${collisions}  ${sizeMB}MB`);
}

fs.writeFileSync(path.join(outDir, '_index.json'), JSON.stringify({
  generatedAt: new Date().toISOString(),
  description: 'offline icon libraries for design-system-generator (icon style step), one JSON per library',
  sourceRoot: 'data/icons-json/<lib>.json',
  libraries: summary.map(s => ({ name: s.lib, total: s.total, byForm: s.byForm })),
}, null, 2));
console.log(`\n共 ${summary.length} 库 ${summary.reduce((a, s) => a + s.total, 0)} 枚图标 → ${outDir}`);
