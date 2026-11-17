# Phases 6.1 - 6.3: IRF V2, combined five-strategy backtest and journal reconciliation - final research report

**Written for:** the strategy owner. Research only: synthetic NIFTY index-point P&L on 390 units (6 x 65; legs 195 + 195), not option profit; no orders, no parameter optimisation, no configuration selected, nothing committed or pushed. Neither window is untouched out-of-sample. Stopped after Phase 6.3 as instructed.

## Headline

* **IRF V2 emits exactly the Phase 5.3 IRF signals** (786 on both; also on 2022-25): the owner-approved first-red-low and 28-point rules were already implemented in Phase 5.3. V2 re-implements Method 2A as an explicit state machine, exposes every reference candle / support / break / EMA fact, and is verified by an independent re-derivation (0 mismatches on both windows). Relative to the frozen Phase 3.6 IRF it changes 730 signals.
* **Combined configuration C** (IRF V2 + ORB V2 [provisional ORB-V2-A, entry signals only] + PDR/PDS first-eligible + RF): 183 trades, gross Rs +37,420, profit factor 1.033, max drawdown Rs 239,830. For reference A (frozen) 196 trades / Rs +297,765 / PF 1.284; B (Phase 5.3) 188 / Rs +258,550 / PF 1.25.
* **ORB V2 under the portfolio exit model is a poor fit for the same entries that looked acceptable standalone**: 39 trades, -41.0 weighted points (PF 0.932) versus the frozen ORB's 41 trades, +355.1 points (PF 1.838); the standalone 30/60 result of Phase 6.0 is unchanged and uses a different exit model. This is reported, not tuned.
* **Journal agreement does not improve materially**: strict matches A 66, B 64, C 67 of 190 rows (strict = date + strategy + time label; **no verified exact trade match is possible** because the journal has no direction or price). All 89 ORB journal rows carry the label 09:15, so an ORB 'strict' match is only a date + strategy match, C's gain over B comes entirely from ORB, and ORB V2 was reconstructed in Phases 5.8-6.0 with this same journal's ORB dates in view: the ORB hit rate is in-sample, not independent confirmation.

## Answers to the 25 questions

**1. IRF signals changed by the support-break rule?** Frozen 874 -> V2 786 confirmed signals (primary window): unchanged 447, same time but a different support level 36, removed 391, added 303. Removed by cause {'SUPPORT_REFERENCE_CHANGED (first red candle low)': 127, 'EMA_28_CLEARANCE_REJECTED': 126, 'ATTEMPT_LIFECYCLE / DOWNSTREAM': 138}; added {'SUPPORT_REFERENCE_CHANGED': 228, 'ATTEMPT_LIFECYCLE / DOWNSTREAM': 75}. Method 2A first signal moves earlier on 243 and later on 59 session-dates; the 28-point rule rejected 514 candidate confirmations. (V2 vs Phase 5.3: 0 changes.)
**2. IRF trades matching the manual journal (config C)?** strict 20 of 73 manual IRF rows (+ 11 time-tolerant, 15 date-only), against A 26 strict and B 20 strict; of C's 85 IRF trades 39 are automated-only.
**3. ORB V2 trades in the combined system?** 39 (primary), 92 (2022-25); each fills at the 09:20 bar open, earlier than any other strategy.
**4. Manual ORB dates reproduced?** strict 38 of 89 manual ORB rows (date + ORB + label 09:15; direction/level unverifiable); the frozen ORB had 35. 38 manual ORB dates have ORB selected as the first trade in C.
**5. Previously disputed dates where ORB V2 activates before IRF?** Of the 34 manual ORB dates on which the frozen (A) or Phase 5.3 (B) IRF executed, ORB is now the selected first trade on 12; classifications: {'ORB NOW SELECTED': 12, 'SOURCE RULE UNRESOLVED': 9, 'IRF STILL SELECTED': 12, 'ORB SIGNAL REJECTED': 1}. A journal ORB label alone is not treated as proof the dispute is resolved (`orb_vs_irf_comparison.csv`).
**6. Total combined trades?** C: 183 (primary), 603 (2022-25).
**7. By strategy (C, primary)?** IRF 85, ORB 39, PDR 31, PDS 19, RF 9. Contributions inside the portfolio are not standalone profits.
**8. Total gross synthetic P&L?** C primary: +95.95 weighted index points = Rs +37,420; 2022-25: Rs +281,395.
**9. Estimated net P&L (primary window, net synthetic Rs)?**

