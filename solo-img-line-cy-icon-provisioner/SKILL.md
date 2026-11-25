---
name: solo-img-line-cy-icon-provisioner
description: "图标交付服务：接收图标需求，经需求澄清、供给路由、视觉确认，交付可直接内嵌使用的图标代码。触发：用户要「找图标/配图标/换图标/图标风格不统一/需要一套图标/图标改色/会动的图标/hover 动效图标/动态质感或双色面性图标（kubai 系）/缺的图标按同款风格现画」，或被 flow-ue-line-xjk-hifi-prototype 等生产类技能作为图标供给环节调用。能力：本地图标库离线检索（43 库 17 万+枚）、Iconify 在线集合、成套场景图标、3D/黏土/拟物质感图标、动效图标（kubai 分层动态/双色面性：静态帧检索 + 引擎程序化现画，交付形态以供给菜单+推荐呈报——静态 SVG / 带 hover 动效的交互组件 / 官方 react/vue 包——由上游选，自动化流程按目标环境自决策）；找不到时明确报未命中并给最近似候选与兜底（程序化生成或生图，可用则直接生成）。不适用：纯讨论图标审美不产出图标；图片压缩/抠图/格式转换等通用素材加工。"
---

# solo-img-line-cy-icon-provisioner · 图标交付服务

## 欢迎语（人类触发时，第一句输出，逐字使用）

见 [references/onboarding.md](references/onboarding.md) §欢迎语——触发后第一句必须逐字输出欢迎语，之后按其引导决策树行走。

**代理调用模式**（上游是主代理/子代理、无对话）时跳过欢迎语，直接进入 I0 模式 B。

## 主干流程

### I0 需求澄清 + 复杂度分级

按 [references/onboarding.md](references/onboarding.md) 执行两种模式：

- **模式 A · 人类对话**：流式盘问（遵守 interrogation-icon.md **九协议**，收敛按七面检查表），问题从需求缺口动态长出，禁止固定问卷
- **模式 B · 代理调用**：校验调用方需求里的字段；**关键字段缺失 → 返回缺字段清单向调用方索取，禁止瞎猜**

澄清同时完成**复杂度分级**：

- **简单档**：常见语义 + 常见风格（搜索/设置/删除 + 线性/面性）→ 快速路径，分钟级交付，不做全套盘问
- **复杂档**：罕见语义 / 特定质感（3D/黏土/拟物/贴纸/像素/动态质感/双色面性）/ 成套一致性 / 多源未命中 → 全流程

分级默认简单档；只有触发复杂条件才升级——避免杀鸡用牛刀。

### I1 需求单冻结（唯一事实源）

按 [references/demand-sheet.md](references/demand-sheet.md) 模板产出「图标需求单」：用途场景 / 语义清单 / 风格族 / 规格 / 交付形态 / 许可约束 / 数量。上游确认（人话签字 / 代理返回确认）后冻结。冻结后执行只读。

**风格族 → 库白名单映射**：需求单的风格族字段直接决定候选库范围（映射表见 [references/sources.md](references/sources.md) §风格族→库白名单映射）。

### I2 供给路由

按序尝试，命中即停（命中 = 语义与风格族双匹配，见 wf-icons.md §视觉确认漏斗）：

1. **本地 `assets/icons-json/*.json` + `cache/`**（离线主力；口径以 `assets/icons-json/` 为准：43 库 174,887 枚，`cache/` 为抓取缓存另计、动态增长不进计数；两个目录与 scripts/ 均相对**本技能根目录**）
2. **Iconify API**（`scripts/iconify_fetch.py`：查 cache → 未命中走 API → 落缓存）
3. **3dicons.co**（仅 C4D 质感变体——Iconify 没有的唯一外部例外，按需下载单文件，禁止整包；**注意 3dicons.com 是他站勿混淆**）
4. **兜底**：见下方「失败纪律」

### I3 视觉确认漏斗（有候选需要挑时必走）

