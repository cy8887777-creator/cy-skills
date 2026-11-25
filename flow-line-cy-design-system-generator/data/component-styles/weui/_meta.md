# WeUI 设计规范 · 采集元信息

- 官方入口：https://weui.io（在线预览）+ https://github.com/weui/weui
- 抓取日期：2026-10-22
- 抓取方式：weui.io 为静态演示页（SPA 壳），全部组件示例标记位于 `<script type="text/html">` 模板中，直接离线解析模板获得 60 个组件区的标题/说明/样式类，并对 20 个核心组件导出 DOM 结构缩进树；README 经 GitHub API 获取（raw.githubusercontent.com 与 jsDelivr 均超时，API 可用）。
- 章节数：3
- 已知限制：weui.io 不含文字版设计原则与色值规范，视觉参考以组件 DOM 结构与 weui-* 样式类为准；组件示例中的交互态（JS 驱动）未捕获。

## 文件清单

- 组件总览.md（60 个组件区：标题/说明/涉及样式类）
- 核心组件视觉形态.md（20 个核心组件的 DOM 结构树）
- 设计说明-README.md（官方仓库 README）
