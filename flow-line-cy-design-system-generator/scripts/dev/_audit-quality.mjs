import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

// 文件名黑名单（元数据/流程类，非组件规范）
const NAME_CULL = /changelog|migrate|contribution|contributing|install|readme|template|issue|faq|^home|deploy|version|release/i;
// 内容信号
const KEEP_SIGNAL = /(API|Props|用法|示例|演示|组件|样式|variant|state|demo|usage|Demos|基础|类型)/i;
const CULL_SIGNAL = /^(#.*?(版本|更新|变更|日志|发布))|(CHANGELOG)|(贡献指南)|(如何安装)|(加入我们)/i;

let totalKeep = 0, totalCull = 0;
const report = [];

for (const libDir of fs.readdirSync(base).filter(d => fs.statSync(path.join(base, d)).isDirectory())) {
  const dir = path.join(base, libDir);
  const files = fs.readdirSync(dir).filter(f => f.endsWith('.md') || f.endsWith('.mdx') || f.endsWith('.md.txt'));
  let keep = 0, cull = 0;
  const culledNames = [];
  for (const f of files) {
    const fp = path.join(dir, f);
    const size = fs.statSync(fp).size;
    let verdict = 'keep';
    if (NAME_CULL.test(f)) verdict = 'cull-name';
    else if (size < 400) verdict = 'cull-stub';
    else {
      const content = fs.readFileSync(fp, 'utf8').slice(0, 3000);
      if (CULL_SIGNAL.test(content) && !KEEP_SIGNAL.test(content)) verdict = 'cull-meta';
      else if (!KEEP_SIGNAL.test(content) && size < 2500) verdict = 'cull-thin-noise';
    }
    if (verdict.startsWith('cull')) {
      cull++; totalCull++;
      culledNames.push(f + (verdict === 'cull-stub' ? '(stub)' : ''));
      fs.rmSync(fp, { force: true });
    } else keep++;
  }
  totalKeep += keep;
  report.push(`${libDir}: 留 ${keep} · 剔 ${cull}${culledNames.length ? '  [' + culledNames.slice(0, 4).join(', ') + (culledNames.length > 4 ? '…' : '') + ']' : ''}`);
}
console.log(report.join('\n'));
console.log(`\n总计: 留 ${totalKeep} · 剔 ${totalCull}`);
