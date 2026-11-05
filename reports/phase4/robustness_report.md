# Robustness report (Phase 4)

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

Diagnostics only: **no rule, threshold or window was changed or selected from these tables**, no trade or regime was excluded, and every loss-making period is shown. Regime thresholds are fixed round numbers declared in `regime_definitions.json` (they were written after the five windows had been run once for sanity checks but before any regime table existed; they are not fitted).

## 1-3. By year, strategy and month

| row | status | trades | gross Rs | net Rs | profit factor | positive / negative months |
|---|---|---|---|---|---|---|
| C_2018 | EXPLORATORY | 185 | -102,063 | -266,713 | 0.9074 | 4 / 8 |
| D_2019_SECONDARY | EXPLORATORY | 182 | 301,314 | 139,334 | 1.3565 | 8 / 4 |
| B1_2022_23 | DATA_VALIDATED | 198 | 288,454 | 112,234 | 1.268 | 9 / 3 |
| B2_2023_24 | DATA_VALIDATED | 219 | -3,851 | -198,761 | 0.9971 | 8 / 4 |
| B3_2024_25 | DATA_VALIDATED | 192 | 224,796 | 53,916 | 1.2213 | 5 / 6 |
| B_2022_25 | DATA_VALIDATED | 609 | 509,398 | -32,612 | 1.1492 | 22 / 13 |
| A_2025_26 | REFERENCE | 196 | 297,765 | 123,325 | 1.2839 | 7 / 5 |

By strategy (gross Rs; full table in `strategy_comparison.csv`):

| row | IRF | ORB | PDR | PDS | RF |
|---|---|---|---|---|---|
| C_2018 | -66,826 | 185,152 | -115,966 | -18,447 | -85,976 |
| D_2019_SECONDARY | 167,427 | 136,617 | -35,763 | -5,460 | 38,493 |
| B1_2022_23 | 143,822 | 82,192 | 38,649 | 55,380 | -31,590 |
| B2_2023_24 | 177,265 | 11,437 | -198,364 | -29,094 | 34,905 |
| B3_2024_25 | 36,328 | 14,625 | 61,522 | 57,525 | 54,795 |
| B_2022_25 | 357,416 | 108,254 | -98,192 | 83,811 | 58,110 |
| A_2025_26 | -11,408 | 138,470 | 94,438 | 80,554 | -4,290 |

Monthly P&L of every window: `monthly_pnl_all_windows.csv`.

## 4. By volatility and trend regime (causal; trailing 20-day volatility and 60-day efficiency ratio, strictly before the session)

| row | vol regime | sessions | trades | gross Rs | avg trade Rs | win % |
|---|---|---|---|---|---|---|
| C_2018 | HIGH_VOL | 28 | 28 | -94,282 | -3367.23 | 42.86 |
| C_2018 | LOW_VOL | 105 | 79 | -24,882 | -314.96 | 50.63 |
| C_2018 | MID_VOL | 111 | 78 | 17,102 | 219.25 | 57.69 |
| D_2019_SECONDARY | HIGH_VOL | 57 | 46 | 162,279 | 3527.8 | 69.57 |
| D_2019_SECONDARY | LOW_VOL | 63 | 51 | 32,272 | 632.79 | 56.86 |
| D_2019_SECONDARY | MID_VOL | 124 | 85 | 106,762 | 1256.03 | 60.0 |
| B1_2022_23 | HIGH_VOL | 18 | 15 | 5,460 | 364.0 | 53.33 |
| B1_2022_23 | LOW_VOL | 118 | 96 | 278,265 | 2898.59 | 65.62 |
| B1_2022_23 | MID_VOL | 112 | 87 | 4,729 | 54.35 | 52.87 |
| B2_2023_24 | HIGH_VOL | 31 | 33 | -49,579 | -1502.39 | 51.52 |
| B2_2023_24 | LOW_VOL | 97 | 84 | 196,414 | 2338.26 | 64.29 |
| B2_2023_24 | MID_VOL | 115 | 102 | -150,686 | -1477.32 | 47.06 |
| B3_2024_25 | HIGH_VOL | 43 | 32 | 62,576 | 1955.48 | 59.38 |
| B3_2024_25 | LOW_VOL | 63 | 56 | 143,325 | 2559.38 | 69.64 |
| B3_2024_25 | MID_VOL | 141 | 104 | 18,896 | 181.69 | 55.77 |
| A_2025_26 | HIGH_VOL | 35 | 30 | -17,745 | -591.5 | 50.0 |
| A_2025_26 | LOW_VOL | 114 | 93 | 151,895 | 1633.28 | 60.22 |
| A_2025_26 | MID_VOL | 98 | 73 | 163,615 | 2241.3 | 63.01 |

