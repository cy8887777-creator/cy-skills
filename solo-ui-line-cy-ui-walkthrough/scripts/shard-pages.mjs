// 观感层分片：页面清单 → ≤N 页/片的确定性切分 + 状态台账
// 用法：node shard-pages.mjs <页面根目录> <输出目录> [片大小=30] [仅子树=相对路径]
// 产出：<输出目录>/shards.json（分片计划）+ shard-status.json（状态台账，断点续跑依据）
import { readdirSync, statSync, writeFileSync, mkdirSync } from 'node:fs'
import { join, relative } from 'node:path'

const root = process.argv[2]
const outDir = process.argv[3]
const SHARD = Number(process.argv[4] || 30)
const only = process.argv[5] // 可选：只切某个子树（相对 root）

function* walk(dir) {
  for (const name of readdirSync(dir)) {
    if (name === 'assets' || name === 'node_modules') continue
    const p = join(dir, name)
    if (statSync(p).isDirectory()) yield* walk(p)
    else if (name.endsWith('.html')) yield p
  }
}

let pages = [...walk(root)].sort().map(f => relative(root, f).split('\\').join('/'))
if (only) pages = pages.filter(p => p === only || p.startsWith(only.replace(/\\/g, '/') + '/'))

const shards = []
for (let i = 0; i < pages.length; i += SHARD) {
  shards.push({ id: 'shard-' + String(shards.length + 1).padStart(2, '0'), pages: pages.slice(i, i + SHARD) })
}

mkdirSync(outDir, { recursive: true })
const plan = { generatedAt: new Date().toISOString(), root, shardSize: SHARD, subtree: only ?? '(全部)', total: pages.length, shards: shards.map(s => ({ ...s, count: s.pages.length })) }
writeFileSync(join(outDir, 'shards.json'), JSON.stringify(plan, null, 2))
const status = { updatedAt: plan.generatedAt, shards: plan.shards.map(s => ({ id: s.id, count: s.count, status: '未派发', findings: null })) }
writeFileSync(join(outDir, 'shard-status.json'), JSON.stringify(status, null, 2))

console.log(`页面 ${pages.length} → ${shards.length} 片（≤${SHARD} 页/片）`)
for (const s of plan.shards) console.log(`  ${s.id}: ${s.count} 页 ｜ ${s.pages[0]} … ${s.pages[s.pages.length - 1]}`)
console.log(`状态台账: ${join(outDir, 'shard-status.json')}（未派发→派出→完成/中断；断点续跑只补非「完成」片）`)
