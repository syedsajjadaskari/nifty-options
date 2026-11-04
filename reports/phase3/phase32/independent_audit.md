# Phase 3.2 - independent audit

Two independent reviews, both read-only on the repository:

1. **A numeric audit** - `scripts/phase32_audit.py`. It imports **nothing** from `nifty_trading`: it rebuilds the 5-minute candles, the EMA(200), the candle geometry, swing highs/lows, the exit walk and the P&L from the raw parquet files and compares them with the delivered files. Results: `independent_audit_results.json`.
2. **A QA review by a fresh reviewer** (no part in writing the code): 35 trades sampled with a fixed seed (one per strategy x method x outcome plus second trades) plus all 213 re-checked numerically, 13 daily journals read, 10 charts rendered and viewed, the workbook inspected with openpyxl, 20 mutation tests run on a scratch copy of the code, and the PDF page citations checked.

## 1. Numeric audit (all 213 trades, every candle row, every workbook cell)

| check | n | result |
|---|---|---|
| entry price = open of the raw 1-minute bar at the fill minute; signal confirmation = fill minute; no fill after 13:00 | 213 | PASS |
| candle OHLC = independent 5-minute aggregation of the raw 1-minute rows | 824 | PASS |
| body %, wick %, direction, strong-bullish/bearish, pin-bar, small-candle flags = independent calculation | 824 | PASS |
| EMA(200) of 5-minute closes = independent causal recomputation (warm-up + data, SMA seed) | 824 | PASS |
| each candle is available at its own end; no candle later than the signal confirmation; previous-session candles belong to an earlier date | 824 | PASS |
| independent exit walk reproduces outcome, both exit times and prices, and each source bar's OHLC | 213 | PASS |
| leg P&L = (exit - entry) x direction x 195 and the legs sum to the trade's gross P&L | 213 | PASS |
| total gross P&L = the frozen Phase 3.0 ledger (Rs 172,146.00) | 213 | PASS |
| initial stop, T1, T2 and the post-T1 stop follow the approved distances | 213 | PASS |
| IRF IRH/IRL and RF High/Low = the raw first 5-minute candle | 107 | PASS |
| PDR/PDS/RF/ORB-gap opening gap = raw first open - official previous close | 80 | PASS |
| ORB Method 1 level = raw previous-session high/low and the first candle broke and closed beyond it | 27 | PASS |
| PDR/PDS zone = an independent swing-high (k=2, red follower) / lowest-low construction | 65 | PASS |
| every session has a journal; every trade is in its journal with a chart; no review status auto-filled | 247 | PASS |
| every trade has a selection check; every second trade is a PDR/PDS signal after the first trade's original full stop | 213 / 16 | PASS |
| no executed trade has a failed entry condition or a recomputation mismatch against the engine's record | 213 | PASS |
| workbook = CSV files, cell by cell, all sheets | 212,012 cells | PASS |
| manual comparison: every match same date, <= 15 minutes, unique; 84 + 129 = 213; all 190 journal rows present | 190 | PASS |
| Phase 3.0 ledger files byte-identical to the hashes frozen before Phase 3.1 | 4 | PASS |

Coverage of strategies x outcomes in the exit audit: IRF 47 stop / 27 T1+stop / 28 target; ORB 14 / 12 / 15; PDR 20 / 23 / 11; PDS 3 / 2 / 6; RF 3 / 1 / 1. The real ledger contains no same-minute stop/target ambiguity, no forced exit and no unresolved exit, so those paths are covered by synthetic tests only (`tests/test_phase32_explanations.py`, `tests/test_phase23_*`).

**An audit finding worth recording.** The first run of the EMA check failed from 2025-10-23 on, because the auditor's EMA series included the one-hour Diwali Muhurat session (2025-10-21), which the engine correctly excludes as a non-standard session. After restricting the independent series to standard sessions (those opening at 09:15 with a near-full day of rows; the only session excluded is 2025-10-21) all 824 EMA values agree. The engine was right; the first auditor assumption was wrong.

## 2. QA reviewer's findings and what was done

No blocking finding; every number was reproduced. All issues were wording, labelling, disclosure or test strength.

