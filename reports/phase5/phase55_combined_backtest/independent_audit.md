# Independent audit (Phase 5.5)

`scripts/phase55_independent_audit.py` recomputes the backtest from the RAW one-minute candles and the delivered signal tables (no `src/` imports). Result: **ALL 27 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | the frozen configuration id FROZEN-PHASE36-42cea2600bd4 is recomputed from the stored hashes / parameters / costs and all 26 active implementation files match their frozen hashes | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |
| 2 | the three configurations carry distinct identifiers (A = the frozen id; B and C are new hashes over the frozen files, the Phase 5 candidate files, the parameters and the provisional assumptions) | 3 | PASS | {'A': 'FROZEN-PHASE36-42cea2600bd4', 'B': 'PHASE55-B-a3ca4d04dd11', 'C': 'PHASE55-C-144ceb6b28b1'} |
| 3 | every file of the Phase 5.5 baseline snapshot (source code, one-minute data, the manual journal, the source PDFs, Phase 3.0-5.4 reports) is byte-identical; only declared Phase 5.5 / 5.6 files were added | 15340 | PASS |  |
| 4 | the original manual journal workbook is unchanged (hash equals the manifest and the baseline snapshot) | 1 | PASS |  |
| 5 | every confirmed signal of A, B and C: the signal candle exists in the raw data, its close equals the reference close, the signal time is the candle's END (never before it completed) on the 5-minute grid and not before 09:20 | 3304 | PASS |  |
| 6 | signal totals: A = 1,083 (874 / 53 / 87 / 57 / 12), B = 1,109 (786 / 53 / 147 / 111 / 12), C = B plus exactly three ORB signals | 3304 | PASS | {'A': 1083, 'B': 1109, 'C': 1112} |
| 7 | no duplicate signal (same configuration, date, time, strategy, method, direction) | 3304 | PASS |  |
| 8 | configuration A's signals equal the delivered Phase 3.6 table and B's equal the delivered Phase 5.3 author-corrected signal table (two earlier, separately audited deliverables); C = B plus three ORB Gap / 200DMA signals | 1112 | PASS |  |
| 9 | every IRF signal of B and C has >= 28 points between the signal candle's high-low range and its own EMA(200) (independent EMA; inclusive boundary) | 1572 | PASS |  |
| 10 | the three ORB signals added by configuration C each satisfy the candle-crossing reading (previous close on the wrong side of its EMA, open NOT beyond the average, candle reaches it and closes beyond, strong candle) and fail the frozen open-beyond reading | 3 | PASS |  |
| 11 | configuration A: the independently re-implemented controller selects exactly the same trades (date, trade number, strategy, direction, entry time) as the backtest | 196 | PASS |  |
| 12 | configuration A: every entry price (= the raw one-minute open at the signal candle's end), both exit prices, the exit class, the gross P&L and the five cost-scenario net P&Ls equal an independent recomputation from the raw candles | 196 | PASS |  |
| 13 | configuration B: the independently re-implemented controller selects exactly the same trades (date, trade number, strategy, direction, entry time) as the backtest | 188 | PASS |  |
| 14 | configuration B: every entry price (= the raw one-minute open at the signal candle's end), both exit prices, the exit class, the gross P&L and the five cost-scenario net P&Ls equal an independent recomputation from the raw candles | 188 | PASS |  |
| 15 | configuration C: the independently re-implemented controller selects exactly the same trades (date, trade number, strategy, direction, entry time) as the backtest | 190 | PASS |  |
| 16 | configuration C: every entry price (= the raw one-minute open at the signal candle's end), both exit prices, the exit class, the gross P&L and the five cost-scenario net P&Ls equal an independent recomputation from the raw candles | 190 | PASS |  |
| 17 | every simulated entry is the open of the raw one-minute bar that starts when the signal candle completed (no past price, no invented price) and no entry is later than 13:00 | 574 | PASS |  |
| 18 | every trade carries the approved position rules: stop 30 (ORB) / 35, Target 1 = 27, Target 2 = 60 (IRF, ORB, RF) / 70 (PDR, PDS), post-T1 stop entry -/+ 6, 6 lots = 390 units in two legs of 195, a second trade only PDR / PDS | 574 | PASS |  |
| 19 | at most two trades per day; a second trade exists only after the first trade's ORIGINAL full stop and its entry is after the first position closed | 540 | PASS |  |
| 20 | intrabar ambiguity audit: the set of trades with a same-minute stop / target conflict recomputed from the raw bars equals the delivered list (and the number of outcomes that depend on the ordering convention is reported) | 0 | PASS | 0 ambiguous trades; the delivered list has 0 |
| 21 | the cost-sensitivity table (net P&L, win rate, profit factor, maximum drawdown for the five scenarios A-E) equals an independent recomputation for A, B and C | 15 | PASS |  |
| 22 | strategy-wise results (trades, gross P&L, T1 / T2 hits, full stops, post-T1 stops, forced exits) equal an independent recomputation for every strategy of A, B and C | 15 | PASS |  |
| 23 | slippage units: the entry slippage applies to the 390 entry units once and the exit slippage to each exited leg once (390 units when both legs exit, 195 for a single exit; nothing is charged twice) - checked on every trade | 574 | PASS |  |
| 24 | robustness window 2022-09-01..2025-08-31 (A, B, C): every trade's entry, exit class, gross P&L and Rs 70 net P&L equals an independent recomputation from the Phase 4 one-minute partitions | 1808 | PASS |  |
| 25 | the frozen configuration A reproduces the delivered Phase 4 window-B backtest (609 trades, identical gross P&L) | 609 | PASS |  |
| 26 | the old Rs 500 fixed-cost columns are not carried into the Phase 5.5 trade tables | 80 | PASS |  |
| 27 | every required Phase 5.5 deliverable exists | 17 | PASS |  |

**Independence caveat.** The audit script is a second implementation written in the same session as the pipeline; the fresh reviewer below is a separate pass.

## Tests and lint

* Before any change (existing suite): **737 passed, 1 skipped**.
* After implementation: **762 passed, 1 skipped (the existing suite had 737 passed, 1 skipped; 25 tests were added for Phases 5.5 / 5.6)**
* `ruff check src tests scripts`: **All checks passed**

## Independent fresh-reviewer pass (Phase 5.5 + 5.6)

A fresh read-only reviewer re-computed the work from the raw candles. **No CRITICAL defect.** All 574 trades of A / B / C and all 1,808 robustness-window trades were recomputed (entry, exits, P&L, stop / T1 / T2 / post-T1 logic) with 0 mismatches; an independent controller selected exactly 196 / 188 / 190 trades; the report figures, cost scenarios, matching totals (one-to-one, 190 journal rows per configuration, date-only pairs never counted as matches, Saturday rows kept and flagged) and the baseline preservation (0 changed, 0 removed files) were confirmed.

Findings and disposition:

| # | finding | disposition |
|---|---|---|
| M1 | the claim "every weekday journal date has an automated trade" was false (19 / 29 / 27 rows in A / B / C are on sessions with no automated trade); the state field was always 0 because a lookup inserted empty days | FIXED (plain dict, state recomputed, sentence replaced by the real counts, new independent audit check and test) |
| M2 | stale "FAILURES PRESENT" / "pending" / "not recorded" text and a README line that said Phase 5.5 passed without reading the audit | FIXED (docs -> audit -> docs order; README derives the status from the audit result; real test / ruff results filled in) |
| M3 | second trades and rows already matched were described as "first valid signal" selections | FIXED (second trades are explained as controller re-entries after a full stop; only unmatched journal rows are compared); new audit check |
| M4 | RF opening-gap rejections were classified as UNRESOLVED_DISCRETIONARY_SELECTION | FIXED (OPENING_GAP_MISMATCH, RF-004; the unresolved wording no longer asserts a discretionary reading) |
| M5 | ORB primary cause decided by method order among ties, with a spurious gap secondary cause | FIXED (ties are flagged TIE-BROKEN in the evidence, the other tied cause is the secondary cause, counts of tie-broken rows are reported; the split is described as indicative) |
| minor | far-away signals labelled LATER / EARLIER (for example +210 minutes) | FIXED (more than 60 minutes: classified by why the engine has no signal near the manual entry, with the nearest signal quoted) |
| minor | controller table omitted MERGED_SAME_STRATEGY_METHOD; same-minute-group wording; exits in the entry minute described as stops only; "ranking" wording; tied days in the largest-difference table | FIXED in the generated text |
| minor | chart legend entry never drawn; docstring said "signal candle's end" | FIXED |
| minor | greedy matcher is not max-cardinality | DOCUMENTED (an exhaustive per-date assignment gives identical counts for A / B / C); no change to the matcher |
| minor | tautological / weak tests (fill >= signal time, factory type check, test name) | FIXED (second trade enters after the first exits; exact engine types pinned; names corrected; tolerant-stage test added) |
| minor | display rounding of two gross figures (662.95 shown as 663.0) | NOT CHANGED (display only; the CSVs hold the exact values) |
| minor | one A trade fills exactly at 13:00 (20260406-1-PDR) | NOTED: the cutoff is inclusive as in the frozen rule ENTRY-CUTOFF-001 |
| minor | the matcher is outcome-blind, so a journal 'BE' can pair with an automated full stop and be counted EXIT_MANAGEMENT_MISMATCH (for example PDR 2026-06-05 in B / C) | NOTED: by design (outcomes never choose pairs); the exit comparison is descriptive |

