# Manual ORB journal reconciliation (ORB V2, standalone)

**Evidence limit.** The journal records only date, entry-time label, strategy and outcome. It has no direction, entry price, level or exit time, so an **exact trade match is impossible**; `STRICT_TIMING` means date + strategy + time label agree, nothing more. A journal label is not proof that an engine candidate is correct, and no date was forced to produce a trade. **Every one of the 89 ORB journal rows carries the time label 09:15**, so 'STRICT_TIMING' is in practice a date + strategy match; the TIME_TOLERANT and DATE_STRATEGY_ONLY classes are therefore empty (their CSV files hold headers only).

## Independently verified reference counts

| quantity | value |
|---|---|
| journal_data_rows | 190 |
| orb_rows | 89 |
| orb_unique_dates | 89 |
| orb_dates_evaluable_sessions | 85 |
| orb_dates_not_evaluable | ['2025-10-11', '2026-08-15', '2026-08-22', '2026-08-29'] |
| saturday_orb_rows | ['2025-10-11', '2026-08-15', '2026-08-22', '2026-08-29'] |
| frozen_A_orb_signal_dates_on_journal_orb_dates | 35 |
| frozen_A_orb_executed_dates_on_journal_orb_dates | 35 |
| previously_missing_dates_A | 50 |
| irf_executed_on_journal_orb_dates_A | 34 |
| irf_executed_on_journal_orb_dates_B | 30 |
| irf_executed_on_journal_orb_dates_C | 29 |
| frozen_A_orb_signal_dates_total | 41 |
| frozen_A_total_orb_trades | 41 |


## Match classes (primary 5paisa window 2025-09-01..2026-08-31)

| config | STRICT_TIMING | TIME_TOLERANT | DATE_STRATEGY_ONLY | MANUAL_ONLY | AUTOMATED_ONLY(V2 trade, no manual ORB row) |
|---|---|---|---|---|---|
| ORB-V2-A | 38 | 0 | 0 | 51 | 1 |
| ORB-V2-B | 38 | 0 | 0 | 51 | 1 |
| ORB-V2-C | 36 | 0 | 0 | 53 | 1 |
| ORB-V2-D | 33 | 0 | 0 | 56 | 1 |


## Secondary-vendor sensitivity (the feed the rulebook screenshots were drawn from; NOT mixed with the primary result)

| config | STRICT_TIMING | TIME_TOLERANT | DATE_STRATEGY_ONLY | MANUAL_ONLY |
|---|---|---|---|---|
| ORB-V2-A | 30 | 0 | 0 | 59 |
| ORB-V2-B | 31 | 0 | 0 | 58 |
| ORB-V2-C | 28 | 0 | 0 | 61 |
| ORB-V2-D | 23 | 0 | 0 | 66 |


## Previously missing dates and handwritten disputes

| question | answer |
|---|---|
| of the 50 previously missing dates, V2-A generates a signal on | 16 |
| ... any of A-D generates a signal on | 16 |
| of the 13 handwritten disputes, V2-A generates a signal on | 4 |
| ... any of A-D | 4 |


Attribution among the previously-missing dates where V2-A signals (categories overlap; one signal can have several): {"any": 16, "gap_beyond_prev_range": 1, "inner_only_level": 13, "ema_crossing_B_or_C": 5, "engulfing_only_route": 2}. Dates that only config B (300-point gap limit) adds: none.

## ORB V2 versus the frozen IRF entry

V2-A signals on **12** dates on which the frozen IRF also executed (config A). On manual ORB dates V2-A would enter before the frozen IRF fill on **12** dates. V2 always fills at 09:20 and no IRF fill precedes 09:25, so wherever both exist V2 is earlier by construction; this is a chronology statement only, the portfolio controller is not changed.

## Outcome labels on the strict matches (descriptive; journal vocabulary vs the standalone 30/60 result)

{"AGREES": 29, "NO_COUNTERPART_IN_30_60": 9}. Journal 'Target' / 'SL' labels agree with the V2 exit on every strict match where a comparison exists; 'BE' (break-even) has no counterpart in a fixed 30/60 exit. This was not checked against any price other than V2's own simulation; it is either support for the rules or a sign that the journal derives from similar bar data - not determined here.

## Rule conformity: manual ORB dates versus all other sessions (descriptive only)

How often each rulebook condition holds on the 85 evaluable manual ORB dates versus the other sessions (condition evaluated for the EMA-implied direction; the author's direction is not recorded). The journal was not used to define or tune any rule; this is a consistency check, not evidence that any construction is the author's.

| feed | group | sessions | gap_ok_pct | level_ok_pct | colour_ok_pct | pattern_ok_pct | wick_ok_pct | V2-A_signal_pct |
|---|---|---|---|---|---|---|---|---|
| 5paisa | manual ORB dates | 85 | 94.1 | 96.5 | 100.0 | 49.4 | 72.9 | 44.7 |
| 5paisa | all other sessions | 162 | 92.6 | 85.8 | 37.0 | 4.9 | 43.2 | 0.6 |
| secondary | manual ORB dates | 85 | 94.1 | 96.5 | 100.0 | 41.2 | 70.6 | 35.3 |
| secondary | all other sessions | 162 | 92.0 | 85.8 | 35.2 | 3.7 | 43.2 | 0.6 |


## Root causes of manual-only dates (config A)

| root_cause | dates |
|---|---|
| MULTIPLE | 23 |
| SOLE:NO_PATTERN | 20 |
| SESSION_NOT_EVALUABLE_OR_NO_SESSION | 4 |
| SOLE:WRONG_SIDE_WICK | 2 |
| SOLE:LEVEL_NOT_BROKEN | 1 |
| SOLE:GAP_TOO_LARGE | 1 |


Files: `orb_89_journal_rows.csv`, `orb_50_previously_missing_dates.csv`, `orb_13_handwritten_disputes.csv`, `orb_vs_irf_timeline.csv`, `exact_or_strict_matches.csv`, `time_tolerant_matches.csv`, `date_only_matches.csv`, `manual_only.csv`, `automated_only.csv`, `mismatch_root_causes.csv`.