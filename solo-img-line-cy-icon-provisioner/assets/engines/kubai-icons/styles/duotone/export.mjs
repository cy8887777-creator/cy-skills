#!/usr/bin/env node
// Copyright (c) 2026 Kubai087. Licensed under the Kubai Icons License; see LICENSE.
// Exports two-tone solid icons as self-contained SVG files, one <name>.svg per icon.
//
//   node export.mjs [--only name,name] [--size 24] [--primary #hex] [--secondary #hex]
//                   [--icons file] [--out dir]
//
// --primary changes the brand colour; the secondary follows it (the primary at 40% over white)
// unless --secondary sets it too. --size sets width and height in pixels (the viewBox stays
// 0 0 16 16). Files go to export/ next to this script unless --out says otherwise.
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { render, secondary, TONES } from './kit.mjs';

const here = path.dirname(fileURLToPath(import.meta.url));
const args = process.argv.slice(2);
const opt = (name, fallback) => { const i = args.indexOf(name); return i >= 0 ? args[i + 1] : fallback; };
const { ICONS } = await import(pathToFileURL(path.resolve(opt('--icons', path.join(here, 'icons.mjs')))).href);
const only = (opt('--only') || '').split(',').map((s) => s.trim()).filter(Boolean);
for (const n of only) if (!ICONS[n]) throw new Error(`No icon named ${n}.`);
const a = opt('--primary', TONES.a);
const b = opt('--secondary', opt('--primary') ? secondary(a) : TONES.b);
const size = Number(opt('--size', 24));
const out = path.resolve(opt('--out', path.join(here, 'export')));

fs.mkdirSync(out, { recursive: true });
const names = only.length ? only : Object.keys(ICONS);
for (const name of names) fs.writeFileSync(path.join(out, `${name}.svg`), render(ICONS[name], { size, a, b, id: name }) + '\n');
console.log(`${names.length} icon(s) in ${a} / ${b} → ${path.relative(process.cwd(), out) || '.'}`);
