import fs from 'node:fs';
const p = new URL('./chain.json', import.meta.url);
const c = JSON.parse(fs.readFileSync(p, 'utf8'));
const ov = c.overview;

// ── case 模式 CSS（靛蓝令牌化）+ 复制 JS：随 values 章注入一次，全局生效 ──

// 工具
const blk = (label, body) => '<div class="block"><div class="spec-label">' + label + '</div>' + body + '</div>';
const sw = (hex, nm, use) => '<button class="swatch" data-hex="' + hex + '" title="点击复制 ' + hex + '"><span class="chip" style="background:' + hex + '"></span><span class="nm">' + nm + '</span><span class="hx">' + hex + (use ? ' · ' + use : '') + '</span></button>';

// ── 01 设计价值观 ──
ov.values = blk('PRINCIPLES · 原则 <span class="role-badge">实测 · 用户拍板</span>', '<ul class="plain">'
  + '<li><b>文档流组织</b> —— 一切决策内容按文档编排：单栏流、键值行、等宽标注；像一份正在被认真排版的设计规范书。</li>'
  + '<li><b>写到哪里亮到哪里</b> —— 当前步用块面声明（实底反白），历史步骤灰阶回看，未至步骤浅灰预告。</li>'
  + '<li><b>视觉同源</b> —— 工作过程与产出物（设计系统文档）视觉同源：预览 Tab 就是最终交付的预演。</li>'
  + '<li><b>清新不冷淡</b> —— 暖纸底 × 冷靛蓝的撞色；玻璃只做容器不做信息层。</li></ul>')
  + blk('WHAT · 风格定义 <span class="role-badge">实测 · 单选整卡</span>', '<p><b>文档编辑风 Workspace Editorial</b> <span class="role-badge">自创</span></p>'
  + '<p>概念：把工作台做成一份正在被认真排版的设计规范书——单栏文档流，候选项是浅底代码块，键值排版，层级靠字号与留白。</p>'
  + '<p class="note">观感：知性、从容、每一条决策都被排版师尊重过。家族：<code>【自创·演化自 minimalism × editorial × notion-style】</code>，不回流风格库。定案过程：用户从 4 候选（含库内 3 张）中单选整卡执行。</p>');

// ── 02 布局 ──
ov.layout =
  blk('WHAT · 三区骨架 <span class="role-badge">实测 · 画像布局归类</span>', '<ul class="plain">'
  + '<li><b>顶栏</b> —— 项目名 · 决策链版本 · 当前步 chip · 四素材入口（超链接色 + 下划线）。</li>'
  + '<li><b>向导流程区（左）</b> —— 步骤列 256px：已完成 ✓ 灰字 / 当前步靛蓝实底反白块 / 未至步浅灰预告；每步带一句副题。</li>'
  + '<li><b>决策面板区（右）</b> —— 当前步大标题（28px 衬线）+ 提示语 + 候选卡网格（双列 gap 18-20）。</li>'
  + '<li><b>文档区（预览 Tab）</b> —— 单栏 720px 阅读宽 + 14 章目录锚点。</li></ul>')
  + blk('APPLICATION · 骨架实物（三区微缩）<span class="role-badge">AI 补全 · 骨架示意</span>', '<div style="border:1px solid #E2E6F2;border-radius:10px;overflow:hidden;font-size:10px;font-family:Consolas,monospace;color:#7C86A0;background:#fff">'
  + '<div style="background:#23283B;color:#DEE5EC;padding:6px 10px;display:flex;gap:8px"><b style="color:#fff">顶栏</b><span>决策链 v1</span><span style="margin-left:auto;color:#8B9BFF;text-decoration:underline">素材入口</span></div>'
  + '<div style="display:flex"><div style="width:130px;background:#F5F4F0;padding:8px;line-height:1.9"><b>步骤列 256px</b><br>✓ 已完成（灰）<br>● 当前步（靛蓝实底反白）<br>3 未至（浅灰预告）</div><div style="flex:1;padding:8px;line-height:1.9"><b>决策面板（文档流）</b><br>当前步大标题 28px 衬线<br>候选卡双列 gap 18-20<br>浅底代码块质感键值行</div></div>'
  + '<div style="padding:6px 10px;background:#EEF1FF">预览 Tab：单栏 720px 阅读宽 · 14 章目录锚点</div></div>')
  + blk('USAGE · 使用规范 <span class="role-badge">AI 补全 · 降级推导</span>', '<ul class="plain">'
  + '<li>候选卡 < 1200px 降单列；步骤列 ≤ 900px 堆叠置顶。</li>'
  + '<li>内容盒 max-width 1376 + 页边距 32，1440 基准无横向溢出。</li>'
  + '<li>当前步块面声明是唯一实底反白区——其他区域禁用大面积实底。</li></ul>');

