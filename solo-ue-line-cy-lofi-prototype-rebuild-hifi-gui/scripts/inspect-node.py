# -*- coding: utf-8 -*-
"""inspect-node.py —— Figma 节点反查（素材语义判定主力：nodeId ↔ name+父链）
用法:
  python inspect-node.py <figma-node.raw.json> --nid 3236:2267,3236:2269   # 正查：素材文件名(3236-2267→nid 3236:2267)的语义
  python inspect-node.py <figma-node.raw.json> --find Nav                   # 反搜：name 含关键词的节点（找图标位的 nid）
  python inspect-node.py <figma-node.raw.json> --nid 3182:2577 --depth 5   # 父链默认最近 3 级，可加深
铁律:
  1. nid 不能猜——文件名差一位（1622/1626 ↔ 1623/1627）也要验证后再定映射
  2. name 是泛化 Object（如 Alt_V3）时，父链 Frame name 才是语义落点
  3. 反查要多轮递进：一次没命中就打目标节点完整父链再查
"""
import json
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def index_tree(node, idmap, path, depth):
    """递归建立 nid -> (name, type, 最近 depth 级父链)"""
    if isinstance(node, dict):
        nid = node.get("id")
        name = node.get("name", "")
        ntype = node.get("type", "")
        if nid and isinstance(nid, str) and ":" in nid:
            idmap[nid] = (name, ntype, " / ".join(path[-depth:]))
        for k, v in node.items():
            if k == "children":
                index_tree(v, idmap, path + [name or ntype], depth)
            else:
                index_tree(v, idmap, path, depth)
    elif isinstance(node, list):
        for it in node:
            index_tree(it, idmap, path, depth)


def main():
    args = sys.argv[1:]
    if len(args) < 3:
        print(__doc__)
        sys.exit(2)
    raw_path = args[0]
    nids, keyword, depth = [], None, 3
    i = 1
    while i < len(args):
        if args[i] == "--nid":
            i += 1
            nids = [s.strip() for s in args[i].split(",") if s.strip()]
        elif args[i] == "--find":
            i += 1
            keyword = args[i]
        elif args[i] == "--depth":
            i += 1
            depth = int(args[i])
        i += 1

    with open(raw_path, "r", encoding="utf-8") as f:
        tree = json.load(f)
    idmap = {}
    index_tree(tree, idmap, [], depth)
    print("indexed %d nodes from %s" % (len(idmap), raw_path))

    for nid in nids:
        # 文件名兼容：3236-2267.png 形式直接传也行
        key = nid.replace("-", ":", 1) if "-" in nid and ":" not in nid else nid
        info = idmap.get(key)
        if info:
            print("nid %-18s name=%r type=%s\n  父链: %s" % (key, info[0], info[1], info[2]))
        else:
            print("nid %-18s 未命中（别猜——检查差一位/换父链再查）" % key)

    if keyword:
        hits = [(k, v) for k, v in idmap.items() if keyword.lower() in v[0].lower()]
        print('\n--find "%s" 命中 %d 个:' % (keyword, len(hits)))
        for k, v in sorted(hits)[:30]:
            print("  %-18s name=%r type=%s 父链: %s" % (k, v[0], v[1], v[2]))


if __name__ == "__main__":
    main()
