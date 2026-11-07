# Phase 5 - data quality report

HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

Per index and window: coverage against the calendar derived from that index's own data, session-quality gate (the frozen Phase 2.1 session logic), the checks required by the brief, and a confidence tier (the Phase 4 rubric: HIGH needs the same provider as the baseline, >= 99% usable sessions and a second vendor within 0.10 point on average; MODERATE the same with a larger vendor difference; LOW a partial year; EXPLORATORY_UNVERIFIABLE a source with nothing to check it against). Tiers are conventions with round-number boundaries, not statistical claims.

## BANKNIFTY

### Coverage by window

| window | dates | minute source | expected sessions | in source | usable | excluded | sessions with missing minutes | sessions with an extreme (> 0.5%) 1-minute move | abnormal 09:15 bars | OHLC violations | warm-up sessions in source | confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M | 2022-09-01..2026-08-31 | FIVEPAISA_1M_BANKNIFTY | 992 | 991 | 985 | 6 | 8 | 16 | 8 | 0 | 20 | MODERATE |
| MS | 2022-09-01..2024-03-22 | KAPRI_1M_BANKNIFTY | 389 | 389 | 386 | 3 | 8 | 5 | 2 | 0 | 30 | EXPLORATORY_UNVERIFIABLE |
| C | 2018-01-01..2018-12-31 | KAPRI_1M_BANKNIFTY | 246 | 246 | 245 | 1 | 1 | 4 | 0 | 0 | 30 | EXPLORATORY_UNVERIFIABLE |
| D_5P | 2019-03-01..2019-12-31 | FIVEPAISA_1M_BANKNIFTY | 201 | 196 | 196 | 0 | 6 | 9 | 2 | 0 | 0 | LOW |
| D_TV | 2019-01-01..2019-12-31 | KAPRI_1M_BANKNIFTY | 244 | 244 | 244 | 1 | 5 | 9 | 2 | 0 | 29 | EXPLORATORY_UNVERIFIABLE |

Expected sessions = weekdays that are not derived holidays plus weekend sessions in the daily series. Dates missing from a source:

* M: 2022-10-24
* D_5P: 2019-06-27, 2019-06-28, 2019-07-01, 2019-07-02, 2019-07-03
* 2022-10-24 is the Diwali Muhurat evening session: absent from the 5paisa minute data, present in the secondary source (where the gate excludes it as a non-standard session) and in the daily series.

### Excluded sessions (the frozen gate), per window

| window | date | weekday | rows | first..last bar | status | reason |
|---|---|---|---|---|---|---|
| M | 2023-10-19 | Thu | 367 | 09:15..15:30 | EXCLUDED_CORRUPT | FROZEN_FEED_OUTSIDE_AUCTION_WINDOW:6;MISSING_MINUTE_BARS_IN_1_CANDLES |
| M | 2023-11-12 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |
| M | 2024-03-02 | Sat | 191 | 09:15..12:30 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| M | 2024-05-18 | Sat | 173 | 09:15..13:37 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| M | 2024-11-01 | Fri | 61 | 18:00..19:00 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| M | 2025-10-21 | Tue | 61 | 13:45..14:45 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| MS | 2022-10-24 | Mon | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| MS | 2023-11-12 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |
| MS | 2024-03-02 | Sat | 105 | 09:15..12:29 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| C | 2018-11-07 | Wed | 60 | 17:30..18:29 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| D_TV | 2019-10-27 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |

Muhurat (evening) sessions, Saturday special sessions and truncated or placeholder sessions are not evaluated. `2023-10-19` is a 5paisa feed defect (BANKNIFTY: frozen prices; SENSEX: the 09:15-09:18 bars are missing) - the secondary source has that day, so a defect in one vendor is not turned into a holiday or a special session for the other.

### Calendar derived from this index's own data

