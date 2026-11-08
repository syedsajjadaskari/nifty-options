# ORB - support / resistance level reconstruction

Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

## What the source defines

* **Method 1 (explicit, p.4 table):** the major level is 'the top of the previous day's range (resistance) / bottom (support)' = the previous day's high / low, marked as a horizontal line (p.3-4 figures). The engine uses exactly this (`prev_high_low`).
* **Method 2 (qualitative + two schematics):** 'a smaller level within the previous day's range' - 'a minor swing high or consolidation top' - near a rising trendline; the p.5 schematic puts it at the high of a recent candle near the END of the previous session, p.7's annotated real chart marks a 'small inner resistance (near trendline)' and the caption admits it is 'drawn approximately; verify the exact levels on your original chart'. No algorithm exists (ORB-M2-*-001 are UNRESOLVED).
* **Real reference charts (unlabelled, no price or date axis): two on p.12 and three on p.13.** The purple level is a horizontal BAND, not a line: in the two p.13 short breakdowns it starts at the left (where a base formed) and runs to the entry candle (how many sessions lie between is only inferred from unlabelled dashed verticals); in the p.13 long and the first p.12 chart it starts inside / before the previous session and runs a little PAST the entry candle, with a rising trendline band below. The rulebook text has no rule for a band or a multi-session level.

## Source chart by source chart (rendered and read; prices are read off the figures and are approximate; the real charts have no price axis, so band edges are described relative to the candles, not measured)

