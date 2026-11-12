# Previous-day levels research (ORB V2)

The rulebook says breaking ANY one previous-day resistance/support, major or inner, is enough, but states that how levels are found 'is not yet defined'. Therefore:

* **Major** = the previous trading day's high / low (single prices, from completed previous-session candles).
* **Inner, SWING_FRACTAL_WICK_ZONE** (configs A, B, D): every confirmed swing high/low (2 candles each side) except the day extreme; resistance zone = [body top, high], support zone = [low, body bottom].
* **Inner, CLUSTER_ZONE** (config C): repeated rejection - at least two swing extremes of the same side within 10 points form one zone [min, max].

Both are PROVISIONAL mechanical constructions; neither is claimed to be the author's method and neither was chosen on profitability or journal agreement. Other source-plausible constructions (body-only zones, multi-candle consolidation boundaries, trendline-like levels) were not built.

## How binding is the level filter?

| window | config | sessions_with_direction | level_test_passed | pass_rate_pct | MAJOR_ONLY | INNER_ONLY | MAJOR_AND_INNER | avg_levels_per_side | sole_failed_gate_is_LEVEL | signals |
|---|---|---|---|---|---|---|---|---|---|---|
| A | ORB-V2-A | 247 | 221 | 89.5 | 0 | 113 | 108 | 9.6 | 3 | 39 |
| A | ORB-V2-B | 247 | 221 | 89.5 | 0 | 113 | 108 | 9.6 | 4 | 39 |
| A | ORB-V2-C | 247 | 201 | 81.4 | 2 | 93 | 106 | 3.3 | 5 | 37 |
| A | ORB-V2-D | 247 | 221 | 89.5 | 0 | 113 | 108 | 9.6 | 3 | 34 |
| A | DIAG-A-OLDSIDE | 247 | 61 | 24.7 | 7 | 38 | 16 | 9.6 | 15 | 27 |
| B | ORB-V2-A | 738 | 649 | 87.9 | 0 | 353 | 296 | 9.8 | 10 | 93 |
| B | ORB-V2-B | 738 | 649 | 87.9 | 0 | 353 | 296 | 9.8 | 10 | 94 |
| B | ORB-V2-C | 738 | 568 | 77.0 | 1 | 272 | 295 | 3.4 | 18 | 85 |
| B | ORB-V2-D | 738 | 649 | 87.9 | 0 | 353 | 296 | 9.8 | 10 | 85 |
| B | DIAG-A-OLDSIDE | 738 | 158 | 21.4 | 22 | 112 | 24 | 9.8 | 44 | 59 |


Reading (this follows from the PROVISIONAL construction: every k=2 swing counts as an inner level, giving roughly eight levels per side, so almost any close beyond the lowest swing passes; under a 'major level only' reading the filter would be far more selective): with the literal 'close beyond the level' wording, a BUY close only has to exceed ONE previous-day swing high / zone ceiling, so the filter rejects mainly days that open and close below almost every previous-day level. The **old-side diagnostic** (DIAG-A-OLDSIDE: the candle must open at or beyond the old side and close beyond the level - i.e. actually *cross* it) is far more selective. Which reading the author means is the largest source of difference in trade count and is unresolved; it is deliberately NOT chosen on results.

## Signal differences versus config A

| window | versus_A | signals_only_in_A | signals_only_in_other | dates_only_in_A | dates_only_in_other |
|---|---|---|---|---|---|
| A | ORB-V2-B | 0 | 0 |  |  |
| A | ORB-V2-C | 2 | 0 | 2026-04-17, 2026-08-13 |  |
| A | ORB-V2-D | 5 | 0 | 2025-11-11, 2026-01-27, 2026-04-17, 2026-06-10, 2026-07-21 |  |
| A | DIAG-A-OLDSIDE | 12 | 0 | 2025-09-05, 2025-10-01, 2025-11-17, 2025-11-28, 2025-12-29, 2026-01-28, 2026-02-12, 2026-03-12, 2026-03-25, 2026-04-16, 2026-04-30, 2026-07-02 |  |
| B | ORB-V2-B | 0 | 1 |  | 2022-09-01 |
| B | ORB-V2-C | 8 | 0 | 2023-08-29, 2023-10-16, 2024-03-14, 2024-06-05, 2024-08-08, 2024-11-18, 2025-03-10, 2025-07-21 |  |
| B | ORB-V2-D | 8 | 0 | 2022-10-28, 2023-01-02, 2023-01-06, 2024-09-26, 2025-02-07, 2025-03-07, 2025-03-10, 2025-05-15 |  |
| B | DIAG-A-OLDSIDE | 34 | 0 | 2022-09-20, 2022-09-28, 2022-10-31, 2022-12-01, 2023-01-02, 2023-01-06, 2023-01-09, 2023-02-07, 2023-03-06, 2023-05-23, 2023-07-03, 2023-07-27 ... |  |


## Gap-ups above the previous day's high

Under the literal wording a candle that opens above yesterday's high and closes higher IS recognised (the close is beyond the major resistance): Example 2 (17 Sep 2025) is such a case (open 25,276.6 > previous high 25,260.5; this is why the screenshot draws no level). Interpretation A (the candle must start on the old side) would reject it. Counts of such sessions are in `ema_gap_research.md`; trades that fire through this route are tabulated in `performance_by_eligibility_category.csv` (dimension 'open beyond previous-day range').