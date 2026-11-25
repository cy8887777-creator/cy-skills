# 生成类图标工作流（wf-genicon）

场景：3D/黏土/拟物/贴纸等质感档图标找不到现成的；或上游接受生成路径。

## 供给优先序

```
0. 动态质感/双色面性（kubai 档）→ wf-icons 漏斗检索 + 未命中走 §程序化生成（引擎现画）
1. 本地 JSON：withicons-soft3d（软3D 1000）/ withicons-clay（黏土 1000）
             / withicons-skeuo（拟物 1000）/ withicons-sticker（贴纸 1000）
             / withicons-pastel（粉彩 1000）/ withicons（基础 7000）
2. 3dicons.co（外部唯一例外站，CC0；现版以 color 变体直下为主，
   玻璃/渐变质感须走其 Editor 材质 remix 后导出 PNG——用前先确认可得）
3. 生图定制（探查环境生图能力：可用则直接生成并 base64 交付；无则交付提示词包）
```

**代码画 C4D 是假 3D，禁止**——软体充气质感只能渲染或生成，SVG 手绘救不了。

## 3dicons.co 取用流程

1. 语义定位：`https://3dicons.co/` 搜索或 GitHub realvjy/3dicons 仓库按名定位
   ⚠️ **3dicons.com（.com）是他站**（iconshock/bypeople 产品，许可非 CC0）——勿混淆，只认 **.co**
2. 单文件下载（pwsh Invoke-WebRequest，几十 KB/枚）；站内 PNG 通常自带透明底
3. 交付加工（属本技能交付环节，见 SKILL.md 边界豁免）：压缩 → base64 `data:image/png` 内嵌
4. 体积纪律：位图图标显示尺寸压 96-128px、单页位图图标 ≤12 个

## 生图提示词包（失败处置选项 d 的交付物）

上游没有生图额度或想自己生成时，交付即拿即用的提示词包：

```markdown
【生图提示词包】
语义：<图标表达的内容，一句话>
─ 中文版（即梦/百炼/通义）─────────────
<主体描述>，<质感关键词：充气3D软体/黏土/磨砂玻璃/渐变>, <色彩：引用需求单色板>,
纯白背景，居中构图，无文字，无水印，简洁干净
─ 英文版（Midjourney/DALL-E）─────────
<subject>, inflated 3d soft body style / clay render / frosted glass,
<palette>, isolated on white background, centered, no text, no watermark
─ 参数建议 ─────────────────────────
Midjourney: --no text, watermark, gradient background（多参数逗号分隔）
一致性锚点（成套）：<固定风格模板句不变，只换主体词；建议固定 seed>
后处理指引：生成 → 抠透明底 → 压缩 → base64 内嵌（纪律同上）
```

**质感词弹药**：优先引用需求单关联的风格卡【材质与光影】段描述——那是权威的风格语言，不要现编。

## 手绘定制（处置选项 b）

- 前置条件：上游具备手绘渠道或确认追加工期——确认后**另开定制需求单**（含工期/交付形态字段），本技能按该需求单交付定制 SVG
- 显式声明"这是定制的"（非现成资源）
- 轻 2.5D/几何类：AI 直接手绘 SVG（等距变换+渐变面，矢量强项）
- 重 C4D 有机形态：不接手绘（假 3D 禁令），引导回生成路径
