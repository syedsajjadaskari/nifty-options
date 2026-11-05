# Data quality by year (Phase 4)

**Written for:** the strategy owner. Every window was validated BEFORE its backtest was run, with thresholds declared in advance (`phase4_data.py`: a 1-minute close-to-close move above 0.5% is reported as an extreme candle, a 09:15 bar wider than 1% of its open is reported, frozen runs are 5 or more identical flat bars - the pipeline's own rule). Reported items are disclosed, not silently dropped; only the pipeline's existing quality gate excludes sessions (identically for every year).

## Checks required by the brief

| check | B 5paisa | B secondary | C 2018 secondary | D 5paisa 2019-03..12 | D 2019 secondary |
|---|---|---|---|---|---|
| sessions in source / usable | 743 / 738 | 743 / 739 | 245 / 244 | 196 / 196 | 244 / 244 |
| chronological order (provider order, before sorting) | yes | yes | yes | yes | yes |
| unique timestamps (duplicates removed) | 660 (2 days, identical) | 0 | 0 | 0 | 0 |
| Asia/Kolkata conversion | IST wall-clock, bar START | IST wall-clock, bar START | IST wall-clock, bar START | IST wall-clock, bar START | IST wall-clock, bar START |
| OHLC rows violating high >= max(open, close) or low <= min(open, close), or non-positive | 0 | 0 | 0 | 0 | 0 |
| sessions with missing regular minutes / total missing minutes | 7 / 1184 | 13 / 1296 | 1 / 1 | 6 / 56 | 0 / 0 |
| sessions with frozen-price runs (>= 5 flat bars) | 3 | 0 | 0 | 0 | 0 |
| sessions with an extreme 1-minute candle (> 0.5%) | 5 | 5 | 1 | 2 | 3 |
| abnormal 09:15 bars (range > 1% of open) | 3 | 3 | 0 | 0 | 1 |
| sessions whose first bar is not 09:15 | 2 | 2 | 1 | 0 | 0 |
| 15:30 closing-print stub present | 99% | 0% | 0% | 100% | 0% |
| sessions with minute data but no 5paisa daily candle | 2 | 2 | 0 | 0 | 0 |
| mean absolute difference between the official daily close and the last 15:29 close (points) | 12.62 | 12.58 | 6.66 | 6.93 | 6.97 |
| minute warm-up sessions available before the window (same source) | 20 | 30 | 30 | 0 | 29 |
| daily bars before the window (need >= 200) | 1401 | 1401 | 248 | 537 | 494 |

Five-minute aggregation, the previous-session high / low and the open convention are the existing, tested Phase 2 / 3 code (a 5-minute candle is five complete 1-minute rows, usable at its end; the open is the first 1-minute open; the official close is the daily close) and are unchanged; the Phase 4 audit re-derives candles and indicators independently from the raw files.

## Trading calendar (derived, validated, date-aware)

The repository's evidence-tier calendar covers only 2025-26, so the Phase 2 pipeline would mark every post-holiday session of an older year as having an unverifiable previous day. A calendar is therefore DERIVED from the data: a weekday is a holiday when there is no 5paisa daily candle AND no minute rows in any source that covers the date (a weekday present in only some series is a vendor data gap, not a holiday); weekend or non-09:15 sessions are special sessions, evaluable only when they carry a full normal-hours session. **Method check:** applied to 2025-09..2026-08 the same method reproduces the evidence-tier calendar exactly (identical = True; 14 derived vs 14 evidence holidays). The derived holidays were **not** compared with NSE circulars; external confirmation was not performed. Closing-auction handling is date-aware: the 2026-08-03 regime applies only from that date, so no auction restriction is applied to any Phase 4 window, and the continuous-trading convention (fills only on bars before 15:30, forced exit at the open of the 15:14 minute) is the unchanged Phase 3 policy.

| year | derived weekday holidays | special / non-standard-start sessions |
|---|---|---|
| 2017 | 12 | - |
| 2018 | 15 | 2018-07-09 (not evaluable) |
| 2019 | 17 | - |
| 2020 | 12 | 2020-02-01 (not evaluable), 2020-11-14 (not evaluable) |
| 2021 | 13 | - |
| 2022 | 12 | - |
| 2023 | 15 | 2023-11-12 (not evaluable) |
| 2024 | 16 | 2024-01-20 (evaluable), 2024-03-02 (not evaluable), 2024-05-18 (not evaluable), 2024-11-01 (not evaluable) |
| 2025 | 9 | 2025-02-01 (evaluable) |

Vendor gaps between series (not holidays; each minute source is only expected inside the years actually retrieved - 2020 and 2021 minute data were not retrieved): 11 weekday(s), listed in `derived_calendar_summary.json`. Note that **2018-07-09 is not a special session**: it is a normal Monday whose 09:15 bar is missing from the secondary file (374 rows from 09:16), so it is excluded by the quality gate and one trading day is lost. The check of the method against the 2025-26 evidence calendar is partly circular (that calendar was itself built from absences in vendor series); the derived dates were reproduced independently and match public knowledge of NSE holidays, but were **not** compared with NSE circulars.

## Excluded and unverifiable sessions (identical rules for every year)

* **B 5paisa:** 2023-10-19 EXCLUDED_CORRUPT (FROZEN_FEED_OUTSIDE_AUCTION_WINDOW:6;MISSING_MINUTE_BARS_IN_1_CANDLES); 2023-11-12 EXCLUDED_NON_STANDARD_START (NON_STANDARD_START:derived special session (weekend, non-standard hours)); 2024-03-02 EXCLUDED_NON_STANDARD_START (SPECIAL_SESSION_NOT_EVALUABLE); 2024-05-18 EXCLUDED_NON_STANDARD_START (SPECIAL_SESSION_NOT_EVALUABLE); 2024-11-01 EXCLUDED_NON_STANDARD_START (NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening / Muhurat session or a missing opening bar)). Expected sessions absent from the source: 2022-10-24.
* **B secondary:** 2023-11-12 EXCLUDED_NON_STANDARD_START (NON_STANDARD_START:derived special session (weekend, non-standard hours)); 2024-03-02 EXCLUDED_NON_STANDARD_START (SPECIAL_SESSION_NOT_EVALUABLE); 2024-05-18 EXCLUDED_NON_STANDARD_START (SPECIAL_SESSION_NOT_EVALUABLE); 2024-11-01 EXCLUDED_NON_STANDARD_START (NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening / Muhurat session or a missing opening bar)). Expected sessions absent from the source: 2022-10-24.
* **C 2018 secondary:** 2018-07-09 EXCLUDED_NON_STANDARD_START (NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening / Muhurat session or a missing opening bar)). Expected sessions absent from the source: 2018-11-07.
* **D 5paisa 2019-03..12:** none. Expected sessions absent from the source: 2019-06-27;2019-06-28;2019-07-01;2019-07-02;2019-07-03.
* **D 2019 secondary:** none. Expected sessions absent from the source: none.

