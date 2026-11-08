# Independent audit (Phase 5.7)

`scripts/phase57_independent_audit.py` parses every rendered SVG (visible text, `data-*` attributes, embedded metadata and the geometry of the lines and markers) and compares it with the ledgers and the Phase 5.6 files; it recomputes the match counts with the independent staged matcher of `phase56_independent_audit.py` from the original journal workbook (no `src/` imports). Result: **ALL 16 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | charts_all holds exactly one chart per executed trade of A, B and C, named <configuration>_<trade id>.svg (574 trades) | 574 | PASS |  |
| 2 | every chart parses as well-formed SVG | 574 | PASS |  |
| 3 | every chart's embedded data equals the ledger / config: entry price and time, initial stop, T1, T2, post-T1 stop (present only when T1 was booked), exits (leg, reason, time, price), outcome, gross P&L, strategy, method, direction | 574 | PASS |  |
| 4 | every VISIBLE label equals the ledger: 'ENTRY hh:mm @ price', 'SL @', 'T1 @', 'T2 @', 'POST-T1 STOP @' (only after T1), and each leg / full / forced exit label with its time and price | 574 | PASS |  |
| 5 | every drawn price line and marker (entry, SL, T1, T2, post-T1 stop, exits) sits at the vertical position that its price has on the chart's own scale | 4120 | PASS |  |
| 6 | every chart's header names the trade, the configuration and the match status | 574 | PASS |  |
| 7 | the exact / time-tolerant / date-and-strategy-only / automated-only counts shown on the charts equal the Phase 5.6 reconciliation AND the independent staged matcher recomputed from the original journal workbook | 3 | PASS | A: strict 66 / tolerant 21 / date-only 18 / automated-only 91; B: strict 64 / tolerant 14 / date-only 17 / automated-only 93; C: strict 67 / |
| 8 | exact_match_summary.csv equals the Phase 5.6 state file (counts, outcome agreement, strict by strategy, both percentages) | 3 | PASS |  |
| 9 | every subset folder (exact, time-tolerant, automated-only, date-and-strategy-only, ORB focus, handwritten dates, configuration differences) holds exactly the trades its definition selects, byte-identical to charts_all | 8 | PASS |  |
| 10 | folder sizes: exact = strict total, time-tolerant = tolerant total, automated-only = Phase 5.6 automated-only total, date-only = date-and-strategy total | 4 | PASS | {'charts_all': 574, 'charts_exact_matches': 197, 'charts_time_tolerant': 49, 'charts_automated_only': 276, 'charts_date_strategy_only': 52,  |
| 11 | a journal-day chart exists for every ORB journal date without a counted match (weekend rows excluded; they have no market data) | 50 | PASS |  |
| 12 | the visual index lists all 574 trades with an existing chart file and the same match-status counts as the charts | 574 | PASS |  |
| 13 | the verification workbook's trade sheet equals the ledger (entry, stop, T1, T2, both exits, reasons, gross P&L, exit class) and links to an existing chart | 574 | PASS |  |
| 14 | the 'Exact matches only' sheet has exactly the strict matches of A + B + C | 197 | PASS |  |
| 15 | every file of the Phase 3.6, 5.5 and 5.6 report folders is byte-identical to its hash recorded before the first Phase 5.7 write (no earlier chart, ledger or report was overwritten) | 1225 | PASS |  |
| 16 | no tracked file is modified or deleted (git status shows only new files; nothing committed) | 50 | PASS |  |

**The audit can fail.** A deliberate corruption of one chart (a changed label price and a moved line) made three checks fail (visible label, price geometry, byte-identity of the subset copy); the chart was then restored and the audit passes again.

**Visual inspection.** Eight charts covering a T1-then-post-T1-stop trade, a full stop, a forced exit, a T2 trade, a second trade, a gap-slippage stop, an automated-only trade and a journal-day chart were rendered in a browser and read for overlaps and wrong labels; the badge width, the clipped zone name and the cut-off entry-price note found that way were fixed.

**Independence caveat.** The audit script is a second implementation written in the same session as the charts; it shares no code with the chart generator other than the independent matcher of the Phase 5.6 audit.

## Tests and lint

* Full suite: **781 passed, 1 skipped, 1 xfailed for the whole working tree (the xfail and 8 of the tests belong to a separate, uncommitted Phase 5.8 test file, not to Phase 5.7); the 11 Phase 5.7 tests pass**
* `ruff check src tests scripts`: **All checks passed**

## What this phase did not do

No backtest, no rule change, no change to the journal matching, no regeneration of earlier ledgers; no paper or live order; nothing committed or pushed.
