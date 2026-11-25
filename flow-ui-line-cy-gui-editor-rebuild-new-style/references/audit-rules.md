# 七轴 UI 走查规则清单

> 凝练来源（8 个源技能，2026-11-21 凝练）：
> solo-ui-line-jk-deep-review（编排/裁定纪律/严重度/触发器）、solo-ui-line-jk-accessibility-review（无障碍）、
> solo-ui-line-jk-layout-review（布局）、solo-ux-line-jk-text-review（文案）、solo-ui-line-jk-font-style-review（排印）、
> solo-ui-line-jk-color-review（色彩）、solo-ui-line-jk-detail-fix（打磨）、solo-ux-line-jk-motion-values（动效）。
>
> 本文件自包含：客户环境读不到源技能，本清单内所有规则、数值、公式均可独立执行，无外部依赖。

---

## 0. 裁定纪律（先读，约束全部七轴）

### 0.1 只收两类规则

本清单只包含两类规则，审查也只报这两类：

1. **触发器级硬伤**：无论项目风格指南写什么都不能豁免的失败（见 0.3 触发器清单）。
2. **有明确数值或公式的打磨规则**：如嵌套圆角公式、对比度阈值、时长表——判定不依赖主观感受。

**品味分歧不是 finding**：密度偏好、圆角大小偏好、语气偏好、色板记法选择、有无阴影的风格倾向——你 merely 不同意，不算发现。项目成文的惯例可以裁决品味分歧，但永远不能豁免触发器。

**一致性例外**：同一细节在项目内部做了两种做法（如一处 press 0.95、另一处 0.96），是 finding；项目内成文且一致的自选值（如全站 press 0.95、无阴影风格、既定密度）保留，不是 finding。

### 0.2 严重度

| 级别 | 定义 | 对应源阶梯 |
| --- | --- | --- |
| P1 | 阻断任务、误导用户、隐藏内容或控件、数据丢失风险、系统性反复失败；全部升级触发器 | HIGH |
| P2 | 明显损害理解、效率、适应性或一致性 | MEDIUM |
| P3 | 孤立打磨，任务影响有限 | LOW |

同级内按影响面排序：一条 token 或共享组件修复 outrank 同一症状在单个叶子组件里的重复。

### 0.3 升级触发器（P1 on sight）

属轴技能确认以下任一症状存在即为 P1，不因表面小而降级；触发器豁免任何报告上限，逐条全列：

1. 交互控件无可访问名。
2. 键盘可达控件无可见焦点指示。
3. 控件或路径 pointer 可达而键盘不可达。
4. 运动或自动播放内容无视 `prefers-reduced-motion`。
5. 内容或控件在 320px 宽或 200% 缩放下被裁剪、重叠或不可达。
6. 正文或控件文本的渲染对比度对未达其所需比值。
7. 状态或含义仅由颜色承载。
8. 破坏性动作无确认、无 undo、无区分处理。
9. 截断内容无法到达完整值。
10. 内容或控件只能越过滚动边缘或无可见线索的折叠才可达。
11. 错误未指名任何恢复方式。
12. 语义色反用（如 danger 色用于非破坏动作）。
13. 状态变化仅由运动承载（动画不跑时无颜色/图标/标签残留）。

### 0.4 走查程序

- **范围先行**：从请求与工作区解析屏幕/流程/功能/仓库范围并在输出中声明；覆盖范围内的全部状态（空、加载、错误、窄宽），存在即查。范围大到无法可信走查时，缩到一个完整流程（请求所指向的，或所有用户必经的入口路径），声明边界与排除项；不暗示未走查的表面被审过。
- **轴顺序**：无障碍 → 布局 → 文案 → 排印 → 色彩 → 打磨 → 动效。先基础后打磨，避免打磨掩盖基础失败。打磨发现永不 outrank 坏掉的交互。
- **证据**：每条 finding 引用 `path/to/file:line` 并附当前实现。仅源码不能支撑视觉发现（运行时行为定结果时须实查渲染态；由声明值必然推出的除外，如 320px 视口上的固定 384px 面板属源码发现）；仅截图不能支撑代码发现。无法运行的检查标 **Not verified**，未走查的轴标 **Not reviewed** 并注明原因——这两者都不是 finding。
- **系统性合并**：一个根因一条 finding，同一行列出全部已确认位置；规则归属其底层所属的轴，次生效写在理由里。
- **修复优先序**（多条可行时取最早）：① 删除（空间能承载的分隔线、高频交互上的动画、原生元素已冗余的 ARIA、无人 import 的字阶）→ ② 用平台（原生元素/原生控件/浏览器自带焦点环）→ ③ 复用项目已有（token、间距步、动效曲线）→ ④ 纠正数值（用本清单给出的精确值）→ ⑤ 新增。修复写在项目自己的写法体系里，不得要求换栈。
- **只读默认**：审查不改动源码，除非用户另要求按发现实施修复；实施后须重跑相关验证。

---

## 1. 无障碍轴

