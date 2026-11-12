# Standalone ORB V2 backtest (30-point stop / 60-point target, one trade per session)

**Synthetic research result.** P&L = NIFTY 50 index points x a declared 75 units; the index cannot be traded and nothing here is CE/PE option P&L (that would need historical strike, expiry, premium and lot data, which are not invented). Not optimised, not approved, not a forecast. No configuration is selected. Neither period is untouched out-of-sample.

Execution conventions (provisional, declared before results): entry at the open of the 09:20 one-minute bar; stop first when both are touched in one minute (none occurred); a bar that opens through the stop fills at its open; targets fill at the target price; forced exit at the open of the 15:14 bar (never at/after 15:15, never on closing-auction bars). Costs: owner's indicative Rs 70 per trade (not a verified brokerage bill) and slippage per side.

## Headline by configuration

| window | config_id | evaluable_sessions | signals | executed_trades | buy | sell | wins | losses | win_rate_pct | profit_factor | avg_win_rs | avg_loss_rs | avg_points_per_trade | total_points | total_rs | max_drawdown_rs | longest_losing_streak | target_pct | stop_pct | forced_pct | avg_hold_minutes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | ORB-V2-A | 247 | 39 | 39 | 20 | 19 | 14 | 25 | 35.9 | 1.115 | 4500.0 | -2260.4 | 2.219 | 86.55 | 6491.2 | 15750.0 | 6 | 35.9 | 64.1 | 0.0 | 43.9 |
| A | ORB-V2-B | 247 | 39 | 39 | 20 | 19 | 14 | 25 | 35.9 | 1.115 | 4500.0 | -2260.4 | 2.219 | 86.55 | 6491.2 | 15750.0 | 6 | 35.9 | 64.1 | 0.0 | 43.9 |
| A | ORB-V2-C | 247 | 37 | 37 | 19 | 18 | 14 | 23 | 37.84 | 1.211 | 4500.0 | -2261.3 | 3.961 | 146.55 | 10991.2 | 15750.0 | 6 | 37.8 | 62.2 | 0.0 | 41.6 |
| A | ORB-V2-D | 247 | 34 | 34 | 17 | 17 | 11 | 23 | 32.35 | 0.952 | 4500.0 | -2261.3 | -0.984 | -33.45 | -2508.8 | 22500.0 | 9 | 32.4 | 67.6 | 0.0 | 44.4 |
| A | DIAG-A-OLDSIDE | 247 | 27 | 27 | 13 | 14 | 10 | 17 | 37.04 | 1.176 | 4500.0 | -2250.0 | 3.333 | 90.0 | 6750.0 | 11250.0 | 5 | 37.0 | 63.0 | 0.0 | 42.9 |
| B | ORB-V2-A | 738 | 93 | 93 | 40 | 53 | 42 | 51 | 45.16 | 1.61 | 4339.5 | -2219.3 | 9.903 | 921.0 | 69075.0 | 13500.0 | 6 | 43.0 | 53.8 | 3.2 | 67.4 |
| B | ORB-V2-B | 738 | 94 | 94 | 41 | 53 | 43 | 51 | 45.74 | 1.65 | 4343.2 | -2219.3 | 10.436 | 981.0 | 73575.0 | 13500.0 | 6 | 43.6 | 53.2 | 3.2 | 66.9 |
| B | ORB-V2-C | 738 | 85 | 85 | 39 | 46 | 38 | 47 | 44.71 | 1.551 | 4322.6 | -2252.8 | 9.157 | 778.35 | 58376.3 | 13500.0 | 5 | 42.4 | 55.3 | 2.4 | 68.7 |
| B | ORB-V2-D | 738 | 85 | 85 | 36 | 49 | 39 | 46 | 45.88 | 1.656 | 4327.1 | -2215.9 | 10.482 | 891.0 | 66825.0 | 13500.0 | 6 | 43.5 | 52.9 | 3.5 | 68.9 |
| B | DIAG-A-OLDSIDE | 738 | 59 | 59 | 20 | 39 | 30 | 29 | 50.85 | 2.018 | 4275.3 | -2191.6 | 14.622 | 862.7 | 64702.5 | 13500.0 | 5 | 47.5 | 47.5 | 5.1 | 68.8 |


## ORB-V2-A by calendar year