// ── 03 密度与多端 ──
ov.density =
  blk('WHAT · 基准 <span class="role-badge">实测 · 画像基准</span>', '<p>基准 <b>PC 1440</b>（1280+ 可用）· 单端 · 静玻璃中密度：面板 padding 24-28 · 卡内 20-22 · 行高 1.7+ · 候选卡双列。</p>')
  + blk('USAGE · 多端降级 <span class="role-badge">AI 补全 · 断点推导</span>', '<ul class="plain"><li><b>&lt;1200px</b>：候选卡降单列，决策面板收窄。</li><li><b>≤900px</b>：步骤列堆叠置顶（移动可读降级，非目标端）。</li><li>移动端为降级态非设计目标——不为其调优玻璃效果。</li></ul>');

// ── 04 设计要求 ──
ov.rules =
  blk('CONCEPTUAL · 理念要求（通用 27 条 · 分组） <span class="role-badge">引用 · 通用规则模板</span>', '<ul class="plain">'
  + '<li><b>理念</b> —— 密度与呼吸按页面任务平衡；视觉层级与信息层级一致（字号+字重+颜色同表）；一致性优先于个性；一屏一个主行动；强调靠对比不靠加码。</li>'
  + '<li><b>颜色</b> —— 状态色语义成对（tint 底+同色字）；渐变只用于主按钮底/图标圆底/装饰区/遮罩；蓝只给可操作元素；主色派生色阶；灰带主色色相；对比度红线正文≥4.5:1。</li>'
  + '<li><b>字体</b> —— 字阶体系取档；正文行高 1.5、标题 1.1-1.25；字重 400/500-600/600-700；长文行宽 66ch；每屏 ≤2 族。</li>'
  + '<li><b>间距形状</b> —— 4pt 网格；相关近无关远（组内 ≤ 组间 1/2）；留白先于分隔线；深色海拔用表面色阶。</li>'
  + '<li><b>阴影</b> —— 阴影带色相；悬浮=强阴影+白描边环；两段式阴影；静态卡片弱阴影。</li>'
  + '<li><b>图像</b> —— 图像质量=观感大头；文字压图加同色相遮罩；占位要有设计。</li></ul>')
  + blk('SPECIFIC · 本项目实测沉淀（4 条） <span class="role-badge">实测 · 自举沉淀</span>', '<ul class="plain">'
  + '<li><b>链接必须像链接</b> —— 超链接色 #4C6FFF + 常显下划线（hover 加深）；墨色无下划线的链接用户无法识别（A 版定案回流）。</li>'
  + '<li><b>玻璃面板上禁实心大色块</b> —— 主按钮玻璃化：rgba 半透 + 白描边 + 彩色柔影（实心靛蓝块在玻璃上是「异物」）。</li>'
  + '<li><b>交付即更新链状态</b> —— 交付物产出后立即写回决策链，「进行中」状态卡交付后持续显示 = 误导。</li>'
  + '<li><b>候选必须有形态级差异</b> —— 同模板换参数（radius/色值）的趋同候选不合格。</li></ul>');

