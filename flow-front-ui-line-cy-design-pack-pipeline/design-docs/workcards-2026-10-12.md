# 2026-10-12 工卡：codex 三方审核修复 + app2 验收遗留收口（1012-01~09）

> 按天拆分与序号重置：本文件卡号 1012-01~09；1010 批次（5 卡全 [x]）在
> workcards-2026-10-10.md。本批来源两线：
> ①**codex 三方审核**（2026-10-12，用户转交，四点全部核实成立——补页判据
> 超证据能力/⑨后重扫没闭环/视口靠自律/探针接口声称不实）；
> ②**app2 验收遗留**（2026-10-10 验收实锤但未落地的假绿洞——报告后改动/
> 旧报告复用/几何悬空/系统性视觉偏差漏网/零字节截图静默）。
> 用户 2026-10-12 裁定「都改」，按一卡一事拆 9 卡。

状态标记：`[ ]` 待施工 / `[~]` 施工中 / `[x]` 完工。一卡一 commit（中文 message 带卡号）。

## 卡总览

| 卡 | 优先级 | 一句话 | 状态 |
|---|---|---|---|
| 1012-01 | P0 | 视口一致性断言：报告记实际视口+⑩核对 device_profile | [x] |
| 1012-02 | P2 | 探针 stdout 纯净化：摘要迁 stderr+恰一行断言 | [x] |
| 1012-03 | P1 | 补页交互证据链：裁判判据降截图可判+⑨遍历证据接入 | [x] |
| 1012-04 | P1 | ⑨后 style-lint 重扫条款（§8/§10 半句） | [x] |
| 1012-05 | P0 | 报告冻结指纹：src 指纹落盘+gate 核对 | [x] |
| 1012-06 | P1 | evidence_index 时序校验（禁旧报告配新哈希） | [x] |
| 1012-07 | P1 | 几何贴底断言（底部固定元素+跨页壳一致） | [x] |
| 1012-08 | P1 | judge 同屏并排+跨页系统性偏差视角 | [x] |
| 1012-09 | P1 | 执行侧疑点全披露+归因附证硬条款 | [x] |

> **施工顺序（审核修订版）**：01 → 05（两 P0，同动 plan-recon --final
> 须先后）→ 04 → 08 → 09 → 03 → 06 → 07；02 小卡搭任意卡。
> **08/09/03 同动 judge-prompt，顺序施工禁并行编辑**（对齐 1010 批
> 02/03 先例）。**复杂卡四张：01/05/06/07（P0 卡+新机制卡+新断言类型）
> 无条件走测试角色 gate**；其余简单卡三绿。codex 建议的两个反例
> （⑨新增页带违规样式 / 补页按钮无响应）分别作 1012-04/1012-03 的
> 验收动作。
> **首轮审核结果（2026-10-12）**：02/04 放行；01/03/05/07/08/09 修订后
> 放行；06 打回重设计（原 mtime 双时序边界误杀正常链）——以上全部
> 已并入本文件 v2；06 机制选主案「报告内嵌 src_hash」。

---

## 1012-01 [x] 视口一致性断言（报告记实际视口 + ⑩核对 device_profile）

**机制层归属**：断言层。

**现象/根因**：4 验收脚本的 `--viewport` 可省略，省略即静默回 375×812
默认（DEFAULT_VIEWPORT 兜底）——PLAN device_profile 选了 Pad/横屏，验收
仍可能在手机视口下全绿通过。`--viewport` 传参靠主会话读 PLAN 自觉，无
机器断言——违反 1009-01「痕迹断言=机器断言非自律」的自身原则（1010-04
B-1b 亲手证实默认路径畅通）。

**修法**（审核修订版 v2）：
1. 4 脚本（e2e-smoke/exits-audit/route-audit/explore-walk）把**实际
   生效视口**写进各自报告 JSON 顶层（`"viewport": {"width": W, "height": H}`）；
2. gate 挂 plan-recon --final：核对各报告 viewport == PLAN
   execution_policy.device_profile 映射视口档（phone_portrait→375x812 /
   tablet→820x1180 / landscape→1280x800），缺字段/不一致 = FAIL，
   **不设存量过渡豁免**（无真实在飞存量；豁免=重开自律口子）；
3. **plan-recon 需扩展 PLAN 头部解析**（现有 parse_plan_rows 只解析
   页面清单表，execution_policy 解析为新增——防施工者误以为挂点现成）；
4. **explore-walk 补落证据索引 + --required 清单扩入**（三选一裁定采纳
   (a)：它全文无 record 调用，不落账本就是观测层洞，一次补齐——否则
   「4 报告全核对」在现载体下核不齐）；
5. contracts.md C-09「机器核查手段」列同步补「--final 视口断言」。

