# 运行环境（references）

Python 解释器选择顺序（每个 python 命令都按此顺序解析）：
1. 环境变量 `I2C_PYTHON` 指定的解释器；
2. `D:\screenshot-to-code\backend\.venv\Scripts\python.exe`（项目 venv，
   依赖与模型通常齐全）；
3. 系统 `python`（缺依赖时由 doctor 引导安装）。

模型文件路径解析顺序：`I2C_BG_MODEL`（直接指定 onnx 文件）→
`I2C_MODELS_DIR` → 技能目录 `models/` →
`D:\screenshot-to-code\backend\models\`。抠图默认**双模型竞速**：
u2net 与 isnet 各抠一份，按确定性指标（背景清净度+中心完整度）打分
择优，全部不合格则回退原图裁剪。脚本自动处理，无需配置。

入场口径（2026-09-30 加固）：两个模型**各自按自己的预处理参数进场**
（u2net 与 isnet 的归一化 mean/std 不同，禁止共用），无信号掩码
（入场缺陷）与低前景掩码（护栏职权）分开记录——竞速必须可审计。

## 运行时依赖形态（S1，技术栈选择时必须提示）

- 含 CDN 的栈（Tailwind / React / Vue / Ionic）：产物打开**需联网**
  （框架库走 CDN）。第 1 步选栈时必须向用户说明这一点；
- 用户需要离线交付时：运行 `scripts/vendor_local.py --html
  <产物>\index.html`，把所选栈的框架依赖落盘到 `assets/vendor/` 并
  改写引用——**仅在用户要求时做**，默认行为不变（保持产物单文件 +
  CDN 的轻量形态）；
- 图标一律内联 SVG（无运行时依赖），字体由 Google Fonts link 提供
  （探测与产物共用，断言前 verify 会等字体就绪）。
