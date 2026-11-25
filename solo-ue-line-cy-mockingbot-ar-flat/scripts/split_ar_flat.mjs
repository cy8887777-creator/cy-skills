// split_ar_flat.mjs — 平铺版分批切分（导入墨刀用：一次导入太多页面会卡死）
//
// 输入 gen_ar_flat.mjs 产出的全量平铺 HTML，按每批 N 屏切成多个独立完整 HTML：
//   • 保留 head 全部 <style>，每批可独立打开
//   • 每批页眉标注「批次 N/M · 屏 X–Y」，导入时对号
//   • 卡片结构原样保留，不做任何翻译/布局改动
//
// 用法：
//   node scripts/split_ar_flat.mjs --file ar_flat.html [--size 25] [--out-dir batches] [--prefix batch]
// 产物：batches/batch_01.html … 每批独立可开；推荐先用 20 屏试导入墨刀，不卡再加到 30。

import fs from 'fs';
import path from 'path';

const args = process.argv.slice(2);
const getArg = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const FILE = getArg('file', 'ar_flat.html');
const SIZE = parseInt(getArg('size', '25'), 10);
const OUT_DIR = getArg('out-dir', 'batches');
const PREFIX = getArg('prefix', path.basename(FILE).replace(/\.html$/, ''));

const html = fs.readFileSync(FILE, 'utf8');

// ---- 结构切分：head（含 style）/ 卡片列表 ----
const headEnd = html.indexOf('</head>') + '</head>'.length;
const head = html.slice(0, headEnd);
const body = html.slice(headEnd);

const MARK = '<div class="card">';
const marks = [];
let p = -1;
while ((p = body.indexOf(MARK, p + 1)) !== -1) marks.push(p);
if (!marks.length) { console.error('✗ 未找到卡片（.card）——确认输入是 gen_ar_flat.mjs 的平铺产物'); process.exit(1); }
// 尾部闭合（grid+wrap）：最后一张卡切到这里为止，避免把源文件的 </body></html> 带进块里
const gridClose = body.indexOf('\n  </div>\n</div>');
if (gridClose === -1 || gridClose < marks[marks.length - 1]) { console.error('✗ 未找到 grid/wrap 尾部闭合，结构异常'); process.exit(1); }
const cards = [];
for (let i = 0; i < marks.length; i++) {
  const end = i + 1 < marks.length ? marks[i + 1] : gridClose;
  cards.push(body.slice(marks[i], end));
}
console.log(`源文件 ${FILE}：${cards.length} 屏 → 每批 ${SIZE} 屏`);

// ---- 分批输出 ----
fs.mkdirSync(OUT_DIR, { recursive: true });
const total = Math.ceil(cards.length / SIZE);
for (let b = 0; b < total; b++) {
  const chunk = cards.slice(b * SIZE, (b + 1) * SIZE);
  const from = b * SIZE + 1, to = b * SIZE + chunk.length;
  const out = `<!DOCTYPE html>
<html lang="zh" dir="ltr">
${head.replace(/<title>[^<]*<\/title>/, `<title>${PREFIX} 批次 ${b + 1}/${total}</title>`)}
<body><div class="wrap">
<header><h1>${PREFIX} · 批次 ${b + 1}/${total}（屏 ${from}–${to} / 共 ${cards.length}）</h1>
<div class="sub">墨刀导入分批文件 · 每批独立完整 · 顺序与全量版一致</div></header>
<div class="grid">
${chunk.join('\n')}
</div></div></body></html>`;
  const name = `${OUT_DIR}/${PREFIX}_${String(b + 1).padStart(2, '0')}.html`;
  fs.writeFileSync(name, out);
  console.log(`  ✓ ${name}（${chunk.length} 屏，${(out.length / 1024).toFixed(0)} KB）`);
}
console.log(`\n完成：${total} 个批次文件在 ${OUT_DIR}/`);
