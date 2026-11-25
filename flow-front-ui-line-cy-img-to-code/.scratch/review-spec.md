# Spec: flow-front-ui-line-cy-img-to-code hard-loop + efficiency rework (baseline 7d3b925 → HEAD)

用户确认的优化需求（2026-09-29/30 三会话穿透复盘后定稿）：

## 总原则
1. PASS 含金量：检测器拿不准必须 REVIEW/非 OK；坏→OK 的成本（终局穿透）永远高于误报→REVIEW。质量判断零落在模型上——凡"REVIEW/提示等人处理"的软路径无效，唯一有效处置：管线物理产出、FAIL 闭环、白名单。
2. 不拆既有 harness（人工加的护栏），时间优化不得减少任何检查覆盖。
3. 检测器/阈值改动必须过回归集（已知坏样本必须拦、好样本不得误判 USE_RAW）。

## 功能需求（17 项，全部要求实现）

P0：
- Q8 SKILL.md 分层瘦身：SKILL.md 收缩为纯状态机（每步入口"先读对应 references 文件"），细则外移 references/（labeling/calibration/assertions/delivery/environment/system-rules 增补/component-templates），内容不得丢失；
- T1 管线增量重跑：同目录重跑时标注未变化的素材复用上次抠图结果（快照比对），全局 pass（RAW 相邻收缩/审计/verdict 聚合）仍全量执行；检测器版本变化时快照失效；
- T2 校准指南落盘（呈现优化部分允许后延）；
- S3 verify 确定性等待：截图前等 fonts.ready + images 全解码 + 无 pending 请求；
- S4 脚本入口 utf-8 统一；
- Q7 页面级像素回归：selftest.py pixel-regression 子命令，diff 两轮 preview_desktop.png 出量化报告。

P1：
- S1′ 技术栈选择提示运行时依赖形态（CDN 需联网）+ 可选 scripts/vendor_local.py 本地化（仅用户要求时）；
- S2 标注回归对照：重跑时 diff 本次与上次 assets.json 标注，输出 added/removed/moved 差异表（labeling_diff）；
- Q1 selftest.py mask-suite：掩码检测器回归集（cases.json），已知坏样本必须非 OK/USE_RAW，未列好样本不得 USE_RAW（allow 列表除外）；
- Q2 标注体检：相邻素材框重叠 >30% → 双方 verdict REVIEW；
- Q5 渐变端点自动拟合：容器沿轴采样拟合线性渐变（双轴尝试+中位数探针+线性度检查），brief 输出 CSS 配方；被覆盖污染时诚实放弃；
- Q6 图标三候选证据板：子代理回传 top-3，人终审落 manifest（文档层）；
- T4 写码骨架模板（references/component-templates.md）。

P2：
- T5 Google Fonts 本地缓存（css2+woff2 落盘，失败回退 CDN）；
- Q4 素材内容 hash 缓存（crop md5 → 掩码复用；gate 判定不缓存）。

## 已知约束
- 不拆既有 harness；不引入新外链依赖；产物契约（单 index.html）不变。
- 2026-09-30 回测发现并要求修复：center_void 不得作为硬门禁（好坏分布重叠无判别力）；low_score 不得硬门禁（好掩码常 0.3+）；T1 复用必须在管线版本变化时失效。
