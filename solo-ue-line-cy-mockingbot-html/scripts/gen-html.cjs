#!/usr/bin/env node
// gen-html.cjs —— 画板提取 JSON → 干净、可编辑、可双击打开的静态 HTML
// 用法：node gen-html.cjs <board.json> <out.html> [--assets <输出根assets绝对目录>] [--assets-rel <HTML引用assets的相对前缀，默认 assets>]
//
// 设计目标：人能直接改源码 —— 平铺 div + 行内 style、每节点一行、图层注释定位、无构建无依赖。
// 固化规则（前会话踩坑）：
//   1) z-index 一律用提取序 idx（墨刀原始 zi 只在同父兄弟内有效，平铺后套用会让全屏底板盖死全部内容）
//   2) svg 外拷丢失查看器全局 fill 规则会渲染成黑块 → 强制注入 fill="currentColor"
//   3) 交互指示层（InteractionMarker / 橙热区）是墨刀查看器 UI，整棵删除
//   4) 舞台尺寸 = 画板自身设定（board.w/h），不写死
//   5) 图片拷进产物 assets/（自包含，挪走墨刀源包不断图）；bgi 里 blob: 丢弃、data:（内嵌 svg）原样内联保留
//   6) 文字换行：有空间不折行（墨刀单行渲染/估算放得下 → nowrap，防字体差异折出孤字），显式多行 pre-line，墨刀多行渲染 normal
const fs = require('fs');
const path = require('path');

const argv = process.argv.slice(2);
const [, , inPath, outPath] = process.argv;
const assetsDir = argv[argv.indexOf('--assets') + 1];
const assetsRel = argv[argv.indexOf('--assets-rel') + 1] || 'assets';
// 交互热区（可选）：--hotzones <read-hotzones.mjs 产出的 hotzones.json> + --state <产物根 state.json>（目标 cid→html 解析）
const hotzonesPath = argv.includes('--hotzones') ? argv[argv.indexOf('--hotzones') + 1] : null;
const statePath = argv.includes('--state') ? argv[argv.indexOf('--state') + 1] : null;
if (!inPath || !outPath || !fs.existsSync(inPath)) {
  console.error('用法: node gen-html.cjs <board.json> <out.html> [--assets <dir>] [--assets-rel <prefix>] [--hotzones <hotzones.json> --state <state.json>]');
  process.exit(1);
}

const j = JSON.parse(fs.readFileSync(inPath, 'utf8'));
const pg = j.page || (j.pages && j.pages[0]);
if (!pg) { console.error('JSON 里没有 page/pages[0]'); process.exit(1); }
const boardW = pg.board.w, boardH = pg.board.h;
const pkgBase = pg.pkgBase || '';
const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
// path 图标色值字典：{styled-components hash 类 → 查看器实测填充色}。
// 查看器对 svg-icon-path-icon 的色值来自 solidColor prop 插值的运行时 CSS（提取 json 无此字段），
// 但色值参与 hash 指纹（同色=同 hash，全站 46 个）→ 从查看器翻页全量采集固化于此
// ⚠ scripts/ 与 references/ 必须同源拷贝：字典缺失时每页 gen 报 MODULE_NOT_FOUND（2026-10-24 实测静默浪费一轮跑批），先给明确报错
const iconColorsPath = path.join(__dirname, '..', 'references', 'icon-colors.json');
if (!fs.existsSync(iconColorsPath)) {
  console.error('✗ 缺少 ' + iconColorsPath + ' —— 请把技能根目录的 references/ 与 scripts/ 一起拷贝');
  process.exit(1);
}
const iconColors = require(iconColorsPath);

