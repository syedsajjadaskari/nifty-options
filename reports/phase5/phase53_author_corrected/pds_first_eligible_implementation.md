# PDS - earliest eligible confirmation (implementation)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

## Preserved (source-defined)

Previous-day support zone; gap-down open below the zone; the retest; the guide's sequence: *Methods 1 and 2 apply to the first red candle at the zone. If that red candle is not satisfying, use Method 3*; the **quality rule** *'do not take a weak red candle ... wait for a small support to form and break (Method 3)'*; Method 3's mandatory small-support break (pivot low, close below); the 13:00 cutoff.

## Replaced (`PROVISIONAL_PDS_MINIMAL_QUALITY`)

The guide lists 'what counts as a good red candle' and the pin-bar definition as open items ('body size and close are not numerically defined'); the 60% / 20% / 2x / 30% values were PROPOSED research numbers. They are replaced by structural dominance tests (no percentage, but an implicit threshold):
* **Method 1**: a red candle whose body is strictly larger than each of its wicks;
* **Method 2**: a red candle whose upper wick is strictly larger than its body and its lower wick, with the high reaching the zone;
* anything else is a weak candle: **Method 3**.
The two tests are mutually exclusive, so no candle confirms two methods (one actionable signal). These tests contain no percentage but are an implicit threshold (a body larger than each wick means a body above roughly a third of the range; a candle with body 37% and wicks 29% / 34% passes as 'good'; a pin with body 28% and wicks 41% / 31% passes), so they are NOT parameter-free and remain provisional (O6). The weak-red distinction is NOT removed: accepting the author's 'first candle entry' on a weak candle would override a source-defined rule, so it is flagged for approval instead.

## Effect (2025-09-01..2026-08-31)

| session level (first PDS signal of the session) | sessions |
|---|---|
| gap-down sessions with a zone retest and a red candle at the zone (ARMED) | 25 |
| gap-down sessions listed in total (incl. no retest / no red candle) | 45 |
| same first signal | 14 |
| **earlier first signal** | 11 |
| later | 0 |
| newly signalled / removed | 0 / 0 |

Signal level (every re-armed signal): Phase 3.6 57 -> Phase 5.3 111 (69 newly generated, 15 removed, 6 earlier, 4 later). A confirmation re-arms the setup, so a more permissive Method 1 test produces more re-armed signals; the controller takes only the first valid signal of the day (and a second PDS only after a full initial stop). Verdicts of the first red candle at the zone: {'WEAK': 5, 'RED_PIN': 4, 'GOOD_RED': 16}.

## The 20 sessions with a later strong red candle after a weak first red (Phase 5.2)

Re-evaluated under the Phase 5.3 reading: **10 first red candles are newly eligible** (weak under the frozen numbers, eligible under the structural tests; confirmation moves earlier), **5 were already eligible under the frozen thresholds** (strong or pin; unchanged) and **5 remain weak** (Method 3, small-support break mandatory; the later strong candles are not used). 5 of the twenty sessions were therefore never 'weak first red' cases under the frozen numbers; they appear in the Phase 5.2 list because a later strong red candle also exists.

