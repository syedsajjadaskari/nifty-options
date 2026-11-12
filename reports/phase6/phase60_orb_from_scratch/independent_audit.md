# Independent audit (Phase 6.0)

## 1. Second implementation vs the engine

`audit.py` re-derives every session of both windows without calling the engine's logic: candles by pandas `resample`, EMA by `ewm`, swing points by vectorised comparisons, wick tests by cross-multiplication, the trade on NumPy arrays. It shares only the raw one-minute frame, the usable-session list and the official closes with the engine (shared assumptions are listed in section 5).

| window|config | sessions_checked | signal_mismatches | failed_condition_set_mismatches | trade_mismatches |
|---|---|---|---|---|
| A/ORB-V2-A | 247 | 0 | 0 | 0 |
| A/ORB-V2-B | 247 | 0 | 0 | 0 |
| A/ORB-V2-C | 247 | 0 | 0 | 0 |
| A/ORB-V2-D | 247 | 0 | 0 | 0 |
| A/DIAG-A-OLDSIDE | 247 | 0 | 0 | 0 |
| B/ORB-V2-A | 738 | 0 | 0 | 0 |
| B/ORB-V2-B | 738 | 0 | 0 | 0 |
| B/ORB-V2-C | 738 | 0 | 0 | 0 |
| B/ORB-V2-D | 738 | 0 | 0 | 0 |
| B/DIAG-A-OLDSIDE | 738 | 0 | 0 | 0 |


**Totals: 4925 session evaluations, 0 signal mismatches, 0 failed-condition mismatches, 0 trade mismatches** (entry, exit reason, gross points).

Also: 5 x 400 random synthetic sessions agree (property test), and a mutation test (audit given a 40% wick limit) disagrees with the engine, so the comparison can fail.

## 2. EMA(200) cross-checks

Against the repository's reference recursion (`data.sessions.causal_ema`, SMA-seeded) over the full chain, ignoring the first 600 candles (seed transient):

| window | candles | compared_after_600_candles | max_abs_diff_incl_warmup | candles_in_evaluated_window | max_abs_diff_in_evaluated_window | mean_abs_diff_in_evaluated_window | opening_candle_emas_checked |
|---|---|---|---|---|---|---|---|
| A | 21674 | 21074 | 0.034283 | 18525 | 0.0 | 0.0 | 247 |
| B | 56835 | 56235 | 0.238764 | 55338 | 3e-05 | 6e-08 | 738 |


Against the TradingView/FYERS labels in the rulebook screenshots (15 Sep 11:45, 17 Sep 13:25, 23 Sep 14:50): -0.05, -0.03 and -0.24 points (5paisa feed); +0.00, 0.00, -0.10 (secondary feed).

## 3. Charts and journal

* Chart annotations: 133 of 133 trade charts carry the ledger's entry, stop, target and exit labels exactly (failures: none).
* Journal recount straight from the workbook with pandas: 190 rows, 89 ORB rows, 89 unique ORB dates; strict-timing recount for V2-A = 38 (reported 38).

## 4. Fresh read-only reviewer

A fresh read-only subagent (no prior context) reviewed the package, tests, outputs and README. Its report is summarised here with the disposition of each finding. No high-severity defect and no look-ahead were found.

**What the reviewer verified independently:** no look-ahead in the signal path (it also rebuilt the chain after scaling every price from 09:20 on for two dates: that day's decision and EMA were unchanged to 9 decimals and earlier days were unchanged); all 39 primary-window ORB-V2-A trades re-derived from raw one-minute bars by its own simulator (entry, stop, target, exit time/price/reason, gross points all matched, including a gap-through-stop and an entry-bar stop); the 3 forced exits of the 2022-25 window; eight no-signal sessions checked by hand; profit factor, drawdown, losing streak, the cost grid and per-year figures recomputed exactly; its own third implementation reproduced all 39 signals; 20+ README numbers checked correct.

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | medium | A third of ORB-V2-A trades rest on provisional pattern conventions (primary window: 13 trades with no full-body match net -120.0 pts; 26 with a full-body match net +206.6 pts); "written-rule reference" overstates it | ACCEPTED. Config title changed; the pattern-route split is now reported in `candle_pattern_validation.md`, `README.md` and the standalone summary |
| 2 | medium | "Level filter nearly non-binding" follows from the provisional inner-level construction (about 8 levels per side; MAJOR_ONLY never occurs) | ACCEPTED. Wording now attributes it to the construction and states that a major-only reading would be far more selective |
| 3 | medium | The no-look-ahead test was vacuous; `data_access` untested; dead assertion; no tests for drawdown / swing ties / journal reader | ACCEPTED and fixed: the engine is now given an object that raises on any intraday access; a synthetic three-session test exercises `data_access` causality (scaling post-09:20 prices on one day changes neither that day's opening candle / EMA / decision nor earlier days); drawdown, swing-tie, short-series and journal-reader tests added (53 tests) |
| 4 | low-medium | All 89 journal labels are 09:15, so "strict" = date + strategy; the 29/29 outcome agreement was unreported; "strongly consistent" is a relative-rate claim (51 of 85 dates are still not reproduced) | ACCEPTED. Reported in `manual_orb_reconciliation.md` and the README with the caveats; header-only CSVs for the empty classes |
| 5 | low | Entry convention described too mildly ("up to the tick"); measured mean 0.9 / max 3.0 pts (2025-26), mean 1.1 / max 6.75 (2022-25) | ACCEPTED. Docstring corrected; OD-7 already disclosed the maximum |
| 6 | low | Gap uses the vendor official close, but the rule is labelled EXPLICIT; using the last chart close flips the gap decision on 2 sessions with no effect on signals | ACCEPTED. New decision OD-15; ORB-R24 text amended |
| 7 | low | The secondary-feed run pairs secondary minutes with 5paisa official daily closes although the docstring said feeds are never mixed | ACCEPTED. Docstring and provenance now state it (affects gap values only) |
| 8 | low | Session usability uses whole-day data (1 session in window A, 5 in window B dropped by events after 09:20: selection, not signal leakage); `ema_prev` included frozen auction candles while `prev_ema_last` did not | PARTLY: `ema_prev` now uses continuous candles like `prev_ema_last` (label-only effect, auction days); the whole-day usability rule is the repository's verified Phase 2 policy and is listed under the audit limits |
| 9 | low | Lint errors, empty `test_results.md`, a hedged inference stated as fact in the examples report | ACCEPTED. ruff clean repo-wide; test/lint logs are now embedded; the 17 Sep statement is hedged |

**Independence caveat (accepted, stated in section 5):** the audit implementation shares the input frames, the usable-session list and every declared interpretation (fractal tie rule, zone edges, hammer proportions, engulfing reference, entry at the open, stop first, 15:14 exit) with the engine. "0 mismatches" therefore shows two copies of the same reading agree; it does not show that the reading is the author's.

**Not checked by the reviewer:** the 5paisa timestamp convention (verified in Phase 2), the secondary-feed minute data, the DOCX screenshots and pixel-estimated zones, the 13 handwritten notes, chart/workbook contents.


## 5. Limits of this audit

* The audit shares the usable-session classification (`classify_session`), the official daily closes and the raw bars with the engine: a defect in those would not be caught here (they are the repository's verified infrastructure from Phases 2-4).
* The audit mirrors the declared conventions (entry at the 09:20 open, stop first, 15:14 forced exit); it cannot judge whether they are the author's intent (see `unresolved_rule_definitions.md`).
* Hand-drawn author annotations and pixel-estimated zones are approximate.
* The 13 handwritten disputes come from the Phase 5.8 transcription and were not re-read.