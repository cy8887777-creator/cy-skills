"""Upgrade a known V2 prototype in a new file, preserving all pages and password data.

T01 双入口（T00 冻结单 §6 逐 patch 分类）：
- apply_current(source)：当前装配路径，只施加「需保留」patch，供 build.compose 消费；
  跳过「仅旧件」与「废弃」（P15 version 反向改写不再施加）。
- upgrade(source)（别名 upgrade_legacy）：既有全量行为，逐字保持不变，供 T07 K 集合旧件迁移调用。
main CLI 保持旧调用兼容（无子命令=仍走全量 upgrade）；migrate-k2 子命令＝V04 K2 受控迁移入口
（T07/C06）。REFIT（用户实测缺陷修复）后 migrate-k2 语义升级＝**编辑器脚本域全套装换装**：
商城旧件只提取页面域六件（头注释/标题/doc id/inject/pages/尾），编辑器域（主样式/主脚本，含
FREE 双块）整体以 apply_current(当前 editor-seed.html) 重建——旧管线只换 FREE JS/CSS 两块，
残留旧骨架（缺 applyStyleConfigOn 种子挂钩→向导 ReferenceError 卡死；旧视图结构并存→双视窗）。
校验升级：主脚本体/主样式体/FREE JS/FREE CSS 四跨度 SHA 必须与当前 seed 全等（不等=管线内部
错误 E-K2-EDITOR-DOMAIN）；页面域六件换装前后逐字节相等；recompose∘extract==id 幂等自证；
已迁移成品（V03R 在案＋编辑器域==当前资产）放行为幂等重跑输入。
"""
import argparse
import difflib
import hashlib
import json
import sys
import time
from pathlib import Path
import re
from html.parser import HTMLParser

ROOT=Path(__file__).resolve().parents[1]


def strip_extension_scripts(source):
    """Remove actual injected extension tags, never lookalikes inside user notes."""
    offsets=[0]
    for line in source.splitlines(keepends=True):offsets.append(offsets[-1]+len(line))
    ranges=[]
    class ExtensionParser(HTMLParser):
        start=None
        def source_offset(self):
            line,column=self.getpos();return offsets[line-1]+column
        def extension(self,tag,attrs):
            return tag=='script' and dict(attrs).get('src','').strip().lower().startswith(('chrome-extension://','moz-extension://','edge-extension://','safari-web-extension://'))
        def handle_starttag(self,tag,attrs):
            if self.extension(tag,attrs):self.start=self.source_offset()
        def handle_startendtag(self,tag,attrs):
            if self.extension(tag,attrs):ranges.append((self.source_offset(),self.source_offset()+len(self.get_starttag_text())))
        def handle_endtag(self,tag):
            if tag=='script' and self.start is not None:
                end=self.source_offset();match=re.match(r'</script\s*>',source[end:],re.I)
                if match:ranges.append((self.start,end+len(match[0])))
                self.start=None
    parser=ExtensionParser();parser.feed(source);parser.close()
    for start,end in reversed(ranges):source=source[:start]+source[end:]
    return source


