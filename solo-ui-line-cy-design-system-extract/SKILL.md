---
name: solo-ui-line-cy-design-system-extract
description: >
  从设计源（多图包 / HTML / URL / Figma / 文本，蓝湖可选）提取设计系统，
  沉淀成三构造交付（design-system.html 人看定案 + system-rules.md AI 读 + system-rules.json 机器版），
  让后续 vibe AI 编码时直接消费——保证产出 UI 一致、不像 AI 默认模板。
  可独立调用，也可被 flow-front-ui-line-cy-design-pack-pipeline 第 ⑥ 站调用。
  触发：用户表达"提取设计系统 / 沉淀设计规范 / 出设计系统文档 /
  从 [图包|HTML|URL|Figma] 提 token / 把这套设计系统化"等意图时使用。
  适用边界：本技能做的是「照抄提取」——设计源已有成熟、完整、定稿的视觉（成品图包/页面/Figma 稿），
  从中归纳沉淀既有设计。不适用：设计源只是结构草稿（如低保真 HTML 原型）、视觉决策尚未定稿、
  需要通过逐项共创拍板来「生成」一套新设计系统——那是共创生成，超出提取的范畴。
---

# solo-ui-line-cy-design-system-extract — 设计系统提取技能

把任意设计源**系统性**变成可被工程消费的设计系统。**目标产物 = 同一内容的三种构造**：演示（HTML，定案事实源）+ 规则（md，AI 读）+ 结构化数据（system-rules.json，机器消费）——md 与 json 由定案 HTML 派生，一致性由构造保证。

**激活导览（第一动作）**：技能被调起后**立即**读 `references/onboarding.md`，按模板播报（每句独立一行）；先盘点后播报 = 违规。细则不进本文件。

---

## 核心铁律（全文准则；细则在各文件）

1. **职责边界 = 收 + 出**：只做"6 种输入 → 三构造交付物"；源获取归用户/上游，下游消费归其他技能。
2. **Schema 是契约**：所有引擎产出汇入 `sample-input/middle.schema.json`；不合规 = 未完成。
3. **三构造自洽，实测计数，名实一致**：HTML（权威源）与派生的 md / system-rules.json 同版本同计数同章节；**normalized.json / middle.json 是 work/ 过程件，不是交付物，禁以任何交付口径提及**；计数以实测为准，严禁凑数；命名跟值走。
4. **PASS 含金量**：自检拿不准必须 REVIEW；守门员是脚本 verdict，模型目检只是复核。自检任何一项 REVIEW → 不许宣称"完成"，只展示"哪些过了 / 哪些要人决"。
5. **模型自由度仅两处**：解析策略选择；定案 HTML 时 token 值的最终确认。其余以脚本与自检为准。
6. **异常必上报，禁自动绕路**：实测与契约不符（证据全 0 / 数量骤降 / 文件缺失）→ 停下定性上报；先怀疑工具再怀疑输入。**禁止把工具故障"合法化"成降级路线继续跑**（Ludo 二次事故教训：旧脚本不读外链 css 造成"5 页全 0"，执行会话却据此自判"输入薄→降级 rawjson"）。
7. **没拿到"写吧 / 落盘"指令不写文件**；激活后先读 `references/activation.md` 锁定 6 项前置参数（只问未决项）。
8. **新约束立门**：进本技能前先回答"能不能变成代码"——能则进脚本/自检件，不能才写文字，且写细则文件、不进主 md。
9. **产物用自己的设计规范排版（强制）**：三构造——尤其演示 HTML——的文档样式必须直接取自本次提取出的 token 表（皮肤色、字体、圆角、间距档），演示页看起来就是被提取的那套系统；文档结构与项目 token 的分离由 --skin-* 皮肤层承担。自检 doc_contrast + raw_values 两件会核这个：皮肤色不在项目 token 白名单=违规。
10. **对外话术纪律（全程）**：**一切用户可见的文字**只说材料语言和结果语言；内部代号（A/B-1/B-2/C-1/C-2/D、站号、gate、熔断、降级、Schema、middle.json、normalized.json、token 段位名）**禁止上用户屏幕**，只进文件与代码；产物形态是契约常量**禁问**，输入类型自动判定**禁问**，参与度默认全自动**不问只播报**；AskUserQuestion 一个 tab 对应一个参数，未决项 = 0 **不出表单**。对照表见 `references/activation.md` §7。
11. **外部协议优先**：任务书附**协议页**时（如主线 flow-ux-ui-line-cy-hifi-design 管线调起），守门与登记口径以协议页为准——「写吧/落盘」停等在自动模式下转待确认包并标「未确认·自动通过」；无协议页按本文件原生流程。

