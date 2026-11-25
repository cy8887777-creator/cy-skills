import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

const LIBS = [
  { id: 'taro-ui', gh: 'NervJS/taro-ui', branch: 'main', probes: ['/docs/', '/sites/'], ext: /\.md$/, limit: 25 },
  { id: 'wot-design', gh: 'Moonofweisheng/wot-design-uni', branch: 'main', probes: ['/docs/', '/component/'], ext: /\.md$/, limit: 30 },
  { id: 'uni-ui', gh: 'dcloudio/uni-ui', branch: 'main', probes: ['/docs/', '/components/'], ext: /\.md$/, limit: 30 },
  { id: 'naive-ui', gh: 'tusen-ai/naive-ui', branch: 'main', probes: ['/src/docs/', '/docs/'], ext: /\.md$/, limit: 25 },
  { id: 'framework7', gh: 'framework7io/framework7', branch: 'master', probes: ['/kitchen-sink/', '/docs/'], ext: /\.md$/, limit: 20 },
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
        const fname = (dirTag && dirTag !== 'docs' && dirTag !== 'components' ? dirTag + '-' : '') + name;
        fs.writeFileSync(path.join(out, fname), await rr.text());
        ok++;
      } catch (e) { /* 跳过 */ }
    }
    console.log('✅ ' + ok + '/' + targets.length);
  } catch (e) { console.log('❌ ' + e.message); }
}