def apply_current(source):
    """T01 当前装配路径：把当前受控种子装配为运行时（build.compose 唯一消费入口）。

    仅施加 T00 冻结单 §6 分类为「需保留」的 patch（行号=本文件旧口径）：
      P01,P04-P14,P17,P21,P22,P24,P25,P27-P30,P32-P39；装配层受控注入（口令/页面树/图标/profile）在 build.py。
    跳过「仅旧件」：P02,P03,P16,P18-P20,P23,P26,P31,P40；跳过「废弃」：P15（version 反向改写"3.7.0"）。
    当前 seed 上与 upgrade() 的唯一行为差异＝不再把 version: "2.0" 反向改写为 "3.7.0"。
    受控运行时块（FREE_EDITOR/FREE_STYLE）已存在的输入具名无损拒绝（重复块失败）；
    旧件完整迁移（K 集合再升级）必须走 upgrade()，属 T07。
    """
    if '/*FREE_EDITOR_START*/' in source or '/*FREE_STYLE_START*/' in source:
        raise ValueError('apply_current: controlled runtime block already present; only the current seed is accepted (legacy re-upgrade must use upgrade())')
    source=strip_extension_scripts(source)  # P01 剥离浏览器扩展 script 标签（真实 src 前缀）
    # P05 EXTENSION_CLONE_CLEAN：导出克隆清扩展脚本
    if '/*EXTENSION_CLONE_CLEAN*/' not in source:
        source=source.replace('var clone = document.documentElement.cloneNode(true);','var clone = document.documentElement.cloneNode(true);\n    /*EXTENSION_CLONE_CLEAN*/ clone.querySelectorAll(\'script[src^="chrome-extension://"],script[src^="moz-extension://"],script[src^="edge-extension://"],script[src^="safari-web-extension://"]\').forEach(function(n){n.remove();});',1)
    # P06 DIRECT_DELETE：删除时清布局记录
    if '/*DIRECT_DELETE*/' not in source:
        source=source.replace('      var s = el.closest(".screen");\n      el.remove();','      var s = el.closest(".screen");\n      /*DIRECT_DELETE*/ directForget(el);\n      el.remove();',1)
    # P07 DIRECT_DUPLICATE：复制清 layout-anchor（复制身份/布局记录）
    if '/*DIRECT_DUPLICATE*/' not in source:
        source=source.replace('      var c = el.cloneNode(true);\n      c.classList.remove', '      var c = el.cloneNode(true);\n      /*DIRECT_DUPLICATE*/ c.removeAttribute("data-layout-anchor");c.querySelectorAll("[data-layout-anchor]").forEach(function(n){n.removeAttribute("data-layout-anchor");});\n      c.classList.remove',1)
    # P08 HISTORY_SELECTION_CLEAN：撤销恢复清选择高亮
    if '/*HISTORY_SELECTION_CLEAN*/' not in source:
        source=source.replace('canvas.innerHTML=state.html;document.documentElement', 'canvas.innerHTML=state.html;/*HISTORY_SELECTION_CLEAN*/ canvas.querySelectorAll(".is-selected,.is-hover,.annotation-hover").forEach(function(n){n.classList.remove("is-selected","is-hover","annotation-hover");});document.documentElement',1)
    # P09 SINGLE_SELECTION：select 单选清理
    if '/*SINGLE_SELECTION*/' not in source:
        source=source.replace('  function select(el){\n    if (selected)', '  function select(el){\n    /*SINGLE_SELECTION*/ canvas.querySelectorAll(".is-selected").forEach(function(n){n.classList.remove("is-selected");});\n    if (selected)',1)
    # P10 DIRECT_STYLE_MEMORY：setStyle 同步 directRemember/清形状
    if '/*DIRECT_STYLE_MEMORY*/' not in source:
        source=source.replace('    else selected.style.setProperty(prop, val);\n    syncPanel();','    else selected.style.setProperty(prop, val);\n    /*DIRECT_STYLE_MEMORY*/ if(prop==="border-radius")selected.removeAttribute("data-editor-shape");if(selected.hasAttribute("data-layout-anchor"))directRemember(selected);\n    syncPanel();',1)
    # P11 DIRECT_INSERT_ID：插入组件补 eid
    if '/*DIRECT_INSERT_ID*/' not in source:
        source=source.replace('    var node = tmp.firstElementChild;\n    if (!node) return;','    var node = tmp.firstElementChild;\n    if (!node) return;\n    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");',1)
    # P12 fNote 改多行 textarea
    source=re.sub(r'<input\b(?=[^>]*\bid=[\"\']fNote[\"\'])[^>]*>', '<textarea id=\"fNote\" rows=\"4\" placeholder=\"当前功能或流程的自由说明，可任意换行修改\"></textarea>',source,count=1)
    # P13 LOCAL_SESSION_CLEAN：导出清会话块（凭据不入分发件）
    if '/*LOCAL_SESSION_CLEAN*/' not in source:
        source=source.replace('var clone = document.documentElement.cloneNode(true);','var clone = document.documentElement.cloneNode(true);\n    /*LOCAL_SESSION_CLEAN*/ clone.querySelectorAll("#prototype-local-session").forEach(function(el){el.remove();});',1)
    # P14 GATE_BUTTON_RESET：导出复位 gate 确认按钮
    if '/*GATE_BUTTON_RESET*/' not in source:
        source=source.replace('var cg = clone.querySelector("#editorGate");','/*GATE_BUTTON_RESET*/ var gb=clone.querySelector("#gateConfirm");if(gb)gb.removeAttribute("disabled");\n    var cg = clone.querySelector("#editorGate");',1)
    # P15（废弃，跳过）：不施加 version 反向改写"3.7.0"；产物版本声明由当前装配自带
    # P16/P18/P19/P20（仅旧件，跳过）：旧口令文案/旧保存路由/clone 追加清理均不在当前 seed
    # P17 FIRST_PASSWORD_SOURCE：首次口令保存路由
    source=source.replace('/*FIRST_PASSWORD_EXPORT*/ if(fresh)saveNewHTML();','/*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();')
    if '/*FIRST_PASSWORD_SOURCE*/' not in source:
        source=source.replace("var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');","var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');\n        /*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();",1)
    # P21 buildTabs 重建后保留当前页
    source=source.replace('if (first) setActiveTab(first.getAttribute("data-screen"));','if (first) setActiveTab(curId && screenEl(curId) ? curId : first.getAttribute("data-screen"));',1)
    # P22 移页后滚回可见
    source=source.replace('canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();scheduleSave();','canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();',1)
    source=source.replace('canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();scheduleSave();','canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();',1)
    # P23（仅旧件，跳过）：button('上移页面') 目标串不在当前 seed
    # P24 导出清理追加 .annotation-hover（V05-① 类名空间化：选择器随当前 seed 同步 ed- 前缀）
    source=source.replace('clone.querySelectorAll(".ed-is-selected,.ed-is-hover")','clone.querySelectorAll(".ed-is-selected,.ed-is-hover,.annotation-hover")',1).replace('n.classList.remove("ed-is-selected", "ed-is-hover");','n.classList.remove("ed-is-selected", "ed-is-hover", "annotation-hover");',1)
    # P25 KEEP_VISIBLE_CURRENT＋选中防跟随
    if '/*KEEP_VISIBLE_CURRENT*/' not in source:
        source=source.replace('    var on = null, mid = canvas.getBoundingClientRect().left + 120;',
            '    /*KEEP_VISIBLE_CURRENT*/ var focused=screenEl(curId),view=canvas.getBoundingClientRect();if(focused){var fr=focused.getBoundingClientRect(),visible=Math.max(0,Math.min(fr.right,view.right)-Math.max(fr.left,view.left));if(fr.width&&visible/fr.width>=0.55)return;}\n    var on = null, mid = canvas.getBoundingClientRect().left + 120;',1)
    source=source.replace('if(focused){var fr=focused.getBoundingClientRect()', 'if(focused){if(selected&&selected.isConnected&&selected.closest(".screen")===focused)return;var fr=focused.getBoundingClientRect()',1)
    # P26（仅旧件，跳过）：EXPLICIT_PAGE 目标串为分行写法不命中
    # P27 自动跟随切页时清选中
    source=source.replace('      if (id && id !== curId){\n        curId = id;', '      if (id && id !== curId){\n        if(selected&&selected.closest(".screen")!==on)select(null);\n        curId = id;',1)
    # P03（仅旧件，跳过）：s.scrollIntoView 目标串不在当前 seed
    # P04 el/node/sec smooth→instant（各 1 次；2832 等不在覆盖串＝保留平滑，冻结单 §11.2）
    source=source.replace('el.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });','el.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });',1)
    source=source.replace('node.scrollIntoView({ behavior: "smooth", block: "center" });','node.scrollIntoView({ behavior: "instant", block: "center" });',1)
    source=source.replace('sec.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });','sec.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });',1)
    # P28 预览 toast 按 workspaceInteracted 抑制
    source=source.replace('setTimeout(function(){ toast("预览模式：点击卡片', 'setTimeout(function(){ if(workspaceInteracted)return; toast("预览模式：点击卡片',1)
    # P29 ZOOM_FOCUS：缩放后选中保持可见
    if '/*ZOOM_FOCUS*/' not in source:
        source=source.replace('    zoom = Math.min(1.5, Math.max(0.4, Math.round(z * 10) / 10));\n    applyZoom();',
            '    zoom = Math.min(1.5, Math.max(0.4, Math.round(z * 10) / 10));\n    applyZoom();\n    /*ZOOM_FOCUS*/ if(edit&&selected&&selected.isConnected){selected.scrollIntoView({behavior:"instant",block:"nearest",inline:"nearest"});freeUpdate();}',1)
    # P30 资源装配：free/direct/local-save/media/chooser 的 js+css（受控注入能力本体）
    import base64
    media=(ROOT/'assets/media-components.js').read_text(encoding='utf-8').replace('__DEMO_VIDEO_DATA__','data:video/webm;base64,'+base64.b64encode((ROOT/'assets/demo-media.webm').read_bytes()).decode('ascii'))
    import json
    presets=json.loads((ROOT/'assets/style-presets.json').read_text(encoding='utf-8'))
    chooser=(ROOT/'assets/style-chooser.js').read_text(encoding='utf-8').replace('__STYLE_PRESETS__',json.dumps(presets,ensure_ascii=False).replace('<','\\u003c'))
    js=(ROOT/'assets/free-editor.js').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/direct-manipulation.js').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/local-save-client.js').read_text(encoding='utf-8')+'\n'+media+'\n'+chooser
    css=(ROOT/'assets/free-editor.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/media-components.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/style-chooser.css').read_text(encoding='utf-8')
    js_block='/*FREE_EDITOR_START*/\n'+js+'\n/*FREE_EDITOR_END*/'
    css_block='/*FREE_STYLE_START*/\n'+css+'\n/*FREE_STYLE_END*/'
    # P31（仅旧件，跳过）：FREE 块成对替换再升级入口＝K 迁移登记要件，apply_current 不触发
    # P32 buildExport 守卫＝未知主体无损拒绝
    if '  function buildExport(stamp){' not in source:
        raise ValueError('Not a supported V2 editable prototype; source left unchanged')
    # P33 CSS 块注入（</style> 前）/JS 块注入（finishEditorGate 前）＝当前装配路径
    source=source.replace('</style>',css_block+'\n</style>',1)
    source=source.replace('  finishEditorGate();',js_block+'\n  finishEditorGate();\n  initFreeEditor();',1)
    # P34 首升挂钩（行为保留）：clone 清理/dirty 置位/freeUpdate 挂钩
    source=source.replace('    var clone = document.documentElement.cloneNode(true);','    var clone = document.documentElement.cloneNode(true);\n    clone.querySelectorAll(".free-editor-ui,.workspace-runtime-ui").forEach(function(el){el.remove();});',1)
    source=source.replace('    if (dirty) return;\n    dirty = true;','    dirty = true;',1)
    source=source.replace('if (!el || !el.classList){ hideInspector(); return; }','if (!el || !el.classList){ hideInspector(); freeUpdate(); return; }',1)
    source=source.replace('    syncOnPanel();\n  }','    syncOnPanel();\n    freeUpdate();\n  }',1)
    source=source.replace('    canvas.style.gap = (26 * zoom) + "px";','    canvas.style.gap = (26 * zoom) + "px";\n    freeUpdate();',1)
    source=source.replace('    edit = !preview;','    edit = !preview;\n    setTimeout(freeUpdate,0);',1)
    # P35 空页占位标记
    source=source.replace('<div class="empty" data-block="empty" data-eid="et-', '<div class="empty" data-editor-placeholder="1" data-block="empty" data-eid="et-',1)
    # P36 插入时清占位＋失效选中清理
    marker='    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");\n    if (selected && selected.parentElement && scope.contains(selected)) {'
    replacement='''    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");
    var insertScreen = activeScreen();
    if(insertScreen)insertScreen.querySelectorAll('[data-editor-placeholder],[data-block="empty"][data-eid^="et-"]').forEach(function(el){el.remove();});
    if(selected&&!selected.isConnected)selected=null;
    if (selected && selected.parentElement && scope.contains(selected)) {'''
    if marker not in source:raise ValueError('Unsupported insert function; source left unchanged')
    source=source.replace(marker,replacement,1)
    # P37 插入 free 落点 freePlace
    source=source.replace('    select(node);\n    node.scrollIntoView','    if(insertScreen&&insertScreen.getAttribute("data-layout")==="free")freePlace(node,insertScreen);\n    select(node);\n    node.scrollIntoView',1)
    # P38 新页默认 free 布局＋freeConvert
    source=source.replace('    var sec = tmp.firstElementChild;\n    if (!sec || sec.tagName !== "SECTION") return;','    var sec = tmp.firstElementChild;\n    if (!sec || sec.tagName !== "SECTION") return;\n    sec.setAttribute("data-layout","free");',1)
    source=source.replace('    else canvas.appendChild(sec);\n    buildTabs();','    else canvas.appendChild(sec);\n    freeConvert(sec);\n    buildTabs();',1)
    # P39 保存路由：Ctrl+S/保存主按钮→saveSourceHTML；API 对象→saveSourceHTML/saveSourceFile
    source=source.replace('e.preventDefault(); saveFile(); return;','e.preventDefault(); saveSourceHTML(); return;',1)
    source=source.replace('    saveFile: saveFile,','    saveFile: saveSourceHTML,\n    saveSourceFile: saveSourceHTML,',1).replace('    saveHTML: saveFile,','    saveHTML: saveSourceHTML,',1)
    # P40（仅旧件，跳过）：'覆盖源文件（高级）'按钮目标串不在当前 seed
    return source


