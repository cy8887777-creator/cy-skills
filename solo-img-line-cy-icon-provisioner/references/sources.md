# 供给源清单与风格档案（sources.md）

## 本地 JSON 库清单（assets/icons-json/，离线主力）

> 落地状态（2026-11-23 更新）：**43 库 · 174,887 枚 · ~159MB 全部落地**
> 来源：40 库 = @iconify/json 2.2.553 官方整包（枚数/许可以盘上元数据核对无误）；nieobie-game-pack = GitHub Nieobie/Game-Icon-Pack 本地编译；kubai 两库 = npm kubai-icons-static@0.14.0 拍平（见 §kubai 家族）
> 许可总况：**全部可商用**；game-icons 与 solar 为 CC BY（需署名，⚠ 标记）
> 每库一个 `<prefix>.json`（Iconify 官方格式，body 内嵌 SVG path 本体）
> 实测注意：ph.json（9,161 枚）4.4MB，**Windows PowerShell 5.1** 的 ConvertFrom-Json 有 2MB 长度上限，PS7 或 python 标准库无此限

### 第一梯队（风格主干）

| prefix | 枚数 | 许可 | 风格档案（风格族关键词） |
|---|---|---|---|
| iconmind | 31,722 | MIT | UI 24px 大而全；**线性+面性双系**；密度中等 |
| fluent | 20,334 | MIT | 微软 Fluent；圆角线性/面性；企业现代感 |
| material-symbols | 16,475 | Apache | Google Material 变体家族（含多色层） |
| withicons | 7,000 | MIT | withicons 家族基础版；线性/面性 |
| tabler | 6,305 | MIT | 线性大库，描边 1.5/2 |
| hugeicons | 6,091 | MIT | UI 线性变体；干净锐利 |
| mingcute | 4,542 | Apache | 圆角可爱系；中文设计圈主流 |
| game-icons ⚠署名 | 4,134 | CC BY 3.0 | **游戏剪影**；粗犷单色（游戏界面卡） |
| noto | 3,819 | Apache | 表情图形（仅"内容是表情"语义时用） |
| ri（Remix Icon） | 3,229 | Apache | 线性+面性成对（remix 系） |
| healthicons | 2,797 | MIT | 医疗专题 |
| pinhead | 2,878 | CC0 | 地图/定位专题 |
| icon-park | 2,658 | Apache | 字节官方；**多色**扁平 |
| icon-park-outline | 2,658 | Apache | 字节官方；线性 |
| mynaui | 2,658 | MIT | 圆润现代 |
| carbon | 2,783 | Apache | IBM 风格；16/32px 企业感 |
| ph（Phosphor） | 9,161 | MIT | 六种粗细变体家族（含 duotone 双色调） |
| ion（Ionicons） | 2,361 | MIT | **iOS 原生风**（App 正统） |
| tdesign | 2,366 | MIT | 腾讯风格；圆角线性 |
| lucide | 2,100 | ISC | **圆角线性标杆**（社区事实标准） |
| bi（Bootstrap Icons） | 2,084 | MIT | Bootstrap 经典 |
| boxicons | 3,768 | MIT | Boxicons；线性/面性成对（2026-11-23 补登记，历史在库） |
| icon-park-solid | 1,970 | Apache | 字节官方；实心 |
| icon-park-twotone | 1,947 | Apache | 字节官方；双色调 |
| iconoir | 1,682 | MIT | 经典简洁线性 |
| f7（Framework7） | 1,253 | MIT | iOS 风，移动端生态 |
| heroicons | 1,288 | MIT | Tailwind 官方系 |
| pixelarticons | 1,306 | MIT | **像素风**（pixel-art-ui 卡） |
| dinkie-icons | 1,198 | MIT | 像素位图感 |
| teenyicons | 1,200 | MIT | 极简小尺寸（16px 友好） |
| uil（Unicons） | 1,216 | Apache | 圆角现代 |
| mage | 1,042 | Apache | 独特个性风 |
| withicons-soft3d | 1,000 | MIT | **软3D 充气质感**（inflated-3d 卡） |
| withicons-clay | 1,000 | MIT | **黏土质感** |
| withicons-skeuo | 1,000 | MIT | **拟物**（skeuomorphism 卡） |
| kubai | 3,071 | MIT | **动态质感静态导出**：分层渐变+外描边+投影（悬停动效的静止帧；动效版走引擎生成，见 §kubai 家族） |
| kubai-duotone | 502 | MIT | **双色面性**：16 网格实心双色，浅体+主色点缀 |
| withicons-sticker | 1,000 | MIT | **贴纸感** |
| withicons-pastel | 1,000 | MIT | **粉彩柔和** |
| solar ⚠署名 | 8,859 | CC BY 4.0 | 圆角线性/面性双系 |
| flat-color-icons | 329 | MIT | 彩色扁平（Google 系） |
| feather | 286 | MIT | 极简线性鼻祖 |
| nieobie-game-pack | 815 | CC0 | 原创游戏剪影包（Nieobie，本地编译） |

### 风格族 → 库白名单映射（I1 锁库 / I3 漏斗第一层共用）

