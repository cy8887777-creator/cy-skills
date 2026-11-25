const LIBS = [
  { id: 'shadcn', gh: 'shadcn-ui/ui', branch: 'main' },
  { id: 'daisyui', gh: 'saadeghi/daisyui', branch: 'master' },
  { id: 'antd', gh: 'ant-design/ant-design', branch: 'master' },
  { id: 'vant', gh: 'youzan/vant', branch: 'main' },
  { id: 'element', gh: 'element-plus/element-plus', branch: 'main' },
  { id: 'mantine', gh: 'mantinedev/mantine', branch: 'master' },
];
for (const lib of LIBS) {
  process.stdout.write('[' + lib.id + '] ');
  try {
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(45000) });
    const tree = await r.json();
    const files = [];
    const walk = (node, prefix) => { for (const f of (node.files || [])) { const full = prefix + '/' + f.name; if (f.type === 'directory') walk(f, full); else files.push(full); } };
    walk(tree, '');
    const docish = files.filter(f => /\/(docs?|content|spec)\//i.test(f) && /\.(md|mdx)$/.test(f));
    console.log('文件 ' + files.length + ' · md 文档路径样例:');
    docish.slice(0, 8).forEach(x => console.log('   ', x.slice(0, 120)));
    if (!docish.length) console.log('    （无 md 文档——html/doc 样例）:', files.filter(f => /doc/i.test(f)).slice(0, 4).join(' | ').slice(0, 150));
  } catch (e) { console.log('❌ ' + e.message); }
}