def upgrade(source):
    source=strip_extension_scripts(source)
    # textarea.type is read-only; only native input elements accept a type assignment.
    source=source.replace("}else input.type=f.type||'text';input.value=", "}else if(input.tagName==='INPUT')input.type=f.type||'text';input.value=")
    # Long animated canvas jumps emit intermediate scroll positions and can steal the chosen page focus.
    source=source.replace('s.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });', 's.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });')
    if '/*EXTENSION_CLONE_CLEAN*/' not in source:
        source=source.replace('var clone = document.documentElement.cloneNode(true);','var clone = document.documentElement.cloneNode(true);\n    /*EXTENSION_CLONE_CLEAN*/ clone.querySelectorAll(\'script[src^="chrome-extension://"],script[src^="moz-extension://"],script[src^="edge-extension://"],script[src^="safari-web-extension://"]\').forEach(function(n){n.remove();});',1)
    if '/*DIRECT_DELETE*/' not in source:
        source=source.replace('      var s = el.closest(".screen");\n      el.remove();','      var s = el.closest(".screen");\n      /*DIRECT_DELETE*/ directForget(el);\n      el.remove();',1)
    if '/*DIRECT_DUPLICATE*/' not in source:
        source=source.replace('      var c = el.cloneNode(true);\n      c.classList.remove', '      var c = el.cloneNode(true);\n      /*DIRECT_DUPLICATE*/ c.removeAttribute("data-layout-anchor");c.querySelectorAll("[data-layout-anchor]").forEach(function(n){n.removeAttribute("data-layout-anchor");});\n      c.classList.remove',1)
    if '/*HISTORY_SELECTION_CLEAN*/' not in source:
        source=source.replace('canvas.innerHTML=state.html;document.documentElement', 'canvas.innerHTML=state.html;/*HISTORY_SELECTION_CLEAN*/ canvas.querySelectorAll(".is-selected,.is-hover,.annotation-hover").forEach(function(n){n.classList.remove("is-selected","is-hover","annotation-hover");});document.documentElement',1)
    if '/*SINGLE_SELECTION*/' not in source:
        source=source.replace('  function select(el){\n    if (selected)', '  function select(el){\n    /*SINGLE_SELECTION*/ canvas.querySelectorAll(".is-selected").forEach(function(n){n.classList.remove("is-selected");});\n    if (selected)',1)
    if '/*DIRECT_STYLE_MEMORY*/' not in source:
        source=source.replace('    else selected.style.setProperty(prop, val);\n    syncPanel();','    else selected.style.setProperty(prop, val);\n    /*DIRECT_STYLE_MEMORY*/ if(prop==="border-radius")selected.removeAttribute("data-editor-shape");if(selected.hasAttribute("data-layout-anchor"))directRemember(selected);\n    syncPanel();',1)
    if '/*DIRECT_INSERT_ID*/' not in source:
        source=source.replace('    var node = tmp.firstElementChild;\n    if (!node) return;','    var node = tmp.firstElementChild;\n    if (!node) return;\n    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");',1)
    source=re.sub(r'<input\b(?=[^>]*\bid=[\"\']fNote[\"\'])[^>]*>', '<textarea id=\"fNote\" rows=\"4\" placeholder=\"当前功能或流程的自由说明，可任意换行修改\"></textarea>',source,count=1)
    if '/*LOCAL_SESSION_CLEAN*/' not in source:
        source=source.replace('var clone = document.documentElement.cloneNode(true);','var clone = document.documentElement.cloneNode(true);\n    /*LOCAL_SESSION_CLEAN*/ clone.querySelectorAll("#prototype-local-session").forEach(function(el){el.remove();});',1)
    if '/*GATE_BUTTON_RESET*/' not in source:
        source=source.replace('var cg = clone.querySelector("#editorGate");','/*GATE_BUTTON_RESET*/ var gb=clone.querySelector("#gateConfirm");if(gb)gb.removeAttribute("disabled");\n    var cg = clone.querySelector("#editorGate");',1)
    for v in ['3.4.1','3.5.0','3.6.0','3.7.0']:
        source=source.replace('version: "'+v+'"','version: "3.7.0"',1)
    for old in ['设置后保存此 HTML，再分发已配置版本。没有账号、角色或服务器信息。','设置后会下载已设口令的完整HTML；请转发该文件。再次打开后，只有本次设定的原口令才能编辑。']:
        source=source.replace(old,'设置后将口令写入当前源HTML，不自动下载。首次请选择当前HTML并授权；以后打开或转发该文件，均使用本次原口令。')
    # v6.2：口令门确认按钮文案以源码为准（"设置并进入编辑"），不再反向替换
    source=source.replace('/*FIRST_PASSWORD_EXPORT*/ if(fresh)saveNewHTML();','/*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();')
    if '/*FIRST_PASSWORD_SOURCE*/' not in source:
        source=source.replace("var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');","var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');\n        /*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();",1)
    source=source.replace('e.preventDefault(); saveNewHTML(); return;','e.preventDefault(); saveSourceHTML(); return;',1)
    source=source.replace('saveFile: saveNewHTML,','saveFile: saveSourceHTML,',1).replace('saveHTML: saveNewHTML,','saveHTML: saveSourceHTML,',1)
    source=source.replace('saveSourceFile: saveFile,','saveSourceFile: saveSourceHTML,',1)
    source=source.replace("d.close();saveFile();","d.close();saveBrowserSourceHTML();").replace("d.close();saveSourceHTML();","d.close();saveBrowserSourceHTML();")
    source=source.replace('version: "3.3"','version: "3.7.0"',1).replace('version: "3.4"','version: "3.7.0"',1)
    source=source.replace('version: "3.0"','version: "3.7.0"',1).replace('version: "3.1"','version: "3.7.0"',1).replace('version: "3.2"','version: "3.7.0"',1)
    source=source.replace('clone.querySelectorAll(".free-editor-ui")','clone.querySelectorAll(".free-editor-ui,.workspace-runtime-ui")')
    # Rebuilding labels after rename/reorder must retain the actual current page.
    source=source.replace('if (first) setActiveTab(first.getAttribute("data-screen"));','if (first) setActiveTab(curId && screenEl(curId) ? curId : first.getAttribute("data-screen"));',1)
    source=source.replace('canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();scheduleSave();','canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();',1)
    source=source.replace('canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();scheduleSave();','canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();',1)
    # Notes JSON is a canvas child too: reorder screens, never metadata siblings.
    source=source.replace("button('上移页面',function(){if(sc.previousElementSibling){snapshot();canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();sc.scrollIntoView({block:\"nearest\",inline:\"start\"});scheduleSave();}d.close();});", "button('上移页面',function(){var prev=sc.previousElementSibling;while(prev&&!prev.matches('.screen'))prev=prev.previousElementSibling;if(prev){snapshot();canvas.insertBefore(sc,prev);buildTabs();sc.scrollIntoView({block:\"nearest\",inline:\"start\"});scheduleSave();}d.close();});",1)
    source=source.replace("button('下移页面',function(){if(sc.nextElementSibling){snapshot();canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();sc.scrollIntoView({block:\"nearest\",inline:\"start\"});scheduleSave();}d.close();});", "button('下移页面',function(){var next=sc.nextElementSibling;while(next&&!next.matches('.screen'))next=next.nextElementSibling;if(next){snapshot();canvas.insertBefore(next,sc);buildTabs();sc.scrollIntoView({block:\"nearest\",inline:\"start\"});scheduleSave();}d.close();});",1)
    source=source.replace('clone.querySelectorAll(".is-selected,.is-hover")','clone.querySelectorAll(".is-selected,.is-hover,.annotation-hover")',1).replace('n.classList.remove("is-selected", "is-hover");','n.classList.remove("is-selected", "is-hover", "annotation-hover");',1)
    # A small end-page cannot always align left beside a wide admin screen. Keep explicit focus while visible.
    if '/*KEEP_VISIBLE_CURRENT*/' not in source:
        source=source.replace('    var on = null, mid = canvas.getBoundingClientRect().left + 120;',
            '    /*KEEP_VISIBLE_CURRENT*/ var focused=screenEl(curId),view=canvas.getBoundingClientRect();if(focused){var fr=focused.getBoundingClientRect(),visible=Math.max(0,Math.min(fr.right,view.right)-Math.max(fr.left,view.left));if(fr.width&&visible/fr.width>=0.55)return;}\n    var on = null, mid = canvas.getBoundingClientRect().left + 120;',1)
    source=source.replace('if(focused){var fr=focused.getBoundingClientRect()', 'if(focused){if(selected&&selected.isConnected&&selected.closest(".screen")===focused)return;var fr=focused.getBoundingClientRect()',1)
    if '/*EXPLICIT_PAGE*/' not in source:
        source=source.replace('        curId = id; updatePrevBar();','        /*EXPLICIT_PAGE*/ if(selected&&selected.closest(".screen")!==s)select(null);\n        curId = id; updatePrevBar();',1)
    source=source.replace('      if (id && id !== curId){\n        curId = id;', '      if (id && id !== curId){\n        if(selected&&selected.closest(".screen")!==on)select(null);\n        curId = id;',1)
    # A smooth scroll emits intermediate page changes; quick preview then opened the wrong page.
    source=source.replace('s.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });','s.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });',1)
    source=source.replace('el.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });','el.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });',1)
    source=source.replace('node.scrollIntoView({ behavior: "smooth", block: "center" });','node.scrollIntoView({ behavior: "instant", block: "center" });',1)
    source=source.replace('sec.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });','sec.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });',1)
    source=source.replace('setTimeout(function(){ toast("预览模式：点击卡片', 'setTimeout(function(){ if(workspaceInteracted)return; toast("预览模式：点击卡片',1)
    if '/*ZOOM_FOCUS*/' not in source:
        source=source.replace('    zoom = Math.min(1.5, Math.max(0.4, Math.round(z * 10) / 10));\n    applyZoom();',
            '    zoom = Math.min(1.5, Math.max(0.4, Math.round(z * 10) / 10));\n    applyZoom();\n    /*ZOOM_FOCUS*/ if(edit&&selected&&selected.isConnected){selected.scrollIntoView({behavior:"instant",block:"nearest",inline:"nearest"});freeUpdate();}',1)
    import base64
    media=(ROOT/'assets/media-components.js').read_text(encoding='utf-8').replace('__DEMO_VIDEO_DATA__','data:video/webm;base64,'+base64.b64encode((ROOT/'assets/demo-media.webm').read_bytes()).decode('ascii'))
    import json
    presets=json.loads((ROOT/'assets/style-presets.json').read_text(encoding='utf-8'))
    chooser=(ROOT/'assets/style-chooser.js').read_text(encoding='utf-8').replace('__STYLE_PRESETS__',json.dumps(presets,ensure_ascii=False).replace('<','\\u003c'))
    js=(ROOT/'assets/free-editor.js').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/direct-manipulation.js').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/local-save-client.js').read_text(encoding='utf-8')+'\n'+media+'\n'+chooser
    css=(ROOT/'assets/free-editor.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/media-components.css').read_text(encoding='utf-8')+'\n'+(ROOT/'assets/style-chooser.css').read_text(encoding='utf-8')
    js_block='/*FREE_EDITOR_START*/\n'+js+'\n/*FREE_EDITOR_END*/'
    css_block='/*FREE_STYLE_START*/\n'+css+'\n/*FREE_STYLE_END*/'
    if '/*FREE_EDITOR_START*/' in source:
        source=re.sub(r'/\*FREE_EDITOR_START\*/[\s\S]*?/\*FREE_EDITOR_END\*/',lambda _:js_block,source,count=1)
        return re.sub(r'/\*FREE_STYLE_START\*/[\s\S]*?/\*FREE_STYLE_END\*/',lambda _:css_block,source,count=1)
    if '  function buildExport(stamp){' not in source:
        raise ValueError('Not a supported V2 editable prototype; source left unchanged')
    source=source.replace('</style>',css_block+'\n</style>',1)
    source=source.replace('  finishEditorGate();',js_block+'\n  finishEditorGate();\n  initFreeEditor();',1)
    source=source.replace('    var clone = document.documentElement.cloneNode(true);','    var clone = document.documentElement.cloneNode(true);\n    clone.querySelectorAll(".free-editor-ui,.workspace-runtime-ui").forEach(function(el){el.remove();});',1)
    source=source.replace('    if (dirty) return;\n    dirty = true;','    dirty = true;',1)
    source=source.replace('if (!el || !el.classList){ hideInspector(); return; }','if (!el || !el.classList){ hideInspector(); freeUpdate(); return; }',1)
    source=source.replace('    syncOnPanel();\n  }','    syncOnPanel();\n    freeUpdate();\n  }',1)
    source=source.replace('    canvas.style.gap = (26 * zoom) + "px";','    canvas.style.gap = (26 * zoom) + "px";\n    freeUpdate();',1)
    source=source.replace('    edit = !preview;','    edit = !preview;\n    setTimeout(freeUpdate,0);',1)
    # Empty-page helpers must not become content or displace inserted components.
    source=source.replace('<div class="empty" data-block="empty" data-eid="et-', '<div class="empty" data-editor-placeholder="1" data-block="empty" data-eid="et-',1)
    marker='    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");\n    if (selected && selected.parentElement && scope.contains(selected)) {'
    replacement='''    /*DIRECT_INSERT_ID*/ if(!node.hasAttribute("data-eid"))node.setAttribute("data-eid",id+"-group");
    var insertScreen = activeScreen();
    if(insertScreen)insertScreen.querySelectorAll('[data-editor-placeholder],[data-block="empty"][data-eid^="et-"]').forEach(function(el){el.remove();});
    if(selected&&!selected.isConnected)selected=null;
    if (selected && selected.parentElement && scope.contains(selected)) {'''
    if marker not in source:raise ValueError('Unsupported insert function; source left unchanged')
    source=source.replace(marker,replacement,1)
    source=source.replace('    select(node);\n    node.scrollIntoView','    if(insertScreen&&insertScreen.getAttribute("data-layout")==="free")freePlace(node,insertScreen);\n    select(node);\n    node.scrollIntoView',1)
    source=source.replace('    var sec = tmp.firstElementChild;\n    if (!sec || sec.tagName !== "SECTION") return;','    var sec = tmp.firstElementChild;\n    if (!sec || sec.tagName !== "SECTION") return;\n    sec.setAttribute("data-layout","free");',1)
    source=source.replace('    else canvas.appendChild(sec);\n    buildTabs();','    else canvas.appendChild(sec);\n    freeConvert(sec);\n    buildTabs();',1)
    # v6.2：保存主按钮=写回源文件（saveFile），不再替换为 saveNewHTML（另存新文件走保存▾）
    source=source.replace('e.preventDefault(); saveFile(); return;','e.preventDefault(); saveSourceHTML(); return;',1)
    source=source.replace('    saveFile: saveFile,','    saveFile: saveSourceHTML,\n    saveSourceFile: saveSourceHTML,',1).replace('    saveHTML: saveFile,','    saveHTML: saveSourceHTML,',1)
    source=source.replace('    button(\'重新绑定源文件\'', '    button(\'覆盖源文件（高级）\',function(){d.close();saveBrowserSourceHTML();});\n    button(\'重新绑定源文件\'',1)
    source=source.replace('version: "2.0"','version: "3.7.0"',1).replace('version: "3.4.1"','version: "3.7.0"',1)
    return source


