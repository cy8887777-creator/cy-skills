# 回装操作手册（第 4 步专用）

静态页 → **回装进原产物**（同文件多风格卡）的完整链路。**动手前通读本文**；坑表在最后，每条都是真实事故换来的，撞一次返工一轮。
多风格机制正本=主管线 `references/multi-style-spec.md`（v2 屏集合组架构：data-style-id 独立屏集/CSS 挂域/sprite 前缀红线/受控块合并/页数跨风格不守恒）；注入工具=主管线 `scripts/editor_inject_style.py` 同源（主干机制逐字同步；**本包副本多 asset-mode 外置 CSS 分支**——客户产物形态，主管线 2026-11-24 已回灌）。

> 编号说明：本文「第 1-11 步」是回装链自身的命令序列编号，独立于 SKILL.md 四步流程的编号——本文全部发生在 SKILL.md 第 4 步内部。
> 路径约定：`<产物工作目录>` = `rebuilt/build-work/`（fragments、令牌双件、开工说明、qa 回执全落这里）；`<SKILL>` = 本技能包根目录。以下命令都在客户项目空间执行。
> 运行方式：常规 `python 脚本.py` 即可；**禁 `python -I`**（隔离模式不把脚本目录加入 sys.path，兄弟模块 import 全崩——K 口径实测）。

## 前置

- 页面清单从原产物 `index.html` 读：壳左侧导航树即页面清单（含分组与顺序）；产物内还有 `<script type="application/json" id="prototype-start-doc">` 等契约块可交叉核对。产物为主管线所产时此读取方式必成立；若产物来自其他工具（无壳导航树），以产物实际页面结构为准整理清单（样章卡代表页的"首页必含"改为"入口页必含"），并在交付说明声明。
- **片段命名**：**片段文件名必须 `page-<屏id>.html` 前缀**（gen_tokens/gen_claims 只处理 `page-*.html`——屏 id 本身可任意如 `p01-login`，但文件名不带 `page-` 前缀 = claims 0 条+值域扫描扑空，2026-11-23 端到端实测踩坑两次）；界面可见名一律中文（build 命名门禁）；占位屏（被引用未转化的目标屏）页名带**"（待迁移）"**——机检与走查靠这个标记自动排除占位屏。
- **回装目标=原产物 `index.html`**：注入器自动备份（同目录 `.bak-<时间戳>`），跑坏还原备份即回单风格原状。重跑注入前**先还原备份再注**（对已含双风格的产物重复注入会撞重复 style-id/eid——注入器会拒绝，正确姿势=还原后重来）。
- 新风格 style-id 口径：`db-<风格id>`（^[A-Za-z0-9_-]+$，与 REGISTRY.domBases/family.domBaseId 同值域）；`--src-db` 缺省 db-main（原风格屏回填的 `data-style-id` 标记值）。

## 三份账（转前必建，验收的尺子）

> 【适配注记】本节自主管线转化规范逐字搬入；账本落 `<产物工作目录>/accounts/`（=rebuilt/build-work/accounts/）。本包静态稿令牌第 2 步已冻结（palette.json），账 3 通常只补扩展键与值域——但账 1/账 2 每次转化必建。

**转化不是无损转换，是"自由 CSS 表达"翻译成"受控令牌/组件包表达"。损耗必然，策略=损耗账面化：转前建账、照账转化、转后对账、对不上走例外。** 脚本不许吃源文件自作主张——只执行人工签过字的账。

1. **特征样式清单**（accounts/feature-inventory.md）：逐条列材质/几何/色值/字体/动效，每条标注表达判定——token（令牌可表达）/自由CSS（原样保留）/例外（表达不了，登记边界）。
2. **交互映射表**（accounts/interaction-map.md）：源标注→data-on 映射逐条列；机械映射人工核对后脚本只执行表；无业务落点的可点元素**不发明交互**，防过度转化断言（decorative guard）。
3. **令牌对照表**（accounts/token-map.md）：正本槽映射（token-keys.json 逐字）+扩展键（表外语义色→`--sp-<键>`）+值域登记（design-system JSON 项目版）。

## 命令序列（按序执行，每步过了才进下一步）

