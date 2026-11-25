// read-hotzones.mjs —— 逐页点击收集画板内交互热区（wLr 链接区域 / 带交互 widget）
// 用法：node read-hotzones.mjs <port> <manifest.json> <data-map.json> <out-hotzones.json> [--only cid,…] [--limit N] [--retry]
// 产出 hotzones.json：{ meta, zones: { <板cid>: [{ widgetCid, type, name, x, y, w, h, zi, inters:[{t,trig,toPage,toCanvas,url}] }] } }
//
// 数据源（probe 实测）：热区 widget 的交互定义挂在 React fiber —— DOM div（.tree-node[data-cid]）自身 props 无数据，
// 在其父 fiber（Su 组件）的 props.widget.hotAttr.interactions：
//   { interactionType:1=跳页, interactionTrigger:'tap', targetRBPageKey:目标页面, targetResCanvasKey:目标画布, linkUrl:外链 }
// 坐标：hotAttr.x/y 是父容器相对坐标（不可直接用），必须用 DOM rect 换算回板内绝对坐标（offsetWidth 系，与 extract nodes 同系）
// 懒渲染：不在视口的板内部 .tree-node 不挂载 → 每板 scrollIntoView + 轮询节点数稳定后再扫
// 增量断点：zones 里已有的板跳过；--retry 全部重扫
import fs from 'node:fs';
import path from 'node:path';
import { connect, sleep, detectModel } from './cdp.mjs';

const argv = process.argv.slice(2);
const [PORT, MANIFEST, DATAMAP, OUT] = argv;
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1].split(',').map(s => s.trim()) : null;
const limit = argv.includes('--limit') ? +argv[argv.indexOf('--limit') + 1] : Infinity;
const retry = argv.includes('--retry');
if (!PORT || !MANIFEST || !DATAMAP || !OUT) {
  console.error('用法: node read-hotzones.mjs <port> <manifest> <data-map> <out-hotzones.json> [--only cid,…] [--limit N] [--retry]');
  process.exit(1);
}
const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
const names = JSON.parse(fs.readFileSync(DATAMAP, 'utf8')).names;

const doc = fs.existsSync(OUT) && !retry
  ? JSON.parse(fs.readFileSync(OUT, 'utf8'))
  : { meta: { tool: 'read-hotzones.mjs', generatedAt: new Date().toISOString() }, zones: {} };
const zones = doc.zones || (doc.zones = {});

const c = await connect(PORT);
const { evalJS } = c;
{
  const href = String(await evalJS('location.href'));
  if (!/index\.html/.test(href)) {
    console.error(`✗ 当前 tab 不在墨刀查看器（${href}）`);
    process.exit(1);
  }
}
// 查看器代际（2026-10-20）：legacy=.tree-node.rResCanvas[rc]；pcanvas=PB=v1，画板根 .pcanvas[data-cid=页面cid]。
// widget 级 .tree-node[data-cid] 两代一致，fiber 读取（hotAttr.interactions）逻辑共用——新格式 fiber 结构待全量验证
const MODEL = await detectModel(evalJS);
if (MODEL === 'unknown') { console.error('✗ 无法识别查看器模型'); process.exit(1); }
console.log(`查看器模型: ${MODEL}`);
const ROOT_SEL = MODEL === 'pcanvas' ? '.pcanvas[data-cid]' : '.tree-node.rResCanvas';
const pageCids = new Set(manifest.items.filter(it => it.type === 'page').map(p => p.cid));

// ---------- 与 batch 同款点击 ----------
const CLICK = (cid) => `(() => {
  const item = document.querySelector('.rn-list-item[data-cid="${cid}"]');
  if (!item) return 'NOT_FOUND';
  item.scrollIntoView({ block: 'center' });
  const r = item.getBoundingClientRect();
  if (r.width < 2) return 'ZERO_RECT';
  const o = { bubbles: true, cancelable: true, view: window, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 };
  item.dispatchEvent(new MouseEvent('mousedown', o));
  item.dispatchEvent(new MouseEvent('mouseup', o));
  item.dispatchEvent(new MouseEvent('click', o));
  return (item.className || '').includes('active') ? 'ACTIVE' : 'NO_ACTIVE';
})()`;

const BOARDS = `(() => [...document.querySelectorAll('${ROOT_SEL}')]
  .map(el => ({ cid: el.getAttribute('data-cid'), w: el.offsetWidth, h: el.offsetHeight })))()`;
const isPageBoard = (b) => MODEL === 'pcanvas'
  ? pageCids.has(b.cid || '') && b.w >= 150 && b.h >= 150   // 新模型：画板 cid 即页面 cid
  : /^rc[A-Za-z0-9]+$/.test(b.cid || '') && b.w >= 150 && b.h >= 150;

