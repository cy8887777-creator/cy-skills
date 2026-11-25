# 组件包产包与读包规范（component-pack-spec）

> **V06 归属：附加A（转化可编辑版）专用**——编辑器直出线已随 V06 退役，本文件仅在阶段7 转化线使用；主流程（阶段1-6）不消费本文件。

U2 产包与编辑器组件面板读包的双方契约。schema 本体见 controlled-blocks.md §3（COMPONENT-PACK）；本文件管**怎么产、怎么读、怎么插入**。

## 一、产包时机与顺序（U2 站）

1. **先产包，后产页**——U2 顺序：①展开选中风格令牌（skeletonTokens 选定即锁只扩不改）→ ②按该风格产 10-15 个高频组件写 COMPONENT-PACK → ③再生成页面片段（样式只用①的令牌，结构优先复用②的组件）。页面与组件同一风格源，插入组件不会和页面两套皮；
2. **组件从风格长出来**：组件的圆角/描边/阴影/密度由该风格决定（风格 × 组件形态），不做"通用组件配风格色"——那正是要改掉的旧态；
3. **数量**：10-15 个；类别覆盖高频六类——卡片 / 按钮组 / 表单块 / 列表 / 统计块 / 图文块；页面没有但通用高频的（如按钮组/输入组）可少量补充；
4. **同族变体**：同族的多个风格包（用户选中的同骨架风格 + AI 顺手送的变体）各自配 COMPONENT-PACK 时，组件**结构同源**、`tokenRefs` 指向各自包令牌——同骨架换皮在组件层的体现；
5. `packFor` 必须引用 STYLE-PACK 内存在的 packId（verify_blocks 引用闭合校验）。

## 二、组件条目纪律（html 字段）

1. **类名用组件库类**（.b/.ipt/.card/.li 等 seed 组件库系——与页面片段同源）：插入页面后自动吃皮肤三层（L1 tokens / L2 l2Overrides / L3 iconSet），**插到哪都自动带当前风格**——禁自带内联样式硬值；
2. **data-eid 齐备**：可编辑元素全部挂 data-eid（editor-runtime 页面片段契约），禁 script/iframe/行内事件；
3. **令牌归因**：tokenRefs 列出组件依赖的全部令牌，**口径=所属包 tokens 对象的键名（逐字，键名本身照正本表 assets/token-keys.json）**（lint_tokens 白名单依据）；组件内引用的 `--sp-*` 变量必须真实存在（正本表的变量或包里扩展参数生成的 `--sp-<键名>`）；组件内出现未归因硬值=lint FAIL；
4. **中性内容**：占位文案禁业务词禁 lorem（与比稿卡内容两防同理——插入后用户改前不能带假业务信息）；图片位用占位结构；
5. **消毒边界（面板插入时执行）**：剥 script/iframe/frame/object/embed/行内 on*/javascript: 引用（含 href/src/xlink:href/action/formaction 五属性）与 data:text/html href|src；**style 属性不剥**（组件合法布局需要，如 grid 列数）——受控块为构建链可信源+verify_blocks 把关；CSS 注入风险（含 STYLE-PACK l2Overrides 的 props/selector 理论可闭合规则注入全局选择器）登记为同一已知边界；
6. **布局类内联过渡条款**：组件内布局用内联 style（如 grid 列数）暂沿内置 PAL 先例接受；正式产包链路（U2 生成）建成后排期改令牌化（editor-runtime 扩域口径）。

## 三、面板读包接口（seed 组件面板侧）

1. 面板运行时 parse 产物 HTML 内 COMPONENT-PACK 围栏——**三形态全支持**（HTML 注释/script data-block/JS 注释，契约见 controlled-blocks.md 通则；受控块注入产物后与面板同文件）；
2. 渲染：按组件 name 分组列表（不渲染 html 预览——面板轻量；预览靠插入后实见）；
3. **插入行为**：选中插入点（当前页/当前选中块后）→ 注入 html → 新元素继承页面皮肤（因组件库类+令牌归因，无额外处理）→ 挂 data-eid 可编辑；
4. **降级契约**：无包/解析失败 → 只渲染内置通用组件（面板不得空转，不再标注数据源字样）。
   **两个页签（2026-11-07 用户定案，替代 11-06 的「两区上下共存」）**：有包=胶囊切换「通用组件 | 本项目自定义组件」，通用组件在前、默认选中，切到哪边只显示哪边；无包=不显示切换，只有通用组件。通用组件=全量库（CL.groups 分组，随扩全增长，以 seed CL.groups 实数为准；CSS 组件类令牌化随风格走）；本项目自定义组件=组件包（项目高频精选 10-15 个与业务特有组件），图标统一用拼图；
5. 组件面板 UI 属壳 UI 域（命名空间遵守 namespace-spec 四域——ed- 前缀或豁免白名单）。

## 四、验收口径

- verify_blocks.py 对 COMPONENT-PACK：围栏恰 1 / JSON 可解析 / packFor 引用闭合 / components ≥10（不足=如实标注非 FAIL）；
- 抽 1 组件实测插入：插入后视觉与页面同风格（皮肤生效）、可选中可编辑（data-eid）、tokenRefs⊆包 tokens 键（lint 白名单口径自查——lint_tokens 区域级检查待其扩展后接入）；
