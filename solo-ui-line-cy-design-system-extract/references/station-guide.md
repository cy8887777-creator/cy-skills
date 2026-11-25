# 站序细则（4 站）

每站**只允许做该站规定的事**；站间**不跳步**；通过/失败由脚本退出码决定。

---

## ① 输入识别 + 路由

**职责**：按 `references/activation.md` 锁定 6 项参数（只问未决项），按路由表选引擎。

**站① 前置（第 ⓪ 步）**：先跑 `python scripts/doctor.py` 体检——`ready=true` 直接进本站；`blocking_fail` 非空 → 向用户报告修复命令并停下等指令（禁自动 pip install）；仅 `url_only_fail` → 记录待裁决带项进本站，路由**避开 B-2**（要做 URL 提取须先补齐）。

**动作**：
1. 自动判定：输入类型 / 输入位置 / 输出目录 / 参与度 / 形态（常量）；未决项按表单组装规则出问（未决 = 0 不出表单）
2. 按 `SKILL.md` 入口路由表选引擎（内部代号只进代码与 ② 站 meta，不上用户界面）
3. 播报确认语（材料语言：源在哪、提什么、产物去哪、停等点）
4. 调 `scripts/A/01_inventory.py`（图包）/ `scripts/B/parse_html.py`（HTML）/ `scripts/B/fetch_url.py`（URL + 蓝湖）/ `scripts/C/figma_ingest.py`（Figma）/ `scripts/C/text_llm.py`（文本）

**产出**：确认语已播报 + 路由到的引擎已就绪（来源信息由 ② 站写入 middle.json meta）

**gate**：
- 6 项参数全部锁定（未决 = 0）
- 引擎就绪（路径/URL 可达、依赖齐）

**失败处置**：
- 路径不存在 / URL 不可达 → 回到激活重问第 2 项
- 引擎依赖缺失 → 提示用户安装或换引擎

---

## ② 提取

**职责**：按引擎路由把 6 种输入汇成 `work/middle.json`（符合 Schema）。

### A 类（图包）走完整子流程

```
A-01 盘点（脚本，零看图）
    输入：图包目录
    产出：pages.manifest.json（页面清单）
    规则：基于文件名解析 `编号-页面名-状态.png`，零看图
    失败：命名不规范 → 重命名要求或人工标注

A-02 视觉盘点（视觉模型 + 集成设计盘点思路）
    输入：pages.manifest.json + 图包
    产出：inventory/{page}.md（每页布局 + 素材 + 完整性）
    集成自：flow-front-ui-line-cy-design-pack-pipeline templates/inventory-template.md
    派发：6 项验收清单的视觉模型子代理
    失败：图过少 / 命名歧义 → 提示用户补图

A-03 典型页挑选
    输入：inventory/*.md
    产出：typical_pages.json（2-3 张最复杂页面）
    规则：组件多样性评分 + 视觉密度排序
    失败：只有 1 张图 → 走单图流程（直接进 A-04 单图）

A-04 高保真制作（**调 flow-front-ui-line-cy-img-to-code**）
    输入：typical_pages.json + 原始 PNG
    产出：out/hifi/{page}.html（每页 1 个）
    调：flow-front-ui-line-cy-img-to-code 技能（其完整状态机）
    失败：技能返回非 OK → 进 failed 队列；2 轮失败则跳过该页

A-05 视觉模型质检
    输入：out/hifi/{page}.html + 原始 PNG
    产出：qa/{page}.report.json
    规则：颜色 / 布局 / 字号 / 圆角 / 阴影 5 项对齐检查
    失败：≥3 项偏差 → 回 A-04 重做

A-06 提取（**降级为 B-1**）
    输入：out/hifi/*.html
    产出：work/middle.json（基础色 + 字体 + 间距 + 圆角 + 阴影 + 组件候选）
    调：scripts/B/parse_html.py
    失败：解析器崩溃 → 提交完整 stack + 找单个图另存提示
```

### B-1 类（HTML + 本地 CSS 静态解析）

