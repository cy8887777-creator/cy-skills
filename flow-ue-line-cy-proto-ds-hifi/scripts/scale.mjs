#!/usr/bin/env node
// scale.mjs —— 倍数派生：基准宽页面 → 目标宽版本（全 px ×倍率，rpx 一比一）
// 用法: node scale.mjs <基准375版html> <产物根> <目标宽>   例: node scale.mjs 产物/375/首页/x.html 产物 750
// 规则: 输出至 产物根/<目标宽>/<与基准相同的相对路径>；拒绝无 .stage 容器的文件（防手写/防漏容器）
import fs from 'node:fs';
import path from 'node:path';

const src = path.resolve(process.argv[2] || '');
const root = path.resolve(process.argv[3] || '');
const target = parseInt(process.argv[4] || '0', 10);
if (!src || !fs.existsSync(src) || !target) { console.error('用法: node scale.mjs <基准html> <产物根> <目标宽>'); process.exit(1); }

// 基准宽从源文件 .stage 声明读取
const srcHtml = fs.readFileSync(src, 'utf8');
const bm = srcHtml.match(/\.stage\{[^}]*?width:\s*(\d+)px/) || srcHtml.match(/\.stage\{position:relative;width:(\d+)px/);
if (!bm) { console.error('!! 源文件无 .stage 容器（或未声明宽度），拒绝派生'); process.exit(1); }
const base = parseInt(bm[1], 10);
if (target === base) { console.error('!! 目标宽与基准宽相同，无需派生'); process.exit(1); }
const factor = target / base;

// 核心：全 px ×倍率（750 = 2x 时数值即 rpx 一比一）
let html = srcHtml.replace(/(-?\d+(?:\.\d+)?)px/g, (m, n) => +(parseFloat(n) * factor).toFixed(2) + 'px');

// title 标注语义为「派生」而非「基准」；已标注过则不重复
if (!/派生/.test(html)) {
  html = html.replace(/<title>([^<]*)<\/title>/, (m, t) => /派生|（\d+px/.test(t) ? m : `<title>${t}（派生 ${target}px）</title>`);
}
const rel = path.relative(path.join(root, String(base)), src);
const dest = path.join(root, String(target), rel);
fs.mkdirSync(path.dirname(dest), { recursive: true });
fs.writeFileSync(dest, html);
console.log(`派生: ${rel}  ${base}→${target}  →  ${path.relative(root, dest)}`);
