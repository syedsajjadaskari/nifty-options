# Phase 3.1 - reconciliation summary

**Reconciliation, not optimisation.** No rule, parameter, stop, target, cutoff or selection policy was changed, nothing was fitted to the manual report, and the Phase 3.0 ledgers are untouched. The manual journal is not ground truth (Phase 2.1): its inconsistencies are carried as flags, never corrected. Every figure below is computed from `manual_vs_automated.csv`, `extra_automated_trades.csv`, `daily_signal_timelines.csv` and `analysis_tables.json` by `scripts/phase31_report.py`.

## Conventions

* **Time label:** a journal entry time is the START of the 5-minute entry candle (67 exact matches confirm it); the automated signal is confirmed at the candle END and filled at the next minute's open.
* **Matching** (deterministic, one-to-one, P&L never used): same date and strategy; exact = same candle start; time-shifted = nearest candle start within 15 minutes (3 candles); a journal row whose strategy label is in a Phase 2.1 attribution conflict may match under its alternate label (flagged). The journal has no entry price, so `PRICE_DIFFERENCE` cannot be tested.
* **Baseline** = Phase 3.0 scenario A (EMA-only trend, 35-point stop, reversal-high PDR zone). Classifications under scenarios B and C are columns of `manual_vs_automated.csv`.

## A. How many manual trades match an automated execution?

Of **190** journal rows (the report says 189; 5 rows are Saturday-dated), **84 (44%) match an executed baseline trade** - 67 exact (same candle) and 17 time-shifted. For the matched pairs the outcome class agrees loosely (Target~Target, BE~post-T1 stop, SL~full stop) in 76 of 84 cases, although the stop rules differ. Confidence: HIGH for exact matches on journal rows the Phase 2.1 audit marked VALID; lower for rows in an attribution-conflict cell.

| strategy | EXACT_MATCH | MANUAL_JOURNAL_CONFLICT | MISSING_AUTOMATED_SIGNAL | SIGNAL_REJECTED_BY_ENTRY_RULE | SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER | TIME_SHIFTED_MATCH |
|---|---|---|---|---|---|---|
| IRF | 25 | 1 | 13 | 0 | 19 | 15 |
| ORB | 35 | 4 | 11 | 38 | 0 | 1 |
| PDR | 4 | 0 | 2 | 2 | 0 | 0 |
| PDS | 1 | 0 | 2 | 0 | 0 | 0 |
| RF | 2 | 0 | 0 | 10 | 4 | 1 |
| TOTAL | 67 | 5 | 28 | 50 | 23 | 17 |

## B. Why 213 automated trades vs 189 (190) manual

The identity is exact: **213 automated = 84 matched + 129 automated extras**, and **190 journal rows = 84 matched + 106 unmatched**. The net difference (213 - 190 = 23) is 129 - 106: the automated system takes 129 trades the journal does not show and misses 106 the journal does.

| strategy | manual rows | matched (exact) | matched (time-shifted) | manual unmatched | automated entries (baseline) | automated extra |
|---|---|---|---|---|---|---|
| IRF | 73 | 25 | 15 | 33 | 102 | 62 |
| ORB | 89 | 35 | 1 | 53 | 41 | 6 |
| PDR | 8 | 4 | 0 | 4 | 54 | 49 |
| PDS | 3 | 1 | 0 | 2 | 11 | 10 |
| RF | 17 | 2 | 1 | 14 | 5 | 2 |
| TOTAL | 190 | 67 | 17 | 106 | 213 | 129 |

What the 129 extras are (same-day relation to the journal):

| strategy | MANUAL_TRADED_ONLY_OTHER_STRATEGIES | NO_MANUAL_TRADE_THAT_DAY | SAME_STRATEGY_MANUAL_TRADE_AT_ANOTHER_TIME |
|---|---|---|---|
| IRF | 34 | 16 | 12 |
| ORB | 4 | 2 | 0 |
| PDR | 29 | 19 | 1 |
| PDS | 8 | 1 | 1 |
| RF | 1 | 1 | 0 |
| TOTAL | 76 | 39 | 14 |

Day level (247 sessions): both traded with the same first strategy on **95** days, with a different first strategy on **67**; only the manual trader traded on **18**; only the automated system on **35**; neither on **32**.

