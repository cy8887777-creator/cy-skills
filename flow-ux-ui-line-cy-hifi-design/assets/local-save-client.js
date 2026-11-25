  /* Local companion session exists only in the served response, never in a saved HTML. */
  function localSaveSession(){
    var node=document.getElementById('prototype-local-session');if(!node)return null;
    try{var value=JSON.parse(node.textContent),url=new URL(value.saveURL,location.href);if(location.protocol!=='http:'||location.hostname!=='127.0.0.1'||url.origin!==location.origin||typeof value.token!=='string'||!value.etag)return null;return value;}catch(e){return null;}
  }
  function localSavePreferred(){return document.documentElement.getAttribute('data-save-mode')==='local-helper';}
  function saveViaLocalHelper(){
    if(!editorAllowed(saveSourceHTML))return Promise.resolve(false);
    if(saving){toast('正在保存，请稍候');return Promise.resolve(false);}
    var session=localSaveSession();if(!session)return Promise.resolve(false);saving=true;
    var rev=changeRevision,oldBuilt=builtAt;builtAt=builtAt||String(Date.now());var html;
    try{html=buildExport(builtAt);}catch(e){saving=false;builtAt=oldBuilt;toast('未保存：'+e.message);return Promise.resolve(false);}
    return fetch(session.saveURL,{method:'POST',headers:{'Content-Type':'application/json','X-Prototype-Token':session.token},body:JSON.stringify({html:html,baseHash:session.etag})}).then(function(response){return response.json().then(function(result){if(!response.ok||!result.ok)throw new Error(result.message||'本地写入失败');return result;});}).then(function(result){
      session.etag=result.etag;document.getElementById('prototype-local-session').textContent=JSON.stringify(session);sourcePasswordPending=false;
      document.documentElement.setAttribute('data-exported','1');document.documentElement.setAttribute('data-built',builtAt);exported=true;LS='prdproto:'+storageScope+':export:'+builtAt;
      if(changeRevision===rev)clearDirty();else markDirty();boundFingerprint=html;
      document.getElementById('lockHint').textContent=changeRevision===rev?'已直接覆盖源文件「'+result.file+'」 · 原口令与全部编辑已保存':'已覆盖源文件，保存期间又有新修改，请再点保存';
      toast('已覆盖保存源文件「'+result.file+'」',3000);return true;
    }).catch(function(error){builtAt=oldBuilt;var message=error.message==='Failed to fetch'?'本地保存程序未连接，请启动保存器并从中重新打开原型；当前修改仍保留':error.message;toast('未保存：'+message,5500);if(sourcePasswordPending)document.getElementById('lockHint').textContent='口令尚未写入源文件 · '+message;return false;}).finally(function(){saving=false;});
  }
  function initLocalSaveUI(){
    // A first-password save can happen before gateDerive.finally reenables this runtime control.
    document.getElementById('gateConfirm').disabled=false;
    var session=localSaveSession(),preferred=localSavePreferred();
    if(session){
      document.getElementById('btnSave').title='直接覆盖源文件「'+session.file+'」，不选择文件、不下载';
      document.getElementById('lockHint').textContent=editorConfig.editPassword?'本地直存已连接 · 输入原口令继续编辑':'本地直存已连接 · 首次设置口令后直接保存到源文件';
    }else if(preferred){
      document.getElementById('btnSave').title='请通过同目录的“Windows 原型本地保存器.exe”或“macOS 原型本地保存器.command”打开，保存会直接覆盖源文件';
      document.getElementById('lockHint').textContent='单独打开HTML：通过“Windows 原型本地保存器.exe”或“macOS 原型本地保存器.command”打开后可直接保存；当前可预览、编辑和下载副本';
    }
    // Gate content is rendered when requested; keep the single password field and its validation.
    var gate=document.getElementById('editorGate');new MutationObserver(function(){if(!gate.open||editorConfig.editPassword)return;if(session||preferred)document.getElementById('gateDescription').textContent=session?'只需设置至少8位口令。设置后直接写入当前源HTML，不下载、不选择文件；以后使用原口令编辑。':'只需设置至少8位口令。若需直接覆盖源文件，请通过同目录的本地保存器打开；当前修改可主动下载为完整副本。';}).observe(gate,{attributes:true,attributeFilter:['open']});
  }
