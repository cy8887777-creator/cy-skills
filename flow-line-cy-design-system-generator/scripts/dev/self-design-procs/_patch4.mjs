import fs from 'node:fs';
const p = 'chain.json';
const c = JSON.parse(fs.readFileSync(p, 'utf8'));
const ov = c.overview;

// ── case 大卡规格书格式：卡头栏（来源徽章）+ 变体行（尺寸标注 + 状态穷举单元 + ⧉复制CSS）──
const badge = (t) => '<span style="margin-left:auto;font-size:10px;background:#4C6FFF;color:#fff;border-radius:4px;padding:2px 8px">' + t + '</span>';
const vhead = (name, spec) => '<div style="display:flex;align-items:baseline;gap:8px;margin-bottom:8px"><b style="font-size:13px">' + name + '</b><span style="font-size:11px;color:#979CA5;font-family:Consolas,monospace">' + spec + '</span></div>';
const cell = (lbl, style, inner, ai) => '<div style="text-align:center;flex:1 1 0;min-width:max-content;max-width:100%"><div style="display:flex;align-items:center;justify-content:center;min-height:76px;background:#fff;border-radius:8px;margin:0 4px"><span style="' + style + '">' + inner + '</span></div><div style="display:flex;align-items:center;justify-content:center;gap:6px;margin-top:2px"><span style="font-size:10px;background:#F6F7F9;color:#626A76;border-radius:4px;padding:2px 8px;white-space:nowrap">' + lbl + '</span>' + (ai ? '<span style="font-size:9px;color:#C77D1D;border:1px solid rgba(199,125,29,.45);border-radius:3px;padding:0 3px">AI 补全</span>' : '') + '<button class="css-copy" title="复制该实物根元素的 CSS" style="font-size:10px;border:1px solid #E2E6F2;background:#fff;color:#626A76;border-radius:4px;padding:2px 8px;cursor:pointer">⧉ 复制 CSS</button></div></div>';
const row = (variants) => '<div style="display:flex;gap:6px;flex-wrap:wrap;align-items:flex-end">' + variants.join('') + '</div>';
const mega = (no, name, en, badgeTxt, body) => '<div style="border:1px solid #E2E6F2;border-radius:16px;overflow:hidden;background:#fff;margin:0 0 16px"><div style="padding:12px 18px;background:#F6F7F9;border-bottom:1px solid #E2E6F2;display:flex;align-items:center;gap:8px"><b style="font-size:15px">' + no + '. ' + name + '</b><span style="font-size:11px;color:#979CA5">' + en + '</span>' + badge(badgeTxt) + '</div><div style="padding:6px 18px 16px">' + body + '</div></div>';
const vrow = '<div style="margin-top:12px;padding-top:12px;border-top:1px dashed #EEF1F4">';
const btnP = 'display:inline-block;padding:7px 18px;background:rgba(76,111,255,.88);color:#fff;font-size:14px;border-radius:8px;border:1px solid rgba(255,255,255,.38);box-shadow:0 4px 12px rgba(76,111,255,.35)';
const btnS = 'display:inline-block;padding:7px 18px;background:rgba(255,255,255,.7);color:#4C6FFF;font-size:14px;border-radius:8px;border:1px solid #4C6FFF';
const btnT = 'display:inline-block;padding:7px 12px;color:#4C6FFF;font-size:14px';

// 交互组件大卡（真控件 · 状态穷举 · 复制 CSS）
const cButton = mega('1', '按钮组', 'Button', '工作台实测 · pressed/disabled 为 AI 补全',
  vrow + vhead('主按钮 · 玻璃化', 'h34 · r8 · rgba(76,111,255,.88) · 白描边 .38 · 彩影 0 4px 12px',
    cell('default', btnP, '主操作') + cell('pressed', btnP.replace('.88)', '.78)').replace('margin:0 8px 8px 0', 'margin:0 8px 8px 0;transform:scale(.96);filter:brightness(.96)'), '主操作', 1) + cell('disabled', 'display:inline-block;padding:7px 18px;background:#F0F2F5;color:#B9C0CE;font-size:14px;border-radius:8px;border:none', '禁用态', 1))
  + vrow + vhead('次按钮 / 文字按钮', '白玻璃 .7 靛字靛细边 · 文字钮无底',
    cell('default', btnS, '次操作') + cell('default', btnT, '文字按钮') + cell('disabled', 'display:inline-block;padding:7px 12px;color:#B9C0CE;font-size:14px', '文字禁用', 1)));
