# Phase 4 - independent audit

**Written for:** the strategy owner and any reviewer. The audit verifies that the code did what the written rules say, that the data are what the provenance says, and that nothing else changed. It does **not** verify the strategy rules, the derived calendar against NSE circulars, or either vendor's prices against the exchange. A misreading shared by the engine and the audit script would not be caught (one author wrote both). Two checks were run: (1) `scripts/phase4_independent_audit.py` (raw files and delivered CSVs only; no `src/` imports) and (2) a fresh read-only reviewer subagent (an AI reviewer).

## 1. Independent re-implementation

| # | check | n | result |
|---|---|---|---|
| 1 | every raw provider file equals the SHA-256 recorded at retrieval (5paisa responses; secondary files also equal the repository's git blob SHA-1) | 99 | PASS |
| 2 | every processed partition equals the SHA-256 in its source manifest | 140 | PASS |
| 3 | processed minute and daily data equal an independent reload of the raw files (timestamps and all four prices; the only difference is the 2-decimal rounding of the daily series' float32 noise) | 1062476 | PASS |
| 4 | the derived trading calendar equals an independent derivation from the raw daily and minute files (holidays and special sessions with their evaluable flag) | 130 | PASS |
| 5 | the calendar method reproduces the evidence-tier 2025-26 calendar (holidays and special sessions), independently | 16 | PASS |
| 6 | no trade falls on a derived holiday or on a non-evaluable special session | 939 | PASS |
| 7 | [B] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades) | 609 | PASS |
| 8 | [B] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 609 | PASS |
| 9 | [B] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances | 609 | PASS |
| 10 | [B] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (2383 candles with an EMA) | 2383 | PASS |
| 11 | [B] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 2383 | PASS |
| 12 | [B] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 565 | PASS |
| 13 | [B] all five strategies produced signals and were traded | 5 | PASS |
| 14 | [B] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 744 | PASS |
| 15 | [B] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them | 1401 | PASS |
| 16 | [B_TV] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades) | 601 | PASS |
| 17 | [B_TV] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 601 | PASS |
| 18 | [B_TV] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances | 601 | PASS |
| 19 | [B_TV] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (2358 candles with an EMA) | 2358 | PASS |
| 20 | [B_TV] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 2358 | PASS |
| 21 | [B_TV] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 557 | PASS |
| 22 | [B_TV] all five strategies produced signals and were traded | 5 | PASS |
| 23 | [B_TV] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 744 | PASS |
| 24 | [B_TV] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them | 1401 | PASS |
| 25 | [C] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades) | 185 | PASS |
| 26 | [C] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 185 | PASS |
| 27 | [C] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances | 185 | PASS |
| 28 | [C] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (725 candles with an EMA) | 725 | PASS |
| 29 | [C] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 725 | PASS |
| 30 | [C] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 180 | PASS |
| 31 | [C] all five strategies produced signals and were traded | 5 | PASS |
| 32 | [C] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 246 | PASS |
| 33 | [C] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them | 248 | PASS |
| 34 | [D_5P] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades) | 149 | PASS |
| 35 | [D_5P] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 149 | PASS |
| 36 | [D_5P] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances | 149 | PASS |
| 37 | [D_5P] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (565 candles with an EMA) | 577 | PASS |
| 38 | [D_5P] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 577 | PASS |
| 39 | [D_5P] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 145 | PASS |
| 40 | [D_5P] all five strategies produced signals and were traded | 5 | PASS |
| 41 | [D_5P] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 201 | PASS |
| 42 | [D_5P] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them | 537 | PASS |
| 43 | [D_TV] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades) | 182 | PASS |
| 44 | [D_TV] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit) | 182 | PASS |
| 45 | [D_TV] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances | 182 | PASS |
| 46 | [D_TV] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation (720 candles with an EMA) | 720 | PASS |
| 47 | [D_TV] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window | 720 | PASS |
| 48 | [D_TV] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict) | 177 | PASS |
| 49 | [D_TV] all five strategies produced signals and were traded | 5 | PASS |
| 50 | [D_TV] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table | 244 | PASS |
| 51 | [D_TV] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them | 494 | PASS |
| 52 | annual_comparison.csv equals an independent recomputation for every row (trades, gross, net, profit factor, drawdown, losing streak, win rate, outcomes, index points = gross / 390) | 12 | PASS |
| 53 | the three annual slices of Window B sum to the three-year window (trades, gross, net) | 4 | PASS |
| 54 | the Phase 3.6 reference row reproduces its reported results (196 trades, gross Rs 297,765, illustrative net Rs 123,325) | 1 | PASS |
| 55 | cost sensitivity (fill-level costs) recomputed independently for three periods x four scenarios; the Rs 500 / 0.5 point scenario equals the Phase 3.6 headline | 12 | PASS |
| 56 | every trade of every window records the minute-source id, daily-source id, partition SHA-256 (= the real file hash) and raw-file SHA-256; ids are unique; every trade has its chart and journal section; every session has a journal | 1726 | PASS |
| 57 | the workbook's main sheets equal the CSV files cell by cell | 61234 | PASS |
| 58 | the 2022-08..2025-08 vendor-overlap figures (bars compared, share identical, mean |close difference|) equal an independent recomputation | 284776 | PASS |
| 59 | every strategy, controller, execution and session-construction file equals the hash recorded in the freeze | 26 | PASS |
| 60 | the freeze's regression check regenerated the Phase 3.6 backtest and found every file identical | 466 | PASS |
| 61 | every file of the before-snapshot (data, every earlier report, engines, controller, scripts, tests, docs) is byte-identical except the three research modules edited for Phase 4 | 2474 | PASS |
| 62 | every file of the Phase 3.6 results directory is byte-identical to its pre-Phase-4 hash | 484 | PASS |
| 63 | the Phase 1 dataset and its metadata (data/processed, data/metadata) are byte-identical | 21 | PASS |

