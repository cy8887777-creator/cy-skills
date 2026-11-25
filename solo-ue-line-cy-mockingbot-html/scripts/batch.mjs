// batch.mjs —— 批量编排：逐页面点击挂载 → diff 出画板 → 提取 JSON → 生成 HTML（断点续跑）
// 用法：node batch.mjs <port> <manifest.json> <data-map.json> <输出根目录> [--only cid,cid,…] [--limit N] [--skip-gen]
// 产物结构（镜像墨刀侧边栏目录）：
//   <根>/<folder链>/<页面名>.html          —— 单画布页面
//   <根>/<folder链>/<页面名>/<子画布名>.html —— 多画布页面（用户拍板：同级文件夹多个 html，文件名=子画布名）
//   <根>/assets/                            —— 全部切图共享（gen-html 冲突自动加序号）
//   <根>/boards/<cid>.json                  —— 每板提取 JSON（debug/重生成用）
//   <根>/state.json                         —— 断点：已完成 page cid → 产物清单
//
// 挂载模型（probe 实测）：
//   - 画板挂载后累积不卸载 → 归属 = 首次挂载该板的页面
//   - 画板名走 data-map（DOM 无名称）；页面名走 manifest
import fs from 'node:fs';
import path from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { connect, sleep, detectModel } from './cdp.mjs';
import { WAIT_BOARD, extractBoardPcanvas } from './pcanvas-extract.mjs';

const SCRIPTS = path.dirname(fileURLToPath(import.meta.url));
const argv = process.argv.slice(2);
const [PORT, MANIFEST, DATAMAP, OUTROOT] = argv;
const only = argv.includes('--only') ? argv[argv.indexOf('--only') + 1].split(',').map(s => s.trim()) : null;
const limit = argv.includes('--limit') ? +argv[argv.indexOf('--limit') + 1] : Infinity;
const skipGen = argv.includes('--skip-gen');
const minW = argv.includes('--min-w') ? +argv[argv.indexOf('--min-w') + 1] : 150;   // 主画板最小宽（probe 实测：符号画布 ≤110，主画板 ≥375）
if (!PORT || !MANIFEST || !DATAMAP || !OUTROOT) {
  console.error('用法: node batch.mjs <port> <manifest.json> <data-map.json> <输出根> [--only cid,…] [--limit N] [--skip-gen] [--retry-failed]');
  process.exit(1);
}
fs.mkdirSync(path.join(OUTROOT, 'boards'), { recursive: true });
fs.mkdirSync(path.join(OUTROOT, 'assets'), { recursive: true });

const manifest = JSON.parse(fs.readFileSync(MANIFEST, 'utf8'));
const names = JSON.parse(fs.readFileSync(DATAMAP, 'utf8')).names;
const stateFile = path.join(OUTROOT, 'state.json');
const state = fs.existsSync(stateFile) ? JSON.parse(fs.readFileSync(stateFile, 'utf8')) : { done: {} };

const c = await connect(PORT);
const { evalJS } = c;
// 连上后校验确实在墨刀查看器页：connect 的 urlRe 匹配不到会 fallback 到第一个 tab——连错页面整批跑废
{
  const href = String(await evalJS('location.href'));
  if (!/index\.html/.test(href)) {
    console.error(`✗ 当前 tab 不在墨刀查看器（${href}）——先 node stop-chrome.mjs 收掉旧实例再 start-chrome`);
    process.exit(1);
  }
}
// 查看器代际探测（2026-10-20 双格式实锤）：legacy=gzip 快照+rResCanvas；pcanvas=PB=v1 明文 JSON+三区画布
const MODEL = await detectModel(evalJS);
if (MODEL === 'unknown') {
  console.error('✗ 无法识别墨刀查看器模型（既无 .tree-node.rResCanvas 也无 .pcanvas）——包未加载完或格式再变，先 diagnose 排查');
  process.exit(1);
}
const boardMode = argv.includes('--board-mode') ? argv[argv.indexOf('--board-mode') + 1] : 'long';   // long=长图(默认) viewport=画板视口
console.log(`查看器模型: ${MODEL}${MODEL === 'pcanvas' ? `（板高口径 ${boardMode}）` : ''}`);