## 输出规则（正本 8 句的概括口径 · 正本见 output-templates.md §0）

**正文不带思考过程；频次要带主语（源稿 5 处，禁裸 ×N）；实物按 1x 真实大小渲染；档位只收网格值/惯例值且字体不低于 11px（1x）；组件库只收交互控件；来源标注到条目级（AI 补全逐条标）；溯源声明不确定就不写。**
完整定义与反例见 `references/output-templates.md` §0。多倍图源稿（@2x 截图）由 dual_scale.py 在站④ 定案后统一折算双标（主口径 1x、括注 @2x），脚本守门 + 文字纪律双保险。

---

## 流程（4 站状态机）

```
[用户输入]
    ↓
⓪ 环境体检（doctor.py，READY 才开工）      → scripts/doctor.py
    ↓
① 输入识别 + 路由（6 项参数前置锁定）      → 细则 activation.md
    ↓
② 提取（按路由调引擎，产出 middle.json）   → 细则 station-guide.md 站②
    ↓
③ 体系化（三层 token + 度量 → normalized） → 细则 station-guide.md 站③ + token-architecture.md
    ↓
④ 定案 HTML → dual_scale 双标 → 派生 md/json → 字体自托管 → 自检十三件套 → 落盘
                                              → 细则 output-templates.md + station-guide.md 站④
```

每站只做该站的事；站间不跳步；通过/失败由脚本退出码决定。

| 站 | 一句话 | 产出 | gate |
|---|---|---|---|
| ⓪环境体检 | doctor.py 探测依赖（bs4 阻塞型 / playwright 仅 URL 型） | 环境报告 JSON | READY；或仅 url_only 缺失且非 URL 任务 → 带项裁决 |
| ①输入识别 | 6 项参数锁定（只问未决）+ 选引擎 | 路由决策 | 未决清零 |
| ②提取 | 按路由调脚本（A 图包 / B HTML·URL / C Figma·文本） | middle.json | Schema 校验 |
| ③体系化 | 基础→语义→组件归档 + 坑位契约补全 + 口径折算 | normalized.json | 计数自检 + 命名去重 |
| ④定案+派生 | 渲染补全定案 HTML → **dual_scale 双标（先折算）** → **html_to_json / html_to_md 派生（后派生，顺序禁反）** → 字体自托管 → 自检十三件套 | HTML + md + json | 十三件套全 PASS |

**入口路由表**、**6 项参数**、**生成规则（15 章契约 / 皮肤 / 内容准入三分区）**、**自检十三件套清单**：全在 `references/`（activation.md / station-guide.md / output-templates.md），按站入口先读对应章节再动手。

---

## 前置依赖（第 ⓪ 步自动体检）

Python 3.9+ / beautifulsoup4(B-1 必需)/ playwright(仅 B-2 URL 抓取;装后 `playwright install chromium`)。**第 ⓪ 步 `doctor.py` 探测全部依赖并给出修复命令**——缺什么它说什么;`--fix` 一键安装(由用户触发,禁执行模型自动装);清单见 `requirements.txt`。

---

## 关键机制（一览；细节在对应文件）

