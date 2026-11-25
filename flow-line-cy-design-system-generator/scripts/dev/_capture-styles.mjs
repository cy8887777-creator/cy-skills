import fs from 'node:fs';
import path from 'node:path';
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';

const LIBS = [
  { id: 'shadcn', gh: 'shadcn-ui/ui', branch: 'main', probes: ['apps/www/content/docs/components', 'content/docs/components', 'docs/components'], ext: /\.(md|mdx)$/, limit: 30 },
  { id: 'daisyui', gh: 'saadeghi/daisyui', branch: 'master', probes: ['docs', 'content/docs'], ext: /\.(md|mdx)$/, limit: 30 },
  { id: 'antd-spec', gh: 'ant-design/ant-design', branch: 'master', probes: ['docs/spec'], ext: /\.zh-CN\.md$/, limit: 15 },
  { id: 'vant', gh: 'youzan/vant', branch: 'main', probes: ['packages/vant/docs', 'docs'], ext: /\.md$/, limit: 30 },
  { id: 'tdesign', gh: 'Tencent/tdesign', branch: 'main', probes: ['docs'], ext: /\.md$/, limit: 30 },
  { id: 'element', gh: 'element-plus/element-plus', branch: 'main', probes: ['docs/en-US/component', 'docs'], ext: /\.md$/, limit: 25 },
  { id: 'semi', gh: 'DouyinFE/semi-design', branch: 'main', probes: ['docs'], ext: /\.md$/, limit: 25 },
  { id: 'mantine', gh: 'mantinedev/mantine', branch: 'master', probes: ['docs'], ext: /\.(md|mdx)$/, limit: 25 },
];

const results = [];
for (const lib of LIBS) {
  process.stdout.write('[' + lib.id + '] ');
  let tree = null;
  try {
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(30000) });
    if (!r.ok) { console.log('❌ 树获取 HTTP ' + r.status); results.push({ id: lib.id, ok: false, err: 'tree ' + r.status }); continue; }
    tree = await r.json();
  } catch (e) { console.log('❌ 树获取 ' + e.message); results.push({ id: lib.id, ok: false, err: e.message }); continue; }

  // 展平文件树
  const files = [];
  const walk = node => { for (const f of (node.files || [])) { if (f.type === 'directory') walk(f); else files.push(f.name.startsWith('/') ? f.name : '/' + f.name); } };
  walk(tree);

  // 按 probes 找文档文件
  let targets = [];
  for (const probe of lib.probes) {
    targets = files.filter(f => f.includes('/' + probe + '/') && lib.ext.test(f));
    if (targets.length) break;
  }
  if (!targets.length) {
    console.log('⚠ 未定位文档目录（树文件 ' + files.length + '）');
    results.push({ id: lib.id, ok: false, err: '未定位', hint: files.filter(f => /doc/i.test(f)).slice(0, 5) });
    continue;
  }
  targets = targets.slice(0, lib.limit);
  const out = path.join(base, lib.id);
  fs.mkdirSync(out, { recursive: true });
  let ok = 0;
  for (const f of targets) {
    try {
      const r = await fetch('https://cdn.jsdelivr.net/gh/' + lib.gh + '@' + lib.branch + f, { signal: AbortSignal.timeout(20000) });
      if (!r.ok) continue;
      const rel = f.split('/').pop();
      fs.writeFileSync(path.join(out, rel), await r.text());
      ok++;
    } catch (e) { /* 单文件失败跳过 */ }
  }
  console.log('✅ ' + ok + '/' + targets.length + ' → data/component-styles/' + lib.id + '/');
  results.push({ id: lib.id, ok: ok > 0, count: ok });
}

fs.writeFileSync(path.join(base, '_capture-log.json'), JSON.stringify(results, null, 1));
console.log('\n=== 采集汇总 ===');
results.forEach(r => console.log('  ' + r.id + ': ' + (r.ok ? '✅ ' + (r.count || '') : '❌ ' + (r.err || ''))));
