// read-data.mjs —— 墨刀数据包 → cid→名称 全量字典（data-map.json）
// 双格式自动分支（2026-10-20 实锤，蓝骑同城-师傅端App s1 包 6064 条回归通过）：
//   旧格式：window[<key>][<key>] = [[id,id2,"H4sIA…gzip+base64 快照"],…]（首块全量快照，
//           行式 `cid <修饰>\t{…,"N":"名称",…}`）
//   新格式（PB=v1）：window["hzv3"]["psol"] 明文 JSON——screens/stateList/itemList 直带名称；
//           源数据无 rc 画板 cid（画板 cid 由查看器运行时生成，板名缺失时 batch 兜底 cid）；
//           页面树名走 data.1.js pbj.screen_metas（含 parent_cid/position/画布宽高）
// 输出 schema 两分支一致：{ meta: {tool, source, generatedAt, entries}, names: {cid: 名称} }
import fs from 'node:fs';
import path from 'node:path';
import zlib from 'node:zlib';

const [, , PKG, OUT] = process.argv;
if (!PKG || !OUT) { console.error('用法: node read-data.mjs <墨刀包目录> <out.data-map.json>'); process.exit(1); }

const extraFiles = ['data.0.js', 'data.1.js', 'data.2.js', 'data.3.js', 'data.4.js']
  .map(f => path.join(PKG, 'extra', f)).filter(f => fs.existsSync(f));

// ---------- 格式探测：新格式以 "psol" 明文 JSON 为指纹；否则走旧 gzip 分支 ----------
const psolHit = extraFiles.map(f => ({ f, src: fs.readFileSync(f, 'utf8') })).find(x => x.src.includes('"psol"'));

if (psolHit) {
  // ---------- 新格式（PB=v1）分支 ----------
  const parseWinJson = (f) => {
    const raw = fs.readFileSync(f, 'utf8');
    return JSON.parse(raw.slice(raw.indexOf('=') + 1).replace(/;\s*$/, ''));
  };
  const names = {};
  let n = 0;
  const put = (cid, name) => { if (!cid || !name || names[cid]) return; names[cid] = String(name); n++; };
  // 1) 页面树：sk→页面名（+ project_metas 兜底）
  const pbjFile = path.join(PKG, 'extra', 'data.1.js');
  if (fs.existsSync(pbjFile)) {
    try {
      const pbj = parseWinJson(pbjFile);
      for (const m of (pbj.screen_metas || [])) put(m.cid, m.name);
      for (const v of Object.values(pbj.project_metas || {})) if (v && v.cid) put(v.cid, v.name);
    } catch (e) { console.error('⚠ pbj 解析失败（页面名走 psol 兜底）: ' + e.message); }
  }
  // 2) psol：screen→名、状态→名、元件→display_name/name（嵌套容器递归）
  const psol = JSON.parse(psolHit.src.slice(psolHit.src.indexOf('=') + 1).replace(/;\s*$/, ''));
  const walk = (items) => {
    for (const it of items || []) {
      put(it.cid, it.display_name || it.name);
      for (const k of ['itemList', 'items', 'children', 'widgets']) if (it[k]) walk(it[k]);
    }
  };
  for (const s of psol) {
    put(s.cid, s.name);
    for (const st of s.stateList || []) {
      put(st.cid, st.data && st.data.name);
      walk(st.itemList);
    }
  }
  fs.writeFileSync(OUT, JSON.stringify({
    meta: { tool: 'mockingbot-to-html/read-data.mjs', source: 'plain-JSON psol (PB=v1)', generatedAt: new Date().toISOString(), entries: n },
    names,
  }));
  console.log(JSON.stringify({ ok: true, out: OUT, entries: n, format: 'plain-json' }));
  process.exit(0);
}

// ---------- 旧格式分支（gzip 快照，原逻辑不动） ----------
const dataFile = ['extra/data.1.js', 'extra/data.0.js'].map(f => path.join(PKG, f)).find(f => fs.existsSync(f) && fs.statSync(f).size > 100000);
if (!dataFile) { console.error('找不到主数据文件（extra/data.1.js）'); process.exit(1); }

const src = fs.readFileSync(dataFile, 'utf8');
const m = src.match(/"(H4sIA[^"]+)"/);
if (!m) { console.error('数据文件里没有 gzip 快照块'); process.exit(1); }
const txt = zlib.gunzipSync(Buffer.from(m[1], 'base64')).toString('utf8');

const map = {};
let n = 0;
for (const line of txt.split('\n')) {
  // 行格式实测：`cid\t{…}` / `cid <单字符修饰>\t{…}`（如 `rcV… 5\t`、`rbp… ,\t`）→ 取首 tab 前段首个空白分隔 token
  const tab = line.indexOf('\t');
  if (tab <= 0 || tab > 64) continue;
  const cid = line.slice(0, tab).split(/\s+/)[0];
  if (!cid || !/^[A-Za-z0-9_\/\-!@#$%^&*.]+$/.test(cid)) continue;
  const ni = line.indexOf('"N":"', tab);
  if (ni < 0) continue;
  const e = line.indexOf('"', ni + 5);
  if (e < 0) continue;
  const name = line.slice(ni + 5, e);
  if (!name) continue;
  map[cid] = name;   // 同 cid 多行取首个（快照行优先于 diff 行）
  n++;
}
fs.writeFileSync(OUT, JSON.stringify({ meta: { tool: 'mockingbot-to-html/read-data.mjs', source: dataFile, generatedAt: new Date().toISOString(), entries: n }, names: map }));
console.log(JSON.stringify({ ok: true, out: OUT, entries: n, format: 'gzip-snapshot' }));
