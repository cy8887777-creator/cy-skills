# 写码规则（移植自 screenshot-to-code 保真系统提示词）

**写 index.html 之前必须读完本文件。** 本文件是写码阶段的完整规则集，
与布局说明书（layout_brief.txt）共同决定产出质量。

## 0. 设计系统（选填；解析逻辑已代码化，模型只消费结论）

设计系统是**选填**输入（第 1 步第 5 项四问打包确认，答案落盘
request.json 的 design_system 字段）。

**解析链（2026-09-29 起由 font_probe.py 的 resolve_styles 执行，
不再由模型在提示词层自行判断）**：

```
设计系统定义了该属性？ ──有──→ 用设计系统（写码照抄）
        │无
        ▼
有专项实测器？（字体→font_probe 渲染比对；颜色→palette；圆角→拟合）
        │有
        ▼
   用实测值 ──两者都没有──→ 模型目测 + [UNSOURCED] 标记进交付报告
```

- 设计系统与截图多为"族与实例"关系（阶梯 vs 具体档）：族取设计
  系统，档取最近实测——这不是冲突；
- 真冲突（值域不相交）：设计系统胜，差异记入 styles.json 的
  `conflicts` 并在交付报告以 `[DS-CONFLICT]` 提示；
- 模型的唯一职责：**读 styles.json 照抄**。styles.json 缺失或
  degraded 时走字形特征兜底并标注 [UNSOURCED]；
- 1:1 还原在设计系统缺字体条目时不受影响：font_probe 的封闭集
  渲染比对给出池内最接近的免费字体（原图可能用商业字体，免费近似
  是行业标准做法）。

## 1. 一次成型纪律（最重要）

- 写 `index.html` 之前先重读 layout_brief.txt，从上到下按报告的行顺序
  搭骨架：顶条 → 内容行 → 固定底栏。
- 元素位置、尺寸、间距**直接使用说明书里的数字（±5px 内）**，
  不凭记忆或感觉估算。
- **颜色只从实测取**：layout_brief.txt 的 palette / row-samples /
  sample[] 是脚本对原图的实测取色。写每个区块颜色前先查对应行的
  实测值；拟用色不在实测值及其邻近色域内 → 停止落笔，回原图补取样
  确认。低分辨率读图对"按钮底色/文字颜色"的印象常常是错的
  （浅紫玻璃按钮 vs 饱和渐变按钮在缩略图上难分辨），**实测数据
  优先于读图印象**。
- **容器（按钮/胶囊/卡片）几何只从实测取**：CONTAINERS 段给出
  自动检测的 bbox、拟合 radius、shape 判定与实测色（**全部逻辑 px，
  管线已按 dpr 归一——1:1 即 CSS px，禁止任何换算——radius 无
  例外**）。
  按钮类元素必须按这些数字构建并打 `data-container="cN"`（verify
  断言尺寸 ±max(6px,12%)）。圆角按输出行的 `shape:` 落笔：
  `pill` 才用 border-radius = h/2；`rounded-rect` 用 r_css，
  **禁止自行改判形状、禁止对数值加减修正**（字段事故：把 22 物理
  当 24 CSS 手调，圆角放大 4 倍；把圆角矩形目测成胶囊——实测取色
  优先于目测印象，对圆角同理）。
  缩略图上 r=15 与 r=25 无法区分，而这两者在成品上肉眼可见地不同。
  CONTAINERS 未覆盖的浅色/低对比容器：写码前用脚本实测 bbox/radius。
- **禁止先写草稿再返工**——先粗写全页再修改是布局漂移和浪费的
  第一大根源。一次成型，结构性问题靠说明书在上游消灭。
- 文案**逐字取自截图**，不改写、不翻译、不省略。
- 所有代码直接写入文件，不在对话里输出代码片段。

## 1.5 布局两层规则与产物形态（硬约束）

**产物形态**：纯静态平铺 HTML。body 即画布，按源图逻辑尺寸
（管线入口已按检测 dpr 归一——brief 每个数字 1:1 就是 CSS px）。
**禁止**套任何外壳容器、居中包装、
手机框、预览壳——产物要导入 Figma 等设计工具，外壳会被一起带进去。

