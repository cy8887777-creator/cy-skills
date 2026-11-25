#!/usr/bin/env node
// fetch-design-mds.mjs —— 采集 VoltAgent/awesome-design-md（MIT）各品牌 DESIGN.md 到 data/design-mds/
// 来源：https://github.com/VoltAgent/awesome-design-md · 经 jsDelivr 树发现 + CDN 下载
// 用法: node fetch-design-mds.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const REPO = 'VoltAgent/awesome-design-md';
const BRANCH = 'main';
const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const outDir = path.join(skillRoot, 'data', 'design-mds');

const CDN_TREE = `https://data.jsdelivr.com/v1/packages/gh/${REPO}@${BRANCH}?structure=flat`;
const CDN_RAW = (p) => `https://cdn.jsdelivr.net/gh/${REPO}@${BRANCH}${p}`;
const GH_RAW = (p) => `https://raw.githubusercontent.com/${REPO}/${BRANCH}${p}`;
const GH_API = (p) => `https://api.github.com/repos/${REPO}/contents${p}?ref=${BRANCH}`;
// 三通道：jsDelivr → raw.githubusercontent → GitHub Contents API（base64）
async function fetchText(url) { try { const r = await fetch(url); return r.ok ? await r.text() : null; } catch (e) { return null; } }
async function getText(repoPath, tries = 4) {
  for (let i = 0; i < tries; i++) {
    if (i % 3 === 0) { const t = await fetchText(CDN_RAW(repoPath)); if (t && t.length > 500) return t; }
    else if (i % 3 === 1) { const t = await fetchText(GH_RAW(repoPath)); if (t && t.length > 500) return t; }
    else {
      try {
        const r = await fetch(GH_API(repoPath), { headers: { 'User-Agent': 'design-system-generator' } });
        if (r.ok) {
          const j = await r.json();
          if (j.content && j.encoding === 'base64') {
            const t = Buffer.from(j.content, 'base64').toString('utf8');
            if (t.length > 500) return t;
          }
        }
      } catch (e) { /* retry */ }
    }
    await new Promise(r => setTimeout(r, 1000 * (i + 1)));
  }
  return null;
}

async function getJson(url, tries = 2) {
  for (let i = 0; i < tries; i++) {
    try { const r = await fetch(url); if (r.ok) return await r.json(); } catch (e) { /* retry */ }
    await new Promise(r => setTimeout(r, 800));
  }
  throw new Error('tree fetch failed: ' + url);
}

// 品牌中文名与分组
const BRANDS = {
  'airbnb': ['爱彼迎', '消费生活'], 'apple': ['苹果', '科技巨头'], 'bmw': ['宝马', '出行汽车'], 'cal': ['Cal.com', '效率工具'],
  'claude': ['Claude', 'AI 产品'], 'coinbase': ['Coinbase', '金融支付'], 'cursor': ['Cursor', 'AI 产品'], 'figma': ['Figma', '设计创作'],
  'ferrari': ['法拉利', '出行汽车'], 'lamborghini': ['兰博基尼', '出行汽车'], 'renault': ['雷诺', '出行汽车'], 'ibm': ['IBM', '科技巨头'],
  'linear.app': ['Linear', '效率工具'], 'notion': ['Notion', '效率工具'], 'pinterest': ['Pinterest', '消费生活'], 'raycast': ['Raycast', '效率工具'],
  'spacex': ['SpaceX', '科技巨头'], 'spotify': ['Spotify', '消费生活'], 'stripe': ['Stripe', '金融支付'], 'tesla': ['特斯拉', '出行汽车'],
  'uber': ['Uber', '出行汽车'], 'vercel': ['Vercel', '开发工具'], 'x.ai': ['xAI', 'AI 产品'], 'zapier': ['Zapier', '效率工具'],
  'nvidia': ['英伟达', '科技巨头'], 'elevenlabs': ['ElevenLabs', 'AI 产品'], 'mistral.ai': ['Mistral AI', 'AI 产品'], 'minimax': ['MiniMax', 'AI 产品'],
  'together.ai': ['Together AI', 'AI 产品'], 'cohere': ['Cohere', 'AI 产品'], 'ollama': ['Ollama', 'AI 产品'], 'runwayml': ['Runway', 'AI 产品'],
  'composio': ['Composio', '开发工具'], 'clickhouse': ['ClickHouse', '开发工具'], 'mongodb': ['MongoDB', '开发工具'], 'hashicorp': ['HashiCorp', '开发工具'],
  'supabase': ['Supabase', '开发工具'], 'expo': ['Expo', '开发工具'], 'posthog': ['PostHog', '开发工具'], 'sentry': ['Sentry', '开发工具'],
  'replicate': ['Replicate', '开发工具'], 'opencode.ai': ['OpenCode', '开发工具'], 'voltagent': ['VoltAgent', '开发工具'], 'mintlify': ['Mintlify', '开发工具'],
  'airtable': ['Airtable', '效率工具'], 'intercom': ['Intercom', '效率工具'], 'miro': ['Miro', '设计创作'], 'framer': ['Framer', '设计创作'],
  'webflow': ['Webflow', '设计创作'], 'clay': ['Clay', '效率工具'], 'sanity': ['Sanity', '开发工具'], 'resend': ['Resend', '开发工具'],
  'revolut': ['Revolut', '金融支付'], 'kraken': ['Kraken', '金融支付'], 'wise': ['Wise', '金融支付'], 'lovable': ['Lovable', 'AI 产品'],
  'warp': ['Warp', '开发工具'], 'superhuman': ['Superhuman', '效率工具'],
};
const GROUP_ORDER = ['AI 产品', '开发工具', '设计创作', '效率工具', '金融支付', '出行汽车', '科技巨头', '消费生活'];

