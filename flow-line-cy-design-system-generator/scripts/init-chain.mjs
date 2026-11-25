#!/usr/bin/env node
// init-chain.mjs —— 新项目开链：生成规范决策链骨架（十步标准 shape）
// 为什么必须有这步：决策链骨架禁止手写 —— 手写会带来遗留字段（如旧 samplePage）、编号错乱、状态混乱。
// 用法: node init-chain.mjs <项目名> <输出chain.json路径> [第〇步画像副题]
// 画像完成后执行者把第〇步 candidates/chosen/status 补进链里（用编辑，不改其他步骤）。
import fs from 'node:fs';
import path from 'node:path';

const [, , project, outFile, profileSub] = process.argv;
if (!project || !outFile) {
  console.error('用法: node init-chain.mjs <项目名> <输出chain.json路径> [第〇步画像副题]');
  process.exit(1);
}

// 九段流程定稿：〇画像 → ①外部输入 → ②风格定义层 → ③设计令牌 → ④组件风格 → ⑤图片素材 → ⑥图标风格 → ⑦查漏 → ⑧样品页 → ⑨收尾
const STEPS = [
  ['profile', '0', '第〇步 原型画像', profileSub || '页面组件盘点 · 端向 · 业务域 · 约束'],
  ['external', '1', '第一步 外部输入', '用户提交内容逐条解析展示 · 多次提交多条'],
  ['concept', '2', '第二步 风格定义层', '风格库检索/自创 · 完整风格描述 · 单选整卡执行'],
  ['direction', '3', '第三步 设计令牌', '选定卡实现层 × 业务色锚拼装设计令牌 · 并排方向卡（组件形态不在此步）'],
  ['compstyle', '4', '第四步 组件风格', '先选基调库 · 再逐族规范过目（形态来自库，颜色用已锁令牌）'],
  ['imagery', '5', '第五步 图片素材', '生图 / 图包 / 占位 · 单张策略卡确认（先探测本地生图能力）'],
  ['icon', '6', '第六步 图标风格', '开源库样例 + 链接；特殊风格可生成'],
  ['gaps', '7', '第七步 查漏', '对照章节模板盘点缺口 —— 确保进样品页前信息齐'],
  ['samplepage', '8', '第八步 样品页', '代表页每页 3 版 · 不同子代理 · 看版定案 · 回流中间件'],
  ['finalize', '9', '第九步 收尾 · 章节成文与审阅', '回流后最终状态逐章成文 → 审阅修改 → 导出纯净版'],
];

const chain = {
  project,
  version: 1,
  profile: profileSub || '',
  current: 'profile',
  steps: STEPS.map(([id, no, title, sub], i) => ({
    id, no, title, sub,
    status: i === 0 ? 'now' : 'todo',
  })),
  auto: {},
  overview: {},
  history: [],
};
// 注意：chain 里没有 samplePage 字段 —— 样品页就是 steps 里的第八步，别再加独立字段。

fs.mkdirSync(path.dirname(path.resolve(outFile)), { recursive: true });
fs.writeFileSync(outFile, JSON.stringify(chain, null, 2));
console.log('决策链骨架已生成: ' + path.resolve(outFile));
console.log('步骤: ' + STEPS.map(s => s[1] + ' ' + s[2]).join(' → '));
