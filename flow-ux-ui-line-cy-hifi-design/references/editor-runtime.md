# 页面片段规范（editor-runtime）

> **V06 归属：附加A（转化可编辑版）专用**——编辑器直出线已随 V06 退役，本文件仅在阶段7 转化线使用；主流程（阶段1-6）不消费本文件。

U2 生产的核心法律：AI 生成的每个页面片段必须遵守本规范——这是可编辑、可构建、可验收的前提。产物为**纯声明式片段**，全部行为由编辑器运行时解释。

## 生成入口

```powershell
python scripts/validate.py
python scripts/build.py --check pages/                 # 片段预检（目录模式：合并全部片段补全跨页目标）
python scripts/build.py --pages pages/ --title "<项目名>" --start-doc intake/开工文档.md --output "build/<项目名>.html"
```

输出必须是新路径；构建器拒绝覆盖已有文件（保护用户编辑）。设计令牌用 `--design-system <json>`（默认 assets/design-system.json），令牌转成真实 CSS 变量与内嵌 JSON，不只是说明文档。

## 页面片段契约

- 页根节点：`<section class="screen" data-screen="唯一安全ID" data-name="页面名">`
- 内部结构：`.scr-head` → `.device.mobile|tablet|desktop`（端型按开工文档页面清单声明）→ `.viewport` → `.app` 或后台布局
- 最小可运行样例：`assets/starter-pages.html`；组件样式与插入模板见 `assets/editor-seed.html`
- 每个可编辑节点赋唯一 `data-eid`；容器用 `data-block`
- 交互绑定用 `data-on` JSON（属性内引号转义 `&quot;`）：
  `{"click":{"goto":"detail"}}`
- 支持的运行时动作：goto / back / close / sheet / toast / submit / tab / toggle / switch / check / scroll / link 等；新业务规则在运行时命名动作中实现，**禁止字符串 eval**

**构建校验（build.py PageValidator）**：页 ID 唯一、元素 ID 唯一、交互 JSON 合法、跳转目标存在、图片/音视频/海报一律 data URL 内嵌；片段**禁止**引入 script、iframe、外链样式、行内事件。复杂业务逻辑统一进受控运行时，不进片段。

## 标注规范（考核第 5 条）

每页片段携带标注声明（画布内 JSON，随快照与完整 HTML 保存）：

- 每个功能点一条：`功能描述` + `变更记录`（本期改动/新增），多行自由文本，可随时编辑
- 绑定 data-eid 语义身份（非屏幕坐标）——业务重绘按身份恢复
- 预览态"标注模式"下点选添加，不误触业务；编号徽章 + 说明卡；标注列表为汇总入口
- 旧 data-note 自动纳入

## 风格令牌应用与换肤生成规范

**令牌来源与继承纪律**：
- 令牌唯一正源=选型回传（`intake/selection-result.json` 的 skeletonTokens，契约见 solo-ui-line-cy-gui-style-picker `references/selection-contract.md`）；style-presets.json 九槽仅 picker 缺位兜底
- **键名逐字照正本表 `assets/token-keys.json`**：一律全小写连字符；表里每个键都写明了运行时把它送到哪个变量（emits）；表外参数是扩展参数，同样全小写连字符，运行时生成 `--sp-<键名>`，页面直接引用
- **选定即锁，U2 只扩不改**：skeletonTokens 已锁值（色板/字体/字阶/圆角/间距档/控件尺寸/阴影/motion 基准）在展开与生产中禁改——锁的是什么、值从哪来，见 solo-ui-line-cy-gui-style-picker `references/token-minimum.md`「取值」
- U2 全量展开（`--design-system design-system.json`）：在已锁值边界内扩间距阶梯/尺寸阶梯/密度/网格列数/motion 全套

**令牌扩域（禁硬值）**：
- 颜色/字号/圆角/阴影**之外新增**：间距（margin/padding）、控件尺寸（高度/最小宽）、网格列数、gap——**只能引用令牌**，禁自创硬值（lint 按正本表 `assets/token-keys.json` 核查，白名单外 px 值=FAIL）；风格需要的特例尺寸登记成扩展参数（如 `hero-height`），页面引用 `var(--sp-hero-height)`
- 品牌定制：替换槽内 `--brand*` 系变量后**先出首页高保真**作视觉基准，其余页面以它对齐
- 出稿内容遵守真实感等级：A 档按开工文档 §1 拍板的真实感等级与行业数据规则写真内容；B 档可示意但禁 lorem ipsum