# T01：legacy 别名。upgrade() 即旧件全量迁移路径，行为逐字保持不变（含 P15 version 反向改写、
# P31 FREE 块成对替换、P40 等仅旧件 patch）——供 T07 K 集合迁移调用；本轮不改其逻辑。
upgrade_legacy = upgrade


# ==================== V04 K2 受控迁移（migrate-k2 子命令） ====================
# REFIT v2（编辑器脚本域全套装换装）：旧管线（upgrade_legacy 局部换 FREE JS/CSS 两块）残留旧骨架，
# 用户实测实锤两缺陷：①新 FREE 块 T04 applyStyleConfig 调种子挂钩 applyStyleConfigOn——旧骨架无此函数
# →风格向导「应用」ReferenceError 卡死；②旧骨架模式/视口结构与当前块并存→双视窗。
# 新流程：K2 严格预检（无损拒绝；已迁移成品放行幂等重跑）→ 页面域六件提取（header/title/doc_id/
# inject/pages/tail，锚点不符具名拒绝）→ apply_current(当前 editor-seed.html) 全量重装配 →
# 编辑器域四跨度（主样式体/主脚本体/FREE JS/FREE CSS）SHA 全集校验（≠当前资产=管线内部错误）→
# 「需保留」30 项审计（构造性全 verified）→ 受控块恰 1 → 页面域六件逐字节回读比对 → 幂等自证。
# 退出码：0=迁移成功；1=具名拒绝（E-K2-*，零产出）；2=参数/IO/环境错误。行号/行尾口径全部 \n。
K2_FREE_MARKERS=['/*FREE_EDITOR_START*/','/*FREE_EDITOR_END*/','/*FREE_STYLE_START*/','/*FREE_STYLE_END*/']
K2_V03R_MARKERS=['V03R-fit-guard','V03R-panel-fix','V03R-lang-subtree']
K2_GUARD='  function buildExport(stamp){'
K2_FENCE='prototype-contract'
K2_CANVAS_ANCHOR='<main class="canvas" id="canvas">'
K2_CONTROLLED_ONCE=['id="project-design-tokens"','id="prototype-design-system"','id="prototype-config"','id="prototype-start-doc"','id="prototype-page-tree"','id="prototype-icon-library"']
K2_OLD_BACKUP_STMT='clone.querySelectorAll("[data-free-backup]").forEach(function(n){ n.removeAttribute("data-free-backup"); });'
K2_FNOTE_RE=re.compile(r'<input\b(?=[^>]*\bid=[\"\']fNote[\"\'])[^>]*>')
K2_RE_VERSION_ANY=re.compile(r'version: "(?:3\.[0-9](?:\.[0-9]+)?)"')
K2_FREE_PAIRS=[('/*FREE_EDITOR_START*/','/*FREE_EDITOR_END*/'),('/*FREE_STYLE_START*/','/*FREE_STYLE_END*/')]
# upgrade_legacy 全量行为在块外区域的受认可变换（冻结单 §6 分类：需保留/仅旧件/废弃 的 replace 目标系）
# REFIT 后 migrate-k2 不再走 upgrade_legacy 局部换装（骨架整体重建，子集变换被当前骨架内含）；
# 本表保留为冻结 §6 对照与 work-k\migrate_k.py 历史口径参照，勿删。
K2_SANCTIONED_RESIDUAL=[
    ("}else input.type=f.type||'text';input.value=", "}else if(input.tagName==='INPUT')input.type=f.type||'text';input.value="),
    ('s.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });', 's.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });'),
    ('el.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });', 'el.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });'),
    ('node.scrollIntoView({ behavior: "smooth", block: "center" });', 'node.scrollIntoView({ behavior: "instant", block: "center" });'),
    ('sec.scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" });', 'sec.scrollIntoView({ behavior: "instant", inline: "start", block: "nearest" });'),
    ('e.preventDefault(); saveNewHTML(); return;', 'e.preventDefault(); saveSourceHTML(); return;'),
    ('e.preventDefault(); saveFile(); return;', 'e.preventDefault(); saveSourceHTML(); return;'),
    ('saveFile: saveNewHTML,', 'saveFile: saveSourceHTML,'),
    ('saveHTML: saveNewHTML,', 'saveHTML: saveSourceHTML,'),
    ('saveFile: saveFile,', '    saveFile: saveSourceHTML,\n    saveSourceFile: saveSourceHTML,'),
    ('saveHTML: saveFile,', '    saveHTML: saveSourceHTML,'),
    ('saveSourceFile: saveFile,', 'saveSourceFile: saveSourceHTML,'),
    ('d.close();saveFile();', 'd.close();saveBrowserSourceHTML();'),
    ('d.close();saveSourceHTML();', 'd.close();saveBrowserSourceHTML();'),
    ('clone.querySelectorAll(".free-editor-ui")', 'clone.querySelectorAll(".free-editor-ui,.workspace-runtime-ui")'),
    ('if (first) setActiveTab(first.getAttribute("data-screen"));', 'if (first) setActiveTab(curId && screenEl(curId) ? curId : first.getAttribute("data-screen"));'),
    ('canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();scheduleSave();', 'canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();'),
    ('canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();scheduleSave();', 'canvas.insertBefore(sc.nextElementSibling,sc);buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();'),
    ("button('上移页面',function(){if(sc.previousElementSibling){snapshot();canvas.insertBefore(sc,sc.previousElementSibling);", "button('上移页面',function(){var prev=sc.previousElementSibling;while(prev&&!prev.matches('.screen'))prev=prev.previousElementSibling;if(prev){snapshot();canvas.insertBefore(sc,prev);"),
    ("button('下移页面',function(){if(sc.nextElementSibling){snapshot();canvas.insertBefore(sc.nextElementSibling,sc);", "button('下移页面',function(){var next=sc.nextElementSibling;while(next&&!next.matches('.screen'))next=next.nextElementSibling;if(next){snapshot();canvas.insertBefore(next,sc);"),
    ('clone.querySelectorAll(".is-selected,.is-hover")', 'clone.querySelectorAll(".is-selected,.is-hover,.annotation-hover")'),
    ('n.classList.remove("is-selected", "is-hover");', 'n.classList.remove("is-selected", "is-hover", "annotation-hover");'),
    ('        curId = id; updatePrevBar();', '        /*EXPLICIT_PAGE*/ if(selected&&selected.closest(".screen")!==s)select(null);\n        curId = id; updatePrevBar();'),
    ('      if (id && id !== curId){\n        curId = id;', '      if (id && id !== curId){\n        if(selected&&selected.closest(".screen")!==on)select(null);\n        curId = id;'),
    ('setTimeout(function(){ toast("预览模式：点击卡片', 'setTimeout(function(){ if(workspaceInteracted)return; toast("预览模式：点击卡片'),
    ('/*FIRST_PASSWORD_EXPORT*/ if(fresh)saveNewHTML();', '/*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();'),
    ("var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');", "var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');\n        /*FIRST_PASSWORD_SOURCE*/ if(fresh)saveFirstPassword();"),
    ('设置后保存此 HTML，再分发已配置版本。没有账号、角色或服务器信息。', '设置后将口令写入当前源HTML，不自动下载。首次请选择当前HTML并授权；以后打开或转发该文件，均使用本次原口令。'),
    ('设置后会下载已设口令的完整HTML；请转发该文件。再次打开后，只有本次设定的原口令才能编辑。', '设置后将口令写入当前源HTML，不自动下载。首次请选择当前HTML并授权；以后打开或转发该文件，均使用本次原口令。'),
    ('<input id="fNote"', '<textarea id="fNote"'),
    ('version: "2.0"', 'version: "3.7.0"'),
]
# apply_current「需保留」装配审计表：(patch, done形态或marker, 原目标, 替换, 必需)
K2_RETAIN_AUDIT=[
    ('P05', '/*EXTENSION_CLONE_CLEAN*/', 'var clone = document.documentElement.cloneNode(true);', None, True),
    ('P06', '/*DIRECT_DELETE*/', '      var s = el.closest(".screen");\n      el.remove();', '      var s = el.closest(".screen");\n      /*DIRECT_DELETE*/ directForget(el);\n      el.remove();', True),
    ('P07', '/*DIRECT_DUPLICATE*/', '      var c = el.cloneNode(true);\n      c.classList.remove', None, True),
    # P08：旧锚 /*HISTORY_SELECTION_CLEAN*/ 已随当前 seed 改写退役（seed 自注：逻辑内化于快照前清理），
    # done 形态更新为现役后继语句（含 .is-drophost 的选择清理）
    ('P08', 'canvas.querySelectorAll(".ed-is-selected,.ed-is-hover,.annotation-hover,.ed-is-drophost")', None, None, True),
    ('P09', '/*SINGLE_SELECTION*/', '  function select(el){\n    if (selected)', None, True),
    ('P10', '/*DIRECT_STYLE_MEMORY*/', '    else selected.style.setProperty(prop, val);\n    syncPanel();', None, True),
    ('P11', '/*DIRECT_INSERT_ID*/', '    var node = tmp.firstElementChild;\n    if (!node) return;', None, True),
    ('P12', '<textarea id="fNote"', '<input id="fNote"', 'RE_SUB_FNOTE', True),
    ('P13', '/*LOCAL_SESSION_CLEAN*/', 'var clone = document.documentElement.cloneNode(true);', None, True),
    ('P14', '/*GATE_BUTTON_RESET*/', 'var cg = clone.querySelector("#editorGate");', None, True),
    ('P17', '/*FIRST_PASSWORD_SOURCE*/', "var cb=unlockCallback;unlockCallback=null;if(cb)cb();else setMode('edit');", None, True),
    ('P21', 'setActiveTab(curId && screenEl(curId) ? curId : first.getAttribute("data-screen"))', 'if (first) setActiveTab(first.getAttribute("data-screen"));', None, True),
    ('P22', 'buildTabs();sc.scrollIntoView({block:"nearest",inline:"start"});scheduleSave();', 'canvas.insertBefore(sc,sc.previousElementSibling);buildTabs();scheduleSave();', None, True),
    ('P24', 'clone.querySelectorAll(".ed-is-selected,.ed-is-hover,.annotation-hover")', 'clone.querySelectorAll(".is-selected,.is-hover")', None, True),
    ('P25', '/*KEEP_VISIBLE_CURRENT*/', '    var on = null, mid = canvas.getBoundingClientRect().left + 120;', None, True),
    ('P27', 'if(selected&&selected.closest(".screen")!==on)select(null);', '      if (id && id !== curId){\n        curId = id;', None, True),
    ('P28', 'if(workspaceInteracted)return; toast("预览模式：点击卡片', 'setTimeout(function(){ toast("预览模式：点击卡片', None, True),
    ('P29', '/*ZOOM_FOCUS*/', '    zoom = Math.min(1.5, Math.max(0.4, Math.round(z * 10) / 10));\n    applyZoom();', None, True),
    ('P30', '/*FREE_EDITOR_START*/', None, None, True),
    ('P32', K2_GUARD, None, None, True),
    ('P33', '/*FREE_STYLE_START*/', '</style>', None, True),
    ('P34-dirty', '    dirty = true;', '    if (dirty) return;\n    dirty = true;', None, True),
    ('P34-hideins', 'hideInspector(); freeUpdate();', 'if (!el || !el.classList){ hideInspector(); return; }', None, True),
    ('P34-editmode', '    edit = !preview;\n    setTimeout(freeUpdate,0);', '    edit = !preview;', None, True),
    ('P35', 'data-editor-placeholder="1" data-block="empty"', '<div class="empty" data-block="empty" data-eid="et-', None, True),
    ('P36', 'var insertScreen = activeScreen();', None, None, True),
    ('P37', 'if(insertScreen&&insertScreen.getAttribute("data-layout")==="free")freePlace(node,insertScreen);', None, None, True),
    ('P38', 'sec.setAttribute("data-layout","free");', None, None, True),
    ('P39-ctrlS', 'e.preventDefault(); saveSourceHTML(); return;', None, None, True),
    ('P39-api', '    saveFile: saveSourceHTML,', None, None, True),
]

