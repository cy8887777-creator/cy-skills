import fs from 'node:fs';
import path from 'node:path';
const H = { 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/vnd.github+json' };
const base = 'C:/Users/admin/.claude/skills/design-system-generator/data/component-styles';
fs.mkdirSync(base, { recursive: true });

async function list(dir) {
  const r = await fetch('https://api.github.com/repos/' + dir, { headers: H, signal: AbortSignal.timeout(20000) });
  if (!r.ok) throw new Error('HTTP ' + r.status);
  return r.json();
}
async function blob(url) {
  const r = await fetch(url, { headers: H, signal: AbortSignal.timeout(20000) });
  const j = await r.json();
  return Buffer.from(j.content, 'base64').toString('utf8');
}
async function grab(repoDir, outSub, filter, limit) {
  const items = await list(repoDir);
  fs.mkdirSync(path.join(base, outSub), { recursive: true });
  const targets = items.filter(x => x.type === 'file' && filter(x.name)).slice(0, limit);
  let ok = 0;
  for (const t of targets) {
    try {
      const c = await blob(t.git_url);
      fs.writeFileSync(path.join(base, outSub, t.name), c);
      ok++;
      console.log('  ✅', t.name, '(' + Math.round(t.size / 1024) + 'KB)');
    } catch (e) { console.log('  ❌', t.name, e.message); }
  }
  console.log('  子计:', ok + '/' + targets.length);
}

console.log('[1] shadcn/ui · components 文档');
try { await grab('repos/shadcn-ui/ui/contents/apps/www/content/docs/components', 'shadcn', n => /\.(md|mdx)$/.test(n), 30); }
catch (e) { console.log('  失败:', e.message); }

console.log('[2] daisyUI · 结构探查');
try {
  const root = await list('repos/saadeghi/daisyui/contents');
  console.log('  根目录:', root.map(x => x.name).join(', ').slice(0, 200));
  const docsDir = root.find(x => x.name === 'content' || x.name === 'docs');
  if (docsDir) {
    const sub = await list('repos/saadeghi/daisyui/contents/' + docsDir.name);
    console.log('  ' + docsDir.name + '/:', sub.slice(0, 12).map(x => x.name).join(', ').slice(0, 180));
  }
} catch (e) { console.log('  失败:', e.message); }
