# Cross-configuration reconciliation with the manual journal

> SYNTHETIC index-point P&L; no real option P&L. The journal has no direction, price or exit time: matching uses only date, strategy and the entry-time label, and every automated-trade explanation rests on the actual candles and the documented rules.

The reconciliation is run SEPARATELY for A, B and C; no configuration is selected or approved, and a higher match count is not an approval criterion (the strategy rules were not changed to raise it).

## Matching totals (190 journal rows)

| configuration | automated trades | strict | time-tolerant | matched (strict + tolerant) | date + strategy only (not a match) | manual rows without a match | automated trades without a match | matched pairs with the same exit class | dates with different strategies |
|---|---|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 196 | 66 | 21 | 87 | 18 | 103 | 109 | 80 / 87 | 57 |
| B - Phase 5.3 author-corrected | 188 | 64 | 14 | 78 | 17 | 112 | 110 | 71 / 78 | 57 |
| C - B + ORB gap crossing | 190 | 67 | 14 | 81 | 17 | 109 | 109 | 74 / 81 | 56 |

Manual rows without a match include the five weekend-dated rows (no session) and the date-and-strategy-only rows. Of the 190 journal rows, 185 fall on evaluated sessions; 19 (A), 29 (B) and 27 (C) of them are on sessions on which the automated system took no trade at all (no valid signal, or none that passed the filters); the other unmatched rows are on days with an automated trade of another strategy, or of the same strategy at another time.

## By strategy

| cfg | strategy | journal rows | strict | time-tolerant | manual-only rows (incl. date + strategy only) | automated trades | automated trades without a match |
|---|---|---|---|---|---|---|---|
| A | ORB | 89 | 35 | 0 | 54 | 41 | 6 |
| A | IRF | 73 | 26 | 15 | 32 | 109 | 68 |
| A | PDR | 8 | 0 | 3 | 5 | 25 | 22 |
| A | PDS | 3 | 1 | 0 | 2 | 11 | 10 |
| A | RF | 17 | 4 | 3 | 10 | 10 | 3 |
| B | ORB | 89 | 35 | 0 | 54 | 41 | 6 |
| B | IRF | 73 | 20 | 10 | 43 | 90 | 60 |
| B | PDR | 8 | 4 | 1 | 3 | 28 | 23 |
| B | PDS | 3 | 1 | 0 | 2 | 19 | 18 |
| B | RF | 17 | 4 | 3 | 10 | 10 | 3 |
| C | ORB | 89 | 38 | 0 | 51 | 44 | 6 |
| C | IRF | 73 | 20 | 10 | 43 | 89 | 59 |
| C | PDR | 8 | 4 | 1 | 3 | 28 | 23 |
| C | PDS | 3 | 1 | 0 | 2 | 19 | 18 |
| C | RF | 17 | 4 | 3 | 10 | 10 | 3 |

**Exits.** Among the matched pairs the manual outcome label and the automated exit class agree in 80 of 87 (A), 71 of 78 (B) and 74 of 81 (C) pairs, i.e. for most (not all) matched entries the approved stops / targets give the recorded outcome class (the disagreements are listed as EXIT_MANAGEMENT_MISMATCH). The journal has no exit price or time, so the exit decisions cannot be compared beyond that label; what the journal's 'BE' label meant (exact-entry stop or another break-even rule) is not documented, while the approved rule stops at entry -/+ 6.

## Earliest-cause classification (manual-only rows)

| cfg | cause | rows |
|---|---|---|
| A | CANDLE_STRENGTH_MISMATCH | 22 |
| A | LEVEL_CONSTRUCTION_MISMATCH | 20 |
| A | DIFFERENT_STRATEGY_SELECTED | 12 |
| A | OPENING_GAP_MISMATCH | 12 |
| A | LATER_SIGNAL | 10 |
| A | EARLIER_SIGNAL | 9 |
| A | EMA_FILTER_MISMATCH | 7 |
| A | UNRESOLVED_DISCRETIONARY_SELECTION | 5 |
| A | MANUAL_JOURNAL_INCONSISTENCY | 5 |
| A | PORTFOLIO_CONTROLLER_CONSTRAINT | 1 |
| B | CANDLE_STRENGTH_MISMATCH | 22 |
| B | LEVEL_CONSTRUCTION_MISMATCH | 20 |
| B | EMA_FILTER_MISMATCH | 16 |
| B | DIFFERENT_STRATEGY_SELECTED | 12 |
| B | OPENING_GAP_MISMATCH | 12 |
| B | EARLIER_SIGNAL | 10 |
| B | LATER_SIGNAL | 10 |
| B | UNRESOLVED_DISCRETIONARY_SELECTION | 5 |
| B | MANUAL_JOURNAL_INCONSISTENCY | 5 |
| C | CANDLE_STRENGTH_MISMATCH | 27 |
| C | LEVEL_CONSTRUCTION_MISMATCH | 20 |
| C | EMA_FILTER_MISMATCH | 12 |
| C | DIFFERENT_STRATEGY_SELECTED | 12 |
| C | EARLIER_SIGNAL | 10 |
| C | LATER_SIGNAL | 10 |
| C | OPENING_GAP_MISMATCH | 8 |
| C | UNRESOLVED_DISCRETIONARY_SELECTION | 5 |
| C | MANUAL_JOURNAL_INCONSISTENCY | 5 |