**本卡 P0 = 复杂卡，无条件走测试角色 gate**（视口断言语义/旧格式拒绝/
explore-walk 落账格式由测试角色定标）。

**验收**：反例 fixture——PLAN device_profile=tablet 但报告 viewport
375x812 → --final FAIL；一致 → PASS；缺 viewport 字段 → FAIL；4 报告
JSON 含 viewport 字段（fixture 断言）；explore-walk 落账且 --final
可消费。codex 复核点：防「参数加了没人传、默认值静默兜底」型假绿。

**来源**：codex 三方审核（2026-10-12）点 3。

**测试标准定稿（2026-10-12，测试角色协商稿经主代理裁定 10 项）**：
- **共享规范 S1**：报告 JSON 顶层 `viewport`（4 playwright 工具必填，
  style-lint 无浏览器豁免——plan-recon 核对按豁免集 `{"style-lint"}`
  跳过）+ `src_hash`（06，五工具必填）；S2 账行 schema 不扩字段（真值
  在报告本体，gate 经 report_path 读报告）；S3 report_path 落账
  resolve 绝对路径；值=parse_viewport 产物（默认兜底路径也如实记录
  375x812——抓静默兜底的关键）；
- **plan-recon**：新增 parse_device_profile（execution_policy 节匹配
  device_profile 行，plan-template 真实形态为 fixture 蓝本，退化形态
  一律 FAIL）；档位映射闭集同 C-09；**--required 默认扩 explore-walk**
  （plan-recon 与 evidence_index main 两处同步，防漂移 grep 点）；逐
  route verdict 查询域维持 ("exits-audit","route-audit") 不变
  （explore-walk 随机游走覆盖不满全集，扩入恒 FAIL——只经 check_all
  走整场断言）；
- **explore-walk**：新增 --src + record 落账（per_id 键=visited 的
  route path，按页归因）；
- **裁定 10 项**：①01 顺带 resolve report_path（06 前置，归属注释）；
  ②explore-walk per_id 按页归因（改游走循环 fail 归属，防回归
  test_explore_walk 全绿）；③e2e-smoke 无 --src 时 record 对齐
  exits-audit fail-closed 跳过（行为变化留痕）；④route-audit record
  target resolve（现状潜在死行 bug 顺带修）；⑤tol=8px 为建议值，
  施工时对 app2 三案例实测后锁值；⑦批末拦截若直读 jsonl 不受 06
  保护——条文补「消费经 latest_valid/check_all 禁直读」；⑧05
  --require-frozen 默认关残险由 §10 清场(c) 条文兜底，不加第二道
  机器防线（接受残险注明）；⑩未知 device_profile 档名=FAIL
  （fail-closed，禁静默跳过）；
- **反例**：F1-F6（01：tablet 配 375 双向/缺字段/无 device_profile/
  未知档名/4 报告字段/explore-walk 落账链）挂 test_plan_recon_final
  扩展+test_explore_walk；
- **防假绿关键**：报告 viewport 值与 browser.new_page 实传同源变量，
  禁两处各算（R4）。

**完工记录（2026-10-13，接手会话续施工）**：
1. **上会话半成品收尾（working tree 既有 diff 核实+修复）**：4 脚本
   viewport 字段/plan-recon 视口断言/explore-walk --src 落账/e2e-smoke
   fail-closed 等 diff 均在位；修复 `plan-recon` **src_h NameError**
   （src_hash 缓存原在视口核对段之后才赋值，--final 必炸——提前至
   final 分支开头）；修复 explore-walk **stderr 非 UTF-8**（Windows
   子进程 GBK 输出致 fail-closed 提示乱码，reconfigure 对齐 stdout
   口径）；
2. **裁定④落地+同族排查**：route-audit record target resolve
   （原文路径与消费端 latest_valid 的 resolve 比对不符=潜在死行）；
   同族排查 exits-audit/explore-walk 已 resolve 无病、**e2e-smoke
   同病顺带修**（eng_src 加 .resolve()）；
3. **测试**：test_plan_recon_final 扩 F1a-F3b 六反例（上会话已写，
   本轮实跑全绿）+ 既有 1009-15 反例不回归；test_explore_walk 扩
   F4/F5（报告 viewport 字段=默认兜底如实记 375x812；--src 真实落账
   链 + latest_valid 消费到 per_id 按页归因的 PASS 行；无 --src →
   stderr 显式 fail-closed）；test_route_audit/test_exits_audit/
   test_e2e_assert 各扩 F4 生产端断言（复用既有 playwright 产物）。
   **受影响用例全量实跑 PASS**（2026-10-13 本机，playwright 真跑）；
