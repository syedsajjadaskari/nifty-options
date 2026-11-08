# Signal validation (before execution)

SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill).

Every configuration was run through the same unchanged Phase 3.1 / 3.2 pipeline (engines -> shared controller -> exit policy); only the engine factory differs. The run STOPS (nothing is written as verified) on any of: a frozen-baseline mismatch, a signal total different from the expected reference, a duplicate or off-grid timestamp, a signal difference outside the rules a configuration changes, or a failed entry check not explained by a configuration's own rule. None of these occurred.

## Baseline reproduction (configuration A)

A reproduces the Phase 3.6 results field for field: 196 trades (Phase 3.6: 196), 1083 signals (Phase 3.6: 1083), 64 compared trade columns with 0 mismatches, gross synthetic P&L Rs 297,765 (Phase 3.6: Rs 297,765). On the 2022-09-01..2025-08-31 window A also reproduces the delivered Phase 4 window-B backtest (609 trades, identical gross P&L).

## Frozen identity

`FROZEN-PHASE36-42cea2600bd4` was recomputed from the stored hashes, parameters and costs (FROZEN-PHASE36-42cea2600bd4); all 26 active implementation files match their frozen hashes; the live parameters equal the frozen parameters.

## Confirmed signals

| configuration | id | total | IRF | ORB | PDR | PDS | RF | expected | matches |
|---|---|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | FROZEN-PHASE36-42cea2600bd4 | 1083 | 874 | 53 | 87 | 57 | 12 | 1083 | True |
| B - Phase 5.3 author-corrected | PHASE55-B-a3ca4d04dd11 | 1109 | 786 | 53 | 147 | 111 | 12 | 1109 | True |
| C - B + ORB gap crossing | PHASE55-C-144ceb6b28b1 | 1112 | 786 | 56 | 147 | 111 | 12 | B + 3 ORB | n/a (C = B + exactly 3 ORB signals, audit-verified) |

## Validation checks

| check | A | B | C |
|---|---|---|---|
| duplicate signals | 0 | 0 | 0 |
| signals off the 5-minute grid | 0 | 0 | 0 |
| signals before 09:20 | 0 | 0 | 0 |
| signals at or before 13:00 (actionable) | 717 | 738 | 741 |
| signals after 13:00 (post-cutoff; not tradable) | 366 | 371 | 371 |
| same-minute groups with more than one strategy at ANY time of day / of those at or before 13:00 (only these can collide at execution; a collision on a day without an earlier position is an UNRESOLVED day under the approved convention) | 18 / 11 | 15 / 8 | 15 / 8 |
| entry checks that FAIL (all explained below) | 0 | 51 | 53 |
| executed / ignored (position active or day finished) / rejected / conflict / merged (same strategy and method) signals | 196 / 599 / 265 / 5 / 18 = 1083 | 188 / 652 / 235 / 2 / 32 = 1109 | 190 / 653 / 235 / 2 / 32 = 1112 |

The independent audit confirms for all 3,304 signals that the signal candle exists in the raw data, its close equals the reference close, and the signal time is the candle's END on the 5-minute grid (no signal precedes its candle's completion).

## Entry checks that fail by design

The Phase 3.2 explainer checks every executed trade against the FROZEN rules. Where a configuration deliberately replaces a rule, the corresponding check fails; every failure below is explained by the configuration's own change (an unexplained failure stops the run):

| configuration | strategy / rule | failing checks | explanation |
|---|---|---|---|
| B | IRF IRF-M2A-001 | 21 | IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes |
| B | IRF IRF-M2A-002 | 4 | IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes |
| B | PDR PDR-B04 | 17 | PDR minimal confirmation (Phase 5.3) replaces the frozen numeric pattern thresholds the check encodes |
| B | PDS PDS-M1-001 | 6 | PDS structural dominance test (Phase 5.3) replaces the frozen numeric good-red thresholds the check encodes |
| B | PDS PDS-M2-001 | 3 | PDS structural dominance test (Phase 5.3) replaces the frozen numeric pin-bar thresholds the check encodes |
| C | IRF IRF-M2A-001 | 20 | IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes |
| C | IRF IRF-M2A-002 | 4 | IRF Method 2A support = LOW of the first red candle (Phase 5.3) replaces the frozen swing-low support the check encodes |
| C | ORB ORB-GAP-LONG-002 | 1 | ORB gap candle-crossing candidate (Phase 5.4): the candle, not the open, crosses the average; the frozen check requires the open beyond it |
| C | ORB ORB-GAP-SHORT-002 | 2 | ORB gap candle-crossing candidate (Phase 5.4): the candle, not the open, crosses the average; the frozen check requires the open beyond it |
| C | PDR PDR-B04 | 17 | PDR minimal confirmation (Phase 5.3) replaces the frozen numeric pattern thresholds the check encodes |
| C | PDS PDS-M1-001 | 6 | PDS structural dominance test (Phase 5.3) replaces the frozen numeric good-red thresholds the check encodes |
| C | PDS PDS-M2-001 | 3 | PDS structural dominance test (Phase 5.3) replaces the frozen numeric pin-bar thresholds the check encodes |