```
B-1 解析
    输入：HTML 文件路径 ×N（多页一次传，自动合并证据）
    产出：work/middle.json（证据稿）
    调：scripts/B/parse_html.py
    规则：
      1. bs4 解析 DOM
      2. CSS 来源 = <style> 块 ∪ <link> 的本地文件 ∪ 同目录 style.css（Figma 导出惯例）
         ——远程 <link> 不加载，记入 css_sources_skipped（要它先走 B-2 fetch）
      3. 普通声明值分桶聚合（颜色/字号/行高/圆角/阴影/间距/内边距/描边/透明度/动效）→ raw_evidence
      4. **渐变桶 gradients**：background 简写渐变原样聚合+频次（2026-10-16 补：旧版只认
         background-color，Figma 导出的 linear-gradient 全部漏抓，三次产物靠 agent 手动补录
         ——现已机器化，站② 末核对渐变桶非空即视为已覆盖）
      5. **CSS 变量（--*）直得 token 候选**：hex → primitive；其余按变量名映射合法
         category；rgba/多段值进不了 colorToken pattern 的留在证据桶
      6. **素材引用 img_asset_refs**：img src + background-image:url() 逐枚计数
         ——素材库"逐枚清单+预览"的原始证据（站④ 消费）
      7. **形态统计 render_mode_stats**：img 元素数 / 背景图引用数 / 样式类候选数
         ——元素形态三分支（样式渲染/切图/混合）判定证据；站④ 组件实物策略按形态走：
         样式渲染 → 按值渲染实物；切图 → 直接贴图；混合 → 贴图+容器规格
      8. class 频次 + data-figma-name 组件线索 → raw_evidence
      9. **整页稿区块扫描**（站② 末 agent 核对项）：除组件页外，必须核对整页样稿的
         区块清单（页面级组合件：表 / 数据格 / 入口组 / 横幅 / 区头 / 装饰矢量）已进
         raw_evidence——这些区块须进入组件清单或标「AI 补全」，禁静默遗漏
      10. tokens 补全是站③ 职责（证据桶是唯一数据源）
    失败：五桶全空 → **exit 1 熔断**（见 B-1 异常处置，禁自动降级）
```

**B-1 异常处置（2026-10-15 血泪修正，禁再犯）**：
- 证据量异常（如全 0 / 骤降）= **未预期结果** → 第一动作**定性上报等用户拍板**——先怀疑工具（脚本没读到外链 css？路径错了？），再怀疑输入。**禁止把"证据薄"当场内化为合法降级路线继续往下跑**（Ludo 二次事故：旧脚本不读外链 css 造成"5 页全 0"，执行会话据此自动降级 rawjson，用户质问"输入有问题你为什么不找我确认"）
- 降级扫 figma-node.raw.json 只允许**按页逐个批**：哪页 CSS 实测确实薄（如 451B 空壳页），单独列清单报用户，批准后才扫那几页；其余页一律走 B-1 正路

### ②+ Figma 导出混合包（B-1 正路 + rawjson 补充证据）

```
输入：页面目录（.html + style.css + figma-node.raw.json + assets/）
产出：work/middle.json（meta.source_type = B1_figma_export）
规则：
  1. **主路 = B-1 解析全部页**——parse_html.py 已内置本地外链 css 加载，
     Figma 导出页的证据就在 style.css 里，**不存在"必然证据薄"**
  2. rawjson 定位 = **补充证据源**，仅当某页 CSS 实测证据极少（如 451B 空壳页）
     才按页申请扫描（fills/strokes/文本样式），**逐页经用户拍板**——
     定性上报格式："第 X 页 CSS 实测仅 N 条（正常页 M 条），是否批准该页补扫 rawjson？"
  3. raw.json 非 Variables/Styles 契约格式 → 不作 C-1 路由；figma-audit.json 可作组件参考证据
  4. 每页证据量与来源变更如实记录进 meta.supplementary_notes
```

### B-2 类（URL 无头抓 + 静态解析）

```
B-2-a 抓取（**只抓不解析**）
    输入：URL
    产出：source/fetched.html（快照落 source/，到此即止）
    调：scripts/B/fetch_url.py
    规则：playwright headless + wait_until="networkidle"（避免 SPA 渲染缺失）
          脚本内**禁自动链式跑 B-2-b**——链式会把上一步输入的 middle.json 覆盖掉（A8 修正）
    失败：超时 / 401 / 反爬 → 提示用户换 URL 或提供 HTML

B-2-b 解析（**调 B-1**）
    输入：source/fetched.html
    产出：work/middle.json
    调：scripts/B/parse_html.py
    失败：同 B-1
```

