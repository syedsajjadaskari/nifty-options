import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const out = path.dirname(fileURLToPath(import.meta.url));
const payload = JSON.parse(await fs.readFile(path.join(out, 'workbook_data.json'), 'utf8'));
const wb = Workbook.create();
const sheets = {};
const titleFill = '#182D4B';

function col(n) {
  let s = '';
  for (let k = n; k > 0; k = Math.floor((k - 1) / 26)) s = String.fromCharCode(65 + (k - 1) % 26) + s;
  return s;
}

for (const spec of payload.sheets) {
  const sh = wb.worksheets.add(spec.name);
  sheets[spec.name] = sh;
  sh.showGridLines = false;
  sh.tabColor = spec.name === 'Overview' ? titleFill : '#58708D';
  const columns = spec.headers.length;
  const last = col(columns);
  const bodyEnd = spec.rows.length + 4;
  sh.getRange(`A1:${last}${bodyEnd}`).format.font = { name: 'Arial', size: 10, color: '#172333' };
  sh.getRange('A1').values = [[spec.title]];
  sh.getRange('A1').format.font = { name: 'Arial', size: 15, bold: true, color: titleFill };
  sh.getRange('A2').values = [[spec.subtitle]];
  sh.getRange('A2').format.font = { name: 'Arial', size: 10, italic: true, color: '#596575' };
  sh.getRange(`A4:${last}4`).values = [spec.headers];
  sh.getRange(`A4:${last}4`).format = { fill: titleFill, font: { name: 'Arial', size: 10, bold: true, color: '#ffffff' }, horizontalAlignment: 'center', verticalAlignment: 'center', wrapText: true, rowHeight: 38 };
  if (spec.rows.length) sh.getRange(`A5:${last}${bodyEnd}`).values = spec.rows;
  sh.getRange(`A5:${last}${bodyEnd}`).format.verticalAlignment = 'center';
  sh.getRange(`A5:${last}${bodyEnd}`).format.rowHeight = 34;
  for (let c = 0; c < columns; c++) {
    const cr = sh.getRange(`${col(c+1)}4:${col(c+1)}${bodyEnd}`);
    cr.format.columnWidth = spec.widths?.[c] ?? 22;
    cr.format.wrapText = true;
  }
  for (const c of spec.numericColumns ?? []) {
    sh.getRange(`${col(c+1)}5:${col(c+1)}${bodyEnd}`).setNumberFormat('0');
    sh.getRange(`${col(c+1)}5:${col(c+1)}${bodyEnd}`).format.horizontalAlignment = 'right';
  }
  for (const c of spec.dateColumns ?? []) {
    const values = spec.rows.map(r => [r[c] ? new Date(`${r[c]}T00:00:00Z`) : null]);
    sh.getRange(`${col(c+1)}5:${col(c+1)}${bodyEnd}`).values = values;
    sh.getRange(`${col(c+1)}5:${col(c+1)}${bodyEnd}`).setNumberFormat('yyyy-mm-dd');
  }
  for (let i = 0; i < spec.rows.length; i++) {
    const lines = Math.max(...spec.rows[i].map((v,c) => Math.ceil(String(v ?? '').length / ((spec.widths?.[c] ?? 22) * 1.05))));
    if (lines > 2) sh.getRange(`A${i+5}:${last}${i+5}`).format.rowHeight = 12 * lines + 12;
  }
  if (spec.name === 'Disputes') sh.getRange(`I5:M${bodyEnd}`).setNumberFormat('0.00');
  if (spec.name !== 'Overview') {
    sh.freezePanes.freezeRows(4);
    sh.freezePanes.freezeColumns(spec.name === 'Journal' ? 2 : 1);
  }
}

