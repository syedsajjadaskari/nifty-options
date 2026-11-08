# ORB - the author's corrections (13 disputed dates, AC27)

Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

All 13 handwritten ORB remarks are plain text ('ORB should have activated instead of IRF'); the six handwritten pages contain NO ORB drawing, level, candle or direction (all six pages were read and rendered). The author never says which ORB method, which level or which direction. The first candle is GREEN on 12 of the 13 dates and RED on 1; IRF is a short-only strategy, so on the green days the system sold a market that opened with a strong green candle, and the only ORB that a green first candle can support is a LONG.

**The engine produced no confirmed ORB signal on any of the 13 dates** (15 ORB records exist on those dates, all invalidated; 0 confirmed). Because ORB decides at 09:20 and IRF can only fire later, ORB would already have priority by TIME under the controller's first-valid-signal rule: the dispute is an ORB QUALIFICATION problem, not a controller-priority problem.

## The 13 dates

| date | AC / hand page | author's words | first candle (colour, body %, wicks %) | open gap | ORB status | Phase 3.6 trade taken | manual journal row |
|---|---|---|---|---|---|---|---|
| 2025-09-11 | AC04 / p.1 | This should be an ORB trade. / It is shown as IRF, ORB should activate | GREEN, 97.7, 2.3/0.0 | -27.6 | Method 2 LONG: INVALIDATED (TRENDLINE_NOT_SUPPORTIVE) | IRF Method 1 09:30 SHORT @ 24985.2 | ORB 09:15 |
| 2025-09-16 | AC06 / p.2 | IRF is taken, which is wrong. / ORB should take place in this conditio | GREEN, 71.7, 9.2/19.1 | 10.3 | NO RECORD (no level broken / no gap crossing in either direc | IRF Method 2A 10:25 SHORT @ 25161.5 | ORB 09:15 |
| 2025-10-08 | AC12 / p.3 | This should be an ORB trade, but is shown as IRF. / ORB should activat | GREEN, 98.7, 1.3/0.0 | -28.55 | NO RECORD (no level broken / no gap crossing in either direc | IRF Method 2A 09:50 SHORT @ 25155.1 | ORB 09:15 |
| 2025-10-16 | AC14 / p.3 | ORB should have activated, instead IRF is activated. | GREEN, 26.7, 29.9/43.4 | 77.45 | Method 1 LONG: INVALIDATED (CANDLE_QUALITY(not a strong body | IRF Method 1 09:40 SHORT @ 25414.1 | ORB 09:15 |
| 2025-10-17 | AC15 / p.3 | ORB should have activated, instead IRF is activated. | GREEN, 22.9, 19.1/58.0 | -44.0 | Method 2 SHORT: INVALIDATED (TREND:EMA_PREV_SESSION_CLOSE wr | IRF Method 2A 11:45 SHORT @ 25742.05 | no journal row |
| 2025-10-27 | AC16 / p.3 | ORB should have activated, instead IRF is activated. / IRF activation  | GREEN, 19.1, 32.7/48.2 | 56.8 | Method 2 LONG: INVALIDATED (TREND:EMA_PREV_SESSION_CLOSE wro | IRF Method 2B 10:00 SHORT @ 25935.75 | ORB 09:15 |
| 2025-11-21 | AC24 / p.4 | ORB should have activated, but IRF is activated | GREEN, 49.7, 6.8/43.4 | -75.95 | Method 2 SHORT: INVALIDATED (TREND:EMA_PREV_SESSION_CLOSE wr | IRF Method 1 09:45 SHORT @ 26129.9 | IRF 09:40 |
| 2025-11-28 | AC28 / p.5 | ORB should be activated instead of IRF | GREEN, 6.4, 6.4/87.2 | 21.9 | Method 2 LONG: INVALIDATED (TRENDLINE_NOT_SUPPORTIVE) | IRF Method 1 09:40 SHORT @ 26211.0 | ORB 09:15 |
| 2025-12-05 | AC31 / p.5 | ORB should activate instead of IRF. | GREEN, 84.2, 0.0/15.8 | -32.6 | Gap/200DMA SHORT: INVALIDATED (CLOSE_NOT_BEYOND_MA) | IRF Method 1 09:55 SHORT @ 26042.15 | ORB 09:15 |
| 2025-12-12 | AC33 / p.5 | Should be ORB, But IRF is activated. | GREEN, 52.2, 0.7/47.1 | 84.2 | Method 1 LONG: INVALIDATED (CANDLE_QUALITY(not a strong body | IRF Method 2A 10:00 SHORT @ 26006.5 | ORB 09:15 |
| 2025-12-24 | AC37 / p.6 | ORB should be activated instead of IRF | GREEN, 24.3, 5.5/70.1 | 6.6 | NO RECORD (no level broken / no gap crossing in either direc | IRF Method 2B 10:20 SHORT @ 26225.3 | ORB 09:15 |
| 2025-12-30 | AC39 / p.6 | ORB should be activated instead of IRF. | RED, 76.2, 0.0/23.8 | 8.9 | Method 1 SHORT: INVALIDATED (CANDLE_QUALITY(not a strong bod | IRF Method 1 10:45 SHORT @ 25949.1 | ORB 09:15 |
| 2025-12-31 | AC40 / p.6 | ORB should activate first, Which hits SL Ep then PDR. / PDR 1st candle | GREEN, 74.3, 25.7/0.0 | 36.6 | Method 1 LONG: INVALIDATED (TREND:EMA_PREV_SESSION_CLOSE wro | PDR PDR 10:10 LONG @ 25994.35 | ORB 09:15 |

## What is missing on each date (first failing predicate per method, colour-matching direction)

| date | Method 1 | Method 2 | Gap / 200 DMA | relevant source rules | conflict with the existing code? |
|---|---|---|---|---|---|
| 2025-09-11 | level_broken | trendline | gap_in_direction | ORB-GAP-LONG-001; ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2- | YES: the closest method (Method 1, Method 2) is rejected by a condition the engine decides with a research assumption / numeric approximation / owner  |
| 2025-09-16 | level_broken | inner_level_broken | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2-LONG-001; ORB-M2-L | YES: the closest method (Method 1, Gap/200DMA) is rejected by a condition the engine decides with a research assumption / numeric approximation / owne |
| 2025-10-08 | level_broken | inner_level_broken | gap_in_direction | ORB-GAP-LONG-001; ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2- | NO conflict with an explicit source rule: the closest method fails an explicit source condition (level / gap not reached); the author's level is unkno |
| 2025-10-16 | candle_quality | trendline | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-GAP-LONG-004; ORB-M1-LONG-003; ORB-M2- | YES: the closest method (Method 1) is rejected by a condition the engine decides with a research assumption / numeric approximation / owner variant (N |
| 2025-10-17 | level_broken | inner_level_broken | gap_in_direction | ORB-GAP-LONG-001; ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2- | NO conflict with an explicit source rule: the closest method fails an explicit source condition (level / gap not reached); the author's level is unkno |
| 2025-10-27 | level_broken | trend | candle_shape | ORB-GAP-LONG-004; ORB-M1-LONG-002; ORB-M1-LONG-003; ORB-M2-L | YES: the closest method (Gap/200DMA) is rejected by a condition the engine decides with a research assumption / numeric approximation / owner variant  |
| 2025-11-21 | level_broken | inner_level_broken | gap_in_direction | ORB-GAP-LONG-001; ORB-GAP-LONG-002; ORB-GAP-LONG-004; ORB-M1 | UNDETERMINED: every method fails two or more predicates, so the author's setup cannot be identified; the engine violates no explicit source rule that  |
| 2025-11-28 | level_broken | trendline | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2-LONG-001 | YES: the closest method (Method 1, Method 2, Gap/200DMA) is rejected by a condition the engine decides with a research assumption / numeric approximat |
| 2025-12-05 | level_broken | inner_level_broken | gap_in_direction | ORB-GAP-LONG-001; ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2- | UNDETERMINED: every method fails two or more predicates, so the author's setup cannot be identified; the engine violates no explicit source rule that  |
| 2025-12-12 | candle_quality | trendline | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-GAP-LONG-004; ORB-M1-LONG-003; ORB-M2- | YES: the closest method (Method 1) is rejected by a condition the engine decides with a research assumption / numeric approximation / owner variant (N |
| 2025-12-24 | level_broken | inner_level_broken | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-M1-LONG-002; ORB-M2-LONG-002 | YES: the closest method (Method 1, Method 2, Gap/200DMA) is rejected by a condition the engine decides with a research assumption / numeric approximat |
| 2025-12-30 | candle_quality | candle_quality | gap_in_direction | ORB-GAP-SHORT-001; ORB-GAP-SHORT-002; ORB-GAP-SHORT-003; ORB | YES: the closest method (Method 1, Method 2) is rejected by a condition the engine decides with a research assumption / numeric approximation / owner  |
| 2025-12-31 | trend | trend | gap_crosses_200_average | ORB-GAP-LONG-002; ORB-GAP-LONG-004; ORB-M1-LONG-003; ORB-M2- | UNDETERMINED: every method fails two or more predicates, so the author's setup cannot be identified; the engine violates no explicit source rule that  |

The full per-date predicate table (observed value, rule, rule id, signed margin) for both directions is in `orb_predicate_matrix.csv`; the required definition per date is in `orb_13_disputed_dates.csv` (`required_correction_or_unresolved_definition`).

## Distribution of the missing conditions

| method | first failing predicate | dates |
|---|---|---|
| Method 1 | level_broken | 9 |
| Method 1 | candle_quality | 3 |
| Method 1 | trend | 1 |
| Method 2 | trendline | 4 |
| Method 2 | inner_level_broken | 6 |
| Method 2 | trend | 2 |
| Method 2 | candle_quality | 1 |
| Gap / 200 DMA | gap_in_direction | 6 |
| Gap / 200 DMA | gap_crosses_200_average | 6 |
| Gap / 200 DMA | candle_shape | 1 |

The causes are NOT one defect: Method 1's level is not broken on 9 dates (the first candle closes inside the previous day's range), the frozen Method 2 inner level is not broken on 6, the Method 2 trendline blocks 4, the trend filter blocks 2 (both are gap-ups through the EMA, i.e. Gap-setup territory), and the numeric candle thresholds block 3 (plus a 0.08-point open-versus-average tie on one date).

## Dates where the author's interpretation may conflict with the code

* **Numeric thresholds and research constructions (not source rules):** 2025-09-11, 2025-09-16, 2025-10-16, 2025-10-27, 2025-11-28, 2025-12-12, 2025-12-24, 2025-12-30 - the closest method is rejected by a trendline / strength / trend / gap-crossing rule that the engine decides with a research assumption.
* **Explicit source conditions not met:** 2025-10-08, 2025-10-17 - the closest method fails an explicit source condition (the first candle breaks neither the previous-day extreme nor the frozen inner level); the author's level is unknown (no drawing).
* **Unidentifiable:** 2025-11-21, 2025-12-05, 2025-12-31 - every method fails two or more predicates.

The author is not assumed correct about objective candle conditions: where the rulebook's own illustrations (p.3, p.10) show clean candles, the disputed candles are less clean (see `orb_candle_strength_review.md`).

## Two dates whose journal row differs from the handwritten correction

* 2025-11-21 (AC24: 'ORB should have activated, but IRF is activated'): the manual journal records an IRF trade at 09:40 (Target), not an ORB.
* 2025-10-17 (AC15): there is no journal row at all.

## AC27 - the ORB colour rule (2025-11-27)

The author wrote: 'ORB is activated on a red candle for long side, which is wrong. ORB for long should be in green closing.' The frozen engine produced a Method 1 LONG signal on a RED first candle (body 15%, lower wick 85%: it passes the owner-style bullish pin-bar test; the rulebook's text states no colour for the pin bar and its p.10 figure draws the pin bar green, so 'any colour' is the engine's reading, not a source statement). The Phase 5.1 colour rule (long needs a green first candle, short a red one) removes 3 frozen ORB signals (53 -> 50), including AC27's, and none of those dates carries a manual ORB journal row (a date overlap only; the journal has no direction). The LONG half has explicit author evidence (AC27); the SHORT half (red first candle for shorts) is an interpretation of 'the same rules in both directions' (ORB-GLOBAL-002) and is NOT activated here.