1. **库白名单过滤**：风格族砍掉 90% 不候选（零成本）
2. **名字检索**：本地 JSON 键名 grep 或 Iconify search API（毫秒，处理的是名字不是图形）
3. **网格批审**：候选 ≤5 且形态代码可判 → 直接读 SVG 源码定性（stroke-width/fill/复杂度）；候选多或需求模糊 → `python scripts/render_grid.py` 出编号网格对比图 → 用宿主的读图工具一次看一批
4. **模糊需求** → 网格图交上游挑，AI 只给推荐与理由，不替上游瞎定

### I4 适配加工

按需求单规格：改色（currentColor/指定色）、描边粗细对齐、尺寸、位图转 base64 data URI。多图标统一规格后用 SVG sprite（`<symbol>`+`<use>`）。

### I5 交付 + 验收

按 [references/demand-sheet.md](references/demand-sheet.md) 交付单格式输出：**可直接粘进产物的代码块** + 台账（语义→库→许可→形态判定）。验收 = 逐项回查需求单；emoji 扫描零命中。

**失败纪律（最高优先）**：全链路未命中 → 显式声明未命中 + 给最近似候选（带差异说明）+ 五处置选项（用候选/转手绘/改语义/生图/程序化生成——探查当前环境可用的能力：kubai 引擎在场（Node+Chrome）走程序化生成（wf-icons §程序化生成），生图能力可用则直接生成并 base64 交付，均无则给生图提示词包供上游自行生图）。**禁止静默降级塞违和图标充数**——形态违和等于二次污染。

## 分场景工作流（何时读哪个）

| 需求场景 | 读 |
|---|---|
| 欢迎语 + 引导决策树 | [references/onboarding.md](references/onboarding.md) |
| 怎么问（流式盘问协议） | [references/interrogation-icon.md](references/interrogation-icon.md) |
| 需求单 / 交付单格式 | [references/demand-sheet.md](references/demand-sheet.md) |
| 单图标 / 批量图标（含四步漏斗细节、失败五选项与程序化生成） | [references/wf-icons.md](references/wf-icons.md) |
| 成套场景图标（整页一致性 / 场景套装生成） | [references/wf-iconset.md](references/wf-iconset.md) |
| 3D/黏土/拟物质感、生图提示词包 | [references/wf-genicon.md](references/wf-genicon.md) |
| 动效图标（SMIL/CSS；复杂动画转 solo-img-line-cy-lottie-json） | [references/wf-motion.md](references/wf-motion.md) |
| kubai 系图标（动态质感/双色面性：检索、改色、程序化生成、引擎更新） | [references/sources.md](references/sources.md) §kubai 家族 + [references/wf-icons.md](references/wf-icons.md) §程序化生成 |
| 本地库清单 / 每库风格档案 / 风格族→库白名单映射 | [references/sources.md](references/sources.md) |

## 硬规矩

1. **禁止 emoji 当图标**——任何风格零容忍（本条约束交付产物；对话文本中的 emoji 不在此列）；emoji 只在"内容本身是表情"的语义时作为图形素材（noto/fluent-emoji 库）
2. **形态跟随风格**——以需求单风格族为判定基准；形态不匹配宁可报未命中，禁止线性图标塞 3D/拟物风格充数
3. **产物零依赖**——交付的代码块必须可直接内嵌（SVG 源码 / base64 data URI / sprite / 内联引擎的自包含交互组件），禁止交付**外部链接**（CDN/远程资源/跨文件引用；脚本内联在产物内不算外部依赖）
4. **许可透明**——交付单必须写来源与许可；商用约束（CC BY 署名）如实标注
5. **离线优先**——本地 JSON 库是主力；本地未命中即允许在线补取（Iconify），取一次落 cache 后恢复离线
6. **外部协议优先**——任务书附**协议页**时（如主线 flow-ux-ui-line-cy-hifi-design 调起），守门与登记口径以协议页为准；无协议页按本文件原生流程