class K2Rejected(Exception):
    """migrate-k2 具名无损拒绝：携带 E-K2-* 错误码与可选 detail；CLI 层打印 JSON 并 exit 1（零产出）。"""
    def __init__(self,code,message,detail=None):
        super().__init__('%s: %s'%(code,message));self.code=code;self.message=message;self.detail=detail

def k2_free_spans(text):
    spans=[]
    for a,b in K2_FREE_PAIRS:
        i=text.find(a);j=text.find(b)
        if i<0 or j<0 or j<i:spans.append(None)
        else:spans.append((i,j+len(b)))
    good=[s for s in spans if s]
    good.sort()  # 文件位置序（style 块在前、editor 块在后）
    if len(good)!=2:return [None,None]
    return good

def k2_strip_blocks(text):
    spans=k2_free_spans(text)
    if any(s is None for s in spans):return None
    out,pos=[],0
    for s in spans:
        out.append(text[pos:s[0]]);pos=s[1]
    out.append(text[pos:])
    return ''.join(out)

def k2_canonical(text):
    """页面域统计（剔除 FREE 双块后）：屏数/属性计数/标注/free 备份痕迹。"""
    resid=k2_strip_blocks(text)
    screens=re.findall(r'<section class="screen" data-screen="([^"]+)"',text)
    resid_screens=re.findall(r'<section class="screen" data-screen="([^"]+)"',resid or text)
    return {'screens':len(screens),'screen_ids':screens,'resid_screens':len(resid_screens),
        'data_eid':(resid or text).count('data-eid='),'data_on':(resid or text).count('data-on='),
        'data_note':(resid or text).count('data-note='),'data_block':(resid or text).count('data-block='),
        'data_layout_free':(resid or text).count('data-layout="free"'),
        'free_backup_resid':(resid or text).count('data-free-backup'),'free_backup_full':text.count('data-free-backup'),
        'annotations_block':text.count('id="prototype-annotations"'),'layouts_block':text.count('id="prototype-layouts"')}

