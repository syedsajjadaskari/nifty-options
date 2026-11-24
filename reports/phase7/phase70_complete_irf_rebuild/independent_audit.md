# Independent audit (Phase 7.0)

## 1. Second implementation vs production (no shared logic)
`audit.py` rebuilds the 5-minute candles with `pandas.resample`, finds signals with NumPy index searches and replays trades on one-minute NumPy arrays; it is compared with the production state machines for **every session x method x scenario**.

| window/scenario | signal comparisons | trade comparisons | mismatches |
|---|---|---|---|
| A/SL40_T60 | 492 | 266 | 0 |
| A/SL35_T60 | 492 | 266 | 0 |
| A/SL40_ENTRY_SIGNAL_CLOSE | 492 | 266 | 0 |
| A/SL40_TIE_MINUTE_ORDER | 492 | 266 | 0 |
| A/SL40_FORCED_EXIT_1300 | 492 | 266 | 0 |
| A/SL35_FORCED_EXIT_1300 | 492 | 266 | 0 |
| A/SL40_CUTOFF_EXCLUSIVE | 492 | 266 | 0 |
| A/SL40_M2_INVALIDATE_BELOW_A | 492 | 232 | 0 |
| A/SL40_T60__M2_ALT_BREAKOUT_RED | 492 | 266 | 0 |
| B/SL40_T60 | 1472 | 765 | 0 |
| B/SL35_T60 | 1472 | 765 | 0 |
| B/SL40_ENTRY_SIGNAL_CLOSE | 1472 | 765 | 0 |
| B/SL40_TIE_MINUTE_ORDER | 1472 | 765 | 0 |
| B/SL40_FORCED_EXIT_1300 | 1472 | 765 | 0 |
| B/SL35_FORCED_EXIT_1300 | 1472 | 765 | 0 |
| B/SL40_CUTOFF_EXCLUSIVE | 1472 | 765 | 0 |
| B/SL40_M2_INVALIDATE_BELOW_A | 1472 | 679 | 0 |
| B/SL40_T60__M2_ALT_BREAKOUT_RED | 1472 | 764 | 0 |

## 2. Causality (no look-ahead)
1031 signals (both methods, both windows): re-running the state machine on candles truncated at the failure candle reproduces the identical signal and timestamp; truncated one candle earlier it produces none; the fill timestamp is never before the signal timestamp. Failures: **0**.

## 3. Test suite
`tests/test_phase70_irf_v3.py` - Method 1 (figure, order, wick, equality, colour-agnostic, later cycles), Method 2 (figure, B = open not wick, first red only, red-before-breakout, no second breakout, wick, red-breakout variant, equality), isolation, causality, entry/stop/target maths, same-window tie, forced exit, cutoff inclusive of 13:00, combined cases (only M1 / only M2 / neither / same instant / M2 first), no double counting, metrics, journal matching stages, independent rebuild on synthetic days, example arithmetic and figures, undated examples never dated, no imports of old IRF engines / no unsupported-filter tokens, registry completeness.

## 4. Checks listed in the task
| Check | Result |
|---|---|
| Opening-range accuracy | first candle = the five 09:15-09:19 rows; verified in tests and by the independent rebuild |
| Correct reference levels | M1 level, M2 Level A / B (open of the first red candle) verified by tests and the independent rebuild |
| Candle sequencing / confirmation timing | signal_time == failure-candle end in every row (checked) |
| No future data | see section 2 |
| No unsupported extra filters | AST/token test on method1.py/method2.py; no EMA/gap/S-R/body/first-red-low code exists |
| No duplicate trades | one combined trade per day; test + `combined_irf_backtest.csv` unique dates per window/scenario |
| Entry/exit prices, stop/target | independent array replay: 0 mismatches |
| Method isolation | tests |
| Combined selection | tests + overlap analysis |
| Journal matching | staged one-to-one matcher tested; journal SHA-256 `97a9ad4dfb5520619bb979770115d7b6f4e3e37e649af255c543f5fce9694781` equals the Phase 6.3 audit SHA; the workbook is opened read-only |
| Chart correctness | charts built from the same trace/trade objects; Nov-3 chart inspected beside the embedded screenshot |

## 5. Limitations of this audit
* The independent rebuild was written by the same author from the same reading of the PDFs, so it detects coding defects, not a mistaken interpretation; interpretation risks are the unresolved questions. That is why an external read-only reviewer was also run (section 6).
* Window B uses the secondary 5paisa store of Phase 4; both stores' session classification is inherited from `classify_session`.

## 6. External read-only reviewer (separate agent, read both PDFs first, wrote its own aggregation and state machines)
**Result:** no signal or P&L defect. It reproduced signal time and level for both methods in all 246 window-A sessions (0 mismatches) and rebuilt every traded session at SL40 and SL35 (278 trades, 0 bad); three sessions were traced by hand (2025-09-01, 2025-09-02, 2025-12-15).

| # | Reviewer finding | Class | Action taken |
|---|---|---|---|
| 1 | MFE/MAE were updated for bars after the exit minute inside a 5-minute window (diagnostic only; fills, exits, P&L unaffected) | confirmed defect | fixed in `execution.py` (excursions only up to the exit bar); test `test_mfe_mae_stop_at_the_exit_bar` |
| 2 | 'Red' = close < open; a doji is not red - not in the registry | disclosure gap | registry row M2-R20; test added |
| 3 | M2 setup is never invalidated; in about a third of rally sessions the first red candle itself closes below Level A | ambiguity | quantified in `m2_rally_diagnostics.json` and README; new labelled variant `SL40_M2_INVALIDATE_BELOW_A` (not in the source) with independent-rebuild support; registry M2-R18 expanded; question 20 |
| 4 | 'No entry after 1 pm' could exclude a fill at exactly 13:00:00 | ambiguity | new sensitivity `SL40_CUTOFF_EXCLUSIVE` (fill must start <= 12:59); test added |
| 5 | Red rally-breakout candle as first red (only a handful of sessions) | ambiguity, disclosed | already reported as `M2_ALT_BREAKOUT_RED` |
| 6 | M2 Example 4: failure candle one candle later than the engine's | unresolved | kept as a documented non-reproduction; registry M2-R21; question 19 |
| 7 | Journal label is compared with the signal-candle START (a label meaning entry time would shift every match by 5 minutes) | disclosure nuance | stated in `recon.py` and the README; conventions unchanged from Phase 5.6/6.3 |
| 8 | Each method contributes only its first cycle to the combined book | design note | by design (1 trade/day); later cycles are counted, not traded |
Everything else (M1/M2 logic, look-ahead, execution maths, combined selection, metrics, matcher, no imported older-IRF assumptions) was rated NO ISSUE.

