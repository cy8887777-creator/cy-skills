# solo-ue-line-cy-mockingbot-html 详细规范

主文档见 [../SKILL.md](../SKILL.md)。本文是脚本参数、数据 schema、边界 case 的细节。

## 墨刀导出包解剖

```
<pkg>/                          # 墨刀导出的项目目录（含 index.html 的那层）
├── index.html                  # SPA 查看器（webpack runtime）
├── extra/
│   ├── data.0.js               # 小数据
│   ├── data.1.js               # 主数据 ~20MB：window[<key>][<key>]=[[id,id2,"H4sIA…"],…]（key 名随包变，按 H4sIA 块定位）
│   └── data.2.js
└── uploads7/                   # 切图（img src 直接引用）
```

- data.1.js 首个 `"H4sIA…"` 块 = 全量快照（gzip+base64），解压 ~百 MB 级行式文本
- 行格式三种形态：`cid\t{…}`、`cid ,\t{…}`、`cid 5\t{…}` —— 统一 `line.slice(0, tab).split(/\s+/)[0]` 取 cid
- 只取 `"N":"名称"` 字段建 cid→N 字典（数十万条）；**层级/坐标一律不用快照**（可能滞后），归属走 CDP 挂载 diff

### 导出格式版本（2026-10-20 双格式实锤）

| 指纹 | 旧格式（gzip 快照） | 新格式（PB=v1 明文 JSON） |
|---|---|---|
| 数据 | `window[k][k]=[[id,id2,"H4sIA…"],…]` | `window["hzv3"]["psol"]=[{ttag:"PB=v1&PBT=screen",cid:"sk…",stateList:[{itemList:[…]}]}]`；`data.1.js`=pbj（screen_metas 页面树含 name/parent_cid/position/w/h/bgcolor）；`data.0.js`=pid；`data.3.js`=psv2am（常空） |
| 画板 cid | `rc…` 纯段，快照里有 rc 行 | **源数据无 rc**（查看器运行时生成），板名走 `names[cid]||cid` 兜底 |
| 侧边栏条目数 vs psol 条目数 | 一致 | DOM 侧边栏 120 < psol 136（16 个组件源/子画布不进侧边栏）——以侧边栏为批次真值 |
| 提取根 | `.tree-node.rResCanvas[data-cid]` | `.pcanvas[data-cid=页面cid]`（active 才有尺寸），walk 含三区并逐元素 `zoneOf` 打 zone 标 |
| 归属 | diff/认领/同板复用三段式 | 点击即激活页面自己的 pcanvas，board=page.cid，无归属逻辑 |
| 色值 | 静态 icon-colors.json | 提取端现场扫 stylesheet 建 `hash→色`（规则形如 `.kKhnky.fill g [fill]{fill:rgb(234,88,12)}`；声明 currentcolor 的规则过滤、落回继承色） |
| 板高 | 画板设计尺寸 | `--board-mode long`（默认）：H=max(视口812, 内容底)+footer 孪生去重钉底；`viewport`：原始画板高 |

分支判定：数据层探 `"psol"` 字串（read-data）；DOM 层 `cdp.mjs detectModel()`（`.pcanvas[data-cid]`→pcanvas，`.tree-node.rResCanvas`→legacy）。两分支 boards/<cid>.json schema 一致。

## 脚本契约

### start-chrome.mjs `<pkg>/index.html [basePort=9225]`
- chrome.exe 三候选路径探测；`--headless=new --window-size=1920,2400 --allow-file-access-from-files --remote-debugging-port`
- 等侧边栏 `.rn-list-item` 挂出；写 `.claude-tmp/chrome-<port>.json`：`{port, pid, udd}`

### stop-chrome.mjs `<infoFile>`
- 按 PID `taskkill /PID xxx /T /F`。**严禁 /IM chrome.exe**

### read-tree.mjs `<port> <out.json>`
- 读全部 `.rn-list-item[data-cid]`，按 cid 去重（DOM 同条目重复出现）
- `depth = Math.round(paddingLeft / 20) - 1`，栈法重建 parent
- 产物 `{items:[{cid,name,type:'folder'|'page',expander,depth,parent,dir}]}`（dir = 目录链，folder 名串成路径）

### read-data.mjs `<pkg> <out.json>`
- 双格式自动分支：任一 extra/data.*.js 含 `"psol"` → 明文分支（pbj.screen_metas 页面名 + psol screen/state/元件 display_name|name 递归）；否则 gzip 分支
- 产物 `{meta:{…}, names:{cid:N}}`；同 cid 多行取首个（快照行优先）

### batch.mjs `<port> <manifest> <data-map> <outRoot> [--only c1,c2] [--limit N] [--skip-gen] [--retry-failed] [--min-w 150] [--board-mode long|viewport]`
- **pcanvas 模型主循环**（`cdp.mjs detectModel()` 分流）：点击 → `WAIT_BOARD` 轮询（MOUNTING/NOT_ACTIVE/TOO_SMALL → 空页面记 empty）→ `extractBoardPcanvas`（pcanvas-extract.mjs：懒加载预滚+PICK 三区提取+hash 色字典+伪元素物化+postPass）→ gen-html；板缓存/断点/sanitize 与 legacy 共用
- postPass（仅 long 口径全效）：footer 子树与内容层**子树文本串相等**判孪生（根是 0×0 包装器，勿比尺寸）→ footer 副本整树删；幸存 footer 节点 y += contentBottom−视口高（钉底）；H=max(视口, 内容底)。viewport 口径不位移、H=画板原始高
- 每页：三连 dispatch 点击（带坐标）→ 1.2s 间隔轮询挂载稳定（连续两次相同）→ diff 新板
- `uniqByCid`（newBoards 与 orphans 两处）→ 同 cid 取**面积最大**（不同 scale 双挂载）→ `w>=minW && h>=minW` 过滤符号画布
- diff=0 → 认领 `mountedBase ∩ 未认领`（初始默认页的板不卸载）
- **同板缓存**：boards/<cid>.json 已在 → 复用跳过 extractBoard（改提取逻辑要重提时先删 boards/）
- extractBoard（内联 ROLL+PICK）→ gen-html → 落盘 `boards/<cid>.json` + 页面 html
- 板提取失败记 `state.done[页].failedBoards`（页面不算整页失败）；`--retry-failed` 重置含 error/failedBoards 的页面重跑
- 连上后校验 location.href 含 index.html（防 connect fallback 连错 tab 整批跑废）
- 命名：单板 `<dir链>/<页面名>.html`；多板 `<dir链>/<页面名>/<子画布名=dataMap[cid]>.html`（重名从基名重算加 cid 尾缀，不叠加）
- state.json 记 {done, claimed} 断点续跑
- 文件名 sanitize：非法字符替换、Windows 保留名（CON/PRN/AUX…）加前缀、60 字符截断

