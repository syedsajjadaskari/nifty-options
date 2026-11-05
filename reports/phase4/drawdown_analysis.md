# Drawdown analysis (Phase 4)

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

Drawdown is measured on the cumulative trade-by-trade synthetic P&L (peak-to-trough, running peak starting at zero), exactly as in Phase 3. Rupee figures use the fixed 390-unit multiplier; index points are the per-unit weighted points of the same trades. The last column states the drawdown as a MULTIPLE of two hypothetical capital levels (Rs 1,00,000, the project's earlier reporting convention, and Rs 5,00,000, an illustrative larger level). **Neither level is claimed to be sufficient to support six derivative lots; no return percentage is computed** because no defensible capital or margin assumption exists for this synthetic cash-index series.

| row | status | max DD gross Rs | max DD net Rs | max DD index points | peak -> trough (trade dates) | trades in the drawdown | period gross Rs | DD as multiple of Rs 1 lakh / Rs 5 lakh | longest losing streak |
|---|---|---|---|---|---|---|---|---|---|
| C_2018 | EXPLORATORY | 157,287 | 282,264 | 403.3 | 2018-03-28 -> 2018-11-15 | 118 | -102,063 | 1.57x / 0.31x | 6 |
| D_2019_SECONDARY | EXPLORATORY | 99,508 | 135,998 | 255.15 | 2019-09-30 -> 2019-12-17 | 41 | 301,314 | 1.00x / 0.20x | 5 |
| D_2019_5PAISA_PARTIAL | PARTIAL_YEAR | 74,246 | 100,056 | 190.38 | 2019-09-30 -> 2019-11-25 | 29 | 352,609 | 0.74x / 0.15x | 4 |
| B1_2022_23 | DATA_VALIDATED | 188,341 | 230,171 | 482.93 | 2022-09-01 -> 2022-12-01 | 47 | 288,454 | 1.88x / 0.38x | 5 |
| B2_2023_24 | DATA_VALIDATED | 186,313 | 295,902 | 477.73 | 2023-12-07 -> 2024-06-10 | 117 | -3,851 | 1.86x / 0.37x | 5 |
| B3_2024_25 | DATA_VALIDATED | 173,706 | 218,206 | 445.4 | 2025-01-22 -> 2025-04-29 | 50 | 224,796 | 1.74x / 0.35x | 7 |
| B_2022_25 | DATA_VALIDATED | 188,341 | 390,816 | 482.93 | 2022-09-01 -> 2022-12-01 | 47 | 509,398 | 1.88x / 0.38x | 7 |
| A_2025_26 | REFERENCE | 130,650 | 178,500 | 335.0 | 2026-04-01 -> 2026-06-11 | 40 | 297,765 | 1.31x / 0.26x | 4 |
| B_2022_25_TV | VENDOR_SENSITIVITY | 268,086 | 405,677 | 687.4 | 2023-12-05 -> 2024-06-20 | 122 | 626,135 | 2.68x / 0.54x | 7 |

| row | max DD gross Rs / period gross Rs |
|---|---|
| C_2018 | n/a (period gross is not positive) |
| D_2019_SECONDARY | 0.33 |
| D_2019_5PAISA_PARTIAL | 0.21 |
| B1_2022_23 | 0.65 |
| B2_2023_24 | n/a (period gross is not positive) |
| B3_2024_25 | 0.77 |
| B_2022_25 | 0.37 |
| A_2025_26 | 0.44 |
| B_2022_25_TV | 0.43 |

Reading: the worst drawdown is large relative to what a whole year earns (see the ratio columns of the tables below), so the equity curve is very noisy relative to its drift; the three-year window's worst drawdown equals the worst single year's (it occurs inside 2022-23). Net drawdowns are larger than gross because the illustrative costs accrue on every trade. The drawdown figures are descriptions of this synthetic history, not a risk limit or a position-sizing recommendation.
