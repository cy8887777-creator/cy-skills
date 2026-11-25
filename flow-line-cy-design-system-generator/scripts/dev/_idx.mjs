import fs from 'node:fs';
const f = 'C:/Users/admin/.claude/skills/design-system-generator/SKILL.md';
let s = fs.readFileSync(f, 'utf8');
// 数据表加 component-styles 行
const row = '| data/component-styles/ | **组件风格库清单 INDEX**（32 库，微信/移动/PC/非大厂分组，官方链接待实测）+ 运行时快照位 | 第四步组件风格的风格基调来源；INDEX 注册于 2026-10-22 |';
const anchor = '| templates/sample-page-brief.md | 样品页子代理任务书模板（3 版诠释策略 + 回流格式） | 本技能 |';
if (s.includes(anchor) && !s.includes('data/component-styles/')) {
  s = s.replace(anchor, row + '\n' + anchor);
  console.log('数据表已加 component-styles 行');
}
// 第四步行：候选来源改为 INDEX
const oldSrc = '| **第四步 组件风格** | 核心组件族形态：按钮族 → 标签族 → 卡片族 → 输入族 → 导航/底栏（每组当前令牌下 2~3 变体）；次级组件（徽标/空态/分割线/头像）从已选派生过目 | 已锁令牌 + uupm 组件模式 | 分组变体卡（真渲染） |';
const newSrc = '| **第四步 组件风格** | 核心组件族形态：按钮族 → 标签族 → 卡片族 → 输入族 → 导航/底栏（每组当前令牌下 2~3 变体）；次级组件（徽标/空态/分割线/头像）从已选派生过目；另加 **AI 生成 2~3 张**【AI 生成】 | **风格基调 = data/component-styles/INDEX.md 组件风格库清单**（按端向选 6~8 库，运行时抓官方文档，实测可达）+ 已锁令牌派生 | 风格卡（该库风格的核心组件组合样 × 我们的令牌）+ AI 卡（标【AI 生成】） |';
if (s.includes(oldSrc)) { s = s.replace(oldSrc, newSrc); console.log('第四步行已更新'); }
else console.log('第四步行未精确匹配——检查');
fs.writeFileSync(f, s);
