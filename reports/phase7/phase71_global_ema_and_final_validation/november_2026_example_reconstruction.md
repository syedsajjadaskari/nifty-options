# November 2026 data and example reconstruction (Priority 3)

## Data
Retrieved read-only through the project's authenticated 5paisa client into a NEW raw namespace (`data/raw/phase71_5paisa_nov2026/`, manifest with request parameters, UTC time, row counts, SHA-256), processed to `data/phase71/processed/FIVEPAISA_1M_NOV2026/`. The frozen stores were not touched. Provider timestamps are naive IST bar-start labels. Coverage 2026-11-02..2026-11-18 (13 session dates):

| date | weekday | rows_total | rows_in_session_0915_1529 | rows_outside_session | missing_minutes | duplicate_stamps | ohlc_violations | complete_session | note |
|---|---|---|---|---|---|---|---|---|---|
| 2026-11-02 | Mon | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-03 | Tue | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-04 | Wed | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-05 | Thu | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-06 | Fri | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-08 | Sun | 71 | 70 | 1 | 305 | 0 | 0 | False | weekend / special session (Muhurat-type partial) |
| 2026-11-09 | Mon | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-11 | Wed | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-12 | Thu | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-13 | Fri | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-16 | Mon | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-17 | Tue | 376 | 375 | 1 | 0 | 0 | 0 | True |  |
| 2026-11-18 | Wed | 405 | 375 | 30 | 0 | 0 | 0 | True |  |

Quality notes: every full session has 375 in-session rows and no missing minutes; the provider also returns a 15:30 stub row (dropped from candles, as in earlier phases) and, on 2026-11-18, rows after 15:30. 2026-11-08 is a Sunday partial (Muhurat-type) session; 2026-11-10 and 11-14/15 have no rows. No candle was manufactured. These sessions are NOT in the frozen backtest windows (both end before November).

## Reconstruction (engine = Phase 7.0 IRF V3 modules, unchanged; each chart embeds the original screenshot at its extracted resolution above the replay: `charts/EX_*`)

| example | date | feed | A_diff | B_diff | failure_candle | failure_close | failure_close_minus_stated_entry | SL40_exit | sequence_reproduced(entry within 2pt) | outcome_agrees(SL40) |
|---|---|---|---|---|---|---|---|---|---|---|
| M1-E2 | 2026-11-11 | 5P_NOV2026 | -0.25 |  | 09:50-09:55 | 25364.35 | 0.45 | TARGET 60.0 @ 12:27 | True | True |
| M1-E3 | 2026-11-16 | 5P_NOV2026 | 9.0 |  | 10:00-10:05 | 25299.55 | -0.2 | TARGET 60.0 @ 10:32 | True | True |
| M2-E2 | 2026-11-12 | 5P_NOV2026 | -0.75 | 0.05 | 10:10-10:15 | 25336.7 | -1.25 | TARGET 60.0 @ 11:31 | True | True |
| M2-E3 | 2026-11-06 | 5P_NOV2026 | -21.85 | 2.4 | 10:35-10:40 | 24648.7 | 1.45 | TARGET 60.0 @ 10:54 | True | True |
| M2-E4 | 2026-11-03 | 5P_NOV2026 | -3.85 | -0.2 | 10:05-10:10 | 23613.0 | 0.2 | STOP -40.75 @ 10:31 | True | True |
| M2-E4 | 2026-11-03 | TV_SECONDARY | -0.45 | -0.2 | 10:00-10:05 | 23621.0 | 8.2 | STOP -40.0 @ 10:33 | False | True |

* **Sequence reproduced (failure close within 2 points of the stated entry): all five dated examples on the 5paisa feed**; outcomes agree (targets for M1-E2, M1-E3, M2-E2, M2-E3; stop-loss for M2-E4).
* **Printed Level-A values that disagree with the data:** M2 Example 4 (3 Nov) prints 23,611.15 vs 23,607.30 on the 5paisa feed (-3.85; the secondary feed gives 23,610.70, -0.45, so a feed difference); M2 Example 3 (6 Nov) prints Level A 24,540.05 but the first-candle high is 24,518.20 (-21.85); M1 Example 3 (16 Nov) prints 25,301.55 vs 25,310.55 (+9.00, looks like a digit transposition). The printed entry/outcome still reproduce, so these look like hand-placed lines. Question 10.
* M2 Example 4 (3 Nov) reproduces on the 5paisa feed and one candle earlier on the secondary feed (see `irf_method2_timing_audit.md`).
* **Undated screenshots (M1 Example 1, M2 Example 1) remain undated** - no date was assigned (level-only search already found no supporting session).
* Approximate screenshot prices were used only as comparison evidence; every price above is from the stored candles.
