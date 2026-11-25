#!/usr/bin/env node
// diagnose.mjs —— 单页挂载诊断（probe8/9 精华收编）：点击指定页面，打印挂载板前后对比
// 用法：node diagnose.mjs <port> <data-map.json> <页面cid> [页面cid…]
// 输出：点击选中态 / 卸载板 / 新挂板 / 当前挂载全列表（名/尺寸/是否 rc 纯段页面画布）
// 用途：batch 报「无新画板挂载」「点击未选中」时定位是空页面、组件源混入还是点击失效
import fs from 'node:fs';
import { connect, sleep, detectModel } from './cdp.mjs';

const [PORT, DATAMAP, ...cids] = process.argv.slice(2);
if (!PORT || !DATAMAP || !cids.length) {
  console.error('用法: node diagnose.mjs <port> <data-map.json> <页面cid> [页面cid…]');
  process.exit(1);
}
const dm = JSON.parse(fs.readFileSync(DATAMAP, 'utf8')).names;
const c = await connect(PORT);
const { evalJS } = c;
const MODEL = await detectModel(evalJS);
console.log(`查看器模型: ${MODEL}`);

// 旧模型画板 = .tree-node.rResCanvas[rc]；新模型（PB=v1）画板 = .pcanvas[data-cid=页面cid]（激活带 .active）
const SNAP = MODEL === 'pcanvas'
  ? `(() => JSON.stringify([...document.querySelectorAll('.pcanvas[data-cid]')].map(el =>
      ({ cid: el.getAttribute('data-cid') || '', w: el.offsetWidth, h: el.offsetHeight }))))()`
  : `(() => JSON.stringify([...document.querySelectorAll('.tree-node.rResCanvas')].map(el =>
      ({ cid: el.getAttribute('data-cid') || '', w: el.offsetWidth, h: el.offsetHeight }))))()`;
const snap = async () => JSON.parse(await evalJS(SNAP)).filter(b => b.w >= 150);
const isRC = (cid) => MODEL === 'pcanvas' ? true : /^rc[A-Za-z0-9]+$/.test(cid);   // pcanvas 模型挂载者即页面画布

const CLICK = (cid) => `(() => {
  const it = document.querySelector('.rn-list-item[data-cid="${cid}"]');
  if (!it) return 'NOT_FOUND';
  it.scrollIntoView({ block: 'center' });
  const r = it.getBoundingClientRect();
  const o = { bubbles: true, cancelable: true, view: window, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 };
  it.dispatchEvent(new MouseEvent('mousedown', o));
  it.dispatchEvent(new MouseEvent('mouseup', o));
  it.dispatchEvent(new MouseEvent('click', o));
  return (it.className || '').includes('active') ? 'ACTIVE' : 'NO_ACTIVE';
})()`;

for (const cid of cids) {
  const before = await snap();
  const st = await evalJS(CLICK(cid));
  await sleep(3500);
  const after = await snap();
  const gone = before.filter(b => !after.some(a => a.cid === b.cid)).map(b => b.cid);
  const add = after.filter(b => !before.some(x => x.cid === b.cid)).map(b => b.cid);
  console.log(`\n==== ${dm[cid] || cid}（${cid}）点击: ${st}`);
  console.log(`卸载: ${gone.join(', ') || '(无)'} | 新挂: ${add.join(', ') || '(无)'}`);
  console.log('当前挂载:');
  for (const b of after) console.log(`  ${isRC(b.cid) ? '[页面画布]' : '[组件源/符号]'} ${b.cid} ${b.w}×${b.h} 名="${dm[b.cid] || '?'}"`);
  if (!st.startsWith('ACTIVE')) console.log(`  ⚠ 点击未选中——条目不在 DOM（树未展开）或命中检测失败`);
  if (!add.length && !gone.length) console.log(`  ○ 无新增无卸载——同板复用（看当前挂载里的非基线 rc 板）或空页面`);
}
c.close();
