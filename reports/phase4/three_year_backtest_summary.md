# Three-year backtest summary (Window B, 2022-09-01 .. 2025-08-31)

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

Window B uses the same provider as the Phase 3.6 baseline (5paisa minutes + 5paisa daily). The three annual slices come from ONE continuous run under identical frozen rules (the 5-minute EMA is warm throughout; the controller state is per day, so slicing the ledger by date is exact).

## Headline (frozen Phase 3.6 configuration, no parameter changed)

| row | status | confidence | sessions | trades (1st/2nd) | IRF / ORB / PDR / PDS / RF | index points | gross Rs (390 units) | illustrative net Rs | win % | profit factor (gross / net) | max drawdown Rs | longest losing streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1_2022_23 | DATA_VALIDATED | MODERATE | 248 | 198 (186/12) | 103 / 40 / 36 / 7 / 12 | 739.62 | 288,454 | 112,234 | 59.09 | 1.268 / 1.0977 | 188,341 | 5 |
| B2_2023_24 | DATA_VALIDATED | MODERATE | 243 | 219 (199/20) | 111 / 37 / 45 / 6 / 20 | -9.87 | -3,851 | -198,761 | 54.34 | 0.9971 / 0.8592 | 186,313 | 5 |
| B3_2024_25 | DATA_VALIDATED | MODERATE | 247 | 192 (180/12) | 114 / 24 / 25 / 14 / 15 | 576.4 | 224,796 | 53,916 | 60.42 | 1.2213 / 1.0498 | 173,706 | 7 |
| B_2022_25 | DATA_VALIDATED | MODERATE | 738 | 609 (565/44) | 328 / 101 / 106 / 27 / 47 | 1306.15 | 509,398 | -32,612 | 57.8 | 1.1492 / 0.991 | 188,341 | 7 |