Holidays per year (weekday with no daily candle and no minute rows in any source covering the date): {'2017': 12, '2018': 15, '2019': 17, '2020': 12, '2021': 13, '2022': 12, '2023': 15, '2024': 16, '2025': 13, '2026': 10}. Special sessions: 2022-10-24 (weekday, first bar is not 09:15: an even; evaluable=False), 2023-11-12 (weekend, non-standard hours; evaluable=False), 2024-01-20 (weekend, normal hours; evaluable=True), 2024-03-02 (weekend, non-standard hours; evaluable=False), 2024-05-18 (weekend, non-standard hours; evaluable=False), 2024-11-01 (weekday, first bar is not 09:15: an even; evaluable=False), 2025-02-01 (weekend, normal hours; evaluable=True), 2025-10-21 (weekday, first bar is not 09:15: an even; evaluable=False), 2026-02-01 (weekend, normal hours; evaluable=True). Vendor gaps between series (weekday traded per the daily series but absent from a covering minute source): 9. Opening-bar defects (one vendor missing 09:15-09:xx where another has it): none. The calendar is derived, not read from an exchange circular; it was cross-checked against the NIFTY calendars, which should agree because NSE and BSE close together.

### Closing-auction regime (decided per index from its own data)

The index freezes at one price over 15:16-15:26 on 21 of 21 sessions from 2026-08-03 and on 0 of 44 sessions between 2026-06-01 and 2026-08-02 (first session with the pattern: 2026-08-03). The regime is therefore applied to BANKNIFTY from 2026-08-03 **because its own data show it** (frozen-window bars are reference prints, not fillable; the official close is the daily vendor close), not by assuming NSE's rule for BSE or vice versa. The regulatory circular was not read directly (the NIFTY evidence calendar cites secondary sources).

### Other checks required by the brief

| check | main window M (5paisa) | how it is checked |
|---|---|---|
| timezone and alignment | IST; 1-minute bars labelled by START; 376 rows per session incl. the 15:30 stub | raw files; independent audit |
| duplicates | 652 duplicate rows removed (dates ['2022-10-10', '2023-09-27']); conflicting duplicates 0 | identical rows dropped, last kept |
| OHLC consistency | 0 violating rows | high >= max(open, close), low <= min, positive, no NaN |
| missing candles | 8 sessions with missing regular minutes (total 1497 minutes); nothing is filled | per-session table |
| frozen / flat prices | 24 sessions with a >= 5-minute frozen run (of which 21 are the expected closing-auction freeze from 2026-08-03) | frozen runs outside the auction window exclude the session |
| large discontinuities | 16 sessions with a 1-minute move > 0.5% (max 1.24%); 8 abnormal 09:15 bars; flagged, not removed | predeclared thresholds |
| session open | 09:15 bar present on 988 of 991 sessions | the first 1-minute open is the session open |
| minute high/low vs daily candle | mean abs difference: high 5.56, low 5.42 points | 5paisa daily vs the minute session extremes |
| previous-day close | official close = the 5paisa DAILY close (differs from the last 15:29 close by 36.55 points on average, as for NIFTY) | convention; independent audit recomputes previous-day high / low / close |
| open vs previous daily close | mean abs overnight gap 188.0 points | sanity |
| 5-minute aggregation | complete 5-minute candles only (5 one-minute rows), labelled by start; recomputed independently from the raw rows for every explanation candle | independent audit |
| EMA(200) warm-up | 20 sessions of same-source minute warm-up for the main window; 0 for D_5P (EMA undefined for the first ~3 sessions); >= 200 daily bars precede every window | warm-up rows never traded |

The OFFICIAL daily close is not the last 15:29 bar's close and (for the NSE indices) not the 15:30 stub either; the frozen logic uses the vendor daily close for the previous-day close.

## SENSEX

### Coverage by window