// ── 05 颜色 ──
ov.color =
  blk('PRINCIPLES · 原则 <span class="role-badge">实测 · 撞色策略拍板</span>', '<ul class="plain">'
  + '<li><b>撞色策略</b> —— 暖纸底 #FAFAF7 × 冷靛蓝 #4C6FFF：一个暖中性做画布，一个冷强调做操作。</li>'
  + '<li><b>清新纪律</b> —— 禁纯黑主色、禁深色实心大色块、禁霓虹；低饱和 + 大留白。</li>'
  + '<li><b>层级三层</b> —— 底色（纸白）→ 表面（白/浅靛）→ 强调（靛蓝），写样式只引用语义槽位。</li></ul>')
  + blk('APPLICATION · 主色 ramp（5 档 · 点击复制） <span class="role-badge">实测 · 锁值</span>', '<div class="swatches">'
  + sw('#3550C4', 'indigo-700', 'CTA 深 / 实底反白')
  + sw('#4C6FFF', 'indigo-500', '品牌主色 · 选中/可操作')
  + sw('#8B9BFF', 'indigo-300', '次级强调 / hover')
  + sw('#D6DCFF', 'indigo-100', '轻底 / 选中底')
  + sw('#EEF1FF', 'indigo-50', '代码块底 / 最浅组底')
  + '</div>')
  + blk('SEMANTIC · 语义层（8）+ 状态色（3） <span class="role-badge">实测 · 锁值</span>', '<div class="sw-group"><b>NEUTRAL · 底与文字</b><span class="role-badge">锁值</span></div><div class="swatches">'
  + sw('#FAFAF7', 'bg', '暖纸底')
  + sw('#F5F4F0', 'surface', '表面分层')
  + sw('#23283B', 'text-primary', '主文字 13.96:1')
  + sw('#7C86A0', 'text-secondary', '辅助注标专用 3.6:1')
  + sw('#E2E6F2', 'border', '边框')
  + '</div><div class="sw-group"><b>STATUS · 状态</b></div><div class="swatches">'
  + sw('#3D8B6E', 'success', '已完成')
  + sw('#D9932C', 'warning', '进行中/待核验')
  + sw('#C75450', 'danger', '危险/删除')
  + '</div>')
  + blk('USAGE · 使用规范 <span class="role-badge">实测 + 张力已知</span>', '<ul class="plain">'
  + '<li>靛蓝只给可操作元素与强调；正文恒 #23283B；辅助注标 #7C86A0 不承载正文与数据值。</li>'
  + '<li>状态标签成对：tint 底 + 同色字（玻璃签 = 色点 + 深字 + 灰 hex）。</li>'
  + '<li>已知张力：#7C86A0 对浅底 3.2-3.6:1 —— 维持注标用途，严格 AA 场景需微调 muted 令牌（锁值暂不动）。</li></ul>');

// ── 06 字体 ──
ov.type =
  blk('PRINCIPLES · 配对与三轨 <span class="role-badge">实测 · 用户拍板</span>', '<ul class="plain">'
  + '<li><b>标题</b> —— 思源宋体（Noto Serif SC）SemiBold/Bold：编辑文气的骨架。</li>'
  + '<li><b>正文</b> —— 系统无衬线（PingFang SC / Microsoft YaHei）：屏幕可读。</li>'
  + '<li><b>标注</b> —— Consolas / JetBrains Mono：代码块、hex、坐标、字段名。</li>'
  + '<li>uupm typography-cn 交叉验证：「文化、编辑、杂志、人文」✓</li></ul>')
  + blk('APPLICATION · 字阶真渲染（6 档） <span class="role-badge">实测 · 锁值字阶</span>',
  '<div class="type-row"><span style="font-family:\'Noto Serif SC\',\'Songti SC\',serif;font-size:28px;font-weight:700;color:#23283B">纸上见色，字里生风</span><span class="meta"><b>28 / Display</b> · 思源宋 700 · 行高 1.25 · 当前步标题</span></div>'
  + '<div class="type-row"><span style="font-family:\'Noto Serif SC\',\'Songti SC\',serif;font-size:20px;font-weight:600;color:#23283B">候选名与章节标题</span><span class="meta"><b>20 / Title</b> · 思源宋 600</span></div>'
  + '<div class="type-row"><span style="font-size:16px;color:#23283B">正文强调：决策内容的关键行。</span><span class="meta"><b>16 / Body-Em</b> · 无衬线 400</span></div>'
  + '<div class="type-row"><span style="font-size:14px;color:#23283B">正文示例：检验日常阅读的舒适程度与行高节奏。</span><span class="meta"><b>14 / Body</b> · 行高 1.7 · 默认</span></div>'
  + '<div class="type-row"><span style="font-size:12.5px;color:#5A6472">次级说明：提示语与尾注。</span><span class="meta"><b>12.5 / Caption</b></span></div>'
  + '<div class="type-row"><span style="font-family:Consolas,monospace;font-size:11px;color:#8A93A0">chosen: "靛蓝纸底" // 等宽标注</span><span class="meta"><b>11 / Mono</b> · Consolas · hex/字段名</span></div>')
  + blk('USAGE · 混排规范 <span class="role-badge">引用 · 通用</span>', '<ul class="plain"><li>禁阶梯外字号；中英混排等宽场景用 JetBrains Mono；全大写仅短标签并加字距 5-10%。</li></ul>');