const cInput = mega('2', '输入框', 'Input', '工作台实测 · focus 为 AI 补全',
  vrow + vhead('默认 / 聚焦', 'h34 · 白玻璃 .75 · focus 靛边+光环 3px',
    cell('default', 'display:inline-block;width:190px;height:34px;line-height:20px;background:rgba(255,255,255,.75);color:#B9C0CE;font-size:13px;border-radius:8px;border:1px solid #E2E6F2;padding:6px 12px', '请输入风格关键词…')
    + cell('focus', 'display:inline-block;width:190px;height:34px;line-height:20px;background:rgba(255,255,255,.9);color:#23283B;font-size:13px;border-radius:8px;border:1px solid #4C6FFF;box-shadow:0 0 0 3px rgba(76,111,255,.15);padding:6px 12px', '靛蓝纸底', 1)));
const cTag = mega('3', '状态签', 'Tag', '工作台实测',
  vrow + vhead('四态 · tint 底+色点+同色字', 'r6 · 玻璃签',
    cell('info', 'display:inline-block;padding:4px 10px;background:rgba(255,255,255,.6);backdrop-filter:blur(6px);color:#3550C4;font-size:12px;border-radius:6px;border:1px solid rgba(255,255,255,.8)', '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#4C6FFF;margin-right:5px"></span>进行中')
    + cell('success', 'display:inline-block;padding:4px 10px;background:rgba(255,255,255,.6);backdrop-filter:blur(6px);color:#2C664F;font-size:12px;border-radius:6px;border:1px solid rgba(255,255,255,.8)', '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#3D8B6E;margin-right:5px"></span>已完成')
    + cell('warning', 'display:inline-block;padding:4px 10px;background:rgba(255,255,255,.6);backdrop-filter:blur(6px);color:#C77D1D;font-size:12px;border-radius:6px;border:1px solid rgba(255,255,255,.8)', '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#D9932C;margin-right:5px"></span>待核验')
    + cell('danger', 'display:inline-block;padding:4px 10px;background:rgba(255,255,255,.6);backdrop-filter:blur(6px);color:#C75450;font-size:12px;border-radius:6px;border:1px solid rgba(255,255,255,.8)', '<span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:#C75450;margin-right:5px"></span>危险')));
const cCheck = mega('4', '复选 / 开关', 'Check · Switch', '工作台实测',
  vrow + vhead('复选二态 / 开关二态', '复选 15px r4 · 开关 34×19',
    cell('checked', 'display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#23283B', '<span style="width:15px;height:15px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;background:#4C6FFF;color:#fff;font-size:10px">✓</span>已选')
    + cell('unchecked', 'display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#23283B', '<span style="width:15px;height:15px;border-radius:4px;border:1px solid #C9D2CE;background:#fff;display:inline-block"></span>未选', 1)
    + cell('switch-on', 'display:inline-block;width:34px;height:19px;border-radius:999px;background:#4C6FFF;position:relative', '<span style="position:absolute;top:2.5px;right:2.5px;width:14px;height:14px;border-radius:50%;background:#fff"></span>')
    + cell('switch-off', 'display:inline-block;width:34px;height:19px;border-radius:999px;background:#C9D2CE;position:relative', '<span style="position:absolute;top:2.5px;left:2.5px;width:14px;height:14px;border-radius:50%;background:#fff"></span>', 1)));
