#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
image-gen skill：T2I 文生图 + I2I 图编辑 + T2V 文生视频（统一脚本）
================================================================
调用：百炼原生 MultiModalConversation API（图文）
     百炼原生 video-generation/video-synthesis API（视频，异步）

endpoint（图）：
  https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation
endpoint（视频）：
  https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis
  （需 X-DashScope-Async: enable，异步轮询）

模型（图）：
  qwen-image-3.0-pro（默认，UI/设计/文字渲染强项）
  wan2.7-image-pro（写实/品牌色/系列图强项）
模型（视频）：
  wan2.5-t2v-preview（文生视频 + 带音频，5/10 秒）— 默认
  wan3.0-video（最新，2-30 秒，无音频）
  wan2.2-t2v-plus（5 秒）

用法：
  # T2I：纯文本生图
  python gen_image.py "一只穿西装的橘猫"

  # I2I：基于本地图编辑
  python gen_image.py "改成夜景" --image room.png

  # T2V：纯文本生视频（异步，1-5 分钟）
  python gen_image.py --video "玻璃碎片缓慢旋转，背景纯色，电影感光影" --duration 5

  # T2V：循环视频（无音频，5 秒，720P）
  python gen_image.py --video "水晶球缓慢漂浮，循环无缝" --duration 5 --resolution 720P --no-audio

参数（图）：
  --prompt        文本指令（必填）
  --image         本地图片路径（I2I，可多次，最多 3 张）
  --image-url     远程图片 URL（I2I，可多次，最多 3 张）
  --size          1024*1024 / 1280*720 / 1024*1536 等
  -n, --num       生成张数（默认 1）
  -o, --out-dir   输出目录（默认 ./out）
  --model         auto / qwen-image-3.0-pro / wan2.7-image-pro
  --base          API base

参数（视频，需 --video 触发）：
  --video         触发视频模式
  --duration      视频时长（秒），5 或 10（wan2.5）/ 2-30 整数（wan3.0）
  --resolution    480P / 720P / 1080P
  --ratio         16:9 / 9:16 / 1:1 / 4:3 / 3:4 / adaptive
  --no-audio      不生成音频（部分模型支持）
  --video-model   wan2.5-t2v-preview（默认）/ wan3.0-video / wan2.2-t2v-plus
  --poll-interval 轮询间隔秒（默认 10）

Token 配置（按优先级）：
  1) 环境变量 BAILIAN_TOKEN
  无 token 时直接报错退出 —— 脚本里不放任何 token 兜底

仅限交互式使用，禁止批量/自动化（Token Plan 服务条款）。
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ============== 图文 API 配置 ==============
DEFAULT_BASE = "https://token-plan.cn-beijing.maas.aliyuncs.com/api/v1"
DEFAULT_MODEL = "qwen-image-3.0-pro"
DEFAULT_SIZE = "1024*1024"
MAX_REFERENCE_IMAGES = 3

# ============== 视频 API 配置 ==============
VIDEO_ENDPOINT = "/services/aigc/video-generation/video-synthesis"
DEFAULT_VIDEO_MODEL = "wan2.5-t2v-preview"
DEFAULT_VIDEO_RESOLUTION = "720P"
DEFAULT_VIDEO_RATIO = "16:9"
DEFAULT_VIDEO_DURATION = 5
DEFAULT_POLL_INTERVAL = 10
VIDEO_TIMEOUT = 600  # 总超时 10 分钟


# ============== Token 加载 ==============
def load_token() -> str:
    tok = os.environ.get("BAILIAN_TOKEN", "").strip()
    if tok:
        return tok
    secrets_file = Path.home() / ".claude" / "secrets.md"
    if secrets_file.exists():
        for line in secrets_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line and not line.lower().startswith("bearer "):
                k, v = line.split("=", 1)
                if k.strip() in ("BAILIAN_TOKEN", "TOKEN"):
                    return v.strip().strip('"').strip("'")
            elif line.startswith("sk-"):
                return line
    sys.exit(
        "错误：未找到 BAILIAN_TOKEN。\n"
        "  一次性配置（推荐）：运行 skill 目录下的 set_token.bat，粘贴你的 sk-sp-... 即可。\n"
        "  或手动编辑 %USERPROFILE%\\.claude\\secrets.md，加一行：\n"
        "    BAILIAN_TOKEN=sk-sp-你的key\n"
    )


# ============== 图文 API ==============
def encode_local_image(path: str) -> str:
    p = Path(path)
    if not p.exists():
        sys.exit(f"找不到图片：{p.resolve()}")
    mt, _ = mimetypes.guess_type(str(p))
    if not mt:
        mt = "image/png"
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{mt};base64,{b64}"


def build_content(prompt: str, images: list[str]) -> list[dict]:
    content: list[dict] = []
    for url in images:
        content.append({"image": url})
    if prompt:
        content.append({"text": prompt})
    return content