**两层布局**（防重叠/错位，之前实测翻过车）：

| 层 | 方法 | 坐标来源 |
|---|---|---|
| 区块级（骨架） | SKELETON/CONTAINERS 实测框钉位置，结构关系用 flex/grid 表达 | 说明书 SKELETON/CONTAINERS 段 |
| 素材 `<img>` | 按实测坐标 absolute 嵌入（或 flex 内按框尺寸占位） | 说明书 assets 段 |
| 区块内部 | 一律 flex/grid 流式布局，元素互相让位 | 语义 + ROW 关系标注 |

**骨架与素材均为实测值**。骨架对齐（同行等高、等间距、贴缘、居中）
由 CSS 布局引擎保证——对齐是结构关系，坐标各自为政误差会独立累积。

三条禁令：
1. **同一视觉区域内，禁止文档流元素与绝对定位元素混居**——
   字体加载高度一浮动，两套定位就会叠到一起；
2. 区块内部禁止逐元素绝对定位——说明书数字是**位置参考与核对
   基准**，不是 CSS 坐标表；
3. **禁止用 margin 硬凑文字/元素定位**（含负 margin 调位）——文字
   块位置取 SKELETON text_block 实测值，用 flex/grid 的
   justify/align/gap 到达，margin 只承担"语义间距"（相邻元素的
   设计间隙），不承担"把元素推到某个坐标"。
4. 文字区块固定行高（line-height 写死），消灭字体加载浮动。

骨架元素按 SKELETON 段标记 `data-skeleton="sN"`：面状类型（container/
button_bar/nav_bar/decoration）断言尺寸 ±max(6px,12%)；text_block
断言中心点 ±max(8px,15%)（字体度量合理改变墨迹框，位置才是对齐所需）。

## 1.6 字体还原三步（每块文字必过，2026-09-28 字段事故后新增）

全站单一字体 + 顺手一个字重是还原失败的常见根因：游戏 UI 的拉丁
标题/数字多为**圆体**（rounded sans），阿语正文字重普遍比 Latin 文
重一档。写每块文字前过三步：

1. **选族**：照抄 styles.json 的 global 族（探测或设计系统给出）；
   degraded 时才按字形特征兜底选族（几何直线型阿语 →
   Almarai/Tajawal；圆润连笔型 → Cairo；仅原图明显圆体才用圆体），
   交付报告标注 [UNSOURCED]；
2. **对字重/字号**：**逐块照抄 styles.json 的合同条目**（2026-10 起
   为全量合同——每个 text_block 一条 family/weight/size_css，
   styles_consistency 断言全覆盖）；无设计系统时代表块来自渲染
   比对、其余块来自墨迹估算，**禁止全站顺手写同一档字重**；
3. **对宽度**：`[WIDTH-RISK]` 文字块写码时就预留宽度或压缩字号。
   **文字渲染宽 > 实测框宽的唯一正规处置是缩字号/换紧凑字重并如实
   报告；禁止负 margin 把文字硬凑回实测中心**——那会制造"断言绿、
   视觉文字插进图标"的穿帮（verify 的 layout_integrity 断言会抓
   负 margin 与文字×素材相交）。

写完后的文字核对**走数据不走图**：styles_consistency（逐块合同）+
skeleton_geometry（位置）+ text_overflow（折行）+ texts_present
（文案）四断言全绿 = 文字正确；diff 目检图的文字区已灰罩，禁止
逐带看文字（2026-10 定稿）。

**背景提升防御（必写，2026-09-27 实测翻过车）**：`html` 没有自己的
背景时，`body` 的背景（含渐变/光斑）会被 CSS 提升到整个浏览器画布
并默认 `repeat` 平铺——页面右侧出现重复渐变条。凡 body 用了
background-image，必须同时写：

```css
html { background: #FFFFFF; }        /* 阻断背景传播，色值随页面底色 */
body { background-repeat: no-repeat; }
```

产物仍是无外壳的 body 画布，此规则只影响浏览器预览，不影响 Figma 导入。

## 2. 素材三条铁律

