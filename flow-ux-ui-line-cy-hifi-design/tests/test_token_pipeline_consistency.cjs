// 正本表一致性守卫（2026-11 键名统一批追加）。
// 背景：运行时不携带 assets/token-keys.json，style-chooser.js 内嵌一份正本键读取清单、
// DENSITY_WORDS 与 keyPattern，靠人工与正本表保持同步——本测试是这份人工同步的机械防线。
// 断言：
//   ① chooser 内 cv(t,'…') 读取键集 == 正本表 keys[].key 集合（双向：不漏键、不多读、无驼峰残留）；
//   ② DENSITY_WORDS 键集 == density.allowed，中文词映射 = {compact:紧凑, regular:适中, loose:舒展}；
//   ③ chooser KEY_PATTERN 逐字 == 正本表 keyPattern；
//   ④ 正本表自洽：每个键自合 keyPattern（keyPattern 只约束形态，aliases 不参与——它们是
//      形态合法的错误键名登记，检查脚本据此提示正确键名）。
// 跑法：node tests/test_token_pipeline_consistency.cjs   （纯 Node，无浏览器依赖）
const fs = require('fs'), path = require('path'), assert = require('assert');
const ROOT = path.resolve(__dirname, '..');
const src = fs.readFileSync(path.join(ROOT, 'assets', 'style-chooser.js'), 'utf8');
const tk = JSON.parse(fs.readFileSync(path.join(ROOT, 'assets', 'token-keys.json'), 'utf8'));

/* ① cv() 读取键集 vs 正本表键集 */
const cvKeys = [...new Set([...src.matchAll(/cv\(t,'([^']+)'\)/g)].map(m => m[1]))].sort();
const canonical = tk.keys.map(k => k.key).sort();
assert.ok(cvKeys.length > 0, 'chooser 中未找到 cv(t,…) 读取清单（解析器失配？）');
/* 对象值键特例：cv 只收字符串/数值，object 键由 tokensToParams 直接消费 t.<key>（须在此登记并锚定消费点） */
const OBJECT_KEYS_TAKEN_DIRECTLY = ['dark'];
for (const k of OBJECT_KEYS_TAKEN_DIRECTLY) {
  assert.ok(tk.keys.some(x => x.key === k), '特例名单里的键不在正本表: ' + k);
}
assert.ok(/var darkT=\(t\.dark&&typeof t\.dark==='object'/.test(src) && /t\.dark===true\|\|darkT/.test(src),
  'dark 键的消费点变了（对象取字段 + 布尔开关），请同步更新本测试锚点');
const effective = canonical.filter(k => !OBJECT_KEYS_TAKEN_DIRECTLY.includes(k));
const missing = effective.filter(k => !cvKeys.includes(k));
const extra = cvKeys.filter(k => !effective.includes(k));
assert.deepStrictEqual({ missing, extra }, { missing: [], extra: [] },
  'chooser 读取清单与正本表键集不一致——缺=' + JSON.stringify(missing) + ' 多/旧名=' + JSON.stringify(extra));
pass('cv() 读取键集与正本表 keys[].key 一致（' + cvKeys.length + ' 键；对象键 ' +
  JSON.stringify(OBJECT_KEYS_TAKEN_DIRECTLY) + ' 直接消费且有锚点，无漏读/多读/旧名）');

/* ② DENSITY_WORDS vs density.allowed */
const dwMatch = src.match(/var DENSITY_WORDS=(\{[^}]*\});/);
assert.ok(dwMatch, 'chooser 中未找到 DENSITY_WORDS 定义');
const densityWords = {};
for (const m of dwMatch[1].matchAll(/([a-zA-Z0-9_]+):\s*'([^']*)'/g)) densityWords[m[1]] = m[2];
assert.ok(Object.keys(densityWords).length > 0, 'DENSITY_WORDS 解析为空（书写形态变了？）');
const density = tk.keys.find(k => k.key === 'density');
assert.ok(density && Array.isArray(density.allowed) && density.allowed.length > 0, '正本表缺 density.allowed');
assert.deepStrictEqual(Object.keys(densityWords).sort(), [...density.allowed].sort(),
  'DENSITY_WORDS 键集与 density.allowed 不一致');
assert.deepStrictEqual(densityWords, { compact: '紧凑', regular: '适中', loose: '舒展' },
  'DENSITY_WORDS 中文词映射偏离正本表 emits 口径（紧凑/适中/舒展）');
pass('DENSITY_WORDS 键集 == density.allowed，中文词映射符合正本表口径');

/* ③ keyPattern 逐字一致 */
const kpMatch = src.match(/var KEY_PATTERN=\/(.+)\/;/);
assert.ok(kpMatch, 'chooser 中未找到 KEY_PATTERN 定义');
assert.equal(kpMatch[1], tk.keyPattern, 'chooser KEY_PATTERN 与正本表 keyPattern 不一致');
pass('chooser KEY_PATTERN 与正本表 keyPattern 逐字一致');

/* ④ 正本表自洽：每个键自合 keyPattern（keyPattern 只约束形态——全小写连字符；
   aliases 是形态合法的「错误键名」登记，不参与形态断言，由检查脚本提示正确键名） */
const re = new RegExp(tk.keyPattern);
for (const k of tk.keys) {
  assert.ok(re.test(k.key), '正本键应自合 keyPattern: ' + k.key);
}
pass('正本表自洽：' + tk.keys.length + ' 键全部自合 keyPattern（aliases 为错误键名登记，不参与形态断言）');

function pass(s) { console.log('PASS', s); }
console.log('RESULT: token-keys.json ⇆ style-chooser.js 一致性 4/4 PASS');
