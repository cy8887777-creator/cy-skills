import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

const LIBS = [
  { id: 'shadcn', gh: 'shadcn-ui/ui', branch: 'main', probe: '/apps/www/content/docs/components/', ext: /\.(md|mdx)$/, limit: 30 },
  { id: 'antd', gh: 'ant-design/ant-design', branch: 'master', probe: '/components/', ext: /index\.zh-CN\.md$/, limit: 30 },
  { id: 'vant', gh: 'youzan/vant', branch: 'main', probe: '/packages/vant/docs/markdown/', ext: /\.zh-CN\.md$/, limit: 30 },
  { id: 'element', gh: 'element-plus/element-plus', branch: 'main', probe: '/docs/en-US/component/', ext: /\.md$/, limit: 25 },
  { id: 'daisyui', gh: 'saadeghi/daisyui', branch: 'master', probe: '/components/', ext: /\.md$/, limit: 20 },
];

for (const lib of LIBS) {
  process.stdout.write('[' + lib.id + '] ');
  try {
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(45000) });
    const tree = await r.json();
    const files = [];
    const walk = (node, prefix) => { for (const f of (node.files || [])) { const full = prefix + '/' + f.name; if (f.type === 'directory') walk(f, full); else files.push(full); } };
    walk(tree, '');
    let targets = files.filter(f => f.includes(lib.probe) && lib.ext.test(f)).slice(0, lib.limit);
    if (!targets.length) { console.log('⚠ 未匹配（' + files.length + ' 文件）'); continue; }
    const out = path.join(base, lib.id);
    fs.mkdirSync(out, { recursive: true });
    let ok = 0;
    for (const f of targets) {
      try {
        const rr = await fetch('https://cdn.jsdelivr.net/gh/' + lib.gh + '@' + lib.branch + f, { signal: AbortSignal.timeout(20000) });
        if (!rr.ok) continue;
        fs.writeFileSync(path.join(out, f.split('/').pop()), await rr.text());
        ok++;
      } catch (e) { /* 跳过 */ }
    }
    console.log('✅ ' + ok + '/' + targets.length + ' → ' + lib.id + '/');
  } catch (e) { console.log('❌ ' + e.message); }
}
