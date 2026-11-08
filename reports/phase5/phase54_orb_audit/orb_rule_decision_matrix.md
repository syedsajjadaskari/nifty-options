# ORB - rule decision matrix

Audit evidence only: no controller, no fills, no P&L, no backtest was run. Variants are disabled by default and none is source-defined or approved.

Every row is a candidate or an existing choice; all candidates are disabled by default (`research/phase54.py`, `strategies/orb_candidates.py`). Combinations were deliberately NOT searched (that would be fitting). 'Dates' = how many of the 13 disputed dates the variant makes a confirmed ORB signal; impact = confirmed ORB signals, signals added / removed against the frozen 53; the journal columns are descriptive.

| # | proposed rule | source evidence | disputed dates on which the variant yields a signal (the author gave no level, so this is NOT support) | contradictory examples / cost | affected methods | historical signal impact | implementation difficulty | owner approval required |
|---|---|---|---|---|---|---|---|---|
| R1 | Method 1 level = previous-day high / low (current) | p.4 table: 'top / bottom of the previous day's range'; p.3-4 figures | none (keeps the engine) | 9 dates do not break it | Method 1 | frozen: 53 signals | none | no (source-explicit) |
| R2 | Method 1 / 2 level = multi-session extreme or zone (p.13 bands) | p.13 reference images only; no rule, no N, no band width | broken on 3 / 3 / 2 of 13 (N = 2 / 3 / 5) | unknown (no author drawing) | Method 1 | not built; population 19.9% / 16.7% / 10.6% of sessions broken | high: base / width / N undefined | YES |
| R3 | Method 2 inner level = highest inner swing | p.4: 'a smaller level within the previous day's range' (not 'the biggest') | none | removes 2 frozen signals | Method 2 | 51 signals (0 added / 2 removed) | low | YES |
| R4 | Method 2 inner level = first inner swing from the open | p.5 schematic: a recent swing the candle must cross | 2025-12-24 | removes 8 frozen signals | Method 2 | 47 (2 / 8); date overlap with journal ORB rows 37 | low | YES |
| R5 | Method 2 inner level = most distant inner swing broken | none (a convenience reading: 'any inner level broken') | 2025-12-24 | adds 3 signal dates with no journal ORB | Method 2 | 58 (5 / 0) | low | YES |
| R6 | Method 2 trendline = any two of the last three swing lows (highs) | p.5-7: 'connect the relevant swing lows' (no count) | 2025-11-28 | adds 2 signal dates with no journal ORB | Method 2 | 69 (16 / 0) | low | YES |
| R7 | Method 2 without a trendline (DIAGNOSTIC) | contradicts p.7: 'a trendline by itself is not an entry signal' implies it is part of Method 2 | 2025-09-11,2025-11-28 | drops a source-named condition | Method 2 | 77 (24 / 0) | trivial | NOT recommended (diagnostic only) |
| R8 | Strong-candle profile LOOSE (50% / 25%) | p.3-10: 'strong' is qualitative; the figures show clean candles | 2025-12-12,2025-12-30 | p.10 illustrations favour clean candles; AC27 / other dates unaffected | Methods 1, 2, Gap | 66 (13 / 0); date overlap with journal ORB rows 43 | trivial (existing profile) | YES |
| R9 | Strong-candle profile STRICT (70% / 15%) (DIAGNOSTIC) | closest to the p.3 / p.10 figures | none | removes 15 frozen signals | Methods 1, 2, Gap | 38 (0 / 15) | trivial | YES (diagnostic) |
| R10 | Trend = EMA side + two higher swings (owner variant B) | p.3: 'supported by bullish price structure' | none | removes 24 frozen signals; AC27 signal removed | Methods 1, 2 | 29 (0 / 24) | low (existing) | YES |
| R11 | Trend = first-candle close vs EMA(200) at 09:20 (literal 'price above the 200 EMA') (DIAGNOSTIC) | p.3 / p.4 wording; frozen design deliberately avoids the gap establishing the trend | none | both EMA dates then fail other conditions; AC27 signal kept | Methods 1, 2 | 66 (13 / 0); added signal dates without a journal ORB 1 | low (existing mode) | YES (diagnostic; do not relax merely to add trades) |
| R12 | Gap setup: the candle (not only the open) may cross the 200 average | p.8 / p.9 schematics and the p.12 real chart DRAW the candle opening on the old side, crossing and closing beyond; text: 'a candle that only crosses the line but closes below it does not qualify' | none (2025-12-31 then fails the wick test) | none found | Gap / 200 DMA | 56 (3 / 0); 10 of 246 gap cases differ | low (built, disabled) | YES (the figures favour this reading over the frozen one) |
| R13 | ORB colour rule (long green, short red) | AC27 (long only); short mirror = ORB-GLOBAL-002 interpretation | none (AC27 is a removal) | none | Methods 1, 2, Gap | 50 (0 / 3); the removed signals lie on dates without a journal ORB | trivial (existing) | YES (short side has no author evidence) |
| R14 | Automatic ORB priority over IRF | not in any document; the brief forbids it | all 13 'ORB instead of IRF' | no ORB signal exists, so priority could not help; ORB (09:20) already precedes IRF in time | controller | none | n/a | NOT applicable (qualification problem) |

