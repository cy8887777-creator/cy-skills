// verify-tpl.mjs —— 断言骨架：DOM 数字断言（唯一测试手段；禁用视觉模型做测试）
// 用法: 复制改名 verify-<页>.mjs，在「断言区」填断言，跑 node verify-xxx.mjs <page.html> [port]
// 铁律:
//  1. 任何 rect 断言必须减 stage 原点（body 有展示壳 padding，视口绝对坐标会整体漂移 24/48px）
//  2. 视口 423×900（>画布 375+两侧 padding），小了 stage 被 flex 压缩、全部断言作废
//  3. 动画断言双采样：挂上 animation ≠ 在滚，两次采样 transform 差值对得上理论速度才算真动
//  4. 每轮改版后断言只增不减（旧断言是防回归资产）
//  5. 断言失败 exit 1，批处理可感知
import { pathToFileURL } from 'node:url';

const [page, portArg] = process.argv.slice(2);
if (!page) { console.error('用法: node verify-<页>.mjs <page.html> [port]'); process.exit(2); }
const PORT = +(portArg || 9224);
const url = pathToFileURL(page.replace(/\\/g, '/')).href;

const targets = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
const ws = new WebSocket(targets.find(x => x.type === 'page').webSocketDebuggerUrl);
await new Promise(r => ws.addEventListener('open', r, { once: true }));
let id = 0; const pend = new Map();
ws.addEventListener('message', ev => { const m = JSON.parse(ev.data); if (m.id && pend.has(m.id)) { pend.get(m.id)(m); pend.delete(m.id); } });
const send = (method, params = {}) => new Promise((resolve, reject) => {
  const i = ++id; pend.set(i, resolve); ws.send(JSON.stringify({ id: i, method, params }));
  setTimeout(() => { if (pend.has(i)) { pend.delete(i); reject(new Error('timeout ' + method)); } }, 20000);
});
await send('Page.enable');
await send('Emulation.setDeviceMetricsOverride', { width: 423, height: 900, deviceScaleFactor: 1, mobile: false });
await send('Page.navigate', { url });
await new Promise(r => setTimeout(r, 2000));

// ev(expr): expression 里 return 的值必须可 JSON 序列化（纯数据）
const ev = async (expr) => JSON.parse((await send('Runtime.evaluate', { returnByValue: true, expression: expr })).result.result.value);
// 取层盒（stage 相对坐标，rect 断言一律用它算，禁止视口绝对坐标）
const boxOf = async i => ev(`JSON.stringify((()=>{const s=document.querySelector('.stage').getBoundingClientRect();
  const d=document.querySelector('[data-idx="${i}"]'); if(!d) return null;
  const b=d.getBoundingClientRect(); return {x:+(b.x-s.x).toFixed(1),y:+(b.y-s.y).toFixed(1),w:+b.width.toFixed(1),h:+b.height.toFixed(1)}})())`);

// ---- 断言区 ----
const errs = [];
const assert = (name, cond, detail) => { console.log((cond ? 'PASS ' : 'FAIL ') + name + (detail ? ' | ' + detail : '')); if (!cond) errs.push(name); };

// 示例（照抄改层号/期望值）：
const imgAll = await ev("JSON.stringify([...document.querySelectorAll('[data-idx] img')].every(im=>im.complete&&im.naturalWidth>0))");
assert('img 全部加载', imgAll === true);
// const b311 = await boxOf('311');
// assert('Battle 按钮高 56', b311 && b311.h === 56, JSON.stringify(b311));

// TODO: 本页断言写这里（每轮改版新增的布局全部固化成断言）

console.log(errs.length ? `\n✗ ${errs.length} 项失败: ${errs.join(', ')}` : '\n全部 PASS');
ws.close(); process.exit(errs.length ? 1 : 0);
