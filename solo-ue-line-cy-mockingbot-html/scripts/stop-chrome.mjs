// stop-chrome.mjs —— 按 PID 收掉技能自己起的 Chrome（绝不 taskkill /IM chrome.exe）
// 用法：node stop-chrome.mjs <infoFile 或 port>
import { exec } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';
import os from 'node:os';

const a = process.argv[2];
if (!a) { console.error('用法: node stop-chrome.mjs <infoFile路径 或 端口>'); process.exit(1); }

let infoFile = fs.existsSync(a) ? a : path.join(os.tmpdir(), `mth-chrome-${a}.json`);
if (!fs.existsSync(infoFile)) { console.error('找不到实例信息文件: ' + infoFile); process.exit(1); }

const { pid } = JSON.parse(fs.readFileSync(infoFile, 'utf8'));
exec(`taskkill /PID ${pid} /T /F`, (err) => {
  console.log(err ? `结束失败（可能已退出）: ${err.message}` : `已停止 pid=${pid}`);
  try { fs.unlinkSync(infoFile); } catch {}
});
