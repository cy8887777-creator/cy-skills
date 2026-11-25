import fs from 'node:fs';
const x = JSON.parse(fs.readFileSync('chain.json', 'utf8')).overview.component;
let idx = 0;
(x.match(/.{60} \+ .{60}/g) || []).forEach(m => { idx++; console.log(`-- 断裂 ${idx} --\n${m}\n`); });
console.log('== css-copy 相关 ==');
(x.match(/.{40}css-copy.{40}/g) || []).forEach(m => console.log(' ·', m));
console.log('== button 相关 ==');
(x.match(/.{30}button.{30}/g) || []).forEach(m => console.log(' ·', m));
