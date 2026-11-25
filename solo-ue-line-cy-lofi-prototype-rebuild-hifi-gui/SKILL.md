---
name: solo-ue-line-cy-lofi-prototype-rebuild-hifi-gui
description: 把低保真 HTML 原型升级为高保真 HTML 原型（基底替换法）。当用户要「高保真 / 基底替换 / 低保真转高保真 / lofi to hifi / hifi prototype / 按设计规范换肤 / 设计规范套原型」，且输入是 solo-ue-line-cy-mockingbot-html 技能产出的可编辑 HTML（data-idx 绝对定位 DOM）时使用。不重写页面：复制基底后只做定点替换（字体/颜色/图标/卡片/对齐），验证一律 DOM 断言+几何 probe，禁用视觉模型做测试。
---

# 低保真 HTML → 高保真 HTML（基底替换法）

## 是什么 / 不是什么

**是**：把「墨刀导出包 → 可编辑 HTML」（solo-ue-line-cy-mockingbot-html 技能产物）作为**基底**原样复制，在客户 Figma 设计规范 + 美术素材库约束下，用 transform 脚本做**定点替换**——字体、色板、按钮、卡片、图标、对齐（v2 立项方法论六条全档见 pitfalls ⑧）。

**不是**：不凭空生成 html、不重写基底、不翻主题基调（浅色基底配客户 Light 系）、不加任何原型里没有的文案、不找外站图标（icons8/3dicons/thridy 全禁——thridy 实测全站带水印）。

## 三输入依赖（缺一先补，不开工）

1. **基底 html**：墨刀导出包的转换产物（375×812、每节点 div+行内 style、`<!-- [idx] -->` 注释、z-index=idx）。墨刀原始「演示模式.html」是运行时渲染，**不能**当基底
2. **设计规范**：客户 Figma 导出的 Design System 目录（`figma-node.raw.json` 可按 nodeId 反查语义；规范值用脚本提取，不手抄 Figma）
3. **素材库**：单一来源 3D 库（`manifest.md` 索引）。**manifest 是语义权威但会滞后，用户会重组目录——引用前以实际目录为准**；盘点时 png/svg/webp 全要翻

## 分步流程（八步）

1. **前置确认**：读 memory/决策记录确认已拍板口径（不重新问）；盘全规范目录（Background/Buttons/Cards/Colour Palette/Icons 全部过一遍，只看 Icons=偷懒）；素材 manifest 待判形清零才开工。细则见 [references/spec.md](references/spec.md) §1
2. **建映射表**：先产出「图标位 → 素材 → 语义依据」映射表，nodeId 反查+判形**双确认**查证完才准落码（语义磨 7 轮的根因就是跳过这步）→ spec §2
3. **基底核查与复制**：复制前验证资源依赖（img src 与 style url() 两处）；复制后通读盘点替换点（大文件分段读）；上游引号截断 bug（style 属性内未转义双引号）换字体栈时顺手修 → spec §1
4. **逐类替换**：顺序=字体→色板→按钮→卡片→图标，每类一段独立 transform 脚本+一次校验，一把全换=出错无法定位 → spec §3
5. **几何与对齐**：联动让位/锚点边对齐/中心线量化 0.5px/8pt 微调+注释标原值 → spec §4
6. **验证**：grep 收尾 → CDP DOM 断言 → PIL ASCII 判形三层链；probe-clip 三通道清零 → spec §5
7. **缺口清单交付**：客户库缺→近义替代要明说；3D 生成缺→只报中文清单（提示词不由 AI 出，生成完全交用户），现状 2D 占位
8. **收口**：拍板口径当场落 memory/决策记录；版本注释进 html 头部；实验产物用户定性前不 git 提交

## 硬规则红线（18 条——每条实锤事故级，违反=返工/怒斥）

1. **复制基底，禁止重写**——「你直接复制进去就完了 干嘛要重写一遍？？」
2. **严禁自编文案**——只许动样式（颜色/渐变/描边/投影/尺寸/字重/位置），原型没有的文案一个字不许加
3. **不得擅改基底基调**——「你做什么深色底啊 英文的不是浅色背景么」
4. **3D 图标唯一来源=素材库**（客户素材+用户生成），外站一律不用；tag/称号族素材禁挪功能位
5. **缺素材只报中文缺口清单，不出提示词**——「你就说你缺什么素材…中文的」
6. **规范替换不能无脑覆盖墨刀内容真值**——两源冲突（如按钮撞色）单列 A/B 请示拍板
7. **原型漏画≠照搬空缺**——缺口主动补全（同血缘素材或请示），忠实空缺=半成品
8. **data-idx 是唯一可靠锚点**——同串节点字符串定位必歧义
9. **整行替换锚到旧行末尾 + 每次 transform 后跑 div 开/闭平衡**——残尾 `</div>` 提前闭合 .stage = 下半页 89 节点整体错位
10. **换 3D 必隐藏旧 2D 容器族**（成对层同步改），否则 2D/3D 叠影
11. **svg currentColor 染 svg 所在层，不是外层容器**；全局 `[data-idx] svg{display:block}` 防 inline 基线下坠被裁顶
12. **断言失败不写盘**——sub 带命中次数断言，全部通过才 write；跑完 grep 残留回验（退出码 0 ≠ 替换生效）
13. **先映射表后落码**——语义查证完（nodeId 反查+判形双确认）才准写替换脚本
14. **禁用视觉模型做测试**——验证=DOM 断言+几何 probe+PIL ASCII；截图只落盘供人工验收；视觉模型报告须逐条 DOM 反查甄别
15. **验证视口锁手机版式（≥423×900）+几何一律相对 .stage 原点**——视口太窄 stage 被 flex 压缩是验证环境问题不是页面问题
16. **「挂上了」≠「生效了」**——动画/裁切类改动要双采样实测或结构断言，没实测不许宣称完成（「你越没加啊，编瞎话」）
17. **布局微调限 8pt 节奏+注释标原值**；组件改尺寸必查下方邻居联动让位
18. **实验产物用户定性前不 git 提交**；拍板口径当场落 memory/决策记录（口径外置，防会话崩溃丢口径）

