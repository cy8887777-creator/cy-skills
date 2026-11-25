---
name: solo-ue-line-cy-mockingbot-html
description: 把墨刀（MockingBot）导出的原型 HTML 包转换成干净、可查看、可编辑的静态 HTML。当用户要「墨刀转 HTML / 墨刀导出包还原 / 原型包转可编辑页面 / 生成原型文件夹树」时使用。产物：镜像墨刀侧边栏页面目录的文件夹树，每块画布一个独立 HTML，尺寸按墨刀里设定的画布尺寸，源码可直接改。
---

# 墨刀导出包 → 可编辑 HTML

## 是什么 / 为什么

墨刀导出的 HTML 包（`index.html` SPA + `extra/data.*.js` 私有数据 + `uploads*/` 切图）是 webpack runtime 包裹的 gzip+base64 私有格式，**无法直接编辑**。本技能用 headless Chrome 打开墨刀查看器，逐页挂载画板后从渲染后 DOM 提取节点真值（坐标/样式/文字/图），重生成干净的平铺静态 HTML：

- **可查看**：目录树镜像墨刀侧边栏页面目录（目录→文件夹），根目录 `_index.html` 总导航（左页面树+右画布平铺预览，点击卡片新标签打开）
- **可编辑**：普通 HTML，无构建、无运行时，每节点一个 div + 行内 style，带 `<!-- [idx] parent=N name=... -->` 注释定位
- **画布尺寸不写死**：每块画板按墨刀里设定的 w/h（如 375×812 手机板、750×1754 规范板）

## 墨刀导出格式版本（2026-10-20 双格式实锤，脚本已自动分支）

| | 旧格式（本文档历史基线） | 新格式（PB=v1） |
|---|---|---|
| 数据指纹 | `extra/data.1.js` 含 `H4sIA` gzip+base64 快照 | `window["hzv3"]["psol"]` 明文 JSON，**全包 0 个 H4sIA** |
| 源数据画板 | 快照里有 `rc…` 行 | **无 rc cid**（画板 cid 查看器运行时生成，板名缺失兜底 cid） |
| 挂载模型 | `.tree-node.rResCanvas[data-cid=rc]`，累积挂载，diff 归属/认领/同板复用 | `.pcanvas[data-cid=页面cid]`，累积挂载、激活者带 `.active`；**页面↔画布 1:1**，无需归属兜底 |
| 页面分区 | 画板=设计尺寸 | pcanvas 三区：`screen-header`(状态栏+导航栏)/`screen-content(.widgets 滚动内容)`/`screen-footer`(固定底栏)——**提取根必须含三区**，只提 .widgets 会丢顶栏底栏 |
| path-icon 色值 | 静态字典 `references/icon-colors.json`（hash→色，旧包采集） | 同为 hash 定向硬编码规则（`.kKhnky.fill g [fill]{fill:rgb(234,88,12)}`），**提取时现场扫 stylesheet 建字典**，无规则落回继承色 |
| 交互数据 | widget fiber `hotAttr.interactions` | 同机制（fiber 结构待新格式全量验证） |

自动分支：`read-data.mjs`（探 `"psol"`）、`batch.mjs`/`extract-board.mjs`/`diagnose.mjs`/`read-hotzones.mjs`（`cdp.mjs detectModel()`：有 `.pcanvas[data-cid]` 且 cid 为页面 cid→pcanvas；pcanvas 的 cid 为 **rc 画布段=混合代际→legacy**；无 pcanvas 时 `.tree-node.rResCanvas`→legacy）。两分支产物 schema 一致，gen-html 及下游零改动兼容。新格式 CLI：`batch.mjs --board-mode long|viewport`（默认 long=内容全展开+固定底栏钉到画布底部；viewport=画板视口忠实口径，fold 外内容被 gen-html 越界规则丢弃）。

**混合代际（2026-10-23 飞燕包实锤，第三种形态）**：新查看器 DOM + gzip 数据（TAG 20261013 导出）——初始页画板挂 `.pcanvas` 但 `data-cid` 是 **rc 画布段**（非页面 cid），点击切换的其他页画板全走 `.tree-node.rResCanvas` **单槽换装**（切页卸上一页板），初始板永不卸载；默认页画板同时存在于 pcanvas 三区壳内的同名 rResCanvas（旧分支照常可提取）。判据与处置：detectModel 见 pcanvas cid 为 rc 纯段 → 返回 legacy，整条管线走旧格式分支（旧分支按 rc cid diff 归属，天然兼容）。⚠ 若误判成 pcanvas：WAIT_BOARD 按页面 cid 等画布永远 MOUNTING 超时 → 全部页面被误记「空页面」（实测 5/5 全空、184 页包首跑全废）。

## 分步流程