const ov = sheets.Overview;
const journalEnd = payload.sheets.find(s => s.name === 'Journal').rows.length + 4;
for (let i = 0; i < 3; i++) {
  const row = 5 + i;
  const cfg = String.fromCharCode(65 + i);
  // Journal: A config, B date, C session, D signal, E ORB fill, F IRF fill,
  // G other fill, H no trade, I signal/no ORB fill, J evaluable.
  const formulas = [
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$J$5:$J$${journalEnd},1)`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$D$5:$D$${journalEnd},1)`,
    `=B${row}-C${row}`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$E$5:$E$${journalEnd},1)`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$I$5:$I$${journalEnd},1)`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$F$5:$F$${journalEnd},1)`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$G$5:$G$${journalEnd},1)`,
    `=COUNTIFS(Journal!$A$5:$A$${journalEnd},A${row},Journal!$H$5:$H$${journalEnd},1)`,
  ];
  ov.getRange(`B${row}:I${row}`).formulas = [formulas];
  ov.getRange(`B${row}:I${row}`).setNumberFormat('0');
  const expected = payload.expected[cfg];
  const actual = ov.getRange(`B${row}:I${row}`).values[0];
  if (actual.some((v,k) => Number(v) !== expected[k])) throw new Error(`Summary mismatch ${cfg}: ${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
}
ov.getRange('A10').values = [['190 source rows | 89 ORB rows / unique dates | 85 evaluable sessions | 4 ORB Saturday dates have no session']];
ov.getRange('A12').values = [['Interpretation']];
ov.getRange('A12').format.font.bold = true;
ov.getRange('A13').values = [['No confirmed frozen ORB was bypassed for IRF on a journal-ORB date. This does not prove source fidelity.']];
ov.getRange('A14').values = [['Gap-open requirement conflicts with figures; numeric strength and inner/trendline construction remain provisional.']];
ov.getRange('A15').values = [['No new trades or P&L simulated. Manual direction / price / level remain unknown. A/B/C are separate configurations.']];
ov.getRange('A17').values = [['Checks']];
ov.getRange('A17').format.font.bold = true;
ov.getRange('A18:B23').values = payload.checks;
ov.getRange('A18:A23').format.columnWidth = 38;
ov.getRange('A18:B23').format.rowHeight = 30;
ov.getRange('A25').values = [['Source details and exact code lines: Sources. Full raw evidence and authority explanations: adjacent CSV and daily files.']];
ov.getRange('A13:I15').format.rowHeight = 26;
ov.getRange('B4:I4').format.columnWidth = 20;
ov.getRange('A4:A7').format.columnWidth = 38;

// Recalculation probe in memory; restore before export. A summary must react to
// changed evidence rather than merely display hardcoded verified totals.
const j = sheets.Journal;
const saved = j.getRange('D5').values[0][0];
const before = Number(ov.getRange('C5').values[0][0]);
j.getRange('D5').values = [[saved ? 0 : 1]];
const after = Number(ov.getRange('C5').values[0][0]);
if (after !== before + (saved ? -1 : 1)) throw new Error('COUNTIFS recalculation did not react');
j.getRange('D5').values = [[saved]];
if (Number(ov.getRange('C5').values[0][0]) !== before) throw new Error('Summary restore failed');

await fs.mkdir(path.join(out, 'workbook_previews'), { recursive: true });
for (const spec of payload.sheets) {
  const range = spec.name === 'Overview' ? 'A1:I25' : `A1:${col(Math.min(spec.headers.length, 7))}${Math.min(spec.rows.length+4, 10)}`;
  const preview = await wb.render({ sheetName: spec.name, range, scale: 1.3, format: 'png' });
  await fs.writeFile(path.join(out, 'workbook_previews', `${spec.name}.png`), new Uint8Array(await preview.arrayBuffer()));
}
for (const [name, range] of [['Chronology','H4:K8'],['Disputes','H4:N8']]) {
  const preview = await wb.render({ sheetName: name, range, scale: 1.3, format:'png' });
  await fs.writeFile(path.join(out,'workbook_previews',`${name}_detail.png`),new Uint8Array(await preview.arrayBuffer()));
}
const xlsx = await SpreadsheetFile.exportXlsx(wb);
await xlsx.save(path.join(out, 'ORB_Forensic_Verification.xlsx'));
await fs.writeFile(path.join(out, 'workbook_verification.json'), JSON.stringify({
  formula_counts_match_independent_summary: true,
  recalculation_probe_restored: true,
  sheets: payload.sheets.map(s => ({ name:s.name, rows:s.rows.length })),
  limitations: 'Analysis workbook; authority and manual direction are not inferred. Native Excel recalculation not separately opened.'
}, null, 2));
console.log('Workbook exported; formula counts and recalculation probe passed.');