const cTab = mega('5', 'Tab 标签页', 'Tabs', '工作台实测',
  vrow + vhead('激活 / 未激活', '激活=靛底下划线 2px + 700', 
    cell('on', 'border-bottom:2px solid #4C6FFF;padding:6px 2px;font-weight:700;color:#3550C4;font-size:13px;display:inline-block', '工作台')
    + cell('off', 'color:#7C86A0;font-size:13px;padding:6px 2px;display:inline-block', '预览', 1)));
const cProg = mega('6', '进度条', 'Progress', '工作台实测',
  vrow + vhead('进行中', '轨道 6px #EEF1FF · 填充靛蓝',
    cell('64%', 'display:inline-flex;align-items:center;gap:8px', '<span style="width:120px;height:6px;border-radius:999px;background:#EEF1FF;display:inline-block;overflow:hidden"><span style="display:block;width:64%;height:100%;background:#4C6FFF"></span></span><span style="font-size:11px;color:#8A93A0;font-family:Consolas,monospace">64%</span>')));
const cMsg = mega('7', '消息 / 警告条', 'Alert', '工作台实测',
  vrow + vhead('信息 / 警告', '白实底 · 左侧 3px 语义边',
    cell('info', 'background:#fff;border:1px solid #E2E6F2;border-left:3px solid #4C6FFF;border-radius:8px;padding:8px 12px;font-size:12.5px;color:#23283B;text-align:left', '<b>消息提示</b>　令牌已锁定：靛蓝纸底')
    + cell('warn', 'background:#fff;border:1px solid #E2E6F2;border-left:3px solid #D9932C;border-radius:8px;padding:8px 12px;font-size:12.5px;color:#23283B;text-align:left', '<b>警告</b>　辅助色对比度 3.6:1')));
const cPage = mega('8', '分页', 'Pagination', '工作台实测',
  vrow + vhead('当前 / 常规', '当前=靛蓝字 700',
    cell('cur', 'color:#4C6FFF;font-weight:700;font-size:13px;display:inline-block', '2')
    + cell('norm', 'color:#7C86A0;font-size:13px;display:inline-block', '1', 1)
    + cell('norm2', 'color:#7C86A0;font-size:13px;display:inline-block', '3', 1)));