| row | trend regime | sessions | trades | gross Rs | avg trade Rs | win % |
|---|---|---|---|---|---|---|
| C_2018 | SIDEWAYS | 228 | 173 | -118,326 | -683.97 | 52.02 |
| C_2018 | TRENDING_UP | 16 | 12 | 16,263 | 1355.25 | 58.33 |
| D_2019_SECONDARY | SIDEWAYS | 228 | 170 | 340,470 | 2002.76 | 62.94 |
| D_2019_SECONDARY | TRENDING_DOWN | 1 | 1 | -13,650 | -13650.0 | 0.0 |
| D_2019_SECONDARY | TRENDING_UP | 15 | 11 | -25,506 | -2318.73 | 45.45 |
| B1_2022_23 | SIDEWAYS | 198 | 157 | 253,324 | 1613.53 | 59.87 |
| B1_2022_23 | TRENDING_UP | 50 | 41 | 35,129 | 856.81 | 56.1 |
| B2_2023_24 | SIDEWAYS | 179 | 153 | 84,854 | 554.6 | 58.17 |
| B2_2023_24 | TRENDING_UP | 64 | 66 | -88,706 | -1344.02 | 45.45 |
| B3_2024_25 | SIDEWAYS | 219 | 169 | 232,986 | 1378.62 | 60.36 |
| B3_2024_25 | TRENDING_DOWN | 8 | 6 | -49,335 | -8222.5 | 16.67 |
| B3_2024_25 | TRENDING_UP | 20 | 17 | 41,145 | 2420.29 | 76.47 |
| A_2025_26 | SIDEWAYS | 236 | 185 | 331,500 | 1791.89 | 60.54 |
| A_2025_26 | TRENDING_DOWN | 8 | 7 | 3,120 | 445.71 | 57.14 |
| A_2025_26 | TRENDING_UP | 3 | 4 | -36,855 | -9213.75 | 25.0 |

The cells are noisy (some have few sessions) and the pattern is not stable across years: for example high-volatility sessions lose money in 2018, 2023-24 and 2025-26 but earn money in 2019, 2022-23 and 2024-25. The regime tables describe the history; they do not justify a filter. Combined cells: `robustness_regimes.csv`. No event explanation is offered for any day.

## 5. By morning entry time

