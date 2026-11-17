# Independent audit (Phase 6.2)

1. Execution audit: 3996 / 3996 trades verified from raw bars by a separate simulator (see `entry_exit_execution_audit.md`).
2. Regression gates: A and B reproduce Phase 5.5, A reproduces Phase 4 on 2022-25, D1 == B ({'A': {'phase55_trades': 196, 'reproduced_trades': 196, 'mismatches': 0, 'gross_phase55': 297765.0, 'gross_now': 297765.0}, 'B': {'phase55_trades': 188, 'reproduced_trades': 188, 'mismatches': 0, 'gross_phase55': 258550.5, 'gross_now': 258550.5}, 'window_B_A_vs_phase4': {'phase4_trades': 609, 'now': 609, 'same_ids': True, 'gross_equal': True}, 'D1_equals_B_A': True, 'D1_equals_B_B': True}).
3. ORB V2 integration: the opening candle equals the controller's candle on every session; fills at 09:20.
4. Pytest and ruff results are in the final report.

## Reviewer

A fresh read-only subagent (no prior context) reviewed Phases 6.1-6.3. **No high-severity defect.** Independently verified by it: all 39 config-C ORB trades (raw bars: 09:15-09:20 candle, 09:20 fill, stop / T1 / T2 / post-T1 levels, both exit legs, P&L, direction vs the Phase 6.0 signal file; all 12 dates where A or B executed IRF and C executed ORB included); all 594 primary-window Method 2 attempts and all 271 Method 2A signals re-derived from raw candles (EMA within 5e-7; no look-ahead; day's-low restriction not applied); IRF V2 == Phase 5.3 (786 signals each); an independent controller replay over 3,959 signal days in all five configurations and both windows (zero mismatches; 307 two-trade days with no rule violation); the strict / tolerant / date-only / manual-only / automated-only counts for A, B, C recomputed from the workbook; costs (per trade, per fill, slippage on filled units) recomputed exactly; A and B identical to the committed Phase 5.5 ledgers.

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | medium | The B-vs-C 'causal reason' text was wrong on 41 dates (legacy ORB traded in B, ORB V2 did not signal) and 22 of the 58 'ORB V2 effect' dates differed only in the method label (same trades) | ACCEPTED: reasons rewritten by case (ORB V2 took the first trade / legacy ORB trade not reproduced / direction or outcome differs / method label only); label-only dates are no longer counted as changes |
| 2 | medium | Journal 'strict' is weaker evidence than the headline suggests: all 89 ORB labels are 09:15 (ORB strict = date + strategy); C's gain over B is entirely ORB; ORB V2 was built with this journal's ORB dates in view, so the ORB hit rate is in-sample | ACCEPTED: stated in the reconciliation summary, the final report and the headline |
| 3 | low | The adapter's EMA integration check was vacuous (`hasattr(c, "e")`; field is `ema`): NaN in every row | ACCEPTED and fixed; the numbers were not wrong (ORB V2 EMA equals the context EMA within 5e-7 on all 247 sessions) |
| 4 | low | Weak tests: a `>` or `>=` second-trade check; a tautological date assertion; a by-construction 'reference cannot break itself' test | ACCEPTED: strict `>` check (a second entry in the first trade's stop minute is forbidden); tautology removed; the test now asserts only later candles are examined |
| 5 | low | Two ruff findings in `phase61_run.py` | ACCEPTED, fixed |
| 6 | low | Attempt-log quirks: EMA-vetoed attempts showed final_state SUPPORT_BROKEN; `first_close_below_support` blank when the first below-support close was vetoed | ACCEPTED and fixed (signals unaffected) |
| 7 | low | Fills on a touch are shared by the backtest and the audit (e.g. the 2026-04-30 ORB trade reaches T1 with a 0.2-point margin) | NOTED as a limitation; the slippage scenarios partly cover it |
| 8 | low | A same-minute ORB V2 / PDS collision leaves 2024-10-04 (2022-25 window) without a trade | NOTED: the frozen no-priority rule, working as designed |

**Independence caveat (accepted):** the execution audit takes signal time, direction, strategy and quantities from the ledger (it cannot catch a wrong selection; the reviewer's separate controller replay covers selection) and shares the execution conventions with the backtest; the IRF audit shares `recent_resistance`, the proposal defaults and the lifecycle / search-start interpretation with the engine. Not checked by the reviewer: ORB V2's inner-level / pattern logic (Phase 6.0, provisional), PDR / PDS / RF signal generation, IRF V2 and ORB signals on the 2022-25 window, workbooks, charts and daily files.
