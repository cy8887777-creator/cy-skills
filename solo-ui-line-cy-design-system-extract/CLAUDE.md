# solo-ui-line-cy-design-system-extract · 模块工作纪律

> 配合全局 `CLAUDE.md`（分诊/铁律/子代理/双轴/语言）。本文件只承载**本模块特有**的纪律。

---

## 1. 写入谨慎

- **没拿到明确"写吧 / 落盘"指令不写文件**（同 SKILL.md 铁律 7）
- **激活 6 项参数未全部锁定（未决未清零）** → 任何脚本、模板、产物都不许动
- **templates/（真实案例）+ sample-input/（Schema 示例）可引用与复述，但改动须走版本流程**（案例即模板，改它会改所有下游产物的形态基准）
- 自检脚本发现 FAIL → 不修主代码，**先报告根因**，等裁决

## 2. 6 路输入路由

| 输入 | 引擎 | 子调用 | 文件入口 |
|---|---|---|---|
| ①图包 | A | **集成** flow-front-ui-line-cy-design-pack-pipeline 思路 + **调** flow-front-ui-line-cy-img-to-code 单图高保真 | scripts/A/01~06 |
| ②HTML | B-1 | — | scripts/B/parse_html.py |
| ②+ Figma 导出混合包 | B-1+ | DOM 薄 → 遍历 figma-node.raw.json 取值（不作 C-1） | scripts/B/parse_html.py + raw-node 遍历 |
| ③URL | B-2 | 先 playwright 抓 → 落盘 → 调 B-1 | scripts/B/fetch_url.py |
| ④蓝湖 | D | 降级 B-2；不强求 | scripts/B/fetch_url.py (lanhu mode) |
| ⑤Figma | C-1 | **消费** Figma 工具 JSON，**不调工具** | scripts/C/figma_ingest.py |
| ⑥文本 | C-2 | 纯 LLM 解析 + 补全 | scripts/C/text_llm.py |

**A 类最终走 B-1**：高保真 HTML 出来后，**降级为 B-1 解析**。

## 3. JSON Schema 是契约

`sample-input/middle.schema.json` 是 6 路引擎产出的**唯一**目标 Schema。

- 任何引擎产出**未通过 schema 校验** → 视为未完成（铁律：坏 → OK 成本永远高于误报）
- 改 Schema 必须改 example + 改 4 段计数 + 改所有引用路径
- Schema 版本号 = 系统版本号

## 4. 三构造同源（v4.1 · HTML 是定案事实源）

| 交付物 | 受众 | 生成方式 |
|---|---|---|
| `<产物根>/design-system.html` | 人看（**定案事实源**） | gen_html.py 渲染 + agent 补全到定案 → dual_scale.py 双标折算 |
| `<产物根>/system-rules.md` | AI 读 | **html_to_md.py 从定案 HTML 派生** |
| `<产物根>/system-rules.json` | 机器消费 | **html_to_json.py 从定案 HTML 派生** |

- **产物根 = `<项目>/design system/out/`**（多套设计系统并存互不干扰）
- **站④ 工序顺序禁反：先 dual_scale 双标折算（1x 主口径），后 html_to_json / html_to_md 派生**——顺序反了 json/md 口径错、三构造不自洽
- **中间数据（middle.json / normalized.json）是提取过程记录，归 `work/`，不改不交付；normalized.json 已废除交付身份（v2/v3 旧口径），禁以任何交付口径提及**
- 一致性由单源派生在构造上保证：改产物 = 改定案 HTML → 重新派生；**禁止手改 md/json 后不同步 HTML**
- gen_md.py 已废除（deprecated/）——v3 时代"normalized 直接生成 md"的路径不再使用

## 5. 4 段 token 计数口径

**计数模式 = 4 段相加（基础 + 语义 + 组件 + 度量）。真实案例 templates/ 实测 134（35+29+22+48）——是案例值，不是及格线。**

- 真实项目**计数以实测为准**：三构造对账（self_check counts 件含 json 核对）
- **禁止塞槽**：为凑数字硬编槽位（Ludo 事故"粉叫 blue-300"）——命名必须跟值走（名实一致件套会抓）
- 组件覆盖同口径：项目实测有几个写几个；component-anatomy 33 类字典由 gen_components 自动枚举坑位（缺坑出占位），agent 填值或声明不适用
- **概念规则层（设计要求/禁令）来源 = `references/design-quality-rules.md` 六域规则库**：填充时逐域筛选、消化为带本系统值例证的条目，禁空白域禁照抄；**提取层实测值违反通则只标 REVIEW 提示，禁改值**——输入是什么输出就是什么

## 6. A 类集成 ≠ 调子技能

