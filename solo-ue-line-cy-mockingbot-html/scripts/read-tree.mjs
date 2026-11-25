// read-tree.mjs —— 读墨刀侧边栏页面树 → manifest.json（folder/page/层级/cid/名称）
// 用法：node read-tree.mjs <port> <out.manifest.json>
// 层级信号（probe 实测）：DOM 平铺无嵌套，层级 = .rn-list-item 自身 padding-left / 20 - 1（顶层=0）
// 名称载体（probe 实测）：画板自身无 data-name，名称只能从侧边栏 .editable-span 拿 → 本脚本建立全量 cid→name
import fs from 'node:fs';
import { connect } from './cdp.mjs';

const [, , PORT, OUT] = process.argv;
if (!PORT || !OUT) { console.error('用法: node read-tree.mjs <port> <out.manifest.json>'); process.exit(1); }
const c = await connect(PORT);
const { evalJS } = c;

const raw = await evalJS(`(() => {
  return [...document.querySelectorAll('.rn-list-item[data-cid]')].map(el => {
    const span = el.querySelector('.editable-span');
    return { cid: el.getAttribute('data-cid'), txt: (span ? span.textContent : el.textContent || '').trim(),
      folder: /\\bfolder\\b/.test(el.className || ''), expander: !!el.querySelector(':scope > .expander'),
      pl: parseFloat(getComputedStyle(el).paddingLeft) || 0 };
  });
})()`);
if (!raw || !raw.length) { console.error('侧边栏为空'); c.close(); process.exit(1); }

// 按 cid 去重（同 cid 只保留首个；DOM 顺序即树序）
const seen = new Set();
const items = [];
for (const r of raw) {
  if (!r.cid || seen.has(r.cid)) continue;
  seen.add(r.cid);
  r.depth = Math.max(0, Math.round(r.pl / 20) - 1);
  items.push(r);
}

// 栈法重建父子关系
const stack = [];   // stack[d] = 深度 d 的最近节点
for (const it of items) {
  stack.length = it.depth;                 // 弹到深度 < it.depth
  const parent = stack[it.depth - 1] || null;
  it.parent = parent ? parent.cid : null;
  stack[it.depth] = it;
}

// 路径（folder 链，供产物镜像目录结构）
const byCid = new Map(items.map(i => [i.cid, i]));
for (const it of items) {
  const segs = [];
  let p = it.parent ? byCid.get(it.parent) : null;
  while (p) { segs.unshift(p.txt); p = p.parent ? byCid.get(p.parent) : null; }
  it.dir = segs;   // 所属目录链（folder 名 + 嵌套 page 名，按侧边栏真实层级）
}

const manifest = {
  meta: { tool: 'mockingbot-to-html/read-tree.mjs', port: PORT,
    generatedAt: new Date().toISOString(),
    totalDomEntries: raw.length, uniqueItems: items.length,
    folders: items.filter(i => i.folder).length, pages: items.filter(i => !i.folder).length,
    maxDepth: Math.max(...items.map(i => i.depth)),
    depthDist: items.reduce((m, i) => (m[i.depth] = (m[i.depth] || 0) + 1, m), {}) },
  items: items.map(({ cid, txt, folder, expander, depth, parent, dir }) =>
    ({ cid, name: txt, type: folder ? 'folder' : 'page', expander: !!expander, depth, parent, dir })),
};
fs.writeFileSync(OUT, JSON.stringify(manifest, null, 1));
console.log(JSON.stringify({ ok: true, out: OUT, ...manifest.meta }));
c.close();
