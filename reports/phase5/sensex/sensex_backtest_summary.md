# SENSEX - Phase 5 backtest summary (frozen Phase 3.6 rules, NIFTY index-point parameters, index prices only)

> HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

**What was run.** IRF, ORB, PDR (body-based), PDS and RF through the shared Phase 3.0 controller (first valid signal; at most two trades a day; second trade only PDR/PDS after an initial full stop; 13:00 entry cutoff; same-minute conflicts untraded), exactly as frozen (`FROZEN-PHASE36-42cea2600bd4`; every strategy, controller and framework file verified before each run). Stops 35 points (ORB 30), T1 27, T2 60 (PDR/PDS 70), post-T1 stop entry -/+ 6, forced exit at the open of the 15:14 minute - the NIFTY point values, **not scaled to SENSEX's level**. Units: a fixed 390 per trade is only a rupee comparison device. Data: BSE index SENSEX, scrip 999901 (see `data_discovery.md`).

## Headline (main window, 5paisa data)

|  | value |
|---|---|
| sessions evaluated / expected | 983 / 988 |
| confirmed / fully valid signals | 4237 / 4171 |
| executed trades (first / second) | 821 (755 / 66) |
| gross weighted index points | +97.2 |
| average points per trade | 0.118 |
| win rate | 57.98% |
| profit factor (points) | 1.0082 |
| max drawdown (index points) | 1713.61 |
| longest losing streak | 10 |
| stop / T1 as % of the index | 0.0472% / 0.0372% (avg level 73,490) |
| initial full stops / T1 reached / T2 reached | 42.0% / 58.0% / 24.8% |
| average holding | 5.7 one-minute bars |
| same-minute conflict days | 10 |

## By period

| period | status | sessions | trades | win % | PF (pts) | index points | avg pts/trade | max DD (pts) | stops % | T1 % | T2 % | hold (min) | conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M_2022_23 2022-09-01..2023-08-31 | DATA_VALIDATED | 247 | 206 | 60.68 | 1.2433 | +671.9 | 3.262 | 279.59 | 39.3 | 60.7 | 30.1 | 9.2 | 2 |
| M_2023_24 2023-09-01..2024-08-31 | DATA_VALIDATED | 242 | 208 | 52.88 | 0.7134 | -960.1 | -4.616 | 1408.67 | 47.1 | 52.9 | 17.8 | 4.9 | 1 |
| M_2024_25 2024-09-01..2025-08-31 | DATA_VALIDATED | 247 | 204 | 58.82 | 1.1111 | +323.5 | 1.586 | 633.6 | 41.2 | 58.8 | 28.4 | 4.1 | 1 |
| M_2025_26 2025-09-01..2026-08-31 | DATA_VALIDATED | 247 | 203 | 59.61 | 1.0221 | +61.9 | 0.305 | 582.23 | 40.4 | 59.6 | 23.2 | 4.4 | 6 |
| M_ALL 2022-09-01..2026-08-31 | DATA_VALIDATED | 983 | 821 | 57.98 | 1.0082 | +97.2 | 0.118 | 1713.61 | 42.0 | 58.0 | 24.8 | 5.7 | 10 |
| M_TO_2024_03_22 2022-09-01..2024-03-22 | DATA_VALIDATED | 384 | 318 | 59.12 | 1.0939 | +414.3 | 1.303 | 707.12 | 40.9 | 59.1 | 26.4 | 8.1 | 2 |
| MS_2022_09_2024_03 2022-09-01..2024-03-22 | VENDOR_SENSITIVITY | 386 | 326 | 56.75 | 0.9841 | -76.5 | -0.235 | 789.0 | 43.3 | 56.7 | 25.2 | 7.8 | 4 |
| C_2018 2018-01-01..2018-12-31 | EXPLORATORY | 198 | 151 | 61.59 | 1.3496 | +675.0 | 4.47 | 288.5 | 37.7 | 61.6 | 31.8 | 23.7 | 2 |
| D_2019_5P_PARTIAL 2019-03-01..2019-12-31 | PARTIAL_YEAR | 201 | 170 | 64.12 | 1.4105 | +860.5 | 5.062 | 220.01 | 35.9 | 64.1 | 31.8 | 16.2 | 1 |
| D_2019_SECONDARY 2019-01-01..2019-12-31 | EXPLORATORY | 235 | 191 | 62.3 | 1.2944 | +727.5 | 3.809 | 220.01 | 37.7 | 62.3 | 30.4 | 16.7 | 1 |

