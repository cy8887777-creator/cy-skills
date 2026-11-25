// ui-walkthrough · 批量机检编排器
// 用法: node batch.mjs <页面根URL> <页面根目录> <输出目录> [--caliber 项目口径.json] [--compare 旧台账.json] [--viewport 390x844,1440x900]
// 退出码: 0=干净  1=存在严重问题  2=引擎故障
// 零截图：capturePage({ screenshot:false })；全量数据只落盘，进度日志供人排查
import { pathToFileURL } from 'node:url'
import { readdirSync, mkdirSync, writeFileSync, statSync, readFileSync, existsSync } from 'node:fs'
import { join, dirname, relative } from 'node:path'
import { fileURLToPath } from 'node:url'

// ---------- 引擎解析（多候选，DSH_DESIGN_AUDIT_LIB 环境变量可覆盖） ----------
const HERE = dirname(fileURLToPath(import.meta.url))
const LIB_CANDIDATES = [
  process.env.DSH_DESIGN_AUDIT_LIB,
  join(HERE, '../../node_modules/dsh-design-audit/lib/') + '',
  'C:/Users/admin/.dsh/profiles/desktop/node_modules/dsh-design-audit/lib/',
  'D:/deepseek harness workspace/dsh-design-audit/lib/',
].map(p => p && p.replace(/\\/g, '/')).filter(Boolean)

let capturePage, runChecks, EVIDENCE_EXPRESSION
for (const base of LIB_CANDIDATES) {
  try {
    ;({ capturePage } = await import(pathToFileURL(base + 'cdp.js').href))
    ;({ runChecks } = await import(pathToFileURL(base + 'checks.js').href))
    ;({ EVIDENCE_EXPRESSION } = await import(pathToFileURL(base + 'collect.js').href))
    if (capturePage && runChecks && EVIDENCE_EXPRESSION) break
  } catch { /* 尝试下一候选 */ }
}
if (!capturePage || !runChecks || !EVIDENCE_EXPRESSION) {
  console.error('引擎故障: design-audit 引擎库未找到（cdp.js/checks.js/collect.js）')
  process.exit(2)
}

// ---------- 参数解析（位置参数 + 具名参数） ----------
const argv = process.argv.slice(2)
const flags = {}
const positional = []
for (let i = 0; i < argv.length; i += 1) {
  if (argv[i] === '--caliber') flags.caliber = argv[(i += 1)]
  else if (argv[i] === '--compare') flags.compare = argv[(i += 1)]
  else if (argv[i] === '--viewport') flags.viewport = argv[(i += 1)]
  else positional.push(argv[i])
}

const BASE = (positional[0]?.replace(/\/$/, '')) ?? 'http://127.0.0.1:8377'
const ROOT = positional[1] ?? process.cwd()
const OUT = positional[2] ?? join(process.cwd(), 'ledger')
mkdirSync(OUT, { recursive: true })

// ---------- 视口（--viewport "390x844" 或逗号分隔多档 "390x844,1440x900"；多档时台账页 id 加 @宽 后缀） ----------
const VIEWPORTS = (flags.viewport ?? '390x844').split(',').map(s => {
  const [w, h] = s.trim().split('x').map(Number)
  return Number.isFinite(w) && Number.isFinite(h) && w > 0 && h > 0 ? { w, h } : null
}).filter(Boolean)
if (!VIEWPORTS.length) {
  console.error('视口参数格式错误: ' + String(flags.viewport) + '（期望 390x844 或 390x844,1440x900）')
  process.exit(2)
}

