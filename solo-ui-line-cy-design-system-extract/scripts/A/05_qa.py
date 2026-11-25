"""
scripts/A/05_qa.py — A-05 视觉模型质检（**调裁判子代理**）

复用：design-pack-pipeline/templates/judge-prompt.md（任务书全文）
不做自创逻辑 —— 任务书原文复制；主会话派裁判子代理

输入：out/hifi/{page}/index.html + 原 PNG
产出：out/qa/{page}.report.json
派发：design-pack-pipeline 裁判子代理（任务书全文）
"""
import sys
from pathlib import Path

REUSED = Path(__file__).parent / "_reused"
JUDGE = REUSED / "judge-prompt.md"


def main():
    if len(sys.argv) < 3:
        print("用法: python 05_qa.py <hifi_dir> <原图包目录>", file=sys.stderr)
        sys.exit(1)
    hifi_dir = Path(sys.argv[1])
    img_dir = Path(sys.argv[2])

    if not hifi_dir.exists():
        print(f"[FAIL] {hifi_dir} 不存在", file=sys.stderr)
        sys.exit(2)

    pages = sorted([d.name for d in hifi_dir.iterdir() if d.is_dir()])
    print(f"[INFO] {len(pages)} 页待质检；裁判任务书 = {JUDGE.name}")

    # 任务书原文 + 本批次特定输入
    judge_text = JUDGE.read_text(encoding="utf-8")
    for page in pages:
        sub_prompt = f"""{judge_text}

---

## 本批特定输入

- 页 id：{page}
- 还原 HTML：{hifi_dir / page / "index.html"}
- 原图：{img_dir}/{page}.png
- 产出：out/qa/{page}.report.json
"""
        out_file = Path("out/qa") / f"{page}_subagent_prompt.md"
        out_file.parent.mkdir(parents=True, exist_ok=True)
        out_file.write_text(sub_prompt, encoding="utf-8")
        print(f"[OK] 打包 {page} 裁判子代理提示词 -> {out_file}")

    print(f"\n[INFO] {len(pages)} 份裁判子代理提示词已生成，主会话下一步用 Task 派发")
    return 0


if __name__ == "__main__":
    sys.exit(main())
