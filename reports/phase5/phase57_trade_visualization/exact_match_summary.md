# Exact journal-match summary (Phase 5.7)

> SYNTHETIC NIFTY 50 index-point P&L (6 lots x 65 units); not option P&L. The journal records no price, direction or exit time, so 'exact' below means exact on DATE, STRATEGY and the entry-time LABEL only - never on price or outcome.

## The answer: how many executed trades exactly match the manual journal?

| configuration | automated executed trades | EXACT (strict) matches | % of automated trades | % of the 190 journal rows |
|---|---|---|---|---|
| A - frozen Phase 3.6 | 196 | 66 | 33.67 % | 34.74 % |
| B - Phase 5.3 author-corrected | 188 | 64 | 34.04 % | 33.68 % |
| C - B + ORB gap crossing (provisional) | 190 | 67 | 35.26 % | 35.26 % |

An EXACT match is a one-to-one pair with the same date, the same strategy and a journal entry-time label equal to the automated signal CANDLE START (the journal labels the five-minute candle start). Time-tolerant matches (within 15 minutes) are NOT mixed into this number, and date-and-strategy-only pairs are never counted as matches. The matching is the verified Phase 5.6 matching, unchanged.

## Full table

| measure | A - frozen Phase 3.6 | B - Phase 5.3 author-corrected | C - B + ORB gap crossing (provisional) |
|---|---|---|---|
| total automated executed trades | 196 | 188 | 190 |
| strict / EXACT matches | 66 | 64 | 67 |
| time-tolerant matches (0 < /delta/ <= 15 min) | 21 | 14 | 14 |
| date-and-strategy-only pairs (time more than 15 min apart; NOT matches) | 18 | 17 | 17 |
| total counted matches (strict + time-tolerant ONLY) | 87 | 78 | 81 |
| counted matches as % of automated trades | 44.39 % | 41.49 % | 42.63 % |
| counted matches as % of the 190 journal rows | 45.79 % | 41.05 % | 42.63 % |
| manual-only rows - no counted match (includes the date-and-strategy-only pairs and the 5 Saturday rows) | 103 | 112 | 109 |
|   of which with no automated trade of the same date and strategy at all (journal-row view of 'manual only') | 85 | 95 | 92 |
| automated-only trades - no counted match (includes the date-and-strategy-only pairs) | 109 | 110 | 109 |
|   of which with no journal row of the same date and strategy left for them (AUTOMATED_ONLY on the charts) | 91 | 93 | 92 |
| counted matches whose journal outcome label agrees with the automated exit class | 80 | 71 | 74 |
| counted matches whose outcome label differs | 7 | 7 | 7 |
| exact (strict) matches with the same outcome label | 64 | 61 | 64 |
| exact (strict) matches with a different outcome label | 2 | 3 | 3 |

Outcome labels are compared AFTER matching and never choose a pair (Target ~ TARGET, SL ~ INITIAL_FULL_STOP, BE ~ T1_THEN_BUFFER_STOP); what the journal's 'BE' meant is undocumented.

## Exact (strict) matches by strategy

| configuration | IRF | ORB | PDR | PDS | RF | total |
|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 26 | 35 | 0 | 1 | 4 | 66 |
| B - Phase 5.3 author-corrected | 20 | 35 | 4 | 1 | 4 | 64 |
| C - B + ORB gap crossing (provisional) | 20 | 38 | 4 | 1 | 4 | 67 |

## Time-tolerant matches by strategy (reported separately)

| configuration | IRF | ORB | PDR | PDS | RF | total |
|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 15 | 0 | 3 | 0 | 3 | 21 |
| B - Phase 5.3 author-corrected | 10 | 0 | 1 | 0 | 3 | 14 |
| C - B + ORB gap crossing (provisional) | 10 | 0 | 1 | 0 | 3 | 14 |

## Per strategy: journal rows, automated trades and match stages

| cfg | strategy | journal rows | automated trades | strict | time-tolerant | date + strategy only | manual-only (no counted match) | automated trades without counted match | strict % of journal rows | strict % of automated trades |
|---|---|---|---|---|---|---|---|---|---|---|
| A | IRF | 73 | 109 | 26 | 15 | 14 | 32 | 68 | 35.62 | 23.85 |
| A | ORB | 89 | 41 | 35 | 0 | 0 | 54 | 6 | 39.33 | 85.37 |
| A | PDR | 8 | 25 | 0 | 3 | 3 | 5 | 22 | 0.0 | 0.0 |
| A | PDS | 3 | 11 | 1 | 0 | 1 | 2 | 10 | 33.33 | 9.09 |
| A | RF | 17 | 10 | 4 | 3 | 0 | 10 | 3 | 23.53 | 40.0 |
| B | IRF | 73 | 90 | 20 | 10 | 15 | 43 | 60 | 27.4 | 22.22 |
| B | ORB | 89 | 41 | 35 | 0 | 0 | 54 | 6 | 39.33 | 85.37 |
| B | PDR | 8 | 28 | 4 | 1 | 1 | 3 | 23 | 50.0 | 14.29 |
| B | PDS | 3 | 19 | 1 | 0 | 1 | 2 | 18 | 33.33 | 5.26 |
| B | RF | 17 | 10 | 4 | 3 | 0 | 10 | 3 | 23.53 | 40.0 |
| C | IRF | 73 | 89 | 20 | 10 | 15 | 43 | 59 | 27.4 | 22.47 |
| C | ORB | 89 | 44 | 38 | 0 | 0 | 51 | 6 | 42.7 | 86.36 |
| C | PDR | 8 | 28 | 4 | 1 | 1 | 3 | 23 | 50.0 | 14.29 |
| C | PDS | 3 | 19 | 1 | 0 | 1 | 2 | 18 | 33.33 | 5.26 |
| C | RF | 17 | 10 | 4 | 3 | 0 | 10 | 3 | 23.53 | 40.0 |

## Reading the numbers

* The 190 journal rows include 5 Saturday-dated rows that can never match; the maximum possible number of matches is therefore below 190.
* 'Exact' says the journal and the automated system started the SAME strategy on the SAME day with the SAME candle label. It does not say that prices or exits agree (the journal records neither). Of the exact matches, 189 of 197 (A + B + C) carry the same outcome label.
* No configuration is selected or ranked here; the counts are descriptive. They come unchanged from `reports/phase5/phase56_manual_reconciliation/` (audited again by `independent_audit.md`).

Files: `exact_match_summary.csv`, `manual_match_breakdown.csv`, `all_executed_trades_visual_index.csv` (one row per trade with its match status), `Phase57_Trade_Verification.xlsx`.
