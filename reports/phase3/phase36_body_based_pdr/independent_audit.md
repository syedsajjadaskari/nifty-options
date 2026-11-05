# Phase 3.6 - independent audit

**Written for:** the strategy owner and any reviewer. The audit verifies that the code did what the written rules say and that nothing else changed; it does **not** verify the source rules (the pattern thresholds and zone conventions are provisional, and a misreading shared by the engine and the audit script would not be caught - the author of both is the same). Two independent checks were run: (1) `scripts/phase36_independent_audit.py`, a second implementation from the raw data, and (2) a fresh read-only reviewer subagent (an AI reviewer, not a human).

## 1. Independent re-implementation: `scripts/phase36_independent_audit.py`

Written from the raw one-minute parquet files and the delivered CSVs only; it imports nothing from `src/` (derived from the Phase 3.2 / 3.5 audits; the body-zone rebuild is new; the signal-stream function comes from the Phase 3.4 independent script, which is also free of `src/` imports).

| # | check | n | result |
|---|---|---|---|
| 1 | entry price equals the raw 1-minute bar open at the fill minute (all trades) | 196 | PASS |
| 2 | candle OHLC equals an independent 5-minute aggregation of the raw 1-minute rows | 755 | PASS |
| 3 | body %, wick %, direction, strong/pin/small flags equal an independent calculation | 755 | PASS |
| 4 | EMA(200) of 5-minute closes equals an independent causal recomputation (warm-up + data) | 755 | PASS |
| 5 | each candle is available at its own end time | 755 | PASS |
| 6 | no explanation candle is later than the signal confirmation | 755 | PASS |
| 7 | independent exit walk reproduces every trade's outcome, both exit times and prices, and the source-bar OHLC | 196 | PASS |
| 8 | leg P&L = (exit - entry) x direction x 195 per leg and the legs sum to the trade's gross P&L | 196 | PASS |
| 9 | independent total gross P&L (legs re-priced from the raw bars) equals the delivered ledger total | 196 | PASS |
| 10 | illustrative net = gross - Rs 500 - 0.5 point x 2 x 390 units on every trade | 196 | PASS |
| 11 | initial stop, Target 1, Target 2 and the post-T1 stop follow the approved distances | 196 | PASS |
| 12 | IRF IRH/IRL and RF High/Low equal the raw first 5-minute candle | 119 | PASS |
| 13 | PDR/PDS/RF/ORB-gap opening gap equals raw first open minus the official previous close | 56 | PASS |
| 14 | ORB Method 1 level equals the raw previous-session high/low and the first candle broke and closed beyond it | 27 | PASS |
| 15 | PDR zone equals the independent previous-day highest-BODY-high candle zone (body low .. body high, wicks ignored); PDS zone equals the independent lowest-low construction | 36 | PASS |
| 16 | every evaluable session has a journal; every executed trade is in its journal with a chart; no review status was auto-filled | 247 | PASS |
| 17 | every trade has a selection check (SEL-FIRST-001 or DAY-SL-001) | 196 | PASS |
| 18 | every second trade is a PDR/PDS signal confirmed after the first trade's original full stop | 8 | PASS |
| 19 | no executed trade has a failed entry condition or a recomputation mismatch | 196 | PASS |
| 20 | every trade has a setup explanation, a selection explanation and an exit narrative | 196 | PASS |
| 21 | workbook equals the CSV files cell by cell (all sheets, all rows) | 193542 | PASS |
| 22 | manual comparison: every match is same date, <=15 minutes, unique; matched + extra automated = executed trades; 190 journal rows all present | 190 | PASS |
| 23 | Phase 3.0 ledger files are byte-identical to the hashes frozen at the start of Phase 3.1 | 4 | PASS |
| 24 | the PDR signals fed to the controller equal an independent rebuild of the body-based rules (highest body high, open strictly above, three patterns, strict close) from the raw data | 87 | PASS |
| 25 | candidate B (multiple-body-high zone) rebuilt independently gives the same signals as candidate A (same ceiling by construction) | 87 | PASS |
| 26 | every executed PDR trade: signal in the independent rebuild, ceiling = previous-session highest BODY high (never above the wick high), open strictly above it, close strictly above it, patterns equal the explanation, entry = next 1-minute open | 25 | PASS |
| 27 | the confirmed signals of IRF, ORB, PDS and RF equal the Phase 3.5 export and the Phase 3.2 export row for row (date, time, method, direction, reference close) | 996 | PASS |
| 28 | the Phase 3.5 PDR stream (81) is still the wick-ceiling stream and differs from the body-based stream, which has a different count | 87 | PASS |
| 29 | all five engines contributed confirmed signals and executed trades | 5 | PASS |
| 30 | controller rules: first valid signal of the day, max 2 trades, fill <= 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing was valid (or a same-minute conflict) | 188 | PASS |
| 31 | strategy_performance.csv and the Phase 3.0 / 3.5 / 3.6 comparison equal an independent recomputation (trade counts, gross, illustrative net) from the three ledgers | 24 | PASS |
| 32 | monthly P&L (gross) of the three runs equals an independent recomputation | 12 | PASS |
| 33 | manual journal matching reproduced independently equals the delivered matches (same journal row -> same trade, same delta) | 88 | PASS |
| 34 | every trade id is unique and links to its chart and its daily-journal section | 196 | PASS |
| 35 | every data file, every earlier report (Phase 2.x - 3.5), every other engine, both earlier PDR engines, the controller and every other file of the before-snapshot is byte-identical (only the listed research modules / CLI changed) | 1983 | PASS |
| 36 | the five engines, the Phase 3.4 / 3.5 PDR engine, the controller, the selection rules and the parameter definitions are byte-identical | 11 | PASS |
| 37 | every file of the Phase 3.5 results directory is byte-identical to its pre-Phase-3.6 hash | 470 | PASS |

