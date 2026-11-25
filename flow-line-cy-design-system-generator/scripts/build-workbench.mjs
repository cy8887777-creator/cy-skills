#!/usr/bin/env node
// build-workbench.mjs —— 决策链 → 工作台单文件静态页（v6：九段步骤统一渲染 + 顶栏原始素材入口）
// 用法: node build-workbench.mjs <chain.json> <输出目录>
// 同步产出: 原始组件库规范.html / 原始参考令牌库.html（顶栏右侧入口的目标页面）
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const args = process.argv.slice(2);
const chainFile = args[0], outDirArg = args[1];
const SAMPLE = args.includes('--sample'); // 样例模式：所有步骤可点（预览案例用）
if (!chainFile || !outDirArg) { console.error('用法: node build-workbench.mjs <chain.json> <输出目录>'); process.exit(1); }
const chain = JSON.parse(fs.readFileSync(chainFile, 'utf8').replace(/^\uFEFF/, ''));
const outDir = path.resolve(outDirArg);
fs.mkdirSync(outDir, { recursive: true });

const esc = s => String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// 章节唯一权威 = references/chapters.md（14 章）；增删章必须三处同步：chapters.md / 本表 / export-clean.mjs 的 CHAPTERS
const CHAPTERS = [
  ['values', '01', '设计价值观', 'DESIGN VALUES'],
  ['layout', '02', '布局', 'LAYOUT'],
  ['density', '03', '密度与多端', 'PLATFORMS'],
  ['rules', '04', '设计要求', 'REQUIREMENTS'],
  ['color', '05', '颜色', 'COLOR'],
  ['type', '06', '字体', 'TYPOGRAPHY'],
  ['spacing', '07', '间距', 'SPACING'],
  ['radius', '08', '圆角', 'RADIUS'],
  ['shadow', '09', '阴影', 'SHADOW'],
  ['motion', '10', '动效', 'MOTION'],
  ['component', '11', '组件', 'COMPONENTS'],
  ['icon', '12', '图标', 'ICONS'],
  ['imagery', '13', '图像与插画', 'IMAGERY'],
  ['bans', '14', '设计禁令', 'PROHIBITIONS'],
];

// ---------- Tab1 左栏步骤（可点击） ----------
function renderSteps() {
  const row = s => {
    const st = s.status === 'done' ? 'done' : (s.id === chain.current ? 'now' : 'todo');
    const mark = st === 'done' ? '✓' : (st === 'now' ? '●' : esc(s.no || ''));
    const sub = s.sub ? `<div class="ssub">${esc(s.sub)}</div>` : '';
    const clickable = (SAMPLE || s.status === 'done' || s.id === chain.current || (s.candidates && s.candidates.length)) ? ` onclick="selectStep('${esc(s.id)}')" style="cursor:pointer"` : '';
    return `<div class="step ${st}"${clickable} data-id="${esc(s.id)}"><span class="st">${mark}</span><div class="stx"><div class="stt">${esc(s.title)}</div>${sub}</div></div>`;
  };
  let h = (chain.steps || []).map(row).join('\n');
  // 兼容极旧决策链：steps 里没有样品页步骤时才补画遗留 samplePage 字段（新版九段链 steps 已含 0-9，不再出现多余行）
  if (chain.samplePage && !(chain.steps || []).some(s => s.id === 'samplepage')) h += '\n' + row({ ...chain.samplePage, id: 'samplepage' });
  return h;
}

