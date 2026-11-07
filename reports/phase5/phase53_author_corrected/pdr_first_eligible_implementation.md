# PDR - earliest eligible confirmation (implementation)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

## Preserved

Previous-day body-based resistance zone; the session must open strictly above the zone ceiling; a gap up; the **retest** (the first candle whose range meets the zone) must come first and **the retest candle itself may not confirm** (sequencing unresolved, preserved); the confirmation must close strictly above the zone ceiling; chronological processing; the 13:00 cutoff. Gap and zone requirements are unchanged.

## Replaced (`PROVISIONAL_PDR_MINIMAL_CONFIRMATION`)

The numeric thresholds (body 60% / wick 20% / 2x / 30% / 10% / 60%) were PROPOSED research values; the author's own note says no fixed percentage or wick size is required, and the PDR guide says: *"After the zone has been tested, wait for a green candle and take the long entry on that confirmation"* (s.4.3). The smallest transparent convention is therefore:
* `GOOD_GREEN_BODY`: a green candle (close > open), any size;
* `LOWER_PRICE_REJECTION` (covers the hammer): a candle of any colour whose lower wick is strictly larger than both its body and its upper wick and whose low reached the zone;
* in both cases the close must be **strictly above the zone ceiling**. A green candle that closes at or below the ceiling, that is the retest candle, or that comes before the retest is **not** eligible.

The first eligible candle activates the signal at its close; the fill is the next executable one-minute open (existing execution engine); a later or stronger candle never replaces it.

## Effect (2025-09-01..2026-08-31)

| armed sessions only (opened above the zone and retested it): first PDR signal | sessions |
|---|---|
| armed setups (retest happened) | 42 |
| same first signal | 18 |
| **earlier first signal** | 21 |
| newly signalled (no PDR signal before) | 3 |
| later | 0 |
| removed | 0 |

Signal level (every re-armed signal): Phase 3.6 87 -> Phase 5.3 147 (64 earlier, 60 newly generated, 23 unchanged). The engine re-arms after a confirmation, so a looser confirmation yields more re-armed signals; the controller still takes only the first valid signal of the day, and a count increase is not an improvement.

Patterns behind the Phase 5.3 PDR signals (`patterns_passed`): first signal of each session {'GOOD_GREEN_BODY': 32, 'GOOD_GREEN_BODY+LOWER_PRICE_REJECTION': 2, 'LOWER_PRICE_REJECTION': 2}; all re-armed signals {'GOOD_GREEN_BODY': 132, 'GOOD_GREEN_BODY+LOWER_PRICE_REJECTION': 12, 'LOWER_PRICE_REJECTION': 3}. The rejection pattern is an addition beyond the guide's 'wait for a green candle' (it comes from the author's Phase 3.4 statement 'one good green body candle OR lower price rejection OR hammer'); the counts show how often it alone is the trigger.

The diagnostic re-derivation agrees with the engine on every session (sessions where they differ: 0), and the independent audit re-derives the same first signals from the raw candles.

## The eight retest-candle setups (separately reported)

Phase 5.2 found 8 armed setups whose retest candle itself would have qualified under the old thresholds. They are **not** changed (the retest candle may not confirm). With the new minimal convention 16 armed setups have a retest candle that would qualify.

| date | retest candle | Phase 3.6 first signal | Phase 5.3 first signal | if the retest candle were allowed |
|---|---|---|---|---|
| 2025-11-17 | 09:15 25940.6/25952.05/25906.6/25951.05 | 10:20 | 09:30 | 09:20 |
| 2025-11-27 | 09:15 26261.25/26261.25/26210.85/26253.6 | 10:00 | 09:25 | 09:20 |
| 2025-12-19 | 09:15 25911.5/25938.25/25884.3/25925.1 | 09:25 | 09:25 | 09:20 |
| 2026-01-05 | 09:15 26341.9/26350.4/26306.65/26340.25 | 10:20 | 10:15 | 09:20 |
| 2026-01-22 | 10:30 25292.9/25314.4/25246.4/25310.85 | none | 10:45 | 10:35 |
| 2026-01-28 | 09:15 25248.6/25336.15/25227.65/25336.0 | 10:25 | 09:25 | 09:20 |
| 2026-02-10 | 09:15 25912.85/25934.45/25871.45/25918.05 | 09:25 | 09:25 | 09:20 |
| 2026-02-11 | 09:15 26000.65/26000.65/25949.1/25985.0 | none | none | 09:20 |

## The five handwritten PDR examples

| correction | date | author's first green candle | retest candle | Phase 5.3 first eligible candle | status |
|---|---|---|---|---|---|
| AC02 | 2025-09-02 | 09:25 | 09:25 | 09:30 | NOT_RECONCILED_RETEST_CONVENTION |
| AC10 | 2025-10-06 | 09:30 | 09:20 | 09:30 | RECONCILED |
| AC11 | 2025-10-07 | 09:20 | 09:15 | 09:20 | RECONCILED |
| AC29 | 2025-12-01 | 09:20 | 09:15 | 09:20 | RECONCILED |
| AC40 | 2025-12-31 | 09:45 | 09:40 | 09:45 | RECONCILED |

AC10, AC11, AC29 and AC40 now enter on the author's first green candle. AC02's candle is the retest candle itself; reconciling it requires allowing same-candle retest and confirmation, which the brief forbids without a source-proven rule (owner decision O7).

## Remaining decisions

O7: retest/confirmation sequencing; O6: whether the green-candle convention (and the rejection definition) is what the author means.