## C. Primary root cause of each unmatched manual trade (106) and of each extra automated trade (129)

Manual trades with no executed automated counterpart (heuristic mapping from the rejection chain; see `root_cause_analysis.md` for the evidence and its limits):

| root_cause_primary | IRF | ORB | PDR | PDS | RF | TOTAL |
|---|---|---|---|---|---|---|
| SOURCE_AMBIGUITY | 0 | 21 | 0 | 0 | 8 | 29 |
| PORTFOLIO_COMPETITION | 19 | 0 | 0 | 0 | 4 | 23 |
| PROPOSED_NUMERICAL_THRESHOLD | 0 | 18 | 0 | 0 | 0 | 18 |
| TREND_FILTER | 0 | 10 | 0 | 0 | 2 | 12 |
| UNKNOWN | 10 | 0 | 0 | 2 | 0 | 12 |
| JOURNAL_INCONSISTENCY | 1 | 4 | 0 | 0 | 0 | 5 |
| ZONE_SELECTION | 0 | 0 | 4 | 0 | 0 | 4 |
| TIME_ALIGNMENT | 3 | 0 | 0 | 0 | 0 | 3 |

Automated extras (a STRATEGY-LEVEL dependency, not trade-specific proof):

| root_cause_primary | IRF | ORB | PDR | PDS | RF | TOTAL |
|---|---|---|---|---|---|---|
| ZONE_SELECTION | 0 | 0 | 49 | 0 | 0 | 49 |
| PROPOSED_NUMERICAL_THRESHOLD | 27 | 0 | 0 | 10 | 0 | 37 |
| SOURCE_AMBIGUITY | 35 | 1 | 0 | 0 | 0 | 36 |
| TREND_FILTER | 0 | 5 | 0 | 0 | 2 | 7 |

## D. The four collision days

Both policies are diagnostic counterfactuals; neither is approved and neither is chosen for its result.

| date | extra_entries | manual_trades_that_day | trades_MARK_DAY_UNRESOLVED | trades_SKIP_COLLISION_EVENT_CONTINUE_DAY |
|---|---|---|---|---|
| 2025-09-08 | 1 | RF@09:25:BE | [] | [["IRF", "09:45", "TARGET"]] |
| 2026-02-18 | 2 | RF@09:25:SL | [] | [["PDR", "09:40", "INITIAL_FULL_STOP"], ["PDR", "10:20", "TARGET"]] |
| 2026-06-23 | 1 | IRF@10:10:BE | [] | [["PDS", "10:50", "TARGET"]] |
| 2026-07-13 | 1 | nan | [] | [["PDS", "11:55", "INITIAL_FULL_STOP"]] |

Continuing the day after skipping the colliding signals would add **5** entries over the four days (counts only).

## E. Journal checks (all 190 rows)

* conforms to the approved portfolio rules: **184** rows; non-conforming: **6** (5 Saturday-dated rows, and **row 134: 2026-05-19, a PDR trade after an ORB breakeven** - confirmed against the workbook: row 133 ORB 09:15 BE, row 134 PDR 09:35 BE).
* duplicates: 0; entries labelled after 13:00: 0 (latest labels IRF 12:20, RF 11:00, PDS 10:30, PDR 10:20, ORB 09:15).
* Phase 2.1 flags carried: 172 VALID, 13 UNRESOLVED (rows in a strategy-month cell the report's arithmetic cannot reproduce), 5 INVALID (Saturdays).
* The report's per-trade P&L is printed only for 9 trades (its drawdown-window table); every other P&L in `manual_journal_normalized.csv` is DERIVED from the outcome with the report's payoff rules and labelled as such.

## F. Scenario sensitivity (the matching only; no scenario is preferred)

Matched manual trades: baseline 84, structure trend 64, PDR shelf 87.

## G. What this does and does not show

* The timing convention and the first-candle strategies are broadly consistent with the journal: where the system trades, it usually trades the same candle and (loosely) the same outcome class.
* The gap between the two ledgers is mostly **selection and filtering**, not timing: see `root_cause_analysis.md`.
* Nothing here says which side is 'right'. The journal is a discretionary, self-recorded record with known inconsistencies; the engines contain mechanical stand-ins that the owner has not approved.

