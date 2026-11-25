// pcanvas-extract.mjs —— 新版墨刀查看器（PB=v1 明文 JSON 导出，pcanvas 三区模型）的共享提取模块
// 2026-10-20 实锤固化（蓝骑同城-师傅端App s1 包，6 页样板回归通过）：
//   - 挂载模型：.pcanvas[data-cid=页面cid] 累积挂载、激活者带 .active（display:none 时 offsetWidth=0）
//   - 页面↔画布 1:1（cid 即页面 cid），无需旧版的 diff 归属/认领/同板复用兜底
//   - 画布分三区：screen-header（状态栏+导航栏）/ screen-content(.widgets 滚动内容) / screen-footer(固定底栏)
//     ——提取根必须含三区（旧版只提 .widgets 会丢顶栏底栏）
//   - path-icon 色值 = hash 定向硬编码规则（如 .kKhnky.fill g [fill]{fill:rgb(234,88,12)}），
//     提取时现场扫 stylesheet 建 hash→色字典，无规则才落回继承色（比旧版静态 icon-colors.json 更稳，跨包通用）
//   - tab 选中下划线等是 ::after 伪元素 → 对可见伪元素物化成真实节点
//   - 固定层（footer）与内容层常有同物孪生（tab 栏/底部主按钮）→ 子树文本串相等判孪生，footer 副本让位
//   - 板高口径 boardMode：'long'=内容全展开+footer 钉底（默认，评审友好）；'viewport'=画板原始视口（墨刀忠实）
//   - transform 坐标已含在 rect 里，仅回收 st.tf 供 gen-html 透传「不改 AABB 的方向性翻转」（180°/镜像）
//   - 绘制序采样（2026-10-20 第二批实锤）：查看器真实绘制序 ≠ DOM 序（实测订单条 zi=10 压住地图 zi=13，
//     CSS 规则推不出真实层序），平铺模型 z=idx 会把晚 DOM 的地图盖到条上——PICK 给节点打 data-mth 标，
//     SAMPLE 网格采样 elementsFromPoint 收集真实堆叠链，postPass 按约束拓扑重排。以查看器实测为准，零规则猜测。
//     已知边界：只采样首屏可视区（812，内部滚动区 fold 外不采，兜底原序）；pointer-events:none 元素
//     靠采样期临时强制可命中的样式纳入；采样漏掉的小元素拓扑排序按原序兜底（不比平铺差）
import { connect, sleep } from './cdp.mjs';

export { detectModel } from './cdp.mjs';

// 等画布就绪：挂载 + active + 布局真值达标（display:none 时 offsetWidth=0）
export const WAIT_BOARD = (cid, minW = 150) => `(() => {
  const p = document.querySelector('.pcanvas[data-cid="${cid}"]');
  if (!p) return 'MOUNTING';
  if (!(p.className || '').toString().includes('active')) return 'NOT_ACTIVE';
  if (p.offsetWidth < ${minW}) return 'TOO_SMALL:' + p.offsetWidth;
  return 'READY:' + p.offsetWidth + 'x' + p.offsetHeight;
})()`;

// 懒加载图预滚（与旧版同思路，根换成 pcanvas）
export const ROLL = (cid) => `(() => {
  const p = document.querySelector('.pcanvas[data-cid="${cid}"]');
  if (!p) return -1;
  p.scrollIntoView({ block: 'center', inline: 'center' });
  const pend = p.querySelectorAll('.image-container.is-default-image');
  pend.forEach((el, i) => setTimeout(() => el.scrollIntoView({ block: 'center', inline: 'center' }), i * 60));
  return pend.length;
})()`;

