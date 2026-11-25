---
name: image-to-code-skills
description: >
  把 UI 截图高保真还原为单个可运行的 HTML 页面（image-to-code）。
  确定性管线脚本化：box_2d 像素化、行列聚类、布局说明书、素材裁剪、
  双模型本地抠图竞速择优、标注校准检查图、页面结构断言，全部由脚本
  执行；模型只做看图标注、按说明书写码、按检查报告修码。产物为纯
  静态平铺稿（可导入 Figma）。当用户要「截图转代码 / 截图转 HTML /
  还原设计稿 / 高保真复刻页面」时使用。
---

# flow-front-ui-line-cy-img-to-code

把截图还原成高保真 HTML。**1:1 高保真还原是必须目标**——档位只决定
素材与校准的深度，技术栈只决定实现载体，都不降低还原标准。流程是
**状态机**：每一步只允许做该步规定的事，每步的通过/失败由脚本退出码
决定，模型没有裁量权。

## 铁律（先读，全程有效）

1. **工作颗粒度由脚本和本文件定死**：不许跳步、不许加步、不许把 FAIL
   解释成 PASS、不许自行判断"差不多可以了"。
2. **模型只有三处自由度**：看图写 assets.json（第 2 步）、按说明书写
   index.html（第 4 步）、按检查报告（脚本 FAIL 明细 + 独立裁判清单）
   修代码（第 5 步）。其余一切判断以脚本输出与裁判 verdict 为准。
3. **档位由用户定**：模型无权升降档。执行中发现档位的前提不成立
   （如抠图模型缺失），停下报告并给选项，等用户决定。
4. **先问后做**：图片路径、输出目录、档位、技术栈、设计系统，用户没
   确认前不开工，不许猜路径。技术栈与设计系统若在用户任务指令中已
   给明，视为已确认，不必重复追问。
5. **PASS 含金量原则**：模型信任脚本的 PASS 是义务——因此脚本放行的
   一切必须可信；检测器"拿不准"必须给 REVIEW/非 OK，**坏 → OK 的
   成本（终局穿透，无人再看第二眼）永远高于误报 → REVIEW 的成本
   （多看一眼）**。质量判断零落在模型上：目检/detail 图/zoom 图一律
   只是复核辅助，不是守门员；守门员是 verdict 与 verify 断言。凡
   "REVIEW/提示等人处理"的软路径一律无效，唯一有效的处置是：管线
   物理产出（坏 alpha 不落盘）、FAIL 闭环（verify 必红必修）、
   白名单清单（未确认引用必 FAIL）。
6. **每步入口先读该步的 references 文件再动手**（下文各步标明）——
   细则全部在 references/ 里，本文件只保留状态机骨架；跳读细则 =
   违反铁律 1。

## 状态机

### 第 0 步：环境体检 + 多态确认（每次运行必做）

**先读 `references/environment.md`（解释器顺序、模型路径、运行时
依赖形态）。**

```
<python> scripts/doctor.py --full          # --full 必带：真实启动浏览器
<python> scripts/doctor.py --make-vision-test <输出目录>\vision_test.png
```
- 体检：退出码 0（READY）→ 过；退出码 1 → 看报告的
  `model_only_fail` 字段（2026-10-07 第五轮评审：规则在代码里，
  不许模型自己数失败项）：
  - `false`（存在非模型项失败）→ 逐条执行 `fix_commands`（或
    `doctor.py --fix --full`）后**复跑**，连续两次仍不 READY →
    停，原样报告 fix_commands；
  - `true`（失败项全部为抠图模型）→ **不停机**，带"待裁决"进
    第 1 步——档位在第 1 步才确认，缺模型机器必须能活着走到
    "选快速档"：用户选**保真档** → 回头执行 fix_commands 直到
    READY 再进第 2 步；选**快速档** → 复跑
    `<python> scripts/doctor.py --full --tier fast` 确认 READY 后
    进第 2 步。
- **档位分档（2026-10-07）**：模型检查项（isnet/u2net）仅**保真档**
  必需——**快速档**下模型缺失不阻塞（其余项 READY 即可开工），
  第 3 步抠图命令带 `--no-alpha`（素材走 RAW/SVG 路径）。
  **时序注意**：第 0 步体检先于第 1 步确认档位，`doctor.py` 默认按
  **保真口径**检查——此时模型缺失**不得**擅自改用 --tier fast
  （档位必须用户定），按上面 `model_only_fail` 流程带项前进。
- 多态：用 Read 打开测试图，描述三种图形（矩形/圆/三角）、各自颜色、
  数字串 `7 3 4 9`。全部正确 → 过；描述不出 → **技能终止**（换多态
  模型会话；坐标全靠标注，瞎标=全盘错）。

### 第 1 步：需求确认（先问后做）

