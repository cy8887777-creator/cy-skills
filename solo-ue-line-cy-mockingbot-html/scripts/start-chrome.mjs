// start-chrome.mjs —— 起独立 CDP headless Chrome 加载墨刀导出包
// 用法：node start-chrome.mjs <墨刀包目录(含index.html)> [起始端口=9225]
// 输出 JSON（stdout 最后一行）：{ port, pid, infoFile }——后续脚本用 port 连接，结束时用 stop-chrome.mjs 收
// 规则：
//   - 自动跳过被占用端口（绝不复用别的会话实例，防打架）
//   - 独立 user-data-dir 隔离；禁止 taskkill /IM chrome.exe（会杀用户所有窗口），只按 PID 杀
//   - 大窗口 1920x2400（窗口过小会导致画板缩放退化 screenW<80，提取坐标失真）
import { spawn, exec } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';
import { sleep, connect, waitUntil } from './cdp.mjs';

const args = process.argv.slice(2);
const pkgDir = args[0];
if (!pkgDir || !fs.existsSync(path.join(pkgDir, 'index.html'))) {
  console.error('用法: node start-chrome.mjs <墨刀包目录(含index.html)> [起始端口=9225]');
  process.exit(1);
}
const basePort = +(args[1] || 9225);   // 从 9225 起探测空闲端口，占用则 +1 错开

function findChrome() {
  const cands = [
    'C:/Program Files/Google/Chrome/Application/chrome.exe',
    'C:/Program Files (x86)/Google/Chrome/Application/chrome.exe',
    path.join(process.env.LOCALAPPDATA || '', 'Google/Chrome/Application/chrome.exe'),
  ];
  for (const c of cands) if (c && fs.existsSync(c)) return c;
  throw new Error('未找到 chrome.exe（请确认 Chrome 安装路径）');
}

async function portFree(p) {
  try { await fetch(`http://127.0.0.1:${p}/json/version`, { signal: AbortSignal.timeout(500) }); return false; }
  catch { return true; }
}

let port = basePort;
for (let i = 0; i < 20; i++) { if (await portFree(port)) break; port++; }

const url = encodeURI('file:///' + path.resolve(pkgDir, 'index.html').replace(/\\/g, '/'));
const udd = path.join(os.tmpdir(), `mth-chrome-${port}`);
const child = spawn(findChrome(), [
  '--headless=new', '--disable-gpu', '--no-sandbox',
  '--allow-file-access-from-files',
  `--remote-debugging-port=${port}`,
  `--user-data-dir=${udd}`,
  '--window-size=1920,2400',
  url,
], { stdio: 'ignore', detached: true });   // detached+unref：chrome 脱离 node 进程树——否则 node 退出（process.exit）会把 chrome 连带杀掉
child.unref();

// 等 SPA 就绪：调试端口可达 + 侧边栏页面树挂出（墨刀主数据包大，要给足时间）
let ready = false, lastErr = '';
for (let i = 0; i < 90 && !ready; i++) {
  await sleep(2000);
  try {
    const c = await connect(port);
    await waitUntil(c.evalJS, `document.querySelectorAll('.rn-list-item[data-cid]').length > 0`, { timeout: 5000, label: 'sidebar tree' });
    c.close(); ready = true;
  } catch (e) { lastErr = e.message; }
}
if (!ready) {
  try { exec(`taskkill /PID ${child.pid} /T /F`); } catch {}
  console.error('墨刀 SPA 未在 180 秒内就绪：' + lastErr);
  process.exit(1);
}

// 记录实例信息（stop-chrome.mjs 消费）
const infoFile = path.join(os.tmpdir(), `mth-chrome-${port}.json`);
fs.writeFileSync(infoFile, JSON.stringify({ port, pid: child.pid, udd, startedAt: new Date().toISOString() }));
console.log(JSON.stringify({ ok: true, port, pid: child.pid, infoFile }));
process.exit(0);   // 必须：spawn 的 chrome 子进程挂着事件循环，不显式退出则 && 串行的后续命令永远等不到
