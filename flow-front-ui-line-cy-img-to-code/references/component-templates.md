# 写码骨架模板（references）——第 4 步配套

React + Tailwind 栈的**标准件写法**（与实测数值组合使用）。目标：把
结构从"逐次发明"变成"填数据"——省时间 + 消灭单位/RTL 低级错误。
HTML+CSS 栈同构（class 换 style）。所有数字来自 brief（逻辑 px，
1:1 即 CSS px——管线已按 dpr 归一，禁止任何换算）。

## 0. 画布壳（每页必用）

```jsx
// html: dir=rtl（阿语）+ html{background:底色} 阻断背景传播
// body: width:375px; height:100dvh; max-height:812px; overflow:hidden
const IMG = ({n, x, y, w, h, r, style}) => (          // RAW 素材（圆角必裁）
  <img src={`assets/asset_${n}.png`} data-asset={`asset_${n}`}
    style={{left:x, top:y, width:w, height:h, position:'absolute',
      borderRadius:r||0, objectFit:'cover', ...style}}/>);
const ALPHA = ({n, x, y, w, h, style}) => (           // 透明素材
  <img src={`assets/asset_${n}_alpha.png`} data-asset={`asset_${n}`}
    style={{left:x, top:y, width:w, height:h, position:'absolute', ...style}}/>);
```

## 1. 状态栏（时间 + 挖孔 + 右侧图标）

```jsx
<div className="abs" data-skeleton="sN" style={{left:0, top:0, width:375, height:H}}></div>
<div className="abs" style={{left:T_X, top:T_Y, width:'max-content', fontSize:15, fontWeight:700, color:'#FFF', lineHeight:'16px', direction:'ltr'}}>9:30</div>
```
时间/图标块**必须 `width:'max-content'`**（默认块宽会盖住挖孔，
layout_integrity 报文字×img 相交——实测事故）。

## 2. 文字块骨架（中心点断言，统一写法）

```jsx
<div data-skeleton="sN" className="abs" style={{
  left: CX, top: TOP, transform:'translateX(-50%)', width:'max-content',
  fontSize:F, fontWeight:W, color:C, lineHeight:LH+'px',
  whiteSpace:'nowrap'}}>TEXT</div>
{/* CX = 标注框中心x；TOP = 标注框顶y；两值都取 brief SKELETON 段（逻辑 px 直接用） */}
```

## 3. 双币胶囊（玻璃 + blur）

```jsx
<div className="abs" data-skeleton="sN" style={{left:L, top:T, width:W,
    height:H, direction:'ltr', display:'flex', gap:G}}>
  <div style={{width:W1, height:H1, borderRadius:100,
    background:'rgba(127,96,239,0.08)', border:'1px solid rgba(127,96,239,0.24)',
    backdropFilter:'blur(4px)', display:'flex', alignItems:'center',
    paddingLeft:PL, paddingRight:PR, gap:G2, boxSizing:'border-box'}}>...</div>
</div>
```

## 4. 等距图标行（flex + justify-between）

```jsx
<div className="abs" data-skeleton="sN" style={{left:L, top:T, width:W,
    height:H, direction:'ltr', display:'flex', alignItems:'center',
    justifyContent:'space-between', paddingLeft:PL}}>
  <IMG n={1} x={0} y={0} w={W1} h={H1} style={{position:'relative', borderRadius:R}}/>
  ...
</div>
```

## 5. 按钮对（RTL：图标右文字左，padding-right 定位）

```jsx
<div className="abs" data-skeleton="sN" style={{left:L, top:T, width:W,
    height:H, direction:'ltr', display:'flex', gap:G, paddingLeft:PL}}>
  <div data-container="cN" style={{width:BW, height:BH, borderRadius:BR,
      background:'linear-gradient(180deg,C1,C2)', border:'1px solid BC',
      direction:'rtl', display:'flex', alignItems:'center',
      justifyContent:'flex-start', paddingRight:PR, gap:G2,
      boxSizing:'border-box'}}>
    <ALPHA n={N} x={0} y={0} w={IW} h={IH} style={{position:'relative', flexShrink:0}}/>
    <span style={{fontSize:FS, fontWeight:FW, color:'#FFF',
      lineHeight:'20px', whiteSpace:'nowrap'}}>TEXT</span>
  </div>
</div>
```

## 6. 底部 dock（absolute 钉画布底 + 内部 absolute 项）

```jsx
<div className="abs" data-skeleton="sN" style={{left:L, top:T, width:W,
    height:H, borderRadius:24, background:'rgba(46,28,84,0.62)',
    border:'1px solid #B', backdropFilter:'blur(16px)', boxSizing:'border-box'}}>
  <div data-container="cN" className="abs" style={{left:X1, top:Y1, width:W1,
      height:H1, borderRadius:R1, background:'linear-gradient(...)',
      boxShadow:'...', boxSizing:'border-box'}}>
    <ALPHA n={N} x={IX} y={IY} w={IW} h={IH}/>   {/* absolute 相对 padding box */}
  </div>
  <ALPHA n={M} x={X2} y={Y2} w={W2} h={H2} style={{borderRadius:'50%'}}/>
</div>
```
**底栏锚 body 画布：`position:absolute; bottom:0` 语义（top 按实测），
禁止 `position:fixed`**（fixed 锚视口，RTL/宽视口下与正文撕裂）。

## 7. 入口列（图标 + 标签，flex column 定高单元）

```jsx
<div className="abs" style={{left:L, top:T, width:W, height:H,
    display:'flex', flexDirection:'column', alignItems:'center'}}>
  {units.map(u => (
    <div key={u.n} style={{width:W, height:UH, display:'flex',
        flexDirection:'column', alignItems:'center'}}>
      <ALPHA n={u.n} x={0} y={0} w={IW} h={IH} style={{position:'relative'}}/>
      <div style={{marginTop:3, fontSize:11, fontWeight:500,
        color:'#F8F5FF', lineHeight:'14px', textAlign:'center',
        whiteSpace:'nowrap'}}>{u.label}</div>
    </div>))}
</div>
```
单元定高（icon 顶严格对齐实测 y），label `marginTop` 只承担语义间距。

## 8. 自检口诀（写完过一遍）

数字照抄 brief 了吗（逻辑 px 1:1，禁止换算）？文字块 `max-content` 了吗？flex 内素材
`position:'relative'` 了吗（默认是 absolute，会飞出流）？RTL 容器里
padding-right 对应"行首"吗？`boxSizing:'border-box'` 加了吗？
