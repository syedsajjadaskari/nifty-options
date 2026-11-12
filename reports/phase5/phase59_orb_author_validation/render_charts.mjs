import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import sharp from 'sharp';

const out=path.dirname(fileURLToPath(import.meta.url));
const payload=JSON.parse(await fs.readFile(path.join(out,'case_data.json'),'utf8'));
for (const file of (await fs.readdir(path.join(out,'author_review_charts'))).filter(x=>x.endsWith('.svg'))) {
  await sharp(path.join(out,'author_review_charts',file),{density:144})
    .resize({width:3400}).withMetadata({density:300}).png()
    .toFile(path.join(out,'author_review_charts',file.replace('.svg','.png')));
}
for (const [date,data] of Object.entries(payload)) {
  const folders=[];
  if(data.case.priority) folders.push('priority_five');
  else if(data.case.handwritten_dispute) folders.push('remaining_eight');
  if(data.case.missing_journal_orb) folders.push('all_missing_orb');
  for(const folder of folders) {
    const kinds=data.case.priority&&folder==='priority_five'?['overview','opening_1m','history_5m']:['overview'];
    for(const kind of kinds) for(const ext of ['svg','png']) {
      const name=`${date}_${kind}.${ext}`;
      await fs.copyFile(path.join(out,'author_review_charts',name),path.join(out,folder,name));
    }
  }
}
const reference=path.resolve(out,'../phase57_trade_visualization/charts_all/A_20251212-1-IRF.svg');
await sharp(reference).png().toFile(path.join(out,'source_reference','phase57_visual_reference.png'));
const hand=Object.entries(payload).filter(([,x])=>x.case.handwritten_dispute).map(([d])=>d);
const thumbnails=await Promise.all(hand.map(async(d,i)=>({input:await sharp(path.join(out,'author_review_charts',`${d}_overview.png`)).resize(600,375).png().toBuffer(),left:(i%2)*600,top:Math.floor(i/2)*375})));
await sharp({create:{width:1200,height:Math.ceil(hand.length/2)*375,channels:3,background:'#f0f2f5'}}).composite(thumbnails).png().toFile(path.join(out,'source_reference','all_13_chart_contact.png'));
console.log('62 high-resolution charts rendered; five/eight/fifty subsets populated.');
