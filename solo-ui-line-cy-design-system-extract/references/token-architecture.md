# Token 架构（4 段相加模式；本文件数字 = v2 演示案例历史实测 85，现行合流版案例实测 134 = 35+29+22+48）

> **数字均为各自案例的实测值，不是契约及格线。** 真实项目计数以实测为准（self_check counts 件套核三构造对账：HTML = md = system-rules.json），四段**相加模式**不变。命名跟值走——见名实一致纪律（§末）。下文 85 全表仅作 4 段架构的形态示例保留。

权威参考：`templates/design-system.html`（合流版模板）+ `templates/system-rules.md`（实测 134）。

> **计数口径（必须统一）**：现行合流版案例 = 基础 35 + 语义 29 + 组件 22 + 度量 48 = **134**。任何文档、脚本、报告只用这一个口径；本文件内 85 全表为 v2 历史形态示例。

---

## 1. 基础层（19 = 主色 2 + 主色辅助 3 + 中性 8 + 功能 6）

### 主色组（2）

| Token | 值 | 唯一职责 | 禁用于 |
|---|---|---|---|
| `--blue-600` | #3056D3 | **品牌主色**：CTA / 链接 / 选中态 | 大面积铺色、正文文字 |
| `--blue-700` | #2443AB | 主色 hover / active | 默认态 |

### 主色辅助阶（3）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--blue-500` | #4569E0 | 聚焦描边 | 大面积铺色 |
| `--blue-300` | #A8C0F4 | 次级强调、装饰渐变 | 文字 |
| `--blue-100` | #E8EEFC | 浅底、focus 光晕 | 文字 |

### 中性色（8）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--gray-50` | #FAFAFA | 页面底色 | 卡片内部 |
| `--gray-100` | #F4F4F5 | 禁用底、表头底 | 正文文字色 |
| `--gray-200` | #E4E4E7 | 分隔线、卡片描边 | 输入框描边 |
| `--gray-300` | #D4D4D8 | 输入框 / 控件默认描边 | 分隔线 |
| `--gray-400` | #A1A1AA | 禁用文字、占位符 | 正常文字 |
| `--gray-500` | #71717A | 次要文本 | 长正文（≥3 行段落）、主标题 |
| `--gray-700` | #3F3F46 | 深次文本 | 主标题 |
| `--gray-900` | #18181B | 主文本 | 非文本场景 |

### 功能色（6 = 3 主 + 3 浅底）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--success` | #16A34A | 成功状态文字 / 图标 | 正文 |
| `--success-bg` | #E7F6EC | 成功浅底 | 正文文字色 |
| `--warning` | #D97706 | 警告状态 | 正文 |
| `--warning-bg` | #FDF1E2 | 警告浅底 | 正文文字色 |
| `--danger` | #DC2626 | 危险 / 错误状态 | 正文 |
| `--danger-bg` | #FDEAEA | 危险浅底 | 正文文字色 |

**基础层铁律**：
- 主色只 1 枚（blue-600），其他蓝阶都是它的派生
- 中性色按 50→900 阶梯成档，**禁自造灰色**
- 功能色每色 = 主色 + 浅底配对，**缺一即坏**
- 角色边界（主色/中性/功能）禁互相越界

---

## 2. 语义层（17）

### 颜色（6）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--color-text-primary` | gray-900 | 主文本 | 非文本场景 |
| `--color-text-secondary` | gray-500 | 次文本、标签 | ≥3 行连续段落、主标题 |
| `--color-text-disabled` | gray-400 | 禁用文本 | 正常文本 |
| `--color-bg-page` | gray-50 | 页面底色 | 卡片内部 |
| `--color-bg-card` | #FFFFFF | 卡片、浮层底 | 页面底色 |
| `--color-border` | gray-200 | 分隔线、卡片描边 | 输入框描边 |

### 输入相关（2）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--input-border-default` | gray-300 | 输入控件默认描边 | 分隔线 |
| `--input-border-focus` | blue-500 | 输入控件聚焦描边 | 默认态 |

### 焦点（1）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--focus-ring` | `0 0 0 3px` blue-100 | 所有可聚焦控件的键盘焦点光晕 | 装饰 |

### 字族（1）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--font-family-base` | "PingFang SC", "Microsoft YaHei", "Helvetica Neue", sans-serif | 全局唯一字族 | 品牌混排 |

### 行高（1）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--line-height-body` | 1.6 | 正文行高 | 标题（标题见 §4 字号表） |

### Icon（3）

| Token | 值 | 用途 |
|---|---|---|
| `--icon-sm` | 16px | 行内图标 |
| `--icon-md` | 20px | 按钮内图标 |
| `--icon-lg` | 24px | 独立图标 / 空态 |

### 行动色（1）

| Token | 值 | 用途 | 禁用于 |
|---|---|---|---|
| `--color-action-primary` | blue-600 | 主行动、链接、选中 | 大面积铺色 |

### 描边色（2，本节累计）

| Token | 值 | 用途 |
|---|---|---|
| `--stroke-color-default` | gray-300 | 默认描边色 |
| `--stroke-color-strong` | gray-700 | 强描边色 |

**语义层铁律**：
- 业务代码**只许引用语义层**（少量组件层）；**禁引用基础层**（基础层是底层事实，不直接面向 UI）
- 命名必须回答"用在哪、禁用在哪"——任何缺禁用的语义 token 都不合格

---

## 3. 组件层（6）

| Token | 值 | 归属 | 禁用于 |
|---|---|---|---|
| `--button-bg-primary` | action-primary | 主按钮底色 | 次按钮 |
| `--button-bg-primary-hover` | blue-700 | 主按钮悬停 | 默认态 |
| `--button-bg-danger` | danger | **危险按钮底色（高危操作唯一载体）** | 普通操作 |
| `--button-bg-danger-hover` | #B91C1C | 危险按钮悬停 | 默认态 |
| `--input-border-focus` | blue-500 | 输入控件聚焦描边 | 默认态 |
| `--tag-bg-brand` | blue-100 | 品牌标签底色 | 错误标签 |

