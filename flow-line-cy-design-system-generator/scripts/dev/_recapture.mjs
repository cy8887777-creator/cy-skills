import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

// 清掉碰撞后的坏目录
for (const d of ['antd', 'daisyui']) fs.rmSync(path.join(base, d), { recursive: true, force: true });

const LIBS = [
  { id: 'antd', gh: 'ant-design/ant-design', branch: 'master', probe: '/components/', ext: /index\.zh-CN\.md$/, nameFrom: f => { const m = f.match(/\/components\/([^/]+)\/index\.zh-CN\.md$/); return m ? m[1] + '.zh-CN.md' : null; }, limit: 40 },
  { id: 'daisyui', gh: 'saadeghi/daisyui', branch: 'master', probe: '/components/', ext: /\.md$/, nameFrom: f => { const parts = f.replace(/\/+$/, '').split('/'); const i = parts.indexOf('components'); if (i >= 0 && parts[i + 1]) return parts[i + 1].replace(/[^\w.-]/g, '_') + '.md'; const m = f.match(/([^/]+)\/\+page\.md$/); return m ? m[1].replace(/[^\w.-]/g, '_') + '.md' : null; }, limit: 30 },
];

for (const lib of LIBS) {
  process.stdout.write('[' + lib.id + '] ');
  try {
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(45000) });
    const tree = await r.json();
    const files = [];
    const walk = (node, prefix) => { for (const f of (node.files || [])) { const full = prefix + '/' + f.name; if (f.type === 'directory') walk(f, full); else files.push(full); } };
    walk(tree, '');
    const out = path.join(base, lib.id);
    fs.mkdirSync(out, { recursive: true });
    const targets = files.filter(f => f.includes(lib.probe) && lib.ext.test(f)).slice(0, lib.limit);
    let ok = 0;
    for (const f of targets) {
      const name = lib.nameFrom(f);
      if (!name) continue;
      try {
        const rr = await fetch('https://cdn.jsdelivr.net/gh/' + lib.gh + '@' + lib.branch + f, { signal: AbortSignal.timeout(20000) });
        if (!rr.ok) continue;
        fs.writeFileSync(path.join(out, name), await rr.text());
        ok++;
      } catch (e) { /* 跳过 */ }
    }
    console.log('✅ ' + ok + '/' + targets.length + ' → ' + lib.id + '/');
  } catch (e) { console.log('❌ ' + e.message); }
}