// ── 07 间距 ──
ov.spacing =
  blk('PRINCIPLES · 4pt 网格 <span class="role-badge">引用 · 4pt 通用</span>', '<p>所有间距取 4 的倍数：4 / 8 / 12 / 16 / 20 / 24 / 28 / 32。组内间距 ≤ 组间距的 1/2；留白先于分隔线。</p>')
  + blk('APPLICATION · 间距档（实物） <span class="role-badge">AI 补全 · 静玻璃派生</span>', '<div class="space-ruler">'
  + '<div class="space-row"><span class="lbl">面板 padding</span><span class="comp-stage" style="padding:0;width:56px;height:28px"></span><span>28</span></div>'
  + '<div class="space-row"><span class="lbl">候选卡内 padding</span><span class="comp-stage" style="padding:0;width:44px;height:22px"></span><span>20-22</span></div>'
  + '<div class="space-row"><span class="lbl">候选卡间距</span><span class="comp-stage" style="padding:0;width:40px;height:18px"></span><span>18-20</span></div>'
  + '<div class="space-row"><span class="lbl">标题与正文间</span><span class="comp-stage" style="padding:0;width:28px;height:14px"></span><span>10-14</span></div>'
  + '<div class="space-row"><span class="lbl">图标与文字间</span><span class="comp-stage" style="padding:0;width:16px;height:12px"></span><span>8</span></div>'
  + '</div>')
  + blk('USAGE <span class="role-badge">引用 · 通用</span>', '<ul class="plain"><li>非网格数值就近归档不新造；分隔线是最后手段（分隔线+边框+阴影禁三件套齐上）。</li></ul>');

// ── 08 圆角 ──
ov.radius =
  blk('APPLICATION · 三档（实物） <span class="role-badge">AI 补全 · 基调派生</span>', '<div class="comp-stage">'
  + '<span class="radius-box" style="border-radius:6px">标签 6</span>'
  + '<span class="radius-box" style="border-radius:8px">控件 8</span>'
  + '<span class="radius-box" style="border-radius:10px">卡片 10</span>'
  + '<span class="radius-box" style="border-radius:999px;width:84px">徽标 圆</span>'
  + '<span class="stage-lbl">RADIUS · 只用 6 / 8 / 10 / 圆四档 · 静玻璃派生</span></div>')
  + blk('USAGE <span class="role-badge">AI 补全 · 派生</span>', '<ul class="plain"><li>玻璃容器 10 · 控件（按钮/输入）8 · 状态签/代码块 6 · 徽标全圆；禁档外圆角。</li></ul>');

// ── 09 阴影 ──
ov.shadow =
  blk('APPLICATION · 三影（实物） <span class="role-badge">AI 补全 · 基调派生</span>', '<div class="comp-stage">'
  + '<span class="shadow-card" style="box-shadow:0 4px 16px rgba(35,40,59,.08)">柔影<br>0 4px 16px · 8%</span>'
  + '<span class="shadow-card" style="background:#4C6FFF;color:#fff;box-shadow:0 4px 12px rgba(76,111,255,.35)">彩色柔影<br>主按钮专用</span>'
  + '<span class="shadow-card" style="border:1px solid #4C6FFF;box-shadow:0 0 0 3px rgba(76,111,255,.15)">focus 光环<br>3px · 15%</span>'
  + '<span class="stage-lbl">SHADOW · 阴影全部带靛蓝/墨色相 · 禁纯黑阴影</span></div>')
  + blk('USAGE <span class="role-badge">AI 补全 · 派生</span>', '<ul class="plain"><li>柔影=玻璃面板与静态卡；彩色柔影=主按钮独占；光环=focus 态独占；静态内容禁大阴影（阴影=海拔≠重要）。</li></ul>');

