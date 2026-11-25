# -*- coding: utf-8 -*-
# transform-tpl.py —— 批量改版脚本模板（基底替换法唯一安全写法）
# 用法: 复制本模板改名 transform-<版本>.py，按下面的 TODO 填改版项，跑 python transform-xxx.py
# 铁律（全部实战事故换来，违反必炸）:
#  1. 锚点用完整 style 前缀串（left:220px;top:499px;...），禁止用短锚点截中段——
#     短锚点只吃到旧行中段，残尾 </div> 会提前闭合 stage，其后全部节点被踢出画布（89 节点整体偏移事故）
#  2. 替换 svg 多行元素：墨刀 svg 行可跨多行（path 续行+</svg>+</div>），整行替换必留残尾——
#     替换后必须做 div 平衡检查（本模板自带）
#  3. 断言失败绝不写盘（fail-fast，写一半的文件=下一个会话的雷）
#  4. 成对层（底轨/填充、框/图）必须同一次改版里同步改——只改一半=新 bug
#  5. 每个改版版本独立编号 v2a/v2b/... 落 .claude-tmp/，产物只改一个 index.html，git 是总退路
import io, re, sys

PAGE = r"TODO:目标 index.html 绝对路径"

with io.open(PAGE, "r", encoding="utf-8") as f:
    lines = f.readlines()

def find(idx):
    """data-idx 唯一锚定。注意 'data-idx="6"' 不会误配 'data-idx="60"'（带右引号即完整匹配）"""
    mark = 'data-idx="%s"' % idx
    hits = [i for i, l in enumerate(lines) if mark in l]
    assert len(hits) == 1, "idx %s hits=%d（应为 1，多了说明层号重复/少了说明写错）" % (idx, len(hits))
    return hits[0]

def sub(idx, old, new):
    """行内单点替换：old 必须含完整属性串（含 px），命中且仅命中一次"""
    i = find(idx)
    assert old in lines[i], "idx %s 锚点未命中: %r" % (idx, old[:60])
    assert lines[i].count(old) == 1, "idx %s 锚点命中 %d 次（歧义，换更长锚点）" % (idx, lines[i].count(old))
    lines[i] = lines[i].replace(old, new, 1)

def hide(idx):
    """隐藏空壳/越界层（不动 DOM 结构，可随时恢复）"""
    i = find(idx)
    assert 'style="' in lines[i] and 'display:none' not in lines[i]
    lines[i] = lines[i].replace('style="', 'style="display:none;', 1)

def check_div_balance():
    """div 平衡检查——任何含 </div> 删改的版本写盘前必跑"""
    txt = "".join(lines)
    n_open = len(re.findall(r"<div\b", txt))
    n_close = txt.count("</div>")
    assert n_open == n_close, "div 不平衡: open=%d close=%d（大概率替换留了残尾 </div>）" % (n_open, n_close)

# ---------------- TODO: 改版项写这里 ----------------
# sub("311", "height:48px", "height:56px")           # 例：按钮加高
# hide("272")                                          # 例：隐藏越界空层
# for idx in ("332", "335", "338"): ...                # 例：成组改
# -----------------------------------------------------

check_div_balance()

with io.open(PAGE, "w", encoding="utf-8", newline="") as f:
    f.writelines(lines)
print("transform done, %d lines written" % len(lines))
