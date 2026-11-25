# 项目 profile 登记：mall（商城专项）

- **profile id**：`mall`（构建参数 `--profile mall`；机器可读登记见同目录 [mall.json](<mall.json>)，注入配置以该文件为唯一权威）
- **状态**：registered-placeholder（已登记，规则未迁移）
- **默认**：**不启用**。`--profile` 缺省为 `none`，不注入任何专项；专项是否启用属于项目配置，只按显式参数启用——绝不按页面内容/home/category/cart/profile 等同名 id 自动判定（任务书 §3-C06）。
- **登记人/日期**：T01（运行时集成人R）／2026-11-01
- **规则迁移责任**：T03/T04/T07。本轮只建立 profile 机制与登记文件；**不改 seed 与 chooser 本身**（商城规则在 seed/chooser 中的移除属 T03/T04 范围）。

## 1. 这是什么

机械配件商城项目遗留的专项规则集合。历史上这些规则直接长在 seed 与 style-chooser 里，导致"任何新项目都隐式携带商城规则"。本轮起：通用装配不带专项；需要商城效果的旧/新项目，构建时显式 `--profile mall`，装配只注入规则标记占位（CSS 变量 `--project-profile:mall` + 类开关 `prototype-profile-mall`），真实规则待迁移后挂在该开关之下。

## 2. 规则来源（本轮只读登记，行号为文件 `\n` 口径）

### 2.1 seed 侧：editor-seed.html:658-682（屏幕选择器族）

四商城主导航页的 mobile 固定壳与吸底规则，前缀统一为
`body #canvas .screen:is([data-screen="home"],[data-screen="category"],[data-screen="cart"],[data-screen="profile"]):not([data-layout="free"]):not(:has(.free-canvas)) > .device.mobile`：

| 目标 | 效果 |
|---|---|
| `> .device.mobile`（本体） | height/min-height 812px !important |
| `> .device.mobile > .viewport` | height 100%、min-height 0、overflow hidden（滚动收纳进 app） |
| `> .device.mobile > .viewport > .app` | flex:1 1 0、min-height 0、overflow auto、padding-bottom 0、scrollbar-width none |
| `… > .app::-webkit-scrollbar` | display:none |
| `… > .app > *` | flex-shrink:0 |
| `… > .app > .tabbar` | sticky 吸底 height 56px、z-index 40 |
| `screen[data-screen="cart"]` 变体 `… > .app > [data-eid="cart-settle-bar"]` | sticky bottom:56px、margin-top:auto |
| `screen[data-screen="cart"]` 变体 `… > .app > .tabbar` | margin-top:0 |

### 2.2 chooser 侧：style-chooser.js（mall 选择器族，运行时注入 CSS）

| 组 | 选择器 | sc 行 |
|---|---|---|
| overlay 根 | `.mall-modal` | 24 |
| 背景族 | `.mall-content`、`.mall-admin`、`.mall-admin-main` | 31 |
| 导航族（含 dark 变体 sc:65） | `.mall-bottom`、`.mall-admin-top` | 32 |
| 卡片族 | `.mall-product`、`.mall-cart-line`、`.mall-order-card`、`.mall-address`、`.mall-manual`、`.mall-record`、`.mall-table-wrap`、`.mall-table-scroll`、`.mall-cart-summary`、`.mall-grid-form`、`.mall-stats>div`、`.mall-chat .bubble` | 33 |
| 文本/边框族 | `.mall-product-info`、`.mall-summary` | 34 |
| 圆角族 | `.mall-field input/select/textarea`、`.mall-history button`、`.mall-cart-ops button` | 35-36 |
| 强调族 | `.mall-methods .b.selected`、`.mall-chat .bubble.mine` | 40 |
| **间距专项（冻结单 §4 点名）** | `.mall-content`（padding `p.space` + gap `max(10, p.space-2)`） | **44** |
| hero 族（白字 sc:46、sc:66） | `.mall-hero`、`.mall-profile`、`.mall-wallet`、`.mall-poster`（及 h1/p/strong） | 45-47 |
| 侧栏族 | `.mall-admin-side`、`.side`（及子件 hover/on 态） | 48-50 |
| 表格族 | `.mall-admin table/th/td` | 51 |
| 杂项 | `.mall-stats>div`、`.mall-chart>div`、`.mall-badge`、`.mall-detail-image`、`.mall-cart-line img`、`.mall-product img`、`.mall-price`、`.mall-detail-price`、`.mall-note`、`.mall-product-info small`、`.mall-sub`、`.mall-field`、`.mall-history` | 53-60 |
| 示例文案 | 预设卡片「商城 · 商品列表」（chooser 资产，归 G/T03，仅登记） | 76 |

## 3. 构建期注入契约（本轮实现）

`--profile mall` 时，compose 在 `</head>` 前注入**恰一次**受控块（重复/缺失＝具名失败）：

```html
<style id="project-profile-css" data-project-profile="mall">/*PROJECT_PROFILE:mall*/ :root{--project-profile:mall;}.prototype-profile-mall{/* placeholder: 专项规则迁移属 T03/T04/T07，清单见 assets/project-profiles/mall.md */}</style>
```

- 默认构建（`--profile none`/缺省）：不注入该块；产物中不存在 `project-profile-css` / `data-project-profile` / `PROJECT_PROFILE:` 标记。
- 受控块唯一校验：`build.check_controlled_blocks` 对全部装配注入块（prototype-config、FREE_EDITOR/FREE_STYLE、本块等）执行"恰一次"断言，重复或缺失即 ValueError（退出码 2）。
- 真实规则迁移（T03/T04/T07）落点：以 `--project-profile` 变量与 `html.prototype-profile-mall` 类开关承载上表规则，替换 seed/chooser 中的原位实现；迁移完成前，chooser 运行时字符串中的 mall 选择器仍存在（如实声明，不假称已清除）。
