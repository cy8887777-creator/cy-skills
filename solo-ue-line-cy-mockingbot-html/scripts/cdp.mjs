// cdp.mjs —— CDP 公共模块：连接调试页面 / evalJS / sleep
// 所有脚本共用，保持连接方式一致（Node 22+ 全局 WebSocket）
export function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

export async function connect(port, urlRe = /index\.html/) {
  const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const page = list.find(t => t.type === 'page' && urlRe.test(t.url || '')) || list.find(t => t.type === 'page');
  if (!page) throw new Error(`端口 ${port} 无可调试页面（墨刀 index.html 是否已加载？）`);
  const ws = new WebSocket(page.webSocketDebuggerUrl);
  let msgId = 0; const pending = new Map();
  ws.addEventListener('message', ev => {
    const m = JSON.parse(ev.data);
    if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); }
  });
  const send = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++msgId; pending.set(id, resolve);
    ws.send(JSON.stringify({ id, method, params }));
    setTimeout(() => { if (pending.has(id)) { pending.delete(id); reject(new Error('timeout ' + method)); } }, 120000);
  });
  await new Promise((res, rej) => {
    ws.addEventListener('open', res, { once: true });
    ws.addEventListener('error', rej, { once: true });
  });
  async function evalJS(expr) {
    const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true });
    if (r.exceptionDetails) {
      throw new Error((r.exceptionDetails.exception || {}).description || 'eval error');
    }
    return r.result.result.value;
  }
  return { ws, send, evalJS, close: () => ws.close() };
}

// 轮询直到条件为真（evalJS 返回 truthy），超时抛错
export async function waitUntil(evalJS, expr, { timeout = 60000, interval = 1000, label = 'condition' } = {}) {
  const t0 = Date.now();
  while (Date.now() - t0 < timeout) {
    if (await evalJS(expr)) return true;
    await sleep(interval);
  }
  throw new Error(`等待超时: ${label}`);
}

// detectModel —— 墨刀查看器代际探测（2026-10-20 双格式实锤，batch/extract-board/diagnose/read-hotzones 共用）
//   'legacy'  = .tree-node.rResCanvas[rc…]（gzip 快照格式导出，画板累积挂载）
//   'pcanvas' = .pcanvas[data-cid=页面cid]（PB=v1 明文 JSON 导出，pcanvas 三区 header/content/footer，
//               激活者带 .active，页面↔画布 1:1，cid 即页面 cid）
//   'unknown' = 两者都没探到（包异常/未加载完，调用方报错退出）
// 混合代际（2026-10-23 飞燕包实锤）：新查看器 DOM + gzip 数据——初始页画板挂 .pcanvas 但 data-cid 是 rc 画布段
// （非页面 cid），点击切换的其他页画板全走 .tree-node.rResCanvas 单槽换装。这种包必须走 legacy 管线
// （pcanvas 分支按页面 cid 等画布永远 MOUNTING 超时 → 全部误判空页面）。判据：pcanvas 的 data-cid 是
// rc 纯段 = 混合包 → legacy；真 PB=v1 的 pcanvas cid 即页面 cid（rbp…）→ pcanvas。
export async function detectModel(evalJS) {
  return await evalJS(`(() => {
    const pc = document.querySelector('.pcanvas[data-cid]');
    if (pc) {
      const cid = pc.getAttribute('data-cid') || '';
      if (/^rc[A-Za-z0-9]+$/.test(cid)) return 'legacy';
      return 'pcanvas';
    }
    if (document.querySelector('.tree-node.rResCanvas')) return 'legacy';
    return 'unknown';
  })()`);
}
