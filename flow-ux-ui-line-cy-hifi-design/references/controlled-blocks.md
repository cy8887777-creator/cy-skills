# 受控块 schema（controlled-blocks）

> **V06 归属：附加A（转化可编辑版）专用**——编辑器直出线已随 V06 退役，本文件仅在阶段7 转化线使用；主流程（阶段1-6）不消费本文件。

换肤模块四受控块的格式契约。生成时（U2/U3）产出、构建注入产物、编辑器面板读取、K2 迁移校验——四方共同依赖本文件。

## 通则

- 受控块以 HTML 注释围栏落在交付 HTML 的配置区，格式对齐 K2 迁移范式（预检不符=具名拒绝，exit 1 零产出）；
- 每块首行带 `schemaVersion`，升级走 migrate 路线，禁原地手改；
- STYLE-PACK 一围栏多包：本产物全部皮肤包（所有族）都在 `packs` 数组里，四类围栏各恰 1（对齐 K2 六受控块各恰 1 惯例）；
- 生成侧（AI）只负责**内容**，块的包裹与落位由 build.py 注入；
- **围栏形态契约（冻结三形态，消费侧=chooser/readComponentPack/verify_blocks 三处照此实现）**：① HTML 注释 `<!-- NAME:BEGIN/END -->`；② `<script data-block="NAME">`（type=application/json **可省**——门禁从宽对齐面板，防产/检两判分叉）；③ JS 注释 `/*NAME_START*/…/*NAME_END*/`。识别优先级①>②>③，同一块多形态并存=违规；
- 校验器（丁线）按本文件逐块断言：块存在 / JSON 可解析 / 必填字段齐 / 引用闭合（PACK 引用的 family 必须在 REGISTRY）。

## 1. STYLE-REGISTRY（族登记 + 皮清单）

> **多成员口径（2026-11-23，v2 屏集合组）**：`domBases`/`families`/packs 支持多成员——单文件多风格（构建时 N 风格、事后回装）按 `multi-style-spec.md` 执行：domBaseId/familyId/packId 全局唯一、families 每族挂一个 domBaseId；页面 DOM=每风格一套 `section.screen` 屏集合（每屏挂 `data-style-id="<风格id>"`，值域=domBaseId；屏内单容器，v1 的屏内 `[data-dom-base]` 双容器已废弃）；页数跨风格可不守恒；`pageTree` 为 `{风格id:{屏id:组名}}` 分组表。本节示例为单成员最小形态。

```json
{
  "schemaVersion": 1,
  "domBases": [
    { "domBaseId": "db-main", "note": "主骨架（选中方向生长）", "pages": ["home","list","detail"] }
  ],
  "families": [
    {
      "familyId": "fam-1",
      "domBaseId": "db-main",
      "label": "同族·紧凑档",
      "members": ["pack-ant-primary", "pack-ant-loose", "pack-ant-warm"],
      "note": "AI 生成时现场判定：骨架相同=同族；跨族不进本块（走生成级出口）"
    }
  ]
}
```

- 族=骨架一样的集合，唯一判据；AI 现场判（四个方面逐个风格列给用户确认，见 editor-runtime.md「AI 判族」），判完落此表，**不建机械判定**；
- 用户选中的同骨架风格全部进族，成员数不设上限；AI 另外每族顺手送 1-2 个同族变体。

## 2. STYLE-PACK（皮肤包 ×N）

```json
{
  "schemaVersion": 1,
  "packs": [
    {
      "packId": "pack-ant-primary",
      "familyId": "fam-1",
      "identity": { "styleId": "wiki:antd", "styleName": "Ant Design", "origin": "wiki|ai-generated", "mood": "一句话情绪" },
      "screenshot": "data:image/png;base64,…（可选：首页按包渲染截帧，面板卡片真图缩略；缺省=色板条降级）",
      "tokens": { "primary": "#1677ff", "text-primary": "#1f2329", "radius-md": "8px", "space-2": "12px", "size-ctl-md": "36px", "weight-head": "600", "…": "最小集全量展开 + 扩展参数；键名逐字照 assets/token-keys.json，U2 只扩不改 picker 已锁值" },
      "palettes": [
        { "paletteId": "pal-default", "label": "默认", "swatches": ["#1677ff","#e6f4ff","#333","#f5f5f5"] },
        { "paletteId": "pal-blue", "label": "国际蓝", "hero": "#0047BB", "swatches": ["#0047BB","#f4f6fa","#10131a","#ffffff"] },
        { "paletteId": "pal-dark",   "label": "暗色", "swatches": ["…"] }
      ],
      "iconSet": "lucide-line",
      "l2Overrides": [ { "selector": ".card", "props": "…按组件类重写外观的 CSS 片段…" } ]
    },
    { "packId": "pack-ant-loose", "familyId": "fam-1", "…同族另一个包，字段同上…" }
  ]
}
```

