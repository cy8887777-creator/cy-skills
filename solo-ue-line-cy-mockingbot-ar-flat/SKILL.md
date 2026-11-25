---
name: solo-ue-line-cy-mockingbot-ar-flat
description: 将墨刀（MockingBot）导出的原型 HTML 翻译为阿拉伯语 RTL 版，并产出「矩阵式平铺版」静态 HTML。当用户要把墨刀原型翻成阿语、出阿语平铺/评审版、或做中东/GCC 项目本地化时使用；支持按页面树分批次处理。
agent_created: true
---

# 墨刀 → 阿拉伯语平铺版（solo-ue-line-cy-mockingbot-ar-flat）

## Overview

把墨刀导出的原型（HTML `.zip` 解压后的 `index.html`）翻成阿拉伯语 RTL 版本，最终交付**矩阵式平铺静态 HTML**（无交互、评审可读、列数随屏宽自适应）。

与截图 OCR 路线不同，本 skill 走 **Chrome CDP 提取 DOM 节点（嵌套坐标/层级/样式）→ 前置过滤交互层 → 术语表优先翻译 → 几何嵌套 RTL 镜像 + 阿语字体/bidi → 生成**，因此能真实重排为 RTL 而非图片。

详细技术规范、DOM 选择器、CDP 命令、RTL/字体/过滤/高度规则与已知坑见 `references/spec.md`（执行前必读）。分步实操命令、参数、填表与人工复核清单见 `references/使用说明书.md`（人类同事与 AI 共用的执行手册，加载技能后执行前必读）。

> **翻译权威单一化（2026-09-02）**：原「英转阿UI文案翻译」技能已并入本技能，其全部翻译方法论（语境推断三层 / 元素类型→语气 / 阿语专项 / 风险标注）收编进 `references/spec.md` §5。本技能现为阿语本地化**唯一入口**，勿再调用已归档的独立翻译技能。

## When to use

- 用户要把墨刀原型翻成阿拉伯语（中东/GCC 游戏、社交、棋牌等项目）。
- 用户要「阿语平铺版 / 阿语评审版 / 阿语静态展示版」。
- 用户给的是墨刀导出文件，并希望保留布局、按页面分批翻译。
- 触发词：墨刀转阿语、原型阿语化、阿语平铺、RTL 本地化、中东项目本地化。

## 前置准备（一次性）

1. 拿到墨刀导出的 `.zip`，解压得到 `index.html`（+ `extra/data.1.js`）。若是 `.mdrp` 私有格式，**无法直接解析**，必须让用户在墨刀里「导出 HTML」再走本流程。
2. 用 Chrome 打开导出文件并开调试端口：
   ```
   "/c/Program Files/Google/Chrome/Application/chrome.exe" --headless=new --disable-gpu --no-sandbox --allow-file-access-from-files --remote-debugging-port=9223 --user-data-dir="C:/Users/1/AppData/Local/Temp/jam3a-chrome2" "file:///解压目录/index.html"
   ```
   > ⚠️ **禁止 `taskkill /F /IM chrome.exe`**——会杀掉用户所有 Chrome 窗口。用独立 `--user-data-dir` 隔离，不与用户浏览器冲突；后台常驻时 `sleep` 保活即可（详见 spec.md §1）。
3. 确认端口可达：`http://127.0.0.1:9223/json/list` 能返回页面。
4. 准备好术语对照表（PM 提供，中英阿三栏 Markdown 或 JSON）。表内词条优先级最高、跨页跨模块复用。

## Workflow（七阶段）

> 核心管线：`提取(嵌套) → 前置整删交互层 → 术语表优先翻译 → 嵌套 RTL 镜像 → 阿语字体+bidi → 矩阵平铺 HTML`。
> 提取与生成是两步独立脚本：提取可一次跑多页缓存 JSON，生成可反复跑（换术语表/补译不重提）。

