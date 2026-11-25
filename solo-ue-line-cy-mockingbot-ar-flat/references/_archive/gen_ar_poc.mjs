// gen_ar_poc.mjs — 英文节点 + 翻译表 → 阿拉伯语「可交互 POC」（带审查工具栏，用于评审前自查溢出/重叠）
//
// 用法：
//   node gen_ar_poc.mjs [--src en_nodes.json] [--tr translations.json] [--out ar_poc.html]
//
// 与平铺版区别：保留原版(LTR)并排对照 + 视图/数字/图标镜像/溢出审查 工具栏（含 JS）。
// 仅作评审自查用；最终交付请用 gen_ar_flat.mjs 产出「无交互平铺版」。
import fs from 'fs';

const A = {};
for (let i = 2; i < process.argv.length; i++) {
  const a = process.argv[i];
  if (a.startsWith('--')) {
    const k = a.slice(2);
    const v = process.argv[i + 1];
    if (v === undefined || v.startsWith('--')) A[k] = true;
    else { A[k] = v; i++; }
  }
}
const SRC = A.src || 'en_nodes.json';
const TRP = A.tr || 'translations.json';
const OUT = A.out || 'ar_poc.html';
const W = 375;

const pages = JSON.parse(fs.readFileSync(SRC, 'utf8'));
let TR = {};
try { TR = JSON.parse(fs.readFileSync(TRP, 'utf8')); } catch (e) { console.log('⚠ 未找到 translations.json'); }
const tr = t => (t && TR[t] !== undefined ? TR[t] : t);
const esc = s => String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