// 绘制序采样：网格布点 elementsFromPoint，收集 data-mth 真实堆叠链（首层在上）
// 步长自适应（封顶 ~1200 点）；采样期对全部标记元素逐个内联 pointer-events:auto!important 强制可命中
// （⚠ 不能用样式表规则——实测墨刀自己的样式表会以更高优先级压回来，地图 img 依旧隐身、采样链缺失；
//   内联 important 优先级最高必生效），采完逐个恢复原值
export const SAMPLE = (cid) => `(() => {
  const p = document.querySelector('.pcanvas[data-cid="${cid}"]');
  if (!p) return [];
  const pr = p.getBoundingClientRect();
  const forced = [];
  for (const el of p.querySelectorAll('[data-mth]')) {
    forced.push([el, el.style.getPropertyValue('pointer-events'), el.style.getPropertyPriority('pointer-events')]);
    el.style.setProperty('pointer-events', 'auto', 'important');
  }
  const W = p.offsetWidth, H = Math.min(p.offsetHeight, 812);
  const step = Math.max(20, Math.ceil(Math.sqrt(W * H / 1200)));
  const stacks = [];
  for (let y = 8; y < H; y += step) {
    for (let x = 8; x < W; x += step) {
      const dq = [];
      for (const el of document.elementsFromPoint(pr.x + x, pr.y + y)) {
        const v = el.getAttribute ? el.getAttribute('data-mth') : null;
        if (v == null) continue;
        const n = Number(v);
        if (dq[dq.length - 1] !== n) dq.push(n);
      }
      if (dq.length >= 2) stacks.push(dq);
    }
  }
  for (const [el, pv, pp] of forced) { pv ? el.style.setProperty('pointer-events', pv, pp) : el.style.removeProperty('pointer-events'); }
  return stacks;
})()`;