**原则**：做两次走查——纯键盘走查（每个流程无鼠标可完成）与读屏走查（每个控件播报名字、角色、状态）。发现须引用其违反的 WCAG 2.2 Level A/AA 条款号、AT 用户无法完成的具体任务、或 0.3 中的触发器；其余一切是推荐、永不 P1——这包括 AAA 条款、APG 约定、单 `<h1>` 与无跳级大纲、提交时验证优于禁用按钮、44px/40px 目标（大目标是启发式，保持既定可用的密度）。拿不准时取平台默认而非自定义重建，删 ARIA 优于加 ARIA。对比度测量归色彩轴；文案措辞归文案轴。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 1.1 | 每个交互控件的可访问名 | 无任何可访问名 = P1（触发器）。图标按钮 `aria-label` 须命名动作（"Delete project"）非字形（"Trash icon"/"X"）；可见标签文本须出现在可访问名开头；`aria-hidden` 不得落在按钮/链接/input 的祖先上（或改用 inert） | P1 / P2 |
| 1.2 | 键盘路径与 tabindex | pointer 可达而键盘不可达 = P1（触发器）。正向 `tabindex` = 违规，只用 `0`（加入自然顺序）与 `-1`（程序焦点）；组合控件用 roving tabindex（活动项 0、其余 -1），焦点须留在输入内的场景（combobox）用 `aria-activedescendant` | P1 / P2 |
| 1.3 | APG 键盘模式 | 非原生交互元素无键盘处理：Escape 关覆盖层、箭头键在组合控件内移动、Tab 在控件间移动、Enter/Space 激活按钮。`role="button"`/`role="tab"` 无 `onKeyDown` = 违规；真链接必须支持 Cmd/Ctrl/中键点击 | P2 |
| 1.4 | 焦点指示 | `outline: none` 无已验证替代 = P1（触发器）。样式用 `:focus-visible` 非裸 `:focus`；优先浏览器原生指示环；自定义环对它跨越的每个相邻色须 ≥3:1（1.4.11），`currentColor` 画的环同检；`2px` 实线周长 + 3:1 变化是 2.4.13 AAA 目标（推荐级）；forced-colors 模式下保留系统色 | P1 |
| 1.5 | 对话框焦点管理 | 打开时焦点移入、关闭时还原到触发器；优先 `<dialog>` + `showModal()`（背景惰性 + Escape）；自定义覆盖层须背景设 `inert`、自身 `role="dialog"` + `aria-modal="true"`。缺失 = 违规 | P2 |
| 1.6 | 命中区域 | WCAG 2.5.8 AA 基线 24×24 CSS px（或其例外），不足 = 违规；44×44（触屏）/40×40（桌面）为启发式不强制；扩展命中区不得互相重叠；装饰层（光晕等）须 `pointer-events: none`，否则吞噬下层控件点击 | P2 |
| 1.7 | 拖拽替代 | 每个拖拽交互须有单指针替代（按钮/菜单达成同一结果，2.5.7）；仅有 `onDragStart` 或拖拽库无替代 = 违规 | P2 |
| 1.8 | 表单标签 | 每个 input 有 `<label for>` 或包裹 `<label>`；placeholder 当 label = 违规；标签与控件共享一个命中目标（checkbox 与文本间无死区）；关于用户的字段须有有效 `autocomplete` token；禁止粘贴 = 违规（用户粘贴密码与验证码） | P2 |
| 1.9 | 提交验证与播报 | 禁用提交按钮守验证 = 违规（例外：标签写明唯一要求、如输入对象名的破坏性确认可保持禁用）；失败字段 `aria-invalid="true"` + `aria-describedby` 指向行内错误 + 焦点首个无效字段；`role="status"` 承载非紧急未绑定更新（toast/结果数），先渲染稳定空区域再更新文本（区域随文本一起挂载 = 违规）；`role="alert"` 只承载紧急未绑定错误（成功 toast 用 assertive = 违规） | P2 |
| 1.10 | 颜色冗余线索 | 状态仅由颜色承载 = P1（触发器）。须配图标/文本/下划线等第二线索（1.4.1） | P1 |
| 1.11 | prefers-reduced-motion | 运动、缩放、模糊须包在 `@media (prefers-reduced-motion: no-preference)` 内（opt-in）= 触发器级。不透明度淡入、加载 spinner、瞬时状态变化、短暂按压缩放留在外面；RM 下用 opacity 交叉淡化替换滑动/缩放，不瞬间移除元素；parallax 与 autoplay 全关 | P1 |
| 1.12 | 计时内容 | 移动/闪烁/滚动内容持续 >5 秒须有可见暂停控件；自动更新内容无论时长须有暂停（频率控制算数，2.2.2）；承载动作或错误的 toast 常驻至被关闭 | P2 |
| 1.13 | alt 文本 | `<img>` 无 `alt` 属性 = 违规；装饰图 `alt=""`、信息图描述含义、功能图描述动作（非画面内容）；tooltip 挂在原生 `disabled` 控件上 = 违规（改文字旁置或 `aria-disabled` 保持可聚焦） | P2 |
| 1.14 | 结构导航与缩放 | 标题描述其章节并成连贯大纲；一个可见主 `<main>`；重复导航在前时 "Skip to content" 为首个可聚焦元素。文本须存活 200% 缩放（1.4.4）；页面 320px 宽 reflow 无横向滚动（1.4.10）——320px 下裁剪/重叠/不可达 = P1（触发器）；viewport meta 含 `maximum-scale=1` 或 `user-scalable=no` = 违规 | P1 / P2 |

（聚焦元素完全藏于 sticky 头部之后的判定见 2.11 与 1.4，修复 `scroll-padding` 归布局轴。）

