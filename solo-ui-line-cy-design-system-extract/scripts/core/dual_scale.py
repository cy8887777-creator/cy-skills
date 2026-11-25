# -*- coding: utf-8 -*-
"""dual_scale.py — 正文多倍图双标自动改造（1× 主口径，括注 @2x 源稿值；CSS 渲染区不动）

口径：源稿 750 @2x → 正文 token 主口径 1x（=源值÷2），括注 @2x 源稿值。
安全规则：
  - <style> 块 / style="" 属性 / <script> 块整体摘除后转换，再放回（CSS 渲染保持源稿原样）
  - 排除：口径基准值（--skip，默认 375/750/812）、已含"（@2x"的重复处理（幂等）、
    < 1px 的亚像素值（折算无意义）
用法：
    python dual_scale.py <design-system.html> [system-rules.md] [--dry] [--skip 375,750,812]
    （第二参数可选；合流管线只传 HTML——md 由已双标 HTML 派生，天然 1x 口径）
    --dry 预览样例不实写；幂等可安全重放。
计数说明：「字号对」仅命中"字 N/权重三档"写法（如"字 24/700"）；其他字号写法不计数，以 px双标/尺寸对为准。
来源：跑腿案例产物 work/dual_scale.py 回流泛化（2026-10-23；原版 by 案例执行现场）。
"""
import re
import sys
from pathlib import Path


def half(v):
    f = float(v) / 2
    return "%g" % round(f, 2)


def make_convertors(skip):
    n = {"px": 0, "dim": 0, "w": 0}

    def ok(v):
        return v not in skip and float(v) >= 1.0 and "（@2x" not in v

    def px_repl(m):
        pre, v = m.group(1), m.group(2)
        if not ok(v):
            return m.group(0)
        n["px"] += 1
        return "%s%spx（@2x %spx）" % (pre, half(v), v)

    def dim_repl(m):
        pre, a, b = m.group(1), m.group(2), m.group(3)
        if a in skip or b in skip or float(a) < 1 or float(b) < 1:
            return m.group(0)
        n["dim"] += 1
        return "%s%s×%s（@2x %s×%s）" % (pre, half(a), half(b), a, b)

    def w_repl(m):
        v, w = m.group(1), m.group(2)
        if v in skip:
            return m.group(0)
        n["w"] += 1
        return "字 %s（@2x %s）/%s" % (half(v), v, w)

    px_pat = re.compile(r"([^>\d（.（@]|^)(\d+(?:\.\d+)?)px(?!\）|（)")
    dim_pat = re.compile(r"([^>\d（.（@]|^)(\d+(?:\.\d+)?)×(\d+(?:\.\d+)?)(?=[\s·（<,])")
    w_pat = re.compile(r"字 (\d+(?:\.\d+)?)/(\d{3})")
    return px_pat, px_repl, dim_pat, dim_repl, w_pat, w_repl, n


def convert(text, skip):
    px_pat, px_repl, dim_pat, dim_repl, w_pat, w_repl, n = make_convertors(skip)
    text = px_pat.sub(px_repl, text)
    text = dim_pat.sub(dim_repl, text)
    text = w_pat.sub(w_repl, text)
    return text, n["px"], n["dim"], n["w"]


def protect(text):
    """摘除 CSS/JS 区 → 返回 (受保护文本, 恢复函数)"""
    store = []

    def stash(m):
        store.append(m.group(0))
        return "\x00%d\x00" % (len(store) - 1)

    text = re.sub(r"<style[^>]*>.*?</style>", stash, text, flags=re.S)
    text = re.sub(r"<script[^>]*>.*?</script>", stash, text, flags=re.S)
    text = re.sub(r'style="[^"]*"', stash, text)

    def restore(t):
        return re.sub(r"\x00(\d+)\x00", lambda m: store[int(m.group(1))], t)

    return text, restore


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 1:
        print(__doc__)
        return 2
    dry = "--dry" in sys.argv
    skip = {"375", "750", "812"}
    if "--skip" in sys.argv:
        skip |= {s.strip() for s in sys.argv[sys.argv.index("--skip") + 1].split(",") if s.strip()}

    for path in args:
        p = Path(path)
        raw = p.read_text(encoding="utf-8")
        body, restore = protect(raw)
        new_body, a, b, c = convert(body, skip)
        new = restore(new_body)
        print("%s: px双标 %d 处, 尺寸对 %d 处, 字号对 %d 处" % (p.name, a, b, c))
        if dry:
            seen = 0
            for m in re.finditer(r".{16}\d+(?:\.\d+)?px（@2x \d+(?:\.\d+)?px）", new):
                print("   样例:", m.group(0).replace("\n", " "))
                seen += 1
                if seen >= 4:
                    break
        else:
            p.write_text(new, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
