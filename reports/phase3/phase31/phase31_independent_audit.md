# Phase 3.1 - independent audit (QA review and dispositions)

Three independent read-only reviews fed this phase: (1) the IRF/RF source-to-code auditor and (2) the ORB/PDR/PDS auditor (reports in `source_to_code_audit.md`), and (3) a QA reviewer who re-checked the reconciliation itself from the raw journal workbook, the raw 1-minute data and the Phase 3.0 ledgers, without using the Phase 3.1 code to produce the answers. The reviewers could not edit the repository; every fix below was made by the implementer and is listed with its test.

## What the QA reviewer verified (PASS)

| check | result |
|---|---|
| Counts from the raw workbook (190 rows: ORB 89, IRF 73, RF 17, PDR 8, PDS 3), the baseline ledger (213) and the three CSVs | all agree; 84 matched (67 exact, 17 time-shifted) + 129 extras = 213 and 84 + 106 missing = 190; per-strategy tables agree with the summary and `reconciliation_counts.json`; matched and extras are disjoint; no automated trade or manual row used twice |
| All 84 matches against raw 1-minute data | entry price = open of the bar at the entry time; candle start = signal time - 5 min; fill = signal time; delta within 15 min; for every time-shifted match the matched trade is the only same-strategy trade that day |
| Label convention | offsets of -10/-5/0/+5/+10 minutes give 3/4/**67**/2/2 exact hits: "label = candle start" is strongly supported |
| 22 unmatched rows sampled with a fixed seed (20261103) across all classes | portfolio blockers were active or finished before the signal; Saturday rows have no session; ORB "no level break" rows recomputed from raw data; row 132 (wick 0.244 vs limit 0.20), row 201 (body 0.473) and RF row 167 (open 6.2 points above yesterday's high) confirmed |
| Traces | all 19 `disputed_trade_traces/*_1m.csv` equal the raw data |
| Timeline blockers | 0 rows have a blocker that started after the signal |
| Ledger integrity | sha256 of all four Phase 3.0 ledgers equals `phase30_ledger_hashes.json`; the provenance hashes of the 14 data files equal the files on disk |
| Matching uses no P&L | date, strategy, candle start and label only; the outcome comparison is descriptive |

## Findings and dispositions

| id | finding | disposition |
|---|---|---|
| S2-1 | The failed-setup step of `_classify_unmatched` was not time-anchored: an `INCOMPLETE_AT_EOD` record (stamped with the last candle of the session) explained 8 IRF rows and 1 PDS row whose manual decision was hours earlier, and inflated SOURCE_AMBIGUITY | **Fixed.** A failed setup now explains a manual row only if it failed at or before the label (+ tolerance); an end-of-session pending setup counts only within the tolerance of its stamp, otherwise it is recorded in the chain as `SETUP_PENDING_NEVER_CONFIRMED`. Those rows moved from SIGNAL_REJECTED_BY_ENTRY_RULE to MISSING_AUTOMATED_SIGNAL (entry-rule 59 -> 50, missing 19 -> 28; matches, extras and totals unchanged). Test: `test_an_end_of_session_pending_setup_does_not_explain_an_earlier_manual_decision` |
| S2-2 | Look-ahead in the fallbacks of `blocker_of` (collision and first-trade fallbacks ignored the signal time) | **Fixed** (time-checked); `state_at` was already causal and is now commented. No delivered row was affected (the reviewer found 0 violations). Test: `test_blockers_and_states_never_use_information_from_after_the_signal_time` (the reviewer's mutations of these lines were not caught by the old tests) |
| S2-3 | `startswith("TREND")` also matched `TRENDLINE_NOT_SUPPORTIVE`, so 9 ORB Method 2 trendline rows were reported as TREND_FILTER | **Fixed.** Only `TREND:` is a trend-filter rejection (TREND_FILTER 21 -> 12); trendline rows are SOURCE_AMBIGUITY (the guide gives no construction). The catch-all that defaulted any unmapped entry-rule detail to SOURCE_AMBIGUITY now returns UNKNOWN with `UNMAPPED_ENTRY_RULE_DETAIL`; the genuinely source-ambiguous RF/ORB gap, range and MA-definition details are mapped explicitly. Test: `test_trendline_is_not_a_trend_filter_and_an_unmapped_detail_is_unknown_not_a_default_cause` |
| S2-4 | Over-strong prose in `root_cause_analysis.md` ("biggest single lever", "created mostly by extra PDR and IRF trades, not by the first-signal rule", "Timing is not the problem") | **Fixed.** Reworded and computed: the ranking is "one of the largest, under the heuristic"; 8 of the 23 portfolio-rejected rows met a still-open position, 12 met a day already finished or restricted by an earlier automated trade that had exited, 3 are collisions (so the approved one-trade-per-day rule is the mechanism); timing is "small compared with selection", with 12 unmatched rows having a confirmed same-strategy signal more than 15 minutes away (a labelled tolerance) |
| S2-5 | `NO_RAW_SIGNAL_AND_NO_SETUP_RECORD` was false for rows that do have a confirmed signal far from the label | **Fixed.** The chain is now `NO_CONFIRMED_SIGNAL_WITHIN_TOLERANCE_AND_NO_ANCHORED_SETUP_RECORD`, with the nearest confirmed signal and its delta appended when one exists (test above) |
| S3-1 | Row 93's alternate-label match (ORB 09:15 -> PDR 09:20) is derived from Phase 2.1 attribution hypotheses that are outcome-count based; a dead no-op expression at the classification line | Dead expression **removed**. The alternate-label origin is disclosed here and in the `matched_via_alternate_label` column (one row; the matcher itself never reads P&L) |
| S3-2 | Row 83 (2026-02-03 IRF): the first 1-minute bar spans about 490 points after a gap, so IRH/IRL are inflated and "TIME_ALIGNMENT" overstates certainty | **Documented** in the root-cause analysis; the label stays a heuristic |
| S3-3 | Some prose numbers in `phase31_report.py` and the analysis text are hand-typed ("247", "72 of 108", "51 days", PDR/PDS funnel figures from the Phase 2.x audit) although the header says every figure is computed | **Partly fixed:** the counts that changed with this review are now computed (IRF/PDS class lists, TIME_ALIGNMENT, UNKNOWN, portfolio split, far-signal count). The remaining typed figures are quoted from the source auditors' read-only runs and are attributed to them; the claim "every figure computed" applies to the tables |
| S3-4 | "SOFTWARE_BUG: none" and "mechanically looser than every PDR chart" are asserted | **Accepted as stated with attribution:** the first is now backed by `confirmed_software_defects.md` (one latent defect, found by the source audit and fixed); the second is the PDR auditor's measured comparison (`source_to_code_audit.md`, Appendix B) |
| S3-5 | Table B puts "manual unmatched" (manual strategy) beside "automated extra" (matched strategy); the alternate-label row makes the columns not row-aligned | **Noted:** the totals reconcile; one row is affected |
| S3-6 | Missing tests (tolerance boundary, tie-break, exact-over-shifted with alt labels, real-data causality, summary equals CSVs, failed-setup within tolerance) | **Added:** tolerance boundary (15 vs 16 minutes), the tie-break to the earlier candle, blocker/state causality, anchored failed setups and the nearest-signal chain, trendline/unmapped mapping. 23 tests in the file (19 before). The real-data causality and summary-equals-CSV checks are covered by the existing delivered-output tests (identity, ledger membership, ledger hashes) and by the QA reviewer's one-off checks; no new delivered-output test was written for them |

Also noted by the QA reviewer: the reconciliation uses 247 sessions (2025-10-21 has 1-minute data but no timeline; hard-coded in the report script), and `git` cannot prove the Phase 3.0 ledgers are unmodified (`reports/phase3/` is untracked), so integrity rests on the sha256 file written at the start of Phase 3.1, corroborated by file times older than every Phase 3.1 output and by the data provenance hashes.

## State after the fixes

* Regenerated: `manual_vs_automated.csv`, `missing_manual_trades.csv`, `extra_automated_trades.csv`, timelines, matrix, `reconciliation_counts.json`, `analysis_tables.json`, `reconciliation_summary.md`, `root_cause_analysis.md`, `disputed_trade_traces/`. Matches (84), extras (129) and missing (106) are unchanged; only the classification and root-cause labels of unmatched rows moved as described.
* `ruff` clean; full suite **413 passed**; the four Phase 3.0 ledger hashes unchanged.

## Not verified by anyone (limits of this audit)

* Scenarios B and C (`ema_structure`, `pdr_shelf`) classifications and their sensitivity counts (64 and 87 matched); the `analysis_tables.json` funnels (PDR 140/246, 383 raw signals, ORB 108-109/247) and the Phase 2.x figures they quote were verified by the source auditors' own read-only runs, not by the QA reviewer.
* The signal engines were not independently re-implemented; the auditors ran them and replayed them on truncated sessions (no look-ahead found).
* EMA-based trend rejections (rows 69, 145, 151) were not recomputed from raw data; the PDR/PDS zone computations beyond the gap sign were not recomputed; the SVG charts and 18 of 19 trace documents were not read line by line.
* Coverage is **not exhaustive**: 84 of 84 matches and 22 of 106 unmatched rows were checked against raw data, the rest rest on the classification code and the delivered-output tests.
* The manual journal is a discretionary record with known inconsistencies; nothing in this audit says which side is right.