4. **卡面验收逐条对照**：tablet 配 375 双向 FAIL/PASS ✓（F1b）；
   缺字段 FAIL 不设豁免 ✓（F2）；无 device_profile/未知档名 FAIL
   ✓（F3a/b）；4 报告 JSON 含 viewport ✓（F4×4 脚本）；explore-walk
   落账且 --final 可消费 ✓（F5）；codex 复核点（防"传参没人传、
   默认值静默兜底"假绿）✓——viewport=parse_viewport 同源产物，
   兜底路径如实记录，⑩核对报告实际值 vs PLAN 档。

---

## 1012-02 [x] 探针 stdout 纯净化（摘要迁 stderr + 恰一行断言）

**机制层归属**：契约层（探针输出接口）。

**现象/根因**：intake.py `--probe` 卡面/docstring 声称 stdout 单行 JSON，
实际 JSON 后还 print 人类摘要行——接口声称与实现不符；test_device_probe
只解析第一行所以未抓到（codex 指实：intake.py:110 附近）。

**修法**：人类摘要行改走 **stderr**（stdout 纯 JSON；机器解析与人读
两不误）；docstring/卡面措辞同步「stdout=单行 JSON，stderr=人类摘要」；
**probe 错误路径两处 stdout 文案同步迁 stderr**（审核建议采纳——否则
失败路径 stdout 口径仍脏）；test_device_probe 补断言：stdout 恰一行且
json.loads 可解析。

**验收**：新断言绿；全量套件绿。

**来源**：codex 三方审核点 4（小实错）。

**完工记录（2026-10-13，接手会话施工）**：①intake.py 三处 print 迁
stderr（成功路径人类摘要/空图包错误/目录不存在错误）+ docstring 写明
接口口径「stdout=单行 JSON（机器解析唯一对象），stderr=人类摘要与错误
提示」+ stderr reconfigure UTF-8（对齐 1012-01 explore-walk 同族口径）；
②test_device_probe 扩 3 断言：成功路径 stdout 恰一行且整体 json 可解析
（比原 jout 只解析第一行更强——人类摘要混入即 FAIL）+ 摘要文案在
stderr + 两条错误路径 stdout 空且文案在 stderr。**test_device_probe
全量实跑 PASS**（2026-10-13 本机，含既有 F1-F15+A/B 系不回归）。

---

## 1012-03 [x] 补页交互证据链（裁判判据降截图可判 + ⑨遍历证据接入）

**机制层归属**：断言层（判据与证据能力对齐）。

**现象/根因**：judge-prompt 产品验收官分支（1010-03 升级版）要求判
「交互全可点且有可见反馈」，但裁判输入只有成品截图/推导布局文档/PRD——
**静态截图无法证明点击有效**，判据超出证据能力；codex 反例「补页按钮
无响应」按现条文裁判判不住。

**修法**（两道防线分工，禁合并；审核修订版 v2）：
1. **裁判判据降为证据可支撑口径**：功能维度改「交互入口齐备且语义
   完整（截图可判）」——入口在不在、语义对不对归裁判；点没点得动
   不归裁判（判据句子与输入能力对齐）；
2. **交互有效性=⑨自测遍历证据**：载体事实更正——「synthesized 补页
   视为已存在目标，正常接线」句实际在 **station-guide §9c**（非
   wiring-prompt，其只有合议补页触发句）；遍历会真点补页交互；⑩补页
   验收行（验收矩阵「补页可用性」）显式要求**「在案」=⑨自测报告含该
   补页交互清单遍历结果 + exits-audit 索引该补页 route 的 verdict
   在册**（点击无反馈=FAIL）。本卡真实增量在**非出口类交互**（页内
   开关/toggle——exits-audit 对声明出口本就物理点击）；「补页按钮
   无响应」反例由这道防线抓；
3. judge-prompt 与 station-guide 两处条文同步改，防两任务书口径漂移；
   推演判定主体=复审代理。

**验收**：grep 两处条文；codex 反例推演（补页按钮无响应 → ⑨遍历 FAIL
可抓、裁判不再被要求判不可判项）。

**完工记录（2026-10-12）**：①judge-prompt 产品验收官功能判据改「交互
入口齐备且语义完整（截图可判）」+点名有效性归⑨遍历/exits-audit/
contracts-lint 三道机器兜底；②station-guide「补页可用性」行补真值列
（⑨自测报告遍历结果+exits-audit verdict 在册=「在案」定义）与真实
增量定位（非出口类交互）。grep 两处在位 ✓；codex 反例推演留复审。

**来源**：codex 三方审核点 1。

---

## 1012-04 [x] ⑨后 style-lint 重扫条款

**机制层归属**：断言层（触发时序）。

