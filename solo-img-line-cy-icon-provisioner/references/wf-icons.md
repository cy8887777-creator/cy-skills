# 单图标 / 批量图标工作流（wf-icons）

需求档位：简单档走 §快速路径；复杂档走 §全流程。档位判定标准见 onboarding.md §复杂度分级（语义常见+常见风格族+≤10 = 简单档）。

## 快速路径（简单档，目标分钟级）

```
1. 风格族 → 库白名单（查 sources.md §风格族→库白名单映射，通常锁定 1-3 库）
2. 语义关键词 → 本地检索：python scripts/iconify_fetch.py --search <关键词> --prefix <白名单前缀>
3. 命中（语义与风格族双匹配）→ 代码读形确认 → 适配 → 交付
4. 未命中 → 升级复杂档（见下方升级规则）
```

跳过需求单全套冻结（三最小字段+规格默认值即可）、跳过网格批审——**简单需求不做全套流程**。

**代码读形确认**：读 SVG 源码判形态（stroke-width→线性粗细 / fill→剪影 / path 数→细节度）。确认不过 → 换同库次候选重判；**连败 2 次 → 升级复杂档**。

## 全流程（复杂档）

**入口前置**：从快速路径升级上来时，先补齐需求单并冻结（已确认面不重问，规格可用默认值），然后从步骤 1 开始；直接复杂档需求从 I1 冻结后进入。

### 步骤 1：供给路由（I2）

按序尝试，命中即停（**命中 = 语义与风格族双匹配**——cache/ 本地库里语义命中但风格族不符的图标不算命中，禁止塞违和图标）：
1. 本地 `assets/icons-json/<prefix>.json`（`iconify_fetch.py --search <关键词> --prefix <白名单>` 查询键名）
2. `cache/`（历史取用沉淀——命中同样要过形态自检）
3. Iconify API（`iconify_fetch.py --fetch prefix:name`，命中自动落 cache）
4. 3dicons.co（仅质感变体档，见 wf-genicon.md）

### 步骤 2：视觉确认漏斗（I3，候选 ≥2 时必走；候选 =1 也须代码读形确认）

```
① 库白名单过滤     风格族 → 1-3 库（零成本砍 90%）
② 名字检索         白名单内语义关键词检索（毫秒，输出候选名单）
③ 分流判定：
   候选 ≤5 且"代码可判"（path ≤3 且无 clip/mask 嵌套）→ 直接读 SVG 源码定性
   候选多或含复杂结构（多 path/嵌套 clip/mask）→ render_grid.py 网格图批审
④ 模糊需求         → 网格图交上游挑（附推荐与理由）；明确需求 → AI 定 + 理由写进交付单
```

**成本红线**：10 个图标需求 ≈ 30 候选 ≈ 2-3 张网格图——禁止逐个图标视觉比对。

### 步骤 3：适配加工（I4）

- 改色：线性图标把 `stroke` 换 `currentColor`（跟随主题）或指定色；剪影同理改 `fill`。⚠ **kubai 两库例外**——分层库渐变/推导色禁 currentColor 替换（走引擎 `--accent` 重渲染），duotone 走双 hex 替换（见 sources.md §kubai 家族「改色特殊路径」），需求单风格族命中 kubai 系时先读那节再动手
- 描边对齐：统一 `stroke-width` 到需求单规格（1.5/1.8/2）
- 尺寸：`width`/`height` 按需求单；viewBox 保持原库
- 位图（3dicons PNG 等）：下载透明底 PNG → 压缩 → base64 `data:image/png` 内嵌（位图图标的交付加工属本技能范围，见 SKILL.md 边界豁免）
- 多图标：统一规格后合并 SVG sprite（`<symbol id="ic-xxx">` + `<use href="#ic-xxx">`）。例外：kubai-duotone 图标跨图标共用短 id（d-g1 等），sprite 合并前必须先做 id 唯一化（见 sources.md §kubai 家族），否则逐个内联

### 步骤 4：交付 + 验收（I5）

按 demand-sheet.md 交付单。验收逐面回查需求单 + emoji 扫描交付产物（正则 `[\u{1F000}-\u{1FAFF}\u{1FB00}-\u{1FBFF}\u{2600}-\u{27BF}]`；装饰纹样 ✦✧ 豁免需逐个人工判定）零命中。

**验收闭环**：FAIL → 回步骤 3 修正重验；二次 FAIL → 转未命中交付单。**部分命中**（N 个需求命中 M<N）→ 先交已命中 M 个 + 附未命中单（对缺失位走五处置），处置后补交剩余——不等全量。

## 失败处置（全链路未命中时）

按 demand-sheet.md「未命中交付单」输出五处置选项（a 用候选 / b 手绘定制 / c 改语义 / d 生图提示词包 / e 程序化生成）。其中选项 d 的组装规则见 wf-genicon.md §提示词包；选项 e 的完整流程见下方 §程序化生成。

**kubai 系直达**：需求单风格族为「动态质感」或点名 kubai/分层动态/双色面性（kubai 档）时，白名单检索未命中即直接走 §程序化生成，不必先过 a-d。