```bash
# 假设：墨刀包 = <pkg>（含 index.html 的目录），产物根 = <out>
# 所有脚本在 scripts/ 下，Node 22+（用全局 WebSocket/fetch）

# 1. 起 headless Chrome（自动探测空闲端口，默认 9225 起；写 .claude-tmp/chrome-<port>.json 记 pid）
node start-chrome.mjs <pkg>/index.html [basePort]

# 2. 读侧边栏页面树 → manifest.json（folder/page + 层级 + dir 链）
node read-tree.mjs <port> <out-manifest.json>

# 3. 解 data.1.js gzip 快照 → data-map.json（cid→名称字典，数十万条；多语言子画布名只在这里）
node read-data.mjs <pkg> <out-data-map.json>

# 4. 批量提取生成（核心，断点续跑 state.json；自动探测查看器代际：legacy / pcanvas 新格式）
#    规矩：先 --only 抽 3~5 页样板 → 用户验收 → 再全量
#    同 cid 板已有 boards/<cid>.json 时走缓存跳过 DOM 提取（全量省时大头）；--retry-failed 重置失败页重跑
#    新格式（pcanvas）专有：--board-mode long|viewport（默认 long=长图口径，viewport=画板视口）
node batch.mjs <port> <manifest> <data-map> <产物根> [--only cid1,cid2] [--limit N] [--skip-gen] [--retry-failed] [--board-mode long|viewport]

# 5. 交互热区收集（可与 batch 并行：独立实例逐页点击，读 widget fiber 里的跳转定义 → 产物根/hotzones.json）
#    【可整段跳过】纯 UI 交付（不做可点击跳转）时可不采（2026-10-24 用户口径），regen 与产物零依赖它；hotzones.json 仅作交互档案 + add-interactions R5 映射源
#    增量断点（已收板跳过）；--retry 全量重扫。收完 regen 时自动带上热区层
node read-hotzones.mjs <port> <manifest> <data-map> <产物根/hotzones.json> [--only cid,…] [--limit N] [--retry]

# 6. 生成总导航（产物根/_index.html，左树右平铺预览器；读 state.json 给空页/失败页出占位标注）
#    左侧墨刀真实层级页面树（页面嵌套页面也渲染为可展开节点）+搜索；右侧画布平铺墙：
#    点页面平铺其全部画布（卡定宽 320 居中），点文件夹=纯展开/收起子级；卡片=iframe 静态
#    预览+懒加载，点击=新标签打开该画布 html（右侧不允许跳转，跳转在新标签闭环）；
#    缩放 适应/100%；hash 记忆选中
node make-index.cjs <产物根> [manifest.json]

# 6. 对账自检（孤儿/缺失/共用板/失败清单/blob 残留；不平退码 1）
node audit.mjs <产物根>

# 7.（改了 gen-html 生成规则后）用 boards/*.json 缓存秒级重刷全部产物，不重新提取
#    产物根有 hotzones.json 时自动带上热区跳转层
node regen.mjs <产物根> [--only 页面cid,…] [--concurrency 4]

# 7b.（regen 之后）语义交互绑定：元素本体绑 onclick（tab/返回/取消/父子链接四规则，见生成规则 18）
node scripts/add-interactions.mjs <产物根> [--dry]   # 幂等；跑完死链断言必须 0

# 8. 产物质量自检（渲染断言：孤字/nowrap溢出/居中/越界/双份渲染/对齐；出 inspect-report.json）
node inspect.mjs <port> <产物根>
```

自检：`Page.captureScreenshot` 按 `.stage` 的 getBoundingClientRect **clip** 截产物图和墨刀原图对比（注意：截图/导航必须另开 tab，不能占墨刀 tab——connect 的 urlRe 匹配不到会 fallback 连错页）。完整自检清单见 spec.md 末尾。

## 产物结构

```
<out>/
├── _index.html                 # 总导航（make-index 生成）
├── assets/                     # 全部切图（多板共享，重名加序号）
├── boards/<cid>.json           # 每板提取中间产物（重生成/调试用）
├── state.json                  # 批量断点
└── <目录链镜像侧边栏>/
    ├── 单板页面.html            # 页面只挂 1 块画布
    └── 多板页面/
        ├── English.html        # 一页挂多块画布（如多语言板）→ 同级文件夹下多个 html
        └── 中文.html
```

## 生成规则（不可省）