### C-1 类（Figma JSON 消费）

```
C-1 消费
    输入：Figma 工具导出的 JSON（用户已跑工具出）
    产出：work/middle.json
    调：scripts/C/figma_ingest.py
    规则：
      1. 解析 Figma Variables → 基础层 + 语义层
      2. 解析 Figma Styles → 组件层候选
      3. 解析 Components（若 JSON 含）→ 组件清单
    失败：JSON 不是 Figma 工具格式 → 拒绝并提示用户
```

### C-2 类（纯 LLM 解析）

```
C-2 解析
    输入：文本（粘的或文件）
    产出：work/middle.json
    调：scripts/C/text_llm.py
    规则：
      1. LLM 抽取 token / 组件 / 规则
      2. 抽取不到的 token 按 templates/system-rules.md 占位逻辑补 demo 值
    失败：文本太短（< 200 字）→ 提示用户补描述或换其他输入
```

### D 类（蓝湖，可选）

同 B-2 流程；登录态失败直接提示用户换 Figma 或导 HTML，**不阻塞主流程**。

---

**gate**：
- `work/middle.json` 存在
- `scripts/core/schema.py validate middle.json` 退出码 0
- 4 段 token 计数（基础/语义/组件/度量）至少基础层非空

**失败处置**：
- Schema 校验失败 → 看缺哪段 → 提示用户补信息或换输入
- 基础层为空 → 99% 是输入问题，回激活

---

## ③ 体系化

**职责**：middle.json → 三层 token + 度量，归档到 normalized.json。

**动作**：
1. 调 `scripts/core/tokenize.py`：
   - 基础层（颜色 + 度量原始值）→ 自动去重 + 命名规范
   - 语义层 → 按 middle.json 命名映射，缺名补 demo
   - 组件层 → 按 class 聚类映射
   - 度量 → 中间表度量值
   - 计数以项目实测为准（铁律 3），缺失不硬凑
2. **agent 归档补全（tokenize 之后、normalized 定稿之前）**：
   - **渐变 token 化**：gradients 桶高频渐变立 token——CTA 类渐变落组件层（如 button-bg-primary 原样渐变串）、端点色视频次落基础层、渐变面板落组件/模式层。**归因要精确**：核对选择器与 DOM 尺寸，别把小元素（如 24×12 标签条）的渐变安到主按钮头上
   - **背景层级体系**（2026-10-16 新增）：页面背景立四级语义 token——`color-bg-shell`（body 环境底，找 html,body 声明）/ `color-bg-page`（内容主区底）/ `color-bg-card`（卡片底）/ `color-bg-overlay`（浮层遮罩，黑色半透明证据）——全部用实测值，语义分层不造值
   - **字重档位**（schema 已支持 font_weight 类别）：font-weight 声明聚类归档（如 400/500/600/700 各档+频次），落 metric 段 `weight-N`
   - **间距节奏归纳**（2026-10-16 修正方向）：间距规范是 **AI 归纳的节奏系统**，不是声明值统计——收敛成少量主档（贴 4pt 网格惯例），低频散值（使用 1-2 次）不立档、规则写"就近归档"；提取到的声明值只作证据佐证。**页面级布局间距**（Figma 绝对定位导出稿藏在 left/top 坐标里）由 AI 推理补全（如主按钮 left:16px → 页面边距 16px），标 AI 补全
3. 输出 `work/normalized.json`（带 `token_count_summary`）

**gate**：
- 4 段计数自检
- 命名去重（无重复 token 名）
- 必含项断言（success/warning/danger、focus-ring、font-family-base 必有）
- **渐变核对**（2026-10-16 新增）：源材料 gradients 桶非空 → normalized 里必须有对应渐变 token——防渐变漏提复发
- **背景层级核对**：color-bg-page 有值时，四级（shell/page/card/overlay）至少归档三级（源材料证据不足的层标 AI 补全）

**失败处置**：
- 缺关键 token → 警告 + 用 demo 值补 + 落报告
- 命名重复 → 自动改名（如 `gray-100` 已存在，新加的 `gray-100#ABC` 改 `gray-101`）