**现象/根因**：1010-05 只写「批末全扫范围含⑨新增页」——**能扫到 ≠
实际跑过**：⑧批末跑的报告对⑨补页是旧的。终验 src_hash 时序兜底存在
（工程变更后旧 PASS 无效），但 §8/§10 条文表述会误导执行端「批末跑
一次即完事」（codex 指实 station-guide.md:230）。

**修法**：station-guide 一致性维度行（矩阵行本身在 §10 内，行内补句
即可）补半句：「⑨有新增/补全页 → ⑩全扫前必须重跑 style-lint
（1009-01/15/17 三层时序断言使⑧批末旧报告自动失效）」——把隐式兜底
显式化为规定动作。

**验收**：grep 条文；codex 反例推演（⑨新增页带违规样式：未重扫 →
src_hash 失效 FAIL；重扫 → 抓出违规——两条路都通向正确结论）。

**来源**：codex 三方审核点 2。

**完工记录（2026-10-12）**：station-guide 一致性维度行补「⑨有新增/
补全页 → ⑩全扫前必须重跑 style-lint」+三层时序断言依据注明（v3 复审
建议的精确化引用）。grep 验收：条文在位 ✓。codex 反例推演留复审。

---

## 1012-05 [x] 报告冻结指纹（src 指纹落盘 + gate 核对）

**机制层归属**：断言层。

**现象/根因**：交付报告出具后工程仍可被改动而报告数字不失效——app2
实证（2026-10-10）：base.css 晚于 DELIVERY.md 16 分钟被改，四份验收
报告全部不覆盖最终工程态，「数字=最终工程态」靠执行端自觉。1008-03
有「报告出具后再改动必须重跑」条款但**无机器断言**。

**修法**（审核修订版 v2）：
1. ⑩出具交付报告时对工程 src/ 全量内容指纹落盘
   （`pipeline/frozen-src-fingerprint.json`）；**指纹算法必须与
   evidence_index.src_hash 同口径**（单一口径防两套哈希对不上账；
   文件清单仅作诊断信息可选保留）——即清场 (c)「报告数字区标注
   工程内容 hash」的机器可核形态；
2. 交付 gate（plan-recon --final 或证据核对步骤）核对当前 src 指纹 ==
   报告指纹，**不一致 = FAIL**（逼「重跑全部工具重出数字」，对齐 §10
   清场 (c)）；**指纹文件不存在 = FAIL**（未冻结即未完成交付准备；
   正常流程=出具报告时落指纹，不存在合法的无指纹态）；
3. **协同**：与 1012-06 同口径 src_hash；出具报告时同步落指纹+落账
   （时点合一）；
4. 载体施工时定（plan-recon 扩展或独立小脚本），须留痕；定标并入
   测试角色 gate（**定标点名**：报告出具前的首次 --final 运行时点——
   指纹按定义尚不存在，核对与出数须分时点或分开关，禁无开关塞进
   --final 主流程必 FAIL）。
**本卡 P0 = 复杂卡，无条件走测试角色 gate**（指纹口径/缺失语义/核对
挂点由测试角色定标）。

**验收**：反例 fixture——报告指纹落盘后改 src 一处 → gate FAIL；
恢复后 → PASS。

**来源**：app2 验收 A1 实锤（2026-10-10）+ codex 收尾意见「假绿问题
尚未落地应明确列为未收口」。

**测试标准定稿（2026-10-12，测试角色协商稿经主代理裁定）**：
- 指纹文件 `pipeline/frozen-src-fingerprint.json` 最小内容
  `{src_hash, time, note}`——src_hash **直调 evidence_index.src_hash
  单一口径**；文件清单仅可选诊断禁必填；
- **冻结与核对强制分开关（防自洗定标核心）**：plan-recon 新增
  `--freeze-fingerprint`（写指纹+stdout 留痕）与 `--final
  --require-frozen`（核对）**互斥，同给=报错 exit 1**——一跑既冻结又
  核对则每次 --final 重写指纹、改 src 恒一致，机制失效；`--final`
  不带 `--require-frozen` 行为与现状完全一致（报告出具前中间态不必
  FAIL——卡面定标点名项的解法）；残险（没人传 --require-frozen）
  由 §10 清场(c) 条文兜底（裁定⑧）；
- 行为表：一致 PASS / 不一致 FAIL（文案含「重跑全部工具重出数字」）/
  指纹不存在 FAIL / 损坏缺字段 FAIL（fail-closed）/ 空 src 树 FAIL /
  重复 freeze 覆盖+stdout 显式声明（合法新时点动作）；
- 反例 F1-F6 全 fast 挂 test_plan_recon_final 扩展；
- 防回归：test_plan_recon/test_plan_recon_final 全绿；src_hash 禁
  循环内重算（对齐既有缓存纪律）。