1. z-index 一律 = 提取序 idx（墨刀原始 zi 只在同父兄弟内有效，跨层会穿）
2. svg fill 注入分两类（外拷丢查看器 CSS 会黑块/变色）：普通 svg-icon 注入 `fill="currentColor"`；**path 图标（`svg-icon-path-icon` 类）除外**——按规则 12 字典写死色或默认黑，注 currentColor 反而错
3. **查看器交互标记三件套整删**（漏一件都出事）：①InteractionMarker 容器（cls 匹配）②橙色热区块及其 `wLr` 透明壳（cls 含 wLr——壳无视觉内容但 48×46 级盖住按钮吃掉真实点击；2026-09-16 快照 2580 壳，子树验证零内容后整树删）③✦ 角标 svg 本体（svg 源码 class 含 `icon/link/mark`，12.6~30px 多形态；SVG 元素 cls 提取值是坏值 `[object SVGAnimatedString]` 不可依赖，按 svg 内容判）。症状：产物页面出现淡蓝 ✦ 小闪电角标 = 漏③；按钮绑了 onclick 仍点不动 = 漏②
4. 懒加载预滚：提取前 scrollIntoView + 轮询 `is-default-image` 清零再 PICK
5. 缩放退化判定看**布局真值 offsetWidth**：`offsetWidth < 80 && rect宽 < 80` 才弃板。只 rect 缩小、offsetWidth 正常 = 画布挂在 0 宽容器（如 group-list 分组缩略形态）被 transform 等比压扁渲染——布局层未动，折行/textH/坐标在布局系全正确，rect×sx 换算数学有效（2026-09-16 送礼效果 4 页 12 板实锤：rect 44×96 / offsetWidth 375×812，换算产物入父框率 97-100%）
6. 墨刀 DOM 有「双份渲染」（同内容节点渲染两遍）——处理口径见 10②（同文本同位同尺寸去重）
7. **文字换行策略（用户拍板：有空间尽量不要换行，但不是所有文本都不换行——看左右空间）**：产物字体 fallback 与墨刀渲染字体宽度有差异，同宽框里文字变宽会把单行文本折出孤字并压到下方节点。判定优先级（实测校准：hug 框 ratio≈1.0、长文案 1.46，阈值 1.08 分得很开）：①墨刀显式 white-space 只有 nowrap/pre 族才还原——`break-spaces` 是查看器默认文本样式，不代表设计意图 ②含显式换行 `\n`（提取时 `<br>` 转的）→ `pre-line` ③**估宽主判据**：估单行宽（CJK≈fs、其他≈0.55fs）≤ 框宽×1.08 = 放得下/贴框 hug（墨刀文本框自动贴合内容宽）→ `nowrap` ④估算超框但墨刀实测单行（st.textH ≤1.5 行高）= 溢出框渲染的单行 → 也 `nowrap`。textH 只做本向兜底：临界折行时它被 fallback 字体污染（实测临界文本 ratio 0.99 却测出 2 行），不能反着用 ⑤**按钮文案单行还原（2026-09-17 用户实锤「按钮文案换行」）**：est 超框且 textH>1.5lh（墨刀里就两行）但**最紧包含文本框中心的实心底板能容纳单行**（est ≤ 底板宽×1.05）→ nowrap——文本框被画窄是稿子失误（同按钮其他状态板就是一行宽），设计意图一行；单行文字要垂直居中回原框中线（top += (h-lh)/2，两行变一行后排版顶框顶会偏上）；底板放不下的（真窄按钮）保持墨刀折行。**拉宽规则（规则 17）的行数基准须同步强制 1**——mkLines 按 textH/lh 算出 2 行会让 want 减半、拉宽失效
8. **字体链兜底**：墨刀常只写 `NotoSans` 一个字体名，本机没装就裸 fallback 到浏览器默认（中文宽度差异是折行主因之一）→ gen-html 对无通用字族的 ff 追加 `,"Microsoft YaHei","PingFang SC",sans-serif`
9. **省略号兜底**（用户口径：单行 UI 位放不下按 UI 惯例 …）：单行框（h ≤1.8×行高）内容 >1.3× 框宽 → `nowrap+hidden+ellipsis`；被画布 clamp 收窄的 nowrap 文字同样补省略号。样本实测微溢出全 ≤15px（hug 框字体余量），本规则是全量兜底
10. **B 类规避（用户拍板：稿子问题在产物侧规避）**：①右/下越界节点 clamp 回画布（左/上负坐标保持，stage 裁剪视觉一致）②同文本+同位+同尺寸双份渲染去重（留视觉在上的）③同 y 带同高元素组 top 归一到中位（只动同高元素，错落设计不动；实测一组 ×12 元素归一）④空页 _index 占位 ⑤**同位双层占位文字叠印不自动删**（同位同色两层占位文案，无法判断哪层是真文案——产物忠实还原，源头改稿二选一）。稿子原状记录在产物根 `_墨刀稿问题报告.md`
11. **`.stage` 必须 `flex:none`**：body 是 flex 居中布局，画板宽于视口（如 web 端横板数千 px 宽）时 flex 默认收缩会把 stage 压窄、右半被 overflow:hidden 裁掉——实测曾把数千 px 宽板压成一半
12. **svg 颜色两套机制分流（2026-09-17 图标颜色不一致二轮实锤，推翻上一轮「一律 currentColor」）**：墨刀查看器对两类图标组件上色机制完全不同——
    - **`svg-icon-path-icon`（path 图标，全站 9347 个，带 `.fill` 修饰）**：styled-components 按 solidColor prop 在**运行时 CSS 写死填充色**（`.hash.fill:not([fill]){fill:rgb(...)}`），色值不随容器 color、提取 json 里没有该字段（st.clr 是容器色不是图标色）。但色值参与 hash 类指纹（同色=同 hash，全站仅 46 个）→ 固化字典 `references/icon-colors.json`，gen-html 按 svg class 里的 hash 查字典还原：子元素写死 fill|stroke（**含源码自带的 currentColor**，VIP阿语板 kBNHRO 实锤——查看器 `[fill]/[stroke]` 规则盖一切有 attr 的元素）一律替换成字典色，none/transparent 形状语义保留；**stroke 型元素补 `fill="none"`**（查看器 `g [stroke]{fill:none}` 的等价——漏补会让 chevron 开放路径隐式闭合填成实心块）；svg 标签无 fill 注入字典色
    - **`svg-icon-path-icon` 无 `.fill` 修饰（294 个）**：查看器无任何 fill 规则 → svg 默认黑、path 自身 attr 生效（源码自带 currentColor 是合法形态，解析容器色），产物不注入任何 fill
    - **`.svg-icon` 类（占位图标等，非 pure）**：查看器 CSS `fill:currentColor` 随容器色 → 写死色替换 currentColor（上一轮修复，对这类仍正确）；`pure-svg-icon` 真彩色图标保留原色
    - **分流判定必须用完整类名** `\bsvg-icon-path-icon\b`——旧 `/svg-icon/` 子串会误命中 path-icon（上轮修复误伤 23/36 图标的根源）。字典来源：查看器翻页采集（侧边栏条目带序号前缀「2 中文」须 strip；图标组件懒挂载，翻页后要滚动画布触发；贪心集合覆盖选页）。**教训：色值活在运行时 CSS 里，DevTools CSS domain 对 file:// 页 0 样式表、document.styleSheets 部分被 SecurityError 挡——定性必须开浏览器量 computed + 穷举所有 sheet 的规则原文**
    - **新格式（pcanvas）字典改为提取端现场采集（2026-10-20）**：path-icon 色值规则是 hash 定向硬编码（`.kKhnky.fill g [fill]{fill:rgb(234,88,12)}` 橙、`.dIuGtu…{fill:rgb(16,16,16)}` 深——同一 map-marker 图标在不同 hash 下色不同），静态字典对新包全 miss。PICK 里首次扫全部 stylesheet：selector 含 `svg-icon-path-icon|.fill` 且 fill/stroke 值非 currentcolor/none/transparent → `map[hash]=色`（缓存 `window.__mthIconMap`）；svg 按 `StyledSVGIconPathComponent-sc-… <hash>` 查表，查不到落回继承色 `cs.color`。继承色只对「hash 规则声明 currentcolor」的图标正确——**千万别用继承色兜底硬编码色图标**（实测 收 图钉 87 灰 vs 真 234 橙）