// 提取主探针：三区全收 + hash 色字典 + 伪元素物化 + 全节点记色 + tf 采集 + 空 src img 跳过
export const PICK = (cid) => `(() => {
  const p = document.querySelector('.pcanvas[data-cid="${cid}"]');
  if (!p) return { err: 'board gone' };
  if (!(p.className || '').toString().includes('active')) return { err: 'not active' };
  const brr = p.getBoundingClientRect();
  const sx = p.offsetWidth / (brr.width || 1), sy = p.offsetHeight / (brr.height || 1);
  if (p.offsetWidth < 80 && brr.width < 80) return { error: 'scale degenerate screenW=' + brr.width.toFixed(1) };
  const baseUrl = location.href.replace(/index\\.html.*$/, '');
  // hash→色 现场字典（path-icon 的 solidColor 走 hash 定向硬编码规则；声明 currentcolor 的规则过滤掉、落回继承）
  if (!window.__mthIconMap) {
    const map = {};
    for (const sheet of document.styleSheets) {
      let list; try { list = sheet.cssRules; } catch (e) { continue; }
      for (const r of list || []) {
        if (!r.selectorText || !r.style) continue;
        if (!/svg-icon-path-icon|\\.fill\\b/.test(r.selectorText)) continue;
        const pick = (v) => (v && !/currentcolor|none|transparent/i.test(v)) ? v.trim() : null;
        const col = pick(r.style.getPropertyValue('fill')) || pick(r.style.getPropertyValue('stroke'));
        if (!col) continue;
        const ms = r.selectorText.match(/\\.([A-Za-z0-9]{6})(?![\\w-])/g) || [];
        for (const m of ms) { const h = m.slice(1); if (!map[h]) map[h] = col; }
      }
    }
    window.__mthIconMap = map;
  }
  const nodes = [];
  const zoneOf = (el) => {
    for (let e = el; e && e !== p; e = e.parentElement) {
      const cl = (e.className || '').toString();
      if (/\\bscreen-header\\b/.test(cl)) return 'header';
      if (/\\bscreen-footer\\b/.test(cl)) return 'footer';
    }
    return 'content';
  };
  // 伪元素物化：可见（有 bg/border/阴影/文本）才产节点；图标字体字形（\\f167 类）无法还原，跳过
  function pseudoRec(el, pseudoType, parentIdx, zone) {
    const cs = getComputedStyle(el, pseudoType);
    if (!cs || cs.display === 'none') return null;
    const content = cs.content;
    if (!content || content === 'none' || content === 'normal') return null;
    const probe = document.createElement('div');
    for (const k of ['position','left','right','top','bottom','width','height','margin','transform','backgroundColor','borderRadius','borderTopWidth','borderTopStyle','borderTopColor','borderBottomWidth','borderBottomStyle','borderBottomColor','borderLeftWidth','borderLeftStyle','borderLeftColor','borderRightWidth','borderRightStyle','borderRightColor','boxShadow','opacity','color','fontSize','fontWeight','textAlign','lineHeight','fontFamily']) { try { probe.style[k] = cs[k]; } catch (e) {} }
    let txt = '';
    if (content.startsWith('"') && content.endsWith('"') && content.length > 2) {
      txt = content.slice(1, -1);
      if (/\\\\/.test(txt)) return null;
      probe.textContent = txt;
    }
    el.appendChild(probe);
    const r = probe.getBoundingClientRect();
    el.removeChild(probe);
    const hasBg = cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)';
    const hasBorder = parseFloat(cs.borderTopWidth) > 0 || parseFloat(cs.borderBottomWidth) > 0 || parseFloat(cs.borderLeftWidth) > 0 || parseFloat(cs.borderRightWidth) > 0;
    const hasShadow = cs.boxShadow && cs.boxShadow !== 'none';
    if (!hasBg && !hasBorder && !hasShadow && !txt.trim()) return null;
    if (r.width < 1 || r.height < 1) return null;
    const rec = { idx: nodes.length, parent: parentIdx, depth: 0, tag: 'div', zone,
      x: +((r.x - brr.x) * sx).toFixed(1), y: +((r.y - brr.y) * sy).toFixed(1),
      w: +(r.width * sx).toFixed(1), h: +(r.height * sy).toFixed(1), cls: 'pseudo::' + pseudoType };
    const st = {};
    if (hasBg) st.bg = cs.backgroundColor;
    if (parseFloat(cs.borderBottomWidth) > 0) { st.bw = cs.borderBottomWidth; st.bc = cs.borderBottomColor; st.bs = cs.borderBottomStyle; }
    else if (parseFloat(cs.borderTopWidth) > 0) { st.bw = cs.borderTopWidth; st.bc = cs.borderTopColor; st.bs = cs.borderTopStyle; }
    if (cs.borderRadius && cs.borderRadius !== '0px') st.br = cs.borderRadius;
    if (cs.boxShadow && cs.boxShadow !== 'none') st.bsh = cs.boxShadow;
    st.clr = cs.color;
    if (txt.trim()) { rec.text = txt; st.fs = cs.fontSize; st.fw = cs.fontWeight; st.ta = cs.textAlign; st.lh = cs.lineHeight; st.ff = cs.fontFamily; }
    rec.st = st;
    nodes.push(rec);
    return rec;
  }
  // img/bgi 专属：沿祖先链取全部「非结构性 ovf:hidden/clip」祖先盒的交集 = 该图的真实可视区。
  // 实测（2026-10-20）：地图 img 盒 647，真实裁剪源是 StyledImageWrapper（relative+hidden，315）——
  // 查看器因此只画地图顶段；不裁会全高盖住订单条。结构性容器（screen-*/scontainer/widgets/pcanvas）
  // 的 overflow 属查看器滚动机制（fold 外内容靠它展示），不计入，否则长页被视口截断
  function ancestorClipBox(el) {
    let clip = null;
    for (let a = el.parentElement; a && a !== p.parentElement; a = a.parentElement) {
      const acs = getComputedStyle(a);
      const isStruct = /\b(screen-header|screen-content|screen-footer|scontainer|widgets|pcanvas)\b/.test((a.getAttribute('class') || '').toString());
      if (!isStruct && (acs.overflow === 'hidden' || acs.overflow === 'clip')) {
        const ar = a.getBoundingClientRect();
        const bx0 = (ar.x - brr.x) * sx, by0 = (ar.y - brr.y) * sy, bw0 = ar.width * sx, bh0 = ar.height * sy;
        clip = clip
          ? { x: Math.max(clip.x, bx0), y: Math.max(clip.y, by0), w: Math.min(clip.x + clip.w, bx0 + bw0) - Math.max(clip.x, bx0), h: Math.min(clip.y + clip.h, by0 + bh0) - Math.max(clip.y, by0) }
          : { x: bx0, y: by0, w: bw0, h: bh0 };
      }
    }
    return (clip && clip.w > 0 && clip.h > 0) ? clip : null;
  }
  function walk(el, parentIdx, depth, zone) {
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    if (cs.display === 'none' || cs.visibility === 'hidden' || +(cs.opacity) <= 0.01) return;
    if (/Scrollbar/i.test(el.className || '')) return;
    if (el !== p) zone = zoneOf(el);   // 每元素实测所属区（曾漏这行：footer 全被标 content，钉底落空）
    const dx = (r.x - brr.x) * sx, dy = (r.y - brr.y) * sy, dw = r.width * sx, dh = r.height * sy;
    const idx = nodes.length;
    const rec = { idx, parent: parentIdx, depth, tag: el.tagName.toLowerCase(), zone,
      x: +dx.toFixed(1), y: +dy.toFixed(1), w: +dw.toFixed(1), h: +dh.toFixed(1),
      cls: (el.className || '').toString().slice(0, 80) };
    const nm = el.getAttribute('data-name') || '';
    if (nm) rec.name = nm.slice(0, 80);
    const own = (() => {
      let s = '';
      for (const x of el.childNodes) {
        if (x.nodeType === 3 && x.textContent.trim()) s += x.textContent.trim() + ' ';
        else if (x.nodeType === 1 && x.tagName === 'BR') s = s.replace(/\\s+$/, '') + '\\n';
      }
      return s.trim();
    })();
    if (own) rec.text = own;
    const st = {};
    if (cs.whiteSpace && cs.whiteSpace !== 'normal') st.ws = cs.whiteSpace;
    if (own && el.children.length === 0) {
      try {
        const rg = document.createRange(); rg.selectNodeContents(el);
        const rb = rg.getBoundingClientRect();
        if (rb.height > 0) st.textH = +(rb.height * sy).toFixed(1);
      } catch (e) {}
    }
    if (cs.backgroundColor && cs.backgroundColor !== 'rgba(0, 0, 0, 0)') st.bg = cs.backgroundColor;
    if (cs.backgroundImage && cs.backgroundImage !== 'none') {
      st.bgi = /^url\\(["']?data:/i.test(cs.backgroundImage) ? cs.backgroundImage.slice(0, 30000) : cs.backgroundImage.slice(0, 500);
    }
    if (cs.borderRadius && cs.borderRadius !== '0px') st.br = cs.borderRadius;
    if (cs.borderWidth && cs.borderWidth !== '0px') { st.bw = cs.borderWidth; st.bc = cs.borderColor; st.bs = cs.borderStyle; }
    if (cs.opacity && cs.opacity !== '1') st.op = cs.opacity;
    st.clr = cs.color;   // 全节点记色：svg currentColor / data:bgi currentColor 都靠它
    if (cs.zIndex && cs.zIndex !== 'auto') st.zi = cs.zIndex;
    if (cs.overflow && cs.overflow !== 'visible') st.ovf = cs.overflow;
    if (cs.boxShadow && cs.boxShadow !== 'none') st.bsh = cs.boxShadow;
    if (cs.filter && cs.filter !== 'none') st.flt = cs.filter;
    if (cs.clipPath && cs.clipPath !== 'none') st.cp = cs.clipPath;
    if (cs.mask && cs.mask !== 'none' && cs.mask !== '') st.mk = cs.mask;
    if (cs.transform && cs.transform !== 'none') st.tf = cs.transform;   // 仅 gen-html 透传不改 AABB 的翻转（180°/镜像）
    if (rec.text) { st.fs = cs.fontSize; st.fw = cs.fontWeight; st.ta = cs.textAlign; st.lh = cs.lineHeight; st.ff = cs.fontFamily; }
    if (Object.keys(st).length) rec.st = st;
    if (rec.tag === 'svg') {
      let sv = el.outerHTML;
      // path-icon（.fill 修饰）着色 = hash 定向硬编码规则 → 现场字典解析；无规则才落回继承色
      const clsM = sv.slice(0, sv.indexOf('>')).match(/class="([^"]*)"/);
      const cls = clsM ? clsM[1] : '';
      if (/(?:^|\\s)svg-icon-path-icon(?:\\s|$)/.test(cls) && /(?:^|\\s)fill(?:\\s|$)/.test(cls)) {
        const hashM = cls.match(/StyledSVGIconPathComponent-sc-[\\w-]+\\s+(\\S+)/);
        const solid = (hashM && window.__mthIconMap[hashM[1]]) || cs.color;
        sv = sv.replace(/\\b(fill|stroke)="(?!none|transparent)[^"]*"/gi, '$1="' + solid + '"');
        // 线性图标补丁：stroke 型元素补 fill="none"，防开放路径（chevron/箭头）隐式闭合填成实心块
        sv = sv.replace(/<(path|g|circle|rect|polygon|polyline|line|ellipse)\\b([^>]*)>/gi, (m, tag2, attrs) =>
          /\\sstroke="(?!none|transparent)[^"]*"/i.test(attrs) && !/\\sfill="/i.test(attrs) ? '<' + tag2 + attrs + ' fill="none">' : m);
        if (!/\\sfill=/.test(sv.slice(0, sv.indexOf('>')))) sv = sv.replace(/<svg\\b/i, '<svg fill="' + solid + '" ');
      }
      rec.svg = sv;
      el.setAttribute('data-mth', String(idx));   // 采样标记——必须在取 outerHTML 之后，防污染 svg 源码
      nodes.push(rec);
      return;
    }
    if (rec.tag === 'img') {
      rec.img = el.getAttribute('src') || '';
      if (!rec.img) return;   // 空 src（SketchArtboardImage 占位等）不产节点
      // img 专属祖先裁剪（2026-10-20 实锤：地图 img 盒 647 高被 image_view(定位+hidden,315) 裁成顶段，
      // 不裁会全高盖住订单条）。CSS 规则：绝对定位子元素只被「定位的」overflow:hidden 祖先裁剪，
      // 静态 0×0 包装器的 hidden 不裁（绝对定位子元素逃逸）——故只认「定位 + hidden/clip」祖先
      const clipBox = ancestorClipBox(el);
      if (clipBox) {
        const nx = Math.max(rec.x, clipBox.x), ny = Math.max(rec.y, clipBox.y);
        const nw = Math.min(rec.x + rec.w, clipBox.x + clipBox.w) - nx;
        const nh = Math.min(rec.y + rec.h, clipBox.y + clipBox.h) - ny;
        if (nw <= 0.5 || nh <= 0.5) return;   // 完全被裁掉 = 查看器不可见
        if (nw < rec.w - 0.5 || nh < rec.h - 0.5) {
          rec.clipFrom = { dx: +(nx - rec.x).toFixed(1), dy: +(ny - rec.y).toFixed(1), w: +rec.w.toFixed(1), h: +rec.h.toFixed(1) };   // 原盒偏移/尺寸，gen-html 按原盒渲染复现查看器取景
          rec.x = +nx.toFixed(1); rec.y = +ny.toFixed(1); rec.w = +nw.toFixed(1); rec.h = +nh.toFixed(1);
        }
      }
    }
    if (!rec.img && st.bgi) {
      // bgi 同法：定位+hidden 祖先盒收紧几何（背景 cover 居中裁，取景近似）
      const clipBox = ancestorClipBox(el);
      if (clipBox) {
        const nx = Math.max(rec.x, clipBox.x), ny = Math.max(rec.y, clipBox.y);
        const nw = Math.min(rec.x + rec.w, clipBox.x + clipBox.w) - nx;
        const nh = Math.min(rec.y + rec.h, clipBox.y + clipBox.h) - ny;
        if (nw <= 0.5 || nh <= 0.5) return;
        if (nw < rec.w - 0.5 || nh < rec.h - 0.5) { rec.x = +nx.toFixed(1); rec.y = +ny.toFixed(1); rec.w = +nw.toFixed(1); rec.h = +nh.toFixed(1); }
      }
    }
    el.setAttribute('data-mth', String(idx));   // 采样标记
    nodes.push(rec);
    pseudoRec(el, '::before', idx, zone);
    pseudoRec(el, '::after', idx, zone);
    for (const ch of el.children) walk(ch, idx, depth + 1, zone);
  }
  walk(p, null, 0, 'content');
  return { board: { w: p.offsetWidth, h: p.offsetHeight }, pkgBase: baseUrl, nodes };
})()`;