Status: DATA_VALIDATED = the 5paisa data window passed the quality gate (**this says nothing about the strategy**); VENDOR_SENSITIVITY = the same dates on the secondary source; EXPLORATORY = secondary source only, unverifiable; PARTIAL_YEAR = 5paisa minute data start 2019-03-01. Every period is reported; nothing was dropped after seeing results. 2018 and 2019 are historical research with a strategy developed on later NIFTY data.

## By strategy (main window)

| strategy | trades | win % | PF (pts) | index points | avg pts | max DD | stops % | T1 % | T2 % | hold |
|---|---|---|---|---|---|---|---|---|---|---|
| IRF | 444 | 59.68 | 1.0082 | +51.5 | 0.116 | 899.84 | 40.3 | 59.7 | 24.3 | 5.7 |
| ORB | 127 | 55.12 | 1.1631 | +278.9 | 2.196 | 423.12 | 44.9 | 55.1 | 29.9 | 2.2 |
| PDR | 129 | 55.81 | 0.8354 | -328.6 | -2.547 | 763.05 | 44.2 | 55.8 | 18.6 | 9.5 |
| PDS | 56 | 55.36 | 1.02 | +17.5 | 0.312 | 269.5 | 44.6 | 55.4 | 26.8 | 5.2 |
| RF | 65 | 58.46 | 1.0822 | +77.9 | 1.198 | 299.5 | 41.5 | 58.5 | 29.2 | 4.8 |

### By strategy and Sep-Aug year (index points)

| strategy | M_2022_23 | M_2023_24 | M_2024_25 | M_2025_26 | C_2018 (exploratory) | D_2019 5paisa (partial) |
|---|---|---|---|---|---|---|
| IRF | +53.9 | +23.1 | -176.4 | +151.0 | +352.5 | +485.0 |
| ORB | +286.5 | -352.6 | +385.5 | -40.5 | +270.0 | +525.0 |
| PDR | +247.0 | -541.5 | +66.0 | -100.0 | -60.5 | -97.0 |
| PDS | +123.5 | -25.0 | -170.0 | +89.0 | +0.0 | +13.5 |
| RF | -39.0 | -64.0 | +218.4 | -37.5 | +113.0 | -66.0 |

PDR (body-based) zone-failure profile in the main window: 129 PDR trades; 317 PDR setups invalidated because the session did not open strictly above the zone (2.46 per trade); 471 PDR setups rejected in total (reasons in `windows/M/rejected_signals.csv`). No zone-failure rule was changed.

## Relative scale of the transferred rules