13. **svg 无 width/height 属性必须补 `width:100%;height:100%;display:block`**：wLine 分割线/线性 svg-icon 靠查看器 CSS 定尺寸，产物里裸 svg 按默认 **300×150** 渲染——375 宽的线被 svg 自身裁成 300（用户验收「线右侧断一截」）。同时 svg 注入只加 `fill="currentColor"` attr，**不要再插 style 属性**——svg 原 outerHTML 自带 style（如 filter）会撞成双 style，后者被浏览器丢弃
14. **img 圆角两段式继承（cover 载体优先 + 贴合兜底）**：墨刀图片 = wImage→Wrapper→image-container 多层圆角容器嵌套 img，平铺提取只拿 img 叶子（自身 br 空）→ 产物方图。**①cover 载体**：查看器 img 元素是 object-fit:cover 拉伸后的【溢出尺寸】（img 85×64 溢出 64×64 br=100px 容器裁圆——第二轮验收实锤，名人堂 83 图全直角），父链第一个 br 容器且容器≤img（cover 语义）→ br 继承 + **产物框换成容器框**（img 溢出框套 br 会变胶囊形，不是墨刀里的正圆）；**②贴合兜底**：img≈容器（±2px，或 h≥24 高差≤8px——胶囊卡「图 36×42.7 在 36×48」常态；h<24 小图标严格防误继承）。img 有 br 必配 overflow:hidden（br 不裁子内容）；bgi 只取 br 不换框不加 overflow（background 天然被裁）。另注意：父链全无 br 的 img 是 PNG 圆素材族（alpha 自带圆形），不需要也不该给 CSS br。效果：img 带 br 959→3963（+3004）
15. bgi：blob: 丢弃；**data:（墨刀内嵌 svg）原样内联保留**（CSS 原生支持 data URI，里面的 currentColor 替换成节点 color 防黑块）
16. **交互热区层已下线（2026-09-16 用户拍板「不要再有热区，影响后续导入和使用」）**：regen 不再携带 --hotzones（hzArgs 恒空），产物 html 零热区元素/注释/CSS（三层 grep 断言 0）。下线缘由：跳转语义大面积不可用（tab 栏跳自己 URL 不变、623/2590 目标未收录、三语板视觉相同跳了看不出），透明热区盖画面还拦截后续导入工具的点击/解析。hotzones.json 数据保留在产物根仅作档案（2590 热区/跳转关系可查）；gen-html 的 --hotzones 能力保留但无流程携带。产物保留：入场动画 + 右下浮动返回钮（history.back）
17. **纯文本框宽自适应（2026-09-16 用户口径「页面宽度够就拉长文字区域宽度，别折行」）**：产物字体 fallback 比墨刀宽 → 同框折出更多行。对无 bg/bgi/border/shadow/overflow 的纯文本框按估宽拉宽：单行(nowrap)拉到估宽×1.05、多行拉到 估宽/墨刀行数(textH/lh)×1.05；右缘封顶 boardW−x；text-align center/right 按锚点回调 left。**有背景/边框的容器框保持原宽**（拉宽会撑破视觉容器）
18. **语义交互层（2026-09-16 用户拍板：按元素语义直绑交互；2026-09-17 增 R5 热区档案映射）**：regen 后跑 `scripts/add-interactions.mjs <产物根>` 给元素 div 本体绑 onclick + cursor:pointer（不改 DOM 结构、不新增覆盖层，不伤后续导入）。五规则：
    - ①tab 栏按 svg path 指纹：骰子 `M26.080 23.232`→Ludo对战首页 / 多人 `M2.667 29.333`→群组大厅 / 气泡 `M416 192`→聊天 / 人像 `M12 2C6.48` 且仅边列→个人中心；指南针 `M12 10.9`=发现页无目标不绑。**指纹优先于 active 高亮色**（语言板间 active 画错常见）；当前页==目标页不绑（防「点击不动」）
    - ②无 tab 栏页面左上 (x<12%W, 40<y<13%H) 18~30px svg→history.back（排除 ✦ 角标 svg，它有 18~30px 形态）
    - ③弹窗取消词典（Cancel/取消/Close/关闭/Dismiss/OK/Okay + 阿语词）→history.back
    - ④文本===当前页直接子级页面名的中文段或英文段→跳子页同语言板（宁缺毋滥：同段多页命中不绑；Confirm/Delete 类目标歧义不绑）
    - ⑤热区档案映射（R5，补语义规则覆盖不到的功能按钮——Quests/商城入口/任务链等）：读产物根 hotzones.json，热区矩形几何命中板内**产物真实存在**的节点（json 里被 gen-html 删掉的 wLr 壳/角标无 div，命中前须过 htmlIdxSet 过滤，否则注入静默落空）→ 绑跳转。目标解析 toCanvas 板优先/toPage 页兜底，**语言对齐优先于原 cid 板**（墨刀数据记录的目标是当初定义交互的语言板，复制到其他语言板时不换——中文板点商城会跳 English 板）；跳过 trig≠tap/url 外链/目标去重≠1/跳自己/已被语义绑定覆盖的热区。**热区内全部合格候选同绑**（择优取 z 最高会系统性选中角标/红点——角标永远浮在按钮右上最上层；触发区域=整个热区语义，底板/图标/文字/角标都绑、点哪都跳）。**t=2 无目标 tap 热区 = 墨刀「返回上一页」交互**（2026-09-17 用户实锤 Cancel Matchmaking 无交互：全站 308 条 t=2 全部无目标、位置不限于左上箭头——底部取消/右侧关闭位 R2 救不到）→ 命中节点绑 history.back()（kind=goback）；**热区跨板复用（t=2 与 t=1 都复用，2026-09-17 子代理全站排查实锤）**：同页兄弟板的热区（同位 x,y,w 取整去重）直接对本板几何命中——t=2 返回与语言无关、复制板布局保位；t=1 跳页热区常只画在 EN 板（「开始匹配」热区只在 EN 板定义 → 中文板 10+ 块主 CTA 裸奔），t=1 借用目标走 zoneHref 接收板语言对齐（能力本就具备），错位落空无害（宁缺毋滥不变）。**命中过滤三个放行修复（2026-09-17 子代理实锤）**：a) 窄文本条放行——`‹` 返回键 json w=6.7 被 w<12 全排，有文本且 h≥16、w≥4 的窄条放行；b) 大热区蒙层通道——弹窗整体关闭热区（≥120×120，如 278×352）只压到大背景层被「面积≤热区×3」排除，热区盖住九成的大层=弹窗蒙层放行（点击关闭=返回语义）；c) 重叠双向——`max(重叠/节点, 重叠/热区) ≥0.5`，原单向判定把「热区完全在按钮内」的反向包含算未命中（表格行 343×46.5 只 49.4% 落在 175×45 热区内被卡）。**±84 坐标校准**：母版系板（商城Shop 全系/搜索群组）hotzones y 与板内真值恒差 84px（iPhoneX 状态栏帧偏移，x 逐像素一致）——原位零命中才试 y±84 平移重试（防误绑），命中同样过全部过滤
    - ⑥同页跨板镜像（2026-09-17 用户实锤「中文板 Quests 整块点不动」的根因：功能入口热区只在 EN 板定义，复制板 zones 里只有 tab 热区被 R1 覆盖 → 中文/阿语板 R5 整板零绑定）：基准板（zone 绑定最多，通常 English）的 zone action 三轮配对抄到同页其他语言板——一轮同指纹（svg/img 切图 URL/bgi）+直接坐标（LTR 板）；二轮同指纹 y 序 zip（RTL 板 x 翻转坐标对不上）；三轮跨形态尺寸序（svg 板↔img 板指纹互斥，如阿语板图标全 img）+**y 平手歧义挂起、RTL 定向后反侧重试**（板名含阿文或偏侧投票全反侧；错绑比不绑糟——贪心在同 y 双功能列必抢错，实测任务图标配到排行榜）。**镜像 href 必须按接收板语言重算**（action 带 tgtPage 引用，直接抄基准板成品 href 会中文板跳 English 板）
    - ⑦业务流词典（R6，2026-09-17 用户拍板「热区只在英文版画、中阿的都没做——不要根据热区，理解 html 的业务」）：墨刀热区是英文板的残缺数据，主 CTA 按页面业务流推演目标直绑。页面上下文 + 三语等值词典 + 按钮形限制（w≤240 h≤44），**不覆盖已有绑定**（R5 热区先绑的保留，R6 只补裸奔）：①四游戏对战首页入口词——Create room/创建房间/إنشاء غرفة→游戏房间无玩家、Quick/Battle/开启对战/معركة→本游戏选人页（Ludo/Uno 取 rank 场景页，Carrom/Jackaroo 无 rank 命名取 1v1）、Main Event/主活动→主赛事首页、Crew War/战队战争/حرب الفرق→战队赛首页；②充值 Top Up 底部主 CTA（y>0.85H，EN「Top Up $9.99」/中「充值 $9.99」/阿 شحن 拆节点绑主词）→确认充值弹窗；③VIP 已购买续订主 CTA（y>0.88H）→支付确认；④打开游戏选择 Create/创建/إنشاء→群组内开启游戏-群主视角；⑤新手引导关闭→back、告知领导层发消息→back、升级弹窗 Claim Rewards→back；⑥结算页（第一名/二三四名/胜利/失败）Play Again/继续匹配→**父页面**（匹配中，结算页在匹配中页子目录，目标即 ../板.html）；⑦R3 词典补「好的」。**web 充值旅程板不绑**（3696 宽六帧横拼流程文档板，非手机屏交互）
    - **语言对齐剥尾序号**：目标页板名「中文 2」对当前板「中文」——同语言板复制时墨刀自动加「 2」后缀，精确等值匹配落空会回退 English 板（中文板点创建房间跳英文房间实锤）→ 对齐先精确等值、再剥尾部数字比，语言仍对不上才回退原 cid 板/第一板
    - **propagate 邻域扩散三层**（action → 板内周边命中层同绑，镜像后也要跑）：①覆盖层扩散（矩形内更高 z 节点——平铺兄弟结构不冒泡）；②底板包含扩散（action 矩形被 idx 更小的底板包含且面积≤9×——镜像 svg 锚点只绑图标本体，点底板边缘环不动）；③图标-文字组队（w≤80 图标正下 22px/正右 12px 的文本同绑——热区只画图标不盖文字，跨语言文字无法字面配对靠组队传导）
    - 幂等重跑先剥旧注入；跑完死链断言必须 0
    - 坑位（症状→处置，详表在 spec「已知边界 case」）：**阿语板 tab 绑定数翻倍**→双套 tab 栏叠放（LTR+RTL 镜像），按指纹各绑两套都对；**tab 错跳个人中心**→「群组我的」EN 板 tab2 孤例画错人像，人像指纹仅认边列；**中文「取消」「OK」不绑**→hug 窄框（取消≈30px/OK≈20px），cancel 宽度下限须 16；**程序自测通过但用户说点不动**→el.click() 绕过命中测试，验收必须 Input.dispatchMouseEvent 真实点击；**zone 计划数远大于注入数**→命中了产物已删节点，须 htmlIdxSet 过滤；**中文板点击跳 English 板**→热区 toCanvas 未做语言对齐（R5 与镜像两个环节都会犯）；**绑到角标/红点上**→择优取 z 最高的系统性错误，热区内全绑；**阿语板 svg 指纹全找不到**→RTL 板图标是 img 切图形态（视觉字段=n.img，bgi/name 都不是），跨形态走三轮尺寸序；**中文板主 CTA（开始匹配等）裸奔**→t=1 热区只在 EN 板定义，t=1 跨板复用没开；**返回键 `‹` 不绑**→窄文本条 w<12 被 R5 全排，有文本窄条放行；**弹窗整块点不动**→大热区蒙层被面积上限排除，≥120×120 蒙层通道放行；**表格行按钮裸奔**→重叠单向判定卡反向包含，双向重叠比；**商城Shop 系返回/充值入口零绑定**→母版系板热区 y 恒差 84px，原位零命中才 y±84 校准重试；**中文板跳 English 板且目标页明明有中文板**→板名带复制序号（「中文 2」），语言对齐剥尾数字匹配；**首页 Quick/Battle 竖排两行按钮**→同一按钮的两文本节点，词典都绑+propagate 组队传导；**产物 grep 按钮文本查不到**→大小写（Create room vs Create Room）与 `&amp;` 实体（Close & Start Playing）两个形态坑，等值匹配先统一

