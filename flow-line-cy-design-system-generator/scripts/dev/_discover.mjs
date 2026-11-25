import fs from 'node:fs';
const H = { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github+json' };
async function list(dir) {
  const r = await fetch('https://api.github.com/repos/' + dir, { headers: H, signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
for (const repo of ['repos/shadcn-ui/ui/contents', 'repos/saadeghi/daisyui/contents']) {
  console.log('===', repo, '===');
  try {
    const items = await list(repo);
    console.log(items.map(x => (x.type === 'dir' ? '📁' : '📄') + x.name).join('  ').slice(0, 300));
  } catch (e) { console.log('失败:', e.message); }
}