// ---------- DOM 工具 ----------
const SNAP = `(() => [...document.querySelectorAll('.tree-node.rResCanvas')]
  .map(el => ({ cid: el.getAttribute('data-cid'), w: el.offsetWidth, h: el.offsetHeight })))()`;
const snap = () => evalJS(SNAP);
const CLICK = (cid) => `(() => {
  const item = document.querySelector('.rn-list-item[data-cid="${cid}"]');
  if (!item) return 'NOT_FOUND';
  item.scrollIntoView({ block: 'center' });
  const r = item.getBoundingClientRect();
  if (r.width < 2) return 'ZERO_RECT';
  // 必须带坐标：墨刀 mousedown 处理做命中检测，无坐标点击部分页面不切（probe 实测）
  const o = { bubbles: true, cancelable: true, view: window, clientX: r.x + r.width / 2, clientY: r.y + r.height / 2 };
  item.dispatchEvent(new MouseEvent('mousedown', o));
  item.dispatchEvent(new MouseEvent('mouseup', o));
  item.dispatchEvent(new MouseEvent('click', o));
  return (item.className || '').includes('active') ? 'ACTIVE' : 'NO_ACTIVE';
})()`;
// 页面画布判定：真画布 cid 一律 rc 纯段（probe 实测）；含 / 或拼接段（_rc/_cV/wb 前缀复合）= 跨页复用的组件源（列表条目/弹窗类），不是页面画布
const isPageBoard = (b) => /^rc[A-Za-z0-9]+$/.test(b.cid || '') && b.w >= minW && b.h >= minW;

