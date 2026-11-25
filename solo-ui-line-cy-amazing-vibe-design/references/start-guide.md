# 启动与第一轮对话指南

> 主会话视角：用户激活技能后，第一轮该说什么、问什么、怎么问。

## 激活协议

用户说"用 solo-ui-line-cy-amazing-vibe-design 设计 X" / "重设计 X" / "升级 X 设计" → 走激活协议。

**3 项全部到手才进阶段一**（1 必填 + 2 选填）：

| # | 必/选 | 问什么 | 缺则后果 |
|---|---|---|---|
| 1 | **必填** | **产物输出目录**（路径，如 `./my-landing-page/`） | 产物落哪不知道 |
| 2 | 选填 | 目标受众（谁会看 / 在什么场景） | 方向可能偏 |
| 3 | 选填 | 设计系统（已有组件库 / 风格范本） | 字体/组件库重做（可答"无"） |

**注意**：**"产品 / 页面"不是两个问题**——是"你想做哪种页面（落地页 / 应用界面 / 仪表盘 / 作品集 / 内部工具）"——**由用户在答"产物输出目录"前后自然带出**（如路径含 "landing-page" / "dashboard" 自然知道）——**不单独问**。

落盘到 `<output_dir>/brief.json`（机器读入口）+ `<output_dir>/brief.md`（人读）。

## 开场白模板

用友好的开场（不要像机器），示例：

> "好嘞，开始之前我得问 1 个必填的：你希望产物落到哪个目录？（比如 `./my-landing-page/`）
>
> 顺手能答 2 个选填（不答也行）：
> - 设计给谁看？在什么场景？
> - 已有设计系统/组件库吗？没有就答'无'。
>
> 答完我就跑种子 + 方向探索。"

## AskUserQuestion 用法

**第 1 轮（必填）**：用 AskUserQuestion 问 1 个问题（header: `产物输出目录`）——**问题数 1 个**。

**第 2 轮（选填）**：用 AskUserQuestion 问 2 个问题（headers: `目标受众` + `设计系统`）——**问题数 2 个**。

**问题数量**：1-4 个（Claude Code 工具限制）。
**选项**：2-4 个 + "其他"。
**header 标签**：用 `产物输出目录` / `目标受众` / `设计系统`（短词，不要完整句子）。

## 中途零打断原则

3 项收集完前**不调用任何脚本、不读任何 references、不调任何子代理**。

- 用户答"随便" → 不放过，AskUserQuestion 给出"4 选 1"（如"商用 / 个人 / 玩具 / 高保真效果图"）
- 用户答"你定" → 仍然要确认，但允许快速给 4 选 1 + 默认项
- 用户路径含特殊字符（空格/中文）→ 主动规范成"无空格无中文"的目录名

## 完成后立即执行

3 项到手后立即：
1. **建产物目录**：`mkdir -p <output_dir>/screens <output_dir>/media <output_dir>/code`
2. **落 2 个入口文件**：
   - `<output_dir>/brief.json`（机器读入口，缺失拒跑）
   - `<output_dir>/brief.md`（人读，按 `templates/design-brief.md`）
3. **直接进入阶段一**（生成种子 + 方向探索）——**无"用户确认简报"步骤**

## 用户参与节点（全程清单）

| 阶段 | 用户参与 | 形式 |
|---|---|---|
| 激活 | 答 1 必填 + 2 选填 | AskUserQuestion |
| 阶段一·发现 | 选 1 个方向 | AskUserQuestion（3-4 选 1） |
| 阶段一·发现 | 注入品味批注（想象/避免/取而代之/还缺） | 自由文本 |
| 阶段二·定义 | 评审 ≥ 9/10 时的"验收" | AskUserQuestion（接受/继续/换方向） |
| 阶段二·定义 | 停滞时（连续 2 轮 < 0.3 提升） | 上报（评分历史 + 处置建议） |
| 阶段三·交付 | 减法决策（删除/合并/降级） | 列表确认 |
| 阶段三·交付 | 上线验收 | AskUserQuestion（接受/再修一处） |
| 任意 | 用户说"停" | 立即冻结 |

## 工具与文件位置

> 路径都基于 `<output_dir>`，**不**写死 `design/`。

| 资源 | 路径 |
|---|---|
| 种子生成 | `node scripts/seed.mjs`（Bash 工具） |
| 评审子代理 | `Agent(general-purpose, prompt=templates/judge-prompt.md)` |
| 简报模板 | `templates/design-brief.md` |
| 记录模板 | `templates/design-record.md` |
| 简报落盘 | `<output_dir>/brief.md` + `<output_dir>/brief.json` |
| 记录落盘 | `<output_dir>/DESIGN-RECORD.md` |
| 截图保存 | `<output_dir>/screens/r{n}-{viewport}.png` |
| 素材保存 | `<output_dir>/media/` |
| 代码保存 | `<output_dir>/code/` |
| 评审任务书 | `templates/judge-prompt.md` |
| 评审调用规范 | `references/judge-prompt.md` |

## 图像/视频生成（实现者写代码时调用）

本技能主流程**不直接调**图像/视频生成 API——由**实现者**（主会话自己，写代码时）探查当前环境的生图能力后按需调用。

**写到需要图/视频的地方才探查**（禁动工前预探查）：探查到环境有生图/视频能力（例：本机 solo-img-line-cy-bailian-image-gen）→ 按下表调用；探查不到 → 降级外链图库/占位并如实告知（下表命令作废）。

- **P8 图像素材**：实现者调 `python ~/.claude/skills/solo-img-line-cy-bailian-image-gen/gen_image.py "<prompt>"` 生成图片
- **P9/P10 视频/关键帧**：实现者调 `python ~/.claude/skills/solo-img-line-cy-bailian-image-gen/gen_image.py --video "<prompt>" --duration 5 --resolution 480P` 生成视频（已验证 `wan3.0-video` 可用，约 90s 出 mp4）
- **I2I 图编辑**：实现者用 `--image <本地图>` 编辑现有素材
- **模型分流**：默认 `auto`（按 prompt 关键词 + 是否有 image 自动选 `qwen-image-3.0-pro` 或 `wan2.7-image-pro`）

**有 solo-img-line-cy-bailian-image-gen 时**，实现者写代码前先确认 `BAILIAN_TOKEN` 已配置（在 `~/.claude/secrets.md`，由 solo-img-line-cy-bailian-image-gen skill 引导）。**实现者不要**自己硬猜服务名——就按上表调。

## 出错处置

| 情况 | 处置 |
|---|---|
| 用户沉默 | 1 分钟内不重问；如必须确认，用 AskUserQuestion 给出 3 选项 |
| 简报缺失必填项 | 立即停下，列缺失项让用户补 |
| 种子解读异常 | 重跑一次，仍异常则改用 Prompt P2 的简化版（不依赖种子） |
| 评审 JSON 解析失败 | 重派 1 次，仍失败则按当前最佳版本交付并标注 |
| 用户中途说"停" | 立即冻结，按 `<output_dir>/DESIGN-RECORD.md` 当前状态交付 |

## 反馈语言

- 简短、具体、有主张（与"评审"风格一致）
- 不堆砌形容词
- 中文为主，专有名词保留英文（"种子"、"评审"、"简报"、"减法"、"vibe"）
- 不夸奖用户的设计选择（"很好！"），直接说"下一步做什么"
