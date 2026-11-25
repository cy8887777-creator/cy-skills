import fs from 'node:fs';
const p = 'chain.json';
const c = JSON.parse(fs.readFileSync(p, 'utf8'));
const ov = c.overview;

// ═══ C1 · 辅助色严格 AA：#7C86A0(3.6:1) / #8A93A0(2.9:1) → #64748B(4.77:1) ═══
let n1 = 0;
const walk = o => { for (const k in o) { if (typeof o[k] === 'string') { if (o[k].includes('#7C86A0')) { n1 += o[k].split('#7C86A0').length - 1; o[k] = o[k].split('#7C86A0').join('#64748B'); } if (o[k].includes('#8A93A0')) { n1 += o[k].split('#8A93A0').length - 1; o[k] = o[k].split('#8A93A0').join('#64748B'); } } else if (o[k] && typeof o[k] === 'object') walk(o[k]); } };
walk(ov); walk(c.steps);
(c.steps.find(x => x.id === 'direction').candidates || []).forEach(x => { if (x.tokens && x.tokens.colors && x.tokens.colors.textSecondary === '#7C86A0') x.tokens.colors.textSecondary = '#64748B'; });
c.history.push({ step: 'direction', note: 'C1 辅助色严格 AA：text-secondary #7C86A0(3.6:1)/#8A93A0(2.9:1) → #64748B(4.77:1 对纸白) · 全链替换 · v1.1' });
c.version = '1.1';

// ═══ C2 · 组件章 28 组全量大卡 ═══
const badge = t => '<span style="margin-left:auto;font-size:10px;background:#4C6FFF;color:#fff;border-radius:4px;padding:2px 8px">' + t + '</span>';
const vhead = (name, spec) => '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:8px"><b style="font-size:13px">' + name + '</b><span style="font-size:11px;color:#64748B;font-family:Consolas,monospace">' + spec + '</span></div>';
const cell = (lbl, style, inner, ai) => '<div style="text-align:center;flex:1 1 0;min-width:max-content;max-width:100%"><div style="display:flex;align-items:center;justify-content:center;min-height:76px;background:#fff;border-radius:8px;margin:0 4px"><span style="' + style + '">' + inner + '</span></div><div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:2px"><span style="font-size:10px;background:#F6F7F9;color:#64748B;border-radius:4px;padding:2px 8px;white-space:nowrap">' + lbl + '</span>' + (ai ? '<span style="font-size:9px;color:#C77D1D;border:1px solid rgba(199,125,29,.45);border-radius:3px;padding:0 3px">AI 补全</span>' : '') + '<button class="css-copy" title="复制该实物根元素的 CSS" style="font-size:10px;border:1px solid #E2E6F2;background:#fff;color:#64748B;border-radius:4px;padding:2px 8px;cursor:pointer">⧉ 复制 CSS</button></div></div>';
const mega = (no, name, en, badgeTxt, body) => '<div style="border:1px solid #E2E6F2;border-radius:16px;overflow:hidden;background:#fff;margin:0 0 16px"><div style="padding:12px 18px;background:#F6F7F9;border-bottom:1px solid #E2E6F2;display:flex;align-items:center;gap:8px"><b style="font-size:15px">' + no + '. ' + name + '</b><span style="font-size:11px;color:#64748B">' + en + '</span>' + badge(badgeTxt) + '</div><div style="padding:6px 18px 16px">' + body + '</div></div>';
const vrow = '<div style="margin-top:12px;padding-top:12px;border-top:1px dashed #EEF1F4">';
const sgl = (name, spec, body) => vrow + vhead(name, spec) + '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:flex-end">' + body + '</div>';
const btnP = 'display:inline-block;padding:7px 18px;background:rgba(76,111,255,.88);color:#fff;font-size:14px;border-radius:8px;border:1px solid rgba(255,255,255,.38);box-shadow:0 4px 12px rgba(76,111,255,.35)';
const glassSig = 'display:inline-block;padding:4px 10px;background:rgba(255,255,255,.6);backdrop-filter:blur(6px);border:1px solid rgba(255,255,255,.8);border-radius:6px;font-size:12px';
const dot = cc => '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + cc + ';margin-right:5px;vertical-align:1px"></span>';
const cards = [];
const S = (no, name, en, bt, spec, style, inner) => cards.push(mega(String(no), name, en, bt, sgl(name, spec, cell('default', style, inner))));