Overall: **ALL PASS** (37 checks); machine-readable in `independent_audit_results.json`.

## 2. Pre-existing files edited in Phase 3.6 (and nothing else)

A hash snapshot of 1983 files (source, tests, scripts, `data/`, `reports/` including every earlier phase, `docs/`) was recorded before the first edit (`before_snapshot.json`, git head `ed5642a`; the Phase 3.3 - 3.5 work was still uncommitted). The audit proves every file in it is byte-identical **except** these seven (the independent reviewer re-hashed all of them; it found only the documented ones changed):

| file | why it was edited |
|---|---|
| `src/nifty_trading/research/phase3.py` | `PDR_ENGINES` / `make_engines` / `combined_scenario` accept `BODY_BASED_PHASE36`; Phase 3.0 scenarios and the meaning of `REVISED_PHASE34` unchanged. |
| `src/nifty_trading/research/phase31.py` | the PDR diagnostic probe uses the body zone when the body engine is active. |
| `src/nifty_trading/research/phase32.py` | `explain_pdr_body` (the body-high calculation, wick shown as ignored), PDR-B rule statuses. |
| `src/nifty_trading/research/phase32_build.py` | phase / banner labels for Phase 3.6. |
| `src/nifty_trading/research/phase32_render.py` | one extra row in the daily-journal header for the body run: the previous-day highest BODY high (the PDR ceiling), next to the wick high. |
| `src/nifty_trading/research/phase32_excel.py` | Rule Definitions sheet lists the PDR-B rules / PDRBodyConfig for the body run. |
| `scripts/phase35_run.py` | new option `--pdr-engine body-based` (dispatches to `phase36`); `revised` and `legacy` unchanged; refuses to write Phase 3.6 results into a Phase 3.5 directory or any other `reports/` directory that is not a Phase 3.5 / 3.6 output. |

The allowed-edit list of the audit and of the snapshot test is exactly these seven files (an earlier draft also allowed `tests/test_phase35_combined.py`, which was not edited; the independent review pointed out that this weakened the guard, so it was removed).

The five engines (`irf`, `orb`, `pds`, `rf`, `pdr`), the Phase 3.4 / 3.5 engine `pdr_revised.py`, `trading_day.py`, `selection.py`, `exit_policy.py`, `params.py`, `definitions.py`, `base.py`, all data files and **every file of the Phase 3.0 - 3.5 result directories** are byte-identical to the snapshot.

