# BANKNIFTY - Phase 5 backtest summary (frozen Phase 3.6 rules, NIFTY index-point parameters, index prices only)

> HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

**What was run.** IRF, ORB, PDR (body-based), PDS and RF through the shared Phase 3.0 controller (first valid signal; at most two trades a day; second trade only PDR/PDS after an initial full stop; 13:00 entry cutoff; same-minute conflicts untraded), exactly as frozen (`FROZEN-PHASE36-42cea2600bd4`; every strategy, controller and framework file verified before each run). Stops 35 points (ORB 30), T1 27, T2 60 (PDR/PDS 70), post-T1 stop entry -/+ 6, forced exit at the open of the 15:14 minute - the NIFTY point values, **not scaled to BANKNIFTY's level**. Units: a fixed 390 per trade is only a rupee comparison device. Data: NSE index BANKNIFTY, scrip 999920005 (see `data_discovery.md`).

## Headline (main window, 5paisa data)

|  | value |
|---|---|
| sessions evaluated / expected | 985 / 992 |
| confirmed / fully valid signals | 4307 / 4244 |
| executed trades (first / second) | 820 (761 / 59) |
| gross weighted index points | -358.5 |
| average points per trade | -0.437 |
| win rate | 58.41% |
| profit factor (points) | 0.9692 |
| max drawdown (index points) | 1303.9 |
| longest losing streak | 7 |
| stop / T1 as % of the index | 0.0695% / 0.055% (avg level 49,812) |
| initial full stops / T1 reached / T2 reached | 41.6% / 58.4% / 22.6% |
| average holding | 6.7 one-minute bars |
| same-minute conflict days | 13 |

## By period

| period | status | sessions | trades | win % | PF (pts) | index points | avg pts/trade | max DD (pts) | stops % | T1 % | T2 % | hold (min) | conflicts |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M_2022_23 2022-09-01..2023-08-31 | DATA_VALIDATED | 248 | 217 | 56.22 | 0.9215 | -254.1 | -1.171 | 937.55 | 43.8 | 56.2 | 23.0 | 9.4 | 5 |
| M_2023_24 2023-09-01..2024-08-31 | DATA_VALIDATED | 243 | 201 | 63.68 | 1.1244 | +310.1 | 1.543 | 420.4 | 36.3 | 63.7 | 21.4 | 6.6 | 3 |
| M_2024_25 2024-09-01..2025-08-31 | DATA_VALIDATED | 247 | 203 | 54.68 | 0.8572 | -448.9 | -2.212 | 877.45 | 45.3 | 54.7 | 22.2 | 5.5 | 3 |
| M_2025_26 2025-09-01..2026-08-31 | DATA_VALIDATED | 247 | 199 | 59.3 | 1.0124 | +34.4 | 0.173 | 363.6 | 40.7 | 59.3 | 23.6 | 5.2 | 2 |
| M_ALL 2022-09-01..2026-08-31 | DATA_VALIDATED | 985 | 820 | 58.41 | 0.9692 | -358.5 | -0.437 | 1303.9 | 41.6 | 58.4 | 22.6 | 6.7 | 13 |
| M_TO_2024_03_22 2022-09-01..2024-03-22 | DATA_VALIDATED | 385 | 328 | 59.45 | 0.9762 | -107.5 | -0.328 | 1038.05 | 40.5 | 59.5 | 21.3 | 8.4 | 7 |
| MS_2022_09_2024_03 2022-09-01..2024-03-22 | VENDOR_SENSITIVITY | 386 | 328 | 58.54 | 0.9133 | -404.4 | -1.233 | 953.25 | 41.5 | 58.5 | 20.1 | 8.8 | 10 |
| C_2018 2018-01-01..2018-12-31 | EXPLORATORY | 245 | 194 | 59.28 | 1.2763 | +744.7 | 3.839 | 183.0 | 40.7 | 59.3 | 34.0 | 24.6 | 3 |
| D_2019_5P_PARTIAL 2019-03-01..2019-12-31 | PARTIAL_YEAR | 196 | 157 | 59.87 | 1.0967 | +208.4 | 1.328 | 420.5 | 40.1 | 59.9 | 26.1 | 14.1 | 3 |
| D_2019_SECONDARY 2019-01-01..2019-12-31 | EXPLORATORY | 244 | 197 | 61.42 | 1.1871 | +482.9 | 2.451 | 507.1 | 38.6 | 61.4 | 26.9 | 17.8 | 3 |