- **6 路输入 → 3 类引擎**：A 图包（集成 flow-front-ui-line-cy-design-pack-pipeline 盘点 + 调 flow-front-ui-line-cy-img-to-code 高保真，最终降级 B-1）/ B HTML·URL（静态解析；URL 先 playwright 抓快照）/ C Figma JSON·文本（工具消费 / 纯 LLM）。路由判据见 station-guide.md。
- **B-1 本地外链 css 必须加载**：CSS 来源 = `<style>` 块 ∪ `<link>` 本地文件 ∪ 同目录 style.css（Figma 导出惯例）——Figma 导出页的证据全在外链 css（Ludo 事故根因，勿再犯）。
- **B-2 两步分离（A8 修正）**：fetch_url.py 只落快照（`source/fetched.html`）即止；静态解析是站②显式第二步（parse_html.py 独立调用）——脚本内禁自动链式，防覆盖上一步输入的 middle.json。
- **美术资产管线**：parse_html 第 6 桶分级（icon_lucide / icon / illustration，语义名 → 结构 → 相对画布比例，禁绝对像素阈值）→ asset_exporter.py 落盘产物 assets/（插画合成 SVG + 位图复制 + manifest.md 登记）→ 素材内部值不产生 token 证据 → self_check assets_registry 对账登记。
- **契约驱动体系化**：tokenize 按 component-anatomy.md 坑位字典逐坑核对，缺项 AI 补全并标注；多倍图口径由解析层探测画布、站④ dual_scale.py 统一折算。概念规则层（设计要求/禁令）来源 = design-quality-rules.md 六域质量规则库——填充逐域消化，提取层实测违反通则只提示不改。
- **形态生成器 + 一键管线**：`run_pipeline.py` 一条命令跑完渲染→形态（组件 33 类枚举/素材网格/线框）→双标→派生（json/md）→字体→自检；agent 只做中间的定案补全（语义活），完成后 `--derive-only` 重派生。中间 json（middle/normalized）归 work/ 不交付。
- **dual_scale.py 双标改造**：@2x 源稿值折算为 1x 主口径、括注 @2x（如 `12px（@2x 24px）`）；CSS 渲染区整体摘除不动；口径基准值（375/750/812）跳过；幂等可重放，`--dry` 预览。**必须先双标后派生**，否则 json/md 口径错、三构造不自洽。
- **字体 fetch_fonts.py 整包自托管**（@font-face / base64 woff2 随产物打包，不依赖系统安装）；交互代码原样保留并带剪贴板降级。
- **自检十三件套**（self_check.py，路径必填）：counts / anchors（动态互验）/ contradictions / raw_values / features / gradient_truth / doc_contrast / source_audit / css_syntax / delivery（自包含+交互降级）/ workspace（交付区卫生）/ assets_registry（素材登记对账）/ template_form（模板形态对照）。任一 REVIEW 不许宣称完成。
- **集成与子代理派发纪律**：references/integrations.md。

---

## 目录约定（要点）

```
SKILL.md                ← 本文件（路由器：触发/流程/铁律/指针）
templates/              ← 三构造模板实例（案例即模板；15 章 v3 形态）
sample-input/           ← middle.schema.json（核心契约）+ 示例
references/             ← 细则（按需加载）：onboarding / activation / station-guide /
                          token-architecture / component-anatomy / design-quality-rules /
                          anti-patterns / output-templates / integrations / agent-prompts/
scripts/                ← A 图包管线 / B 解析抓取 / C Figma·文本 / core（schema·tokenize·
                          html_to_json·html_to_md·gen_html·gen_components·gen_layouts·gen_assets·
                          dual_scale·asset_exporter·fetch_fonts·fetch_iconset·parse_common·
                          run_pipeline·self_check；gen_md 已废弃进 deprecated/）
tests/                  ← 锚点/计数/Schema/管线/转换器断言（动态章数）

产物根（每次提取）= <项目>/design system/out/   ← 多套设计系统并存互不干扰；根下白名单以 self_check 机器守门为准
├── design-system.html             ← 定案事实源（人看）
├── system-rules.md                ← 从 HTML 派生（AI 读）
├── system-rules.json              ← 从 HTML 派生（机器读）
├── system-spec/                   ← 演示资产：字体 woff2、assets/icons/<图标库>/
├── assets/                        ← 素材落盘（asset_exporter 产物：插画 SVG/位图+manifest）
├── hifi/                          ← 图包线高保真中间产物（A 路由）
├── work/                          ← 过程区：middle/normalized.json、临时脚本、备份（不交付）
└── source/                        ← 源材料快照（fetched.html 等）
```

## 触发与不触发

**触发**："提取/出/沉淀/整理" + "设计系统/设计规范/主题色/组件库/token"；flow-front-ui-line-cy-design-pack-pipeline 第 ⑥ 站调用。
**不触发**：纯知识问答（"什么是设计系统"）；调试组件视觉细节；直接生成 UI（solo-ui-line-cy-amazing-vibe-design）；单图转 HTML（flow-front-ui-line-cy-img-to-code）。

---

*solo-ui-line-cy-design-system-extract v4.1.0 · 2026-11-03（v4 架构线 × 2026-10-24 Ludo 整改线双线合流）*
