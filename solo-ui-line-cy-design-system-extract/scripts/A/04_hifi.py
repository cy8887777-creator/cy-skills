"""
scripts/A/04_hifi.py — A-04 高保真制作（**真触发 image-to-code-skills**）

复用：image-to-code-skills 完整 5 步状态机
不做自创 —— 通过 Skill 工具触发（主会话执行）
        —— 本脚本生成 request.json 喂给 image-to-code-skills 第 1 步契约

input：typical_pages.json + 原 PNG 目录
output：typical_pages.json 同目录的 request/ 子目录，每页 1 个 request.json
"""
import json
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("用法: python 04_hifi.py <typical_pages.json> <原图包目录>", file=sys.stderr)
        sys.exit(1)
    typical_path = Path(sys.argv[1])
    img_dir = Path(sys.argv[2])

    data = json.loads(typical_path.read_text(encoding="utf-8"))
    pages = data.get("typical_pages", [])

    # 准备 request/ 目录
    req_dir = typical_path.parent / "request"
    req_dir.mkdir(exist_ok=True)

    print(f"[INFO] {len(pages)} 张典型页待做高保真")
    print(f"[INFO] 为每页生成 image-to-code-skills request.json")
    print(f"[INFO] 主会话下一步：用 Skill image-to-code-skills，每页传对应 request.json")

    for page in pages:
        # 找原图（typical_pages 里的 page 字段对应 manifest["images"] 里的 id）
        # 这里假设原图文件名 = id 去后缀；实际触发时按 manifest 找
        request = {
            "image": f"{img_dir}/{page}.png",
            "output_dir": f"out/hifi/{page}/",
            "tier": "保真",
            "stack": "HTML + CSS",
            "design_system": None,  # A-06 完成后回填
        }
        out_file = req_dir / f"{page}.request.json"
        out_file.write_text(json.dumps(request, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  [OK] {page} -> {out_file}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
