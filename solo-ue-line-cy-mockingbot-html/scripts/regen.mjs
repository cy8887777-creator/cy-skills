// regen.mjs —— 用 boards/<cid>.json 缓存统一重生成全部页面 HTML（gen-html 规则升级后全量重刷，不用重新提取）
// 用法：node regen.mjs <产物根目录> [--only <页面cid,...>] [--concurrency 4]
// 场景：改了 gen-html.cjs 的生成规则（如换行策略/字体链/data:svg），提取数据不用动，秒级重刷所有产物
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';

const SCRIPTS = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const ROOT = argv[0];
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1].split(',').map(s => s.trim()) : null;
const conc = argv.includes('--concurrency') ? +argv[argv.indexOf('--concurrency') + 1] : 4;
if (!ROOT || !fs.existsSync(path.join(ROOT, 'state.json'))) {
  console.error('用法: node regen.mjs <产物根目录> [--only 页面cid,…] [--concurrency 4]');
  process.exit(1);
}
const state = JSON.parse(fs.readFileSync(path.join(ROOT, 'state.json'), 'utf8'));
// 交互热区层已下线（2026-09-16 用户拍板：跳转语义大量跳自己/未收录，且透明热区盖画面影响后续导入使用）。
// hotzones.json 数据保留在产物根仅作档案；gen-html 的 --hotzones 能力保留但不再被任何流程携带。
const hzArgs = [];

// 收集任务：state.done 每板 {json, html}（html 相对 OUTROOT）
const jobs = [];
for (const [pcid, d] of Object.entries(state.done)) {
  if (only && !only.includes(pcid)) continue;
  for (const b of (d.boards || [])) {
    if (!b.json || !b.html) continue;
    const json = path.resolve(ROOT, b.json);
    const html = path.resolve(ROOT, b.html);
    if (!fs.existsSync(json)) { console.log(`✗ 缓存缺失 ${b.name}: ${b.json}`); continue; }
    const rel = path.relative(path.dirname(html), path.join(ROOT, 'assets')).replace(/\\/g, '/');
    jobs.push({ name: d.dir.concat(d.name, b.name).join('/'), json, html, rel });
  }
}
console.log(`待重生成: ${jobs.length} 板（并发 ${conc}）`);

const genHtml = (j) => new Promise((resolve) => {
  const p = spawn(process.execPath, [path.join(SCRIPTS, 'gen-html.cjs'), j.json, j.html,
    '--assets', path.join(ROOT, 'assets'), '--assets-rel', j.rel, ...hzArgs], { stdio: 'pipe' });
  let buf = '';
  p.stdout.on('data', d => buf += d); p.stderr.on('data', d => buf += d);
  p.on('error', (e) => resolve({ ok: false, j, err: e.message }));
  p.on('close', (code) => resolve({ ok: code === 0, j, err: code !== 0 ? buf.trim() : '' }));
});

let done = 0, fail = 0;
const t0 = Date.now();
const queue = jobs.slice();
const workers = Array.from({ length: Math.min(conc, queue.length) }, async () => {
  while (queue.length) {
    const r = await genHtml(queue.shift());
    done++;
    if (!r.ok) { fail++; console.log(`✗ [${done}/${jobs.length}] ${r.j.name}: ${r.err}`); }
    else if (done % 50 === 0) console.log(`… [${done}/${jobs.length}] ${((Date.now() - t0) / 1000).toFixed(0)}s`);
  }
});
await Promise.all(workers);
console.log(JSON.stringify({ ok: true, regen: done - fail, failed: fail, seconds: +((Date.now() - t0) / 1000).toFixed(1) }));
