# 设计审查报告

- 目标：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\examples\workbench.html`
- 生成时间：2026-10-23T12:38:35.794Z
- 视口：1440×900、390×844
- 渲染引擎：Chrome/155.0.8059.82
- 问题总数：**8**　高 3｜中 2｜低 3

## 截图（供视觉复核）

- w1440：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-203815-workbench-audit\w1440.png`
- w390：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-203815-workbench-audit\w390.png`

## 无障碍（2）

### [高] WCAG 1.4.3 对比度（最低）（18 处）

- 位置：`div > div:nth-of-type(2) > span:nth-of-type(1)`
- 实测：2.38:1（rgb(255, 255, 255) on rgb(7, 193, 96)，11px）
- 判据：≥ 4.5:1
- 说明：18 处文本对比度不足：div > div:nth-of-type(2) > span:nth-of-type(1) 2.38:1；div > div:nth-of-type(2) > span:nth-of-type(1) 2.38:1；div.stepside:nth-of-type(1) > div.step.todo:nth-of-type(10) > span.st 2.4:1；div.ccard:nth-of-type(1) > div.chead:nth-of-type(1) > span.cno:nth-of-type(1) 2.46:1；div.ccard:nth-of-type(2) > div.chead:nth-of-type(1) > span.cno 2.46:1

> 建议色是按当前色算出来的达标值（逐步加深直到越过判据线）。能用设计令牌（如 --color-text-muted）替代硬编码色值时优先用令牌，并把令牌本身提到达标值，而不是逐处覆盖。

```css
div > div:nth-of-type(2) > span:nth-of-type(1) {
  color: #3b3b3b; /* 2.38:1 → 4.7:1（判据 4.5:1） */
}
div.stepside:nth-of-type(1) > div.step.todo:nth-of-type(10) > span.st {
  color: #000000; /* 2.4:1 → 1.61:1（判据 4.5:1） */
}
div.ccard:nth-of-type(1) > div.chead:nth-of-type(1) > span.cno:nth-of-type(1) {
  color: #66696f; /* 2.46:1 → 4.91:1（判据 4.5:1） */
}
div.ccard:nth-of-type(2) > div.chead:nth-of-type(1) > span.cno {
  color: #66696f; /* 2.46:1 → 4.91:1（判据 4.5:1） */
}
div.ccard:nth-of-type(3) > div.chead:nth-of-type(1) > span.cno {
  color: #66696f; /* 2.46:1 → 4.91:1（判据 4.5:1） */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > div.cact:nth-of-type(3) {
  color: #66696f; /* 2.76:1 → 5.5:1（判据 4.5:1） */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > div.cact:nth-of-type(3) {
  color: #66696f; /* 2.76:1 → 5.5:1（判据 4.5:1） */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > div.cact:nth-of-type(3) {
  color: #66696f; /* 2.76:1 → 5.5:1（判据 4.5:1） */
}
div.step.todo:nth-of-type(10) > div.stx > div.stt:nth-of-type(1) {
  color: #000000; /* 2.87:1 → 1.35:1（判据 4.5:1） */
}
```

### [高] WCAG 2.5.8 目标尺寸（最小 24×24）（4 处）

- 位置：`div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(4)`
- 实测：75.56×18px
- 判据：≥ 24×24px（平台建议 ≥ 44×44px）
- 说明：4 个交互目标小于 24×24px：div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(1)(99.56×18)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(2)(99.56×18)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(3)(87.56×18)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(4)(75.56×18)

> 若必须保持小图标视觉尺寸，用伪元素扩大热区（::after { content: ""; position: absolute; inset: -13px; }），但父元素需 position: relative。

```css
div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(1) {
  min-width: 44px;
  min-height: 44px; /* 由 99.56×18 提升；命中区达标即可，图标视觉尺寸可不变 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(2) {
  min-width: 44px;
  min-height: 44px; /* 由 99.56×18 提升；命中区达标即可，图标视觉尺寸可不变 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(3) {
  min-width: 44px;
  min-height: 44px; /* 由 87.56×18 提升；命中区达标即可，图标视觉尺寸可不变 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(4) {
  min-width: 44px;
  min-height: 44px; /* 由 75.56×18 提升；命中区达标即可，图标视觉尺寸可不变 */
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
```

## 排版（2）

### [中] 正文字号下限（13 处）

- 位置：`div.step.todo:nth-of-type(10) > div.stx > div.ssub:nth-of-type(2)`
- 实测：10px
- 判据：≥ 12px（正文建议 ≥ 14px）
- 说明：13 处文本小于 12px，最小 10px：div.step.done:nth-of-type(1) > div.stx > div.ssub:nth-of-type(2)；div.step.done:nth-of-type(2) > div.stx > div.ssub:nth-of-type(2)；div.step.done:nth-of-type(3) > div.stx > div.ssub:nth-of-type(2)；div.step.done:nth-of-type(4) > div.stx > div.ssub:nth-of-type(2)

> 若为法律/次要标注等确需小字的场景，请在小字之上补足对比度（≥4.5:1）作为补偿。

```css
div.step.done:nth-of-type(1) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(2) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(3) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(4) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(5) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(6) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(7) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.done:nth-of-type(8) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.now:nth-of-type(9) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
div.step.todo:nth-of-type(10) > div.stx > div.ssub:nth-of-type(2) {
  font-size: 14px; /* 由 10px 提升 */
}
```

### [中] WCAG 1.4.12 文本间距（行高）（16 处）

- 位置：`div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > div.cact:nth-of-type(3)`
- 实测：line-height 1.2（13.2px / 11px）
- 判据：段落行高 ≥ 1.5；绝对下限 1.3
- 说明：16 处多行文本行高过紧，最紧 1.2：body > div.top:nth-of-type(1) > b；div.step.done:nth-of-type(1) > div.stx > div.ssub:nth-of-type(2)；div.step.done:nth-of-type(2) > div.stx > div.ssub:nth-of-type(2)；div.step.done:nth-of-type(3) > div.stx > div.ssub:nth-of-type(2)

> 行高用无单位数值（1.5）而非 px，避免子元素继承后被固定死。

```css
body > div.top:nth-of-type(1) > b {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(1) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(2) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(3) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(4) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(5) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.done:nth-of-type(6) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.now:nth-of-type(9) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.step.todo:nth-of-type(10) > div.stx > div.ssub:nth-of-type(2) {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.wb > div.carea:nth-of-type(2) > p.curhint {
  line-height: 1.5; /* 由 1.2 提升 */
}
```

## 交互与动效（1）

### [低] 点击目标（平台建议 44×44）（2 处）

- 实测：2 个目标 24–44px
- 判据：触屏场景 ≥ 44×44px（Apple HIG / Material）
- 说明：未达平台建议值（未违反 WCAG AA）：body > div.tabs:nth-of-type(2) > button.on:nth-of-type(1)(75×37)；body > div.tabs:nth-of-type(2) > button:nth-of-type(2)(62×37)

```css
/* 触屏断点内统一放大命中区 */
@media (pointer: coarse) {
  body > div.tabs:nth-of-type(2) > button.on:nth-of-type(1) {
    min-height: 44px;
  }
}
```

> 只在粗指针（触屏）下放大，桌面端保持信息密度。

## 间距节奏（1）

### [低] 间距基准网格（10 处）

- 实测：16 种间距值，其中 10 种非 4 的倍数
- 判据：≥ 2/3 的间距值落在 4px（或 8px）网格上
- 说明：间距缺少基准网格，视觉节奏会显得随意：非网格值 1px、2px、3px、6px、9px、10px、11px、14px

```css
:root {
  --space-1: 4px;
  --space-2: 8px;
  --space-3: 12px;
  --space-4: 16px;
  --space-6: 24px;
  --space-8: 32px;
}
```

> 先定义阶梯，再把散落值吸附到最近的阶梯（13px → 12px，27px → 24px）。

## 色彩（1）

### [低] 文本色数量

- 实测：17 种文本色
- 判据：≤ 6–8 种（含语义色）
- 说明：文本色过多会削弱层级表达：rgb(232, 236, 242)、rgb(143, 183, 232)、rgb(32, 37, 44)、rgb(185, 194, 206)、rgb(125, 195, 131)、rgb(255, 255, 255)、rgb(95, 107, 123)、rgb(122, 130, 142)、rgb(151, 156, 165)、rgb(27, 102, 201)

```css
:root {
  --text-primary: #1a202c;
  --text-secondary: #4a5568;
  --text-muted: #718096;
  --accent: #2b6cb0;
  --danger: #c53030;
  --success: #2f855a;
}
```

> 色板收敛到"层级 + 语义"两类；数量本身不是错，无体系才是。

## 布局（1）

### [高] 横向溢出（移动端必修）（40 处）

- 位置：`div.carea:nth-of-type(2) > div.cands:nth-of-type(2) > div.ccard:nth-of-type(2)`
- 实测：内容宽 543px > 视口 390px，最大越界 153px
- 判据：scrollWidth ≤ clientWidth（无横向滚动）
- 说明：页面出现横向滚动，越界元素：#carea(+153px)；div.wb > div.carea:nth-of-type(2) > div.curhead:nth-of-type(1)(+153px)；div.carea:nth-of-type(2) > div.curhead:nth-of-type(1) > b(+82.77px)；div.wb > div.carea:nth-of-type(2) > p.curhint(+153px)

```css
div.carea:nth-of-type(2) > div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) {
  max-width: 100%;
  /* 固定像素宽是常见元凶：改用相对单位或 min() */
  width: min(100%, 1200px);
}

/* 兜底自检：临时给全部元素加 outline 可定位越界者 */
/* * { outline: 1px solid red; } */
```

> 排查顺序：固定 px 宽 → 负 margin → 100vw（含滚动条）→ 长英文/URL 不换行（加 overflow-wrap: anywhere）。

## 未覆盖

- 审美与视觉层级（需要模型看图判断，不在确定性判据内）
- 真实交互态（hover / focus / disabled 的视觉表现）
- 内容与信息架构（文案质量、流程合理性）
- 性能指标（LCP/CLS 需真实采样，本工具只检查图片尺寸预留这类静态风险）
