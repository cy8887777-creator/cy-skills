# -*- coding: utf-8 -*-
"""editor_gen_claims — 片段 → 交互断言（interaction-claims）生成器（附加A 转化线）

把试点期手工造 claims 的做法工具化（复核 P1：正式链第 4 步的 claims 输入此前无生产者）。
verify-interactions.mjs 只消费开工文档（或任意 start-doc 文件）里的 ```interaction-claims 围栏；
本工具从片段反扫生成围栏文本，执行者把它嵌入 intake/开工文档.md §6 后跑真点验收。

生成规则（试点验证口径）：
  - data-eid + data-on goto 且目标屏在片段包内 → 真断言（click → 断言目标屏 .on）
  - 目标屏不在包内 → decorative 降级（断言"停留本屏"，验证点击通路不崩不误跳，目标屏待全量验收）
  - 每屏筛选 chips（.fchip.chip）取 1 条选中态断言（click → .on 落在被点 chip）
  - --guard "页id:CSS选择器"（可多次）：防过度交互断言——断言该选择器元素不带 data-on
    （源稿视觉暗示可点但业务无落点的元素，转化不得发明交互）

用法：
  python editor_gen_claims.py --pages <片段目录> [--out <围栏文本.md>] [--guard "page-submit:sel:.shot .del"]
输出：围栏全文（```interaction-claims ... ```）——--out 落盘或 stdout。
"""
import argparse
import io
import re
import sys
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--pages', required=True, help='片段目录（page-*.html 主屏 + 占位屏）')
    ap.add_argument('--out', help='围栏文本输出文件（缺省 stdout）')
    ap.add_argument('--guard', action='append', default=[],
                    help='防过度交互断言，格式 "页id:CSS选择器"，可多次')
    a = ap.parse_args()

    pages = Path(a.pages)
    screens = set()
    bodies = {}
    for p in sorted(pages.rglob('*.html')):  # rglob：分组子目录（pages/<组>/x.html）一并扫描
        t = p.read_text(encoding='utf-8')
        body = t.split('</style>')[-1]
        for m in re.finditer(r'data-screen="([\w-]+)"', body):
            screens.add(m.group(1))
        bodies[p.stem] = body

    claims = []
    for stem, body in sorted(bodies.items()):
        m = re.search(r'data-screen="([\w-]+)"', body)
        if not m or not stem.startswith('page-'):
            continue  # 占位屏容器文件（zz-*）不产 claim，但屏集合已计入
        sid = m.group(1)
        for em in re.finditer(
                r'data-eid="(%s-act-\d+)" data-on="[^"]*goto&quot;:&quot;([\w-]+)&quot;' % sid, body):
            eid, tgt = em.group(1), em.group(2)
            if tgt in screens:
                claims.append({"page": sid, "eid": eid, "action": "goto",
                               "steps": [["click", eid]],
                               "assert": ["selector:.screen.on[data-screen=%s]" % tgt]})
            else:
                claims.append({"page": sid, "eid": eid, "action": "goto",
                               "steps": [["click", eid]],
                               "assert": ["selector:.screen.on[data-screen=%s]" % sid],
                               "decorative": True})
        for cm in re.finditer(r'class="fchip chip" data-eid="([\w-]+)"', body):
            claims.append({"page": sid, "eid": cm.group(1), "action": "tab",
                           "steps": [["click", cm.group(1)]],
                           "assert": ["selector:.fchip.on[data-eid=%s]" % cm.group(1)]})
            break  # 每屏 1 条选中态断言足够

    for g in a.guard:
        if ':' not in g:
            print('FAIL --guard 格式应为 页id:CSS选择器：%r' % g)
            raise SystemExit(2)
        sid, sel = g.split(':', 1)
        claims.append({"page": sid, "eid": "guard", "action": "guard",
                       "steps": [["click", "sel:" + sel]],
                       "assert": ["gone:%s[data-on]" % sel], "decorative": True})

    text = '\n'.join(json_line(c) for c in claims)
    fence = '```interaction-claims\n%s\n```\n' % text
    n_real = sum(1 for c in claims if not c.get('decorative'))
    n_dec = len(claims) - n_real
    if a.out:
        Path(a.out).write_text(fence, encoding='utf-8')
        print('claims %d 条（真断言 %d / decorative %d）→ %s' % (len(claims), n_real, n_dec, a.out))
    else:
        print(fence)
        print('# 共 %d 条（真断言 %d / decorative %d）——嵌入开工文档 §6 后跑 verify-interactions'
              % (len(claims), n_real, n_dec))


def json_line(c):
    import json
    return json.dumps(c, ensure_ascii=False)


if __name__ == '__main__':
    main()