cards.push(mega('1', '按钮组', 'Button', '工作台实测 · pressed/disabled 为 AI 补全',
  vrow + vhead('主按钮 · 玻璃化', 'h34 · r8 · rgba(76,111,255,.88) · 白描边 .38 · 彩影 0 4px 12px',
    cell('default', btnP, '主操作') + cell('pressed', btnP.replace('.88)', '.78)') + ';transform:scale(.96);filter:brightness(.96)', '主操作', 1) + cell('disabled', 'display:inline-block;padding:7px 18px;background:#F0F2F5;color:#B9C0CE;font-size:14px;border-radius:8px;border:none', '禁用态', 1))
  + vrow + vhead('次按钮 / 文字按钮', '白玻璃 .7 靛字靛细边 · 文字钮无底',
    cell('default', 'display:inline-block;padding:7px 18px;background:rgba(255,255,255,.7);color:#4C6FFF;font-size:14px;border-radius:8px;border:1px solid #4C6FFF', '次操作')
    + cell('default', 'display:inline-block;padding:7px 12px;color:#4C6FFF;font-size:14px', '文字按钮'))));
cards.push(mega('2', '输入框', 'Input', '工作台实测 · focus 为 AI 补全',
  vrow + vhead('默认 / 聚焦', 'h34 · 白玻璃 .75 · focus 靛边+光环 3px',
    cell('default', 'display:inline-block;width:190px;height:34px;line-height:20px;background:rgba(255,255,255,.75);color:#64748B;font-size:13px;border-radius:8px;border:1px solid #E2E6F2;padding:6px 12px', '请输入风格关键词…')
    + cell('focus', 'display:inline-block;width:190px;height:34px;line-height:20px;background:rgba(255,255,255,.9);color:#23283B;font-size:13px;border-radius:8px;border:1px solid #4C6FFF;box-shadow:0 0 0 3px rgba(76,111,255,.15);padding:6px 12px', '靛蓝纸底', 1))));
cards.push(mega('3', '状态签', 'Tag', '工作台实测',
  vrow + vhead('四态 · 玻璃签 tint+色点+同色字', 'r6 · blur 6',
    cell('info', glassSig + ';color:#3550C4', dot('#4C6FFF') + '进行中') + cell('success', glassSig + ';color:#2C664F', dot('#3D8B6E') + '已完成') + cell('warning', glassSig + ';color:#C77D1D', dot('#D9932C') + '待核验') + cell('danger', glassSig + ';color:#C75450', dot('#C75450') + '危险'))));
cards.push(mega('4', '复选 / 开关', 'Check · Switch', '工作台实测',
  vrow + vhead('复选二态 / 开关二态', '复选 15px r4 · 开关 34×19',
    cell('checked', 'display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#23283B', '<span style="width:15px;height:15px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;background:#4C6FFF;color:#fff;font-size:10px">✓</span>已选')
    + cell('unchecked', 'display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#23283B', '<span style="width:15px;height:15px;border-radius:4px;border:1px solid #C9D2CE;background:#fff;display:inline-block"></span>未选', 1)
    + cell('switch-on', 'display:inline-block;width:34px;height:19px;border-radius:999px;background:#4C6FFF;position:relative', '<span style="position:absolute;top:2.5px;right:2.5px;width:14px;height:14px;border-radius:50%;background:#fff"></span>')
    + cell('switch-off', 'display:inline-block;width:34px;height:19px;border-radius:999px;background:#C9D2CE;position:relative', '<span style="position:absolute;top:2.5px;left:2.5px;width:14px;height:14px;border-radius:50%;background:#fff"></span>', 1))));
