# Independent verification and self-review

Fresh reconstruction challenged the previous reports rather than accepting their conclusions. This file records a separate consistency review by the same investigator; no second reviewer is implied.

| Check | Result | Observed |
|---|---|---|
| Requested evidence artifacts exist | PASS | ['README.md', 'orb_original_source_rules.md', 'orb_source_to_code_mapping.csv', 'orb_implementation_line_by_line.md', 'orb_all_entry_predicates.csv', 'orb_13_handwritten_disputes.csv', 'orb_all_manual_journal_dates.csv', 'orb_vs_irf_selection_timeline.csv', 'orb_missing_trade_root_causes.csv', 'orb_level_construction_comparison.md', 'orb_moving_average_investigation.md', 'orb_candle_strength_investigation.md', 'orb_candidate_signal_differences.csv', 'orb_implementation_defects.md', 'orb_required_author_clarifications.md', 'ORB_Forensic_Verification.xlsx', 'charts', 'daily'] |
| Journal date rows 89 per configuration | PASS | 267 |
| 13 distinct handwritten dates per configuration | PASS | 39 |
| No author direction or exact level invented | PASS | 267 |
| Every focus date has daily page | PASS | 91 |
| Every evaluable focus date has raw1m/5m/prior5/chart | PASS | 87 |
| All SVGs parse | PASS | [] |
| independent_signal_parity_failures | PASS | [] |
| orb_prefix_failures | PASS | [] |
| stored_signal_disagreements | PASS | [] |
| ledger_signal_or_fill_failures | PASS | [] |
| first_selection_failures | PASS | [] |
| Nearest-inner reconstruction independently matches optional engine across all247 sessions | PASS | 247 |
| Independent raw5m OHLC and EMA checks | PASS | {'ohlc_candles_checked': 18525, 'ohlc_max_error': 0.0, 'ema_max_error': 1.6370904631912708e-10, 'failures': []} |
| Frozen and candidate strategy files match original Phase5.5 manifest | PASS | [] |
| Audited PDFs, journal, data and ledgers unchanged since measured | PASS | [] |
| Chart ledger stop and T1/T2 arithmetic | PASS | [] |
| Chart exit prices satisfy raw-bar range or documented conservative gap-target convention | PASS | {'unexpected': [], 'conservative_target_fills': 6} |
| Exported XLSX cached summary equals independent counts | PASS | {'A': [85, 35, 50, 35, 0, 34, 5, 16], 'B': [85, 35, 50, 35, 0, 30, 5, 20], 'C': [85, 38, 47, 38, 0, 29, 5, 18]} |
| Exported XLSX retains COUNTIFS formulas | PASS | B5:B7 |
| Exported XLSX Journal has all267 configuration/date rows | PASS | 271 |
| Exported workbook includes every isolated candidate difference | PASS | {'expected': 70, 'actual': 70} |
| Exported XLSX has no error cells | PASS | [] |
| Workbook table freezes retained | PASS | C5 |
| Full pytest suite finished successfully | PASS | 781 passed, 1 skipped, 1 xfailed in 1475.28s (0:24:35) |
| Full ruff check passes | PASS | All checks passed! |

## Material limitations

- The same investigator performed this independent reconstruction and self-review; no second human or agent review is claimed.
- No exact author direction, level, trendline or entry price is recorded for the13 disputes or journal rows. No profitability-based choice or objectively proven missed author trade is asserted.
- Gap figures support candle crossing, while part of wording supports open crossing; indicator identity and excessive extension remain unresolved.
- A/B/C strategy signals and first-entry choice were freshly verified. Existing ledger exits were range/arithmetic checked; no new exit walk, P&L or second-trade outcome calculation was run.
- The requested full pytest suite includes existing baseline historical-regression tests. No candidate profitability backtest or new profitability report was run.
- Six ledger target fills (two ORB trades repeated in A/B/C) lie outside their exit minute's traded range because the existing model conservatively fills a gapped target at its level. These are model fills, not observed prices; ledger_target_gap_conventions.csv records the actual bars. Previous ledgers are preserved.
- All13 PDF source pages and6 handwritten pages were visually inspected. All7 workbook sheets were rendered/reviewed; four representative historical charts were inspected at full size. All87 SVGs were parsed and structurally checked, not87 separate human chart interpretations.
- Native Excel was not opened. Artifact-tool summary recalculation reacted to a changed Journal signal and was restored; exported cached counts/formulas were read back independently.
- Historical contexts use offline full-session quality checks. Real-time adapter/broker timing is outside the verified path; no paper/live orders were placed.
- Phase5.7 was concurrently developed by another process. This audit never writes its paths; changes by that other process are not attributed to this audit.

## Test interpretation

New source-example tests cover both gap-diagram directions, the author's green-long correction, independent body geometry, first5m aggregation, incomplete bucket exclusion, EMA seed/prefix causality and confirmed-pivot availability. One strict xfail preserves a confirmed existing optional-wrapper metadata defect, intentionally left unfixed under the audit-only instruction. It is not treated as a passing implementation test. The one skipped test is the Phase3.4 snapshot-preservation test, explicitly superseded by the Phase3.5 snapshot test (`tests/test_phase34_pdr_revision.py:321`).

Snapshot/default-equivalence tests elsewhere establish reproducibility, not author fidelity. Missing source tests require the author's exact price-axis examples with indicator settings and level/anchor drawings. No test can certify an undefined discretionary rule merely because signal counts match the journal.
