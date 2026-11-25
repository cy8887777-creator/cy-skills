// add-interactions.mjs —— 语义交互绑定（2026-09-16 用户拍板：按元素语义直绑交互，hotzones.json 数据弃用）
// 用法：node add-interactions.mjs <产物根> [--dry]
//
// 背景：墨刀热区数据实测不可信（跳自己/目标错/未收录）且透明热区层已下线（影响导入）。
// 本脚本读 boards/*.json 语义（文本/图标指纹/位置）直接给产物 html 的元素 div 绑 onclick：
//   R1 tab 栏：底部 5 列图标栏，按 svg path 指纹识别列语义（指纹优先于 active 高亮色——语言板间 active 画错常见）：
//        tab1 骰子 M26.080 23.232 → 游戏对战（板块默认首页 = Ludo对战首页）
//        tab2 指南针 M12 10.9    → 发现（三个发现页全 EMPTY 无目标 → 不绑）
//        tab3 多人 M2.667 29.333 → 群组group-大厅列表
//        tab4 气泡 M416 192      → 聊天Chats
//        tab5 人像 M12 2C6.48    → 个人中心Profile
//      当前页 == 目标页的 tab 不绑（跳自己 = 点击不动）。
//   R2 返回箭头：无 tab 栏的页面，左上角 (x<0.12W, 40<y<0.12H) 的 18~30px svg → history.back()
//      （主页面有 tab 栏不适用，天然排除 Ludo 首页左上等级角标等误绑）
//   R3 弹窗取消：文本 ∈ {Cancel, 取消, Close, 关闭, Dismiss} 且按钮形 (w 50~260, h 26~70) → history.back()
//   R4 父子链接：文本 === 当前页直接子级页面名的中文段或英文段（双语名按语言边界切分）→ 跳该子页（同语言板优先）
//      （宁缺毋滥：同文本命中多个子页 / 段长 <2 不绑；Confirm/Delete 类动词目标歧义大，一律不绑）
//   R5 热区档案映射（2026-09-17）：语义规则覆盖不到的功能按钮（Quests/购物车等），读 hotzones.json 档案——
//      热区矩形几何命中板内节点直绑（toCanvas 板优先/toPage 兜底；跳过 trig≠tap、url、目标≠1、跳自己、
//      已被语义绑定覆盖的热区；命中节点取 z 最高）。语义绑定优先，R5 只做补充。
//
// 注入形态：div[data-idx] 加 onclick + style 尾部 cursor:pointer（不改 DOM 结构，不伤后续导入）。
// 幂等：重跑先剥除本脚本注入的 onclick/data-nav/cursor（按特征正则），再重新绑定。
// 跳转目标语言板对齐：目标页 boards 里与当前板同名（English/中文/العربية）优先，否则第一板。
import fs from 'node:fs';
import path from 'node:path';

const ROOT = process.argv[2];
const dry = process.argv.includes('--dry');
if (!ROOT || !fs.existsSync(path.join(ROOT, 'state.json'))) {
  console.error('用法: node add-interactions.mjs <产物根> [--dry]');
  process.exit(1);
}
const state = JSON.parse(fs.readFileSync(path.join(ROOT, 'state.json'), 'utf8'));

// ---- 页面索引 ----
// key: dir.join('/') + '/' + name；entries: {pcid, dir, name, boards:[{cid,name,html,json}]}
const pages = [];
const byPath = new Map();
for (const [pcid, d] of Object.entries(state.done || {})) {
  const p = { pcid, dir: d.dir || [], name: d.name, boards: (d.boards || []).map(b => ({ ...b })) };
  pages.push(p);
  byPath.set(p.dir.join('/') + '/' + p.name, p);
}
const findPage = (dirStr, name) => byPath.get(dirStr + '/' + name);

// tab 目标（硬编码语义映射——目录名即语义约定）
// edge:true 的目标只认「边列」（x<W*0.2 或 x>W*0.78）——人像指纹防中间列孤例错绑
// （「群组group-我的」EN 板 tab2 画错成人像，全站孤例；阿语板双套 tab 栏叠放=LTR+RTL 两版，按指纹各自绑语义都对）
const TAB_TARGETS = [
  { fp: 'M26.080 23.232', dir: '游戏对战   game battle', name: 'Ludo对战首页  Ludo Battle Home' },   // 骰子→游戏对战
  // 指南针→发现：发现页全 EMPTY 无目标，不绑（指纹保留占位，page=null）
  { fp: 'M12 10.9', target: null },
  { fp: 'M2.667 29.333', dir: '群组group', name: '群组group-大厅列表' },                              // 多人→群组
  { fp: 'M416 192', dir: '聊天Chats', name: '聊天Chats' },                                            // 气泡→聊天
  { fp: 'M12 2C6.48', dir: '个人中心Profile', name: '个人中心Profile', edge: true },                   // 人像→个人中心（仅边列）
].map(t => ({ ...t, page: t.dir ? findPage(t.dir, t.name) || null : null }));
const tabTargetsMissing = TAB_TARGETS.filter(t => t.dir && !t.page).map(t => t.name);

// R3 词典（整词）
// 词典整词匹配（含阿语——阿语板同样有取消/关闭按钮；2026-09-16 质检实锤：w≥40 下限曾把「取消」(≈30px)/「OK」(≈20px) 窄 hug 框全卡掉，中文 cancel 一度 0 绑定）
const CANCEL_WORDS = new Set(['Cancel', '取消', 'Close', '关闭', 'Dismiss', 'CANCEL', 'OK', 'Okay', '好的',
  'إلغاء', 'إغلاق', 'حسناً', 'حسنا', 'موافق']);