0. **over_photo 素材禁画遮罩（2026-10-08 重影根因修复）**：素材
   带有 `over_photo_text_erased: true`（或 brief 行的
   `over_photo_text_erased` 标记）时，图内的文字像素已被管线
   inpaint 擦除，但**半透明遮罩仍在图里**——HTML 直接在该 img 上
   定位渲染文字层即可，**禁止**再画任何遮罩 div / 渐变 overlay /
   blur 垫片（再画 = 与图内遮罩叠加变暗 + 视觉穿帮）。文字坐标
   照常按 brief 的 text_block 实测值。
1. **真图胜过重绘**：logo、吉祥物、插画、人物、产品照片等有辨识度的
   素材必须用 `assets_report.json` 里给出的裁剪图/透明图
   （相对路径引用），禁止用 CSS/SVG 临摹、emoji 或近似形状替代。
   **例外——css-native 类反着来**：纯几何 UI（判据收紧：**≤2 笔画
   的规则形状**——加号、箭头、星星、勾选、纯色圆、细线框、简单
   胶囊；brief 的 `[css-native]` 提示是机器参考）**必须** CSS/SVG
   重建，禁止位图裁剪贴上——矩形裁剪的烘焙底色在重构背景上必然
   露缝。
   **CSS/SVG 重建时禁止用字体字符冒充图形**：`+`/`★`/`→`/`●` 等
   字符的字形由字体决定，与原图图形几乎必然不符（字段事故：字体
   加号 vs 原图圆头粗十字）——一律用 inline SVG 画形状，
   形态以原图为准（端头、臂宽、比例）。
   **手画 SVG 只允许用于纯几何**：带形态细节的图标（购物车、齿轮、
   导航图标等）禁止手画临摹——凭空画一个精确形态超出可靠能力
   （2026-10 齿轮两版手画均失真实证）。此类扁平 2D 图标的正规路径
   是**图标库识别**（SKILL.md 第 4 步）：Iconify API 搜索候选 →
   渲染比对 → 高置信才引用，元素打 `data-icon="<集合>:<名称>"`，
   按原图实测色做渐变上色；低置信/离线 → 降级抠图，**禁止引用
   "差不多是这个"的图标**。立体拟物质感图标只走抠图，两条路都不
   适用。
2. **素材是内容，不是结构**：绝不能把整张截图贴进页面当布局；
   裁剪图只按 box_px 放在它的坑位上。
   2.5. **ALPHA GATE 是物理约束不是提示**（2026-09-30）：被 gate 的
   掩码落盘为 `asset_N_alpha.rejected`（不可引用），`assets/` 里
   不存在可用的 `_alpha.png`——页面若引用它，verify 的 img_loaded
   直接 404 FAIL，强制走 RAW/SVG。不需要模型"记得"某条 WARN。
   2.6. **素材处置一律按 `assets_report.json` 的 `verdict` 执行**
   （OK / REVIEW(附原因) / USE_RAW），模型无裁量权：verdict 非 OK
   的素材要么按指令降级、要么修框重跑，不允许目测放行；REVIEW 的
   处置必须落盘到校准记录。
   2.7. **内联 SVG 图标双重纪律**（2026-09-30）：①每个图标库内联
   SVG 必须带 `data-icon="<库>:<名>"` 属性，且该 key 必须已在
   `references/icon_manifest.json` 中 `confirmed:true`（人 4x 复核
   后落盘）——未确认 key = verify icon_contract FAIL，子代理的
   HIGH 裁决不是通行证；②SVG 替代素材坑位时必须带
   `data-asset="asset_N"`，且 viewBox 自带 ~12-22% 内边距——尺寸按
   **getBBox 占比反算补偿**（`图形宽 = viewBox占比 × rect宽`，先把
   rect 放大到墨迹等于坑位框），verify 的 icon_contract 断渲染
   墨迹宽 ≈ 坑位框（±15%），只把 rect 设为坑位尺寸而图形缩小 =
   FAIL（白改：购物车/齿轮渲染为原图 60-70%）。
   2.8. **图标库裁决 = 比对后自动定稿，禁止打断用户**（2026-09-30
   修订，取代"人工终审"版）：子代理回传 **top-3 候选 + 证据对比板**
   （原图 vs 候选 4x 并排）；**高置信命中（形状+风格+细节三吻合）
   由主代理直接定稿**：SVG 内联 + `data-icon` + **自动落盘
   `references/icon_manifest.json`**（confirmed:true + note 记录证据：
   对比板路径/命中集合/置信度）。**低置信/无命中 → 静默降级抠图**，
   同样不打断。**任何情况下禁止就图标引用 AskUser/打断用户**——用户
   终审在交付后的 diff/zoom 材料上（不满意走第 7 步换图标）。
   manifest gate 保留但语义修正：它防的是"未经比对凭空引用"
   （confirmed 条目必须带证据 note 才算数），不是用户审批——比对过
   的模型自动落盘是流程的一部分，不是需要批准的动作。
   预算仍为一轮搜索 + 一轮比对（top-3 一次产出）。
