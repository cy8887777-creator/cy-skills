# 站间契约总表（1009-10）

> 定位：**设计者对账索引**——站间交付物接口契约的唯一登记处。
> 任务书必须直接携带该角色必需的契约全文（编号仅交叉引用），
> **新增契约必须先进本表再落任务书**；表内反例编号须真实存在于
> tests/test_pipeline.py。

| 编号 | 契约 | 生产→消费 | 内容 | 机器核查 | 反例 |
|---|---|---|---|---|---|
| C-01 | 页面路由契约 | ④→⑧⑨⑩ | route_id→{path, redirect_to?, role, required_exits, entry_declarations} | route-audit/exits-audit/plan-recon --final | test_route_audit/test_exits_audit/test_plan_recon |
| C-02 | 行为 ID 契约 | ③→⑨⑩ | behaviors 逐条稳定行为 ID；⑨按 ID 记责任站三态 | plan-recon 全集差集 | test_plan_recon_final |
| C-03 | 弹层挂宿主 | 写码→⑨ | 弹层条件渲染挂宿主禁独立路由 | contracts-lint | test_contracts_lint |
| C-04 | 双处理分界 | 写码→⑨ | 本地 stopPropagation 全局跳过 | 自测遍历 | 反例套件（1007-14） |
| C-05 | 路由 slug | ①→⑧⑨ | manifest 名→slug 映射禁中文直通 | contracts-lint 命名 | test_contracts_lint |
| C-06 | intent 透传 | ⑥→⑦⑧ | 共享组件 intent prop 透传禁绕开手写 | 零引用审查 | 审查项（1007-24） |
| C-07 | 转装同口径 | ⑤→⑦ | 精绘转装同 lint/裁判口径 | contracts-lint | （随 15 号卡补） |
| C-08 | 素材含字标记 | 单页技能→管线 | over_photo_text_erased 标记驱动 DOM 规则 | 转装 gate 检查 | 1008-14 实证 |
| C-09 | 设备形态/视口档 | ①探针→⑥⑩+4 验收脚本 | device_profile（phone_portrait/tablet/landscape）→ 视口档（375x812 / 820x1180 / 1280x800）；落 PLAN execution_policy；脚本经 --viewport 消费 | test_device_probe（探针分带/置信度/视口映射/参数穿透） | test_device_probe（1010-04） |