Status: DATA_VALIDATED = the 5paisa data window passed the quality gate (**this says nothing about the strategy**); VENDOR_SENSITIVITY = the same dates on the secondary source; EXPLORATORY = secondary source only, unverifiable; PARTIAL_YEAR = 5paisa minute data start 2019-03-01. Every period is reported; nothing was dropped after seeing results. 2018 and 2019 are historical research with a strategy developed on later NIFTY data.

## By strategy (main window)

| strategy | trades | win % | PF (pts) | index points | avg pts | max DD | stops % | T1 % | T2 % | hold |
|---|---|---|---|---|---|---|---|---|---|---|
| IRF | 445 | 60.45 | 1.0299 | +185.6 | 0.417 | 666.35 | 39.6 | 60.4 | 24.3 | 6.7 |
| ORB | 147 | 55.78 | 0.9323 | -132.0 | -0.898 | 456.0 | 44.2 | 55.8 | 19.7 | 2.9 |
| PDR | 131 | 55.73 | 0.8643 | -275.6 | -2.103 | 427.55 | 44.3 | 55.7 | 19.8 | 11.4 |
| PDS | 36 | 61.11 | 0.9367 | -31.0 | -0.861 | 164.5 | 38.9 | 61.1 | 16.7 | 5.8 |
| RF | 61 | 54.1 | 0.8923 | -105.5 | -1.73 | 260.0 | 45.9 | 54.1 | 26.2 | 6.5 |

### By strategy and Sep-Aug year (index points)

| strategy | M_2022_23 | M_2023_24 | M_2024_25 | M_2025_26 | C_2018 (exploratory) | D_2019 5paisa (partial) |
|---|---|---|---|---|---|---|
| IRF | +139.5 | +491.1 | -416.4 | -28.6 | +103.0 | -35.5 |
| ORB | -121.5 | -162.0 | -100.5 | +252.0 | +326.2 | +259.4 |
| PDR | -284.6 | +129.0 | -135.5 | +15.5 | +240.0 | +3.0 |
| PDS | -4.0 | -98.0 | +155.5 | -84.5 | +101.0 | -59.5 |
| RF | +16.5 | -50.0 | +48.0 | -120.0 | -25.5 | +41.0 |

PDR (body-based) zone-failure profile in the main window: 131 PDR trades; 325 PDR setups invalidated because the session did not open strictly above the zone (2.48 per trade); 464 PDR setups rejected in total (reasons in `windows/M/rejected_signals.csv`). No zone-failure rule was changed.

## Relative scale of the transferred rules

