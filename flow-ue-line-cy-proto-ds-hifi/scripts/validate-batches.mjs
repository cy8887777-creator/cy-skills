#!/usr/bin/env node
// validate-batches.mjs —— 派发前批次清单自校验（归零制前置闸）
// 用法: node validate-batches.mjs <原型根> <产物根> [batches目录]
//   batches 默认 <产物根>\.gen\batches；dump 默认 <产物根>\.gen\dumps
//   样板排除：batches 目录下可选 _samples.json（rel 数组）
// 断言: 每页 dump 存在｜rel 在原型树｜非样板页无遗漏｜无重复派发｜depth=层级
import fs from 'node:fs';
import path from 'node:path';

const PROTO = path.resolve(process.argv[2] || '');
const PROD = process.argv[3] ? path.resolve(process.argv[3]) : null;
const DIR = process.argv[4] ? path.resolve(process.argv[4]) : (PROD ? path.join(PROD, '.gen', 'batches') : null);
if (!fs.existsSync(PROTO) || !PROD || !fs.existsSync(DIR)) {
  console.error('用法: node validate-batches.mjs <原型根> <产物根> [batches目录]');
  process.exit(1);
}
const DUMPS = path.join(PROD, '.gen', 'dumps');

const proto = [];
(function walk(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['assets', 'fonts', 'node_modules', '.gen'].includes(e.name) || e.name.startsWith('_') || e.name.startsWith('.') || /^\d+$/.test(e.name)) continue;
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walk(f, r);
    else if (e.name.endsWith('.html')) proto.push(r);
  }
})(PROTO, '');
const protoSet = new Set(proto);

const samplesPath = path.join(DIR, '_samples.json');
const samples = new Set(fs.existsSync(samplesPath) ? JSON.parse(fs.readFileSync(samplesPath, 'utf8').replace(/^\uFEFF/, '')) : []);
const problems = [];
for (const s of samples) if (!protoSet.has(s)) problems.push(`样板清单含未知页 → ${s}`);
const seen = new Set();
const files = fs.readdirSync(DIR).filter(f => f.endsWith('.json') && !f.startsWith('_')).sort();
for (const bf of files) {
  let raw = fs.readFileSync(path.join(DIR, bf), 'utf8').replace(/^\uFEFF/, '');
  let b;
  try { b = JSON.parse(raw); }
  catch (e) { problems.push(`${bf}: JSON 解析失败 → ${e.message}`); continue; }
  if (!Array.isArray(b.pages) || !b.pages.length) { problems.push(`${bf}: pages 为空`); continue; }
  for (const p of b.pages) {
    if (!p.rel || !protoSet.has(p.rel)) { problems.push(`${bf}: rel 不在原型树 → ${p.rel}`); continue; }
    if (samples.has(p.rel)) problems.push(`${bf}: 样板页不应进批次 → ${p.rel}`);
    if (seen.has(p.rel)) problems.push(`${bf}: 重复派发 → ${p.rel}`);
    seen.add(p.rel);
    const dump = path.join(DUMPS, p.rel.replace(/\.html$/, '.txt'));
    if (!fs.existsSync(dump)) problems.push(`${bf}: dump 缺失 → ${path.relative(PROD, dump)}`);
    const depth = p.rel.split('/').length - 1;
    if (p.depth !== depth) problems.push(`${bf}: depth=${p.depth} 应为 ${depth} → ${p.rel}`);
  }
}
for (const r of proto) if (!seen.has(r) && !samples.has(r)) problems.push(`未派发遗漏 → ${r}`);

console.log(`原型: ${proto.length}  批次派发: ${seen.size}  样板: ${samples.size}  批次: ${files.length}`);
if (problems.length) {
  console.log('问题数: ' + problems.length);
  problems.forEach(p => console.log('  ✗ ' + p));
  process.exit(2);
}
console.log('✅ 批次清单校验通过（可派发）');
