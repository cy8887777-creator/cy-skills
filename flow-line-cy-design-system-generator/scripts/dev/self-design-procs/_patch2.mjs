import fs from 'node:fs';
const p = 'chain.json';
const c = JSON.parse(fs.readFileSync(p, 'utf8'));
const ov = c.overview;

const glassPanel = 'background:rgba(255,255,255,.66);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.85);border-radius:10px';
const solid = 'background:#fff';
const btnPri = '<span style="display:inline-block;padding:7px 18px;background:rgba(76,111,255,.88);color:#fff;font-size:14px;border-radius:8px;border:1px solid rgba(255,255,255,.38);box-shadow:0 4px 12px rgba(76,111,255,.35);margin:0 8px 8px 0">主操作</span>';
const btnSec = '<span style="display:inline-block;padding:7px 18px;background:rgba(255,255,255,.7);color:#4C6FFF;font-size:14px;border-radius:8px;border:1px solid #4C6FFF;margin:0 8px 8px 0">次操作</span>';
const btnTxt = '<span style="display:inline-block;padding:7px 12px;color:#4C6FFF;font-size:14px;margin:0 8px 8px 0">文字按钮</span>';
const btnDis = '<span style="display:inline-block;padding:7px 18px;background:#F0F2F5;color:#B9C0CE;font-size:14px;border-radius:8px;border:none;margin:0 8px 8px 0">禁用态</span>';
const inp = 'display:inline-block;width:190px;height:34px;line-height:34px;background:rgba(255,255,255,.75);color:#B9C0CE;font-size:13px;border-radius:8px;border:1px solid rgba(255,255,255,.85);padding:0 12px;margin:0 8px 8px 0;vertical-align:middle;';
const tag = (bg, fg, dot, txt) => '<span style="display:inline-block;padding:2px 10px;background:' + bg + ';color:' + fg + ';font-size:12px;border-radius:6px;border:1px solid rgba(255,255,255,.8);margin:0 6px 6px 0"><span style="display:inline-block;width:7px;height:7px;border-radius:50%;background:' + dot + ';margin-right:5px;vertical-align:1px"></span>' + txt + '</span>';
const stage = (lbl, body) => '<div class="comp-stage">' + body + '<span class="stage-lbl">' + lbl + '</span></div>';

const chk = (on, lbl) => '<span style="display:inline-flex;align-items:center;gap:6px;font-size:13px;color:#23283B;margin:0 14px 8px 0"><span style="width:15px;height:15px;border-radius:4px;display:inline-flex;align-items:center;justify-content:center;background:' + (on ? '#4C6FFF' : '#fff') + ';border:1px solid ' + (on ? '#4C6FFF' : '#C9D2CE') + ';color:#fff;font-size:10px">' + (on ? '✓' : '') + '</span>' + lbl + '</span>';
const sw = (on) => '<span style="display:inline-block;width:34px;height:19px;border-radius:999px;background:' + (on ? '#4C6FFF' : '#C9D2CE') + ';position:relative;margin:0 10px 8px 0;vertical-align:middle"><span style="position:absolute;top:2.5px;' + (on ? 'right:2.5px' : 'left:2.5px') + ';width:14px;height:14px;border-radius:50%;background:#fff;box-shadow:0 1px 2px rgba(0,0,0,.15)"></span></span>';
const avatar = (c, t) => '<span style="display:inline-flex;width:36px;height:36px;border-radius:50%;background:' + c + ';color:#fff;font-size:13px;align-items:center;justify-content:center;margin:0 8px 8px 0;font-weight:600">' + t + '</span>';