| date | first red candle | body / wicks % | eligible now? | method | support break mandatory | original | new | reason if still rejected |
|---|---|---|---|---|---|---|---|---|
| 2025-09-22 | 09:50 25315.25/25317.35/25284.65/25305.1 | 31.0 / 6.4 / 62.5 | WEAK(Method 3 path - source quality rule) | Method 3 (mandatory small-support break) | True | 11:25 Method 3 | 11:25 Method 3 | first red candle 09:50 is weak (body 31.0%, wicks 6.4% / 62.5%: the body does not exceed both wicks and it is not a red pin bar). Source quality rule (PDS guide |
| 2025-11-03 | 09:15 25694.1/25737.45/25659.2/25687.85 | 8.0 / 55.4 / 36.6 | RED_PIN(Method 2) | Method 2 | False | 12:15 Method 3 | 09:20 Method 2 |  |
| 2025-11-07 | 12:50 25486.2/25502.35/25474.75/25478.45 | 28.1 / 58.5 / 13.4 | RED_PIN(Method 2) | Method 2 | False | 12:55 Method 2 | 12:55 Method 2 |  |
| 2025-11-14 | 09:20 25811.1/25811.1/25783.55/25788.7 | 81.3 / 0.0 / 18.7 | GOOD_RED(Method 1) | Method 1 | False | 09:25 Method 1 | 09:25 Method 1 |  |
| 2025-12-09 | 12:15 25893.1/25896.15/25887.45/25888.15 | 56.9 / 35.1 / 8.0 | GOOD_RED(Method 1) | Method 1 | False | 12:40 Method 3 | 12:20 Method 1 |  |
| 2025-12-18 | 09:25 25796.3/25804.35/25780.05/25780.05 | 66.9 / 33.1 / 0.0 | GOOD_RED(Method 1) | Method 1 | False | 09:30 Method 1 | 09:30 Method 1 |  |
| 2025-12-26 | 09:25 26134.35/26139.85/26125.4/26132.85 | 10.4 / 38.1 / 51.6 | WEAK(Method 3 path - source quality rule) | Method 3 (mandatory small-support break) | True | 09:55 Method 3 | 09:55 Method 3 | first red candle 09:25 is weak (body 10.4%, wicks 38.1% / 51.6%: the body does not exceed both wicks and it is not a red pin bar). Source quality rule (PDS guid |
| 2026-01-06 | 09:35 26217.35/26229.3/26193.4/26200.0 | 48.3 / 33.3 / 18.4 | GOOD_RED(Method 1) | Method 1 | False | 10:40 Method 3 | 09:40 Method 1 |  |
| 2026-01-21 | 09:20 25239.2/25240.2/25185.95/25221.4 | 32.8 / 1.8 / 65.3 | WEAK(Method 3 path - source quality rule) | Method 3 (mandatory small-support break) | True | 10:25 Method 3 | 10:25 Method 3 | first red candle 09:20 is weak (body 32.8%, wicks 1.8% / 65.3%: the body does not exceed both wicks and it is not a red pin bar). Source quality rule (PDS guide |
| 2026-02-16 | 09:25 25482.6/25484.45/25453.65/25472.25 | 33.6 / 6.0 / 60.4 | WEAK(Method 3 path - source quality rule) | Method 3 (mandatory small-support break) | True |  |  | first red candle 09:25 is weak (body 33.6%, wicks 6.0% / 60.4%: the body does not exceed both wicks and it is not a red pin bar). Source quality rule (PDS guide |
| 2026-04-02 | 14:25 22673.85/22684.3/22645.85/22665.65 | 21.3 / 27.2 / 51.5 | WEAK(Method 3 path - source quality rule) | Method 3 (mandatory small-support break) | True |  |  | first red candle 14:25 is weak (body 21.3%, wicks 27.2% / 51.5%: the body does not exceed both wicks and it is not a red pin bar). Source quality rule (PDS guid |
| 2026-04-13 | 14:00 23893.05/23897.3/23882.6/23887.6 | 37.1 / 28.9 / 34.0 | GOOD_RED(Method 1) | Method 1 | False | 15:05 Method 3 | 14:05 Method 1 |  |
| 2026-05-18 | 13:05 23645.9/23647.25/23605.25/23610.35 | 84.6 / 3.2 / 12.1 | GOOD_RED(Method 1) | Method 1 | False | 13:10 Method 1 | 13:10 Method 1 |  |
| 2026-05-20 | 11:30 23599.95/23607.95/23588.55/23594.5 | 28.1 / 41.2 / 30.7 | RED_PIN(Method 2) | Method 2 | False | 12:10 Method 3 | 11:35 Method 2 |  |
| 2026-05-27 | 09:30 23903.95/23903.95/23869.75/23881.2 | 66.5 / 0.0 / 33.5 | GOOD_RED(Method 1) | Method 1 | False | 13:20 Method 3 | 09:35 Method 1 |  |
| 2026-06-11 | 10:20 23183.15/23191.5/23174.7/23176.9 | 37.2 / 49.7 / 13.1 | RED_PIN(Method 2) | Method 2 | False | 14:45 Method 3 | 10:25 Method 2 |  |
| 2026-06-23 | 09:40 24126.4/24133.05/24109.45/24114.85 | 48.9 / 28.2 / 22.9 | GOOD_RED(Method 1) | Method 1 | False | 10:30 Method 3 | 09:45 Method 1 |  |
| 2026-07-13 | 10:00 24121.05/24128.65/24105.2/24110.1 | 46.7 / 32.4 / 20.9 | GOOD_RED(Method 1) | Method 1 | False | 10:55 Method 3 | 10:05 Method 1 |  |
| 2026-07-23 | 10:10 23966.6/23968.0/23955.75/23957.35 | 75.5 / 11.4 / 13.1 | GOOD_RED(Method 1) | Method 1 | False | 10:15 Method 1 | 10:15 Method 1 |  |
| 2026-08-18 | 09:30 24245.1/24246.4/24220.65/24232.65 | 48.3 / 5.0 / 46.6 | GOOD_RED(Method 1) | Method 1 | False | 10:50 Method 3 | 09:35 Method 1 |  |

## AC38 (2025-12-26, 'First candle entry')

AC38: NOT_RECONCILED_CONFLICT_WITH_SOURCE_RULE - the author's 'first candle entry' is a weak first red candle; the PDS guide says do not take a weak red candle (Method 3); flagged for owner approval rather than overridden.

## Remaining decisions

O6: may a weak first red candle be taken directly (overriding the guide's quality rule and Method 3)? Are the structural quality tests what the author means by a 'good' red candle?