1. **拆屏转化（必带 --db，CSS 挂域）**：
   `python <SKILL>/scripts/editor_convert.py --src <静态页html> --out <产物工作目录>/fragments --screens <页id=标题,...> --groups "<组名:页id,页id;组名:页id,...>" --colors <colors.json> --ext-keys <ext-keys.json> --db db-<风格id>`
   ——拆屏+交互标注+CSS 域前缀（`.screen[data-style-id="db-<风格id>"]`——**连写**：data-style-id 挂 .screen 自身，带空格=后代选择器永不命中、变量全灭（坑 K16）；多风格隔离的根基，**漏 --db 会被注入器拒绝**）+内联颜色 var 化；旁批 aside.anno 同步转 `data-note`；BASE_PATCH/:root 兜底随 --db 域化（防跨域泄漏）。**转化损耗明示**：转化器只映射两类交互——`data-go`（→data-on goto）与筛选 chips（`fchip`→运行时选中态组）；**`data-sheet` 弹层与 `data-seg` 分段的交互转化后消失**（样式保留、行为没了）——画师标注了弹层/分段的页面，转化后交互以静态展示登记例外（或转化后手工补壳交互），禁静默丢。图片走 `assets/images/` 约定路径（转化器只内联该前缀的 src；源稿用 `assets/img/` 等其他目录时先改名）。`--screens` 每段可带第三段 `页id=标题=说明`（说明可选）。`--groups` 按导航菜单结构分组（底栏/侧栏菜单名即组名，非业务域）。**片段改名（必做，转化后立即）**：转化器落盘文件名=`<屏id>.html`，而 gen_tokens/gen_claims 只处理 `page-*.html`——把每片段改名为 `page-<屏id>.html`（**section 内 data-screen 不动**：claims/契约的 page 保持语义 id 形态，与第 6 步样例 path `…/page-<屏id>.html` 对齐；漏改=值域扫描扑空+claims 0 条）。
2. **令牌骨架**：
   `python <SKILL>/scripts/editor_gen_tokens.py --pages <产物工作目录>/fragments/pages --out-dir <产物工作目录> --palette <palette.json> --colors <colors.json> --ext-keys <ext-keys.json> --title <产品名> --pack-id <风格id>`
   ——palette.json = SKILL.md 第 2 步落盘的令牌集（`rebuilt/intake/palette.json`，`--palette` 直通填槽）；骨架产出 **`design-system-converted.json` 与 `style-blocks.json`**（第 4/6/7/8 步都用这两个实际文件）。骨架含 **TODO 占位槽**：`--palette` 没覆盖的槽按第 2 步归纳的令牌集**逐槽填完**再继续——拦截机制有三：片段里的硬色值/物理值会被 lint 归因失败拦下（坑 K3 口径）；gen_tokens 结尾打印的待填清单是人工兜底清单；verify_blocks 会拦 style-blocks packs[].tokens 里的 TODO（E-PACK-TODO，2026-11-23 端到端实证后加入）——design-system 语义槽的 TODO 仍只有 lint 拦，别指望单道闸。另注意：圆角类页面变量（--sp-radius-sm/--radius 等）构建令牌块只发 --radius-2 值域形态，**radius-sm/md 缺静态值会落回种子默认 8/14px**——把真实圆角值写进 ext-keys 静态兜底，页面 CSS 统一用 --sp-* 形态引用。**一切令牌槽同理（2026-11-24 uni-ui 实测升级）**：palette/ext-keys 没覆盖的槽会静默落回种子默认（实例：hero 文字色/圆角档落回种子值=静态稿白字变产物深灰字、16px 圆角变 10px）——gen_tokens 结尾待填清单**逐槽裁决**（填真值或登记豁免），漏网的由渲染对账门（第 10b 步）暴露。
3. **撞车检查**：
   `python <SKILL>/scripts/editor_check_collisions.py --src <静态页html> --runtime <原产物index.html> --screens <页id,...>`
   ——`--runtime` 传**原产物的 index.html**（编辑器运行时类的参照正本；缺省路径在本包无文件，必须显式传）。清零才继续。