---

## 2. 布局轴

**原则**：布局定分组、对齐、间距与响应式结构，再用缩放、翻译、RTL 镜像对其做压力测试。本轴数值仅在项目没有自己的间距刻度或密度系统时适用，有则用项目 token——与起点值不同本身不是发现；发现需要可展示的失败：裁剪、重叠、镜像断裂、分组误读。命中区域与焦点行为归无障碍轴；圆角阴影归打磨轴；换行截断机制归排印轴；措辞归文案轴。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 2.1 | 组间距 | 组间距 ≥ 2× 组内间距：组内 8px 意味着组间 ≥16px。先用空间分组，背景形状次之，分隔线最后且仅当空间承载不了 | P2 |
| 2.2 | 控件可区分 | 交互元素须有背景形状、边框、下划线或固定放置区（如工具栏）；样式与旁边静态文本无异的控件读不出是控件 = 违规 | P2 |
| 2.3 | 顺序 | 视觉顺序 = DOM 顺序；用 `order`/`row-reverse`/grid placement 把内容移出源序列 = 违规。最重要内容靠顶部与前缘；行内识别内容在前、元数据与动作殿后 | P2 |
| 2.4 | 轨道溢出 | `grid-template-columns: … 1fr` 或持长文本/宽表格的 flex 子项溢出其轨道 = 违规；修复 `minmax(0, 1fr)` / flex 子项 `min-width: 0`。溢出导致内容裁剪/重叠 = P1（触发器），否则 P2 | P1 / P2 |
| 2.5 | 视口与尺寸陷阱 | `width: 100vw` = 违规（含滚动条致桌面横向滚动），用 `100%`；移动全高面板 `height: 100vh` = 违规，用 `100dvh`（软键盘只缩视觉视口，底部动作留在稳定 chrome）；装文本的盒用固定 `height` = 违规，用 `min-height` 或 `max-height` + `overflow-y: auto` | P2 |
| 2.6 | 响应式结构 | 断点来自内容而非设备预设；撑到放不下才折叠，先测最小与最大支持尺寸；可复用组件内的 `@media (max-width: …)` = 违规，改父级 `@container`；`container-type: inline-size` 落在无确定宽度的 flex item/inline-block/absolute 元素上 = 违规（size containment 会把收缩适应盒压到 0），给它确定宽度 | P3 |
| 2.7 | 安全区 | `env(safe-area-inset-*)` 而视口 meta 无 `viewport-fit=cover` = 违规（insets 解析为 0）；`*-inline-*` 逻辑属性与 `safe-area-inset-left/right` 物理值混用 = 违规（物理 left/right + 对应 inset + `[dir="rtl"]` 覆盖） | P2 |
| 2.8 | RTL 镜像 | 方向相关布局写成 leading/trailing：`margin-inline-start`、`padding-inline-end`、`inset-inline-start`、`text-align: start`；物理 left/right 仅留给物理几何（安全区）。镜像 UI 上 `float: left` = 违规（`float: inline-start`）；`translateX` / `background-position: left` 无 `[dir="rtl"]` 覆盖 = 违规（二者无逻辑形态）。镜像断裂即可展示失败 | P2 |
| 2.9 | 隐藏内容线索 | 离屏或折叠内容无可见线索 = P1（触发器）；用项目既定线索、让下一项探出边缘 16–32px、或折叠控件 | P1 |
| 2.10 | 截断回径 | 用户需要的被截断值无路径到全文（无展开控件/详情视图/键盘可达 tooltip）= P1（触发器）；截断机制本身归排印轴 | P1 |
| 2.11 | sticky chrome | sticky 头部未设 `scroll-padding-block-start` = 违规，值 = 头部高度；否则锚点目标与聚焦元素落其下方（焦点被完全遮住同时触发无障碍轴 P1） | P2 |
| 2.12 | 间距起点（无既定密度系统时） | 相邻 bordered/filled 控件间 12px 起；borderless 文本/图标控件可见字形间 24px（计各自 padding）；紧凑布局可更小，前提是命中区不重叠且控件可区分；内容布局中全宽按钮收进版心，移动端约 16px 起内缩 | P3 |
| 2.13 | 增长与裁剪 | 文本容器用 `max-width` + `min-height`，禁固定宽高、行可换行；翻译使字符串变长且短串比例增长更大（单词按钮标签是屏上最险物），用伪本地化与德语等长串 locale 测试；关键动作不得停在缩放/缩放/滚动会裁剪它的位置——被裁 = P1（触发器）；背景媒体可出血到视口边缘，控件与文本留在版心与安全区内 | P1 / P2 |

---

## 3. 文案轴

