# 数据资产登记表（全量 · 出处 / 数量 / 采集日 / 脚本清单）

> SKILL.md 只留 4 行核心；本表是数据资产的完整登记权威。全部为本地快照——技能运行不依赖外部网站。
> 许可与署名：图标库 → `data/icons-json/THIRD_PARTY_NOTICES.md`；refactoring-ui → `data/refactoring-ui/_meta.md`；uupm → `data/uupm/_meta.md`（⚠ 上游许可未查证，分发前核实）。

| 路径 | 内容 | 出处 |
|---|---|---|
| data/uupm/ | 风格/语义色/字体配对/准则/图表色/落地结构/产品类型/提示词 + HTML 落地指南（英文原版备查）；**zh/ 中文沉淀 12 份**（9 份数据集镜像 + products.zh 中文版 + 中文开源字体搭配 typography-cn 13 组 + ux-guidelines.zh 句级翻译版——**当前为空表待补**；由 scripts/uupm-zh.mjs 生成，素材页与 AI 消费中文版；数据更新后重跑该脚本再沉淀） | ui-ux-pro-max 快照（采集日未记录，年龄不可考） |
| data/design-mds/ | **58 个知名品牌设计语言分析稿**（Apple/Stripe/Linear/Notion/Tesla/Claude/Cursor…每品牌一份 DESIGN.md：设计价值观/色板/字阶/间距/组件特征，含 _meta.json 中文名与分组）。⚠ 上游 awesome-design-md 已增长（同类浏览站实测 112 条目），下次联网时重跑采集脚本对齐 | VoltAgent/awesome-design-md（MIT）· 采集 2026-10-22 · scripts/fetch-design-mds.mjs |
| data/refactoring-ui/ | **通用设计规则与禁令（中文合并版）**——案例「设计要求+禁令」章为底本 + RU 补充条目（标 RU）；另存英文快照原文 12 文件备查 | 案例底本 + refactoring-ui-skill 快照（基于《Refactoring UI》，非官方，见 _meta.md；采集日未记录） |
| data/case/ | 骨架模板：案例 system-rules（章节结构/标注写法/禁令模板）+ spec 案例样张（**形态基准**；导出模板内联于 export-clean.mjs）+ **成文前必读的案例导读 `references/case-guide.md`**（结构地图/卡槽解剖/复写工作法）。⚠ **真实项目案例（含业务禁令与 token 全量），整技能对外分发前需脱敏** | solo-ui-line-cy-design-system-extract 产物（与用户实战产物哈希同源 · 2026-10-29 验证） |
| data/icons-json/ | **10 个开源图标库合并 JSON（每库一个 <库名>.json：icons 键→完整 SVG + iconForms 变体表），共 29381 枚**（material-symbols 7864 / tabler 6238 / remixicon 3078 / phosphor 3024 / solar 2470 / bootstrap 2078 / lucide 1891 / boxicons 1479 / heroicons 972 / feather 287；lucide 为默认本地预览库） | 各开源库 · 采集 2026-10-23（2026-11-25 由散装 SVG 合并为 JSON）· 合并脚本 scripts/build-icons-json.mjs · 采集脚本 scripts/dev/_collector/collect_icons.py · 许可见 THIRD_PARTY_NOTICES.md |
| data/component-styles/ | **组件风格库清单 INDEX**（31 库分组登记）+ **已快照文档 446 个（23 库）**：antd 40 / element 30 / daisyui 27 / vant 15 / varlet 14 / arco 14 / antd-mobile 12 / wechat-miniprogram 10 / naive-ui 4 / tdesign-mobile 2 / weui 3 / hig-apple 12 / harmonyos 26 / material3 11 / shadcn-ui 30 / chakra-ui 30 / heroui 30 / mantine 32 / carbon 30 / fluent-2 20 / flowbite 30 / preline 23 / radix-themes 1（Tremor / Atlassian / Untitled UI 仅登记官网出处；23 快照库中 14 库附 _meta.md 记录出处与已知限制，国内 9 库暂缺） | 各组件库官方文档 · 有 meta 的 14 库采集 2026-10-22 · 采集日志 scripts/dev/_capture-log.json |
| design-style-wiki（本机外部库 · 探查式引用） | **中文 GUI 设计风格词典**：151 张风格卡（`atlas/cards/<slug>/card.md`，六段式：一句话/家族层/GUI 实现层/机器层 token 骨架/血统）+ INDEX 谱系决策树——第二步风格定义层与画像风格判断的检索源。**探查式：发现 `atlas/INDEX.md` 才启用；只读不写、不回流、不同步**；检索协议（先 INDEX 后卡、禁全库通读）见其 INDEX ①节 | 项目所有者自建（持续生长中 · 2026-10）· 接入契约 WIKI-INTEGRATION-BRIEF.md |

