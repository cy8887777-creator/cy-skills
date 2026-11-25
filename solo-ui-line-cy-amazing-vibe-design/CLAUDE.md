# 项目指令（escape-the-mean 技能维护）

> **受众声明**：本文件给"开发/强化本技能"的 AI 会话。
> SKILL.md 给"使用本技能跑流程"的会话。两者互不承载。

## 强化纪律

1. **改动前自检**：用 `node scripts/seed.mjs` 跑一次默认输出，确认基线未坏；改动后必须再跑一次。
2. **改动边界**：强化时不外推用户未授权的方向（用户说"强化铁律"≠"重写 SKILL.md 全部"）。
3. **SKILL.md 不承载工程纪律**：开发规则、git 提交规范等放本文件；用户会话不应读这些。
4. **references/ 按需加载**：单文件超过 200 行时考虑拆出 references/；SKILL.md 只保状态机骨架。
5. **新增 references 时同步** SKILL.md 引用 + scripts/doctor.py 的体检项。
6. **新增子代理任务书时**：templates/ 和 references/ 各一份（前者子代理视角，后者主会话视角）。

## 强化检查清单（每改必过）

- [ ] 改动后跑 `node scripts/seed.mjs --json` 确认输出结构未变
- [ ] SKILL.md frontmatter 仍包含 `name: escape-the-mean`
- [ ] 所有内部链接目标文件存在
- [ ] 模板占位符风格统一（统一用 `{花括号}` 形式）
- [ ] 文档语言：中文优先，专有名词保留英文
- [ ] 若动了 SKILL.md 操作步骤，同步更新 references/ 对应章节
- [ ] 若新增 API 调用（图像/视频），在 references/ 标注服务名 + 密钥位置

## 已知边界

- **本技能不实现"自动评审"**——评审必须由独立子代理人工判断（详见 references/judge-prompt.md）
- **本技能不实现"自动图像生成"**——图像/视频生成依赖外部 skill 或服务（详见 references/start-guide.md 工具节）
- **本技能不保证跨文化审美**——种子解读规则基于拉丁字母表 + 阿拉伯数字，其他字符集需扩展 alphabet

## 与其他 skill 的协作

- **生图/视频能力（探查式）**：实现者写代码时探查当前环境可用的生图能力——有则用它；无则降级外链图库/占位并告知。本技能 P8/P9/P10 需要它
- **flow-front-ui-line-cy-img-to-code**（单图生成前端代码技能）：**独立 skill**，**不是本技能下游**——它是"截图 → HTML"的高保真还原
- **flow-front-ui-line-cy-design-pack-pipeline**（多图管线技能）：**独立 skill**——多页项目级管线，与本技能各自解决不同问题

## 作为被调用方

**其他 skill 想用"更强的设计能力"时调本技能**——典型场景：

### 场景 1：Pipeline 1（**0 → 高保真美观的交互效果图**，**待建**）

- **任务**：从 0 开始，做**一整套软件**的高保真 **HTML 效果图**（静态 HTML + CSS + 资产代码，多页）
- **调本技能**：Pipeline 1 调本技能生成"**主要页面**"——**剩下的次要页面**由 Pipeline 自己用相同的简报/设计语言完善
- **调法**：Pipeline 1 主流程中"主要页面"环节，`Skill('escape-the-mean')` 启动本技能，**输出**：`design/brief.md` + `design/code/{主要页面}.html`（多份）—— Pipeline 拿这些补其他页面

### 场景 2：Pipeline 2（**低保真交互原型 → 高保真交互原型**，**待建**）

- **任务**：用户已有**低保真交互原型**（lo-fi HTML），想升级为有品味的高保真交互原型
- **调本技能**：把现有低保真稿作为 brief 输入，走本技能的"重设计"流程
- **调法**：同场景 1，但 brief 包含"现有 lo-fi HTML"作为参考

### 场景 3：用户直接激活（最常见）

- 任务：用户说"用 escape-the-mean 设计 X"
- 走激活协议 5 项，详见 `references/start-guide.md`

### 接口约定（被调用方应清楚）

- **触发关键词**：用户说"设计 / 重设计 / 美化 / 更有品味 / 别像 AI 做的 / 升级设计 / 重新定方向"——触发本技能
- **入口**：先 `Skill('escape-the-mean')` 启动本 skill，**不要**直接读 SKILL.md 后自己跑（会跳过激活协议）
- **传出**：本技能完成后留下 `design/brief.md` + `design/DESIGN-RECORD.md` + **代码资产**（HTML/CSS/JS）——调用方可读 brief 拿设计方向，读代码直接用或自己补其他页面

### 已知 TODO（待建，会调用本技能）

- **Pipeline 1：0 → 高保真美观的交互效果图**（**未建**）—— 多页 HTML 静态效果图，调本技能做主要页面
- **Pipeline 2：lo-fi → hi-fi 交互原型**（**未建**）—— 把现有低保真交互原型升到高保真
