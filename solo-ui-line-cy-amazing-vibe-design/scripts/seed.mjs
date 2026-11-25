#!/usr/bin/env node
/**
 * 逃离均值 · 种子生成与方向解读脚本（Node ≥ 18，零依赖）
 *
 * 用法：
 *   node seed.mjs                  生成 1 个 32 位种子并输出解读
 *   node seed.mjs --count 4        并行发散：一次生成 4 个种子
 *   node seed.mjs --seed k7Qa9Z…   解读已有种子（复现）
 *   node seed.mjs --length 48      指定长度（8–64）
 *   node seed.mjs --json           以 JSON 输出，便于代理解析
 *
 * 解读规则与 references/direction-catalog.md 第 1 节、交互式案例完全一致。
 * 种子只用于激发灵感，不得出现在设计中。
 */
import { webcrypto } from 'node:crypto';

const ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
const HARMONY = ['单色', '互补', '类似色', '三分色', '分裂互补'];
const HARMONY_OFFSET = [0, 180, 32, 120, 150];
const ARCHETYPE = ['编辑大标题', '不对称网格', '中心海报', '目录索引', '便当网格', '终端打印', '横向色带'];
const TYPEFACE = ['衬线展示', '怪诞无衬线', '等宽', '窄体', '圆体'];
const RADIUS = ['直角 0', '微圆 4px', '圆润 12px', '胶囊'];
const MOTIF = ['网格线', '点阵', '巨型数字', '斜纹', '正圆', '票据齿孔', '等高线', '套准十字'];
const VOICE = ['冷静克制', '俏皮', '宣言式', '技术精确'];
const DOSE = ['点缀', '适中', '大胆色块'];

function parseArgs(argv) {
  const args = { count: 1, length: 32, json: false, seed: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--json') args.json = true;
    else if (a === '--count') args.count = Math.max(1, Math.min(12, Number(argv[++i]) || 1));
    else if (a === '--length') args.length = Math.max(8, Math.min(64, Number(argv[++i]) || 32));
    else if (a === '--seed') args.seed = String(argv[++i] ?? '');
    else if (a === '--help' || a === '-h') args.help = true;
  }
  return args;
}

/** 来自系统熵源的随机串：这才是“外部随机性”。 */
export function generateSeed(length = 32) {
  const buf = new Uint32Array(length);
  webcrypto.getRandomValues(buf);
  return Array.from(buf, (n) => ALPHABET[n % ALPHABET.length]).join('');
}

function fnv1a(str) {
  let h = 0x811c9dc5;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return h >>> 0;
}

const isDigit = (c) => c >= '0' && c <= '9';
const isUpper = (c) => c >= 'A' && c <= 'Z';
const isLower = (c) => c >= 'a' && c <= 'z';
const classOf = (c) => (isDigit(c) ? 'd' : isUpper(c) ? 'u' : 'l');
const indexOf = (c) => Math.max(0, ALPHABET.indexOf(c ?? 'A'));

function isPrime(n) {
  if (n < 2) return false;
  for (let i = 2; i * i <= n; i++) if (n % i === 0) return false;
  return true;
}

function findPalindrome(s) {
  for (let len = Math.min(7, s.length); len >= 3; len--) {
    for (let i = 0; i + len <= s.length; i++) {
      const sub = s.slice(i, i + len);
      if (sub === [...sub].reverse().join('')) return sub;
    }
  }
  return null;
}

export function validateSeed(seed) {
  return /^[A-Za-z0-9]{8,64}$/.test(seed);
}