**组件层铁律**：
- 只收录**跨页面复用 ≥3 次**的组件 token
- 单次复用进组件内联样式，不进 token 表
- 命名格式：`--<component>-<slot>-<state>`（如 `--button-bg-primary-hover`）

---

## 4. 度量（43 = 间距 7 + 圆角 4 + 阴影 5 + 字号 6 + 行高 5 + padding 4 + stroke_width 4 + opacity 3 + z-index 5）

> 演示值；任何项目提取后值可改、计数不变。

### 间距（7）

| Token | 值 | 场景 |
|---|---|---|
| `--space-1` | 4px | 图标与文字间隙 |
| `--space-2` | 8px | 组件内部元素间隙 |
| `--space-3` | 12px | 紧凑列表行距 |
| `--space-4` | 16px | 组件之间 |
| `--space-6` | 24px | 卡片内边距、分组之间、栅格栏距 |
| `--space-8` | 32px | 区块之间 |
| `--space-12` | 48px | 章节之间 |

### 圆角（4）

| Token | 值 | 归属组件 |
|---|---|---|
| `--radius-sm` | 4px | 开关、小元素 |
| `--radius-md` | 8px | 按钮、输入框、下拉 |
| `--radius-lg` | 12px | 卡片、弹窗、弹层 |
| `--radius-full` | 9999px | 标签、头像、圆点 |

### 阴影（5 = sm/md/lg + focus/overlay）

| Token | 值 | 层级 |
|---|---|---|
| `--shadow-sm` | `0 1px 2px rgba(24,24,27,.06)` | 卡片（默认浮起） |
| `--shadow-md` | `0 4px 12px rgba(24,24,27,.10)` | 下拉菜单 |
| `--shadow-lg` | `0 12px 32px rgba(24,24,27,.16)` | 模态弹窗（最高层） |
| `--shadow-focus` | `0 0 0 3px var(--blue-100)` | 键盘焦点光晕（= --focus-ring 的具象化） |
| `--shadow-overlay` | `0 8px 16px rgba(24,24,27,.08), 0 12px 32px rgba(24,24,27,.16)` | 双层阴影（Drawer / 复杂弹层） |

### 字号（6，字重三档 400/600/700）

| Token | 字号 / 行高 / 字重 | 用途 |
|---|---|---|
| `--font-size-display` | 28 / 36 / 700 | 页面主标题 |
| `--font-size-title` | 22 / 30 / 700 | 区块标题 |
| `--font-size-subtitle` | 18 / 26 / 600 | 次级标题 |
| `--font-size-body` | 16 / 26 / 400 | 正文 |
| `--font-size-caption` | 14 / 22 / 400 | 辅助说明 |
| `--font-size-footnote` | 12 / 20 / 400 | 注脚、标签 |

### 行高（5，独立档）

| Token | 值 | 场景 |
|---|---|---|
| `--line-height-tight` | 1.3 | display 标题 |
| `--line-height-snug` | 1.45 | subtitle |
| `--line-height-normal` | 1.6 | body |
| `--line-height-relaxed` | 1.75 | 长文阅读 |
| `--line-height-loose` | 2 | 说明 / 段落 |

### Padding（4，组件内尺寸体系化）

| Token | 值 | 归属 |
|---|---|---|
| `--padding-sm` | 8px | 小型元素内边距 |
| `--padding-md` | 12px | 中型元素 |
| `--padding-lg` | 16px | 大型元素 |
| `--padding-xl` | 24px | 容器类内边距 |

### Stroke 宽度（4）

| Token | 值 | 归属 |
|---|---|---|
| `--stroke-width-hairline` | 0.5px | 极细分割线 |
| `--stroke-width-thin` | 1px | 标准描边 |
| `--stroke-width-base` | 1.5px | 图标描边（默认） |
| `--stroke-width-bold` | 2px | 强描边、按钮按下态 |

### Opacity（3）

| Token | 值 | 用途 |
|---|---|---|
| `--opacity-disabled` | 0.45 | 禁用态整体透明 |
| `--opacity-tint` | 0.12 | 浅底派生 |
| `--opacity-mask` | 0.45 | 弹层遮罩 |

### Z-index（5，禁止自造数值）

| Token | 值 | 归属 |
|---|---|---|
| `--z-dropdown` | 1000 | 下拉 / Select 浮层 |
| `--z-sticky` | 1100 | 吸顶表头 |
| `--z-drawer` | 1200 | 侧滑抽屉 |
| `--z-modal` | 1300 | 模态弹窗 |
| `--z-toast` | 1400 | 全局轻提示（永远最顶） |

---

## 总和确认

| 段 | 计数 |
|---|---|
| 基础 | 19 |
| 语义 | 17（含 stroke_color 2） |
| 组件 | 6 |
| 度量 | 43 |
| **合计** | **85** |

> 描边分两类：粗细（4 档，归度量 stroke_width）+ 颜色（2 档，归语义 stroke_color），跨段不重复计。
> **自检脚本断言（2026-10-15 修正）**：4 段实测相加 = md 声明 = HTML 声明（**三份自洽**；85 仅案例回归 `--expect-total` 传入）。**禁止为凑 85 把真实项目塞进固定槽位或保留错位名**——颜色词命名（red/orange/yellow/green/cyan/blue/purple/pink）必须与值实测色相一致，self_check features 件套的名实一致检查会抓。

---

*设计系统提取技能 · token-architecture 细则 · v2.0.0 · 2026-10-14*
