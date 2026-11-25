#!/usr/bin/env node
// build-index.mjs —— 产物总入口索引（按倍数目录分链接）
// 用法: node build-index.mjs <产物根> <基准宽> <目标宽...>
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.argv[2]);
const widths = process.argv.slice(3).map(Number);
if (!widths.length) { console.error('用法: node build-index.mjs <产物根> <基准宽> <目标宽...>'); process.exit(1); }
const BASE = widths[0];

// 以基准树为页面清单
const pages = [];
(function walk(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (['assets', 'fonts', '.gen'].includes(e.name) || e.name.startsWith('_')) continue;
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walk(f, r);
    else if (e.name.endsWith('.html')) pages.push(r);
  }
})(path.join(ROOT, String(BASE)), '');
pages.sort((a, b) => a.localeCompare(b, 'zh'));

const groups = {};
for (const r of pages) {
  const top = r.includes('/') ? r.split('/')[0] : '（根目录）';
  (groups[top] = groups[top] || []).push(r);
}
const esc = s => s.replace(/&/g, '&amp;').replace(/</g, '&lt;');
const linkFor = (w, r) => {
  const b = r.split('/').pop().replace(/\.html$/, `-${w}.html`);
  const dir = r.includes('/') ? r.slice(0, r.lastIndexOf('/') + 1) : '';
  const candidate = `${w}/${dir}${b}`;
  return fs.existsSync(path.join(ROOT, candidate)) ? candidate : `${w}/${r}`;
};
let body = '';
for (const [g, list] of Object.entries(groups)) {
  body += `<section><h2>${esc(g)}</h2><ul>`;
  for (const r of list) {
    const name = r.split('/').pop().replace(/\.html$/, '');
    const links = widths.map(w => `<a href="${esc(linkFor(w, r))}">${w}</a>`).join('');
    body += `<li><span class="n">${esc(name)}</span>${links}</li>`;
  }
  body += '</ul></section>';
}
const html = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>高保真产物 · 总入口</title><style>
body{font-family:'Noto Sans SC','PingFang SC',sans-serif;background:#F0F2F5;margin:0;padding:32px;color:#20252C;}
h1{font-size:22px;margin:0 0 4px;} .sub{color:#979CA5;font-size:13px;margin-bottom:24px;}
section{background:#fff;border-radius:12px;padding:16px 20px;margin-bottom:16px;box-shadow:0 2px 7px rgba(20,90,180,.05);}
h2{font-size:16px;margin:0 0 10px;} ul{list-style:none;margin:0;padding:0;}
li{display:flex;align-items:center;gap:12px;padding:6px 0;border-bottom:1px solid #F0F2F5;}
li:last-child{border-bottom:none;} .n{flex:1;font-size:14px;}
a{font-size:12px;color:#2196F3;text-decoration:none;border:1px solid rgba(33,150,243,.35);border-radius:999px;padding:2px 12px;}
a:hover{background:rgba(33,150,243,.08);}
</style></head><body><h1>高保真产物 · 总入口</h1><div class="sub">${pages.length} 页 × 倍数 [${widths.join(', ')}] · 每页含画布容器</div>${body}</body></html>`;
fs.writeFileSync(path.join(ROOT, '_index.html'), html);
console.log('saved: _index.html,', pages.length, '页 ×', widths.length, '倍数');
