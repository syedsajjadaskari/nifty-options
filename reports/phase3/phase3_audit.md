# Phase 3.0 - independent audit

## 1. Who audited what
A fresh agent with no part in writing the engine audited the backtest. It was read-only on the repository and data, wrote its own simulator that **does not import** the project's `exit_policy` or `trading_day` (it only reads the raw 1-minute parquet), and worked from the owner's rules as given in the Phase 3.0 brief. Its raw report is kept as `phase3_audit_raw_auditor6.md`. The earlier Phase 2.3 reviewer's fuzzing of the controller (1,500 random days, an independent oracle on 3,000 more, 50 hand-computed exit paths) also applies to the same code.

## 2. Results
| check | result |
|---|---|
| **Independent recalculation** | **All 839 trades of the four ledgers** (213 + 203 + 210 + 213) re-simulated from the raw 1-minute bars with 0 mismatches in outcome class, entry price, stop/T1/T2/post-T1 levels, leg exit times and prices, gross P&L, adverse slippage and ambiguity counts. The comparator was shown to detect a perturbed value. The sample covers all five strategies, all outcome classes, 16 second trades, 6 gap-through-stop trades, entries at 12:30 and 12:55, 41 ORB trades at 09:20, 13 trades on closing-auction-regime days |
| **State machine** | 0 violations on all ledgers: at most 2 entries/day; the second trade only after an `INITIAL_FULL_STOP` and only PDR/PDS, entered after the first trade's exit minute; no entry after 13:00; no trade on a collision day; the controller's decision tree re-run by the auditor reproduces every trade and the disposition of every logged signal (all 1,161 baseline log rows) |
| **No look-ahead** | all 18,525 five-minute candles and the 5-minute EMA(200) recomputed from the raw minutes match to 0.0; every `signal_time` is a 5-minute candle end and equals the entry minute (never before 09:20); re-running the engines on truncated or noise-padded future candles gives identical signals up to each signal time (0 violations in 1,281 cut points); previous-day inputs use earlier sessions only. IRF Method 1 re-derived independently: the same 349 (day, time) signals; all 27 baseline ORB Method 1 and 54 PDR trades satisfy their conditions |
| **Forced exit** | no trade was force-exited in any scenario, every trade is resolved and the latest exit is 14:50, so the 15:14 path is not exercised by real ledgers. The auditor cross-checked it on real data with its own simulator: 2,964 cases (all 247 sessions, entries 09:20 and 13:00, both directions, 1,620 forced exits, including auction days) agree with `evaluate_exit` with 0 differences; 7 synthetic unit tests pass |
| **Costs and metrics** | every figure in every `summary`, `strategy_performance`, `monthly_pnl`, `equity_curve`, the 4 x 4 cost/slippage grids and `all_summaries.json` recomputed from `trades.csv`: 0 discrepancies; re-running the code reproduces all four ledgers exactly; provenance hashes match the files |
| **Scenarios** | each `config_snapshot.json` differs from the baseline in exactly one setting (`trend_mode`, `pdr_zone_method`, `stop_variant`); `sl40` has the same signals as the baseline; the scenarios were never combined |
| **Comparison report** | every number in sections 1-5 recomputes; the manual-report figures are quoted correctly against `Performance_Report.txt`; the legacy-breakeven diagnostic was reproduced independently (Rs 1,41,219; 52 Target, 74 BE, 87 SL) |

No CRITICAL or MAJOR finding.

## 3. Findings and what was done
| ID | Finding | Disposition |
|---|---|---|
| MINOR-1 | "247 evaluated / 1 excluded" overstates coverage: on 2025-10-23 ORB/PDR/PDS/RF are blocked (their previous session is the unverifiable Muhurat day), only IRF can trade | **Disclosed**: every summary now lists "evaluated only partially"; the comparison's limits repeat it. No P&L effect |
| MINOR-2 | the comparison text said "PDR and IRF lose less" for scenario D although PDR is profitable in every scenario | **Fixed** ("PDR and IRF are higher, PDS and RF lower") |
| MINOR-3 | previous-day levels/zones use all candles of the previous session, including the auction print on auction days (it changes the previous-day level on 5 of the 19 sessions that follow an auction day); no report said so | **Disclosed** in every summary, the config snapshot and the comparison. No parameter was changed. (The auditor measured a two-trade difference in August 2026 if only continuous candles were used: RF 2026-08-05 -Rs 13,650 dropped, PDR 2026-08-12 +Rs 4,095 added) |
| MINOR-4 | the diagnostic table showed "0 (as BE)" for the post-T1 class | **Fixed**: shows the legacy BE count (74) and the entry -/+ 6 count separately |
| MINOR-5 | "forced-exit sensitivity Rs 0" read like a robustness result | **Fixed**: the summaries say that with no forced exit the assumption had no effect and that this is a statement about an empty set |
| MINOR-6 | in the second-trade state another strategy's same-minute signal is rejected before the collision test (1 of 16 second trades per scenario) | **Disclosed** in every summary and the comparison |
| INFO | latent: if the 15:14 bar were missing on an ordinary day the code would force the exit at the 15:15 bar | **Fixed**: the forced exit must fill strictly before 15:15 (otherwise the position stays unresolved); the test was updated. No data impact (the auditor found a 15:14 bar on every session); the ledgers are byte-identical before and after the fix |
| INFO | day-state labels unexplained; `config_snapshot.json` lacked per-strategy stops/targets; scenario A's title said "35-point stop" though ORB uses 30; the "189 trades on 180 days (5 days with two trades)" phrase did not reconcile | **Fixed**: labels explained in the comparison; the snapshot now lists the per-strategy levels and lots; the title says "(ORB 30)"; the journal facts are stated separately from the report's |
| INFO | the break-even mechanism was stated as fact in one place | **Hedged** ("probably ... not isolated further") |

## 4. Not covered by the audit
* Signal **generation** was re-derived independently only for IRF Method 1, ORB Method 1 and PDR. IRF 2A/2B/3, ORB Method 2 and the gap setup, PDS, RF, the candle-quality thresholds, the structure trend and the shelf zone were checked through the causality test and the exit/state-machine recomputation, not re-derived.
* The state-machine recomputation takes its signal universe from the controller's own logs (it verifies the controller, not signal generation).
* Real data never exercised: forced exits, a same-minute T1 + post-T1 stop, T1 and T2 in one minute, any stop/target ambiguity, an entry at exactly 13:00 (all are covered by synthetic tests and the earlier fuzzing, not by these ledgers).
* The vendor data's legitimacy, the registry, and whether any assumption is sensible were out of scope. No profit figure was used to change a rule or parameter.

## 5. Software state
Full suite on the final files and lint: see the final report. The audited ledgers are unchanged by the fixes above.