cards.push(mega('5', 'Tab 标签页', 'Tabs', '工作台实测',
  vrow + vhead('激活 / 未激活', '激活=靛底下划线 2px + 700',
    cell('on', 'border-bottom:2px solid #4C6FFF;padding:6px 2px;font-weight:700;color:#3550C4;font-size:13px;display:inline-block', '工作台')
    + cell('off', 'color:#7C86A0;font-size:13px;padding:6px 2px;display:inline-block', '预览', 1))));
cards.push(mega('6', '进度条', 'Progress', '工作台实测',
  vrow + vhead('进行中', '轨道 6px #EEF1FF · 填充靛蓝',
    cell('64%', 'display:inline-flex;align-items:center;gap:8px', '<span style="width:120px;height:6px;border-radius:999px;background:#EEF1FF;display:inline-block;overflow:hidden"><span style="display:block;width:64%;height:100%;background:#4C6FFF"></span></span><span style="font-size:11px;color:#64748B;font-family:Consolas,monospace">64%</span>'))));
cards.push(mega('7', '消息 / 警告条', 'Alert', '工作台实测',
  vrow + vhead('信息 / 警告', '白实底 · 左侧 3px 语义边',
    cell('info', 'background:#fff;border:1px solid #E2E6F2;border-left:3px solid #4C6FFF;border-radius:8px;padding:8px 12px;font-size:12.5px;color:#23283B;text-align:left', '<b>消息提示</b>　令牌已锁定：靛蓝纸底')
    + cell('warn', 'background:#fff;border:1px solid #E2E6F2;border-left:3px solid #D9932C;border-radius:8px;padding:8px 12px;font-size:12.5px;color:#23283B;text-align:left', '<b>警告</b>　辅助色对比度 4.77:1'))));
cards.push(mega('8', '分页', 'Pagination', '工作台实测',
  vrow + vhead('当前 / 常规', '当前=靛蓝字 700',
    cell('cur', 'color:#4C6FFF;font-weight:700;font-size:13px;display:inline-block', '2')
    + cell('norm', 'color:#64748B;font-size:13px;display:inline-block', '1', 1)
    + cell('norm2', 'color:#64748B;font-size:13px;display:inline-block', '3', 1))));
