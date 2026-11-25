# 多风格单文件规格（multi-style-spec）· v2 屏集合组架构

> **v2 重写（2026-11-23 用户裁决）**：v1 的"每屏 N 套容器+共用页面树"架构**作废**——用户定案：切风格=左侧页面树、组件、内容**三样整套换**，每个风格的页面组织（页数/命名/分组）可以不同。v1 只换了组件和内容、页面树共用，架构性做错，推倒重做。
> 定位不变：接通「单文件多风格」构建侧。壳与面板侧复用（syncLayers 三层/applyPack/state），**页面组织与树渲染改造**为本 v2 核心。两个触发场景：①构建时多风格（主管线）；②事后回装（换风技能第 4 步）。
> 交付形态红线不变：产物 file:// 双击直开（2026-11-23 实测：外置内容文件 fetch 被拦、iframe 跨域拒——页面 DOM 必须内嵌）。

## 一、DOM 结构（v2：每风格一套屏集合，屏内单容器）

- 每个 section.screen 挂 **`data-style-id="<风格id>"`**——整屏属于唯一风格；**屏内只有一套内容容器**（v1 的屏内 `[data-dom-base]` 双容器机制**废弃**）；
- **页面 id 全局唯一**：非当前风格页 id 必须带风格段（`<风格段>-<语义id>`，如 `polaris-p01-login`），原风格页 id 保持原样（首个风格不前缀）；
- **页数跨风格可不守恒**：每个风格按自己的布局语言组织页面（5 页 vs 4 页合法）；每风格各自对齐供料页面底线+补页登记（换风技能铁律 3 口径随之修正）；
- **页面树按风格独立**：`pageTree` 映射从全局单表改为 **`{风格id: {屏id: 组名}}` 分组表**——切风格时左树只渲染当前风格的段（树内容随风格换）。

## 二、壳改造点（style-chooser / seed runtime / free-editor）

1. **screenList/styleEl 过滤**：全局 `.screen` 遍历改为按当前 `data-style-id` 过滤（`screenList()` 返回当前风格屏集；`screenEl(id)` 不变——页 id 已全局唯一）；
2. **页面树渲染**：树数据源按当前风格段渲染，切风格=树重建（节点集合/分组/顺序都换）；
3. **applyPack 联动（替代 v1 applyDomBase）**：切卡时①三层（L1/L2/L3）照旧；②**屏集合显隐**：当前风格屏 display 正常、其他风格屏 `display:none`；③**curId 重映射**：按页序把当前页映射到新风格同序页并 openScreen（切卡不丢页位）；④左树重建刷新；
4. **style-id 从 REGISTRY 推导**：family.domBaseId 字段沿用（值=风格组 id，语义升格为"风格屏集合 id"），数据结构不变——**受控块 schema 零变更**；
5. **编辑态**：编辑操作天然只落在当前风格屏（过滤后可见屏集）——画布拦截逻辑不动。

## 三、CSS/eid/sprite 隔离（沿用 v1，前缀换 style-id）

- 页面业务 CSS 逐条挂域：`[data-style-id="<风格id>"]` 前缀（v1 的 `[data-dom-base]` 前缀语义平移）——同名类互不覆盖；挂域形态**连写** `.screen[data-style-id="…"]`（data-style-id 挂 .screen 自身；**带空格=后代选择器永不命中、变量全灭**——2026-11-24 uni-ui 实测 K16，convert 的 dom_scope_css/ext-keys 已修连写，手写 CSS 同此口径）；
- 令牌仍由壳单包应用（`html[data-ui-style]` 前缀 L1，切包重建），无共存冲突；
- 图标 sprite symbol id 按包前缀 `icon-<packId>-<语义>`（first-wins 红线不变）；data-eid 按风格段前缀（页 id 已带段，eid 自然唯一，注入器校验查重）；
- **@keyframes 动画名与 @font-face 全局互压**（v1 实测确认）：同名跨风格互压，命名按风格加段（画师纪律）。

## 四、受控块合并与注入器（v2 形态）

- STYLE-REGISTRY：domBases（沿用字段名）/families/packs 追加成员，id 全局唯一查重——**schema 零变更**；
- pageTree 数据：从单映射扩为分组表（兼容读法：旧单映射=原风格段）——注入器合并时追加新风格段；
- **注入器 v2 DOM 手术简化**：不再"源内容包容器+屏内嵌套"——新风格 fragments 直接生成 `section.screen[data-style-id=新风格]` 列表 **append 到 canvas 末尾**（初始 display:none，壳接管）+ pageTree 分组段追加 + 源屏挂 data-style-id + CSS 挂域 + eid/sprite 前缀 + 受控块合并 + 备份/对账/自检；
- 源屏回填 `data-style-id="原风格id"`（首个风格不前缀页 id）。

## 五、互撞检查（沿用 v1 §四）

风格间 fragments 类名全集比对（同名合法、样式定义无域前缀=违规）；eid/sprite id 查重。

## 六、验收口径（v2）

1. 切卡：左树**随风格整套换**（节点集合/分组/页数可为不同集合）+ 屏集合显隐正确 + curId 按页序重映射（切卡不丢页位）；
2. 隔离：激活 A 时抽 B 屏元素 computed 全为 A 域值（B 的硬值零渗漏）；
3. 两域真点各自全绿；图标往返两轮无 first-wins 回归；
4. **页数不对称实测**：两风格页数不同（如 5 vs 4）时切卡/树/真点全正常——v1 做不到的必须是 v2 的通过项；
5. 编辑态只落在当前风格屏；file:// 直开全功能；回装场景备份/还原/重注可重复。