**原则**：管"字写的是什么"，不管"字长什么样"（渲染归排印轴）。先盘存再审查：找翻译调用（`t(`、`i18n.`、`<FormattedMessage`、`$t(`）与其读取的 locale 文件（`locales/**/*.json`、`messages/*.json`、`*.po`、`*.strings`，文案也可能来自 CMS/API），列出每个对象的名词与每个动作的动词，记录各元素类型的大小写与语气指南；新文案用清单上的词。刻意的品牌声音不是缺陷——只有造成不一致、歧义、翻译风险或语气与赌注不匹配时才报；纯属你口味的改写不是 finding。语气随赌注伸缩：成功/引导/空态可轻、常规操作与设置中性、错误与破坏性确认平静平白零玩笑、数据丢失与安全严肃明确。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 3.1 | 术语一致 | 同一事物两种叫法 = 违规（菜单里 "Archive" 就不能 toast 里 "Move to storage"）；多步流程一套词汇贯穿（进入 "Get started"、推进 "Continue" 或 "Next" 二选一、收尾 "Done"）；教学文案对读者直称 "you"，错误里 "we" 是推诿（"Unable to load content. Check your connection and try again."）；禁同一流程内混用人称（"My account" 挨着 "Your settings"） | P2 |
| 3.2 | 链接目的地 | 链接文本脱离上下文须可懂（读屏用户按链接列表导航）：`Click here`/`here` = 违规；同页两个 "Learn more" = 违规，逐个加后缀（"Learn more about exports"） | P2 |
| 3.3 | 错误说怎么修 | 错误未指名恢复方式 = P1（触发器）。错误是指令且在失败字段旁：坏例 "That password is too short"/"Invalid date"/"Oops! Something went wrong."，好例 "Choose a password with at least 8 characters"/"Enter a date as DD/MM/YYYY"/"Unable to save. Check your connection and try again."；无责备、错误文案无感叹号；正向措辞（"Use at least 8 characters" 非 "Don't use fewer than 8"）；已知要求在输入前以 helper text 展示；同一错误反复触发 = 改交互使其不可能发生 | P1 / P2 |
| 3.4 | 动词开头按钮 | 按钮标签以命名动作的动词开头："Send"/"Save draft"/"Delete project"；`OK!`/`Let's go!`/裸 `OK` = 违规 | P2 |
| 3.5 | 图标按钮名 | 图标按钮可访问名命名动作（"Delete project"/"Close dialog"）非字形（"Trash icon"/"Close icon"/"X"）= 违规 | P2 |
| 3.6 | 破坏性保护 | 可逆且高频（归档/移动/删入回收站）→ 立即执行并就地给 undo："Project archived. Undo"；不可逆、影响他人或批量销毁 → 先确认；破坏性动作无确认、无 undo、无区分处理 = P1（触发器） | P1 |
| 3.7 | 确认对话框配方 | 标题命名动作与对象（"Delete 'Q3 report'?"），`Are you sure` = 违规；正文说清丢失什么、什么不可恢复（适用时带计数）；按钮动词+对象（`Delete project`/`Cancel`），`Yes`/`No` = 违规；账号/工作区/仓库级要求输入对象名方可执行 | P2 |
| 3.8 | 字符串完整构建 | 句子碎片拼接（`"You have " + n + " new messages"`、模板字面量持碎片）= 违规（各语言语序不同），写单条消息加占位符；手搓复数（`n === 1 ? "" : "s"`）= 违规（许多语言多于两种复数形式），用 locale 复数规则；`toLocaleDateString()` 无 locale 或 `getMonth()` 手搓日期 = 违规，数字/日期/列表走 `Intl` | P2 |
| 3.9 | toggle ON 态 | 开关标签描述开启时发生什么（"Send read receipts"）；`Don't`/`Disable`/`Hide` 开头 = 违规（双重否定）；引用设置直接链接（"Notification settings"），不描述路径（"Go to Settings > Notifications > Email"） | P2 |
| 3.10 | 空态指向 | 空态须说明此地是什么 + 如何填充 + 一个明确下一步（"No projects yet" + 说明 + "Create a project"），裸 "No results." = 违规；过滤空态点名查询并给出口（"No results for 'quarterly'. Clear filters"）；持久信息不得驻留空态（内容一出现即消失） | P2 |
| 3.11 | 占位符示例 | placeholder 显示字段所接受格式的真实示例（`name@example.com`、`DD/MM/YYYY`），放指令 = 违规 | P2 |
| 3.12 | 冗余与大小写打磨 | `successfully` 删（"Changes saved"）；例行指令删 `Please`；每元素类型一套大小写策略（项目无政策时用 sentence case），`Save Changes` 挨着 `Discard changes` = 违规 | P3 |

---

## 4. 排印轴