3. **透明度**：人物/logo/图标类素材优先用 `_alpha.png`（已去背），
   **但受第 3 步掩码量化门禁约束**：`fidelity_ratio < 0.9` 或
   mask score `< 0.65` 的透明版不得使用（主体被掩码收缩/啃边，
   小图标失真人眼在校准图上不可辨）——改用原图裁剪或图标库路径。
   某素材在 assets_report.json 里 `alpha: null`（抠图失败）时，
   **禁止把带背景的原图直接贴页面了事**，按优先级处理：
   a. 纯几何 → inline SVG 重建（首选）；
   b. 扁平 2D 图标 → 图标库识别（SKILL.md 第 4 步）→ 命中引用，
      未命中再评估原图底色融合直贴；
   c. 照片/插画类 → `mix-blend-mode`（multiply/screen）让底色消失，
      或评估底色与页面背景融合时才直接贴；
   d. 都不行 → 中性占位块。素材位置一律按说明书坑位（box_px）。
   **降级素材（a/d 两种，页面上没有 `<img src*=asset_N>`）必须用
   `data-asset="asset_N"` 属性标记占位元素**——verify_page.py 靠它
   对降级素材做位置断言；不标记 = 该素材按"页面缺失"报 FAIL。
   c（原图直贴）本身是 `<img>`，无需标记。
4. **圆角矩形素材必须裁切圆角，全站统一处理**：RAW 裁剪是矩形像素
   图，原图里的圆角效果 = 图标像素 + 圆角外烘焙的原背景色。页面背景
   是 CSS 重构的，与原背景必有逐像素色差——裸贴时圆角外四角会以
   "直角杂底"暴露（色差小处侥幸隐形、色差大处穿帮，表现为"有的
   有圆角有的没有"）。规则：凡矩形位图素材其内容为圆角方形（游戏
   图标、卡片图标、按钮图），`<img>` 必须配
   `border-radius:<R>px; overflow:hidden`，R 取 brief ASSETS 段
   `rounded-rect subject radius≈Npx`（逻辑 px，直接用），
   brief 未给出时回原图实测。圆形头像同理用 `border-radius:50%`。
   全页所有矩形素材统一执行——要么都裁，要么（该抠图的）都抠，
   禁止混用裸贴与裁切。
   **圆形头像附加规则（2026-10 新增）**：RAW 裁剪框大于头像本体
   （含边缘杂边/阴影）时，直接 `border-radius:50%` 会把杂边裁进
   圆内、有效头像缩小——必须先把显示框收紧到头像本体 bbox
   （回原图实测圆的直径与圆心）再圆形化；或头像类素材直接走
   抠图（want_alpha:true）。

降级（仅当 assets_report.json 中该素材无 alpha 且 extract 阶段标记失败）：
按 box_px 尺寸手绘 inline SVG（形状/比例/配色贴近原图），
或中性占位块（纯色块/浅渐变）——位置仍按说明书的坑位。
**禁止**因个别素材失败而打乱整体布局。

## 3. 画布契约（竖屏稿）