| 类型 | 含义 | 例子 |
|---|---|---|
| **集成** | 把对方**思路**（盘点模板、视觉盘点子模块逻辑）抄/化用到本技能 | A-01 集成 flow-front-ui-line-cy-design-pack-pipeline ①盘点思路；A-02 集成 ②视觉盘点逻辑 |
| **调** | 通过对方入口（CLI/API/技能触发）直接用对方代码 | A-04 调 flow-front-ui-line-cy-img-to-code 单图高保真；C-1 消费 Figma 工具 JSON |

**A 类严禁调 flow-front-ui-line-cy-design-pack-pipeline 本体**——A 是把对方**第 ⑥ 站**反过来用的独立技能。

## 7. 自检十三件套（必跑，路径参数必填指本项目 out/）

```
python scripts/core/self_check.py <项目out目录> [--source-dir 源材料目录]
 1. counts          4 段实测 = md 声明 = HTML 声明 = json tokens.count（三构造对账）
 2. anchors         导航 ↔ id 动态互验 + 编号连续（不写死章数）
 3. contradictions  历史矛盾条文正则（按块切行防跨卡误伤；剔除禁令章/教学否定句）
 4. raw_values      白名单 = 本项目 token 值 + 文档排版/生成器结构色（外来品牌色 = 污染 REVIEW）
 5. features        交互功能存活 + 名实一致（颜色词命名与色相符）
 6. gradient_truth  源渐变种类 vs 产物渐变 token（--source-dir 启用；认 linear/radial/conic）
 7. doc_contrast    文档结构元素实际底×字对比度（含 var 链穿透）
 8. source_audit    溯源声明回源核对（--source-dir 启用；0 命中 = 瞎编）
 9. css_syntax      文件头完整 + CSS 缺分号粘连/无单位值
10. delivery        字体自托管存在 + 剪贴板 execCommand 降级 + 皮肤点缀色来自项目 token
11. workspace       交付区卫生（.py/.bak 留交付区 = REVIEW）
12. assets_registry 素材登记对账——normalized.assets 插画 ↔ md 素材章（10/24 线合流）
13. template_form   模板形态对照——templates 逐章签名（章节/标题/spec-label/资产元素）
                    自动派生、换模板自动跟随，对产物 diff（10/24 线合流）
```

**任一 REVIEW** → 不得宣称"完成"；只展示"哪些过 / 哪些要人决"。自检脚本历史上曾硬编码读技能自家演示目录造成假绿（Ludo 事故自招）——路径参数必填即为此雷拆除，**禁改回默认路径**。

## 8. 子代理纪律

- 视觉盘点 / 视觉模型质检 / 自检**派子代理**
- 任务书**全文复制到子代理提示词开头**（`references/agent-prompts/*.md`）
- 任务书必带"疑点清单"节（强制全量披露）
- 子代理**只读不写**（自检类）；视觉盘点子代理**只看图不查代码**

## 9. 失败处置

| 失败类型 | 处置 |
|---|---|
| 激活参数未决未清零 | 按表单组装规则补问（只问未决项），不动手 |
| 路径/URL 不可达 | 重问第 2 项 |
| Schema 校验失败 | 报告哪段缺，**不强行编造 demo 值** |
| A 类高保真 2 轮失败 | 跳过该页进 failed 队列，**不阻塞主流程** |
| 自检任意 REVIEW | 报告根因 + 改生成/派生，**不修模板实例**（模板只随案例数据走） |
| 换肤校验 FAIL（exit 1） | 模板 --skin-* 块形态被破坏 → 恢复模板皮肤块，禁手改产物皮肤 |
| 3 轮修复仍失败 | 进交付报告"留档代价 > 修复代价"判定，**不阻塞用户叫停** |

## 10. 状态机铁律

- **不跳站**（激活 → 提取 → 体系化 → 定案 + 派生）
- **不并行**（每站等上站 gate 通过再跑）
- **不把 FAIL 解释成 PASS**（自检的 REVIEW 必须升级用户）
- **产物目录白名单**：产物根 = `<项目>/design system/out/`，根下只准有交付物（design-system.html / system-rules.md / system-rules.json / system-spec/ / assets/ / hifi/ / work/ / source/，与 station-guide §目录纪律及 self_check 机器白名单同口径）——**work/ 收中间 json 与临时脚本，source/ 收源材料快照（fetched.html 等）**，交付区禁 .py/.bak 残留（workspace 件套机器核）；短任务不立 PLAN.md 台账，产物即状态

---

*solo-ui-line-cy-design-system-extract · CLAUDE.md · v4.1.0 · 2026-11-03（v4 架构线 × 2026-10-24 Ludo 整改线双线合流）*
