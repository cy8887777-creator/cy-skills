import fs from 'node:fs';
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
    const r = await fetch('https://data.jsdelivr.com/v1/packages/gh/' + lib.gh + '@' + lib.branch, { signal: AbortSignal.timeout(30000) });
    const tree = await r.json();
    const files = [];
    const walk = node => { for (const f of (node.files || [])) { if (f.type === 'directory') walk(f); else files.push(f.name.startsWith('/') ? f.name : '/' + f.name); } };
    walk(tree);
    const docish = files.filter(f => /doc/i.test(f)).slice(0, 8);
    console.log('文件 ' + files.length + ' · doc 路径样例:');
    docish.forEach(x => console.log('   ', x.slice(0, 110)));
    if (!docish.length) console.log('    （无 doc 路径——样例前 5）:', files.slice(0, 5).join(' | ').slice(0, 160));
  } catch (e) { console.log('❌ ' + e.message); }
}
