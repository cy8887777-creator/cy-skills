import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

const LIBS = [
  { id: 'element-zh', gh: 'element-plus/element-plus', branch: 'dev', probes: ['/docs/zh-CN/'], ext: /\.md$/, limit: 60 },
  { id: 'nutui', gh: 'jdf2e/nutui', branch: 'next', probes: ['/src/sites/doc/', '/docs/'], ext: /\.md$/, limit: 30 },
  { id: 'arco', gh: 'arco-design/arco-design', branch: 'main', probes: ['/docs/'], ext: /\.md$/, limit: 30 },
  { id: 'tdesign-mobile', gh: 'Tencent/tdesign-mobile-vue', branch: 'main', probes: ['/docs/'], ext: /\.(md|mdx)$/, limit: 30 },
];

for (const lib of LIBS) {
  process.stdout.write('[' + lib.id + '] ');
  try {
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(60000) });
    if (!r.ok) { console.log('❌ 树 ' + r.status); continue; }
    const tree = await r.json();
    const files = [];
    const walk = (node, prefix) => { for (const f of (node.files || [])) { const full = prefix + '/' + f.name; if (f.type === 'directory') walk(f, full); else files.push(full); } };
    walk(tree, '');
    let targets = [];
    for (const probe of lib.probes) {
      targets = files.filter(f => f.includes(probe) && lib.ext.test(f));
      if (targets.length) break;
    }
    if (!targets.length) {
      const guess = files.filter(f => lib.ext.test(f)).slice(0, 5);
      console.log('⚠ 未定位（' + files.length + ' 文件）样例:', guess.join(' | ').slice(0, 180));
      continue;
    }
    targets = targets.slice(0, lib.limit);
    const out = path.join(base, lib.id);
    fs.mkdirSync(out, { recursive: true });
    let ok = 0;
    for (const f of targets) {
      try {
        const rr = await fetch('https://cdn.jsdelivr.net/gh/' + lib.gh + '@' + lib.branch + f, { signal: AbortSignal.timeout(20000) });
        if (!rr.ok) continue;
        const parts = f.split('/'); const name = parts[parts.length - 1];
        const dirTag = parts[parts.length - 2] || '';
        const fname = (dirTag && !name.match(/^(index|README)/i) ? dirTag + '-' : '') + name;
        fs.writeFileSync(path.join(out, fname), await rr.text());
        ok++;
      } catch (e) { /* 跳过 */ }
    }
    console.log('✅ ' + ok + '/' + targets.length);
  } catch (e) { console.log('❌ ' + e.message); }
}