## 坑清单（全部实战踩过，动手前重读）

**数据格式**
- `data.1.js`：`window[<key>][<key>]=[[id,id2,"H4sIA…gzip+base64 快照"],[id,"增量"],…]`（key 名随包变，代码按 `"H4sIA…"` 块定位，不写死）；只解首个 H4sIA 块
- 解压后行格式是 `cid <单字符修饰>\t{…}`（如 `rcV… 5\t`、`rbp… ,\t`）——cid 必须 `line.slice(0,tab).split(/\s+/)[0]`，否则 rbp（页面树）/rc（画板）行全丢，名称全 undefined

**新格式（PB=v1 pcanvas）专属坑（2026-10-20 六页样板实锤）**
- **数据字典**：`read-data.mjs` 探到 `"psol"` 走明文分支（psol 元件名 + pbj.screen_metas 页面名）；源数据无 rc cid，多板页板名兜底 cid 属正常
- **提取根必须含三区**：只提 `.screen-content .widgets` 丢顶栏（screen-header 61px：状态栏+导航栏）和底栏（screen-footer 50px：tab 栏）——验证码登录类页两区恰好 0 高，样板页选不当会漏暴露
- **zoneOf 必须逐元素调用**：walk 里漏调（只透传父 zone）会让 footer 全被标 content，钉底平移静默落空（首版实锤）
- **固定层孪生去重**：footer 与内容层常有同物（tab 栏/底部主按钮各一份，内容层那份可能在长内容中部）——子树文本串相等判孪生，footer 副本整树让位；**孪生判定别比对根尺寸**（footer 根常是 0×0 包装器，尺寸比对恒不中）
- **伪元素物化**：tab 选中下划线 = `::after`（56×2px currentcolor），DOM 走查天然不可见——按 computed style 克隆探针节点量 rect 物化；图标字体字形（content 形如 `\f167`）跳过
- **空 src img**：header 里 `SketchArtboardImage` src="" 占位，不跳过会渲染碎图
- **transform 只透传不改 AABB 的翻转**：rect 坐标已含变换，180°/镜像补 `transform:` 才能还原图标方向（gen-html 白名单正则）；90° 类透传会破坏宽高
- **板高口径**：长图口径 H=max(视口, 内容底)、固定层钉底；视口口径 H=画板原始高，fold 外内容靠 gen-html 越界丢弃
- **绘制序 ≠ DOM 序（平铺模型必踩）**：实测订单条 zi=10 压住地图 zi=13，表面 z 值与 CSS 规则都推不出真实层序——产物按 idx 平铺时晚 DOM 的地图会盖住订单条（离线普查 32/120 页命中此类嫌疑）。修法 = 采样法：PICK 给节点打 `data-mth` 标 → `SAMPLE` 网格布点 `elementsFromPoint` 收集真实堆叠链（采样期临时强制 `[data-mth]` 可命中，防 pointer-events:none 漏采）→ postPass 按约束拓扑重排 idx。以查看器实测为准，零规则猜测；只采首屏可视区，fold 外兜底原序；合法覆盖（弹窗蒙层）不受影响——查看器盖着它也盖着
- **祖先裁剪链（比 z 序更常见的「盖住」根因）**：img 的 `ovf:hidden` 祖先限定其可视区——实测地图 img 盒 647 高，被 StyledImageWrapper/image_view（315 高 + hidden）裁到只剩顶段，查看器因此不与订单条重叠；平铺模型不裁，img 全高盖住订单条（离线普查 32/120 页嫌疑）。修法（img/bgi 专属 `ancestorClipBox`）：沿祖先链取**全部非结构性 `ovf:hidden/clip` 祖先盒的交集**（结构性容器 screen-*/scontainer/widgets/pcanvas 的 overflow 属查看器滚动机制，不计，否则长页被视口截断）→ img 盒与裁剪区求交（完全在外=查看器未绘制，丢弃；部分相交=取交集 + 记 `clipFrom`=原盒偏移/尺寸，gen-html 按 clipFrom 绝对定位渲染原盒，object-fit:cover 居中裁会取错段）。**反例教训：全域 walk 级裁剪会翻车**——墨刀查看器对几乎所有元素 computed 都是 overflow:hidden，按 CSS 语义层层求交会把长页截断在视口处（首页 701→403 节点实锤），必须收敛到 img/bgi 专属
- **pe:none 元素采样**：`pointer-events:none` 的元素（如地图 img）不进 elementsFromPoint——样式表 `[data-mth]{pe:auto!important}` 会被墨刀自己的样式压回（实测 computed 仍 none），必须**逐元素内联** `setProperty('pointer-events','auto','important')`（内联 important 优先级最高必生效），采完恢复原值
- **页面↔画布 1:1**：无需旧版归属三段式；「空页面」判定=点击 ACTIVE 但 WAIT_BOARD 超时（MOUNTING/NOT_ACTIVE/TOO_SMALL）