| # | finding | disposition |
|---|---|---|
| S2-1 | README/summary pointed to this file, which did not exist; the 2025-10-23 journal showed truncated raw codes and never said "Muhurat" | **Fixed:** this file; the journal now prints the full reason and explains the excluded Muhurat session; truncation of codes removed everywhere |
| S2-2 | 11 ORB trades passed only through the pin-bar alternative but the setup text read like a strong candle (3 on an opposite-colour candle; one at exactly 2.00 x body) | **Fixed:** the setup text states that the strong-candle test failed and the pin route was used, with the ratio, close position, colour note and any exact-threshold pass; `source_fidelity = PIN_BAR_ROUTE_USED` |
| S2-3 | IRF Method 2 text mixed candle-end and candle-start labels; "held above for a while" was unconditional | **Fixed:** every candle is named by its start-end range; the hold wording is conditional on the closes actually observed |
| S2-4 | IRF-M2B-002 / IRF-M2-005 shown PASS although the engine relaxes (single-candle push) or tightens (red before break) the guide's wording | **Fixed in a way that keeps the required result vocabulary:** the result stays PASS/FAIL/..., and a new `source_fidelity` column says `ENGINE_RELAXES_SOURCE` / `ENGINE_STRICTER_THAN_SOURCE`; counted in the summary (7 Method 2B trades; all 16 Method 2A) |
| S2-5 | PDR zone provenance weaker than it looked (41 of 54 zones are not the previous day's high; 23 interaction candles closed below the floor; Example 3 not reproduced) | **Fixed:** `source_fidelity` flags on PDR-002/PDR-006, a setup-text sentence ("traded through the zone ... BELOW its floor"), and a summary section. The audit's zone check validates the engine's research definition, not the author's drawn zone - stated in the summary |
| S2-6 | trend-filter PASS conflicts with the guides' "EMA is never the sole proof" | **Fixed:** `source_fidelity = EMA_ONLY_PROXY` on the trend checks; 36 trades counted in the summary |
| S2-7 | the guide's 35-or-40 rule would pick 40 on 35 IRF and 4 PDS trades; only shown in a NOT_APPLICABLE row | **Fixed:** flag `SOURCE_RULE_WOULD_SELECT_40` and the counts in the summary |
| S2-8 | no numbers for invalidated setups on no-trade days; truncated text; the 2026-07-13 conflict day flagged NO_TRADE_BOTH; "PDR PDR LONG" | **Mostly fixed:** truncation removed, triage now flags all four unresolved-conflict days (and the summary says four days were lost), headings fixed. **Not done:** per-condition numbers for non-executed setups (disclosed in the summary and README: only reason codes and failed rule ids are exported for them) |
| S2-9 | "why this strategy over the other four" was thin | **Fixed:** the selection explanation now states what each of the other four engines had recorded at that moment (confirmed signals, invalidated setups with their reasons, or no setup record) |
| S2-10 | tests did not guard upper-wick %, the short-side P&L sign, rule/definition status mapping, the cutoff and first-signal FAIL paths, the T1 text, MFE | **Fixed:** six tests added (42 in the file); the surviving mutations are now caught. Mutations of the build/render/Excel/chart modules are still covered only by the delivered-output tests and by this audit script |
| S3 | PDR-008/PDS-TGT-001 conflict only in text; `rule_status` column name misleading; IRF-GLOBAL-005 rule/check mismatch; RF-010 wording; sign confusion; no glossary; float noise; "stop rules differ"; Method 3 not mentioned; Sunday session; win-rate definition; chart labels/clipping/markers; Excel links | **Fixed:** `source_fidelity` on the targets; README explains `rule_status` + `definition_status` + `source_fidelity` and carries a glossary; disclosure renamed `NOTE-IRF-REPEATED-SETUPS`; RF-010 reworded; signs corrected; values rounded to 6 decimals; "may differ"; Method 3 in the summary (37 rejected setups, no confirmed signal); weekend special session flagged; win rate defined; chart labels readable, candle roles marked, label clipping removed; chart and journal links in the trades sheet. **Left as is:** the trendline of ORB Method 2 is not drawn (its two points are in the candle table); colour rules cover the key result columns only; booleans and dates are text in Excel so they sort and filter identically to the CSVs |

## 3. Software state

`ruff` clean; full suite **455 passed** (413 before Phase 3.2 + 42 new). The Phase 3.0 ledgers are unchanged (hash check above, and the baseline re-run is identical field by field).

## 4. Not verified by anyone (limits)

* The trigger logic of IRF Methods 2A/2B, the PDR interaction/green-candle sequence, PDS Methods 1-3, ORB Method 2 and the Gap setup was re-derived independently only for the base conditions listed above (levels, zones, gaps, candle geometry, EMA) and, by the QA reviewer, for IRF Method 1 (62 of 62), ORB Method 1 (27 of 27) and RF (5 of 5); the rest rests on the engines' own state machines, the causality tests of Phase 3.0 and the consistency of the explanation with them.
* The explanation layer recomputes with the engines' own definition functions; the independent audit covers geometry, EMA, levels and exits but not the strong/pin **thresholds themselves** (they are the proposals).
* PDF figure pages (images) were not re-read for this phase; the quoted source wording was checked against the text layer.
* The workbook was inspected with openpyxl, not in Excel itself.
* Phase 3.1 match classes (84 / 129 / 106) were re-verified arithmetically and are identical to Phase 3.1; they were not re-derived by a third implementation.