layout_brief.txt 出现 CANVAS CONTRACT 时：
- 单一固定画布：壳体精确 `W px × H px`（100dvh），页面**永不**高于画布；
- 禁止 min-h-screen / min-height:100vh 之类让内容撑开页面的写法；
- overflow 裁切（`overflow: hidden`）；
- **底栏锚定到 body 画布，不是视口**：固定画布（不滚动）页面一律
  `position: absolute; left:<画布边距>; bottom:0`（或 relative 容器
  的流内钉底），锚点是 body/画布容器。**禁止 `position:fixed`**——
  fixed 的包含块是视口，`dir=rtl` 或宽视口下 body 靠边时底栏会与
  正文撕裂（正文贴右、底栏留在左下）。fixed 仅适用于真滚动长页；
  verify 的 `bottom_bar`/`canvas_alignment` 断言按"与 body 画布
  对齐"判定，viewport-anchored 实现会 FAIL。

## 4. 技术栈规范（第 1 步用户必选；产物恒为单文件）

**无论选哪个栈，产物一律是单个 `index.html`**（浏览器直接打开可运行），
保证 verify_page.py 断言与交付流程不变。

| 栈（第 1 步确认） | 接入口径 |
|---|---|
| HTML + CSS（默认推荐） | 纯 HTML/CSS，不引任何框架与 CDN 样式 |
| HTML + Tailwind | Tailwind Play CDN `https://cdn.tailwindcss.com`；区块级定位等关键几何建议同步写行内 style，防 CDN 失联布局崩塌 |
| React + Tailwind | React 18 UMD + **Babel standalone 必须钉 `@babel/standalone@7.25.6`**（unpkg 该精确版本；禁用 cdn.babeljs.io/babel.min.js——那是 Babel 8，自动 JSX runtime 注入 import 导致浏览器内编译崩溃）+ Tailwind CDN |
| Bootstrap | Bootstrap 5.3.2（jsdelivr，带 integrity） |
| Vue + Tailwind (beta) | Vue 3.3.11 global build（npmmirror）+ Tailwind CDN |
| Ionic + Tailwind (beta) | Ionic CDN + Tailwind；图标用 ionicons（此栈不用 Font Awesome） |
| 其他 | 用户指定；先确认能单文件运行，再开工 |

**任何栈下不变的红线**：
- 1:1 还原优先于栈习惯：位置/尺寸/间距仍按说明书数字（±5px）、
  文案逐字取自截图、素材按校准裁决引用；
- 布局两层规则（§1.5）与画布契约（§3）对任何栈同样生效——
  React/Vue 的组件树外层禁止再套居中外壳/手机框；
- Tailwind 下的区块级绝对定位用 arbitrary values（如
  `top-[195.5px]`）或行内 style 实现，区块内部仍一律 flex/grid 流式；
- 图标：Font Awesome 5.15.3 cdnjs（Ionic 栈除外，用 ionicons）；
- 字体：可用 Google Fonts 或其他公开字体。

## 5. RTL 规则（阿语等右到_left 截图）

- 根元素 `dir="rtl"`；
- 水平镜像布局：行序、图标列、面包屑箭头；
- **只翻有方向含义的图标**（箭头/返回），纯装饰不动；
- **说明书坐标是 LTR 屏幕空间，不镜像数字**：x 最大的元素就是屏幕最右、
  RTL 阅读序第一；直接按数字映射左右，禁止脑内重推镜像坐标。

## 6. 暗色稿取色规则

- 背景是**分层暗色**（如 #1a1d21 / #23272e 叠加），不是纯 #111；
- 对比度看「文字 vs 紧贴它的背景」，不是 vs 页面背景；
- **不要擅自提亮**原设计刻意压低的对比度。

## 7. 修正规则（仅 verify FAIL 时）

- 用精确字符串替换定点修，**禁止整文件重写**；
- 修什么以 verify_report.json 里 FAIL 项为准，不做清单之外的"顺手改"；
- **禁止为凑断言而扭曲实现**（2026-09-28 字段事故）：不许用负 margin
  把超宽文字凑回断言中心点（文字穿进图标、断言全绿）；不许拉伸/
  移动底栏容器去满足 bottom_bar 贴底容差（底栏离开实测位置）。正确
  处置永远是回根源修：字体宽度问题改字体/字号，位置容差问题先核对
  原图实测空隙再判断是断言口径还是实现错；
- 修完重跑同一命令复检，最多 2 轮（SKILL.md 状态机定死）。

## 8. 收尾

一两句话总结：产出的文件清单 + 每个素材用了原图还是降级 +
verify 结果。页面里不留任何代码片段。