**侧边栏树**
- DOM 平铺无嵌套，层级 = `.rn-list-item` 自身 `padding-left / 20 - 1`（顶 20px、子 40、孙 60）
- folder vs page 看有无 `.expander`；page 也可带 expander（页面嵌套页面）
- 同 cid 条目 DOM 里出现多次，按 cid 去重

**挂载模型（batch 核心）**
- 点击页面条目 = mousedown/mouseup/click 三连 dispatch，**必须带 clientX/clientY**（墨刀 mousedown 做坐标命中检测，无坐标部分页面切不动）；点击后校验条目 class 含 `active`，未选中重试一次
- **页面画布 cid 一律 rc 纯段**（`/^rc[A-Za-z0-9]+$/`）；路径型（`/a/b`）与拼接段（`…_rc…`/`…_cV…`）= 跨页复用的组件源（列表条目/弹窗类，几百 px 宽也会混进来）→ 一律过滤，minW 只是 rc 板的尺寸兜底
- 切页卸载上一页的板，但**初始默认页的板永不卸载**
- **归属三段式**（diff=0 时依次兜底）：①认领基线板（排除已在产物里出现过的 cid——跨进程续跑时上批遗留板会被错认）②同板复用（弹窗/状态标注页与前页共用画布，当前挂载的非基线 rc 板即本页板）③空页面（选中生效、卸前页板、不挂新板——墨刀里真没画布，记 empty 不算失败；实测存在此类页面）
- **基线归属预备（2026-10-23 实锤补丁，重启/首屏防串页）**：全新启动基线可含 **2 块页面板**（pcanvas 壳内默认页板 + 换装槽预载板），兜底①放任认领会把两块全判给首个无新增页 → 串页（实测：首跑启动页抢走密码登录板、密码登录反被记空页面；中断续跑首保养订单页错领登录板 108 节点 vs 真板 191）。batch.mjs 主循环前先做基线归属预备：①URL `?screen=rbpX&canvasId=rcY` 归位默认页板（reserved：该板只许默认页认领）②flush 点击首个待处理页并 reserved 其板（flush 无新增时把唯一未归属的基线板保留给它）③兜底① 只认领 `reserved.get(cid)===本页cid` 的基线板——reserved 无归属的基线板永不认领（宁缺毋滥，漏了由 audit「多页共用板」与人工兜底）
- **同 cid 板可能挂载两份（不同 scale，如 750 与 905 宽）** → uniqByCid 取**面积最大**那份（真实设计尺寸）
- **同板缓存**：boards/<cid>.json 已在（他页同板/断点续跑）→ 跳过 DOM 提取直接复用；改了提取逻辑要全量重提时先删 boards/
- 板级提取失败记 `state.done[页].failedBoards` 留痕（页面不算整页失败），`--retry-failed` 一键重置失败页重跑

