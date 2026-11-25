# 静态稿 → 编辑器版 转化规范（附加A 执行规范）

> 出处：2026-11-19 师傅工单 harmonyos 线试点实证（3 屏全链绿）。试点全记录与坑明细：该项目 `editor-pilot/report.md`。
> 定位：把 gui 技能产出的静态高保真单文件（preview-shell 壳 + N 屏 + aside.anno）转成 build.py 正式链的可编辑产物。

## 总则

**转化不是无损转换，是"自由 CSS 表达"翻译成"受控令牌/组件包表达"。损耗必然，策略=损耗账面化：转前建账、照账转化、转后对账、对不上走例外。** 脚本不许吃源文件自作主张——只执行人工签过字的账。

源稿只读；全部产物进独立目录（`editor-<项目名>/`），转坏删目录重跑。

## 三份账（转前必建，验收的尺子）

1. **特征样式清单**（accounts/feature-inventory.md）：逐条列材质/几何/色值/字体/动效，每条标注表达判定——token（令牌可表达）/自由CSS（原样保留）/例外（表达不了，登记边界）。
2. **交互映射表**（accounts/interaction-map.md）：源标注→data-on 映射逐条列；机械映射人工核对后脚本只执行表；无业务落点的可点元素**不发明交互**，防过度转化断言（decorative guard）。
3. **令牌对照表**（accounts/token-map.md）：正本槽映射（token-keys.json 逐字）+扩展键（表外语义色→`--sp-<键>`）+值域登记（design-system JSON 项目版）。

## 转化管线（脚本自动 + AI 填槽，工具都在技能 scripts/）

**脚本步**（`scripts/editor_convert.py`，通用版；试点项目 `editor-pilot/tools/convert_pilot.py` 为首个参考实现）：
拆屏 → `data-go`→`data-on goto`+`data-eid` → 筛选 chips 子项加 `.chip`（触发运行时内置选中态组）删 data-seg/data-tab/data-filter → 插 `.scr-head` → 图片 dataURL → **内联 style 颜色 var 化**（多屏源稿行内色值多，漏了静默留硬值——lint 会拦，但别等门禁抓）→ **业务 CSS 全选择器加 `.screen` 作用域前缀** → 颜色 var 化（正本槽 + `color-mix` 派生透明档 + 扩展键）→ 圆角/边框主档 var 化 → box-shadow 整串保护+登记 → 占位屏（被引用未转化的目标屏，防空跳）→ 自检（CSS 括号配平 + 旧标注残留=0，不过不落盘）。

**AI 步**（`scripts/editor_gen_tokens.py` 出骨架，AI 按账填语义）：值域登记 JSON 全自动；STYLE-PACK 正本最小集槽位骨架自动生成、真实值对照账3 填写；palettes 配 4-5 套跨色相；COMPONENT-PACK 10-15 条；claims 反扫可脚本化（grep data-eid→goto 即可）。

**配套工具**（同在技能 scripts/）：`editor_check_collisions.py`（转化前跑，K1 前置）、`editor_shoot_compare.mjs`（对账截图：--src/--built/--out/--screens）。

## 十坑（全部试点+全量实证，动手前先读）

