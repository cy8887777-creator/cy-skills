  /* Geometry stays on the selected DOM node: product/action ancestry is retained. */
  function directTarget(el){
    if(!el||!el.isConnected||!el.closest('.viewport')||el.matches('.viewport,.app,.adpage,.mall-content,.statusbar,.appbar,.tabbar,.mall-bottom,[data-editor-placeholder],script'))return null;
    var item=freeItem(el);
    if(item&&item.parentElement.classList.contains('free-canvas')&&(el===item||item.classList.contains('btns')))return item;
    return el;
  }
  function directRoot(el){var root=freeRoot(el.closest('.screen'));return root&&root.contains(el)?root:(el.closest('.app,.adpage')||el.closest('.viewport'));}
  function directGeometry(el){
    var root=directRoot(el),r=el.getBoundingClientRect(),rr=root.getBoundingClientRect(),scale=freeScale(root);
    return {x:(r.left-rr.left)/scale+root.scrollLeft,y:(r.top-rr.top)/scale+root.scrollTop,w:r.width/scale,h:r.height/scale,root:root,scale:scale};
  }
  function directPrepare(el){
    if(el.hasAttribute('data-free-item')&&el.parentElement.classList.contains('free-canvas'))return;
    var g=directGeometry(el),cs=getComputedStyle(el);
    if(!el.hasAttribute('data-direct-item')){
      el.setAttribute('data-direct-item','1');
      if(cs.position==='static')el.style.position='relative';
      if(cs.display==='inline')el.style.display='inline-block';
      el.style.left=(parseFloat(el.style.left)||0)+'px';el.style.top=(parseFloat(el.style.top)||0)+'px';
      el.style.width=Math.round(g.w)+'px';el.style.height=Math.round(g.h)+'px';
    }
    el.style.flex='none';el.style.boxSizing='border-box';el.style.minWidth='24px';el.style.minHeight='24px';el.style.maxWidth='none';el.style.maxHeight='none';
    // Moving a nested feature should not be clipped by its former card bounds.
    for(var parent=el.parentElement;parent&&parent!==el.closest('.viewport');parent=parent.parentElement){
      var style=getComputedStyle(parent);if(/hidden|clip/.test(style.overflow+style.overflowX+style.overflowY)){parent.setAttribute('data-editor-overflow','1');parent.style.overflow='visible';}
    }
  }
  function directCoordinate(el,key,value){
    directPrepare(el);var g=directGeometry(el),property=key==='x'?'left':'top';el.style[property]=Math.round((parseFloat(el.style[property])||0)+value-g[key])+'px';
  }
  function directRadius(el){var value=getComputedStyle(el).borderTopLeftRadius,g=directGeometry(el);return value.includes('%')?Math.min(g.w,g.h)*parseFloat(value)/100:parseFloat(value)||0;}
  function directSetRadius(el,value){el.style.borderRadius=value;el.removeAttribute('data-editor-shape');if(el.matches('.btns'))Array.from(el.children).forEach(function(child){if(child.matches('.b,button'))child.style.borderRadius='inherit';});}
  function directLayouts(){var node=document.getElementById('prototype-layouts');try{return node?JSON.parse(node.textContent):[];}catch(e){return [];}}
  function directRemember(el){
    if(!el||!el.closest('.screen'))return;
    /* T03.1b 单一真相：record.style 只是元素 style 属性的锚点快照，不是第二份值来源。
       实例覆盖登记（editor-seed.html data-editor-ov）不复制任何样式值——只记来源
       （panel/custom-css/legacy-local）+时间戳，并以 entry.anchor 引用本记录的
       data-layout-anchor id（去重引用，避免两份真相）。「恢复所选属性跟随全局」
       (resetInstanceOverrides) 删属性后会重调 directRemember 重录 style 串，
       布局记录随之不再含已恢复属性。 */
    var records=directLayouts(),id=el.getAttribute('data-layout-anchor'),sc=el.closest('.screen'),product=el.closest('[data-product]');
    if(!id||Array.from(canvas.querySelectorAll('[data-layout-anchor]')).some(function(n){return n!==el&&n.getAttribute('data-layout-anchor')===id;}))id='layout-'+crypto.randomUUID();el.setAttribute('data-layout-anchor',id);
    var record={id:id,page:sc.getAttribute('data-screen'),eid:el.getAttribute('data-eid'),tag:el.tagName,product:product&&product.getAttribute('data-product'),action:el.getAttribute('data-on'),field:el.getAttribute('data-field'),style:el.getAttribute('style')||'',direct:el.getAttribute('data-direct-item'),sizing:el.getAttribute('data-direct-sizing'),shape:el.getAttribute('data-editor-shape')};
    var index=records.findIndex(function(r){return r.id===id;});if(index<0)records.push(record);else records[index]=record;
    var node=document.getElementById('prototype-layouts');if(!node){node=document.createElement('script');node.id='prototype-layouts';node.type='application/json';canvas.appendChild(node);}node.textContent=JSON.stringify(records).replace(/</g,'\\u003c');
  }
  function directForget(el){
    var ids=new Set(Array.from(el.querySelectorAll('[data-layout-anchor]')).concat([el]).map(function(n){return n.getAttribute('data-layout-anchor');}));
    var node=document.getElementById('prototype-layouts');if(node)node.textContent=JSON.stringify(directLayouts().filter(function(r){return !ids.has(r.id);})).replace(/</g,'\\u003c');
  }
  function directRestore(){
    if(freeGesture)return;
    directLayouts().forEach(function(rec){
      var sc=screenEl(rec.page);if(!sc)return;var all=Array.from(sc.querySelectorAll('[data-layout-anchor]')),el=all.find(function(n){return n.getAttribute('data-layout-anchor')===rec.id;});
      // Existing live nodes are authoritative. Do not roll back later colour,
      // text or CSS edits just because an unrelated business list changed.
      if(el)return;
      if(!el){
        var root=sc;if(rec.product){root=Array.from(sc.querySelectorAll('[data-product]')).find(function(n){return n.getAttribute('data-product')===rec.product;});if(!root)return;}
        var candidates=Array.from(root.querySelectorAll(rec.tag));
        if(root.tagName===rec.tag)candidates.unshift(root);
        if(rec.action)candidates=candidates.filter(function(n){return n.getAttribute('data-on')===rec.action;});
        else if(rec.field)candidates=candidates.filter(function(n){return n.getAttribute('data-field')===rec.field;});
        else if(!rec.product)candidates=candidates.filter(function(n){return n.getAttribute('data-eid')===rec.eid;});
        if(candidates.length!==1)return;el=candidates[0];
      }
      if(el.getAttribute('style')!==rec.style)el.setAttribute('style',rec.style);
      el.setAttribute('data-layout-anchor',rec.id);
      [['data-direct-item',rec.direct],['data-direct-sizing',rec.sizing],['data-editor-shape',rec.shape]].forEach(function(pair){if(pair[1]!==null)el.setAttribute(pair[0],pair[1]);});
      for(var parent=el.parentElement;parent&&parent!==el.closest('.viewport');parent=parent.parentElement){var style=getComputedStyle(parent);if(/hidden|clip/.test(style.overflow+style.overflowX+style.overflowY)){parent.setAttribute('data-editor-overflow','1');parent.style.overflow='visible';}}
    });
    freeUpdate();
  }
  function initDirectControls(panel){
    var tools=document.createElement('div');tools.className='direct-controls';tools.innerHTML='<label>拖拽方式<select id="freeMoveMode"><option value="direct">直接移动（默认）</option><option value="flow">原有流式排序</option></select></label><label>尺寸适应<select id="freeSizing"><option value="fixed">手动宽高</option><option value="fill">填满父容器宽度</option><option value="content">高度跟随内容</option></select></label><label>组件形状<select id="freeShape"><option value="rectangle">矩形</option><option value="rounded">圆角矩形</option><option value="pill">胶囊</option><option value="ellipse">椭圆 / 圆形</option></select></label><span class="hint">拖动组件改位置；拉边角改尺寸，Shift保留比例；拖动菱形点改圆角。</span>';
    panel.appendChild(tools);
    document.getElementById('freeSizing').onchange=function(){var el=directTarget(selected);if(!editorAllowed()||!el)return;snapshot();directPrepare(el);el.setAttribute('data-direct-sizing',this.value);if(this.value==='fill'){el.style.width='100%';el.style.left='0px';el.style.height='auto';}else if(this.value==='content'){el.style.height='auto';}else{var g=directGeometry(el);el.style.width=Math.round(g.w)+'px';el.style.height=Math.round(g.h)+'px';}directRemember(el);scheduleSave();syncPanel();};
    document.getElementById('freeShape').onchange=function(){var el=directTarget(selected);if(!editorAllowed()||!el)return;snapshot();var kind=this.value;directSetRadius(el,{rectangle:'0px',rounded:'12px',pill:'9999px',ellipse:'50%'}[kind]);el.setAttribute('data-editor-shape',kind);directRemember(el);scheduleSave();syncPanel();};
    document.getElementById('fStyle').addEventListener('change',function(){if(editorUnlocked&&selected&&selected.hasAttribute('data-layout-anchor'))directRemember(selected);});
    var queued=false;new MutationObserver(function(){if(!queued){queued=true;requestAnimationFrame(function(){queued=false;directRestore();});}}).observe(canvas,{childList:true,subtree:true});directRestore();
  }
