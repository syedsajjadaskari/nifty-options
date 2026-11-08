# Cross-configuration comparison (A, B, C)

SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill).

The configurations are compared, never combined, and **none is selected as better**: B and C rest on provisional conventions and a higher or lower synthetic P&L is not an approval criterion.

## Totals

| configuration | sessions | sessions with a trade | no-trade sessions | trades (first / second) | gross points | avg points / trade | win rate % | profit factor (gross) | max drawdown Rs (gross) | T1 hits | T2 hits | full stops | post-T1 stops | forced exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 247 | 188 | 59 | 196 (188 / 8) | 763.5 | 3.895 | 59.69 | 1.284 | 130,650 | 117 | 65 | 78 | 52 | 1 |
| B - Phase 5.3 author-corrected | 247 | 175 | 72 | 188 (175 / 13) | 663.0 | 3.526 | 58.51 | 1.25 | 204,146 | 110 | 62 | 77 | 47 | 2 |
| C - B + ORB gap crossing | 247 | 177 | 70 | 190 (177 / 13) | 643.5 | 3.387 | 58.42 | 1.24 | 215,846 | 111 | 62 | 78 | 48 | 2 |

## Strategy distribution of the executed trades

| configuration | IRF | ORB | PDR | PDS | RF |
|---|---|---|---|---|---|
| A | 109 | 41 | 25 | 11 | 10 |
| B | 90 | 41 | 28 | 19 | 10 |
| C | 89 | 44 | 28 | 19 | 10 |

## Net P&L (synthetic Rs)

| scenario | A | B | C |
|---|---|---|---|
| gross P&L (scenario A: no costs) | 297,765 | 258,550 | 250,946 |
| B: Rs 70 per trade, zero slippage | 284,045 | 245,390 | 237,646 |
| C: Rs 70 + 0.25 point slippage per side | 245,825 | 208,730 | 200,596 |
| D: Rs 70 + 0.5 point slippage per side | 207,605 | 172,070 | 163,546 |
| E: Rs 70 + 1.0 point slippage per side | 131,165 | 98,750 | 89,446 |

## Day-level differences

| comparison | days with a different trade sequence | by kind |
|---|---|---|
| A_vs_B | 65 | FIRST_TRADE_CHANGED: 42; SAME_ENTRIES_DIFFERENT_EXIT_OR_PNL: 3; SECOND_TRADE_DIFFERS: 1; TRADED_ONLY_IN_A: 16; TRADED_ONLY_IN_B: 3 |
| A_vs_C | 67 | FIRST_TRADE_CHANGED: 42; SAME_ENTRIES_DIFFERENT_EXIT_OR_PNL: 3; SECOND_TRADE_DIFFERS: 1; TRADED_ONLY_IN_A: 16; TRADED_ONLY_IN_C: 5 |
| B_vs_C | 3 | FIRST_TRADE_CHANGED: 1; TRADED_ONLY_IN_C: 2 |

Journal-independent attribution: every differing day is attributed to the EARLIEST signal that exists in one configuration only (`trade_differences_between_configurations.csv`, column `earliest_differing_signal`). A vs B: first-trade changes by strategy pair (A -> B): {('IRF', 'IRF'): 25, ('PDR', 'PDR'): 13, ('IRF', 'PDS'): 3, ('PDS', 'PDS'): 1}. B vs C: the three ORB Gap signals explain all 3 changed days.

### The twelve days with the largest P&L difference (A vs B, gross Rs; equal differences are listed in date order, so tied days beyond the twelfth are not shown)