// ---------- 单板热区扫描（滚动到位 + 懒渲染稳定 + fiber 读） ----------
const SCAN = (cid) => `(() => {
  const b = [...document.querySelectorAll('${ROOT_SEL}')]
    .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(cid)})[0];
  if (!b) return { err: 'gone' };
  b.scrollIntoView({ block: 'center', inline: 'center' });
  const brr = b.getBoundingClientRect();
  const sx = b.offsetWidth / (brr.width || 1), sy = b.offsetHeight / (brr.height || 1);
  const hits = [];
  for (const w of b.querySelectorAll('.tree-node[data-cid]')) {
    const fk = Object.keys(w).find(k => k.startsWith('__reactFiber$'));
    if (!fk) continue;
    const f = w[fk];
    const props = f && f.return && f.return.memoizedProps;
    const widget = props && props.widget;
    const hot = widget && widget.hotAttr;
    const inter = hot && hot.interactions;
    if (!inter || !inter.length) continue;
    const r = w.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) continue;
    hits.push({
      widgetCid: widget.key, type: hot.type, name: (hot.name || '').slice(0, 60),
      x: +((r.x - brr.x) * sx).toFixed(1), y: +((r.y - brr.y) * sy).toFixed(1),
      w: +(r.width * sx).toFixed(1), h: +(r.height * sy).toFixed(1), zi: hot.zIndex || 0,
      inters: inter.map(i => ({ t: i.interactionType, trig: i.interactionTrigger || '', toPage: i.targetRBPageKey || '', toCanvas: i.targetResCanvasKey || '', url: i.linkUrl || i.url || '' }))
    });
  }
  return { hits };
 })()`;

async function scanBoard(cid) {
  // 懒渲染：先滚到位，轮询内部节点数稳定（连续两次相同）
  await evalJS(`(() => { const b = [...document.querySelectorAll('${ROOT_SEL}')].filter(el => el.getAttribute('data-cid') === ${JSON.stringify(cid)})[0]; if (b) b.scrollIntoView({ block: 'center', inline: 'center' }); return 1; })()`);
  let prev = -1, stable = 0;
  for (let i = 0; i < 10 && stable < 2; i++) {
    await sleep(700);
    const n = await evalJS(`(() => { const b = [...document.querySelectorAll('${ROOT_SEL}')].filter(el => el.getAttribute('data-cid') === ${JSON.stringify(cid)})[0]; return b ? b.querySelectorAll('.tree-node[data-cid]').length : -1; })()`);
    if (n === prev) stable++; else { stable = 0; prev = n; }
  }
  return await evalJS(SCAN(cid));
}

// ---------- 主循环 ----------
const pages = manifest.items.filter(it => it.type === 'page');
let todo = only ? pages.filter(p => only.includes(p.cid)) : pages;
todo = todo.slice(0, limit);
console.log(`待处理页面: ${todo.length} / ${pages.length}（已收热区板 ${Object.keys(zones).length}）`);

let doneCount = 0, newBoards = 0, zoneTotal = 0, failStreak = 0;
for (const page of todo) {
  const label = page.dir.concat(page.name).join('/');
  try {
    // 每页校验还在墨刀查看器：tab 崩溃（chrome-error/内存爆）后 click 全 NOT_FOUND，会空转整批——连错 5 页熔断退出保断点
    const href = String(await evalJS('location.href'));
    if (!/index\.html/.test(href)) throw new Error('TAB 离开墨刀查看器（' + href.slice(0, 60) + '）——实例疑似崩溃，重启实例增量续跑');
    let st = await evalJS(CLICK(page.cid));
    if (st !== 'ACTIVE') { await sleep(1200); st = await evalJS(CLICK(page.cid)); }
    if (st === 'NOT_FOUND') throw new Error('条目不在 DOM');
    if (st !== 'ACTIVE') throw new Error('点击未选中（' + st + '）');
    // 等挂载稳定（板数两次相同）
    let prevCnt = -1, stable = 0;
    for (let i = 0; i < 10 && stable < 2; i++) {
      await sleep(1100);
      const bs = await evalJS(BOARDS);
      const n = bs.filter(isPageBoard).length;
      if (n === prevCnt) stable++; else { stable = 0; prevCnt = n; }
    }
    const boards = (await evalJS(BOARDS)).filter(isPageBoard);
    const fresh = boards.filter(b => !zones[b.cid]);
    let got = 0, zn = 0;
    for (const b of fresh) {
      const r = await scanBoard(b.cid);
      if (r && !r.err) {
        zones[b.cid] = r.hits;
        got++; zn += r.hits.length; zoneTotal += r.hits.length;
      }
    }
    if (got) { newBoards += got; fs.writeFileSync(OUT, JSON.stringify(doc)); }
    doneCount++; failStreak = 0;
    console.log(`✓ [${doneCount}/${todo.length}] ${label} → 新板 ${got}（热区 ${zn}）${fresh.length === 0 ? '（板均已收）' : ''}`);
  } catch (e) {
    doneCount++; failStreak++;
    console.log(`✗ [${doneCount}/${todo.length}] ${label}: ${e.message}`);
    // 崩溃类错误（离开查看器/连错 5 页）立即熔断退出——断点在 hotzones.json，重启实例接着跑
    if (/离开墨刀查看器/.test(e.message)) { console.log('!! tab 已崩溃，熔断退出（重启实例后增量续跑）'); break; }
    if (failStreak >= 5) { console.log('!! 连续 5 页失败，熔断退出（疑似实例异常）'); break; }
  }
}
// 全收完补写一次（防 zero-hit 页没落盘）
fs.writeFileSync(OUT, JSON.stringify(doc));
const typeCount = {};
for (const zs of Object.values(zones)) for (const z of zs) for (const i of z.inters) typeCount[i.t] = (typeCount[i.t] || 0) + 1;
console.log(JSON.stringify({ pages: doneCount, boardsWithZones: Object.keys(zones).length, zones: zoneTotal, typeCount }, null, 0));
c.close();