S(9, '文本域', 'Textarea', '工作台实测', '宽 190 · 白玻璃 · 多行', 'display:inline-block;width:190px;background:rgba(255,255,255,.75);border:1px solid #E2E6F2;border-radius:8px;padding:6px 12px;font-size:13px', '<span style="color:#23283B">靛蓝纸底 · 撞色文气</span><span style="float:right;color:#64748B">▾</span>');
S(10, '选择器', 'Select', 'AI 补全 · 按工作台推断', 'h34 · 白玻璃 · ▾', 'display:inline-block;width:190px;height:34px;line-height:20px;background:rgba(255,255,255,.75);color:#64748B;font-size:13px;border-radius:8px;border:1px solid #E2E6F2;padding:6px 12px', '静态选择器 ▾');
S(11, '头像', 'Avatar', '工作台实测', '36px 圆 · 靛蓝/雾青/淡茶', 'display:inline-flex;width:36px;height:36px;border-radius:50%;background:#4C6FFF;color:#fff;font-size:13px;align-items:center;justify-content:center;font-weight:600', '陈');
S(12, '徽标数', 'Badge', 'AI 补全 · 按工作台推断', 'min-w16 · 危险红', 'display:inline-flex;min-width:16px;height:16px;border-radius:999px;background:#C75450;color:#fff;font-size:10px;align-items:center;justify-content:center;padding:0 4px', '6');
S(13, '面包屑', 'Breadcrumb', '工作台实测', '三级 · 当前墨字', 'font-size:12px;color:#64748B', '工作台 / 第三步 / <b style="color:#23283B">设计令牌</b>');
S(14, '侧栏菜单', 'Sidebar Menu', '工作台实测', '深底 #23283B · 当前态靛蓝左线', 'display:inline-flex;flex-direction:column;gap:4px;background:#23283B;color:#DEE5EC;border-radius:8px;padding:8px 12px;font-size:11.5px', '<span style="color:#fff;border-left:2px solid #4C6FFF;padding-left:8px">第三步 设计令牌</span><span style="padding-left:8px;opacity:.6">第四步 组件</span>');
S(15, '代码块', 'Code', '工作台实测', '浅靛底 · 等宽', 'display:inline-block;font-family:Consolas,monospace;font-size:11px;background:#EEF1FF;color:#3550C4;border-radius:4px;padding:4px 9px', 'tokens.chosen = "靛蓝纸底"');
S(16, '时间线', 'Timeline', '工作台实测', '节点 8px · 靛蓝/雾青', 'display:inline-flex;flex-direction:column;gap:6px;font-size:11.5px;color:#64748B', '<span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#4C6FFF"></span>画像确认</span><span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#3D8B6E"></span>风格落锤</span>');
S(17, '加载', 'Loading', 'AI 补全 · 按工作台推断', '符号 + 文字', 'font-size:12px;color:#64748B', '◌ 加载中…');
S(18, '空态', 'Empty', '工作台实测 · 禁令「空态必须有出路」', '虚线框 + 出路链接', 'display:inline-block;text-align:center;padding:10px 14px;background:#fff;border:1px dashed #E2E6F2;border-radius:8px;font-size:11.5px;color:#64748B', '暂无候选<br><span style="color:#4C6FFF">回复「再来一批」</span>');
S(19, '气泡', 'Tooltip', 'AI 补全 · 按工作台推断', '深底白字 r6', 'display:inline-block;background:#23283B;color:#fff;font-size:11.5px;border-radius:6px;padding:5px 10px', '气泡提示 ▾');
S(20, '警告条', 'Alert', '工作台实测', '白底左 3px 琥珀', 'display:inline-block;background:#fff;border:1px solid #E2E6F2;border-left:3px solid #D9932C;border-radius:8px;padding:6px 10px;font-size:12px;color:#23283B', '警告条示例');
S(21, '表格', 'Table', '工作台实测', '1px 线 · 表头等宽底', 'display:inline-block;border:1px solid #E2E6F2;border-radius:8px;overflow:hidden', '<table style="border-collapse:collapse;width:260px;font-size:12px"><tr><th style="border:1px solid #E2E6F2;padding:5px 9px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10px;text-align:left">TOKEN</th><th style="border:1px solid #E2E6F2;padding:5px 9px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10px;text-align:left">值</th></tr><tr><td style="border:1px solid #E2E6F2;padding:5px 9px;font-family:Consolas,monospace">primary</td><td style="border:1px solid #E2E6F2;padding:5px 9px;font-family:Consolas,monospace">#4C6FFF</td></tr></table>');
S(22, '列表项', 'List Item', '工作台实测', '白卡 r8 · ✓ + 文字 + ›', 'display:inline-flex;align-items:center;gap:10px;background:#fff;border:1px solid #E2E6F2;border-radius:8px;padding:8px 12px;font-size:12.5px', '<span style="color:#3D8B6E">✓</span>第〇步 画像<span style="color:#B9C0CE">›</span>');
S(23, '玻璃卡', 'Glass Card', '工作台实测', '容器层 · rgba .66+blur10', 'display:inline-block;width:200px;background:rgba(255,255,255,.66);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.85);border-radius:10px;padding:12px 14px;box-shadow:0 4px 16px rgba(35,40,59,.08);vertical-align:top', '<b style="font-size:12.5px;color:#23283B">玻璃卡（容器层）</b><br><span style="font-size:11.5px;color:#64748B">信息区退纯白</span>');
S(24, '实底卡', 'Solid Card', '工作台实测', '信息层 · 恒实底', 'display:inline-block;width:200px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:12px 14px;vertical-align:top', '<b style="font-size:12.5px;color:#23283B">实底卡（信息层）</b><br><span style="font-size:11.5px;color:#64748B">正文长文恒实底</span>');
S(25, '抽屉', 'Drawer', 'AI 补全 · 按工作台推断', '右滑 64 宽 · 左投影', 'display:inline-flex;width:64px;height:110px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;box-shadow:-4px 0 16px rgba(35,40,59,.10);flex-direction:column;padding:10px 8px;gap:6px', '<b style="font-size:10px;color:#64748B">抽屉</b><span style="height:1px;background:#E2E6F2"></span><span style="font-size:10px;color:#64748B">右滑出</span>');
S(26, '分割线', 'Divider', '工作台实测', '1px #E2E6F2 或留白', 'display:inline-block;width:160px;height:1px;background:#E2E6F2', '&nbsp;');
S(27, '卡头栏', 'Card Header', '工作台实测', 'F6F7F9 底 + 来源徽章', 'display:block;border:1px solid #E2E6F2;border-radius:12px;overflow:hidden', '<span style="display:block;padding:8px 14px;background:#F6F7F9;border-bottom:1px solid #E2E6F2;font-size:12px;color:#23283B"><b>1. 按钮组</b> <span style="color:#64748B">Button</span><span style="float:right;font-size:10px;background:#4C6FFF;color:#fff;border-radius:4px;padding:2px 8px">来源徽章位</span></span><span style="display:block;padding:10px 14px;font-size:11.5px;color:#64748B">大卡头栏：名称+英文+来源徽章</span>');
S(28, '语义边卡', 'Semantic Edge', 'AI 补全 · 按工作台推断', '左 3px 语义色', 'display:inline-block;background:#fff;border:1px solid #E2E6F2;border-left:3px solid #4C6FFF;border-radius:8px;padding:8px 12px;font-size:12px;color:#23283B', '语义边卡');