---

## ④ 定案 HTML + 双标 + 派生 + 自检

**职责**：以 templates 真实案例为骨架渲染并补全定案 HTML，双标折算后从定案 HTML 派生 md 与 json，自检十三件套 + 落盘。

**templates 即真实案例**：templates/ 下的案例是一个真实项目的完整产物——**每章动笔前先读 templates 对应章节：形态照它长（结构、分组、标注、双标格式），数据用你项目的；案例的业务词禁止迁移**。

**动作（命令 + 中间的 agent 语义活；脚本必须用 Bash 实际执行，"读过"不算"做过"）**：
1. 调 `scripts/core/run_pipeline.py <out目录> [assets源目录]`——**一键管线初稿**：gen_html 渲染初稿（:root 全量+换肤）→ gen_components 组件库 33 类字典枚举 → gen_assets 素材网格 → gen_layouts 九类线框 → html_to_json → html_to_md → fetch_fonts → self_check；任一步失败即停（初稿摸底，交付口径以定案后重派生为准）
2. **agent 补全定案 HTML**（唯一的语义活）：占位组填推断值或声明不适用、素材语义名、迷你示例页组件拼装、规则散文——补全时对照 output-templates §0 八句输出规则（正本）；**正文补全禁动交互脚本（侧边栏高亮、点击复制等 JS 原样保留）**
3. 调 `scripts/core/dual_scale.py <design-system.html> <system-rules.md>`——**双标折算**：@2x 源稿值折算为 1x 主口径、括注 @2x（如 `12px（@2x 24px）`）；CSS 渲染区整体摘除不动；口径基准值（375/750/812）跳过；幂等可重放，`--dry` 预览
4. 调 `scripts/core/run_pipeline.py <out目录> --derive-only`——从已双标的定案 HTML 重派生 json/md + 字体 + 自检（不动 HTML；gen_* 形态生成器不重跑）
5. 写交付报告（自检十三项 ✓/REVIEW 逐条列明；等用户参与度决定是否要审）

**管线禁令**：禁跳过 run_pipeline 改用自写脚本串联（复测事故：手搓 = 皮肤填错/无字体/形态崩坏）；**工序顺序禁反：先双标后派生**——dual_scale 必须在 --derive-only 重派生之前完成，顺序反了 json/md 口径错、三构造不自洽；--derive-only 之外的任何重跑都不得在 agent 补全定案后执行（gen_html 会以模板初稿覆盖定案正文）。

**目录纪律**：产物根 = `<项目>/design system/out/`，根下白名单（workspace 件套机器核）：design-system.html / system-rules.md / system-rules.json / system-spec/（字体 woff2 + assets/icons/<图标库>/）/ assets/ / hifi/ / work/ / source/。**work/ = 过程区**（middle.json / normalized.json / 临时脚本 / 备份）——中间 json 不改不交付，网页快照 fetched.html 归 source/，图标归 system-spec/assets/icons/<库>/，脚本备份禁留交付区。

**生成器纪律**（Ludo 事故 + 复测事故换的）：
- **gen 与派生脚本（gen_html / dual_scale / html_to_json / html_to_md / fetch_fonts）不得跳过、不得用自写脚本替代**——皮肤换肤、双标折算、字体自托管、三构造派生都在脚本里。复测事故实证：agent 提及 fetch_fonts 92 次执行 0 次，从零手搓产物 → 皮肤填错、无字体、形态崩坏
- **agent 自写脚本只许做一件事**：在 gen 产出的定案 HTML 基础上做正文补全；**禁止绕过管线从零拼装任何交付物**
- **计数纪律**：产物计数 = 项目实测；三构造同源即天然一致，禁止为凑数塞槽位
- **命名纪律**：token 名跟值走——真实紫就叫 purple，禁止"值改粉、名留 blue"
- **组件条目四件套**：规格 + 分级变体 + 使用说明（通用语义，禁业务强耦合）+ 来源标注（条目级：AI 补全逐条标，提取的不标）；字典坑位逐个核对，缺项必须 AI 补全或声明不适用
- **素材库强制交付**：缩略图网格（96px 等高 + 棋盘格衬底 + lightbox）+ 语义分组逐枚四件套 + pHash 去重；原图禁 1:1 铺进产物
- **图标章**：现有图标实物陈列 + 开源库匹配整库交付（fetch_iconset.py）+ 使用形态三分类（裸图标 / 带容器 / 带文字）
- **内容准入**：HTML（人看）只放实物演示/规格/使用说明/Do-Don't；md（AI 读）只放可执行规则+值；过程叙事、源工具名禁入交付物正文，家在 work/ 的中间 json 证据层
- **组件库 vs 素材库边界**：交互控件进组件库（能点/能输/有状态），美术资源归素材/图标章
- **布局模板骨架家族**：九类骨架，每模板线框 + token 渲染迷你示例页（只用产物归档 token 拼装，拼不出 = 规范缺口回填）；小样与来源页面逐段一致，每组附原稿节点依据——**无依据禁标「已提取」**