// Node 侧后处理：采样约束拓扑重排 → footer 孪生去重 → 板高口径
export function postPass(data, boardMode = 'long', stacks = []) {
  const nodes = data.nodes;
  // ---- 采样约束 → 拓扑重排（以查看器实测绘制序为准；无约束的小元素按原序稳定兜底） ----
  if (Array.isArray(stacks) && stacks.length) {
    const ids = new Set(nodes.map(n => n.idx));
    const below = new Map();   // u → Set(v)：u 绘制在 v 之下（升序时 u 先于 v）
    const addEdge = (u, v) => {
      if (u === v || !ids.has(u) || !ids.has(v)) return;
      if (!below.has(u)) below.set(u, new Set());
      below.get(u).add(v);
    };
    for (const stack of stacks) for (let i = stack.length - 1; i > 0; i--) addEdge(stack[i], stack[i - 1]);
    const indeg = new Map([...ids].map(i => [i, 0]));
    for (const [, vs] of below) for (const v of vs) indeg.set(v, (indeg.get(v) || 0) + 1);
    const order = [];
    const avail = [...ids].filter(i => indeg.get(i) === 0).sort((a, b) => a - b);
    while (avail.length) {
      const u = avail.shift();
      order.push(u);
      for (const v of (below.get(u) || [])) {
        indeg.set(v, indeg.get(v) - 1);
        if (indeg.get(v) === 0) { avail.push(v); avail.sort((a, b) => a - b); }
      }
    }
    if (order.length < nodes.length) {          // 环内残余（理论上不应出现）按原序追加
      const inOrder = new Set(order);
      order.push(...nodes.map(n => n.idx).filter(i => !inOrder.has(i)).sort((a, b) => a - b));
    }
    const remap = new Map(order.map((old, i) => [old, i]));
    for (const n of nodes) {
      n.idx = remap.get(n.idx);
      n.parent = n.parent == null ? null : (remap.has(n.parent) ? remap.get(n.parent) : null);
    }
    nodes.sort((a, b) => a.idx - b.idx);
  }
  const byParent = new Map();
  for (const n of nodes) {
    if (!byParent.has(n.parent)) byParent.set(n.parent, []);
    byParent.get(n.parent).push(n);
  }
  const subtreeText = (n) => {
    let s = String(n.text || '').trim();
    for (const ch of (byParent.get(n.idx) || [])) s += subtreeText(ch);
    return s;
  };
  const subtreeDrop = (n) => { n.__drop = true; for (const ch of (byParent.get(n.idx) || [])) subtreeDrop(ch); };
  const contentBottom = Math.max(data.board.h,
    ...nodes.filter(n => n.zone !== 'footer').map(n => n.y + n.h), 1);
  const footerRoots = nodes.filter(n => n.zone === 'footer' && !(nodes[n.parent] && nodes[n.parent].zone === 'footer'));
  const kept = [];
  for (const fr of footerRoots) {
    const ft = subtreeText(fr);
    // 纯文本串判定：footer 根常是 0×0 包装器，尺寸比对会误杀（实测「确认送达」双份实证）
    const twin = ft && nodes.some(n => n.zone !== 'footer' && !n.__drop
      && String(n.text || '').trim() && subtreeText(n) === ft);
    if (twin) subtreeDrop(fr);
  }
  const shift = contentBottom - data.board.h;
  for (const n of nodes) {
    if (n.__drop) continue;
    if (boardMode === 'long' && n.zone === 'footer') n.y = +(n.y + shift).toFixed(1);   // 无孪生的固定层钉到长画布底部
    kept.push(n);
  }
  const boardH = boardMode === 'long' ? Math.max(data.board.h, contentBottom) : data.board.h;
  return { nodes: kept, board: { w: data.board.w, h: +boardH.toFixed(1) } };
}

