#!/usr/bin/env node
// build-manifest.mjs —— 对账 + 任务清单 + 同名冲突预检（零依赖）
// 分叉自 lofi-rebuild-hifi-design · 2026-10-23 · 与上游零差异，仅声明分叉；此后不再随上游同步
// 用法: node build-manifest.mjs <原型根> <dump目录> <产物根> <基准宽>
// 产出: <产物根>/.gen/manifest.json（rel/depth/dump/title）+ 冲突/异常报告
import fs from 'node:fs';
import path from 'node:path';

const PROTO = path.resolve(process.argv[2]);
const DUMPS = path.resolve(process.argv[3]);
const OUTROOT = path.resolve(process.argv[4]);
const BASE = parseInt(process.argv[5] || '375', 10);
fs.mkdirSync(path.join(OUTROOT, '.gen'), { recursive: true });

// 1) 原型树页面清单
const pages = [];
(function walk(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['assets', 'fonts', 'node_modules', '.gen'].includes(e.name) || e.name.startsWith('_') || e.name.startsWith('.') || /^\d+$/.test(e.name)) continue;
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walk(f, r);
    else if (e.name.endsWith('.html')) pages.push(r);
  }
})(PROTO, '');
pages.sort((a, b) => a.localeCompare(b, 'zh'));

// 2) manifest（dump 存在性 + depth）
const items = [], problems = [];
for (const rel of pages) {
  const dumpRel = rel.replace(/\.html$/, '.txt');
  const dp = path.join(DUMPS, dumpRel);
  if (!fs.existsSync(dp)) { problems.push(`缺dump: ${rel}`); continue; }
  const title = (fs.readFileSync(dp, 'utf8').match(/^# (.+?)  \(rel=/) || [])[1] || rel;
  items.push({ rel, depth: rel.split('/').length - 1, dump: path.relative(OUTROOT, dp).replace(/\\/g, '/'), title });
}

// 3) 同 basename 冲突预检（同名页在不同目录——生成时防止相互覆盖/引用混乱，列出供知悉）
const byBase = {};
for (const it of items) { const b = it.rel.split('/').pop(); (byBase[b] = byBase[b] || []).push(it.rel); }
const collisions = Object.entries(byBase).filter(([, v]) => v.length > 1);
for (const [b, rels] of collisions) problems.push(`同名页 ${b} ×${rels.length}（各自独立产物，互不影响；子代理勿跨目录引用）: ${rels.join(' | ')}`);

// 4) 产物目录不应已存在同名基准页（防覆盖）
for (const it of items) {
  const p = path.join(OUTROOT, String(BASE), it.rel);
  if (fs.existsSync(p)) problems.push(`产物已存在(将覆盖): ${String(BASE)}/${it.rel}`);
}

fs.writeFileSync(path.join(OUTROOT, '.gen', 'manifest.json'), JSON.stringify(items, null, 1));
console.log(`页面: ${items.length}  基准宽: ${BASE}  异常: ${problems.length}`);
for (const p of problems) console.log('  ⚠', p);
if (problems.some(p => p.startsWith('缺dump'))) process.exit(2);