// R4 双语名切分：最长全英文后缀 & 中文段（最后一个中文字符处截断）& 全称（2026-09-16 质检实锤：
// 旧版「最长全中文前缀」的 isZh 允许英文字母，「商城Shop」整串被判中文段 → 按钮文本「商城」永远对不上，中文板 link 一度 0 绑定）
const isEn = (s) => /^[A-Za-z0-9 .&()\-·:'’!?/]+$/.test(s);
function nameSegments(name) {
  const segs = new Set();
  // 最长全英文后缀（i 从小到大第一个命中的最长）
  for (let i = 0; i < name.length - 1; i++) {
    const suf = name.slice(i);
    if (isEn(suf) && /[A-Za-z]/.test(suf)) { segs.add(suf.trim()); break; }
  }
  // 中文段：头到最后一个中文字符（剥掉尾部英文——「商城Shop」→「商城」、「ludo皮肤 ludo Skins」→「ludo皮肤 ludo皮」不成立则取整段头）
  let lastZh = -1;
  for (let i = 0; i < name.length; i++) if (/[一-龥]/.test(name[i])) lastZh = i;
  if (lastZh >= 1) segs.add(name.slice(0, lastZh + 1).trim());
  // 全称（页面标题文本常与页面名全称相同）
  if (name.trim().length >= 2) segs.add(name.trim());
  return segs;
}

// ---- 子级页面索引（R4）：父路径 → [{segs, page}] ----
const childIndex = new Map();   // 父key → Map(seg → page)（seg 冲突标 null）
for (const p of pages) {
  const parentKey = p.dir.join('/');
  if (!childIndex.has(parentKey)) childIndex.set(parentKey, new Map());
  const m = childIndex.get(parentKey);
  for (const s of nameSegments(p.name)) {
    if (s && s.length >= 2) {
      if (m.has(s) && m.get(s) !== p) m.set(s, null);   // 多页命中 → 禁用该段
      else if (!m.has(s)) m.set(s, p);
    }
  }
}

// ---- 板语言名对齐 ----
// 剥尾序号匹配（2026-09-17 实锤：目标页板名「中文 2」与当前板「中文」不等值 → 精确匹配落空回退 English 板，
// 中文板点创建房间跳英文房间。同语言板复制时墨刀自动加「 2」后缀的形态，剥掉尾部数字再比）
const langMatch = (bs, curBoardName) => {
  const strip = (s) => String(s).replace(/\s*\d+\s*$/, '').trim();
  return bs.find(b => b.name === curBoardName)
    || bs.find(b => strip(b.name) === strip(curBoardName) && strip(b.name) !== '') || bs[0];
};
const boardHref = (targetPage, curBoardName, fromHtml) => {
  const bs = targetPage.boards.filter(b => b.html);
  if (!bs.length) return null;
  const same = langMatch(bs, curBoardName);
  const abs = path.resolve(ROOT, same.html);
  if (!fs.existsSync(abs)) return null;
  return path.relative(path.dirname(path.resolve(ROOT, fromHtml)), abs).replace(/\\/g, '/');
};

// ---- R5 热区档案映射（2026-09-17 用户拍板：Quests/购物车等语义规则覆盖不到的功能按钮，用 hotzones.json 几何映射）----
// 数据源：产物根 hotzones.json（read-hotzones 收的墨刀原始跳转定义档案）。
// 逐热区：tap 交互解析跳转目标（toCanvas 板 cid 优先直取产物板，toPage 页 cid 兜底取第一板）→
// 热区矩形（板内绝对坐标，与 boards json 节点同系）几何命中板内节点 → 绑 onclick。
// 跳过：trig≠tap / url 外链 / 目标去重后 ≠1（缺失 851 或多目标歧义 494）/ 跳自己（同页）/ 热区已被语义绑定覆盖。
// 命中择节点：中心在热区内（±2px）+ 重叠面积占节点 ≥0.5 + 面积 ≤ 热区×3（防背景层）+ w/h≥12（防碎片）→ 取 z 最高。
const HOTZONES = fs.existsSync(path.join(ROOT, 'hotzones.json'))
  ? JSON.parse(fs.readFileSync(path.join(ROOT, 'hotzones.json'), 'utf8')) : { zones: {} };
const pageByPcid = new Map(pages.map(pp => [pp.pcid, pp]));
const boardByCid = new Map();   // 板cid → {page, board}（产物存在的板）
// ---- R6 业务流词典目标页（2026-09-17 用户拍板：墨刀热区只在英文板画、中阿板全没做——热区是残缺数据
// 不可作绑定依据；主 CTA 按页面业务流推演目标直绑，页面上下文+按钮形限制，不覆盖已有绑定）----
const findPageBy = (nameRe) => pages.find(pp => nameRe.test(pp.name)) || null;
const PAGE_GAME_ROOM = findPageBy(/游戏房间 无玩家/);                       // 自建房间首屏
const PAGE_MAIN_EVENT = findPageBy(/Main Events-Home/);                     // 主赛事首页
const PAGE_CREW_WAR = findPageBy(/主页-战队赛/);                            // 战队赛首页
const PAGE_CONFIRM_RECHARGE = findPageBy(/确认充值弹窗/);                    // 充值流下一步
const PAGE_PAYMENT_CONFIRM = findPageBy(/支付确认Payment Confirm/);         // VIP/通行证订阅流下一步
const PAGE_LAUNCH_GROUP_GAME = findPageBy(/群组内开启游戏-群主视角/);         // 群内开游戏流下一步
// 各游戏快速对战入口 → 该游戏选人页（Carrom/Jackaroo 无 rank 命名，取 1v1 默认模式）
const QUICK_TARGETS = [
  { game: /ludo/i, page: findPageBy(/ludo选择人数和规则（ rank场景）/) },
  { game: /uno/i, page: findPageBy(/Uno选择人数和规则（ rank场景）/) },
  { game: /carrom/i, page: findPageBy(/克郎棋选择1v1/) },
  { game: /jackaroo/i, page: findPageBy(/Jackroo选择1v1/) },
].filter(t => t.page);
for (const pp of pages) for (const bb of pp.boards) if (bb.html && fs.existsSync(path.resolve(ROOT, bb.html))) boardByCid.set(bb.cid, { page: pp, board: bb });
function zoneHref(tap, curBoardName, fromHtml) {
  const tb = tap.toCanvas && boardByCid.get(tap.toCanvas);
  const tp = tap.toPage && pageByPcid.get(tap.toPage);
  const page = tb ? tb.page : tp;
  if (!page) return null;
  // 语言对齐：目标页有与宿主同名的板优先（含剥尾序号——「中文 2」对「中文」；墨刀数据记录的 toCanvas
  // 常是当初定义交互的那块语言板，复制到其他语言板时目标不换——2026-09-17 实锤中文板点商城跳 English 板）；
  // 语言对齐不上才回退原 cid 板
  const bs = page.boards.filter(x => x.html && fs.existsSync(path.resolve(ROOT, x.html)));
  if (!bs.length) return null;
  const same = bs.find(x => x.name === curBoardName)
    || bs.find(x => x.name.replace(/\s*\d+\s*$/, '').trim() === curBoardName)
    || (tb && bs.find(x => x.cid === tb.board.cid)) || bs[0];
  return { page, html: same.html };
}

// ---- html 注入（幂等） ----
const stripRe = /(<div data-idx="\d+" style="[^"]*")\s+data-nav="[^"]*"\s+onclick="[^"]*"/g;
function inject(html, actions) {
  // actions: Map(idx → {kind, href?})；先剥旧注入
  html = html.replace(stripRe, '$1').replace(/(<div data-idx="\d+" style="[^"]*?);?cursor:pointer;?/g, '$1');
  if (!actions.size) return html;
  const esc = (s) => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  let n = 0;
  html = html.replace(/(<div data-idx="(\d+)" style="[^"]*)"/g, (m, head, idx) => {
    const a = actions.get(+idx);
    if (!a) return m;
    const code = a.href ? `location.href='${a.href.replace(/'/g, '&#39;')}'` : 'if(history.length>1)history.back()';
    n++;
    return `${head.replace(/;?$/, '')};cursor:pointer" data-nav="${a.kind}" onclick="${code}"`;
  });
  return { html, injected: n };
}