WAN_TRIGGERS: set[str] = {
    "人像", "肖像", "真人", "拟物", "产品照", "摄影风", "摄影",
    "4k", "印刷", "大屏", "印刷级",
    "角色一致", "系列图", "同一人物", "同款人物", "一致人物", "多造型",
    "品牌色", "色号", "调色盘", "hex",
    "portrait", "realistic", "real person", "photography", "product photo",
    "print", "large screen", "consistent character", "series",
    "same character", "brand color", "color palette",
}


def pick_image_model(prompt: str, has_image: bool) -> tuple[str, str]:
    if has_image:
        return "qwen-image-3.0-pro", "I2I 图编辑只能 qwen-image-3.0-pro（wan 不支持 image input）"
    p = prompt.lower()
    hits = [kw for kw in WAN_TRIGGERS if kw in p]
    if hits:
        return "wan2.7-image-pro", f"关键词命中「{hits[0]}」→ wan2.7-image-pro（写实/品牌色/角色一致性强项）"
    return "qwen-image-3.0-pro", "默认 → qwen-image-3.0-pro（UI/设计/文字渲染/复杂版面强项）"


def generate_image(prompt: str, images: list[str], model: str, size: str | None, n: int, base: str) -> dict:
    url = f"{base}/services/aigc/multimodal-generation/generation"
    payload: dict = {
        "model": model,
        "input": {"messages": [{"role": "user", "content": build_content(prompt, images)}]},
        "parameters": {"n": n},
    }
    if size:
        payload["parameters"]["size"] = size
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {load_token()}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"HTTP {e.code}: {body[:800]}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误: {e.reason}")


# ============== 视频 API（异步） ==============
def submit_video(prompt: str, model: str, resolution: str, ratio: str,
                 duration: int, audio: bool, base: str) -> str:
    """提交视频生成任务，返回 task_id。"""
    url = f"{base}{VIDEO_ENDPOINT}"
    payload: dict = {
        "model": model,
        "input": {"prompt": prompt},
        "parameters": {
            "resolution": resolution,
            "ratio": ratio,
            "duration": duration,
        },
    }
    if not audio:
        payload["parameters"]["audio"] = False
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {load_token()}",
            "X-DashScope-Async": "enable",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            obj = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        sys.exit(f"提交视频任务失败 HTTP {e.code}: {body[:800]}")
    except urllib.error.URLError as e:
        sys.exit(f"网络错误: {e.reason}")
    task_id = obj.get("output", {}).get("task_id")
    if not task_id:
        sys.exit(f"提交响应无 task_id: {json.dumps(obj, ensure_ascii=False)[:500]}")
    return task_id


