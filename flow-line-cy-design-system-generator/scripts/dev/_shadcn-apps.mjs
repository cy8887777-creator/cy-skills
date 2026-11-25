import fs from 'node:fs';
const H = { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github+json' };
async function list(p) {
  const r = await fetch('https://api.github.com/repos/shadcn-ui/ui/contents' + p, { headers: H, signal: AbortSignal.timeout(20000) });
  if (!r.ok) { console.log('HTTP', r.status, p); return []; }
  return r.json();
}
const apps = await list('/apps');
console.log('apps/:', apps.map(x => (x.type === 'dir' ? '📁' : '') + x.name).join('  '));
for (const a of apps.filter(x => x.type === 'dir')) {
  try {
    const sub = await list('/apps/' + a.name + '/contents');
    const interesting = sub.filter(x => /content|docs/i.test(x.name));
    console.log('  apps/' + a.name + ':', sub.map(x => (x.type === 'dir' ? '📁' : '') + x.name).join('  ').slice(0, 150));
    for (const it of interesting) {
      const deep = await list('/apps/' + a.name + '/contents/' + it.name);
      const docDirs = deep.filter(x => x.type === 'dir' && /component/i.test(x.name));
      if (docDirs.length) console.log('    ↳ ' + it.name + '/:', docDirs.map(x => x.name).join(','));
    }
  } catch (e) { console.log('  ' + a.name + ' 跳过:', e.message); }
}