// 展示组（横条实物 · default 态）
const flat = (lbl, body) => '<div class="comp-stage">' + body + '<span class="stage-lbl">' + lbl + '</span></div>';
const shows = [
  flat('9-11 · 文本域 / 选择器 / 头像 · 徽标数', '<span style="display:inline-block;width:190px;background:rgba(255,255,255,.75);border:1px solid #E2E6F2;border-radius:8px;padding:6px 12px;font-size:13px;margin:0 10px 8px 0"><span style="color:#23283B">靛蓝纸底 · 撞色文气</span><span style="float:right;color:#B9C0CE">▾</span></span><span style="display:inline-block;width:190px;height:34px;line-height:34px;background:rgba(255,255,255,.75);color:#B9C0CE;font-size:13px;border-radius:8px;border:1px solid #E2E6F2;padding:0 12px;margin:0 10px 8px 0">静态选择器 ▾</span><span style="display:inline-flex;width:36px;height:36px;border-radius:50%;background:#4C6FFF;color:#fff;font-size:13px;align-items:center;justify-content:center;font-weight:600;margin:0 8px 8px 0">陈</span><span style="display:inline-flex;width:36px;height:36px;border-radius:50%;background:#3D8B6E;color:#fff;font-size:13px;align-items:center;justify-content:center;font-weight:600;margin:0 8px 8px 0">宇</span><span style="display:inline-block;position:relative;margin:0 12px 8px 0"><span style="display:inline-flex;width:30px;height:30px;border-radius:8px;background:#fff;border:1px solid #E2E6F2;align-items:center;justify-content:center;color:#5A6472">✉</span><span style="position:absolute;top:-5px;right:-7px;min-width:16px;height:16px;border-radius:999px;background:#C75450;color:#fff;font-size:10px;display:flex;align-items:center;justify-content:center;padding:0 4px">6</span></span>'),
  flat('12-14 · 面包屑 / 侧栏菜单 / 代码块', '<span style="font-size:12px;color:#7C86A0;margin:0 12px 8px 0">工作台 / 第三步 / <b style="color:#23283B">设计令牌</b></span><span style="display:inline-flex;flex-direction:column;gap:4px;background:#23283B;color:#DEE5EC;border-radius:8px;padding:8px 12px;font-size:11.5px;margin:0 12px 8px 0;vertical-align:top"><span style="color:#fff;border-left:2px solid #4C6FFF;padding-left:8px">第三步 设计令牌</span><span style="padding-left:8px;opacity:.6">第四步 组件</span></span><code style="font-family:Consolas,monospace;font-size:11px;background:#EEF1FF;color:#3550C4;border-radius:4px;padding:4px 9px;margin:0 12px 8px 0;display:inline-block">tokens.chosen = "靛蓝纸底"</code>'),
  flat('15-17 · 时间线 / 进度点 / 加载', '<span style="display:inline-flex;flex-direction:column;gap:6px;font-size:11.5px;color:#5A6472;margin:0 12px 8px 0;vertical-align:top"><span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#4C6FFF"></span>画像确认</span><span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#3D8B6E"></span>风格落锤</span></span><span style="font-size:12px;color:#8A93A0;margin:0 12px 8px 0">◌ 加载中…</span>'),
  flat('18-20 · 空态 / 气泡 / 警告', '<span style="display:inline-block;text-align:center;padding:10px 14px;background:#fff;border:1px dashed #E2E6F2;border-radius:8px;font-size:11.5px;color:#8A93A0;margin:0 10px 8px 0">暂无候选<br><span style="color:#4C6FFF">回复「再来一批」</span></span><span style="display:inline-block;background:#23283B;color:#fff;font-size:11.5px;border-radius:6px;padding:5px 10px;margin:0 10px 8px 0;position:relative">气泡提示 ▾</span><span style="display:inline-block;background:#fff;border:1px solid #E2E6F2;border-left:3px solid #D9932C;border-radius:8px;padding:6px 10px;font-size:12px">警告条示例</span>'),
  flat('21-23 · 表格 / 列表项 / 时间容器', '<table style="border-collapse:collapse;width:280px;font-size:12px;background:#fff;display:inline-table;vertical-align:top;margin:0 12px 8px 0"><tr><th style="border:1px solid #E2E6F2;padding:5px 9px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10px;text-align:left">TOKEN</th><th style="border:1px solid #E2E6F2;padding:5px 9px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10px;text-align:left">值</th></tr><tr><td style="border:1px solid #E2E6F2;padding:5px 9px;font-family:Consolas,monospace">primary</td><td style="border:1px solid #E2E6F2;padding:5px 9px;font-family:Consolas,monospace">#4C6FFF</td></tr></table><span style="display:inline-flex;align-items:center;gap:10px;background:#fff;border:1px solid #E2E6F2;border-radius:8px;padding:8px 12px;font-size:12.5px;margin:0 12px 8px 0"><span style="color:#3D8B6E">✓</span>第〇步 画像<span style="color:#B9C0CE">›</span></span>'),
  flat('24-26 · 玻璃卡 / 实底卡 / 抽屉', '<span style="display:inline-block;width:200px;background:rgba(255,255,255,.66);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.85);border-radius:10px;padding:12px 14px;box-shadow:0 4px 16px rgba(35,40,59,.08);vertical-align:top;margin:0 10px 8px 0"><b style="font-size:12.5px">玻璃卡（容器层）</b><br><span style="font-size:11.5px;color:#7C86A0">信息区退纯白</span></span><span style="display:inline-block;width:200px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:12px 14px;vertical-align:top;margin:0 10px 8px 0"><b style="font-size:12.5px">实底卡（信息层）</b><br><span style="font-size:11.5px;color:#7C86A0">正文长文恒实底</span></span><span style="display:inline-flex;width:64px;height:110px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;box-shadow:-4px 0 16px rgba(35,40,59,.10);vertical-align:top;flex-direction:column;padding:10px 8px;gap:6px;margin:0 10px 8px 0"><b style="font-size:10px;color:#7C86A0">抽屉</b><span style="height:1px;background:#E2E6F2"></span><span style="font-size:10px;color:#5A6472">右滑出</span></span>'),
  flat('27-28 · 卡头栏范例说明 / 语义边卡', '<span style="display:inline-block;border:1px solid #E2E6F2;border-radius:12px;overflow:hidden;vertical-align:top;margin:0 10px 8px 0"><span style="display:block;padding:8px 14px;background:#F6F7F9;border-bottom:1px solid #E2E6F2;font-size:12px"><b>1. 按钮组</b> <span style="color:#979CA5">Button</span><span style="float:right;font-size:10px;background:#4C6FFF;color:#fff;border-radius:4px;padding:2px 8px">来源徽章位</span></span><span style="display:block;padding:10px 14px;font-size:11.5px;color:#7C86A0">大卡头栏：名称+英文+来源徽章<br>（状态穷举见上方交互大卡）</span></span><span style="display:inline-block;background:#fff;border:1px solid #E2E6F2;border-left:3px solid #4C6FFF;border-radius:8px;padding:8px 12px;font-size:12px;vertical-align:top">语义边卡</span>'),
];