**原则**：管文字如何渲染（字阶、间距、字体特性、换行断字、截断省略、标点）。本轴有精确值的项——unitless line-height、`18px` 以下字重 400+、60–75 字符行长、iOS `16px` 输入、变动数值上的 `tabular-nums`——缺失即发现；letter-spacing、字体搭配、字阶比例是启发式，只在破坏项目自己的字阶时才报。禁主动提议换字体（收费或免费），除非任务本身就是换字体。措辞归文案轴；语义标题结构归无障碍轴；对比度测量归色彩轴。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 4.1 | 字重地板 | `18px` 以下用字重 100–300（`font-thin`/`font-light`）= 违规，改 400+；100–300 属于 28px 及以上且即便如此也须对背景核查 | P2 |
| 4.2 | 行高纪律 | `line-height` 用 px/rem = 违规，必须 unitless（随字号缩放）；角色值：display `1.1`、headings `1.2`–`1.3`、body `1.5`–`1.6`（偏离 = P3）；换行达三行及以上的文本（描述、卡片正文、高度受限的行）`line-height` < `1.4` = 违规（`leading-none`/`leading-tight` 落在此类文本上） | P2 / P3 |
| 4.3 | 行长上限 | 长文行长须有上限且落在 60–75 字符；任何单位均可，但必须有 cap 且落区间内，无 cap = 违规 | P2 |
| 4.4 | iOS 输入字号 | input 文本 <`16px` = 违规（iOS Safari 整页缩放）；修复二选一：移动端放大（`text-base sm:text-sm`），或保持 `font-size: 16px` 用 `transform: scale()` 渲染目标尺寸——审查时问设计要哪种或两个都给 | P2 |
| 4.5 | 字号地板 | 长文正文 `16px` 起（有可命名理由才偏离：字体偏小/窄行宽/密专业工具）；inputs 与 menus `14px` 起；captions `13px`；极少低于 `12px` | P3 |
| 4.6 | 表格数字 | timer、counter、price、数字表列无 `font-variant-numeric: tabular-nums` = 违规（逐位等宽防跳动）；散文中的数字保持比例字型；`font-feature-settings: "tnum"` = 违规，用属性形式 | P2 |
| 4.7 | 属性优先于原始标签 | `font-variation-settings: "wght"/"opsz"` = 违规（用 `font-weight`；去掉 `"opsz"` 让 `font-optical-sizing: auto` 生效）；`font-feature-settings: "tnum"/"zero"` = 违规（用 `font-variant-numeric: tabular-nums`/`slashed-zero`）；原始标签只留给自定义轴（`"GRAD" 80`）与无属性特性行（`"ss01" 1`） | P3 |
| 4.8 | 字体加载 | 声明的 `font-weight` 在已加载 `@font-face` 中无对应字重 = 违规（浏览器合成扭曲字形），加载该字重或改用家族自带值；body/界面文本上 `font-synthesis: none` = 违规——仅在验证 fallback 栈后、且只禁不需要的 longhand | P2 / P3 |
| 4.9 | 换行控制 | `text-wrap: balance` 落在段落上 = 违规（用于标题/短描述，Chromium 六行以上忽略；段落用 `pretty` 防孤词）；应用 UI 中 `text-align: justify` = 违规（`text-align: start`，justify 只属于特定编辑版式）；长词/链接/ID 可能逃逸容器处加 `overflow-wrap: break-word`；标签徽章上换行会显得坏时 `white-space: nowrap` | P3 |
| 4.10 | 截断机制 | 单行三件套：`overflow: hidden` + `text-overflow: ellipsis` + `white-space: nowrap`（Tailwind `truncate`）；多行：`display: -webkit-box` + `-webkit-box-orient: vertical` + `-webkit-line-clamp: N` + `overflow: hidden`（Tailwind `line-clamp-N`）；`-webkit-line-clamp` 缺 `display: -webkit-box` = 违规。截断后回径归布局轴 | P2 |
| 4.11 | 排版标点 | 渲染文本用排版字符：`...`→`…`、`--`→em/en dash、连字符范围→en dash = 违规；代码保持直引号；文案存自然大小写、显示用 `text-transform`（重设计不须改文案），大小写写死在 copy = 违规 | P3 |
| 4.12 | 单位纪律 | `letter-spacing` 用 px = 违规，用 em（值：`24px`+ 标题 `-0.01em` 至 `-0.02em`；`14px` 及以下大写标签 `0.05em`；正文 0；`font-kerning: none` 永不是修复）；body `font-size` 用 px = 违规，用 rem（读者浏览器字号仍生效） | P3 / P2 |
| 4.13 | 双向与可选性 | 混合方向值（名字/数字/URL）无 `<bdi>` 或 `dir` = 违规，禁手搓数字重排；设置 `lang`（引号/断字/发音）与 `dir`；`user-select: none`/`select-none` 落在布局根或文本容器 = 违规——仅限拖拽/手势表面；`-webkit-font-smoothing` 落在组件内 = 违规，根上一次（配 `-moz-osx-font-smoothing: grayscale`） | P2 |

---

## 5. 色彩轴