## Variant table (signal-only; ORB engine only)

| variant | authority | ORB signals | added | removed | of the 13 | date overlap with journal ORB rows (of 89, descriptive) | signal dates without a journal ORB | AC27 date signal |
|---|---|---|---|---|---|---|---|---|
| orb-frozen | ACTIVE_REFERENCE | 53 | 0 | 0 | 0 | 35 | 6 | Method 1 LONG 09:20 |
| orb-var-inner-highest-fractal | RESEARCH_PROPOSAL_NOT_APPROVED | 51 | 0 | 2 | 0 | 33 | 6 | Method 1 LONG 09:20 |
| orb-var-inner-nearest-from-open | RESEARCH_PROPOSAL_NOT_APPROVED | 47 | 2 | 8 | 1 | 37 | 6 | Method 1 LONG 09:20 |
| orb-var-inner-highest-broken | DIAGNOSTIC_ONLY | 58 | 5 | 0 | 1 | 37 | 9 | Method 1 LONG 09:20 |
| orb-var-trendline-any-pair | RESEARCH_PROPOSAL_NOT_APPROVED | 69 | 16 | 0 | 1 | 40 | 7 | Method 1 LONG 09:20 |
| orb-var-trendline-none | DIAGNOSTIC_ONLY | 77 | 24 | 0 | 2 | 43 | 7 | Method 1 LONG 09:20; Method 2 LONG 09:20 |
| orb-var-strength-strict | DIAGNOSTIC_ONLY | 38 | 0 | 15 | 0 | 24 | 5 | Method 1 LONG 09:20 |
| orb-var-strength-loose | RESEARCH_PROPOSAL_NOT_APPROVED | 66 | 13 | 0 | 2 | 43 | 6 | Method 1 LONG 09:20 |
| orb-var-trend-structure | OWNER_VARIANT_NOT_ACTIVE | 29 | 0 | 24 | 0 | 18 | 3 | none |
| orb-var-trend-ema-basic | DIAGNOSTIC_ONLY | 66 | 13 | 0 | 0 | 37 | 6 | Method 1 LONG 09:20 |
| orb-var-gap-candle-crossing | RESEARCH_PROPOSAL_NOT_APPROVED | 56 | 3 | 0 | 0 | 38 | 6 | Method 1 LONG 09:20 |
| orb-var-colour | CANDIDATE_NOT_APPROVED | 50 | 0 | 3 | 0 | 35 | 3 | none |

## Conclusions

* **No single construction reproduces the disputed dates:** the best variant reproduces 2 of 13, and together all variants reach 5 (2025-09-11, 2025-11-28, 2025-12-12, 2025-12-24, 2025-12-30); 8 dates are reproduced by none (an unknown level, or several simultaneous misses).
* **Level and candle strength dominate** where the engine has no ORB on a date with a journal ORB row (50 in-session dates; the binding predicate of the closest method is {'level_broken': 15, 'candle_quality': 13, 'candle_shape': 9, '2 predicates fail': 9, 'trend': 2, 'gap_crosses_200_average': 2}). This is a date-only description: the journal carries no direction, price or level, so it cannot score a rule and no rule was chosen by it.
* **Nothing here should be promoted without the author's drawings** of the level, the trendline and the entry candle for at least the six level dates; the matrix gives the owner the exact trade-offs.
