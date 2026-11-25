#!/usr/bin/env node
// content-dump.mjs —— 从可编辑 HTML 原型解析每页内容清单（零依赖）
// 用法: node content-dump.mjs <原型根> <dump输出目录>   （两参必填；输出目录务必在原型之外）
// 产出: <输出目录>/<相对路径>.txt（title/声明宽/文字阅读序/图片清单）+ <输出目录>/dump-report.json
import fs from 'node:fs';
import path from 'node:path';

const ROOT = path.resolve(process.argv[2] || '');
const OUT = process.argv[3] ? path.resolve(process.argv[3]) : null;
if (!ROOT || !fs.existsSync(ROOT) || !OUT) {
  console.error('用法: node content-dump.mjs <原型根> <dump输出目录>（输出目录务必在原型目录之外，避免污染输入）');
  process.exit(1);
}
fs.mkdirSync(OUT, { recursive: true });

const EXCLUDE = new Set(['assets', 'fonts', 'node_modules', '.gen']);
const pages = [], bad = [];

// 顺序扫描：保留文档序的文字与图片（去 script/style/noscript/style 属性干扰）
function parsePage(html) {
  const title = (html.match(/<title[^>]*>([^<]*)</) || [])[1] || '';
  const vp = (html.match(/<meta[^>]*name=["']viewport["'][^>]*content=["']([^"']*)["']/i) || [])[1] || '';
  const wDecl = vp.match(/width=(\d+)/i)?.[1]
    || html.match(/\.stage\{[^}]*?width:\s*(\d+)px/)?.[1]
    || html.match(/<body[^>]*style="[^"]*width:\s*(\d+)px/)?.[1]
    || html.match(/class="[^"]*\bstage\b[^"]*"[^>]*style="[^"]*width:\s*(\d+)px/)?.[1]
    || html.match(/style="[^"]*width:\s*(\d+)px[^"]*"[^>]*class="[^"]*\bstage\b/)?.[1]
    || '';
  const clean = html.replace(/<script[\s\S]*?<\/script/gi, '<').replace(/<style[\s\S]*?<\/style/gi, '<').replace(/<!--[\s\S]*?-->/g, '<');
  // 越界剔除：data-idx 原型中负 left/top 坐标（含 translate 负位移）的节点 = 画外内容，连同其直接文本一并剔除
  // 局限：直接文本级；嵌套子树残余由主代理在清单阶段语义把关
  const clean2 = clean.replace(/<[^>]*style="([^"]*)"[^>]*>([^<]*)</gi, (m, style, inner) => {
    const off = /(?:left|top):\s*-\d|translate(?:X|Y)?\(\s*-/i.test(style);
    return off ? '<<' : m;
  });
  const images = [];
  for (const m of clean2.matchAll(/<img\b[^>]*>/gi)) {
    const src = m[0].match(/src=["']([^"']+)["']/i)?.[1] || '';
    if (src && !/^data:/i.test(src)) images.push(src);
  }
  // 内联背景图（bg 素材也进清单，否则绕过素材本地引用断言）
  for (const m of clean2.matchAll(/url\((['"]?)([^)'"]+)\1\)/gi)) {
    if (!/^data:/i.test(m[2])) images.push('(bg)' + m[2]);
  }
  const texts = [];
  for (const m of clean2.matchAll(/>([^<>]+)</g)) {
    const t = m[1].replace(/&nbsp;/g, ' ').replace(/&amp;/g, '&').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&quot;/g, '"').trim();
    if (t) texts.push(t);
  }
  // 相邻重复折叠
  const dedup = [];
  for (const t of texts) if (!dedup.length || dedup[dedup.length - 1] !== t) dedup.push(t);
  return { title, viewport: vp, declaredWidth: wDecl, images, texts: dedup };
}

(function walk(dir, rel) {
  for (const e of fs.readdirSync(dir, { withFileTypes: true })) {
    if (EXCLUDE.has(e.name) || e.name.startsWith('_') || e.name.startsWith('.')) continue;
    const f = path.join(dir, e.name), r = rel ? rel + '/' + e.name : e.name;
    if (e.isDirectory()) walk(f, r);
    else if (e.name.endsWith('.html')) {
      const html = fs.readFileSync(f, 'utf8');
      const p = parsePage(html);
      if (p.texts.length === 0 && p.images.length === 0) { bad.push({ rel: r, reason: '无可解析内容（疑似 JS 渲染页/空壳/整页大图）' }); continue; }
      const dumpRel = r.replace(/\.html$/, '.txt');
      const dp = path.join(OUT, dumpRel);
      fs.mkdirSync(path.dirname(dp), { recursive: true });
      let dump = `# ${p.title || r}  (rel=${r}, 声明宽=${p.declaredWidth || '未声明'})\n`;
      for (const t of p.texts) dump += t + '\n';
      if (p.images.length) { dump += '--- images ---\n'; for (const s of p.images) dump += s + '\n'; }
      fs.writeFileSync(dp, dump);
      pages.push({ rel: r, dump: dumpRel, title: p.title, declaredWidth: p.declaredWidth, texts: p.texts.length, images: p.images.length });
    }
  }
})(ROOT, '');

const report = { pages: pages.length, unparseable: bad, pages_detail: pages };
fs.writeFileSync(path.join(OUT, 'dump-report.json'), JSON.stringify(report, null, 1));
// dump 清单校验和（供 audit 校验清单未被改动）
const manifest = {};
for (const p of pages) {
  const dp = path.join(OUT, p.dump);
  const content = fs.readFileSync(dp, 'utf8');
  manifest[p.dump] = { bytes: Buffer.byteLength(content, 'utf8'), lines: content.split('\n').length };
}
fs.writeFileSync(path.join(OUT, 'dumps-manifest.json'), JSON.stringify(manifest, null, 1));
console.log(`✅ 可解析 ${pages.length} 页  ❌ 不可解析 ${bad.length} 页  🔒 dumps-manifest.json（${Object.keys(manifest).length} 项）`);
for (const b of bad) console.log('  ❌', b.rel, '—', b.reason);
if (bad.length) process.exit(2);
