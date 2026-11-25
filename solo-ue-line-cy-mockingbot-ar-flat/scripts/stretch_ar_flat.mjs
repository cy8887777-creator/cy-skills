// stretch_ar_flat.mjs — 阿语平铺版「自动拉宽」后处理（gen_ar_flat.mjs 之后可选执行）
//
// 解决问题：墨刀组件按英文短文案定宽，阿语译文变长后在固定宽度内被迫折行——
//   其中大部分周围其实有空间，把组件拉宽即可恢复单行，无需精简译文。
//
// 判定逻辑（2026-09-02 群组模块 219 页实测提炼）：
//   1) 找「真实换行」的阿语文本叶子（Range 行矩形数 ≥2 依据的盒高/行高比 1.6~3.6 预筛 + nowrap 克隆实测需求宽）
//   2) 组件级试扩：文字盒 + 紧贴胶囊(最近带背景祖先且宽 ≤ needW+30) 左/右/居中三向同扩
//   3) 碰撞判据「只认新压到」：扩后与新 bbox 相交、且与原 bbox 不相交的叶子才是障碍
//      （文字原本就叠着的列表底板/背景层不算障碍——这是避免大面积误判的关键）
//   4) 拉宽成功 → 行盒垂直居中收回单行高（避免下半截空白）
//   5) 拉宽失败 → 字号 -1px/-2px 重测兜底（fs≥12），仍不行保持换行（描述句天然放不下一行，自动保留多行）
//
// 用法：
//   node scripts/stretch_ar_flat.mjs --file <ar_flat.html> [--port 9223]
// 前置：Chrome 调试端口已启动（与提取阶段同一实例即可）：
//   chrome --headless=new --remote-debugging-port=9223 --user-data-dir=<隔离目录> <file://...>
//
// 效果（群组模块实测）：450 处真实 2 行换行 → 0；3 行原版单行项 44 处恢复；
//   剩余多行均为描述/占位/原版多行设计。处理后自动备份原文件为 <file>.pre-stretch.bak。

import fs from 'fs';
import path from 'path';

// ---- 参数 ----
const args = process.argv.slice(2);
const getArg = (k, d) => { const i = args.indexOf('--' + k); return i >= 0 && args[i + 1] ? args[i + 1] : d; };
const FILE = getArg('file', 'ar_flat.html');
const PORT = getArg('port', '9223');
const fileAbs = path.resolve(FILE);
const fileUrl = 'file:///' + encodeURI(fileAbs.replace(/\\/g, '/')).replace(/#/g, '%23').replace(/\?/g, '%3F');

// ---- CDP ----
let page;
try {
  const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
  page = targets.find(t => t.type === 'page');
} catch {
  console.error(`✗ 端口 ${PORT} 无 Chrome 调试实例。请先启动：`);
  console.error('  chrome --headless=new --remote-debugging-port=' + PORT + ' --user-data-dir=<隔离目录> "<file://原型index.html>"');
  process.exit(1);
}
const ws = new WebSocket(page.webSocketDebuggerUrl);
let msgId = 0; const pending = new Map();
ws.addEventListener('message', ev => { const m = JSON.parse(ev.data); if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } });
function send(method, params = {}) {
  return new Promise((res, rej) => {
    const id = ++msgId; pending.set(id, res);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); rej(new Error('timeout ' + method)); } }, 300000);
  });
}
await new Promise(r => ws.addEventListener('open', r, { once: true }));

// ---- 备份 ----
const bak = fileAbs + '.pre-stretch.bak';
fs.copyFileSync(fileAbs, bak);

await send('Page.navigate', { url: fileUrl });
await new Promise(r => setTimeout(r, 9000));

