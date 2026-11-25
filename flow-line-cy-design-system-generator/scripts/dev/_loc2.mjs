import fs from 'node:fs';
const f = 'C:/Users/admin/.claude/skills/design-system-generator/SKILL.md';
const c = fs.readFileSync(f, 'utf8');
const lines = c.split('\n');
lines.forEach((line, i) => {
  if (/data\/|scripts\/|references\/|templates\//.test(line) && line.includes('|')) console.log('L' + (i + 1) + ': ' + line.trim().slice(0, 140));
});