// ── 10 动效 ──
ov.motion =
  blk('PRINCIPLES · 克制纪律 <span class="role-badge">AI 补全 · 玻璃纪律推导</span>', '<ul class="plain"><li>淡入与位移 <b>200-300ms</b> ease-out；列表项 stagger ≤ 40ms；玻璃面板淡入配透明度渐变（0.6→1）。</li></ul>')
  + blk('USAGE · 禁令 <span class="role-badge">引用 · 通用</span>', '<ul class="plain"><li>禁视差 / 弹跳 / 大位移；禁装饰性循环动画；动效只服务于「东西从哪来」的空间叙事。</li></ul>');

// ── 11 组件 ──
ov.component =
  blk('PRINCIPLES · 静玻璃纪律 <span class="role-badge">实测 · 用户逐族拍板</span>', '<ul class="plain">'
  + '<li>玻璃只用于<b>容器层与控件层</b>；文字层/代码块/长文区<b>恒实底</b>。</li>'
  + '<li>磨砂 blur ≤ 12px（面板 10 / 顶栏 12 / 签 6）。</li>'
  + '<li>玻璃面板 = rgba(255,255,255,.66) + blur(10) + 白描边 rgba(255,255,255,.85) + 柔影 + radius 10。</li></ul>')
  + blk('APPLICATION · 五族实物（组件舞台） <span class="role-badge">实测 · 用户逐族拍板</span>',
  '<div class="comp-stage"><span class="dsbtn pri">主按钮</span><span class="dsbtn sec">次按钮</span><span class="dsbtn txt">文字按钮</span><span class="stage-lbl">按钮族 · h34 · 主=靛蓝玻璃+白描边(.38)+彩影 · 次=白玻璃靛字靛细边</span></div>'
  + '<div class="comp-stage"><span class="tagchip ok">● 已完成</span><span class="tagchip warn">● 待核验</span><span class="tagchip">● 进行中</span><span class="tagchip err">● 危险</span><span class="stage-lbl">标签族 · 玻璃签 rgba(255,255,255,.6)+blur(6)+白描边 · 色点+深字 · r6</span></div>'
  + '<div class="comp-stage"><span style="display:inline-block;width:220px;height:34px;line-height:34px;background:rgba(255,255,255,.75);color:#B9C0CE;font-size:14px;border-radius:8px;border:1px solid rgba(255,255,255,.85);padding:0 12px;box-sizing:border-box">请输入风格关键词…</span><span class="stage-lbl">输入族 · 白玻璃(.75)+blur(6) · focus=靛边+光环 rgba(76,111,255,.15)</span></div>'
  + '<div class="comp-stage"><span style="display:inline-block;background:rgba(255,255,255,.78);border:1px solid #E2E6F2;border-radius:10px;padding:12px 16px;box-shadow:0 4px 16px rgba(35,40,59,.08)"><b style="font-size:13px">候选卡片容器</b><br><span style="font-size:12px;color:#5A6472">白玻璃 .66 + blur(10) · r10 · 长文内容区退纯白</span></span><span class="stage-lbl">卡片族 · 内容区可退纯白保可读</span></div>'
  + '<div class="comp-stage" style="background:rgba(255,255,255,.66);backdrop-filter:blur(12px)"><span style="font-size:12.5px;color:#23283B"><b>顶栏</b> = 白玻璃条 blur(12) + 靛蓝当前态</span><span class="stage-lbl">导航族 · 侧栏恒纸白实底（不玻璃，保可读）</span></div>')
  + blk('USAGE · 次级组件派生 <span class="role-badge">AI 补全 · 派生</span>', '<ul class="plain"><li>徽标/空态/分割线/头像从五族派生：徽标=圆角全+玻璃底；空态=纸白+靛蓝线条插画位（本项目无图片位则纯排版）；分割线 1px #E2E6F2 或留白。</li></ul>');

// ── 12 图标 ──
ov.icon =
  blk('PRINCIPLES · Feather 线性 2px <span class="role-badge">实测 · 用户拍板</span>', '<ul class="plain"><li>stroke 2px currentColor · 24 网格 · ISC 许可 · 极简线性开山库——与静玻璃+文档编辑风气质同源。</li></ul>')
  + blk('APPLICATION · 常用图标实物（6 枚） <span class="role-badge">实测 · 库实物</span>',
  '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg><s>check</s></span>'
  + '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"/><polyline points="12 5 19 12 12 19"/></svg><s>arrow-right</s></span>'
  + '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></svg><s>settings</s></span>'
  + '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg><s>search</s></span>'
  + '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg><s>x</s></span>'
  + '<span class="icon-cell"><svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg><s>file-text</s></span>')
  + blk('USAGE · 补位与生成 <span class="role-badge">AI 补全 · 补位规则</span>', '<ul class="plain"><li>Feather 287 枚已停更——缺口图标用 <b>Tabler 同语法</b>（stroke 2px）补位，禁混用其他风格库。</li><li>库中确实没有的业务图标：按 PROMPT 母版生成（线性 2px · 24 网格 · 圆角端点）。</li></ul>');