// ---------- 提取（与 extract-board.mjs 同源逻辑，单连接复用） ----------
async function extractBoard(cid, outJson) {
  const ROLL = `(() => {
    const b = [...document.querySelectorAll('.tree-node.rResCanvas')]
      .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(cid)})[0];
    if (!b) return -1;
    b.scrollIntoView({ block: 'center', inline: 'center' });
    const pend = b.querySelectorAll('.image-container.is-default-image');
    pend.forEach((el, i) => setTimeout(() => el.scrollIntoView({ block: 'center', inline: 'center' }), i * 60));
    return pend.length;
  })()`;
  let n = await evalJS(ROLL);
  if (n === -1) return { err: 'board gone' };
  for (let i = 0; i < 20 && n > 0; i++) {
    await sleep(1500);
    n = await evalJS(`(() => {
      const b = [...document.querySelectorAll('.tree-node.rResCanvas')]
        .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(cid)})[0];
      return b ? b.querySelectorAll('.image-container.is-default-image').length : 999;
    })()`);
  }
  await evalJS(ROLL);
  await sleep(3000);
  const PICK = `(() => {
    const vp = [...document.querySelectorAll('.tree-node.rResCanvas')]
      .filter(el => (el.getAttribute('data-cid')||'') === ${JSON.stringify(cid)})[0];
    if (!vp) return { err: 'board gone' };
    const brr = vp.getBoundingClientRect();
    const sx = vp.offsetWidth / (brr.width || 1), sy = vp.offsetHeight / (brr.height || 1);
    // 退化判定看布局真值 offsetWidth：brr 只是渲染 rect。画布挂在 0 宽容器（如 group-list 分组缩略）时被 transform
    // 等比缩到几十 px 渲染——布局层未动（offsetWidth 仍是设计尺寸），折行/textH/坐标在布局系全正确，rect×sx 换算数学有效（2026-09-16 送礼效果 4 页实锤）。
    // 仅 offsetWidth 也退化（窗口太小 fit 重排）才是真 scale degenerate。
    if (vp.offsetWidth < 80 && brr.width < 80) return { error: 'scale degenerate screenW=' + brr.width.toFixed(1) };
    const baseUrl = location.href.replace(/index\\.html.*$/, '');
    const nodes = [];
    function walk(el, parentIdx, depth) {
      const r = el.getBoundingClientRect();
      const cs = getComputedStyle(el);
      if (cs.display === 'none' || cs.visibility === 'hidden' || +(cs.opacity) <= 0.01) return;
      const dx = (r.x - brr.x) * sx, dy = (r.y - brr.y) * sy, dw = r.width * sx, dh = r.height * sy;
      const idx = nodes.length;
      const rec = { idx, parent: parentIdx, depth, tag: el.tagName.toLowerCase(),
        x: +dx.toFixed(1), y: +dy.toFixed(1), w: +dw.toFixed(1), h: +dh.toFixed(1),
        cls: (el.className || '').toString().slice(0, 80) };
      const nm = el.getAttribute('data-name') || '';
      if (nm) rec.name = nm.slice(0, 80);
      const own = (() => {
        // 直接文字子节点；<br> 记为显式换行（textContent 丢 <br> 信息，产物需 pre-line 才能还原多行）
        // 注意：本段在反引号模板里，发往浏览器的反斜杠必须双写（\\s、\\n）——单写会被模板解析吃掉
        let s = '';
        for (const x of el.childNodes) {
          if (x.nodeType === 3 && x.textContent.trim()) s += x.textContent.trim() + ' ';
          else if (x.nodeType === 1 && x.tagName === 'BR') s = s.replace(/\\s+$/, '') + '\\n';
        }
        return s.trim();
      })();
      if (own) rec.text = own;
      const st = {};
      // 换行真值①：设计者显式 white-space（normal 是默认值不记）
      if (cs.whiteSpace && cs.whiteSpace !== 'normal') st.ws = cs.whiteSpace;
      // 换行真值②：文字实际渲染高度（Range 测内容 bbox，不含框 padding——墨刀框常比内容大）
      //   仅纯文字叶子可测：有子元素时 range 会混入子元素高度。墨刀里单行渲染 → 产物 nowrap（用户口径：空间够不换行）
      if (own && el.children.length === 0) {
        try {
          const rg = document.createRange(); rg.selectNodeContents(el);
          const rb = rg.getBoundingClientRect();
          if (rb.height > 0) st.textH = +(rb.height * sy).toFixed(1);
        } catch (e) {}
      }
      if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') st.bg = cs.backgroundColor;
      if (cs.backgroundImage && cs.backgroundImage !== 'none') {
        // data:（内嵌 svg 图标）放宽截断——gen-html 会原样内联，500 字符会剪坏 URI；外部引用照旧防 state 爆
        // 模板字符串内反斜杠双写：\\( 才能把字面括号发给浏览器
        st.bgi = /^url\\(["']?data:/i.test(cs.backgroundImage) ? cs.backgroundImage.slice(0, 30000) : cs.backgroundImage.slice(0, 500);
      }
      if (cs.borderRadius && cs.borderRadius !== '0px') st.br = cs.borderRadius;
      if (cs.borderWidth && cs.borderWidth !== '0px') { st.bw = cs.borderWidth; st.bc = cs.borderColor; st.bs = cs.borderStyle; }
      if (cs.opacity && cs.opacity !== '1') st.op = cs.opacity;
      if (cs.color) st.clr = cs.color;
      if (cs.zIndex && cs.zIndex !== 'auto') st.zi = cs.zIndex;
      if (cs.overflow && cs.overflow !== 'visible') st.ovf = cs.overflow;
      if (cs.boxShadow && cs.boxShadow !== 'none') st.bsh = cs.boxShadow;
      if (cs.filter && cs.filter !== 'none') st.flt = cs.filter;
      if (cs.clipPath && cs.clipPath !== 'none') st.cp = cs.clipPath;
      if (cs.mask && cs.mask !== 'none' && cs.mask !== '') st.mk = cs.mask;
      if (rec.text) { st.fs = cs.fontSize; st.fw = cs.fontWeight; st.ta = cs.textAlign; st.lh = cs.lineHeight; st.ff = cs.fontFamily; }
      if (Object.keys(st).length) rec.st = st;
      if (rec.tag === 'svg') { rec.svg = el.outerHTML; nodes.push(rec); return; }
      if (rec.tag === 'img') rec.img = el.getAttribute('src') || '';
      nodes.push(rec);
      for (const ch of el.children) walk(ch, idx, depth + 1);
    }
    walk(vp, null, 0);
    return { board: { w: vp.offsetWidth, h: vp.offsetHeight },
      pkgBase: baseUrl, nodes };
  })()`;
  const data = await evalJS(PICK);
  if (!data || data.err || data.error) return { err: JSON.stringify(data) };
  const doc = { meta: { tool: 'batch.mjs', generatedAt: new Date().toISOString() },
    page: { cid, name: names[cid] || cid, board: data.board, pkgBase: data.pkgBase, nodes: data.nodes } };
  fs.writeFileSync(outJson, JSON.stringify(doc));
  return { ok: true, nodes: data.nodes.length, board: data.board };
}