## Earliest-cause classification (automated trades without a match)

| cfg | cause | trades |
|---|---|---|
| A | DIFFERENT_STRATEGY_SELECTED | 57 |
| A | UNRESOLVED_DISCRETIONARY_SELECTION | 27 |
| A | EARLIER_SIGNAL | 9 |
| A | LATER_SIGNAL | 9 |
| A | PORTFOLIO_CONTROLLER_CONSTRAINT | 7 |
| B | DIFFERENT_STRATEGY_SELECTED | 57 |
| B | UNRESOLVED_DISCRETIONARY_SELECTION | 24 |
| B | PORTFOLIO_CONTROLLER_CONSTRAINT | 12 |
| B | EARLIER_SIGNAL | 9 |
| B | LATER_SIGNAL | 8 |
| C | DIFFERENT_STRATEGY_SELECTED | 56 |
| C | UNRESOLVED_DISCRETIONARY_SELECTION | 24 |
| C | PORTFOLIO_CONTROLLER_CONSTRAINT | 12 |
| C | EARLIER_SIGNAL | 9 |
| C | LATER_SIGNAL | 8 |

## ORB mismatch analysis

The journal has 89 ORB rows; ORB is by far the largest source of manual-only rows. Matched ORB rows (strict): A 35, B 35, C 38. Causes of the unmatched ORB rows (primary, by the earliest failing predicate of the closest ORB method for the first candle's colour direction - the journal has no direction, so the direction is an ASSUMPTION): 

| cause | A | B | C |
|---|---|---|---|
| CANDLE_STRENGTH_MISMATCH | 22 | 22 | 27 |
| EMA_FILTER_MISMATCH | 5 | 5 | 1 |
| LEVEL_CONSTRUCTION_MISMATCH | 19 | 19 | 19 |
| MANUAL_JOURNAL_INCONSISTENCY | 4 | 4 | 4 |
| OPENING_GAP_MISMATCH | 4 | 4 | 0 |

**How to read this table.** The journal has no direction, so the closest of the three ORB methods (fewest failing predicates, for the direction implied by the first candle's colour) is used. Where several methods tie, the evidence does not single out one cause: the primary cause is then TIE-BROKEN by the fixed method order (Method 1, Method 2, Gap) and the other tied cause is given as the secondary cause. Rows flagged `TIE-BROKEN` in the evidence: A 28 of 54, B 28 of 54, C 24 of 51. The split between causes is therefore indicative, not a measurement.

* **CANDLE_STRENGTH_MISMATCH / LEVEL_CONSTRUCTION_MISMATCH dominate**: the first candle either fails the numeric 'strong candle' profile (the rulebook is qualitative) or breaks neither the previous-day extreme nor the engine's inner level (the rulebook draws multi-candle bands and the author's levels are unknown). Both are the unresolved Phase 5.4 constructions, not defects.
* **EMA_FILTER_MISMATCH / OPENING_GAP_MISMATCH**: the trend test (previous close against its EMA, an owner-approved variant of the rulebook's 'price above the 200 EMA') or the Gap-setup crossing reading rejects the day.
* **MANUAL_JOURNAL_INCONSISTENCY**: ORB rows dated on Saturdays (no session).
* **Configuration C** adds 3 ORB Gap / 200DMA trades through the candle-crossing reading; their journal status in C: {'20260327-1-ORB': 'STRICT', '20260715-1-ORB': 'STRICT', '20260813-1-ORB': 'STRICT'}. This is reported descriptively; C is a provisional scenario and the DMA-versus-EMA question is unresolved.

## IRF mismatch analysis

| cause (manual IRF rows without a match) | A | B | C |
|---|---|---|---|
| DIFFERENT_STRATEGY_SELECTED | 11 | 10 | 10 |
| EARLIER_SIGNAL | 9 | 10 | 10 |
| EMA_FILTER_MISMATCH | 0 | 9 | 9 |
| LATER_SIGNAL | 5 | 8 | 8 |
| MANUAL_JOURNAL_INCONSISTENCY | 1 | 1 | 1 |
| PORTFOLIO_CONTROLLER_CONSTRAINT | 1 | 0 | 0 |
| UNRESOLVED_DISCRETIONARY_SELECTION | 5 | 5 | 5 |

* **DIFFERENT_STRATEGY_SELECTED / PORTFOLIO_CONTROLLER_CONSTRAINT**: the controller's first-valid-signal rule took an earlier signal of another strategy (or the manual IRF entry fell inside a running position). **EARLIER_SIGNAL / LATER_SIGNAL**: an automated IRF signal exists but at another time (the IRF reference candle / first-red-candle / EMA conventions move it).
* **EMA_FILTER_MISMATCH** (B, C): the provisional 28-point EMA clearance rejected the candidate; **LEVEL_CONSTRUCTION_MISMATCH** (B, C; used for an IRF row only when A has a signal near the manual entry that B / C do not - see the table for how often): the first-red-candle LOW support moved or removed the Method 2A signal; **UNRESOLVED_DISCRETIONARY_SELECTION**: the engine saw no IRF setup (IRF-M1-003 boundary, Method 3 wick share and the unresolved day's-low rule are discretionary).

## PDR / PDS mismatch analysis

| strategy / cause | A | B | C |
|---|---|---|---|
| PDR DIFFERENT_STRATEGY_SELECTED | 1 | 1 | 1 |
| PDR LATER_SIGNAL | 3 | 1 | 1 |
| PDR LEVEL_CONSTRUCTION_MISMATCH | 1 | 1 | 1 |
| PDS DIFFERENT_STRATEGY_SELECTED | 0 | 1 | 1 |
| PDS LATER_SIGNAL | 2 | 1 | 1 |

The journal has only 8 PDR and 3 PDS rows. The earliest-confirmation conventions of B / C move PDR / PDS entries earlier; the remaining PDR / PDS differences are date-and-strategy time differences or controller selections.

## Strategy-selection differences

Dates on which the journal and the automated system traded DIFFERENT strategies only: A 57, B 57, C 56 (`wrong_strategy_dates.csv`). On these dates the automated controller's first valid signal belonged to another strategy than the manual choice; no priority was introduced to align them.

## Handwritten author corrections versus the three configurations

| status | A | B | C |
|---|---|---|---|
| ENTRY_EARLIER_THAN_A | 0 | 4 | 4 |
| ENTRY_UNCHANGED | 6 | 2 | 2 |
| GENERAL_REMARK | 2 | 2 | 2 |
| IRF_SIGNAL_REJECTED_OR_CHANGED | 0 | 2 | 2 |
| IRF_TRADE_CHANGED | 0 | 4 | 4 |
| IRF_TRADE_UNCHANGED | 8 | 4 | 4 |
| IRF_UNCHANGED | 2 | 0 | 0 |
| NOT_ADDRESSED_BY_THE_CONFIGURATIONS | 9 | 9 | 9 |
| ORB_STILL_NOT_TRADED | 12 | 12 | 12 |
| PENDING_OWNER_DEFINITION | 2 | 2 | 2 |
| STILL_TRADED_RED_CANDLE_LONG | 1 | 1 | 1 |

Per correction: `handwritten_author_corrections_comparison.csv`. The 12 corrections stating that ORB should have been traded still have no ORB trade in A, B and C (all dated 2025; C's three added ORB trades are on 2026-03-27, 2026-07-15, 2026-08-13, none on a disputed date).

## Reading the comparison

* Journal rows matched by a trade: A 87, B 78, C 81 of 190. B matches 9 fewer journal rows than A (strict IRF matches fall from 26 to 20; strict PDR matches rise from 0 to 4); C adds back 3 through its 3 added ORB trades, each of which strictly matches an ORB journal row. Match counts are descriptive; they are not an approval criterion and no configuration is chosen on them.
* A large part of the manual journal cannot be reproduced mechanically: the journal records discretionary entries (ORB on 89 rows against 41 / 41 / 44 automated ORB trades in A / B / C), and many automated trades have no manual counterpart (the controller trades the first valid signal of every session, whether or not the trader took it).
* Every mismatch has an earliest cause with evidence in `mismatch_root_causes.csv`; the rules were not rewritten to increase reconciliation.
