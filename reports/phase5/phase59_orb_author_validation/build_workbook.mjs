import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook,SpreadsheetFile } from '@oai/artifact-tool';
const out=path.dirname(fileURLToPath(import.meta.url));
const data=JSON.parse(await fs.readFile(path.join(out,'workbook_data.json'),'utf8'));
const wb=Workbook.create(),sheets={};
const col=n=>{let s='';for(;n>0;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
for(const spec of data.sheets) {
  const sh=wb.worksheets.add(spec.name);sheets[spec.name]=sh;
  sh.showGridLines=false;sh.tabColor=spec.name==='CaseReview'?'#8A6120':'#183149';
  const last=col(spec.headers.length),end=spec.rows.length+4;
  sh.getRange(`A1:${last}${end}`).format.font={name:'Arial',size:10,color:'#24374A'};
  sh.getRange('A1').values=[[spec.title]];sh.getRange('A1').format.font={name:'Arial',size:15,bold:true,color:'#183149'};
  sh.getRange('A2').values=[[spec.subtitle]];sh.getRange('A2').format.font={name:'Arial',size:10,italic:true,color:'#5E6A75'};
  sh.getRange(`A4:${last}4`).values=[spec.headers];
  sh.getRange(`A5:${last}${end}`).values=spec.rows;
  if(spec.name==='CaseReview')sh.tables.add(`A4:${last}${end}`,true,'AuthorCases');
  sh.getRange(`A4:${last}4`).format={fill:'#183149',font:{name:'Arial',size:10,bold:true,color:'#ffffff'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:48};
  sh.getRange(`A5:${last}${end}`).format.verticalAlignment='top';
  sh.getRange(`A5:${last}${end}`).format.rowHeight=32;
  for(let c=0;c<spec.headers.length;c++) {
    sh.getRange(`${col(c+1)}4:${col(c+1)}${end}`).format.columnWidth=spec.widths[c];
    sh.getRange(`${col(c+1)}4:${col(c+1)}${end}`).format.wrapText=true;
  }
  for(let i=0;i<spec.rows.length;i++) {
    const lines=Math.max(...spec.rows[i].map((v,c)=>Math.ceil(String(v??'').length/(spec.widths[c]*1.05))));
    sh.getRange(`A${i+5}:${last}${i+5}`).format.rowHeight=Math.max(spec.name==='CaseReview'?108:32,lines*12+14);
  }
  for(const c of spec.dateColumns??[]) {
    sh.getRange(`${col(c+1)}5:${col(c+1)}${end}`).values=spec.rows.map(r=>[r[c]?new Date(`${r[c]}T00:00:00Z`):null]);
    sh.getRange(`${col(c+1)}5:${col(c+1)}${end}`).setNumberFormat('yyyy-mm-dd');
  }
  for(const c of spec.numericColumns??[])sh.getRange(`${col(c+1)}5:${col(c+1)}${end}`).setNumberFormat('0');
  if(spec.inputRange) {
    sh.getRange(spec.inputRange).format.fill='#FFF5D6';
    sh.getRange(spec.inputRange).format.font.color='#70531B';
  }
  if(spec.name!=='Overview'){sh.freezePanes.freezeRows(4);sh.freezePanes.freezeColumns(2);}
}
const c=sheets.CaseReview;
c.getRange('D5:D56').dataValidation={rule:{type:'list',values:['Method 1','Method 2','Gap setup','Other (cite PDF)']}};
c.getRange('E5:E56').dataValidation={rule:{type:'list',values:['BUY','SELL']}};
for(const column of ['J','K','L'])c.getRange(`${column}5:${column}56`).dataValidation={rule:{type:'list',values:['Yes','No','Unresolved']}};
c.getRange('G5:G56').setNumberFormat('0.00');
for(const column of ['H','I'])sheets.RuleQuestions.getRange(`${column}5:${column}10`).dataValidation={rule:{type:'list',values:['Yes','No','Unresolved']}};
sheets.IRFExecutions.getRange('E5:H38').setNumberFormat('#,##0.00');
sheets.IRFExecutions.getRange('J5:J38').setNumberFormat('#,##0.00');
sheets.IRFExecutions.getRange('L5:L38').setNumberFormat('#,##0.00');
const overview=sheets.Overview;
const formulas=[
 '=COUNTA(OriginalJournal!A5:A194)',
 '=COUNTIF(OriginalJournal!D5:D194,"ORB")',
 null,
 '=COUNTIFS(OriginalJournal!D5:D194,"ORB",OriginalJournal!E5:E194,1)',
 '=COUNTIFS(OriginalJournal!D5:D194,"ORB",OriginalJournal!F5:F194,1)',
 '=COUNTIFS(OriginalJournal!D5:D194,"ORB",OriginalJournal!G5:G194,1)',
 '=SUM(CaseReview!Y5:Y56)',
 '=COUNTIFS(OriginalJournal!D5:D194,"ORB",OriginalJournal!H5:H194,1)',
 '=SUM(CaseReview!Z5:Z56)',
 '=COUNTA(CaseReview!A5:A56)',
 '=SUM(CaseReview!AA5:AA56)',
];
for(let i=0;i<formulas.length;i++)if(formulas[i])overview.getRange(`B${5+i}`).formulas=[[formulas[i]]];
overview.getRange('A18:B20').values=[['Author case responses received',0],['Engineering approval Yes',0],['Cases awaiting author confirmation',52]];
overview.getRange('B18:B20').formulas=[['=COUNTA(CaseReview!J5:J56)'],['=COUNTIF(CaseReview!L5:L56,"Yes")'],['=B14-B18']];
overview.getRange('A18:B20').format.rowHeight=28;
overview.getRange('A22').values=[['Amber cells are blank author inputs. Confirming a trade does not approve engineering implementation.']];
overview.getRange('A24').values=[['Source: original workbook + fresh ORB reconstruction + existing A ledger. Full provenance: source_to_chart_traceability.csv.']];
overview.getRange('A26').values=[['52 unique cases = 50 missing dates + 13 handwritten dates - 11 overlaps. No author entries or approvals are inferred.']];
overview.getRange('A28').values=[['No trading rule, stop, target or portfolio policy is activated by this workbook. Await the returned annotated charts.']];
const expected=[190,89,89,85,35,35,50,34,13,52,5];
const actual=overview.getRange('B5:B15').values.flat().map(Number);
if(actual.some((v,i)=>v!==expected[i]))throw new Error(`Baseline formula mismatch ${JSON.stringify(actual)}`);
if(c.getRange('D5:L56').values.flat().some(v=>v!==null&&v!==''))throw new Error('Author fields were populated');
// Prove workflow counts react, while the separate approval remains blank/zero.
c.getRange('J5').values=[['Yes']];
if(Number(overview.getRange('B18').values[0][0])!==1||Number(overview.getRange('B19').values[0][0])!==0)throw new Error('Approval workflow not separated');
c.getRange('J5').values=[[null]];
if(Number(overview.getRange('B18').values[0][0])!==0)throw new Error('Response probe was not restored');
await fs.mkdir(path.join(out,'workbook_previews'),{recursive:true});
for(const [name,range] of [['Overview','A1:F28'],['CaseReview','A1:I7'],['CaseReview_approvals','I4:L7'],['OriginalJournal','A1:H10'],['IRFExecutions','A1:L9'],['RuleQuestions','A1:D7'],['RuleQuestions_inputs','G4:I7']]) {
  const sheetName=name.startsWith('CaseReview')?'CaseReview':name.startsWith('RuleQuestions')?'RuleQuestions':name;
  const preview=await wb.render({sheetName,range,scale:1.3,format:'png'});
  await fs.writeFile(path.join(out,'workbook_previews',name+'.png'),new Uint8Array(await preview.arrayBuffer()));
}
const file=await SpreadsheetFile.exportXlsx(wb);await file.save(path.join(out,'ORB_Author_Review.xlsx'));
await fs.writeFile(path.join(out,'workbook_checks.json'),JSON.stringify({baseline_formulas_match:true,author_fields_blank:true,workflow_probe_restored:true,approval_does_not_follow_trade_confirmation:true,sheets:data.sheets.map(s=>({name:s.name,rows:s.rows.length}))},null,2));
console.log('Author workbook exported; response fields blank and baseline/workflow checks pass.');