// ---- 交互热区层（可选参数才有）：zones[板cid] → 每热区 <a> 跳目标产物 html ----
// 目标解析优先级：toCanvas（板 cid 直跳）→ toPage（页面 cid 跳该页首板）→ url（外链 _blank）→ 无 href（目标未收录，hover 提示）
let hzLines = [];
if (hotzonesPath && statePath && fs.existsSync(hotzonesPath) && fs.existsSync(statePath)) {
  const zones = JSON.parse(fs.readFileSync(hotzonesPath, 'utf8')).zones || {};
  const st = JSON.parse(fs.readFileSync(statePath, 'utf8'));
  const ROOT = path.dirname(path.resolve(statePath));
  const canvasMap = new Map(), pageMap = new Map();   // 板cid/页面cid → { html(产物根相对), name }
  for (const [pcid, d] of Object.entries(st.done || {})) {
    const bs = d.boards || [];
    for (const b of bs) if (b.cid && b.html) canvasMap.set(b.cid, { html: b.html, name: (bs.length > 1 ? d.name + '/' : '') + (b.name || '') });
    if (bs.length && bs[0].html) pageMap.set(pcid, { html: bs[0].html, name: d.name });
  }
  const relHref = (h) => encodeURI(path.relative(path.dirname(path.resolve(outPath)), path.resolve(ROOT, h)).replace(/\\/g, '/'));
  for (const z of (zones[pg.cid] || [])) {
    // 一个 widget 可绑多个交互：静态页只支持单点击单目标，取第一个跳页优先、其次外链
    const jump = z.inters.find(i => i.t === 1 && (i.toCanvas || i.toPage));
    const ext = z.inters.find(i => i.url);
    let href = '', title = '', extTarget = false;
    if (jump) {
      const tgt = canvasMap.get(jump.toCanvas) || pageMap.get(jump.toPage);
      if (tgt) { href = relHref(tgt.html); title = `跳转 → ${tgt.name}`; }
      else title = `跳转目标未收录（${jump.toCanvas || jump.toPage}）`;
    } else if (ext) { href = ext.url; title = `外链 → ${ext.url}`; extTarget = true; }
    if (!title) title = '交互热区';
    hzLines.push(`<!-- 热区 [${z.widgetCid}] ${z.name} ${title} -->`);
    hzLines.push(`<a class="mth-hz" ${href ? `href="${esc(href)}"${extTarget ? ' target="_blank" rel="noopener"' : ''}` : ''} title="${esc(title)}" style="left:${z.x}px;top:${z.y}px;width:${z.w}px;height:${z.h}px"></a>`);
  }
}

// ---- 节点索引（img 圆角要从父链继承：墨刀头像是 wImage→Wrapper→container 三层嵌套圆角包着 img，平铺提取只拿 img 叶子，自身 br 为空） ----
const byIdx = new Map(pg.nodes.map(n => [n.idx, n]));
// 圆角继承两段式（2026-09-16 两轮验收实锤）：
// ① cover 载体形态：查看器 img 元素是 object-fit:cover 拉伸后的【溢出尺寸】（如 img 85×64 溢出 64×64 容器、br=100px 裁圆），
//    父链第一个 br 容器 ≤ img（cover 语义：容器不大于 img）→ 该容器就是圆形显示区：br 继承 + 产物框用【容器框】
//    （用 img 溢出框套 br 会变胶囊形，不是墨刀里的正圆/圆角）
// ② 贴合兜底：img ≈ 容器尺寸（胶囊卡「图 36×42.7 在 36×48 br=48」高差 5~8px 常态；h<24 小图标严格 ±2px 防「圆角不属于图」误继承）
const inheritBr = (n) => {
  if (n.st && n.st.br) return { br: n.st.br };
  let p = byIdx.get(n.parent);
  while (p) {                       // ① 最近 br 容器 = cover 载体
    if (p.st && p.st.br) {
      if (p.w > 4 && p.h > 4 && p.w <= n.w + 2 && p.h <= n.h + 2) return { br: p.st.br, box: p };
      break;                        // 第一个 br 容器不是 cover 载体（比 img 大）——远祖 br 不属于图，不往上
    }
    p = byIdx.get(p.parent);
  }
  const big = n.h >= 24;            // ② 贴合兜底
  p = byIdx.get(n.parent);
  while (p) {
    if (p.st && p.st.br) {
      const wFit = Math.abs(p.w - n.w) < 2;
      const hFit = Math.abs(p.h - n.h) < 2 || (big && p.h - n.h >= 0 && p.h - n.h <= 8);
      if (wFit && hFit) return { br: p.st.br };
    }
    p = byIdx.get(p.parent);
  }
  return null;
};

