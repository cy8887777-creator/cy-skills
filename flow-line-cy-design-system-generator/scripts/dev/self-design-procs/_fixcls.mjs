import fs from 'node:fs';
const p = '_compose.mjs';
let s = fs.readFileSync(p, 'utf8');

// 1) 删除自带 CSS/JS 常量（export-clean 模板已内置全套 case 样式与复制函数）
s = s.replace(/const CSS = `[\s\S]*?`;\n/, '');

// 2) ds* 自造类 → case 原生类名（长键优先）
const map = [
  ['dsspacelo', 'space-ruler'], ['dsspacerow', 'space-row'],
  ['dstyperow', 'type-row'], ['dstmeta', 'meta'],
  ['dsswb', 'swatch'], ['dssw', 'swatches'],
  ['dsstage', 'stage-lbl'], ['dscomp', 'comp-stage'],
  ['dstag.ok', 'tagchip ok'], ['dstag.warn', 'tagchip warn'], ['dstag.err', 'tagchip err'], ['dstag', 'tagchip'],
  ['dsrb', 'radius-box'], ['dssh', 'shadow-card'], ['dsicon', 'icon-cell'],
  ['dsgroup', 'sw-group'], ['dsrole', 'role-badge'],
  ['dsblk', 'block'], ['dslab', 'spec-label'], ['dsplain', 'plain'],
  ['dsnote', 'note'], ['dsCopy', 'copyHex'],
];
for (const [a, b] of map) s = s.split(a).join(b);

// 3) ov.values = CSS + ... → ov.values = ...（CSS 常量已删）
s = s.replace("ov.values = CSS\n  + ", "ov.values = ");

fs.writeFileSync(p, s);
console.log('类名对齐 case 原生词汇表 · CSS 常量已移除（模板供样式）');
