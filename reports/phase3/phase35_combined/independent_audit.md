# Phase 3.5 - independent audit

**Written for:** the strategy owner and any reviewer who must decide whether the combined backtest can be trusted. The audit verifies that the code did what the written rules say and that nothing else changed; it does **not** verify the source rules (the PDR thresholds and the open-above-zone requirement are provisional research assumptions, and a misreading of a rule shared by the engine and the audit would not be caught - the author of both is the same).

## 1. Independent re-implementation: `scripts/phase35_independent_audit.py`

Written from the raw one-minute parquet files and the delivered CSVs only; it imports nothing from `src/` (the signal-stream rebuild reuses the Phase 3.4 independent script, which is also free of `src/` imports). It is derived from the Phase 3.2 audit with the legacy-PDR checks replaced by the revised-PDR ones.

| # | check | n | result |
|---|---|---|---|
| 1 | entry price equals the raw 1-minute bar open at the fill minute (all trades) | 198 | PASS |
| 2 | candle OHLC equals an independent 5-minute aggregation of the raw 1-minute rows | 739 | PASS |
| 3 | body %, wick %, direction, strong/pin/small flags equal an independent calculation | 739 | PASS |
| 4 | EMA(200) of 5-minute closes equals an independent causal recomputation (warm-up + data) | 739 | PASS |
| 5 | each candle is available at its own end time | 739 | PASS |
| 6 | no explanation candle is later than the signal confirmation | 739 | PASS |
| 7 | independent exit walk reproduces every trade's outcome, both exit times and prices, and the source-bar OHLC | 198 | PASS |
| 8 | leg P&L = (exit - entry) x direction x 195 per leg and the legs sum to the trade's gross P&L | 198 | PASS |
| 9 | independent total gross P&L (legs re-priced from the raw bars) equals the delivered ledger total | 198 | PASS |
| 10 | illustrative net = gross - Rs 500 - 0.5 point x 2 x 390 units on every trade | 198 | PASS |
| 11 | initial stop, Target 1, Target 2 and the post-T1 stop follow the approved distances | 198 | PASS |
| 12 | IRF IRH/IRL and RF High/Low equal the raw first 5-minute candle | 121 | PASS |
| 13 | PDR/PDS/RF/ORB-gap opening gap equals raw first open minus the official previous close | 56 | PASS |
| 14 | ORB Method 1 level equals the raw previous-session high/low and the first candle broke and closed beyond it | 27 | PASS |
| 15 | PDR zone equals the independent previous-day-high candle zone (body top .. wick high); PDS zone equals the independent lowest-low construction | 36 | PASS |
| 16 | every evaluable session has a journal; every executed trade is in its journal with a chart; no review status was auto-filled | 247 | PASS |
| 17 | every trade has a selection check (SEL-FIRST-001 or DAY-SL-001) | 198 | PASS |
| 18 | every second trade is a PDR/PDS signal confirmed after the first trade's original full stop | 10 | PASS |
| 19 | no executed trade has a failed entry condition or a recomputation mismatch | 198 | PASS |
| 20 | every trade has a setup explanation, a selection explanation and an exit narrative | 198 | PASS |
| 21 | workbook equals the CSV files cell by cell (all sheets, all rows) | 193304 | PASS |
| 22 | manual comparison: every match is same date, <=15 minutes, unique; matched + extra automated = executed trades; 190 journal rows all present | 190 | PASS |
| 23 | Phase 3.0 ledger files are byte-identical to the hashes frozen at the start of Phase 3.1 | 4 | PASS |
| 24 | the PDR signals fed to the controller equal an independent rebuild of the Phase 3.4 rules (candidate A, provisional thresholds) from the raw data | 81 | PASS |
| 25 | every executed PDR trade: signal in the independent rebuild, close strictly above the zone ceiling, open above it, patterns equal the explanation, entry = next 1-minute open | 25 | PASS |
| 26 | the confirmed signals of IRF, ORB, PDS and RF equal the Phase 3.2 export row for row (date, time, method, direction, reference close) | 996 | PASS |
| 27 | all five engines contributed confirmed signals and executed trades | 5 | PASS |
| 28 | controller rules: first valid signal of the day, max 2 trades, fill <= 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing was valid (or a same-minute conflict) | 188 | PASS |
| 29 | strategy_performance.csv and the Phase 3.0 comparison equal an independent recomputation (trade counts, gross, illustrative net) from the two ledgers | 12 | PASS |
| 30 | manual journal matching reproduced independently equals the delivered matches (same journal row -> same trade, same delta) | 89 | PASS |
| 31 | every data file, earlier report, other engine, the controller, selection, exit policy, parameters and every other file of the before-snapshot is byte-identical (only the listed research modules changed) | 1028 | PASS |
| 32 | the five engines (incl. the revised PDR), the controller, the selection rules and the parameter definitions are byte-identical | 11 | PASS |

Overall: **ALL PASS** (32 checks). Results are machine-readable in `independent_audit_results.json`.

## 2. Pre-existing files edited in Phase 3.5 (and nothing else)

