---
name: solo-img-line-cy-bailian-image-gen
description: "调用阿里云百炼 Token Plan 的生图技能（qwen-image-3.0-pro / wan2.7-image-pro）。用户要「生成图片/画一张/做个 logo/概念图/效果图/插画/配图/海报/banner/头像」等时使用；拿到原图路径时也支持改图、换风格、局部替换、图生图等图片编辑（仅 qwen 模型支持）。首次使用会引导配置 API token。用户只是描述、讨论或查看图片时不要调用。"
---

# solo-img-line-cy-bailian-image-gen skill（百炼 Token Plan 生图技能）

## ⚠️ 首次使用引导（最重要的一段）

**调 `gen_image.py` 之前，必须先确认 token 已配置**。本 skill 默认是用户拿到后**没有**token 的状态，所以这一步是必经的。

### 第 0 步：先判断有没有 token

跑下面的 Bash 命令快速探测（不要直接调脚本再试）：

```bash
test -n "$BAILIAN_TOKEN" && echo "ENV=OK" || echo "ENV=MISSING"
grep -E "^BAILIAN_TOKEN=" ~/.claude/secrets.md 2>/dev/null && echo "SECRETS=OK" || echo "SECRETS=MISSING"
```

两种都为 `MISSING` → **必须进入下面 1～3 步引导流程**，禁止直接调脚本。

### 第 1 步：先问用户要 token

**问**：「请提供你的百炼 Token Plan API key（以 `sk-sp-` 开头）。如果还不知道去哪拿，请去阿里云百炼控制台 → Token Plan → 应用的 API key。」

