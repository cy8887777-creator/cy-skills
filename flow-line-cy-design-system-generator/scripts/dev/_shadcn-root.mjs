import fs from 'node:fs';
const H = { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github+json' };
const r = await fetch('https://api.github.com/repos/shadcn-ui/ui/contents', { headers: H, signal: AbortSignal.timeout(20000) });
console.log('HTTP', r.status);
if (r.ok) {
  const items = await r.json();
  console.log(items.map(x => (x.type === 'dir' ? '📁' : '📄') + x.name).join('  ').slice(0, 400));
} else {
  const j = await r.json().catch(() => ({}));
  console.log('响应:', JSON.stringify(j).slice(0, 200));
}
