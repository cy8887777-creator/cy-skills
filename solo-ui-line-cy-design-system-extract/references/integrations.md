# 集成清单（从 SKILL.md 下放 · 本技能真用了哪些参照技能的轮子）

> 铁律 6 镜像：集成 = 原文复制 / subprocess 调子进程 / 任务书打包——**不自创**。

## flow-front-ui-line-cy-design-pack-pipeline 集成

| 本技能用 | 复用源（原文复制） | 复用方式 |
|---|---|---|
| A-01 盘点 | `flow-front-ui-line-cy-design-pack-pipeline/scripts/intake.py` | `subprocess.run(intake.py <图包> --probe)` |
| A-02 视觉盘点子代理 | `flow-front-ui-line-cy-design-pack-pipeline/templates/inventory-prompt.md` | 任务书原文 + 模板原文打包 |
| A-03 典型页挑选 | `flow-front-ui-line-cy-design-pack-pipeline/references/strategy-rules.md` | 策略判据原文 |
| A-05 视觉模型质检 | `flow-front-ui-line-cy-design-pack-pipeline/templates/judge-prompt.md` | 任务书原文 + 派裁判子代理 |
| 状态机严格性 / 疑点清单 | flow-front-ui-line-cy-design-pack-pipeline 铁律 | 借鉴思路 |
| 子代理派发纪律 | flow-front-ui-line-cy-design-pack-pipeline agent-roles | 借鉴思路 |

**复制位置**：`scripts/A/_reused/` 下 5 个原文件（intake.py / inventory-prompt.md / inventory-template.md / judge-prompt.md / strategy-rules.md）。

## flow-front-ui-line-cy-img-to-code 集成

| 本技能用 | 复用源（原文复制） | 复用方式 |
|---|---|---|
| A-04 高保真制作 | `flow-front-ui-line-cy-img-to-code/SKILL.md` 完整 5 步状态机 | 通过 Skill 工具触发 |
| A-04 request.json 协议 | flow-front-ui-line-cy-img-to-code 第 1 步契约 | image / output_dir / tier / stack / design_system |
| 铁律 2（模型自由度） | flow-front-ui-line-cy-img-to-code 铁律 | 借鉴思路 |
| 铁律 5（PASS 含金量） | flow-front-ui-line-cy-img-to-code 铁律 | 借鉴思路 |
| 裸值扫描模式 | flow-front-ui-line-cy-img-to-code verify_page.py | 借鉴思路（本技能自实现设计系统领域特化） |

**复制位置**：`scripts/A/_reused/image-to-code-SKILL.md`（摘录）。

## 必须自创（本技能领域独有）

- 6 路输入 → 1 个 JSON Schema（`sample-input/middle.schema.json`）
- 体系化（基础→语义→组件 + 度量归档）—— `scripts/core/tokenize.py`
- 三构造生成（HTML 定案事实源；渲染 + md/json 单源派生）—— `scripts/core/gen_html.py` + `html_to_md.py` + `html_to_json.py`
- 双标折算（1x 主口径括注 @2x，CSS 渲染区摘除不动，幂等 + --dry）—— `scripts/core/dual_scale.py`
- 设计系统领域自检（十三件套）—— `scripts/core/self_check.py`
- 美术资产管线（第 6 桶采集 / 落盘 / 登记）—— `scripts/B/parse_html.py` + `scripts/core/asset_exporter.py`
- 图标整库现拉（按项目风格判定上游库）—— `scripts/core/fetch_iconset.py`
- 字体自托管下载 —— `scripts/core/fetch_fonts.py`
- B/C 类输入引擎（网页解析抓取 parse_html / fetch_url，Figma 摄取 figma_ingest，文本 text_llm——参照技能没做）—— `scripts/B/` + `scripts/C/`

## 子代理派发纪律

- **派发模式（铁律）：子代理一律后台模式（run_in_background）——主会话保持可对话，用户插话不杀代理；回执靠完成通知回收，禁前台阻塞等待。**
- A 类视觉盘点/质检派子代理：任务书 = `references/agent-prompts/visual-audit-prompt.md`（含 6 项验收清单），独立子代理**只看图**不查代码。
- 自检用独立子代理做矛盾条文复查（双轴：spec 找契约偏差，standards 查同族洞）。
- 子代理必带"疑点清单"：审查/测试类回报必含，无论自认为成立与否全数列出。
- 派发前声明分工（几个/各管什么），文件不交叉。