## 脚本

| 脚本 | 职责 |
|---|---|
| scripts/content-dump.mjs | 原型 → 内容清单（画像用；分叉自 lofi-rebuild-hifi-design，已声明不再同步） |
| scripts/build-manifest.mjs | 清单索引 + 同名冲突预检（画像用；同上） |
| scripts/init-chain.mjs | 新项目开链：生成十步标准骨架（开链必用，禁止手写 chain.json） |
| scripts/build-workbench.mjs | 决策链 JSON → 工作台单文件页（两 Tab）+ 同步产出顶栏四个原始素材入口页 |
| scripts/build-icons-json.mjs | data/icons 散装 SVG → data/icons-json 每库一个合并 JSON（图标键保留 outline/fill 变体；数据源变更后重跑） |
| scripts/build-raw-assets.mjs | 原始素材入口页：组件库风格样张卡（23 库）+ 令牌参考全可视化卡 + 品牌设计语言页 + 图标库页（读 data/icons-json，SVG 消毒）；可独立跑 |
| scripts/fetch-design-mds.mjs | 采集 awesome-design-md 各品牌 DESIGN.md（jsDelivr/raw/GitHub API 三通道）→ data/design-mds/ |
| scripts/export-clean.mjs | 决策链 JSON → 纯净版（system-rules.md + design-system.html；未锁章拒绝导出）。模板 = case 形态（侧栏+hero+章节框架+骨架类+点击复制）；导出时内置品牌污染扫描（case 值残留非零即 FAIL） |
| scripts/verify_chain.mjs | **落锤门禁**（退出码裁定）：shape 契约 / 交付留档 / 组件覆盖度 ≥20 组 / 必备卡槽 / 角色标注 ≥30 / 14 章非空 / case 原生类名 / 品牌污染——每步落锤后必跑，exit 0 才算完成 |
| scripts/uupm-zh.mjs | uupm 英文参考数据 → 中文版沉淀（9 份镜像，zh 目录共 12 份；数据更新后重跑） |
| scripts/dev/ | 一次性采集/调试脚本存档（技能运行不使用） |

## 其他

| 路径 | 内容 |
|---|---|
| examples/ | 标准形态样例：sample-chain.json（规范链 shape）+ workbench.html（渲染样例）+ 四个素材入口页样例 |
| references/chapters.md | 产物章节模板（**14 章** × 生成方式分类；预览与导出共用的唯一章节权威，改章三处同步） |
| references/co-creation-playbook.md | 九段共创玩法手册（三类交互/候选生成规则/应答模式/回流）——九段细则权威 |
| references/concept-boundary.md | 第二步风格定义层的硬边界（单选整卡 / 血统标注 / 自创规则） |
| templates/sample-page-brief.md | 样品页子代理任务书模板（3 版诠释策略 + 数据边界 + 回流格式） |

## 采集日惯例

新采集/更新任何资产组时，在对应 `_meta.json` / `_meta.md` 写入 `fetchedAt`（ISO 日期）与上游具体版本/commit（不要只记 @main/@master 分支引用——不可重现）。当前三组年龄不可考：uupm、refactoring-ui、component-styles 国内 9 库。
