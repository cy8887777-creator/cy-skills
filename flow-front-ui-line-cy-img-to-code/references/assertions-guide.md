# 断言与目检指南（references）——第 5 步细则

## §1 断言清单（verify_page.py 一次跑完）

| 断言 | 检查什么 | FAIL 抓的事故 |
|---|---|---|
| img_loaded / console / failed_requests | 素材全加载、无报错（含 ALPHA GATE 404 强制降级闭环） | 引用被 gate 的 alpha、路径错、CDN 挂 |
| bottom_bar | 底栏与画布对齐（容差=实测空隙） | 为凑贴底把底栏拉离实测位置 |
| canvas_contract / canvas_alignment | 画布固定、宽视口不撕裂 | 内容撑高页面；fixed 在 RTL 下撕离画布 |
| texts_present | 文案逐字存在 | 文案被改写/省略 |
| asset_geometry / container_geometry / skeleton_geometry | 素材/按钮/骨架尺寸位置 ±max(6px,12%) | 布局漂移、素材放错坑位 |
| text_overflow | 叶子文本不溢出自己的盒子 | 标签被折行 |
| layout_integrity | 文字×img 穿插 / 容器子内容溢出 / 负 margin | 文字为凑断言被插进图标 |
| styles_consistency | computed style 逐块核对 styles.json | 字体族/字重/字号没照合同落 |
| font_drift_warning / font_drift_check | 渲染宽超框 35%+；墨迹高比/笔画密度实测（WARN 通道） | 字重过重、字体漂移 |
| **raw_occlusion**（2026-09-30） | 带底 RAW 与文字块相交或间距 <2px 即 FAIL | 剑贴片 0px 相接盖住文字 |
| **icon_contract**（2026-09-30） | svg[data-icon] key ∈ manifest confirmed；替坑 SVG 墨迹宽 ≈ 坑位框 ±15% | 子代理 HIGH 误判；viewBox 折扣 60-70% |
| **墨迹宽 gate**（skeleton_geometry 内） | text_block Range 墨迹宽 > 原始标注框 ×1.15 即 FAIL | flex 拉宽元素框骗过 rect 断言 |
| **ext 框基准** | edge-extended 骨架按 base_box 断言 | 星星画进误扩框、断言全绿 |

## §2 文字零图检

文字质量完全由数据断言负责（styles_consistency 全量合同 +
skeleton_geometry 中心点 + 墨迹宽 + text_overflow + texts_present）。
verify 之后文字不需要看图——FAIL 读明细直接改码复检。diff 目检图的
文字区已灰罩，禁止再逐带核对文字。

## §3 视觉终审（独立裁判执行，PASS 后必做）

三项目检材料由**独立裁判子代理**核对——主会话禁止自己看图自评
（输入/纪律/输出格式/循环规则见 `judge-guide.md`，派发时作为裁判
任务书）：

1. **diff 逐带对照**（`_diff_sheet.png`）：裁判核对顶部 FULL PAGE
   行页级位置关系（底栏与画布、区块顺序、无整体漂移）；之后逐带
   结构化 checklist——容器（位置/尺寸/圆角形态/底色渐变/描边/
   内容方位）、css-native 重建元素**形态**（"意思到了"不算过）、
   结构性嵌套（卡片底部内嵌条带在卡片内）。尾部 **SMALL ASSET
   ZOOM 区**：<50px 素材放大并排——形状级失真在带状图被稀释，
   只有这里可见；
2. **素材回贴比对**（`_asset_render_check_*.png`）：裁判只逐行核对
   REVIEW 行（瘦小/啃边/细节丢失），auto-ok 行已由数值盖章；发现
   收缩/啃边 → 裁判报 blocker，主会话弃用透明版回第 3 步门禁；
3. **宽视口整页**（`preview_wide.png`）：画布与底栏整体形态。

裁判输出固定结构清单（verdict + findings，每条带严重度与证据）。
主会话按清单处置：blocker/major → 第 7 步规则定点修 → 重跑 verify
→ 重派裁判（≤2 轮）；minor → 记交付报告已知偏差。
禁止：主会话自评代替裁判、跳过本步、把 FAIL 说成 PASS、修清单外
的东西。