**完工记录（2026-10-13，接手会话施工）**：
1. **载体=plan-recon 扩两开关**：`--freeze-fingerprint`（写
   pipeline/frozen-src-fingerprint.json {src_hash,time,note}，src_hash
   直调 evidence_index.src_hash 单一口径；重复 freeze 覆盖+stdout
   显式声明合法新时点；空 src 树 FAIL fail-closed）与 `--final
   --require-frozen`（核对：一致 PASS/不一致 FAIL 文案含「重跑全部
   工具重出数字」/指纹不存在 FAIL/损坏缺字段 FAIL）——**同给=报错
   exit 1**（防自洗定标核心）；`--final` 不带 require 行为与现状
   完全一致（中间态不误伤）；require 核对消费 final 分支开头缓存的
   src_h（禁循环重算）；
2. **条文同步**：station-guide 清场 (c) 补机器化载体句（freeze 时点
   =出具报告时点，与证据落账时点合一；两开关互斥）；
3. **测试**：test_plan_recon_final 扩 F6a（互斥 exit 1）/F6b（首次
   落盘+重复覆盖声明）/F1（一致 PASS）/F2（改 src FAIL 含重跑文案）/
   F3（指纹不存在 FAIL）/F4（缺字段 FAIL）/F5（空树 FAIL）——7 断言
   全绿；既有 01 段六反例+1009-15 全部反例不回归（fixture 复用含
   破坏态恢复：PLAN/报告 viewport 在 05 段开头还原合规态）；
4. **卡面验收逐条对照**：报告指纹落盘后改 src 一处 → gate FAIL ✓
   （F2）；恢复后 → PASS ✓（F6b 重复 freeze 模拟重新冻结新时点）；
   互斥 ✓（F6a）；定标行为表六态全覆盖 ✓（F1-F6）。

---

## 1012-06 [x] evidence_index 报告内嵌哈希校验（禁旧报告配新哈希）

**机制层归属**：观测层（证据账本可信性）。

**现象/根因**：evidence_index.py 登记时不校验 report 文件与 src_hash
的对应关系——旧报告可配新哈希登记（app2 实证：15:10 登记轮的
route-audit/smoke 报告实为 15:05/15:06 产物，哈希与报告内容不对应）。

**修法（审核打回后重设计，v2）**：~~原案 report_mtime 双时序边界~~
**已废**——审核实证三工具均先 record() 后写报告文件（e2e-smoke
L223→229 / route-audit L277→286 / exits-audit L480→488），mtime 上界
恒假；首次登记下界（report_mtime ≥ 首次登记时刻）与「先写报告后入账」
的正常流恒矛盾；mtime 本身受拷贝/git/FAT 2 秒精度影响不可作证据地基。
**新机制（报告内嵌 src_hash，v4——终审残留角补正）**：
1. **覆盖全部落账工具（5 个）**：e2e-smoke/exits-audit/route-audit
   /explore-walk（1012-01 补落账时直接按新序实现）/**style-lint**；
   各工具运行时算好 src_hash 写进报告 JSON 顶层
   （`"src_hash": "<同 evidence_index 算法>"`）。**style-lint 载体
   补正（终审必改，采纳方案 a）**：style-lint 现无报告文件
   （record 的 report_path 传空串，输出走 stdout）→ **新增报告
   JSON 落盘**（--out 参数，内嵌 src_hash），record 改传该路径——
   五工具机制完全统一不留豁免特例，顺带补齐「原始输出有文件可引」
   （对齐交付纪律「原始输出进报告附录」）；
2. **调用顺序改造（复审死角②，机制必要组成）**：现状三工具均为
   先 record() 后写报告（e2e-smoke L223→229 等）——record 时报告
   文件尚不存在，无从校验内嵌哈希。**record() 调用移到报告写盘
   之后**：先写报告（内嵌 src_hash）→ 再 record（record 读报告文件，
   校验「内嵌 src_hash == 登记 src_hash」，不一致/缺字段 → 拒绝
   入账 exit 非零）。行为变化说明：之前 record 失败报告也写；改后
   报告写而拒账——报告在盘、账本拒收，验收端按账本断言即 FAIL，
   语义更严不更松；
3. `latest_valid()` 消费端双校验（账行 vs 报告内嵌哈希，不一致=无效
   verdict）；
4. 旧格式报告（无内嵌字段）按缺字段处理 = 拒绝——不设过渡豁免。
不破坏现有「重跑 PASS 结清旧 FAIL」语义。**本卡为新机制卡，走测试角色
gate**（校验语义/拒绝路径/旧格式拒绝行为/调用顺序改造的回归由测试
角色定标；**定标点名两项**：①record 拒绝路径禁被既有 try/except
静默吞掉——须 stderr 显式报错或传染 exit code；②latest_valid 对
不一致报告的消费语义=视同无记录〔fail-closed 最严〕）。

**验收**：反例——旧报告内容配新哈希登记 → record 拒绝；报告内嵌哈希
与登记一致 → PASS；无内嵌字段报告 → 拒绝；test_evidence_chain 不回归。

**来源**：app2 验收 A2 实锤；v2 机制经 1012 首轮审核打回后重设计
（2026-10-12）。**与 1012-05 协同**：同口径 src_hash 单一口径；出具
报告时同步落指纹+落账（时点合一）。

**测试标准定稿（2026-10-12，测试角色协商稿经主代理裁定）**：
- **record()**：签名不变，行为新增——读 report_path 报告文件，校验
  「内嵌 src_hash == record 自算 src_hash(src)」；不存在/缺字段/不一致
  → 抛 `RecordRejected` + stderr 显式原因（**拒绝路径禁被既有
  try/except 静默吞——定标点名①**）；record 自身 IO 异常维持既有
  「不掩盖主判定」豁免（两语义切割）；
- **调用顺序（五工具统一）**：算 src_hash 一次 → 构造并写报告（内嵌
  同值）→ record（读盘校验）→ stdout 摘要；
- **调用方改造**：`except RecordRejected` → stderr 显式 + **工具
  exit code 置 1**（与断言结果取或）；`except Exception` 维持旧语义；
  两 catch 分层禁裸 except 回退；
- **latest_valid()**：内置双校验——命中账行后读报告，内嵌≠账行/不可达/
  缺字段 → **返回 None 视同无记录，禁向前回退次旧行**（回退=「删新
  报告复活旧 PASS」攻击面，fail-closed 最严=定标点名②）；放
  latest_valid 内部使全部消费方自动获得；
- **style-lint**：新增 `--out` **默认值必死**
  （`<src>/../pipeline/style-lint_report.json`，与账本同目录——缺省
  不落报告则 record 无文件可校验全红）；
- **裁定③④**：e2e-smoke 无 --src 时 record fail-closed 跳过（对齐
  exits-audit 先例，行为变化留痕）；route-audit record target resolve
  （现状潜在死行顺带修）；
- 反例 F1-F6（不一致拒绝/缺字段拒绝/端到端改报告→latest_valid None/
  test_plan_recon_final rec_idx fixture **真实化**/style-lint 默认
  落盘/playwright 链）；