ov.component =
  '<div class="block"><div class="spec-label">PRINCIPLES · 原则<span class="role-badge">实测 · 自举沉淀</span></div><ul class="plain">'
  + '<li><b>实物即规格</b> —— 每个状态都是可测量的实物（尺寸/圆角/投影直接来自 token）；找不到实物的组件视为规范缺口。</li>'
  + '<li><b>状态穷举</b> —— 交互组件至少 default / pressed / disabled 三态（大卡穷举）；展示型组件给 default（横条陈列）。</li>'
  + '<li><b>来源分层</b> —— 徽章：实测（工作台逐族拍板）/ AI 补全（按压/禁用等推断态，橙角标）。</li></ul></div>'
  + '<div class="block"><div class="spec-label">APPLICATION · 组件全景（28 组 · 交互 8 组大卡穷举 + 展示 20 组横条）<span class="role-badge">实测 · 用户逐族拍板</span></div>'
  + '<p class="note">交互组件 = 大卡规格书（状态穷举 + ⧉ 复制 CSS）；展示组件 = 实物横条（default 态）。玻璃纪律全局生效。</p>'
  + cButton + cInput + cTag + cCheck + cTab + cProg + cMsg + cPage
  + shows.join('')
  + '</div>'
  + '<div class="block"><div class="spec-label">USAGE · 派生与边界<span class="role-badge">AI 补全 · 派生规则</span></div><ul class="plain">'
  + '<li><b>派生规则</b> —— 新组件从五族语言派生：玻璃度 / radius 档（6/8/10）/ 语义色 / 等宽标注，禁第二套视觉语言。</li>'
  + '<li><b>玻璃度边界</b> —— 容器与控件可玻璃；表格/代码块/长文/标签内文字恒实底。</li>'
  + '<li><b>尺寸档</b> —— 控件高 34（标准）/ 28（紧凑）；图标 16/20/24；禁档外尺寸。</li></ul></div>';
console.log('[探针] 赋值后: len', ov.component.length, '· button', (ov.component.match(/<button/g) || []).length, '· cButton.type', typeof cButton, '· cButton.len', cButton ? cButton.length : '-');

fs.writeFileSync(p, JSON.stringify(c, null, 2));
const _chk = JSON.parse(fs.readFileSync(p, 'utf8'));
console.log('回读: component 长度', _chk.overview.component.length, '· button', (_chk.overview.component.match(/<button/g) || []).length);
console.log('组件章重写：8 交互大卡（状态穷举+复制CSS）+ 7 展示横条（20 组）');
