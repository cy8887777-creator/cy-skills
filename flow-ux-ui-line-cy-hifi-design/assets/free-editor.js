  /* Free-position layout and full-file download. Embedded in the final HTML. */
  var freeBox=null,freeGesture=null,freeClickUntil=0,freeInitialized=false,workspaceInteracted=false;
  function createAnchorNotes(){
    function read(){var node=document.getElementById('prototype-annotations');try{return node?JSON.parse(node.textContent):[];}catch(e){return [];}}
    function write(records){var node=document.getElementById('prototype-annotations');if(!node&&!records.length)return;if(!node){node=document.createElement('script');node.type='application/json';node.id='prototype-annotations';canvas.appendChild(node);}var value=JSON.stringify(records).replace(/</g,'\\u003c');if(node.textContent!==value)node.textContent=value;}
    function descriptor(el){var sc=el.closest('.screen'),product=el.closest('[data-product]');return {page:sc.getAttribute('data-screen'),eid:el.getAttribute('data-eid'),product:product&&product.getAttribute('data-product'),action:el.getAttribute('data-on'),field:el.getAttribute('data-field'),tag:el.tagName,pageNote:el.matches('.app,.adpage,.viewport')};}
    function resolve(rec){var sc=screenEl(rec.page);if(!sc)return null;var all=Array.from(sc.querySelectorAll('[data-annotation-anchor]'));var exact=all.find(function(el){return el.getAttribute('data-annotation-anchor')===rec.id;});if(exact)return exact;
      if(rec.pageNote)return sc.querySelector('.app')||sc.querySelector('.adpage')||sc.querySelector('.viewport');
      var root=sc;if(rec.product){root=Array.from(sc.querySelectorAll('[data-product]')).find(function(el){return el.getAttribute('data-product')===rec.product;});if(!root)return null;if(rec.tag===root.tagName&&!rec.action&&!rec.field)return root;}
      if(rec.action)return Array.from(root.querySelectorAll('[data-on]')).find(function(el){return el.tagName===rec.tag&&el.getAttribute('data-on')===rec.action;})||null;
      if(rec.field)return Array.from(root.querySelectorAll('[data-field]')).find(function(el){return el.getAttribute('data-field')===rec.field;})||null;
      return rec.eid?Array.from(root.querySelectorAll('[data-eid]')).find(function(el){return el.getAttribute('data-eid')===rec.eid;})||null:null;
    }
    function record(el,records){var d=descriptor(el),id=el.getAttribute('data-annotation-anchor');if(!id){id='note-'+crypto.randomUUID();el.setAttribute('data-annotation-anchor',id);}var old=records.find(function(r){return r.id===id;});var next=Object.assign({id:id},d,{content:el.getAttribute('data-note'),type:el.getAttribute('data-note-type')||'function'});if(old)Object.assign(old,next);else records.push(next);}
    function remember(el){var records=read();record(el,records);write(records);}
    function forget(el){var sc=el.closest('.screen'),id=el.getAttribute('data-annotation-anchor');write(read().filter(function(r){return !(r.id===id&&sc&&r.page===sc.getAttribute('data-screen'));}));}
    function sync(){var records=read().filter(function(r){return !!screenEl(r.page);}),seen=new Set();Array.from(canvas.querySelectorAll('[data-note]')).forEach(function(el){if(!(el.getAttribute('data-note')||'').trim())return;var id=el.getAttribute('data-annotation-anchor');if(id&&seen.has(id))el.removeAttribute('data-annotation-anchor');record(el,records);seen.add(el.getAttribute('data-annotation-anchor'));});records.forEach(function(r){var el=resolve(r);if(!el)return;if(el.getAttribute('data-annotation-anchor')!==r.id)el.setAttribute('data-annotation-anchor',r.id);if(el.getAttribute('data-note')!==r.content)el.setAttribute('data-note',r.content);if(el.getAttribute('data-note-type')!==r.type)el.setAttribute('data-note-type',r.type);});write(records);}
    return {sync:sync,remember:remember,forget:forget,read:read,resolve:resolve};
  }
  function freeRoot(screen){screen=screen||currentScreenEl();if(!screen)return null;/* 批2修复：补后台页兜底根（原只认 .mall-content/.adpage/.app，平台管理端后台页根为 .viewport>[data-block]，缺失导致切换静默空转却弹成功 toast） */return screen.querySelector('.mall-content')||screen.querySelector('.adpage')||screen.querySelector('.app')||screen.querySelector('.viewport > [data-block]')||screen.querySelector('.viewport')||screen;}
  function freePageOn(){var screen=currentScreenEl();return !!(screen&&screen.getAttribute('data-layout')==='free');}
  function freeScale(root){var w=root.offsetWidth;return w?root.getBoundingClientRect().width/w:zoom||1;}
  function freeItem(node){return node&&node.closest&&node.closest('[data-free-item]');}
  function freeConvert(screen){
    var root=freeRoot(screen);if(!root)return;
    var rect=root.getBoundingClientRect(),scale=freeScale(root),items=Array.from(root.children).filter(function(el){return !el.matches('.appbar,.tabbar,.mall-bottom,.statusbar,[data-editor-placeholder],[data-block="empty"][data-eid^="et-"]');});
    items.forEach(function(el){if(!el.getAttribute('data-eid'))el.setAttribute('data-eid',newEid());});
    /* 批4：快照原始流式状态（真双向开关——切回时精确恢复转换前布局，undo 之外的第二重保险） */
    var backup={rootCls:root.className,rootStyle:root.style.cssText,items:items.map(function(el){return {eid:el.getAttribute('data-eid')||'',css:el.style.cssText};})};
    screen.setAttribute('data-free-backup',JSON.stringify(backup));
    var positions=items.map(function(el){var r=el.getBoundingClientRect();return {el:el,x:(r.left-rect.left)/scale+root.scrollLeft,y:(r.top-rect.top)/scale+root.scrollTop,w:r.width/scale,h:r.height/scale};});
    screen.setAttribute('data-layout','free');root.classList.add('free-canvas');root.style.position='relative';root.style.minHeight=Math.max(720,root.clientHeight)+'px';
    positions.forEach(function(p){p.el.setAttribute('data-free-item','1');Object.assign(p.el.style,{position:'absolute',left:Math.max(0,p.x)+'px',top:Math.max(0,p.y)+'px',width:Math.max(24,p.w)+'px',height:Math.max(24,p.h)+'px',margin:'0'});});
  }
  /* 批4：切回相对定位——按快照精确还原原流式布局；free 期间新增（快照外）的子项清除绝对定位样式后保留、追加到末尾 */
  function freeRevert(screen){
    if(!editorAllowed())return false;
    var raw=screen.getAttribute('data-free-backup');
    if(!raw){toast('未找到切换前布局快照，可用撤销还原');return false;}
    var root=freeRoot(screen);if(!root)return false;
    var backup;
    try { backup=JSON.parse(raw); } catch(e) { toast('布局快照损坏，可用撤销还原'); return false; }
    snapshot();
    var known={};
    backup.items.forEach(function(it){ if(it.eid) known[it.eid]=true; });
    Array.from(root.children).forEach(function(el){
      if(el.hasAttribute('data-free-item') && !known[el.getAttribute('data-eid')||'']){
        el.removeAttribute('data-free-item');
        el.style.removeProperty('position');el.style.removeProperty('left');el.style.removeProperty('top');
        el.style.removeProperty('width');el.style.removeProperty('height');el.style.removeProperty('margin');
        root.appendChild(el);
      }
    });
    backup.items.forEach(function(it){
      var el=it.eid?Array.from(root.children).find(function(child){return child.getAttribute('data-eid')===it.eid;}):null;
      if(el){ el.style.cssText=it.css; el.removeAttribute('data-free-item'); }
    });
    root.className=backup.rootCls;root.style.cssText=backup.rootStyle;
    screen.removeAttribute('data-layout');
    screen.removeAttribute('data-free-backup');
    buildTabs();scheduleSave();freeUpdate();return true;
  }
  function freePlace(node,screen){
    var root=freeRoot(screen);if(!root)return;var count=root.querySelectorAll(':scope>[data-free-item]').length;
    var measured=node.getBoundingClientRect(),scale=freeScale(root);if(node.parentElement!==root)root.appendChild(node);
    var width=node.classList.contains('btns')?152:Math.min(Math.max(measured.width/scale,160),root.clientWidth-48),height=node.classList.contains('btns')?48:Math.max(36,measured.height/scale);
    var bottom=Math.max(0,...Array.from(root.querySelectorAll(':scope>[data-free-item]')).filter(function(el){return el!==node;}).map(function(el){return (parseFloat(el.style.top)||0)+el.offsetHeight;}));
    node.setAttribute('data-free-item','1');if(!node.hasAttribute('data-eid'))node.setAttribute('data-eid',newEid());
    Object.assign(node.style,{position:'absolute',left:(24+(count%3)*12)+'px',top:Math.max(root.querySelector(':scope>.appbar')?88:24,bottom+16)+'px',width:width+'px',height:height+'px',margin:'0'});
    root.style.minHeight=Math.max(720,parseFloat(node.style.top)+height+80)+'px';
  }
  function freeUpdate(){
    var screen=currentScreenEl(),on=!!(screen&&screen.getAttribute('data-layout')==='free'),button=document.getElementById('btnFreeLayout');
    if(button){button.textContent=on?'切换为相对定位':'切换为绝对定位';button.classList.toggle('on',on);}
    var item=directTarget(selected),geometry=item&&directGeometry(item);
    ['freeX','freeY','freeW','freeH','freeZ','freeSizing','freeShape'].forEach(function(id){var input=document.getElementById(id);if(input)input.disabled=!edit||!item;});
    if(item){var values={freeX:geometry.x,freeY:geometry.y,freeW:geometry.w,freeH:geometry.h,freeZ:parseInt(item.style.zIndex)||0};Object.keys(values).forEach(function(id){var input=document.getElementById(id);if(input)input.value=Math.round(values[id]);});
      var shape=document.getElementById('freeShape'),sizing=document.getElementById('freeSizing');if(shape)shape.value=item.getAttribute('data-editor-shape')||(directRadius(item)>0?'rounded':'rectangle');if(sizing)sizing.value=item.getAttribute('data-direct-sizing')||'fixed';}
    if(!freeBox)return;
    if(!edit||!item||!item.isConnected||document.body.classList.contains('annotating')){freeBox.hidden=true;return;}
    var rect=item.getBoundingClientRect();freeBox.hidden=false;Object.assign(freeBox.style,{left:rect.left+'px',top:rect.top+'px',width:rect.width+'px',height:rect.height+'px'});
    var radius=freeBox.querySelector('.free-radius');if(radius)radius.style.right=Math.max(12,Math.min(rect.width/2,directRadius(item)*geometry.scale)-6)+'px';
  }
  function freeDragStart(e,item,handle){
    if(!editorUnlocked||!edit||e.button!==0||document.body.classList.contains('annotating'))return;
    var active=document.activeElement;if(active&&active.closest('#inspector')&&active.matches('input,textarea,select'))active.blur();
    var focus=handle?selected:pick(e.target),previous=directTarget(selected),actual=handle?previous:(previous&&previous.contains(e.target)?previous:directTarget(focus));if(!actual||e.target.closest('[contenteditable="true"]'))return;
    e.preventDefault();e.stopImmediatePropagation();
    select(actual);var geometry=directGeometry(actual);
    freeGesture={item:actual,focus:focus,root:geometry.root,handle:handle||'',startX:e.clientX,startY:e.clientY,x:parseFloat(actual.style.left)||0,y:parseFloat(actual.style.top)||0,w:geometry.w,h:geometry.h,visualX:geometry.x,visualY:geometry.y,scale:geometry.scale,radius:directRadius(actual),moved:false,style:actual.getAttribute('style')||''};
    freeUpdate();
  }
  function freeDragMove(e){
    var g=freeGesture;if(!g)return;e.preventDefault();e.stopImmediatePropagation();var dx=(e.clientX-g.startX)/g.scale,dy=(e.clientY-g.startY)/g.scale;
    if(!g.moved&&Math.abs(dx)+Math.abs(dy)<3)return;
    if(!g.moved){snapshot();g.moved=true;directPrepare(g.item);}
    if(g.handle==='radius'){directSetRadius(g.item,Math.round(Math.max(0,Math.min(Math.min(g.w,g.h)/2,g.radius+(-dx+dy)/2)))+'px');freeUpdate();return;}
    var x=g.x,y=g.y,w=g.w,h=g.h;
    if(g.handle){if(g.handle.includes('e'))w=Math.max(24,g.w+dx);if(g.handle.includes('s'))h=Math.max(24,g.h+dy);if(g.handle.includes('w')){w=Math.max(24,g.w-dx);x=g.x+g.w-w;}if(g.handle.includes('n')){h=Math.max(24,g.h-dy);y=g.y+g.h-h;}
      if(e.shiftKey&&g.handle.length===2){var ratio=g.w/g.h;if(Math.abs(w-g.w)>Math.abs(h-g.h)*ratio)h=w/ratio;else w=h*ratio;if(g.handle.includes('w'))x=g.x+g.w-w;if(g.handle.includes('n'))y=g.y+g.h-h;}}
    else{x=g.x+dx;y=g.y+dy;}
    x=Math.max(g.x-g.visualX,Math.min(x,g.x-g.visualX+Math.max(0,g.root.clientWidth-w)));y=Math.max(g.y-g.visualY,y);
    Object.assign(g.item.style,{left:Math.round(x)+'px',top:Math.round(y)+'px',width:Math.round(w)+'px',height:Math.round(h)+'px'});g.item.setAttribute('data-direct-sizing','fixed');
    g.root.style.minHeight=Math.max(720,g.visualY+y-g.y+h+80)+'px';freeUpdate();
  }
  function freeDragEnd(e){var g=freeGesture;if(!g)return;freeGesture=null;if(g.moved){e.preventDefault();e.stopImmediatePropagation();freeClickUntil=Date.now()+300;directRemember(g.item);select(g.item);scheduleSave();syncPanel();g.item.scrollIntoView({behavior:'instant',block:'nearest',inline:'nearest'});}else if(!g.handle&&g.focus&&g.focus.isConnected){e.preventDefault();e.stopImmediatePropagation();freeClickUntil=Date.now()+300;select(g.focus);}freeUpdate();}
  var sourcePasswordPending=false;
  function saveSourceHTML(){
    if(localSaveSession())return saveViaLocalHelper();
    if(localSavePreferred()){
      if(!editorAllowed(saveSourceHTML))return Promise.resolve(false);
      toast('请启动同目录的本地保存器（Windows .exe / Mac .app）打开原型，再点击保存即可直接覆盖；当前修改仍保留。',5500);
      document.getElementById('lockHint').textContent=sourcePasswordPending?'口令尚未写入源文件 · 请通过本地保存器打开后保存':'请通过同目录的本地保存器打开，以直接覆盖源文件';return Promise.resolve(false);
    }
    return saveBrowserSourceHTML();
  }
  function saveBrowserSourceHTML(){
    if(!editorAllowed(saveSourceHTML))return Promise.resolve(false);
    if(saving){toast('正在保存，请稍候');return Promise.resolve(false);}
    saving=true;var selectedThisTime=!fileHandle&&!storedHandle,rev=changeRevision,oldBuilt=builtAt;
    /* Ask for the file while the Save click still has user activation, before cloning a large document. */
    var start;try{start=selectedThisTime?pickNewHandle():Promise.resolve(fileHandle||storedHandle);}catch(e){start=Promise.reject(e);}
    return start.then(function(h){return h.getFile().then(function(f){return f.text();}).then(function(disk){
      var parsed=new DOMParser().parseFromString(disk,'text/html');
      if(parsed.documentElement.getAttribute('data-doc')!==docKey)throw new Error('所选文件项目不匹配，请选择当前打开的源HTML。');
      var here=decodeURIComponent(location.pathname.split('/').pop()||'');
      if(location.protocol==='file:'&&here!==h.name)throw new Error('请选择当前打开的源文件「'+here+'」，其他副本请使用另存为。');
      if(boundFingerprint!==null&&disk!==boundFingerprint)throw new Error('源文件已由其他窗口修改，请先处理冲突；当前修改仍保留。');
      return ensurePerm(h).then(function(ok){if(!ok)throw new Error('未获得写入授权，修改仍保留。');builtAt=builtAt||String(Date.now());var html=buildExport(builtAt);return writeHandle(h,html,rev);});
    });}).then(function(){sourcePasswordPending=false;document.getElementById('lockHint').textContent=changeRevision===rev?'口令与本次修改已写入源文件 · 重开后输入原口令继续编辑':'口令已写入源文件 · 保存期间又有新修改，请再次保存';return true;}).catch(function(e){
      builtAt=oldBuilt;var cancelled=e&&e.name==='AbortError';toast(cancelled?'已取消保存，源文件未改动；当前修改仍保留。':'未保存：'+e.message+'；不支持覆盖时可主动选择另存为或下载完整HTML。',5500);
      if(sourcePasswordPending)document.getElementById('lockHint').textContent='口令尚未写入源文件，请点击“保存”完成授权；当前不会自动下载';
      return false;
    }).finally(function(){saving=false;});
  }
  function saveFirstPassword(){sourcePasswordPending=true;document.getElementById('lockHint').textContent='正在将首次口令保存到源文件；首次请选择当前HTML并授权';return saveSourceHTML();}
  function saveNewHTML(){
    if(!editorAllowed(saveNewHTML))return;
    var html;try{html=buildExport(String(Date.now()));}catch(e){toast('未生成文件：'+e.message);return;}
    var stamp=new Date().toISOString().replace(/[:.]/g,'-'),name=fileName()+(editorConfig.editPassword?'_已设口令':'')+'-'+stamp+'.html';var url=URL.createObjectURL(new Blob([html],{type:'text/html;charset=utf-8'})),a=document.createElement('a');a.href=url;a.download=name;document.body.appendChild(a);a.click();a.remove();setTimeout(function(){URL.revokeObjectURL(url);},30000);
    var button=document.getElementById('btnDownloadHTML');if(button){button.setAttribute('data-export-requested','1');button.title='完整HTML下载已发起。请确认下载完成；源文件未被覆盖。';}
    toast('已发起完整新HTML下载：保留页面、编辑器、口令和交互。请确认下载完成。',4500);
  }
  function freeDetachSelected(){
    if(!editorAllowed()||!selected||!freePageOn())return;
    var root=freeRoot(),el=selected;if(el===root||el.matches('.appbar,.tabbar,.statusbar,.mall-bottom'))return;
    snapshot();var rect=el.getBoundingClientRect(),rr=root.getBoundingClientRect(),scale=freeScale(root),cs=getComputedStyle(el);var x=(rect.left-rr.left)/scale+root.scrollLeft,y=(rect.top-rr.top)/scale+root.scrollTop;
    root.appendChild(el);el.setAttribute('data-free-item','1');Object.assign(el.style,{position:'absolute',left:Math.max(0,x)+'px',top:Math.max(0,y)+'px',width:rect.width/scale+'px',height:rect.height/scale+'px',fontSize:cs.fontSize,color:cs.color,margin:'0'});select(el);scheduleSave();freeUpdate();
  }
  function initFreeEditor(){
    if(freeInitialized)return;freeInitialized=true;
    ['btnFreeLayout','freeProperties','fGrpPos'].forEach(function(id){var old=document.getElementById(id);if(old)old.remove();});
    document.querySelectorAll('.free-editor-ui').forEach(function(el){el.remove();});
    var toggle=document.createElement('button');toggle.className='tb';toggle.id='btnFreeLayout';toggle.textContent='绝对定位 / 相对定位';toggle.title='切换本页：绝对定位=自由画布可拖拽摆放；相对定位=常规流式布局';var fls=document.getElementById('btnFreeLayoutSlot');if(fls)fls.appendChild(toggle);else{var anchor=document.getElementById('btnInsert');if(anchor)anchor.before(toggle);}
    toggle.onclick=function(){if(!editorAllowed(function(){toggle.click();}))return;var screen=currentScreenEl();if(!screen)return;/* 批4：真双向开关——free 态再点切回相对定位（快照式精确还原） */if(freePageOn()){if(freeRevert(screen))toast('已切回相对定位布局（还原为本页切换前样式；绝对定位期间新增的组件保留在末尾）。');return;}snapshot();freeConvert(screen);scheduleSave();freeUpdate();toast('已切换为绝对定位：拖动组件改位置，拉动八个控点改尺寸。');};
    var panel=document.createElement('div');panel.className='fld';panel.id='freeProperties';panel.innerHTML='<div class="g2">'+[['freeX','X'],['freeY','Y'],['freeW','宽'],['freeH','高'],['freeZ','层级']].map(function(f){return '<label>'+f[1]+'<input type="number" id="'+f[0]+'" step="1"></label>';}).join('')+'</div><div class="acts"><button id="freeCenter">水平居中</button><button id="freeDetach">拆出独立拖动</button><button id="freeFront">置顶</button></div><span class="hint">选中组件后拖动，或输入坐标；方向键微调，Shift加速。</span>';
    /* 卡片化：位置固定+位置尺寸形状+拖拽/尺寸/形状控件统一进「位置与层级」折叠卡（v6.3 全面板零散装行） */
    var posWrap=document.createElement('details');posWrap.className='ed-fgrp';posWrap.id='fGrpPos';posWrap.open=true;
    posWrap.innerHTML='<summary>位置与层级</summary><div class="ed-fgrp-b" id="posBody"></div>';
    document.getElementById('insBody').prepend(posWrap);
    var posBody=document.getElementById('posBody');
    var pin=document.getElementById('pinField');if(pin)posBody.appendChild(pin);
    posBody.appendChild(panel);initDirectControls(panel);
    ['freeX','freeY','freeW','freeH','freeZ'].forEach(function(id){
      var apply=function(withSnapshot){var item=directTarget(selected);if(!editorAllowed()||!item)return;var el=document.getElementById(id);var n=Number(el.value);if(!Number.isFinite(n))return;if(withSnapshot)snapshot();if(id==='freeX'||id==='freeY')directCoordinate(item,id==='freeX'?'x':'y',n);else if(id==='freeZ')item.style.zIndex=String(Math.round(n));else{directPrepare(item);item.style[id==='freeW'?'width':'height']=Math.max(24,n)+'px';item.setAttribute('data-direct-sizing','fixed');}directRemember(item);scheduleSave();freeUpdate();};
      var el0=document.getElementById(id);
      el0.oninput=function(){apply(false);};
      el0.onchange=function(){apply(true);};
    });
    document.getElementById('freeCenter').onclick=function(){var item=directTarget(selected);if(!editorAllowed()||!item)return;snapshot();var g=directGeometry(item);directCoordinate(item,'x',Math.max(0,(g.root.clientWidth-g.w)/2));directRemember(item);scheduleSave();freeUpdate();};
    document.getElementById('freeFront').onclick=function(){var item=directTarget(selected);if(!editorAllowed()||!item)return;snapshot();directPrepare(item);item.style.zIndex=String(1+Math.max(0,...Array.from(directRoot(item).querySelectorAll('[data-direct-item],[data-free-item]')).map(function(el){return parseInt(el.style.zIndex)||0;})));directRemember(item);scheduleSave();freeUpdate();};
    document.getElementById('freeDetach').onclick=freeDetachSelected;
    freeBox=document.createElement('div');freeBox.className='free-editor-ui free-box';freeBox.hidden=true;
    /* 批1a配套：缩放控点覆盖小元素中心时双击改字被拦——控点 dblclick 时藏框→向下方元素重发 dblclick（canvas 主 handler 即可正常接住） */
    freeBox.addEventListener('dblclick',function(e){
      if(!e.target.classList||(!e.target.classList.contains('free-resize')&&!e.target.classList.contains('free-radius')))return;
      freeBox.hidden=true;
      var under=document.elementFromPoint(e.clientX,e.clientY);
      freeBox.hidden=false;
      if(!under||freeBox.contains(under))return;
      under.dispatchEvent(new MouseEvent('dblclick',{bubbles:true,cancelable:true,clientX:e.clientX,clientY:e.clientY,view:window}));
    },false);
    ['nw','n','ne','e','se','s','sw','w'].forEach(function(direction){var h=document.createElement('span');h.className='free-resize free-'+direction;h.dataset.resize=direction;h.onpointerdown=function(e){freeDragStart(e,directTarget(selected),direction);};freeBox.appendChild(h);});var radiusHandle=document.createElement('span');radiusHandle.className='free-radius';radiusHandle.title='拖动调整圆角';radiusHandle.onpointerdown=function(e){freeDragStart(e,directTarget(selected),'radius');};freeBox.appendChild(radiusHandle);document.body.appendChild(freeBox);
    // Suppress only the click produced by the just-finished gesture. A new
    // pointerdown (including Preview) starts a real new interaction immediately.
    document.addEventListener('pointerdown',function(){freeClickUntil=0;},true);
    canvas.addEventListener('pointerdown',function(e){if(!edit)return;var item=directTarget(pick(e.target));if(item&&document.getElementById('freeMoveMode').value!=='flow')freeDragStart(e,item);},true);
    document.addEventListener('pointermove',freeDragMove,true);document.addEventListener('pointerup',freeDragEnd,true);
    document.addEventListener('pointercancel',function(){if(freeGesture){freeGesture.item.setAttribute('style',freeGesture.style);freeGesture=null;freeUpdate();}},true);
    document.addEventListener('click',function(e){if(e.detail&&Date.now()<freeClickUntil&&canvas.contains(e.target)){freeClickUntil=0;e.preventDefault();e.stopImmediatePropagation();}},true);
    window.addEventListener('scroll',freeUpdate,true);window.addEventListener('resize',freeUpdate);
    document.addEventListener('keydown',function(e){if(!editorUnlocked||!edit||!selected||/INPUT|TEXTAREA|SELECT/.test(e.target.tagName)||e.target.isContentEditable)return;if(!['ArrowLeft','ArrowRight','ArrowUp','ArrowDown'].includes(e.key))return;var item=directTarget(selected);if(!item)return;e.preventDefault();snapshot();directPrepare(item);var d=e.shiftKey?10:1;var geometry=directGeometry(item);directCoordinate(item,'x',Math.max(0,geometry.x+(e.key==='ArrowLeft'?-d:e.key==='ArrowRight'?d:0)));directCoordinate(item,'y',Math.max(0,geometry.y+(e.key==='ArrowUp'?-d:e.key==='ArrowDown'?d:0)));directRemember(item);scheduleSave();freeUpdate();},true);
    document.getElementById('btnSave').onclick=saveSourceHTML;
    document.getElementById('btnSave').textContent='保存';document.getElementById('btnSave').title='覆盖保存当前源HTML；首次选择当前文件并授权，后续授权有效时直接保存。';
    loadHandle().then(function(h){if(!fileHandle)storedHandle=h;});
    /* v6.2 H3：btnExport 文案由 editor-seed 定稿维护（下载纯净分发版），不再运行时改名 */
    /* v2 多风格：数据类初始化（删占位/free 转换）必须全量屏遍历——过滤版只覆盖当前风格会漏初始化其他风格屏（钉死点2） */
    screenListAll().forEach(function(screen){
      var root=freeRoot(screen);if(!root)return;
      var hasContent=Array.from(root.children).some(function(el){return !el.matches('.appbar,.tabbar,.mall-bottom,.statusbar,[data-editor-placeholder],[data-block="empty"][data-eid^="et-"]');});
      if(hasContent)root.querySelectorAll('[data-editor-placeholder],[data-block="empty"][data-eid^="et-"]').forEach(function(el){el.remove();});
      if(screen.getAttribute('data-screen').startsWith('pg-')&&!screen.hasAttribute('data-layout'))freeConvert(screen);
      if(screen.getAttribute('data-layout')==='free')root.classList.add('free-canvas');
    });freeUpdate();initWorkspaceEditor();
    var downloadButton=document.createElement('button');downloadButton.id='btnDownloadHTML';downloadButton.className='tb workspace-runtime-ui';downloadButton.textContent='另存为完整 HTML（可继续编辑）';downloadButton.title='保存一份新的可继续编辑的 HTML 副本';downloadButton.onclick=saveNewHTML;var expAnchor=document.getElementById('btnExport');if(expAnchor)expAnchor.after(downloadButton);
    initLocalSaveUI();
  }

  /* Workspace geometry and annotations are additive: existing fields/actions stay wired. */
  function initWorkspaceEditor(){
    document.addEventListener('pointerdown',function(){workspaceInteracted=true;},true);
    document.addEventListener('keydown',function(){workspaceInteracted=true;},true);
    document.querySelectorAll('.workspace-runtime-ui').forEach(function(el){el.remove();});
    var bar=document.querySelector('.topbar'),body=document.body,noteField=document.getElementById('fNote').closest('.fld');body.classList.remove('has-annotation-card','annotation-right','annotation-drawer');
    /* backdrop-filter makes fixed descendants relative to the toolbar: navigation must be a sibling.
       v6: #tabs 已迁入 #sidepanel（无 backdrop-filter 的固定侧栏），不再强制移动；palette 保留旧行为。 */
    ['palette'].forEach(function(id){var el=document.getElementById(id);if(el&&el.parentElement!==body)body.insertBefore(el,canvas);});
    noteField.id='annotationField';var grpB=document.querySelector('#fGrpContent .ed-fgrp-b');if(grpB)grpB.appendChild(noteField);else document.getElementById('insBody').prepend(noteField);
    noteField.querySelector('label').textContent='功能 / 变更标注';
    document.getElementById('fNote').placeholder='添加备注：记录该元素的功能说明…';
    var hint=document.createElement('span');hint.className='hint workspace-runtime-ui';hint.textContent='可直接改字；多行说明、类型与全页列表请点顶部“标注”。';noteField.appendChild(hint);
    var restore=document.createElement('button');restore.id='btnRestoreElement';restore.className='mini workspace-runtime-ui';restore.textContent='恢复显示所选元素';restore.onclick=function(){if(!editorAllowed()||!selected)return;snapshot();selected.classList.remove('is-hidden');scheduleSave();syncPanel();};
    var opsActs=document.querySelector('#fGrpOps .acts');(opsActs||document.querySelector('#insBody .acts')).after(restore);
    var add=document.createElement('button');add.id='btnAnnotate';add.className='tb workspace-runtime-ui';add.textContent='＋ 标注';add.title='标注当前功能或流程；未选择功能点时先点击目标，不自动标注整页';
    document.getElementById('btnInsert').after(add);
    var listButton=document.createElement('button');listButton.id='btnAnnotationList';listButton.className='tb workspace-runtime-ui';listButton.textContent='标注列表';listButton.title='查看、定位、编辑已有标注';add.after(listButton);
    var dialog=document.createElement('dialog');dialog.id='annotationDialog';dialog.className='workspace-runtime-ui';
    dialog.innerHTML='<div class="annotation-head"><h2>功能与变更标注</h2><button class="tb" id="annotationClose">关闭</button></div><p id="annotationTarget"></p><div id="annotationEditor"><label>标注类型<select id="annotationType"><option value="function">功能说明</option><option value="flow">流程说明</option><option value="change">变更记录</option></select></label><label>标注内容<textarea id="annotationText" rows="5" placeholder="输入功能描述、规则、变更原因或验收条件"></textarea></label><div class="annotation-actions"><button class="tb on" id="annotationSave">保存标注</button><button class="tb warn" id="annotationDelete">删除此标注</button></div></div><h3>项目标注列表</h3><div id="annotationItems"></div>';
    body.appendChild(dialog);var target=null,anchorNotes=createAnchorNotes(),annotationPicking=false,pinsQueued=false,pagePinsEnabled=false;
    var modeButton=document.createElement('button');modeButton.id='btnAnnotationMode';modeButton.className='tb workspace-runtime-ui';modeButton.textContent='标注模式';add.before(modeButton);
    var pageButton=document.createElement('button');pageButton.id='btnPageAnnotate';pageButton.className='tb workspace-runtime-ui';pageButton.textContent='页面标注';listButton.before(pageButton);
    var banner=document.createElement('div');banner.id='annotationModeHint';banner.className='workspace-runtime-ui';banner.hidden=true;banner.textContent='标注模式：点击功能点添加或修改说明；不执行业务按钮。页面整体说明请点“页面标注”，Esc退出。';body.appendChild(banner);
    var pins=document.createElement('div');pins.id='annotationPins';pins.className='workspace-runtime-ui';body.appendChild(pins);
    function picking(on){annotationPicking=!!on;body.classList.toggle('annotating',annotationPicking);modeButton.classList.toggle('on',annotationPicking);modeButton.textContent=annotationPicking?'退出标注':'标注模式';banner.hidden=!annotationPicking;canvas.querySelectorAll('.annotation-hover').forEach(function(el){el.classList.remove('annotation-hover');});}
    modeButton.onclick=function(){picking(!annotationPicking);};
    var tools=document.createElement('div');tools.className='annotation-description-tools';tools.innerHTML='<select id="annotationTemplateKind" aria-label="说明模板类型"><option value="function">功能点说明模板（可选）</option><option value="flow">当前流程说明模板（可选）</option><option value="page">页面说明模板（显式选择）</option><option value="change">变更说明模板</option></select><button class="tb" id="annotationTemplate">插入完整说明模板</button>';
    document.getElementById('annotationEditor').prepend(tools);
    document.getElementById('annotationText').rows=12;
    document.getElementById('annotationText').closest('label').classList.add('annotation-raw-field');document.getElementById('annotationType').closest('label').classList.add('annotation-type-field');
    var detail=document.createElement('div');detail.id='annotationDescriptionPreview';detail.className='annotation-description-preview';document.getElementById('annotationText').closest('label').after(detail);
    var indexTools=document.createElement('div');indexTools.className='annotation-index-tools';indexTools.innerHTML='<input id="annotationSearch" placeholder="搜索页面、功能名称、规则或说明全文" aria-label="搜索标注"><select id="annotationScope" aria-label="标注页面范围"><option value="all">全部页面</option><option value="current">当前页面</option></select><span id="annotationMatches"></span>';
    document.getElementById('annotationItems').before(indexTools);
    var dialogBody=document.createElement('div');dialogBody.className='annotation-dialog-body';while(dialog.children.length>1)dialogBody.appendChild(dialog.children[1]);dialog.appendChild(dialogBody);
    function formatNote(container,text){container.replaceChildren();text.split('\n').forEach(function(line){if(!line.trim())return;var heading=/^(【.+】|#{1,3} )/.test(line),p=document.createElement(heading?'h4':'p');p.textContent=line.replace(/^#{1,3} /,'');container.appendChild(p);});}
    function descriptionPreview(text){formatNote(detail,text);detail.hidden=!text.trim();}
    dialog.addEventListener('click',function(e){if(e.target!==dialog)return;var r=dialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)dialog.close();});
    /* The card is a view over the same anchored note, never a second coordinate-bound copy. */
    var sideTarget=null,sideEditing=false,sideContent='',sideLane='left',sideChoice='auto';
    var sideCard=document.createElement('aside');sideCard.id='annotationCard';sideCard.className='workspace-runtime-ui annotation-card';sideCard.hidden=true;sideCard.setAttribute('aria-label','功能说明卡');
    sideCard.innerHTML='<header><strong id="annotationCardTitle">功能说明</strong><select id="annotationCardSide" aria-label="说明卡位置"><option value="auto">自动选侧</option><option value="left">左侧</option><option value="right">右侧</option></select><button class="tb" id="annotationCardClose" aria-label="关闭说明卡">×</button></header><p id="annotationCardContext"></p><div class="annotation-card-body"><div id="annotationCardRead"></div><textarea id="annotationCardText" aria-label="编辑说明全文" hidden></textarea></div><footer><button class="tb" id="annotationCardEdit">编辑说明</button><button class="tb on" id="annotationCardSave" hidden>保存说明</button><button class="tb" id="annotationCardCancel" hidden>取消编辑</button><button class="tb" id="annotationCardFullEdit">完整编辑 / 模板</button><span id="annotationCardStatus"></span></footer>';body.appendChild(sideCard);
    var sideLine=document.createElementNS('http://www.w3.org/2000/svg','svg');sideLine.id='annotationConnector';sideLine.classList.add('workspace-runtime-ui');sideLine.setAttribute('aria-hidden','true');sideLine.innerHTML='<path fill="none" stroke="#e9692d" stroke-width="2"/><circle r="5" fill="#e9692d"/>';sideLine.style.display='none';body.appendChild(sideLine);
    function closeCard(){sideTarget=null;sideCard.hidden=true;sideLine.style.display='none';body.classList.remove('has-annotation-card','annotation-right','annotation-drawer');}
    function chooseCardSide(){if(!sideTarget)return;var wasOpen=body.classList.contains('has-annotation-card');body.classList.remove('has-annotation-card','annotation-right','annotation-drawer');var cr=canvas.getBoundingClientRect(),vp=sideTarget.closest('.viewport').getBoundingClientRect();sideLane=sideChoice==='auto'?(cr.right-vp.right>vp.left-cr.left+8?'right':'left'):sideChoice;body.classList.toggle('annotation-right',sideLane==='right');if(wasOpen)body.classList.add('has-annotation-card');}
    document.getElementById('annotationCardSide').onchange=function(){sideChoice=this.value;chooseCardSide();requestAnimationFrame(function(){sideTarget.scrollIntoView({behavior:'instant',block:'nearest',inline:'nearest'});updateCard();});};
    function cardEditing(on){sideEditing=!!on;document.getElementById('annotationCardRead').hidden=sideEditing;document.getElementById('annotationCardText').hidden=!sideEditing;document.getElementById('annotationCardEdit').hidden=sideEditing;document.getElementById('annotationCardSave').hidden=!sideEditing;document.getElementById('annotationCardCancel').hidden=!sideEditing;document.getElementById('annotationCardFullEdit').hidden=sideEditing;if(on){document.getElementById('annotationCardText').value=sideTarget.getAttribute('data-note')||'';document.getElementById('annotationCardText').focus();}}
    function updateCard(){
      if(!sideTarget)return;if(!sideTarget.isConnected){var key=sideTarget.getAttribute('data-annotation-anchor');sideTarget=entries(true).find(function(el){return el.getAttribute('data-annotation-anchor')===key;});if(!sideTarget){closeCard();return;}}
      var sc=sideTarget.closest('.screen');if(sc!==currentScreenEl()||!body.classList.contains('shownotes')){closeCard();return;}
      var text=sideTarget.getAttribute('data-note')||'';if(!text.trim()){closeCard();return;}if(sideContent!==text){formatNote(document.getElementById('annotationCardRead'),text);sideContent=text;}
      var cr=canvas.getBoundingClientRect(),r=sideTarget.getBoundingClientRect(),vp=sideTarget.closest('.viewport').getBoundingClientRect(),width=Math.min(350,Math.max(290,innerWidth*.22)),topbar=bar.getBoundingClientRect().bottom,narrow=innerWidth<1100||cr.width<width+Math.min(390,(sc.querySelector('.device')||sideTarget.closest('.viewport')).getBoundingClientRect().width)+88,right=sideLane==='right';
      body.classList.toggle('annotation-drawer',narrow);document.documentElement.style.setProperty('--annotation-card-width',width+'px');
      var cardTop=Math.max(topbar+16,Math.min(r.top,innerHeight-360));Object.assign(sideCard.style,{left:((right&&!narrow)?cr.right-width-16:cr.left+16)+'px',top:narrow?'auto':cardTop+'px',bottom:narrow?'16px':'auto',width:(narrow?Math.min(420,cr.width-32):width)+'px',maxHeight:(narrow?Math.min(400,innerHeight*.45):innerHeight-cardTop-14)+'px'});
      var visible=r.bottom>Math.max(cr.top,vp.top)&&r.top<Math.min(cr.bottom,vp.bottom)&&r.right>cr.left&&r.left<cr.right;sideLine.style.display=visible&&!narrow?'block':'none';
      if(visible&&!narrow){var cb=sideCard.getBoundingClientRect(),x=right?cb.left:cb.right,y=Math.min(cb.bottom-24,Math.max(cb.top+45,r.top+r.height/2)),tx=Math.max(vp.left,Math.min(vp.right,right?r.right-Math.min(r.width/2,24):r.left+Math.min(r.width/2,24))),ty=Math.max(vp.top+5,Math.min(vp.bottom-5,r.top+Math.min(r.height/2,24))),dir=right?-1:1;sideLine.querySelector('path').setAttribute('d','M '+x+' '+y+' C '+(x+30*dir)+' '+y+', '+(tx-30*dir)+' '+ty+', '+tx+' '+ty);sideLine.querySelector('circle').setAttribute('cx',tx);sideLine.querySelector('circle').setAttribute('cy',ty);}
      document.getElementById('annotationCardStatus').textContent=visible?'说明跟随当前目标':'目标已滚出视口；说明仍可查看';
    }
    function showCard(el){sideTarget=el;sideContent='';sideCard.hidden=false;chooseCardSide();body.classList.add('has-annotation-card');var sc=el.closest('.screen');document.getElementById('annotationCardTitle').textContent=el.getAttribute('data-note-type')==='change'?'变更说明':el.getAttribute('data-note-type')==='flow'?'流程说明':'功能说明';document.getElementById('annotationCardContext').textContent=(sc?sc.getAttribute('data-name'):'页面')+' · '+(el.matches('.app,.adpage,.viewport')?'页面标注':(el.getAttribute('aria-label')||el.textContent||'功能点').trim().slice(0,45));cardEditing(false);updateCard();requestAnimationFrame(function(){el.scrollIntoView({behavior:'instant',block:'nearest',inline:'nearest'});updateCard();});tip.hidden=true;}
    document.getElementById('annotationCardClose').onclick=closeCard;
    document.getElementById('annotationCardEdit').onclick=function(){cardEditing(true);};
    document.getElementById('annotationCardCancel').onclick=function(){cardEditing(false);};
    document.getElementById('annotationCardSave').onclick=function(){if(!editorAllowed()||!sideTarget)return;var text=document.getElementById('annotationCardText').value.trim();if(!text){snapshot();anchorNotes.forget(sideTarget);sideTarget.removeAttribute('data-note');sideTarget.removeAttribute('data-note-type');scheduleSave();closeCard();queuePins();return;}snapshot();sideTarget.setAttribute('data-note',text);anchorNotes.remember(sideTarget);scheduleSave();cardEditing(false);updateCard();queuePins();};
    document.getElementById('annotationCardFullEdit').onclick=function(){openTarget(sideTarget);};
    document.getElementById('annotationCardRead').ondblclick=function(){document.getElementById('annotationCardEdit').click();};
    document.getElementById('annotationCardRead').title='双击可自由编辑说明，段落和内容不限模板';
    body.classList.add('anchored-annotations');
    document.getElementById('annotationText').addEventListener('input',function(){descriptionPreview(this.value);});
    document.getElementById('annotationTemplate').onclick=function(){if(!editorAllowed()||!target)return;var kind=document.getElementById('annotationTemplateKind').value,sc=target.closest('.screen'),name=kind==='page'?(sc?sc.getAttribute('data-name'):'当前页面'):(target.getAttribute('aria-label')||target.getAttribute('placeholder')||target.textContent||'当前功能').trim().slice(0,60);var text='【'+(kind==='page'?'页面说明':kind==='change'?'变更说明':kind==='flow'?'流程说明':'功能点说明')+'】'+name+'\n需求编号：待确认\n\n【功能目的】\n说明用户希望完成什么任务。\n\n【入口与前置条件】\n说明入口、适用角色和数据条件。\n\n【操作流程】\n1. 用户输入或选择。\n2. 系统校验并给出结果。\n3. 成功后进入下一步或返回。\n\n【字段与业务规则】\n明确必填项、格式、边界、计算与状态约束。\n\n【异常与空状态】\n明确无数据、输入错误、操作失败与恢复方式。\n\n【验收条件】\n列出可以实际操作核对的结果。\n\n【变更记录】\n记录变更内容、影响范围；未确认规则明确标为待确认。';var field=document.getElementById('annotationText');field.value=field.value.trim()?field.value+'\n\n'+text:text;descriptionPreview(field.value);document.getElementById('annotationType').value=kind==='change'?'change':kind==='flow'?'flow':'function';};
    var annotationLimit=80;document.getElementById('annotationSearch').oninput=function(){annotationLimit=80;render();};document.getElementById('annotationScope').onchange=function(){annotationLimit=80;render();};
    function entries(skipSync){if(!skipSync)anchorNotes.sync();return Array.from(canvas.querySelectorAll('[data-note]')).filter(function(el){return (el.getAttribute('data-note')||'').trim();});}
    function render(){
      var container=document.getElementById('annotationItems');container.replaceChildren();
      var all=entries();listButton.textContent='标注列表 ('+all.length+')';var term=document.getElementById('annotationSearch').value.trim().toLowerCase(),scope=document.getElementById('annotationScope').value;var matches=all.filter(function(el){var sc=el.closest('.screen');return (scope!=='current'||sc===currentScreenEl())&&(!term||((sc?sc.getAttribute('data-name'):'')+' '+el.getAttribute('data-note')).toLowerCase().includes(term));});document.getElementById('annotationMatches').textContent='匹配 '+matches.length+' / 全部 '+all.length+'；点击条目查看完整说明';
      if(!all.length){var empty=document.createElement('p');empty.textContent='还没有标注。选中元素后点击“＋ 标注”，也可为当前页面添加。';container.appendChild(empty);}
      matches.slice(0,annotationLimit).forEach(function(el){var row=document.createElement('button');row.className='annotation-entry';var sc=el.closest('.screen');var title=document.createElement('strong');title.textContent=(sc?sc.getAttribute('data-name'):'页面')+' · '+(el.getAttribute('data-note-type')==='change'?'变更记录':'功能说明');var content=document.createElement('span'),text=el.getAttribute('data-note');content.textContent=text.length>180?text.slice(0,180)+'…（点击查看全文）':text;row.append(title,content);row.onclick=function(){target=el;if(sc)goTo(sc.getAttribute('data-screen'));if(edit&&!annotationPicking)select(el);el.scrollIntoView({block:'nearest',inline:'nearest',behavior:'instant'});refreshTarget();dialogBody.scrollTop=0;detail.scrollTop=0;queuePins();};container.appendChild(row);});if(matches.length>annotationLimit){var more=document.createElement('button');more.className='tb';more.id='annotationMore';more.textContent='继续显示下一批说明';more.onclick=function(){annotationLimit+=80;render();};container.appendChild(more);}
    }
    function refreshTarget(){
      dialog.classList.toggle('annotation-readonly',!editorUnlocked);
      var sc=target&&target.closest('.screen');document.getElementById('annotationTarget').textContent=target?'当前目标：'+(sc?sc.getAttribute('data-name'):'页面')+' / '+(target.getAttribute('data-eid')||target.className):'点击下方标注可查看内容并定位页面。';
      document.getElementById('annotationText').value=target?target.getAttribute('data-note')||'':'';
      descriptionPreview(document.getElementById('annotationText').value);
      document.getElementById('annotationType').value=target&&['change','flow'].includes(target.getAttribute('data-note-type'))?target.getAttribute('data-note-type'):'function';
      document.getElementById('annotationTemplateKind').value=target&&target.matches('.app,.adpage,.viewport')?'page':target&&target.getAttribute('data-note-type')==='flow'?'flow':'function';
      ['annotationText','annotationType','annotationSave','annotationDelete','annotationTemplate','annotationTemplateKind'].forEach(function(id){document.getElementById(id).disabled=!target||!editorUnlocked;});
    }
    function openTarget(el){target=el;refreshTarget();render();if(!dialog.open)dialog.showModal();dialogBody.scrollTop=0;detail.scrollTop=0;if(editorUnlocked)document.getElementById('annotationText').focus();}
    add.onclick=function(){if(!editorAllowed(function(){add.click();}))return;if(!edit){picking(true);return;}var sc=currentScreenEl();if(!selected||!selected.isConnected||selected.closest('.screen')!==sc||selected.matches('.app,.adpage,.viewport,.mall-content')){picking(true);toast('请点击需要说明的具体功能或流程节点；不会自动绑定整页。');return;}openTarget(selected);};
    pageButton.onclick=function(){if(!editorAllowed(function(){pageButton.click();}))return;pagePinsEnabled=true;queuePins();var sc=currentScreenEl();if(sc)openTarget(sc.querySelector('.app')||sc.querySelector('.adpage')||sc.querySelector('.viewport'));};
    var parentButton=document.createElement('button');parentButton.id='annotationParent';parentButton.className='tb';parentButton.textContent='选择上一级功能区';document.querySelector('#annotationEditor .annotation-actions').appendChild(parentButton);
    parentButton.onclick=function(){if(target&&target.parentElement&&target.parentElement.closest('.viewport')&&!target.parentElement.matches('.app,.adpage,.viewport,.mall-content'))openTarget(target.parentElement);else toast('已到当前功能区边界；整页说明请明确使用页面标注。');};
    document.addEventListener('pointerdown',function(e){if(annotationPicking&&canvas.contains(e.target)){e.preventDefault();e.stopImmediatePropagation();}},true);
    document.addEventListener('click',function(e){if(!annotationPicking||!canvas.contains(e.target))return;e.preventDefault();e.stopImmediatePropagation();var el=e.target.closest('button,[data-on]')||e.target;if(el.closest('.viewport')&&!el.matches('.app,.adpage,.viewport,.mall-content'))openTarget(el);else toast('请点击具体功能点，整页说明使用单独的页面标注入口。');},true);
    canvas.addEventListener('pointermove',function(e){if(!annotationPicking)return;canvas.querySelectorAll('.annotation-hover').forEach(function(el){el.classList.remove('annotation-hover');});var el=e.target.closest('button,[data-on]')||e.target;if(el.closest('.viewport')&&!el.matches('.app,.adpage,.viewport,.mall-content'))el.classList.add('annotation-hover');});
    document.addEventListener('keydown',function(e){if(e.key!=='Escape')return;var gate=document.getElementById('editorGate');if(gate.open){e.preventDefault();e.stopImmediatePropagation();document.getElementById('gateCancel').click();return;}var opened=document.querySelector('dialog[open]');if(opened){e.preventDefault();e.stopImmediatePropagation();opened.close();return;}if(sideTarget||annotationPicking){e.preventDefault();e.stopImmediatePropagation();closeCard();picking(false);}},true);
    listButton.onclick=function(){target=null;refreshTarget();render();dialog.showModal();};
    document.getElementById('annotationClose').onclick=function(){dialog.close();};
    document.getElementById('annotationSave').onclick=function(){if(!editorAllowed()||!target||!target.isConnected)return;var value=document.getElementById('annotationText').value.trim();if(!value){document.getElementById('annotationDelete').click();return;}snapshot();target.setAttribute('data-note',value);target.setAttribute('data-note-type',document.getElementById('annotationType').value);anchorNotes.remember(target);scheduleSave();document.body.classList.add('shownotes');if(selected===target)syncPanel();render();queuePins();toast('标注已保存，仅绑定当前所选目标。');};
    document.getElementById('annotationDelete').onclick=function(){if(!editorAllowed()||!target)return;snapshot();anchorNotes.forget(target);target.removeAttribute('data-note');target.removeAttribute('data-note-type');scheduleSave();if(selected===target)syncPanel();refreshTarget();render();queuePins();};
    document.getElementById('fNote').addEventListener('change',function(){if(!editorUnlocked||!selected)return;if(this.value.trim())anchorNotes.remember(selected);else anchorNotes.forget(selected);queuePins();});
    function paintPins(){pinsQueued=false;anchorNotes.sync();pins.replaceChildren();if(!body.classList.contains('shownotes')){closeCard();return;}updateCard();var cr=canvas.getBoundingClientRect();entries(true).forEach(function(el,index){if(!pagePinsEnabled&&el.matches('.app,.adpage,.viewport'))return;var sc=el.closest('.screen'),vp=el.closest('.viewport'),r=el.getBoundingClientRect();if(!sc||!vp||!r.width||!r.height||!el.checkVisibility())return;var vr=vp.getBoundingClientRect(),x=Math.min(r.right-8,vr.right-22),y=Math.max(r.top+3,vr.top+3);if(x<Math.max(cr.left,vr.left)||x>Math.min(cr.right,vr.right)-18||y<Math.max(cr.top,vr.top)||y>Math.min(cr.bottom,vr.bottom)-22)return;var pin=document.createElement('button');pin.className='annotation-pin';pin.textContent=String(index+1);pin.title='点击查看完整说明，可随时编辑';pin.setAttribute('aria-label','查看标注 '+(index+1));pin.dataset.anchor=el.getAttribute('data-annotation-anchor');pin.style.left=x+'px';pin.style.top=y+'px';pin.onclick=function(e){e.stopPropagation();showCard(el);};pins.appendChild(pin);});}
    function queuePins(){if(!pinsQueued){pinsQueued=true;requestAnimationFrame(paintPins);}}
    var tip=document.createElement('div');tip.id='annotationTooltip';tip.className='workspace-runtime-ui';tip.hidden=true;body.appendChild(tip);
    function showNoteTip(e){var el=e.target.closest('[data-note]');if(!el||sideTarget||el.matches('.app,.adpage,.viewport')||!body.classList.contains('shownotes')){tip.hidden=true;return;}var note=el.getAttribute('data-note');tip.textContent=note.slice(0,120)+(note.length>120?'…':'')+'\n点击橙色编号查看完整说明';tip.hidden=false;var r=el.getBoundingClientRect();tip.style.left=Math.max(8,Math.min(innerWidth-330,r.left))+'px';tip.style.top=Math.max(parseFloat(getComputedStyle(document.documentElement).getPropertyValue('--ed-bar-height'))+4,Math.min(innerHeight-tip.offsetHeight-12,r.bottom+8))+'px';}
    canvas.addEventListener('pointerover',showNoteTip);canvas.addEventListener('pointermove',showNoteTip);
    canvas.addEventListener('pointerout',function(e){if(!e.relatedTarget||!e.target.closest('[data-note]')||!e.target.closest('[data-note]').contains(e.relatedTarget))tip.hidden=true;});
    canvas.addEventListener('scroll',function(){tip.hidden=true;queuePins();},true);window.addEventListener('resize',queuePins);
    var queued=false;
    function workspaceSize(){queued=false;var h=Math.ceil(bar.getBoundingClientRect().height);document.documentElement.style.setProperty('--ed-bar-height',h+'px');/* 批1a修复：编辑态（已解锁）常挂 has-inspector，画布让位与选中解耦——修复"单击选中→画布重排336px→双击落点错位/改错元素"。副作用=编辑态右侧恒预留面板宽（inspector 未选中时空态），预览态不受影响 */var hasPanel=edit&&editorUnlocked;body.classList.toggle('has-inspector',hasPanel);if(hasPanel&&selected&&selected.isConnected){var sr=selected.getBoundingClientRect(),cr=canvas.getBoundingClientRect();if(sr.left<cr.left||sr.right>cr.right||sr.top<cr.top||sr.bottom>cr.bottom)selected.scrollIntoView({behavior:'instant',block:'nearest',inline:'nearest'});}if(!body.classList.contains('shownotes'))tip.hidden=true;freeUpdate();queuePins();}
    function update(){if(!queued){queued=true;requestAnimationFrame(workspaceSize);}}
    new ResizeObserver(update).observe(bar);new MutationObserver(update).observe(inspector,{attributes:true,attributeFilter:['hidden']});new MutationObserver(update).observe(body,{attributes:true,attributeFilter:['class']});
    new MutationObserver(function(){listButton.textContent='标注列表 ('+entries(true).length+')';queuePins();}).observe(canvas,{subtree:true,attributes:true,attributeFilter:['data-note','style','hidden','class'],childList:true});
    window.addEventListener('resize',update);workspaceSize();render();if(!editorConfig.editPassword){var lh=document.getElementById('lockHint');if(lh)lh.textContent='请先设置编辑口令并保存到当前源文件；不自动下载';}
  }