def k2_seed_current():
    """当前资产编辑器域基准：apply_current(assets/editor-seed.html)，\\n 口径，进程内缓存。"""
    if 'cur' not in _K2_SEED_CACHE:
        raw=(ROOT/'assets/editor-seed.html').read_text(encoding='utf-8')
        _K2_SEED_CACHE['cur']=re.sub(r'\r\n|\r','\n',apply_current(raw))
    return _K2_SEED_CACHE['cur']

_K2_SEED_CACHE={}

def k2_editor_spans(text):
    """编辑器域四跨度：主样式体（首个 <style> 内，含 FREE CSS 块）/主脚本体（含守卫与 FREE JS 块）/
    FREE JS 块/FREE CSS 块。锚点缺失→K2Rejected(E-K2-EDITOR-DOMAIN)。"""
    def bad(msg):raise K2Rejected('E-K2-EDITOR-DOMAIN',msg)
    so=text.find('<style>')
    if so<0:bad('主 <style> 未定位（管线内部错误）')
    sc=text.find('</style>',so)
    if sc<0:bad('主 </style> 未定位（管线内部错误）')
    guard=text.find(K2_GUARD)
    if guard<0:bad('buildExport 守卫未定位（管线内部错误）')
    so2=text.rfind('<script>',0,guard)
    sc2=text.find('</script>',guard)
    if so2<0 or sc2<0:bad('主 <script> 未定位（管线内部错误）')
    i=text.find('/*FREE_EDITOR_START*/');j=text.find('/*FREE_EDITOR_END*/')
    if i<0 or j<i:bad('FREE JS 块未定位（管线内部错误）')
    free_js=text[i:j+len('/*FREE_EDITOR_END*/')]
    i=text.find('/*FREE_STYLE_START*/');j=text.find('/*FREE_STYLE_END*/')
    if i<0 or j<i:bad('FREE CSS 块未定位（管线内部错误）')
    free_css=text[i:j+len('/*FREE_STYLE_END*/')]
    return {'style_body':text[so+7:sc],'script_body':text[so2+8:sc2],'free_js':free_js,'free_css':free_css}

def k2_editor_shas(spans):
    return {k:hashlib.sha256(v.encode('utf-8')).hexdigest()[:16] for k,v in spans.items()}

def k2_preflight(text):
    """K2 严格预检（无损拒绝）：守卫恰1→FREE 对恰1→旧世代家族拒绝（K1/K0；已迁移成品放行幂等重跑）
    →口令依据恰1→受控块恰1→</head> 恰1。"""
    if text.count(K2_GUARD)!=1:
        raise K2Rejected('E-K2-UNKNOWN-SUBJECT','buildExport 守卫出现 %d 次（恰1才算受支持的 V2 可编辑原型；0=陌生主体/截断件）'%text.count(K2_GUARD))
    counts={m:text.count(m) for m in K2_FREE_MARKERS}
    if any(text.count(m)!=1 for m in K2_FREE_MARKERS):
        raise K2Rejected('E-K2-FREE-PAIR','FREE 受控块非成对各恰1：%s'%json.dumps(counts))
    v03r={m:text.count(m) for m in K2_V03R_MARKERS}
    already_current=False
    if any(v>0 for v in v03r.values()):
        # V03R 在案＝K1 族标记。例外：编辑器域四跨度与当前资产逐字节全等＝本管线已迁移成品
        # →放行为幂等重跑输入（A10）；否则维持具名拒绝（K1 件不适用 K2 路径）。
        try:
            got=k2_editor_spans(text);ref=k2_editor_spans(k2_seed_current())
            already_current=all(got[k]==ref[k] for k in ref)
        except K2Rejected:
            already_current=False
        if not already_current:
            raise K2Rejected('E-K2-NOT-LEGACY','V03R 三标记在案（当前基线家族=K1，不适用 K2 迁移路径；编辑器域≠当前资产亦非已迁移成品）：%s'%json.dumps(v03r))
    if text.count(K2_FENCE)>0:
        raise K2Rejected('E-K2-NOT-LEGACY','prototype-contract 围栏在案（本轮新格式=K0，不适用 K2 迁移路径）；出现 %d 次'%text.count(K2_FENCE))
    cb={m:text.count(m) for m in K2_CONTROLLED_ONCE}
    if cb['id="prototype-config"']!=1:
        raise K2Rejected('E-K2-PASSWORD-BASIS','prototype-config 出现 %d 次（口令依据缺失/重复=坏状态，无损拒绝）'%cb['id="prototype-config"'])
    missing=[m for m,c in cb.items() if c!=1]
    if missing:
        raise K2Rejected('E-K2-CONTROLLED-SHAPE','受控块非恰1：%s'%json.dumps({m:text.count(m) for m in missing}))
    if text.count('</head>')!=1:
        raise K2Rejected('E-K2-CONTROLLED-SHAPE','</head> 出现 %d 次'%text.count('</head>'))
    return {'free_pair':counts,'v03r':v03r,'already_current':already_current,'controlled':cb,'old_backup_stmt':text.count(K2_OLD_BACKUP_STMT)}

