# Manual journal - source audit

> SYNTHETIC index-point P&L; no real option P&L. The journal has no direction, price or exit time: matching uses only date, strategy and the entry-time label, and every automated-trade explanation rests on the actual candles and the documented rules.

## The source

`docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx` (read-only; SHA-256 in `configuration_manifest.json` of Phase 5.5 and in the baseline snapshot; unchanged). Two sheets: 'Trading Journal' and 'Summary'. The data sheet has FIVE columns only: serial number, date, entry-time label, strategy, outcome (Target / SL / BE). **It records no direction, entry price, stop, target, exit time or exit price**; nothing was invented.

## Verified figures

| item | value | note |
|---|---|---|
| data rows | 190 | serial numbers 1-190 |
| 'Total trades' in the Summary sheet | 189 | differs from the 190 data rows; the Summary appears stale (it also lists 80 Target outcomes against 81 in the data sheet); the 190 rows are used and nothing was corrected |
| rows by strategy | {'IRF': 73, 'PDR': 8, 'ORB': 89, 'RF': 17, 'PDS': 3} | ORB 89 |
| outcomes in the data sheet | {'BE': 44, 'Target': 81, 'SL': 65} | Target 81 / SL 65 / BE 44 |
| weekend-dated rows | 5 | row 23 (sheet row 26) 2025-10-11 Sat ORB; row 82 (sheet row 89) 2026-02-14 Sat IRF; row 181 (sheet row 194) 2026-08-15 Sat ORB; row 185 (sheet row 198) 2026-08-22 Sat ORB; row 189 (sheet row 202) 2026-08-29 Sat ORB |
| weekend rows with market data | 0 | none of the five Saturdays has any one-minute data in the dataset: they are not exchange sessions. They are kept as written (not moved to a neighbouring date) and can never match |
| rows on evaluated sessions | 185 | every weekday journal date is one of the 247 evaluated sessions |
| dates with two journal rows | 5 | no date has more than two |
| entry-time label types | text 'HH:MM' for most rows, a time object (09:15:00) for 19 rows | both rendered HH:MM; seconds dropped |

The Phase 2.1 'attribution hypotheses' (which relabel two groups of journal rows as PDR / ORB) used by the Phase 3.2 reconciliation are NOT applied: the original strategy labels are used.

## What the label means

The journal labels the five-minute candle START (the ORB rows say 09:15, the first candle; the automated ORB signal is confirmed at 09:20). The convention is the pre-existing Phase 3.1 one and is NOT tuned: the automated side is compared at its signal CANDLE START. Evidence that it is the right reading: in configuration A, 66 of 87 matched pairs have the manual label equal to the signal candle start (delta 0); the time-tolerant pairs fall symmetrically in -15..+15 minutes ({-15: 4, -10: 3, -5: 4, 5: 5, 10: 3, 15: 2}), with no systematic offset.

## Matching procedure (one-to-one, staged; implemented in `research/phase56.py`)

1. **STRICT**: same date, same strategy, label == signal candle start (0 minutes). 2. **TIME_TOLERANT**: remaining rows, same date and strategy, |difference| <= 15 minutes (three candles, the Phase 3.1 tolerance, not widened). 3. **DATE_STRATEGY_ONLY**: remaining rows with the same date and strategy but a larger time difference: reported separately and NOT counted as a match. Within each stage the smallest |difference| pairs first (ties: lower journal row, then trade id); a journal row and an automated trade are each used at most once. Outcome labels (Target ~ TARGET, SL ~ INITIAL_FULL_STOP, BE ~ T1_THEN_BUFFER_STOP) are compared AFTER matching and never choose a pair.

**Limitation.** Within a stage the assignment is greedy (smallest time difference first), not a maximum-cardinality assignment. For this data an exhaustive per-(date, strategy) assignment gives the same counts in A, B and C (reviewer check); a different tie-break could change which pair is chosen in a contrived case (labels 10:00 and 10:15 against signals 10:10 and 10:30), not the totals reported here.

Date-and-strategy-only pairs (configuration A): time differences {-135: 1, -100: 1, -85: 2, -50: 1, -45: 1, -35: 1, -25: 1, -20: 1, 20: 6, 30: 1, 95: 1, 150: 1} minutes.