### make-index.cjs `<outRoot> [manifest.json]`（左树右平铺预览器，2026-09-17 用户三轮反馈定稿形态）
- 传 manifest → 左侧墨刀真实层级页面树 + 搜索过滤（subtreeMatch 保父链 + mark 高亮，**页面嵌套页面的子级也参与匹配**）；同层顺序=墨刀侧边栏原始顺序
- **页面嵌套页面**（manifest 466 条子级 parent 指向 page）：页面也挂 children 渲染为可展开节点（▶ 箭头=开合子级，点名称=预览其画布）——只认 folder 当容器会把这些全甩顶层（用户实锤「层级缩进没了」的根因）；树递归（count/findById/autoFirst/subtreeMatch）都必须走全部 children 不能只走文件夹
- 交互（2026-09-17 用户拍板）：**点文件夹=纯展开/收起（不平铺子页面）**；点页面=平铺其全部画布；缩放**默认=原尺寸 1:1**（2026-09-17 用户拍板「375 板就显示 375 宽」——iframe 不 transform，卡宽=画布+48），「适应」为可选缩小（统一 320 卡宽 scale 等比）；旧「100% 单列纵排」模式已删
- 网格：`.grid` 用 **flex wrap + justify-content:center**（卡宽不定=各画布原尺寸，grid 定宽轨道不适用）；懒加载前 fbox 占位须显式 width/height（flex 里无宽时 aspect-ratio 不触发，fbox 零高永不进视口）
- 卡片 = 板名标签 + iframe **静态预览**（IntersectionObserver 懒加载 root=#wall rootMargin 400px）+ 透明遮罩——**右侧不允许跳转**；点击卡片 = `window.open(url,'_blank')` 新标签打开该画布（跳转交互在新标签闭环；file:// 下用户手势内实测不被拦；被拦时 toast + location.href 兜底）
- **iframe 无滚动条**（2026-09-17 用户实锤）：产物 html body 有 `padding:24px` 衬边，塞等尺寸 iframe 必溢出出滚动条 → iframe 尺寸给足「画布+48」+ `scrolling="no"`（不依赖同源注入——file:// 下用户无 --allow-file-access-from-files 时 contentDocument 不可访问），fbox 底色调 #E9E9EF 与产物 body 同色做无缝衬边；aspect-ratio/scale 同步 +48
- 左栏拖拽调宽：#side 与 #main 间 5px dragbar（col-resize，220~640 clamp），拖动实时 scaleAll 重算，宽度 localStorage(`idx-side-w`) 记忆
- 板尺寸读 boards/<cid>.json 的 page.board.w/h（缺失默认 375×812）；hash 路由 `#p=<pageId>` 恢复选中 + 首次进入自动选第一个有板页面
- 读 state.json：空页面出灰字占位「墨刀无画布（内容在子页面）」、失败页/部分失败页出红字 ⚠ 条目（不生成文件，不污染产物目录）
- 不传 → 退回磁盘目录扫描（中文 localeCompare 排序；无法区分页面画布目录 vs 子页面目录）

### audit.mjs `<outRoot>`（对账，不平退码 1）
- 多页共用板提示 / state↔磁盘 html 孤儿缺失 / boards json 对账 / 空页失败清单 / 产物 blob:·InteractionMarker 残留

### diagnose.mjs `<port> <data-map> <页面cid>…`（单页排障）
- 点击（带坐标）→ 前后挂载对比：选中态、卸载/新挂板、当前挂载全列表（标注页面画布 vs 组件源）

### cdp.mjs（公共模块）
- `connect(port, urlRe=/index\.html/)` → `{ws, send, evalJS, close}`；**urlRe 匹配不到 fallback 到第一个 page**（导航离开墨刀后是隐患）
- `send()` 返回整个响应对象；`evalJS` 检查顶层 `exceptionDetails`
- `waitUntil(evalJS, expr, {timeout, interval, label})`
- `detectModel(evalJS)` → `'legacy'|'pcanvas'|'unknown'`：查看器代际指纹（`.pcanvas[data-cid]` / `.tree-node.rResCanvas`），batch/extract-board/diagnose/read-hotzones 共用

