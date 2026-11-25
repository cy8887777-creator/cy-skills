"""
scripts/C/text_llm.py — C-2 纯 LLM 解析

复用：主会话 LLM 能力（**不写 LLM 调用代码**——本脚本只生成结构化提示词）
输入：文本（粘的或文件路径）
产出：out/text_llm_prompt.md（主会话下一步用 Skill 工具调 LLM 解析）

规则（SKILL.md 站 ② C-2）：
  1. 主会话读提示词
  2. 用 LLM 抽取 token / 组件 / 规则
  3. 输出 middle.json
"""
import sys
from pathlib import Path


PROMPT_TEMPLATE = """你是 design-system-extract 的 C-2 引擎（纯 LLM 文本解析）。

## 输入

用户提供以下设计规范文本（粘的或文件）：

```
{user_text}
```

## 你的任务

从文本中**抽取**以下结构化信息，**不编造**——抽不到就标 null：

```json
{{
  "tokens": {{
    "primitive": {{ "<name>": {{ "value": "<hex>", "role": "primary|neutral|functional", "usage": "...", "prohibition": "..." }} }},
    "semantic":  {{ "<name>": {{ "value": "...", "category": "text|bg|border|input|focus|action|font_family|line_height|icon|stroke_color", "usage": "...", "prohibition": "..." }} }},
    "component": {{ "<name>": {{ "value": "...", "owner": "<组件>", "usage": "...", "prohibition": "..." }} }},
    "metric":    {{ "<name>": {{ "value": "<px>", "category": "spacing|radius|shadow|font_size|line_height|padding|stroke_width|opacity|z_index", "usage": "..." }} }}
  }},
  "components": [{{ "name": "...", "variants": ["..."], "states": ["..."], "key_specs": {{}} }}],
  "patterns": {{
    "form_validation": "...",
    "loading_strategy": "...",
    "danger_action": "..."
  }}
}}
```

## 硬规则

1. **不编造 token 值**：文本里没说就 null，不要凑 demo 值
2. **4 段分类严格**：hex → primitive；引用 → semantic；组件专属 → component；px 数值 → metric
3. **不发明组件**：文本里没提的组件不写
4. **疑点全量披露**：抽不到 / 矛盾 / 含糊的地方全部列出

## 产物

输出**仅**JSON（包在 ```json 代码块里），便于落盘到 out/middle.json。
"""


def main():
    if len(sys.argv) < 2:
        print("用法: python text_llm.py <text_or_path> [out_prompt.md]", file=sys.stderr)
        sys.exit(1)
    src = Path(sys.argv[1])
    if src.exists() and src.is_file():
        user_text = src.read_text(encoding="utf-8")
    else:
        user_text = src.as_posix()  # 当作直粘文本

    if len(user_text) < 200:
        print(f"[WARN] 文本过短（{len(user_text)} 字符），可能无法抽取完整 token", file=sys.stderr)
        print(f"[WARN] 建议用户补描述或换其他输入（见 SKILL.md 站 ② C-2 失败处置）", file=sys.stderr)

    prompt = PROMPT_TEMPLATE.format(user_text=user_text)
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("out/text_llm_prompt.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(prompt, encoding="utf-8")
    print(f"[OK] C-2 提示词已生成 -> {out}  ({len(prompt)} chars)")
    print(f"[INFO] 主会话下一步：用 LLM 解析此提示词 + 抽取 JSON + 落盘到 out/middle.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
