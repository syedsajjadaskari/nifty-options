# Configuration comparison (neutral)

These are four research INTERPRETATIONS of one rulebook, not four strategies and not a ranking. **No configuration is selected, preferred or recommended; none was tuned to history.** The windows are not untouched out-of-sample evidence: the 2025-26 window informed earlier ORB research and the 2022-25 window was used in Phase 4/5 validation. P&L is synthetic NIFTY index-point P&L x 75 units; the index is not tradable.

| id | definition | differs from A by |
|---|---|---|
| ORB-V2-A | written-rule reference (250-pt gap limit, swing-zone inner levels, previous-session candle as engulfing reference) | - |
| ORB-V2-B | 300-pt gap limit | gap limit only |
| ORB-V2-C | clustered repeated-rejection inner zones | inner construction only |
| ORB-V2-D | engulfing disabled at 09:20 | pattern convention only |
| DIAG-A-OLDSIDE | break = candle crosses the level (open on old side) | break reading only; DIAGNOSTIC, not a candidate |

## Results (5paisa = primary; `_TV` = secondary-vendor sensitivity)

| window | config_id | signals | buy | sell | executed_trades | win_rate_pct | profit_factor | avg_points_per_trade | total_points | total_rs | max_drawdown_rs | longest_losing_streak | target_hits | stop_hits | forced_exits |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A | ORB-V2-A | 39 | 20 | 19 | 39 | 35.9 | 1.115 | 2.219 | 86.55 | 6491.2 | 15750.0 | 6 | 14 | 25 | 0 |
| A | ORB-V2-B | 39 | 20 | 19 | 39 | 35.9 | 1.115 | 2.219 | 86.55 | 6491.2 | 15750.0 | 6 | 14 | 25 | 0 |
| A | ORB-V2-C | 37 | 19 | 18 | 37 | 37.84 | 1.211 | 3.961 | 146.55 | 10991.2 | 15750.0 | 6 | 14 | 23 | 0 |
| A | ORB-V2-D | 34 | 17 | 17 | 34 | 32.35 | 0.952 | -0.984 | -33.45 | -2508.8 | 22500.0 | 9 | 11 | 23 | 0 |
| A | DIAG-A-OLDSIDE | 27 | 13 | 14 | 27 | 37.04 | 1.176 | 3.333 | 90.0 | 6750.0 | 11250.0 | 5 | 10 | 17 | 0 |
| B | ORB-V2-A | 93 | 40 | 53 | 93 | 45.16 | 1.61 | 9.903 | 921.0 | 69075.0 | 13500.0 | 6 | 40 | 50 | 3 |
| B | ORB-V2-B | 94 | 41 | 53 | 94 | 45.74 | 1.65 | 10.436 | 981.0 | 73575.0 | 13500.0 | 6 | 41 | 50 | 3 |
| B | ORB-V2-C | 85 | 39 | 46 | 85 | 44.71 | 1.551 | 9.157 | 778.35 | 58376.3 | 13500.0 | 5 | 36 | 47 | 2 |
| B | ORB-V2-D | 85 | 36 | 49 | 85 | 45.88 | 1.656 | 10.482 | 891.0 | 66825.0 | 13500.0 | 6 | 37 | 45 | 3 |
| B | DIAG-A-OLDSIDE | 59 | 20 | 39 | 59 | 50.85 | 2.018 | 14.622 | 862.7 | 64702.5 | 13500.0 | 5 | 28 | 28 | 3 |
| A_TV | ORB-V2-A | 31 | 16 | 15 | 31 | 38.71 | 1.256 | 4.727 | 146.55 | 10991.2 | 7008.8 | 3 | 12 | 19 | 0 |
| A_TV | ORB-V2-B | 32 | 16 | 16 | 32 | 37.5 | 1.193 | 3.642 | 116.55 | 8741.2 | 9258.8 | 4 | 12 | 20 | 0 |
| A_TV | ORB-V2-C | 29 | 15 | 14 | 29 | 41.38 | 1.402 | 7.122 | 206.55 | 15491.2 | 6750.0 | 3 | 12 | 17 | 0 |
| A_TV | ORB-V2-D | 24 | 12 | 12 | 24 | 41.67 | 1.417 | 7.356 | 176.55 | 13241.2 | 4758.8 | 2 | 10 | 14 | 0 |
| B_TV | ORB-V2-A | 72 | 32 | 40 | 72 | 47.22 | 1.731 | 11.357 | 817.7 | 61327.5 | 11250.0 | 4 | 31 | 37 | 4 |
| B_TV | ORB-V2-B | 73 | 33 | 40 | 73 | 47.95 | 1.784 | 12.023 | 877.7 | 65827.5 | 11250.0 | 4 | 32 | 37 | 4 |
| B_TV | ORB-V2-C | 63 | 30 | 33 | 63 | 46.03 | 1.605 | 9.794 | 617.0 | 46275.0 | 13500.0 | 4 | 26 | 34 | 3 |
| B_TV | ORB-V2-D | 57 | 26 | 31 | 57 | 47.37 | 1.725 | 11.188 | 637.7 | 47827.5 | 7447.5 | 4 | 24 | 29 | 4 |


## Where the configurations disagree

| window | versus_A | signals_only_in_A | signals_only_in_other | dates_only_in_A | dates_only_in_other |
|---|---|---|---|---|---|
| A | ORB-V2-B | 0 | 0 |  |  |
| A | ORB-V2-C | 2 | 0 | 2026-04-17, 2026-08-13 |  |
| A | ORB-V2-D | 5 | 0 | 2025-11-11, 2026-01-27, 2026-04-17, 2026-06-10, 2026-07-21 |  |
| A | DIAG-A-OLDSIDE | 12 | 0 | 2025-09-05, 2025-10-01, 2025-11-17, 2025-11-28, 2025-12-29, 2026-01-28, 2026-02-12, 2026-03-12, 2026-03-25, 2026-04-16, 2026-04-30, 2026-07-02 |  |
| B | ORB-V2-B | 0 | 1 |  | 2022-09-01 |
| B | ORB-V2-C | 8 | 0 | 2023-08-29, 2023-10-16, 2024-03-14, 2024-06-05, 2024-08-08, 2024-11-18, 2025-03-10, 2025-07-21 |  |
| B | ORB-V2-D | 8 | 0 | 2022-10-28, 2023-01-02, 2023-01-06, 2024-09-26, 2025-02-07, 2025-03-07, 2025-03-10, 2025-05-15 |  |
| B | DIAG-A-OLDSIDE | 34 | 0 | 2022-09-20, 2022-09-28, 2022-10-31, 2022-12-01, 2023-01-02, 2023-01-06, 2023-01-09, 2023-02-07, 2023-03-06, 2023-05-23, 2023-07-03, 2023-07-27 ... |  |


Differences in P&L between rows are small-sample effects of a few dates (see the lists above) and must not be read as evidence for one interpretation.