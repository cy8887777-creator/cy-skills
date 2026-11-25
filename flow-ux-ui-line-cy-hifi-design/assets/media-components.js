/*MEDIA_COMPONENTS_START*/
  // Component state lives in the canvas, so history and complete HTML exports share it.
  (function(){
    var demoVideo='__DEMO_VIDEO_DATA__';
    function picture(i){return 'data:image/svg+xml;base64,'+btoa(unescape(encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="320"><rect width="640" height="320" fill="'+['#183446','#315568','#637f8c'][i%3]+'"/><circle cx="500" cy="130" r="85" fill="#ffffff18"/><text x="36" y="120" fill="white" font-size="30">内容 '+(i+1)+' / Slide '+(i+1)+'</text><text x="36" y="175" fill="#dce7ed" font-size="19">离线示意 · 可替换图片与说明</text></svg>')));}
    function button(action,label){return '<button type="button" class="b ghost" data-media-action="'+action+'">'+label+'</button>';}
    function slide(src,index,prefix,hidden){return '<figure data-media-slide'+(hidden?' hidden':'')+' data-eid="'+prefix+'-slide-'+index+'"><img src="'+escHtml(src)+'" alt="离线示意图片" data-eid="'+prefix+'-image-'+index+'"><figcaption data-eid="'+prefix+'-caption-'+index+'">内容说明 '+(index+1)+'</figcaption></figure>';}
    function template(kind){
      var items='';for(var i=0;i<3;i++)items+=slide(picture(i),i,'%E',kind==='video'||i>0);
      return '<div class="prototype-media" data-block="custom" data-eid="%E" data-media-widget="'+kind+'" data-media-index="0" data-media-first="'+(kind==='video'?'video':'image')+'" data-media-autoplay="'+(kind==='carousel'?'1':'0')+'" data-media-interval="4800">'
        +'<div class="prototype-media-stage">'+items+'<video data-media-video data-eid="%E-video" controls playsinline preload="metadata" src="'+demoVideo+'"'+(kind==='video'?'':' hidden')+'></video></div>'
        +'<div class="prototype-media-controls">'+button('prev','‹ 上一张')+'<span data-media-counter>1 / 3</span>'+button('next','下一张 ›')+button('image','图片')+button('video','视频')+'</div>'
        +'<div class="prototype-media-controls">'+button('upload-video','上传视频')+button('configure','媒体设置')+'</div><p class="prototype-media-hint">离线示意媒体；上传后随完整HTML保存。</p></div>';
    }
    ['carousel','gallery','video'].forEach(function(kind,i){
      PAL[kind]=template(kind);
    });
    function slides(root){return Array.from(root.querySelectorAll(':scope>.prototype-media-stage>[data-media-slide]'));}
    function setText(el,text){if(el&&el.textContent!==text)el.textContent=text;}
    function render(root){
      var images=slides(root),index=Number(root.getAttribute('data-media-index')||0);index=Math.max(0,Math.min(images.length-1,index));
      if(!root.hasAttribute('data-media-view'))root.setAttribute('data-media-view',root.getAttribute('data-media-first')||'image');
      var mode=root.getAttribute('data-media-view');images.forEach(function(item,i){item.hidden=mode==='video'||i!==index;});
      var video=root.querySelector('[data-media-video]');if(video){video.hidden=mode!=='video';if(video.hidden||!isPreview()||root.closest('.screen')!==screenEl(curId))video.pause();}
      setText(root.querySelector('[data-media-counter]'),images.length?(index+1)+' / '+images.length:'0 / 0');
      root.querySelectorAll('[data-media-slide] img').forEach(function(img){img.style.objectFit=root.getAttribute('data-media-fit')||'contain';});
    }
    function all(){return Array.from(canvas.querySelectorAll('[data-media-widget]'));}
    var waiting=false;
    function queue(){if(waiting)return;waiting=true;requestAnimationFrame(function(){waiting=false;all().forEach(render);});}
    new MutationObserver(queue).observe(canvas,{childList:true,subtree:true});
    new MutationObserver(queue).observe(document.body,{attributes:true,attributeFilter:['class']});
    function commit(root,change){if(!root.isConnected||!editorUnlocked)return;snapshot();change();render(root);scheduleSave();if(selected&&selected.isConnected)syncPanel();}
    function readFile(file){return new Promise(function(resolve,reject){var r=new FileReader();r.onload=function(){resolve(r.result);};r.onerror=function(){reject(Error('文件读取失败，原媒体未修改'));};r.readAsDataURL(file);});}
    function playable(data){return new Promise(function(resolve,reject){var probe=document.createElement('video'),done=false;var timer=setTimeout(function(){finish(false);},8000);function finish(ok){if(done)return;done=true;clearTimeout(timer);probe.onloadedmetadata=probe.onerror=null;probe.removeAttribute('src');probe.load();if(ok)resolve(data);else reject(Error('浏览器无法播放此视频，原媒体未修改；请使用兼容的MP4或WebM。'));}probe.preload='metadata';probe.onloadedmetadata=function(){finish(Number.isFinite(probe.duration)&&probe.duration>0);};probe.onerror=function(){finish(false);};probe.src=data;probe.load();});}
    function choose(root,kind,replace){
      if(!editorAllowed(function(){choose(root,kind,replace);}))return;
      var input=document.createElement('input');input.type='file';input.accept=kind==='video'?'video/mp4,video/webm':'image/*';input.multiple=kind!=='video'&&!replace;input.hidden=true;input.className='workspace-runtime-ui';document.body.appendChild(input);
      input.addEventListener('cancel',function(){input.remove();},{once:true});
      input.onchange=function(){
        var files=Array.from(input.files||[]);input.remove();if(!files.length)return;
        if(files.length>6||files.some(function(f){return f.size>8*1024*1024||!(kind==='video'?/^video\/(mp4|webm)$/:/^image\//).test(f.type);})){toast('请选择正确格式且单个不超过8MB的文件；图片一次最多6张。');return;}
        Promise.all(files.map(function(file){return readFile(file).then(function(data){if(kind==='video')return playable(data);return new Promise(function(resolve){compressImage(data,resolve);});});})).then(function(values){
          if(!editorUnlocked||!root.isConnected){toast('目标已关闭或锁定，原媒体未修改');return;}
          commit(root,function(){
            if(kind==='video'){var v=root.querySelector('[data-media-video]');v.pause();v.src=values[0];v.load();root.setAttribute('data-media-view','video');}
            else if(replace){var item=slides(root)[Number(root.getAttribute('data-media-index')||0)];if(item)item.querySelector('img').src=values[0];}
            else{var stage=root.querySelector('.prototype-media-stage');values.forEach(function(src){var tmp=document.createElement('div');tmp.innerHTML=slide(src,slides(root).length,newEid());stage.insertBefore(tmp.firstElementChild,stage.querySelector('video'));});root.setAttribute('data-media-index',slides(root).length-1);root.setAttribute('data-media-view','image');}
          });toast('媒体已内嵌；点击保存写回完整HTML');
        }).catch(function(e){toast(e.message);});
      };input.click();
    }
    function configure(root){
      if(!root||!root.isConnected)return;if(!editorAllowed(function(){configure(root);}))return;
      var d=document.createElement('dialog');d.className='prototype-media-dialog workspace-runtime-ui';
      d.innerHTML='<form method="dialog"><header><strong>媒体设置</strong><button value="cancel" class="tb">关闭</button></header><div class="prototype-media-fields"><label>首屏媒体<select data-setting="first"><option value="image">图片</option><option value="video">视频</option></select></label><label>自动轮播<select data-setting="autoplay"><option value="0">关闭</option><option value="1">开启</option></select></label><label>轮播间隔（毫秒）<input type="number" min="1000" max="60000" data-setting="interval"></label><label>图片适应<select data-setting="fit"><option value="contain">完整显示</option><option value="cover">填满裁切</option></select></label><label>当前图片说明<textarea rows="3" data-setting="caption"></textarea></label><label>当前图片跳转页面<select data-setting="target"><option value="">无跳转</option></select></label></div><footer><button type="button" data-setting-action="add">添加图片</button><button type="button" data-setting-action="replace">替换当前图片</button><button type="button" data-setting-action="video">上传视频</button><button type="button" data-setting-action="remove">删除当前图片</button><button type="submit" value="apply" class="b pri">应用设置</button></footer><p data-media-error role="status"></p></form>';
      var field=function(name){return d.querySelector('[data-setting="'+name+'"]');},item=slides(root)[Number(root.getAttribute('data-media-index')||0)];
      field('first').value=root.getAttribute('data-media-first')||'image';field('autoplay').value=root.getAttribute('data-media-autoplay')||'0';field('interval').value=root.getAttribute('data-media-interval')||4800;field('fit').value=root.getAttribute('data-media-fit')||'contain';field('caption').value=item?item.querySelector('figcaption').textContent:'';
      canvas.querySelectorAll('.screen').forEach(function(s){var option=document.createElement('option');option.value=s.dataset.screen;option.textContent=s.dataset.name||s.dataset.screen;field('target').appendChild(option);});
      try{field('target').value=item?(JSON.parse(item.getAttribute('data-on')||'{}').click||{}).goto||'':'';}catch(e){}
      d.querySelector('form').onsubmit=function(e){if(e.submitter&&e.submitter.value==='cancel')return;e.preventDefault();if(!editorUnlocked||!root.isConnected){d.close();return;}var interval=Number(field('interval').value);if(!Number.isFinite(interval)||interval<1000||interval>60000){d.querySelector('[data-media-error]').textContent='轮播间隔应为1000至60000毫秒';return;}
        commit(root,function(){root.setAttribute('data-media-first',field('first').value);root.setAttribute('data-media-view',field('first').value);root.setAttribute('data-media-autoplay',field('autoplay').value);root.setAttribute('data-media-interval',interval);root.setAttribute('data-media-fit',field('fit').value);if(item){item.querySelector('figcaption').textContent=field('caption').value;var target=field('target').value;if(target)item.setAttribute('data-on',JSON.stringify({click:{goto:target}}));else item.removeAttribute('data-on');}});d.close();
      };
      d.querySelectorAll('[data-setting-action]').forEach(function(b){b.onclick=function(){var action=b.dataset.settingAction;if(action==='remove'){if(slides(root).length<=1){d.querySelector('[data-media-error]').textContent='至少保留一张图片';return;}commit(root,function(){item.remove();root.setAttribute('data-media-index',0);});d.close();}else{d.close();choose(root,action==='video'?'video':'image',action==='replace');}};});
      d.addEventListener('click',function(e){if(e.target===d){var r=d.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)d.close();}});d.addEventListener('close',function(){d.remove();},{once:true});document.body.appendChild(d);d.showModal();
    }
    function initMediaUI(){
      ['carousel','gallery','video'].forEach(function(kind,i){if(!palette.querySelector('[data-ins="'+kind+'"]')){var b=document.createElement('button');b.dataset.ins=kind;b.className='workspace-runtime-ui';b.textContent=['广告轮播','图片图库','内嵌视频'][i];palette.appendChild(b);}});
      var old=document.getElementById('btnMediaSettings');if(old)old.remove();
      var panel=document.createElement('button');panel.id='btnMediaSettings';panel.className='mini workspace-runtime-ui';panel.textContent='媒体设置（轮播 / 图库 / 视频）';panel.type='button';panel.onclick=function(){var root=selected&&selected.closest('[data-media-widget]');if(root)configure(root);else toast('请先选中轮播、图库或视频组件');};var mGrpB=document.querySelector('#fGrpContent .ed-fgrp-b');if(mGrpB)mGrpB.appendChild(panel);else document.getElementById('insBody').appendChild(panel);
    }
    var previousInit=initFreeEditor;initFreeEditor=function(){previousInit();initMediaUI();};
    canvas.addEventListener('click',function(e){
      var b=e.target.closest('[data-media-action]'),root=b&&b.closest('[data-media-widget]');if(!root||!isPreview()||document.body.classList.contains('annotating'))return;
      e.preventDefault();e.stopImmediatePropagation();var action=b.dataset.mediaAction;
      if(action==='configure'){configure(root);return;}if(action==='upload-video'){choose(root,'video');return;}
      if(action==='image'||action==='video')root.setAttribute('data-media-view',action);
      else if(action==='next'||action==='prev'){var n=slides(root).length;root.setAttribute('data-media-index',(Number(root.getAttribute('data-media-index')||0)+(action==='next'?1:n-1))%Math.max(n,1));root.setAttribute('data-media-view','image');}
      render(root);
    },true);
    var ticks=new WeakMap();setInterval(function(){var now=Date.now();all().forEach(function(root){
      var run=isPreview()&&!document.hidden&&!document.body.classList.contains('annotating')&&!document.body.classList.contains('has-annotation-card')&&root.closest('.screen')===screenEl(curId)&&root.offsetParent&&root.getAttribute('data-media-autoplay')==='1'&&root.getAttribute('data-media-view')!=='video';
      if(!run){ticks.set(root,now);render(root);return;}var last=ticks.get(root);if(!last){ticks.set(root,now);return;}if(now-last>=Math.max(1000,Number(root.getAttribute('data-media-interval')||4800))){var count=slides(root).length;root.setAttribute('data-media-index',(Number(root.getAttribute('data-media-index')||0)+1)%Math.max(count,1));render(root);ticks.set(root,now);}
    });},250);all().forEach(render);
  })();
/*MEDIA_COMPONENTS_END*/
