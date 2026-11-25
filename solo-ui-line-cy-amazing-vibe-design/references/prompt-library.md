> 每个模板注明用途、阶段与要点。`{花括号}` 为占位符。原文示例同时给出英文原句，便于直接使用。

| 编号 | 名称 | 阶段 |
| --- | --- | --- |
| P1 | 默认基线（仅用于对照） | 发现 |
| P2 | 种子字符串流程 | 发现 |
| P3 | 野心简报 | 发现 |
| P4 | 灵感阶梯三连 | 发现 |
| P5 | 评审回路 · 实现者指令 | 定义 |
| P6 | 评审回路 · 评审者提示（固定） | 定义 |
| P7 | 排名式评审 | 定义 |
| P8 | 图像素材补强 | 定义 |
| P9 | 循环视频 + 抠像 | 定义 |
| P10 | 关键帧过渡 + 滚动擦洗 | 定义 |
| P11 | 减法指令 | 交付 |
| P12 | 密钥存放 | 全程 |

---

## P1 · 默认基线（仅用于对照）◆

用途：记录“不用本技能时”的产物，作为独特性质量门（G1）的对照。

```
Build me a landing page for my productivity app.
为我的效率应用做一个落地页。
```

---

## P2 · 种子字符串流程 ◆

```
I want you to build me a landing page for my productivity app.

Follow this procedure:
1. Generate a long, random alphanumeric string using a shell script.
2. Define the creative direction (color scheme, layout, typography, etc.) based on the string.
   Look beyond the surface for subpatterns, special numbers, anything that inspires you.
3. Use your judgment to bring this direction to life and make it look great.

Don't reveal the string in the design. It's only for your inspiration.
```

```
请为 {产品} 做一个 {页面类型}。

按以下流程：
1. 用 shell 脚本生成一串长的随机字母数字串。
2. 基于这串字符定义创意方向（配色、版式、字体等）。透过表面寻找子模式、特殊数字和任何能激发你的东西。
   请把你的解读过程列出来。
3. 运用你的判断把这个方向落地，并让它好看。

不要在设计中暴露这串字符，它只用于激发灵感。
```

要点：并行运行 3–4 次，得到差异显著的方向；要求列出解读过程，便于记录与复现。

---

## P3 · 野心简报 ◆

```
为 {产品} 做一个落地页，采用 {跨领域灵感源} 的主题。{灵感如何映射到界面}。
无论多大胆，它都必须仍然能作为 {页面类型} 工作：{功能约束}。
```

原文示例：

```
Build me a landing page for my productivity app, with a bold pixel art theme and stunning graphics.
Each section should feel like a still from a video game, yet somehow it should all function as a landing page.

Build me a landing page for my productivity app, set in an isometric living 3D city,
where different features are somehow represented by neighborhoods or buildings.

Build me a landing page for my productivity app, with a radically asymmetric layout,
dissonant colors and typography, and uncomfortable negative space. Break all the rules but still make it look good.
```

---

## P4 · 灵感阶梯三连 ◆

第 1 步 · 广而浅：

```
I want to come up with a bold, unique design language for my product.
Can you list as many ideas as you can, with short, high-level descriptions? Go broad, not deep.
```

第 2 步 · 品味批注（以“工业控制面板”为例）：

```
Industrial Control Panel:
- I'm imagining something tactile. Clicky, satisfying buttons, nice sounds.
- Initially I pictured something cartoony or skeuomorphic, but this feels tacky to me. Avoid that.
- Instead, want consistent components and little touches that land this look without going overboard.
- Gray gradients would look boring. Need more texture. Maybe we can incorporate some color,
  while retaining the control panel feel?
Can you sharpen this one based on my tastes?
```

第 3 步 · 压缩：

```
Can you write a concise prompt that an AI agent could use to build an initial POC page with this?
```

---

## P5 · 评审回路 · 实现者指令 ◆

```
I want you to improve this design. To figure out what to focus on, use a {大模型} subagent as a design critic.

Follow this procedure at each iteration:
- Capture a screenshot of the current design
- Invoke the critic in a fresh context, with just the screenshot, not the code,
  implementation details, or earlier iterations/critiques
- Ask it to evaluate the aesthetic that the design is going for, imagine how a top design studio
  would execute this aesthetic, then outline the biggest gaps
- Lastly, it should provide a score out of 10 indicating how close the current design is to that
  studio-level quality bar

Provide this guidance to the critic in its prompt:
- It should think high-level about the overall structure and composition as well as look at the fine details
- It should watch out for patterns that feel overdone, excessive, or otherwise obviously AI-generated, and penalize them
- It should provide tight, specific feedback, not vague prose
- It should be bold and opinionated, not rely on what's safe or easy

Your work is only complete when the critic independently deems it 9/10 or higher.
Do not put that criterion in the critic prompt; keep it objective in its scoring.
Use the same critic prompt each time.
```