4. **lint 清零**：
   `python <SKILL>/scripts/lint_tokens.py --design-system <design-system-converted.json> --style-blocks <style-blocks.json> <产物工作目录>/fragments/pages`
   ——报的每条要能定位到具体行；整串归因说明写法有误（坑 K3），修写法不修归因。两侧 `--design-system` 都禁省略：build 侧省略会静默回退包内默认资产（"清晰企业应用"）；lint 侧省略退化为只查物理白名单，归因检查静默失效。
5. **claims 生成**：
   `python <SKILL>/scripts/editor_gen_claims.py --pages <产物工作目录>/fragments/pages --out <claims.md>`
   ——产出**围栏文本**（markdown，内含 ```interaction-claims 围栏），不是 JSON；每条断言自带 claimId/expect/featureIds 三字段，featureIds=`f-<eid>` 指向契约 feature。真实跑通的单行样例（字段与 prototype_contract 校验逐字对齐；**缺 claimId/expect = E-CONTRACT-SCHEMA，缺/空 featureIds 或引用未声明 feature = E-CLAIM-REF-UNKNOWN**）：
     `{"page": "p01-login", "eid": "p01-login-act-01", "action": "goto", "steps": [["click", "p01-login-act-01"]], "assert": ["selector:.screen.on[data-screen=p03-home]"], "claimId": "c-p01-login-act-01", "expect": "点击 p01-login-act-01 后激活屏 p03-home", "featureIds": ["f-p01-login-act-01"]}`
   （claimId 只要求非空+全局唯一、形态不限——gen_claims 默认产 `<页id>-cNN` 序号形态，上例为手工形态；硬约束是 eid 与 featureIds 的 `f-<eid>` 对应关系。）
   `--guard` 为可选追加断言（必须带值，如 `--guard "page-home:.sel-x"`）；注意 guard 条目当前全链按 decorative 登记不执行——防过度交互靠人工走查兜底。
6. **开工说明组装**（第 7 步 U2 终检 `--start-doc` 与第 9 步真点验证的输入，本步产出）：
   在 `<产物工作目录>/开工说明.md` 按此最小结构组装：
   - 头部：产品名、新风格名与风格提示词来源（wiki 卡 id）、页面清单（与第 1 步 `--screens` 一致，页面数守恒基准）；
   - ` ```prototype-contract ` 围栏一段。**原产物 docs/ 有该围栏**：复制并按新风格改写（页面 id 与 features 一一对应，禁增删页）。**没有时**（旧版产物常见）以 `scripts/prototype_contract.py` 的 schema 为正本自造，最小样例（两页，**字段与校验器逐字对齐+实测跑通版**——schemaVersion=1、device ∈ mobile/tablet/desktop、**每页必带 path**（fragments 相对路径，缺=E-ID-PAGE-UNDECLARED）、features 归页且 kind ∈ interactive/display、**exceptions 条目六字段**（id/page/target/property/reason/confirmationRef，可为空数组但键必须在））：
     `````
     ```prototype-contract
     {
       "schemaVersion": 1,
       "revision": "yueli-limegang-r1",
       "pages": [
         {
           "id": "p01-login", "path": "销售主链路/page-p01-login.html", "name": "登录", "device": "mobile",
           "responsibility": "授权账号登录入口与忘记密码提示",
           "features": [
             {"id": "f-p01-login-act-01", "kind": "interactive", "desc": "登录进入首页"}
           ]
         },
         {
           "id": "p03-home", "path": "销售主链路/page-p03-home.html", "name": "首页", "device": "mobile",
           "responsibility": "营生概况与快捷入口",
           "features": [
             {"id": "f-p03-home-act-01", "kind": "interactive", "desc": "查看客户跳转"}
           ]
         }
       ],
       "exceptions": [
         {"id": "ex-p02-sheet-01", "page": "p01-login", "target": ".lp-forgot", "property": "interaction",
          "reason": "弹层交互转化后消失（转化器只映射 data-go），登记静态展示", "confirmationRef": "用户裁决 2026-11-23"}
       ]
     }
     ```
     `````
     （注意 `"path"` 键**只写一次**——端到端实测出现过重复 path 键的手滑，JSON 能跑但脏。）
     pages 数与第 1 步 `--screens` 严格一致；features 逐条 `f-<eid>` 声明——**与第 5 步 claims 的 featureIds 一一对应（含 guard 条目的 `f-guard-<页id>` 也要声明，缺了契约校验报 E-CLAIM-REF-UNKNOWN）**；
   - `## 6 真点断言` 一节：把第 5 步 `claims.md` 的 ```interaction-claims 围栏整段嵌入。
   缺围栏会被构建前检查拦（E-CONTRACT-FENCE-MISSING）。
6b. **契约校验（独立 CLI，别跳过）**：
   `python <SKILL>/scripts/prototype_contract.py <产物工作目录>/开工说明.md --pages <产物工作目录>/fragments/pages`
   ——**build 正式构建不深校验 claims 字段**（违规进 badLines 不拦截），本 CLI 是契约+claims 的唯一硬闸（exit 0=有效 / 1=契约或 claims 违规，逐条 ruleId:file:line）；过 0 错再进第 7 步。
7. **造回执对**（回装链语义：U2=注入前 fragments 终检必过；U1 随交付归档）：
   - **U2（先造，顺带构建前终检）**：
     `python <SKILL>/scripts/build.py --check <产物工作目录>/fragments/pages --start-doc <开工说明.md> --phase final --design-system <design-system-converted.json> --style-blocks <style-blocks.json> --report <u2.json>`
     通过则产出 `u2.json` 且报 findings 统计；有 error 先修页再重跑。
   - **U1**：
     `python <SKILL>/scripts/qa_receipt.py --make --station U1 --kind check --result passed --inputs "<开工说明.md>,<fragments目录下全部html>,<SKILL>/assets/runtime-contract.json,<design-system-converted.json>,<style-blocks.json>" --out <u1.json>`
   - `--inputs` 一律**相对路径**书写，`runtime-contract.json` 先拷本地副本再引——bash MSYS 会把绝对路径 `C:/` 改写成 `C;C:\Program Files\...`（坑 K12），命令示例中的 `<SKILL>/assets/...` 占位同样按此处理。
   - 两份回执落 `<产物工作目录>/qa/`。
8. **注入回装（替代 build 的组装步）**：
   `python <SKILL>/scripts/editor_inject_style.py --target <原产物>/index.html --fragments <产物工作目录>/fragments/pages --style-blocks <style-blocks.json> --db db-<风格id> --pack-id <风格id> --screens <前缀化后页id,...> [--src-db db-main] [--cover <封面文件>] [--src-shot <原风格截帧>] [--src-pack-id <原包id>] [--out <输出路径>]`
   ——`--screens` 传**前缀化后**页 id（`<风格段>-<语义id>`，风格段=`--db` 去 `db-` 前缀，如 `polaris-p01-login`；注入器按前缀化清单严格对账，传语义 id 会被拒绝）。注意与第 1 步同名参数（语义 id）语义不同。
   **封面注入（用户裁决 2026-11-23：面板卡缩略禁色板条降级）**：`--cover` 传新风格封面（库卡=选型时存档的 wiki `cover.svg`，见 selection.md ⑥；自创=手绘程序化 SVG），注入器转 data URI 填新 pack.screenshot；`--src-shot` 传原风格截帧图（playwright 对单风格原状备份截设备框内画面，jpeg q40 即可）、`--src-pack-id` 传原包 id，注入器填原 pack.screenshot——两张卡都必须真图。
   ——自动备份原产物（同目录 `.bak-<时间戳>`）→ 屏对账（新风格页 id 必须带风格段前缀、与原风格页 id 全局唯一；**页数跨风格可不守恒**——各风格按自己的布局语言组织页面，多/少都合法，对账结果登记交付说明）→ **v2 屏集合组注入**（新风格 fragments 生成 `section.screen[data-style-id="db-<风格id>"]` 列表 append 到 canvas 末尾（初始隐藏，壳接管显隐）；源屏回填 `data-style-id="db-main"`；**无屏内容器**——v1 的"每屏双容器"已废弃）→ 源屏与新屏 CSS 按 `[data-style-id]` 挂域+eid/sprite 按包前缀 → pageTree 单映射扩分组表并追加新风格段（左树随风格整套换）→ 受控块合并（STYLE-REGISTRY.domBases/families/STYLE-PACK.packs/COMPONENT-PACK 追加，id 全局唯一查重）→ 自检（style-id 屏集统计、四块 JSON 可解析、CSS 括号配平）→ 落盘。机制正本=主管线 `multi-style-spec.md` v2（屏集合组架构，页数不对称是合法场景）。
   **非法输入具名拒绝**（至少六类：受控块不齐/packId 撞/familyId 撞/eid 撞/片段无域前缀/重复 style-id；此外 domBaseId/组件包 compId/sprite symbol 撞、goto 跨段引用、v1 双容器形态、对账不符同样具名拒绝）——撞了就还原备份重来，禁硬绕。**字体注意**：新风格 woff2 手动拷进原产物 `assets/fonts/`（注入器不拷字体文件，只搬 CSS）；@font-face 的 url() 引用路径按原产物 assets 相对位置书写。U1/U2 回执（第 7 步产物）随交付说明归档——回装链的质量关=U2 终检+注入器自检+第 9/10 步真点对账。
9. **真点验证**：
   `node <SKILL>/scripts/verify-interactions.mjs <产物index.html> <开工说明.md>`
   ——第二参数是开工说明（脚本从中读 ```interaction-claims 围栏；传第 5 步的 claims.md 也可，脚本会整篇扫描）。无 playwright 时降级：`node <SKILL>/scripts/verify-interactions.mjs <产物> <开工说明.md> --allow-dom-fallback`（DOM 断言模式），仍不可用退 `node --check` 全部运行时 JS + 交付说明注明"未做真点验证"。