## 高频坑速查（按症状 → [references/pitfalls.md](references/pitfalls.md)）

| 症状 | 根因 | pitfalls 章节 |
|------|------|------|
| 下半页整体错位 / 底栏下空一条 | 残尾 `</div>` 提前闭合 .stage | ③⑤ |
| 图标换了但没变色 | currentColor 染了外层容器 | ③ |
| 图标顶部被裁一条 | svg inline 基线下坠 | ③ |
| 截图判形全乱 / 坐标全偏 24px+ | 视口压缩 stage / 没减 stage 原点 | ⑥ |
| verify 全绿但用户说不生效 | verify 只测改过的层 / 挂上≠生效 | ⑥ |
| 替换脚本报锚点未命中 | 同串歧义 / 构造串被历史变更污染 | ⑤ |
| 文字折行出孤字 | 字体宽度差异，scrollWidth 断言缺失 | ⑥ |
| 图标语义用错连环返工 | 判形误判进档案 | ② |
| overflow:hidden 加了裁不到目标层 | data-idx 平级 absolute，裁切需真父子 | ③ |
| img 引用批量 broken | 相对路径深度 / 无扩展名素材编号是目录 | ⑤ |

## 工具速查（scripts/ 七件套，Windows + Node 22+/Python，CDP 端口默认 9224）

```bash
# 1. Figma 节点反查（素材语义判定主力：文件名 3236-2267 → nid 3236:2267 → name+父链；--find 反搜）
python inspect-node.py <figma-node.raw.json> --nid 3236:2267,... [--find 关键词] [--depth 3]

# 2. 判形探针（素材语义辅助；结论须 nodeId 反查双确认）
python inspect-shape.py <素材...> [--width 44] [--colors 3]

# 3. 全页显示不全扫描（A 裁切 / A2 img 越盒 / B 越出 stage / C 文字溢出；清零=通过）
node probe-clip.mjs <page.html> [port]

# 4. 几何实测（指定层渲染盒 stage 相对坐标 + Range 文字精确宽；对齐全用数字算）
node probe-geom.mjs <page.html> <idx,idx,...> [port]

# 5. 批量改版模板（复制改名 transform-<版本>.py 填规则；断言失败不写盘+div 平衡检查）
python transform-tpl.py   # 复制后编辑 TODO 区

# 6. 断言骨架（复制改名 verify-<页>.mjs 填断言；断言只增不减，是防回归活文档）
node verify-<页>.mjs <page.html> [port]

# 7. 分区截图（stage 相对坐标 clip；只落盘供人工验收，禁止当测试依据）
node shot.mjs <page.html> <out.png> <x,y,w,h> [port]   # 全页 0,0,-1,-1
```

CDP 前置（probe/verify/shot 三件跑前必起）：

```bash
"C:\Program Files\Google\Chrome\Application\chrome.exe" --headless=new --remote-debugging-port=9224 --allow-file-access-from-files --window-size=1920,2400 about:blank
# chrome.exe 三候选路径：Program Files / Program Files (x86) / %LOCALAPPDATA%\Google\Chrome\Application
# --allow-file-access-from-files 必带（file:// 页面加载本地资源）；用完按 PID 杀，严禁 taskkill /F /IM chrome.exe（杀用户全部 Chrome）
# 直连用 /json/list（/json/new 会卡死）；换实验线换端口（9224=本技能线约定）
```

**context 防爆纪律**（本技能天生高危：基底 html 大、svg 密集、截图多——会话就是这么崩过的）：大文件分段读/grep 定位后 offset 局部读；probe/verify 长输出重定向文件再挑读；截图只落盘不进 context，判形走 PIL ASCII；transform 脚本落 `.claude-tmp/` 可重跑不依赖会话内状态；拍板口径当场落 memory。全套见 pitfalls ⑦。

## 上下游

- **上游 = solo-ue-line-cy-mockingbot-html 技能**：本技能输入即其产物（产物契约：data-idx 语义、`[idx 图层名]` 注释、z-index=idx、body padding 24 展示壳、`.stage` flex:none）。上游已知 bug（style 属性引号截断、svg 需注入 width/height）在本技能换字体栈时顺手修并回报
- **真值查询回链**：查墨刀真值（入口集/文案/坐标）回上游产物 grep 坐标区段，不回墨刀原始演示 html；阿语 RTL 镜像公式 `x_en = 375 − x_ar − w`
- **端口分工**：CDP 9224=本技能线，9225=墨刀转换线，不互碰
- **交付 Figma 走 MHTML**：Chrome 打开等图片全加载 → Ctrl+S 选「单一文件 MHTML」（打包当时已加载资源；display:none 层带进去属正常）
- **批量预留**：墨刀 550 页全量转换后按页消费，纪律同上游——先 1 页打样→用户验收→再批量；基底复制的资源依赖验证就是流水线接口测试

## 详细规范

分步操作细则见 [references/spec.md](references/spec.md)；200 条坑全档（带出处与用户原话）见 [references/pitfalls.md](references/pitfalls.md)，按症状索引跳转、按需读取。