### 阶段 1 · 定位与读取（提取英文画板，嵌套节点）
运行 `scripts/extract_en.mjs`：
```
node scripts/extract_en.mjs --file "<index.html 的 file:// 路径>" --screen <cid> [--keywords "Quests|..."] [--out en_nodes.json]
# 或按页面树分批：
node scripts/extract_en.mjs [--pages all|1,2,3|引导页Onboarding,手机号登录Phone Login] [--out en_nodes.json]
```
- 精确定位（推荐）：`--screen <cid>` 配合 `--file` 用 URL 参数 `?view_mode=device&screen=<cid>` 直达，**避开不可靠的侧边栏点击**；可选 `--keywords` 用正则锁定画板（如 `Quests|Check-in|...`）。
- 画板选取：**CJK 字符数最少者**即英文板（**未必为 0**，漏翻中文可能残留，按漏翻中文直翻阿语处理）。
- **缩放健康门**：画板屏幕宽 < 80 拒绝提取（会子像素退化导致空白）；新 Chrome 首次启动退化时自动重试。
- 嵌套 walk：记录 `parent`/`depth`/`z-index`/`overflow`/`transform`/`cls`/`color`/`SVG`，保留 DOM 树；跳过 `display:none`/隐藏整棵子树、SVG 内不深入。
- 输出 `en_nodes.json`（嵌套结构，`meta.pkgBase` 用于图片路径补全）。
- 母版告警：内容页节点数异常少（<20）时提示「疑似母版」，回报 PM 而非硬解。

### 阶段 2 · 前置过滤（交互指示层整删，自动）
生成阶段**第一步**自动完成（无需单独命令）：识别橙热区 `rgba(255,140,25,0.1x)` + 蓝闪 `#298DF8`/`InteractionMarker` → **整棵删除**；若命中节点子树含真实内容（文本/图片/非蓝闪 SVG）→ **降级中和**（剥橙底/不发射蓝闪，保留容器与内容），**零误伤**。
> 此步在翻译之前（PM 2026-09-01 18:33 定），后续阶段只看真实 UI。

### 阶段 3 · 翻译（术语表优先 + Agent 语境翻译）
生成阶段**第二步**自动完成：
- **翻译模型（PM 2026-09-02 纠正）**：术语表的作用是**规范行业用语、统一翻译用词**（consistency authority），**不是全量翻译词典**。正确流程：
  1. **术语表有的 → 严格按术语表来**（保证跨页/跨模块用词一致）。
  2. **术语表没有的 → 由 Agent 从英文语义 + 页面标题推断场景，做语境翻译**（不是留英文、不是标"未命中"就结束）。
  3. Agent 将语境翻译结果填入 `--extra` JSON（`{ "原文": "阿语译文" }`），脚本通过 `--extra` 兜底应用。
  4. **"未命中" = Agent 尚未翻译**，不是"不可译"。Agent 必须补译，不应把未命中当最终指标汇报给 PM。