A hash snapshot of 1028 files (source, tests, scripts, `data/`, `reports/`, `docs/`) was recorded before the first edit (`before_snapshot.json`, git head `ed5642a`). The audit proves every file in it is byte-identical **except** these seven:

| file | why it was edited |
|---|---|
| `src/nifty_trading/research/phase3.py` | `Scenario` gained `pdr_engine` / `pdr_revision` (defaults keep the legacy behaviour); `make_engines` selects the PDR engine; `combined_scenario()` added. The four Phase 3.0 scenarios are unchanged. |
| `src/nifty_trading/research/phase31.py` | `run_timelines` passes the selection; the PDR diagnostic probe uses the revised zone when the revised engine is active. |
| `src/nifty_trading/research/phase32.py` | explainer for revised PDR trades (`explain_pdr_revised`), status labels of the PDR-A rules, `config_id` accepts a PDR revision. |
| `src/nifty_trading/research/phase32_build.py` | `build(scenario=...)`; the frozen-ledger comparison ignores the scenario *label* column. |
| `src/nifty_trading/research/phase32_render.py`, `phase32_excel.py` | phase / banner labels from the bundle (Phase 3.2 defaults unchanged); revision rules in the Rule Definitions sheet; Excel cell-length cap. |
| `tests/test_phase34_pdr_revision.py` | the broad Phase 3.4 freeze test is skipped once the Phase 3.5 snapshot exists (superseded by `tests/test_phase35_combined.py`). |

The five engines (including `pdr.py` and `pdr_revised.py`), `trading_day.py`, `selection.py`, `exit_policy.py`, `params.py`, `definitions.py` and `base.py` are byte-identical to the snapshot; all data files and every earlier report (Phase 2.x - 3.4) are byte-identical.

## 3. Regression check of the framework

`python scripts/phase35_run.py --pdr-engine legacy` re-runs the Phase 3.0 baseline through the modified framework: 213 trades, gross Rs 172,146, 67 exact + 17 time-shifted journal matches, **zero field differences** against the frozen `reports/phase3/baseline/trades.csv` (output in `reports/phase3/phase35_legacy_check/`). The Phase 3.2 tests, which rebuild the baseline bundle, also still pass.

## 4. Defects found while building this run, and what was done

| finding | disposition |
|---|---|
| The frozen-ledger comparison flagged every row because the scenario label column differs by construction (`baseline` vs `phase35_*`). | Fixed: the label column is excluded; every numeric, time and outcome field is still compared. |
| Four PDR signals have `reference_levels` text longer than Excel's 32,767-character cell limit (long armed sessions list every evaluated candle); an over-long cell can make Excel report a corrupt file. | Fixed: the workbook cell is cut with a visible marker `...[TRUNCATED IN EXCEL - full text in the CSV file]`; the CSV keeps the full text; the audit compares accordingly; a test checks no cell exceeds the limit. |
| The legacy check 'the zone is an area with positive height' fails for candidate A when the previous-day-high candle closes on its high (zone from body top to wick high has zero height): 1 executed PDR trade(s) (20260826-1-PDR). | Reported as UNRESOLVED (the author gave no rule for a zero-height zone), not as a failure; covered by a test. The engine treats such a zone as a line (touched when a candle's range includes the price) - unchanged from Phase 3.4. |
| The explainer's rule-source lookup raised on the disclosure row `PDR-A04x`. | Fixed (default text); found by the first full run, before any output was accepted. |

## 5. Tests and static checks

* `pytest -q`: **540 passed, 1 skipped (the superseded Phase 3.4 freeze test)**; `ruff check src tests scripts`: **All checks passed**.
* New: `tests/test_phase35_combined.py` (engine selection swaps only the PDR slot; the combined scenario changes nothing but the PDR engine; the Phase 3.0 scenario set is unchanged; the command line; the revised-PDR explanation including the zero-height zone; the Excel limit; the delivered bundle obeys the portfolio rules, adds up and labels the PDR assumptions as provisional; a one-time hash-snapshot check that honours `PHASE35_ALLOW_LATER_EDITS=1`).

## 6. Not verified

* The strategy author's intent for every `PROPOSED_FOR_REVIEW` / `OWNER_INTERPRETATION` item (pattern numbers, open-above-zone, zone floor, 'strictly above').
* The PDR / PDS Target 2 of 70 versus the performance report's 60 (a recorded source conflict), RF's Target 2 of 60 (research assumption) and the provisional 15:14 forced exit - all unchanged from Phase 3.0; no forced exit occurred in this run.
* How the two same-minute-conflict days should have been resolved: no tie-break is approved, so nothing was traded on them.
* The workbook beyond a cell-by-cell equality with the CSV files (formatting and the opening in Excel itself were not tested on a desktop Excel).
* The independent audit did not re-derive the entry signals of IRF, ORB, PDS and RF from raw data (their engines are unchanged and their signal streams are identical to the Phase 3.2 export, 996 / 996; the entry numbers of the executed trades were recomputed in the Phase 3.2 audit method).