| window | dates | minute source | expected sessions | in source | usable | excluded | sessions with missing minutes | sessions with an extreme (> 0.5%) 1-minute move | abnormal 09:15 bars | OHLC violations | warm-up sessions in source | confidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| M | 2022-09-01..2026-08-31 | FIVEPAISA_1M_SENSEX | 988 | 985 | 983 | 6 | 8 | 8 | 6 | 0 | 20 | MODERATE |
| MS | 2022-09-01..2024-03-22 | KAPRI_1M_SENSEX | 387 | 387 | 386 | 3 | 9 | 1 | 0 | 0 | 31 | EXPLORATORY_UNVERIFIABLE |
| C | 2018-01-01..2018-12-31 | KAPRI_1M_SENSEX | 246 | 200 | 198 | 2 | 5 | 1 | 0 | 0 | 0 | EXPLORATORY_UNVERIFIABLE |
| D_5P | 2019-03-01..2019-12-31 | FIVEPAISA_1M_SENSEX | 202 | 201 | 201 | 0 | 2 | 2 | 1 | 0 | 0 | LOW |
| D_TV | 2019-01-01..2019-12-31 | KAPRI_1M_SENSEX | 245 | 245 | 235 | 10 | 15 | 2 | 2 | 0 | 29 | EXPLORATORY_UNVERIFIABLE |

Expected sessions = weekdays that are not derived holidays plus weekend sessions in the daily series. Dates missing from a source:

* M: 2022-10-24, 2023-02-27, 2024-07-19
* C: 2018-01-01, 2018-01-02, 2018-01-03, 2018-01-04, 2018-01-05, 2018-01-08, 2018-01-09, 2018-01-10, 2018-01-11, 2018-01-12, 2018-01-15, 2018-01-16, 2018-01-17, 2018-01-18, 2018-01-19, 2018-01-22, 2018-01-23, 2018-01-24, 2018-01-25, 2018-01-29, 2018-01-30, 2018-01-31, 2018-02-01, 2018-02-02, 2018-02-05, 2018-02-06, 2018-02-07, 2018-02-08, 2018-02-09, 2018-02-12, 2018-02-14, 2018-02-15, 2018-02-16, 2018-02-19, 2018-02-20, 2018-02-21, 2018-02-22, 2018-02-23, 2018-02-26, 2018-02-27, 2018-02-28, 2018-03-01, 2018-03-05, 2018-03-06, 2018-03-07, 2018-03-12
* D_5P: 2019-10-27
* 2022-10-24 is the Diwali Muhurat evening session: absent from the 5paisa minute data, present in the secondary source (where the gate excludes it as a non-standard session) and in the daily series.

### Excluded sessions (the frozen gate), per window

| window | date | weekday | rows | first..last bar | status | reason |
|---|---|---|---|---|---|---|
| M | 2023-10-19 | Thu | 363 | 09:19..15:30 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:not in calendar |
| M | 2023-11-12 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |
| M | 2024-03-02 | Sat | 162 | 09:15..12:30 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| M | 2024-05-18 | Sat | 165 | 09:15..13:29 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| M | 2024-11-01 | Fri | 61 | 18:00..19:00 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| M | 2025-10-21 | Tue | 61 | 13:45..14:45 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| MS | 2022-10-24 | Mon | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| MS | 2023-11-12 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |
| MS | 2024-03-02 | Sat | 105 | 09:15..12:29 | EXCLUDED_NON_STANDARD_START | SPECIAL_SESSION_NOT_EVALUABLE |
| C | 2018-03-13 | Tue | 164 | 12:46..15:29 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| C | 2018-11-07 | Wed | 60 | 17:30..18:29 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekday, first bar is not 09:15: an evening /  |
| D_TV | 2019-01-23 | Wed | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-24 | Thu | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-25 | Fri | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-28 | Mon | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-29 | Tue | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-30 | Wed | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-01-31 | Thu | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-02-01 | Fri | 1 | 09:15..09:15 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_1_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-02-04 | Mon | 2 | 09:15..15:29 | EXCLUDED_NO_OPENING_CANDLE | MISSING_MINUTE_BARS_IN_2_CANDLES;NO_COMPLETE_OPENING_CANDLE |
| D_TV | 2019-10-27 | Sun | 60 | 18:15..19:14 | EXCLUDED_NON_STANDARD_START | NON_STANDARD_START:derived special session (weekend, non-standard hours) |

Muhurat (evening) sessions, Saturday special sessions and truncated or placeholder sessions are not evaluated. `2023-10-19` is a 5paisa feed defect (BANKNIFTY: frozen prices; SENSEX: the 09:15-09:18 bars are missing) - the secondary source has that day, so a defect in one vendor is not turned into a holiday or a special session for the other.