- 查找顺序：保留类（数字/时间/拉丁专名/专有名词不译）→ **术语表（`--terms`）**→ **Agent 语境翻译（`--extra`）**→ 未命中则原样保留并列入清单（仅作为 Agent TODO 提示）。
- 术语表支持 Markdown 三栏 `| 中文 | 英文 | 阿拉伯语 |` 或 JSON `{ "English": "Arabic" }`；EN 键小写化、`/` 切多值、CN 键直用。默认内置 `references/术语表.md`（**团队定稿合并版 335 条**：项目组+PM 2026-08-29 拍板的 21KB 英中阿表为权威源，合并技能原内置 140 条作缺口补充；同词冲突以团队表胜），可用 `--terms` 覆盖。
- **术语权威单一来源（2026-09-02 PM 定）**：所有术语以技能内 `references/` 下资产为准，**不再从项目其他文件夹（如 `D:\workbuddy项目\Jam3a\8.13\` 等）读取术语表/规范**。资产清单：`术语表.md`（默认消费，合并权威版）、`terms_ar.json`（同内容的 JSON 形态）、`术语表_Jam3a团队定稿.md`（21KB 团队原表复制，仅作 provenance/人工核对，不供解析）、`keep_latin.json`（不可译清单 + 合规禁用词）、`术语表_内置140.md`（合并用的稳定源，勿改）、`build_terms.py`（由团队原表重生成上述资产的脚本）。改术语请改 `术语表_Jam3a团队定稿.md` 后重跑 `build_terms.py`。
- **键归一化（normKey）**：查找前自动去除零宽字符（U+200B 等）、不换行连字符（U+2011 等）、不换行空格（U+00A0）、合并多余空白——避免原型工具注入的隐形格式符导致精确匹配失败。
- 漏翻中文（英文板里残留的中文）→ 经 `--extra` 或术语表直翻阿语（不回译英文）。
- 译文里夹拉丁/数字用 `<bdi>` 隔离，避免双向重排错乱。
- 语境推断三层（页面名→场景 / 模块→领域 / 元素类型→语气）+ 元素类型→语气表 + 风险标注框架（超长/歧义/不可译/待确认）详见 `references/spec.md` §5.1–§5.4，为本技能翻译方法论**单一事实源**。

### 阶段 4 · RTL 镜像布局（嵌套递归，自动）
生成阶段**第三步**自动完成：子节点在其**父容器内**水平翻转 `rx' = containerW − rx − n.w`（递归传递，等价于全局镜像）；逻辑对齐 `left↔right`（视觉方向）、方向符号翻面。纯图形组合后续可整体 `scaleX(-1)` 优化（见 spec.md §6）。

### 阶段 5 · 字体与防裁切（自动）
阿语 `Noto Sans Arabic`；纯拉丁/数字 `Noto Sans SC` + `direction:ltr`；**禁用 PingFang**（无阿语字形）。阿语行盒高于英文 → `min-height` 防裁切。

### 阶段 6 · 平铺版输出（最终交付）
运行 `scripts/gen_ar_flat.mjs`：
```
node scripts/gen_ar_flat.mjs --src en_nodes.json [--terms 术语表.md] [--extra 补充.json] [--out ar_flat.html] [--title "标题"] [--theme dark|light] [--palette 配色.json]
```
- **暗色模式（默认开启）**：阿语版**默认暗色**（Jam3a 产品暗色优先，PM 2026-09-02 定）；`--theme light` 可切回亮色。配色表默认读技能内置 `references/dark-palette.json`（Jam3a 暗色规范），可用 `--palette` 指定自定义配色。
  - **弹窗类页面自动豁免**：页面命名含「**弹窗**」或「**Popup**」的页面**不套暗色、保留原主题**，并在该屏标题上打「原主题」标记（PM 2026-09-02 规则）。
  - 只改**色值**，不动布局（布局由原型镜像决定）。映射范围：背景 `bg` / 文字与图标 `clr` / 边框 `bc`。
  - 分属性映射：同一亮色作背景与作文字时映射不同暗色（如 `#FFFFFF` 作背景→`#333333`，作文字→`#F2F2F2`）。
  - **组件级语义覆盖（2026-09-02 实装）**：按钮/输入框等组件优先按 `dark-palette.json` 的 `components` 表映射，覆盖通用 `bg`/`clr`/`bc` 表。例如主按钮亮色原型常用深色底白字，识别为 `button-primary` 后映射为填充 `#F0F0F0` + 文字 `#0A0A0A`，避免生成黑色按钮。规则来源以 PM 提供的暗色规范截图为最高优先。
  - 半透明色（rgba 带 alpha）、渐变、图片**不映射**（改色会破坏叠加）。
  - **G7-补（2026-09-02 实装）**：未知字面量色值不再"保持原色"，而是按亮度启发式自动转暗色：
    - 近白/浅色（lum>180）：背景→`#1e1e1e` 暗面、文字→`#e8eaed` 浅字、边框→`#3a3a3a` 暗边。
    - 近黑（lum<50）：文字→`#c8c8c8` 可见、边框→`#4a4a4a`、背景→`#252525`。
    - 中间灰保持原色（已接近暗色系可接受范围）。仍记录进「暗色未匹配色值」清单供 PM 复核。
  - **图标可见性（G7-补）**：暗色模式下 SVG 图标和 img 图片自动施加 `filter:brightness(0) invert(0.85)` 强制亮化，解决原色图标在 `#121212` 暗底上不可见的问题。品牌彩色图标如需保留原色，可在 keep-colors 列表中排除。
  - 预览画布外壳恒定中性灰不随主题变（否则暗色下与手机框黑边同色、边界糊掉），仅屏内承载主题色。
  - **配色表回填（PM 2026-09-02）**：首跑 Ludo 实测的 8 个未匹配色值已按角色补入 `dark-palette.json`——品牌黄 `#E8CA2C` 入 `keep`（保留原色），`#1A1A1A`/`#9F9F9F`/`#555555`/`#7A7A7A`/`#444444`/`#EEEEEE`/`#FFFFFF` 按 `bg`/`clr`/`bc` 分角色给暗色值。回填后该原型暗色未匹配 = 0；亮度启发式仍为**未来新原型**兜底，新出现未匹配色值仍进清单供回填（见阶段 6 暗色 + §12.6 维护指引）。
