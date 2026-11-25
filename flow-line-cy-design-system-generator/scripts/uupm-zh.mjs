#!/usr/bin/env node
// uupm-zh.mjs —— uupm 参考数据中文化沉淀工具
// 读 data/uupm/*.csv（英文原版，保留备查）→ 翻译介绍性内容 → 写 data/uupm/zh/*.csv（中文版，供渲染与 AI 消费）
// 列名（schema）保留英文不动；只翻译单元格内容。将来 uupm 数据更新后重跑本脚本即可再沉淀。
// 用法: node uupm-zh.mjs
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

// 英→中高频词映射（覆盖 uupm 快照高频介绍词；未命中词保留原文）
const GLOSSARY = {
  'saas': 'SaaS', 'micro': '轻量', 'general': '通用', 'commerce': '电商', 'ecommerce': '电商', 'luxury': '奢侈品', 'finance': '金融', 'financial': '金融', 'fintech': '金融科技', 'crypto': '加密货币', 'dashboard': '数据看板', 'analytics': '分析', 'healthcare': '医疗健康', 'health': '健康', 'education': '教育', 'educational': '教育', 'app': '应用', 'gaming': '游戏', 'government': '政务', 'public': '公共', 'service': '服务', 'services': '服务', 'portfolio': '作品集', 'personal': '个人', 'creative': '创意', 'agency': '机构', 'b2b': 'B2B', 'b2c': 'B2C', 'startup': '创业', 'startups': '创业者', 'corporate': '企业', 'business': '商业', 'enterprise': '企业级', 'travel': '旅行', 'restaurant': '餐饮', 'real': '房产', 'estate': '地产', 'nonprofit': '非营利', 'media': '媒体', 'news': '新闻', 'blog': '博客', 'music': '音乐', 'event': '活动', 'fitness': '健身', 'wellness': '身心健康', 'fashion': '时尚', 'beauty': '美妆', 'spa': '美容', 'wedding': '婚庆', 'photography': '摄影', 'food': '食品', 'coffee': '咖啡', 'supply': '供应链', 'logistics': '物流', 'insurance': '保险', 'legal': '法律', 'consulting': '咨询', 'developer': '开发者', 'api': 'API', 'kids': '儿童', 'pet': '宠物', 'sports': '体育', 'career': '招聘', 'job': '职位', 'dating': '社交', 'social': '社交', 'community': '社区',
  'minimal': '极简', 'minimalism': '极简主义', 'swiss': '瑞士风', 'clean': '干净', 'simple': '简洁', 'spacious': '留白', 'functional': '功能导向', 'white': '白', 'space': '留白', 'high': '高', 'contrast': '对比', 'geometric': '几何感', 'sans': '无衬线', 'serif': '衬线', 'display': '展示型', 'mono': '等宽', 'elegant': '优雅', 'sophisticated': '精致', 'timeless': '经典', 'premium': '高端', 'editorial': '杂志感', 'classic': '经典', 'modern': '现代', 'professional': '专业', 'friendly': '亲切', 'approachable': '亲和', 'playful': '俏皮', 'fun': '有趣', 'warm': '温暖', 'warmth': '温度', 'bold': '大胆', 'bright': '明亮', 'vibrant': '鲜活', 'energetic': '有活力', 'dark': '深色', 'moody': '氛围感', 'futuristic': '未来感', 'innovative': '创新', 'tech': '科技', 'trust': '信任', 'trustworthy': '可信赖', 'reliable': '可靠', 'calm': '平静', 'soft': '柔和', 'rounded': '圆润', 'sharp': '锐利', 'luxurious': '奢华', 'artistic': '艺术', 'freedom': '自由', 'interpretation': '诠释', 'retro': '复古', 'vintage': '怀旧', 'brutalist': '粗野主义', 'glassmorphism': '玻璃拟态', 'glass': '玻璃', 'transparency': '透明', 'transparencies': '透明', 'neumorphism': '新拟物', 'embossed': '浮雕', 'debos': '压印', 'frosted': '磨砂', 'gradient': '渐变', 'gradients': '渐变', 'glow': '发光', 'neon': '霓虹', 'cyberpunk': '赛博朋克', 'flat': '扁平', 'skeuomorphic': '拟物', 'monochrome': '单色', 'monochromatic': '单色系', 'pastel': '粉彩', 'muted': '低饱和', 'neutral': '中性', 'earthy': '大地色', 'natural': '自然', 'organic': '有机感', 'asymmetric': '不对称', 'overlapping': '叠压', 'layered': '分层', 'immersive': '沉浸', 'interactive': '互动', 'storytelling': '叙事', 'narrative': '叙事', 'scroll': '滚动', 'dynamic': '动态', 'adaptive': '自适应', 'smart': '智能', 'personalization': '个性化', 'recommendation': '推荐', 'anticipation': '期待感', 'urgency': '紧迫感', 'authority': '权威感', 'hierarchy': '层级', 'clear': '清晰', 'direct': '直接', 'conversion': '转化', 'focused': '聚焦',
  'blue': '蓝', 'navy': '藏青', 'teal': '青绿', 'cyan': '青', 'green': '绿', 'mint': '薄荷', 'yellow': '黄', 'gold': '金', 'golden': '金色', 'orange': '橙', 'red': '红', 'pink': '粉', 'purple': '紫', 'lavender': '薰衣草紫', 'indigo': '靛蓝', 'violet': '紫罗兰', 'brown': '棕', 'beige': '米色', 'grey': '灰', 'gray': '灰', 'black': '黑', 'accent': '强调色', 'primary': '主色', 'secondary': '辅色', 'palette': '色板', 'colors': '配色', 'color': '配色', 'cool': '冷调', 'hot': '热调', 'distinct': '区分', 'opacity': '不透明度', 'fill': '填充', 'outline': '描边', 'shadow': '阴影', 'grain': '颗粒', 'texture': '质感',
  'hero': '首屏', 'button': '按钮', 'buttons': '按钮', 'feature': '特性', 'features': '特性', 'testimonial': '证言', 'testimonials': '证言', 'pricing': '定价', 'video': '视频', 'form': '表单', 'lead': '获客', 'magnet': '磁吸', 'signup': '注册', 'sign-up': '注册', 'email': '邮件', 'capture': '收集', 'footer': '页脚', 'nav': '导航', 'navigation': '导航', 'menu': '菜单', 'card': '卡片', 'cards': '卡片', 'table': '表格', 'compare': '对比', 'comparison': '对比', 'versus': '对比', 'sticky': '吸顶', 'bottom': '底部', 'center': '居中', 'right': '右侧', 'left': '左侧', 'above': '上方', 'below': '下方', 'overlay': '叠层', 'background': '背景', 'headline': '大标题', 'statement': '宣言', 'prop': '价值点', 'value': '价值', 'benefit': '收益', 'benefits': '收益点', 'bullets': '要点', 'solution': '方案', 'problem': '问题', 'overview': '总览', 'demo': '演示', 'product': '产品', 'mockup': '样机', 'showcase': '陈列', 'social-proof': '社会证明', 'reviews': '评价', 'post': '后置', 'section': '区块', 'order': '顺序', 'single-column': '单列', 'wizard': '向导', 'onboarding': '新手引导', 'steps': '分步', 'step': '步骤', 'progression': '递进', 'tier': '档位', 'tiers': '档位', 'plans': '方案', 'subscribe': '订阅', 'waitlist': '候补', 'coming-soon': '即将上线', 'launch': '发布', 'early': '抢先', 'access': '访问', 'notify': '提醒', 'countdown': '倒计时', 'teaser': '预告', 'preview': '预览', 'chapter': '章节', 'climax': '高潮', 'chaptered': '分章', 'reveal': '渐显', 'pattern': '模式', 'carousel': '轮播', 'logo': '标志', 'logos': '标志墙', 'grid': '网格', 'gallery': '画廊', 'fullscreen': '全屏', 'split': '分栏', 'centered': '居中',
  'line': '折线图', 'area': '面积图', 'smooth': '平滑', 'bar': '柱状图', 'column': '柱状图', 'grouped': '分组', 'stacked': '堆叠', 'pie': '饼图', 'donut': '环形图', 'scatter': '散点图', 'plot': '图', 'bubble': '气泡图', 'heat': '热力', 'heat-map': '热力图', 'heatmap': '热力图', 'choropleth': '填色地图', 'funnel': '漏斗图', 'sankey': '桑基图', 'gauge': '仪表盘', 'bullet': '子弹图', 'radar': '雷达图', 'spider': '蜘蛛图', 'treemap': '矩形树图', 'waterfall': '瀑布图', 'candlestick': 'K线图', 'ohlc': 'K线', 'kpi': '指标卡', 'number': '大数字', 'map': '地图', 'sunburst': '旭日图', 'icicle': '冰柱图', 'alluvial': '冲积图', 'chord': '弦图', 'ribbon': '缎带图', 'histogram': '直方图', 'box': '箱线图', 'violin': '小提琴图', 'timeline': '时间线', 'dial': '表盘', 'thermometer': '温度计', 'sparkline': '迷你线', 'big': '大号', 'chart': '图', 'charts': '图表', 'trend': '趋势', 'trends': '趋势', 'time-series': '时序', 'time-series-forecast': '时序预测', 'forecast': '预测', 'part-to-whole': '部分与整体', 'percentage': '占比', 'proportion': '比例', 'share': '份额', 'ranking': '排名', 'correlation': '相关性', 'distribution': '分布', 'relationship': '关系', 'intensity': '强度', 'density': '密度', 'matrix': '矩阵', 'geographic': '地理', 'geo': '地理', 'location': '位置', 'region': '区域', 'spatial': '空间', 'flow': '流向', 'flows': '流向', 'process': '流程', 'performance': '绩效', 'target': '目标', 'confidence': '置信', 'band': '带', 'anomaly': '异常', 'detection': '侦测', 'alert': '告警', 'alerts': '告警', 'hierarchical': '层级', 'nested': '嵌套', 'cumulative': '累计', 'changes': '变化', 'multi': '多', 'variable': '变量', 'stock': '股票', 'trading': '交易', 'increases': '上涨', 'decreases': '下跌', 'duration': '时长', 'schedule': '排期', 'gantt': '甘特',
  'and': '·', 'or': '/', 'with': '配', 'for': '适用', 'use': '用', 'used': '用于', 'best': '最佳', 'good': '适合', 'avoid': '避免', 'not': '不', 'data': '数据', 'visualization': '可视化', 'visual': '视觉', 'interactivity': '交互性', 'filtering': '筛选', 'sorting': '排序', 'hover': '悬停', 'tooltip': '提示', 'tooltips': '提示', 'labels': '标签', 'label': '标签', 'legend': '图例', 'axis': '坐标轴', 'series': '系列', 'multiple': '多', 'single': '单', 'per': '每', 'each': '各', 'when': '当', 'show': '展示', 'shows': '展示', 'large': '大', 'small': '小', 'first': '优先', 'slices': '扇区', 'useful': '适用', 'perfect': '适合', 'ideal': '理想', 'great': '适合', 'sites': '站点', 'site': '站点', 'website': '网站', 'websites': '网站', 'page': '页', 'pages': '页', 'content': '内容', 'projects': '项目', 'project': '项目', 'portfolios': '作品', 'tools': '工具', 'heavy': '重', 'complex': '复杂', 'quick': '快', 'read': '读', 'reading': '阅读', 'mobile': '移动', 'desktop': '桌面', 'minimal-single': '极简单列',
};
function zh(text) {
  return String(text ?? '').replace(/[A-Za-z][A-Za-z0-9&-]*/g, w => {
    const key = w.toLowerCase();
    if (/^(#\w+|\d+\w*|px|pt|rgb|rgba|hex|wt|stt)$/i.test(w)) return w;
    if (key === 'cta') return 'CTA';
    if (key === 'ai') return 'AI';
    if (key === 'faq') return 'FAQ';
    if (['b2b', 'b2c', 'saas', 'api', 'kpi', 'ohlc'].includes(key)) return GLOSSARY[key] || w;
    return Object.prototype.hasOwnProperty.call(GLOSSARY, key) ? GLOSSARY[key] : w;
  });
}
// 图表名专项：先剥 Chart/Maps 词尾再映射，避免「折线图 图」
const chartZh = t => zh(String(t ?? '').replace(/\bCharts?\b/g, '').replace(/\bMaps?\b/gi, '地图')).replace(/\s+/g, ' ').trim();

// 落地页 Pattern 名专项映射（干净中文名；未命中保留原文）
const PATTERN_ZH = {
  'Hero + Features + CTA': '首屏 + 特性组 + CTA',
  'Hero + Testimonials + CTA': '首屏 + 证言 + CTA',
  'Product Demo + Features': '产品演示 + 特性组',
  'Minimal Single Column': '极简单列',
  'Funnel (3-Step Conversion)': '三步转化漏斗',
  'Comparison Table + CTA': '对比表格 + CTA',
  'Lead Magnet + Form': '获客磁吸 + 表单',
  'Pricing Page + CTA': '定价页 + CTA',
  'Video-First Hero': '视频首屏',
  'Scroll-Triggered Storytelling': '滚动叙事',
  'AI Personalization Landing': 'AI 个性化落地页',
  'Waitlist/Coming Soon': '候补/即将上线',
};
const patternZh = t => PATTERN_ZH[String(t ?? '').trim()] || String(t ?? '');

// ---------- CSV 解析/序列化（引号内逗号安全） ----------
function parseCsv(text) {
  const rows = []; let row = [], cell = '', inQ = false;
  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    if (inQ) {
      if (ch === '"') { if (text[i + 1] === '"') { cell += '"'; i++; } else inQ = false; }
      else cell += ch;
    } else {
      if (ch === '"') inQ = true;
      else if (ch === ',') { row.push(cell); cell = ''; }
      else if (ch === '\n') { row.push(cell); cell = ''; rows.push(row); row = []; }
      else if (ch !== '\r') cell += ch;
    }
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows.filter(r => r.some(c => String(c).trim() !== ''));
}
const csvCell = v => { const s = String(v ?? ''); return /[",\n]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s; };
const toCsv = rows => rows.map(r => r.map(csvCell).join(',')).join('\n');

// ---------- 主流程 ----------
const skillRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const srcDir = path.join(skillRoot, 'data', 'uupm');
const outDir = path.join(srcDir, 'zh');
fs.mkdirSync(outDir, { recursive: true });
const FILES = ['colors.csv', 'typography.csv', 'styles.csv', 'charts.csv', 'landing.csv', 'products.csv', 'ux-guidelines.csv', 'prompts.csv', 'stack-html-tailwind.csv'];
// 不翻译的文件：ux-guidelines（Do/Don't 准则，破碎中文不可读，保留英文原文）、prompts（AI 提示词，必须纯英文可复制）、stack（技术栈已从素材页移除，原样沉淀备查）
const NO_TRANSLATE = new Set(['ux-guidelines.csv', 'prompts.csv', 'stack-html-tailwind.csv']);
// 内容列（全部列都翻；标题列用专项规则）
const TITLE_COLS = { 'charts.csv': ['Data Type'], 'landing.csv': ['Pattern Name'], 'typography.csv': ['Font Pairing Name'] };

for (const f of FILES) {
  const p = path.join(srcDir, f);
  if (!fs.existsSync(p)) { console.warn('跳过（不存在）: ' + f); continue; }
  const rows = parseCsv(fs.readFileSync(p, 'utf8'));
  if (NO_TRANSLATE.has(f)) {
    // ux-guidelines 的中文版由人工句级翻译维护（zh/ux-guidelines.zh.csv），这里只留英文备份，绝不覆盖
    const outName = f === 'ux-guidelines.csv' ? 'ux-guidelines.en.csv' : f;
    fs.writeFileSync(path.join(outDir, outName), toCsv(rows));
    console.log('原样沉淀（不翻译）: zh/' + outName + ' (' + (rows.length - 1) + ' 行)');
    continue;
  }
  const head = rows.shift().map(h => h.trim());
  const out = [head];
  for (const r of rows) {
    out.push(head.map((h, i) => {
      const cell = (r[i] ?? '').trim();
      if (!cell) return '';
      if (/^(No|STT|Google Fonts URL|CSS Import|Tailwind Config)$/i.test(h)) return cell; // 序号/URL/代码列不动
      if (/font/i.test(h)) return cell; // 字体名列（Font / Heading Font / Body Font）=专有名词，不翻——翻啦会污染 font-family
      if (/pairing/i.test(h)) return cell; // 搭配名含字体名，保留原文
      if ((TITLE_COLS[f] || []).includes(h)) {
        // 标题列：图表名/落地页 Pattern 用专项规则，其他过 zh
        if (f === 'charts.csv') return chartZh(cell);
        if (f === 'landing.csv') return patternZh(cell);
        return zh(cell);
      }
      if (f === 'charts.csv' && /chart|option/i.test(h)) return chartZh(cell);
      if (f === 'landing.csv' && /section/i.test(h)) return cell; // Section Order 保留原文，由渲染器按关键词归类画版式
      return zh(cell);
    }));
  }
  fs.writeFileSync(path.join(outDir, f), toCsv(out));
  console.log('已沉淀中文版: zh/' + f + ' (' + (out.length - 1) + ' 行)');
}
console.log('完成 —— 中文参考数据目录: ' + outDir);