**交互热区（read-hotzones 核心）**
- 交互定义**不在数据快照里**（快照 0 条 ita 行）——在查看器 React fiber：widget DOM div（`.tree-node[data-cid]`）自身 props 无数据，在其**父 fiber（Su 组件）的 `props.widget.hotAttr.interactions`**：`{interactionType:1=跳页, interactionTrigger:'tap', targetRBPageKey:目标页面cid, targetResCanvasKey:目标画布cid, linkUrl:外链}`
- **hotAttr.x/y 是父容器相对坐标（不可直接用）**——与板内绝对坐标可差几十 px 平移；必须用 DOM rect × (offsetWidth/rect.width) 换算（与 extract nodes 同系）
- InteractionMarker（链子小图标）只是查看器标记 UI，且**只在激活板上渲染**——别依赖它枚举热区；直接扫板内全部 widget fiber
- 不在视口的板内部 .tree-node 懒渲染 → 每板 scrollIntoView + 轮询节点数稳定再扫（节点数 0 也算稳定，别把空板当失败）
- 多语言板交互常只画在其中一块上（如仅 English 板有热区）——稿子原状，其余板 0 热区是事实不是漏采（记入问题报告）

**CDP**
- `send()` 返回**整个响应对象** `{id, result, …}`——截图取 `shot.result.data`
- `exceptionDetails` 在响应**顶层**（不在 r.result 里）
- ESM import Windows 绝对路径必须 `file:///C:/…`（否则 ERR_UNSUPPORTED_ESM_URL_SCHEME）
- **反引号模板里发往浏览器的代码，反斜杠必须双写**（`\\s`、`\\n`、`\\(`）——单写会被模板字面量解析吃掉（`\s`→`s`、`'\n'`→单引号内真实换行），浏览器端静默求值成 undefined，整批提取全失败且不报语法错。改 PICK/CLICK/SNAP 里任何正则或转义后跑 `.claude-tmp` 里 check-pick 类脚本核一遍再上批
- **style 属性值里的双引号必须 HTML 转义（`"`→`&quot;`）**：font-family 值常带引号（墨刀原始 ff 如 `Roboto, "Helvetica Neue"`），裸引号会把 style 属性拦腰截断，排在 ff 之后的所有声明（white-space 等）被浏览器当垃圾属性丢弃——**源码 grep 有、渲染全失效**，且无任何报错。曾让换行修复整体失效（orphan 74 例）。验证 CSS 是否生效必须开浏览器量 DOM（inspect.mjs），grep 源码不算数
- **行数/折行判定不能用 Range.getClientRects().length**：阿语连写脚本单行文本也返回多段 rect；用 bbox 高÷max(行高,字号) 代替。紧行高（lh<fs）时 Range 高≈1.35×fs 会被算两行
- **inspect 反复加载同批 file:// html 必须防缓存**：`Network.setCacheDisabled` + URL 版本串双保险，否则 regen 后 navigate 仍读旧 DOM，越界/尺寸全误报（实测数千 px 宽板被旧读数报成一半，排查过一轮）
- **win32 路径进 file URL 必须先 `.replace(/\\/g, '/')` 再 encodeURI**：`path.join` 返回反斜杠，不替换 navigate 会**静默失败**（evalJS 一律 no stage，无任何报错）——症状极像加载时序问题，加重试无效；排查先打 `location.href`
- 巨大 DOM 上别跑全扫探针（`querySelectorAll('*')`、`document.styleSheets` 遍历都会 120s 超时——只扫目标元素类型）；长批任务转 background + state.json 断点
- connect 的 urlRe 匹配不到会 **fallback 到第一个 tab**——batch 连上后会校验 location.href 含 index.html，不在墨刀页直接报错退出（连错页面整批跑废）

