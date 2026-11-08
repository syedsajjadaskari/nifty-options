# Combined five-strategy backtest - summary (Phase 5.5)

SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill).

Primary window 2025-09-01..2026-08-31 (5paisa one-minute NIFTY 50), three configurations run INDEPENDENTLY through the unchanged controller (first valid signal; max two trades; second trade only PDR / PDS after an original full stop; 13:00 cutoff; no strategy priority). **No configuration is selected, ranked or approved here, and no parameter was tuned.**

## Headline (gross, synthetic)

| configuration | sessions | sessions with a trade | no-trade sessions | trades (first / second) | gross points | avg points / trade | win rate % | profit factor (gross) | max drawdown Rs (gross) | T1 hits | T2 hits | full stops | post-T1 stops | forced exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 247 | 188 | 59 | 196 (188 / 8) | 763.5 | 3.895 | 59.69 | 1.284 | 130,650 | 117 | 65 | 78 | 52 | 1 |
| B - Phase 5.3 author-corrected | 247 | 175 | 72 | 188 (175 / 13) | 663.0 | 3.526 | 58.51 | 1.25 | 204,146 | 110 | 62 | 77 | 47 | 2 |
| C - B + ORB gap crossing | 247 | 177 | 70 | 190 (177 / 13) | 643.5 | 3.387 | 58.42 | 1.24 | 215,846 | 111 | 62 | 78 | 48 | 2 |

## Cost scenarios (net synthetic Rs)

| scenario | A frozen | B author-corrected | C B + ORB gap |
|---|---|---|---|
| gross P&L (scenario A: no costs) | 297,765 | 258,550 | 250,946 |
| B: Rs 70 per trade, zero slippage | 284,045 | 245,390 | 237,646 |
| C: Rs 70 + 0.25 point slippage per side | 245,825 | 208,730 | 200,596 |
| D: Rs 70 + 0.5 point slippage per side | 207,605 | 172,070 | 163,546 |
| E: Rs 70 + 1.0 point slippage per side | 131,165 | 98,750 | 89,446 |
| win rate % (scenario B / E) | 59.69 / 59.69 | 58.51 / 58.51 | 58.42 / 58.42 |
| profit factor (scenario B / E) | 1.269 / 1.118 | 1.236 / 1.09 | 1.226 / 1.08 |
| max drawdown Rs (scenario B / E) | 133,450 / 175,700 | 207,786 / 248,346 | 219,556 / 260,896 |
| alt: Rs 70 per order FILL (interpretation sensitivity) | 256,605 | 219,070 | 211,046 |

The Rs 70 is applied once per executed trade (entry plus both exit legs); whether it really covers the entry and both partial exits is unconfirmed, so the per-fill alternative is shown. Slippage is applied to the ACTUAL filled units (entry 390 once; each exited leg 195 once). Percent returns are not given: no capital base was specified.

## Strategy-wise results (the executed portfolio trades of each configuration; not standalone backtests)

| cfg | strategy | raw signals | sessions with a pre-cutoff signal | executed | first / second | winners | win % | gross Rs | gross points | avg points | PF (gross) | max DD Rs | T1 | T2 | full stops | post-T1 stops | forced | avg minutes held | net Rs (Rs 70, 0 slip) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | IRF | 874 | 152 | 109 | 109 / 0 | 60 | 55.05 | -11,408 | -29.25 | -0.268 | 0.983 | 163,215 | 60 | 32 | 49 | 28 | 0 | 43.2 | -19,038 |
| A | ORB | 53 | 41 | 41 | 41 / 0 | 27 | 65.85 | 138,470 | 355.05 | 8.66 | 1.838 | 36,446 | 27 | 15 | 14 | 12 | 0 | 38.9 | 135,600 |
| A | PDR | 87 | 28 | 25 | 21 / 4 | 16 | 64.0 | 94,438 | 242.15 | 9.686 | 1.792 | 35,685 | 16 | 10 | 8 | 6 | 1 | 67.3 | 92,688 |
| A | PDS | 57 | 17 | 11 | 7 / 4 | 8 | 72.73 | 80,554 | 206.55 | 18.777 | 2.959 | 27,476 | 8 | 6 | 3 | 2 | 0 | 79.8 | 79,784 |
| A | RF | 12 | 10 | 10 | 10 / 0 | 6 | 60.0 | -4,290 | -11.0 | -1.1 | 0.921 | 36,855 | 6 | 2 | 4 | 4 | 0 | 92.9 | -4,990 |
| B | IRF | 786 | 132 | 90 | 90 / 0 | 47 | 52.22 | -34,252 | -87.825 | -0.976 | 0.942 | 204,555 | 47 | 28 | 43 | 19 | 0 | 45.0 | -40,552 |
| B | ORB | 53 | 41 | 41 | 41 / 0 | 27 | 65.85 | 138,470 | 355.05 | 8.66 | 1.838 | 36,446 | 27 | 15 | 14 | 12 | 0 | 38.9 | 135,600 |
| B | PDR | 147 | 30 | 28 | 22 / 6 | 19 | 67.86 | 108,615 | 278.5 | 9.946 | 1.925 | 35,490 | 19 | 10 | 8 | 9 | 1 | 64.9 | 106,655 |
| B | PDS | 111 | 19 | 19 | 12 / 7 | 11 | 57.89 | 50,008 | 128.225 | 6.749 | 1.457 | 64,155 | 11 | 7 | 8 | 3 | 1 | 78.2 | 48,678 |
| B | RF | 12 | 10 | 10 | 10 / 0 | 6 | 60.0 | -4,290 | -11.0 | -1.1 | 0.921 | 36,855 | 6 | 2 | 4 | 4 | 0 | 92.9 | -4,990 |
| C | IRF | 786 | 132 | 89 | 89 / 0 | 46 | 51.69 | -51,217 | -131.325 | -1.476 | 0.913 | 204,555 | 46 | 27 | 43 | 19 | 0 | 43.4 | -57,447 |
| C | ORB | 56 | 44 | 44 | 44 / 0 | 29 | 65.91 | 147,830 | 379.05 | 8.615 | 1.836 | 46,390 | 29 | 16 | 15 | 13 | 0 | 37.0 | 144,750 |
| C | PDR | 147 | 30 | 28 | 22 / 6 | 19 | 67.86 | 108,615 | 278.5 | 9.946 | 1.925 | 35,490 | 19 | 10 | 8 | 9 | 1 | 64.9 | 106,655 |
| C | PDS | 111 | 19 | 19 | 12 / 7 | 11 | 57.89 | 50,008 | 128.225 | 6.749 | 1.457 | 64,155 | 11 | 7 | 8 | 3 | 1 | 78.2 | 48,678 |
| C | RF | 12 | 10 | 10 | 10 / 0 | 6 | 60.0 | -4,290 | -11.0 | -1.1 | 0.921 | 36,855 | 6 | 2 | 4 | 4 | 0 | 92.9 | -4,990 |

