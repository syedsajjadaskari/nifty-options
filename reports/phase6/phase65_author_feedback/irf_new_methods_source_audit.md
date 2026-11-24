# The two newer IRF method rulebooks

Both are physically present in `docs/strategy_docs/`: `IRF_Inverse_Retest_Failure_Rulebook.pdf` (8 pages; 'Method 1: High Breakout Failure') and `IRF_Method2_First_Red_Candle_Rulebook.pdf` (8 pages; 'Method 2: First Red Candle Resistance Failure'). Their contents were read in full; nothing below is inferred beyond them.

|  | NEW Method 1 | NEW Method 2 |
|---|---|---|
| Level that must break and fail | high of the 09:15 candle (wick included) | Level B = top of the BODY (the open) of the FIRST red candle in the rally after a close above Level A (= first-candle high); wick ignored |
| Sequence | any candle closes above the level (green or red) -> the FIRST later candle that closes back below = failure, immediately or many candles later | close above A (rally) -> first red candle marks B -> a later candle closes above B (second breakout, no entry) -> a later candle closes below B = failure |
| Entry | short at the failure candle's close (TO CONFIRM) | short at the failure candle's close |
| Stop / target / filters | 35-40 points / 60 points; no trend, EMA, gap or previous-day condition; 1 trade a day; no entry after 13:00 | same |


|  | difference |
|---|---|
| Existing frozen Method 1 | the failure must be the VERY NEXT candle (window of one candle); new Method 1 allows any later candle |
| Existing Method 2A (first-red-candle support) | the first red candle's WICK LOW is a SUPPORT and a close below it is the trigger; the new Method 2 uses the red candle's BODY TOP as a RESISTANCE and needs a second breakout above it first |
| Existing Method 2B (resistance break) | resistance = top of the first push; new Method 2 resistance = open of the first red candle; both need a close above and then a red-candle/close below, but the levels differ |


TO CONFIRM items in the rulebooks (kept open): the colour of the first candle; a close exactly on a level (ignored here); entry price = failure close; one trade per day and re-entry after a stop; stop-before-target when both are touched in one candle; the end-of-day exit; whether a red candle that IS the breakout candle may be the first red candle of the rally (default here: no; a labelled variant is also computed). The rulebooks' dated chart examples (Nov 2026: 3, 6, 11, 12, 16) fall after the end of the evaluated data (2026-08-31) and the other examples are undated, so none could be reconstructed from our one-minute data.

## Signal-level comparison with the existing IRF (detectors only; not integrated into any portfolio)

Sessions with a new-method signal (to 13:00): window 2025-26 - Method 1 126 / 247, Method 2 87; window 2022-25 - Method 1 377 / 738, Method 2 270.

New Method 1 versus the frozen IRF's first signal of the day (2025-26): {'LATER_THAN_FIRST_EXISTING (but equals a later existing signal time)': 32, 'NO_NEW_SIGNAL': 121, 'SAME_TIME_AS_FIRST_EXISTING': 92, 'EARLIER_THAN_FIRST_EXISTING': 1, 'LATER_THAN_FIRST_EXISTING': 1}. New Method 2: {'LATER_THAN_FIRST_EXISTING': 32, 'SAME_TIME_AS_FIRST_EXISTING': 16, 'NO_NEW_SIGNAL': 160, 'LATER_THAN_FIRST_EXISTING (but equals a later existing signal time)': 25, 'EARLIER_THAN_FIRST_EXISTING': 13, 'NEW_SIGNAL_NO_EXISTING_IRF_SIGNAL': 1}.

Standalone hypothetical diagnostic (first signal per day through the SAME approved exit rules; not portfolio results, not a recommendation):

| window | method | trades | win_rate_pct | profit_factor | gross_rs | net_rs_70 |
|---|---|---|---|---|---|---|
| A | NEW-M1 | 126 | 53.97 | 1.018 | 14430.0 | 5610.0 |
| A | NEW-M2 | 87 | 62.07 | 1.219 | 96535.0 | 90445.0 |
| A | FROZEN-IRF first signal | 152 | 52.63 | 0.857 | -140498.0 | -151138.0 |
| A | IRF-V2 first signal | 132 | 52.27 | 0.927 | -62722.0 | -71962.0 |
| B | NEW-M1 | 377 | 56.76 | 1.099 | 218946.0 | 192556.0 |
| B | NEW-M2 | 270 | 57.78 | 1.099 | 149263.0 | 130363.0 |
| B | FROZEN-IRF first signal | 476 | 55.88 | 1.075 | 212618.0 | 179298.0 |
| B | IRF-V2 first signal | 429 | 54.55 | 0.955 | -118872.0 | -148902.0 |


Limitations of the standalone diagnostic: it applies the PORTFOLIO IRF exit rules (T1 27 on half, post-T1 stop entry +6, T2 60, forced exit 15:14) and not the rulebooks' single 60-point target with a 35-40 point stop; the Method 2 rulebook's 'latest entry time and exit time: 1 pm' is not tested as a 13:00 exit; times in the CSV (`first_red_time`, `second_breakout_time`, `new_m*_time`) are candle END times. It is not a result for the new methods as specified.

Files: `irf_new_methods_vs_existing.csv`, `irf_new_methods_standalone_diagnostic.csv`.