| figure | candles that produce the level | available when | horizontal / diagonal | bodies or wicks | zone boundaries | breakout confirmation | versus the current algorithm |
|---|---|---|---|---|---|---|---|
| p.3 Method 1 long (schematic) | the upper part of the last staircase candles (about 24,175-24,180) of the previous session | marked before the open | horizontal line (single) | highs / upper wicks touch the line; bodies just below | none (a line) | 09:15-09:20 candle opens below and closes about 55 points above | same as the engine: the previous day's high (p.4 table) |
| p.4 Method 1 short (schematic) | the lows of the last descending candles (about 24,160) | marked before the open | horizontal line | lows / lower wicks | none | candle opens above and closes below | same (previous day's low) |
| p.5 Method 2 long (schematic) | the highs of the last 3-4 candles of the previous session ('inner resistance', about 24,150) below a dashed 'major resistance' (about 24,220); the trendline joins swing lows from about 24,060 | inner level: end of the previous session; trendline: needs two swing lows | inner level horizontal; trendline diagonal rising | candle highs (wicks) | none | candle closes above the inner level; the major level is NOT yet broken | plausibly the latest fractal inside the range; trendline: at least two fractal lows (engine: the last two) |
| p.6 Method 2 short | text only ('apply the same steps in reverse') | - | - | - | - | - | no figure |
| p.7 annotated real chart (Method 2 long) | a small swing high inside the previous day's range 'near the trendline' (yellow dashed); the major zone (purple band) is the multi-candle top of the earlier rally | previous session ('drawn approximately') | inner level horizontal; trendline diagonal rising; major zone a horizontal band | swing HIGHS (wicks) for the inner level; the major band spans bodies and wicks | major band about 10 candle ranges wide; inner level a line | a large gap-up green 09:20 candle closes through the inner level; the major band stays above | consistent with 'a recent swing high'; the exact swing is not recoverable |
| p.8 Gap-up (schematic) | the 200 DMA (a falling diagonal line); the previous close lies below it | known before the open | DIAGONAL (the average) | n/a | the drawn GAP UP box lies wholly below the line | the first candle OPENS below the line, crosses it and closes above | the frozen engine needs the OPEN above the average: NOT what is drawn |
| p.9 Gap-down (schematic) | the 200 DMA (a rising diagonal line) | known before the open | diagonal | n/a | the GAP DOWN box lies wholly above the line | the first candle opens above the line, crosses it and closes below | same difference |
| p.12 chart 1 (long, real) | a thin purple zone from earlier highs, with a rising trendline BAND (blue parallelogram) below | earlier sessions | zone horizontal; trendline diagonal band | highs / bodies of the earlier swing tops | thin zone (about one to two candle ranges); the entry candle follows just after the zone's right edge | a tall gap-up candle breaks above the zone | NOT reproduced (multi-session zone, trendline band) |
| p.12 chart 2 (gap-up long, real) | the EMA(200) (a curved line); no horizontal level | known before the open | curved diagonal | n/a | none | a tall green candle starts far below the EMA and closes at / through it | the Gap setup with the CANDLE crossing the average (frozen engine: open beyond) |
| p.13 chart 1 (short, real) | a base at the left: a purple BAND over its range (about 3 candle heights) | earlier sessions (number only inferred) | horizontal band | bodies AND wicks (a zone) | a band, both edges drawn | a large red candle (gap down) closes below the band; EMA(200) above price | NOT reproduced (multi-session band) |
| p.13 chart 2 (short, real) | a thin purple band from a left candle | earlier sessions | horizontal thin band | bodies / lows | thin band | a large red candle breaks below; EMA near / above | NOT reproduced |
| p.13 chart 3 (long, real) | a purple resistance band that starts inside the previous session and runs past the entry candle; a rising blue trendline far below price; EMA(200) crossing the band | previous session onward | band horizontal; trendline diagonal | bodies and wicks of the highs | band | a green candle breaks above the band and the EMA | NOT reproduced (band + a trendline spanning many sessions) |

None of the real charts is dated or labelled with a method, so they cannot be matched to the 13 disputed dates; the author's drawings for those dates would be needed. A definition that reproduced the bands would need a band (body to wick), a base-detection rule and a session lookback - none exists in the source.

## What the engine does

Method 1: previous-day extreme. Method 2: the latest 5-candle fractal of the previous session inside its range (`LATEST_FRACTAL_K2`; trendline = last two fractal lows / highs). Nothing multi-session.

## Constructions that can be computed at 09:15 (causal; none hardcoded to a date)

Every family below uses only completed candles of earlier sessions. 'Broken' = the first candle breaks AND closes beyond the level (colour-matching direction). Families that are not in the source are labelled so.

| family | source status | sessions broken (of 247) | % | + strong candle | + strong + trend (all gates but the trendline) | on the 13 disputed dates | on journal ORB dates (89) | on dates without a journal ORB |
|---|---|---|---|---|---|---|---|---|
| M1_PREVIOUS_DAY_EXTREME | EXPLICIT_DOCUMENT_RULE (Method 1) | 69 | 27.9 | 33 | 24 | 4 | 48 | 21 |
| M2_LATEST_FRACTAL_K2 | CURRENT_ENGINE_ASSUMPTION | 118 | 47.8 | 56 | 36 | 7 | 72 | 46 |
| M2_HIGHEST_FRACTAL_K2 | RESEARCH_PROPOSAL | 84 | 34.0 | 38 | 28 | 4 | 56 | 28 |
| M2_NEAREST_FRACTAL_FROM_OPEN_K2 | RESEARCH_PROPOSAL | 76 | 30.8 | 38 | 22 | 8 | 42 | 34 |
| M2_HIGHEST_BROKEN_FRACTAL_K2 | RESEARCH_PROPOSAL | 156 | 63.2 | 70 | 47 | 12 | 82 | 74 |
| MS_EXTREME_2_SESSIONS | RESEARCH_PROPOSAL (not in the written rules; the | 49 | 19.9 | 23 | 19 | 3 | 36 | 13 |
| MS_EXTREME_3_SESSIONS | RESEARCH_PROPOSAL (not in the written rules; the | 41 | 16.7 | 17 | 15 | 3 | 28 | 13 |
| MS_EXTREME_5_SESSIONS | RESEARCH_PROPOSAL (not in the written rules; the | 26 | 10.6 | 11 | 11 | 2 | 19 | 7 |
| MS_SWING_NEAREST_FROM_OPEN_3_SESSIONS | RESEARCH_PROPOSAL | 113 | 45.9 | 52 | 33 | 9 | 57 | 56 |

Reading the table: a construction that is broken on most sessions (e.g. 'the most distant inner swing broken' on 63.2% of sessions, 12 of the 13 disputed dates, but also 74 sessions without a manual ORB) does not SELECT ORB days: any strong candle crosses some swing. A construction that is rarely broken (previous-day extreme: 27.9%) explains only 4 of the 13. The manual journal is used here descriptively only (it has no direction or price); no rule was chosen to match it.

## Which constructions the first candle broke on each of the 13 dates

| date | m1 PREVIOUS_DAY_EXTREME | m2 LATEST | m2 HIGHEST | m2 NEAREST_FRACTAL_FROM_OPEN_K2 | m2 HIGHEST_BROKEN | ms EXTREME_2 | ms EXTREME_3 | ms EXTREME_5 | ms SWING_NEAREST_FROM_OPEN_3 |
|---|---|---|---|---|---|---|---|---|---|
| 2025-09-11 | . | x | . | x | x | . | . | . | x |
| 2025-09-16 | . | . | . | x | x | . | . | . | x |
| 2025-10-08 | . | . | . | . | . | . | . | . | x |
| 2025-10-16 | x | x | x | . | x | x | x | x | . |
| 2025-10-17 | . | . | . | x | x | . | . | . | x |
| 2025-10-27 | . | x | . | x | x | . | . | . | x |
| 2025-11-21 | . | . | . | . | x | . | . | . | . |
| 2025-11-28 | . | x | . | . | x | . | . | . | . |
| 2025-12-05 | . | . | . | x | x | . | . | . | x |
| 2025-12-12 | x | x | x | . | x | x | x | . | . |
| 2025-12-24 | . | . | . | x | x | . | . | . | x |
| 2025-12-30 | x | x | x | x | x | x | x | x | x |
| 2025-12-31 | x | x | x | x | x | . | . | . | x |

`x` = broken. Per-date detail (level, open already beyond the level, close minus level) is in `orb_level_families_13.csv` and each `daily/<date>.md`; each `charts/<date>.svg` draws the source-defined previous-day levels, the frozen inner level and the provisional constructions with different line styles.

## The dates with no previous-day level broken

On 2025-09-11, 2025-09-16, 2025-10-08, 2025-10-17, 2025-10-27, 2025-11-21, 2025-11-28, 2025-12-05, 2025-12-24 the first candle neither breaks nor closes beyond the previous-day extreme. On the six of them where the frozen inner level is also unbroken (2025-09-16, 2025-10-08, 2025-10-17, 2025-11-21, 2025-12-05, 2025-12-24), the author's level cannot be reconstructed from the source, and no deterministic construction I could justify reproduces them: the variants that change the inner level reproduce 1 date (2025-12-24) at most.

## Does each construction generalise?

| construction | deterministic from causal data | generalises? | evidence |
|---|---|---|---|
| previous-day extreme (Method 1) | yes | yes (source-explicit) | broken on 27.9% of sessions |
| latest inner fractal (frozen Method 2) | yes (k = 2 is a parameter) | yes, but one reading among several | 47.8% of sessions |
| highest inner swing / nearest from the open / most distant broken | yes | yes, but non-discriminating or order-dependent | 34.0% / 30.8% / 63.2% of sessions |
| multi-session extreme (2 / 3 / 5 sessions) | yes (N is a parameter the source does not give) | unknown: N undefined | 19.9% / 16.7% / 10.6% of sessions |
| multi-session swing nearest the open | yes (3 sessions, k = 2 arbitrary) | non-discriminating | 45.9% of sessions |
| the p.13 boxed zones (base + extension across sessions) | no: base, width and extension rule are undefined | cannot be implemented without the author's definition | not built |

## Unresolved alternatives (for the author)

1. Is 'previous-day resistance / support' always the day's extreme, or the most recent swing / zone the price reacted to (the p.13 bands)? 2. How is the Method 2 inner level chosen when the previous day has several swings? 3. Is the level a LINE (high / low) or a BAND (body to wick), and are bodies or wicks used? The p.13 bands and the p.3-p.7 figures suggest bands / swings; the written rules and the p.4 table say the day's top / bottom. The author's drawings for the 13 dates are what is needed to settle it.