**排障**
- 单页挂载异常（无新板/点击不选中）→ `node diagnose.mjs <port> <data-map> <页面cid>`：打印点击选中态、卸载/新挂板、当前挂载全列表（标注页面画布 vs 组件源）

**Chrome 实例纪律**
- 每技能实例独立端口（默认 9225 起；起前自动探测空闲端口，同机多实例自动错开）
- start-chrome 必须 `spawn(..., {detached:true}) + child.unref() + process.exit(0)`：不 exit 则 `&&` 串行的后续命令永远等不到；**直接 exit 不 detached 则 Windows 进程树连带杀掉 chrome**（实例秒死，batch 全 ECONNREFUSED）——两坑都要防
- **严禁杀 start-chrome 的 node 父进程**（旧版不退出时它挂着）——chrome 与它同树，杀它=杀实例；收实例只用 stop-chrome.mjs
- 收 Chrome **只按 infoFile 里的 PID** `taskkill /PID xxx /T /F`——**严禁 `taskkill /F /IM chrome.exe`**（杀用户全部 Chrome）
- 必须 `--allow-file-access-from-files`（file:// 下加载 extra/*.js）+ `--headless=new`，窗口给足（1920×2400）
- 长批双实例并行（batch + read-hotzones）时单 tab 渲染进程可能内存超限崩溃（tab 变 `chrome-error://chromewebdata/`，点击全 NOT_FOUND）——脚本每页校验 href + 连续失败熔断，崩了重启实例增量续跑即可，断点无损
- 平台假设：Windows（chrome.exe 路径三候选 / taskkill）——换 mac/linux 需改 start/stop-chrome 的路径与杀进程命令

**流程纪律**
- 先样板（3~5 页）→ 用户验收 → 再全量；全量断点续跑
- 截图自检导航必须另开 tab，勿覆盖墨刀 SPA（覆盖了要 Page.navigate 回去重等 1~2 分钟数据重载）

## 详细规范

脚本参数、提取字段、产物 schema、边界 case 见 [references/spec.md](references/spec.md)。