## Signal differences between configurations

| comparison | differences by strategy and side |
|---|---|
| A_vs_B | IRF:ONLY_IN_A: 391; IRF:ONLY_IN_B: 303; PDR:ONLY_IN_A: 26; PDR:ONLY_IN_B: 86; PDS:ONLY_IN_A: 20; PDS:ONLY_IN_B: 74 |
| A_vs_C | IRF:ONLY_IN_A: 391; IRF:ONLY_IN_C: 303; ORB:ONLY_IN_C: 3; PDR:ONLY_IN_A: 26; PDR:ONLY_IN_C: 86; PDS:ONLY_IN_A: 20; PDS:ONLY_IN_C: 74 |
| B_vs_C | ORB:ONLY_IN_C: 3 |

* A vs B: differences are confined to IRF, PDR and PDS (the three strategies Phase 5.3 changed); ORB and RF are identical (enforced by the run). IRF: first-red-candle LOW support and the 28-point EMA gate remove 391 and add 303 signals; PDR / PDS: the minimal earliest-confirmation conventions let the setup re-arm more often (more signals; a count increase is not an improvement).
* B vs C: exactly three ORB Gap / 200DMA signals are added and nothing else (enforced by the run; each re-derived independently from the raw candles).

Full list: `signal_differences.csv` (every signal that exists in one configuration only, with its time and levels); every signal with `all_confirmed_signals.csv` (controller disposition per signal).

## Simultaneous signals

Same-minute signals of different strategies are not resolved by any approved tie-break; the controller marks the day UNRESOLVED_EXECUTION and trades nothing. Final day states: A: {'DAY_FINISHED': 123, 'SECOND_TRADE_ELIGIBLE': 65, 'READY_FOR_FIRST_TRADE': 57, 'UNRESOLVED_EXECUTION': 2}; B: {'DAY_FINISHED': 115, 'SECOND_TRADE_ELIGIBLE': 60, 'READY_FOR_FIRST_TRADE': 71, 'UNRESOLVED_EXECUTION': 1}; C: {'DAY_FINISHED': 116, 'SECOND_TRADE_ELIGIBLE': 61, 'READY_FOR_FIRST_TRADE': 69, 'UNRESOLVED_EXECUTION': 1}. Groups (first 8 per configuration):

| configuration | same-minute multi-strategy signals |
|---|---|
| A | 2025-09-22 14:00: IRF/Method 1/SHORT, IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-11-07 14:05: IRF/Method 2A/SHORT, IRF/Method 2B/SHORT, PDS/Method 3/SHORT; 2025-11-14 09:55: IRF/Method 1/SHORT, PDS/Method 1/SHORT; 2025-11-14 13:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-12-09 12:40: IRF/Method 1/SHORT, PDS/Method 3/SHORT; 2025-12-09 14:05: IRF/Method 1/SHORT, PDS/Method 3/SHORT; 2026-01-06 10:40: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2026-04-13 15:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT |
| B | 2025-09-22 11:25: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-11-03 10:10: IRF/Method 2A/SHORT, PDS/Method 1/SHORT; 2025-11-07 14:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-11-14 13:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-12-09 12:20: IRF/Method 1/SHORT, PDS/Method 1/SHORT; 2025-12-09 12:35: IRF/Method 2A/SHORT, IRF/Method 2B/SHORT, PDS/Method 1/SHORT; 2025-12-09 12:40: IRF/Method 1/SHORT, PDS/Method 1/SHORT; 2025-12-09 13:45: IRF/Method 2B/SHORT, PDS/Method 1/SHORT |
| C | 2025-09-22 11:25: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-11-03 10:10: IRF/Method 2A/SHORT, PDS/Method 1/SHORT; 2025-11-07 14:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-11-14 13:05: IRF/Method 2A/SHORT, PDS/Method 3/SHORT; 2025-12-09 12:20: IRF/Method 1/SHORT, PDS/Method 1/SHORT; 2025-12-09 12:35: IRF/Method 2A/SHORT, IRF/Method 2B/SHORT, PDS/Method 1/SHORT; 2025-12-09 12:40: IRF/Method 1/SHORT, PDS/Method 1/SHORT; 2025-12-09 13:45: IRF/Method 2B/SHORT, PDS/Method 1/SHORT |