The stop is 0.0472% of SENSEX on average (T1 0.0372%) against 0.1557% (T1 0.1232%) for NIFTY over the same dates. Measured on the 5paisa one-minute bars of 2022-09..2025-08, the median one-minute high-low range is 20.4 points on SENSEX (0.029% of the level; 90th percentile 44.0) against 6.5 points on NIFTY (0.030%). The 35-point stop is therefore about 1.7 median one-minute ranges on SENSEX against 5.4 on NIFTY, which is why trades resolve in minutes here (average holding 5.7 one-minute bars against 65.6 for NIFTY): the stops sit within a few bars of ordinary noise, so the result mostly measures noise at a narrow stop width. This is a rule-transfer diagnostic, not a tradable configuration; nothing was rescaled (that would change the rules), and fills at that precision (entry at the next bar's open, stops filled at the worse of level and open) are a simulation convention, not an execution claim.

## Costs

| fixed Rs / trade | slippage pts / fill | net Rs (fixed 390, synthetic) | profit factor | max DD Rs |
|---|---|---|---|---|
| 0.0 | 0.0 | 37,922 | 1.0082 | 668,306 |
| 0.0 | 0.5 | -282,268 | 0.9405 | 785,696 |
| 0.0 | 1.0 | -602,458 | 0.8765 | 955,373 |
| 0.0 | 2.0 | -1,242,838 | 0.7586 | 1,405,273 |
| 500.0 | 0.0 | -372,578 | 0.9221 | 818,806 |
| 500.0 | 0.5 | -692,768 | 0.8591 | 1,013,123 |
| 500.0 | 1.0 | -1,012,958 | 0.7995 | 1,224,953 |
| 500.0 | 2.0 | -1,653,338 | 0.6893 | 1,745,418 |
| 1000.0 | 0.0 | -783,078 | 0.842 | 1,070,873 |
| 1000.0 | 0.5 | -1,103,268 | 0.7833 | 1,295,793 |
| 1000.0 | 1.0 | -1,423,458 | 0.7276 | 1,546,953 |
| 1000.0 | 2.0 | -2,063,838 | 0.6244 | 2,134,378 |
| 1500.0 | 0.0 | -1,193,578 | 0.7673 | 1,366,633 |
| 1500.0 | 0.5 | -1,513,768 | 0.7124 | 1,617,793 |
| 1500.0 | 1.0 | -1,833,958 | 0.6602 | 1,915,978 |
| 1500.0 | 2.0 | -2,474,338 | 0.5634 | 2,524,378 |

Rs figures use the fixed 390-unit multiplier (a comparison device; not contract P&L; not comparable with the other indices). The average trade earns 0.118 weighted index points before costs. 0.5 point of slippage on every unit of the three fills (390 entry + 195 + 195 exit units) costs 1.0 weighted index point per trade, so an average trade below that does not survive even this mild slippage assumption; the grid above shows the full range.

## Vendor sensitivity (same frozen system, same dates, different minute data)

| comparison | sessions_in_both | trades_5paisa | trades_secondary | identical_trade_signals | same_outcome_among_identical | trades_only_5paisa | trades_only_secondary | gross_index_points_5paisa | gross_index_points_secondary | points_on_identical_trades_5paisa | points_on_identical_trades_secondary | points_on_trades_only_5paisa | points_on_trades_only_secondary | confirmed_signals_5paisa | confirmed_signals_secondary | signals_in_both | signal_agreement_pct_of_union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-09-01..2024-03-22: 5paisa vs secondary-source minutes | 384 | 318 | 324 | 262 | 258 | 56 | 62 | 414.29 | -90.0 | 48.5 | 43.5 | 365.79 | -133.5 | 1690 | 1666 | 1486 | 79.5 |
| 2019-03..12: 5paisa vs secondary-source minutes (sessions of both) | 201 | 170 | 168 | 158 | 157 | 12 | 10 | 860.49 | 806.49 | 824.99 | 857.99 | 35.5 | -51.5 | 898 | 872 | 821 | 86.5 |

The result depends materially on which vendor's bars are used; the trade sets overlap only partly. Neither vendor can be declared correct.

## Files

`windows/<M|MS|C|D_5P|D_TV>/` (trades, exits, entry conditions, candles, signals, rejected/ignored signals, daily summary, issues, configuration snapshot), `daily/<window>/YYYY-MM/YYYY-MM-DD.md` (one journal per evaluated session including no-trade days, each with an option-feasibility block), `charts/<window>/<trade>.svg` (actual candles), `SENSEX_Daily_Verification.xlsx`, `trade_level_signals.csv`, `daily_summary.csv`, `strategy_performance.csv`, `entry_explanations.csv`, `exit_explanations.csv`, `cost_sensitivity.csv`, `vendor_sensitivity.csv`, `monthly_index_points.csv`, `data/` (quality tables, coverage, overlaps).
