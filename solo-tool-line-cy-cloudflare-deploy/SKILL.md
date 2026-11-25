---
name: solo-tool-line-cy-cloudflare-deploy
description: Cloudflare对接引导 —— 前端/静态站点发布 Cloudflare Pages 全流程（发布/部署/上线/Cloudflare对接），任意项目通用，项目连接信息从项目内文件发现。用户喊"发布"即用本技能
---

# Cloudflare对接引导（→ Cloudflare Pages，任意项目通用）

本技能**不带任何项目信息**。每个项目的项目名 / token / 账户 ID / 构建产物目录，一律从**项目内文件**发现（见下），其他项目拿来即用。

## 第 0 步：发现项目配置（每次先做）

按顺序在项目内找连接信息，找到即用：

1. **私有部署脚本**（惯例位置 `.claude-tmp/deploy-*.sh`，gitignore 不入库）：成熟的脚本自含项目名、token 路径、账户 ID、产物目录，直接跑第 2 步
2. **wrangler 配置**（仓库根 `wrangler.jsonc` / `wrangler.toml`）：`pages_build_output_dir` 指向构建产物目录
3. **package.json**：`build` / `deploy` 类脚本名确认构建入口
4. 以上都没有 → 走「附录 B：首次接入新项目」；token 没有 → 走「附录 A：建 token」

## 第 1 步：发布前置检查

0. **发布指令与 git 同步（铁律）**：
   - 只有用户明确说"发布 / 部署 / 上线 / 更新线上"才执行本技能的构建部署；改完代码自测通过只到"请示本地 commit"为止，**不得顺手部署**
   - 顺序：**①本地 commit → ②push 远程 → ③Cloudflare 部署**。部署前确认 `git status` 干净、最新 commit 已在远程主干上——仓库没同步完不部署
   - 整体 build+部署耗时，不要无意义重复跑
   - 多项目仓库看本次 commit 改了哪个工程就发哪个（可能多个都发）
1. **token 在不在**：读项目约定的私有 token 文件（惯例 `.claude-tmp/cloudflare-token.txt`，应为一行 `cfut_` 开头）。不存在 → 附录 A
2. **构建入口在不在**：package.json 应有 build 类脚本
3. **wrangler 配置合法性**：必须有 `pages_build_output_dir`；**不许有** `account_id` / `assets` 键（Pages 模式禁此二键）

## 第 2 步：构建

按项目自己的构建命令跑（第 0 步发现的 build 脚本），产物目录以 `pages_build_output_dir` 为准。构建报错按报错修；若项目 mock 依赖 dev 中间件，注意生产构建可能需要运行时 mock 方案——这是项目自己的事，与部署无关。

## 第 3 步：部署

优先跑第 0 步发现的项目部署脚本。脚本缺失（新机器/新项目）时内联等价命令（含**代理自动探测**——只在代理软件活着时才 export，没开时硬 export 反而 fetch failed）：

```bash
cd "<项目根>"
if curl -s -o /dev/null --max-time 3 -x http://127.0.0.1:9567 https://api.cloudflare.com/client/v4/ 2>/dev/null; then
  export HTTPS_PROXY=http://127.0.0.1:9567 HTTP_PROXY=http://127.0.0.1:9567
else
  unset HTTPS_PROXY HTTP_PROXY
fi
export CLOUDFLARE_API_TOKEN=$(tr -d '[:space:]' < <项目token文件>)
export CLOUDFLARE_ACCOUNT_ID=<项目账户ID>
npx wrangler pages deploy <产物目录> --project-name <项目名>
```

（代理端口 `127.0.0.1:9567` 是本机惯例，按实际改。）

## 第 4 步：线上验证

curl 直连实测可达（不加代理前缀）：

```bash
curl -s -o /dev/null -w "%{http_code} %{size_download}B\n" https://<项目名>.pages.dev/
curl -s https://<项目名>.pages.dev/ | grep -o "<title>[^<]*"
curl -s -o /dev/null -w "%{http_code}\n" https://<项目名>.pages.dev/<一条深链路由>
```

