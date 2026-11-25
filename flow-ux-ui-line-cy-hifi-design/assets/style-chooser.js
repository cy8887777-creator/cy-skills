/*STYLE_CHOOSER_START*/
  (function(){
    /* ============ 风格面板（UI V3 草图版式；底层换肤机制延续 V2 不动） ============
       数据源（降级链；界面不出现数据源/降级等内部字样）：
         正式态 = 受控块 STYLE-REGISTRY / STYLE-PACK（围栏两形态与 scripts/verify_blocks.py
                  同构：<!-- NAME:BEGIN/END --> 注释围栏、<script data-block="NAME">；
                  兼容 /*NAME_START* / JS 注释围栏形态）；
         降级态 = __STYLE_PRESETS__ 九槽（包装成单组「风格组1」，版式同正式态）；
         面板不得空转：两态都失败时降级读九槽（presets 常量内联，必有）。
       应用链（全部保留）：applyPack 整套（L1 override+L2 l2Overrides+L3 iconSet+材质保持+
       跨族屏集合整套切换——v2 桥 __spApplyStyleScreens：data-style-id 屏集显隐+左树重建+curId 页序重映射）、applyPalette 配色级、state 持久化 prototype-style-state、
       恢复原方案（面板底部低调文字按钮）、scheduleSave 标脏。
       UI 版式（用户草图）：卡片=左缩略图右名称/介绍，下「风格令牌」一行人话特征词，
       再下「配色版」3 色块胶囊平铺；勾打在当前应用的那粒胶囊上，只有当前卡有勾；
       页面 2 = 更多风格方向（静态说明：重绘正道+配色版分工+wiki 浏览指引） */
    var presets=__STYLE_PRESETS__,owned=['--accent','--accent-soft','--style-bg','--style-surface','--style-text','--style-muted','--style-line','--style-soft','--style-dark-bg','--style-dark-surface','--style-dark-text','--style-dark-muted','--style-dark-line'];
    /* ---------- 0. state 读写（V1 协议原样延续） ---------- */
    function read(){var n=document.getElementById('prototype-style-state');try{return n?JSON.parse(n.textContent):{id:'original'};}catch(e){return {id:'original'};}}
    function write(state){var n=document.getElementById('prototype-style-state');if(!n){n=document.createElement('script');n.type='application/json';n.id='prototype-style-state';canvas.appendChild(n);}n.textContent=JSON.stringify(state).replace(/</g,'\\u003c');}
    function baseline(){var state=read();if(state.original)return state.original;var values={};owned.forEach(function(k){values[k]=document.documentElement.style.getPropertyValue(k);});return {values:values,dark:document.body.classList.contains('dark')};}
    var OWNED_STATE_KEYS=['schemaVersion','id','presetId','colorId','original','effective','custom','source','packId','familyId','paletteId','domBaseId','material'];
    function writeState(next){
      /* 合并写：只覆盖 chooser 自有键；未知键（R 侧实例覆盖等）原样保留（V1「保留实例覆盖」语义）。
         注意 OWNED 键集是「全量重写」语义——调用方经 ownedFull() 补齐存量 OWNED 键后再传入，
         避免 partial 更新（如只换 palette）意外清掉 original/schemaVersion 等键。 */
      var prev={};try{var parsed=read();if(parsed&&typeof parsed==='object'&&!Array.isArray(parsed))prev=parsed;}catch(e){prev={};}
      var merged={};
      Object.keys(prev).forEach(function(k){if(OWNED_STATE_KEYS.indexOf(k)<0)merged[k]=prev[k];});
      Object.keys(next).forEach(function(k){merged[k]=next[k];});
      write(merged);
    }
    function ownedFull(partial){
      /* 以现 state 的 OWNED 键为底、partial 覆盖 → 全量 OWNED 键集（writeState 的安全前置） */
      var st={};try{var v=read();if(v&&typeof v==='object'&&!Array.isArray(v))st=v;}catch(e){}
      var out={};
      OWNED_STATE_KEYS.forEach(function(k){if(st[k]!==undefined)out[k]=st[k];});
      Object.keys(partial||{}).forEach(function(k){out[k]=partial[k];});
      return out;
    }
    /* ---------- T04 六字段微调核心（TUNE_CORE 段=纯函数原样保留，不改 DOM 不写 state） ---------- */
    var TUNE_FIELDS=['font','fontSize','lineHeight','radius','shadow','space'];
    var ENG_FONT='Microsoft YaHei, PingFang SC, system-ui, sans-serif';
    var FONT_ENUMS=['preset','system','sansCN','serif','mono'];
    var FONT_STACKS={system:'system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, "PingFang SC", "Microsoft YaHei", sans-serif',sansCN:'"PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", system-ui, sans-serif',serif:'Georgia, "Times New Roman", "Songti SC", SimSun, "Noto Serif SC", serif',mono:'ui-monospace, SFMono-Regular, Menlo, Consolas, "Courier New", monospace'};
    var SHADOW_ENUMS=['preset','none','soft','medium','strong'];
    var SHADOW_MAPS={none:'none',soft:'0 2px 8px rgba(15,23,42,.08)',medium:'0 6px 18px rgba(15,23,42,.14)',strong:'0 12px 32px rgba(15,23,42,.22)'};
    var SPACE_ENUMS=[12,16,20];
    function fontKeyOf(v){if(typeof v!=='string')return null;for(var k in FONT_STACKS){if(FONT_STACKS[k]===v)return k;}return null;}
    function shadowKeyOf(v){if(typeof v!=='string')return null;for(var k in SHADOW_MAPS){if(SHADOW_MAPS[k]===v)return k;}return null;}
    function spaceKeyOf(v){return (typeof v==='number'&&SPACE_ENUMS.indexOf(v)>=0)?String(v):null;}
    function numOr(v,d){return (typeof v==='number'&&isFinite(v))?v:d;}
    function tuneBaseline(p){return {font:(p&&typeof p.font==='string'&&p.font)?p.font:ENG_FONT,fontSize:numOr(p&&p.size,14),lineHeight:numOr(p&&p.lineHeight,1.55),radius:numOr(p&&p.radius,14),shadow:(p&&typeof p.shadow==='string'&&p.shadow)?p.shadow:'none',space:numOr(p&&p.space,16)};}
    function tuneNumber(raw,name,min,max,errors){
      if(raw==null||raw==='preset')return null;
      if(typeof raw!=='number'){errors.push({field:name,message:name+'须为数字，不接受带单位/字符串值（收到 '+String(raw)+'）'});return null;}
      if(!isFinite(raw)){errors.push({field:name,message:name+'须为有限数（收到 NaN/Infinity）'});return null;}
      if(raw<min||raw>max){errors.push({field:name,message:name+'超出范围 '+min+'–'+max+'（收到 '+raw+'）'});return null;}
      return raw;
    }
    function normalizeStyleConfig(input,baseline){
      var errors=[];
      var b=tuneBaseline(baseline);
      var src=(input&&typeof input==='object'&&!Array.isArray(input))?input:null;
      if(!src){errors.push({field:'config',message:'微调配置须为对象'});return {valid:false,errors:errors};}
      Object.keys(src).forEach(function(k){if(TUNE_FIELDS.indexOf(k)<0)errors.push({field:k,message:'未知字段（只接受 '+TUNE_FIELDS.join('/')+'）'});});
      var eff={},source={};
      var fv=src.font;
      if(fv==null||fv==='preset'){eff.font=b.font;source.font='preset';}
      else if(typeof fv==='string'&&FONT_ENUMS.indexOf(fv)>=0){eff.font=FONT_STACKS[fv];source.font='custom';}
      else errors.push({field:'font',message:'未知字体档位（允许 preset/system/sansCN/serif/mono）'});
      var nv=tuneNumber(src.fontSize,'fontSize',10,24,errors);
      if(nv==null){eff.fontSize=b.fontSize;source.fontSize='preset';}else{eff.fontSize=nv;source.fontSize='custom';}
      var lv=tuneNumber(src.lineHeight,'lineHeight',1,2.5,errors);
      if(lv==null){eff.lineHeight=b.lineHeight;source.lineHeight='preset';}else{eff.lineHeight=lv;source.lineHeight='custom';}
      var rv=tuneNumber(src.radius,'radius',0,48,errors);
      if(rv==null){eff.radius=b.radius;source.radius='preset';}else{eff.radius=rv;source.radius='custom';}
      var sv=src.shadow;
      if(sv==null||sv==='preset'){eff.shadow=b.shadow;source.shadow='preset';}
      else if(typeof sv==='string'&&SHADOW_ENUMS.indexOf(sv)>=0){eff.shadow=SHADOW_MAPS[sv];source.shadow='custom';}
      else errors.push({field:'shadow',message:'未知阴影档位（允许 preset/none/soft/medium/strong）'});
      var pv=src.space;
      if(pv==null||pv==='preset'){eff.space=b.space;source.space='preset';}
      else if(typeof pv==='number'&&SPACE_ENUMS.indexOf(pv)>=0){eff.space=pv;source.space='custom';}
      else errors.push({field:'space',message:'密度间距档位未知（允许 preset/12/16/20）'});
      if(errors.length)return {valid:false,errors:errors};
      return {valid:true,effective:eff,source:source};
    }
    /* ---------- 1. 受控块解析（与 verify_blocks.py 围栏两形态同构 + JS 注释围栏兼容） ---------- */
    function fenceText(name){
      var html=null;
      try{html=document.documentElement.outerHTML;}catch(e){return null;}
      var m,re;
      re=new RegExp('<!--\\s*'+name+':BEGIN\\s*-->([\\s\\S]*?)<!--\\s*'+name+':END\\s*-->');
      m=html.match(re);if(m)return m[1];
      re=new RegExp("<script\\b[^>]*\\bdata-block=[\"']"+name+"[\"'][^>]*>([\\s\\S]*?)<\\/"+'script>','i');
      m=html.match(re);if(m)return m[1];
      re=new RegExp('/\\*'+name+'_START\\*/([\\s\\S]*?)/\\*'+name+'_END\\*/');
      m=html.match(re);if(m)return m[1];
      return null;
    }
    function parseBlock(name){var t=fenceText(name);if(!t)return null;try{var v=JSON.parse(t);return (v&&typeof v==='object'&&!Array.isArray(v))?v:null;}catch(e){return null;}}
    function blocksValid(reg,pack){
      if(!reg||!pack)return false;
      if(!Array.isArray(reg.families)||!reg.families.length)return false;
      if(!Array.isArray(reg.domBases)||!reg.domBases.length)return false;
      if(!Array.isArray(pack.packs)||!pack.packs.length)return false;
      var famIds={},packIds={},dbIds={};
      reg.families.forEach(function(f){if(f&&f.familyId)famIds[f.familyId]=true;});
      reg.domBases.forEach(function(d){if(d&&d.domBaseId)dbIds[d.domBaseId]=true;});
      pack.packs.forEach(function(p){if(p&&p.packId)packIds[p.packId]=true;});
      var ok=true;
      reg.families.forEach(function(f){if(!famIds[f.familyId]||!dbIds[f.domBaseId])ok=false;});
      pack.packs.forEach(function(p){if(!famIds[p.familyId])ok=false;});
      reg.families.forEach(function(f){(f.members||[]).forEach(function(m){if(!packIds[m])ok=false;});});
      return ok;
    }
    var REGISTRY=parseBlock('STYLE-REGISTRY'),PACKDATA=parseBlock('STYLE-PACK');
    var MODE=blocksValid(REGISTRY,PACKDATA)?'registry':'builtin';
    /* ---------- 2. 统一包模型（两态同构：pack={packId,familyId,identity,tokens,palettes,iconSet,l2Overrides,[builtin],[screenshot]}） ---------- */
    function paletteOf(pack,paletteId){
      var ps=(pack&&Array.isArray(pack.palettes)&&pack.palettes.length)?pack.palettes:[{paletteId:'pal-default',label:'默认',swatches:[]}];
      if(paletteId){for(var i=0;i<ps.length;i++)if(ps[i].paletteId===paletteId)return ps[i];}
      return ps[0];
    }
    function presetToPack(p){
      /* 九槽 id=original 是「本产物原始设计」：名称与色块读产物自身设计令牌（#prototype-design-system），
         不用预设表里的遗留品牌色——否则卡片显示一种颜色、页面实际是另一种 */
      if(p.id==='original'){
        var ds=null;try{var dn=document.getElementById('prototype-design-system');ds=dn?JSON.parse(dn.textContent):null;}catch(e){ds=null;}
        var tk=(ds&&ds.tokens)||{};
        p=Object.assign({},p,{name:'原始方案',summary:'本产物原始设计',
          accent:tk.accent||p.accent,bg:tk.bg||p.bg,text:tk.text||p.text,surface:tk.surface||p.surface});
      }
      return {packId:p.id,familyId:'fam-builtin',
        identity:{styleId:'builtin:'+p.id,styleName:p.name,origin:'builtin',mood:p.summary||''},
        tokens:{},palettes:[{paletteId:'pal-default',label:'默认',swatches:[p.accent,p.bg,p.text,p.surface]}],
        iconSet:null,l2Overrides:null,builtin:p};
    }
    function originalPack(){
      /* 「原始方案」虚拟包：不进任何族成员（面板不显示卡片），仅作 state.id='original' 的
         当前包解析目标——syncLayers 对它输出空 override（保持产物原始样式） */
      var op={packId:'original',familyId:null,identity:{styleId:'builtin:original',styleName:'原始方案',origin:'builtin',mood:''},
        tokens:{},palettes:[],iconSet:null,l2Overrides:null,
        builtin:{id:'original',name:'原始方案',summary:'本产物原始样式',accent:'#e9692d',bg:'#edf1f4',surface:'#ffffff',text:'#173144'}};
      return op;
    }
    function buildModel(){
      if(MODE==='registry'){
        var packs=PACKDATA.packs.slice();
        packs.push(originalPack());
        return {source:'registry',domBases:REGISTRY.domBases,families:REGISTRY.families,packs:packs};
      }
      var bp=presets.map(presetToPack);
      return {source:'builtin',
        domBases:[{domBaseId:'db-main',note:'当前结构',pages:null}],
        families:[{familyId:'fam-builtin',domBaseId:'db-main',label:'内置风格',members:bp.map(function(x){return x.packId;})}],
        packs:bp};
    }
    var MODEL=buildModel();
    function packById(id){for(var i=0;i<MODEL.packs.length;i++)if(MODEL.packs[i].packId===id)return MODEL.packs[i];return null;}
    function familyOf(pack){if(!pack)return null;for(var i=0;i<MODEL.families.length;i++)if(MODEL.families[i].familyId===pack.familyId)return MODEL.families[i];return null;}
    /* tokens → 规范化形态参数（preset 同构形状，供共享规则表消费）。
       键名正本=assets/token-keys.json：一律全小写连字符，逐字读取——不认驼峰/旧别名/
       --sp-color-* 候选名（写错=读不到=落默认；报错由检查脚本负责，运行时不猜）。
       表外但符合 keyPattern 的键=扩展参数：透传成 --sp-<键名>（buildStepTokensCSS 写出）。 */
    var KEY_PATTERN=/^[a-z][a-z0-9]*(-[a-z0-9]+)*$/;
    var DENSITY_WORDS={compact:'紧凑',regular:'适中',loose:'舒展'};
    /* CSS 值安全过滤（纵深防御，唯一出处）：含 ; { } < > 或注释符 /* 的包值一律丢弃（返回 null），
       数字透传。所有进字符串拼接 CSS 的包值（正本键/插值/扩展参数）都过它；报错归检查脚本。 */
    function cssSafe(v){
      if(v==null)return null;
      if(typeof v==='number')return isFinite(v)?v:null;
      var s=String(v);
      if(!s||/[;{}<>]/.test(s)||s.indexOf('/*')>=0)return null;
      return s;
    }
    function cv(t,key){var v=t?t[key]:null;if(typeof v==='string'&&v)return cssSafe(v);if(typeof v==='number'&&isFinite(v))return v;return null;}
    function tokensToParams(pack){
      var t=(pack&&pack.tokens)||{},pal=paletteOf(pack),sw=(pal&&pal.swatches)||[];
      var num=function(v,d){var n=parseFloat(v);return isFinite(n)?n:d;};
      var darkT=(t.dark&&typeof t.dark==='object'&&!Array.isArray(t.dark))?t.dark:null;
      var p={
        name:(pack.identity&&pack.identity.styleName)||pack.packId,
        summary:(pack.identity&&pack.identity.mood)||'',
        accent:cv(t,'primary')||(sw[0]||'#1677ff'),
        bg:cv(t,'bg')||(sw[1]||'#f5f6f8'),
        surface:cv(t,'surface')||(sw[3]||'#ffffff'),
        text:cv(t,'text-primary')||(sw[2]||'#1f2329'),
        muted:cv(t,'text-secondary')||'#626b78',
        line:cv(t,'border')||'#dce1e8',
        radius:num(cv(t,'radius-md'),14),
        shadow:cv(t,'shadow-md')||'none',
        font:cv(t,'font-body')||ENG_FONT,
        size:num(cv(t,'size-body'),14),
        space:num(cv(t,'space-2'),16),
        hero:cv(t,'hero')||null,nav:cv(t,'nav')||null,blur:0,borderWidth:cv(t,'border-width'),
        dark:!!(t.dark===true||darkT),
        darkBg:darkT?(cssSafe(darkT.bg)||'#101318'):null,darkSurface:darkT?(cssSafe(darkT.surface)||'#20252d'):null,
        darkText:darkT?(cssSafe(darkT.text)||'#f3f5fa'):null,darkMuted:darkT?(cssSafe(darkT.muted)||'#b8c0ce'):null,darkLine:darkT?(cssSafe(darkT.line)||'#424b5a'):null
      };
      /* 正本表逐键透传（null=包未提供→页面落 :root 基线），buildStepTokensCSS 据此有值才写 --sp-* */
      p.space1=cv(t,'space-1');p.space2raw=cv(t,'space-2');
      p.space3=cv(t,'space-3');p.space4=cv(t,'space-4');
      p.ctlSm=cv(t,'size-ctl-sm');p.ctlMd=cv(t,'size-ctl-md');p.ctlLg=cv(t,'size-ctl-lg');
      p.sizeTitle=cv(t,'size-title');p.sizeHead=cv(t,'size-head');p.sizeBody=cv(t,'size-body');p.sizeCaption=cv(t,'size-caption');
      p.weightHead=cv(t,'weight-head');p.weightBody=cv(t,'weight-body');
      p.lhHead=cv(t,'line-height-head');p.lhBody=cv(t,'line-height-body');
      p.motionDur=cv(t,'motion-duration-base');p.motionEase=cv(t,'motion-easing-base');
      p.fontHead=cv(t,'font-head');p.fontNum=cv(t,'font-num');
      p.surfaceAlt=cv(t,'surface-alt');
      p.radiusSm=cv(t,'radius-sm');p.radiusMdRaw=cv(t,'radius-md');p.radiusLg=cv(t,'radius-lg');
      p.shadowSm=cv(t,'shadow-sm');p.shadowMdRaw=cv(t,'shadow-md');
      p.gridCols=cv(t,'grid-cols');p.density=cv(t,'density');
      p.okColor=cv(t,'success');p.dangerColor=cv(t,'danger');p.warnColor=cv(t,'warning');
      /* 扩展参数通道：表外键且符合 keyPattern → --sp-<键名> 原样透传；
         非法键（驼峰/下划线/大写）与对象值一律忽略（报错归检查脚本）；
         值安全统一走 cssSafe（与正本通道同一过滤函数） */
      var ext={};
      Object.keys(t).forEach(function(k){
        if(typeof k!=='string'||!KEY_PATTERN.test(k))return;
        var v=t[k];
        if(v==null||typeof v==='object')return;
        var s=cssSafe(String(v));
        if(s==null)return;
        ext[k]=s;
      });
      p.ext=ext;
      if(!p.hero)p.hero=p.accent;
      return p;
    }
    function packParams(pack){return pack&&pack.builtin?pack.builtin:tokensToParams(pack);}
    function packSixBase(pack){return tuneBaseline(packParams(pack));}
    /* ---------- 3. 当前包解析与色板值 ---------- */
    function currentPack(){
      var st=read();
      if(MODE==='registry'){
        var pid=st.packId||st.presetId||st.id;
        var p=packById(pid);
        if(p)return p;
        var f=MODEL.families[0],m=(f&&f.members&&f.members[0])||null;
        return m?packById(m):MODEL.packs[0];
      }
      var bid=st.presetId||st.id;
      var bp=packById(bid);
      return bp||MODEL.packs[0];
    }
    function currentPaletteId(pack){
      var st=read();
      var pal=paletteOf(pack,st.paletteId||st.colorId);
      return pal.paletteId;
    }
    /* ---------- 配色推算（换配色=整页换色，不只按钮） ----------
       swatches 语义（controlled-blocks §2）：[0]主色 [1]底色 [2]文字 [3]表面；
       palette 可带显式 hero/line/muted 字段（写了就全用写的）。
       未写的角色从配色四色推算：
         line/muted —— 算出包原值在「包底色×包文字」连线上的位置，再落到「配色底×配色文字」
                       同位置（包边框/次要文字是独立特征色时不在线上→保留包值，风格特征不丢）；
         soft/浅衬底 —— 配色主色的极淡色；
         hero/横幅 —— palette 显式字段优先；包 hero 缺省（=包主色）或与包主色同族→配色主色，
                       包 hero 是中性色（瑞士黑块）→配色文字色，独立色→保留包值；
         按钮文字 —— 按配色主色亮度定深浅（L>0.35 用配色文字色，否则白）。 */
    function hexToRgb(c){if(typeof c!=='string')return null;var m=c.match(/^#([0-9a-fA-F]{6})$/);if(!m)return null;var n=parseInt(m[1],16);return [(n>>16)&255,(n>>8)&255,n&255];}
    function rgbToHex(r,g,b){function h(v){v=Math.max(0,Math.min(255,Math.round(v))).toString(16);return v.length<2?'0'+v:v;}return '#'+h(r)+h(g)+h(b);}
    function mixHex(a,b,t){var A=hexToRgb(a),B=hexToRgb(b);if(!A||!B)return a;return rgbToHex(A[0]+(B[0]-A[0])*t,A[1]+(B[1]-A[1])*t,A[2]+(B[2]-A[2])*t);}
    /* c 在 bg→text 连线上的投影位置（0=贴底色，1=贴文字）；投影偏差大=独立色 → null */
    function blendPos(c,bg,text){
      var C=hexToRgb(c),B=hexToRgb(bg),T=hexToRgb(text);
      if(!C||!B||!T)return null;
      var dr=T[0]-B[0],dg=T[1]-B[1],db=T[2]-B[2],len2=dr*dr+dg*dg+db*db;
      if(len2<1)return null;
      var t=((C[0]-B[0])*dr+(C[1]-B[1])*dg+(C[2]-B[2])*db)/len2;
      if(t<-0.08||t>1.08)return null;
      var dist=Math.abs(C[0]-(B[0]+dr*t))+Math.abs(C[1]-(B[1]+dg*t))+Math.abs(C[2]-(B[2]+db*t));
      return dist>60?null:Math.max(0,Math.min(1,t));
    }
    function remapBetween(c,fBg,fText,tBg,tText){var t=blendPos(c,fBg,fText);return t==null?c:mixHex(tBg,tText,t);}
    function isNeutral(c){var C=hexToRgb(c);if(!C)return true;var mx=Math.max(C[0],C[1],C[2]),mn=Math.min(C[0],C[1],C[2]);return mx-mn<24;}
    function paletteHero(params,c){
      var ph=params.hero;
      if(!ph||ph===params.accent)return c.accent;
      if(isNeutral(ph))return c.text;
      var rp=blendPos(ph,params.bg,params.accent);
      return rp!=null?mixHex(c.bg,c.accent,rp):ph;
    }
    function paletteColors(pack,paletteId){
      /* paletteId 缺省=当前应用色板（L1 重烘时不传 id，读 state） */
      var pid=(paletteId==null)?currentPaletteId(pack):paletteId;
      var params=packParams(pack),pal=paletteOf(pack,pid),sw=(pal&&pal.swatches)||[];
      var acc=(sw[0]||params.accent),bg=(sw[1]||params.bg),text=(sw[2]||params.text),surface=(sw[3]||params.surface);
      var line=(typeof pal.line==='string'&&pal.line)?pal.line:remapBetween(params.line,params.bg,params.text,bg,text);
      var muted=(typeof pal.muted==='string'&&pal.muted)?pal.muted:remapBetween(params.muted,params.bg,params.text,bg,text);
      var hero=(typeof pal.hero==='string'&&pal.hero)?pal.hero:paletteHero(params,{accent:acc,bg:bg,text:text});
      return {accent:acc,bg:bg,text:text,surface:surface,line:line,muted:muted,hero:hero,
        /* 浅衬底=主色 8% 淡色（从表面向主色走 8%，方向别反——反了就是饱和主色） */
        soft:mixHex(surface,acc,0.08),
        primaryText:primaryText({accent:acc,text:text})};
    }
    function paletteValues(pack,paletteId){
      var pc=paletteColors(pack,paletteId),params=packParams(pack);
      /* 暗色组不随配色推算：暗底必须配浅文字，从深色配色自动反推不可靠 → 恒取包值 */
      return {'--accent':pc.accent,'--accent-soft':hexToRgba2(pc.accent,.1),'--style-bg':pc.bg,'--style-surface':pc.surface,'--style-text':pc.text,'--style-muted':pc.muted,'--style-line':pc.line,'--style-soft':pc.soft,'--style-dark-bg':params.darkBg||'#101318','--style-dark-surface':params.darkSurface||'#20252d','--style-dark-text':params.darkText||'#f3f5fa','--style-dark-muted':params.darkMuted||'#b8c0ce','--style-dark-line':params.darkLine||'#424b5a'};
    }
    function primaryText(params){
      var acc=(params&&typeof params.accent==='string')?params.accent:'';
      if(!/^#[0-9a-fA-F]{6}$/.test(acc))return '#fff';
      var ink=(params&&typeof params.text==='string'&&params.text)?params.text:'#15171c';
      var n=parseInt(acc.slice(1),16),r=(n>>16)&255,g=(n>>8)&255,b=n&255;
      function lin(c){c/=255;return c<=0.03928?c/12.92:Math.pow((c+0.055)/1.055,2.4);}
      var L=0.2126*lin(r)+0.7152*lin(g)+0.0722*lin(b);
      return L>0.35?ink:'#fff';
    }
    function effectiveFor(pack){
      var st=read();
      var e=st.effective;
      if(e&&typeof e==='object'&&!Array.isArray(e)&&TUNE_FIELDS.every(function(k){return e[k]!=null;}))return e;
      var b=packSixBase(pack),c=(st.custom&&typeof st.custom==='object'&&!Array.isArray(st.custom))?st.custom:{},out={};
      TUNE_FIELDS.forEach(function(k){out[k]=(c[k]!=null)?c[k]:b[k];});
      return out;
    }
    /* ---------- 4. CSS 层（L1 override / L2 l2Overrides / L3 iconSet / 材质 / domBase 显隐） ---------- */
    function ensureStyleNode(id){var s=document.getElementById(id);if(!s){s=document.createElement('style');s.id=id;document.head.appendChild(s);}return s;}
    /* 阶梯值规范化：数字/纯数字串补单位（px/ms），带单位串透传，空/null→不写（落 :root 基线） */
    function unitVal(v,unit){if(v==null||v==='')return null;if(typeof v==='number'&&isFinite(v))return v+unit;v=String(v).trim();if(!v)return null;return /^\d+(\.\d+)?$/.test(v)?v+unit:v;}
    function buildStepTokensCSS(p,eff){
      /* L1 换肤阶梯令牌（正本表键 → 页面域变量）：包 tokens 有值才写，缺省落 :root 基线。
         line-height-head 特例：包未提供时写 eff.lineHeight（保持「标题行高随容器/微调」的现状继承行为）。
         本段输出拼在 buildOverrideCSS 的 roots 覆盖节点里——语义色（--ok/--danger/--warn 及
         -soft 浅色）与其余页面变量同节点、同包作用域，切包整节点替换不残留。 */
      var d='';
      var put=function(name,val){val=cssSafe(val);if(val!=null)d+=name+':'+val+';';};
      put('--sp-space-1',unitVal(p.space1,'px'));put('--sp-space-2',unitVal(p.space2raw,'px'));
      put('--sp-space-3',unitVal(p.space3,'px'));put('--sp-space-4',unitVal(p.space4,'px'));
      put('--sp-size-ctl-sm',unitVal(p.ctlSm,'px'));put('--sp-size-ctl-md',unitVal(p.ctlMd,'px'));put('--sp-size-ctl-lg',unitVal(p.ctlLg,'px'));
      put('--sp-size-title',unitVal(p.sizeTitle,'px'));put('--sp-size-head',unitVal(p.sizeHead,'px'));
      put('--sp-size-body',unitVal(p.sizeBody,'px'));put('--sp-size-caption',unitVal(p.sizeCaption,'px'));
      put('--sp-weight-head',p.weightHead);put('--sp-weight-body',p.weightBody);
      put('--sp-line-height-body',unitVal(p.lhBody,''));
      put('--sp-line-height-head',p.lhHead!=null?unitVal(p.lhHead,''):(eff&&eff.lineHeight!=null?eff.lineHeight:null));
      put('--sp-motion-duration-base',unitVal(p.motionDur,'ms'));put('--sp-motion-easing-base',p.motionEase);
      put('--sp-font-head',(typeof p.fontHead==='string'&&p.fontHead)?p.fontHead:null);
      /* 正本表补全通道：次级表面/语义色/圆角阴影阶梯/边框粗细/数字字体/栅格列数。
         --sp-radius-md 与 --sp-shadow-md 为原值档案（--radius/--shadow 仍由 radius-md/shadow-md
         经微调基线 eff 驱动，本函数不动它们）。语义色浅色=主色 12% 透明淡色（与 accent-soft 同思路）。 */
      var softTint=function(c){var rgb=hexToRgb(c);return rgb?('rgba('+rgb[0]+','+rgb[1]+','+rgb[2]+',0.12)'):null;};
      put('--sp-surface-alt',(typeof p.surfaceAlt==='string'&&p.surfaceAlt)?p.surfaceAlt:null);
      put('--ok',p.okColor);put('--ok-soft',softTint(p.okColor));
      put('--danger',p.dangerColor);put('--danger-soft',softTint(p.dangerColor));
      put('--warn',p.warnColor);put('--warn-soft',softTint(p.warnColor));
      put('--sp-radius-sm',unitVal(p.radiusSm,'px'));put('--sp-radius-md',unitVal(p.radiusMdRaw,'px'));put('--sp-radius-lg',unitVal(p.radiusLg,'px'));
      put('--sp-shadow-sm',(typeof p.shadowSm==='string'&&p.shadowSm)?p.shadowSm:null);
      put('--sp-shadow-md',(typeof p.shadowMdRaw==='string'&&p.shadowMdRaw)?p.shadowMdRaw:null);
      put('--sp-border-width',unitVal(p.borderWidth,'px'));
      put('--sp-font-num',(typeof p.fontNum==='string'&&p.fontNum)?p.fontNum:null);
      put('--sp-grid-cols',unitVal(p.gridCols,''));
      var ext=p.ext||{};
      Object.keys(ext).forEach(function(k){put('--sp-'+k,ext[k]);});
      return d;
    }
    function buildOverrideCSS(pack,eff){
      /* packId 纵深防御：不合 ^[A-Za-z0-9_-]+$ 的包不生成覆盖样式（防拼断选择器，报错归检查脚本） */
      if(!pack||!/^[A-Za-z0-9_-]+$/.test(String(pack.packId||'')))return '';
      var packId=pack.packId;
      /* 2026-11-19 K9：转化产物（html[data-conversion]）页面 CSS 自带完整设计，
         组件重写表（.hero 染 hero 色、.card 重新描边等）会以 data-ui-style 高特异性碾压页面样式——
         转化产物只保留 L1 根变量段+暗色段+壳弹层段（换配色核心），跳过组件重写段。 */
      var CONV=document.documentElement.hasAttribute('data-conversion');
      var prefix='html[data-ui-style="'+packId+'"] ',scope=prefix+'#canvas .screen',overlay=prefix+'.proto-ov',modal=prefix+'.mall-modal',roots=[scope,overlay,modal,prefix+'.prototype-media-dialog',prefix+'.proto-result'];
      if(pack.builtin&&pack.builtin.id==='original')return '';
      var p=packParams(pack);
      /* hero 与按钮文字随当前配色推算（applyPalette 落色后 syncLayers 会带着新 state 重建本节点） */
      var pc=paletteColors(pack,null);
      var css='';
      css=roots.join(',')+'{--bg:var(--style-bg);--surface:var(--style-surface);--text:var(--style-text);--muted:var(--style-muted);--muted-2:var(--style-muted);--line:var(--style-line);--line-2:var(--style-line);--soft:var(--style-soft);--radius:'+eff.radius+'px;--shadow:'+(cssSafe(eff.shadow)||'none')+';--style-primary-text:'+(cssSafe(pc.primaryText)||'#fff')+';font-family:'+(cssSafe(eff.font)||ENG_FONT)+';font-size:'+eff.fontSize+'px;line-height:'+eff.lineHeight+';'+buildStepTokensCSS(p,eff)+'}';
      css+=roots.map(function(s){return s.replace(prefix,prefix+'body.dark ');}).join(',')+'{--bg:var(--style-dark-bg);--surface:var(--style-dark-surface);--text:var(--style-dark-text);--muted:var(--style-dark-muted);--muted-2:var(--style-dark-muted);--line:var(--style-dark-line);--line-2:var(--style-dark-line);--soft:var(--style-dark-bg)}';
      css+=[modal,prefix+'.prototype-media-dialog',prefix+'.proto-result',overlay+' .ov-panel'].join(',')+'{background:var(--surface);color:var(--text);border-radius:'+eff.radius+'px}';
      if(!CONV){
      var rules={
        '.viewport,.app,.adpage,.ad-main,.mall-content,.mall-admin,.mall-admin-main':'background:var(--bg);color:var(--text);font-family:inherit',
        '.appbar,.statusbar,.tabbar,.adtop,.mall-bottom,.mall-admin-top':'background:'+(cssSafe(p.nav)||'var(--surface)')+';color:var(--text);border-color:var(--line);backdrop-filter:blur('+(p.blur||0)+'px)',
        '.card,.mall-product,.mall-cart-line,.mall-order-card,.mall-address,.mall-manual,.mall-record,.list,.stat,.prototype-media,.mall-table-wrap,.mall-table-scroll,.tbl-wrap,.mall-cart-summary,.mall-grid-form,.mall-stats>div,.mall-chat .bubble':'background:var(--surface);color:var(--text);border:var(--sp-border-width,1px) solid var(--line);border-radius:'+eff.radius+'px;box-shadow:'+(cssSafe(eff.shadow)||'none'),
        '.card-h,.card-b,.li,.mall-product-info,.mall-summary':'color:var(--text);border-color:var(--line)',
        '.b,.ipt,.fs,.mall-field input,.mall-field select,.mall-field textarea,.mall-history button,.mall-cart-ops button,.prototype-media-fields input,.prototype-media-fields select,.prototype-media-fields textarea,.prototype-media-dialog footer button':'border-radius:'+Math.min(eff.radius,22)+'px;border-color:var(--line);font-family:inherit',
        '.b:not(.pri):not(.dan),.ipt,.fs,.mall-field input,.mall-field select,.mall-field textarea,.mall-cart-ops button,.prototype-media-fields input,.prototype-media-fields select,.prototype-media-fields textarea,.prototype-media-dialog footer button:not(.pri)':'background:var(--surface);color:var(--text)',
        'button,input,select,textarea':'font-family:inherit',
        '.b.pri':'background:var(--accent);color:var(--style-primary-text);font-weight:var(--sp-weight-head,600)',
        '.b.pri strong,.b.pri b,.b.pri span':'color:inherit',
        '.mall-methods .b.selected,.tag.accent,.chip.on,.mall-chat .bubble.mine':'background:var(--accent-soft);color:var(--accent);border-color:var(--accent)',
        '.tag,.imgbox,.list.flat .li,.li .av:not(.r),.gt,.fnode,.up,.segs.pill,.chip,.note,.pager span,.prototype-media-stage img,.prototype-media-stage video':'border-radius:'+Math.min(eff.radius,16)+'px',
        '.imgbox,.chip,.segs.pill':'background:var(--soft);color:var(--muted);border-color:var(--line)',
        '.segs.pill .sg.on':'background:var(--surface);color:var(--text)',
        '.mall-content':'padding:'+eff.space+'px;gap:'+Math.max(10,eff.space-2)+'px',
        '.mall-hero,.mall-profile,.mall-wallet,.mall-poster,.hero':'background:'+(cssSafe(pc.hero)||'var(--accent)')+';color:white;border-radius:'+eff.radius+'px;box-shadow:'+(cssSafe(eff.shadow)||'none'),
        '.mall-hero h1,.mall-hero p,.mall-hero strong,.mall-profile h2,.mall-profile p,.mall-wallet h2,.mall-wallet p,.mall-poster h2,.mall-poster p':'color:#fff',
        '.mall-hero .b:not(.pri)':'background:rgba(255,255,255,.12);color:#fff;border-color:rgba(255,255,255,.35)',
        '.mall-admin-side,.side':'background:'+pc.hero+';color:#fff',
        '.mall-admin-side .b:not(.pri),.side .ni':'background:transparent;color:#fff;border-color:transparent',
        '.mall-admin-side .b:hover,.side .ni.on':'background:var(--accent);color:var(--style-primary-text)',
        '.mall-admin table,.mall-admin th,.mall-admin td,table.tbl td':'background:var(--surface);color:var(--text);border-color:var(--line)',
        'table.tbl th':'background:var(--soft);color:var(--muted);border-color:var(--line)',
        '.mall-stats>div':'color:var(--muted)',
        '.mall-chart>div':'background:var(--accent)',
        '.mall-badge':'background:var(--accent-soft);color:var(--accent)',
        '.mall-detail-image,.mall-cart-line img,.mall-product img':'background:var(--soft)',
        '.mall-price,.mall-detail-price':'color:var(--accent)',
        '.mall-note':'background:var(--soft);color:var(--text)',
        'h1,h2,h3,h4,strong,.h1,.h2,.h3,.appbar .t':'color:var(--text);font-family:var(--sp-font-head,inherit)',
        '.mall-product-info small,.mall-sub,.mall-field,.mall-history':'color:var(--muted)'
      };
      Object.keys(rules).forEach(function(selectors){css+=selectors.split(',').flatMap(function(s){return roots.map(function(r){return r+' '+s;});}).join(',')+'{'+rules[selectors]+'}';});
      }
      css+=prefix+'.prototype-media-dialog footer button{border-radius:'+Math.min(eff.radius,22)+'px;border-color:var(--line);font-family:inherit}';
      css+=prefix+'.prototype-media-dialog footer button:not(.pri){background:var(--surface);color:var(--text)}';
      css+=prefix+'body.dark #canvas .screen .appbar,'+prefix+'body.dark #canvas .screen .statusbar,'+prefix+'body.dark #canvas .screen .mall-bottom,'+prefix+'body.dark #canvas .screen .tabbar,'+prefix+'body.dark #canvas .screen .mall-admin-top{background:var(--surface)}';
      if(!CONV)css+=scope+' .mall-hero h1,'+scope+' .mall-hero strong{color:#fff}';
      return css;
    }
    /* L2：l2Overrides 按组件类重写外观（scoped 到页面容器；每条 {selector,props}）。
       前缀带 html[data-ui-style=packId]：与 L1 同特异性且节点更靠后——族内皮差异稳定压过 L1 基线，
       切包时整节点内容替换，旧包 L2 不残留。 */
    function buildL2CSS(pack){
      var ov=pack&&Array.isArray(pack.l2Overrides)?pack.l2Overrides:null;
      if(!ov||!ov.length)return '';
      /* packId 纵深防御：不合 ^[A-Za-z0-9_-]+$ 的包不生成覆盖样式 */
      if(!/^[A-Za-z0-9_-]+$/.test(String(pack.packId||'')))return '';
      var prefix='html[data-ui-style="'+pack.packId+'"] ';
      var scopes=[prefix+'#canvas .screen .viewport',prefix+'#canvas .screen',prefix+'.proto-ov .ov-panel'];
      var css='';
      ov.forEach(function(o){
        if(!o||typeof o.selector!=='string'||typeof o.props!=='string'||!o.selector||!o.props)return;
        /* 纵深防御：props 含 { } < > 或注释符的条目整条跳过（可跳出规则块注入 CSS；
           ; 是声明分隔符，保留。报错归检查脚本） */
        if(/[{}<>]/.test(o.props)||o.props.indexOf('/*')>=0)return;
        o.selector.split(',').forEach(function(sel){
          sel=sel.trim();if(!sel)return;
          /* 纵深防御：选择器含 { } < > " 或注释符的条目整条跳过（报错归检查脚本） */
          if(/[{}<>"]/.test(sel)||sel.indexOf('/*')>=0)return;
          css+=scopes.map(function(sc){return sc+' '+sel;}).join(',')+'{'+o.props+'}';
        });
      });
      return css;
    }
    /* L3：iconSet 图标族显隐——产物含 sprite 子系统（[data-style-sprite] 容器，每 iconSet 一套内联 sprite）
       时按包显隐；当前生成链路未建 sprite 子系统 = 空实现（no-op），子系统出现后此处即刻生效 */
    function applyIconSet(iconSet){
      var sprites=document.querySelectorAll('#canvas [data-style-sprite]');
      if(!sprites.length)return {applied:false,reason:'no-sprite-subsystem'};
      var n=0;
      sprites.forEach(function(node){
        var on=!iconSet||node.getAttribute('data-style-sprite')===iconSet;/* iconSet 空=不约束（全显，恢复原状语义） */
        node.style.display=on?'':'none';
        if(on)n++;
      });
      return {applied:true,matched:n};
    }
    /* 材质叠加（令牌级：像素/手绘/毛玻璃/拟物，可组合，不动骨架）。
       材质=用户显式叠加语义，规则用 !important 压过 L1 形态（工程取舍：材质优先级最高）。 */
    var MATERIAL_KEYS=['pixel','sketch','glass','skeuo'];
    var MATERIAL_NAMES={pixel:'像素',sketch:'手绘',glass:'毛玻璃',skeuo:'拟物'};
    function buildMaterialCSS(onMap){
      var css='';
      var sel='#canvas .screen';
      if(onMap.pixel){
        css+=sel+'{--radius:0px;--shadow:none}';
        css+=sel+' .card,'+sel+' .b,'+sel+' .ipt,'+sel+' .imgbox,'+sel+' .chip,'+sel+' .tag,'+sel+' .fs,'+sel+' .segs{border-radius:0!important;box-shadow:none!important}';
        css+=sel+' .card{border:2px solid var(--line)!important}';
        css+=sel+' img{image-rendering:pixelated}';
        css+=sel+' .b.pri{border:2px solid var(--text)!important;box-shadow:3px 3px 0 var(--line)!important}';
      }
      if(onMap.sketch){
        css+=sel+' .card,'+sel+' .imgbox,'+sel+' .chip{border-radius:14px 18px 12px 20px/18px 12px 20px 14px!important;border:2px solid var(--text)!important;box-shadow:2px 3px 0 rgba(21,32,43,.18)!important}';
        css+=sel+' .b{border-radius:12px 16px 10px 18px/16px 10px 18px 12px!important;border:1.5px solid var(--text)!important;background:var(--surface)!important}';
        css+=sel+' .b.pri{background:var(--accent)!important;color:var(--style-primary-text,#fff)!important}';
      }
      if(onMap.glass){
        css+=sel+' .card,'+sel+' .appbar,'+sel+' .tabbar,'+sel+' .stat,'+sel+' .list{background:color-mix(in srgb,var(--surface) 55%,transparent)!important;-webkit-backdrop-filter:blur(14px);backdrop-filter:blur(14px);border:1px solid color-mix(in srgb,var(--line) 70%,transparent)!important;box-shadow:0 8px 28px rgba(18,28,45,.10)!important}';
        css+=sel+' .viewport,'+sel+' .app{background:linear-gradient(150deg,color-mix(in srgb,var(--bg) 82%,var(--accent) 4%),var(--bg))!important}';
      }
      if(onMap.skeuo){
        css+=sel+' .card,'+sel+' .stat,'+sel+' .list{background:linear-gradient(180deg,color-mix(in srgb,var(--surface) 92%,#fff) 0%,var(--surface) 55%,color-mix(in srgb,var(--surface) 90%,#000)) 100%)!important;box-shadow:0 1px 2px rgba(0,0,0,.18),0 10px 24px rgba(0,0,0,.16),inset 0 1px 0 rgba(255,255,255,.65)!important;border:1px solid color-mix(in srgb,var(--line) 80%,#000)!important}';
        css+=sel+' .b{box-shadow:0 1px 0 rgba(255,255,255,.7) inset,0 2px 3px rgba(0,0,0,.16)!important}';
        css+=sel+' .b.pri{background:linear-gradient(180deg,color-mix(in srgb,var(--accent) 84%,#fff),var(--accent))!important;box-shadow:0 1px 0 rgba(255,255,255,.4) inset,0 3px 6px color-mix(in srgb,var(--accent) 45%,#000)!important}';
      }
      return css;
    }
    function currentMaterials(){
      var st=read(),m=(st.material&&typeof st.material==='object'&&!Array.isArray(st.material))?st.material:{};
      var out={};MATERIAL_KEYS.forEach(function(k){out[k]=!!m[k];});return out;
    }
    function applyMaterials(){
      var onMap=currentMaterials();
      var node=ensureStyleNode('prototype-style-material');
      var css=buildMaterialCSS(onMap);
      var keys=MATERIAL_KEYS.filter(function(k){return onMap[k];});
      if(keys.length)document.documentElement.setAttribute('data-style-material',keys.join(' '));
      else document.documentElement.removeAttribute('data-style-material');
      if(node.textContent!==css)node.textContent=css;
      return onMap;
    }
    /* v2 多风格：切卡联动=section 级显隐+curId 页序重映射+左树重建，委托 seed 桥
       （值域=domBaseId 直通零转换，钉死点1）；桥不存在时回落 v1 屏内容器显隐（兼容旧产物）。 */
    function applyDomBase(domBaseId){
      /* 排查 P1-7 同语义：空值透传给桥，由桥按产物基域兜底（baseStyleId），chooser 侧不硬编码 db-main */
      if(window.__spApplyStyleScreens){return window.__spApplyStyleScreens(domBaseId);}
      var applied=0;
      document.querySelectorAll('#canvas .screen').forEach(function(scr){
        var nodes=scr.querySelectorAll('[data-dom-base]');
        if(nodes.length<2)return;
        nodes.forEach(function(n){
          var on=!domBaseId||n.getAttribute('data-dom-base')===domBaseId;
          n.style.display=on?'':'none';
          if(on)applied++;
        });
      });
      return applied;
    }
    function hasDomBaseDom(domBaseId){
      /* v2 多风格：屏集合存在性判定（data-style-id=domBaseId）；回落 v1 容器查法 */
      if(document.querySelector('#canvas .screen[data-style-id="'+domBaseId+'"]'))return true;
      return !!document.querySelector('#canvas [data-dom-base="'+domBaseId+'"]');
    }
    /* ---------- 5. 提交口（切换五档的实现入口） ---------- */
    function syncLayers(pack){
      /* 应用某包的全套表现层：L1 override + L2 + L3 + 材质保持 + domBase 显隐 */
      var eff=effectiveFor(pack);
      var root=document.documentElement;
      var style=ensureStyleNode('prototype-style-override');
      var css=buildOverrideCSS(pack,eff);
      if(style.textContent!==css)style.textContent=css;
      if(!pack.builtin||pack.builtin.id!=='original'){if(root.getAttribute('data-ui-style')!==pack.packId)root.setAttribute('data-ui-style',pack.packId);}
      else root.removeAttribute('data-ui-style');
      var l2=ensureStyleNode('prototype-style-l2');
      var l2css=buildL2CSS(pack);
      if(l2.textContent!==l2css)l2.textContent=l2css;
      applyIconSet(pack.iconSet);
      applyMaterials();
    }
    function applyPack(packId,paletteId){
      var pack=packById(packId);
      if(!pack)return {ok:false,reason:'no-pack'};
      var fam=familyOf(pack);
      var cur=currentPack();
      var curFam=familyOf(cur);
      /* 档5：跨族且产物内没有该族 DOM = 出口提示，产物内不长新族 */
      if(fam&&curFam&&fam.familyId!==curFam.familyId&&!hasDomBaseDom(fam.domBaseId)){
        toast('「'+((pack.identity&&pack.identity.styleName)||packId)+'」需要重新生成原型后才能切换');
        return {ok:false,reason:'cross-family-no-dom'};
      }
      var pal=paletteOf(pack,paletteId);
      var r=applyStyleConfigOn({values:paletteValues(pack,pal.paletteId),dark:!!packParams(pack).dark},'live',{commit:true});
      if(!r||!r.ok){toast('样式提交失败，请重试');return {ok:false,reason:'hook'};}
      /* 切包=新微调上下文：custom/effective 重置为新包基线（微调跟随当前应用包，不跨包泄漏）；
         state 先写（syncLayers 的 effectiveFor 读 state） */
      var eff=packSixBase(pack);
      writeState(ownedFull({schemaVersion:2,source:MODE,id:pack.packId,packId:pack.packId,familyId:familyIdOf(pack),
        presetId:pack.packId,paletteId:pal.paletteId,colorId:pal.paletteId,
        original:(r.original!=null?r.original:read().original||null),effective:eff,
        custom:{},domBaseId:(fam&&fam.domBaseId)||null,material:currentMaterials()}));
      syncLayers(pack);
      if(fam&&curFam&&fam.familyId!==curFam.familyId)applyDomBase(fam.domBaseId);/* 档4：跨族多 DOM 显隐 */
      else if(read().domBaseId)applyDomBase(null);
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      toast('已应用「'+((pack.identity&&pack.identity.styleName)||packId)+'」，点击保存写回当前HTML');
      return {ok:true,packId:pack.packId,paletteId:pal.paletteId};
    }
    function familyIdOf(pack){var f=familyOf(pack);return f?f.familyId:null;}
    function applyPalette(paletteId,packId){
      /* 档1：色板级切换——只换 palette（写值最快，形态层不动）。
         胶囊挂在卡片上：点的是「该卡片的包」——若它尚未应用（原始方案/其他包），
         先应用该包再落色板（applyPack 一步到位）；packId 缺省=当前应用包。 */
      var pack=(packId&&packById(packId))||currentPack();
      if(!pack){toast('未找到该风格包');return {ok:false,reason:'no-pack'};}
      var cur=currentPack();
      if(cur.packId!==pack.packId)return applyPack(pack.packId,paletteId);
      if(!pack.palettes||pack.palettes.length<2){toast('当前风格只有一个配色（该包未提供色板变体）');return {ok:false,reason:'single-palette'};}
      var pal=paletteOf(pack,paletteId);
      if(paletteId&&pal.paletteId!==paletteId){toast('未找到该配色');return {ok:false,reason:'no-palette'};}
      var st=read();
      var r=applyStyleConfigOn({values:paletteValues(pack,pal.paletteId),dark:!!packParams(pack).dark},'live',{commit:true});
      if(!r||!r.ok){toast('样式提交失败，请重试');return {ok:false,reason:'hook'};}
      writeState(ownedFull({paletteId:pal.paletteId,colorId:pal.paletteId}));
      /* 换配色也要重建 L1：hero/按钮文字按新配色推算（旧实现只写根变量，L1 里烘死的包色不动） */
      syncLayers(pack);
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      toast('已切换配色「'+(pal.label||pal.paletteId)+'」');
      return {ok:true,paletteId:pal.paletteId};
    }
    function setMaterial(key,on){
      if(MATERIAL_KEYS.indexOf(key)<0)return {ok:false,reason:'unknown-material'};
      var m=currentMaterials();m[key]=!!on;
      /* 材质只动叠加层+state，不重写根色不碰 body.dark（applyStyleConfigOn 会整条覆写根变量，此处禁用）；
         但 state 变更须随草稿持久化（V1 apply 同款 scheduleSave，不压 undo 栈） */
      writeState(ownedFull({material:m}));
      scheduleSave();
      applyMaterials();
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      toast('材质「'+MATERIAL_NAMES[key]+'」已'+(on?'开启（叠加在当前风格上）':'关闭'));
      return {ok:true,material:m};
    }
    /* T04 微调提交口（V1 签名兼容：presetId/palette/tune；V2 扩展 packId/paletteId） */
    function applyStyleConfig(config){
      var cfg=(config&&typeof config==='object')?config:{};
      var pack=packById(cfg.packId||cfg.presetId||cfg.id);
      if(!pack||(pack.builtin&&pack.builtin.id==='original')){toast('微调需先应用一个风格方案（原始方案不支持形态微调）');return {ok:false,reason:'no-preset'};}
      if(!editorAllowed(function(){applyStyleConfig(config);}))return {ok:false,reason:'locked'};
      var pal=paletteOf(pack,cfg.paletteId||cfg.colorId);
      var base=packSixBase(pack);
      var n=normalizeStyleConfig(cfg.tune||cfg.custom||{},base);
      if(!n.valid){var e0=n.errors[0];toast('微调未生效：'+e0.field+'——'+e0.message+(n.errors.length>1?('（共 '+n.errors.length+' 项未通过）'):''));return {ok:false,errors:n.errors};}
      var r=applyStyleConfigOn({values:paletteValues(pack,pal.paletteId),dark:!!packParams(pack).dark},'live',{commit:true});
      if(!r||!r.ok){toast('样式提交失败，请重试');return {ok:false,reason:'hook'};}
      var custom={};
      TUNE_FIELDS.forEach(function(k){if(n.source[k]==='custom'&&n.effective[k]!==base[k])custom[k]=n.effective[k];});
      writeState(ownedFull({schemaVersion:2,source:MODE,id:pack.packId,packId:pack.packId,familyId:familyIdOf(pack),presetId:pack.packId,paletteId:pal.paletteId,colorId:pal.paletteId,original:(r.original!=null?r.original:read().original||null),effective:n.effective,custom:custom,material:currentMaterials()}));
      syncLayers(pack);
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      var tweaked=Object.keys(custom).length>0;
      toast('已应用「'+((pack.identity&&pack.identity.styleName)||pack.packId)+(tweaked?'·已微调':'')+' × '+(pal.label||'默认')+'」，点击保存写回当前HTML');
      return {ok:true,packId:pack.packId,paletteId:pal.paletteId,effective:n.effective,custom:custom};
    }
    function restorePreset(){
      var st=read(),pack=currentPack();
      if(!pack||(pack.builtin&&pack.builtin.id==='original')||(st.packId&&st.packId==='original')){toast('当前未应用风格方案，无预设形态可恢复');return {ok:false,reason:'no-preset'};}
      var pal=paletteOf(pack,st.paletteId||st.colorId);
      applyStyleConfigOn({values:paletteValues(pack,pal.paletteId),dark:!!packParams(pack).dark},'live',{restore:true});
      var eff=packSixBase(pack);
      writeState(ownedFull({effective:eff,custom:{}}));
      scheduleSave();/* 恢复也是 state 变更：随草稿持久化（同 setMaterial 纪律），否则刷新即回卷 */
      syncLayers(pack);
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      toast('已恢复「'+((pack.identity&&pack.identity.styleName)||pack.packId)+'」预设形态（微调已清除，实例覆盖保留）');
      return {ok:true,packId:pack.packId,effective:eff};
    }
    function restoreOriginal(){
      var st=read();
      /* 交付初始风格语义（--active-pack 构建注入 initialPackId）：恢复=回到交付时的样子
         （initialPackId 包+默认色板整套，清材质/微调残留）；无 initialPackId 走原语义
         （回产物原始基线）。旧产物/九槽降级件行为不变。 */
      if(st.initialPackId&&MODE==='registry'){
        var ip=packById(st.initialPackId);
        if(ip&&!(ip.builtin&&ip.builtin.id==='original')){
          var ipal=paletteOf(ip,null);
          var r=applyStyleConfigOn({values:paletteValues(ip,ipal.paletteId),dark:!!packParams(ip).dark},'live',{restore:true});
          if(!r||!r.ok){toast('样式提交失败，请重试');return {ok:false,reason:'hook'};}
          var ifam=familyOf(ip);
          writeState(ownedFull({schemaVersion:2,source:MODE,id:ip.packId,packId:ip.packId,familyId:familyIdOf(ip),
            presetId:ip.packId,paletteId:ipal.paletteId,colorId:ipal.paletteId,
            original:(st.original||null),effective:packSixBase(ip),custom:{},
            domBaseId:(ifam&&ifam.domBaseId)||null,material:{}}));
          syncLayers(ip);
          if(ifam&&ifam.domBaseId)applyDomBase(ifam.domBaseId);
          else if(read().domBaseId)applyDomBase(null);
          scheduleSave();/* 恢复是用户操作：标脏随草稿持久化（同原语义纪律） */
          if(window.__spPanelRefresh)window.__spPanelRefresh();
          toast('已恢复交付时的风格「'+((ip.identity&&ip.identity.styleName)||ip.packId)+'」');
          return {ok:true,packId:ip.packId,paletteId:ipal.paletteId,restored:'initial'};
        }
      }
      var o=st.original;
      if(!o||!o.values||typeof o.values!=='object'){toast('没有可恢复的原始方案（本件未动过风格或为旧版文件）');return {ok:false,reason:'no-original'};}
      
      document.documentElement.removeAttribute('data-ui-style');
      /* 内联通道清场：包根变量写在 <html> style 上（seed applyStyleConfigOn 同款 13 键先清后写），
         只清三节点清不掉——2026-11-24 实测 restore 后 --accent 残留 pk 值（token_pipeline T-restore 抓住） */
      owned.forEach(function(k){document.documentElement.style.removeProperty(k);});
      ensureStyleNode('prototype-style-override').textContent='';
      ensureStyleNode('prototype-style-l2').textContent='';
      ensureStyleNode('prototype-style-material').textContent='';
      document.documentElement.removeAttribute('data-style-material');
      applyDomBase(null);
      applyIconSet(null);
      writeState(ownedFull({id:'original',presetId:'original',packId:null,familyId:null,paletteId:null,colorId:null,effective:null,custom:{},domBaseId:null,material:{}}));
      scheduleSave();/* 恢复也是 state 变更：随草稿持久化（同 setMaterial 纪律），否则刷新即回卷 */
      if(window.__spPanelRefresh)window.__spPanelRefresh();
      toast('已恢复原始方案（完整基线：颜色＋字体＋行高＋形态实际值；材质与皮肤层已卸）');
      return {ok:true};
    }
    /* ---------- 6. render（幂等重算；MutationObserver 触发，V1 机制延续） ---------- */
    function render(){
      var pack=currentPack();
      syncLayers(pack);
      var st=read();
      if(st.domBaseId)applyDomBase(st.domBaseId);/* state 记的是 domBaseId（applyPack 写 fam.domBaseId） */
    }
    /* ---------- 7. 面板 UI（双 Tab） ---------- */
    function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}
    function sourceBadgeText(){
      if(MODE==='registry'){
        var fams=MODEL.families.length,packs=MODEL.packs.length-(MODEL.packs.some(function(x){return x.packId==='original';})?1:0);
        return '数据源：风格登记块（'+fams+' 族 · '+packs+' 包）';
      }
      return '数据源：内置九槽预设（本产物未含风格登记块）';
    }
    function thumbHTML(pack){
      var shot=(typeof pack.screenshot==='string'&&/^data:image\//.test(pack.screenshot))?pack.screenshot:null;
      if(shot)return '<img class="ed-sp-shot" src="'+shot+'" alt="">';
      /* 色板条缩略（构建期无截图时的降级形态，spec §二） */
      var pal=paletteOf(pack,read().packId===pack.packId?read().paletteId:null);
      var sw=(pal&&pal.swatches&&pal.swatches.length)?pal.swatches:[];
      var params=packParams(pack);
      var four=[sw[0]||params.accent,sw[1]||params.bg,sw[3]||params.surface,sw[2]||params.text];
      return '<span class="ed-sp-palbar">'+four.map(function(c){return '<i style="background:'+esc(c)+'"></i>';}).join('')+'</span>';
    }
    /* 风格令牌行：包 tokens → 3-4 个人话特征词（主色名/圆角档/字体/间距档），不出现键名或数值 */
    function colorWord(c){
      if(typeof c!=='string'||c.charAt(0)!=='#')return null;
      var m=c.match(/^#([0-9a-fA-F]{6})$/);if(!m)return null;
      var n=parseInt(m[1],16),r=(n>>16)&255,g=(n>>8)&255,b=n&255;
      var mx=Math.max(r,g,b),mn=Math.min(r,g,b),l=(mx+mn)/510;
      if(mx-mn<18)return l>0.82?'浅灰':(l<0.25?'炭黑':'灰');
      var d=(mx-mn)/255,h;
      if(mx===r)h=60*(((g-b)/255)/d%6);else if(mx===g)h=60*(((b-r)/255)/d+2);else h=60*(((r-g)/255)/d+4);
      if(h<0)h+=360;
      var base=h<14?'红':h<38?'橘':h<55?'琥珀':h<70?'黄':h<95?'青柠':h<150?'绿':h<175?'薄荷':h<200?'青':h<225?'天蓝':h<255?'蓝':h<285?'靛蓝':h<320?'紫':h<345?'洋红':'玫红';
      if(l<0.32)return '深'+base;if(l>0.78)return '浅'+base;return base;
    }
    function radiusWord(v){v=Math.round(Number(v)||0);return v<=2?'直角':v<=8?'硬朗':v<=15?'适中':v<=24?'圆润':'特圆';}
    function fontWord(f){
      /* 看字体栈首选字体（栈尾 sans-serif/serif 是兜底关键字，不代表风格） */
      var first=String(f||'').split(',')[0].replace(/["']/g,'').trim().toLowerCase();
      if(/mono|consolas|menlo|courier/.test(first))return '等宽';
      if(/^serif$|georgia|times|songti|simsun|宋|serif sc|noto serif|playfair|garamond/.test(first))return '衬线';
      return '无衬线';
    }
    function spaceWord(v){v=Math.round(Number(v)||16);return v<=13?'紧凑':v<=17?'适中':'舒展';}
    function humanTokens(pack){
      var p=packParams(pack),out=[],seen={};
      function push(w){if(w&&!seen[w]&&out.length<4){seen[w]=1;out.push(w);}}
      if(p.dark)push('深色');
      push(colorWord(p.accent));push(radiusWord(p.radius));
      /* 密度词：包 tokens 的 density 键优先（compact=紧凑/regular=适中/loose=舒展）。
         显式 density 优先于字体词占位——暗色包四槽占满时密度词仍可见；
         包未提供 density 时回退按 space-2 间距推断（末位，行为同旧）。 */
      push(DENSITY_WORDS[p.density]);
      push(fontWord(p.font));
      if(!DENSITY_WORDS[p.density]&&!p.dark)push(spaceWord(p.space));
      return out.join(' · ');
    }
    /* 风格卡（页面 1）：左缩略图右名称/介绍，下「风格令牌」行，「配色版」3 色块胶囊平铺；
       勾打在当前应用的那粒胶囊上（勾角标+描边高亮），只有当前卡有勾；卡右上角不放勾 */
    function cardHTML(pack,curPack){
      var fam=familyOf(pack),curFam=familyOf(curPack);
      var cross=!!(fam&&curFam&&fam.familyId!==curFam.familyId);
      var crossNoDom=cross&&!hasDomBaseDom(fam.domBaseId);
      var isOn=curPack.packId===pack.packId;
      var curPalId=isOn?currentPaletteId(pack):null;
      var name=(pack.identity&&pack.identity.styleName)||pack.packId;
      var mood=(pack.identity&&pack.identity.mood)||'';
      var pals=(pack.palettes&&pack.palettes.length)?pack.palettes:[{paletteId:'pal-default',label:'默认',swatches:[]}];
      return '<div class="ed-sp-card'+(isOn?' is-on':'')+(crossNoDom?' is-regen':'')+'" data-pack="'+esc(pack.packId)+'" role="button" tabindex="0" aria-pressed="'+isOn+'">'
        +(crossNoDom?'<span class="ed-sp-regen">需重新生成</span>':'')
        +'<span class="ed-sp-head"><span class="ed-sp-thumb">'+thumbHTML(pack)+'</span>'
        +'<span class="ed-sp-meta"><b class="ed-sp-name">'+esc(name)+'</b><i class="ed-sp-mood">'+esc(mood)+'</i></span></span>'
        +'<span class="ed-sp-tokens"><i>风格令牌</i>'+esc(humanTokens(pack))+'</span>'
        +'<span class="ed-sp-palsec"><i class="ed-sp-palslabel">配色版</i><span class="ed-sp-pals">'
        +pals.map(function(pal){
          var sw=(pal.swatches||[]).slice(0,3);
          if(!sw.length){var pp=packParams(pack);sw=[pp.accent,pp.bg,pp.text];}
          var on=isOn&&pal.paletteId===curPalId;
          return '<button type="button" class="ed-sp-pal'+(on?' on':'')+'" data-pal="'+esc(pal.paletteId)+'" aria-pressed="'+on+'" title="配色：'+esc(pal.label||pal.paletteId)+'">'
            +'<span class="ed-sp-palsw">'+sw.map(function(c){return '<i style="background:'+esc(c)+'"></i>';}).join('')+'</span>'
            +(on?'<span class="ed-sp-palcheck" title="当前配色">✓</span>':'')
            +'</button>';
        }).join('')
        +'</span></span></div>';
    }
    /* 2026-11-21 用户定案：点「更多风格方向」→ 模态弹窗（竖向时间线四步）。
       四步按客户动作链切（打开库→选+复制→装→执行），每步一个成果：
       库打开→提示词到手→技能装好→替换完成。第③步下载+安装一体（放进产物文件夹=装好）。
       RESKIN_SKILL_URL 由 wiki 项目方发布技能包后填入，空=按钮灰显「即将上线」。 */
    var RESKIN_SKILL_URL='';
    function openReskinDialog(){
      var dlg=document.getElementById('spReskinDialog');
      if(!dlg){
        dlg=document.createElement('dialog');
        dlg.id='spReskinDialog';
        dlg.className='ed-sp-dialog workspace-runtime-ui';
        dlg.innerHTML='<header><strong>想换一个完整风格？</strong><button type="button" class="tb" data-sp-dlg-close>✕</button></header>'
          +'<div class="ed-sp-dialog-body">'
          +'<p class="ed-sp-dialog-lead">换风格会按新风格<b>重画全部页面</b>，跑完本产物内就多一套可切换的新风格（原风格保留，随时切回）。</p>'
          +'<div class="ed-sp-dialog-steps">'
          +'<div class="ed-sp-step"><span class="ed-sp-stepno">1</span><div class="ed-sp-stepmain"><b>打开风格库</b>'
          +'<div class="ed-sp-stepd">风格库 wiki 里浏览全部风格方向。 <a href="https://design-style-wiki.pages.dev" target="_blank" rel="noopener" class="ed-sp-wikilink">打开风格库 →</a></div></div></div>'
          +'<div class="ed-sp-step"><span class="ed-sp-stepno">2</span><div class="ed-sp-stepmain"><b>选风格、复制提示词</b>'
          +'<div class="ed-sp-stepd">挑一个心仪的风格，在它的风格卡上复制完整提示词——每张卡都自带。</div></div></div>'
          +'<div class="ed-sp-step"><span class="ed-sp-stepno">3</span><div class="ed-sp-stepmain"><b>下载安装技能</b>'
          +'<div class="ed-sp-stepd">下载技能包，放进<b>本产物所在的文件夹</b>——放好即安装完成。</div>'
          +'<div class="ed-sp-stepact" data-sp-skillbtn></div></div></div>'
          +'<div class="ed-sp-step"><span class="ed-sp-stepno">4</span><div class="ed-sp-stepmain"><b>执行技能，完成替换</b>'
          +'<div class="ed-sp-stepd">打开你的 AI 编程工具，把项目空间选到<b>本产物所在的文件夹</b>，启用「换风格技能」（启用方式见技能包内说明），把复制的提示词交给它。跑完即得到新风格的编辑器版本。</div></div></div>'
          +'</div>'
          +'<div class="ed-sp-dialog-note">只想换个配色？关闭弹窗回上一页，用「配色版」色块秒换主题色——页面形态不变。</div>'
          +'</div>'
          +'<footer><button type="button" class="tb" data-sp-dlg-close>我知道了</button></footer>';
        document.body.appendChild(dlg);
        dlg.querySelectorAll('[data-sp-dlg-close]').forEach(function(b){
          b.addEventListener('click',function(){dlg.close();});
        });
        dlg.addEventListener('click',function(e){if(e.target===dlg)dlg.close();});
      }
      var slot=dlg.querySelector('[data-sp-skillbtn]');
      if(slot){
        if(RESKIN_SKILL_URL)slot.innerHTML='<a class="ed-sp-skillbtn" href="'+esc(RESKIN_SKILL_URL)+'" target="_blank" rel="noopener">下载换风格技能</a>';
        else slot.innerHTML='<span class="ed-sp-skillwrap"><button type="button" class="ed-sp-skillbtn" disabled>下载换风格技能</button><i class="ed-sp-skillhint">即将上线</i></span>';
      }
      dlg.showModal();
    }
    function open(){
      /* 右侧抽屉（用户定稿：面板挡预览 → 改右抽屉推开画布，可拖宽并记住宽度）。
         非模态：不弹遮罩、点画布不自动关；Esc 或关闭按钮收起；已开时再点入口=收起。
         workspace-runtime-ui 标记保留（导出清理依赖，free-editor.js 清理按类删根节点）。 */
      if(document.getElementById('stylePanel')){close();return;}
      var d=document.createElement('aside');
      d.id='stylePanel';d.className='ed-sp-drawer workspace-runtime-ui';
      d.innerHTML='<span class="ed-sp-grip" title="拖动调宽" aria-hidden="true"></span>'
        +'<header><strong>设计风格</strong><button type="button" class="tb" data-sp-close>关闭</button></header>'
        +'<nav class="ed-sp-ptabs"><button type="button" class="ed-sp-tab on" data-tab="1">已生成的可选风格</button><button type="button" class="ed-sp-tab" data-tab="2">更多风格方向</button></nav>'
        +'<div class="ed-sp-body"><div class="ed-sp-page on" data-page="1"></div></div>'
        +'<footer><button type="button" class="ed-sp-restore" id="spRestoreOriginal">恢复原方案</button><span class="ed-sp-status" id="spStatus"></span></footer>';
      document.body.appendChild(d);
      var page1=d.querySelector('[data-page="1"]');
      function renderPage1(){
        var cur=currentPack();
        var html='';
        MODEL.families.forEach(function(fam,i){
          var members=(fam.members||[]).map(packById).filter(Boolean);
          if(!members.length)return;
          html+='<div class="ed-sp-grp"><div class="ed-sp-grph"><b>风格组'+(i+1)+'</b></div>'
            +'<div class="ed-sp-grid">'+members.map(function(pk){return cardHTML(pk,cur);}).join('')+'</div></div>';
        });
        if(!html)html='<div class="ed-sp-empty">本产物暂无已生成的可选风格。</div>';
        page1.innerHTML=html;
        page1.querySelectorAll('.ed-sp-card[data-pack]').forEach(function(card){
          var pack=packById(card.getAttribute('data-pack'));
          if(!pack)return;
          card.addEventListener('click',function(e){
            if(e.target.closest('.ed-sp-pal'))return;/* 胶囊自处理：只换配色 */
            applyPack(pack.packId);
          });
          card.addEventListener('keydown',function(e){if(e.key==='Enter'||e.key===' '){e.preventDefault();applyPack(pack.packId);}});
          card.querySelectorAll('.ed-sp-pal').forEach(function(btn){
            btn.addEventListener('click',function(e){
              e.stopPropagation();
              if(pack.palettes&&pack.palettes.length>1){applyPalette(btn.getAttribute('data-pal'),pack.packId);}
              else if(cur.packId!==pack.packId){applyPack(pack.packId,btn.getAttribute('data-pal'));}
              /* 单配色且已是当前卡：胶囊仅作当前配色展示，不动作 */
            });
          });
        });
        refreshStatus();
      }
      function refreshStatus(){
        var s=d.querySelector('#spStatus'),st=read(),pack=currentPack();
        if(s){
          var noStyle=!st.packId&&(!st.id||st.id==='original')&&!st.presetId;
          s.textContent=noStyle?'当前：原始方案':'当前：'+((pack.identity&&pack.identity.styleName)||pack.packId)+' × '+(paletteOf(pack,st.paletteId||st.colorId).label||'默认');
        }
        var ro=d.querySelector('#spRestoreOriginal');
        if(ro){
          /* 有交付初始风格（--active-pack）或原始基线，二者任一即可恢复 */
          var ip=st.initialPackId?packById(st.initialPackId):null;
          var hasInit=!!(ip&&!(ip.builtin&&ip.builtin.id==='original'));
          var okO=hasInit||!!(st.original&&st.original.values&&typeof st.original.values==='object');
          ro.disabled=!okO;
          ro.title=okO?(hasInit?'恢复到交付时的风格':'恢复本产物原始样式'):'没有可恢复的基线（本件未动过风格或为旧版文件）';
        }
      }
      renderPage1();
      window.__spPanelRefresh=function(){if(document.getElementById('stylePanel'))renderPage1();};
      d.querySelectorAll('.ed-sp-tab').forEach(function(t){
        t.addEventListener('click',function(){
          if(t.getAttribute('data-tab')==='2'){openReskinDialog();return;} /* 2026-11-20 用户定案：点击=弹窗，不切页 */
          d.querySelectorAll('.ed-sp-tab').forEach(function(x){x.classList.toggle('on',x===t);});
          d.querySelectorAll('.ed-sp-page').forEach(function(pg){pg.classList.toggle('on',pg.getAttribute('data-page')===t.getAttribute('data-tab'));});
        });
      });
      /* 左缘拖宽：280–620px，指针抬起才落盘（localStorage），下次打开按记住的宽度开 */
      var SP_WKEY='edSpDrawerWidth';
      function applyW(w,save){
        w=Math.max(280,Math.min(620,Math.round(w)));
        document.documentElement.style.setProperty('--ed-sp-width',w+'px');
        if(save){try{localStorage.setItem(SP_WKEY,String(w));}catch(e){}}
        return w;
      }
      var saved=NaN;try{saved=parseInt(localStorage.getItem(SP_WKEY),10);}catch(e){}
      applyW(isFinite(saved)&&saved>=280&&saved<=620?saved:360,false);
      var grip=d.querySelector('.ed-sp-grip'),dragging=false;
      grip.addEventListener('pointerdown',function(e){
        dragging=true;try{grip.setPointerCapture(e.pointerId);}catch(err){}
        document.body.classList.add('ed-sp-resizing');e.preventDefault();
      });
      grip.addEventListener('pointermove',function(e){if(dragging)applyW(window.innerWidth-e.clientX,false);});
      grip.addEventListener('pointerup',function(e){if(!dragging)return;dragging=false;document.body.classList.remove('ed-sp-resizing');applyW(window.innerWidth-e.clientX,true);});
      grip.addEventListener('pointercancel',function(){dragging=false;document.body.classList.remove('ed-sp-resizing');});
      function onKey(e){if(e.key==='Escape'){e.stopPropagation();close();}}
      spKeyHandler=onKey;
      document.addEventListener('keydown',onKey);
      d.querySelector('[data-sp-close]').onclick=function(){close();};
      document.documentElement.setAttribute('data-sp-open','');
      var ro=d.querySelector('#spRestoreOriginal');
      if(ro)ro.onclick=function(){restoreOriginal();};
    }
    var spKeyHandler=null;
    function close(){
      var el=document.getElementById('stylePanel');
      if(!el)return false;
      if(spKeyHandler){document.removeEventListener('keydown',spKeyHandler);spKeyHandler=null;}
      el.remove();
      document.documentElement.removeAttribute('data-sp-open');
      document.body.classList.remove('ed-sp-resizing');
      window.__spPanelRefresh=null;
      return true;
    }
    /* ---------- 8. 导出与挂载（window.StylePanel；V1 的 StyleWizard 两步向导入口随 V2 单入口替换移除） ---------- */
    window.StylePanel={
      open:open,
      applyPack:applyPack,
      applyPalette:applyPalette,
      setMaterial:setMaterial,
      applyStyleConfig:applyStyleConfig,
      restorePreset:restorePreset,
      restoreOriginal:restoreOriginal,
      normalizeStyleConfig:function(input,baseline){return normalizeStyleConfig(input,baseline);},
      info:function(){return {mode:MODE,registry:MODE==='registry'?{families:MODEL.families.length,packs:MODEL.packs.length}:null,
        currentPackId:currentPack().packId,paletteId:currentPaletteId(currentPack()),material:currentMaterials(),
        sourceLabel:sourceBadgeText()};}
    };
    /* ---------- 9. 启动自动应用（--active-pack 交付初始风格） ----------
       新构建件特征：state 带 packId（build.py --active-pack 注入）且 original 未建立
       =用户从未操作过。此时按该包+默认色板补齐整套视觉（根变量+L1/L2/L3+domBase）——
       启动 render() 只走 syncLayers，缺根变量写入，交付件打开会仍是构建默认蓝。
       走 applyStyleConfigOn restore 通道：不 snapshot、不 scheduleSave、不压撤销栈
       （用户没操作=文件不算变动）；该分支会顺手补记写前 pristine original（只写 state 节点，
       不标脏），initialPackId 恢复语义不受影响。一次会话只执行一次（防观察器回环）。 */
    var initialApplied=false;
    function applyInitialPack(){
      if(initialApplied)return;
      initialApplied=true;
      if(MODE!=='registry')return;
      var st=read();
      if(!st.packId||st.id==='original'||st.presetId==='original')return;
      if(st.original&&st.original.values)return;/* 有操作痕迹：视觉交由常规链路/草稿恢复 */
      var pack=packById(st.packId);
      if(!pack||(pack.builtin&&pack.builtin.id==='original'))return;
      var pal=paletteOf(pack,st.paletteId||st.colorId);
      applyStyleConfigOn({values:paletteValues(pack,pal.paletteId),dark:!!packParams(pack).dark},'live',{restore:true});
      syncLayers(pack);
      var fam=familyOf(pack);
      if(fam&&fam.domBaseId)applyDomBase(fam.domBaseId);
    }
    function init(){applyInitialPack();render();}
    var previous=initFreeEditor;initFreeEditor=function(){previous();init();};
    var queued=false;function queueRender(){if(queued)return;queued=true;requestAnimationFrame(function(){queued=false;render();});}
    new MutationObserver(queueRender).observe(canvas,{childList:true,subtree:true});
    new MutationObserver(queueRender).observe(document.documentElement,{attributes:true,attributeFilter:['style']});
    new MutationObserver(queueRender).observe(document.body,{attributes:true,attributeFilter:['class']});
    render();
  })();
/*STYLE_CHOOSER_END*/
