# 选型回传契约（selection-contract）

solo-ui-line-cy-gui-style-picker 与主技能（flow-ux-ui-line-cy-hifi-design）之间的唯一接口。**原子技能只读 V0.1、只返回本契约的确定值，不改 start-doc**——合并权归主技能。

## 1. 回传文件：`intake/selection-result.json`

```json
{
  "schemaVersion": 1,
  "skill": "solo-ui-line-cy-gui-style-picker",
  "project": "<V0.1 项目名>",
  "status": "selected | failed",
  "audienceGroups": [
    {
      "group": "用户端",
      "products": ["用户端.html"],
      "selected": [
        {
          "styleId": "wiki:<选中卡id> | gen:<slug>",
          "styleName": "<选中卡中文名>",
          "origin": "wiki | ai-generated",
          "mood": "一句话情绪定调",
          "skeletonTokens": {
            "primary": "#…", "text-primary": "#…", "radius-md": "…",
            "space-2": "…", "size-ctl-md": "…", "weight-head": "…",
            "…": "其余 token-minimum 全部 32 键；键名逐字照抄 token-minimum（全小写连字符）；定位=选定风格的取值记录（主技能阶段5 登记进开工文档 1.0 §6 风格记录、附加A 编辑版转化时参考），不约束画面"
          },
          "skeleton": { "…STYLE-CONTRACT.pages 同款结构（form 开放词汇）…" },
          "confirmRecord": { "rounds": 1, "labels": [], "variantOf": null }
        }
      ],
      "rejected": [ { "styleId": "…", "reason": "太密" } ]
    }
  ],
  "pipeline": "static-html | scaffold",
  "scaffold": null
}
```

- `pipeline`：选型选到大厂 UI 脚手架且用户拍板"直接工程"时填 `scaffold`（P3 后管线，当前版本该路由出现即停线报告）；
- `status: failed`：重出一轮仍不收敛 → **宁停勿错**，`reason` 字段必填，主技能停下报告，不猜默认风格硬推进；
- `products`：该受众组**比稿卡采用 V0.1 §3 页面地图里的代表页名清单**（样张浇在哪几页的记录，供主技能对账；此时产物页面尚未生成，填页面地图页名）；
- `confirmRecord`：拍板过程记录——`rounds`=拍板历经轮次数；`labels`=用户拍板原话要点（逐条）；`variantOf`=该卡由哪张卡微调/混搭而来（源卡 styleId，原创无源=null）；
- 用户多选：`selected` 数组多成员；同族成员共享 domBase（主技能按族推导 DOM 套数，用户不选套数）。族/骨架归属写入前，按四个方面（信息密度、元素粒度、布局范式、内容分布）逐个风格列给用户确认，规则见主技能 references/editor-runtime.md「AI 判族」。

## 2. 选型结果与开工文档的对接（V06：无风格槽节）

- 0.1 **没有"风格槽"节**：受众组在 §1"给谁用"分组、动效档在 §5；picker **不改 0.1**，也无须它占位。
- 选型由主技能在阶段5 装入 **1.0 §6 风格记录**：样张记录（selected 摘要+mood+来源+本文件路径）+ 令牌记录（skeletonTokens 原样登记，**不约束画面**）+ 气质归纳（从提示词/样张）。
- 手续门禁已随 V06 退役：校验点=用户确认 1.0 时 §6 非空。

## 3. 版本语义与冻结

- **V0.1**：主技能阶段1 收口盘问产物，五节（项目定义[含受众组]/业务链路/页面地图/功能刻度/动效档）——无风格、无布局样张、无令牌；
- **1.0**：主技能阶段5 完善——**三份文档各自定稿**：开工文档 1.0（0.1 五节原文不动 + §6 风格记录[样张摘要/令牌登记/气质归纳，登记性质] + §7 业务补全[补问结论，委托 AI 定的标「AI 决定」]）→ **用户签字冻结**；页面地图扩展与设计资产与动效规范随阶段4/5 成文（`design/` 下）——此后经用户裁决的修订直接修订并在 ledger.md 记一行；
- 签字行沿用 start-doc 流程纪律；1.0 之后风格即契约，改风格=变更流程。

## 4. 三问的档位字段（随 V0.1 记录）

- 功能刻度：`a MVP | b 核心+闭环 | c 完整打磨`——落 0.1 §4 作深度声明；
- 动效档：落 0.1 §5；
- 交互档（a 静态形态/b 导航级/c 演示级）：落 0.1 §5——picker 不使用该档，仅随 V0.1 记录；
- 三档均为**策划输入**，交付前提醒式核对，不做机器拦截。
