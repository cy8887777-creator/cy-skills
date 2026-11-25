import fs from 'node:fs';
const p = '_compose.mjs';
let s = fs.readFileSync(p, 'utf8');

// 36 个 block 按出现顺序的来源角色
const roles = [
  '实测 · 用户拍板', '实测 · 单选整卡',          // values
  '实测 · 画像布局归类', 'AI 补全 · 降级推导',    // layout
  '实测 · 画像基准', 'AI 补全 · 断点推导',        // density
  '引用 · 通用规则模板', '实测 · 自举沉淀',        // rules
  '实测 · 撞色策略拍板', '实测 · 锁值', '实测 · 锁值', '实测 + 张力已知', // color
  '实测 · 用户拍板', '实测 · 锁值字阶', '引用 · 通用', // type
  '引用 · 4pt 通用', 'AI 补全 · 静玻璃派生', '引用 · 通用', // spacing
  'AI 补全 · 基调派生', 'AI 补全 · 派生',         // radius
  'AI 补全 · 基调派生', 'AI 补全 · 派生',         // shadow
  'AI 补全 · 玻璃纪律推导', '引用 · 通用',        // motion
  '实测 · 用户逐族拍板', '实测 · 用户逐族拍板', 'AI 补全 · 派生', // component
  '实测 · 用户拍板', '实测 · 库实物', 'AI 补全 · 补位规则', // icon
  '实测 · 用户纠偏', '保留 · 策略卡',             // imagery
  '引用 · 通用模板', '实测 4 + 引用 13', '引用 · 红线', '引用 · 顺序' // bans
];
let i = 0;
s = s.replace(/blk\('([^']+)'/g, (m, label) => {
  const r = roles[i++] || '';
  return "blk('" + label + ' <span class="role-badge">' + r + '</span>' + "'";
});

// icon 章 PROMPT 母版块
const promptBlk = " + blk('PROMPT · 新图标生成提示词母版<span class=\"role-badge\">AI 兜底</span>', '<pre style=\"font-family:Consolas,monospace;font-size:12px;line-height:1.8;background:#23252B;color:#D8D9DD;padding:16px 20px;border-radius:8px;overflow-x:auto;white-space:pre-wrap;margin:0 0 12px\">线性图标 · Feather 语法 · stroke 2px / 24 网格 / 圆角端点(round cap+join) / currentColor 单色 / 无填充无渐变\\n主体: [图标语义] · 视觉隐喻: [具象动作物] · 构图: 居中满格留 2px 边距\\n禁: 多色 / 厚描边 / 拟物细节 / 文字内嵌\\n输出: 24×24 svg · 单 path 组 · 可内联</pre>')\n  ";
s = s.replace(" + blk('USAGE · 补位与生成'", promptBlk + "+ blk('USAGE · 补位与生成'");

fs.writeFileSync(p, s);
console.log('角色 badge 注入:', i, '处 · PROMPT 母版:', s.includes('PROMPT · 新图标生成提示词母版') ? '✓' : '✗');