| label | A | B | C |
|---|---|---|---|
| Gross synthetic index P&L (no cost) | 297765.0 | 258550.5 | 37420.5 |
| Rs 70 per completed trade | 284045.0 | 245390.5 | 24610.5 |
| Rs 70 per order fill (entry + each exit leg) | 256605.0 | 219070.5 | -1009.5 |
| Rs 70 per trade + 0.25 pt slippage per side | 245825.0 | 208730.5 | -11074.5 |
| Rs 70 per trade + 0.5 pt slippage per side | 207605.0 | 172070.5 | -46759.5 |
| Rs 70 per trade + 1 pt slippage per side | 131165.0 | 98750.5 | -118129.5 |


**10. Win rate / profit factor / max drawdown (C, primary)?** 53.55% / 1.033 / Rs 239,830 (2022-25: 57.21% / 1.082 / Rs 283,793).
**11. Versus Phase 3.6 (A) and Phase 5.3 (B)?** Primary window gross Rs: A +297,765, B +258,550, C +37,420; PF 1.284 / 1.25 / 1.033. 2022-25: A +509,398, B +152,539, C +281,395. The attribution runs show B -> C comes entirely from ORB V2 (IRF V2 == Phase 5.3 IRF; D1 == B) and B and C genuinely differ on 36 dates (A and B on 65; method-label-only differences excluded) out of 117 dates on which the three configurations are not all identical (`configuration_comparison.md`).
**12. Strict journal matches?** A 66, B 64, C 67 (of 190 rows; 5 are weekend-dated).
**13. Additional time-tolerant (<= 15 min)?** A 21, B 14, C 15.
**14. Date-and-strategy-only?** A 18, B 17, C 17 (not counted as matches).
**15. Manual-only rows?** A 85, B 95, C 91 (each includes the 5 weekend-dated rows).
**16. Automated-only trades?** A 91, B 93, C 84.
**17. Wrong-strategy dates?** A 61, B 61, C 53.
**18. Main causes of unmatched IRF trades / rows (C)?** Manual IRF rows not matched: {'MISSING_STRATEGY_SIGNAL': 7, 'DIFFERENT_STRATEGY_SELECTED': 16, 'PORTFOLIO_CONTROLLER_CONSTRAINT': 3, 'MANUAL_JOURNAL_INCONSISTENCY': 1}; automated IRF trades with no journal counterpart: {'UNRESOLVED_DISCRETIONARY_SELECTION': 14, 'DIFFERENT_STRATEGY_SELECTED': 25} (cause vocabulary of Phase 5.6; `mismatch_root_causes.csv`). The IRF reconciliation per journal row is in `irf_support_break_reconciliation.csv`.
**19. Main causes of unmatched ORB trades / rows (C)?** Manual ORB rows not matched: {'MISSING_STRATEGY_SIGNAL': 20, 'DIFFERENT_STRATEGY_SELECTED': 27, 'MANUAL_JOURNAL_INCONSISTENCY': 4}; automated ORB trades with no journal row: {'UNRESOLVED_DISCRETIONARY_SELECTION': 1}. For the rejected manual ORB dates the ORB V2 rejection reasons (mostly the provisional pattern definitions and the wrong-side-wick rule) are in `orb_vs_irf_comparison.csv`.
**20. Handwritten corrections reconciled?** None is claimed reconciled (the notes give no numeric entry, level or direction). Status in C: {'C_TRADES_EQUAL_B': 26, 'ORB_NOW_TRADED_DIRECTION_UNVERIFIED': 4, 'ORB_STILL_NOT_TRADED': 10}. Method 2B cases are out of the approved IRF scope (`irf_handwritten_cases.csv`, `handwritten_corrections_comparison.csv`).
**21. Entries, stops, targets and exits consistent with the raw one-minute candles?** Yes: 3996 of 3996 executed trades (all configurations, both windows) re-derived by a separate simulator with 0 problems (`entry_exit_execution_audit.md`).

**22. Stability across 2022-2025 (gross Rs by calendar year; A / B / C):**