// ── 13 图像 ──
ov.imagery =
  blk('WHAT · 无图策略 <span class="role-badge">实测 · 用户纠偏</span>', '<p>工作台为纯工具界面：无摄影/插画位；氛围由 <b>CSS 静玻璃渐变</b>（淡彩氛围斑 blur22-26 / op .25-.3）承担，非图片。</p>')
  + blk('USAGE · 保留策略（样品页出现配图位时） <span class="role-badge">保留 · 策略卡</span>', '<ul class="plain"><li><b>主用</b>：bailian-image-gen 生图（清新静玻璃系提示词：柔和渐变氛围 · 白玻璃质感 · 靛蓝点缀 · 大量留白）。</li><li><b>补位</b>：用户图包优先（真实感 &gt; 生成感）。</li><li><b>兜底</b>：纯色卡 + 构图说明，不阻塞流程。</li><li><b>禁止</b>：暗黑系 · 霓虹 · 重拟物 · 写实人物 · 低对比。</li></ul>');

// ── 14 设计禁令 ──
ov.bans =
  blk('CONCEPTUAL · 概念性禁令（9） <span class="role-badge">引用 · 通用模板</span>', '<ul class="plain">'
  + '<li>禁信息撑满 —— 布局要有呼吸感与主次</li><li>禁为留白牺牲信息密度（与上条成对）</li><li>禁让用户思考「这是什么」—— 图标必配文字标签</li><li>禁一屏多主任务</li><li>禁什么都居中</li><li>禁间距全程一个值</li><li>禁卡片套卡片</li><li>禁满屏毛玻璃与无目的光晕</li><li>禁标题加 emoji</li></ul>')
  + blk('SPECIFIC · 具体禁令（13 + 本项目 4） <span class="role-badge">实测 4 + 引用 13</span>', '<ul class="plain">'
  + '<li>禁裸 hex/裸值 · 禁纯黑阴影 · 禁魔法间距 · 禁双主按钮 · 禁阶梯外字号 · 禁状态标签不成对 · 禁颜色作唯一信息载体 · 禁混用图标来源 · 禁 z-index 自造 · 禁把 AI 补全值当实测 · 禁静态内容大阴影 · 禁分隔线+边框+阴影三件套 · 禁空态只有「暂无数据」</li>'
  + '<li><b>本项目补充</b> —— ⑭禁深色实心大色块压玻璃面板 ⑮禁参数化模板式趋同候选 ⑯禁纯黑主色（外部否决） ⑰禁候选与已锁风格混搭（单选整卡）</li></ul>')
  + blk('A11Y · 无障碍红线 <span class="role-badge">引用 · 红线</span>', '<ul class="plain">'
  + '<li>状态不只靠颜色 —— 颜色 + 文字标签双通道；转灰度自读一遍</li>'
  + '<li>图标必须可懂 —— 图标+文字；纯图形操作必带语义文案</li>'
  + '<li>对比度红线 —— 正文 ≥ 4.5:1 · 大字 ≥ 3:1（辅助色 #7C86A0 仅注标）</li>'
  + '<li>触控热区 ≥ 44px（含视觉外扩）</li></ul>')
  + blk('REVIEW · 审查顺序 <span class="role-badge">引用 · 顺序</span>', '<p class="note">层级 → 间距 → 排版 → 色彩 → 深度 → 图像 → 收尾。层级没理顺，间距对错无从谈起。</p>');

fs.writeFileSync(p, JSON.stringify(c, null, 2));
const total = Object.values(ov).reduce((n, v) => n + (typeof v === 'string' ? v.length : 0), 0);
console.log('14 章 case 级成文完成 · overview 总量 ' + Math.round(total / 1024) + 'KB');
