#!/usr/bin/env node
// verify_chain.mjs —— 决策链质量门禁（自举实测教训全量编译为断言）
// 用法: node verify_chain.mjs <chain.json> <概览HTML产物(可选,design-system.html)>
// 退出码: 0=全过 · 1=有 FAIL。落锤流程：更新链 → 本脚本 PASS 才算落锤完成。
// 断言来源：①约束回读失忆(组件覆盖度) ②shape 契约(renderTokenCard) ③交付即更新
// ④卡槽来源角色 ⑤复写方法论(品牌污染/原生类名) ⑥chapters.md 覆盖标准(≥20 组)
import fs from 'node:fs';

const [, , chainFile, specHtml] = process.argv;
if (!chainFile) { console.error('用法: node verify_chain.mjs <chain.json> [design-system.html]'); process.exit(1); }
const c = JSON.parse(fs.readFileSync(chainFile, 'utf8').replace(/^\uFEFF/, ''));
const step = id => (c.steps || []).find(x => x.id === id) || {};
const ov = c.overview || {};
const F = [];
const ok = (name, pass, detail) => { if (!pass) F.push(name + (detail ? ' —— ' + detail : '')); };

// ── A. shape 契约：direction 步候选必须 tokens 完整形态（renderTokenCard 专用） ──
const dir = step('direction');
const dirCands = dir.candidates || [];
if (dirCands.length) {
  ok('A1 direction 候选 shape', dirCands.every(x => x.tokens && x.tokens.colors && x.tokens.scale && x.tokens.fontHead),
    '存在缺 tokens.colors/scale/fontHead 的候选（会渲染为空白）');
  ok('A2 tokens.colors 完整 11 键', dirCands.every(x => x.tokens.colors && Object.keys(x.tokens.colors).length >= 11),
    '语义色 8 + 状态色 3 不足');
}

// ── B. 交付即更新：done 步不允许空 candidates（进行中卡变误导） ──
(c.steps || []).forEach(s => {
  if (s.status === 'done' && !(s.candidates || []).length && !s.chosen) {
    ok(`B done 步候选留档: ${s.id}`, false, 'done 且无 candidates 无 chosen——交付/决策未写回链');
  }
});

// ── C. 组件章覆盖度 ≥20 组（chapters.md 章 11 覆盖标准） ──
const comp = String(ov.component || '');
const stageCount = (comp.match(/comp-stage/g) || []).length;
ok('C1 组件章大卡 ≥20 组', (comp.match(/border-radius:16px/g) || []).length >= 20, `实际 ${(comp.match(/border-radius:16px/g) || []).length} 张大卡（规格书标准）`);
ok('C2 组件章声明覆盖 ≥20 组', /[2-9][0-9]\s*组|≥\s*20/.test(comp), '未见 ≥20 组覆盖声明');
ok('C3 组件实物用真控件', (comp.match(/<button/g) || []).length >= 20, `真 button 仅 ${(comp.match(/<button/g) || []).length} 个——装饰 span 演示不合格（实物即规格原则）`);
ok('C4 状态穷举', /default|pressed|disabled|禁用/.test(comp), '交互组件缺状态穷举（≥三态）');
ok('C5 来源分层徽章', /来源徽章|已提取|AI 补全/.test(comp), '组件大卡缺来源分层徽章');

// ── D. 必备卡槽（case 词汇表齐备性） ──
ok('D1 颜色章色板 ≥10', (String(ov.color || '').match(/swatch/g) || []).length >= 10, '点击复制色板墙不足');
ok('D2 字体章字阶行 ≥5', (String(ov.type || '').match(/type-row/g) || []).length >= 5, '字阶真渲染行不足');
ok('D3 图标章实物 ≥5', (String(ov.icon || '').match(/<svg/g) || []).length >= 5, '图标实物陈列不足');
ok('D4 图标章 PROMPT 母版', String(ov.icon || '').includes('PROMPT'), '缺新图标生成提示词母版');
ok('D5 来源角色标注 ≥30', (Object.values(ov).join('').match(/role-badge/g) || []).length >= 30,
  '卡槽来源角色（实测/AI 补全/引用）标注不足——禁 AI 补全值冒充实测');

// ── E. 逐章非空（14 章全填充） ──
const CH = ['values', 'layout', 'density', 'rules', 'color', 'type', 'spacing', 'radius', 'shadow', 'motion', 'component', 'icon', 'imagery', 'bans'];
CH.forEach(id => ok(`E 章 ${id} 非空`, String(ov[id] || '').replace(/<[^>]*>/g, '').trim().length >= 2, '空章'));

// ── F. case 形态（概览禁自造类前缀——只用 case 原生词汇表） ──
const badCls = Object.values(ov).join('').match(/class="(ds|my|xx)[a-z-]*"/g);
ok('F1 概览用 case 原生类名', !badCls, '发现自造类: ' + (badCls || []).slice(0, 3).join(','));

// ── G. 品牌污染（spec 产物 · case 品牌值零残留） ──
if (specHtml && fs.existsSync(specHtml)) {
  const w = fs.readFileSync(specHtml, 'utf8');
  const POLLUTION = ['#2196F3', '#0D96FB', '#067AFA', '跑腿', '示例设计系统', 'v2.0.0', 'blue-500'];
  const hits = POLLUTION.filter(k => w.includes(k));
  ok('G1 品牌污染零残留', !hits.length, 'case 值残留: ' + hits.join('·'));
  ok('G2 侧栏+hero+格纹', w.includes('sidebar') && w.includes('hero-meta') && w.includes('body::before'), 'case 形态骨架缺失');
}

if (F.length) {
  console.error(`[FAIL] ${F.length} 项:`);
  F.forEach(x => console.error('  ✗ ' + x));
  process.exit(1);
}
console.log('[PASS] 决策链门禁全过（shape/交付留档/覆盖度/卡槽/角色标注/14 章/case 形态' + (specHtml ? '/品牌污染' : '') + '）');