- 如果用户答不上来，告诉他在阿里云百炼 [https://bailian.console.aliyun.com/](https://bailian.console.aliyun.com/) 找到 Token Plan 应用的 API key
- **不要**自己硬猜或编造 token
- **不要**问用户"是不是 XXX？"这种引导性问法（容易被诱导输入错的）

### 第 2 步：用 AskUserQuestion 问用户密钥存哪里

提供以下选项让用户选：

| 选项 | 含义 |
|------|------|
| **A. `~/.claude/secrets.md`**（推荐） | 跟 Claude 自己的 `.credentials.json` 同层，本机所有 API key 集中管理，符合多数 AI 工具惯例，立即可用 |
| B. Windows 用户环境变量 | 适合临时不想留文件的用户，但**新开 cmd 才生效**，当下用不了 |
| C. skill 目录里的 `.token` 文件 | ❌ **不推荐**：分享/打包 skill 时会带出 token，泄露风险高 |

**默认推 A**（在 AskUserQuestion 里把 A 标 "推荐"）。

### 第 3 步：根据用户选择写入

**A 路径**（推荐）：
```bash
# 文件不存在则先创建骨架
if [ ! -f ~/.claude/secrets.md ]; then
  cat > ~/.claude/secrets.md << 'EOF'
# Secrets

# 格式：KEY=VALUE（每行一条，# 开头是注释）

EOF
fi
# 追加或替换 BAILIAN_TOKEN 这一行
grep -v "^BAILIAN_TOKEN=" ~/.claude/secrets.md > /tmp/secrets.tmp
echo "BAILIAN_TOKEN=<用户的token>" >> /tmp/secrets.tmp
mv /tmp/secrets.tmp ~/.claude/secrets.md
# 校验
grep "BAILIAN_TOKEN=" ~/.claude/secrets.md
```

**B 路径**：
```cmd
setx BAILIAN_TOKEN "<用户的token>"
```
告诉用户「**新开 cmd 后才生效**，本次对话如果继续要用，需要重启 cmd 或改用 A 路径」。

**C 路径**：警告用户分享风险（"也"请用户确认接受风险再写），不推荐。

### 第 4 步：完成 onboarding，进入正常调用

写入完成后，告诉用户「token 已存到 Y，下次直接用就行」，然后按下面"触发判断 + 调用方式"正常调脚本。

---

## 触发判断

**T2I 触发**：用户明确要求生成一张**新**的图片素材。
- ✅ 「帮我画一张」「做个 logo」「生个图」「给我出个效果图」「画个头像」「做个 banner」
- ❌ 「这图是什么意思」「看一下这张图」（讨论/理解已有图）

**I2I 触发**：用户明确要**修改/编辑**某张已存在的图，且你能拿到图片路径。
- ✅ 「把这张图改成夜景」「修一下那个 logo」「换种风格」「背景换成雪山」「去掉这个水印」
- ❌ 「这张图怎么做的」（只是询问，不是要编辑）

## 调用方式

```bash
python "C:/Users/admin/.claude/skills/solo-img-line-cy-bailian-image-gen/gen_image.py" "<prompt>" [options]
```

### 参数

| 场景 | 命令 |
|------|------|
| 文生图 | `... "一只橘猫"` |
| 图编辑（本地图） | `... "改成夜景" --image C:/path/to/room.png` |
| 图编辑（多图参考，最多 3） | `... "参考构图" --image a.png --image b.png` |
| 图编辑（远程 URL） | `... "改成日式" --image-url https://...jpg` |
| 指定尺寸 | 加 `--size 1280*720` / `1024*1536` |
| 多张备选 | 加 `-n 2` 或更多 |
| 手动指定模型 | `--model wan2.7-image-pro` 或 `--model qwen-image-3.0-pro` |

### Prompt 改写纪律

- 用户的中文/短描述**直接传**，不要替用户大改 prompt
- 用户描述太含糊（只有"做个图"）→ **先追问**用户要什么，不要硬猜
- 不要编造用户没说的元素

## 模型分流（auto 模式）

默认 `--model auto`，脚本按 prompt 关键词 + 是否传 `--image` 自动选 `qwen-image-3.0-pro` 或 `wan2.7-image-pro`。

| 场景 | 走哪个 |
|------|-------|
| 有 `--image`（I2I 图编辑） | **qwen**（强制） |
| UI / mockup / 界面 / dashboard / 后台 / 应用 / Web | **qwen** |
| 海报 / banner / 配文 / 题图 / 副标题 / 菜单 / 试卷 / 报纸 / PPT / 信息图 | **qwen** |
| icon / 图标 / 插画 / 空状态 / 引导页 / 概念图 / Logo | **qwen** |
| 人像 / 肖像 / 真人 / 团队介绍 / portrait / realistic | **wan** |
| 写实场景 / 拟物 / 产品摄影 / photography | **wan** |
| 同一角色多造型 / 系列图 / consistent character / series | **wan** |
| 品牌色 / 调色盘 / Hex / 4K / 印刷 / 大屏 | **wan** |
| 其他默认 | **qwen** |

软件设计场景（你是做软件设计的项目）：绝大多数 UI / 设计 / 配图场景都走 qwen，真人头像/拟物/系列图才换 wan。

## 完成后动作

1. 把图片保存路径告诉用户（绝对路径）
2. 用户没指定输出目录时默认 `./out/`，告知位置
3. 任务结束，**不要**自动接着"看看好不好""要不要再改"——等用户回话

## 失败处理

- **报错「未找到 BAILIAN_TOKEN」**：token 没配置，**回到本 skill 顶部"首次使用引导"走 onboarding 流程**
- HTTP 401/403：token 失效或权限不足，让用户去百炼控制台检查
- HTTP 400 + `url error`：模型不在白名单或 endpoint 错，已实测只有 `qwen-image-3.0-pro` 走 `/services/aigc/multimodal-generation/generation`、`wan2.7-image` 系列走 `/compatible-mode/v1/chat/completions`
- 网络错误/超时：稍等重试，**不要**自动重试超过 2 次

## 关键事实（踩坑来的）

1. **走 DashScope 原生 MultiModalConversation，不是 OpenAI 兼容端点**
   - ✅ `POST .../api/v1/services/aigc/multimodal-generation/generation`
   - ❌ `/compatible-mode/v1/chat/completions`（该路径下 qwen-image-3.0-pro 报 url error）
   - ❌ `/images/generations`（百炼没接 OpenAI 标准生图路径）
   - ❌ `/apps/anthropic/v1/messages`（那是给 Claude Code 当对话 backend 的）

2. **content 是 list 形式**，元素是 `{"text": ...}` / `{"image": ...}`。I2I 时 image 和 text 都在同一个 messages 里，image 接受 base64 data URL 或公网 URL。T2I 时只传 `{"text": ...}`

4. **最多 3 张参考图**

5. **仅限交互式使用**，禁止批量/自动化调用（违反 Token Plan 服务条款）

6. **脚本里没有 token 兜底**，必须先走 onboarding
