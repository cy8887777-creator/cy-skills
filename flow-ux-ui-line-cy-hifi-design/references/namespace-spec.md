# 命名空间规范（namespace-spec）· V05-① · 定稿（四域版）

> **V06 归属：附加A（转化可编辑版）专用**——编辑器直出线已随 V06 退役，本文件仅在阶段7 转化线使用；主流程（阶段1-6）不消费本文件。

> 初稿三域被预研实证推翻（壳实际三层、变量也三层），主代理裁决 A'+C 合并为本四域定稿。
> 预研证据链：`C:\Users\admin\.zcode\workspace\default\ns-v05-baseline\`（归属判定表 var_rules_analysis2.txt / JS 引用点 js_refs_analysis.txt / 迁移脚本 ns_migrate.py / 干跑版 seed_migrated.dry.html / 校验器草稿 verify_namespace.draft.mjs / 基线快照全套，seed 基线 md5 `6d0d05845007fcfa7ca8a6d977cb25ed`）。

## 动机（实证缺陷）

壳与页面共居一个 DOM/CSS 空间，双向污染各有一路：
1. **页面劫持壳**：页面片段在自身或祖先定义 `--editor-nav-width`，壳侧栏 `var(--editor-nav-width)` 读到页面值（实证案例）；
2. **壳污染页面**：壳 `:root` 定义的通用词变量（`--accent`/`--muted`/`--line`/`--soft`…）向下继承进页面片段，页面 CSS 若用同名 var 会意外吃到壳的值。

解法：壳域命名空间化——类名 `ed-` 前缀、CSS 变量 `--ed-` 前缀，撞名概率归零。

## 四域分界（改造的边界判据）

| 域 | 内容 | 处置 |
|---|---|---|
| **①壳 UI 独占域** | seed 独占壳类：`sp-*`/`ov-*`/`np-*`/`ins-*`/`cl-*`/`dbg-*`/`pdlg*`/`mode-tabs`/`drop-menu`/`mm-*`/`ui-swatch`/`canvas-tools`/`save-split`/`more-wrap`/`zbox`/`pseg`/`toast`/`lockhint`/`ruler-*`/`gate-actions`/`tab` 系 + body 状态类 `editing`/`preview`/`ui-edit`/`ui-browse`/`ov-on`/`annotate-mode`/`note-panel-on`/`editor-locked`/`editor-unconfigured`/`editor-dark`/`inspect-mode`/`ruler-on`/`anchors-off`/`dropmark`/`ghost`/`dbg-*` + `is-selected`/`is-hover`/`is-drophost`/`drop-line` | **改名**：类名加 `ed-` 前缀；类内 var(--页面令牌) 54 条规则改 var(--ed-*)（按归属判定表） |
| **②页面域** | `:root` 18 个页面令牌声明（--bg…--shadow）+ `body.dark` + 组件库类（`.app`/`.card`/`.b`/`.ipt`/`.tabbar`/`.hero`/`.form`/`.li` 系全部，约 150 个——fragments/build/design-tokens/chooser/free-editor 五方契约） | **一个字符不动** |
| **③皮肤引擎域** | `STYLE_OWNED_VARS` 数组、`--style-*` 全系、皮肤 `values` 配置键（含字符串 `"--accent"`） | **一个字符不动**（零 diff 断言） |
| **④受控块契约域** | 变量 `--editor-nav-width`/`--editor-bar-height`/`--editor-panel-width`（free-editor.css 声明+定位、free-editor.js setProperty）**执行改名** `--ed-nav-width`/`--ed-bar-height`/`--ed-panel-width`（panel-width 为主代理验收期补裁：与 nav/bar 同构型劫持风险，三兄弟不留半拉子）——授权同步改 free-editor.css 与 free-editor.js + upgrade_html.py patch 同步；受控块消费的壳类 `.topbar`/`.tools`/`.tabs`/`.tb`/`.mini`/`.fld`/`.g2`/`.acts`/`.hint`/`.inspector`/`.dbg`/`.palette`/`.canvas` 与读写状态类 `shownotes`/`has-inspector`/`is-hidden`/`annotation-hover`/`annotating`/`has-annotation-card` **豁免不改**（记遗留项） | 变量改名；类名豁免 |

预览协议域（`device`/`mobile`/`tablet`/`desktop`/`viewport`/`screen`/`free-canvas`/`free` 系/`page` 系/全部 `data-*`/受控块注释标记/`<!--PROTOTYPE_PAGES-->`）并入豁免白名单，不改。

## 关键机制裁决

1. **映射层（seed:45-57）保留结构、仅改指向**：容器选择器原样，声明右侧 `--ui-*`→`--ed-*`（`--accent:var(--ed-accent)`…）。这层是防串色机制——删掉它，受控块耦合豁免类的 18 条规则（如 `.fld input:focus{border-color:var(--accent)}`）会吃到皮肤注入的页面值，换肤一次壳跟着变（恰是验收第 4 条要防的）；
2. **`--accent` 双身份落地**：壳侧 `--ui-accent`→`--ed-accent`（含 editor-dark 组与 applyTheme JS 同步）；`:root` 的 `--accent` 声明**保留**（页面身份，design tokens 注入链兜底，页面组件 60+ 处 `var(--accent)` 靠它+皮肤注入供值）——两域各一份，值同是默认巧合；
   - 裁定补充（2026-11-05）：`--ok`/`--warn`/`--danger`/`--shadow` 四令牌壳侧 9 处**保持页面令牌引用**（判定表中标记为壳改的 54 条规则里，这 4 令牌不随 PAGE_TOK 10 令牌改写）——劫持路径物理不存在：页面片段在 `#canvas` 内是壳后代，CSS 变量只向下继承，页面子树定义这些令牌影响不了壳祖先树里的 `.np-del` 等元素；反向污染也不成立（`:root` 声明是 design tokens 统一供值链）；且皮肤 `STYLE_OWNED_VARS` 不含这 4 个，无换肤串色路径；