| row | entry time (fill) | trades | gross Rs | avg trade Rs | win % | initial full stops |
|---|---|---|---|---|---|---|
| C_2018 | 09:20-09:59 | 104 | -22,308 | -214.5 | 53.85 | 46 |
| C_2018 | 10:00-10:59 | 56 | -85,527 | -1527.27 | 50.0 | 24 |
| C_2018 | 11:00-11:59 | 17 | 49,706 | 2923.85 | 58.82 | 5 |
| C_2018 | 12:00-13:00 | 8 | -43,934 | -5491.69 | 37.5 | 5 |
| D_2019_SECONDARY | 09:20-09:59 | 107 | 335,146 | 3132.21 | 68.22 | 31 |
| D_2019_SECONDARY | 10:00-10:59 | 48 | -11,954 | -249.03 | 54.17 | 22 |
| D_2019_SECONDARY | 11:00-11:59 | 18 | 10,920 | 606.67 | 50.0 | 4 |
| D_2019_SECONDARY | 12:00-13:00 | 9 | -32,799 | -3644.33 | 44.44 | 4 |
| B1_2022_23 | 09:20-09:59 | 113 | 95,570 | 845.75 | 56.64 | 49 |
| B1_2022_23 | 10:00-10:59 | 56 | 63,434 | 1132.74 | 57.14 | 24 |
| B1_2022_23 | 11:00-11:59 | 20 | 90,002 | 4500.11 | 75.0 | 5 |
| B1_2022_23 | 12:00-13:00 | 9 | 39,448 | 4383.17 | 66.67 | 3 |
| B2_2023_24 | 09:20-09:59 | 125 | 67,080 | 536.64 | 57.6 | 53 |
| B2_2023_24 | 10:00-10:59 | 49 | 37,694 | 769.26 | 53.06 | 22 |
| B2_2023_24 | 11:00-11:59 | 37 | -78,400 | -2118.91 | 48.65 | 19 |
| B2_2023_24 | 12:00-13:00 | 8 | -30,225 | -3778.12 | 37.5 | 5 |
| B3_2024_25 | 09:20-09:59 | 102 | 131,684 | 1291.01 | 59.8 | 41 |
| B3_2024_25 | 10:00-10:59 | 63 | 141,746 | 2249.93 | 65.08 | 22 |
| B3_2024_25 | 11:00-11:59 | 22 | -79,053 | -3593.32 | 45.45 | 12 |
| B3_2024_25 | 12:00-13:00 | 5 | 30,420 | 6084.0 | 80.0 | 1 |
| A_2025_26 | 09:20-09:59 | 113 | 274,599 | 2430.08 | 61.95 | 43 |
| A_2025_26 | 10:00-10:59 | 55 | 11,749 | 213.61 | 54.55 | 24 |
| A_2025_26 | 11:00-11:59 | 16 | 10,442 | 652.64 | 62.5 | 6 |
| A_2025_26 | 12:00-13:00 | 12 | 975 | 81.25 | 58.33 | 5 |

## 6. Concentration of profit

| row | trades | gross Rs | top-5 wins Rs | top 5 as % of gross profit | gross excluding the top 5 wins Rs | trades needed for half of the gross profit |
|---|---|---|---|---|---|---|
| C_2018 | 185 | -102,063 | 86,775 | 8.7 | -188,838 | 30 |
| D_2019_SECONDARY | 182 | 301,314 | 90,675 | 7.9 | 210,639 | 34 |
| B1_2022_23 | 198 | 288,454 | 94,575 | 6.9 | 193,879 | 39 |
| B2_2023_24 | 219 | -3,851 | 94,575 | 7.2 | -98,426 | 39 |
| B3_2024_25 | 192 | 224,796 | 94,575 | 7.6 | 130,221 | 35 |
| B_2022_25 | 609 | 509,398 | 94,575 | 2.4 | 414,824 | 112 |
| A_2025_26 | 196 | 297,765 | 94,575 | 7.0 | 203,190 | 38 |