Overall: **ALL PASS** (63 checks); machine-readable in `independent_audit_results.json`.

## 2. Freeze, regression and preservation

* The source snapshot was taken at freeze time and already contains the Phase 4 edits to `phase32_build.py`, `phase32_render.py` and `phase32_excel.py` (they preserve default behaviour; proven by the regression run and by a test that rebuilds the Phase 3.6 backtest with the defaults). The pre-Phase-4 state is `before_snapshot.json`.
* The run guard checks EVERY file hashed in the freeze (26 files) and every parameter, not only the engine folders (a reviewer found the first version narrower than documented).
* Frozen configuration `FROZEN-PHASE36-42cea2600bd4` (git head `ed5642a`, 38 uncommitted files at freeze time; reproducible source snapshot `frozen/source_snapshot_phase36.tar.gz`, sha256 `a597b46a8673f852...`).
* Regression: the Phase 3.6 backtest was regenerated with the current code into a scratch directory and compared file by file with `reports/phase3/phase36_body_based_pdr/`: 466 files compared (all CSV / JSON files, all daily journals, all charts), identical = **True** (`data_provenance.json` is compared on its data hashes, because it also records a hash of the whole `src/` tree, which changes whenever a module is added).
* A hash snapshot of 2474 files (source, tests, scripts, `data/`, `reports/` of every earlier phase, `docs/`) was recorded before the first Phase 4 edit (`before_snapshot.json`). The audit proves every file in it is byte-identical except the research modules edited for this phase (listed in the audit check), so the Phase 3.0 - 3.6 reports, the Phase 1 dataset and every strategy engine are unchanged. New data live only in `data/raw/phase4_*` and `data/phase4/`.

## 3. Tests and static checks

* `pytest -q`: **612 passed, 1 skipped (full suite, pytest -q)**; `ruff check src tests scripts`: **ruff check src tests scripts: All checks passed**.
* New: `tests/test_phase4_multiyear.py` (freeze enforcement, CLI, calendar derivation, source namespaces and hashes, no-journal mode, metrics and cost model, regimes causality, workbook = CSV, trade source columns).

## 4. Not verified

* Either vendor's prices against the exchange; the derived holiday list against NSE circulars; the licence of the secondary dataset's underlying data; the historical NIFTY lot sizes (secondary reporting only).
* The strategies' source rules (unchanged and still partly provisional).
* The workbook beyond cell-by-cell equality with the CSV files (not opened in desktop Excel).