**原则**：系统是 ramp 不是颜色——一条 neutral ramp、一条 accent ramp、只建产品实际渲染的状态 ramp；每个 step 因某个角色而存在（页面背景/组件 hover/边框/实心填充/正文），无角色消费的 step 不生成。primitive 按值命名（`--blue-600`）且永不进组件；semantic token 按角色命名（`--color-text-secondary`）指向 primitive，是组件唯一引用层。感知亮度一律指 OKLCH `L`（0–1）。**对比度纪律：没实测过不得报对比度值，能算的颜色禁止估算**；记法、带色调的中性色、渐变插值空间是项目选择不是发现；坏的角色映射、失败的对比对、出 gamut 的 step 才是发现。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 5.1 | 对比度实测程序 | 报告中的对比度值未经实测 = 该 finding 无效。测前景对其**实际渲染所对的背景**（非页面背景；含 alpha 合成与下层图像），明暗两主题都测；无法实查的标 Not verified | P1 |
| 5.2 | 对比度阈值 | 失败对 = P1（触发器）。文本 4.5:1（1.4.3 AA）；大文本（≥`24px` 或 ≥`18.67px` bold）3:1；UI 组件边界/状态/有意义图形 3:1（1.4.11）；inactive 控件与 logo 豁免。修复改亮度（对比度响应的通道）非色相；报告失败对 + 实测值 + 未达阈值，颜色本身留着（设计决定，受托才改，改后重测） | P1 |
| 5.3 | 白字压中饱和填充 | `text-white` 落在 Tailwind `500` 系填充上 = 违规——多数 `500` 色相与若干 `600` 色相对 4.5:1 失败；实测并报告 | P2 |
| 5.4 | alpha 底色 | 文本压在带 alpha 的颜色上（`/50`、`rgba(`、`color-mix(` 混 `transparent`）= 违规——须测合成后的渲染结果，或改用实心 token | P2 |
| 5.5 | 组件内颜色字面量 | 组件文件内有 hex/`rgb(`/`oklch(` 字面量而项目已有对应 token = 违规，复用或补角色 token（用项目记法）；全 hex 代码库里孤立一个 `oklch(` = 违规（除非迁移在范围内） | P2 / P3 |
| 5.6 | 组件引 primitive | 组件引用 primitive（`var(--blue-600)`、`bg-blue-600`）= 违规——semantic token 指向 primitive，组件只引 semantic 层（这是主题换色不触组件的接缝） | P2 |
| 5.7 | 语义命名 | 语义名含色相或组件名（`--color-blue-button`、`--color-sidebar-gray`）= 违规，按角色改名（`--color-accent-solid`、`--color-bg-surface`）；`--color-primary` 与 `--color-text-primary` 并存 = 违规，品牌 token 改名 `accent` | P2 |
| 5.8 | token 跨角色借用 | `border`/`separator` token 出现在 `color:`、`text` token 出现在 `background:` = 违规——今天值恰好对，边界变浅文本跟着变；缺角色就补 token | P2 |
| 5.9 | 语义色反用 | 语义色用于违背其含义之处（danger 色用于非破坏动作）= P1（触发器） | P1 |
| 5.10 | 一色一义 | OKLCH 色相 `15°` 以内视为同色；同色承担两种含义 = 违规；状态色相距 accent 色相 <`15°` = 违规——移开至少 `15°` 或给破坏动作区分处理；颜色永不单独承载含义（配图标/标签，归无障碍轴） | P2 |
| 5.11 | 一视图一填充 | 填充色编码主强调时，一个主操作获得填充、peer 保持中性 = 违规多个同级互抢；填充给背景而非标签（实心按钮远处读作主操作，accent 文字按钮读作链接）；已用其他方式建立层级的多彩背景（编码不同状态/类别）可保留 | P3 |
| 5.12 | 暗色主题 | dark token 等于 light ramp 反序 = 违规——降 accent chroma、拉开 dark 端、重测每一对；`prefers-color-scheme` 与 `.dark` class 两套切换机制并存 = 违规，全站取一 | P2 |
| 5.13 | ramp 纪律与 gamut | 一条 ramp 贯穿单一色相、中段最鲜、亮端步进更细（`50`–`200` 每步 OKLCH `L` ≈`0.04`–`0.05`，与中段同距 = 违规）；chroma 按各 hue 自身最大值的比例取，跨 hue 复制同一数值 = 违规；仅明度差异的 `hsl(` ramp = 违规（恒定感知色相重建）；无角色消费的死 ramp = 违规；`oklch()` chroma 超 sRGB 且未先声明 sRGB 值 = 违规——先声明 sRGB 值，`@media (color-gamut: p3)` 内再给鲜艳值 | P3 |

---

## 6. 打磨轴

**原则**：本轴持有表面与图标的精确值。数值是精确值不是可近似的范围：`oklch(0 0 0 / 0.1)` 不等于 `0.15`，`1.5px` 描边不等于 `2px`；例外是光学微调与同心 padding 截断——它们是起点、靠眼判断。保留项目的组件库、token 与密度；项目内成文且一致的惯例（如无阴影风格）是偏好不是发现，同一细节项目内两种做法是发现。打磨在交互健全之后进行，打磨发现永不 outrank 坏掉的交互。色彩 token 与对比度归色彩轴，动效归动效轴。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 6.1 | 嵌套圆角公式 | 嵌套表面共享可见且均匀的内缩时：**外半径 = 内半径 + padding + 边框宽度**；带 padding 的父与子用相同 `border-radius` = 违规。例外：padding 超 `24px`、或 padding 故意不对称时，按独立表面各守各的 radius token | P3 |
| 6.2 | 光学对齐 | 几何居中显得歪时按眼微调（起点值）：按钮图标侧 padding 少 `2px`；播放三角朝其指向偏移；不对称字形在 SVG 自身内修 | P3 |
| 6.3 | 阴影替代深度边框 | 仅为制造深度而存在的边框 = 违规，换分层透明 `box-shadow`；结构边框保留：分隔线、表格单元格、选中态、表单输入（输入边界需 3:1 非文本对比度，归无障碍轴） | P3 |
| 6.4 | 阴影环兜底 | `box-shadow: 0 0 0 1px` 环旁无 `border` = 违规——加 `border: 1px solid transparent`（forced-colors 模式移除一切 `box-shadow`，靠这条仍能画出边缘） | P3 |
| 6.5 | 图片描边 | 内容图片描边：`1px` outline 内缩 `1px`；亮色 `oklch(0 0 0 / 0.1)`、暗色 `oklch(1 0 0 / 0.1)`；用调色板近黑/着色中性/accent 色 = 违规（色调在图片边缘显为彩色 fringe）；透明 artwork（logo/插画）跳过描边 | P3 |
| 6.6 | hover 门控 | hover 专属样式未包 `@media (hover: hover)` = 违规——触屏上 `:hover` 点按后锁存，读作卡死的选中态（Tailwind 4 的 `hover:` 已编译进该查询，Tailwind 3 没有）；控件自带按压态时设 `-webkit-tap-highlight-color: transparent` 防灰色闪现叠加 | P2 |
| 6.7 | 滚动遏制 | 可滚动 dialog/drawer/menu/side panel 无 `overscroll-behavior: contain` = 违规——滚到尽头不得带动背后页面 | P2 |
| 6.8 | 图标描边匹配字重 | 图标渲染描边须跟随相邻文本字重：`1.5px`（字重 400）→ `2.5px`（字重 700）连续对应；每 surface 一个图标库 | P3 |
| 6.9 | 图标着色 | 图标 SVG 内硬编码 `fill="#…"`/`stroke="#…"` = 违规——用 `currentColor`，hover/选中/disabled 状态色取自 CSS color 与 opacity，不用独立资产；outline 为默认变体，fill 标记激活态 | P3 |
| 6.10 | RTL 图标镜像 | `dir="rtl"` 下仅镜像含义跟随阅读方向的图标；方向无关图标（如播放）不镜像 | P3 |