10. **截图对账**：
    `node <SKILL>/scripts/editor_shoot_compare.mjs --src <静态页html> --built <产物index.html> --out <截图目录> --screens <页id1,页id2,...>`
    ——与 preview 逐屏目检。playwright 不可用则跳过（脚本给出可读报错），让用户开浏览器抽页看并在交付说明声明。
10b. **渲染对账门（强制，交付回执链硬项）**：
    `node <SKILL>/scripts/qa/acc_render_diff.mjs --src <静态稿index.html> --built <产物index.html> --db db-<风格id> --out <产物工作目录>/qa/render-diff.json`
    ——静态稿为基准逐屏计算样式差分（按单类聚合值集对账；壳包装/svg 子树/旁批 aside 自动豁免）。**前置：产物须处于新风格激活态**（`--active-pack=新风格` 构建，或载入后先点新风格卡——否则 B 屏 var() 消费原风格根变量=大面积假差异；脚本读 state.domBaseId 守门，不符拒报 exit 2）。**机检/撞车/U2/回归全是机制回执，只有这道门拦得住"选择器未命中/变量死/种子回退"类渲染退化**（2026-11-24 uni-ui 实测：chips 竖排、hero 蓝底深字、圆角 16→10 全是此类，人眼之外无一关卡住——门还多照亮 199 条同类潜伏退化）。exit 0=零差异；exit 1=有差异，**差异清单即工单**（≥200 条自动截断——修一批重跑见余量），逐条归因修根因后重跑归零；exit 2=playwright 不可用/目标打不开/前置不满足，按降级口径处理并声明。单屏采样上限 400 元素，触顶屏记入 report.truncated（覆盖不全明示，不算 FAIL）。