### pcanvas-extract.mjs（新格式共享提取模块，batch/extract-board 复用）
- 导出：`WAIT_BOARD(cid,minW)`、`ROLL(cid)`（懒加载预滚）、`PICK(cid)`（三区提取主探针）、`SAMPLE(cid)`（绘制序采样）、`postPass(data,boardMode,stacks)`、`extractBoardPcanvas({port,cid,outJson,name,boardMode,tool})`、`detectModel`
- PICK：根=`.pcanvas.active`，walk 三区并逐元素 `zoneOf` 打 zone 标；hash→色现场字典（扫 stylesheet，规则含 `svg-icon-path-icon|.fill` 且色值非 currentcolor/none/transparent）；伪元素物化（可见才产节点）；**全节点记 st.clr**；空 src img 跳过；`st.tf` 采集；`data-mth=idx` 打标（svg 在取完 outerHTML 后打，防污染源码）；**img/bgi 祖先裁剪**（沿祖先链取全部非结构性 `ovf:hidden/clip` 祖先盒交集=img 真实可视区——结构性容器 screen-*/scontainer/widgets/pcanvas 的 overflow 属滚动机制不计；完全在外=未绘制丢弃，部分相交=取交集 + 记 `clipFrom`=原盒偏移/尺寸）
- SAMPLE：网格布点（步长自适应封顶 ~1200 点，只采首屏可视区 812）逐点 `elementsFromPoint`，收集 `data-mth` 真实堆叠链；采样期对全部标记元素**逐个内联** `pointer-events:auto!important` 强制可命中（⚠ 样式表 `[data-mth]{pe:auto!important}` 会被墨刀自己的样式压回——实测 computed 仍 none；内联 important 必生效），采完逐个恢复原值
- postPass：①采样约束拓扑重排（链上下关系为硬边，Kahn+原 idx 稳定优先；环内残余按原序追加）②footer 孪生去重（子树文本串相等，footer 副本整树让位——勿比对根尺寸，根常是 0×0 包装器）③幸存 footer 钉底 + 板高口径（long：H=max(视口,内容底)；viewport：原始高）

### extract-board.mjs（单板 CLI，调试用）/ gen-html.cjs（board.json → html，可独立重跑）
- gen-html 可选参 `--hotzones <hotzones.json> --state <state.json>`：交互热区跳转层能力保留但**已下线（2026-09-16 用户拍板：影响后续导入使用）**——regen 的 hzArgs 恒空，产物 html 零热区（元素/注释/CSS 三层 grep 断言 0）；hotzones.json 数据保留仅作档案

### read-hotzones.mjs `<port> <manifest> <data-map> <out-hotzones.json> [--only cid,…] [--limit N] [--retry]`
- 逐页点击（batch 同款三连 dispatch）→ 每板 scrollIntoView + 懒渲染稳定 → 扫 widget fiber（父层 props.widget.hotAttr.interactions）
- 产物 `{ meta, zones: { 板cid: [{ widgetCid, type, name, x,y,w,h(板内绝对坐标), zi, inters:[{t,trig,toPage,toCanvas,url}] }] } }`
- 增量断点（zones 已有板跳过）；坐标换算与 extract nodes 同系（DOM rect × offsetWidth/rect.width）
- 可与 batch 并行（各自独立 Chrome 实例，互不干扰）

