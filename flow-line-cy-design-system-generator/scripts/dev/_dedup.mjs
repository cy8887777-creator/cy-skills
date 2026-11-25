import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

let totalDup = 0;
const report = [];
for (const libDir of fs.readdirSync(base).filter(d => fs.statSync(path.join(base, d)).isDirectory())) {
  const dir = path.join(base, libDir);
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.md'));
  // 归一化名称：去语言后缀
  const norm = f => f.replace(/\.en-US|\.en\b|\.zh-CN|\.zh\b|\.fr-FR/i, '').toLowerCase();
  // 1) 同名双语对：保留中文，删英文
  const groups = {};
  files.forEach(f => { (groups[norm(f)] ||= []).push(f); });
  let dup = 0;
  const dupNames = [];
  for (const k of Object.keys(groups)) {
    const g = groups[k];
    if (g.length < 2) continue;
    const zh = g.find(x => /zh/i.test(x));
    const keep = zh || g[0];
    g.filter(x => x !== keep).forEach(x => { fs.rmSync(path.join(dir, x), { force: true }); dup++; dupNames.push(x); });
  }
  // 2) 内容完全相同的异名文件（哈希）
  const hashes = {};
  for (const f of fs.readdirSync(dir)) {
    const h = crypto.createHash('md5').update(fs.readFileSync(path.join(dir, f))).digest('hex');
    if (hashes[h]) { fs.rmSync(path.join(dir, f), { force: true }); dup++; dupNames.push(f + '(同内容)'); }
    else hashes[h] = f;
  }
  totalDup += dup;
  const final = fs.readdirSync(dir).length;
  report.push(`${libDir}: 去 ${dup} → 留 ${final}${dupNames.length ? '  [' + dupNames.slice(0, 3).join(', ') + (dupNames.length > 3 ? '…' : '') + ']' : ''}`);
}
console.log(report.join('\n'));
console.log(`\n去除重复: ${totalDup}`);