**gate**：
- 自检十三件套全 PASS：1 counts / 2 anchors（动态互验，不写死章数）/ 3 contradictions / 4 raw_values / 5 features / 6 gradient_truth（传 --source-dir 对照源材料渐变 ground truth——三次产物渐变漏提事故的机器防线）/ 7 doc_contrast / 8 source_audit / 9 css_syntax / 10 delivery（自包含 + 交互降级）/ 11 workspace（交付区卫生）/ 12 assets_registry（normalized.assets 插画↔md 素材章对账）/ 13 template_form（templates 逐章签名↔产物 diff）
- 三构造一致：定案 HTML 为源，md/json 派生后计数与 HTML 声明一致；system-rules.json 的 tokens.count 一并对账
- 尺寸双口径统一：正文值 1x 主口径、括注 @2x（dual_scale 已折算的标记不得手改回裸值）
- 无证据组件/区块有显式声明清单（「AI 补全」/「源无证据」），禁编造

**失败处置**：
- 锚点漏配 → 回到 gen_html 补 id
- 矛盾条文命中 → 标红 + 给出裁决建议
- 裸值命中 → 标黄 + 标 token 替代名

**自检不通过** → 不得宣称"完成"；只能展示"哪些过了 / 哪些要人决"。
- **素材形态自适应**（站④ 复写组件实物时）：样式渲染元素按值渲染实物、切图元素直接贴图、混合元素贴图+容器规格——判定依据 = parse_html 的 render_mode_stats + DOM 标签（img vs div+class）

---

## 跨站机制

- **每站完成即播报**：done / failed + 原因 / REVIEW，禁止"差不多"——短任务不立台账文件，产物文件就是台账
- **修复轮根因门**：任何站失败必先报告根因再修；禁止"改一版试试看"
- **冻结终审**：3 轮修复仍失败 → 进交付报告"留档代价 > 修复代价"判定，**不阻塞用户叫停**
- **职责边界**：本技能管 middle.json 之后的体系化与三构造交付，**不碰上游 6 种源的获取**（A-01 盘点是集成思路，**不是调 flow-front-ui-line-cy-design-pack-pipeline**）

---

*设计系统提取技能 · station-guide 细则 · v4.1.0 · 2026-11-03（双线合流）*

<!-- 合流记录（已全部落定，留档防复发；2026-11-24 复核）：
1. 站④ dual_scale 步骤——已核实修复：run_pipeline.py 已挂 dual_scale（④b）、⑧ 步已标"十三件套"，与本文档口径一致。
2. B-1 规则 9"整页稿区块扫描"——已落为"站② 末 agent 核对项"，维持人工核对，不机器化（定案）。
3. B-1 规则 5"CSS 变量直得 token 候选"——已与 parse_html.py 实际实现对齐（colorToken pattern 外的值留证据桶）。
4. 十三件套清单——已核实修复：output-templates.md §4 已列 13 件，与 gate 内联清单同序。
5. 整改版站③"案例参考段位非门槛"——按口径卡 #10 废弃不回流；"计数以实测为准"精神已并入站③ 动作 1。
6. 站④"派生双产物"字样——已按验收口径改为三构造表述，全清。
7. 素材形态自适应句留站④ 末；source_fidelity 抽查语义已并入布局模板家族纪律与 gate"无证据显式声明"条。
-->