const res = await send('Runtime.evaluate', {
  expression: `(() => {
    const stat = { stretch: 0, shrink: 0, remain: 0, samples: [] };
    const isPlace = t => { const s = t.replace(/[\\s]+/g, ' '); return /(\\S+) \\1 \\1/.test(s) || /\\.\\.$/.test(t); };
    for (const screen of document.querySelectorAll('.screen')) {
      const sr = screen.getBoundingClientRect();
      const leavesOf = () => { const a = []; for (const el of screen.querySelectorAll('*')) if (!el.children.length) a.push(el); return a; };
      let leaves = leavesOf().map(el => { const b = el.getBoundingClientRect(); return { el, l: b.left, r: b.right, t: b.top, b: b.bottom }; }).filter(x => (x.r - x.l) >= 2 && (x.b - x.t) >= 2);
      for (const el of screen.querySelectorAll('*')) {
        if (el.children.length) continue;
        const txt = (el.textContent || '').trim();
        if (!txt || !/[\\u0600-\\u06FF]/.test(txt) || isPlace(txt)) continue;
        const cs = getComputedStyle(el);
        const r0 = el.getBoundingClientRect();
        const lh = parseFloat(cs.lineHeight) || parseFloat(cs.fontSize) * 1.4;
        const lines = Math.round(r0.height / lh * 10) / 10;
        if (lines < 1.6 || lines > 3.6) continue;   // 2~3 行换行项（4+ 行为多行设计块）
        const measure = () => {
          const c = el.cloneNode(true);
          c.style.cssText += ';white-space:nowrap;position:absolute;visibility:hidden;width:auto;height:auto;';
          el.parentElement.appendChild(c);
          const w = Math.ceil(c.getBoundingClientRect().width) + 2;
          c.remove(); return w;
        };
        const needW = measure();
        if (needW <= r0.width + 3) continue;         // 其实单行放得下（盒高 min-height 假象）
        const anc = new Set();
        for (let n = el.parentElement; n && n !== screen.parentElement; n = n.parentElement) anc.add(n);
        anc.add(el);
        let vc = null;                               // 紧贴胶囊：最近带背景祖先且不大于 needW+30
        for (let n = el.parentElement; n && n !== screen.parentElement; n = n.parentElement) {
          const s = getComputedStyle(n);
          if (s.backgroundColor !== 'rgba(0, 0, 0, 0)' || (s.borderWidth && s.borderWidth !== '0px')) {
            if (n.getBoundingClientRect().width <= needW + 30) vc = n;
            break;                                  // 更外层大面板不跟随扩（列表底板/弹窗背景本就够大）
          }
        }
        const hit = (L, R, T, B) => {                // 只认「新压到」：原本就叠着的不算障碍
          const cur = leaves.map(x => { const b = x.el.getBoundingClientRect(); return { el: x.el, l: b.left, r: b.right, t: b.top, b: b.bottom }; });
          for (const x of cur) {
            if (anc.has(x.el) || x.el.contains(el)) continue;
            const nowHit = L < x.r - 2 && R > x.l + 2 && T < x.b - 2 && B > x.t + 2;
            if (!nowHit) continue;
            const wasHit = r0.left < x.r - 2 && r0.right > x.l + 2 && r0.top < x.b - 2 && r0.bottom > x.t + 2;
            if (wasHit) continue;
            return true;
          }
          return false;
        };
        const dW = needW - r0.width;
        const cands = [
          { name: 'L', dl: -dW, dr: 0 },
          { name: 'R', dl: 0, dr: dW },
          { name: 'C', dl: -dW / 2, dr: dW / 2 },
        ];
        let ok = null;
        for (const cd of cands) {
          const eL = r0.left + cd.dl, eR = r0.right + cd.dr;
          if (eL < sr.left + 1 || eR > sr.right - 1) continue;
          if (hit(eL, eR, r0.top, r0.bottom)) continue;
          if (vc) {
            const vb = vc.getBoundingClientRect();
            const vL = vb.left + cd.dl, vR = vb.right + cd.dr;
            if (vL < sr.left + 1 || vR > sr.right - 1) continue;
            if (hit(vL, vR, vb.top, vb.bottom)) continue;
          }
          ok = cd; break;
        }
        if (ok) {
          if (vc) {
            const vb = vc.getBoundingClientRect();
            const vl0 = parseFloat(vc.style.left) || 0;
            vc.style.width = Math.round(vb.width + (ok.dr - ok.dl)) + 'px';
            if (ok.dl) vc.style.left = (vl0 + ok.dl).toFixed(1) + 'px';
          }
          el.style.width = needW + 'px';
          if (ok.dl) el.style.left = ((parseFloat(el.style.left) || 0) + ok.dl) + 'px';
          if (r0.height > lh * 1.5) {                // 行盒垂直居中收回单行高
            const curTop = parseFloat(el.style.top) || 0;
            el.style.height = Math.round(lh) + 'px';
            el.style.top = (curTop + (r0.height - lh) / 2).toFixed(1) + 'px';
          }
          stat.stretch++;
          if (stat.samples.length < 12) stat.samples.push({ t: txt.slice(0, 18), dir: ok.name, w: Math.round(r0.width), nw: needW, vc: !!vc });
          leaves = leavesOf().map(el => { const b = el.getBoundingClientRect(); return { el, l: b.left, r: b.right, t: b.top, b: b.bottom }; }).filter(x => (x.r - x.l) >= 2 && (x.b - x.t) >= 2);
          continue;
        }
        const fs0 = parseFloat(cs.fontSize);          // 缩字号兜底：-1px，仍不行 -2px（fs≥12），都不行还原
        let shrunk = 0;
        for (const drop of [1, 2]) {
          if (fs0 - drop < 12) break;
          el.style.fontSize = (fs0 - drop) + 'px';
          if (measure() <= r0.width + 3) { shrunk = drop; break; }
        }
        if (shrunk) { stat.shrink++; if (stat.samples.length < 12) stat.samples.push({ t: txt.slice(0, 18), shrink: shrunk }); }
        else { el.style.fontSize = ''; stat.remain++; }
      }
    }
    return stat;
  })()`, returnByValue: true });

if (res.result.exceptionDetails) {
  console.error('✗ 执行异常:', JSON.stringify(res.result.exceptionDetails).slice(0, 500));
  console.error('（原文件未动，备份在', bak + '）');
  process.exit(1);
}
console.log('拉宽统计 → 拉宽', res.result.result.value.stretch, '· 缩字号', res.result.result.value.shrink, '· 保持多行', res.result.result.value.remain);
console.log('样例:', JSON.stringify(res.result.result.value.samples.slice(0, 6)));

const html = await send('Runtime.evaluate', { expression: `'<!DOCTYPE html>\\n' + document.documentElement.outerHTML`, returnByValue: true });
fs.writeFileSync(fileAbs, html.result.result.value);
console.log(`✓ 已保存 ${FILE}（${(fs.statSync(fileAbs).size / 1024 / 1024).toFixed(2)} MB），处理前备份：${path.basename(bak)}`);
ws.close(); process.exit(0);
