# 动效图标工作流（wf-motion）

场景：图标需要动效（加载旋转/成功打勾/心跳呼吸/微交互反馈）。

## 决策树

```
动效需求进来
├─ hover 物体动效（文件夹打开/信封掀盖/日历翻页——物体本身会做的动作，悬停触发）
│    → **kubai 路径**：先检索静态帧（漏斗同 wf-icons），缺图标走程序化生成；
│      交付「交互 SVG 组件」（内联引擎自包含片段或官方 react/vue 包，
│      见 wf-icons §程序化生成第 4 步）——不是本文件的手写 SMIL/CSS
├─ 简单动效（旋转/脉冲/打勾描画/摇摆——单属性变化，无图层编排，加载/反馈循环类）
│    → 本技能手写，交付内联动图 SVG（SMIL 或 CSS，见下表）
├─ 复杂动画（≥2 图层编排 / 路径变形 / 逐帧 / 复杂缓动曲线 任一）
│    → 转交 solo-img-line-cy-lottie-json 技能（Lottie JSON；注意：网页消费需宿主引
│      lottie-web 播放器——与"产物零依赖"冲突时优先拆解为简单动效组合）
└─ 上游要自己可视化调 3D 材质/角度 → 告知 app.3dicons.co 的 3D 重调工具
   （仅调材质角度、导出 PNG，**不做动画**）；SVG 动画可视化编辑可用
   LottieFiles 等第三方编辑器（人工工具，AI 不驱动）
```

## 简单动效：SMIL / CSS 两选一

| 场景 | 用 | 理由 |
|---|---|---|
| 图标内嵌在单文件 HTML、需跟随主题色 | **CSS animation**（`@keyframes` + class） | 宿主有 CSS 上下文，媒体查询可用 |
| 图标需独立分发（单独一个 .svg 文件 / `<img>` 嵌入） | **SMIL**（`<animateTransform>` 内嵌 SVG，同样支持 currentColor） | 自包含；注意 SMIL 不响应 prefers-reduced-motion（见下方纪律） |
| 独立 .svg 又需要 reduced-motion | **`<style>` 内嵌进 .svg 文件**（自包含且支持 @media 的第三方案） | 兼得自包含与无障碍 |

## 常用模板

```html
<!-- CSS 脉冲（呼吸感，通知/状态点） -->
<svg class="ic-pulse" viewBox="0 0 24 24">...</svg>
<style>
.ic-pulse{animation:icPulse 1.6s ease-in-out infinite}
@keyframes icPulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.55;transform:scale(.92)}}
@media (prefers-reduced-motion: reduce){.ic-pulse{animation:none}}
</style>

<!-- CSS 旋转（加载态） -->
.ic-spin{animation:icSpin 1s linear infinite}
@keyframes icSpin{to{transform:rotate(360deg)}}

<!-- SMIL 打勾描画（成功反馈，stroke-dashoffset 动画内嵌 SVG 自包含） -->
<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round">
  <path d="M4 12.5l5 5L20 6.5" stroke-dasharray="30" stroke-dashoffset="30">
    <animate attributeName="stroke-dashoffset" from="30" to="0" dur="0.45s" fill="freeze"/>
  </path>
</svg>
```

## reduced-motion 纪律

1. **CSS 交付**：交付块必须附 @media 降级，选择器**枚举实际交付类名**（如 `.ic-pulse,.ic-spin{animation:none}`）——禁止 `.ic-*` 通配写法（非法选择器，整条规则被浏览器静默丢弃）
2. **SMIL 交付**：不响应媒体查询——需 reduced-motion 的宿主改用 `<style>` 内嵌 .svg 方案或 CSS 内联（见上表第三行）
3. **单文件纪律**：CSS 动画的 keyframes 必须随交付块一起给（内嵌产物用）
4. **动效图标也是图标**：台账登记同 wf-icons，来源标"手写动效"或"库图标+动效改编"
5. 溢出场景（多图层编排/Lottie 导出）转 solo-img-line-cy-lottie-json，不硬写