// ---------- 口径：技能缺省 ← 项目口径覆盖（同名字段整体替换） ----------
const SKILL_ROOT = join(HERE, '..')
let CAL = {}
try {
  CAL = JSON.parse(readFileSync(join(SKILL_ROOT, 'config/caliber.json'), 'utf8'))
} catch { /* 缺省常量兜底 */ }
if (flags.caliber) {
  if (!existsSync(flags.caliber)) {
    console.error('项目口径文件不存在: ' + flags.caliber)
    process.exit(2)
  }
  try {
    const project = JSON.parse(readFileSync(flags.caliber, 'utf8'))
    CAL = { ...CAL, ...project }
  } catch (err) {
    console.error('项目口径文件解析失败: ' + String(err.message))
    process.exit(2)
  }
}
let TOUCH_MIN = 22, FONT_BODY = 12, FONT_HINT = 11
let GRAD = Array.isArray(CAL.gradient_tokens) ? CAL.gradient_tokens : []
let QUERY = typeof CAL.query_convention === 'string' ? CAL.query_convention : ''
let HIDE = Array.isArray(CAL.hide_selectors) ? CAL.hide_selectors : []
let FOCUS_SHARED = Array.isArray(CAL.focus_shared_selectors) ? CAL.focus_shared_selectors : ['.input,.select,.textarea']
if (Number.isFinite(CAL.touch_min_px)) TOUCH_MIN = CAL.touch_min_px
if (Number.isFinite(CAL.font_floor_body)) FONT_BODY = CAL.font_floor_body
if (Number.isFinite(CAL.font_floor_hint)) FONT_HINT = CAL.font_floor_hint

// ---------- 已仲裁豁免（上一轮驳回的误报，复跑自动豁免） ----------
let EXEMPT_RULES = []
try {
  const ex = JSON.parse(readFileSync(join(OUT, 'exemptions.json'), 'utf8'))
  EXEMPT_RULES = Array.isArray(ex) ? ex : (Array.isArray(ex.items) ? ex.items : [])
} catch { /* 无豁免文件，正常 */ }

// ---------- 页面枚举 ----------
function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    const st = statSync(p)
    if (st.isDirectory()) {
      if (name !== 'assets' && name !== 'node_modules') yield* walk(p)
    } else if (name.endsWith('.html')) yield p
  }
}
const pages = [...walk(ROOT)].sort()

// ---------- 证据包：finding 按 selector 匹配回取证桶的原始条目 ----------
function contextFor(f, evidence) {
  const id = String(f.id ?? '')
  const msg = String(f.message ?? '')
  const sel = String(f.selector ?? '')
  const bySel = (arr) => (Array.isArray(arr) ? arr.find(e => String(e.selector ?? '') === sel) : undefined)
  let entry, bucket
  if (/contrast|对比度/i.test(id + msg)) { entry = bySel(evidence.text); bucket = 'text' }
  else if (/typography|字号|行高/i.test(id + msg)) { entry = bySel(evidence.text); bucket = 'text' }
  else if (/tap|触控|目标/i.test(id + msg)) { entry = bySel(evidence.controls); bucket = 'controls' }
  else if (/overflow|溢出|横向/i.test(id + msg)) { entry = bySel(evidence.overflow); bucket = 'overflow' }
  else if (/alt|图片/i.test(id + msg)) { entry = bySel(evidence.images?.missingAlt) ?? bySel(evidence.images?.broken); bucket = 'images' }
  else if (/label|表单/i.test(id + msg)) { entry = bySel(evidence.unlabeledInputs); bucket = 'unlabeledInputs' }
  if (entry === undefined) { // 兜底：跨桶按选择器扫一遍
    for (const key of ['text', 'controls', 'overflow']) {
      const hit = bySel(evidence[key])
      if (hit) { entry = hit; bucket = key; break }
    }
  }
  if (entry === undefined) return { available: false, reason: '证据未含该元素明细' }
  // 所在区块提示：取选择器顶层两段作为区块容器线索
  const blockHint = sel.split('>').slice(0, 2).join('>').trim()
  return { available: true, bucket, entry, blockHint }
}