| # | 坑 | 解法 |
|---|---|---|
| K1 | 运行时/种子全局类污染页面（.hero 染蓝、.chips 强制 wrap、.app 加 gap、.viewport 顶垫 34px、.flow 加 gap:9px/padding:4px） | ① 全选择器 `.screen` 前缀 ② 剔壳规则黑名单 ③ 显式压回运行时漏进属性（BASE_PATCH 现含 5 处：app gap / chips wrap / hero 渐变+白字+flex / viewport 垫层 / flow gap+padding）|
| K2 | box-shadow 保护正则吞规则闭合 `}`，CSS 中段全崩 | 正则用前瞻 `(?=[;}\n])`；**转化脚本自带括号配平自检**（{=  }），不配平不落盘 |
| K3 | lint 整串归因失效（静默坑） | shadow 扫描用 group(1) 不带属性名；shadow 内嵌色值登记进 tokens 颜色集 |
| K4 | build 拒绝覆盖旧产物，报错被截断，修完看的还是旧文件 | 纪律：每次构建必验证"新产物标志"（Built 行/配平数）再进下一步 |
| K5 | 扩展键 `--sp-<键>` 构建期不发静态值，页面渲染失败 | 片段 CSS 头部自带 `:root` 扩展键定义兜底（与包值一致，运行时激活后覆盖无害）|
| K6 | `--active-pack` 触发皮肤注入器硬涂 .hero 等区块 | 转化构建**不传 --active-pack**；换肤走编辑器面板动态激活 |
| K7 | verify-interactions mobile 视口 640 在长页面树下临界失效：device 左缘元素（页内返回钮 x≈148）被 ASIDE.ed-sidepanel 盖住，真点超时=假阴性 | 工具 mobile 视口已改 800（2026-11-19 已修）；**屏数翻倍/页面名变长时先复核验收工具视口适配** |
| K8 | 改壳时 JS 字符串转义被多层转义链（bash→python→文件）吃掉，运行时整块语法错误、真点大面积假死 | 纪律：**改壳后构建前先跑内嵌 JS 语法自检**（逐块 new Function 校验）；不可见字符宁用 chr() 构造 |
| K9 | 换肤应用包时 chooser 组件重写层（高特异性 `html[data-ui-style]` 前缀）把页面 .hero 等重写成 accent 纯色，毁掉源稿设计 | build 加 `--conversion`：产物标 data-conversion，chooser 对转化产物跳过组件重写段、只换根变量——换配色=主题色柔光跟随（光晕/按钮/选中态），页面设计不动 |
| K10 | 压回规则"存在"但没赢：运行时 `.device.mobile .viewport`（三类特异性）压过两类压回，34px 垫层实际没压掉 | **压回选择器必须对齐运行时规则的真实特异性**（如 `.screen .device.mobile .viewport`）；压回后必须实测 computed 值验证，不能只看规则存在 |
| K11 | 域化选择器带空格：`.screen [data-style-id=…]` 后代形式永不命中——变量全灭、样式落回种子默认（chips 竖排、hero 蓝底深字、圆角 16→10 同根；2026-11-24 uni-ui 实测） | **连写** `.screen[data-style-id=…]`——data-style-id 挂 .screen 自身；convert 的 dom_scope_css/ext-keys 两处已修连写（scope_prefix 原本就连写），手写 CSS 同此口径，渲染对账门兜底 |

## 正式链（全绿标准）

```
lint_tokens 清零 → qa_receipt 造 U1+U2(final) 回执 → build.py --pages --start-doc --conversion 正式构建
→ editor_gen_claims.py 反扫片段生成 claims → verify-interactions 真点全绿（闭环断言+decorative 降级+guard）
→ 截图对账：源稿 vs 产物逐屏对比，账1 特征清单逐条目检
→ 渲染对账门：`scripts/qa/acc_render_diff.mjs --src <源稿> --built <产物> --db db-<风格id>`——静态稿为基准
   逐屏计算样式差分（按单类聚合值集），**唯一拦得住"选择器未命中/变量死/种子回退"类渲染退化的关**
   （2026-11-24 uni-ui 实测定案：chips 竖排/hero 蓝底深字人眼之外无一关卡住）；exit 1=差异清单即工单，
   归因修根因复跑归零；exit 2=环境不可用按降级口径声明
```

claims 生成（此前无生产者，复核 P1 已补）：`python scripts/editor_gen_claims.py --pages <片段目录> --out qa/claims-gen.md --guard "页id:sel:选择器"`——从片段反扫 data-eid/goto 自动生成断言（目标屏在包内=真断言；缺页=decorative 降级；--guard 加防过度交互断言）。生成物落**独立文件**直接作 verify-interactions 的 start-doc 输入（工具支持全文档扫描围栏）——V06 定案交互声明**不进开工文档**（start-doc.md 头部声明），禁嵌入开工文档。