def k2_residual_diff(text,out):
    """块外残差对比：FREE 双块剔除后必须逐字节一致；不一致→逐 hunk 比对受认可变换表（未匹配即拒）。"""
    pre_resid=k2_strip_blocks(text);post_resid=k2_strip_blocks(out)
    if pre_resid is None or post_resid is None:
        raise K2Rejected('E-K2-FREE-PAIR','迁移后 FREE 双块定位失败（成对结构被破坏）')
    if pre_resid==post_resid:return {'outside_blocks_identical':True,'applied_transforms':[]}
    sm=difflib.SequenceMatcher(None,pre_resid.split('\n'),post_resid.split('\n'),autojunk=False)
    hunks=[]
    for tag,i1,i2,j1,j2 in sm.get_opcodes():
        if tag=='equal':continue
        frag_old='\n'.join(pre_resid.split('\n')[i1:i2])[:300]
        frag_new='\n'.join(post_resid.split('\n')[j1:j2])[:300]
        ok=None
        for old_s,new_s in K2_SANCTIONED_RESIDUAL:
            if old_s in frag_old and new_s in frag_new:
                ok=old_s[:60];break
        if K2_RE_VERSION_ANY.search(frag_old) and 'version: "3.7.0"' in frag_new:
            ok=ok or 'version→3.7.0'
        hunks.append({'sanctioned':bool(ok),'matched':ok,'old':frag_old,'new':frag_new})
    bad=[h for h in hunks if not h['sanctioned']]
    if bad:
        raise K2Rejected('E-K2-UNSANCTIONED-DIFF','块外出现不受认可的变更（无损拒绝）',bad[:5])
    return {'outside_blocks_identical':False,'applied_transforms':hunks}

def k2_apply_retain(text):
    """apply_current「需保留」装配：幂等补施＋合规校验（done 在案→verified；目标在→补施；双缺→拒绝）。"""
    log=[]
    for pid,done,target,repl,required in K2_RETAIN_AUDIT:
        if text.count(done)>=1:
            log.append({'patch':pid,'state':'verified'});continue
        if target and text.count(target)>=1:
            if repl=='RE_SUB_FNOTE':
                text=K2_FNOTE_RE.sub('<textarea id="fNote" rows="4" placeholder="当前功能或流程的自由说明，可任意换行修改"></textarea>',text,count=1)
            elif repl:
                text=text.replace(target,repl,1)
            else:
                text=text.replace(target,target,1)
            if text.count(done)>=1:
                log.append({'patch':pid,'state':'applied'});continue
            raise K2Rejected('E-K2-RETAIN-ABSENT','%s 补施后 done 形态仍未在案'%pid)
        raise K2Rejected('E-K2-RETAIN-ABSENT','%s：done 形态与原目标均不在案（主体变体不受支持，无损拒绝）'%pid)
    return text,log

def k2_check_controlled_blocks(text,expected):
    """build.py check_controlled_blocks 等价：每标记恰1，否则 ValueError。"""
    for marker in expected:
        n=text.count(marker)
        if n!=1:
            raise ValueError('Controlled block %s appears %d time(s); expected exactly 1'%(marker,n))

def k2_page_counts(pages):
    """页面域计数（pages 槽内，\n 口径）：屏集合/属性计数——页面域完整性证据。"""
    screens=re.findall(r'<section class="screen" data-screen="([^"]+)"',pages)
    return {'screens':len(screens),'screen_ids':screens,
        'data_eid':pages.count('data-eid='),'data_on':pages.count('data-on='),
        'data_note':pages.count('data-note='),'data_block':pages.count('data-block='),
        'data_layout_free':pages.count('data-layout="free"'),'free_backup':pages.count('data-free-backup')}

def k2_extract_page_domain(text):
    """页面域六件提取（REFIT v2）：header（首 DOCTYPE 前注释）/title/doc_id/inject（</style> 后
    单行受控注入）/pages（canvas 槽内全部屏）/tail（末 </html> 后空白）。锚点不符→E-K2-PAGE-EXTRACT。
    页面域=六件总和；其余全部为编辑器域（种子骨架），由重装配以当前资产整体替换。"""
    def bad(msg):raise K2Rejected('E-K2-PAGE-EXTRACT',msg)
    dt=text.find('<!DOCTYPE html>')
    if dt<0:bad('<!DOCTYPE html> 未定位')
    # 全文含 JS 导出串字面量（saveNewHTML 等），不做全局恰 1；改验文档位：首 DOCTYPE 前仅允许注释/空白
    # （V04R-HEADER-FIX：正则 fullmatch 在个别 CRLF/长注释输入上与逐字扫描不一致（外部重放通过而进程内失败），
    #   改为逐字扫描判定——语义等价且行为确定：跳过空白与 <!--...--> 注释块，其余即异常。）
    header=text[:dt]
    _i=0;_n=len(header)
    while _i<_n:
        if header[_i].isspace():_i+=1;continue
        if header.startswith('<!--',_i):
            _j=header.find('-->',_i+4)
            if _j<0:bad('首 <!DOCTYPE html> 前含未闭合注释（文档位异常）')
            _i=_j+3;continue
        bad('首 <!DOCTYPE html> 前含注释/空白以外内容（文档位异常）')
    if '__PROJECT_' in header:bad('header 含装配占位（非受控源件）')
    h_end=text.find('</head>')
    if h_end<0:bad('</head> 未定位')
    head=text[dt:h_end]
    mt=re.findall(r'<title>(.*?)</title>',head)
    if len(mt)!=1:bad('<title> 非恰 1')
    mi=re.findall(r'data-doc="([^"]*)"',head)
    if len(mi)!=1:bad('data-doc 非恰 1')
    so=text.find('<style>')
    if so<0:bad('主 <style> 未定位')
    sc=text.find('</style>',so)
    if sc<0 or sc>h_end:bad('主 </style> 未定位')
    if text[sc+8]!='\n':bad('inject 起始锚（主 </style> 后须为换行）不符')
    inj_end=text.find('</head>',sc)
    if inj_end!=h_end:bad('</head> 恰 1 但不在主样式闭合后')
    inject=text[sc+9:h_end]
    if '__PROJECT_' in inject:bad('inject 含装配占位')
    for cid in K2_CONTROLLED_ONCE:
        if inject.count(cid)!=1:bad('inject 受控块 %s 非恰 1'%cid)
    if text.count(K2_CANVAS_ANCHOR)!=1:bad('canvas 槽锚 %s 非恰 1'%K2_CANVAS_ANCHOR)
    ca=text.find(K2_CANVAS_ANCHOR)
    ps=ca+len(K2_CANVAS_ANCHOR)
    if text[ps]!='\n':bad('pages 起始锚（canvas 开标签后须为换行）不符')
    pe=text.find('\n</main>',ps)
    if pe<0:bad('canvas 闭合 \\n</main> 未定位')
    pages=text[ps+1:pe]
    if '<section class="screen" data-screen="' not in pages:bad('pages 域无 screen（截断件?）')
    if '__PROJECT_' in pages:bad('pages 含装配占位')
    guard=text.find(K2_GUARD)
    sc2=text.find('</script>',guard)
    if sc2<0 or text[sc2+9:sc2+16]!='\n</body':bad('主 </script> 尾锚（\\n</body）不符')
    de=text.find('</html>',sc2)
    if de<0 or text.find('</html>',de+1)>=0:bad('</html> 非恰 1')
    tail=text[de+7:]
    if tail.strip()!='':bad('尾部含非空白内容')
    return {'header':header,'title':mt[0],'doc_id':mi[0],'inject':inject,'pages':pages,'tail':tail,
            'pages_counts':k2_page_counts(pages)}

