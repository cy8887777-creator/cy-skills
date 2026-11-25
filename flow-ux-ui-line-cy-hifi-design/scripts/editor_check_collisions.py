# -*- coding: utf-8 -*-
"""editor_check_collisions — 源稿类名 × 编辑器运行时内置类 撞车检测（附加A 转化线，K1 前置）

转化前必跑：列出让运行时/种子全局规则接管页面样式的"全局可达撞车类"。
用法：
  python editor_check_collisions.py --src <静态稿.html> [--screens id1,id2] [--runtime <参照html>]
  --screens 缺省=全屏；--runtime 缺省=技能自带构建样例 build-qa/pipeline/product.html。
全局可达判定口径：选择器无 .screen/.app/.device/.viewport 前缀限定且层数浅（≤2 层祖先）。
撞车类的漏进属性在转化时由 BASE_PATCH/--app-patch 压回（见 references/editor-conversion.md K1）。
"""
import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def rules(css):
    out, depth, buf = [], 0, ''
    for ch in css:
        buf += ch
        if ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0:
                out.append((buf.strip().split('{')[0].strip(), buf))
                buf = ''
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', required=True, help='静态稿 html（只读）')
    ap.add_argument('--runtime', default=None, help='运行时参照 html（缺省=技能自带构建样例）')
    ap.add_argument('--screens', default=None, help='只查这些屏（逗号分隔 data-screen id），缺省全屏')
    a = ap.parse_args()
    rt_path = a.runtime or (Path(__file__).parent.parent / 'build-qa' / 'pipeline' / 'product.html')
    rt = Path(rt_path).read_text(encoding='utf-8')
    src = Path(a.src).read_text(encoding='utf-8')
    rt_css = '\n'.join(re.findall(r'<style[^>]*>(.*?)</style>', rt, re.S))
    if a.screens:
        segs = []
        for sid in [x.strip() for x in a.screens.split(',') if x.strip()]:
            parts = src.split('data-screen="%s"' % sid, 1)
            if len(parts) < 2:
                print('WARN 源稿无 %s，跳过' % sid)
                continue
            segs.append(parts[1].split('</section>')[0])
        scope = ' '.join(segs)
    else:
        scope = src
    used = set()
    for m in re.findall(r'class="([^"]+)"', scope):
        used.update(m.split())
    coll = {}
    for sel, _body in rules(rt_css):
        if sel.startswith('@keyframes'):
            continue
        for part in sel.split(','):
            p = part.strip()
            if not p or p.startswith('@'):
                continue
            for cm in re.finditer(r'\.([a-zA-Z][\w-]*)', p):
                c = cm.group(1)
                if c in used:
                    coll.setdefault(c, set()).add(p)
    danger = {}
    for c, sels in coll.items():
        globs = [x for x in sels
                 if not re.match(r'^\.(screen|app|device|viewport)\b', x) and x.count(' ') <= 2]
        if globs:
            danger[c] = sorted(globs)[:8]
    print('== 全局可达撞车类', len(danger))
    for c in sorted(danger):
        print('  .%s:' % c)
        for x in danger[c]:
            print('     ', x[:110])
    print('提示：撞车类的漏进属性由转化器 BASE_PATCH/--app-patch 压回（editor-conversion.md K1）；'
          '新撞车类若带布局属性（padding/gap/wrap/padding-top 等），先在产物截图对账确认再补 app-patch。')


if __name__ == '__main__':
    main()
