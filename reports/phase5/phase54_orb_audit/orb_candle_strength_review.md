# ORB - the strong-candle condition (review of the three rejected candles)

Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

## What the source says

* p.3 / p.4 (Method 1): 'a strong green body and a small upper wick' (short: strong red body, small lower wick). p.5-7 (Method 2): 'convincing green body, limited upper wick'. p.8-9 (Gap): 'a strong green body, or a suitable bullish pin-bar-type candle'; 'reject candles with a very large lower wick'.
* p.10 (the candle-quality figure): PREFERRED = a big body closing near the high with a small upper wick; CONDITIONAL = a bullish pin bar ('its position and close must support the breakout'); REJECT = strong upper-wick rejection. 'A pin bar's shape alone is never sufficient.'
* **No percentage is given anywhere.** The figures draw very clean candles (a body of roughly 80-90% of the range with a tiny wick in the Method 1 and Method 2 charts and in the p.10 'preferred' example).

## What the engine uses (RESEARCH_PROPOSAL, not source)

Strong = body >= 60% of the range and the wick against the trade <= 20% (profile MODERATE); alternatives STRICT (70% / 15%) and LOOSE (50% / 25%); the conditional pin bar = wick >= 2x the body with the close within 30% of the range (the owner's recommendation); a rejection-wick flag at 33% (Gap setup only).

## The three disputed candles rejected by the threshold

| date | direction | OHLC | body % | wick against the trade % | close location % | STRICT | MODERATE | LOOSE | pin bar (owner test) | miss vs MODERATE (body / wick, points of %) | miss vs LOOSE |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-10-16 | LONG | 25401.0/25424.65/25382.85/25412.15 | 26.67 | 29.9 | 70.1 | False | False | False | False (wick/body 1.63, 29.9% from the extreme) | -33.33 / -9.9 | -23.33 / -4.9 |
| 2025-12-12 | LONG | 25982.75/26002.8/25964.9/26002.55 | 52.24 | 0.66 | 99.34 | False | False | True | False (wick/body 0.9, 0.66% from the extreme) | -7.76 / 19.34 | 2.24 / 24.34 |
| 2025-12-30 | SHORT | 25951.0/25951.0/25894.6/25908.05 | 76.15 | 23.85 | 23.85 | False | False | True | False (wick/body 0.0, 23.85% from the extreme) | 16.15 / -3.85 | 26.15 / 1.15 |

(Positive margin = satisfied by that many percentage points; negative = missed by that much.)

Full measurement fields for the three candles (points): 

| date | O / H / L / C | range | body | upper wick | lower wick | colour | close - previous-day level (trade direction) | close location in the range % |
|---|---|---|---|---|---|---|---|---|
| 2025-10-16 | 25401.0/25424.65/25382.85/25412.15 | 41.8 | 11.15 | 12.5 | 18.15 | GREEN | 47.8 | 70.1 |
| 2025-12-12 | 25982.75/26002.8/25964.9/26002.55 | 37.9 | 19.8 | 0.25 | 17.85 | GREEN | 80.8 | 99.34 |
| 2025-12-30 | 25951.0/25951.0/25894.6/25908.05 | 56.4 | 42.95 | 0.0 | 13.45 | RED | 14.2 | 23.85 |

* **2025-12-12** (green, body 52.2%, opposite wick 0.7%): rejected by MODERATE only because the body is 7.8 points short of 60%; it passes LOOSE (50%). The candle also opened and closed above the previous high (gap +84).
* **2025-12-30** (red short, body 76.2%, lower wick 23.9%): rejected by MODERATE because the lower wick is 3.9 points above 20%; it passes LOOSE (25%). It broke and closed below the previous low.
* **2025-10-16** (green, body 26.7%, upper wick 29.9%, lower wick 43.4%; gap +77 above the previous high): fails EVERY profile and the owner pin test (wick/body 1.63 < 2). It is neither the 'preferred' nor the 'rejected' shape of p.10 (the upper wick is below the 33% rejection flag) - the source does not decide it.

## Two further candles that fail the shape test inside the Gap setup

| date | OHLC | body % | wick against the trade % | pin test | note |
|---|---|---|---|---|---|
| 2025-10-27 | 25851.95/25877.6/25828.1/25861.4 | 19.09 | 32.73 | False (wick/body 2.52; 32.73% from the extreme, needs <= 30) | a pin-bar-type candle (lower wick 2.5x the body) whose close is 2.7 points of % outside the owner's 30% band; fails by a hair |
| 2025-12-31 | 25975.45/26026.85/25975.45/26013.65 | 74.32 | 25.68 | False (wick/body 0.0; 25.68% from the extreme, needs <= 30) | body 74% but the wick against the trade is 25.7% (fails MODERATE and LOOSE by 5.7 / 0.7 points) |

## The author's own numeric remarks (handwritten pages; all in IRF context, listed as evidence)

AC32 (2025-12-11): 'should be ignored as candle body is less than 50%'; AC07 (2025-09-17): 'entry candle body is 40% wick is 60%'; AC01 (2025-09-01): '60+ body candle in the entry side'. The author thus uses body percentages of 40-60% when discussing entry candles for IRF; the 50% remark is close to the LOOSE profile (50% / 25%) and 60% to MODERATE. They are not ORB statements and do not fix an ORB threshold.

## Verdict on the current threshold

* **Explicitly supported by the source?** No - the rulebook gives no numbers. **A reasonable provisional approximation?** Partly: MODERATE (60% / 20%) is looser than the rulebook's own figures; LOOSE (50% / 25%) is looser still. **In conflict with the author's illustration?** The illustrations (clean 80-90% bodies) support the stricter reading, while the author's handwritten expectation (2025-12-12, 2025-12-30) supports a looser one: the author's two statements point in different directions. **Undefined?** Yes: 'strong' and 'convincing' remain qualitative, so a numeric approximation remains necessary.
* Population (first candles that break and close beyond the previous-day extreme, 69 sessions): strong under STRICT 15, MODERATE 25, LOOSE 33; pin bar 8. The profile changes the ORB signal count (53 -> 38 with STRICT, 66 with LOOSE) and reproduces 2 of the 13 disputed dates with LOOSE (2025-12-12,2025-12-30).
* **No threshold was optimised.** The percentages were not tuned; the three profiles are the ones that already existed. Choosing between them is an owner decision (`orb_rule_decision_matrix.md`, R8).
