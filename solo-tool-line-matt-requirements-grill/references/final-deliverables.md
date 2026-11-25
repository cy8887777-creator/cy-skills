# Final Deliverables

Read this reference only when the user requests final Excel or PRD deliverables.

## Required pipeline

Never generate final outputs primarily from conversational memory.

```text
resolved requirements model
-> consistency audit
-> Excel feature list + PRD
```

The governed requirements model is the authoritative source set declared by the
host project: normally `project.config.json`, `docs/requirements/product.md`,
`docs/requirements/confirmed-decisions.md`, and
`docs/acceptance/acceptance-baseline.json`. Standalone mode uses
`requirements/MASTER_REQUIREMENTS.md`. Never generate a parallel master solely
for final delivery.

Normalize and correct the requirements source before regenerating a mismatched deliverable. Never patch two inconsistent outputs independently.

## Excel feature list

Generate an actual `.xlsx`. Unless the user supplies another template, include these sheets.

### `功能清单`

Use these columns:

1. 需求编号
2. 端
3. 一级模块
4. 二级模块
5. 功能名称
6. 功能说明
7. 使用角色
8. 前置条件
9. 业务规则
10. 权限/数据范围
11. 异常/边界情况
12. 依赖
13. 阶段
14. 验收标准
15. 状态
16. 备注

Descriptions must be detailed enough for quotation, estimation, development, testing, and acceptance. Avoid vague text such as “支持订单管理”.

### `角色权限`

Include role, module, function, operation, data scope, restrictions, and PERM ID.

### `业务规则`

Include BR ID, module, rule, trigger, result, and related requirement IDs.

### `待确认问题`

Include unresolved `OPEN` items; never hide uncertainty.

## PRD

Generate the PRD from the resolved requirements model, using this default structure unless the user supplies another template:

1. 文档信息
2. 项目背景
3. 项目目标
4. 项目范围
5. 一期范围
6. 非一期 / 明确不做
7. 术语
8. 用户和角色
9. 权限与数据权限
10. 产品信息架构
11. 核心业务流程
12. 功能需求
13. 业务规则
14. 状态流转
15. 异常和边界条件
16. 通知
17. 第三方接口
18. 后台配置
19. 非功能需求
20. 数据与安全
21. 验收标准
22. 待确认事项
23. 变更记录

Reference stable requirement IDs for important PRD requirements.

## Consistency audit

Before delivery verify:

- every Phase 1 functional requirement appears in Excel
- every major Phase 1 requirement is described in PRD
- requirement IDs and terminology match
- roles, operation permissions, and data scopes match
- business rules and phase labels match
- rejected and out-of-scope items do not return
- `OPEN` items remain visibly open

If any check fails, fix the resolved authoritative requirements sources first,
regenerate affected outputs, and rerun the audit. Do not patch Excel and PRD
independently.