def k2_recompose(pd):
    """全量重装配（build.compose 同构）：apply_current(当前 seed) → 占位替换（title 全局，含顶栏 <b>）
    → </head> 前回插 inject → PROTOTYPE_PAGES 槽回插 pages → header/tail 原样拼回。
    seed 自带文末 </html>\\n——截到最后一个 </html>（含）为止，文档尾部由源件 tail 原样接管。"""
    seed=k2_seed_current()
    end=seed.rfind('</html>')
    if end<0:raise K2Rejected('E-K2-EDITOR-DOMAIN','seed </html> 未定位（管线内部错误）')
    doc=seed[:end+7].replace('__PROJECT_TITLE__',pd['title']).replace('__PROJECT_ID__',pd['doc_id'])
    if doc.count('</head>')!=1:raise K2Rejected('E-K2-EDITOR-DOMAIN','seed </head> 非恰 1（管线内部错误）')
    doc=doc.replace('</head>',pd['inject']+'</head>',1)
    if doc.count('<!--PROTOTYPE_PAGES-->')!=1:raise K2Rejected('E-K2-EDITOR-DOMAIN','seed PROTOTYPE_PAGES 槽非恰 1（管线内部错误）')
    doc=doc.replace('<!--PROTOTYPE_PAGES-->',pd['pages'],1)
    return pd['header']+doc+pd['tail']

def migrate_k2(text):
    """K2 受控迁移核心 v2（编辑器脚本域全套装换装；旧件文本→新件文本），不含 IO。
    流程：预检（含已迁移成品放行）→页面域六件提取→apply_current(当前 seed) 全量重装配→
    编辑器域四跨度 SHA 全集校验（≠当前资产=管线内部错误 E-K2-EDITOR-DOMAIN）→
    「需保留」30 项审计（构造性全 verified）→受控块恰 1/占位零残留→
    页面域六件换装前后逐字节相等→幂等自证（recompose∘extract==id）。识别不符抛 K2Rejected（E-K2-*）。"""
    pre=k2_preflight(text)
    t0=time.perf_counter()
    pd=k2_extract_page_domain(text)
    out=k2_recompose(pd)
    dt=(time.perf_counter()-t0)*1000.0
    # 编辑器脚本域全集 SHA 校验（REFIT 升级点：FREE JS/CSS 两项 → 主样式体/主脚本体/FREE JS/FREE CSS 全集）
    got=k2_editor_spans(out);ref=k2_editor_spans(k2_seed_current())
    if got!=ref:
        raise K2Rejected('E-K2-EDITOR-DOMAIN','编辑器域换装后与当前资产不一致（管线内部错误）',
            {'product':k2_editor_shas(got),'current':k2_editor_shas(ref)})
    out2,retain_log=k2_apply_retain(out)
    if out2!=out or any(e['state']!='verified' for e in retain_log):
        raise K2Rejected('E-K2-EDITOR-DOMAIN','当前 seed 未内含全部「需保留」装配（管线内部错误）',
            {'retain_log':retain_log})
    expected=K2_FREE_MARKERS+K2_CONTROLLED_ONCE+[K2_GUARD,'</head>']
    try:k2_check_controlled_blocks(out,expected)
    except ValueError as e:raise K2Rejected('E-K2-CONTROLLED-COUNT',str(e))
    if '<!--PROTOTYPE_PAGES-->' in out or '__PROJECT_TITLE__' in out or '__PROJECT_ID__' in out:
        raise K2Rejected('E-K2-CONTROLLED-COUNT','装配槽/占位残留于迁移产物')
    post_free_counts={m:out.count(m) for m in K2_FREE_MARKERS}
    if any(v!=1 for v in post_free_counts.values()):
        raise K2Rejected('E-K2-FREE-PAIR','迁移后 FREE 对计数异常：%s'%json.dumps(post_free_counts))
    pd2=k2_extract_page_domain(out)
    ident={k:(pd[k]==pd2[k]) for k in ('header','title','doc_id','inject','pages','tail')}
    if not all(ident.values()):
        raise K2Rejected('E-K2-INTEGRITY','页面域六件换装前后不一致（页面域受损）:%s'%json.dumps([k for k,v in ident.items() if not v]),pd['pages_counts'])
    if k2_recompose(pd2)!=out:
        raise K2Rejected('E-K2-EDITOR-DOMAIN','幂等自证失败（recompose∘extract≠id，管线内部错误）')
    report={'recompose_ms':round(dt,2),'already_current':pre['already_current'],
        'editor_domain_shas':k2_editor_shas(got),
        'retain_log':retain_log,
        'retain_applied':sum(1 for e in retain_log if e['state']=='applied'),
        'retain_verified':sum(1 for e in retain_log if e['state']=='verified'),
        'page_domain':{'identical':ident,'pages_counts_pre':pd['pages_counts'],
                       'pages_counts_post':pd2['pages_counts'],
                       'screens_fulltext_pre':len(re.findall(r'<section class="screen" data-screen="',text)),
                       'screens_fulltext_post':len(re.findall(r'<section class="screen" data-screen="',out))},
        'old_backup_stmt_in_source':pre['old_backup_stmt']}
    return out,report

def cmd_migrate_k2(argv):
    """migrate-k2 子命令 CLI：python upgrade_html.py migrate-k2 <旧件> --output <新件> [--json-out <日志>]。
    REFIT v2：编辑器脚本域全套装换装（商城旧件页面域保留、编辑器域以当前资产重建）。"""
    ap=argparse.ArgumentParser(prog='upgrade_html.py migrate-k2',description='V04 K2 受控迁移：编辑器脚本域全套装换装+页面域六件保留（识别不符具名拒绝 E-K2-*，零产出）')
    ap.add_argument('source',type=Path);ap.add_argument('--output',required=True,type=Path);ap.add_argument('--json-out',type=Path,default=None)
    args=ap.parse_args(argv)
    if args.output.exists():
        print(json.dumps({'result':'rejected','code':'E-K2-OUTPUT-EXISTS','message':'目标已存在（已有输出无损拒绝，选新路径）：%s'%args.output},ensure_ascii=False));return 1
    if not args.source.exists():
        print(json.dumps({'result':'error','code':'E-IO','message':'source not found'},ensure_ascii=False));return 2
    src_bytes=args.source.read_bytes();pre_sha=hashlib.sha256(src_bytes).hexdigest()
    try:text=src_bytes.decode('utf-8')
    except UnicodeDecodeError as e:
        print(json.dumps({'result':'rejected','code':'E-K2-DECODE','message':'源件非严格 UTF-8（%s）'%e},ensure_ascii=False));return 1
    if not text:
        print(json.dumps({'result':'rejected','code':'E-K2-EMPTY','message':'源件为空'},ensure_ascii=False));return 1
    # 行尾统一为 \n（与 read_text 通用换行口径/冻结单 \n 行号口径一致；写入落盘 newline='' 保持 \n）
    crlf_lines=text.count('\r\n')
    text=re.sub(r'\r\n|\r','\n',text)
    try:out,report=migrate_k2(text)
    except K2Rejected as e:
        payload={'result':'rejected','code':e.code,'message':e.message}
        if e.detail is not None:payload['detail']=e.detail
        print(json.dumps(payload,ensure_ascii=False));return 1
    args.output.parent.mkdir(parents=True,exist_ok=True)
    if args.output.exists():
        print(json.dumps({'result':'rejected','code':'E-K2-OUTPUT-EXISTS','message':'落盘前复查：目标已存在（无损拒绝）'},ensure_ascii=False));return 1
    with open(args.output,'w',encoding='utf-8',newline='') as f:f.write(out)
    if hashlib.sha256(args.source.read_bytes()).hexdigest()!=pre_sha:
        print(json.dumps({'result':'rejected','code':'E-K2-SOURCE-DRIFT','message':'迁移后源件字节发生变化（不应发生）'},ensure_ascii=False));return 1
    out_bytes=args.output.read_bytes()
    result={'result':'migrated','source':str(args.source),'output':str(args.output),
        'pre_sha256':pre_sha,'pre_bytes':len(src_bytes),
        'post_sha256':hashlib.sha256(out_bytes).hexdigest(),'post_bytes':len(out_bytes),
        'source_unchanged':True,'entry':'upgrade_html.py migrate-k2','upgrade_module':__file__,
        'source_crlf_lines_normalized':crlf_lines}
    result.update(report)
    js=json.dumps(result,ensure_ascii=False,indent=1)
    print(js)
    if args.json_out:args.json_out.write_text(js,encoding='utf-8')
    return 0


def main(argv=None):
    argv=list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0]=='migrate-k2':sys.exit(cmd_migrate_k2(argv[1:]))
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args(argv)
    if args.output.exists():parser.error('Destination exists; choose a new path to preserve edits')
    value=upgrade(args.source.read_text(encoding='utf-8'))
    args.output.parent.mkdir(parents=True,exist_ok=True);args.output.write_text(value,encoding='utf-8')
    print('Upgraded without modifying source:',args.output.resolve())


if __name__=='__main__':main()
