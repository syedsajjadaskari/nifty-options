# 2018 backtest summary (Window C, 2018-01-01 .. 2018-12-31) - EXPLORATORY

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

**Status: EXPLORATORY.** 5paisa returns no one-minute data for 2018, so the only minute source is the secondary vendor, whose bars differ systematically from 5paisa wherever the two can be compared (2019-2026) and which cannot be checked against any other vendor for 2018. The official daily closes and the 200-day averages come from the 5paisa daily series. This is a full calendar year of sessions (244 of 245 usable; 2018-07-09 lacks its 09:15 bar and is excluded), but the data confidence is the lowest tier.

## Headline (frozen Phase 3.6 configuration, no parameter changed)

| row | status | confidence | sessions | trades (1st/2nd) | IRF / ORB / PDR / PDS / RF | index points | gross Rs (390 units) | illustrative net Rs | win % | profit factor (gross / net) | max drawdown Rs | longest losing streak |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_2018 | EXPLORATORY | EXPLORATORY_UNVERIFIABLE | 244 | 185 (180/5) | 90 / 42 / 32 / 3 / 18 | -261.7 | -102,063 | -266,713 | 52.43 | 0.9074 / 0.7745 | 157,287 | 6 |

| row | avg trade Rs | median trade Rs | largest win Rs | largest loss Rs | Target 2 | T1 then buffer stop | initial full stop | forced exit | conflict days | unresolved | positive / negative months | trades per session | avg holding (min) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_2018 | -551.69 | 1170.0 | 18,915 | -13,650 | 31 | 27 | 80 | 47 | 0 | 0 | 4 / 8 | 0.7582 | 187.12 |

## By strategy (gross Rs, 390 units)

| row | strategy | trades | gross Rs | net Rs | win % | profit factor | share of gross |
|---|---|---|---|---|---|---|---|
| C_2018 | IRF | 90 | -66,826 | -146,926 | 50.0 | 0.8846 | n/m (window gross not positive) |
| C_2018 | ORB | 42 | 185,152 | 147,772 | 71.43 | 2.427 | n/m (window gross not positive) |
| C_2018 | PDR | 32 | -115,966 | -144,446 | 46.88 | 0.4746 | n/m (window gross not positive) |
| C_2018 | PDS | 3 | -18,447 | -21,117 | 33.33 | 0.3243 | n/m (window gross not positive) |
| C_2018 | RF | 18 | -85,976 | -101,996 | 33.33 | 0.4082 | n/m (window gross not positive) |

## Monthly P&L (gross Rs)

| month | C_2018 |
|---|---|
| 2018-01 | -36,914 |
| 2018-02 | -54,210 |
| 2018-03 | 113,997 |
| 2018-04 | -62,264 |
| 2018-05 | 18,291 |
| 2018-06 | -8,541 |
| 2018-07 | -80,282 |
| 2018-08 | 41,866 |
| 2018-09 | 31,551 |
| 2018-10 | -12,090 |
| 2018-11 | -40,696 |
| 2018-12 | -12,772 |

## Coverage and exceptions (per row: the sessions of that period only)

* **C_2018** (2018-01-01..2018-12-31): 245 sessions in the source, 244 usable; excluded: 2018-07-09 EXCLUDED_NON_STANDARD_START; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): 2; expected sessions 246, missing from the source: 2018-11-07; warm-up sessions in the same source: 30.

The year is loss-making: gross Rs -102,063, profit factor 0.9074. The losses are concentrated in high-volatility sessions (see `robustness_report.md`). The result is reported as it is; no period, strategy or trade was removed. **Scale caveat:** the stops and targets are fixed index POINTS, and the index was about 2.3x lower in 2018 than in 2025, so the same 35-point stop is about twice as wide in relative terms (see the scale table in `robustness_report.md`); 2018 is therefore not a like-for-like test of the strategy's risk, and holds positions longer (more forced exits).

Full detail: `windows/C/`, `daily/C/YYYY-MM/` (244 journals), `charts/C/` (185 charts).
