"""
scripts/core/fetch_iconset.py — 开源图标库整库下载（Iconify 公开源，标准库实现零依赖）

用途（站④ 图标章规程）：判定与项目图标风格最匹配的开源图标库后，把该库**全套图标**
下载落盘随产物交付——前端 / AI 加图标时本地直接挑，零搜索成本、风格必然统一。

用法：
    python fetch_iconset.py <prefix> <输出目录> [--height 24] [--limit N]

示例：
    python fetch_iconset.py lucide out/system-spec/assets/icons/lucide
    python fetch_iconset.py tabler out/system-spec/assets/icons/tabler --limit 50   # 试跑前 50 枚

流程：
    1) GET https://api.iconify.design/collection?prefix=<p>  → 枚举全部图标名
    2) 逐个 GET https://api.iconify.design/<p>/<name>.svg?height=<h> → 落盘
    3) 写 manifest.json（库版本信息 + 图标名清单 + 下载时间）——产物溯源用

常用库 prefix：lucide / tabler / ph / mdi / fluent-emoji / solar / hugeicons
（全量清单见 https://icon-sets.iconify.design ；选库依据 = 与项目图标风格比对，见站④ 规程）
"""
import argparse
import json
import sys
import time
import urllib.request
from pathlib import Path

API = "https://api.iconify.design"


def _get(url: str, retries: int = 2) -> bytes:
    last_err = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "design-system-extract/2.1"})
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001 —— 网络抖动重试，最终失败上报
            last_err = e
            time.sleep(1.0)
    raise RuntimeError(f"下载失败 {url}: {last_err}")


def list_icons(prefix: str) -> list[str]:
    data = json.loads(_get(f"{API}/collection?prefix={prefix}").decode("utf-8"))
    names = list(data.get("icons", {}).keys()) + list(data.get("uncategorized", []) or [])
    for alias_group in (data.get("aliases", {}) or {}).values():
        pass  # aliases 是已有图标的别名，不入库（去重）
    return sorted(set(names))


def main():
    ap = argparse.ArgumentParser(description="Iconify 整库 SVG 下载（图标库配套资产包）")
    ap.add_argument("prefix", help="图标库前缀，如 lucide / tabler / ph")
    ap.add_argument("out_dir", help="输出目录，如 out/system-spec/assets/icons/lucide")
    ap.add_argument("--height", default="24", help="SVG height 参数（默认 24；SVG 矢量可缩放，仅影响 viewBox 基准）")
    ap.add_argument("--limit", type=int, default=0, help="仅下载前 N 枚（0=全部；试跑用）")
    args = ap.parse_args()

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    print(f"[..] 枚举图标库 {args.prefix} ...")
    names = list_icons(args.prefix)
    if not names:
        print(f"[FAIL] 库 {args.prefix} 无图标或前缀不存在（全量清单见 icon-sets.iconify.design）", file=sys.stderr)
        return 2
    if args.limit:
        names = names[: args.limit]
    print(f"[OK] 共 {len(names)} 枚，开始下载 → {out}")

    ok, failed = 0, []
    for i, name in enumerate(names, 1):
        try:
            svg = _get(f"{API}/{args.prefix}/{name}.svg?height={args.height}")
            (out / f"{name}.svg").write_bytes(svg)
            ok += 1
        except Exception as e:  # noqa: BLE001 —— 单枚失败不阻塞整库，最终列清单上报
            failed.append(f"{name}: {e}")
        if i % 50 == 0:
            print(f"  ... {i}/{len(names)}")
        time.sleep(0.05)  # 限速，礼貌对待公共 API

    manifest = {
        "source": f"iconify:{args.prefix}",
        "library_url": f"https://icon-sets.iconify.design/{args.prefix}/",
        "height": args.height,
        "count": ok,
        "failed": failed,
        "icons": names,
    }
    (out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[OK] 下载完成 {ok}/{len(names)} → {out}（manifest.json 已登记）")
    if failed:
        print(f"[WARN] {len(failed)} 枚失败：{failed[:5]}{' ...' if len(failed) > 5 else ''}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
