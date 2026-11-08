# ORB - the EMA / trend condition and the trendline (review)

Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

## What the source requires

* Trend (Methods 1 and 2): 'Established trend in trade direction'; p.3: 'Confirm the uptrend. **Price above the 200 EMA is a basic confirmation, supported by bullish price structure.**' (short: price below the 200 EMA, bearish structure). p.5: 'if the breakout is near the EMA, wait for a convincing close above it'. The Gap / 200 DMA setup needs no established trend.
* The rulebook mixes '200 DMA', '200 EMA' and '200 DMA / EMA' (ORB-MA-001); the repository uses the EMA(200) of completed five-minute closes (reproduces the PDR chart legends to 0.005).
* Trendline (Method 2): 'connect swing lows (rising)' / 'swing highs (falling)'; 'a trendline by itself is not an entry signal'. No count, tolerance or algorithm is given.

## What the engine requires (stricter or different?)

* **Trend, frozen (`EMA_PREV_SESSION_CLOSE`, owner-approved variant A):** the PREVIOUS session's last close on the trend side of its own EMA. Design reason: the opening gap can never establish the trend. The rulebook's literal wording ('price above the 200 EMA' when the 09:20 candle is checked) is a different sampling time. The structure variant (`STRUCTURE_EMA_SWING2`: EMA side plus two higher swing highs and lows) is stricter still and is NOT active.
* **Trendline, frozen:** a line through the last two previous-session k=2 fractal lows (highs), required to slope in the trade direction with the first close on the trend side. This is a research construction.

## The two EMA dates