Standalone strategy results are NOT summed into a portfolio result. A strategy's trades here exist only where the controller selected it (first valid signal), so they depend on every other strategy's signals.

## By calendar year (primary window; gross Rs / Rs 70 net)

| configuration | year | trades | gross points | gross Rs | net Rs (70, 0 slip) | net Rs (70, 1.0 slip) |
|---|---|---|---|---|---|---|
| A | 2025 | 73 | 566.825 | 221,062 | 215,952 | 159,012 |
| A | 2026 | 123 | 196.675 | 76,703 | 68,093 | -27,847 |
| B | 2025 | 66 | 629.75 | 245,602 | 240,982 | 189,502 |
| B | 2026 | 122 | 33.2 | 12,948 | 4,408 | -90,752 |
| C | 2025 | 66 | 629.75 | 245,602 | 240,982 | 189,502 |
| C | 2026 | 124 | 13.7 | 5,343 | -3,337 | -100,057 |

Monthly and annual tables per strategy and cost scenario: `monthly_performance.csv`, `annual_performance.csv`.

## Robustness window 2022-09-01..2025-08-31 (5paisa one-minute data, Phase 4 window B)

738 evaluated sessions. Configuration A reproduces the delivered Phase 4 backtest exactly. Gross synthetic Rs by calendar year (Sep-Dec 2022, 2023, 2024, Jan-Aug 2025); the index-point stops, targets and the 28-point EMA threshold are NOT rescaled although the index level differs by about a third across the window.

| configuration | signals | trades | gross Rs | net Rs (70, 0 slip) | net Rs (70, 1.0 slip) | max DD Rs (gross) | 2022 | 2023 | 2024 | 2025 |
|---|---|---|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 3142 | 609 | 509,398 | 466,768 | -8,252 | 188,341 | 64 / -96,691 | 206 / 462,950 | 210 / 6,484 | 129 / 136,656 |
| B - Phase 5.3 author-corrected | 3121 | 598 | 152,539 | 110,679 | -355,761 | 282,799 | 65 / -148,083 | 198 / 232,586 | 209 / -8,024 | 126 / 76,060 |
| C - B + ORB gap crossing | 3132 | 601 | 269,539 | 227,469 | -241,311 | 280,849 | 65 / -146,133 | 199 / 312,731 | 210 / -2,954 | 127 / 105,895 |

Signals by strategy in the window: A: 2487 IRF / 149 ORB / 305 PDR / 121 PDS / 80 RF; B: 2182 IRF / 149 ORB / 453 PDR / 257 PDS / 80 RF; C: 2182 IRF / 160 ORB / 453 PDR / 257 PDS / 80 RF. Per-trade rows: `multi_year_trades.csv`; per year: `multi_year_by_year.csv`. 2018 and 2019 windows were NOT run: the only 2018 minute source is a secondary vendor with no overlap vendor to check it against, and the 5paisa 2019 minute data is a partial year; mixing them would not be comparable (documented in Phase 4).

## Reading the numbers

* The three configurations differ in P&L, trade counts and drawdown; the differences come from changed signals and the portfolio selection they cause (see `cross_configuration_comparison.md`). Nothing here is evidence that a configuration is better: the author's corrections were not designed to raise P&L, B and C rest on PROVISIONAL conventions, and the results of a single year are exposed to the 2025-26 path.
* The robustness window shows large year-to-year differences (negative and positive years) ; the differences between the configurations in that window are not the same as in the primary window (descriptive only; no configuration is selected).

## What this is NOT

Synthetic index-point P&L is not option P&L: no strike, expiry, premium, bid / ask, lot-size history or realistic option cost is modelled. An options study needs historical option contracts and premiums (`reports/phase5/options_feasibility/` records what is missing).