## Fresh independent reviewer

A reviewer with no prior context on this phase was given the master prompt, the repository (read-only) and the generated reports, and asked to attack the work: re-walk trades from raw minutes, check the freeze, check the claims in the documents against the CSV files, and look for look-ahead, silent merging and overstated conclusions.

**Verdict (first pass):** the numbers were reproduced; the *words* and a few guards needed correction. Re-walking all 1,726 trades from the processed minute files gave **zero mismatches** in entry, exit, outcome and P&L. The reviewer found no look-ahead, no vendor mixing inside a run and no change to a strategy file. The findings below concern disclosure, guard strength and wording. Every one was acted on; none was dismissed.

| # | Finding | Disposition |
|---|---|---|
| F1 | Fixed-point stops/targets are not scaled to the index level (index ~2.3x lower in 2018-19), so years are not like-for-like | New section 11 in `robustness_report.md` (scale table: stop as % of index, forced-exit share, holding time); caveat added to the 2018, 2019 and readiness text. Nothing rescaled (that would be a rule change) |
| F2 | The statement "secondary first open equals the 5paisa daily open in 99% of sessions" was true only for 2022-25 | Replaced by a table for every window incl. Window A; the relationship reverses in 2019; which convention matches the exchange is stated as not established |
| F3 | Coverage text quoted whole-window numbers under per-slice rows | Coverage is now per period row (sessions of that slice only) |
| F4 | `DATA_VALIDATED` could be read as "strategy validated" | Defined in README, three-year summary and workbook README: data quality gate only |
| F5 | Run guard checked fewer files than documented | `verify_freeze()` checks every file hashed in the freeze and every parameter; tamper tests added for framework files |
| F6 | Strategy-share column misleading when the window gross is not positive | Shown as "n/m" |
| F7 | Data-quality diagnostic counted dropped sessions instead of the predeclared issues | Rebuilt: missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle; trades and gross on issue vs other sessions |
| F8 | PDR's loss over the three years was not stated in the summary | Stated with per-year numbers; IRF is the main source of profit; PDR+PDS offset IRF in 2023-24 |
| F9 | The same-minute conflict rule (no approved tie-break) was not quantified | Conflict-day counts per year added to the three-year summary |
| F10 | Overlap percentages were rounded in a way that hid a one-tick case | Rounding fixed, one-tick test added |
| F11 | Calendar-method validation is partly circular | Disclosed; derived dates also not compared with NSE circulars |
| F12 | "Seven years" wording | Replaced by "six distinct years" (2018, 2019 appears in two vendor runs, 2022-23, 2023-24, 2024-25, Window A) |
| F13 | float32 wording: the noise is in the DAILY candles, not the minute responses | Corrected |
| F14 | README of the secondary vendor says nothing on 2018-19 cleaning; Muhurat bars kept as exception | Added to data source discovery |
| F15 | 2018-07-09 labelled as a special session | Reworded: a normal Monday with a missing 09:15 bar, excluded by the gate |
| F16 | 2020-2021 minute data not retrieved: vendor gaps looked like holidays | Coverage notes say each source is only expected inside the years retrieved |
| F17 | Source snapshot already contains the (behaviour-preserving) Phase 4 edits to three framework files | Stated in the audit; pre-Phase-4 state is `before_snapshot.json`; a test rebuilds Phase 3.6 with the defaults |
| F18 | Windows B and B_TV are not on identical session sets | Disclosed (2023-10-19 excluded in B only) |
| F19 | `RiskLimits` note in the readiness text | Added: its Rs 10,000 daily loss limit is below the strategy's own single-trade loss (Rs 13,650) |
| F20 | Probe file path in the docs was relative to the wrong directory | Fixed |
| F21 | Test/ruff results were placeholders | Real results recorded below |

**Limits the reviewer could not remove:** the quality of the 2018 secondary-vendor data cannot be checked against any other source; which vendor's 09:15 bar is the exchange's is unknown; the result at 390 fixed units says nothing about what was executable historically.