ov.component =
  '<div class="block"><div class="spec-label">APPLICATION · 组件全景（31 组 · 静玻璃语言派生 · 每组变体/状态）</div>'
  + '<p class="note">覆盖 = 原型实际组件清单（步骤列/Tab/代码块/色板块…）∪ 设计系统常用标准件。玻璃纪律全局生效：容器层可玻璃，信息层/正文恒实底。</p>'

  // A 基础控件
  + stage('A · 基础控件（8）', 
      '<span class="stage-lbl" style="margin:0 0 8px">按钮</span>' + btnPri + btnSec + btnTxt + btnDis
      + '<span class="stage-lbl" style="margin:8px 0 8px">输入 / 文本域 / 选择器</span>'
      + '<div><span style="' + inp + '">请输入风格关键词…</span><span style="' + inp + 'border-color:#4C6FFF;box-shadow:0 0 0 3px rgba(76,111,255,.15);color:#23283B">已聚焦态</span>'
      + '<span style="display:inline-block;width:190px;background:rgba(255,255,255,.75);border:1px solid rgba(255,255,255,.85);border-radius:8px;padding:6px 12px;margin:0 8px 8px 0;vertical-align:top"><span style="display:block;font-size:13px;color:#23283B">靛蓝纸底 · 撞色文气</span><span style="display:inline-block;margin-top:4px;font-size:11px;color:#B9C0CE">文本域 ▾</span></span>'
      + '<span style="' + inp + '">静态选择器 ▾</span></div>'
      + '<span class="stage-lbl" style="margin:8px 0 8px">复选 / 单选 / 开关</span>'
      + '<div>' + chk(true, '已选') + chk(false, '未选') + '<span style="display:inline-flex;align-items:center;gap:6px;font-size:13px;margin:0 14px 8px 0"><span style="width:15px;height:15px;border-radius:50%;border:1px solid #C9D2CE;background:#fff;display:inline-block"></span>单选</span>' + sw(true) + sw(false) + '</div>')

  // B 标签与徽标
  + stage('B · 标签 / 状态签 / 徽标数 / 头像（4）',
      tag('#EEF1FF', '#3550C4', '#4C6FFF', '进行中') + tag('#E6F4ED', '#2C664F', '#3D8B6E', '已完成') + tag('#FDF3E5', '#C77D1D', '#D9932C', '待核验') + tag('#FBEAEA', '#C75450', '#C75450', '危险')
      + '<span style="display:inline-block;position:relative;margin:0 14px 8px 0"><span style="display:inline-flex;width:30px;height:30px;border-radius:8px;background:#F0F2F5;align-items:center;justify-content:center;color:#5A6472">✉</span><span style="position:absolute;top:-5px;right:-7px;min-width:16px;height:16px;border-radius:999px;background:#C75450;color:#fff;font-size:10px;display:flex;align-items:center;justify-content:center;padding:0 4px">6</span></span>'
      + avatar('#4C6FFF', '陈') + avatar('#3D8B6E', '宇') + avatar('#C9A87C', 'DS'))

  // C 导航
  + stage('C · 导航（5）',
      '<div style="width:100%;background:rgba(255,255,255,.66);backdrop-filter:blur(12px);border:1px solid rgba(255,255,255,.85);border-radius:8px;padding:10px 14px;display:flex;gap:14px;align-items:center;margin-bottom:8px"><b style="font-size:13px">工作台自举</b><span style="font-size:11px;background:#4C6FFF;color:#fff;border-radius:6px;padding:3px 10px">当前步</span><span style="margin-left:auto;font-size:12px;color:#4C6FFF;text-decoration:underline">素材入口 ↗</span></div>'
      + '<span class="stage-lbl" style="margin:0 0 8px">Tab / 面包屑 / 侧栏菜单 / 分页</span>'
      + '<div style="display:flex;gap:16px;flex-wrap:wrap;align-items:center"><span style="border-bottom:2px solid #4C6FFF;padding:6px 2px;font-weight:700;color:#3550C4;font-size:13px">工作台</span><span style="color:#7C86A0;font-size:13px;padding:6px 2px">预览</span>'
      + '<span style="font-size:12px;color:#7C86A0">工作台 / 第三步 / <b style="color:#23283B">设计令牌</b></span>'
      + '<span style="background:#23283B;color:#DEE5EC;border-radius:8px;padding:8px 12px;font-size:11.5px;display:inline-flex;flex-direction:column;gap:4px"><span style="color:#fff;border-left:2px solid #4C6FFF;padding-left:8px">第三步 设计令牌</span><span style="padding-left:8px;opacity:.6">第四步 组件</span></span>'
      + '<span style="font-size:12px;color:#7C86A0">‹ 1 <b style="color:#4C6FFF">2</b> 3 … 9 ›</span></div>')

  // D 反馈
  + stage('D · 反馈（6）',
      '<div style="width:100%;display:flex;flex-direction:column;gap:8px">'
      + '<div style="background:#fff;border:1px solid #E2E6F2;border-left:3px solid #4C6FFF;border-radius:8px;padding:8px 12px;font-size:12.5px"><b>消息提示</b>　令牌已锁定：靛蓝纸底</div>'
      + '<div style="background:#fff;border:1px solid #E2E6F2;border-left:3px solid #D9932C;border-radius:8px;padding:8px 12px;font-size:12.5px"><b>警告</b>　辅助色对比度 3.6:1（注标用途）</div></div>'
      + '<span class="stage-lbl" style="margin:8px 0 8px">进度 / 加载 / 空态 / 气泡</span>'
      + '<div style="display:flex;gap:18px;align-items:center;flex-wrap:wrap">'
      + '<span style="display:inline-flex;align-items:center;gap:8px"><span style="width:120px;height:6px;border-radius:999px;background:#EEF1FF;display:inline-block;overflow:hidden"><span style="display:block;width:64%;height:100%;background:#4C6FFF"></span></span><span style="font-size:11px;color:#8A93A0;font-family:Consolas,monospace">64%</span></span>'
      + '<span style="font-size:12px;color:#8A93A0">◌ 加载中…</span>'
      + '<span style="display:inline-block;text-align:center;padding:10px 14px;background:#fff;border:1px dashed #E2E6F2;border-radius:8px;font-size:11.5px;color:#8A93A0">暂无候选<br><span style="color:#4C6FFF">回复「再来一批」</span></span>'
      + '<span style="display:inline-block;background:#23283B;color:#fff;font-size:11.5px;border-radius:6px;padding:5px 10px;position:relative">气泡提示 ▾</span></div>')

  // E 数据展示
  + stage('E · 数据展示（5）',
      '<table style="border-collapse:collapse;width:100%;font-size:12.5px;background:#fff"><tr><th style="border:1px solid #E2E6F2;padding:6px 10px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10.5px;text-align:left">TOKEN</th><th style="border:1px solid #E2E6F2;padding:6px 10px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10.5px;text-align:left">值</th><th style="border:1px solid #E2E6F2;padding:6px 10px;background:#F5F4F0;font-family:Consolas,monospace;font-size:10.5px;text-align:left">用途</th></tr><tr><td style="border:1px solid #E2E6F2;padding:6px 10px;font-family:Consolas,monospace">primary</td><td style="border:1px solid #E2E6F2;padding:6px 10px;font-family:Consolas,monospace">#4C6FFF</td><td style="border:1px solid #E2E6F2;padding:6px 10px;color:#7C86A0">选中/可操作</td></tr></table>'
      + '<span class="stage-lbl" style="margin:8px 0 8px">列表项 / 时间线 / 代码块</span>'
      + '<div style="display:flex;gap:14px;flex-wrap:wrap">'
      + '<span style="display:inline-flex;align-items:center;gap:10px;background:#fff;border:1px solid #E2E6F2;border-radius:8px;padding:8px 12px;font-size:12.5px"><span style="color:#3D8B6E">✓</span>第〇步 画像<span style="color:#B9C0CE;margin-left:auto">›</span></span>'
      + '<span style="display:inline-flex;flex-direction:column;gap:6px;font-size:11.5px;color:#5A6472;padding:4px 0"><span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#4C6FFF"></span>画像确认</span><span style="display:flex;gap:8px;align-items:center"><span style="width:8px;height:8px;border-radius:50%;background:#3D8B6E"></span>风格落锤</span></span>'
      + '<code style="font-family:Consolas,monospace;font-size:11px;background:#EEF1FF;color:#3550C4;border-radius:4px;padding:4px 9px;display:inline-block">tokens.chosen = "靛蓝纸底"</code></div>')

  // F 容器
  + stage('F · 容器（3）',
      '<span style="display:inline-block;width:200px;background:rgba(255,255,255,.66);backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.85);border-radius:10px;padding:12px 14px;box-shadow:0 4px 16px rgba(35,40,59,.08);vertical-align:top;margin-right:10px"><b style="font-size:12.5px">玻璃卡（容器层）</b><br><span style="font-size:11.5px;color:#7C86A0">信息区已退纯白</span></span>'
      + '<span style="display:inline-block;width:200px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:12px 14px;vertical-align:top;margin-right:10px"><b style="font-size:12.5px">实底卡（信息层）</b><br><span style="font-size:11.5px;color:#7C86A0">正文长文区恒实底</span></span>'
      + '<span style="display:inline-flex;width:64px;height:120px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;box-shadow:-4px 0 16px rgba(35,40,59,.10);vertical-align:top;flex-direction:column;padding:10px 8px;gap:6px"><b style="font-size:10px;color:#7C86A0">抽屉</b><span style="height:1px;background:#E2E6F2"></span><span style="font-size:10px;color:#5A6472">右滑出</span></span>'
      + '<span class="stage-lbl">分割线：1px #E2E6F2 或留白（三件套禁令）</span>')

  + '</div>'
  + '<div class="block"><div class="spec-label">USAGE · 派生与边界</div><ul class="plain">'
  + '<li><b>次级组件派生规则</b> —— 一切新组件从五族语言派生：容器层玻璃度 / radius 档（6/8/10）/ 语义色 / 等宽标注，不发明第二套视觉语言。</li>'
  + '<li><b>玻璃度边界</b> —— 容器与控件可玻璃；表格/代码块/长文/标签内文字恒实底。</li>'
  + '<li><b>尺寸档</b> —— 控件高 34（标准）/ 28（紧凑）；图标 16/20/24；禁档外尺寸。</li></ul></div>';

fs.writeFileSync(p, JSON.stringify(c, null, 2));
console.log('组件章重写：28 组全景');