通过标准：首页 200、标题正确、深链 200（SPA 需 `_redirects` 回退到 index.html）。

## 第 5 步：汇报

向用户汇报：部署 URL、上传文件数、验证结果、本次构建内容摘要。

## 坑位对照表（踩过的，出错先查这里）

| 症状 | 原因 | 处置 |
|---|---|---|
| `Unable to resolve api.cloudflare.com` | 命令行不继承系统代理（代理软件开着时） | 探测后 export `HTTPS_PROXY/HTTP_PROXY`；deploy 脚本应内置探测 |
| `fetch failed`（部署/上传阶段网络错误） | 代理软件**没开**但命令行硬 export 了代理 | `unset HTTPS_PROXY HTTP_PROXY` 直连重试（api.cloudflare.com 直连实测可达）；别无条件前缀代理 |
| `Failed to automatically retrieve account IDs` | Pages-only token 查 `/accounts` 恒空，wrangler 自动获取必挂 | 显式 `CLOUDFLARE_ACCOUNT_ID=<ID>`，且需 wrangler 配置先合法 |
| 部署报 config 不支持 `account_id`/`assets` | Pages 模式配置禁此二键 | 删掉，保留 `pages_build_output_dir` |
| `Missing entry-point`（Delegating to Workers） | wrangler 4.x pages 命令默认委托新路线 | `pages project create` 与首次 deploy 加 `--force` 走旧版直传；**项目建好后绝不再加** |
| 想走浏览器 OAuth 授权 | AI 会话非交互环境跑不通 | API token 是唯一可行路线（附录 A） |
| `*.html` 资源线上 308 → 无扩展名 | Pages 漂亮 URL 自动去扩展 | 浏览器自动跟随重定向，功能无影响，不用处理 |
| 部署偶发 DNS/网络抖动失败 | 网络波动 | 直接重试一次通常即过 |
| 浏览器打不开 pages.dev | 国内直连不稳 | 提醒用户开代理访问 |

## 红线

- **token 绝不进 git、绝不写入任何项目文件**，只存 gitignore 的私有路径（惯例 `.claude-tmp/cloudflare-token.txt`）
- 部署脚本、构建产物、同步中间层保持 gitignore
- 多会话共仓：不回滚他人对 wrangler 配置 / .gitignore 的改动

## 附录 A：建 token 步骤（token 缺失时引导用户）

1. 用户开 https://dash.cloudflare.com/profile/api-tokens → 创建令牌 → **创建自定义令牌**（别选"读取所有资源"模板，那是只读）
2. 权限：账户 → **Cloudflare Pages → 编辑**
3. 账户资源：包括 → 用户自己的账户
4. 创建后复制 `cfut_` 开头的值（只显示一次），发到会话里
5. 会话写入项目私有 token 文件（惯例 `.claude-tmp/cloudflare-token.txt`，覆盖旧值）
6. 账户 ID 从 dashboard 首页右侧「Account ID」复制，随项目存档（部署脚本/项目私有配置），不要写进本技能

## 附录 B：首次接入新项目

1. 确认产物：构建后确定静态产物目录，写 `wrangler.jsonc`：`{ "pages_build_output_dir": "<产物目录>" }`（不要 `account_id`/`assets`）
2. 建 token（附录 A）存 `.claude-tmp/cloudflare-token.txt`；产物目录/token 路径补进 `.gitignore`
3. 建项目：`npx wrangler pages project create <项目名> --force`（4.x 必须 `--force`，见坑位表）
4. 首次部署也带 `--force`；此后一律不带
5. SPA 路由：产物目录放 `_redirects`（内容 `/* /index.html 200`）保证深链可达
6. 访问控制：默认公开；需要门禁时再上 Cloudflare Access，别预先加
7. 落一个私有部署脚本 `.claude-tmp/deploy-pages.sh`（代理探测 + token/账户 ID + deploy 命令），下次直接跑