11. **交付**：交付物=**回装后的原产物文件**（不产新文件）。交付说明必含五项：①页面数对账结果+补页清单（铁律 3 口径：每风格对齐供料底线，**跨风格页数可不守恒**，v2 架构合法场景）；②跳过了什么/未验证项；③风格卡形态（面板 Tab1 新卡：**真封面**——库卡 wiki cover.svg/自创手绘 SVG/原风格截帧，色板条降级=封面链失败要查）；④口令提醒（产物编辑口令默认 12345678，提醒用户交付前修改）；⑤**回退指引**（同目录 `.bak-<时间戳>` 还原即回单风格原状；**还原后把 `.bak-<时间戳>` 改回 `.html` 后缀才能 file:// 直开**——Chromium 不按 HTML 渲染未知后缀）。
   **交付前一键回归自证**：`python <SKILL>/scripts/qa/run_reskin_regression.py <产物.html>`——七项核心（切卡树整套换/隔离/两域真点/curId 重映射/图标往返/页数不对称）+封面供给链（真图×卡数/零色板条）一键全跑，exit 0=全过；playwright 三级探测同「客户环境降级」口径，全落空=exit 2 环境不可用，按上文降级并声明。
   **交付=回执链三件齐，缺一不算交付（2026-11-24 定案）**：①渲染对账门 0 差异（第 10b 步，差异逐条归因修复后复跑归零）；②run_reskin_regression 全绿回执；③交付说明五项齐。**接手/失联收口死规则**：接手代理先对已落盘回执链现状（qa/ 目录三件）再动手；失联代理的落盘改动**逐字 diff 甄别采纳**（对照备份与账目，禁盲信盲弃）；能自己收场的收口不另派代理——子代理不可寻址（发不了消息、停不掉），派收口前先盘点落盘现状。