- **术语表（默认内置）**：未传 `--terms` 时自动套用技能内置 `references/术语表.md`（**团队定稿合并版 335 条**，PM+同事 2026-08-29 拍板为权威，合并原内置 140 条缺口补充）；可用 `--terms` 指定项目专属表覆盖。合规禁用词与不可译清单见 `references/keep_latin.json`，生成时应拦截/保留。
- 矩阵式 Grid（`auto-fill 375px` + `gap 28px` + 居中，**列数自适应无上限**）。
- **平铺方向 = LTR（中文习惯，PM 2026-09-02 定）**：`<html lang="zh" dir="ltr">`，网格/标题/目录整体**从左往右**排布；**仅每屏 `.screen` 内部内容做 RTL 镜像**（`direction:rtl`）。即「平铺不套阿语阅读习惯，屏内才镜像」——评审时版面符合中文顺序，屏内仍是正确的阿语 RTL。
- 每卡墨刀中文原名标题 + 375 宽舞台；**无 `<script>`、无交互**。
- 高度不设限：`max(812, 所有元素 top+height)`；超 812 整页显示不裁切。
- QC 输出：翻译统计（术语表命中/补充/保留/未命中）、交互整删数、超宽告警清单（G2，供人工精简/换行复核）。
- **超宽「频率高页面」清单（PM 2026-09-02 answer #3）**：运行日志在 G2 明细前先按超宽条目数**降序**输出各页清单，供 PM **优先人工精简**译文（阿语比英文长，超宽只告警不自动处理，精简清单交人工）；HTML 页眉同步显示超宽总条数。

### 阶段 6.5 · 自动拉宽后处理（可选，2026-09-02）

gen 输出后、自检前执行（阿语比英文长 20-40%，多数折行是墨刀组件按英文短文案定宽所致，拉宽组件即可恢复单行，**不必精简译文**）：
```
node scripts/stretch_ar_flat.mjs --file ar_flat.html [--port 9223]
```
- 需 Chrome 调试端口（与提取阶段同实例）；自动备份 `.pre-stretch.bak`，失败不动原文件。
- 描述句/提示语放不下一行会自动失败保持多行（PM 认可设置项描述换行）——无需人工分类。
- 完成后用「Range 行矩形数」复验真实 2 行换行应为 0（注意：盒高/lh 判行数会被 min-height 撑高的盒子欺骗，勿用）。

### 阶段 7 · 自检与分批续作
- 平铺版 `grep -c` 确认：`<script>` = 0、PingFang = 0、`<html ... dir="ltr">` 存在（平铺整体 LTR）、`direction:rtl`（`.screen` 内容镜像）存在。
- 抽查：超 812 页面是否完整；数字是否 1234；拉丁专名隔离；箭头翻面；超宽告警项是否需精简译文。
- **翻译覆盖确认**：未命中应为 0（Agent 已完成全部语境翻译）。若 >0，说明 Agent 还有文案未翻译——补进 `--extra` 后重跑阶段 6（无需重提）。**禁止将"未命中 N 条"作为最终指标汇报给 PM**（见阶段 3 翻译模型说明）。
- 分批：同模块多页 `--pages all` 一次提取，或后续 `--pages` 只补新页；术语表 + `--extra` 跨页跨模块复用。

