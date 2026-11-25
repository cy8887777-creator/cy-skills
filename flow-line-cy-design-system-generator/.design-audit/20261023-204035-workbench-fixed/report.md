# 设计审查报告

- 目标：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\examples\workbench.html`
- 生成时间：2026-10-23T12:40:48.817Z
- 视口：1440×900、390×844
- 渲染引擎：Chrome/155.0.8059.82
- 问题总数：**6**　高 1｜中 2｜低 3

## 截图（供视觉复核）

- w1440：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-204035-workbench-fixed\w1440.png`
- w390：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-204035-workbench-fixed\w390.png`

## 无障碍（1）

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

## 排版（2）

### [中] 正文字号下限（3 处）

- 位置：`div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > div.cact:nth-of-type(3)`
- 实测：11px
- 判据：≥ 12px（正文建议 ≥ 14px）
- 说明：3 处文本小于 12px，最小 11px：div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > div.cact:nth-of-type(3)；div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > div.cact:nth-of-type(3)；div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > div.cact:nth-of-type(3)

> 若为法律/次要标注等确需小字的场景，请在小字之上补足对比度（≥4.5:1）作为补偿。

```css
div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > div.cact:nth-of-type(3) {
  font-size: 14px; /* 由 11px 提升 */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > div.cact:nth-of-type(3) {
  font-size: 14px; /* 由 11px 提升 */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > div.cact:nth-of-type(3) {
  font-size: 14px; /* 由 11px 提升 */
}
```

### [中] WCAG 1.4.12 文本间距（行高）（5 处）

- 位置：`div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > p.cdesc`
- 实测：line-height 1.2（14.4px / 12px）
- 判据：段落行高 ≥ 1.5；绝对下限 1.3
- 说明：5 处多行文本行高过紧，最紧 1.2：body > div.top:nth-of-type(1) > b；div.wb > div.carea:nth-of-type(2) > p.curhint；div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > p.cdesc；div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > p.cdesc

> 行高用无单位数值（1.5）而非 px，避免子元素继承后被固定死。

```css
body > div.top:nth-of-type(1) > b {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.wb > div.carea:nth-of-type(2) > p.curhint {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > p.cdesc {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > p.cdesc {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(3) > p.cdesc {
  line-height: 1.5; /* 由 1.2 提升 */
}
```

## 交互与动效（1）

### [低] 点击目标（平台建议 44×44）（6 处）

- 实测：6 个目标 24–44px
- 判据：触屏场景 ≥ 44×44px（Apple HIG / Material）
- 说明：未达平台建议值（未违反 WCAG AA）：div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(1)(103.56×27)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(2)(103.56×27)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(3)(91.56×27)；div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(4)(79.56×27)

```css
/* 触屏断点内统一放大命中区 */
@media (pointer: coarse) {
  div.top:nth-of-type(1) > span.rawlinks:nth-of-type(5) > a:nth-of-type(1) {
    min-height: 44px;
  }
}
```

> 只在粗指针（触屏）下放大，桌面端保持信息密度。

## 间距节奏（1）

### [低] 间距基准网格（10 处）

- 实测：16 种间距值，其中 10 种非 4 的倍数
- 判据：≥ 2/3 的间距值落在 4px（或 8px）网格上
- 说明：间距缺少基准网格，视觉节奏会显得随意：非网格值 2px、3px、5px、6px、9px、10px、11px、14px

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

## 未覆盖

- 审美与视觉层级（需要模型看图判断，不在确定性判据内）
- 真实交互态（hover / focus / disabled 的视觉表现）
- 内容与信息架构（文案质量、流程合理性）
- 性能指标（LCP/CLS 需真实采样，本工具只检查图片尺寸预留这类静态风险）
