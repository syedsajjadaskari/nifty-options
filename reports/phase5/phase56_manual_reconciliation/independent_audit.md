# Independent audit (Phase 5.6)

`scripts/phase56_independent_audit.py` re-reads the original workbook, re-implements the one-to-one matching and re-derives the ORB evidence from the raw candles (no `src/` imports). Result: **ALL 28 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | journal workbook re-read: 190 data rows (ids 1..190), Summary sheet says 189, 89 ORB rows, outcomes Target 81 / SL 65 / BE 44, five weekend-dated rows (all Saturdays), 19 time objects, five dates with two rows, none with more | 190 | PASS | {'IRF': 73, 'PDR': 8, 'ORB': 89, 'RF': 17, 'PDS': 3} {'BE': 44, 'Target': 81, 'SL': 65} weekend=[(23, '2025-10-11'), (82, '2026-02-14'), (181, '2026-0 |
| 2 | the journal workbook is byte-identical to the Phase 5.5 baseline snapshot | 1 | PASS |  |
| 3 | the state file's journal facts equal the recount | 1 | PASS |  |
| 4 | the five weekend-dated rows have NO one-minute data on those dates (not exchange sessions); every weekday journal date is a session of the dataset | 190 | PASS |  |
| 5 | configuration A: the independent staged one-to-one matching reproduces every delivered pair (stage, trade, time difference) | 105 | PASS | strict 66 / tolerant 21 / date+strategy only 18; state 66 / 21 / 18 |
| 6 | configuration A: one-to-one - every journal row appears exactly once, no trade is used by two journal rows, every executed trade is either in a strict / time-tolerant pair or in the automated-only table (never both; date-and-strategy-only trades are listed in the automated-only table too) | 281 | PASS |  |
| 7 | configuration A: every pair has the same date and strategy, the stage agrees with the time difference, and the descriptive outcome-class flag is recomputed correctly | 281 | PASS |  |
| 8 | configuration A: outcome-class agreement among strict + time-tolerant pairs recounted | 87 | PASS | 80/87 |
| 9 | configuration B: the independent staged one-to-one matching reproduces every delivered pair (stage, trade, time difference) | 95 | PASS | strict 64 / tolerant 14 / date+strategy only 17; state 64 / 14 / 17 |
| 10 | configuration B: one-to-one - every journal row appears exactly once, no trade is used by two journal rows, every executed trade is either in a strict / time-tolerant pair or in the automated-only table (never both; date-and-strategy-only trades are listed in the automated-only table too) | 283 | PASS |  |
| 11 | configuration B: every pair has the same date and strategy, the stage agrees with the time difference, and the descriptive outcome-class flag is recomputed correctly | 283 | PASS |  |
| 12 | configuration B: outcome-class agreement among strict + time-tolerant pairs recounted | 78 | PASS | 71/78 |
| 13 | configuration C: the independent staged one-to-one matching reproduces every delivered pair (stage, trade, time difference) | 98 | PASS | strict 67 / tolerant 14 / date+strategy only 17; state 67 / 14 / 17 |
| 14 | configuration C: one-to-one - every journal row appears exactly once, no trade is used by two journal rows, every executed trade is either in a strict / time-tolerant pair or in the automated-only table (never both; date-and-strategy-only trades are listed in the automated-only table too) | 282 | PASS |  |
| 15 | configuration C: every pair has the same date and strategy, the stage agrees with the time difference, and the descriptive outcome-class flag is recomputed correctly | 282 | PASS |  |
| 16 | configuration C: outcome-class agreement among strict + time-tolerant pairs recounted | 81 | PASS | 74/81 |
| 17 | the weekend rows are never matched, keep their original dates, carry the weekend flag and the cause MANUAL_JOURNAL_INCONSISTENCY in all three configurations | 15 | PASS |  |
| 18 | every delivered journal row equals the original workbook row (date, label, strategy, outcome): nothing was altered, relabelled or invented | 846 | PASS |  |
| 19 | every classified mismatch uses only the specified root-cause vocabulary and carries evidence text | 673 | PASS |  |
| 20 | the classified-mismatch table covers every manual row without a strict / time-tolerant match, every matched pair with a different exit class and every automated-only trade | 673 | PASS | expected {'A': 219, 'B': 229, 'C': 225} got {'A': 219, 'B': 229, 'C': 225} |
| 21 | manual_only / automated_only table sizes equal the state counts per configuration | 6 | PASS |  |
| 22 | ORB evidence: the first 09:15 candle (colour, open, high, low, close) and the previous-day high quoted in every manual-only ORB explanation equal the values recomputed from the raw one-minute data | 147 | PASS | 42 previous-day highs checked |
| 23 | dates on which the journal and the automated system traded only DIFFERENT strategies (no weekday journal strategy of the date appears among its automated trades) recounted per configuration | 3 | PASS | delivered {'A': 57, 'B': 57, 'C': 56}; independent count {'A': 57, 'B': 57, 'C': 56} |
| 24 | weekday journal rows on sessions with NO automated trade recounted per configuration (equals the state field; all of them are unmatched) | 3 | PASS | independent {'A': 19, 'B': 29, 'C': 27}; state {'A': 19, 'B': 29, 'C': 27} |
| 25 | second trades without a journal counterpart are explained as controller re-entries after a full stop (never as first valid signals) | 31 | PASS |  |
| 26 | 247 session explanations and the charts exist; each chart is a well-formed SVG | 247 | PASS | 143 charts |
| 27 | the Phase 5.6 deliverables exist (independent_audit.md is written after this audit) | 16 | PASS |  |
| 28 | every file of the Phase 5.5 baseline snapshot is still byte-identical (journal, candles, source code, earlier reports) | 15340 | PASS |  |

**Independence caveat.** The audit script is a second implementation written in the same session; the fresh reviewer below is a separate pass.

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