## Conventions（已与 PM 确认，强制）

1. 高度不设限（超 812 整页显示）；平铺整页、无交互。
2. 字体：阿语 Noto Sans Arabic；LTR 内容 Noto Sans SC/Noto Sans；禁用 PingFang。
3. 数字 1234（西阿拉伯数字）；区号/时间/邮箱/游戏拉丁名/品牌名/专有名词（XP/GVG/PVP/LV/VIP）原样保留。
4. 设计侧统一「组合」不用「母版/Master」（否则导入墨刀难拆元素级）。
5. 平铺版：矩阵自适应列、统一 28px 间隔、中文标题、无交互、前置整删交互层。
6. 平铺方向：整体 LTR（中文习惯，左→右），**仅 `.screen` 内容 RTL 镜像**；平铺本身不套阿语阅读习惯。
6. 读取/翻译一律找**英文页面**；英文板漏翻中文直接翻阿语，不回译英文。

## Resources

- `scripts/extract_en.mjs` — Chrome CDP 嵌套提取英文画板（支持 `--screen`/`--pages`/`--keywords` 分批）。
- `scripts/gen_ar_flat.mjs` — 前置过滤 + 术语表优先翻译 + 嵌套 RTL 镜像 + 矩阵平铺（最终交付）。
- `scripts/stretch_ar_flat.mjs` — **自动拉宽后处理（可选，2026-09-02）**：gen 之后跑一遍，修复「墨刀组件按英文短文案定宽 → 阿语变长被迫折行」问题。组件级试扩（文字+紧贴胶囊）+ 只认新压到的碰撞判定 + 缩字号兜底；描述句放不下一行自动保持多行。群组模块实测 450 处 2 行换行→0。`node scripts/stretch_ar_flat.mjs --file ar_flat.html [--port 9223]`（需 Chrome 调试端口；自动备份 `.pre-stretch.bak`）。
- `scripts/split_ar_flat.mjs` — **平铺版分批切分（2026-09-03）**：把全量平铺 HTML 按每批 N 屏切成多个独立完整 HTML，供分批导入墨刀（一次导入太多页面会卡死）。保留 head 样式与卡片内容原样（零翻译/布局改动），每批页眉标注「批次 N/M · 屏 X–Y」便于对号；图片为 file:/// 绝对路径，批次文件放任何目录不断图。`node scripts/split_ar_flat.mjs --file ar_flat.html [--size 25] [--out-dir batches] [--prefix 批名]`。建议先按 20 屏试导入墨刀，不卡再调到 30。
- `references/术语表.md` — **默认消费术语表**（团队定稿合并版 335 条；`--terms` 不传时自动套用）。
- `references/terms_ar.json` — 同内容 JSON 形态（供 `--terms <json>`）。
- `references/keep_latin.json` — 不可译清单 + 合规禁用词（生成时拦截/保留，勿译）。
- `references/术语表_Jam3a团队定稿.md` — 21KB 团队原表副本（**权威源 / provenance**；改术语改这里，再跑 build_terms.py）。
- `references/术语表_内置140.md` — 合并用的稳定源（build_terms.py 只读，勿改）。
- `references/build_terms.py` — 由团队原表重生成上述术语资产的脚本（可复现）。
- `references/dark-palette.json` — 暗色模式配色表（含 `page.screen` + `bg`/`clr`/`bc` 分属性映射 + `components` 组件级语义覆盖 + `keep` 品牌/语义色保留）。
- `references/spec.md` — 技术规范、DOM/CDP 细节、RTL/字体/过滤/高度规则、已知坑、暗色模式组件色规则。
- `references/使用说明书.md` — 面向人类同事与 AI 的执行手册（分步命令、填表、人工复核清单）。