// ---------- 文件名净化 ----------
const ILLEGAL = /[<>:"/\\|?*\x00-\x1f]/g;
const RESERVED = /^(con|prn|aux|nul|com[1-9]|lpt[1-9])(\.|$)/i;
const sanitize = (s, fallback) => {
  let t = String(s || '').replace(ILLEGAL, '_').replace(/\s+/g, ' ').trim().replace(/[. ]+$/, '');
  if (RESERVED.test(t)) t = '_' + t;
  return t.slice(0, 60) || fallback;
};

// ---------- gen-html 子进程 ----------
const genHtml = (json, out, assetsRel) => new Promise((resolve) => {
  const p = spawn(process.execPath, [path.join(SCRIPTS, 'gen-html.cjs'), json, out,
    '--assets', path.join(OUTROOT, 'assets'), '--assets-rel', assetsRel], { stdio: 'pipe' });
  let buf = '';
  p.stdout.on('data', d => buf += d); p.stderr.on('data', d => buf += d);
  p.on('close', (code) => resolve({ code, buf: buf.trim() }));
});

// ---------- 主循环 ----------
const uniqByCid = (arr) => {   // 同 cid 板可能重复挂载（不同 scale 双份，实测 750/905）——取面积最大（真实设计尺寸），不赌首块
  const best = new Map();
  for (const b of arr) {
    const cur = best.get(b.cid);
    if (!cur || b.w * b.h > cur.w * cur.h) best.set(b.cid, b);
  }
  return [...best.values()];
};
const pages = manifest.items.filter(it => it.type === 'page');
// --retry-failed：把带 error / failedBoards 的已 done 页面重置重跑（板 json 有缓存的走缓存，快）
if (argv.includes('--retry-failed')) {
  const fl = Object.entries(state.done).filter(([, d]) => d.error || (d.failedBoards || []).length).map(([pc]) => pc);
  for (const pc of fl) delete state.done[pc];
  if (fl.length) console.log(`--retry-failed：重置 ${fl.length} 个失败页面`);
}
let todo = pages.filter(p => !state.done[p.cid]);
if (only) todo = todo.filter(p => only.includes(p.cid));
todo = todo.slice(0, limit);
console.log(`待处理页面: ${todo.length} / ${pages.length}（已完成 ${Object.keys(state.done).length}）`);

// ================= 新查看器主循环（pcanvas 模型，2026-10-20） =================
// 页面↔画布 1:1（cid 即页面 cid）：点击即挂载+激活自己的 pcanvas，无需旧版 diff 归属/认领/同板复用兜底
if (MODEL === 'pcanvas') {
  let doneCount = 0, failCount = 0;
  for (const page of todo) {
    const label = page.dir.concat(page.name).join('/');
    try {
      let st = await evalJS(CLICK(page.cid));
      if (st !== 'ACTIVE') { await sleep(1500); st = await evalJS(CLICK(page.cid)); }
      if (st === 'NOT_FOUND') throw new Error('条目不在 DOM（树未展开？）');
      if (st !== 'ACTIVE') throw new Error('点击未选中（' + st + '）');
      // 等画布就绪（挂载 + active + 布局真值达标）
      let ready = '';
      for (let i = 0; i < 10; i++) {
        await sleep(1200);
        ready = String(await evalJS(WAIT_BOARD(page.cid, minW)));
        if (ready.startsWith('READY')) break;
      }
      if (!ready.startsWith('READY')) {
        // 真空页面（墨刀里没画布）：记空不算失败
        state.done[page.cid] = { name: page.name, dir: page.dir, boards: [], empty: true, at: new Date().toISOString() };
        fs.writeFileSync(stateFile, JSON.stringify(state));
        doneCount++;
        console.log(`○ [${doneCount}/${todo.length}] ${label} → 空页面（${ready}）`);
        continue;
      }
      const cid = page.cid;
      const bname = names[cid] || cid;
      const json = path.join(OUTROOT, 'boards', cid.replace(/[\/]/g, '_') + '.json');
      let boardInfo;
      if (fs.existsSync(json)) {
        try {
          const old = JSON.parse(fs.readFileSync(json, 'utf8'));
          if (old.page && Array.isArray(old.page.nodes)) {
            boardInfo = { cid, name: bname, board: old.page.board, nodes: old.page.nodes.length, json };
            console.log(`  （缓存复用 ${bname}）`);
          }
        } catch {}
      }
      if (!boardInfo) {
        const r = await extractBoardPcanvas({ port: PORT, cid, outJson: json, name: bname, boardMode, tool: 'batch.mjs (pcanvas model)' });
        if (!r || !r.ok) throw new Error(`提取失败 ${bname}: ${r && r.err}`);
        boardInfo = { cid, name: bname, board: r.board, nodes: r.nodes, json };
      }
      const pageDir = path.join(OUTROOT, ...page.dir.map(s => sanitize(s, '目录')));
      const html = path.join(pageDir, sanitize(page.name, 'page') + '.html');
      const rel = path.relative(path.dirname(html), path.join(OUTROOT, 'assets')).replace(/\\/g, '/');
      if (!skipGen) { const g = await genHtml(boardInfo.json, html, rel); if (g.code !== 0) console.log(`  ✗ gen: ${g.buf}`); }
      state.done[page.cid] = { name: page.name, dir: page.dir, boards: [{ ...boardInfo, html: path.relative(OUTROOT, html) }], at: new Date().toISOString() };
      fs.writeFileSync(stateFile, JSON.stringify(state));
      doneCount++;
      console.log(`✓ [${doneCount}/${todo.length}] ${label} → ${boardInfo.board.w}x${boardInfo.board.h}, ${boardInfo.nodes} 节点`);
    } catch (e) {
      failCount++;
      state.done[page.cid] = { name: page.name, dir: page.dir, boards: [], error: String(e.message || e), at: new Date().toISOString() };
      fs.writeFileSync(stateFile, JSON.stringify(state));
      console.log(`✗ [${doneCount + failCount}/${todo.length}] ${label}: ${e.message}`);
    }
  }
  console.log(JSON.stringify({ done: doneCount, failed: failCount, remaining: pages.filter(p => !state.done[p.cid]).length, model: MODEL }));
  process.exit(0);
}

const mountedBase = new Set((await snap()).map(b => b.cid));   // 归属基线：开跑前已挂的板不属于任何后续页面
// —— 基线归属预备（2026-10-23 飞燕混合包实锤：全新启动基线可含 2 块页面板——pcanvas 内默认页板 + 换装槽预载板）——
// 兜底「认领基线板」放任认领会把两块全判给首个无新增页 → 串页（启动页抢走密码登录板、密码登录反被记空页面）。
// 处置：① URL screen/canvasId 能归位的板只许默认页认领；② 开跑先 flush 点击首个待处理页，diff 到的新板保留给该页；
// ③ 兜底1 只认领 reserved 归属到本页的基线板（reserved 无归属的基线板永不认领——宁缺毋滥，audit 兜底）。
const reserved = new Map();   // 基线板cid → 页面cid
{
  let u = {};
  try { u = JSON.parse(await evalJS(`JSON.stringify((()=>{const s=new URLSearchParams(location.search);return {screen:s.get('screen'),canvasId:s.get('canvasId')};})())`)) || {}; } catch {}
  if (u && u.screen && u.canvasId && /^rc[A-Za-z0-9]+$/.test(u.canvasId)) reserved.set(u.canvasId, u.screen);
}
if (todo.length) {
  const before = new Set((await snap()).map(b => b.cid));
  let st = await evalJS(CLICK(todo[0].cid));
  if (st !== 'ACTIVE') { await sleep(1500); st = await evalJS(CLICK(todo[0].cid)); }
  if (st === 'ACTIVE') {
    let flushed = null;
    for (let i = 0; i < 10 && !flushed; i++) {
      await sleep(1200);
      const now = uniqByCid((await snap()).filter(b => !before.has(b.cid) && !mountedBase.has(b.cid) && isPageBoard(b)));
      if (now.length === 1) flushed = now[0].cid;
      else if (now.length > 1) break;   // 多板新增歧义，交给主循环 diff 处理
    }
    if (flushed) reserved.set(flushed, todo[0].cid);
    else {
      // flush 无新增：首个待处理页的板可能开跑前已挂在槽位——把唯一未归属的基线板保留给该页
      const cur = new Set((await snap()).map(b => b.cid));
      const unres = uniqByCid((await snap()).filter(b => mountedBase.has(b.cid) && cur.has(b.cid) && isPageBoard(b) && !reserved.has(b.cid)));
      if (unres.length === 1) reserved.set(unres[0].cid, todo[0].cid);
    }
  }
}
const claimed = new Set();   // 已被某页面认领的基线板
let doneCount = 0, failCount = 0;
for (const page of todo) {
  const label = page.dir.concat(page.name).join('/');
  try {
    const before = new Set((await snap()).map(b => b.cid));
    // 点击（带坐标）→ 校验选中态 → 未选中重试一次
    let st = await evalJS(CLICK(page.cid));
    if (st !== 'ACTIVE') {
      await sleep(1500);
      st = await evalJS(CLICK(page.cid));
    }
    if (st === 'NOT_FOUND') throw new Error('条目不在 DOM（树未展开？）');
    if (st !== 'ACTIVE') throw new Error('点击未选中（' + st + '）');
    // 等挂载稳定：新增不再变化（isPageBoard 过滤组件源/符号画布，见函数注释）
    let newBoards = [], stable = 0;
    for (let i = 0; i < 12 && stable < 2; i++) {
      await sleep(1200);
      const now = uniqByCid((await snap()).filter(b => !before.has(b.cid) && !mountedBase.has(b.cid) && isPageBoard(b)));
      if (now.length === newBoards.length && now.every(b => newBoards.some(x => x.cid === b.cid))) stable++;
      else { stable = 0; newBoards = now; }
    }
    if (!newBoards.length) {
      // 兜底1：认领基线板——初始默认页的板开跑前已挂载且永不卸载。
      //   混合包实锤（2026-10-23）：基线可含多块页面板，放任认领会串页 → 只认领 reserved 归属到本页的板；
      //   排除「已在已完成页面产物里出现过的 cid」：跨进程续跑时上批遗留板会被错认（实测发生过）
      const produced = new Set(Object.values(state.done).flatMap(d => (d.boards || []).map(b => b.cid)));
      const orphans = uniqByCid((await snap()).filter(b => mountedBase.has(b.cid) && isPageBoard(b) && !claimed.has(b.cid) && !produced.has(b.cid) && reserved.get(b.cid) === page.cid));
      if (orphans.length) {
        newBoards = orphans;
        console.log(`  （认领初始残留板 ${orphans.length} 块）`);
      } else {
        // 兜底2：同板复用——页面与前一页共用画布（弹窗/状态标注页），点击后无新增但画布区仍挂着页面板
        const reuse = uniqByCid((await snap()).filter(b => !mountedBase.has(b.cid) && isPageBoard(b)));
        if (reuse.length) {
          newBoards = reuse;
          console.log(`  （同板复用 ${reuse.length} 块——与前页共用画布）`);
        } else {
          // 真空页面（probe9 实测：选中生效、卸前页板、不挂新板——墨刀里就没画布）：不算失败，记空产物
          state.done[page.cid] = { name: page.name, dir: page.dir, boards: [], empty: true, at: new Date().toISOString() };
          fs.writeFileSync(stateFile, JSON.stringify(state));
          doneCount++;
          console.log(`○ [${doneCount}/${todo.length}] ${label} → 空页面（墨刀无画布）`);
          continue;
        }
      }
    }
    for (const b of newBoards) claimed.add(b.cid);
    const boards = []; const failedBoards = [];
    for (const { cid } of newBoards) {
      const bname = names[cid] || cid;
      const json = path.join(OUTROOT, 'boards', cid.replace(/[\/]/g, '_') + '.json');
      // 同板缓存：此 cid 已提取过（他页同板复用/断点续跑）→ 直接复用 boards/<cid>.json，跳过 DOM 提取（全量省时大头）
      if (fs.existsSync(json)) {
        try {
          const old = JSON.parse(fs.readFileSync(json, 'utf8'));
          if (old.page && Array.isArray(old.page.nodes)) {
            boards.push({ cid, name: bname, board: old.page.board, nodes: old.page.nodes.length, json });
            console.log(`  （缓存复用 ${bname}）`);
            continue;
          }
        } catch {}
      }
      const r = await extractBoard(cid, json);
      if (!r || !r.ok) { failedBoards.push({ cid, name: bname, err: r && r.err }); console.log(`  ✗ 提取失败 ${bname}: ${r && r.err}`); continue; }
      boards.push({ cid, name: bname, board: r.board, nodes: r.nodes, json });
    }
    // 生成 HTML（单板：页面名.html；多板：页面名/子画布名.html）
    const pageDir = path.join(OUTROOT, ...page.dir.map(s => sanitize(s, '目录')));
    const results = [];
    if (boards.length === 1) {
      const html = path.join(pageDir, sanitize(page.name, 'page') + '.html');
      const rel = path.relative(path.dirname(html), path.join(OUTROOT, 'assets')).replace(/\\/g, '/');
      if (!skipGen) { const g = await genHtml(boards[0].json, html, rel); if (g.code !== 0) console.log(`  ✗ gen: ${g.buf}`); }
      results.push({ ...boards[0], html: path.relative(OUTROOT, html) });
    } else {
      const sub = path.join(pageDir, sanitize(page.name, 'page'));
      const used = new Set();
      for (const b of boards) {
        let fn = sanitize(b.name, 'board');
        while (used.has(fn.toLowerCase())) fn = sanitize(b.name, 'board') + '_' + b.cid.slice(-4);   // 从基名重算，防多次碰撞尾缀叠加
        used.add(fn.toLowerCase());
        const html = path.join(sub, fn + '.html');
        const rel = path.relative(path.dirname(html), path.join(OUTROOT, 'assets')).replace(/\\/g, '/');
        if (!skipGen) { const g = await genHtml(b.json, html, rel); if (g.code !== 0) console.log(`  ✗ gen: ${g.buf}`); }
        results.push({ ...b, html: path.relative(OUTROOT, html) });
      }
    }
    state.done[page.cid] = { name: page.name, dir: page.dir, boards: results, at: new Date().toISOString() };
    if (failedBoards.length) state.done[page.cid].failedBoards = failedBoards;   // 板级失败留痕，--retry-failed 据此重跑
    fs.writeFileSync(stateFile, JSON.stringify(state));
    doneCount++;
    console.log(`✓ [${doneCount}/${todo.length}] ${label} → ${results.length} 板${failedBoards.length ? `（✗ ${failedBoards.length} 板失败，--retry-failed 可重跑）` : ''} (${results.map(b => names[b.cid] || b.cid.slice(0,8)).join(', ')})`);
  } catch (e) {
    failCount++;
    state.done[page.cid] = { name: page.name, dir: page.dir, boards: [], error: String(e.message || e), at: new Date().toISOString() };
    fs.writeFileSync(stateFile, JSON.stringify(state));
    console.log(`✗ [${doneCount + failCount}/${todo.length}] ${label}: ${e.message}`);
  }
}
console.log(JSON.stringify({ done: doneCount, failed: failCount, remaining: pages.filter(p => !state.done[p.cid]).length }));
c.close();
