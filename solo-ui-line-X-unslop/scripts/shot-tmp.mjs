import { chromium } from 'playwright';
const b = await chromium.launch();
const jobs = [
  ['web.html','web-before-full.png',1440,900],
  ['mobile.html','mobile-before-full.png',390,844],
];
for (const [f,out,w,h] of jobs) {
  const pg = await b.newPage({viewport:{width:w,height:h}});
  await pg.goto('file:///C:/Users/admin/Desktop/design-style-wiki/dashboard/cards/harmonyos-design/demos/harmonyos-design-L-v2/'+f);
  await pg.waitForTimeout(2500);
  await pg.screenshot({path:'C:/Users/admin/Desktop/design-style-wiki/dashboard/cards/harmonyos-design/demos/harmonyos-design-L-v2/unslop/'+out, fullPage:true});
  await pg.close();
}
await b.close();