3. **`--ui-*` 全系→`--ed-*`**（seed:31-40 + editor-dark 组 59-68 + JS applyTheme 同步）；
4. **JS 全链同步**（最大漏改风险）：querySelector(All)/classList/closest/innerHTML 模板串/className 赋值里的①域类名全部同步（引用点清单=js_refs_analysis.txt）；
5. **同步面（实测口径）**：test_editor.cjs 12 处（`.tab`/`.tab-dots`/`.act-debug`/`.editing`/`.is-selected` 系）；audit.mjs 2（`.tab`/`.editor-locked`→ed-）；verify-interactions.mjs 2；**screenshot.mjs 1**（执行期补获）；upgrade_html.py（P08/P24 done 锚 + apply_current P24 补施对）；build.py/verify-editor.mjs 实测零壳类引用不动；①域清单补录 `act-debug`（初稿漏列，任务书隐含）；
6. **文档锚点**：references 内引用旧类名的改新名并抽查行号锚（行号会漂移）。

## 构建迁移校验（verify_namespace.mjs）

对 editor-seed.html 静态扫描：
1. CSS 类选择器：必须 `ed-` 开头**或在豁免白名单**（组件库类清单从 starter-pages.html+build.py+design-tokens 契约提取 / ④域豁免类 / 协议类）；
2. CSS 自定义属性：`:root` 与壳选择器上声明的必须 `--ed-` 开头（②域页面令牌 18 个/`--style-*`/`--device` 等豁免进白名单）；
3. `STYLE_OWNED_VARS` 与 `--style-*` 系零改动断言（防误伤皮肤引擎）；
4. exit≠0 即 FAIL，报每条违规（行号+词）。

## 守门与验收

1. verify_namespace.mjs 对改造后 seed PASS（exit 0）；
2. `python scripts/build.py` 构建走通 + `node tests/test_editor.cjs` 断言全绿（实测 16 条，README 已同步）；
3. **皮肤域零 diff**（对基线快照断言）；
4. **老产物升级实测**：对 K2 原件跑一次 upgrade（migrate-k2 或按 upgrade_html.py 机制），验证升级后产物内 nav 变量新旧名一致；
5. 真实浏览器实测：解锁编辑→侧栏拖宽（原被劫持变量回归位）→总览/演示/编辑三态→换肤注入/清除一次（页面吃皮肤值、壳吃 `--ed-*` 值，两域不串）→截图留证。

## 遗留项（本次不做，如实登记）

- 受控块资产类名空间化（free-editor.js/css 消费的 .tb/.fld 等类名全量 ed- 化）——需连带改受控块资产内全部 querySelector/模板串，量大且收益低于变量改名，记 V06 候选（双轴审查补充：free-editor-ui/free-box/free-resize/free-nw 等壳类同属此批；verify_namespace.mjs 射程=seed <style> 块，free-editor.css 由 upgrade 注入不进扫描——扩射程或显式白名单随本项一并做）；
- `--annotation-card-width`（free-editor.js setProperty + free-editor.css 消费）：壳侧定位变量未 --ed- 化；劫持路径物理不成立（消费点为壳祖先树），命名纪律残留，随受控块类名空间化一并处理；
- `ed-editor-dark` 死状态组（seed CSS 组无 toggle 方，v6.2 删 applyDark 遗留）：V06 清理候选；
- chooser fenceText 启动时两次全文档 outerHTML 拷贝（16MB 级产物有感知）：性能观察项，可缓存首次结果，随下次触达 chooser 时顺手做。
- chooser wizard 既有交互怪癖（验收期发现，非①回归——改前基线对照复现同样行为）：风格面板第一步点预设卡（如「原始工业橙」）后直接点「应用」不生效；官方还原路径「恢复原方案」按钮正常。记 backlog 待查 chooser 交互，不阻塞本改造。