- `tokens` 即 L1：**键名逐字照正本表 `assets/token-keys.json`**（一律全小写连字符；表里每个键都写明运行时把它送到哪个变量）；表外键=扩展参数，同样全小写连字符，运行时生成 `--sp-<键名>`；`l2Overrides` 即 L2（按组件类覆盖）；`iconSet` 指向 L3 图标族（sprite 显隐由运行时按包切换）；
- **`l2Overrides` 的 selector 写页面内的组件类**（如 `.app`、`.card`）：运行时会自动加上页面容器与风格包前缀，所以写 `:root`/`html`/`body` 永远匹配不到；`props` 是完整的 CSS 声明串；
- 配色胶囊读 `palettes`（色板级=最便宜的切换）：**品牌色盘那一版必须有，放第一套作默认；另按该风格的气质再配几套合适的，每包至少 2 套**——锁了品牌色只是说必须有这一版，不代表只有这一版；
- **palette 可选字段 `hero` / `line` / `muted`**（换配色全角色跟随，运行时 paletteColors 推算）：
  `swatches` 固定四槽语义 [0]主色 [1]底色 [2]文字 [3]表面；写了 `hero`/`line`/`muted` 就全用写的；
  没写则推算——line/muted 沿包「底色×文字」连线按包原值位置重映射到配色空间（包特征色不在线上则保留包值），
  hero 按包 hero 来历跟随（缺省=主色系→配色主色；中性色如瑞士黑块→配色文字色；独立色→保留包值）；
  浅衬底(--style-soft)=配色主色极淡色，按钮文字按配色主色亮度定深浅；
  暗色组恒取包值（暗底必须配浅文字，不做自动反推）。

## 3. COMPONENT-PACK（组件包）

```json
{
  "schemaVersion": 1,
  "packFor": "pack-ant-primary",
  "components": [
    { "compId": "stat-card", "name": "统计卡", "html": "…结构片段（data-eid 齐备）…", "tokenRefs": ["primary","radius-md"]（口径=所属包 tokens 键名逐字，见 component-pack-spec §二.3） }
  ]
}
```

- U2 生成时顺手产 10-15 个带当前风格的高频组件（卡片/按钮组/表单块/列表/统计块/图文块）；
- 编辑器组件面板读包：**无包回退内置中性组件**（降级契约，面板不得空转）；
- 组件结构必须遵守 editor-runtime 页面片段契约（data-eid/data-block，禁 script）。

## 4. STYLE-CONTRACT（结构契约）

```json
{
  "schemaVersion": 1,
  "domBaseId": "db-main",
  "styleOrigin": { "styleId": "wiki:antd", "mood": "…" },
  "pages": [
    { "pageId": "home", "form": "枢纽 Hub", "regions": [ {"region":"导航区","shape":"bar","count":1}, {"region":"卡片流","shape":"card","count":4} ] }
  ],
  "motion": { "tier": "b", "tokens": { "duration": "…", "easing": "…" } },
  "density": "high"
}
```

- 骨架描述=AI 生长产物的结构化记录（可渲染即结构化）；`form/regions` 词汇**开放**（extract 九类仅参考，禁套用）；
- 外置技能（style-reskin，P3 后）以本块为作业依据。

## 与既有体系的关系

- 九槽（style-presets.json）：仅作 picker 缺位时的兜底候选源；正式流程走 picker 回传，U2 令牌来源=回传的 skeletonTokens 展开全量；
- editor-runtime「风格令牌应用」节同步扩域（颜色/字号/圆角/阴影之外，加间距/内边距/控件尺寸/列数/gap——禁自创硬值），白名单依据=正本表 assets/token-keys.json。