ov.component =
  '<div class="block"><div class="spec-label">PRINCIPLES · 原则<span class="role-badge">实测 · 自举沉淀</span></div><ul class="plain">'
  + '<li><b>实物即规格</b> —— 每个状态都是可测量的实物（尺寸/圆角/投影直接来自 token）；找不到实物的组件视为规范缺口。</li>'
  + '<li><b>状态穷举</b> —— 交互组件至少 default / pressed / disabled 三态（大卡穷举）；展示型组件给 default（大卡单态）。</li>'
  + '<li><b>来源分层</b> —— 徽章：实测（工作台逐族拍板）/ AI 补全（推断态，橙角标待回填）。</li></ul></div>'
  + '<div class="block"><div class="spec-label">APPLICATION · 组件全景（28 组全量大卡 · 静玻璃语言派生 · 每组规格书）<span class="role-badge">实测 · 用户逐族拍板 + AI 补全 28 处</span></div>'
  + '<p class="note">交互组件 = 大卡状态穷举（含 ⧉ 复制 CSS）；展示组件 = 大卡 default 实物。玻璃纪律：容器层可玻璃，信息层恒实底。</p>'
  + cards.join('')
  + '</div>'
  + '<div class="block"><div class="spec-label">USAGE · 派生与边界<span class="role-badge">AI 补全 · 派生规则</span></div><ul class="plain">'
  + '<li><b>派生规则</b> —— 新组件从五族语言派生：玻璃度 / radius 档（6/8/10）/ 语义色 / 等宽标注，禁第二套视觉语言。</li>'
  + '<li><b>玻璃度边界</b> —— 容器与控件可玻璃；表格/代码块/长文/标签内文字恒实底。</li>'
  + '<li><b>尺寸档</b> —— 控件高 34（标准）/ 28（紧凑）；图标 16/20/24；禁档外尺寸。</li></ul></div>';

fs.writeFileSync(p, JSON.stringify(c, null, 2));
console.log('C1 辅助色 AA 替换', n1, '处 · C2 组件章 28 组全量大卡完成');
