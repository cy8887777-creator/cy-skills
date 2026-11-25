# scripts/dev/ —— 一次性采集/调试脚本存档

开发期用于采集 `data/component-styles/` 组件库快照与图标库的一次性脚本（`_capture*` / `_discover*` / `_dedup` / `_idx` / `_loc2` / `_shadcn-*` / `_audit-quality`；图标库采集器存于本目录 `_collector/`，散装 SVG 已于 2026-11-25 合并为 `data/icons-json/`），以及采集日志 `_capture-log.json`（记录了国内 9 库首轮采集失败、后经补采成功但未生成 _meta.md 的经过）。

- 技能运行时**不使用**本目录任何文件；正式管线脚本在 `scripts/` 根目录。
- 归档时未做路径适配——如需重跑，先检查脚本内的输入输出路径假设。
- 组件库快照的出处登记见 `data/component-styles/INDEX.md` 与各库 `_meta.md`（国内 9 库暂缺 meta）。