## 坑表（每条=一次真实返工）

| # | 坑 | 症状 | 防法 |
|---|---|---|---|
| K1 | 运行时全局类污染 | `.hero` 染蓝、`.chips` 强制换行、`.app` 出现间隙、`.viewport` 多垫层、`.flow` gap+padding 被壳样式改写 | 壳全局类与页面类撞名时，以产物实测 computed 为准压回；转化脚本 BASE_PATCH 已处理已知项，新增壳类先查页面类名再上 |
| K2 | box-shadow 正则吞括号 | 阴影整段消失/样式断裂 | 改正则后跑样本断言（含多层 shadow 的页） |
| K3 | lint 整串归因失效 | 报错指不到具体行 | 修 lint 输入写法，禁把整串标成一处 |
| K4 | build 拒绝覆盖旧产物 | "更新"后还是旧内容 | 重构建前先删旧输出目录 |
| K5 | 扩展键构建期不发静态值 | --ext-keys 键在产物中无值 | 键值成对传入，构建后 grep 产物验证 |
| K6 | --active-pack 硬涂 | 初始风格把页面设计盖掉 | 皮肤注入只写根变量段，页面级样式豁免 |
| K7 | 验证视口过窄假阴性 | 长侧栏页真点全超时 | 视口宽 ≥800（脚本已内置 mobile=800） |
| K8 | 壳补丁转义吞 `*/` | 注释提前闭合，JS 全崩 | 改壳/补丁后必跑 `node --check` 字节级自检 |
| K9 | 换肤组件重写层覆盖页面设计 | 换配色后整页变纯色 | 转化标记链（data-conversion）页面豁免组件重写段 |
| K10 | 压回特异性不对齐 | 压回不生效（computed 未变） | 压回选择器与目标同族同构（`.screen .device.mobile .viewport` 三级对齐），改完实测 computed |
| K11 | 壳全局类新成员漏压回 | 壳新增类（如 .statusbar absolute）撞页面 | 壳每次加全局类同步查 BASE_PATCH；产物侧发现重叠先自压回 position:static 类再登记 |
| K12 | git-bash MSYS 路径改写 | qa_receipt --inputs 里的 C:/ 被改写成 C;C:\Program Files\Git\... | --inputs 一律相对路径或 runtime-contract 用本地副本 |
| K13 | 控制台 GBK 编码搅坏中文/反斜杠 | bash heredoc/-c 传中文参数落盘乱码 | 多步脚本一律文件化（写 .py/.mjs 再执行），禁 -c 内联长中文 |
| K14 | 双风格 CSS 互压 | 激活 A 时 B 的颜色/字体渗进 A（反例实测实锤：B 硬值泄漏进 A 域） | fragments 必带 --db 域前缀（第 1 步漏 --db 注入器拒绝）；同名动画名/字体 family 跨风格互压是 CSS 全局语义切不死——命名按风格加段（multi-style-spec.md §二） |
| K15 | 图标 sprite first-wins | 两风格同名 symbol，切换后 use 引用永远指向第一个 sprite（渲染错图） | 注入器按包前缀 symbol id+use 引用同步改（悬空引用=拒绝）；回归必测 A↔B 往返两轮 |
| K16 | 域化选择器带空格 | `.screen [data-style-id=…]` 后代形式永不命中——变量全灭、样式落回种子默认（chips 竖排、hero 蓝底深字、圆角 16→10 同根；uni-ui 2026-11-24 实测） | data-style-id 挂 .screen 自身，**必须连写** `.screen[data-style-id=…]`——convert 生成侧三类四处已修（dom_scope_css 两行+ext-keys 块+幂等输入归一；scope_prefix 原本就连写），手写 CSS 同此口径，渲染对账门（第 10b 步）兜底暴露 |

