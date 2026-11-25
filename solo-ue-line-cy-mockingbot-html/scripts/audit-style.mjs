// audit-style.mjs —— 样式保真断言（跑批/regen 后必跑）：「json 里父链有圆角容器的 img，产物必须带圆角」
// 由来（2026-09-16 两轮验收实锤）：圆角规则在 SKILL.md 记了两轮，但产物 img 带 br 只有 959/11348——
// inspect/audit 断言维度不含样式保真，坑被文字记录却没有机器断言，全量丢了 3000+ 处全绿通过。
// 断言口径：img 节点父链 6 层内存在 st.br 容器 → 产物对应 div 必须含 border-radius（PNG 圆素材族父链无 br，天然豁免）。
// 用法：node audit-style.mjs <产物根> [--sample N]
import fs from 'node:fs';
import path from 'node:path';

const argv = process.argv.slice(2);
const ROOT = path.resolve(argv[0]);
const sampleN = argv.includes('--sample') ? +(argv[argv.indexOf('--sample') + 1]) : 8;
if (!ROOT || !fs.existsSync(path.join(ROOT, 'state.json'))) {
  console.error('用法: node audit-style.mjs <产物根> [--sample N]'); process.exit(1);
}
const state = JSON.parse(fs.readFileSync(path.join(ROOT, 'state.json'), 'utf8'));

let shouldHave = 0, hasIt = 0;
const misses = [];
for (const [pcid, d] of Object.entries(state.done)) {
  for (const b of (d.boards || [])) {
    const jp = b.json ? (path.isAbsolute(b.json) ? b.json : path.join(ROOT, b.json)) : null;
    const hp = b.html ? path.join(ROOT, b.html) : null;
    if (!jp || !hp || !fs.existsSync(jp) || !fs.existsSync(hp)) continue;
    const nodes = JSON.parse(fs.readFileSync(jp, 'utf8')).page.nodes;
    const byIdx = new Map(nodes.map(n => [n.idx, n]));
    // 父链 6 层内有 br 容器的 img（画布外节点豁免——gen-html 按画板外辅助层规则不渲染，与墨刀画布视图一致）
    const boardW = JSON.parse(fs.readFileSync(jp, 'utf8')).page.board.w;
    const boardH = JSON.parse(fs.readFileSync(jp, 'utf8')).page.board.h;
    const needBr = new Set();
    for (const n of nodes) {
      if (!n.img || n.x >= boardW || n.y >= boardH) continue;
      let p = byIdx.get(n.parent), depth = 0;
      while (p && depth < 6) { if (p.st && p.st.br) { needBr.add(n.idx); break; } p = byIdx.get(p.parent); depth++; }
    }
    if (!needBr.size) continue;
    const t = fs.readFileSync(hp, 'utf8');
    for (const idx of needBr) {
      shouldHave++;
      const m = t.match(new RegExp(`<div data-idx="${idx}" style="([^"]*)"`));
      if (m && /border-radius/.test(m[1])) hasIt++;
      else if (misses.length < sampleN) misses.push(`${d.name.trim().slice(0, 18)}/${(b.name || '')} idx=${idx}`);
    }
  }
}
const rate = shouldHave ? +(hasIt / shouldHave * 100).toFixed(1) : 100;
console.log(JSON.stringify({ '父链有br的img': shouldHave, '产物带br': hasIt, '覆盖率%': rate }));
if (rate < 99.5) { console.log('✗ 未覆盖样例:'); misses.forEach(s => console.log('  ', s)); process.exit(1); }
console.log('✓ 圆角覆盖率达标');