**皮肤三层落地（U2 生产时一并产出，schema 见 `references/controlled-blocks.md`）**：
- L1 令牌集=STYLE-PACK.tokens（含形态参数与成功/风险/提醒语义色，按正本表送达各变量）；L2 按组件类覆盖样式=l2Overrides（族内皮差异的载体：令牌表达不了的组件形态差写这里；选择器写页面内的组件类，运行时会自动加页面容器与风格包前缀，所以写 `:root`/html/body 永远匹配不到）；L3 图标族=iconSet 指向的内联 sprite 多套备置，运行时按包显隐
- 配色变体=STYLE-PACK.palettes（色板级，风格槽胶囊读它）：品牌色盘那一版必须有，放第一套作默认；另按该风格的气质再配几套合适的，每包至少 2 套

**AI 判族（生成时现场判，零机械资产）**：
- 族=骨架一样。判骨架看四个方面，逐个风格判：**信息密度**（每屏信息单元多少）、**元素粒度**（以大块横幅/卡片/列表行/小部件哪种为主）、**布局范式**（单列/网格/分栏/流式）、**内容分布**（图主导/文主导/控件主导）。任一方面类型不同=不同族；间距大小这类参数差异不算骨架
- 反例："页面模块一一对应"不能当作同族依据——同一个产品的所有风格，模块都对得上；比稿卡若布局被任务书写死，骨架差异也会被抹平，判族前先确认卡是按风格自己长出来的
- 判完按四个方面逐个风格列给用户确认，再落 STYLE-REGISTRY；用户追问时拿这张表回答，不凭印象坚持
- 用户选中的同骨架风格全部进族，成员数不设上限；另外每族顺手送 1-2 个同族令牌包（靠形态参数区分，不靠换颜色）；跨族=生成级出口，产物内不做结构级切换

**多代理任务书同步**：分片任务书（§多代理生产）加两条指针：受控块 schema（controlled-blocks.md）+ 参数名正本（assets/token-keys.json）。

## 编辑与保存语义（产物自带，写给使用说明与验收）

- 打开默认只读；口令解锁（首次设置 ≥8 位，PBKDF2 落配置块，明文不落盘；重开重新锁定）
- 单击选择/双击改字/父级选择/跨容器拖拽（落点可见）/复制/缩进/拆包裹/隐藏恢复
- 拖拽 + 八方向控制点 + Shift 等比 + 菱形圆角点 + 形状切换；X/Y/宽/高/层级输入；原业务页默认支持直接调整，无需先转自由画布
- 左侧页面标签导航；插入组件与手机/平板/后台页面；页面管理改名/复制/排序/删除
- 保存双通道：**覆盖源文件**（File System Access 首次授权→句柄复用）或**另存/下载完整 HTML**（主动点击）；二者均保留全部页面/编辑器/口令/图片/标注/交互；失败保留修改不静默下载
- 续编：开工文档由构建经 `--start-doc` 注入交付 HTML 配置块（`prototype-start-doc`），续编的 AI 读它即知原始规格

## 多代理生产（页面 ≥8 时启用）

- 片段组织约定：`pages/` 按**站点导航树分文件夹**（`pages/商品/列表.html`、`pages/商品/详情.html`）——文件夹=一级栏目，与开工文档站点地图一致；构建按树深度优先遍历，**树序即页面顺序**
- 左侧页面标签自动按文件夹分组显示（可折叠组头）——**文件夹名就是用户看到的分组名，一律用中文栏目名**；页面名、模块名、页面描述同样用中文，不出现文件路径、英文名和内部编号（文件夹名、页面名、页头里的风格包/族编号由 build --check 拦截；模块名和页面描述靠自己守）；构建排序**目录优先、根级 `pages/*.html` 殿后**，组内按文件名排序
- 共享层先行：主代理产出设计令牌应用样例 + 母版页 + 导航/mock 框架 → 冻结
- 按页面清单分片（每代理 ≤5 页，禁止两个代理改同一文件）
- 任务书模板（每代理一份）：`本批页面清单（含树路径） | 片段规范指针（本文档） | 风格令牌值 | 该页交互声明 | 完成定义（--check 过 + lint 预检过；U2 自证=预检+技术检查，不截图——截图仅在质检②③档 U5 走查时拍）`
  > ⚠ 口径注记（2026-11-19）：`--check` 只是 dev-mode 预检，**不构成验收**——编辑器版产物的验收一律走正式链（lint→回执→build --start-doc→verify-interactions，见 editor-conversion.md 正式链节）。此处"完成定义"仅约束分片代理的自证边界，不等于产物验收口径。
- 回交：片段落 `pages/` + 截图落 `qa/`；主代理抽验

## 升级续编

`python scripts/upgrade_html.py <已有HTML> --output <新文件>`：仅接受已知格式，保留页面与口令，拒绝覆盖原文件；浏览器中未保存的内容无法恢复，先导出再升级。

旧世代可编辑原型（K2 家族）改走受控迁移：`python scripts/upgrade_html.py migrate-k2 <旧件> --output <新件>`——预检不符即具名拒绝（E-K2-*，exit 1 零产出），原件零字节不动。
