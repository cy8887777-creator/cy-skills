"""
scripts/A/02_visual_audit.py — A-02 视觉盘点（**真接 manifest["images"] + 真派子代理**）

复用：design-pack-pipeline/templates/inventory-prompt.md（任务书原文）
     + design-pack-pipeline/templates/inventory-template.md（产出模板）
键名修正：intake.py 输出 manifest 键是 "images"（不是 "pages"）

不做自创逻辑 —— 任务书原文 + 模板原文 + 每张图一个子代理提示词
        —— 主会话用 Task 工具派子代理
"""
import json
import sys
from pathlib import Path

REUSED = Path(__file__).parent / "_reused"
PROMPT = REUSED / "inventory-prompt.md"
TEMPLATE = REUSED / "inventory-template.md"


def main():
    if len(sys.argv) < 2:
        print("用法: python 02_visual_audit.py <pages.manifest.json> [批大小=3]", file=sys.stderr)
        sys.exit(1)
    manifest_path = Path(sys.argv[1])
    batch_size = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    if not manifest_path.exists():
        print(f"[FAIL] {manifest_path} 不存在", file=sys.stderr)
        sys.exit(2)

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    # 键名修正：用 intake.py 真输出 "images"
    images = manifest.get("images", [])
    out_dir = manifest_path.parent  # pipeline/ 同级输出
    inv_dir = out_dir.parent / "inventory"
    inv_dir.mkdir(parents=True, exist_ok=True)

    prompt_text = PROMPT.read_text(encoding="utf-8")
    template_text = TEMPLATE.read_text(encoding="utf-8")

    print(f"[INFO] {len(images)} 张图待盘点；任务书={PROMPT.name} 模板={TEMPLATE.name}")

    # 每张图 1 子代理提示词（主会话用 Task 派）
    for img in images:
        page_id = img.get("id", "?")
        img_file = img.get("file", "")
        # 图包原图路径（project.source_dir + file）
        source_dir = manifest.get("source_dir", "")
        img_path = f"{source_dir}/{img_file}"
        sub_prompt = f"""{prompt_text}

---

## 本批特定输入

- 页 id：{page_id}
- 图片路径：{img_path}
- 产出路径：{inv_dir / (page_id + ".md")}
- 产出模板（**原文照抄**作为格式契约）：

```markdown
{template_text}
```
"""
        out_file = inv_dir / f"{page_id}_subagent_prompt.md"
        out_file.write_text(sub_prompt, encoding="utf-8")
        print(f"  [OK] {page_id} 提示词 -> {out_file}")

    print(f"\n[INFO] {len(images)} 份子代理提示词已生成；主会话下一步：用 Task 派子代理，每批 {batch_size} 个")
    return 0


if __name__ == "__main__":
    sys.exit(main())
