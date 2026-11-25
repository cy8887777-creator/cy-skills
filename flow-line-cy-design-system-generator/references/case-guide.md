# 案例导读 · design-system.case.html（成文前必读的结构地图）

> 案例本体 = `data/case/design-system.case.html`（1812KB · 跑腿服务真实项目 · extract 技能实战产物）。
> **本导读是它的结构地图**——成文前先读这篇（5 分钟），按图索骥去案例原文查对应章的完整写法；禁止不读案例直接凭印象成文。

## 一、它是什么

一份**人看的规格书 HTML**：单文件自包含（内联全部 CSS/JS/图标 svg），侧栏导航 + hero + 15 章正文。它同时是：
- **标准答案**——每个卡槽都有案例字面的完整写法（成文 = 逐段复写为本项目值）
- **交互样板**——色板点击复制、组件实物复制 CSS、图标 lightbox，交互代码直接搬

## 二、骨架三层（复刻这三层，形态就对了 80%）

| 层 | 内容 |
|---|---|
| **皮肤变量**（:root 第二段） | `--skin-*` 12 个变量：页面底/正文/次级/分隔线/侧栏底/侧栏字/点缀/格纹/代码底+字（成对）/卡底+字/徽章底+字（成对）——**每条带"→ 深色项目取什么实值"的注释**。换项目 = 只改这一段 |
| **骨架引用别名** | `--paper/--ink/--ink-soft/--line/--accent` 挂皮肤；`--font-display`（标题字体）/`--mono` |
| **骨架类** | `.sidebar(256px 深底+brand+nav)/.hero(SPEC SHEET tag+46px 大标题+四格 meta)/.ch-head(描边章号 64px+h2+en+ch-intro)/.block/.spec-label(::after 延伸分隔线)/.plain` |

背景**格纹**：`body::before` fixed 全屏 24px 网格（`--skin-grid`，浅色项目可设 transparent）——玻璃/浮层效果依赖此类背景纹理。

## 三、15 章清单与各章卡槽

01 设计价值观 → 02 布局 → 03 多端适配 → 04 设计要求 → 05 颜色 → 06 字体 → 07 间距 → 08 圆角 → 09 阴影 → 10 动效 → 11 组件库 → 12 图标 → 13 素材资产 → 14 场景规范（v1.1.0 更名「设计要求」并入）→ 15 变更日志

**标准 block 类型**（每章 2-5 个，共 66 个）：
- `PRINCIPLES · 原则`（ul.plain，b 开头短句）
- `WHAT · 作用`（这层设计承担什么）
- `APPLICATION · 实物`（色板墙/字阶行/组件舞台/布局模板——**真控件+点击复制**）
- `USAGE · 使用规范`（DO ✓ / DON'T ✕ 成对）
- `SPECIFIC · 具体禁令` / `CONCEPTUAL · 概念性禁令` / `A11Y · 无障碍红线`
- `SEMANTIC · 语义层` / `REGISTRY · 引用登记` / `PROMPT · 生成提示词母版`

## 四、关键卡槽解剖（成文时照此复写）

### 色板墙（颜色章）
```html
<div class="sw-group"><b>组名</b><span class="role-badge">主色 3 档 + 渐变浅端</span></div>
<div class="swatches">
  <button class="swatch" data-hex="#hex"><span class="chip" style="background:#hex"></span>
  <span class="nm">token 名</span><span class="hx">#hex · 用途说明</span></button>
</div>
```
语义层色板**按角色分组**（PRIMARY/TINTS/NEUTRAL/功能色），每枚带用途短句。

### 字阶行（字体章）
```html
<div class="type-row"><span style="字号/字重实渲染">示例文本</span>
<span class="meta"><b>档名</b> · 字族 · 行高 · 用途</span></div>
```

### 组件大卡（组件章 · **规格书深度**）
```
大卡容器（r16 白卡）
├─ 卡头栏：N. 组名 + 英文 + 来源徽章（「已提取 N 页 N 处 · X 态为 AI 补全」）
└─ 卡体：每个变体一行
   ├─ 变体名 + 尺寸标注串（「160×56 · 胶囊 · 渐变 82.09deg · 字 12/500 · 投影 shadow-sm」）
   └─ 状态穷举单元（st-cell）：每个状态一格实物
      ├─ 状态标签（default / pressed / disabled；pressed 用 scale(.96)+brightness(.96) 真实模拟）
      ├─ AI 补全橙角标（推断态必标）
      └─ ⧉ 复制 CSS 按钮（读取该实物根元素的 style）
```
三原则：**实物即规格**（尺寸/圆角/投影直接来自 token，找不到实物=规范缺口）· **状态穷举**（交互组件 ≥ default/pressed/disabled）· **来源分层**（蓝标提取/橙标推断）。

### 图标实物（图标章）
内联 svg 陈列按页分组 + 每枚名称标注 + PROMPT 母版（库中缺货时的生成提示词，pre.prompt 块）。

### 素材网格（素材章）
`figure.thumb-cell` 网格 + data-full 原图 + 点击 lightbox。**无图项目此章写策略说明即可**。

## 五、背景的处理方式（贯穿四落点 + 皮肤层）

背景**不单独成章**——按职责拆：**颜色章**（底色 token 登记，带实测一致性说明）/ **间距章 WHAT**（底色从缝隙透出 = 白卡秩序的机制句）/ **禁令章**（禁 #111/#000 作页面底——底色唯一性钉死）/ **布局章原则**（白卡浮于底色）/ **皮肤层**（--skin-page-bg + 格纹 + 侧栏底派生规则的注释）。

## 六、交互 JS（模板尾部，直接搬）

- `copyToClipboard`（clipboard API + execCommand 兜底）+ toast
- `.swatch` 点击 → 复制 data-hex
- `.css-copy` 点击 → 提取相邻实物根元素的 style 组装 CSS 复制
- `.thumb-cell` 点击 → lightbox 看原图
- 滚动监听 → 侧栏当前章高亮

## 七、成文对照工作法

1. 读本章在案例中的**对应章全文**（按需查原文，不用通读 1.8MB）
2. 复制案例该章的 block 骨架与交互代码
3. 逐段把案例演示值替换为本项目**实测锁值**
4. 自查：裸值品牌污染（案例 hex/项目名/日期残留 = 漏网）+ 角色徽章（实测/AI 补全）逐块标