`--conversion` 必带（K9）：产物 html 标 data-conversion，编辑器换肤跳过组件重写层，保留根变量段（主题色/字体/圆角/间距档+暗色+壳弹层）——主题色柔光跟随（光晕/按钮/选中态），页面设计不被纯色覆盖。换肤语义验收：应用任意配色后，源稿卡片（毛玻璃白卡等）形态不变、主题色系元素跟随新色。

- `--check` 是 dev-mode 假绿，**不许**当验收。
- 构建带 `--start-doc` 必须过回执门禁（U1/U2）——这是保障不是负担，照走。
- 片段命名：界面可见名一律中文（build 命名门禁）；占位屏页名带"（待迁移）"。

## 交付形态：代码+asset（`--asset-out`）

```
build.py ... --icon-families lucide --asset-out build/<项目>-editor/
```

- 产出 `DIR/index.html + DIR/assets/`：图片→`assets/img/`、样式→`assets/*.css`（**assets 根，不进 css/ 子目录**）、可执行脚本→`assets/js/`；页面 DOM 与 `prototype-*` JSON 契约块**保持内嵌**（file:// 直开不依赖 fetch）。
- 字体随包拷进 `assets/fonts/`；CSS 内 `url(assets/fonts/…)` 由构建改写为 `url(fonts/…)`。
- **两个 file:// 硬约束**（实测踩过）：①Chromium 字体加载按目录隔离，CSS 必须与 fonts/ 同级；②图标库全量注入约 15MB，转化线用 `--icon-families` 只注实际用到的族（index.html 16MB→952KB）。
- 缺省不带 `--asset-out` = 单文件模式，向后兼容。

## 风格包（换肤能力）

- STYLE-PACK tokens：正本最小集全量给齐（缺一个键 verify_blocks 就拒）+扩展键；l2Overrides 的 selector 只写页面内组件类。
- palettes 同风格多配色：**第一套=品牌原色**，再按风格气质配 4-5 套跨色相方案（每套四槽 swatches + hero/line/muted 全角色），别只给同色系近邻。
- 组件包 10-15 条（六类覆盖），html 片段遵守片段契约（data-eid/data-block，禁 script）。

## 例外机制（对不上的走这里）

编辑器表达不了的：不硬凑。两条出路——自由 CSS 层原样保留（lint 不检的属性如 mask/backdrop-filter/keyframes）；真表达不了的登记交付边界（"这项在编辑器版里的形态是 X"）。**交互降级类例外（如筛选真过滤→选中态）必须报用户拍板，不许脚本自行决定。** 例外清单超过两屏 CSS 总量两成 = 映射策略不成立，停工重议。

已解决的旧例外（2026-11-19 壳修复后失效，别再登记）：
- ~~旁批面板缺位~~：编辑器壳批注面板已接 `aside.anno`（旁批条目带标题完整展示，与 data-note 条目共存）；壳切屏动画已改为只作用于框内内容层（.viewport），device 框不再跟随位移。

## 全量铺量跑本

加屏 = 转化脚本 --screens 加一项。页面分组：`--groups "组名:屏id,屏id;…"` 按导航结构分目录输出（构建自动生成左侧分组）；分组依据=源稿侧铺量整理好的导航结构，转化线只继承不发明。顺序：**撞车检测先扫新屏类名**（`editor_check_collisions.py`）→ 跑转化 → lint/构建/verify → 对账截图（`editor_shoot_compare.mjs`）。多风格线各自独立跑（类名撞车面独立、配色独立提账）。屏数翻倍或页面名变长时，先复核验收工具视口适配（K7）。全部屏对账齐后，一次性出正式产物（asset 模式）交付。

## 回装：产物内追加第二风格（multi-style-spec v2）