| window | config_id | calendar_year | trades | wins | win_rate_pct | profit_factor | total_points | total_rs | max_drawdown_rs | longest_losing_streak |
|---|---|---|---|---|---|---|---|---|---|---|
| A | ORB-V2-A | 2025 | 13 | 2 | 15.38 | 0.364 | -210.0 | -15750.0 | 15750.0 | 6 |
| A | ORB-V2-A | 2026 | 26 | 12 | 46.15 | 1.7 | 296.55 | 22241.2 | 11508.8 | 4 |
| B | ORB-V2-A | 2022 | 12 | 6 | 50.0 | 1.742 | 133.6 | 10020.0 | 4500.0 | 2 |
| B | ORB-V2-A | 2023 | 32 | 13 | 40.62 | 1.345 | 189.1 | 14182.5 | 7766.2 | 3 |
| B | ORB-V2-A | 2024 | 28 | 11 | 39.29 | 1.29 | 148.3 | 11122.5 | 11377.5 | 4 |
| B | ORB-V2-A | 2025 | 21 | 12 | 57.14 | 2.667 | 450.0 | 33750.0 | 9000.0 | 4 |


## ORB-V2-A cost and slippage scenarios

| window | cost_rs_per_trade | slippage_points_per_side | trades | win_rate_pct | profit_factor | total_points | total_rs | max_drawdown_rs |
|---|---|---|---|---|---|---|---|---|
| A | 0 | 0.0 | 39 | 35.9 | 1.115 | 86.55 | 6491.2 | 15750.0 |
| A | 0 | 0.25 | 39 | 35.9 | 1.088 | 67.05 | 5028.7 | 16237.5 |
| A | 0 | 0.5 | 39 | 35.9 | 1.061 | 47.55 | 3566.2 | 16725.0 |
| A | 0 | 1.0 | 39 | 35.9 | 1.011 | 8.55 | 641.2 | 17700.0 |
| A | 70 | 0.0 | 39 | 35.9 | 1.065 | 86.55 | 3761.2 | 16660.0 |
| A | 70 | 0.25 | 39 | 35.9 | 1.039 | 67.05 | 2298.7 | 17147.5 |
| A | 70 | 0.5 | 39 | 35.9 | 1.014 | 47.55 | 836.2 | 17635.0 |
| A | 70 | 1.0 | 39 | 35.9 | 0.966 | 8.55 | -2088.8 | 18610.0 |
| B | 0 | 0.0 | 93 | 45.16 | 1.61 | 921.0 | 69075.0 | 13500.0 |
| B | 0 | 0.25 | 93 | 45.16 | 1.57 | 874.5 | 65587.5 | 13725.0 |
| B | 0 | 0.5 | 93 | 45.16 | 1.531 | 828.0 | 62100.0 | 13950.0 |
| B | 0 | 1.0 | 93 | 45.16 | 1.456 | 735.0 | 55125.0 | 14400.0 |
| B | 70 | 0.0 | 93 | 45.16 | 1.536 | 921.0 | 62565.0 | 13920.0 |
| B | 70 | 0.25 | 93 | 45.16 | 1.498 | 874.5 | 59077.5 | 14145.0 |
| B | 70 | 0.5 | 93 | 45.16 | 1.461 | 828.0 | 55590.0 | 14370.0 |
| B | 70 | 1.0 | 93 | 45.16 | 1.391 | 735.0 | 48615.0 | 15117.5 |


## Signal funnel (config A, cumulative in rulebook order)

| window | step | condition (cumulative, in rulebook order) | sessions_remaining |
|---|---|---|---|
| A | 0 | evaluable sessions | 247 |
| A | 1 | close not on the EMA (direction defined) | 247 |
| A | 2 | gap within limit | 230 |
| A | 3 | previous-day level broken | 206 |
| A | 4 | candle colour matches | 120 |
| A | 5 | at least one pattern | 44 |
| A | 6 | wrong-side wick <= 20% | 39 |
| B | 0 | evaluable sessions | 738 |
| B | 1 | close not on the EMA (direction defined) | 738 |
| B | 2 | gap within limit | 718 |
| B | 3 | previous-day level broken | 630 |
| B | 4 | candle colour matches | 326 |
| B | 5 | at least one pattern | 100 |
| B | 6 | wrong-side wick <= 20% | 93 |


Sole failed gate (sessions failing exactly one condition):
| window | GAP_TOO_LARGE | LEVEL_NOT_BROKEN | COLOUR_MISMATCH | NO_PATTERN | WRONG_SIDE_WICK | signals |
|---|---|---|---|---|---|---|
| A | 2 | 3 | 0 | 26 | 5 | 39 |
| B | 2 | 10 | 0 | 89 | 7 | 93 |
| A_TV | 1 | 2 | 0 | 31 | 6 | 31 |
| B_TV | 1 | 5 | 0 | 97 | 7 | 72 |


Eligibility categories overlap (one trade can satisfy several rules); see `performance_by_eligibility_category.csv`. One combined, non-double-counted result per configuration is the headline table above. Monthly results: `monthly_performance.csv`; annual: `annual_performance.csv`; alternative same-minute stop/target ordering: column `alt_policy_total_points_if_same_bar_resolved_target_first` in `configuration_performance.csv` (no same-minute collision occurred in the primary run).