// ---------- 校准过滤器（机制实现；规则名与细则见 references/calibration.md） ----------
function classify(f) {
  const s = JSON.stringify(f)
  const msg = String(f.message ?? f.title ?? '')
  if (EXEMPT_RULES.some(e => (e.selector && s.includes(e.selector)) || (e.rule && f.rule && String(f.rule).includes(e.rule)))) return 'EXEMPT'
  if (HIDE.length && HIDE.some(sel => s.includes(sel))) return 'EXEMPT'
  if (/对比度|1\.4\.3/.test(msg + s)) {
    if (GRAD.length && GRAD.some(t => s.includes(t))) return 'EXEMPT'
    return 'REAL'
  }
  // 引擎 message 实际形如「N 处文本小于 12px」，不含「字号」二字（calibration.md 引擎现状口径）——
  // 判据须同时覆盖中文档名与引擎句式，否则整条字号分支（含 11px 豁免线）静默失效
  if (/字号|文本小于\s*\d+(\.\d+)?\s*px|typography/i.test(msg)) {
    const m = /([\d.]+)px/.exec(String(f.measured ?? s))
    const px = m ? parseFloat(m[1]) : NaN
    if (!Number.isNaN(px)) {
      if (px <= 10) return 'REAL'
      if (px <= FONT_HINT) return 'EXEMPT'
      return 'P2'
    }
    return 'P2'
  }
  if (/tap|目标尺寸|触控|点击目标|交互目标/i.test(String(f.id ?? '') + msg)) {
    // 捆绑条目：从 measured 解析全部目标尺寸（消息里的"24×24"是判据阈值，不是元素尺寸，不能取）
    const measured = String(f.measured ?? '')
    const pairs = [...measured.matchAll(/(\d+)\s*[×x]\s*(\d+)/g)].map(m2 => parseInt(m2[2], 10))
    if (pairs.length > 0) return pairs.some(h => h < TOUCH_MIN) ? 'REAL' : 'P2'
    const m = /(\d+)\s*[×x]\s*(\d+)/.exec(s)
    const h = m ? parseInt(m[2], 10) : 99
    return h < TOUCH_MIN ? 'REAL' : 'P2'
  }
  if (/焦点可见|2\.4\.7/.test(msg + s) && FOCUS_SHARED.some(sel => s.includes(sel))) return 'EXEMPT'
  return f.severity === 'high' ? 'REAL' : 'P2'
}

// ---------- 中文级别映射 ----------
const SEV = { high: 'P1', medium: 'P2', low: 'P3', info: 'P3', P0: 'P0', P1: 'P1', P2: 'P2', P3: 'P3' }

// ---------- 主循环（页面 × 视口；多视口时台账页 id 带 @宽 后缀区分） ----------
const ledger = []
let n = 0
for (const file of pages) {
  n += 1
  const rel = relative(ROOT, file).split('\\').join('/')
  const url = `${BASE}/${rel}${QUERY}`
  const id = rel.replace(/\.html$/, '')
  for (const vp of VIEWPORTS) {
    const pageId = VIEWPORTS.length > 1 ? `${id}@${vp.w}` : id
    process.stdout.write(`[${String(n).padStart(3, '0')}/${pages.length}] ${pageId} ... `)
    try {
      const result = await capturePage({
        url, width: vp.w, height: vp.h, fullPage: true,
        expression: EVIDENCE_EXPRESSION, screenshot: false, settleMs: 350,
      })
      const evidence = result.evaluation ?? {}
      const checks = runChecks(evidence)
      const findings = Array.isArray(checks) ? checks : (checks?.findings ?? [])
      const judged = findings.map(f => {
        const tier = classify(f)
        const context = tier === 'EXEMPT' ? { available: false, reason: '已豁免' } : contextFor(f, evidence)
        return { page: pageId, tier, context, ...f }
      })
      ledger.push({ page: pageId, elements: result.readiness?.elementCount ?? '?', findings: judged })
      const real = judged.filter(j => j.tier === 'REAL').length
      console.log(`${judged.length} 条（真问题 ${real}）`)
    } catch (err) {
      console.log('引擎错误: ' + String(err.message).slice(0, 100))
      ledger.push({ page: pageId, error: String(err.message), findings: [] })
    }
  }
}

// ---------- 汇总 ----------
const all = ledger.flatMap(l => l.findings ?? [])
const real = all.filter(f => f.tier === 'REAL')
// 校准降级（tier=P2）的问题不算严重级；降级条目与建议档都归入 P2 统计，保证分账闭合
const p1 = real.filter(f => f.tier !== 'P2' && (f.severity === 'high' || f.severity === 'P0' || f.severity === 'P1'))
const p2 = all.filter(f => f.tier === 'P2' || (f.tier === 'REAL' && !p1.includes(f)))
const exempt = all.filter(f => f.tier === 'EXEMPT')
const shells = ledger.filter(l => (l.elements ?? 99) < 20).map(l => l.page)
const errors = ledger.filter(l => l.error)