两个触发场景：①构建时多风格（主管线，逐风格注入）；②事后回装（换风技能第 4 步，客户产物直接加一套可切换风格）。机制正本=`references/multi-style-spec.md`（v2 屏集合组：每风格一套 `section.screen[data-style-id]`，页数可不守恒，页面树按风格分组表）。

```
python scripts/editor_inject_style.py --target <已构建产物.html> --fragments <B风格片段目录> \
  --style-blocks <B风格受控块.json> --db db-<新风格短名> --pack-id <B风格主包id> \
  [--src-db db-main] [--screens 前缀化页id列表] [--out <新文件>]
```

- `--db`：新风格屏集合 id（值域=domBaseId，`^db-[A-Za-z0-9_-]+$`），同时是页 id 前缀段（B 片段页 id 自动前缀化为 `<短名>-<语义id>`，goto 同步）；
- `--src-db`：**原风格屏集合 id（缺省 db-main）**——源屏回填 `data-style-id` 与既有页面 CSS 域前缀升级用它；产物源风格不是 db-main 时必须显式传；多次注入时传产物当前基域即可，自检容忍全部既有域（N≥3 注入不死）；
- B 片段业务 CSS 必须已带 `[data-style-id="<新域>"]` 域前缀（用 `editor_convert --db db-<新风格短名>` 产出，裸样式=违规拒绝）；
- 注入器自带备份（`.bak-<时间戳>`）+ 十步自检（每屏恰一风格标记/屏数分域对齐/eid·sprite 查重/pageTree 分组表形态/v1 残留拒绝），不过不落盘；
- 转后验收=multi-style-spec §六：切卡左树整套换 + 页数不对称正常 + 两域真点各自全绿 + `verify_blocks.py <新产物>` 过门禁 + **渲染对账门**（`scripts/qa/acc_render_diff.mjs --src <B风格静态稿> --built <新产物> --db db-<短名>`，exit 1=差异清单即工单，2026-11-24 定案）。
- **旧版运行时产物**（无面板机制的存量产物）：注入器入口检查会具名拒绝并打印处置三选——A 标准步骤与主客顺序断言见 `multi-style-spec.md` §九，禁盲注。

## 构建时多风格（编排，2026-11-23 定案）

**架构=编排式**：build 先出首选风格产物 → 逐个 `editor_inject_style` 回装附加风格，不改 build 组装段。与换风技能第 4 步**同一注入器**——主管线场景=开工时 N 风格一次编排（本节），换风场景=客户产物事后加卡（上一节回装），机制正本都是 `multi-style-spec.md`。

编排单 JSON（每项目一份）+ 薄编排脚本 `scripts/build_multi_style.py`（纯参数透传，失败即停，`--dry-run` 只打印命令）：

```json
{
  "build":   {"args": {"pages": "pages", "title": "项目名", "style-blocks": "首选风格块.json",
                       "active-pack": "首选包id", "output": "build/single.html"}},
  "injects": [ {"args": {"target": "build/single.html", "fragments": "frag-第二风格",
                          "style-blocks": "第二风格块.json", "db": "db-xxx", "pack-id": "第二风格主包",
                          "out": "build/multi.html"}},
                {"args": {"target": "build/multi.html", "…第三风格…", "out": "build/multi.html"}} ],
  "verify":  ["verify_blocks"]
}
```

```
python scripts/build_multi_style.py <编排单.json> [--dry-run]
```

- 附加风格片段与受控块半边用 `editor_convert.py --db db-xxx` 产出（半边 JSON=该风格自己的 domBases/families/packs 成员，注入器查重合并）；
- `build` 可省略=对已有产物直接回装；每步非 0 即停并打印失败步与参数；verify 列表支持 `"verify_blocks"`（吃最后产物）或 `{"tool": "…", "args": {…}}` 全参数透传；
- build 拒绝覆盖旧产物（K4）——编排重跑前先清输出路径；单测样例见 `tests/test_multi_style_orch.py`（8 断言：双屏集/双卡/分组表两段/中文页名/dry-run 不落盘/AGENTS.md 锚定物断源）。