def poll_video(task_id: str, base: str, interval: int, timeout: int) -> dict:
    """轮询任务直到完成。返回最终 task 对象（含 video_url）。"""
    url = f"{base}/tasks/{task_id}"
    headers = {"Authorization": f"Bearer {load_token()}"}
    deadline = time.time() + timeout
    t0 = time.time()
    while time.time() < deadline:
        req = urllib.request.Request(url, headers=headers, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                obj = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            sys.exit(f"轮询失败 HTTP {e.code}: {body[:500]}")
        status = obj.get("output", {}).get("task_status", "UNKNOWN")
        elapsed = int(time.time() - t0)
        print(f"  [poll {elapsed:3d}s] task_status = {status}")
        if status == "SUCCEEDED":
            return obj
        if status in ("FAILED", "CANCELED"):
            sys.exit(f"视频任务失败：{status}\n{json.dumps(obj, ensure_ascii=False)[:500]}")
        time.sleep(interval)
    sys.exit(f"视频任务超时（{timeout}s）")


# ============== 通用下载 ==============
def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with urllib.request.urlopen(url, timeout=180) as r:
        out.write_bytes(r.read())


# ============== 主入口 ==============
def main() -> int:
    ap = argparse.ArgumentParser(
        description="百炼 image-gen：T2I 文生图 + I2I 图编辑 + T2V 文生视频",
    )
    ap.add_argument("prompt", help="文本指令（必填）")
    # 图相关
    ap.add_argument("--image", action="append", default=[], help="本地图（I2I，可多次，最多 3）")
    ap.add_argument("--image-url", action="append", default=[], help="远程 URL（I2I，可多次，最多 3）")
    ap.add_argument("--size", default=DEFAULT_SIZE, help=f"图尺寸（默认 {DEFAULT_SIZE}）")
    ap.add_argument("-n", "--num", type=int, default=1, help="图生成张数（默认 1）")
    ap.add_argument("--model", default="auto", help="图模型；auto=按关键词自动选")
    # 视频相关
    ap.add_argument("--video", action="store_true", help="切换到视频模式（T2V）")
    ap.add_argument("--video-model", default=DEFAULT_VIDEO_MODEL,
                    help=f"视频模型（默认 {DEFAULT_VIDEO_MODEL}）")
    ap.add_argument("--duration", type=int, default=DEFAULT_VIDEO_DURATION,
                    help=f"视频时长秒（默认 {DEFAULT_VIDEO_DURATION}）")
    ap.add_argument("--resolution", default=DEFAULT_VIDEO_RESOLUTION,
                    help=f"视频分辨率（默认 {DEFAULT_VIDEO_RESOLUTION}）")
    ap.add_argument("--ratio", default=DEFAULT_VIDEO_RATIO,
                    help=f"视频宽高比（默认 {DEFAULT_VIDEO_RATIO}）")
    ap.add_argument("--no-audio", action="store_true", help="不生成音频（部分模型）")
    ap.add_argument("--poll-interval", type=int, default=DEFAULT_POLL_INTERVAL,
                    help=f"轮询间隔秒（默认 {DEFAULT_POLL_INTERVAL}）")
    # 通用
    ap.add_argument("-o", "--out-dir", default="./out", help="输出目录")
    ap.add_argument("--base", default=DEFAULT_BASE, help="API base")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if args.video:
        return run_video(args, out_dir)
    return run_image(args, out_dir)


def run_image(args, out_dir: Path) -> int:
    """图模式主流程。"""
    images: list[str] = []
    for p in args.image:
        images.append(encode_local_image(p))
    for u in args.image_url:
        images.append(u)
    if len(images) > MAX_REFERENCE_IMAGES:
        sys.exit(f"参考图最多 {MAX_REFERENCE_IMAGES} 张，当前 {len(images)} 张")

    if args.model == "auto":
        chosen, reason = pick_image_model(args.prompt, bool(images))
        print(f"[auto]    {reason}")
        args.model = chosen

    mode = "I2I 图编辑" if images else "T2I 文生图"
    print(f"[mode]    {mode}")
    print(f"[prompt]  {args.prompt}")
    if images:
        print(f"[images]  {len(images)} 张参考图")
    print(f"[model]   {args.model}")
    print(f"[size]    {args.size}")
    print(f"[n]       {args.num}")
    print("[call]    ...")

    t0 = time.time()
    obj = generate_image(args.prompt, images, args.model, args.size, args.num, args.base)
    dt = time.time() - t0

    out_urls: list[str] = []
    for ch in obj.get("output", {}).get("choices", []):
        for blk in ch.get("message", {}).get("content", []):
            if blk.get("type") == "image" and blk.get("image"):
                out_urls.append(blk["image"])
    usage = obj.get("usage", {})
    print(f"[done]    {len(out_urls)} 张，耗时 {dt:.1f}s")
    print(f"[usage]   {json.dumps(usage, ensure_ascii=False)}")

    if not out_urls:
        sys.exit("未拿到图片，检查响应与权限")

    saved: list[Path] = []
    for i, u in enumerate(out_urls, 1):
        out = out_dir / safe_filename(args.prompt, "png", i, args.num, len(out_urls))
        download(u, out)
        saved.append(out.resolve())
        print(f"  [{i}] -> {saved[-1]}")
    return 0


def run_video(args, out_dir: Path) -> int:
    """视频模式主流程（异步提交 + 轮询 + 下载）。"""
    print(f"[mode]    T2V 文生视频")
    print(f"[prompt]  {args.prompt}")
    print(f"[model]   {args.video_model}")
    print(f"[resolution] {args.resolution}")
    print(f"[ratio]   {args.ratio}")
    print(f"[duration] {args.duration}s")
    print(f"[audio]   {not args.no_audio}")
    print("[submit]  ...")
    t0 = time.time()
    task_id = submit_video(args.prompt, args.video_model, args.resolution,
                           args.ratio, args.duration, not args.no_audio, args.base)
    print(f"[task]    {task_id}")
    print(f"[poll]    间隔 {args.poll_interval}s ...")
    final = poll_video(task_id, args.base, args.poll_interval, VIDEO_TIMEOUT)
    dt = time.time() - t0

    video_url = final.get("output", {}).get("video_url")
    if not video_url:
        sys.exit(f"任务完成但无 video_url：{json.dumps(final, ensure_ascii=False)[:500]}")
    out = out_dir / safe_filename(args.prompt, "mp4", 1, 1, 1)
    download(video_url, out)
    print(f"[done]    1 个视频，耗时 {dt:.1f}s")
    print(f"[video]   -> {out.resolve()}")
    print(f"[warning] video_url 24 小时内有效，已转存到本地")
    return 0


def safe_filename(prompt: str, ext: str, idx: int, total: int, total_count: int) -> str:
    ts = time.strftime("%Y%m%d-%H%M%S")
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in prompt)[:24] or "空"
    if total_count > 1:
        return f"{ts}_{safe}_{idx}.{ext}"
    return f"{ts}_{safe}.{ext}"


if __name__ == "__main__":
    sys.exit(main())
