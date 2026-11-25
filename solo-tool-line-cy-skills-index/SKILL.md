---
name: solo-tool-line-cy-skills-index
description: "cy 技能库总索引（104 技能，10 条场景线）：按线编目全部本地技能的名字、一句话能力与作者。当用户问「有哪些技能 / 有没有能干 X 的技能 / 某技能是谁写的 / 用哪个技能做 X」，或需要按业务场景定位技能时，先读本目录下的 INDEX.md 再定位具体技能。只做索引导航，不执行任何技能。"
---

# cy-skills 索引

本技能是技能库的**目录**。技能库根：`C:\Users\admin\.dsh\skills`（junction → `.claude\skills`）。

## 查找流程

1. 读同目录 [INDEX.md](INDEX.md)——按 10 条场景线分组的完整编目，每条含：技能全名｜一句话能力
2. 按索引锁定目标技能后，**再读该技能自己的 SKILL.md** 获取完整用法
3. 名字规律：`{类型}-{场景线}-{作者}-{能力短语}`；类型 = solo（单技能）/ flow（流水线）/ plugin（插件配套）

## 命名规范（新增/改名技能必须遵守）

- 场景线 10 条：sale（售前）/ prd / doc（文档）/ ue（原型）/ ux（动效）/ ui / img（图像）/ front / tool / dev
- 复合线合法：ux-ui、front-ui、ui-ux-front、ue-ui-front
- 作者：cy / matt / emil / jk / xjk / ky / hucaidan / pbakaus / Nutlope / Leonxlnx / anthropic / openai / X（来源不明）
- 字符集：全小写 [a-z0-9._~-]（大写会被静默丢弃）
- SKILL.md 的 `name:` 行必须与目录名完全一致

## 更新规则

技能新增、删除、改名后，**同步更新 INDEX.md** 对应条目；每季度可按本流程全量重扫一次（列目录 → 对照 INDEX）。
