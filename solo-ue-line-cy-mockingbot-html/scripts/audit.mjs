#!/usr/bin/env node
// audit.mjs —— 产物对账：跑完一批/全量后自检（原 .claude-tmp/audit1.cjs 收编泛化）
// 用法：node audit.mjs <产物根目录>
// 检查项：
//   1) 多页共用板（同 cid 出现在多个页面产物——提示归属是否错认）
//   2) state 产物清单 vs 磁盘 html：孤儿（盘有账无）/ 缺失（账有盘无）
//   3) boards/*.json vs state 板清单：缺 json / 多余 json
//   4) 空页面 / 失败页面 / 失败板清单
//   5) 产物 html 里残留 blob: / InteractionMarker（应为零）
// 退出码：有孤儿/缺失/失败 → 1（可接 CI），仅共用板提示 → 0
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.argv[2];
if (!ROOT || !fs.existsSync(ROOT)) { console.error('用法: node audit.mjs <产物根目录>'); process.exit(2); }
const norm = (p) => String(p).replace(/\\/g, '/');

const stateFile = path.join(ROOT, 'state.json');
if (!fs.existsSync(stateFile)) { console.error('✗ 没有 state.json（batch 还没跑过？）'); process.exit(2); }
const state = JSON.parse(fs.readFileSync(stateFile, 'utf8'));

// ---- 1. 多页共用板 ----
const cidPages = {};
for (const [pc, d] of Object.entries(state.done)) for (const b of (d.boards || [])) (cidPages[b.cid] = cidPages[b.cid] || []).push(d.name);
const shared = Object.entries(cidPages).filter(([, ps]) => ps.length > 1);

// ---- 2. state vs 磁盘 html ----
const inState = new Set(Object.values(state.done).flatMap(d => (d.boards || []).map(b => norm(b.html))));
const onDisk = [];
(function walk(d) {
  for (const f of fs.readdirSync(d)) {
    if (f === 'assets' || f === 'boards' || f.startsWith('_')) continue;
    const p = path.join(d, f);
    if (fs.statSync(p).isDirectory()) walk(p);
    else if (/\.html?$/i.test(f)) onDisk.push(norm(path.relative(ROOT, p)));
  }
})(ROOT);
const orphans = onDisk.filter(p => !inState.has(p));
const missing = [...inState].filter(p => !onDisk.includes(p));

// ---- 3. boards json 对账 ----
const jsonOnDisk = new Set(fs.readdirSync(path.join(ROOT, 'boards')).filter(f => f.endsWith('.json')).map(f => f.replace(/\.json$/, '')));
const cidInState = new Set(Object.keys(cidPages));
const jsonMissing = [...cidInState].filter(c => !jsonOnDisk.has(c.replace(/[\/]/g, '_')));
const jsonExtra = [...jsonOnDisk].filter(f => !cidInState.has(f));

// ---- 4. 空页 / 失败 ----
const empties = Object.entries(state.done).filter(([, d]) => d.empty).map(([, d]) => (d.dir || []).concat(d.name).join('/'));
const failed = Object.entries(state.done).filter(([, d]) => d.error).map(([, d]) => `${(d.dir || []).concat(d.name).join('/')} → ${d.error}`);
const failedBoards = Object.entries(state.done).filter(([, d]) => (d.failedBoards || []).length)
  .map(([, d]) => `${d.name}: ` + d.failedBoards.map(b => `${b.name}(${b.err})`).join('；'));

// ---- 5. 产物 html 内容残留 ----
let blobHits = 0, imHits = 0;
for (const rel of onDisk) {
  const s = fs.readFileSync(path.join(ROOT, rel), 'utf8');
  if (/url\(["']?blob:/.test(s)) { blobHits++; console.log(`  blob: 残留 → ${rel}`); }
  if (/InteractionMarker/.test(s)) { imHits++; console.log(`  InteractionMarker 残留 → ${rel}`); }
}

// ---- 报告 ----
const done = Object.keys(state.done).length;
const boards = Object.keys(cidPages).length;
console.log(`\n===== 对账报告 =====`);
console.log(`页面 done: ${done} | 板: ${boards} | 磁盘 html: ${onDisk.length} | boards json: ${jsonOnDisk.size}`);
console.log(`空页面 ${empties.length} 个${empties.length ? '：' + empties.join('、') : ''}`);
if (shared.length) console.log(`⚠ 多页共用板 ${shared.length} 块（同 cid 归了两页，人工确认归属）:\n  ` + shared.map(([c, ps]) => `${c} ← ${ps.join(' & ')}`).join('\n  '));
else console.log(`多页共用板: 无`);
console.log(`孤儿 html（盘有账无）: ${orphans.length ? orphans.join('、') : '无'}`);
console.log(`缺失 html（账有盘无）: ${missing.length ? missing.join('、') : '无'}`);
console.log(`缺 json: ${jsonMissing.length ? jsonMissing.join('、') : '无'} | 多余 json: ${jsonExtra.length ? jsonExtra.join('、') : '无'}`);
console.log(`失败页面: ${failed.length ? '\n  ' + failed.join('\n  ') : '无'}${failedBoards.length ? '\n失败板:\n  ' + failedBoards.join('\n  ') : ''}`);
console.log(`内容残留: blob:${blobHits} / InteractionMarker:${imHits}`);

const bad = orphans.length || missing.length || jsonMissing.length || failed.length || failedBoards.length || blobHits || imHits;
console.log(bad ? `\n✗ 对账不平（见上）` : `\n✓ 对账全平`);
process.exit(bad ? 1 : 0);