| row | avg trade Rs | median trade Rs | largest win Rs | largest loss Rs | Target 2 | T1 then buffer stop | initial full stop | forced exit | conflict days | unresolved | positive / negative months | trades per session | avg holding (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| B1_2022_23 | 1456.84 | 4095.0 | 18,915 | -13,650 | 63 | 43 | 81 | 11 | 3 | 0 | 9 / 3 | 0.7984 | 95.39 |
| B2_2023_24 | -17.59 | 4095.0 | 18,915 | -14,079 | 59 | 51 | 99 | 10 | 1 | 0 | 8 / 4 | 0.9012 | 72.46 |
| B3_2024_25 | 1170.81 | 4095.0 | 18,915 | -13,650 | 57 | 58 | 76 | 1 | 7 | 0 | 5 / 6 | 0.7773 | 43.25 |
| B_2022_25 | 836.45 | 4095.0 | 18,915 | -14,079 | 179 | 152 | 256 | 22 | 11 | 0 | 22 / 13 | 0.8252 | 70.71 |

## By strategy (gross Rs, 390 units)

| row | strategy | trades | gross Rs | net Rs | win % | profit factor | share of gross |
|---|---|---|---|---|---|---|---|
| B1_2022_23 | IRF | 103 | 143,822 | 52,152 | 57.28 | 1.2395 | 49.9 |
| B1_2022_23 | ORB | 40 | 82,192 | 46,592 | 62.5 | 1.4683 | 28.5 |
| B1_2022_23 | PDR | 36 | 38,649 | 6,609 | 58.33 | 1.1888 | 13.4 |
| B1_2022_23 | PDS | 7 | 55,380 | 49,150 | 85.71 | 5.0571 | 19.2 |
| B1_2022_23 | RF | 12 | -31,590 | -42,270 | 50.0 | 0.6143 | -11.0 |
| B2_2023_24 | IRF | 111 | 177,265 | 78,475 | 58.56 | 1.2869 | n/m (window gross not positive) |
| B2_2023_24 | ORB | 37 | 11,437 | -21,493 | 54.05 | 1.0575 | n/m (window gross not positive) |
| B2_2023_24 | PDR | 45 | -198,364 | -238,414 | 40.0 | 0.4618 | n/m (window gross not positive) |
| B2_2023_24 | PDS | 6 | -29,094 | -34,434 | 50.0 | 0.2969 | n/m (window gross not positive) |
| B2_2023_24 | RF | 20 | 34,905 | 17,105 | 65.0 | 1.3653 | n/m (window gross not positive) |
| B3_2024_25 | IRF | 114 | 36,328 | -65,132 | 59.65 | 1.0579 | 16.2 |
| B3_2024_25 | ORB | 24 | 14,625 | -6,735 | 54.17 | 1.1136 | 6.5 |
| B3_2024_25 | PDR | 25 | 61,522 | 39,272 | 60.0 | 1.4507 | 27.4 |
| B3_2024_25 | PDS | 14 | 57,525 | 45,065 | 64.29 | 1.8429 | 25.6 |
| B3_2024_25 | RF | 15 | 54,795 | 41,445 | 73.33 | 2.0036 | 24.4 |
| B_2022_25 | IRF | 328 | 357,416 | 65,496 | 58.54 | 1.1936 | 70.2 |
| B_2022_25 | ORB | 101 | 108,254 | 18,364 | 57.43 | 1.2152 | 21.3 |
| B_2022_25 | PDR | 106 | -98,192 | -192,532 | 50.94 | 0.8617 | -19.3 |
| B_2022_25 | PDS | 27 | 83,811 | 59,781 | 66.67 | 1.6798 | 16.5 |
| B_2022_25 | RF | 47 | 58,110 | 16,280 | 63.83 | 1.2504 | 11.4 |

## Monthly P&L (gross Rs)

| month | B1_2022_23 | B2_2023_24 | B3_2024_25 | B_2022_25 |
|---|---|---|---|---|
| 2022-09 | -48,623 | - | - | -48,623 |
| 2022-10 | 15,990 | - | - | 15,990 |
| 2022-11 | -127,042 | - | - | -127,042 |
| 2022-12 | 62,985 | - | - | 62,985 |
| 2023-01 | 160,339 | - | - | 160,339 |
| 2023-02 | 41,116 | - | - | 41,116 |
| 2023-03 | -30,810 | - | - | -30,810 |
| 2023-04 | 76,216 | - | - | 76,216 |
| 2023-05 | 29,445 | - | - | 29,445 |
| 2023-06 | 20,426 | - | - | 20,426 |
| 2023-07 | 43,875 | - | - | 43,875 |
| 2023-08 | 44,538 | - | - | 44,538 |
| 2023-09 | - | 23,780 | - | 23,780 |
| 2023-10 | - | 6,815 | - | 6,815 |
| 2023-11 | - | 25,165 | - | 25,165 |
| 2023-12 | - | 22,045 | - | 22,045 |
| 2024-01 | - | -50,954 | - | -50,954 |
| 2024-02 | - | -64,574 | - | -64,574 |
| 2024-03 | - | 17,784 | - | 17,784 |
| 2024-04 | - | 28,665 | - | 28,665 |
| 2024-05 | - | -48,360 | - | -48,360 |
| 2024-06 | - | -19,617 | - | -19,617 |
| 2024-07 | - | 19,110 | - | 19,110 |
| 2024-08 | - | 36,290 | - | 36,290 |
| 2024-09 | - | - | 59,280 | 59,280 |
| 2024-10 | - | - | -22,425 | -22,425 |
| 2024-11 | - | - | 0 | 0 |
| 2024-12 | - | - | 51,285 | 51,285 |
| 2025-01 | - | - | -8,463 | -8,463 |
| 2025-02 | - | - | -24,960 | -24,960 |
| 2025-03 | - | - | -12,226 | -12,226 |
| 2025-04 | - | - | -69,440 | -69,440 |
| 2025-05 | - | - | 112,320 | 112,320 |
| 2025-06 | - | - | 19,110 | 19,110 |
| 2025-07 | - | - | -17,355 | -17,355 |
| 2025-08 | - | - | 137,670 | 137,670 |

## Coverage and exceptions (per row: the sessions of that period only)

* **B1_2022_23** (2022-09-01..2023-08-31): 248 sessions in the source, 248 usable; excluded: none; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 1.
* **B2_2023_24** (2023-09-01..2024-08-31): 247 sessions in the source, 243 usable; excluded: 2023-10-19 EXCLUDED_CORRUPT; 2023-11-12 EXCLUDED_NON_STANDARD_START; 2024-03-02 EXCLUDED_NON_STANDARD_START; 2024-05-18 EXCLUDED_NON_STANDARD_START; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 9.
* **B3_2024_25** (2024-09-01..2025-08-31): 248 sessions in the source, 247 usable; excluded: 2024-11-01 EXCLUDED_NON_STANDARD_START; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 3.
* **B_2022_25** (2022-09-01..2025-08-31): 743 sessions in the source, 738 usable; excluded: 2023-10-19 EXCLUDED_CORRUPT; 2023-11-12 EXCLUDED_NON_STANDARD_START; 2024-03-02 EXCLUDED_NON_STANDARD_START; 2024-05-18 EXCLUDED_NON_STANDARD_START; 2024-11-01 EXCLUDED_NON_STANDARD_START; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 13; expected sessions 744, missing from the source: 2022-10-24; warm-up sessions in the same source: 20.

## What drives the three-year result

Gross Rs by strategy over the three years: IRF 357,416, ORB 108,254, PDR -98,192, PDS 83,811, RF 58,110. **PDR (the author-corrected strategy) lost money in the validated window** (106 trades, profit factor 0.8617), worst in 2023-24 (Rs -198,364, 40.0% wins) while it was positive in 2022-23 (Rs 38,649) and 2024-25 (Rs 61,522); IRF, ORB, PDS and RF were each positive over the three years, and IRF supplies most of the gross profit. The flat middle year is explained by PDR (and PDS) losses offsetting IRF.

**Same-minute conflicts.** No tie-break between different strategies' simultaneous signals is approved, so such a day is marked unresolved and nothing is traded: 11 of 738 sessions in this window (3 / 1 / 7 by year). This conservative rule removes trades; it is preserved from Phase 3.0 and was not changed.

**Status labels.** `DATA_VALIDATED` means the DATA window passed the quality gate (coverage, structure, calendar); it says nothing about whether the strategy is validated: this window's gross is Rs 509,398, net Rs -32,612 (profit factor 0.991 net). Windows B and B_TV are not on identical session sets (2023-10-19 is excluded in B only).

## Vendor sensitivity (the same window on the secondary vendor's minute bars)

| row | status | trades | gross Rs | net Rs | profit factor | max drawdown Rs |
|---|---|---|---|---|---|---|
| B1_2022_23 | DATA_VALIDATED | 198 | 288,454 | 112,234 | 1.268 | 188,341 |
| B1_TV | VENDOR_SENSITIVITY | 192 | 474,152 | 303,272 | 1.5017 | 139,493 |
| B2_2023_24 | DATA_VALIDATED | 219 | -3,851 | -198,761 | 0.9971 | 186,313 |
| B2_TV | VENDOR_SENSITIVITY | 219 | -83,743 | -278,653 | 0.9403 | 268,086 |
| B3_2024_25 | DATA_VALIDATED | 192 | 224,796 | 53,916 | 1.2213 | 173,706 |
| B3_TV | VENDOR_SENSITIVITY | 190 | 235,726 | 66,626 | 1.2362 | 138,586 |
| B_2022_25 | DATA_VALIDATED | 609 | 509,398 | -32,612 | 1.1492 | 188,341 |
| B_2022_25_TV | VENDOR_SENSITIVITY | 601 | 626,135 | 91,245 | 1.1872 | 268,086 |

The two vendors agree on 2591 of 3624 confirmed signals (71.5% of the union) and on 471 identical executed-trade signals (461 with the same outcome); 138 trades exist only on 5paisa bars (gross Rs -4,914) and 130 only on secondary bars (gross Rs 127,394). The identical trades earn about the same on both (Rs 514,312 vs 498,742); **almost all of the Rs 116,737 difference comes from the ~130 trades that exist on only one vendor's bars.** The year-by-year sign pattern is the same on both vendors (the middle year is the weak one), but the size of every result depends materially on which vendor's minute bars are used; neither is shown to be right.

Full detail: `windows/B/` (trades, entry conditions, exits, signals, daily summary), `daily/B/YYYY-MM/` (738 journals), `charts/B/` (609 charts).