## 程序化生成（处置 e）

用本地引擎 `assets/engines/kubai-icons/`（官方 Kubai Icons skill 原样副本）按需现画：分层动态风格（渐变分层+外描边+悬停形变）或双色面性（16 网格）。上游方法论以其自带文档为准（SKILL.md + PROMPT.md），本节只写编排与边界。

**环境探测**（三者在场才可生成；缺任一 → 降级处置 d 生图，并在交付单如实报原因）：
1. `assets/engines/kubai-icons/SKILL.md` + `src/engine.js` + `scripts/check.mjs` 存在
2. Node ≥18（`node -v`）
3. Chrome 无头可用：`scripts/check.mjs` 只自动探测 Chrome 固定安装路径；仅装 Edge 的机器设环境变量 `CHROME` 指向 msedge.exe（playwright chromium 亦可）

**流程**（分双色面性时先读 `styles/duotone/SKILL.md`，其余读根 `SKILL.md` + `PROMPT.md`）：
1. 复制引擎副本到工作区：`cp -r assets/engines/kubai-icons <工作区>/kubai-work`——工作区用需求单关联的产物目录或 `%TEMP%/icon-provisioner-work/<需求单号>/`；**禁止在 engines/ 原目录内写画**（保原样性），完工清理副本
2. 按其 SKILL.md 流程画新图标：功能 → 一句「物体隐喻+悬停动作」→ 读 `src/icons.js` 里结构最接近的范例 → 追加新图标 → 加进 `src/app.js` 的 `ORDER`。**图标名以 `src/icons.js` 的 `name` 字段为准**（发行包范例为中文命名：'文件夹''邮件''下载'…），`--only`/`--with` 都传这个名
3. 自检：`node scripts/check.mjs --only 新图标名 --with 邮件,下载`——**验收标准：findings.md 无未声明问题项（allow 声明除外）+ 截图过 I3 目检；不达标回改，禁止跳检交付**
4. 导出交付件（**供给菜单 + 推荐，上游拍板**；自动化流程按目标环境自决策并把依据写进交付单）：
   - **静态 SVG** —— 推荐：切图/Figma/文档/原生 App（哪里都能用，不会动）
     `node scripts/export.mjs --only 新图标名 --out <交付目录>` → 独立 SVG，不依赖脚本/样式表
   - **交互 SVG 组件** —— 推荐：网页/H5/React/Vue（hover 会动，物体做自己的动作）
     单文件自包含 HTML 片段：SVG 容器 + 内联 `src/engine.js`（~14KB，多图标共享一次）+ 图标定义 + 事件绑定（**鼠标 hover + 键盘 focus + 触屏/笔 click 切换**——hover 是鼠标语义，触屏用户必须有点击兜底，交付单注明此差异）；无外部链接（符合硬规矩 3）。
     ⚠ **图标定义先查官方定义库再考虑现画**：`assets/engines/kubai-icons-definitions.js`（MIT，967 基础物体，全局 `KUBAI_LIB.ICONS['英文名']`，与 mountIcon 同构）——
     命中 → 内联 bundle + 取定义，**零生成**（官方质感最优）；未命中 → 才按本节流程现画。
     这就是「半命中」场景的正解：静态库命中 ≠ 可交互（静态是死帧），引擎 66 范例 ≠ 全量（只是教材），官方定义库才是交互组件的第一供给。
     注意：静态库 2800+ 含角标变体（folder-plus 等），bundle 只有 967 基础物体——带角标的语义静态直接交付，交互组件官方无定义时走现画并如实告知。
   - **官方框架包** —— 推荐：React/Vue 项目用官方库既有图标（新画的图标不在包里，走前两路）
     React `npm i kubai-icons-react`、Vue `npm i kubai-icons-vue`（均 MIT），交付时告知包名与用法
5. 回 I4/I5：按需求单适配规格 → 交付单许可行如实标注「生成引擎 Kubai Icons License (source-available)；产物图标归需求方，无需署名」

**许可边界（必守）**：
- `assets/engines/kubai-icons/` 逐字节原样（落地时已 diff 核验），禁改内容/禁改名/禁删许可声明；更新只能整包替换官方 release zip 后重新 diff
- 对上游交付：只交导出的 SVG；引擎文件随客户项目分发仅限其 LICENSE §3 清单（src/engine.js、src/icons.js、src/app.js、index.html、scripts/），且项目内不得含 PROMPT.md/SKILL.md 或其改编文本；styles/duotone/ 不在 §3 清单，双色引擎不出我方工作区、只交导出件
- 本技能若商业化售卖，必须剔除 engines/ 改为引导用户自装（官方 README 有现成安装指令）

## 批量需求（N > 10）

- 先分组：按风格族/语义域分组，每组走一遍漏斗（复用库白名单）
- **批量台账**：组号 / 图标位 / 状态（路由中 / 审图中 / 适配中 / 已交付 / 未命中）——断点续作依据
- **分组分批交付**：允许部分组先交付；未命中组走五处置不阻塞其他组
- 交付 sprite 化：全部内联单文件会膨胀时，交付 `<symbol>` 集中定义 + `<use>` 引用
