# 管线与校准指南（references）——第 3 步细则

## §1 产物清单

- `layout_brief.txt`：写码前必读的布局说明书——行顺序、底栏标记、
  pitch 与**行内关系标注（垂直居中/等间距）**、CANVAS CONTRACT、
  **每行色板 palette**、**每行/每素材实测取色 SAMPLES**、
  **CONTAINERS 自动检测的面状容器（bbox+拟合圆角+实测色）**、
  **SKELETON 骨架段（像素精化框+类型+文字摘要+验证状态）**、
  **TEXTS 逐字文案表**、**渐变容器拟合配方（端点色+角度，Q5）**；
- `layout.json`：机器可读版，第 5 步断言基准（含 expected_texts、
  containers、skeleton、assets、原图路径；骨架带 `base_box` 原始
  标注框）；
- `assets/`：裁剪图 + 透明图（被硬门禁拦下的为 `*.rejected`，不可
  引用）；
- `assets_report.json`：逐素材状态（竞速结果、框精化记录、掩码审计、
  **verdict**）；
- `_check_sheet.png`（总览）+ `_check_sheet_detail_*.png`（逐素材/
  容器/骨架放大校准图，≤12 行/张——校准以它为准）。

**读 layout_brief.txt**：第 4 步的一切位置、尺寸、圆角、颜色、文字
依据；颜色与几何只从实测值取，不凭目测估。

## §2 增量重跑（2026-09-30 新增）

同目录管线重跑为**增量模式**：管线自动比对本次 assets.json 与上次
assets_report 的标注差异，只重抠变化的素材，未变化素材复用已有抠图
结果；**全局 pass（RAW 相邻收缩、掩码审计、verdict 聚合）每次全量
执行**——只省重复抠图计算，不省任何检查。改 1-2 枚标注的重跑从
~9 分钟降到 ~1 分钟。强制全量重抠用 `--force-reextract`。

## §3 标注回归对照（S2）

同目录重跑时，管线自动 diff 本次标注与上次标注，输出**标注差异表**
（新增/删除/移动的素材与骨架，含框位移量）到 stdout 与
`assets_report.json` 的 `labeling_diff` 字段：
- 修复重跑场景：差异表用来确认"只改了想改的"——出现计划外的
  新增/删除/移动 = 标注漂移，必须核实后再继续；
- 差异表是机器生成的对照证据，处置（接受/修正）须落盘到校准记录。

## §4 校准循环（必做，不许跳）

用 Read 逐张打开 `_check_sheet_detail_*.png`（逐素材一行：原图上下文
带黄框=标注框/红框=最终框、放大双底 alpha、状态行），逐行核对：

- **REVIEW 行**：脚本已自动检测并修正（BOX-CLIPPED=自动外扩；
  BOX-LOOSE=自动收紧；LOW MASK SCORE / ALPHA COVERAGE=掩码存疑）。
  逐行确认红框确实框住目标主体——修正错了的，改 assets.json 对应
  box_2d 重跑本步；
- **CONTAINER 行**：确认红框是该按钮/胶囊本体、拟合 radius 与视觉
  相符——写码时容器尺寸/圆角/颜色只认这些数字；
- **SKELETON 行**：[model-only — REVIEW] 的框未经像素验证，逐行确认；
  [program-verified] 的框已被像素检测证实，直接采用；
  **model-only 行的确认必须量化（2026-10-09 实测新增，1009-09）**：
  用脚本对标注框做像素扫描对比（框边界 vs 实测墨迹/色块边界，输出
  偏差数值），偏差 >3 逻辑 px → 修 assets.json 重跑——**禁止只看
  缩略图下"框准"结论**（2~3px 误差在缩略图上不可见，实测：按钮
  目测框矮 5px 直接进了写码合同）；
- **ok 的行也要过一遍**，客观判定（不许"差不多/可接受"放行）：
  ① 红框内是目标主体本身；② alpha 边缘无齐直切边；③ 双底下主体
  形状完整；④ RAW 素材核对 brief 测量提示（`[css-native]` /
  `rounded-rect radius≈Npx` / `floats on a uniform background`）；
- 处置：框错 → 修 assets.json 重跑本步；框准但 alpha 残缺 → 弃用
  透明版（记入交付报告）；
- **verdict 消费（硬规则，人眼无裁量权）**：`assets_report.json` 的
  verdict 是每枚素材的确定性处置——`OK` 引用 alpha；`REVIEW` 人工
  复核后处置并落盘；`USE_RAW` / ALPHA GATE 未发布的素材**不存在
  alpha 文件**（引用即 404），写码走 RAW 裁剪或图标库路径。掩码
  5-10% 的主体收缩在 4x 放大图上人眼不可辨，"看着完整"不构成放行
  依据；
- **无法确认正常的信号一律按异常处置并升级，禁止以"可接受"放行**；
- 循环最多 2 轮，全部达标才进第 4 步。`_check_sheet.png` 总览图只看
  全局，细节判定一律以 detail 图为准。

## §5 素材级降级（不问用户，直接降）

最终判定无可用透明版的素材，写码时按优先级：logo/图标/几何 → inline
SVG 重绘；照片/插画 → 评估原图底色与页面背景融合后直贴或
mix-blend-mode；兜底 → 中性占位。位置一律按说明书坑位，降级占位打
`data-asset="asset_N"`。

## §6 档位级故障（必须问用户）

抠图模型整体缺失且用户选了保真档 → 停下报告：给出 `doctor.py --fix`
修复命令，或问是否临时改快速档。等用户决定，不许自行换档。