| date | kind | A trades | B trades | A gross Rs | B gross Rs | difference | earliest differing signal |
|---|---|---|---|---|---|---|---|
| 2026-05-07 | FIRST_TRADE_CHANGED | PDR/PDR LONG 09:45 INITIAL_FULL_STOP -13650.0 / PDR/PDR LONG | PDR/PDR LONG 09:35 T1_THEN_BUFFER_STOP 4095.0 | -27,300 | 4,095 | 31,395 | 09:35 PDR/PDR LONG (only_B) |
| 2025-09-29 | FIRST_TRADE_CHANGED | IRF/Method 2B SHORT 10:40 TARGET 16965.0 | IRF/Method 2A SHORT 10:10 INITIAL_FULL_STOP -13767.0 | 16,965 | -13,767 | -30,732 | 10:10 IRF/Method 2A SHORT (only_B) |
| 2026-01-16 | FIRST_TRADE_CHANGED | IRF/Method 1 SHORT 10:00 INITIAL_FULL_STOP -13650.0 | IRF/Method 2B SHORT 10:45 TARGET 16965.0 | -13,650 | 16,965 | 30,615 | 10:00 IRF/Method 1 SHORT (only_A) |
| 2026-02-25 | FIRST_TRADE_CHANGED | IRF/Method 1 SHORT 09:35 INITIAL_FULL_STOP -13650.0 | IRF/Method 2A SHORT 10:45 TARGET 16965.0 | -13,650 | 16,965 | 30,615 | 09:35 IRF/Method 1 SHORT (only_A) |
| 2026-03-30 | FIRST_TRADE_CHANGED | IRF/Method 1 SHORT 10:10 TARGET 16965.0 | IRF/Method 2A SHORT 09:50 INITIAL_FULL_STOP -13650.0 | 16,965 | -13,650 | -30,615 | 09:50 IRF/Method 2A SHORT (only_B) |
| 2026-05-14 | FIRST_TRADE_CHANGED | IRF/Method 1 SHORT 09:35 TARGET 16965.0 | IRF/Method 2A SHORT 12:05 INITIAL_FULL_STOP -13650.0 | 16,965 | -13,650 | -30,615 | 09:35 IRF/Method 1 SHORT (only_A) |
| 2026-07-15 | FIRST_TRADE_CHANGED | IRF/Method 2A SHORT 10:00 INITIAL_FULL_STOP -13650.0 | IRF/Method 2A SHORT 09:50 TARGET 16965.0 | -13,650 | 16,965 | 30,615 | 09:50 IRF/Method 2A SHORT (only_B) |
| 2026-07-13 | TRADED_ONLY_IN_B | none | PDS/Method 1 SHORT 10:05 INITIAL_FULL_STOP -13650.0 / PDS/Me | 0 | -27,300 | -27,300 | 10:05 PDS/Method 1 SHORT (only_B) |
| 2025-12-04 | FIRST_TRADE_CHANGED | IRF/Method 2B SHORT 10:05 INITIAL_FULL_STOP -13650.0 | IRF/Method 2A SHORT 12:55 T1_THEN_BUFFER_STOP 4095.0 | -13,650 | 4,095 | 17,745 | 10:05 IRF/Method 2B SHORT (only_A) |
| 2026-01-05 | SAME_ENTRIES_DIFFERENT_EXIT_OR_PNL | ORB/Method 1 LONG 09:20 INITIAL_FULL_STOP -11700.0 / PDR/PDR | ORB/Method 1 LONG 09:20 INITIAL_FULL_STOP -11700.0 / PDR/PDR | -25,350 | -7,605 | 17,745 | 10:15 PDR/PDR LONG (only_B) |
| 2026-02-17 | FIRST_TRADE_CHANGED | IRF/Method 2B SHORT 10:45 INITIAL_FULL_STOP -13650.0 | IRF/Method 2A SHORT 10:40 T1_THEN_BUFFER_STOP 4095.0 | -13,650 | 4,095 | 17,745 | 10:40 IRF/Method 2A SHORT (only_B) |
| 2026-04-06 | FIRST_TRADE_CHANGED | PDR/PDR LONG 13:00 INITIAL_FULL_STOP -13650.0 | PDR/PDR LONG 12:55 T1_THEN_BUFFER_STOP 4095.0 | -13,650 | 4,095 | 17,745 | 12:55 PDR/PDR LONG (only_B) |

### B versus C

| date | kind | B trades | C trades | B gross Rs | C gross Rs | earliest differing signal |
|---|---|---|---|---|---|---|
| 2026-03-27 | TRADED_ONLY_IN_C | none | ORB/Gap/200DMA SHORT 09:20 INITIAL_FULL_STOP -11700.0 | 0 | -11,700 | 09:20 ORB/Gap/200DMA SHORT (only_C) |
| 2026-07-15 | FIRST_TRADE_CHANGED | IRF/Method 2A SHORT 09:50 TARGET 16965.0 | ORB/Gap/200DMA LONG 09:20 TARGET 16965.0 | 16,965 | 16,965 | 09:20 ORB/Gap/200DMA LONG (only_C) |
| 2026-08-13 | TRADED_ONLY_IN_C | none | ORB/Gap/200DMA SHORT 09:20 T1_THEN_BUFFER_STOP 4095.0 | 0 | 4,095 | 09:20 ORB/Gap/200DMA SHORT (only_C) |

## Interpretation limits

* Rules changed in B (IRF first-red-candle LOW, 28-point EMA gate, PDR / PDS earliest confirmation) move which strategy wins the first-valid-signal selection, so a day's outcome changes through the PORTFOLIO, not only through the changed strategy.
* C adds only three ORB signals; its extra dates are the dates the isolated Gap candle-crossing reading admits. The indicator interpretation (DMA versus EMA, timeframe) is unresolved in the source, so C is a labelled provisional scenario.
* The robustness window is reported in `combined_backtest_summary.md`; the results differ markedly by year and configuration.