## 七、v1→v2 迁移说明

- v1 的屏内 `[data-dom-base]` 双容器产物：注入器检测到即拒绝并提示按 v2 重放（不再兼容双容器形态——半架构产物是过渡垃圾）；
- v1 已写"页面树不动/页数守恒"验收条目**全部作废**，以本文件 §六为准。

## 八、口令分级与封面供给（v2 补录，2026-11-23 壳现状成文）

**口令分级（browse 可切卡可交互，编辑仍锁；术语档：browse 态=`body.ed-ui-browse`，aka 预览态）**：

- **browse 态免口令**：导出件重开恒为 browse 态——切风格卡（applyPack：卡片点击/回车直通，无口令闸）、配色胶囊落色、外观开关（只动编辑器壳）、页面树切页、data-on 交互点击（browse 态 document 级委托监听）全部免口令可操作——拿到产物的观众即可切卡浏览与交互；
- **换肤入口定位**：`#btnStyle` browse 态绝对定位画布右上（`right:88px` 垂直居中），不随编辑工具组排布（B3 出入裁处补，与换风包侧镜像：style-panel-spec §五.4）；
- **编辑仍锁**：`applyStyleConfig`（配置写改入口，style-chooser 内经 `editorAllowed` 口令闸，未解锁返回 `{ok:false,reason:'locked'}`）与编辑入口（browse 态顶栏"✎ 去编辑"，贴文件名定位，右侧仅"更多▾"）仍锁——点击弹 `editorGate` 口令 dialog，验证后进编辑界面；
- **面板 API 全集**（`window.StylePanel` 导出）：`open` / `applyPack` / `applyPalette` / `setMaterial` / `applyStyleConfig` / `restorePreset` / `restoreOriginal` / `normalizeStyleConfig` / `info`——换肤五 API 免口令，`applyStyleConfig` 与编辑入口走口令；**口令分级实测见 style-panel-spec §六**（B3 出入裁处补指针）；
- 口令本体：默认 `12345678`（build.py `EDIT_PASSWORD`，PBKDF2-SHA-256 哈希注入产物 prototype-config，明文仅 build 侧一处）；交付说明提醒用户修改；改口令走编辑器 UI（"修改编辑口令"仅编辑模式可用，写回源文件后对新开生效）。

**封面供给（用户裁决 2026-11-23：面板卡缩略禁色板条降级）**：

- pack.screenshot 一律真图 data URI（svg/png/jpg；壳侧只认 `data:image/` 前缀，style-chooser screenshot 渲染分支）——色板条仅作封面链失败的降级信号，不是合法交付形态；
- 新风格卡：注入器 `--cover` 传封面文件（库卡=选型存档的 wiki `cover.svg`，自创=手绘程序化 SVG，禁位图）转 data URI 填新 pack.screenshot；
- 原风格卡：注入器 `--src-shot` 传原风格截帧（playwright 对单风格原状备份截设备框内画面）+`--src-pack-id` 指原包（缺省=产物 packs 第一个非 builtin 包）填原 pack.screenshot；
- 验收：面板两张风格卡缩略均为真图——出现色板条=封面链失败要查（回装侧命令序列见换风包 conversion.md 第 8/11 步，口径同源）。

## 九、旧版运行时产物（存量产物无多风格机制，2026-11-24 补录）

**判据**：目标产物 `applyDomBase`/`style-chooser`/风格面板机制 0 命中——注入器入口检查（身份步 0.5）具名拒绝并打印处置三选，禁盲注（数据侧注进去没人消费：uni-ui 实测注入"成功"、真点 90 条 0 过、切卡恒全树不过滤）。**asset-mode 产物**（运行时外置 `assets/js/`）连外置脚本一并扫——外置亦 0 命中才判旧版（2026-11-24 standards 审查实证修复：html 内 0 命中≠运行时缺失）。

**A 重建运行时再注入（经用户裁决授权后走）**：①从旧产物 DOM **机械提取**全部原屏为基座 fragments（只取结构事实，禁当新风格布局参照）；②现行 build.py 重建基座（含面板运行时），基座输入=提取的**原风格 fragments**；③**主客顺序断言**：原风格屏在位且屏数=提取数、运行时消费者命中——**原风格=基座主卡（db-main），新风格=注入卡**，基座误用新风格 fragments=原风格丢失，推倒重做；④重跑注入链 → 真点+回归+渲染对账门全绿。

**C/D**：C=接受现状交付（无点卡切换，交付说明声明缺口）；D=还原 .bak 作废。三选一经用户裁决，禁自选。

**渲染对账门（交付回执链硬项，2026-11-24 定案）**：`scripts/qa/acc_render_diff.mjs --src <静态稿> --built <产物> --db db-<风格id>`——静态稿为基准逐屏计算样式差分（按单类聚合值集；壳包装/svg/旁批 aside 自动豁免）。机检/撞车/U2/回归全是机制回执，唯此门拦得住"选择器未命中/变量死/种子回退"类渲染退化（chips 竖排、hero 蓝底深字实测，人眼之外无一关卡住）；exit 1=差异清单即工单，归因修根因复跑归零；exit 2=环境不可用按降级口径声明。
