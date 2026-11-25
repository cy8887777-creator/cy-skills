# 2026-10-07 工卡：技能改造立卡（25 张待施工）+ 前期修复 done 历史

来源：博物馆项目 21 小时实测（会话 7d536cd4）暴露交付假绿 → 八轮外部评审 + 三轮交付物双轴深审（Spec/Standards）+ 外部 AI 复审，收敛 25 条改动。四要素总表见 ACTIVE-BACKLOG.md。
状态标记：`[ ]` 待施工 / `[~]` 施工中 / `[x]` 完工。一卡一 commit（中文 message 带卡号）。

## 执行环境速查

- 技能根：`C:\Users\admin\.claude\skills\flow-front-ui-line-cy-design-pack-pipeline`
- 反例套件：`python tests/test_pipeline.py`（--fast 跳过 playwright 用例）
- 参照工程（实拍证据）：`D:\测试图转代码技能\ai-museum-app`
- 单页技能（勿动，另一会话负责）：`C:\Users\admin\.claude\skills\flow-front-ui-line-cy-img-to-code`

---

## done 历史（2026-10-06/07 已落地修复，勿重做）

### 单页技能（flow-front-ui-line-cy-img-to-code）

- [x] **1006-1** DPR 合同贯通 + 基准门禁 + vendor 递归（commit 763d7b9）——verify/font_probe 消费端同步、layout.json 缺失拒跑、contracts 首访截图裁判前置、selftest contract-suite
- [x] **1006-2** 独立视觉裁判任务书 judge-guide.md（fd5dff1）——首访截图交独立裁判的机制来源
- [x] **1006-3** 三次评审六项：假 PASS 根除（passed 后置）+ 裁判材料坐标 + vendor 相对路径（929cde9）
- [x] **1006-4** 双轴复查 + 1x 档 + doctor --tier 真分档（0febbc0/a033ef5，另一会话续作）

### 管线技能（flow-front-ui-line-cy-design-pack-pipeline）

- [x] **1007-1** 十站重构 + 结对流水 + 激活协议一幕制（ff0da5f/c56524a/84cba91）
- [x] **1007-2** 一~二次评审：状态图交接/交互职责初步/验收硬门禁/plans 表头驱动（1a7c5bf/cb22653）
- [x] **1007-3** 三~四次评审：运行时路由探针/悬空三档分诊/域精简/状态链初步（e4f6b9b/e0341c0/d814fba）
- [x] **1007-4** 五轮评审：--from-source 必填/style-lint 根修/补页文档链（e3a13b4）+ 双轴二轮：docstring 方括号/推导文档豁免（d814fba）
- [x] **1007-5** 七轮评审：探针证据范围/白名单污染/补页时序（557bf69）+ 八轮：NameError 崩溃/无图页裁判分支/空图包 gate/模型 any（48bd900）+ 双轴四轮：var 冒号判据（db83078）
- [x] **1007-6** 反例套件 tests/test_pipeline.py 固化 21 项（48bd900）+ 双轴 helper 提取（db83078）
- [x] **1007-7** 外部复审吸收：状态映射/交互职责/验收门禁/物理点击/双处理/抽样声明的对照结论（本日对话，未落文件——由本轮 25 卡承接）

---

## 待施工（25 张，详见 ACTIVE-BACKLOG.md 四要素）

### 批 1：骨架+安全网

- [x] **1007-01** 纪律配发架构：四本任务书+主 SKILL.md 减负（效力来源如实=精炼+隔离）——commit 416e7d4
- [x] **1007-05** contracts-lint.py + mock 外置硬检查（6/6 反例：缺挂载/无挂载路由/命名违规/合规 PASS/零实体仅统计）
- [x] **1007-12** 交互职责分界：规则已进 coder/wiring 任务书（随 1007-01）；**反例验证挂账**（p009 需工程 fixture，随 1007-22）——规则落地 [x]，反例 [ ]
  - **残项关闭（2026-10-09）**：工程实证检查产物 D:\yinglongqianduanceshipp——select- 类死标记 0 处（执行 AI 返修+1008-13 命名对齐后已清），intent-router 含本地处理/stopPropagation 机制 8 处；工程级反例由 test_exits_audit/test_contracts_lint 的配置与运行时反例承接。规则+工具+工程实证三齐，关闭。

### 批 2：状态真值链

- [x] **1007-03** PRD states 逐态枚举规则+主流程标记（prd-prompt）
- [x] **1007-04** 状态基准链：默认态选图+status_map 字段+⑥转装核对
- [x] **1007-13** 弹层挂宿主（禁占位宿主+back() 冒充；深链允许背景路由）
- [x] **1007-14** 双处理冲突检查（本地 stopPropagation → 全局跳过）

### 批 3：任务书内容

- [x] **1007-02** 四分法总纲（美术 1:1/功能复刻/缺失补全/错误修正）
- [x] **1007-21** 路由规范化（manifest 文件名→slug，禁直通）
- [x] **1007-23** 素材含字/UI 检测送 REVIEW（不按面积阈值无条件 inpaint）
- [x] **1007-24** 组件 intent 透传 + 禁绕开手写 + 复用率审查项
- [x] **1007-09** ⑦壳补全（按 sitemap/PRD 角色补，非"图上没画就自动加"）

### 批 4：验收与交付

- [x] **1007-06** e2e-smoke.py（像素级 diff 容差 0.1%+反例 3/3）——e2e-smoke.py（物理点击+变化检测辅助+双证据+修复后重跑）
- [x] **1007-07** 首访截图交视觉裁判
- [x] **1007-08** 对比板基准校验（同一 state 即可，声明所比 state）
- [x] **1007-15** 精绘转装 TSX 纳入同口径检查
- [x] **1007-16** FAIL 不许解释成 PASS（P0）
- [x] **1007-17** 已知问题分级：major 必修 + 归因过可修性门

### 批 5：流程与收尾

- [x] **1007-10** 悬空代价分诊 + 判例落地（统一 gaps-and-quality 两版冲突）
- [x] **1007-11** 忽略分类审计（逐条理由；select/tab 禁归忽略）
- [x] **1007-18** 交付报告补全清单章节
- [x] **1007-19** 修复轮根因门（先复现定位，禁"改一版试试"）
- [x] **1007-20** PLAN 增强（站级状态表/solo-dev-line-matt-handoff/简报）+ 主流程通过率双指标
- [x] **1007-25** checkpoint 抽样范围声明
- [x] **1007-10 残项** 判例回填 gaps-and-quality
- [x] **1007-01 残项** 配发架构说明回填 SKILL.md
- [x] **1007-22 残项** codex 五反例并入回归套件

---

- [x] **1007-26** 外部 AI 文档核对四项修复（10-07）：①SKILL 铁律 2 同步为新交互职责分界（原“只打占位⑨接线”与任务书冲突）②route-audit 补 full_page 长页截图实现 ③SKILL 技术栈表声明验收脚本覆盖范围（React+TS；其他栈验收降级告知）④coder-prompt 站号残留 ⑥→⑧

## 纪律（全程适用）

- 每卡闭环：施工 → 自测（tests/test_pipeline.py 对应反例）→ 状态回填 → 一卡一 commit（中文 message 带卡号）
- 撞见方案外的事：停，报用户定夺，不扩 scope
- 单页技能（flow-front-ui-line-cy-img-to-code）本技能不碰，另一会话负责
- codex 回归用例为最终验收：p006 默认态禁弹窗底图 / p009 选择TA 非无效 / 本地关弹窗不触发全局 Toast / 遮挡控件不靠强点 PASS / route-audit FAIL 不改写交付 PASS / 长页滚动内容