---

## 7. 动效轴

**原则**：第一问是"该不该动"，答案常常是不——删动画是合法修复；动效只加在请求要求或原则呼唤之处。数值分两类：按压缩放、图标交叉淡化、stagger、spring bounce 是**精确值**（`0.96` 不等于 `0.95`）；时长、缩放、位移表是桌面 web 的**起点**，按元素大小与行进距离以眼调整，移动端全屏过渡更长更远。保留项目的动效库、token 与曲线，本清单无值处匹配项目动效语言；项目内成文且一致的值（如全站 press 0.95）保留，同一细节两种做法是发现。reduced-motion 要求、暂停控件、拖拽单指针替代归无障碍轴。

| # | 检查什么 | 违规判定与精确值 | 严重度 |
| --- | --- | --- | --- |
| 7.1 | reduced-motion 门控 | 运动/模糊/进出缩放未门控于 `prefers-reduced-motion: no-preference` = P1（触发器）；全局样式表 reset 只够覆盖 CSS 过渡，够不到 Motion 组件——`motion.*`/`m.*` 仅靠样式表 reset = 违规（`MotionConfig reducedMotion="user"`），Motion 动画 `filter` 时仅靠 MotionConfig 亦不够（按 `useReducedMotion()` 分支）；RM 下用 opacity 交叉淡化替换而非瞬间移除；按压缩放保留（短暂反馈非位移） | P1 |
| 7.2 | 运动非唯一通道 | 动画状态变化无残留静态线索（颜色/图标/标签）= P1（触发器） | P1 |
| 7.3 | 高频瞬时 | 按键、行 hover、tab 背后内容必须瞬时，或 ≤`150ms` 的 `opacity`/`background-color` 过渡，更长的表达性动画 = 违规（tab 指示器可在 tab 间行进）；每天多次打开的菜单跳过开场动画、仅动画关闭（context/command 菜单算，设置页菜单不算）；表达性动效留给低频时刻（首载、成功态、空态） | P2 |
| 7.4 | 过渡非 keyframes | 交互状态变化用 CSS transitions/springs（中途反向可重定目标）；`animation:` 落在 `:hover`/`.open` 等被切换的 class 上 = 违规（keyframes 时间线固定不可逆，只留给跑一次的序列） | P2 |
| 7.5 | 具名过渡属性 | `transition-all`/`transition: all` = 违规，具名变化属性；只动画 `transform`/`opacity`/`filter`/`clip-path`（跳过布局；测量过的高度是唯一值得动画的布局属性）；base 规则 `opacity: 0` 仅靠 animation 揭示 = 违规（隐藏态写进 `from` keyframe + `animation-fill-mode: both`）；`will-change: all` 或落在从不动画的元素上 = 违规——仅见首帧卡顿或 `1px`–`2px` 起落位移后加，具名属性且限 transform/opacity/filter | P2 / P3 |
| 7.6 | 时长表（桌面 web 起点） | tooltip 等小元素 `150ms`；dropdown/menu `250ms`；modal/drawer/panel `350ms`–`450ms`；exit 须短于 enter（250 开 → 150 关），exit 与 enter 同时长同距离 = 违规（exit 用 opacity + `4px` blur + 固定 `12px` 位移 @`150ms` ease-out，永不全容器高度；仅当目的地有意义——如 drawer 关闭——才滑全出） | P3 |
| 7.7 | 缓动 | 进出与状态变化 `ease-out`；连续循环（loading）`linear`；有物理感的（sheet 开、形变、drag 落定、slider thumb）用 spring；仅变 color/opacity 的过渡用 spring = 违规（肉眼不可辨），改 `ease-out` + 时长；CSS 无实用 spring，无动效库时以 `cubic-bezier(0.2, 0, 0, 1)` 同时长替代 | P3 |
| 7.8 | spring 参数 | 写作 `{ type: "spring", duration: 0.3, bounce: 0 }`，**bounce 恒为 0**，非 0 = 违规；`0.3` 小切换、`0.4` tab 指示器、`0.45` drawer；同一 surface 共享 spring 时设一次于 `MotionConfig`，子元素不带 `transition` | P3 |
| 7.9 | 缩放与位移 | popup（tooltip/dropdown）enter 自 `0.96`–`0.97`；modal/panel enter 自 `0.98`–`0.99`（大面从 `0.95` 变化过多屏幕）、exit 至 `0.99`；enter scale 低于 `0.98` = 违规。按压：`0.96` @`150ms` `ease-out`（精确值），`active:scale-95` 等低于 `0.96` 且项目无统一按压值 = 违规；disabled 未排除 = 违规（`:not(:disabled):active` 或 `enabled:active:`）。`transform-origin` 指向打开它的触发器（角标从角缩放，居中 dialog 用中心），缺失/`origin-center` = 违规。位移表：文本交换 `4px`、页面过渡 `8px`、dropdown/tooltip 及多数元素 `8px`–`32px`、sheet/side panel 至多自身宽高的 `70%`；dropdown 背离触发器、panel 从被打开的一侧进入 | P3 |
| 7.10 | 入场纪律 | stagger 仅用于低频入场且按语义分块（标题/描述/动作），块间 `100ms`，每块 opacity + `4px` blur + `12px` translateY @`300ms` `ease-out`；例行交互禁 stagger。状态交换的 `AnimatePresence` 未设 `initial={false}` = 违规（首渲染不播状态动画；hero 类有意入场除外） | P3 |
| 7.11 | 图标交叉淡化 | 低频状态切换的图标交换（播放↔暂停、复制↔已复制）用交叉淡化：scale `0.25`→`1`、opacity `0`→`1`、blur `4px`→`0`；有动效库用 `0.3` spring，无库双图标共存 DOM、`300ms` `cubic-bezier(0.2, 0, 0, 1)`；tab 图标交换与行 hover 显露的动作归高频规则（7.3） | P3 |
| 7.12 | 共享布局 | 无关元素（列表行、两个 tab 组）共享同一 `layoutId` = 违规，每对元素专属 id（由条目 key 构建）；`layoutId` 元素带 `initial`/`exit` = 违规（它们在移动途中运行；origin 保持挂载时才用 `AnimatePresence` 包住新元素）；`AnimatePresence` 交换子元素无随状态变化的 `key` = 违规；mode 按位置选：`sync`（默认，子元素异地可同时动）/`wait`（新者待旧者离场）/`popLayout`（同位交叉淡化）；跨状态差异值（如 `borderRadius`）走 `animate` 不走 class；`LazyMotion` 下 `layoutId`/`drag` 需 `domMax`（`domAnimation` 下不运行） | P2 / P3 |
| 7.13 | 高度动画 | 内容变化的容器两侧保持 `height: auto`，用 `ResizeObserver` 测内层 wrapper 动画外层；测量 ref 落在高度动画元素自身 = 违规（须内层 wrapper）；内容挂载前测量为 0，首态给固定高度；每次按键都变的内容（结果列表）跳过动画 | P3 |
| 7.14 | 拖拽 snap | snap 开合的行未设 `dragMomentum={false}` = 违规（落在 snap 点而非速度抛点）；`dragConstraints` = 最外 snap 点；`dragElastic: 0.05`；释放时以 spring 动画至最近 snap 点，提交阈值 = 到该点距离的一半；优先 Motion gesture props（`whileTap` 也响应 Enter 键，`whileHover` 忽略触屏） | P3 |
| 7.15 | 主题切换抑制 | 存在颜色过渡 + 主题切换而无 `disableTransitionOnChange` 或等效覆盖 = 违规——切换时禁用所有过渡、强制样式 flush、下一帧恢复，否则所有颜色过渡齐发拖影 | P3 |

