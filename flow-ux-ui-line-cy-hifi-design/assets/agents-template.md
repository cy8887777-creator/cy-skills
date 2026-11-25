# AGENTS.md — 本产物的 AI 修改指南（模板）

> 占位符：{{TITLE}} / {{DEVICE}} / {{DEFAULT_PWD}}（概况不写页面数与风格名——2026-11-23 定案：本文件会被宿主注入给产物目录里的任何 AI 会话，这两样是锚定物）

# {{TITLE}} — AI 修改指南

本文件是给 AI coding agent（Claude Code / Cursor / Copilot 等）的产物修改指南。本产物是**单文件可编辑 HTML 原型**：页面、交互、标注、换肤状态全部内嵌在**一个 HTML 文件**中，内置可视化编辑器也内嵌在同一文件里。

## 产物概况

- 标题：{{TITLE}}
- 端型：{{DEVICE}}
- 编辑口令：{{DEFAULT_PWD}}（内置默认，可在编辑模式「更多 ▸ 修改编辑口令」中更改）

> 概况不写页面数与当前风格名（2026-11-23 定案：本文件会被宿主自动注入给产物目录里工作的任何 AI 会话——换风格执行链按纪律禁读产物侧事实，这两样是锚定物；页面数请数页面树，当前风格以产物内风格面板/令牌为准。）

## 文件结构（哪些能改、哪些绝对不能动）

单文件内含以下顶层区块，**标注「不可动」的区块是编辑器/运行时的核心，删除或重构会导致编辑器与交互全部报废**：

| 区块 | 作用 | 可否修改 |
|---|---|---|
| `<style id="project-design-tokens">` | 设计系统令牌（颜色/圆角/字体变量） | 改值可以，删块不行 |
| `<script type="application/json" id="prototype-design-system">` | 设计系统数据 | 不可动 |
| `<script type="application/json" id="prototype-config">` | 编辑口令哈希 | 改口令请走编辑器 UI |
| `<script type="application/json" id="prototype-start-doc">` | 开工文档全文（构建 `--start-doc` 时注入） | 只读参考 |
| `<script type="application/json" id="prototype-style-state">` | 当前换肤状态 | 由编辑器管理，不要手改 |
| `<style id="editor-inline-style">` + 编辑器 script 块 | 内置可视化编辑器 | **不可动** |
| `<main id="canvas">` 内的 `<section class="screen" data-screen="...">` | **原型页面**（你的主要工作区） | ✔ 随意修改内容 |
| `<aside id="sidepanel">` / 顶栏 / 面板 | 编辑器 UI | **不可动** |

## 页面骨架规范（改页面必读）

每一屏的结构：

```html
<section class="screen on" data-screen="cart" data-name="购物车">
  <div class="scr-head"><span class="scr-name">购物车</span><span class="scr-note">一句话职责</span></div>
  <div class="device mobile"><div class="notch"></div><div class="statusbar">…</div>
    <div class="viewport"><div class="app">…页面内容…</div></div>
  </div>
</section>
```

（`.device` 类按页面清单端型取 `mobile|tablet|desktop`；notch/statusbar 仅手机壳端有。）

**data-\* 属性语义**（交互全靠它们，破坏即失能）：

- `data-screen`：页面唯一 id（跳转的目标值，改页面 id 时**全局搜索引用**）
- `data-name`：页面树显示名
- `data-eid`：元素 id（标注/定位引用）
- `data-on`：**点击交互 JSON**，格式见下节
- `data-note`：功能标注文本（标注模式的说明）
- `data-pin`："top"/"bottom"/" "（位置固定）
- `data-layout`："free"（该页已启用绝对定位）

## data-on 交互 JSON（跳转/弹层怎么写）

```html
<button data-on='{"click":{"goto":"payresult"}}'>去支付</button>
<button data-on='{"click":{"sheet":"filterSheet"}}'>筛选</button>
<button data-on='{"click":{"toast":"已加入购物车"}}'>加入购物车</button>
<button data-on='{"click":{"back":true}}'>返回</button>
```

- `goto`：跳转到目标页（值为目标 `data-screen`，运行时只消费 screenId）
- `sheet`：打开目标元素（需目标带对应 id）；`close`：关闭弹层
- `toast`：轻提示；`tab/toggle/switch/check/scroll/link`：页内微交互

## 修改守则

1. **改文字/图片/颜色**：随意，但颜色请用设计令牌（`var(--accent)` 等），不要硬编码——否则换肤失效
2. **改结构/增删元素**：保持 `data-screen`/`data-eid`/`data-on` 完整；新增可点击元素想要跳转就补 `data-on`
3. **不要动**上表「不可动」区块；不要重排/格式化整个文件（会破坏编辑器注入的定位）；不要删除文件头的 `<!-- prototype-project: … -->` 注释标记（重建时防误覆他项目的校验依据）
4. **改完自验**：浏览器打开 → 点「✎ 去编辑」（默认口令见上）→ 走一遍你改动的页面与跳转
5. **新增一整屏**：复制一个现有 `<section class="screen">` → 改 `data-screen` 为新唯一 id → 改内容 → 在需要入口的元素上加 `data-on` 指向新 id

## 常见任务配方

- **改按钮跳转**：找到该元素 → 改 `data-on` 里 `goto` 的值为目标 `data-screen`
- **加标注**：给元素加 `data-note="功能说明文字"`
- **换配色**：不要硬编码；用 `--accent` / `--accent-soft` / `--bg` 等令牌，或编辑器内「设计风格」两步向导