writeFileSync(join(OUT, 'ledger.json'), JSON.stringify({ generatedAt: new Date().toISOString(), pages: ledger.length, ledger }, null, 2))

let md = `# UI 走查台账（零截图 · 机械探针）\n\n> 工作文件：供仲裁与修复流程消费；交付给人阅读的是 report.md\n\n`
md += `- 页面：${ledger.length}｜真问题：${real.length}（P1 ${p1.length} / P2 ${p2.length}）｜豁免：${exempt.length}｜空壳：${shells.length}\n\n`
for (const l of ledger) {
  md += `\n## ${l.page}\n`
  for (const f of (l.findings ?? [])) {
    // 级别标签用校准后的级别（降级条目显示 P2，与汇总计数一致）
    const sev = f.tier === 'EXEMPT' ? '豁免' : (f.tier === 'P2' ? 'P2' : (SEV[f.severity] ?? f.severity ?? ''))
    const mark = f.tier === 'EXEMPT' ? `【豁免】` : `[${sev}]`
    md += `- ${mark} ${f.message ?? f.dimension ?? ''} ｜ ${JSON.stringify(f).slice(0, 200)}\n`
  }
}
if (shells.length) md += `\n## 疑似空壳页（元素 <20，需人工归因）\n${shells.map(x => '- ' + x).join('\n')}\n`
if (errors.length) md += `\n## 引擎错误\n${errors.map(x => '- ' + x.page + '：' + x.error).join('\n')}\n`
writeFileSync(join(OUT, 'ledger.md'), md)

// ---------- 复验对比（--compare 旧台账.json） ----------
if (flags.compare) {
  try {
    const oldData = JSON.parse(readFileSync(flags.compare, 'utf8'))
    const key = f => `${f.page}|${f.selector ?? ''}|${f.id ?? f.rule ?? ''}`
    const oldFindings = (oldData.ledger ?? []).flatMap(l => (l.findings ?? []).map(f => ({ ...f, page: l.page })))
    const newKeys = new Set(all.map(key))
    const oldMap = new Map(oldFindings.map(f => [key(f), f]))
    const fixed = [], kept = [], introduced = []
    for (const f of all) (oldMap.has(key(f)) ? kept : introduced).push(f)
    for (const [k, f] of oldMap) if (!newKeys.has(k)) fixed.push(f)
    const line = (f, note) => `- [${SEV[f.severity] ?? f.severity ?? ''}] ${f.page} ｜ ${f.message ?? f.rule ?? ''} ｜ ${note}`
    let cmp = `# 复验对比\n\n- 旧：${oldFindings.length} 条｜新：${all.length} 条\n\n`
    cmp += `## 已修复（旧有新无）${fixed.length} 条\n${fixed.map(f => line(f, '旧实测：' + JSON.stringify(f.measured ?? '').slice(0, 80))).join('\n') || '（无）'}\n\n`
    cmp += `## 仍存在（旧有新有）${kept.length} 条\n${kept.map(f => line(f, '仍需处理')).join('\n') || '（无）'}\n\n`
    cmp += `## 新引入（新有旧无）${introduced.length} 条\n${introduced.map(f => line(f, '本次新发现')).join('\n') || '（无）'}\n`
    writeFileSync(join(OUT, 'compare.md'), cmp)
    console.log(`对比: 已修复 ${fixed.length}｜仍存在 ${kept.length}｜新引入 ${introduced.length} → compare.md`)
  } catch (err) {
    console.error('对比失败: ' + String(err.message))
  }
}

// ---------- 汇总输出 ----------
console.log('---- 汇总 ----')
console.log(`页面 ${ledger.length}｜真问题 ${real.length}（P1 ${p1.length}/P2 ${p2.length}）｜豁免 ${exempt.length}｜空壳 ${shells.length}｜错误 ${errors.length}`)
console.log(`台账: ${join(OUT, 'ledger.md')}`)
// 退出码三态：0=干净｜1=存在严重问题｜2=引擎故障（错误页=该页根本没被检查，漏检即缺口，任何错误页即 2；
// 偶发超时重跑即可区分——守门宁严勿松，禁止把引擎故障吞成"干净"）
process.exitCode = errors.length > 0 ? 2 : (p1.length > 0 ? 1 : 0)