- **回归风险声明（防施工者误判）**：latest_valid 双校验后一切
  report_path 不可达的存量 fixture 账行全变「无记录」——
  test_plan_recon_final rec_idx 真实化属**测试同步升级非脚本回归**。

**完工记录（2026-10-13，接手会话施工）**：
1. **evidence_index**：`RecordRejected` 异常类（与 IO 失败豁免语义
   切割，docstring 写明）；record() 读 report_path 校验内嵌
   src_hash（不存在/缺字段/不一致 → stderr 显式 + raise，三种拒绝
   路径各自文案）；latest_valid() 双校验（报告不可达/内嵌≠账行 →
   None 视同无记录，**禁回退次旧行**——F5b 锁定）；
2. **五工具调用顺序统一**（先写报告内嵌 src_hash → 再 record →
   stdout）：style-lint 新增 `--out`（**默认值必死**
   `<src>/../pipeline/style-lint_report.json`，报告含 tool/src_hash/
   stack/violations 全量——顺带补齐「原始输出有文件可引」）；末尾
   return 改 exit_code 变量（拒账取或置 1）；e2e-smoke/route-audit/
   exits-audit 报告构造+写盘提前、record 挪后、except 两层分层
   （RecordRejected → stderr+置 1 / Exception → 既有豁免）；
   explore-walk 上会话已先写后记，本轮补报告 src_hash+两层分层；