A session whose PREVIOUS session is excluded, missing, or whose previous close cannot be verified makes the previous-day-dependent strategies (ORB, PDR, PDS, and RF's gap logic) NOT_EVALUATED that day; this is the Phase 2 rule applied unchanged. Counts (strategy-sessions) in `not_evaluated_strategy_sessions.csv`:

| window | reason | strategy-sessions |
|---|---|---|
| B | PREV_SESSION_UNVERIFIED | 32 |
| B_TV | PREV_SESSION_UNVERIFIED | 28 |
| C | PREV_SESSION_UNVERIFIED | 8 |
| D_5P | EMA200_5M_WARMUP | 2 |
| D_5P | MA_WARMUP | 1 |
| D_5P | NO_PREVIOUS_SESSION_IN_DATASET | 4 |
| D_5P | PREV_SESSION_UNVERIFIED | 4 |

## Data-quality confidence (rubric fixed in advance)

| tier | meaning |
|---|---|
| HIGH | same provider as the Phase 3.6 baseline, full coverage, >= 99% of sessions usable, official daily closes, and a second vendor overlaps with mean |1-minute close difference| <= 0.10 point |
| MODERATE | same provider as the baseline, >= 98% of sessions usable, official daily closes, a second vendor overlaps but mean |difference| > 0.10 point (the vendors' minute bars differ) |
| LOW | single provider with a partial year and / or provider gaps, and a second vendor that differs materially |
| EXPLORATORY_UNVERIFIABLE | the minute source cannot be checked against an independent vendor for (part of) the period; treat as exploratory only |

| window / period | tier | why |
|---|---|---|
| A_2025_26 | HIGH | 5paisa Phase 1 dataset | REFERENCE |
| B_2022_25 | MODERATE | 5paisa minutes + 5paisa daily | DATA_VALIDATED |
| D_2019_5PAISA_PARTIAL | LOW | 5paisa minutes + 5paisa daily | PARTIAL_YEAR |
| D_2019_SECONDARY | EXPLORATORY_UNVERIFIABLE | secondary vendor minutes + 5paisa daily | EXPLORATORY |
| C_2018 | EXPLORATORY_UNVERIFIABLE | secondary vendor minutes + 5paisa daily | EXPLORATORY |

## Known issues that can affect results

* The confidence tiers are conventions with round-number boundaries (for example 0.10 point of mean difference); the Phase 3.6 reference year's mean difference is 0.089, just inside the HIGH boundary.
* Windows B and B_TV are not on identical session sets: 2023-10-19 is excluded in B only (frozen 5paisa feed).
* The reported count of sessions with missing minutes is dominated by the excluded special sessions: see `coverage_exceptions.csv` for the usable sessions only.
* The two vendors' minute bars differ (see `data_source_discovery.md`); the 09:15 bar, which IRF and ORB use, differs most. Window B was therefore also run on the secondary vendor's bars: `vendor_sensitivity.csv`.
* 2023-10-19 is excluded in the 5paisa run (frozen feed) but present in the secondary run.
* 5paisa lacks five 2019 sessions (2019-06-27 .. 07-03) that the secondary vendor has; the 5paisa 2019 run is a PARTIAL YEAR and has no minute warm-up before 2019-03-01 (the first sessions have no EMA).
* 5paisa has no daily candle on 2022-11-17 and 2024-01-12 although minute data exist; the following sessions' previous close is then unverifiable and the affected strategies are NOT_EVALUATED.
* 2099 session rows carry at least one flag or exception (mostly the official-close-differs-from-last-print note and dropped incomplete 5-minute candles): `coverage_exceptions.csv`.