// ---- 热区判定（查看器交互指示层） ----
const isHotzone = (n) => /^rgba\(255,\s*140,\s*25,/.test((n.st && n.st.bg) || '');
const byParent = new Map();
for (const n of pg.nodes) {
  if (!byParent.has(n.parent)) byParent.set(n.parent, []);
  byParent.get(n.parent).push(n);
}
const drop = new Set();
const markTree = (idx) => { drop.add(idx); (byParent.get(idx) || []).forEach(markTree); };
for (const n of pg.nodes) if (/InteractionMarker/i.test(n.cls || '')) markTree(n.idx);
// 热区 widget 壳（cls 含 wLr）：墨刀查看器给画过热区的 widget 套的透明容器（48×46 级），自身无视觉内容、
// z-index 高，残留会整块盖住下方按钮/图标吃掉真实点击（2026-09-16 用户实锤「页面上点不动」——el.click() 绕过
// 命中测试测不出来，Input.dispatchMouseEvent 真实点击顶层是壳 div）。全量验证 2580 壳子树除橙块/角标外零内容，整树删安全。
for (const n of pg.nodes) if (/wLr/.test(n.cls || '')) markTree(n.idx);
// 交互标记 ✦ svg 本体：墨刀查看器 InteractionMarker 容器内的 link/mark 图标是平铺独立节点——
// SVG 元素的 cls 提取值是坏值 "[object SVGAnimatedString]"（className 是对象，须 .baseVal），容器删了它还在（12.6×12.6 角标残留产物，2026-09-16 用户截图实锤 15+ 处）。
// 按 svg 源码 class 含 icon/link/mark 整删（内容判定，不依赖 parent 树）。
for (const n of pg.nodes) if (/icon\/link\/mark/.test(String(n.svg || ''))) drop.add(n.idx);

// ---- B类规避①：同文本同位双份渲染去重（用户拍板处理）——留 idx 大的一份（z-index 大=视觉盖着的），删被盖的 ----
const dupDrop = new Set();
{
  const seen = new Map();
  for (const n of pg.nodes) {
    const t = String(n.text || '').trim();
    if (t.length < 2) continue;
    const key = t + '@' + Math.round(n.x / 4) + ',' + Math.round(n.y / 4);
    const prev = seen.get(key);
    if (prev && Math.abs(prev.w - n.w) < 3 && Math.abs(prev.h - n.h) < 3) { dupDrop.add(prev.idx); seen.set(key, n); }
    else if (!prev) seen.set(key, n);
  }
}

// ---- B类规避②：同带同高元素 top 对齐（3~4px 亚像素参差）——只动「同高度」元素（同类元素纯误差），不同高度的错落设计不动 ----
{
  const bands = [];
  for (const n of pg.nodes) {
    if (dupDrop.has(n.idx) || drop.has(n.idx)) continue;
    let g = bands.find(b => Math.abs(b.y - n.y) < 3 && Math.abs(b.h - n.h) < 1);
    if (!g) { g = { y: n.y, h: n.h, ns: [] }; bands.push(g); }
    g.ns.push(n);
  }
  for (const g of bands) {
    if (g.ns.length < 3) continue;
    const ys = g.ns.map(n => n.y).sort((a, b) => a - b);
    if (ys[ys.length - 1] - ys[0] < 2) continue;            // 已齐不动
    const mid = ys[Math.floor(ys.length / 2)];
    for (const n of g.ns) n.y = mid;
  }
}

// ---- 图片拷贝 ----
const fileUrlToLocal = (u) => {
  if (!u) return null;
  let s = String(u).trim();
  if (/^(blob:|data:)/.test(s)) return null;
  if (/^https?:/.test(s)) return null;                       // 外链不动（保留原 URL）
  if (/^file:/i.test(s)) {
    try { return decodeURIComponent(new URL(s).pathname.replace(/^\/([A-Za-z]:)/, '$1')); } catch { return null; }
  }
  // 相对路径 → 墨刀包内绝对路径
  const baseLocal = decodeURIComponent(new URL(pkgBase).pathname.replace(/^\/([A-Za-z]:)/, '$1'));
  return path.join(baseLocal, s.replace(/^\.\//, ''));
};
const copied = new Map();   // 源绝对路径(小写) -> 产物文件名
function copyAsset(srcUrl) {
  if (!assetsDir) return null;
  const local = fileUrlToLocal(srcUrl);
  if (!local || !fs.existsSync(local)) return null;
  const key = local.toLowerCase();
  if (copied.has(key)) return copied.get(key);
  const base = path.basename(local).replace(/[<>:"|?*\\\/]/g, '_');
  let name = base, i = 2;
  while (fs.existsSync(path.join(assetsDir, name)) && !sameFile(path.join(assetsDir, name), local)) name = `${i++}_${base}`;
  fs.mkdirSync(assetsDir, { recursive: true });
  fs.copyFileSync(local, path.join(assetsDir, name));
  copied.set(key, name);
  return name;
}
function sameFile(a, b) {
  try { return fs.statSync(a).size === fs.statSync(b).size; } catch { return false; }
}
// bgi：blob: 丢弃（会话级 URL 无法还原）；data:（墨刀内嵌 svg 图标）原样内联保留——CSS 原生支持 data URI
function rewriteBgi(bgi, clr) {
  if (!bgi) return null;
  if (/url\(["']?blob:/.test(bgi)) return null;
  if (/url\(["']?data:/i.test(bgi)) {
    // data:svg 里写 currentColor 的：background-image 不继承宿主 color → 替换成节点 color 真值，防黑块
    return clr ? bgi.replace(/currentColor/g, clr) : bgi;
  }
  return bgi.replace(/url\((["']?)([^"')]+)\1\)/g, (m, q, u) => {
    const name = copyAsset(u);
    return name ? `url("${assetsRel}/${name}")` : (/^https?:/.test(u) ? m : '');
  });
}

// ---- 文字换行策略（用户拍板：有空间尽量不要换行，但不是所有文本都不换行——看左右空间够不够）----
// 成因：产物字体 fallback 与墨刀渲染字体宽度有差异，同宽框里文字变宽 → 单行文本折出孤字并压到下方节点。
// 判定优先级（实测校准：hug 框 ratio≈1.0、长文案 ratio=1.46，阈值 1.08 分得很开）：
//   1) 墨刀显式 white-space 只有 nowrap/pre 族才还原——break-spaces 是查看器默认文本样式（实测 8 节点 7 个都是），不代表设计意图
//   2) 含显式换行 \n → pre-line（HTML 默认折叠 \n）
//   3) 估宽主判据：估单行宽（CJK≈fs、其他≈0.55fs）≤ 框宽×1.08 = 放得下/贴框 hug（墨刀文本框自动贴合内容宽）→ nowrap
//   4) 估算超框但墨刀实测单行（textH ≤ 1.5 行高）= 溢出框渲染的单行 → 也 nowrap。
//      textH 只做本向兜底：临界折行时它被 fallback 字体污染（实测临界文本 ratio 0.99 却测出 2 行），不能反着用
const px = (v, fb) => { const m = parseFloat(v); return Number.isFinite(m) ? m : fb; };
function whiteSpaceRule(n, st) {
  const t = String(n.text);
  // 墨刀显式「不折行」类（nowrap/pre 本身就是单行语义）直接还原；含 \n 的 pre 也靠它保真
  if (st.ws === 'nowrap' || st.ws === 'pre') return `white-space:${st.ws}`;
  if (t.includes('\n')) return 'white-space:pre-line';
  const fs = px(st.fs, 16), lh = px(st.lh, fs * 1.4);
  let est = 0;
  for (const ch of t) est += ch.codePointAt(0) > 0x2e7f ? fs : fs * 0.55;
  if (est <= n.w * 1.08) return 'white-space:nowrap';
  if (st.textH != null && st.textH <= lh * 1.5) return 'white-space:nowrap';
  // 单行框（框高 ≤1.8 行高 = 单行 UI 位）内容严重超框（>1.3×）→ 省略号截断（用户口径：放不下按 UI 惯例 …）；
  // 多行框 → 还原墨刀原换行语义（pre-line/pre-wrap/break-spaces/无→normal）。样本实测微溢出全在 15px 内（hug 框字体余量），本分支是全量兜底
  if (n.h <= lh * 1.8 && est > n.w * 1.3) return 'white-space:nowrap;overflow:hidden;text-overflow:ellipsis';
  return st.ws ? `white-space:${st.ws}` : 'white-space:normal';
}

// ---- 按钮底板索引（按钮文案单行还原用，2026-09-17 用户实锤「按钮文案换行」）----
// 形态：文本框画窄（est 超框、墨刀里就折行 textH≈2×lh），但叠在外层实心按钮底板上、底板宽能容纳单行
// ——设计意图是一行（同按钮其他状态板文本框就是一行宽），稿子失误在产物侧规避（同 B 类规避先例）。
// 底板 = 有 bg/bgi（非透明/非热区橙）、无文本、未被删的实心块
const solidPlates = pg.nodes.filter(n =>
  !String(n.text || '').trim() && !drop.has(n.idx) && !dupDrop.has(n.idx) && !isHotzone(n)
  && ((n.st && n.st.bg && !/transparent/.test(n.st.bg)) || (n.st && n.st.bgi))
  && n.w >= 36 && n.h >= 16);
// 最紧包含文本框中心的底板（取面积最小——排除卡片/全屏大底，只认按钮本体）
function tightPlate(n) {
  const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
  let best = null;
  for (const p of solidPlates) {
    if (cx < p.x || cx > p.x + p.w || cy < p.y || cy > p.y + p.h) continue;
    if (!best || p.w * p.h < best.w * best.h) best = p;
  }
  return best;
}

// ---- 节点渲染 ----
const widgetType = (n) => {
  const m = (n.cls || '').match(/\bw[A-Z][A-Za-z]+\b/);
  return m ? m[0] : (n.tag || '');
};
const lines = [];
let dropped = 0, textCount = 0, svgCount = 0, imgCount = 0, imgMiss = 0;
const iconMiss = {};   // path 图标 hash 未命中字典计数（理论上 0——字典按产物 hash 全集采齐）

for (const n of pg.nodes) {
  if (drop.has(n.idx) || dupDrop.has(n.idx) || isHotzone(n)) { dropped++; continue; }
  if (n.x >= boardW || n.y >= boardH || (n.w <= 0 && n.h <= 0)) continue;   // 画板外辅助层
  // ---- B类规避③：右/下越界 clamp 回画布（稿内出界元素产物贴边裁齐；左/上负坐标保持——HTML 天然支持，stage 裁剪视觉一致） ----
  let nw = n.w, nh = n.h;
  if (n.x + nw > boardW + 1) nw = Math.max(1, boardW - n.x);
  if (n.y + nh > boardH + 1) nh = Math.max(1, boardH - n.y);
  const st = n.st || {};
  const css = [`left:${n.x}px`, `top:${n.y}px`, `width:${nw}px`, `height:${nh}px`, 'position:absolute', 'box-sizing:border-box'];
  if (st.bg) css.push(`background:${st.bg}`);
  const bgi = rewriteBgi(st.bgi, st.clr); if (bgi) css.push(`background-image:${bgi}`);
  // 头像圆角还原（用户验收实锤）：裸 img 叶子自身 br 为空——墨刀头像 = wImage→Wrapper→container 三层圆角容器嵌套 img，
  // 平铺提取父容器丢掉 → 产物方头像。从贴合父链继承 br；且 border-radius 不裁子内容（要 overflow:hidden 配合），否则 img 直角照样露出
  // bgi（背景图形态的图片）同法继承（2026-09-16 补：规范一直写了 bgi 同法但代码漏了分支）——background 天然被 br 裁，不加 overflow:hidden
  if (n.img) {
    const r = inheritBr(n);
    if (r) {
      css.push(`border-radius:${r.br}`, 'overflow:hidden');
      if (r.box) {   // cover 载体：产物框换成容器显示框（img 溢出框套 br 会变胶囊形）
        css[0] = `left:${r.box.x}px`; css[1] = `top:${r.box.y}px`;
        css[2] = `width:${r.box.w}px`; css[3] = `height:${r.box.h}px`;
      }
    }
  } else if (bgi) {
    const r = inheritBr(n);
    if (st.br || (r && r.br)) css.push(`border-radius:${st.br || r.br}`);   // background 天然被 br 裁，无需 overflow:hidden；bgi 无 img 溢出形态，只取 br 不换框
  } else if (st.br) css.push(`border-radius:${st.br}`);
  if (st.bw && st.bw !== '0px') css.push(`border:${st.bw} ${st.bs || 'solid'} ${st.bc || 'transparent'}`);
  if (st.op) css.push(`opacity:${st.op}`);
  if (st.ovf) css.push(`overflow:${st.ovf}`);
  if (st.bsh) css.push(`box-shadow:${st.bsh}`);
  if (st.cp) css.push(`clip-path:${st.cp}`);
  if (st.mk) css.push(`-webkit-mask:${st.mk};mask:${st.mk}`);
  if (st.flt) css.push(`filter:${st.flt}`);
  // 方向性翻转透传（2026-10-20）：rect 坐标已含变换，但 180°/镜像这类不改 AABB 的翻转只改绘制方向——
  // 图标方向翻转移不过 rect。90° 类会破坏宽高语义，不透传（st.tf 仅新模型提取端采集，旧数据无此字段零影响）
  if (st.tf && /rotate\(180deg\)|scaleX\(-1\)|scaleY\(-1\)|scale\(-1/.test(st.tf)) css.push(`transform:${st.tf}`);
  css.push(`z-index:${n.idx}`);            // 平铺互为兄弟：文档序叠放（勿改回墨刀原始 zi）
  if (st.clr) css.push(`color:${st.clr}`); // svg fill=currentColor 依赖继承
  let inner = '';
  if (n.text) {
    textCount++;
    if (st.fs) css.push(`font-size:${st.fs}`);
    if (st.fw) css.push(`font-weight:${st.fw}`);
    if (st.ta) css.push(`text-align:${st.ta}`);
    if (st.lh) css.push(`line-height:${st.lh}`);
    // 字体链兜底：墨刀常只写 "NotoSans" 一个名字，本机没装就裸 fallback 到浏览器默认——中文宽度差异是折行主因之一
    if (st.ff) css.push(`font-family:${st.ff}${/sans-serif|serif|monospace|cursive|fantasy/.test(st.ff) ? '' : ',"Microsoft YaHei","PingFang SC",sans-serif'}`);
    // 换行策略：空间够→nowrap 防孤字折行；墨刀里多行→normal；被 clamp 收窄的单行文字补省略号（跑马灯公告类）
    let rule = whiteSpaceRule(n, st);
    // ---- 按钮文案单行还原：墨刀里折行（est 超框）但最紧包含底板能容纳单行 → nowrap（文字溢出窄文本框、
    // 在底板内居中一行；text-align center 溢出对称）。安全阀 est≤底板宽×1.05：底板也放不下（真窄按钮）保持墨刀折行。
    // 拉宽规则（下方纯文本框宽自适应）会把框补到 est×1.05，溢出随之消除。----
    let btnOneLine = false;
    if (!rule.includes('nowrap') && !String(n.text).includes('\n')) {
      const fs3 = px(st.fs, 16);
      let est3 = 0;
      for (const ch of String(n.text)) est3 += ch.codePointAt(0) > 0x2e7f ? fs3 : fs3 * 0.55;
      if (est3 > n.w * 1.08) {
        const plate = tightPlate(n);
        if (plate && est3 <= plate.w * 1.05) {
          rule = 'white-space:nowrap';
          btnOneLine = true;
          // 墨刀里两行文字垂直居中于框；变一行后排版顶在框顶会偏上——把单行文字垂直居中回原框中线
          const lh3 = px(st.lh, fs3 * 1.4);
          if (nh > lh3 * 1.3) css[1] = `top:${+(n.y + (nh - lh3) / 2).toFixed(1)}px`;
        }
      }
    }
    css.push(rule.includes('nowrap') && (nw < n.w || nh < n.h) ? rule + ';overflow:hidden;text-overflow:ellipsis' : rule);
    // ---- 纯文本框宽自适应（2026-09-16 用户口径「页面宽度够就拉长文字区域宽度，别折行」）----
    // 产物字体 fallback 比墨刀宽 → 同一框里折出更多行/溢出。对无背景/边框/阴影的纯文本框按估宽拉宽：
    //   单行(nowrap) → 拉到估宽×1.05（消除微溢出）；多行 → 拉到 估宽/墨刀行数×1.05（行数贴合墨刀 textH/lh）。
    // 右缘不超画布（boardW-n.x 封顶）；text-align 居中/右对齐时按锚点回调 x。有背景/边框的容器框保持原宽（拉宽会撑破视觉容器）。
    if (!st.bg && !bgi && !(st.bw && st.bw !== '0px') && !st.bsh && !st.ovf) {
      const fs2 = px(st.fs, 16), lh2 = px(st.lh, fs2 * 1.4);
      let est2 = 0;
      for (const ch of String(n.text)) est2 += ch.codePointAt(0) > 0x2e7f ? fs2 : fs2 * 0.55;
      // 按钮单行还原的节点行数基准=1（textH 是墨刀两行真值，会让 want 减半、拉宽失效）
      const mkLines = btnOneLine ? 1 : (st.textH != null ? Math.max(1, Math.round(st.textH / lh2)) : 1);
      const want = Math.ceil(est2 / mkLines * 1.05);
      const maxW = Math.max(nw, boardW - n.x);   // 至少保持原宽；不越画布右缘
      const newW = Math.min(Math.max(nw, want), maxW);
      if (newW > nw + 1) {
        css[0] = `left:${st.ta === 'center' ? +(n.x - (newW - nw) / 2).toFixed(1) : ((st.ta === 'right' || st.ta === 'end') ? +(n.x - (newW - nw)).toFixed(1) : n.x)}px`;
        css[2] = `width:${+newW.toFixed(1)}px`;   // css 槽位：0=left 1=top 2=width 3=height（此前误写 [3] 会顶掉 height 声明）
      }
    }
    inner = esc(n.text);
  }
  if (n.svg) {
    svgCount++;
    // 墨刀查看器两类图标组件两套上色机制（图标颜色与原型不一致修复实锤）：
    // ① svg-icon-path-icon + .fill 修饰（path 图标，全站 9347 个）：查看器 styled-components 按 solidColor prop 在运行时 CSS
    //    写死填充色（.hash.fill:not([fill]){fill:rgb(...)}），色值不随容器 color、json 里无此字段——但色值参与 hash 类指纹
    //    （同色=同 hash）→ 按 references/icon-colors.json 字典还原。等价还原查看器规则：path/g 写死 fill|stroke(非 none)
    //    一律盖成字典色；="none|transparent" 属形状语义保留；svg 标签无 fill 则注入字典色（子元素继承）
    // ② .svg-icon 类（占位图标等）：查看器 CSS 把子元素写死色盖成 currentColor——写死深色/彩色的线性图标在墨刀里随容器 color 变色，
    //    产物同样替换 currentColor。pure-svg-icon / 无 svg-icon 类（真彩色图标如状态圆点）保留原色
    // ③ svg-icon-path-icon 无 .fill 修饰（294 个）：查看器无任何 fill 规则 → svg 默认黑、path 自身 attr 生效，产物不注入任何 fill
    //    （此前无条件注入 currentColor 会让它错变容器色）
    // 分流判定用完整类名 \bsvg-icon-path-icon\b——旧 /svg-icon/ 子串会误命中 path-icon（上轮修复误伤根源）
    let sv = n.svg;
    const clsM = sv.slice(0, sv.indexOf('>')).match(/class="([^"]*)"/);
    const cls = clsM ? clsM[1] : '';
    const isPathIcon = /(?:^|\s)svg-icon-path-icon(?:\s|$)/.test(cls);
    if (isPathIcon && /(?:^|\s)fill(?:\s|$)/.test(cls)) {
      const hashM = cls.match(/StyledSVGIconPathComponent-sc-[\w-]+\s+(\S+)/);
      const color = hashM && iconColors[hashM[1]];
      if (color) {
        // 查看器 [fill]/[stroke] 规则盖「一切有该 attr 的元素」（含源码自带的 currentColor——VIP阿语板 kBNHRO 实锤），
        // 仅 none/transparent 属形状语义保留
        sv = sv.replace(/\b(fill|stroke)="(?!none|transparent)[^"]*"/gi, '$1="' + color + '"');
        // 线性图标补丁：查看器规则 g [stroke]{stroke:COLOR;fill:none} 把「有 stroke 的元素」fill 强制 none——
        // 源码 stroke 型 path 无 fill attr，产物不补 fill="none" 会继承 svg 注入色，开放路径（chevron/箭头）隐式闭合填成实心块
        sv = sv.replace(/<(path|g|circle|rect|polygon|polyline|line|ellipse)\b([^>]*)>/gi, (m, tag, attrs) =>
          /\sstroke="(?!none|transparent)[^"]*"/i.test(attrs) && !/\sfill="/i.test(attrs) ? `<${tag}${attrs} fill="none">` : m);
        if (!/\sfill=/.test(sv.slice(0, sv.indexOf('>')))) sv = sv.replace(/<svg\b/i, `<svg fill="${color}" `);
      } else if (hashM) iconMiss[hashM[1]] = (iconMiss[hashM[1]] || 0) + 1;
    } else if (/svg-icon/.test(cls) && !/pure-svg-icon/.test(cls)) {
      sv = sv.replace(/\b(fill|stroke)="(?!none|currentColor|transparent)[^"]*"/gi, '$1="currentColor"');
    }
    // 无 width/height 属性的 svg（wLine 线 / svg-icon 线性图标，墨刀靠查看器 CSS 定尺寸）默认按 300×150 渲染：
    // 375 宽的分割线被 svg 自身裁成 300——用户验收「线右侧断一截」实锤。补 100% 跟随提取节点框（=墨刀里实际渲染尺寸）
    const openTag = sv.slice(0, sv.indexOf('>'));
    if (!/\swidth=/.test(openTag) && !/\sheight=/.test(openTag)) {
      sv = sv.replace(/<svg\b/i, '<svg width="100%" height="100%" style="display:block" ');
    }
    // fill=currentColor 注在 svg 标签：无 fill attr 的 path 继承它（外拷丢查看器全局 fill 规则会黑块）；
    // 不再注入 style="fill:currentColor"——svg 原有 style 属性（如 wLine 的 filter）会与注入的撞成双 style，后者被浏览器丢弃。
    // path-icon 例外：带 .fill 的已按字典注入字典色；无 .fill 的查看器就是默认黑，注入 currentColor 反而错
    if (isPathIcon) inner += sv;
    else inner += sv.replace(/<svg\b/i, '<svg fill="currentColor" ');
  }
  if (n.img) {
    imgCount++;
    const name = copyAsset(n.img);
    const src = name ? `${assetsRel}/${name}` : (/^(https?:|file:)/.test(n.img) ? n.img : (pkgBase + String(n.img).replace(/^\.\//, '')));
    if (!name && !/^(https?:|file:)/.test(n.img)) imgMiss++;
    // 被祖先 ovf 裁剪过的 img（clipFrom=原盒相对裁剪盒的偏移/尺寸，2026-10-20）：按原盒绝对定位渲染，
    // 复现查看器取景（如地图只露顶段）——object-fit:cover 的居中裁剪会取错段
    const imgStyle = n.clipFrom
      ? `position:absolute;left:${-n.clipFrom.dx}px;top:${-n.clipFrom.dy}px;width:${n.clipFrom.w}px;height:${n.clipFrom.h}px;object-fit:cover`
      : 'width:100%;height:100%;object-fit:cover';
    inner += `<img src="${esc(src)}" style="${imgStyle}" alt="">`;
  }
  // 图层注释：idx/父节点/名称(或widget类型)/文本摘要 —— 改源码时按注释定位
  const label = n.name ? `name="${n.name}"` : widgetType(n);
  const brief = n.text ? ` text="${String(n.text).slice(0, 24).replace(/"/g, "'")}"` : '';
  lines.push(`<!-- [${n.idx}]${n.parent != null ? ` parent=${n.parent}` : ''} ${label}${brief} -->`);
  // style 属性值里的双引号必须 HTML 转义：font-family 值常带引号（"Microsoft YaHei"），裸引号会截断 style 属性，
  // 排在后面的 white-space 等声明全部失效（实测 nowrap 从未生效、折行问题一直没修掉，源码 grep 有但渲染丢）
  lines.push(`<div data-idx="${n.idx}" style="${css.join(';').replace(/"/g, '&quot;')}">${inner}</div>`);
}

const safeTitle = esc(pg.name || 'board');
const doc = `<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${safeTitle}</title>
<!--
  墨刀画板还原 · 由 mockingbot-to-html 技能生成
  画板: ${safeTitle} (cid: ${pg.cid})
  尺寸: ${boardW} x ${boardH} | 节点: ${lines.length / 2}（热区删除 ${dropped}）文本 ${textCount} / svg ${svgCount} / img ${imgCount}${imgMiss ? `（缺源 ${imgMiss}）` : ''}${Object.keys(iconMiss).length ? `（path图标hash未命中 ${JSON.stringify(iconMiss)}）` : ''}${hzLines.length ? ` / 跳转热区 ${hzLines.length / 2}` : ''}
  编辑说明: 布局为绝对定位平铺，每个节点上方注释标了 [idx] 与图层名；z-index=idx 即叠放顺序，勿改成其他值。${hzLines.length ? '末尾 .mth-hz 为交互热区层（默认透明，hover 显蓝色虚线框），href 即跳转目标，可直接改。' : ''}
-->
<style>
  body { margin:0; padding:24px; background:#E9E9EF; display:flex; justify-content:center; }
  /* flex:none 必须有：stage 宽于视口（如 web 端横板数千 px）时 flex 默认收缩会把画板压窄、右半被 overflow:hidden 裁掉 */
  .stage { position:relative; overflow:hidden; background:#fff; box-shadow:0 8px 40px rgba(0,0,0,.18); flex:none;
    animation: mth-in .18s ease-out; }
  @keyframes mth-in { from { opacity:0; transform:translateY(6px); } to { opacity:1; transform:none; } }
  .mth-back { position:fixed; right:18px; bottom:18px; width:40px; height:40px; border-radius:50%;
    background:rgba(0,0,0,.55); color:#fff; font-size:18px; line-height:40px; text-align:center;
    text-decoration:none; opacity:.35; transition:opacity .15s; z-index:10000; font-family:sans-serif; }
  .mth-back:hover { opacity:.9; }
</style>
</head>
<body>
<div class="stage" style="width:${boardW}px;height:${boardH}px">
${lines.join('\n')}${hzLines.length ? '\n' + hzLines.join('\n') : ''}
</div>
<!-- 返回上一页（原型演示用；无历史时隐藏自身） -->
<a class="mth-back" href="javascript:void(0)" onclick="if(history.length>1){history.back()}else{this.style.display='none'}" title="返回">&#8592;</a>
</body>
</html>`;
fs.mkdirSync(path.dirname(outPath), { recursive: true });
fs.writeFileSync(outPath, doc);
const stats = { ok: true, out: outPath, board: `${boardW}x${boardH}`, nodes: lines.length / 2, dropped, text: textCount, svg: svgCount, img: imgCount, imgMiss, iconMiss, assets: copied.size, hotzones: hzLines.length / 2 };
console.log(JSON.stringify(stats));