### regen.mjs `<产物根> [--only 页面cid,…] [--concurrency 4]`
- gen-html 规则升级后用 boards/*.json 缓存并发重生成全部 html，不重新提取（几十板秒级）

### add-interactions.mjs `<产物根> [--dry]`（语义交互绑定，regen 之后跑）
- 读 boards/*.json 语义（svg 指纹/文本/位置）给产物 html 的元素 div 注入 `onclick` + `data-nav` + cursor:pointer——五规则详见 SKILL.md 生成规则 18（tab 指纹/返回箭头/弹窗取消/父子页面名链接/热区档案映射 R5）
- R5（2026-09-17）：读产物根 hotzones.json，热区矩形几何命中板内节点直绑跳转（toCanvas 板优先/toPage 页兜底，均语言对齐后取板）；跳过 trig≠tap / url / 目标去重≠1（缺失+多目标歧义）/ 跳自己 / 已被语义绑定覆盖；命中候选须过 htmlIdxSet（产物 html data-idx 存在集——gen-html 已删的壳/角标 json 里还在但无 div）+ w/h≥12 + 中心在热区内(±2px) + 重叠≥节点 0.5 + 面积≤热区×3。**热区内全部合格候选同绑**（用户实锤：择优「取 z 最高」系统性选中角标/红点——永远浮在按钮右上最上层，按钮本体反而没绑）。跳过统计记 report.r5skip/r5self/r5covered/r5nomatch
- **R5 t=2 返回热区 + 跨板复用（2026-09-17 用户实锤「Cancel Matchmaking 无交互」）**：t=2 无目标 tap = 墨刀「返回上一页」交互（全站 308 条全无目标、位置不限于左上箭头——底部取消按钮/右侧关闭位 R2 语义救不到）→ 几何命中绑 `history.back()`（kind=goback）；**同页兄弟板热区跨板复用（t=2 与 t=1 都复用）**（去重 key=round(x),round(y),round(w)）——t=2 返回交互与语言无关（无目标解析）、复制板布局保位，而镜像三轮全靠 svg/img/bgi 指纹，纯 bg 底板+文本的按钮永远配不上（中文/阿语板 goback=0 的根因）；**t=1 跳页热区跨板复用（子代理全站排查实锤）**：跳页热区常只画在 EN 板（「开始匹配」→中文板 10+ 块主 CTA 裸奔），t=1 借用目标走 zoneHref **接收板语言对齐**（curBoardName 优先），错位落空无害（宁缺毋滥不变）。镜像的 zoneCnt/anchors 放宽到 zone+goback（goback 无 tgtPage，localize 原样返回）
- **R5 命中过滤三个放行修复 + ±84 校准（2026-09-17 子代理全站排查实锤）**：a) 窄文本条放行——`(w<12||h<12)` 的节点若有文本且 h≥16、w≥4 放行（`‹` 返回键 json w=6.7，注册/重置密码 3 板返回零绑定）；b) 大热区蒙层通道——面积>热区×3 的排除对 ≥120×120 热区开例外：节点盖住热区九成（ov≥热区×0.9）= 弹窗整体关闭蒙层，放行（观众头像弹窗 278×352 热区只压到大背景）；c) 重叠双向——`max(ov/节点面积, ov/热区面积) ≥0.5`（原单向把「热区完全在按钮内」的反向包含算未命中：在线人员列表表格行 343×46.5 只 49.4% 落在 175×45 热区内，Leave/Mute/Ban 三跳转裸奔）；d) ±84 坐标校准——母版系板（商城Shop 全系/搜索群组）hotzones y 与板内真值恒差 84px（iPhoneX 状态栏帧偏移，x 逐像素一致实证），**原位零命中才试 y∓84 平移重试**（防误绑），命中同样过全部过滤
- **R6 业务流词典（2026-09-17 用户拍板：热区只在英文板画中阿全没做，是残缺数据；主 CTA 按业务流推演直绑）**：页面上下文 + 三语等值词典 + 按钮形（w≤240 h≤44），不覆盖已有绑定（R5 先绑保留、R6 只补裸奔）。规则族：四游戏首页入口词（创建房间→游戏房间无玩家；Quick/Battle/开启对战/معركة→本游戏选人页，Ludo/Uno 取 rank 场景、Carrom/Jackaroo 取 1v1；主活动→主赛事首页；战队战争→战队赛首页）；充值底部主 CTA（y>0.85H，Top Up $9.99/充值 $9.99/شحن）→确认充值弹窗；VIP 已购买续订（y>0.88H）→支付确认；打开游戏选择 Create/创建/إنشاء→群组内开启游戏-群主视角；新手引导关闭/告知领导层发消息/升级弹窗 Claim Rewards→history.back（kind=flowback）；结算页 Play Again/继续匹配→父页面（匹配中，byPath 取 dir 最后一级）；参赛悬浮窗 Create Room→游戏房间无玩家。R3 词典补「好的」。**web 充值旅程板不绑**（3696 宽六帧横拼流程文档板）。byRule.flow 计数
- **语言对齐剥尾序号**：目标页板名「中文 2」对当前板「中文」（同语言板复制时墨刀自动加「 2」后缀）——精确等值落空回退 English 板（中文板点创建房间跳英文房间实锤）→ boardHref/zoneHref 先精确等值、再剥尾部数字比，仍对不上才回退原 cid 板/第一板
- **同页跨板镜像（2026-09-17 用户实锤「中文板 Quests 按钮点不动」的根因）**：功能入口热区只在当初定义交互的语言板（通常 English）上有——复制出的中文/阿语板 zones[板cid] 里只有 tab 栏热区（被 R1 覆盖）→ R5 整板零 zone 绑定。三遍流程：①每板构建 actions（R1-R5+propagate）②同页跨板镜像 ③统一写盘。镜像 = 基准板（zone 绑定节点最多）的 zone action 经三轮配对抄到其他语言板：
  - 一轮：同指纹（svg normalize / img 切图 URL / bgi）+ 直接坐标（LTR 复制板，dy≤100/dx≤120 取 y 最近）
  - 二轮：RTL 镜像板 x 翻转重排坐标对不上——同指纹未消耗候选双方按 y 排序 zip，dy≤80
  - 三轮：跨形态兜底（svg 板 ↔ img/bgi 板指纹互斥——Ludo 阿语板图标全 img、EN 板全 svg）——图标形态节点（无文本 w/h∈[16,90] svg/img/bgi 任一）× 锚点（w/h≤120）同尺寸±3、dy≤40 取最近；**y 平手歧义挂起**（同图标位多层锚点+Quests/Rankings 同 y 平手，贪心必抢错——错绑比不绑糟）
  - 歧义重试：RTL 镜像定向（几何投票：明确偏侧配对全反侧；或板名含阿文——双套 tab 叠放污染下投票常无样本，语言判定兜底）→ 歧义节点改选**反侧**锚点
  - 镜像 action 按接收板语言重算 href（action 带 tgtPage 引用，boardHref 以接收板名对齐——直接抄基准板 href 会中文板跳 English 板）
  - 镜像锚点也做画布内过滤（inCanvas：x>-20 且 x+w<W+20 且 y>-20——RTL 双套叠放的负坐标隐藏层不参与）
- **propagate（板内邻域扩散，镜像后也要跑）**三层：①覆盖层扩散（矩形内更高 z 无 action 节点同绑——平铺兄弟结构不冒泡）②**底板包含扩散**（action 矩形被 idx 更小的底板包含（±2px）且面积≤9× 同绑——镜像 svg 锚点只绑图标本体，32×32 底板套 24×24 svg 点边缘环不动）③图标-文字组队（w≤80 图标正下方 22px x 重叠>30% / 正右侧 12px y 重叠>30% 的文本同绑——墨刀热区只画图标不盖文字，不同语言文字无法字面配对靠组队传导）
- 报告落 `<产物根>/../.claude-tmp/interactions-report.json`；byRule 是语义计划数（mirror=镜像锚点数）、bound 是实际注入 div 数（含扩散，≥语义数）。MIRROR_DEBUG=1 打镜像投票统计、=2 打三轮逐节点判定
- 幂等：重跑先按特征正则剥除旧注入再绑；跳转目标语言板对齐（目标页 boards 同名板优先，否则第一板）；byRule=语义计划数、bound=实际注入数（扩散后 bound>ΣbyRule 是正常态）
- 跑完必须死链断言（全产物 grep onclick location.href 目标文件存在性）+ Input.dispatchMouseEvent 真实点击抽测

### inspect.mjs `<port> <产物根>`
- 渲染断言自检（另开 tab 逐页加载产物）：orphan 孤字 / nowrapOver 溢出 / ellipMissing 缺省略号 / eccH·eccV 居中偏心 / overStage 越界 / jsonMisalign·jsonDup 对照提取侧；stdout 摘要 + inspect-report.json
- **指标对照 `_墨刀稿问题报告.md`**：jsonDup=双份渲染数、jsonMisalign=同带高差组数、eccV=阿语偏心数——regen 后这三个数与报告一字不差即生成侧零回归（本轮靠此判定法收尾）

## 提取字段（boards/<cid>.json）

```jsonc
{
  "meta": {"tool":"batch.mjs","generatedAt":"…"},
  "page": {
    "cid":"rcVQct6uyhcVOYHw", "name":"页面 1",
    "board":{"w":750,"h":1754},       // 画布尺寸=墨刀设定，不写死
    "pkgBase":"file:///…/pkg/",        // 切图定位基准
    "nodes":[{
      "idx":104, "parent":103, "depth":9, "tag":"div",
      "x":20,"y":1165,"w":147.5,"h":88, // 画板坐标系（rect×scale 换算回）
      "cls":"…", "text":"页面大标题",     // <br> 提取为 \n；text-node 以空格相连
      "st":{"bg":"rgb(255,255,255)","clr":"rgb(23,23,23)","fs":24,"fw":700,"lh":33,"ff":"Roboto,…",
             "ws":"nowrap",              // 墨刀显式 white-space（normal 不记）
             "textH":33.2},              // Range 实测文字渲染高（纯文字叶子才有）——换行判定真值
      "name":"", "bgi":""               // data-name 截 80 / background-image 截 500（data: URI 放宽 30000）
    }]
  }
}
```

pcanvas 模型（新格式）补充字段：
- 节点级 `zone`: `"header"|"content"|"footer"`（每元素 zoneOf 实测，footer 孪生去重/钉底依据）
- `st.tf`: computed transform（仅 gen-html 白名单透传不改 AABB 的翻转：rotate(180deg)/scaleX(-1)/scaleY(-1)/scale(-1)）
- `st.clr`: **全节点**记录（旧版仅文本节点）——svg currentColor 继承、data:bgi 的 currentColor 替换都靠它；path-icon 已按 hash 现场字典把 fill/stroke 预解析为绝对色
- 伪元素节点：`cls:"pseudo::before|::after"`，按 computed style 克隆探针量 rect 物化（图标字体字形跳过）

## 生成 HTML 形态

```html
<div class="stage" style="width:375px;height:812px">
  <!-- [4] parent=3 div text="12:00" -->
  <div data-idx="4" style="left:21px;top:12px;width:53px;height:20px;position:absolute;
       box-sizing:border-box;z-index:4;color:rgb(16,16,16);font-size:14px">12:00</div>
  …
</div>
```

- 平铺：所有节点 absolute 相对 stage，parent 只留注释
- z-index=idx；svg fill 按类分流注入（path-icon 字典色 / 普通 currentColor）；InteractionMarker/热区删
- **svg 颜色两套机制分流（2026-09-17 二轮实锤，推翻「一律 currentColor」）**：①`svg-icon-path-icon` + `.fill` 修饰（path 图标全站 9347 个）——查看器 styled-components 按 solidColor prop 运行时 CSS 写死填充色（`.hash.fill:not([fill]){fill:rgb(...)}`），json 无此字段但色值参与 hash 类指纹（同色=同 hash，全站 46 个）→ gen-html 按 `references/icon-colors.json` 字典还原：子元素写死 fill|stroke（含源码自带 currentColor）替换字典色、none/transparent 保留、**stroke 型补 fill="none"**（漏补 chevron 隐式闭合填实心）、svg 无 fill 注入字典色；②`svg-icon-path-icon` 无 `.fill`（294 个）——查看器零 fill 规则默认黑，产物不注入（源码自带 currentColor 合法）；③`.svg-icon` 类非 pure——查看器 CSS 盖成 currentColor 随容器色，写死色替换 currentColor；pure/无 class 真彩保留。**分流判定用完整类名 `\bsvg-icon-path-icon\b`，`/svg-icon/` 子串误命中是上轮误伤根源**。断言：`node assert-icon-colors.cjs <产物根>`（A 字典色/B 无 currentColor 残留/C hash 未命中=0）。**色值活在运行时 CSS：DevTools CSS domain 对 file:// 页 0 样式表、document.styleSheets 部分 sheet 被 SecurityError 挡——定性须量 computed + 穷举全部 sheet 规则原文**
- **svg 无 width/height 属性补 `width:100% height:100% display:block`**（wLine 分割线/线性图标靠查看器 CSS 定尺寸，裸 svg 默认 300×150——375 宽的线右断 75px）；注入只加 fill attr，不插 style（svg 原 outerHTML 自带 style 会撞成双 style 被浏览器丢弃）
- **img 头像圆角父链继承 + overflow:hidden**：墨刀头像 = 三层圆角容器（wImage→Wrapper→container）嵌 img，平铺提取只拿 img 叶子（自身 br 空）→ 产物方头像。沿父链找**贴合容器**（尺寸 ±2px）的 br 继承；容器 br 必须配 overflow:hidden（border-radius 不裁子内容）。bgi 头像同法继承但 background 天然被 br 裁、不加 overflow:hidden（bgi 自身 br 空的形态样本 0 例，全量遇到照此处理）
- img/bgi 本地化拷 assets/（冲突加序号；blob: 丢弃；**data: URI 原样内联**，其中 currentColor 替换为节点 color）
- **文字换行**（有空间不折行，非一刀切 nowrap）：优先级 ①st.ws 只有 nowrap/pre 族才还原（break-spaces 是查看器默认样式不作数）→ ②含 \n 用 pre-line → ③**估宽主判据**：CJK≈fs、其他≈0.55fs，est ≤ w×1.08 = 放得下/贴框 hug → nowrap → ④est 超框但 st.textH≤1.5×lh（墨刀实测单行=溢出渲染）→ 也 nowrap；否则 normal。textH 只做本向兜底——临界折行时它被 fallback 字体污染（实测 ratio 0.99 却测出 2 行），不能反着用 → ⑤**按钮文案单行还原**（2026-09-17 用户实锤）：墨刀折行（est>框宽×1.08 且 textH>1.5lh）但最紧包含文本框中心的实心底板（bg 非透明/bgi、无文本、≥36×16、非热区橙）宽 ≥ est×1.05 → nowrap + 单行文字垂直居中回原框中线（top+=（h-lh)/2）；**拉宽段的 mkLines 须强制 1**（textH 是墨刀两行真值，不覆盖会让 want 减半、拉宽失效）。安全阀：底板也放不下 = 真窄按钮，保持墨刀折行
- **字体链兜底**：墨刀常只写 `NotoSans` 单个字体名，本机没装裸 fallback 宽度差异大 → 无通用字族的 ff 追加 `,"Microsoft YaHei","PingFang SC",sans-serif`
- **gen-html 规则升级后重刷产物**：`node regen.mjs <产物根>` 用 boards/*.json 缓存并发重生成全部 html，不重新提取
- 头部注释块写编辑指引

## 已知边界 case

| 现象 | 处置 |
|---|---|
| 一页挂多板同尺寸（如多语言子板） | 同级文件夹多个 html，名取 dataMap |
| 同 cid 板挂两份不同 scale（750/905） | uniqByCid 取面积最大 |
| 符号画布（路径型 cid，7~110px） | minW=150 过滤 |
| **大组件源混入**（路径型/拼接段 cid 但 ≥150 宽：列表条目/弹窗类组件，实测 287~334 宽） | `isPageBoard`：仅 `/^rc[A-Za-z0-9]+$/` 算页面画布 |
| **点击不切页**（无坐标 dispatch） | CLICK 必带 clientX/clientY + class 含 active 校验 + 重试一次 |
| **空页面**（选中生效、卸前页板、不挂新板） | 记 `empty:true` 不算失败（实测弹窗类/详情类页面存在此形态） |
| **同板复用页**（弹窗/状态页与前页共用画布，diff=0） | 兜底2：当前挂载的非基线 rc 板即本页板，独立生成 html |
| **跨进程遗留板错认**（续跑时认领到上批板） | 认领候选排除「已在 state.done 产物里出现过的 cid」 |
| 初始默认页板永不卸载 | mountedBase+claimed 认领 |
| 墨刀表格/文字双份渲染（同内容两节点） | 无害（后者盖前者），不去重 |
| 切图懒加载 is-default-image 占位 | ROLL 预滚 scrollIntoView+轮询清零 |
| **单行文字折出孤字并压到下方节点**（字体 fallback 变宽，实测全页面普遍存在） | 提取端记 ws/textH 真值，生成端按「空间够→nowrap」策略（见生成 HTML 形态） |
| 墨刀内嵌 svg 背景图标（data: URI） | gen-html 原样内联 + currentColor 注色；PICK 截断放宽 30000 |
| **svg 图标变色（部分图标颜色与墨刀里不一致）** | 墨刀查看器 CSS 盖写死色为 currentColor，产物无此规则 attr 直接生效 → 按 svg class（svg-icon 非 pure）替换写死色（见「生成 HTML 形态」） |
| **path 图标颜色与墨刀不一致（23/36 深色图标变灰蓝，二轮实锤）** | 上轮 currentColor 修复误伤 path 图标：`svg-icon-path-icon` 是 styled-components 写死色（solidColor prop 插值运行时 CSS），不随容器 color；且 `/svg-icon/` 子串判定误命中 → 完整类名分流 + hash→色值字典（icon-colors.json，46 条全站采齐）写死色；`stroke 型补 fill="none"` 防开放路径隐式闭合变形 |
| **path 图标子元素源码自带 stroke="currentColor" 被漏替换（kBNHRO，VIP阿语板）** | 查看器 `[fill]/[stroke]` 规则盖「一切有该 attr 的元素」（含 currentColor 形态）——替换正则的负向前瞻不得豁免 currentColor（只豁免 none/transparent），否则该形态图标产物变容器色 |
| **色值来源定位不到（CSSOM/DevTools 全空）** | styled-components 规则注入在 file:// 下被 SecurityError 挡的 sheet 里：CSS.getMatchedStylesForNode 对 file:// 返回 0 样式表、document.styleSheets 部分抛异常——须逐 sheet try/catch 穷举 cssRules 原文搜 hash 类，或量 computed + 读 JS chunk 里的组件 css 模板（`["&.fill{[fill]{fill:", …]` + `r=>r.solidColor` 插值）定性 |
| **hash 字典采集（46 条翻 23 页才采齐）** | 侧边栏条目带序号前缀（「2 中文」）精确匹配须 strip `^\d+\s+`；boards json 的 page.name 是**板名**（English/中文/العربية）不是页面名，映射页面须走产物目录名；图标组件**懒挂载**（翻页后规则不一定注入，须滚动画布触发）；贪心集合覆盖选最少页面（46 hash：21 页覆盖，Ludo 板一页 +4 即贪心起点）。补采脚本形态见会话 .claude-tmp/collect-*.mjs |
| **wLine 分割线右断一截** | 线 svg 无 width/height，默认 300×150 裁掉 375−300 → 补 width/height 100%（见「生成 HTML 形态」） |
| **头像/圆角图片方形（稿里是圆的）** | img 叶子自身 br 空，圆角在被丢掉的父容器上 → 两段式继承：①cover 载体（父链第一个 br 容器≤img → 继承 br + 产物框换容器框，img 溢出框套 br 会变胶囊）②贴合兜底（±2px，或 h≥24 高差≤8px）+ overflow:hidden；bgi 只取 br 不加 overflow。父链全无 br 的 img=PNG 圆素材族（alpha 自带圆形）不给 CSS br（见「生成 HTML 形态」） |
| `<br>` 多行文本 | 提取转 \n，生成 pre-line 保留 |
| **交互定义位置** | 不在快照（0 条 ita 行）——在 widget 父 fiber props.widget.hotAttr.interactions；hotAttr.x/y 是父容器相对坐标不可直接用（见 SKILL 坑清单） |
| **目标 cid 不在产物**（空页/组件源板） | 热区层已下线，此条仅存档；跳转关系数据在产物根 hotzones.json 可查 |
| **阿语板双套 tab 栏叠放**（LTR+RTL 镜像两版） | 按 svg 指纹各自绑定，两套语义都对（点哪套都行） |
| **产物页面出现淡蓝 ✦ 小闪电角标**（2026-09-16 用户截图实锤，690 板/2508 处） | 漏删交互标记 ✦ 角标 svg 本体：源码 class 含 `icon/link/mark`（12.6~30px 多形态），其 cls 提取值是坏值 `[object SVGAnimatedString]`（SVG 须 className.baseVal）不可依赖 → gen-html 按 svg 内容整删 |
| **按钮绑了 onclick 仍点不动（真实点击无反应）** | 两个独立根因：①`wLr` 透明壳残留——热区 widget 容器（cls 含 wLr，自身无视觉内容但 48×46 级盖住按钮吃掉命中；2026-09-16 快照 2580 壳，子树验证零内容后按 cls 整树删）②平铺兄弟结构不冒泡——视觉子元素（图标 svg）是绑定容器的兄弟且 z 更高，点击落在其上永不触发容器 onclick → 覆盖层扩散注入（add-interactions 内置）。注意 el.click() 绕过命中测试测不出这两层，排查必须 elementFromPoint 看顶层 + Input.dispatchMouseEvent 真实点击 |
| **跳转断言显示「未跳」但页面其实跳了**（或反之） | 来源与目标常同名（多语言板都叫 English.html），按文件名/URL 尾段对比有歧义 → 断言必须比对**完整 URL**（用 new URL(相对路径, location.href).href 解析期望值再比） |
| **tab 点击错跳到个人中心** | 「群组我的」EN 板 tab2 孤例画错成人像（全站仅此一处）→ 人像指纹仅认边列（x<0.2W 或 x>0.78W），中间列人像不绑 |
| **断言脚本点按钮无效果且 evalJS 返回 undefined**（按钮 handler 明明正常） | CSS 属性选择器值以数字开头必须加引号：`[data-z=100]` 非法（CSS 标识符不能数字开头）→ querySelector 抛 SyntaxError；须写 `[data-z="100"]` 或按 textContent find 后 dispatchEvent（2026-09-17 _index 缩放断言实锤：probe 三轮误报「100% 不生效」，实为断言选择器 bug） |
| **R5 zone 计划数远大于实际注入数**（1652 计划只注入 65） | 热区命中的节点是 gen-html 已删的 wLr 壳/✦ 角标——boards json 里还在、产物 html 无 div，注入静默落空 → 命中候选先过 htmlIdxSet（产物 data-idx 存在集），自然落到下层真按钮（2026-09-17 修复后 1652→1583 计划/3133 注入） |
| **中文板点击跳 English 板**（R5 热区映射） | 墨刀 toCanvas 记录的是当初定义交互的那块语言板，复制到其他语言板时目标不换 → 目标解析语言同名板优先于原 cid 板（实测 Ludo 中文板点商城曾跳 English 板） |
| **断言「完整 URL 比对」仍误报跳转失败** | 完整 URL 还要**编码归一**：file:// 下 location.href 是百分号编码（中文→%E4%B8%AD…）而 Node 侧 expect 常是未编码/encodeURI 形态 → 双方都过 decodeURIComponent 再比（2026-09-17 R5 验收实锤：落点明明正确连续两轮误报）。更稳做法：期望值在页面内 `new URL(href, location.href).href` 解析（同 Chrome 编码形态），跳转后直接比 location.href |
| **中文/阿语板功能按钮整板点不动（R5 zone 零绑定）** | 功能入口热区只在当初定义交互的语言板（通常 English）上有；复制板 zones[板cid] 里只有 tab 栏热区（被 R1 覆盖）→ 整板零 zone。跨板镜像三轮配对（同指纹坐标/同指纹 y 序 zip/跨形态尺寸序），详见 add-interactions 契约（2026-09-17 Ludo 中文板 Quests 实锤） |
| **R5 绑定落在角标/红点上（「绑到了徽标的5上」）** | 择优「取 z 最高」系统性选中角标——永远浮在按钮右上最上层（7×14px「5」全站 20 处错绑）→ 热区内全部合格候选同绑（底板/图标/文字/角标都是交互组成部分）；角标绑定目标=按钮目标即正确 |
| **镜像绑定的 href 语言错位（中文板跳 English 板）** | 基准板锚点的 href 是其语言对齐成品，直接抄不带语言 → action 存 tgtPage 页引用，接收板 boardHref(接收板名) 重算 |
| **RTL 阿语板镜像配对跳错功能（任务图标跳排行榜）** | 跨形态三轮尺寸序配对时，同图标位多层锚点+同 y 双功能列（Quests/Rankings 都 24×24 y210）贪心必抢错 → y 平手歧义挂起 + RTL 定向（几何投票/板名含阿文）后改选反侧锚点；错绑比不绑糟 |
| **阿语板图标 svg 指纹全找不到** | RTL 板图标是 img 切图形态、EN 板是内联 svg——跨形态指纹互斥。图标指纹体系三载体：svg normalize / img 切图 URL / bgi（img 节点的视觉字段是 n.img，bgi/name 都不是） |
| **按钮文案折两行（Start Matchmaking 实锤）** | 文本框画窄的稿子失误：est 超框、墨刀里就两行（textH≈2.4×lh），但同按钮其他状态板文本框就是一行宽——设计意图一行。产物侧规避：最紧包含底板能容纳单行（est≤底板宽×1.05）→ nowrap + 垂直居中 + 拉宽行数基准强制 1（见「生成 HTML 形态」⑤）；底板放不下=真窄按钮保持折行 |
| **Cancel Matchmaking 无交互（t=2 热区全站裸奔）** | 墨刀 t=2 无目标 tap =「返回上一页」交互（全站 308 条全无目标），R5 原来只处理 t=1 跳页 → 底部取消/右侧关闭位全没绑（R2 只救左上箭头）。修复：t=2 命中绑 history.back（kind=goback）+ 同页兄弟板 t=2 热区跨板复用（返回与语言无关、复制板保位；纯 bg 底板+文本按钮无指纹，镜像永远配不上） |
| **中文板主 CTA 裸奔（「开始匹配」10+ 板）** | t=1 跳页热区只画在 EN 板，R5 跨板复用原来只开 t=2 → t=1 也复用（借用目标 zoneHref 接收板语言对齐；子代理全站排查实锤）。另 mirror 指纹配不上纯 bg 底板+文本按钮——跨板复用后该形态由几何命中直接覆盖 |
| **注册/重置密码返回键 `‹` 不绑** | 窄文本条 json w=6.7 被 w<12 尺寸下限全排（产物拉宽后 13px）→ 有文本且 h≥16、w≥4 的窄条放行 |
| **弹窗整块点不动（观众头像弹窗）** | 整体关闭热区（278×352）只压到大背景层，被「面积≤热区×3」排除 → ≥120×120 热区的蒙层通道：节点盖住热区九成=弹窗蒙层放行（点击关闭=返回语义） |
| **表格行按钮裸奔（Leave the Game/Mute/Ban）** | 重叠单向判定：表格行 343×46.5 只 49.4% 落在 175×45 热区内被卡——「热区完全在按钮内」的反向包含不算命中 → 双向 `max(ov/节点, ov/热区) ≥0.5` |
| **商城Shop 系返回/充值入口零绑定** | 母版系板 hotzones y 与板内真值恒差 84px（iPhoneX 状态栏帧偏移，x 逐像素一致）→ 原位零命中才 y±84 平移重试（防误绑），命中同样过全部过滤 |
| **中文板跳 English 板但目标页有中文板** | 目标页板名带复制序号「中文 2」，语言对齐精确等值落空回退 bs[0]=English → 剥尾数字匹配（langMatch / zoneHref 同步） |
| **产物 grep 按钮文本查不到绑定** | 两个形态坑：大小写（首页按钮是「Create room」小写 r）、`&amp;` 实体（「Close & Start Playing」在 html 里是 Close &amp; …）——排查时统一解码+忽略大小写再比 |
| **R6 与 R5 同按钮撞车** | 设计行为：R5 热区先绑的保留（有源数据语义优先），R6 `actions.has` 跳过只补裸奔；验收断言 nav 白名单含 zone/flow/goback/cancel |
| **升级弹窗右半优化版按钮无节点可绑** | 稿子层问题：板宽 375 装了 750 内容（左原始版+右优化版拼接），gen-html 只渲染画布内 → 右半 Claim Rewards 等全不在产物。记录待源稿修，交互层无从绑 |
| **验收脚本 evaluate 全返回 undefined** | CDP Runtime.evaluate 响应形态 `{id, result:{result:{value}}}`——裸写 ws 客户端取 `r.result.value` 是 undefined（技能 cdp.mjs 已封装对，自写探针必踩）；另有 headless chrome 残留实例占端口：换端口 + target 匹配用 decodeURIComponent(url) 且收紧到唯一尾段（error page 的 URL 也含同名目录片段） |
| 缩放退化 screenW<80 | 仅 offsetWidth（布局真值）与 rect 双退化才弃板；rect 单缩（分组缩略容器 transform 压扁）换算有效放行（见 SKILL 生成规则⑤） |
| 中文/阿语文件名 | sanitize + localeCompare 排序 |

## 自检清单（每批跑完）

1. `node audit.mjs <outRoot>` 全平（孤儿/缺失/失败/blob 残留全零）
2. **`node audit-style.mjs <outRoot>` 圆角覆盖率 100%**（父链有 br 且画布内的 img，产物必须带 br——2026-09-16 教训：圆角坑在 SKILL 记了两轮仍静默丢 3000+ 处，因为验收断言没有样式保真维度；**记录的坑必须配机器断言，否则「记录」只是记录**）
3. `_index.html` 能开、文件数 = 预期板数，空页/失败页有占位标注
4. 抽 1~2 板：`.stage` 尺寸 = 墨刀画布尺寸；带文字节点可见性断言（rect 有尺寸 / 无 hidden / 文字色≠背景色）全过
5. clip 截图（按 .stage rect，勿全 viewport——body 空白会误判「内容缺失」）对比墨刀原图（视觉对比归人工，程序只做断言）
6. grep 产物无 `blob:`、无 `InteractionMarker`
7. **跑过 add-interactions 后死链断言必须 0**（全产物 onclick 的 location.href 目标文件全部存在）+ 浏览器抽测四类绑定各 1 例真实点击跳转生效——**必须 Input.dispatchMouseEvent（走命中测试），el.click() 绕过命中测不出覆盖层拦截**（2026-09-16 实锤：程序 el.click() 全绿、用户真实点击全死，三层覆盖问题只有 Input 路径暴露）；跳转断言比对**完整 URL**（目标与来源常同名 English.html，按文件名对比有歧义）
8. **汇报口径与记录一致**：跑批/审计里记过的问题（如问题报告条目）在向用户汇报「完成」时必须逐条对齐，未解决的要如实列出——不许记录和汇报两张皮
