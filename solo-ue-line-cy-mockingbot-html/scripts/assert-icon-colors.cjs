#!/usr/bin/env node
// assert-icon-colors.cjs —— 图标颜色全量离线断言（regen/add-interactions 之后跑）
// 校验三件事（对应 gen-html svg 上色分流，图标颜色与原型不一致修复）：
//   A. .fill 修饰的 path 图标（svg-icon-path-icon）：svg 标签 fill 必须是字典色（references/icon-colors.json）；
//      子元素写死 fill|stroke（非 none）也必须是字典色；stroke 型元素必须补了 fill="none"（查看器 g [stroke]{fill:none} 等价）
//   B. path 图标不得残留 fill="currentColor"（上一轮误伤形态）
//   C. 字典未命中计数必须为 0（hash 全集 46 已采齐；出现新 hash 说明字典要补采）。
//      2026-10-20 起：新管线（pcanvas 模型）提取端已按 hash 规则现场解析为绝对色——字典 miss 但 svg
//      根带非 currentColor 的 fill 记 resolvedOffline（合法）；残留 currentColor/无 fill 才算 miss
// 用法：node assert-icon-colors.cjs <产物根>
const fs = require('fs');
const path = require('path');
const SCRIPTS = __dirname;
const iconColors = require('../references/icon-colors.json');
const ROOT = process.argv[2];
if (!ROOT || !fs.existsSync(ROOT)) { console.error('用法: node assert-icon-colors.cjs <产物根>'); process.exit(1); }

let stat = { icons: 0, dictOk: 0, fillNoneOk: 0, badCurrentColor: 0, missHash: {}, bad: [] };

function walk(dir) {
  let ents; try { ents = fs.readdirSync(dir, { withFileTypes: true }); } catch (e) { return; }
  for (const e of ents) {
    const p = path.join(dir, e.name);
    if (e.isDirectory()) { if (e.name !== 'assets') walk(p); continue; }
    if (!e.name.endsWith('.html') || e.name.startsWith('_')) continue;
    check(fs.readFileSync(p, 'utf8'), path.relative(ROOT, p));
  }
}

function check(html, rel) {
  for (const m of html.matchAll(/<svg\b[^>]*>[\s\S]*?<\/svg>/g)) {
    const sv = m[0];
    const clsM = sv.slice(0, sv.indexOf('>')).match(/class="([^"]*)"/);
    if (!clsM) continue;
    const cls = clsM[1];
    if (!/(?:^|\s)svg-icon-path-icon(?:\s|$)/.test(cls)) continue;
    stat.icons++;
    const hashM = cls.match(/StyledSVGIconPathComponent-sc-[\w-]+\s+(\S+)/);
    const color = hashM && iconColors[hashM[1]];
    if (!color) {
      // 新管线（pcanvas 模型，2026-10-20）提取端已按 hash 规则现场解析成绝对色：svg 根带非 currentColor 的
      // fill 即视为已解析（合法）；只有残留 currentColor / 完全无 fill 才算未解析（预解析没跑或规则没匹配）
      const openTag0 = sv.slice(0, sv.indexOf('>'));
      const f0 = openTag0.match(/\sfill="([^"]*)"/);
      if (f0 && !/currentColor/i.test(f0[1]) && f0[1] !== 'none') { stat.dictOk++; stat.resolvedOffline = (stat.resolvedOffline || 0) + 1; continue; }
      if (hashM) stat.missHash[hashM[1]] = (stat.missHash[hashM[1]] || 0) + 1;
      continue;
    }
    const openTag = sv.slice(0, sv.indexOf('>'));
    const hasFillMod = /(?:^|\s)fill(?:\s|$)/.test(cls);
    if (hasFillMod) {
      // A: svg fill 与子元素写死色必须是字典色；stroke 型必须 fill="none"
      const svgFill = openTag.match(/\sfill="([^"]*)"/);
      const svgOk = svgFill ? svgFill[1] === color || svgFill[1] === 'none' : false;
      let childOk = true;
      for (const pm of sv.matchAll(/<(path|g|circle|rect|polygon|polyline|line|ellipse)\b([^>]*)>/gi)) {
        const attrs = pm[2];
        const f = attrs.match(/\sfill="([^"]*)"/), s = attrs.match(/\sstroke="([^"]*)"/);
        if (f && !['none', 'transparent', color].includes(f[1])) childOk = false;
        if (s && !['none', 'transparent', color].includes(s[1])) childOk = false;
        if (s && !['none', 'transparent'].includes(s[1]) && !f) { childOk = false; stat.fillNoneOk++; } // stroke 型漏补 fill=none
      }
      if (svgOk && childOk) stat.dictOk++;
      else if (stat.bad.length < 20) stat.bad.push(`${rel} hash=${hashM[1]} svgFill=${svgFill ? svgFill[1] : '无'} childOk=${childOk}`);
      // B: 带 .fill 的 path 图标（字典分支已替换）不得残留 currentColor
      if (/fill="currentColor"/.test(sv) || /stroke="currentColor"/.test(sv)) { stat.badCurrentColor++; if (stat.bad.length < 20) stat.bad.push(`${rel} 残留 currentColor hash=${hashM[1]}`); }
    } else {
      // 无 .fill：查看器无 fill 规则（svg 默认黑），产物不应注入 fill attr；
      // 源码自带的 stroke="currentColor" 等是合法形态（查看器解析容器色，产物一致）
      if (/\sfill="/.test(openTag)) { stat.badCurrentColor++; if (stat.bad.length < 20) stat.bad.push(`${rel} 无.fill却带fill attr`); }
    }
  }
}

walk(ROOT);
const pass = stat.icons > 0 && Object.keys(stat.missHash).length === 0 && stat.badCurrentColor === 0 && stat.bad.length === 0;
console.log(JSON.stringify({ ok: pass, ...stat, bad: stat.bad.slice(0, 10) }, null, 1));
process.exit(pass ? 0 : 1);