// ---- 主流程 ----
const report = { pages: 0, boards: 0, bound: 0, byRule: { tab: 0, back: 0, cancel: 0, link: 0, zone: 0, goback: 0, flow: 0, mirror: 0 }, details: [] };

// 邻域扩散+文字组队（板内 action → 周边命中层同绑）
function propagate(actions, pg, byIdx, htmlIdxSet) {
  // ---- 底板包含扩散（2026-09-17 跨板镜像实锤：svg 锚点只绑到图标本体，下层底板（idx 更小的
  // 包含矩形，如 32×32 底板套 24×24 svg）没绑——点图标边缘环不动。热区直绑的板没这问题（热区矩形
  // 盖整块），镜像板靠这条补）：B 矩形 ⊇ action 矩形（±2px）且 idx 更小（z 更低=底板）且面积 ≤9× 同绑。
  for (const [idx, act] of [...actions]) {
    const base = byIdx.get(idx);
    if (!base) continue;
    for (const n of pg.nodes) {
      if (n.idx >= idx || actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
      if (n.x > base.x - 2 || n.y > base.y - 2 || n.x + n.w < base.x + base.w - 2 || n.y + n.h < base.y + base.h - 2) continue;
      if (n.w * n.h > base.w * base.h * 9) continue;   // 防背景大层
      actions.set(n.idx, act);
    }
  }

  // ---- 覆盖层扩散（2026-09-16 真实点击实锤的第三层根因）----
  // 平铺产物里所有节点都是 stage 直接子节点（绝对定位+z-index=idx）：视觉上的「子元素」（tab 图标 svg、
  // 按钮内文字/图形）DOM 上是绑定容器的**兄弟**且 z 更高——点击落在它们身上不会冒泡到容器，onclick 永不触发。
  // （el.click() 直接调绑定 div 绕过命中测试，程序自测发现不了；Input.dispatchMouseEvent 真实点击才暴露）
  // 处理：action 节点矩形范围内、z 更高、中心点落在矩形（外扩4px）内的无 action 节点，同绑同一 onclick。
  for (const [idx, act] of [...actions]) {
    const base = byIdx.get(idx);
    if (!base) continue;
    for (const n of pg.nodes) {
      if (n.idx <= idx || actions.has(n.idx)) continue;
      const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
      if (cx < base.x - 4 || cx > base.x + base.w + 4 || cy < base.y - 4 || cy > base.y + base.h + 4) continue;
      actions.set(n.idx, act);   // 扩散注入不计 byRule（语义绑定数不变，这只是命中层）
    }
  }

  // ---- 图标-文字组队（2026-09-17 用户实锤：Quests 入口图标绑了、下方文字点不动——墨刀热区只画
  // 在图标上不盖文字；「图标在上文字在下/图标在左文字在右」不同组的按钮要当一个整体）----
  // 对图标级小节点 action（w≤80）：正下方 22px 内 x 有重叠的文本、正右侧 12px 内 y 有重叠的文本，同绑。
  for (const [idx, act] of [...actions]) {
    const base = byIdx.get(idx);
    if (!base || base.w > 80 || base.h > 80) continue;
    for (const n of pg.nodes) {
      if (actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
      if (!String(n.text || '').trim() || n.w > 200 || n.h > 40) continue;   // 只认文本标签
      const xOverlap = Math.min(base.x + base.w, n.x + n.w) - Math.max(base.x, n.x);
      const yOverlap = Math.min(base.y + base.h, n.y + n.h) - Math.max(base.y, n.y);
      const below = xOverlap > Math.min(base.w, n.w) * 0.3 && n.y >= base.y + base.h - 2 && n.y - (base.y + base.h) <= 22;
      const right = yOverlap > Math.min(base.h, n.h) * 0.3 && n.x >= base.x + base.w - 2 && n.x - (base.x + base.w) <= 12;
      if (below || right) actions.set(n.idx, act);
    }
  }
}

const boardPlans = [];   // 板级构建快照（第一遍只构建不写盘，跨板镜像后统一注入）
for (const p of pages) {
  report.pages++;
  for (const b of p.boards) {
    if (!b.html || !b.json) continue;
    const jsonAbs = path.resolve(ROOT, b.json);
    const htmlAbs = path.resolve(ROOT, b.html);
    if (!fs.existsSync(jsonAbs) || !fs.existsSync(htmlAbs)) continue;
    report.boards++;
    let pg;
    try { pg = JSON.parse(fs.readFileSync(jsonAbs, 'utf8')).page; } catch { continue; }
    const W = pg.board.w, H = pg.board.h;
    const actions = new Map();
    const pageKey = p.dir.join('/') + '/' + p.name;

    // 产物 html 节点存在集（gen-html 已删 wLr 壳/✦ 角标/InteractionMarker 子树——json 里还在但产物无 div。
    // R5 几何命中须落到真实存在的视觉节点，否则注入静默落空：2026-09-17 实锤 zone 计划 1652 只注入 65）
    const rawHtml = fs.readFileSync(htmlAbs, 'utf8');
    const htmlIdxSet = new Set([...rawHtml.matchAll(/data-idx="(\d+)"/g)].map(m => +m[1]));

    // ---- R1 tab 栏 ----
    // 找底部 24x24 svg 指纹图标（y>0.78H），从 svg 节点沿父链向上找列容器（w 40~90 h 30~90 底部）绑
    const tabSvgs = pg.nodes.filter(n => n.svg && n.w >= 16 && n.w <= 32 && n.h >= 16 && n.h <= 32 && n.y > H * 0.78);
    const byIdx = new Map(pg.nodes.map(n => [n.idx, n]));
    for (const sv of tabSvgs) {
      const hit = TAB_TARGETS.find(t => String(sv.svg).includes(t.fp));
      if (!hit) continue;
      if (hit.edge && !(sv.x < W * 0.2 || sv.x > W * 0.78)) continue;   // 边列限定（人像防中间列孤例）
      if (hit.page && hit.page.pcid !== p.pcid) {
        // 列容器：父链最近的 w 40~90 h 30~90
        let c = byIdx.get(sv.parent), col = null;
        while (c) { if (c.w >= 40 && c.w <= 95 && c.h >= 30 && c.h <= 95 && c.y > H * 0.7) { col = c; break; } c = byIdx.get(c.parent); }
        const target = col || sv;
        const href = boardHref(hit.page, b.name, b.html);
        if (href && !actions.has(target.idx)) { actions.set(target.idx, { kind: 'tab', href }); report.byRule.tab++; }
      }
    }
    const hasTabbar = [...actions.values()].some(a => a.kind === 'tab');

    // ---- R2 返回箭头（无 tab 栏页面） ----
    // 排除 ✦ 交互角标（icon/link/mark svg 有 18~30px 形态会混进计划，但产物已随 gen-html 过滤删除——
    // 注入找不到 div 静默跳过，计划数与注入数差 9 的假阴性来源）
    if (!hasTabbar) {
      for (const n of pg.nodes) {
        if (!n.svg || n.w < 18 || n.w > 30 || n.h < 18 || n.h > 30) continue;
        if (/icon\/link\/mark/.test(String(n.svg))) continue;
        if (n.x < W * 0.12 && n.y > 40 && n.y < H * 0.13 && n.x + n.w < W * 0.25) {
          if (!actions.has(n.idx)) { actions.set(n.idx, { kind: 'back' }); report.byRule.back++; }
        }
      }
    }

    // ---- R3 弹窗取消 ----（hug 文本框实测 h≈20~24；w 下限 40 曾把「取消」(≈30px)/「OK」(≈20px) 窄 hug 框全卡掉——中文 cancel 一度 0 绑定，降到 16，词典整词匹配足够安全）
    for (const n of pg.nodes) {
      const t = String(n.text || '').trim();
      if (!CANCEL_WORDS.has(t)) continue;
      if (n.w >= 16 && n.w <= 300 && n.h >= 16 && n.h <= 72) {
        if (!actions.has(n.idx)) { actions.set(n.idx, { kind: 'cancel' }); report.byRule.cancel++; }
      }
    }
    // 注意：OK 词太泛，弹窗确认 OK 跳回父页也成立（关闭弹窗），保留；Confirm/Delete 不在词典

    // ---- R4 父子链接 ----
    const kids = childIndex.get(pageKey);
    if (kids) {
      for (const n of pg.nodes) {
        const t = String(n.text || '').trim();
        if (t.length < 2 || t.length > 24 || /\d{3,}/.test(t)) continue;
        const kp = kids.get(t);
        if (kp && kp.pcid !== p.pcid) {
          const href = boardHref(kp, b.name, b.html);
          if (href && !actions.has(n.idx)) { actions.set(n.idx, { kind: 'link', href }); report.byRule.link++; }
        }
      }
    }

    // ---- R5 热区档案映射 ----
    // 热区跨板复用（2026-09-17 两轮实锤）：①t=2 返回热区——中文/阿语板 goback=0 的根因是镜像三轮全靠
    // svg/img/bgi 指纹，纯 bg 底板+文本按钮永远配不上；t=2 与语言无关（history.back 无目标解析）、
    // 复制板布局保位 → 同页兄弟板热区直接对本板几何命中。②t=1 跳页热区——子代理全站排查实锤中文板
    // 「开始匹配」等主 CTA 10+ 板裸奔（热区只在 EN 板定义），t=1 借用目标走 zoneHref 接收板语言对齐
    // （能力本就具备），错位落空无害（宁缺毋滥不变）。去重 key=同位（x,y,w 取整）防重复计。
    const zoneList = [...(HOTZONES.zones[b.cid] || [])];
    const seenShare = new Set(zoneList.map(z => Math.round(z.x) + ',' + Math.round(z.y) + ',' + Math.round(z.w)));
    for (const sib of p.boards) {
      if (sib.cid === b.cid || !sib.html) continue;
      for (const z of (HOTZONES.zones[sib.cid] || [])) {
        const ok = (z.inters || []).some(i => i.trig === 'tap' && !i.url && (
          (i.t === 2 && !i.toPage && !i.toCanvas) || (i.t === 1 && (i.toCanvas || i.toPage))));
        if (!ok) continue;
        const key = Math.round(z.x) + ',' + Math.round(z.y) + ',' + Math.round(z.w);
        if (seenShare.has(key)) continue;
        seenShare.add(key); zoneList.push(z);
      }
    }
    // 几何命中：热区内**全部**合格候选同绑（2026-09-17 用户实锤：择优「取 z 最高」系统性选中
    // 角标/红点——它们永远浮在按钮右上最上层（7×14px 的「5」「99」全站错绑 20 处），按钮本体反而
    // 没绑。触发区域=整个热区语义：底板/图标/文字/角标都是交互组成部分，全绑点哪都跳）
    // 三个命中过滤修复（2026-09-17 子代理全站排查实锤）：
    //   a) 窄文本条放行：`‹` 返回键 json w=6.7 被 w<12 全排（注册/重置密码 3 板返回零绑定）
    //   b) 大热区蒙层通道：弹窗整体关闭热区（如 278×352）只压到大背景被 面积≤热区×3 排除——
    //      热区 ≥120×120 时盖住热区九成的大层=弹窗蒙层，点击关闭=返回语义，放行
    //   c) 重叠双向：节点大半在热区 **或** 热区大半被节点盖（原单向判定把「热区完全在按钮内」的
    //      反向包含算未命中——在线人员列表表格行 343×46.5 只 49.4% 落在 175×45 热区内被卡，三跳转裸奔）
    const collectHits = (z) => {
      const zx2 = z.x + z.w, zy2 = z.y + z.h;
      let covered = false; const hits = [];
      for (const n of pg.nodes) {
        if (!htmlIdxSet.has(n.idx)) continue;   // 产物无 div（已删壳/角标）——落到下层真节点
        if ((n.w < 12 || n.h < 12) && !(String(n.text || '').trim() && n.h >= 16 && n.w >= 4)) continue;
        const cx = n.x + n.w / 2, cy = n.y + n.h / 2;
        if (cx < z.x - 2 || cx > zx2 + 2 || cy < z.y - 2 || cy > zy2 + 2) continue;
        if (actions.has(n.idx)) { covered = true; break; }
        const ox = Math.max(0, Math.min(n.x + n.w, zx2) - Math.max(n.x, z.x));
        const oy = Math.max(0, Math.min(n.y + n.h, zy2) - Math.max(n.y, z.y));
        const ov = ox * oy;
        if (n.w * n.h > z.w * z.h * 3 && !(z.w >= 120 && z.h >= 120 && ov >= z.w * z.h * 0.9)) continue;   // 远大于热区的背景层（大热区蒙层通道除外）
        if (ov / (n.w * n.h) < 0.5 && ov / (z.w * z.h) < 0.5) continue;
        hits.push(n);
      }
      return { covered, hits };
    };
    for (const z of zoneList) {
      const taps = (z.inters || []).filter(i => i.trig === 'tap' && !i.url);
      if (!taps.length) continue;
      // t=2 无目标 tap = 墨刀「返回上一页」交互（2026-09-17 用户实锤「Cancel Matchmaking 无交互」：
      // 全站 308 条 t=2 全部无目标、位置不限于左上箭头——底部取消按钮/右侧关闭位 R2 语义救不到）
      const backTap = taps.find(i => i.t === 2 && !i.toPage && !i.toCanvas && !i.url);
      // 目标解析去重（toCanvas 优先；去重后 ≠1 = 缺失或多目标歧义，都不绑）
      const jumpTaps = taps.filter(i => i.t === 1 && (i.toCanvas || i.toPage));
      let tgt = null;
      if (jumpTaps.length) {
        const tgtMap = new Map();
        for (const tp of jumpTaps) {
          const tt = zoneHref(tp, b.name, b.html);
          if (tt) tgtMap.set(tt.html, tt);
        }
        if (tgtMap.size === 1) tgt = [...tgtMap.values()][0];
      }
      if (tgt && tgt.page.pcid === p.pcid) tgt = null;   // 跳自己（同热区 t=2 仍可生效）
      if (!tgt && !backTap) { report.r5skip = (report.r5skip||0) + 1; continue; }
      let { covered, hits } = collectHits(z);
      if (!covered && !hits.length) {
        // 坐标错位校准（子代理实锤：母版系板 hotzones y 与板内真值恒差 84px、x 逐像素一致——
        // 商城Shop 全系/搜索群组等，iPhoneX 状态栏帧偏移）。原位零命中才试平移（防误绑），命中同样过全部过滤
        for (const dy of [-84, 84]) {
          const r2 = collectHits({ ...z, y: z.y + dy });
          if (r2.covered) { covered = true; break; }
          if (r2.hits.length) { hits = r2.hits; break; }
        }
      }
      if (covered) { report.r5covered = (report.r5covered||0) + 1; continue; }
      if (hits.length) {
        if (tgt) {
          const href = path.relative(path.dirname(path.resolve(ROOT, b.html)), path.resolve(ROOT, tgt.html)).replace(/\\/g, '/');
          for (const n of hits) actions.set(n.idx, { kind: 'zone', href, tgtPage: tgt.page });   // tgtPage：跨板镜像时按接收板语言重算 href
          report.byRule.zone++;   // 计热区数（一热区多节点绑定，byRule 语义=热区覆盖数）
        } else {
          for (const n of hits) actions.set(n.idx, { kind: 'goback' });   // t=2 返回：与 cancel 同为 history.back，独立 kind 便于统计
          report.byRule.goback++;
        }
      } else report.r5nomatch = (report.r5nomatch||0) + 1;
    }

    // ---- R6 业务流词典（主 CTA 直绑，三语等值词典；先看页面上下文再匹配文本，不覆盖已有绑定） ----
    // 按钮形限制：文本 w≤240 h≤44（防跑马灯/正文长句误中——等值匹配已排除大多数，双保险）
    const eqBind = (words, target) => {
      for (const n of pg.nodes) {
        if (actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
        const t = String(n.text || '').trim();
        if (!words.includes(t) || n.w > 240 || n.h > 44) continue;
        if (target === 'back') actions.set(n.idx, { kind: 'flowback' });
        else {
          const href = boardHref(target, b.name, b.html);
          if (href) actions.set(n.idx, { kind: 'flow', href }); else continue;
        }
        report.byRule.flow++;
      }
    };
    const isGameHome = /对战首页/.test(p.name) && /game battle/.test(p.dir[0] || '');
    if (isGameHome) {
      eqBind(['Create room', '创建房间', 'إنشاء غرفة'], PAGE_GAME_ROOM);
      const qt = QUICK_TARGETS.find(q => q.game.test(p.name));
      if (qt) eqBind(['Quick', 'Battle', '开启对战', 'معركة'], qt.page);
      eqBind(['Main Event', '主活动'], PAGE_MAIN_EVENT);
      eqBind(['Crew War', '战队战争', 'حرب الفرق'], PAGE_CREW_WAR);
    }
    else if (/参赛悬浮窗/.test(p.name)) eqBind(['Create Room'], PAGE_GAME_ROOM);
    else if (/^充值/.test(p.name) || /充值Top Up/.test(p.name)) {
      // 底部主 CTA（y>0.85H）：EN「Top Up $9.99」/ 中「充值 $9.99」/ 阿 شحن+9.99+$ 拆三节点绑主词
      for (const n of pg.nodes) {
        if (actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
        const t = String(n.text || '').trim();
        if (!/^(Top Up|充值|شحن)/.test(t) || n.y < H * 0.85 || n.w > 240 || n.h > 44) continue;
        const href = boardHref(PAGE_CONFIRM_RECHARGE, b.name, b.html);
        if (href) { actions.set(n.idx, { kind: 'flow', href }); report.byRule.flow++; }
      }
    }
    else if (/VIP 中心·已购买/.test(p.name)) {
      // 续订主 CTA（y>0.88H）：EN Subscribe / 中 立即订阅 / 阿 اشترك بـ（拆节点绑主词）
      for (const n of pg.nodes) {
        if (actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
        const t = String(n.text || '').trim();
        if (!/^(Subscribe|立即订阅|اشترك)/.test(t) || n.y < H * 0.88 || n.w > 240 || n.h > 44) continue;
        const href = boardHref(PAGE_PAYMENT_CONFIRM, b.name, b.html);
        if (href) { actions.set(n.idx, { kind: 'flow', href }); report.byRule.flow++; }
      }
    }
    else if (/打开游戏选择/.test(p.name)) eqBind(['Create', '创建', 'إنشاء'], PAGE_LAUNCH_GROUP_GAME);
    else if (/新手引导/.test(p.name)) eqBind(['Close & Start Playing', '关闭并进入游戏', 'إغلاق وبدء اللعب'], 'back');
    else if (/告知领导层/.test(p.name)) {
      // 发消息按钮（EN Send Message/带(30)字数状态、中 发消息(30s)、阿 إرسال رسالة( 拆节点）→ 发送后关闭弹窗
      for (const n of pg.nodes) {
        if (actions.has(n.idx) || !htmlIdxSet.has(n.idx)) continue;
        const t = String(n.text || '').trim();
        if (!/^(Send Message|发消息|إرسال رسالة)/.test(t) || n.w > 240 || n.h > 44) continue;
        actions.set(n.idx, { kind: 'flowback' }); report.byRule.flow++;
      }
    }
    else if (/玩家游戏同时升级/.test(p.name)) eqBind(['Claim Rewards'], 'back');
    else if (/第[一二三]名|1st Place|2nd–4th Place|Victory|Defeat|胜利|失败/.test(p.name)) {
      // 结算页 Play Again/继续匹配 → 父页面（匹配中，重新开始匹配）；父页=本页 dir 最后一级目录名
      const parent = byPath.get(p.dir.slice(0, -1).join('/') + '/' + p.dir[p.dir.length - 1]);
      if (parent && parent.pcid !== p.pcid) eqBind(['Play Again', '继续匹配'], parent);
    }

    // ---- 板内邻域扩散+图标-文字组队 ----
    propagate(actions, pg, byIdx, htmlIdxSet);

    boardPlans.push({ p, b, pg, byIdx, htmlIdxSet, rawHtml, htmlAbs, actions, pageKey });
  }
}

// ---- 同页跨板镜像（2026-09-17 用户实锤「中文板 Quests 按钮点不动」的根因：墨刀热区只在当初定义交互
// 的语言板（通常 English）上有，复制出的中文/阿语板 zones[板cid] 无数据 → R5 整板零绑定）----
// 基准板（同页 zone 绑定节点数最多）的 zone 类 action，经 **svg 指纹锚点**配对抄到同页其他语言板：
// 复制板 svg 源码逐字一致、尺寸 ±3px、位置弱校验（dy≤100/dx≤120——复制板布局有平移，位置只能弱校验），
// 同指纹多候选取 y 最近。抄完跑 propagate（邻域扩散+文字组队），文字/角标自动跟上——不同语言文字
// 无法字面配对，靠「紧挨锚点图标」的组队关系传导。
// href 直接抄安全：同页所有板同目录（batch.mjs 命名规则），相对路径一致。
{
  const byPage = new Map();
  for (const bp of boardPlans) {
    if (!byPage.has(bp.pageKey)) byPage.set(bp.pageKey, []);
    byPage.get(bp.pageKey).push(bp);
  }
  for (const [, list] of byPage) {
    if (list.length < 2) continue;
    // zone+goback 都算交互锚点（纯 t=2 板也能当基准板；goback 无 tgtPage，localize 原样返回）
    const zoneCnt = (bp) => [...bp.actions.values()].filter(a => a.kind === 'zone' || a.kind === 'goback').length;
    const base = [...list].sort((x, y) => zoneCnt(y) - zoneCnt(x))[0];
    if (!zoneCnt(base)) continue;
    // 基准板 zone 锚点（画布内节点才当锚点/才接收）。图标指纹 = svg normalize / bgi / img 切图 URL——
    // 同页复制板同源切图 URL 逐字一致；跨形态（EN 板 svg ↔ 阿语板 img）指纹互斥靠第三轮尺寸序配对
    const inCanvas = (n, W) => n.x > -20 && n.x + n.w < W + 20 && n.y > -20;
    const fpOf = (n) => n.svg ? String(n.svg).replace(/\s+/g, '')
      : (n.img ? String(n.img) : (n.bgi ? String(n.bgi) : null));
    const fpIdx = new Map();
    const anchors = [];
    for (const [idx, act] of base.actions) {
      if (act.kind !== 'zone' && act.kind !== 'goback') continue;
      const n = base.byIdx.get(idx);
      if (!n || !inCanvas(n, base.pg.board.w)) continue;
      anchors.push({ n, act });
      const fp = fpOf(n);
      if (fp) {
        if (!fpIdx.has(fp)) fpIdx.set(fp, []);
        fpIdx.get(fp).push({ n, act });
      }
    }
    for (const bp of list) {
      if (bp === base) continue;
      const W = bp.pg.board.w;
      let mirrored = 0;
      // 镜像 action 按接收板语言重算 href（锚点的 href 是基准板视角的语言对齐成品——直接抄会把
      // 中文板跳 English 板；tgtPage 存目标页引用，boardHref 以接收板名重新对齐）
      const localize = (act) => {
        if (!act.tgtPage) return act;
        const h = boardHref(act.tgtPage, bp.b.name, bp.b.html);
        return h ? { kind: act.kind, href: h, tgtPage: act.tgtPage } : act;
      };
      const consumed = new Set();   // 基准板锚点已被占用（防重复配）
      const pairs = [];             // 已成立配对（侧位投票用：统计本板是否 RTL 镜像）
      // 第一轮：同指纹（svg↔svg / img↔img）+ 直接坐标（LTR 复制板布局基本保位，dy≤100/dx≤120，取 y 最近）
      const remain = [];
      for (const n of bp.pg.nodes) {
        if (bp.actions.has(n.idx) || !fpOf(n) || !bp.htmlIdxSet.has(n.idx) || !inCanvas(n, W)) continue;
        const cands = fpIdx.get(fpOf(n)) || [];
        let best = null;
        for (const c of cands) {
          if (Math.abs(c.n.w - n.w) > 3 || Math.abs(c.n.h - n.h) > 3) continue;
          if (Math.abs(c.n.y - n.y) > 100 || Math.abs(c.n.x - n.x) > 120) continue;
          if (!best || Math.abs(c.n.y - n.y) < best.dy) best = { c, dy: Math.abs(c.n.y - n.y) };
        }
        if (best) { bp.actions.set(n.idx, localize(best.c.act)); consumed.add(best.c.n.idx); mirrored++; pairs.push({ n, a: best.c.n }); }
        else remain.push(n);
      }
      // 第二轮：RTL 镜像板 x 翻转重排（直接坐标永远对不上——Ludo 阿语板图标 x240 vs EN x20）：
      // 剩余同指纹未消耗候选双方按 y 排序 zip，dy≤80（y 方向布局保序；x 完全不校验）
      const remainByFp = new Map();
      for (const n of remain) {
        const fp = fpOf(n);
        if (!remainByFp.has(fp)) remainByFp.set(fp, []);
        remainByFp.get(fp).push(n);
      }
      for (const [fp, ns] of remainByFp) {
        const cands = (fpIdx.get(fp) || []).filter(c => !consumed.has(c.n.idx))
          .sort((a, b2) => a.n.y - b2.n.y);
        const sorted = [...ns].sort((a, b2) => a.y - b2.y);
        for (let i = 0; i < sorted.length && i < cands.length; i++) {
          const c = cands[i], n = sorted[i];
          if (Math.abs(c.n.w - n.w) > 3 || Math.abs(c.n.h - n.h) > 3) continue;
          if (Math.abs(c.n.y - n.y) > 80) continue;
          bp.actions.set(n.idx, localize(c.act)); consumed.add(c.n.idx); mirrored++; pairs.push({ n, a: c.n });
        }
      }
      // 第三轮：跨形态兜底（svg 板 ↔ img/bgi 板指纹互斥全落空——Ludo 阿语板图标全 img、EN 板全 svg）：
      // 图标形态节点（无文本、w/h∈[16,90]、svg/img/bgi 任一非空）× 未消耗锚点（w/h≤120）：
      // 同尺寸±3、dy≤40 取最近。**y 平手歧义挂起**（EN 板 Quests/Rankings 同 24×24 同 y210，贪心必抢错
      // ——错绑比不绑糟，实测阿语板任务图标曾配到排行榜锚点跳错页），待侧位投票后重试
      const pool = anchors.filter(a => !consumed.has(a.n.idx) && a.n.w <= 120 && a.n.h <= 120);
      const remain3 = remain.filter(n => !bp.actions.has(n.idx) && !String(n.text || '').trim()
        && n.w >= 16 && n.w <= 90 && n.h >= 16 && n.h <= 90 && (n.svg || n.img || n.bgi));
      const amb = [];   // 歧义挂起：{n, cands}
      for (const n of remain3) {
        const cands = pool.filter(a => !consumed.has(a.n.idx)
          && Math.abs(a.n.w - n.w) <= 3 && Math.abs(a.n.h - n.h) <= 3 && Math.abs(a.n.y - n.y) <= 40)
          .sort((a, b2) => Math.abs(a.n.y - n.y) - Math.abs(b2.n.y - n.y));
        if (process.env.MIRROR_DEBUG === '2') console.error(`  [r3] idx${n.idx}(${Math.round(n.w)}x${Math.round(n.h)}@y${Math.round(n.y)}) cands=${cands.map(c => `idx${c.n.idx}(y${Math.round(c.n.y)},dy${Math.round(Math.abs(c.n.y - n.y))})`).join(',')}`);
        if (!cands.length) continue;
        if (cands.length > 1 && Math.abs(cands[1].n.y - cands[0].n.y) < 4) { amb.push({ n, cands }); continue; }   // 歧义挂起
        bp.actions.set(n.idx, localize(cands[0].act)); consumed.add(cands[0].n.idx); mirrored++; pairs.push({ n, a: cands[0].n });
      }
      // 歧义重试（RTL 镜像板定向）：已成立配对统计明确偏侧样本的翻转率，全反侧 → 判定镜像；或板名
      // 是 RTL 语言（阿语等——双套 tab 叠放污染下几何投票常无样本，语言判定兜底）。歧义节点改选
      // **反侧**锚点：Ludo 阿语板 idx36 y208 与 EN Quests(左)/Rankings(右) 同 y 平手，反侧假设锁定 Quests
      if (amb.length) {
        const side = (nn) => (nn.x + nn.w / 2 < W / 2) ? 'L' : 'R';
        const offMid = (nn) => Math.abs(nn.x + nn.w / 2 - W / 2) >= W * 0.15;   // 明确偏侧（中列/居中元素噪声大）
        const strong = pairs.filter(p => offMid(p.a) && offMid(p.n));
        const flips = strong.filter(p => side(p.a) !== side(p.n)).length;
        const byVote = strong.length >= 2 && flips === strong.length;
        const byLang = /[؀-ۿ]/.test(bp.b.name);
        if (process.env.MIRROR_DEBUG) console.error(`[mirror] ${bp.pageKey.split('/').pop()} / ${bp.b.name}: pairs=${pairs.length} strong=${strong.length} flips=${flips} amb=${amb.length} byVote=${byVote} byLang=${byLang}`);
        if (byVote || byLang) {
          for (const { n, cands } of amb) {
            const want = side(n) === 'L' ? 'R' : 'L';
            const pick = cands.find(c => !consumed.has(c.n.idx) && side(c.n) === want);
            if (pick) { bp.actions.set(n.idx, localize(pick.act)); consumed.add(pick.n.idx); mirrored++; }
          }
        }
      }
      if (mirrored) {
        propagate(bp.actions, bp.pg, bp.byIdx, bp.htmlIdxSet);
        report.byRule.mirror += mirrored;
      }
    }
  }
}

// ---- 统一写盘 ----
for (const bp of boardPlans) {
  if (!bp.actions.size) continue;
  const res = inject(bp.rawHtml, bp.actions);
  const inj = typeof res === 'string' ? 0 : res.injected;
  if (!dry && inj) fs.writeFileSync(bp.htmlAbs, res.html);
  report.bound += inj;
  report.details.push({ page: bp.pageKey, board: bp.b.name, injected: inj, acts: [...new Set([...bp.actions.values()].map(a => a.kind))].join(',') });
}

if (tabTargetsMissing.length) console.error('⚠ tab 目标页缺失: ' + tabTargetsMissing.join(' | '));
console.log(JSON.stringify({ ok: true, dry, pages: report.pages, boards: report.boards, bound: report.bound, byRule: report.byRule }));
fs.writeFileSync(path.join(ROOT, '..', '.claude-tmp', 'interactions-report.json'), JSON.stringify(report, null, 1));
