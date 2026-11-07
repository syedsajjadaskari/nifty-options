# PDR - first eligible confirmation candle (audit)

Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

**Requirement (USER_APPROVED):** the first completed candle after all required conditions are satisfied (previous-day body-based zone, open strictly above its ceiling, retest of the zone, an approved pattern, close strictly above the ceiling) activates the signal at ITS close; no later or stronger candle may replace it; nothing before the retest; no incomplete candle.

**Result: no late entry relative to the PRESERVED rules (PDR-A07 retest convention, the proposed numeric thresholds).** Of 140 gap-up sessions, 67 opened strictly above the zone and 42 of those retested it ('armed'); of the armed setups 33 of them produced a signal; in every one the engine's signal is on the first eligible candle (verdicts: {'NO_SIGNAL_EITHER': 107, 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE': 33}). `LATE_ENTRY_DEFECT` count: **0**. Caveat: the setup diagnostics reuse the engine's state machine and pattern functions, so that flag cannot fire by construction; the check with independent value is `scripts/phase52_independent_audit.py` (and the fresh reviewer), which re-derived the zone (highest body high of the previous session), the gap, the retest and the three pattern tests from the raw one-minute data and agrees on every session.

## Why the engine already satisfies the principle

`PDRBodyStrategy._scan` records the first candle whose range meets the zone as the retest, then tests each LATER completed candle in order and activates on the first one that passes a pattern AND closes strictly above the ceiling; the state machine then resets. A later or stronger candle can never replace it. The fill is the next one-minute open (EXE-FILL-001), after the candle has closed.

## What the author's handwritten 'first green candle' examples show

In the five PDR examples (AC02, AC10, AC11, AC29, AC40) the candle the author points at is NOT eligible under the preserved rules: either it is the retest candle itself (convention PDR-A07, a proposal) or it fails the proposed numeric patterns. **The author's example is therefore NOT satisfied; what is satisfied is the first-eligible principle under the preserved proposals.** The PDR guide's own words ('after the zone has been tested, wait for a green candle'; 'green candle formed after the interaction') partly support PDR-A07, but it gives no numeric thresholds.

| date | correction | zone | retest (first touch) candle | engine first signal | author's first green candle | why earlier candles were not eligible |
|---|---|---|---|---|---|---|
| 2025-09-02 | AC02 | 24625.1-24632.25 | 09:25 | 09:35 | 09:25 (body 57.3%, upper wick 1.6%, lower wick 41.1%) | 09:25: IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle) |
| 2025-10-06 | AC10 | 24896.1-24899.8 | 09:20 | 09:40 | 09:30 (body 31.9%, upper wick 10.9%, lower wick 57.2%) | 09:20: IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle) // 09:25: NO_PATTERN: GOOD_GREEN_BODY[not green] / LOWER_PRICE_REJECTION[lower wick < 2x body; close not in top 30% of range] / HAMMER[lower wick < 2x body; body not in upper part] // 09:30: |
| 2025-10-07 | AC11 | 25072.4-25084.7 | 09:15 | 09:40 | 09:20 (body 63.1%, upper wick 21.7%, lower wick 15.2%) | 09:15: IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle) // 09:20: NO_PATTERN: GOOD_GREEN_BODY[upper wick above maximum] / LOWER_PRICE_REJECTION[lower wick < 2x body] / HAMMER[lower wick < 2x body; upper wick above maximum; body not in upper part] |
| 2025-12-01 | AC29 | 26267.85-26274.45 | 09:15 | 09:35 | 09:20 (body 36.2%, upper wick 32.6%, lower wick 31.3%) | 09:15: IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle) // 09:20: NO_PATTERN: GOOD_GREEN_BODY[body below minimum; upper wick above maximum] / LOWER_PRICE_REJECTION[lower wick < 2x body; close not in top 30% of range; low did not reach the zone] / |
| 2025-12-31 | AC40 | 25965.95-25973.7 | 09:40 | 10:10 | 09:45 (body 49.7%, upper wick 26.9%, lower wick 23.4%) | 09:40: IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle) // 09:45: NO_PATTERN: GOOD_GREEN_BODY[body below minimum; upper wick above maximum] / LOWER_PRICE_REJECTION[lower wick < 2x body] / HAMMER[lower wick < 2x body; upper wick above maximum; bod |

## Sensitivity (diagnostics only; NOT activated): how much earlier would entries be under looser readings?

Over the 42 armed setups (zone retested), counting setups whose entry would come earlier than the engine's, or where the engine has no signal:

| reading of 'first eligible' | setups earlier or newly signalled | of which the engine has a signal | of which the engine has none |
|---|---|---|---|
| A: approved patterns, but the retest candle itself may confirm | 8 | 6 | 2 |
| B: first GREEN candle after the retest that closes above the ceiling, no numeric thresholds (the guide's wording) | 24 | 21 | 3 |
| C: as B, retest candle also allowed | 29 | 26 | 3 |

Per-session times are in `pdr_first_eligible_setups.csv` (`sensA_...`, `sensB_...`, `sensC_...`). The shifts are not 'one candle': in several sessions the retest candle at the open would qualify and the engine's own entry comes 5 to 60 minutes later. These readings change entries a lot and are decisions for the owner (O6, O7), not defects.

Per-candle reasons for every setup are in `pdr_first_eligible_setups.csv` (`reasons_earlier_candles_not_eligible`) and `pdr_setup_diagnostics.json`.

## Preserved conventions (labelled, not changed)

* The confirmation candle may not be the retest candle (PDR-A07, PROPOSED). In 8 armed setups the retest candle itself would have qualified (see the sensitivity table for the resulting times: from 5 to 60 minutes earlier). That is a new permission and is NOT made here (decision O7).
* The numeric pattern thresholds are the Phase 3.6 research values (PROPOSED). The author's examples suggest they may be too strict; changing them is an owner decision (O6).

## Diagnostics recorded for every PDR setup

zone construction timestamp (candle that made the zone), zone floor / ceiling, opening-gap eligibility, first zone-touch candle, first eligible confirmation candle, the chosen entry, every later confirmation ignored, and the reason each earlier candle was not eligible (columns of `pdr_first_eligible_setups.csv`).