| window | calendar_year | A | B | C |
|---|---|---|---|---|
| A | 2025 | 221061.75 | 245602.5 | 105787.5 |
| A | 2026 | 76703.25 | 12948.0 | -68367.0 |
| B | 2022 | -96690.75 | -148083.0 | -146932.5 |
| B | 2023 | 462949.5 | 232586.25 | 149847.75 |
| B | 2024 | 6483.75 | -8024.25 | 130074.75 |
| B | 2025 | 136656.0 | 76059.75 | 148404.75 |


Results swing strongly by year in every configuration (e.g. 2022 is negative in all three); samples per year are small; no stability claim is made.

**23. Unresolved source definitions / execution assumptions:** the ORB V2 decisions OD-1..OD-7 and OD-15 of Phase 6.0 (feed, break definition, inner levels, patterns, wick rule, gap limit, entry price, gap reference close) - ORB-V2-A is used only as a provisional reference because no owner selection exists; the IRF red-candle search start and 28-point measure/scope (provisional), the IRF day's-low predicate (not applied), extension of the support-break rule to Method 2B (needs approval); PDR/PDS first-eligible conventions (provisional); the 15:14 forced-exit reference; the Rs 70 cost estimate; no tie-break policy for same-minute collisions; the journal's missing fields.
**24. Frozen historical results unchanged?** Yes: 19278 pre-existing files hashed before any change; 0 changed, 0 removed, 0 new files outside the Phase 6.1-6.3 paths. Configuration A also reproduces the Phase 5.5 ledger (196 trades, 0 mismatches) and Phase 4 on 2022-25 (609 trades); B reproduces Phase 5.5.
**25. Where?** Phase 6.1: `reports/phase6/phase61_irf_support_break/` (README, workbook `IRF_V2_Verification.xlsx`, `charts/`); Phase 6.2: `reports/phase6/phase62_combined_backtest/` (README, `combined_backtest_summary.md`, `Combined_Five_Strategy_Backtest.xlsx`, `daily/` = one report per evaluable session, `charts/` = one per executed C trade); Phase 6.3: `reports/phase6/phase63_manual_reconciliation/` (README, `exact_match_summary.md`, `Manual_vs_Automated_Verification.xlsx`, `daily/`, `charts/`); this report: `reports/phase6/PHASE61_63_FINAL_RESEARCH_REPORT.md`.

## Verification

* Execution audit: 3996/3996 trades verified; IRF Method 2A independent audit: {'A': {'sessions': 247, 'independent_method2a_signals': 168, 'engine_method2a_signals': 168, 'sessions_with_mismatch': 0}, 'B': {'sessions': 738, 'independent_method2a_signals': 477, 'engine_method2a_signals': 477, 'sessions_with_mismatch': 0}}.
* pytest (full suite) and ruff:

```
=========================== short test summary info ============================
FAILED tests/test_phase5_cross_index.py::test_every_nifty_artefact_every_earlier_report_and_every_tracked_file_is_byte_identical_to_the_pre_phase5_snapshot
1 failed, 865 passed, 1 skipped, 1 xfailed in 157.04s (0:02:37)
All checks passed!
```

**One pre-existing test fails and was NOT touched:** `tests/test_phase5_cross_index.py::test_every_nifty_artefact_every_earlier_report_and_every_tracked_file_is_byte_identical_to_the_pre_phase5_snapshot` reports `.gitignore` as changed since the Phase 5 snapshot. The change (adding `.DS_Store` ignore rules) arrived with commit `ea3d8da3` (Phases 5.8-6.0), before this task; the Phase 6.1-6.3 before/after hash check shows `.gitignore` and every other pre-existing file unchanged by this work. Resolving it needs a decision on whether to re-baseline that snapshot or revert the `.gitignore` addition. All other tests pass (including the 29 new ones).

## Independent reviewer

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


## Decisions for the owner (nothing below was decided here)

1. Select (or reject) an ORB V2 variant: ORB-V2-A is provisional, and under the portfolio exit model it adds trades that lose more often than the frozen ORB's. 2. Decide whether the support-break rule should also apply to IRF Method 2B. 3. Define the IRF day's-low predicate. 4. Confirm the 28-point measure/scope. 5. Approve or amend the shared tie-break policy and the forced-exit convention. 6. Provide direction / level / price for journal dates if exact matching is wanted.