| date | previous close - its EMA | first close - EMA | open - EMA | active trend test | structure variant | literal first-close test | EMA change over the last previous hour |
|---|---|---|---|---|---|---|---|
| 2025-10-27 | -41.42 | 22.3 | 12.85 | False (EMA_PREV_SESSION_CLOSE wrong side) | False (STRUCTURE: previous close on the wrong side of EMA(20 | True (EMA5M_BASIC) | -8.06 |
| 2025-12-31 | -4.6 | 38.12 | -0.08 | False (EMA_PREV_SESSION_CLOSE wrong side) | False (STRUCTURE: previous close on the wrong side of EMA(20 | True (EMA5M_BASIC) | -3.94 |

On both dates the previous session closed on the wrong side of its EMA and the market GAPPED UP through it; the first candle closes above the EMA (+22.3 and +38.2 points), so the rulebook's literal 'price above the 200 EMA' test passes while the frozen previous-close test fails (by 41.5 and 4.6 points). These are exactly the conditions of the Gap / 200 DMA special setup, which needs no trend: on 2025-10-27 that setup fails only the candle shape (see the strength review); on 2025-12-31 the open is 0.08 points below the average (a reading difference, below) and the wick is 25.7%.
The literal reading is available as `orb-var-trend-ema-basic` (DIAGNOSTIC): it adds 13 population signals (66 total) but reproduces 0 of the 13 dates, because both disputed dates then fail other conditions. **The EMA filter was not relaxed to generate trades; the variant only measures the effect.** The structure variant removes 24 frozen signals.

## Swing structure and long / short eligibility on all 13 dates (previous session; active trend test)

| date | direction (colour) | confirmed swing highs (n, last two) | confirmed swing lows (n, last two) | EMA change over the last hour | LONG eligible (active) | SHORT eligible (active) | structure variant |
|---|---|---|---|---|---|---|---|
| 2025-09-11 | LONG | 9: [('14:05', 24978.65), ('15:15', 24987.9)] | 10: [('14:25', 24937.5), ('14:40', 24915.35)] | 7.53 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 24978.65->24987.9, sw |
| 2025-09-16 | LONG | 9: [('13:20', 25116.9), ('14:40', 25114.2)] | 11: [('14:20', 25063.2), ('15:15', 25060.7)] | 1.92 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 25116.9->25114.2, swi |
| 2025-10-08 | LONG | 7: [('14:15', 25220.35), ('14:50', 25167.25)] | 10: [('14:40', 25123.3), ('15:10', 25085.9)] | 10.54 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 25220.35->25167.25, s |
| 2025-10-16 | LONG | 6: [('13:35', 25364.35), ('14:35', 25337.95)] | 8: [('14:05', 25311.9), ('14:50', 25287.1)] | 9.76 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 25364.35->25337.95, s |
| 2025-10-17 | LONG | 6: [('14:05', 25576.4), ('14:55', 25624.8)] | 10: [('14:50', 25581.55), ('15:15', 25565.9)] | 26.18 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 25576.4->25624.8, swi |
| 2025-10-27 | LONG | 9: [('14:10', 25774.4), ('14:30', 25784.3)] | 8: [('13:50', 25718.65), ('14:50', 25737.95)] | -8.06 | False (EMA_PREV_SESSION_CLOSE wron | True (EMA_PREV_SESSION_CLOSE on th | False (STRUCTURE: previous close on the wrong side |
| 2025-11-21 | LONG | 10: [('14:15', 26246.2), ('15:00', 26217.85)] | 9: [('14:25', 26198.8), ('15:00', 26169.6)] | 16.3 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 26246.2->26217.85, sw |
| 2025-11-28 | LONG | 8: [('14:30', 26222.45), ('15:00', 26228.2)] | 12: [('14:30', 26180.55), ('14:50', 26173.3)] | 5.81 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 26222.45->26228.2, sw |
| 2025-12-05 | LONG | 8: [('14:30', 26020.85), ('15:00', 26059.05)] | 9: [('14:20', 25992.45), ('14:45', 25988.15)] | 0.13 | False (EMA_PREV_SESSION_CLOSE wron | True (EMA_PREV_SESSION_CLOSE on th | False (STRUCTURE: previous close on the wrong side |
| 2025-12-12 | LONG | 10: [('14:30', 25921.75), ('15:05', 25907.8)] | 9: [('14:10', 25860.6), ('14:50', 25848.25)] | 3.38 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 25921.75->25907.8, sw |
| 2025-12-24 | LONG | 9: [('14:15', 26233.55), ('15:00', 26206.65)] | 10: [('14:45', 26158.7), ('15:00', 26162.3)] | 8.9 | True (EMA_PREV_SESSION_CLOSE on th | False (EMA_PREV_SESSION_CLOSE wron | False (STRUCTURE swing highs 26233.55->26206.65, s |
| 2025-12-30 | SHORT | 10: [('14:25', 25972.45), ('15:05', 25951.05)] | 8: [('14:15', 25924.95), ('14:55', 25922.25)] | -11.46 | False (EMA_PREV_SESSION_CLOSE wron | True (EMA_PREV_SESSION_CLOSE on th | True (STRUCTURE swing highs 25972.45->25951.05, sw |
| 2025-12-31 | LONG | 10: [('14:50', 25954.85), ('15:05', 25957.35)] | 12: [('14:30', 25915.45), ('15:00', 25915.45)] | -3.94 | False (EMA_PREV_SESSION_CLOSE wron | True (EMA_PREV_SESSION_CLOSE on th | False (STRUCTURE: previous close on the wrong side |

## The Gap setup: does the OPEN or the CANDLE have to cross the 200 average?

**Text:** p.7 'provided the gap pushes price through the 200 DMA AND the first 5-minute candle closes beyond it'; p.8 steps 1-3: 'the market opens above the previous close' / 'price may have been below it; the gap must bring price above' / 'a candle that only crosses the line but closes below it does not qualify'; p.12 matrix: 'First-candle confirmation: close beyond 200 DMA'.
**Figures (rendered and read):** in both Gap schematics (p.8 gap-up, p.9 gap-down) the first candle OPENS ON THE OLD SIDE of the 200 DMA (below it for the gap-up, above it for the gap-down), its body crosses the line and it closes beyond it; the drawn gap box lies wholly on the old side and never reaches the line. The real gap-up chart on p.12 shows a tall green candle starting far below the EMA(200) and closing at / through it, and the entry is taken there. **The figures therefore depict the CANDLE crossing the average; the frozen reading (the OPEN must already be beyond it) is the stricter reading and no figure evidences it.** The text alone does not decide it; the figures lean to the candle-crossing reading (the engine's Method 1 likewise lets the candle itself cross the level).
Frozen reading: the previous close on the wrong side of its average AND the open strictly beyond the average. Alternative (variant `orb-var-gap-candle-crossing`): the same previous-close condition, and the candle closes beyond the average and its range reaches it. Across the 246 evaluable gap-in-direction cases of the 247 sessions: frozen qualifies 40, alternative 50; the two readings differ in 10 cases (listed in `summary.json`), one of them 2025-12-31 (open 0.08 below the average). As a signal-only variant: 56 confirmed ORB signals against 53 (3 added, 0 removed; the others of the 10 differing cases fail the candle-shape test); it reproduces 0 of the 13 disputed dates (2025-12-31 then fails the wick test: upper wick 25.7% against 20% / 25%).

Technical notes: (a) the EMA(200) is the EMA of completed five-minute closes seeded with the SMA of the first 200 candles; the 2025-10-21 Muhurat evening session (12 candles) is excluded by the repository's session filter - including it would move the 2025-10-27 EMA from 25839.10 to about 25843.56 and flips no predicate; (b) the fractal pivots are NON-STRICT (>= / <=): flat tops and bottoms count as fractals (the 2025-12-31 long trendline is a zero-slope line), a detail the 'k = 2 fractal' wording does not show.

## The two trendline dates

| date | last three fractals (time, price) | frozen trendline | line value at the open | any-pair-of-last-three |
|---|---|---|---|---|
| 2025-09-11 | [('13:55', 24953.55), ('14:25', 24937.5), ('14:40', 24915.35)] | TRENDLINE_NOT_SUPPORTIVE | 24841.52 | TRENDLINE_NOT_SUPPORTIVE |
| 2025-11-28 | [('14:15', 26172.3), ('14:30', 26180.55), ('14:50', 26173.3)] | TRENDLINE_NOT_SUPPORTIVE | 26158.8 | TRENDLINE_SUPPORTIVE |

Two readings of 'connect the relevant swing lows' exist: the last two fractals (frozen) and any two of the last three. The second makes 2025-11-28 qualify as a Method 2 LONG (`orb-var-trendline-any-pair`: 69 signals, 16 added); dropping the trendline altogether (a diagnostic, since the source says it is part of Method 2) also admits 2025-09-11. The trendline conditions also reject candles that would otherwise qualify on dates outside the dispute.

## Is the current implementation stricter than the documented method?

Yes in three places, none of them an explicit source rule: (1) the trend test samples the previous close instead of the 09:20 price; (2) the inner level / trendline are single research constructions; (3) the strength profile is numeric. **No relaxation is recommended here**; each is listed as an owner decision with its measured effect in `orb_rule_decision_matrix.md`.