---

## 8. 功能覆盖对账（与七轴并行的独立关，页面级；条目原文自源跑批细则逐字搬入）

> 【适配注记】"功能点断言清单"提取源=本包供料（开工文档 1.0+用户输入文档裁决原文）；执行时机=第 3 步走查闭环内、七轴规则审之前（缺功能的页修起来动结构，先查免得走查返工）。

**功能覆盖矩阵（每批交付必附，没矩阵不验收）**：独立只读审计（没参与制作的代理）拿功能点断言清单（开工文档+盘问记录提取）逐条在产物里找承载证据，产出**双向矩阵**——文档有→稿无=缺功能（硬伤必修）；稿有→文档无=画师自主补充（好的吸收进页面地图沉淀，坏的清掉）。页面地图吸收口径：**可补业务/用户场景，界面元素不补**（业务语言进地图，控件语言归画师）。**每个用户操作追加操作真实性三问**（对照端型约束文件）：这个操作在端型生态里存在吗？操作者是谁（用户/平台/宿主）？业务流哪一步有出处？——三问答不出=语义越界（实例："微信已绑定"收款渠道），从产物中清除。

---

## 附：七轴条目计数

| 轴 | 条目数 | P1 触发器对应 |
| --- | --- | --- |
| 1 无障碍 | 14 | 1.1/1.2/1.4/1.10/1.11/1.14 |
| 2 布局 | 13 | 2.4/2.9/2.10/2.13 |
| 3 文案 | 12 | 3.3/3.6 |
| 4 排印 | 13 | — |
| 5 色彩 | 13 | 5.1/5.2/5.9 |
| 6 打磨 | 10 | — |
| 7 动效 | 15 | 7.1/7.2 |
| **合计** | **90** | 覆盖 0.3 全部 13 条触发器 |