### Calendar derived from this index's own data

Holidays per year (weekday with no daily candle and no minute rows in any source covering the date): {'2017': 12, '2018': 15, '2019': 17, '2020': 12, '2021': 13, '2022': 11, '2023': 15, '2024': 16, '2025': 13, '2026': 10}. Special sessions: 2022-08-09 (weekday, first bar is not 09:15: an even; evaluable=False), 2022-10-24 (weekday, first bar is not 09:15: an even; evaluable=False), 2023-11-12 (weekend, non-standard hours; evaluable=False), 2024-01-20 (weekend, normal hours; evaluable=True), 2024-03-02 (weekend, non-standard hours; evaluable=False), 2024-05-18 (weekend, non-standard hours; evaluable=False), 2024-11-01 (weekday, first bar is not 09:15: an even; evaluable=False), 2025-02-01 (weekend, normal hours; evaluable=True), 2025-10-21 (weekday, first bar is not 09:15: an even; evaluable=False), 2026-02-01 (weekend, normal hours; evaluable=True). Vendor gaps between series (weekday traded per the daily series but absent from a covering minute source): 7. Opening-bar defects (one vendor missing 09:15-09:xx where another has it): [{'date': '2023-10-19', 'first_bar_minute_of_day_by_source': {'FIVEPAISA_1M_SENSEX': 559, 'KAPRI_1M_SENSEX': 555}}]. The calendar is derived, not read from an exchange circular; it was cross-checked against the NIFTY calendars, which should agree because NSE and BSE close together.

### Closing-auction regime (decided per index from its own data)

The index freezes at one price over 15:16-15:26 on 21 of 21 sessions from 2026-08-03 and on 0 of 44 sessions between 2026-06-01 and 2026-08-02 (first session with the pattern: 2026-08-03). The regime is therefore applied to SENSEX from 2026-08-03 **because its own data show it** (frozen-window bars are reference prints, not fillable; the official close is the daily vendor close), not by assuming NSE's rule for BSE or vice versa. The regulatory circular was not read directly (the NIFTY evidence calendar cites secondary sources).

### Other checks required by the brief

| check | main window M (5paisa) | how it is checked |
|---|---|---|
| timezone and alignment | IST; 1-minute bars labelled by START; 376 rows per session incl. the 15:30 stub | raw files; independent audit |
| duplicates | 176 duplicate rows removed (dates ['2022-10-10']); conflicting duplicates 0 | identical rows dropped, last kept |
| OHLC consistency | 0 violating rows | high >= max(open, close), low <= min, positive, no NaN |
| missing candles | 8 sessions with missing regular minutes (total 1505 minutes); nothing is filled | per-session table |
| frozen / flat prices | 24 sessions with a >= 5-minute frozen run (of which 21 are the expected closing-auction freeze from 2026-08-03) | frozen runs outside the auction window exclude the session |
| large discontinuities | 8 sessions with a 1-minute move > 0.5% (max 1.10%); 6 abnormal 09:15 bars; flagged, not removed | predeclared thresholds |
| session open | 09:15 bar present on 985 of 989 sessions | the first 1-minute open is the session open |
| minute high/low vs daily candle | mean abs difference: high 5.33, low 5.37 points | 5paisa daily vs the minute session extremes |
| previous-day close | official close = the 5paisa DAILY close (differs from the last 15:29 close by 41.50 points on average, as for NIFTY) | convention; independent audit recomputes previous-day high / low / close |
| open vs previous daily close | mean abs overnight gap 248.5 points | sanity |
| 5-minute aggregation | complete 5-minute candles only (5 one-minute rows), labelled by start; recomputed independently from the raw rows for every explanation candle | independent audit |
| EMA(200) warm-up | 20 sessions of same-source minute warm-up for the main window; 0 for D_5P (EMA undefined for the first ~3 sessions); >= 200 daily bars precede every window | warm-up rows never traded |

The OFFICIAL daily close is not the last 15:29 bar's close and (for the NSE indices) not the 15:30 stub either; the frozen logic uses the vendor daily close for the previous-day close.