// ---------- Tab4 预览 ----------
function renderPreview() {
  const toc = CHAPTERS.map(([id, no, zh, en]) => {
    const filled = !!(chain.overview && chain.overview[id]);
    return `<a class="toc-i ${filled ? 'full' : 'pend'}" onclick="gotoChapter('${id}')"><span class="no">${no}</span>${esc(zh)}<span class="en">${esc(en)}</span><span class="dot"></span></a>`;
  }).join('\n');
  const body = CHAPTERS.map(([id, no, zh, en]) => {
    const filled = chain.overview && chain.overview[id];
    return `<section class="chapter" id="pv-${id}"><div class="ch-head"><span class="no">${no}</span><div><h3>${esc(zh)}<span class="en">${esc(en)}</span></h3></div></div><div class="ch-body">${filled ? chain.overview[id] : '<div class="pending">待定 —— 由共创步骤产生</div>'}</div></section>`;
  }).join('\n');
  return `<div class="pvwrap"><div class="pvtoc">${toc}</div><div class="pvbody">${body}</div></div>`;
}

const STATE = JSON.stringify(chain).replace(/</g, '\\u003c');

const html = `<!DOCTYPE html><html lang="zh"><head><meta charset="UTF-8"><title>${esc(chain.project || '设计系统')} · 共创工作台</title><style>
*{box-sizing:border-box} body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#FAFAF7;color:#23283B;margin:0;position:relative;font-size:14px;line-height:1.7;}
body::before{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background-image:linear-gradient(rgba(76,111,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(76,111,255,.04) 1px,transparent 1px);background-size:24px 24px;}
body::after{content:"";position:fixed;inset:0;pointer-events:none;z-index:0;background:radial-gradient(340px 340px at 8% 6%,rgba(76,111,255,.16),transparent 70%),radial-gradient(300px 300px at 94% 34%,rgba(61,139,110,.13),transparent 70%),radial-gradient(280px 280px at 22% 92%,rgba(201,168,124,.12),transparent 70%);filter:blur(24px);}
.top,.tabs,main,.panel,.wb,.carea,.stepside,.cands,.pvwrap,.pvbody{position:relative;z-index:1;}
.top{background:rgba(255,255,255,.66);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,.85);color:#23283B;padding:12px 24px;display:flex;align-items:center;gap:14px;font-size:13px;flex-wrap:wrap;}
.top b{font-size:15px;font-family:'Noto Serif SC','Songti SC',serif;} .sep{opacity:.25;} .nowchip2{background:#4C6FFF;color:#fff;padding:3px 10px;border-radius:99px;font-size:12px;font-weight:600;}
.rawlinks{margin-left:auto;display:flex;gap:16px;flex-wrap:wrap;}
.rawlinks a{color:#4C6FFF;text-decoration:underline;text-underline-offset:3px;font-size:12px;padding:5px 2px;display:inline-block;}
.rawlinks a:hover{color:#3550C4;text-underline-offset:5px;}
.tabs{display:flex;gap:4px;padding:10px 24px 0;}
.tabs button{border:0;background:transparent;padding:9px 18px;font-size:13px;cursor:pointer;color:#64748B;border-bottom:2px solid transparent;}
.tabs button.on{color:#3550C4;font-weight:700;border-bottom-color:#4C6FFF;}
main{padding:20px 24px;max-width:1240px;margin:0 auto;}
@media(max-width:720px){main{padding:12px}}
.panel{display:none;} .panel.on{display:block;}
.step{display:flex;gap:10px;padding:10px 18px;align-items:center;border-left:3px solid transparent;}
.step.done{color:#64748B;} .step.done .st{background:#EEF1FF;color:#3D8B6E;}
.step.now{background:#4C6FFF;color:#fff;border-radius:8px;margin:2px 8px;box-shadow:0 4px 12px rgba(76,111,255,.35);} .step.now .st{background:rgba(255,255,255,.25);color:#fff;}
.step.todo{color:#B9C0CE;} .step.todo .st{background:#F5F4F0;color:#B9C0CE;}
.step.viewing{outline:1px dashed #4C6FFF;outline-offset:-3px;}
.st{width:22px;height:22px;border-radius:99px;display:flex;align-items:center;justify-content:center;font-size:11px;flex-shrink:0;}
.stt{font-size:13px;font-family:'Noto Serif SC','Songti SC',serif;font-weight:600;} .ssub{font-size:12px;opacity:.75;margin-top:2px;line-height:1.4;}
.wb{display:flex;gap:18px;align-items:flex-start;}
@media(max-width:960px){.wb{flex-direction:column}.stepside{width:100%}}
.stepside{width:280px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:16px 0;flex-shrink:0;box-shadow:0 4px 16px rgba(35,40,59,.06);}
.carea{flex:1;}
.curhead{margin-bottom:6px;} .nowchip{background:#4C6FFF;color:#fff;font-size:11px;padding:2px 10px;border-radius:99px;margin-right:8px;}
.curhint{color:#64748B;font-size:12.5px;margin:6px 0 14px;line-height:1.6;}
.ccard{background:rgba(255,255,255,.66);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border:1px solid rgba(255,255,255,.85);border-radius:10px;box-shadow:0 4px 16px rgba(35,40,59,.08);padding:18px 20px;margin-bottom:14px;position:relative;animation:rise .3s ease-out both;}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:none}}
.rec{position:absolute;top:14px;right:16px;background:#EEF1FF;color:#3550C4;font-size:10px;padding:2px 9px;border-radius:99px;}
.chead{font-size:14px;margin-bottom:8px;} .cname{color:#64748B;font-size:12px;margin-left:8px;}
.sws{display:flex;gap:5px;margin:10px 0;} .sw{width:28px;height:28px;border-radius:6px;border:1px solid rgba(0,0,0,.06);}
.cdesc{font-size:12.5px;color:#5A6470;margin:8px 0;line-height:1.6;}
.cv{font-size:12.5px;padding-left:16px;margin:8px 0;} .cv li{margin:4px 0;} .cv b{margin-right:6px;color:#23283B;}
.cact{font-size:12px;color:#64748B;border-top:1px dashed #E2E6F2;padding-top:9px;margin-top:10px;line-height:1.5;}
.win-badge{position:absolute;top:14px;right:16px;background:#3D8B6E;color:#fff;font-size:10px;padding:2px 9px;border-radius:99px;box-shadow:0 2px 8px rgba(61,139,110,.35);}
/* 候选区双列 + 文字层级 */
.cands{display:grid;grid-template-columns:1fr 1fr;gap:14px;align-items:start;}
.ccard{margin-bottom:0;}
.ccard.full{grid-column:1/-1;}
@media(max-width:960px){.cands{grid-template-columns:1fr}}
.cno{font-size:10px;color:#64748B;background:#EEF1FF;padding:2px 8px;border-radius:99px;margin-right:8px;vertical-align:middle;}
.cname2{font-size:14px;font-weight:700;color:#23283B;font-family:'Noto Serif SC','Songti SC',serif;}
.cdemo{background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:12px;margin:4px 0 10px;overflow:hidden;}
/* 外部输入 */
.ext-quote{background:#fff;border-left:3px solid #D6DCE4;padding:8px 12px;font-size:12.5px;color:#5A6470;border-radius:0 6px 6px 0;margin:6px 0;}
.ext-ask{background:#fff;}
.ext-ask b{display:block;font-size:12px;margin-bottom:4px;color:#23283B;}
.ext-ask span{font-size:11.5px;color:#64748B;}
/* 画像播报 */
.pf-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 18px;margin:6px 0 4px;}
.pf-i{display:flex;gap:8px;align-items:baseline;font-size:12.5px;line-height:1.55;}
.pf-i b{flex-shrink:0;font-size:10.5px;color:#64748B;font-weight:600;min-width:52px;}
.pf-i span{color:#23283B;}
.pf-w{border-bottom:1px dashed #E2E6F2;padding:5px 0;}
.pf-concl{margin-top:12px;background:#E6F4ED;border-radius:8px;padding:9px 12px;font-size:12px;color:#2C664F;}
.pf-concl b{margin-right:8px;font-size:10.5px;color:#2C664F;}
/* 查漏清单 */
.ck{display:flex;gap:8px;align-items:baseline;font-size:12.5px;padding:6px 0;border-bottom:1px dashed #E2E6F2;}
.ck:last-child{border-bottom:0;}
.cktag{flex-shrink:0;font-size:10px;font-weight:600;border-radius:99px;padding:1px 8px;}
.cktag.bu{background:#EEF1FF;color:#3550C4;}
.cktag.qr{background:#F5F4F0;color:#64748B;}
.tok-card .toksec{margin-bottom:14px;} .toklab{font-size:10px;letter-spacing:.1em;color:#64748B;margin-bottom:8px;font-weight:600;} .ctag{font-size:10px;background:#EEF1FF;color:#3550C4;padding:2px 8px;border-radius:99px;margin-left:8px;} .ccard .md{font-size:12px;} .curfoot,.empty{font-size:12px;color:#64748B;margin-top:12px;} .empty{background:#fff;border-radius:10px;padding:22px;text-align:center;}
/* 预览 */
.pvwrap{display:flex;gap:18px;align-items:flex-start;}
@media(max-width:960px){.pvwrap{flex-direction:column}.pvtoc{width:100%;position:static}}
.pvtoc{width:250px;background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:14px 0;position:sticky;top:12px;box-shadow:0 4px 16px rgba(35,40,59,.06);}
.toc-i{display:flex;align-items:baseline;gap:8px;padding:9px 18px;color:#64748B;font-size:12.5px;cursor:pointer;border-left:3px solid transparent;}
.toc-i:hover{color:#23283B;background:#F5F4F0;} .toc-i.full{color:#23283B;} .toc-i.pend{color:#B9C0CE;}
.toc-i.on{color:#3550C4;border-left-color:#4C6FFF;background:#EEF1FF;}
.toc-i .no{font-size:10px;opacity:.7;min-width:18px;font-family:Consolas,monospace;} .toc-i .en{margin-left:auto;font-size:9px;opacity:.6;letter-spacing:.06em;}
.toc-i .dot{width:6px;height:6px;border-radius:99px;margin-left:6px;} .toc-i.full .dot{background:#3D8B6E;} .toc-i.pend .dot{background:#DCE4F0;}
.pvbody{flex:1;}
.chapter{background:#fff;border:1px solid #E2E6F2;border-radius:10px;padding:20px 24px;margin-bottom:12px;box-shadow:0 4px 16px rgba(35,40,59,.06);}
.ch-head{display:flex;align-items:baseline;gap:10px;margin-bottom:10px;} .ch-head .no{font-size:12px;color:#64748B;font-weight:600;font-family:Consolas,monospace;}
h3{font-family:'Noto Serif SC','Songti SC',serif;font-size:17px;margin:0;} .en{font-size:10px;color:#B9C0CE;margin-left:5px;letter-spacing:.08em;}
.ch-body{font-size:13px;line-height:1.7;} .pending{color:#B9C0CE;font-size:12px;}
</style></head><body>
<div class="top"><b>${esc(chain.project || '设计系统')} · 共创工作台</b><span class="sep">|</span><span>决策链 v${esc(chain.version || 1)}</span><span class="sep">|</span><span class="nowchip2">${esc((chain.steps || []).find(s => s.id === chain.current)?.title || '—')}</span><span class="rawlinks"><a href="./原始组件库规范.html" target="_blank">原始组件库规范 ↗</a><a href="./原始参考令牌库.html" target="_blank">原始参考令牌库 ↗</a><a href="./品牌设计语言.html" target="_blank">品牌设计语言 ↗</a><a href="./原始图标库.html" target="_blank">原始图标库 ↗</a></span></div>
<div class="tabs">
  <button class="on" data-t="wb">工作台</button>
  <button data-t="preview">预览</button>
</div>
<main>
  <div class="panel on" id="p-wb"><div class="wb"><div class="stepside" id="stepside">${renderSteps()}</div><div class="carea" id="carea"></div></div></div>
  <div class="panel" id="p-preview">${renderPreview()}</div>
</main>
<script>
const STATE = ${STATE};
let viewing = STATE.current;
function findStep(id){ return (STATE.steps||[]).find(s=>s.id===id); }
function renderPane(){
  const s = findStep(viewing);
  const area = document.getElementById('carea');
  if (!s) { area.innerHTML = '<div class="empty">步骤全部完成</div>'; return; }
  const cands = s.candidates||[];
  let inner = '';
  try {
    if (!(cands.length) && s.status==='now') {
      inner = '<div class="ccard full" style="border-style:dashed"><div class="chead"><b class="cname2">'+s.title+' · 进行中</b><span class="rec" style="position:static;margin-left:auto">制作中</span></div><p class="cdesc">'+(s.hint||'候选正在生成，稍后刷新查看。')+'</p></div>';
    }
    else if (s.id==='profile') inner = renderProfile(s);
    else if (s.id==='external') inner = renderExternal(s);
    else if (s.id==='direction') inner = cands.map((c,i)=>renderTokenCard(c,s,i)).join('');
    else if (s.id==='imagery'||s.id==='gaps') inner = (cands.length===1 ? renderSingle(cands[0],s) : cands.map((c,i)=>renderGeneric(c,s,i)).join(''));
    else inner = cands.map((c,i)=>renderGeneric(c,s,i)).join('');
  } catch (e) {
    inner = '<div class="ccard full"><div class="chead"><b class="cname2">候选渲染异常</b></div><p class="cdesc">该步数据字段不符合渲染约定（对照 examples/sample-chain.json 的 shape），已在会话中修复前降级为通用卡：'+String(e && e.message || e).replace(/</g,'&lt;')+'</p></div>' + cands.map((c,i)=>renderGeneric(c,s,i)).join('');
  }
  area.innerHTML = head(s) + '<div class="cands">' + (inner || '<div class="empty">本步暂无候选内容</div>') + '</div>';
}
function head(s){
  if (s.status==='done') return '<div class="curhead"><span class="nowchip" style="background:#16803C">已完成</span><b>'+s.title+'</b></div>'+(s.reopened?'<p class="curhint">⚠ 此步曾回改，下游步骤建议重看。</p>':'')+'<p class="curhint">当时的选择已标 ✓。点左栏其他步骤可切换；在会话里说「回改 '+s.title+'」可重开此步（下游软提示）。</p>';
  if (s.id===STATE.current) return '<div class="curhead"><span class="nowchip">当前</span><b>'+s.title+'</b></div><p class="curhint">'+(s.hint||'')+'</p>';
  if ((s.candidates||[]).length) return '<div class="curhead"><span class="nowchip" style="background:#5F6B7B">候选已备</span><b>'+s.title+'</b></div><p class="curhint">这一步的候选已生成（可回看），还没轮到决策 —— 按流程顺序走完前面的步骤后在这里拍板。</p>';
  return '<div class="curhead"><b>'+s.title+'</b></div><p class="curhint">未解锁 —— 由前序步骤产生。</p>';
}
function actSel(i){ return '<div class="cact">会话回复「选 '+(i+1)+'」；或描述微调；或说「再来一批」</div>'; }
function actConfirm(){ return '<div class="cact">看完没问题，会话回复「可以」；要调整就直接说改哪里</div>'; }
function cardHead(s,i,name){
  const nm = name || ('候选 '+(i+1));
  const win = s.chosen && (s.chosen===nm || (Array.isArray(s.chosen)&&s.chosen.some(x=>nm.indexOf(x)>=0||x.indexOf(nm)>=0)) || (typeof s.chosen==='string'&&(nm.indexOf(s.chosen)>=0||s.chosen.indexOf(nm)>=0)));
  let t = '<div class="chead"><span class="cno">候选 '+(i+1)+'</span><b class="cname2">'+nm+'</b>';
  if (win) t += '<span class="win-badge" style="position:static;margin-left:auto">✓ 已选定</span>';
  else if (i===0&&s.status==='now') t += '<span class="rec" style="position:static;margin-left:auto">推荐</span>';
  return t + '</div>';
}
function renderGeneric(c,s,i){
  const isObj=(typeof c==='object'&&c!==null);
  const name=isObj?(c.name||('候选 '+(i+1))):String(c);
  const sw=(isObj?(c.swatches||[]):[]).map(x=>'<span class="sw" style="background:'+x+'"></span>').join('');
  const vals=(isObj&&c.values)?'<ul class="cv">'+Object.entries(c.values).map(function(kv){return '<li><b>'+kv[0]+'</b>'+kv[1]+'</li>';}).join('')+'</ul>':'';
  let card = '<div class="ccard">' + cardHead(s,i,name);
  if (isObj && c.demo) card += '<div class="cdemo">'+c.demo+'</div>';
  if (sw) card += '<div class="sws">'+sw+'</div>';
  if (isObj && c.desc) card += '<p class="cdesc">'+c.desc+'</p>';
  card += vals;
  if (s.status==='now') card += actSel(i);
  card += '</div>';
  return card;
}
function renderSingle(c,s){
  const isObj=(typeof c==='object'&&c!==null);
  let card = '<div class="ccard full">' + cardHead(s,0,isObj?c.name:'盘点结果');
  if (isObj && c.desc) card += '<p class="cdesc">'+c.desc+'</p>';
  if (isObj && c.values) Object.entries(c.values).forEach(function(kv){
    const isGap = /^(补|待|缺)/.test(kv[0]);
    card += '<div class="ck"><b class="cktag '+(isGap?'bu':'qr')+'">'+kv[0]+'</b><span>'+kv[1]+'</span></div>';
  });
  if (s.status==='now') card += actConfirm();
  card += '</div>';
  return card;
}
function renderProfile(s){
  const c = (s.candidates||[])[0];
  let rows = '';
  if (c && typeof c==='object' && c.fields) {
    Object.keys(c.fields).forEach(function(k){ rows += '<div class="pf-i"><b>'+k+'</b><span>'+c.fields[k]+'</span></div>'; });
  } else {
    String(c||'').split(/[·；;]+/).map(x=>x.trim()).filter(Boolean).forEach(function(p){ rows += '<div class="pf-i pf-w"><span>'+p+'</span></div>'; });
  }
  const concl = s.chosen ? '<div class="pf-concl"><b>处理结论</b>'+(Array.isArray(s.chosen)?s.chosen.join('；'):s.chosen)+'</div>' : '';
  return '<div class="ccard full"><div class="pf-grid">'+rows+'</div>'+concl+(s.status==='now'?actConfirm():'')+'</div>';
}
function renderExternal(s){
  const subs = s.submissions || [];
  let out = '';
  subs.forEach(function(u,i){
    const sw = (u.swatches||[]).map(function(x){return '<span class="sw" style="background:'+x+'"></span>';}).join('');
    out += '<div class="ccard"><span class="cno">提交 '+(i+1)+'</span><div class="chead"><b class="cname2">'+(u.type||'外部素材')+'</b></div>'
      + (u.quote ? '<div class="ext-quote">'+u.quote+'</div>' : '')
      + (u.desc ? '<p class="cdesc">'+u.desc+'</p>' : '')
      + (sw ? '<div class="sws">'+sw+'</div>' : '')
      + (u.accept ? '<div class="cact">吸收：'+u.accept+'</div>' : '')
      + '</div>';
  });
  out += '<div class="ccard full ext-ask"><b>'+(subs.length?'还可以继续补充':'还没有外部输入')+'</b><span>可以直接发：品牌色卡 · Logo · 参考截图 · 竞品 · 文字要求——发一条解析一条，多次提交会逐条列出；没有要提交的就说「跳过」。</span>'+(s.status==='now'?actConfirm():'')+'</div>';
  return out;
}
function renderTokenCard(c, s, i){
  const t = c.tokens;
  if (!t || !t.colors) return '';
  const C = t.colors;
  const sw = function(hex,label){ return '<div style="text-align:center"><div style="width:44px;height:44px;border-radius:8px;background:'+hex+';border:1px solid rgba(0,0,0,.08)"></div><div style="font-size:9px;color:#8A93A0;margin-top:3px;font-family:Consolas,monospace">'+label+'</div></div>'; };
  let colorRow = '';
  const cmap = [['主色',C.primary],['次色',C.secondary],['CTA',C.cta],['底色',C.bg],['表面',C.surface],['主文字',C.textPrimary],['次文字',C.textSecondary],['边框',C.border]];
  cmap.filter(x => x[1]).forEach(function(x){ colorRow += sw(x[1], x[0]); });
  let statusRow = '';
  [['成功',C.success],['警告',C.warning],['危险',C.danger]].filter(x => x[1]).forEach(function(x){ statusRow += sw(x[1], x[0]); });
  let scaleRow = '';
  (t.scale || []).forEach(function(sz, idx){ const labels=['大标题','标题','正文','次级','辅助','最小']; scaleRow += '<div style="margin:3px 0"><span style="font-family:'+t.fontHead+';font-size:'+sz+'px;font-weight:'+(idx===0?700:idx===1?600:400)+';color:'+C.textPrimary+'">示例标题</span> <span style="font-size:9px;color:#8A93A0">'+sz+'px '+(labels[idx]||('第'+(idx+1)+'档'))+'</span></div>'; });
  return '<div class="ccard tok-card">' + cardHead(s,i,c.name) + '<span class="ctag" style="margin-left:8px">'+(c.concept||'')+'</span>' +
    '<div class="toksec"><div class="toklab">语义色</div><div style="display:flex;gap:8px;flex-wrap:wrap">'+colorRow+'</div>' +
    '<div class="toklab" style="margin-top:10px">状态色</div><div style="display:flex;gap:8px">'+statusRow+'</div></div>' +
    '<div class="toksec"><div class="toklab">字体与字阶 · '+t.fontHead+' / '+t.fontBody+'</div>'+scaleRow+'<div style="margin-top:8px"><span style="font-family:'+t.fontBody+';color:'+C.textSecondary+';font-size:12px">正文示例：这里展示正文的可读性与行高节奏，用于检验日常阅读的舒适程度。</span></div></div>' +
    '<div class="cact">会话回复「选 '+(i+1)+'」；或多选排序；或微调某处；或「再来一批」。圆角/阴影/组件形态都不在这一步 —— 全部在下一步按组件库基调定。</div></div>';
}
function selectStep(id){ viewing = id; renderPane();
  document.querySelectorAll('#stepside .step').forEach(el=>el.classList.toggle('viewing', el.dataset.id===id));
}
document.querySelectorAll('.tabs button').forEach(b => b.onclick = () => {
  document.querySelectorAll('.tabs button').forEach(x => x.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('on'));
  b.classList.add('on'); document.getElementById('p-' + b.dataset.t).classList.add('on');
});
function gotoChapter(id){
  document.querySelectorAll('.tabs button').forEach(x => x.classList.remove('on'));
  document.querySelectorAll('.panel').forEach(x => x.classList.remove('on'));
  document.querySelector('[data-t="preview"]').classList.add('on');
  document.getElementById('p-preview').classList.add('on');
  const el = document.getElementById('pv-' + id); if (el) el.scrollIntoView({behavior:'smooth'});
}
renderPane();
</script></body></html>`;

fs.writeFileSync(path.join(outDir, 'workbench.html'), html);

// 同步生成顶栏右侧四个原始素材入口页（失败不阻塞工作台）
try {
  const { buildRawAssets } = await import('./build-raw-assets.mjs');
  const made = buildRawAssets(path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..'), outDir);
  console.log('原始素材入口页已生成: ' + made.map(n => path.join(outDir, n)).join(', '));
} catch (e) {
  console.warn('原始素材入口页生成失败（工作台不受影响）: ' + e.message);
}
console.log('工作台已生成: ' + path.join(outDir, 'workbench.html'));