## 3. Regression check of the framework

Phase 3.5's own command (`python scripts/phase35_run.py --pdr-engine revised`) and the legacy regression (`--pdr-engine legacy`) are re-run into scratch directories by the test suite / reviewer; the Phase 3.5 results directory is hash-identical (check above).

## 4. Tests and static checks

* `pytest -q`: **589 passed, 1 skipped (the superseded Phase 3.4 freeze test)**; `ruff check src tests scripts`: **All checks passed**.
* New: `tests/test_phase36_body_pdr.py` - raw wick ignored, highest body high, multiple body highs, isolated wick spike, isolated body high, body-high clusters and their parameters, boundaries, zero-height zones, open strictly above (at / inside / below / one tick above), the three alternatives, no fixed percentage labelled author-approved, close strictly above, wick penetration, no look-ahead, previous-session-only data, no duplicate signals, other-strategy streams unchanged (file-level), a one-time snapshot check honouring `PHASE36_ALLOW_LATER_EDITS=1`.

## 5. Not verified

* The author's intent for every `PROPOSED_FOR_REVIEW` / `OWNER_INTERPRETATION` item; whether the clarification supersedes the PDF's wick-topped example boxes.
* Example 5 of the guide (undated); the figures' candle prices beyond the Phase 3.3 readings.
* The controller's behaviour on same-minute conflicts (no approved tie-break), the provisional 15:14 forced exit (this run has 1 forced exit), PDR / PDS Target 2 (70 vs the report's 60) and RF's Target 2 (60) - unchanged from Phase 3.0.
* The workbook beyond cell-by-cell equality with the CSV files (not opened in desktop Excel).

## 6. Fresh reviewer (read-only subagent) - findings and what was done

A fresh AI reviewer, given only the repository and the task list of section 15 of the brief, re-read `pdr_body.py` line by line, ran a differential fuzz of 4,000 random sessions (681 signals; 0 differences from its own oracle), applied 68 mutants, rebuilt the PDR stream from the raw parquet files, re-simulated all 196 trades from the raw one-minute bars, recomputed the journal matching and the three-way tables, re-hashed all 1,983 snapshot files and re-ran Phase 3.5 and the legacy baseline in scratch directories. It modified nothing in the repository.

**Verdicts:** rules vs implementation PASS; independent rebuild PASS (87 of 87 signals, identical patterns); journal and comparison tables PASS (88 matches; Phase 3.0 / 3.5 / 3.6 totals and monthly P&L recompute exactly); nothing else changed PASS; mutation testing, source documents, honesty scan and design challenges CAVEAT. **No blocking (S1) finding; no wrong headline number.** A scratch re-run of `phase35.run("REVISED_PHASE34")` is byte-identical to the delivered Phase 3.5 directory; the legacy engine reproduces `phase35_legacy_check`; a scratch run of `phase36.run` reproduces the delivered files byte for byte. 192 of 196 trades re-simulate exactly; the other four differ only through the documented gap-through-stop rule (fill at the worse of the stop level and the bar open: slippage 0.45, 0.45, 3.45 and 0.05 points).

