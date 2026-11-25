# wiki 检索与读取（wiki-access）

> **【本包适配注记】** 本文自源选型技能全文复制，正文一字未改。本包对应关系：①触发场景=第 0 步选型（selection.md ③，用户第 0 问选 B）；②深读 prompt.md 的时机=比稿池呈报**前**（拍板前不是拍板后）；③兜底链适配：正本"主技能九槽"=本包 `assets/style-presets.json`，AI 自创按用户裁决**允许**（仅兜底位+显著标"AI 新创"，见 selection.md）；④demos 实现层参照子代理禁读，比稿代理同样禁读（防锚定）；⑤**prompt.md 验真口径修正（2026-11-23 实测）**：本文"必须以 `---` frontmatter 开头"与卡库实况不符——实测卡以 `# 提示词` 标题开头（内容为真件），两开口径皆认（`# 提示词` 或 `---`），以 `<!doctype` 开头才是回退假页。

design-style-wiki（风格卡库，≥173 卡（库持续生长，以 manifest.js 实际为准））是候选检索的**第一优先源**。本文件=探查定案（2026-11-05 实测扫描 ≥173 卡（库持续生长，以 manifest.js 实际为准）全量），照读即可，不再探查。

## 路径与总原则

- 根：`https://design-style-wiki.pages.dev`（公网唯一源）
- **BRIEF.md 原生检索协议**（库设计时就为 AI 消费而建）：先读索引 → 指纹比对取 top-N → 只深读入选卡。遵守它，别全库遍历。

## 源探测（唯一源：公网）

**只走公网源 `https://design-style-wiki.pages.dev`**——本机有没有本地 wiki 都走线上：保证你和别人看到的是同一份数据、同一条路径（你测的就是别人用的）。

| 层 | 根 | manifest | 卡文件 |
|---|---|---|---|
| 公网（唯一） | `https://design-style-wiki.pages.dev` | `/manifest.js`（根，无 dashboard 前缀） | `/cards/<slug>/…`（无前缀） |
| 降级 | 公网不可达（纯离线） | 兜底链：九槽 style-presets.json → AI 自创（标 origin=ai-generated） | — |

**内容校验（必须做，不能只看 HTTP 状态码）**：Pages 对缺失路径回退 200+站点首页 HTML——①manifest 内容必须含 `DSW_DATA`（剥前缀后 JSON 解析）；②prompt.md/card.md 必须以 `---` frontmatter 开头且**不是** `<!doctype` 开头；③demos 链接可能 308 重定向，跟随即可；④拉取按 UTF-8 解码。curl 默认 UA 可能被 403，带浏览器 UA 或用 fetch 工具。

## 分层读取（最稳路径）

| 步 | 读什么 | 用途 |
|---|---|---|
| 1 候选检索 | `/manifest.js` | **单文件完成 90% 检索**：≥173 卡（库持续生长，以 manifest.js 实际为准）的 id/zh/en/family/era/mode/tags/**one（比喻锚点式一句话）/feel（气质词）/summary**/colors（hex+中文名+**用途约束**）/best_for/avoid_for/fp/cover/heat/platforms + 13 家族（中文名+定位）+ 10 场景（zh/desc/kw 关键词）。注意：JS 赋值文件，剥掉 `window.DSW_DATA =` 前缀再 JSON 解析，约 0.2MB |
| 2 深读入选卡 | `/cards/<slug>/prompt.md`（九段提示词正本）+ `card.md`（背景） | **适配报告出街前的必读前置（时机=拍板前，不是拍板后）**：prompt.md=九段合并版提示词的独立正本，推荐依据/冲突发现/适配点全从它读——一句话气质看不出"禁品牌换色/数据密集慎用"这类硬冲突；card.md 作背景参考（易混淆判别/适用品类/实现层细节）。**禁只读 card.md 不读 prompt.md**——漏读它会误判"提示词要现造"（jiancewuyou 事故定案） |
| 3 封面 | `/cards/<slug>/cover.svg` | <5KB 程序化 SVG（用卡自身色值绘制），可直接内嵌报告/比稿卡 |
| 4 实现层参照 | `/cards/<slug>/demos/<变体>/{web,mobile}.html` + `gui.domain.js` | 主进程适配参考与事后照镜对账用（结构/字体/动效/材质规范在 gui 域；取最后一个 `=` 之后的对象字面量）——**子代理禁读**（防锚定，见 specimen-card-spec「禁读已有 demo 卡」；参照物进项目的只有 prompt.md） |

## 检索策略（扩散→收敛两段）

**主机制是 AI 的语义扩散，不是关键词匹配**——字面匹配不到≠不适合（点餐 App 的好候选可能藏在"市集""国潮""插画"里，而不是"餐饮"关键词下）。

- **紧凑视图（必做，省上下文）**：manifest 整文件 ~0.2MB，**别整读进上下文**——用一行脚本（python/node 皆可）提取扩散所需字段（id/zh/family/one/feel/heat/platforms）生成紧凑清单（约 1/10 体积）再读；
- **扩散段（先）**：对照产品约束表（见 picker SKILL.md ②——产品性质/场景成败标准/品牌层），通读紧凑清单每张卡的一句话（one/feel），判断"这张卡能不能承担约束表里的任务"——不是"它有没有品类味"；不限关键词、不限家族，鼓励非显然方向；
- **收敛段（后）**：从扩散池挑跨方向的 top 候选深读 prompt.md 验证——硬冲突剔除、适配点标注，出适配报告；
- **辅助线索（不当漏斗）**：场景路由（scenes[]）/跨族差异/best_for 文本/heat——只做排序与平手裁决的参考；
- **过滤永不隐藏卡（jiancewuyou 事故定案）**：任何过滤只用于排序与推荐，不用于从名单里删卡——用户点名某风格而它不在候选里时，先回全量名单核对（flat-2x「扁平 2.0」因缺 mobile 标签被筛掉：卡在库里、名单上没有=检索失误）；
- **成本口径**：九段正文每卡约 2000 字，深读本身便宜，深读张数不设限——贵的是上下文累积（manifest 整读+多轮工具调用的重复处理），紧凑视图就是为此设的。

## 已知缺口与对策

- **无数值化 token**：圆角/阴影/字号藏在 `fp[]` 文字指纹与 gui 散文里——**AI 现场归纳成 token-minimum 取值**（不建机械映射，读文字取值本就是 AI 长项）；
- `manifest` 的 `demo_pages` 字段为 0 填充（定义了没用）：demo 路径自己扫 `cards/<slug>/demos/*/`（结构规律：`<slug>-*-v2/{web,mobile}.html`）；
- `heat` 字符串/`mode`、`gui_tier` 枚举缩写（pers=气质系实现层薄 / main=主流系实现层厚 / na）：picker 做映射；**实现层参照优先选 gui_tier=main 的卡**；
- `official.domain.js` 153/173 为空（正常，仅参考系统卡有官方材料）。

## 勿读清单（过时产物）

- 公网源上只有 manifest 与 `cards/<slug>/` 正件可信；历史过时产物（atlas/INDEX.md、dist/style-wiki-full.md、顶层 demos/ 镜像）未部署到公网，遇 `<!doctype` 回退页即路径不存在。

## 兜底链

本地+公网都不可达（纯离线环境）或 wiki 在位但无合适候选 → 扩大族别重检一轮 → 仍无 → flow-ux-ui-line-cy-hifi-design 九槽（style-presets.json）兜底 → 彻底没有 → AI 自创（标 origin=ai-generated，完整描述+气质锚点，不回流 wiki）。