补充约束 ◇（可追加在末尾）：

```
Run one or two iterations first and report whether scores are converging before continuing.
Stop after {5} iterations, or if the score improves by less than 0.3 for two consecutive iterations,
and report back to me with the score history.
```

---

## P6 · 评审回路 · 评审者提示（固定）◆ / ◇

> 实现者每轮原样使用；**不得**包含停止阈值。

```
你是一名顶级设计工作室的设计评审。你只会看到一张界面截图（以及可选的基准图）。

1. 用一两句话说明这个设计在追求什么美学。
2. 想象一家顶级设计工作室会如何执行这种美学。
3. 列出当前设计与该水准之间最大的差距（最多 5 条），每条包含：区域、问题、具体修改建议、严重程度。
4. 给出 0–10 分的评分，表示当前设计距离工作室水准有多近。

评审时：
- 既要从高层审视整体结构与构图，也要审视字体、间距、对齐等细节；
- 警惕显得过度、过量或明显 AI 生成的模式（如紫色渐变、左文右图模板、无目的光晕、卡片套卡片），并扣分；
- 反馈紧凑、具体，不写含糊的散文；
- 大胆、有主张，不依赖安全或省事的做法；
- 基准图只作为质量基准与情绪板，不是临摹目标。

以 JSON 返回：{"aesthetic": "", "studio_vision": "", "gaps": [{"area": "", "issue": "", "fix": "", "severity": ""}], "score": 0}
```

---

## P7 · 排名式评审 ◆

```
Here are 5 designs: 4 professional examples and 1 screenshot of our product.
Rank them by polish and taste level.
这里有 5 张设计：4 张专业作品，1 张是我们产品的截图。请按精致度与品味排名，并说明排名理由。
```

要点：图片顺序随机；不告诉评审哪一张是“我们的”。

---

## P8 · 图像素材补强 ◆

```
The design is pretty plain. Add more personality using image generation.
Consider shaders or 3D effects in combination with images to create more interesting visuals.
For image generation, use the key in .env.agents (only use it locally, do not store it in the code or product).
Verify that your work looks right frame-by-frame in the browser.
```

---

## P9 · 循环视频 + 抠像 ◆

```
Can you replace the image on this page with a looping video clip that does something more interesting?
Have the crystal splinter apart and slowly spin around. It should have awesome glassy effects that refract
the page background and cast shadows and light around it.

To get convincing glass refraction effects, render the video of the glass over the page background colors
first (so it bakes in the refraction effects), then remove the background with a video matting model.

Use the fal.ai key in .env.agents. Find appropriate recent models for video generation and background removal.
```

---

## P10 · 关键帧过渡 + 滚动擦洗 ◆

```
Build a demo page for {产品} that uses a video model to create interactive transitions between a couple of screens.
Each screen should show the product in a different state, with vertical motion that feels appropriate for scrolling:
- {状态 1}
- {状态 2}
- {状态 3}

Generate the initial frame using your image generation skill. Then, generate a video clip that starts from that frame
and animates to the next state. Use the final frame of that video to seed the next transition so that it continues
seamlessly. Scrub through the transitions one by one as the user scrolls.

Use a video model with strong physics and consistency.
```

---

## P11 · 减法指令 ◆ / ◇

```
请收敛这个设计：
- 简化为以 {图片 / 核心数据} 为中心的布局；
- 去掉渐变、光晕和不必要的容器；
- 去掉与图像重复的标签和说明文字；
- 用平台原生组件替换自造的按钮与输入框；
- 文字更小、更简单、更紧凑；
- 追求真正的极简，具有 {平台} 原生感。
完成后列出你删除了什么、为什么，以及每个保留元素的作用。
```

---

## P12 · 密钥存放 ◆

```
Create a gitignored file called .env.agents, store this API key in it, and note to yourself in AGENTS.md/CLAUDE.md
that these keys are for you to use during development (but must not ship with the product).
```
