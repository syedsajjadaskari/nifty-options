# Exact and staged match summary (configurations A, B, C)

A = Phase 3.6 frozen; B = Phase 5.3 author-corrected (legacy ORB); C = IRF V2 + ORB V2 (provisional ORB-V2-A) + PDR/PDS first-eligible + RF. Primary window 2025-09-01..2026-08-31. One-to-one staged matching (Phase 5.6 matcher and tolerances, unchanged): STRICT = same date + strategy + time label equals the signal-candle start; TIME_TOLERANT = within 15 minutes; DATE_STRATEGY_ONLY = same date and strategy but outside the tolerance (NOT a match).

**No verified exact trade match exists or can exist**: the journal records no direction, entry price or exit detail (see `manual_journal_source_audit.md`). 'Strict' means date + strategy + label only. Date-only agreements are never added to strict matches.

| Measure | A | B | C |
|---|---|---|---|
| Total automated trades | 196 | 188 | 183 |
| IRF trades | 109 | 90 | 85 |
| ORB trades | 41 | 41 | 39 |
| PDR trades | 25 | 28 | 31 |
| PDS trades | 11 | 19 | 19 |
| RF trades | 10 | 10 | 9 |
| Verified exact trade matches | 0 / 190 journal rows | 0 / 190 journal rows | 0 / 190 journal rows |
| Strict recorded-field matches | 66 / 190 journal rows | 64 / 190 journal rows | 67 / 190 journal rows |
| Additional time-tolerant matches (<= 15 min) | 21 / 190 | 14 / 190 | 15 / 190 |
| Date-and-strategy-only agreements | 18 / 190 | 17 / 190 | 17 / 190 |
| Manual-only rows | 85 / 190 | 95 / 190 | 91 / 190 |
|   of which weekend-dated rows | 5 | 5 | 5 |
| Automated-only trades | 91 / 196 trades | 93 / 188 trades | 84 / 183 trades |
| Wrong-strategy dates | 61 | 61 | 53 |
| Outcome-label agreements (strict + time-tolerant pairs) | 80 / 87 | 71 / 78 | 74 / 82 |


## Strict matches by strategy (numerator / manual rows of that strategy)

| strategy | A | B | C |
|---|---|---|---|
| IRF | 26 / 73 | 20 / 73 | 20 / 73 |
| ORB | 35 / 89 | 35 / 89 | 38 / 89 |
| PDR | 0 / 8 | 4 / 8 | 4 / 8 |
| PDS | 1 / 3 | 1 / 3 | 1 / 3 |
| RF | 4 / 17 | 4 / 17 | 4 / 17 |


## Automated trades by strategy and strict share

| strategy | A | B | C |
|---|---|---|---|
| IRF | 26 strict of 109 automated | 20 strict of 90 automated | 20 strict of 85 automated |
| ORB | 35 strict of 41 automated | 35 strict of 41 automated | 38 strict of 39 automated |
| PDR | 0 strict of 25 automated | 4 strict of 28 automated | 4 strict of 31 automated |
| PDS | 1 strict of 11 automated | 1 strict of 19 automated | 1 strict of 19 automated |
| RF | 4 strict of 10 automated | 4 strict of 10 automated | 4 strict of 9 automated |


**Evidence caveat:** every ORB journal row carries the label 09:15, so an ORB strict match is only a date + strategy match; the non-ORB strict matches are the only ones that test the time label (it equals the signal-candle start in the data). ORB V2 was reconstructed with this journal's ORB dates in view (Phases 5.8-6.0), so its ORB agreement is in-sample. Tolerances were not changed to improve any percentage. Files: `strict_matches.csv`, `time_tolerant_matches.csv`, `date_only_matches.csv`, `manual_only.csv`, `automated_only.csv`, `wrong_strategy_dates.csv`, `manual_vs_automated_matching.csv`.