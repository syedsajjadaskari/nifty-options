# Independent audit (Phase 6.1)

`src/nifty_trading/research/irf_v2_audit.py` re-derives every Method 2 attempt and every Method 2A signal (<= 13:00, with the 28-point gate) from RAW five-minute candles built by the Phase 6.0 independent chain (pandas resample, recursive EMA) - not from the engine's state machine, the repository's candles or its EMA.

| window | sessions | independent_method2a_signals | engine_method2a_signals | sessions_with_mismatch |
|---|---|---|---|---|
| A | 247 | 168 | 168 | 0 |
| B | 738 | 477 | 477 | 0 |


Declared shared pieces: the Method 2B resistance helper (`definitions.recent_resistance`, only to know when an attempt ends) and the proposal defaults. The first run disagreed on one 2022-25 session (2024-02-26): the audit lacked the frozen rule that a data gap (missing candles) invalidates an open attempt; the engine was right and the audit was corrected.

IRF V2 equals the Phase 5.3 IRF on both windows (same keys). Handwritten IRF cases: {'cases': 12, 'first_entry_changed_by_v2': 6, 'out_of_scope_2b': 5}.

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