**先读 `references/labeling-guide.md` §0（需求项与目录保护）。**

五项缺一不可，四项（档位/技术栈/输出目录/设计系统）必须一次打包问出
（设计系统选填但必须显式问，不允许自行跳过）；结果立即落盘
`<输出目录>\request.json`（管线入口校验，缺失拒跑）：

```json
{"image": "source.png", "output_dir": "image2code-work/1",
 "tier": "保真", "stack": "HTML + CSS", "design_system": null}
```
- 覆盖保护：同图重跑默认新开递增目录（-v2/-v3），旧产物是版本历史，
  覆盖须列清单经用户确认；
- 技术栈按表选（详见 labeling-guide §0），产物一律单 index.html；
- **运行时依赖提示（S1）**：选含 CDN 的栈（Tailwind/React/Vue/Ionic）
  时必须告知用户"产物打开需联网；如需离线交付可运行
  `scripts/vendor_local.py --html <产物>\index.html` 递归落盘全部
  外部依赖（框架/CSS/字体/图标）——完成后自动无头浏览器离线复测
  （零外链+本地资源全加载才退出 0）"
  （仅用户要求时执行，默认保持 CDN 轻量形态）；
- 多张图 = 多个工作目录逐张跑完整状态机。

### 第 2 步：仔细识别，写 assets.json

**先读 `references/labeling-guide.md`（全文，标注细则与三分类硬规则）。**

把截图复制进输出目录，仔细看图后写 `assets.json`（assets + skeleton +
texts 三段，格式见 labeling-guide）。核心纪律：
- 每个有辨识度的素材都列，宁多勿漏；顶栏/底栏图标必须标注（底栏判定
  只认标注）；
- text_block 必须全标（它是字体合同的唯一候选池）；
- 写完做**三向防漏复扫**（查漏/查误/骨架边界完整性，细则见
  labeling-guide §2），三个方向都过才进第 3 步。
漏标 = 从产物里静默消失；误标 = 幻觉元素进入产物；框小 = 结构残缺
且校准/断言都发现不了。

### 第 3 步：跑确定性管线 + 校准循环

**先读 `references/calibration-guide.md`（全文：两线并行、校准循环
逐行规则、verdict 消费、降级路径）。**

```
<python> scripts/extract_assets.py --image <图> --assets assets.json --out <输出目录> --request <输出目录>\request.json
<python> scripts/font_probe.py   --image <图> --assets assets.json --out <输出目录> --design-system <设计系统，无则省略>
# 快速档（tier=快速）时 extract 命令追加 --no-alpha
# font_probe exit 2 = REVIEW 停机（字体选型拿不准：低分/类别摇摆/空池
# ——1009-03），报告用户给 --design-system 或 --pool，禁自行重探闯闸
```
- 两条命令**一起发出**（文字线不依赖管线产物）；管线完成后用
  layout.json 复跑一次 font_probe 精化字号/字重——精化轮只刷新
  size/weight，family 保持锁定；styles.json 锁定合同（防换池漂移，
  源图变化自动失效），强制重探用 --reprobe；
- 产出：layout_brief.txt（写码唯一几何/颜色/文字依据）、layout.json
  （断言基准）、assets/、assets_report.json（含每素材 verdict）、
  _check_sheet_detail_*.png（校准图）；
- **校准循环必做**：逐行核对 detail 图（行级规则见 calibration-guide），
  处置落盘；素材处置一律按 `assets_report.json` 的 `verdict` 执行
  （OK / REVIEW / USE_RAW），模型无裁量权；循环最多 2 轮；
- 同目录管线重跑为**增量模式**：只重抠标注变化的素材，全局检测
  （相邻收缩/审计/verdict）仍全量执行；
- **检测器回归 gate（合入前置条件）**：任何 extract_assets /
  font_probe 的检测逻辑或阈值修改，合入前必须跑
  `scripts/selftest.py mask-suite`（回归集 regression/cases.json）
  全绿，并用 `scripts/selftest.py pixel-regression --a <旧目录>
  --b <新目录>` 做页面级对比——不过回归集的改动不得合入
  （2026-09-30：center_void 与 low_score 两度过度 gate 好样本，
  均由回归集当场抓获）。

### 第 4 步：一次成型写 index.html

**先读 `references/system-rules.md`（全文，写码规则集）与
`references/component-templates.md`（标准件骨架模板：状态栏/文字块/
胶囊/图标行/按钮对/dock/入口列——结构照模板填实测数据，不要逐次
发明写法）——禁止跳过。**

核心约束（细则以 system-rules.md 为准）：
- 按第 1 步确认的技术栈写码，禁止换栈；body 即画布，禁止任何外壳；
- 两层布局：区块级按说明书坐标定位，区块内部一律 flex/grid；
- **单位铁律（2026-09-30 改版）**：管线入口已按检测 dpr 把坐标归一
  为**逻辑 px**——brief 每个数字 1:1 就是 CSS px，直接用，禁止任何
  缩放换算（旧"÷2"规则作废；dpr 检测异常时管线会停下要求 --dpr），
  radius 无例外；