No single trade dominates (the five largest wins are about 7-9% of a year's gross profit), but removing the best 10% of trades turns every window listed here negative (the 5paisa partial 2019 run stays positive), which is the normal shape of a fixed-target system and says the result depends on the winners it keeps.

## 7. Losing streaks

| row | longest consecutive losing trades |
|---|---|
| C_2018 | 6 |
| D_2019_SECONDARY | 5 |
| B1_2022_23 | 5 |
| B2_2023_24 | 5 |
| B3_2024_25 | 7 |
| B_2022_25 | 7 |
| A_2025_26 | 4 |

## 8-9. Transaction-cost and slippage sensitivity (net Rs; fixed cost per trade x adverse slippage points per fill; fill-level costs)

| row | gross (0 / 0) | Rs 500 / 0 pt | Rs 0 / 0.5 pt | **Rs 500 / 0.5 pt (Phase 3.6 headline)** | Rs 1,000 / 0.5 pt | Rs 500 / 1 pt | Rs 500 / 2 pt | Rs 1,500 / 2 pt |
|---|---|---|---|---|---|---|---|---|
| C_2018 | -102,063 | -194,563 | -174,213 | -266,713 | -359,213 | -338,863 | -483,163 | -668,163 |
| D_2019_SECONDARY | 301,314 | 210,314 | 230,334 | 139,334 | 48,334 | 68,354 | -73,606 | -255,606 |
| B1_2022_23 | 288,454 | 189,454 | 211,234 | 112,234 | 13,234 | 35,014 | -119,426 | -317,426 |
| B2_2023_24 | -3,851 | -113,351 | -89,261 | -198,761 | -308,261 | -284,171 | -454,991 | -673,991 |
| B3_2024_25 | 224,796 | 128,796 | 149,916 | 53,916 | -42,084 | -20,964 | -170,724 | -362,724 |
| B_2022_25 | 509,398 | 204,898 | 271,888 | -32,612 | -337,112 | -270,122 | -745,142 | -1,354,142 |
| A_2025_26 | 297,765 | 199,765 | 221,325 | 123,325 | 25,325 | 46,885 | -105,995 | -301,995 |

The headline model costs about Rs 890 per trade (Rs 500 fixed + 0.5 point on 780 units). The three-year gross edge is about Rs 836 per trade, so **the validated three-year window nets Rs -32,612 at the headline cost model, and loses money at any higher cost or slippage.** The Phase 3.6 reference year is positive only because its gross edge per trade was higher. The cost model is illustrative and not tied to an executable instrument; no cost scenario was chosen because it flatters the result (the full grid is in `cost_sensitivity.csv`).

## 10. Sensitivity to known data-quality issues

| row | sessions with a predeclared data issue | trades on those sessions | gross on those Rs | trades on other sessions | gross on other Rs |
|---|---|---|---|---|---|
| C_2018 | 2 | 1 | 16,965 | 184 | -119,028 |
| D_2019_SECONDARY | 3 | 2 | 33,930 | 180 | 267,384 |
| B1_2022_23 | 1 | 1 | -11,700 | 197 | 300,154 |
| B2_2023_24 | 9 | 2 | 33,930 | 217 | -37,781 |
| B3_2024_25 | 3 | 2 | -7,605 | 190 | 232,401 |
| B_2022_25 | 13 | 5 | 14,625 | 604 | 494,774 |
| A_2025_26 | n/a |  | - |  | - |

A data issue is one of the predeclared items (missing regular minutes, a frozen-price run, an abnormal 09:15 bar, an extreme 1-minute candle). These sessions are few, so the table is a disclosure, not evidence; no session is excluded from the main results.

The bigger data sensitivity is the choice of vendor, not the flagged sessions: see `vendor_sensitivity.csv` and `three_year_backtest_summary.md` (the same three-year window is Rs 509,398 gross on 5paisa bars and Rs 626,135 on the secondary vendor's bars, with 71.5% signal agreement).

## 11. Scale of the fixed-point parameters (why the years are not like-for-like)

Stops, targets and the post-T1 buffer are fixed index POINTS, and the Rs value of a point is constant (390 units), while the index level changed by a factor of about 2.3 across the windows. A 35-point stop is therefore a much wider move in relative terms in 2018-19 than in 2024-26, and positions are held longer when the index is lower (more trades reach the 15:14 forced exit). The windows differ in the RISK the same rules take, so differences between years mix market behaviour with scale. Nothing was rescaled (that would be a rule change).

| row | average entry level | stop 35 / ORB 30 as % of the index | target 1 (27) as % | forced-exit share of trades | initial-full-stop share | average holding (1-minute bars) |
|---|---|---|---|---|---|---|
| C_2018 | 10,747 | 0.33% / 0.28% | 0.25% | 25.4% | 43.2% | 187.1 |
| D_2019_SECONDARY | 11,439 | 0.31% / 0.26% | 0.24% | 12.6% | 33.5% | 168.6 |
| B1_2022_23 | 18,243 | 0.19% / 0.16% | 0.15% | 5.6% | 40.9% | 95.4 |
| B2_2023_24 | 21,943 | 0.16% / 0.14% | 0.12% | 4.6% | 45.2% | 72.5 |
| B3_2024_25 | 24,270 | 0.14% / 0.12% | 0.11% | 0.5% | 39.6% | 43.2 |
| B_2022_25 | 21,474 | 0.16% / 0.14% | 0.13% | 3.6% | 42.0% | 70.7 |
| A_2025_26 | 24,812 | 0.14% / 0.12% | 0.11% | 0.5% | 39.8% | 49.9 |