3. **测试**：新函数 test_report_hash（F1 一致入账/F2 旧报告配新
   哈希拒绝/F3 缺字段拒绝/F4 报告不存在拒绝/F5a 命中最新行/
   **F5b 改坏最新报告 → None 禁回退次旧**/F6 style-lint 默认落盘+
   内嵌哈希/**F7 五工具两层 except 分层静态断言**——定标点名①）；
   rec_idx fixture 真实化（上会话已做）；既有全链不回归——
   test_evidence_chain style-lint 链/exits 链（playwright）、
   test_explore_walk F5 落账链、五 playwright 用例、
   test_plan_recon_final 全部实跑 PASS（2026-10-13 本机）；
4. **卡面验收逐条对照**：旧报告内容配新哈希 → 拒绝 ✓（F2）；内嵌
   一致 → PASS ✓（F1）；无内嵌字段 → 拒绝 ✓（F3）；test_evidence_
   chain 不回归 ✓；定标点名①（拒账禁静默）✓（F7+record 内 stderr）；
   定标点名②（latest_valid 不一致=None 禁回退）✓（F5b）。

---

## 1012-07 [x] 几何贴底断言（底部固定元素 + 跨页壳一致）

**机制层归属**：断言层。

**现象/根因**：app2 实锤三处几何缺陷（收银台「立即支付」按钮悬空、
assistant 页 TabBar 悬浮不贴底+源图无 TabBar 被多加、跨页 TabBar 形态
漂移）全漏网——e2e 只断 URL/文案，裁判检查表无「底部固定元素贴底」项；
几何契约零机器断言。

**修法**（审核修订版 v2——补编写侧载体，防「断言类型加了没人写」）：
1. e2e-smoke 步骤增断言类型 **`expect_pinned_bottom`**（选择器的
   bounding_box.bottom ∈ [视口高-安全区余量, 视口高] 区间；**余量定标
   交本卡测试角色 gate 定**）；
2. **编写侧载体同步**：wiring-prompt「主流程冒烟规则」expect 类型枚举
   扩第四类 expect_pinned_bottom + **强制句**（底部固定元素 TabBar/
   输入栏/提交条必须带此断言）；station-guide ⑧/⑩对应条文同步——
   不同步则重演「参数加了没人传」型假绿（与本批 1012-01 同型病）；
3. 主流程链对底部固定元素抽样断言；跨页壳一致性归⑩既有跨页聚类维度
   扩展抽查（TabBar 同档同规格）。

**验收**：反例 fixture——贴底元素 PASS；故意 margin-bottom 悬空 →
FAIL；grep wiring-prompt/station-guide 新条文；套件全绿。

**来源**：app2 验收 C3/C4 实锤。涉 playwright 断言类型新增，**本卡
无条件走测试角色 gate**（余量定标列入 gate 范围）。

**测试标准定稿（2026-10-12，测试角色协商稿经主代理裁定）**：
- steps 断言类型 `"expect_pinned_bottom": "<css selector>"`（值=
  选择器字符串，locator 语法禁 get_by_text——bounding_box 需元素框）；
- 判定式：`box = loc.first.bounding_box()`，`vh = viewport 高`，
  `tol = 8px（建议值，施工时对 app2 三案例实测后锁值——裁定⑤）`；
  box None → FAIL（禁跳过）；`vh-tol ≤ box.bottom ≤ vh+tol` → PASS；
  否则 FAIL（文案含 selector/box.bottom/vh 三值）；
- **has_expect 枚举同步扩入 "expect_pinned_bottom"**（漏扩则带此断言
  的步骤被判无断言恒 FAIL——本卡最易翻车点，防回归 F4 必在）；
  rec 键名 `pinned_ok`（`_ok` 后缀自动进 checks）；checks 聚合
  all() 下 pinned_ok=False 须拉低整步（防回归 F2）；
- `--viewport` 非默认档下 vh 取实际视口禁硬编码 812（防回归 F1 变体
  820x1180）；fixed 元素被 transform 祖先降级属真实缺陷应 FAIL 不豁免；
- 反例 F1-F4 全 playwright 挂 test_e2e_assert 扩展（贴底 PASS/
  margin 悬空 FAIL/不存在 FAIL/单步仅 pinned 不误杀）。

**完工记录（2026-10-13，接手会话施工）**：
1. **e2e-smoke**：新增 `expect_pinned_bottom` 断言类型（值=CSS 选择器；
   vh=page.evaluate innerHeight 实际视口禁硬编码；tol=8px；count()
   前置+bounding_box(timeout=2s)——selector 不存在即时判 None 禁跳过，
   规避 30s 默认等待；**bounding_box 无 bottom 键，底缘=y+height 自算**
   ——施工实测修正）；`has_expect` 枚举同步扩入（防"带此断言的步骤
   被判无断言恒 FAIL"——本卡最易翻车点）；pinned_ok 自动进 checks
   聚合（_ok 后缀机制，False 拉低整步）；
2. **编写侧载体同步**：wiring-prompt 主流程冒烟规则 expect 枚举扩
   第四类+底部固定元素强制句（TabBar/输入栏/提交条必带，CSS locator
   语法禁 get_by_text）；station-guide ⑩e2e-smoke 行补贴底断言半句
   +跨页壳一致性归既有聚类维度指针。grep 四处在位 ✓（wiring×2/
   station-guide×1/脚本×5/测试×5）；
3. **测试**：test_e2e_assert 扩 F1（贴底 PASS）/F1b（--viewport
   820x1180 下 vh=1180 仍 PASS 禁硬编码变体）/F2（悬空 50px FAIL+
   pinned_ok 拉低整步+错误文案含 bottom/vh 值）/F3（selector 不存在
   FAIL 禁跳过）/F4（单步仅 pinned 不误报无断言）——6 断言全绿
   （playwright 真跑，2026-10-13 本机）；既有空断言/带预期反例不回归；
4. **卡面验收逐条对照**：贴底 PASS ✓（F1）；margin 悬空 FAIL ✓
   （F2）；grep 两载体条文 ✓；套件绿 ✓（既有用例实跑）。

---

## 1012-08 [x] judge 同屏并排 + 跨页系统性偏差视角

**机制层归属**：断言层（视觉审方法）。

**现象/根因**：app2 实锤系统性视觉偏差（全局密度偏大/字重偏粗）裁判
55 页 blocker 0 全漏——「逐页对照」方法对**跨页系统性**偏差天然免疫
（每页内部比对都「差不多」，没人把 20 页并排看「是不是全体偏了一号」）。

**修法**（审核修订版 v2——落点更正）：
1. **同屏并排**落**结对裁判纪律节**（judge-prompt 硬规则区，非首访
   分支——首访分支输入本来无源图，落那里自相矛盾）：审任何页必须源图
   与成品并排对照（禁凭记忆/单图审）；**显式豁免全部无源图分支——
   synthesized / 首访截图验收 / 独立接线裁判**（各自改用分支内已有
   输入做并排：synthesized=推导布局文档+成品；首访/接线=步骤语义
   清单+接线关系表——不豁免则各分支撞同款输入能力矛盾，终审必改）；
2. **系统性偏差检查**落两处：station-guide「抽样视觉对比」条文扩半句
   + judge-prompt 口径节——批末抽样对**同批同类页**（单形态项目=任抽
   ≥5 页；措辞避用「档」，其在 1010-04 语境已专指设备视口档）做同屏
   网格并排——专门回答「全体是否偏向同一方向」（密度/字重/色温），
   任一维度集体偏移 = major（单页看不见、并排才可见的偏差类型）。

**验收**：grep 条文；spec review 演练（判定主体=复审代理）：密度偏大
反例页组按新条文推演必出 major。

**完工记录（2026-10-12）**：①judge-prompt 纪律节增第 6 条「同屏并排」
（有源图页强制源图成品并排；豁免用**定义式兜底**「凡输入无源图的分支
均豁免」+三分支列举——终审建议采纳，旅程连贯性分支自动覆盖）；②
station-guide 抽样视觉对比条文扩「系统性偏差检查」（同批同类页 ≥5 页
同屏网格并排，集体偏移=major，app2 漏网实证注明）。grep 两处在位 ✓；
密度反例推演留复审。

**来源**：app2 验收 C1/C2 漏网根因。

---

## 1012-09 [x] 执行侧疑点全披露 + 归因附证硬条款

**机制层归属**：传递层（披露义务）。

**现象/根因**：app2 六个带参路由截图 0 字节（Windows 冒号 ADS）无人
发现——执行端「自认为不算问题的」不报；「工具 id 规范差异」类归因
（D-037）虽留痕但无「必须附可证伪证据」的硬要求。全局 CLAUDE.md §3
已有疑点清单纪律，但那是主对话轴——执行侧任务书（子代理/执行会话读
的）没有对应条款。

**修法**（审核修订版 v2）：
1. 三份任务书（coder/judge/wiring）各增**独立条款节**（如「披露与
   归因纪律」）——**禁并入 1010-02 申报节**（并入会让「全量披露」被
   读成只适用工具缺陷场景，恰好缩窄掉零字节截图这类非工具缺陷异常，
   与本卡病灶相逆）；与申报节交叉引用不合并；
2. 条款两条：①**自报边界全量披露**——已知限制/自报边界必须列出所有
   已知异常（含自认为「不算缺陷」的），禁自行过滤；②**归因附证**——
   把问题归因于「工具缺陷/设计稿错误/平台限制」必须附可证伪证据
   （截图/JSON 原文/复现步骤），禁口头判；**挂 UDP 边界同款句**：
   语义分歧禁以「工具缺陷」名义绕过 UDP 合议（与 1010-02 边界 b
   同句，防附证条款成绕道新口径）。

**验收**：grep 三处独立条款节；spec review 演练（判定主体=复审代理；
零字节截图场景按新条文必须进自报边界清单）。

**完工记录（2026-10-12）**：三份任务书各增「披露与归因纪律」独立节
（自报边界全量披露含"自认为不算缺陷的"+归因附证可证伪证据+UDP 边界
同款句），与申报节交叉引用不合并——按终审裁定写死独立节。grep 验收
（三节在位）✓。

**来源**：app2 验收 A3/B3 实锤 + 全局 CLAUDE.md §3 疑点清单纪律的
执行侧平移。