- 文字照抄 styles.json 终值；颜色/容器几何/骨架只认实测值；
- 素材引用按 verdict：alpha gate 未发布的（.rejected）引用即 404，
  强制 RAW/SVG；降级占位必须带 `data-asset="asset_N"`；
- **over_photo 素材**（brief 标记 `over_photo_text_erased`）：图内
  文字已被管线擦除、遮罩仍在图里——文字层直接定位渲染在 img 上，
  **禁止**再画遮罩 div/渐变 overlay/blur 垫片（细则 system-rules
  §2.0）；
- 内联 SVG 图标：比对后**由模型自动落 manifest 并引用**
  （`data-icon` + confirmed:true + 证据 note），**禁止就图标引用
  打断用户**；低置信/无命中静默降级抠图；替坑 SVG 尺寸按 getBBox
  占比反算补偿（细则见 system-rules.md §2.7/2.8）；
- **字体子集本地化（1009-04，产物独立性）**：页面含 Google Fonts
  外链时，写完必须跑 `<python> scripts/localize_fonts.py --html
  <产物>\index.html`（按页面字符请求子集 woff2 内嵌，替换外链）——
  字体是渲染正确性的硬依赖，外链在用户浏览器回落 = 字形全崩
  （"宋体"事故的另一半根因）；
- 禁止先写草稿再返工；禁止在对话里输出代码片段。

### 第 5 步：结构断言 + 独立裁判（脚本与裁判说了算）

**先读 `references/assertions-guide.md`（全文：断言明细）；
派裁判前把 `references/judge-guide.md` 作为裁判子代理的任务书。**

```
<python> scripts/verify_page.py --html <输出目录>\index.html --layout <输出目录>\layout.json --image <输出目录>\source.png --out <输出目录>
```
- 退出码 1 → 把全部 FAIL 项**一批修完**再重跑同一命令（禁止逐项
  触发全量 verify），最多 2 轮，仍 FAIL → 停，原样报告明细；
- 退出码 0（PASS）→ **派独立裁判子代理做视觉终审**（输入/纪律/
  输出格式/严重度/循环规则全按 judge-guide.md；主会话**禁止自己
  看图自评**——选手兼裁判是自评偏误的根源）：
  - verdict=FAIL → 修 blocker/major → 重跑 verify → 重派裁判，
    最多 2 轮；仍不过 → 停，报告未清偏差；
  - verdict=PASS → minor 清单进交付报告已知偏差，进第 6 步；
- **"停"是硬指令（2026-09-30 事故后新增）**：修复轮次用尽、或用户
  在任意时点表示停下/接受现状/就此打住 → **立即冻结修复**，按当前
  状态交付并在报告首位如实呈现未修 FAIL。禁止继续修复、禁止用
  AskUser 请求续期修复轮次——修复轮次是安全阀，不是可以争取的
  额度（事故：用户选"就此停下"后模型仍继续修完，违抗明确指令）；
- 文字质量零图检：全由数据断言负责，FAIL 读明细直接修码。

### 第 6 步：交付

**先读 `references/delivery-guide.md`（报告格式与数据纪律）。**
报告所有数字只允许引用脚本产物（verify_report.json / styles.json /
assets_report.json），禁止手写或心算统计。

### 第 7 步：受控修改轮

用户提修改时：不重跑管线（校准基准仍有效），从第 4 步定点修改开始
（精确字符串替换，不整文件重写）；涉及新增/移动素材才补标注重跑
第 3 步；每轮修改完重跑第 5 步同一命令复检。禁止以修改为由整页
重新生成。

## 降级与失败速查

| 情形 | 处置 |
|---|---|
| 体检不过，两次修复仍失败 | 停，报告 fix_commands |
| 当前模型读不懂测试图 | 停，告知需多态模型，禁止继续 |
| 个别素材抠图失败 | 素材级降级：原图 → SVG/占位，位置按坑位 |
| fidelity_ratio <0.9 或 mask score <0.65 | 掩码门禁：alpha 不落盘 → RAW 直贴或图标库路径（人眼放行无效） |
| 图标库识别低置信 / 离线 | 降级抠图兜底；禁止"差不多是这个图标"就引用 |
| 抠图模型整体缺失（保真档） | 停，给 --fix 命令或问是否改快速档 |
| verify FAIL 超 2 轮 | 停，原样报告 FAIL 明细 |
| 裁判 2 轮仍有 blocker/major | 停，报告未清偏差清单 |
| assets.json 被 extract_assets.py 拒绝 | 按 SystemExit 消息修正 json，重跑 |
