# 设计审查报告

- 目标：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\examples\workbench.html`
- 生成时间：2026-10-23T12:41:40.032Z
- 视口：1440×900、390×844
- 渲染引擎：Chrome/155.0.8059.82
- 问题总数：**2**　高 1｜中 1

## 截图（供视觉复核）

- w1440：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-204127-workbench-final\w1440.png`
- w390：`C:\Users\admin\.claude\skills\flow-line-cy-design-system-generator\.design-audit\20261023-204127-workbench-final\w390.png`

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
div.step.todo:nth-of-type(10) > div.stx > div.stt:nth-of-type(1) {
  color: #000000; /* 2.87:1 → 1.35:1（判据 4.5:1） */
}
div.step.todo:nth-of-type(10) > div.stx > div.ssub:nth-of-type(2) {
  color: #000000; /* 2.87:1 → 1.35:1（判据 4.5:1） */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(1) > div.cact:nth-of-type(3) {
  color: #6a717b; /* 3.11:1 → 4.93:1（判据 4.5:1） */
}
div.cands:nth-of-type(2) > div.ccard:nth-of-type(2) > div.cact:nth-of-type(3) {
  color: #6a717b; /* 3.11:1 → 4.93:1（判据 4.5:1） */
}
```

## 排版（1）

### [中] WCAG 1.4.12 文本间距（行高）（2 处）

- 位置：`div.wb > div.carea:nth-of-type(2) > p.curhint`
- 实测：line-height 1.2（14.4px / 12px）
- 判据：段落行高 ≥ 1.5；绝对下限 1.3
- 说明：2 处多行文本行高过紧，最紧 1.2：body > div.top:nth-of-type(1) > b；div.wb > div.carea:nth-of-type(2) > p.curhint

> 行高用无单位数值（1.5）而非 px，避免子元素继承后被固定死。

```css
body > div.top:nth-of-type(1) > b {
  line-height: 1.5; /* 由 1.2 提升 */
}
div.wb > div.carea:nth-of-type(2) > p.curhint {
  line-height: 1.5; /* 由 1.2 提升 */
}
```

## 未覆盖

- 审美与视觉层级（需要模型看图判断，不在确定性判据内）
- 真实交互态（hover / focus / disabled 的视觉表现）
- 内容与信息架构（文案质量、流程合理性）
- 性能指标（LCP/CLS 需真实采样，本工具只检查图片尺寸预留这类静态风险）