async function main() {
  fs.mkdirSync(outDir, { recursive: true });
  const tree = await getJson(CDN_TREE);
  const designFiles = tree.files.filter(f => /^\/design-md\/[^/]+\/DESIGN\.md$/.test(f.name));
  console.log('发现 DESIGN.md: ' + designFiles.length + ' 个');
  let ok = 0, skip = 0, fail = [];
  const queue = designFiles.filter(f => {
    const brand = f.name.split('/')[2];
    const dest = path.join(outDir, brand, 'DESIGN.md');
    if (fs.existsSync(dest) && fs.statSync(dest).size > 500) { skip++; return false; }
    return true;
  });
  console.log('待下载: ' + queue.length + ' 个（已存在跳过 ' + skip + ' 个）');
  async function worker() {
    while (queue.length) {
      const f = queue.shift();
      const brand = f.name.split('/')[2];
      const text = await getText(f.name);
      if (text && text.length > 500) {
        const dir = path.join(outDir, brand);
        fs.mkdirSync(dir, { recursive: true });
        fs.writeFileSync(path.join(dir, 'DESIGN.md'), text);
        ok++;
      } else fail.push(brand);
      await new Promise(r => setTimeout(r, 250));
    }
  }
  await Promise.all(Array.from({ length: 3 }, worker));
  console.log(`下载完成: 成功 ${ok} / 失败 ${fail.length}${fail.length ? ' → ' + fail.join(', ') : ''}`);

  // 汇总 _meta.md
  const brands = fs.readdirSync(outDir).filter(d => fs.statSync(path.join(outDir, d)).isDirectory());
  const lines = [
    '# 品牌设计语言快照（awesome-design-md）', '',
    `- 来源：https://github.com/VoltAgent/awesome-design-md （MIT License）`,
    `- 内容：${brands.length} 个知名品牌的设计系统分析文档（DESIGN.md，供 AI 消费）`,
    `- 抓取日期：${new Date().toISOString().slice(0, 10)} · 通道：jsDelivr CDN`,
    '', '| 品牌 | 分组 | 大小 |', '|---|---|---|',
  ];
  for (const b of brands.sort()) {
    const size = fs.statSync(path.join(outDir, b, 'DESIGN.md')).size;
    lines.push(`| ${b}（${(BRANDS[b] || ['', ''])[0] || b}） | ${(BRANDS[b] || ['', '其他'])[1] || '其他'} | ${(size / 1024).toFixed(1)}KB |`);
  }
  fs.writeFileSync(path.join(outDir, '_meta.md'), lines.join('\n'));
  fs.writeFileSync(path.join(outDir, '_meta.json'), JSON.stringify({ source: 'https://github.com/VoltAgent/awesome-design-md', license: 'MIT', date: new Date().toISOString().slice(0, 10), brands: Object.fromEntries(brands.map(b => [b, { zh: (BRANDS[b] || [b, '其他'])[0], group: (BRANDS[b] || [b, '其他'])[1] || '其他' }])), groups: GROUP_ORDER }, null, 2));
  console.log('汇总: _meta.md + _meta.json · 共 ' + brands.length + ' 个品牌');
}
main().catch(e => { console.error('失败: ' + e.message); process.exit(1); });