function alignLogical(a) {
  if (a === 'left') return 'start';
  if (a === 'right') return 'end';
  return (a === 'start' || a === 'end' || a === 'center' || 'justify') ? a : 'start';
}
const isNumish = t => /^[\d\s+\-×xX:.()/%*#]+$/.test(t) && /\d/.test(t);
const unbdi = s => s.replace(/&lt;bdi&gt;/g, '<bdi>').replace(/&lt;\/bdi&gt;/g, '</bdi>');
const MIRROR = { '‹': '›', '›': '‹', '<': '>', '>': '<', '←': '→', '→': '←', '❮': '❯', '❯': '❮' };
const mirrorArrow = t => (t.trim().length <= 2 && MIRROR[t.trim()]) ? MIRROR[t.trim()] : t;
const isLatinRun = t => /^[\x20-\x7E]+$/.test(t) && /[A-Za-z]/.test(t) && !/[\u0600-\u06FF]/.test(t);

function renderNodes(pg, mode) {
  const rtl = mode === 'ar';
  let out = '';
  (pg.nodes || []).forEach((n, idx) => {
    if (!(n.w > 0 && n.h > 0)) return;
    const st = n.st || {};
    if (!n.text && /255[, ]*140[, ]*25/.test((st.bg || '') + '|' + (st.bc || ''))) return;
    const x = rtl ? +(W - n.x - n.w).toFixed(1) : +(+n.x).toFixed(1);
    let s = `left:${x}px;top:${n.y}px;width:${n.w}px;height:${n.h}px;`;
    if (st.bg) s += `background:${st.bg};`;
    if (st.br) s += `border-radius:${st.br};`;
    if (st.bw) s += `border:${st.bw} solid ${st.bc || '#e0e0e0'};`;
    if (st.bgi && !/devices/.test(st.bgi)) s += `background-image:${st.bgi};background-size:cover;background-position:center;`;
    if (st.op && +st.op < 1) s += `opacity:${st.op};`;

    if (n.tag === 'path') {
      const op = (st.op && +st.op < 1) ? +st.op : 1;
      s += `background:rgba(16,16,16,${(0.14 * op).toFixed(2)});border-radius:2px;`;
      if (n.w <= 40 && n.h <= 40 && n.y > 44) s += 'outline:1px dotted rgba(0,0,0,.25);outline-offset:-1px;';
      out += `<div class="el ic${n.w <= 40 && n.h <= 40 && n.y > 44 ? ' flipable' : ''}" title="icon" style="${s}"></div>\n`;
      return;
    }
    if (n.text) {
      const fs_ = parseFloat(st.fs) || 14;
      let lh = parseFloat(st.lh) || fs_ * 1.35;
      let txt = rtl ? tr(n.text) : n.text;
      if (rtl) txt = mirrorArrow(txt);
      const ta = rtl ? alignLogical(st.ta) : (st.ta || 'start');
      const isLTRContent = rtl && (isNumish(txt) || isLatinRun(txt));
      if (n.h <= lh * 1.6 && !isLTRContent) lh = Math.min(lh, n.h);
      if (st.color) s += `color:${st.color};`;
      s += `font-size:${fs_}px;font-weight:${st.fw || 400};line-height:${lh}px;`;
      if (rtl && !isLTRContent) { s += `font-family:'Noto Sans Arabic','Segoe UI',Tahoma,sans-serif;`; s += `min-height:${Math.max(n.h, fs_ * 1.4).toFixed(1)}px;`; }
      else if (!rtl) s += `font-family:'Noto Sans SC',sans-serif;`;
      else if (isLTRContent) s += `font-family:'Noto Sans SC','Noto Sans',sans-serif;`;
      if (isLTRContent) s += `direction:ltr;unicode-bidi:isolate;`;
      const single = n.h <= lh * 1.6;
      const jcMap = { start: 'flex-start', end: 'flex-end', center: 'center', justify: 'flex-start' };
      if (single) s += `display:flex;align-items:center;justify-content:${jcMap[ta] || 'flex-start'};text-align:${ta};`;
      else s += `display:block;text-align:${ta};`;
      s += `white-space:pre-wrap;overflow:hidden;`;
      out += `<div class="el tx" data-i="${idx}" style="${s}">${unbdi(esc(txt))}</div>\n`;
      return;
    }
    out += `<div class="el" style="${s}"></div>\n`;
  });
  return out;
}

const tabs = pages.map((p, i) => `<button class="tab${i === 0 ? ' on' : ''}" data-i="${i}"><i>${i + 1}</i>${esc(p.name)}</button>`).join('');
const PAGE_JSON = JSON.stringify(pages.map(p => p.name));
let scrAr = '', scrOrig = '';
pages.forEach((pg, pi) => {
  scrAr += `<section class="screen${pi === 0 ? ' active' : ''}" id="a${pi}" dir="rtl">${renderNodes(pg, 'ar')}</section>\n`;
  scrOrig += `<section class="screen${pi === 0 ? ' active' : ''}" id="o${pi}" dir="ltr">${renderNodes(pg, 'orig')}</section>\n`;
});

const html = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>阿拉伯语 RTL 原型 POC（评审自查）</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+Arabic:wght@400;500;600;700&family=Noto+Sans+SC:wght@400;500;700&display=swap" rel="stylesheet">
<style>
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:#eceff1;color:#1a1a1a;font-family:'Noto Sans SC','Noto Sans',sans-serif;display:flex;flex-direction:column;align-items:center;padding:20px 16px 40px;min-height:100vh}
  h1{font-size:17px;font-weight:700;margin-bottom:3px}
  .sub{font-size:12px;color:#607d8b;margin-bottom:14px}
  .bar{display:flex;flex-wrap:wrap;gap:14px;align-items:center;justify-content:center;background:#fff;border:1px solid #cfd8dc;border-radius:10px;padding:9px 14px;margin-bottom:12px;max-width:900px}
  .grp{display:flex;gap:5px;align-items:center;font-size:11px;color:#78909c}
  .grp b{font-weight:600;color:#455a64}
  .btn{font-family:inherit;font-size:11px;padding:4px 11px;border:1px solid #cfd8dc;background:#fff;color:#455a64;border-radius:999px;cursor:pointer}
  .btn.on{background:#1a1a1a;color:#fff;border-color:#1a1a1a}
  .tabs{display:flex;flex-wrap:wrap;gap:6px;justify-content:center;max-width:900px;margin-bottom:16px}
  .tab{font-family:inherit;font-size:12px;padding:5px 12px 5px 8px;border:1px solid #cfd8dc;background:#fff;color:#455a64;border-radius:999px;cursor:pointer;display:flex;align-items:center;gap:6px}
  .tab i{font-style:normal;font-size:10px;font-weight:700;background:#eceff1;color:#90a4ae;border-radius:50%;width:16px;height:16px;display:flex;align-items:center;justify-content:center}
  .tab.on{background:#1a1a1a;color:#fff;border-color:#1a1a1a}
  .tab.on i{background:rgba(255,255,255,.22);color:#fff}
  .pair{display:flex;gap:20px;flex-wrap:wrap;justify-content:center;align-items:flex-start}
  .cell{display:flex;flex-direction:column;align-items:center;gap:6px}
  .cap{font-size:12px;color:#455a64;font-weight:600}
  .stage{position:relative;width:375px;height:812px;background:#fff;border-radius:22px;overflow:hidden;box-shadow:0 12px 40px rgba(0,0,0,.18)}
  .screen{position:absolute;inset:0;display:none;background:#fff;overflow:hidden}
  .screen.active{display:block}
  .el{position:absolute}
  .el.ic{border-radius:2px}
  body.flip .el.flipable{transform:scaleX(-1)}
  body.ovf .el.tx.overflow{outline:2px solid #e53935;outline-offset:-2px;background:rgba(229,57,53,.07)}
  body.ovf .el.tx.clipped{outline:2px dashed #fb8c00;outline-offset:-2px}
  .hide{display:none!important}
  .rep{margin-top:16px;font-size:11px;color:#e53935;text-align:center;max-width:780px;line-height:1.7}
</style>
</head>
<body class="flip">
<h1>阿拉伯语原型 POC（评审自查）</h1>
<div class="sub">${pages.length} 屏 · 画布 375×812 · 标题保留中文，画布内为阿语</div>
<div class="bar">
  <div class="grp"><b>视图</b><button class="btn on" id="vAr">阿语版</button><button class="btn" id="vBoth">并排对照</button><button class="btn" id="vCn">原版</button></div>
  <div class="grp"><b>数字</b><button class="btn on" id="nW">1234</button><button class="btn" id="nA">٠١٢٣</button></div>
  <div class="grp"><b>方向图标</b><button class="btn on" id="fOn">镜像</button><button class="btn" id="fOff">原样</button></div>
  <div class="grp"><b>审查</b><button class="btn" id="tOvf">标出溢出</button><button class="btn" id="tFit">自动收紧字号</button><button class="btn" id="tRst">还原</button><button class="btn" id="tRep">统计</button></div>
</div>
<div class="tabs" id="tabBar">${tabs}</div>
<div class="pair">
  <div class="cell" id="cellOrig"><div class="cap" id="capO"></div><div class="stage">${scrOrig}</div></div>
  <div class="cell" id="cellAr"><div class="cap" id="capA"></div><div class="stage">${scrAr}</div></div>
</div>
<div class="rep" id="rep"></div>
<script>
(function(){
  var cur=0, PAGES=PAGE_JSON;
  var tabEls=document.querySelectorAll('#tabBar .tab');
  var capO=document.getElementById('capO'), capA=document.getElementById('capA');
  function show(i){cur=i;tabEls.forEach(function(t,k){t.classList.toggle('on',k===i);});
    document.querySelectorAll('.screen').forEach(function(s){s.classList.remove('active');});
    var a=document.getElementById('a'+i),o=document.getElementById('o'+i);
    if(a)a.classList.add('active');if(o)o.classList.add('active');
    var n='<s>'+(i+1)+'/'+PAGES.length+' ·</s> '+PAGES[i];
    capO.innerHTML='原版（LTR） '+n;capA.innerHTML='阿拉伯语（RTL） '+n;}
  tabEls.forEach(function(t,k){t.addEventListener('click',function(){show(k);});});show(0);
  var WEST='0123456789',ARAB='٠١٢٣٤٥٦٧٨٩';
  function toArab(s){return s.replace(/[0-9]/g,function(d){return ARAB[+d];});}
  function toWest(s){return s.replace(/[٠-٩]/g,function(d){return WEST[ARAB.indexOf(d)];});}
  var dataAr=[];
  document.querySelectorAll('.screen[id^="a"]').forEach(function(sec){var arr=[];sec.querySelectorAll('.tx').forEach(function(e){arr.push([e,e.textContent]);});dataAr.push(arr);});
  var cellO=document.getElementById('cellOrig'),cellA=document.getElementById('cellAr');
  var bAr=document.getElementById('vAr'),bBoth=document.getElementById('vBoth'),bCn=document.getElementById('vCn');
  function setView(m){bAr.classList.toggle('on',m==='ar');bBoth.classList.toggle('on',m==='both');bCn.classList.toggle('on',m==='cn');
    cellO.classList.toggle('hide',m==='ar');cellA.classList.toggle('hide',m==='cn');}
  bAr.onclick=function(){setView('ar');};bBoth.onclick=function(){setView('both');};bCn.onclick=function(){setView('cn');};setView('both');
  var nW=document.getElementById('nW'),nA=document.getElementById('nA');
  nW.onclick=function(){nW.classList.add('on');nA.classList.remove('on');dataAr.forEach(function(arr){arr.forEach(function(p){p[0].textContent=toWest(p[1]);});});};
  nA.onclick=function(){nA.classList.add('on');nW.classList.remove('on');dataAr.forEach(function(arr){arr.forEach(function(p){p[0].textContent=toArab(p[1]);});});};
  var fOn=document.getElementById('fOn'),fOff=document.getElementById('fOff');
  fOn.onclick=function(){document.body.classList.add('flip');fOn.classList.add('on');fOff.classList.remove('on');};
  fOff.onclick=function(){document.body.classList.remove('flip');fOff.classList.add('on');fOn.classList.remove('on');};
  function over(e){var rg=document.createRange();rg.selectNodeContents(e);var rc=[].slice.call(rg.getClientRects());
    if(!rc.length)return[0,0];var tops={};rc.forEach(function(r){tops[Math.round(r.top)]=1;});var lines=Object.keys(tops).length;
    var wid=Math.max.apply(null,rc.map(function(r){return r.width;}));var cs=getComputedStyle(e);
    var lh=parseFloat(cs.lineHeight)||(parseFloat(cs.fontSize)*1.35);var cap=Math.max(1,Math.floor(e.clientHeight/lh+0.2));
    return[Math.max(0,lines-cap),Math.max(0,Math.round(wid-e.clientWidth)),lines,cap];}
  function allTx(){var a=[];document.querySelectorAll('.screen[id^="a"] .tx').forEach(function(e){a.push(e);});return a;}
  function eachScreen(fn){document.querySelectorAll('.screen[id^="a"]').forEach(function(sec){var keep=sec.classList.contains('active');sec.classList.add('active');fn(sec);if(!keep)sec.classList.remove('active');});}
  var TH=3;
  function sumOver(){var v=0,h=0,n=0,w=0;eachScreen(function(sec){sec.querySelectorAll('.tx').forEach(function(e){var o=over(e);v+=o[0];h+=o[1];if(o[0]>0||o[1]>TH)n++;if(o[1]>TH)w++;});});return{v:v,h:h,n:n,wide:w};}
  var origin=[];
  function snapshot(){if(origin.length)return;allTx().forEach(function(e){origin.push([e,e.style.fontSize,e.style.lineHeight]);});}
  document.getElementById('tOvf').onclick=function(){document.body.classList.add('ovf');eachScreen(function(sec){sec.querySelectorAll('.tx').forEach(function(e){e.classList.remove('overflow','clipped');var o=over(e);if(o[0]>0)e.classList.add('overflow');else if(o[1]>TH)e.classList.add('clipped');});});var s=sumOver();document.getElementById('rep').innerHTML='需处理元素 '+s.n+' 个：折行超出 '+s.v+' 行 · 单行超宽 '+s.wide+' 个'+(s.wide?'（合计 '+s.h+'px）':'')+'。红框=折行超出，橙虚框=单行超宽。';};
  document.getElementById('tFit').onclick=function(){snapshot();document.body.classList.add('ovf');var fixed=0;eachScreen(function(sec){sec.querySelectorAll('.tx').forEach(function(e){e.classList.remove('overflow','clipped');var fs0=parseFloat(e.style.fontSize)||14,lh0=parseFloat(e.style.lineHeight)||fs0*1.35;var ratio=lh0/fs0,fs=fs0,o=over(e);if(!(o[0]>0||o[1]>TH))return;while((o[0]>0||o[1]>TH)&&fs>fs0*0.75){fs-=0.5;e.style.fontSize=fs+'px';e.style.lineHeight=(fs*ratio).toFixed(2)+'px';o=over(e);}if(fs<fs0){fixed++;e.classList.add('clipped');if(o[0]>0)e.classList.add('overflow');}});});var s=sumOver();document.getElementById('rep').innerHTML='已自动收紧 '+fixed+' 个元素（最多缩至原字号 75%）。剩余 '+s.n+' 个：折行超出 '+s.v+' 行 · 单行超宽 '+s.wide+' 个 —— 这些需改阿语文案或调盒高。';};
  document.getElementById('tRst').onclick=function(){document.body.classList.remove('ovf');origin.forEach(function(p){p[0].style.fontSize=p[1];p[0].style.lineHeight=p[2];p[0].classList.remove('overflow','clipped');});origin=[];document.getElementById('rep').innerHTML='已还原为原始字号。';};
  document.getElementById('tRep').onclick=function(){var n=0,h=0;allTx().forEach(function(e){n++;if(/[؀-ۿ]/.test(e.textContent))h++;});var s=sumOver();document.getElementById('rep').innerHTML='文本元素 '+n+' 个 · 已阿语化 '+h+' 个（'+Math.round(h/n*100)+'%）· 需处理 '+s.n+' 个（折行超出 '+s.v+' 行 · 单行超宽 '+s.wide+' 个）。未阿语化的为国家区号、时间、emoji、社交账号字母等有意保留项。';};
})();
</script>
</body>
</html>`;

fs.writeFileSync(OUT, html, 'utf8');
console.log('已生成 POC:', OUT, '| KB:', (html.length / 1024).toFixed(1), '| 页面:', pages.length);