The stop is 0.0695% of BANKNIFTY on average (T1 0.055%) against 0.1557% (T1 0.1232%) for NIFTY over the same dates. Measured on the 5paisa one-minute bars of 2022-09..2025-08, the median one-minute high-low range is 20.8 points on BANKNIFTY (0.044% of the level; 90th percentile 42.4) against 6.5 points on NIFTY (0.030%). The 35-point stop is therefore about 1.7 median one-minute ranges on BANKNIFTY against 5.4 on NIFTY, which is why trades resolve in minutes here (average holding 6.7 one-minute bars against 65.6 for NIFTY): the stops sit within a few bars of ordinary noise, so the result mostly measures noise at a narrow stop width. This is a rule-transfer diagnostic, not a tradable configuration; nothing was rescaled (that would change the rules), and fills at that precision (entry at the next bar's open, stops filled at the worse of level and open) are a simulation convention, not an execution claim.

## Costs

| fixed Rs / trade | slippage pts / fill | net Rs (fixed 390, synthetic) | profit factor | max DD Rs |
|---|---|---|---|---|
| 0.0 | 0.0 | -139,815 | 0.9692 | 508,521 |
| 0.0 | 0.5 | -459,615 | 0.9017 | 727,311 |
| 0.0 | 1.0 | -779,415 | 0.838 | 993,720 |
| 0.0 | 2.0 | -1,419,015 | 0.7205 | 1,602,120 |
| 500.0 | 0.0 | -549,815 | 0.8834 | 789,021 |
| 500.0 | 0.5 | -869,615 | 0.8206 | 1,079,520 |
| 500.0 | 1.0 | -1,189,415 | 0.7612 | 1,383,720 |
| 500.0 | 2.0 | -1,829,015 | 0.6514 | 1,992,925 |
| 1000.0 | 0.0 | -959,815 | 0.8035 | 1,165,320 |
| 1000.0 | 0.5 | -1,279,615 | 0.745 | 1,469,520 |
| 1000.0 | 1.0 | -1,599,415 | 0.6895 | 1,773,965 |
| 1000.0 | 2.0 | -2,239,015 | 0.5867 | 2,383,925 |
| 1500.0 | 0.0 | -1,369,815 | 0.7291 | 1,555,320 |
| 1500.0 | 0.5 | -1,689,615 | 0.6744 | 1,859,985 |
| 1500.0 | 1.0 | -2,009,415 | 0.6224 | 2,164,965 |
| 1500.0 | 2.0 | -2,649,015 | 0.526 | 2,774,925 |

Rs figures use the fixed 390-unit multiplier (a comparison device; not contract P&L; not comparable with the other indices). The average trade earns -0.437 weighted index points before costs. 0.5 point of slippage on every unit of the three fills (390 entry + 195 + 195 exit units) costs 1.0 weighted index point per trade, so an average trade below that does not survive even this mild slippage assumption; the grid above shows the full range.

## Vendor sensitivity (same frozen system, same dates, different minute data)

| comparison | sessions_in_both | trades_5paisa | trades_secondary | identical_trade_signals | same_outcome_among_identical | trades_only_5paisa | trades_only_secondary | gross_index_points_5paisa | gross_index_points_secondary | points_on_identical_trades_5paisa | points_on_identical_trades_secondary | points_on_trades_only_5paisa | points_on_trades_only_secondary | confirmed_signals_5paisa | confirmed_signals_secondary | signals_in_both | signal_agreement_pct_of_union |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2022-09-01..2024-03-22: 5paisa vs secondary-source minutes | 385 | 328 | 326 | 241 | 227 | 87 | 85 | -107.55 | -334.35 | -93.0 | 103.75 | -14.55 | -438.1 | 1783 | 1721 | 1385 | 65.4 |
| 2019-03..12: 5paisa vs secondary-source minutes (sessions of both) | 196 | 157 | 155 | 133 | 125 | 24 | 22 | 208.45 | 371.9 | 485.9 | 337.4 | -277.45 | 34.5 | 864 | 841 | 760 | 80.4 |

The result depends materially on which vendor's bars are used; the trade sets overlap only partly. Neither vendor can be declared correct.

## Files

`windows/<M|MS|C|D_5P|D_TV>/` (trades, exits, entry conditions, candles, signals, rejected/ignored signals, daily summary, issues, configuration snapshot), `daily/<window>/YYYY-MM/YYYY-MM-DD.md` (one journal per evaluated session including no-trade days, each with an option-feasibility block), `charts/<window>/<trade>.svg` (actual candles), `BANKNIFTY_Daily_Verification.xlsx`, `trade_level_signals.csv`, `daily_summary.csv`, `strategy_performance.csv`, `entry_explanations.csv`, `exit_explanations.csv`, `cost_sensitivity.csv`, `vendor_sensitivity.csv`, `monthly_index_points.csv`, `data/` (quality tables, coverage, overlaps).
