# tests/ — 分层移植清单（来源：product-prototype 30 个测试脚本）

> **移植状态（2026-11-04 更新）**：test_editor.cjs 已移植并校正到 V04 后编辑器（16 断言全绿，跑法见下）。
> 其余脚本（annotations/direct/callouts/matrix/feature/workspace）原稿在 E:\dingdingdl\product-prototype-SKills\...\scripts\，
> 未移植——旧断言需逐条对照 V01-V04 改动后的 UI 校正，按需分批搬。test_editor 已覆盖：设计系统生效/冷启动锁定/口令解锁/改字撤销/标注字号隐藏/自由画布物化/图片内嵌/插页/页面管理/调试扫描/保存链(首绑+静默覆盖)/写失败保留脏态/显式导出不清脏/导出件离线重开。
> 三代导出循环（A→B→C）场景待补（离线 context 下 download 事件触发不稳定）。
> 跑法：`python scripts/build.py --pages assets/starter-pages.html --title T --output <靶>.html && PLAYWRIGHT_MODULE_PATH=<npm模块目录> node tests/test_editor.cjs <靶>.html`
> 它们是编辑器能力回归的**待移植安全网**——原脚本硬编码原技能路径（E:\dingdingdl\...），
> 移植时需改路径引用并去掉本地直存相关断言。在移植完成前，编辑器能力回归由
> scripts/fixtures/flawed-site.html（检测器自证）+ audit/verify 的内置检查承担。

## 第一层：直接可用（编辑器能力回归，改造后必须全绿）

| 脚本 | 验证能力 |
|---|---|
| test_editor.cjs | 编辑器核心：选中/改字/拖拽/插入/页面管理/保存重开 |
| test_annotations.cjs | 标注：点选/编号/说明卡/编辑/保存重开（考核第 5 条） |
| test_direct_manipulation.cjs | 普通页直接拖动/八向拉伸/改形状/改字 + 重开保持（考核第 3 条） |
| test_callouts_and_password.cjs | 长说明卡/连线/侧选/口令错误拒绝（考核第 6 条） |
| test_design_style_matrix.cjs | 九槽风格矩阵：全页面 × 风格切换 × 保存重开 |
| test_feature_matrix.cjs | 参考功能矩阵逐项回归 |
| test_workspace.cjs | 工作区行为 |

## 第二层：轻改可用（保存通道改为浏览器双通道）

| 脚本 | 改造点 |
|---|---|
| test_source_save.cjs | 保存语义改为 File System Access / Blob 双通道断言 |
| test_full_acceptance.cjs | 全链路骨架保留（编辑→另存→关浏览器→断网重开→续编）；去掉 EXE/直存环节 |

## 第三层：弃

| 脚本 | 原因 |
|---|---|
| test_local_save.cjs / test_local_save_helper.py / test_native_save.cjs / test_cross_platform_save.py | 本地直存程序不在 v1 范围（纯浏览器双通道已覆盖考核要求） |

## 第四层：视范围保留

| 脚本 | 条件 |
|---|---|
| test_media_components.cjs / test_media_uploads.cjs / test_product_media*.cjs | 交付物含轮播/图库/视频时必须全绿；纯图文项目可暂缓但须声明 |

## 第五层：本技能新增（原技能没有）

| 脚本 | 验证 |
|---|---|
| scripts/verify-interactions.mjs | 交互断言执行器（从开工文档声明机械生成） |
| scripts/audit.mjs | 结构/外链/死链/控制台/断图/几何 + 编辑自证 best-effort |
| scripts/fixtures/flawed-site.html | 已知 8 缺陷测试靶：所有检测器必须报满，少报 = 检测器自身不合格 |