## 例外机制（对不上的走这里；本节自主管线转化规范逐字搬入）

编辑器表达不了的：不硬凑。两条出路——自由 CSS 层原样保留（lint 不检的属性如 mask/backdrop-filter/keyframes）；真表达不了的登记交付边界（"这项在编辑器版里的形态是 X"）。**交互降级类例外（如筛选真过滤→选中态）必须报用户拍板，不许脚本自行决定。** 例外清单超过两屏 CSS 总量两成 = 映射策略不成立，停工重议。

## 旧版运行时产物（存量产物无多风格机制）

**判据（注入器已内置入口检查，撞上会具名拒绝并打印本节指引）**：目标产物 `applyDomBase`/`style-chooser`/风格面板机制 0 命中=旧版运行时——数据侧注进去也没人消费（uni-ui 实测：注入"成功"、真点 90 条 0 过、切卡恒 50 节点）。**asset-mode 产物**（`--asset-out`，运行时外置 `assets/js/`）注入器会连外置脚本一并扫——外置亦 0 命中才判旧版（standards 审查实证修复：html 内 0 命中不等于运行时缺失）。

**A 重建运行时再注入（标准步骤，经用户裁决授权后走）**：
1. 授权口径先讲明：产物 index.html 与 assets/ 会被更新（现行运行时+现行资产），备份链兜底可回退；
2. **原风格屏保全**：从旧产物 DOM **机械提取**全部原屏（`section.screen` 整段）为基座 fragments（`page-<屏id>.html`，data-name 保留原中文名）——只取结构事实（回装链例外条款），禁当作新风格的布局参照（铁律 3 口径不变）；
3. 用技能包现行 `build.py` 重建产物基座（含风格面板运行时），基座输入=上一步提取的**原风格 fragments**；
4. **主客顺序断言（重建后自检，防主客颠倒）**：原风格屏集合在位且屏数=提取数、applyDomBase/style-chooser 消费者命中、风格面板机制在位——**原风格是基座主卡（db-main），新风格是注入卡**；基座若误用新风格 fragments 重建=原风格丢失，推倒重做；
5. 重跑本链第 1 步起的注入序列 → 真点+回归+渲染对账门全绿 → 交付说明补"A 路径执行记录"。

**C/D 口径**：C=接受现状交付（双风格页树可浏览、无点卡切换，交付说明声明缺口）；D=还原 `.bak` 回单风格原状、本轮作废。三选一必须经用户裁决，禁自选。

## 风格包规格（换肤能力；本节自主管线转化规范逐字搬入）

- STYLE-PACK tokens：正本最小集全量给齐（缺一个键 verify_blocks 就拒）+扩展键；l2Overrides 的 selector 只写页面内组件类。
- palettes 同风格多配色：**第一套=品牌原色**，再按风格气质配 4-5 套跨色相方案（每套四槽 swatches + hero/line/muted 全角色），别只给同色系近邻。
- 组件包 10-15 条（六类覆盖），html 片段遵守片段契约（data-eid/data-block，禁 script）。

> 【适配注记】本包 palettes/组件包由第 2 步 `editor_gen_tokens.py` 出骨架，上三条是**填槽规格**：骨架生成后按此把配色补到 4-5 套跨色相、组件包补到 10-15 条，再进构建——只出一套配色的换肤面板是残的。**换风语境"品牌原色"=冻结风格提示词色彩段的主色实值**（提示词写实值色号，答案唯一出处在此）——**禁向用户索要 VI/品牌色**（问=没读题），原产物品牌色禁读。

## 客户环境降级

- playwright：脚本内置三级探测（本地 → `PLAYWRIGHT_MODULE_PATH` 环境变量 → npm 全局）；全部落空时第 9/10 步按上文降级并在交付说明注明，禁静默跳过。
- 图标族：内置 lucide（铁律 5）；`--icon-families` 是主管线构建组装侧的参数，本回装链不涉及（第 7 步仅 `build --check` 终检，第 8 步注入器按包前缀改写 sprite symbol）。
- 产物 JS 改动后：`node --check` 全部运行时 JS（坑 K8 纪律）。