// 单板完整提取（懒加载预滚 + PICK + 后处理 + 写 boards/<cid>.json），batch.mjs / extract-board.mjs 共用
export async function extractBoardPcanvas({ port, cid, outJson, name, boardMode = 'long', tool = 'pcanvas-extract.mjs' }) {
  const c = await connect(port);
  try {
    const { evalJS } = c;
    let n = await evalJS(ROLL(cid));
    if (n === -1) return { err: 'board gone' };
    for (let i = 0; i < 20 && n > 0; i++) {
      await sleep(1500);
      n = await evalJS(`(() => {
        const p = document.querySelector('.pcanvas[data-cid="${cid}"]');
        return p ? p.querySelectorAll('.image-container.is-default-image').length : 999;
      })()`);
    }
    await evalJS(ROLL(cid));
    await sleep(3000);
    const data = await evalJS(PICK(cid));
    if (!data || data.err || data.error) return { err: JSON.stringify(data) };
    let stacks = [];
    try { stacks = await evalJS(SAMPLE(cid)); } catch (e) { stacks = []; }   // 采样失败不致命：兜底原序
    const pp = postPass(data, boardMode, Array.isArray(stacks) ? stacks : []);
    const doc = { meta: { tool, generatedAt: new Date().toISOString() },
      page: { cid, name: name || cid, board: pp.board, pkgBase: data.pkgBase, nodes: pp.nodes } };
    const fs = await import('node:fs');
    fs.writeFileSync(outJson, JSON.stringify(doc));
    return { ok: true, nodes: pp.nodes.length, board: pp.board };
  } finally { c.close(); }
}