| # | finding | disposition |
|---|---|---|
| S2-1 | 35 of 87 signals (14 of 25 traded) fire after a candle had closed below the zone floor between the test and the confirmation; waits up to 44 candles; 22 signals use the 09:15 candle as the test; the wait policy was labelled PROPOSED but its prevalence was not stated. | **Disclosed, not changed** (changing the wait policy would be a new rule). New `pdr_signal_zone_state.csv`; statistics in the summary and in part 4 / 5 of `pdr_body_zone_rule_audit.md`; every trade explanation now carries a PDR-B07 row stating the state of the zone between test and confirmation. Owner decision listed. |
| S2-2 | The three new TARGET winners have the smallest open-above-ceiling margins (1.50, 1.75, 2.85 points); the vendor daily open would flip the open-above-zone test on 5 sessions (including 2025-12-31); the summary's caveat did not say so. | **Disclosed**: new `pdr_trade_open_margins.csv`; the summary section "What the PDR P&L swing rests on" states the margins, the vendor-open sensitivity and the trade-level decomposition. The original first-1-minute-open convention is kept (the brief requires it). |
| S2-3 | Example 5 of the guide appears to open inside the box (Phase 3.3 note, confirmed by the reviewer at 4x), which bears on the now author-approved strictly-above rule; the chart-validation file only said 'undated'. | **Added** to `pdr_source_chart_validation.md` as an unresolved point for the owner. |
| S3-1 | Stale "pending" text for pytest / ruff; "no forced exit occurred if the table shows 0" although there is one (20260821-1-PDR). | **Fixed**: real results are quoted; the forced-exit count is computed. |
| S3-2 | Section 2 listed eight edited files; only six differed from the snapshot at the time (and the allowed list of the test / audit contained two unedited files). | **Fixed**: the allowed list is now exactly the seven files actually edited (the seventh, `phase32_render.py`, was edited during the fixes below); the text says so. |
| S3-3 | PDR-012 row text was stale (said only the first signal is reported); PDR-B04x cited the Phase 3.4 rules as its source; PDR-B02 is AUTHOR_APPROVED but UNRESOLVED. | **Fixed** (PDR-012 name and text; PDR-B04x source). PDR-B02 stays UNRESOLVED on purpose (candidate A does not apply a multi-high zone; disclosed on the row). |
| S3-4 | Drawn-box precision stated as +/- 0.5 point (Phase 3.3: +/- 1); the boxes of Examples 1, 2 and 4 lie at or above the body and are almost disjoint from the body zone; only Example 3's CEILING is reproduced, not its floor. | **Fixed** in `pdr_source_chart_validation.md`. |
| S3-5 | The zone floor never affects signals; the summary described the hull of member bodies as the lower boundary although candidate A uses the anchor candle's body low; the gap-up condition is redundant in this data. | **Fixed**: wording corrected; part 5 of the zone-rule audit states plainly what does not affect the signals. |
| S3-6 | The `BODY_SPIKE_ABOVE_SHELF` flag fires for almost every session, so the 'spike excluded' diagnostic (67 signals) is meaningless. | **Disclosed** in the sensitivity file's note and in part 5 of the zone-rule audit; it never affects the active run. |
| S3-7 | '(better)' / '(worse)' labels on day changes; the daily-journal header showed only the wick high. | **Fixed**: neutral '(higher)' / '(lower)'; the daily journal now shows the previous-day highest BODY high (the ceiling) next to the wick high. |
| S3-8 | The lenient reconciliation (113 vs 87) was not given. | **Added** to `pdr_pattern_classification.md`. |
| S3-9 | The clarification was called both 'takes precedence' and 'to be confirmed'. | **Fixed**: one consistent wording (later statement per the brief; the owner should still confirm explicitly). |
| S3-10 | The default thresholds pass 0 of the author's 4 entry candles; not in the summary's limits. | **Added** to the summary. |
| S3-11 | The `--out` guard of `phase35_run.py` only refuses a fixed list of names. | **Tightened**: any `reports/` directory that is not a Phase 3.5 / 3.6 output is refused; `clean_generated` still asserts the name. |

**Test gaps (68 mutants: 48 killed by the Phase 3.6 test file, 7 more by other PDR test files, 13 real survivors, none changing the 87 signals):** body high from the close only; strict versus inclusive test-candle touch and the floor-side touch; the proximity setting; `patterns_enabled` and proximity not passed to the pattern functions; the CEILING_BELOW_WICK flag; and the shared threshold knobs (green-body minimum, hammer body position). **Added** seven tests covering each of them (`tests/test_phase36_body_pdr.py`, now 49 tests). Two survivors are equivalent or near-equivalent by the data (the gap-up check given the open-above-ceiling rule; the test-index guard that the loop already enforces).

**Not verified by the reviewer:** the author's intent for the PROPOSED / OWNER_INTERPRETATION items; the Excel workbook's contents in desktop Excel; the 'spike excluded' 67-signal diagnostic; Example 5 beyond visual inspection; the charts and the 247 daily journals beyond targeted samples.