export function deriveDirection(seed) {
  const chars = [...seed];
  const sum = chars.reduce((a, c) => a + c.charCodeAt(0), 0);
  const hue = sum % 360;
  const digits = chars.filter(isDigit);
  const upper = chars.filter(isUpper).length;
  const lower = chars.filter(isLower).length;
  const harmonyIdx = digits.length % 5;
  const first = chars[0];
  const last = chars[chars.length - 1];
  const archetypeIdx = indexOf(first) % 7;
  const typeIdx = indexOf(last) % 5;
  const vowels = chars.filter((c) => 'aeiouAEIOU'.includes(c)).length;
  let radiusIdx = vowels % 4;
  const firstDigit = chars.findIndex(isDigit);
  const density = firstDigit === -1 || firstDigit >= 20 ? '疏朗' : firstDigit <= 7 ? '紧凑' : '均衡';
  const sub = seed.slice(8, 16);
  const motifIdx = fnv1a(sub) % 8;
  let flips = 0;
  for (let i = 1; i < chars.length; i++) if (classOf(chars[i]) !== classOf(chars[i - 1])) flips++;
  const digitSum = digits.reduce((a, d) => a + Number(d), 0);
  const palindrome = findPalindrome(seed);
  const twist = palindrome ? '镜像布局' : isPrime(digitSum) ? '竖排书脊' : '无';

  const judgments = [];
  let body = TYPEFACE[typeIdx];
  if (archetypeIdx === 5) {
    body = '等宽';
    judgments.push('终端打印版式下，正文统一为等宽字体');
    if (radiusIdx === 3) {
      radiusIdx = 0;
      judgments.push('胶囊圆角与终端美学冲突，改为直角');
    }
  }

  const readings = [
    { 维度: '主色相', 子模式: `全部字符编码之和 ${sum} → mod 360`, 取值: `${hue}°` },
    { 维度: '配色关系', 子模式: `数字字符 ${digits.length} 个 → mod 5 = ${harmonyIdx}`, 取值: HARMONY[harmonyIdx] },
    { 维度: '明度基调', 子模式: `大写 ${upper} / 小写 ${lower}`, 取值: upper >= lower ? '暗调' : '亮调' },
    { 维度: '版式原型', 子模式: `首字符「${first}」位序 ${indexOf(first)} → mod 7 = ${archetypeIdx}`, 取值: ARCHETYPE[archetypeIdx] },
    { 维度: '字体气质', 子模式: `末字符「${last}」位序 ${indexOf(last)} → mod 5 = ${typeIdx}`, 取值: TYPEFACE[typeIdx] },
    { 维度: '圆角', 子模式: `元音字母 ${vowels} 个 → mod 4 = ${vowels % 4}`, 取值: RADIUS[radiusIdx] },
    { 维度: '密度', 子模式: firstDigit === -1 ? '没有数字' : `首个数字位于第 ${firstDigit + 1} 位`, 取值: density },
    { 维度: '母题', 子模式: `第 9–16 位「${sub}」哈希 mod 8 = ${motifIdx}`, 取值: MOTIF[motifIdx] },
    { 维度: '文案语气', 子模式: `字符类别切换 ${flips} 次 → mod 4 = ${flips % 4}`, 取值: VOICE[flips % 4] },
    { 维度: '强调剂量', 子模式: `数字之和 ${digitSum} → mod 3 = ${digitSum % 3}`, 取值: DOSE[digitSum % 3] },
    {
      维度: '特殊模式',
      子模式: palindrome ? `回文子串「${palindrome}」` : isPrime(digitSum) ? `数字之和 ${digitSum} 是质数` : '未发现',
      取值: twist,
    },
  ];

  return {
    seed,
    summary: `${upper >= lower ? '暗调' : '亮调'}${HARMONY[harmonyIdx]} · ${ARCHETYPE[archetypeIdx]} · ${TYPEFACE[typeIdx]}`,
    accentHue: (hue + HARMONY_OFFSET[harmonyIdx]) % 360,
    bodyTypeface: body,
    readings,
    judgments,
  };
}

function printHuman(d) {
  console.log(`\n种子  ${d.seed}`);
  console.log(`方向  ${d.summary}`);
  console.log('─'.repeat(56));
  for (const r of d.readings) console.log(`${r.维度.padEnd(5, '　')}  ${r.取值.padEnd(8, '　')}  ← ${r.子模式}`);
  if (d.judgments.length) {
    console.log('─'.repeat(56));
    for (const j of d.judgments) console.log(`判断修正：${j}`);
  }
  console.log('\n提示：种子只用于灵感，不要让它出现在设计中。');
}

const isMain = process.argv[1] && import.meta.url.endsWith(process.argv[1].replace(/\\/g, '/').split('/').pop());

if (isMain) {
  const args = parseArgs(process.argv.slice(2));
  if (args.help) {
    console.log('用法：node seed.mjs [--count N] [--length 8-64] [--seed STRING] [--json]');
    process.exit(0);
  }
  if (args.seed !== null && !validateSeed(args.seed)) {
    console.error('种子必须是 8–64 位字母或数字。');
    process.exit(1);
  }
  const seeds = args.seed ? [args.seed] : Array.from({ length: args.count }, () => generateSeed(args.length));
  const results = seeds.map(deriveDirection);
  if (args.json) console.log(JSON.stringify(results.length === 1 ? results[0] : results, null, 2));
  else results.forEach(printHuman);
}
