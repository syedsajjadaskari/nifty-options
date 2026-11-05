# 2019 backtest summary (Window D)

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

Two runs, never merged: (1) the **secondary vendor's full calendar year 2019** (244 sessions, EXPLORATORY: no independent check exists for January-February, and the March-December overlap with 5paisa shows different bars) and (2) **5paisa minutes 2019-03-01 .. 2019-12-31, a PARTIAL YEAR** (196 of 201 expected sessions; five sessions are missing from the provider; no minute warm-up exists before the first session). Where the two overlap they disagree on 33% of signals.

## Headline (frozen Phase 3.6 configuration, no parameter changed)

| row | status | confidence | sessions | trades (1st/2nd) | IRF / ORB / PDR / PDS / RF | index points | gross Rs (390 units) | illustrative net Rs | win % | profit factor (gross / net) | max drawdown Rs | longest losing streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D_2019_SECONDARY | EXPLORATORY | EXPLORATORY_UNVERIFIABLE | 244 | 182 (177/5) | 106 / 37 / 21 / 3 / 15 | 772.6 | 301,314 | 139,334 | 61.54 | 1.3565 / 1.1535 | 99,508 | 5 |
| D_2019_5PAISA_PARTIAL | PARTIAL_YEAR | LOW | 196 | 149 (145/4) | 85 / 35 / 17 / 2 / 10 | 904.12 | 352,609 | 219,999 | 64.43 | 1.5356 / 1.3118 | 74,246 | 4 |

| row | avg trade Rs | median trade Rs | largest win Rs | largest loss Rs | Target 2 | T1 then buffer stop | initial full stop | forced exit | conflict days | unresolved | positive / negative months | trades per session | avg holding (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| D_2019_SECONDARY | 1655.57 | 4095.0 | 18,915 | -13,650 | 49 | 49 | 61 | 23 | 4 | 0 | 8 / 4 | 0.7459 | 168.61 |
| D_2019_5PAISA_PARTIAL | 2366.5 | 4095.0 | 18,915 | -13,650 | 42 | 37 | 49 | 21 | 4 | 0 | 7 / 3 | 0.7602 | 168.94 |

## By strategy (gross Rs, 390 units)

| row | strategy | trades | gross Rs | net Rs | win % | profit factor | share of gross |
|---|---|---|---|---|---|---|---|
| D_2019_SECONDARY | IRF | 106 | 167,427 | 73,087 | 61.32 | 1.3404 | 55.6 |
| D_2019_SECONDARY | ORB | 37 | 136,617 | 103,687 | 67.57 | 1.9731 | 45.3 |
| D_2019_SECONDARY | PDR | 21 | -35,763 | -54,453 | 47.62 | 0.7457 | -11.9 |
| D_2019_SECONDARY | PDS | 3 | -5,460 | -8,130 | 66.67 | 0.6 | -1.8 |
| D_2019_SECONDARY | RF | 15 | 38,493 | 25,143 | 66.67 | 1.6576 | 12.8 |
| D_2019_5PAISA_PARTIAL | IRF | 85 | 169,621 | 93,971 | 63.53 | 1.4331 | 48.1 |
| D_2019_5PAISA_PARTIAL | ORB | 35 | 127,969 | 96,819 | 65.71 | 1.9106 | 36.3 |
| D_2019_5PAISA_PARTIAL | PDR | 17 | 9,009 | -6,121 | 58.82 | 1.1058 | 2.6 |
| D_2019_5PAISA_PARTIAL | PDS | 2 | -9,555 | -11,335 | 50.0 | 0.3 | -2.7 |
| D_2019_5PAISA_PARTIAL | RF | 10 | 55,565 | 46,665 | 80.0 | 3.0354 | 15.8 |

## Monthly P&L (gross Rs)

| month | D_2019_SECONDARY | D_2019_5PAISA_PARTIAL |
|---|---|---|
| 2019-01 | 52,240 | - |
| 2019-02 | -8,678 | - |
| 2019-03 | 45,064 | 90,938 |
| 2019-04 | -13,728 | -8,054 |
| 2019-05 | 52,221 | 104,510 |
| 2019-06 | 26,286 | 12,714 |
| 2019-07 | 34,086 | 43,641 |
| 2019-08 | 87,750 | 57,135 |
| 2019-09 | 79,911 | 60,401 |
| 2019-10 | -27,105 | -34,213 |
| 2019-11 | -56,998 | -4,144 |
| 2019-12 | 30,264 | 29,679 |

## Coverage and exceptions (per row: the sessions of that period only)

* **D_2019_SECONDARY** (2019-01-01..2019-12-31): 244 sessions in the source, 244 usable; excluded: none; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 3; expected sessions 244, missing from the source: none; warm-up sessions in the same source: 29.
* **D_2019_5PAISA_PARTIAL** (2019-03-01..2019-12-31): 196 sessions in the source, 196 usable; excluded: none; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 7; expected sessions 201, missing from the source: 2019-06-27;2019-06-28;2019-07-01;2019-07-02;2019-07-03; warm-up sessions in the same source: 0.

## Vendor comparison for 2019 (sessions present in both)

| row | status | trades | gross Rs | net Rs | profit factor |
|---|---|---|---|---|---|
| D_2019_5PAISA_PARTIAL | PARTIAL_YEAR | 149 | 352,609 | 219,999 | 1.5356 |
| D_2019_SECONDARY | EXPLORATORY | 182 | 301,314 | 139,334 | 1.3565 |

On the 196 sessions both sources have (2019-03..12): 149 trades on 5paisa bars vs 149 on secondary bars, 118 identical trade signals (116 same outcome), gross Rs 352,609 vs 259,623; signal agreement 66.6% of the union. **The 5paisa result is a partial year (10 months, 196 of 201 expected sessions) and must not be read as full-year 2019 performance.** The secondary result is the only full calendar year but is exploratory.

Full detail: `windows/D_TV/`, `windows/D_5P/`, `daily/D_TV|D_5P/YYYY-MM/` (440 journals), charts under `charts/D_TV/` and `charts/D_5P/`.