| 需求单风格族 | 白名单（按序优先；⚠=CC BY 需署名） |
|---|---|
| 线性（细描边） | lucide → tabler → iconoir → feather → hugeicons |
| 圆角线性 | mingcute → mynaui → uil → tdesign → solar ⚠ |
| 面性/实心 | iconmind(面) → icon-park-solid → ri(面) → boxicons(面) → fluent(面) |
| 多色 | icon-park → flat-color-icons → withicons |
| 双色调 | icon-park-twotone → ph(duotone 变体) → kubai-duotone（面性双色，悬停语义动效） |
| **动态质感** | kubai →（缺新图标）engines 程序化生成（wf-icons §程序化生成）→ 生图提示词包 |
| **软3D/充气** | withicons-soft3d →（缺）3dicons.co → 生图提示词包 |
| **黏土** | withicons-clay →（语义缺口）生图提示词包 |
| **拟物** | withicons-skeuo →（语义缺口）生图提示词包 |
| **贴纸** | withicons-sticker →（语义缺口）生图提示词包 |
| **粉彩** | withicons-pastel →（语义缺口）生图提示词包 |
| **像素** | pixelarticons → dinkie-icons |
| **游戏剪影** | game-icons ⚠ → nieobie-game-pack |
| **iOS 原生** | ion → f7（⚠ SF Symbols 仅限 Apple 平台场景、不可入库分发——勿收录） |
| 企业/仪表盘 | carbon → fluent → tdesign |
| 医疗 | healthicons |
| 地图/出行 | pinhead → tabler(定位子集) |
| 表情图形 | noto → fluent-emoji 家族（未收录本地，经 Iconify API 按需取用） |

## kubai 家族（2026-11-23 落地）

两库均来自 npm `kubai-icons-static@0.14.0`（上游 kubai087/kubai-icons 的静态导出包），json 顶层已嵌 `license` 字段（MIT + 版权行 + 全文），单独流转不断链。上游同一套生成技能画出的两个风格：

- **kubai**（3,071 枚）：分层动态风格的静态帧——多层渐变、外描边 mask、投影/内发光滤镜全部内联在 body 的 `<defs>`（id 带 `ki-<图标名>` 后缀，sprite 内联不撞），颜色为推导渐变写死
- **kubai-duotone**（502 枚）：16 网格双色面性，body 内仅浅体/主色两个 hex 系；⚠ 其中 227 枚带通用短 id（`d-g1`/`d-c1`/`d-x1` 等，跨图标重名）——**多图标交付禁用 symbol sprite 合并，逐个内联**（单图标独立交付无碍）；需要 sprite 时先做 id 唯一化（id 与 url(#) 引用同步加 `kd-<名>-` 前缀）

### 改色特殊路径（I4 例外，与通用 currentColor 流程二选一）

kubai 分层图标的填充是渐变 url + 推导色，**禁用 stroke/fill→currentColor 属性替换**（会毁掉分层与光影）。改色两法：

- 分层库：走引擎重渲染（离线）——`node assets/engines/kubai-icons/scripts/export.mjs --only <名>[,名2…] --accent <主色hex> --out <目录>`，可加 `--palette 彩色|蓝灰|青瓷|薄荷|薰衣草|杏色|黑色`（彩色为默认）或 `--state hover` 导出悬停帧
- duotone 库：body 内直接双 hex 替换（浅体系 #BDC8FA 系、主色系 #5A76F2 系，按需求单主色换算）；⚠ body 里还有 #000/#fff，**仅存在于 `<mask>` 内部是结构色**——替换脚本只许碰两个双 hex，勿做全量 hex 替换

### 生成能力（缺新图标时的程序化生成）

`assets/engines/kubai-icons/` = 官方 release zip（v2.0.0）**逐字节原样**（21 文件 644KB，已 diff 核验；含 SKILL.md/PROMPT.md/src/scripts/styles/duotone + LICENSE）。**该目录任何文件禁改禁改名**——原样性是上游许可（Kubai Icons License §5）的生效前提。生成流程、环境探测、许可边界见 [wf-icons.md](wf-icons.md) §程序化生成。

`assets/engines/kubai-icons-definitions.js`（772KB，MIT）= 官方 967 基础物体**程序定义库**打包件（esbuild IIFE，全局 `KUBAI_LIB.ICONS['英文名']`，与交互引擎 mountIcon 同构）。**交互组件场景的第一供给**：命中官方定义 = 内联零生成；官方真没有的新语义才现画。⚠「半命中」记忆锚：静态库命中 ≠ 可交互（静态是死帧）；引擎 66 范例 ≠ 全量（只是教材）——两者之间夹着的正是这个定义库。

### 更新流程（上游发新版时）

1. 库重建：下载 `kubai-icons-static` 新版 npm tarball → 解压 → `python scripts/build_icons_json.py package/svg --out kubai.json --prefix kubai`（duotone 用 `package/svg-duotone` → `kubai-duotone.json`）→ 重嵌顶层 license 字段 → 回写本节枚数/版本
2. 引擎更新：下载官方 release zip `kubai-icons-v*.zip` → 整目录替换 `assets/engines/kubai-icons/` → `diff -r` 对照 zip 确认原样 → 回写本节版本号



| 源 | 用途 | 纪律 |
|---|---|---|
| Iconify API `api.iconify.design` | 补新集合/本地没有的；search 索引全库 | 取一次落 cache，之后离线 |
| 3dicons.co | C4D 质感位图（color 变体直下；玻璃/渐变走其 Editor remix），CC0 | 按需单文件；禁止整包；**.com 是他站勿混淆** |
| GitHub 各库官方仓 | 新版本追平/独立包（如 Nieobie） | 编译 JSON 落地（build_icons_json.py），不囤散文件 |

## 新库接入流程

Iconify 整包：@iconify/json npm tarball 一次下载全部集合 → 挑选复制
Iconify 单库：`https://api.iconify.design/<prefix>.json?icons=all` → 落 `assets/icons-json/<prefix>.json`
本地 SVG 目录：`python scripts/build_icons_json.py <svg目录> --out <prefix>.json`
落地后必做：本文件登记一行（枚数/许可/风格档案）+ 白名单映射表按需补行
