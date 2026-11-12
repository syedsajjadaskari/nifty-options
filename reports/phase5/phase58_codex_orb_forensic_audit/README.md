# Phase 5.8 - independent ORB forensic audit

Completed original-source examination and candle/signal reconstruction; no active strategy changes or profitability backtest. The original13-page PDF and all6 handwritten pages were visually inspected. Existing reports were cross-checks, not the source of rule conclusions.

The previous controller conclusion holds in its **narrow software sense**: no earlier confirmed frozenORB was silently bypassed forIRF on a journal-ORB day. It does **not** establish source fidelity. The engine's latest-fractal inner level, last-two-fractal trendline, numerical shape filters and prior-sessionEMA trend are mechanical interpretations. Gap-open requirement contradicts both source gap figures. The green-long clarification is absent from the frozen engine and A/B/C. Many author-expected entries remain unresolved because no direction, method or level is recorded.

## A. What is implemented

Method1: previous-day extreme broken and closed beyond at09:20, prior-sessionEMA trend, strong body or pin. Method2: latest inner non-strict5bar fractal in previous session; same trend; last-two-pivot trendline supportive; strong/pin and nearEMA15-point band /5-point close margin. Gap: directional gap, prior close old side and OPEN beyondEMA, first close beyond, strong/pin, rejection-wick filter; extension capNone. Both directions, completed first candle only. Baseline trend is prior-sessionEMA location, not standalone ProposalConfig structure default. See [source rules](orb_original_source_rules.md), [traceability](orb_source_to_code_mapping.csv), [line-by-line audit](orb_implementation_line_by_line.md), [predicates](orb_all_entry_predicates.csv).

Missing/unfinished source components: mechanically defined inner/consolidation zones, relevant trendline choice, exact structural trend, excessive opening extension and indicator ambiguity; author green-long not enabled by default. Some current rules are narrower (open beyondMA, fixed thresholds, latest-pair construction), while the prior-only trend and disabled extension can be more permissive. There is no universal claim all implementation differences reject valid trades.

## B. Independently verified journal coverage

Original workbook: **190 data rows**, **89 ORB rows**, **89 unique ORB dates**, **85 evaluable ORB dates**. Row-level records are preserved in `orb_manual_journal_rows.csv`; unique-date/config records in `orb_all_manual_journal_dates.csv`. Five Saturday entries are retained as journal inconsistencies, not silently shifted. The workbook Summary sheet's189 total is not the data-row count.

| config | orb_signal_dates | no_orb_signal_evaluable_dates | orb_executed_dates | orb_signal_no_orb_execution | irf_executed_dates | another_strategy_executed_dates | no_automated_trade_dates |
|---|---|---|---|---|---|---|---|
| A | 35 | 50 | 35 | 0 | 34 | 5 | 16 |
| B | 35 | 50 | 35 | 0 | 30 | 5 | 20 |
| C | 38 | 47 | 38 | 0 | 29 | 5 | 18 |

Counts are unique dates per configuration. `no_orb_signal_evaluable_dates` excludes no-session journal dates. The signal/no-execution column isolates portfolio effects. IRF and other-strategy date counts can overlap when a second trade occurs; they are not a mutually exclusive partition. `first_executed_strategy_counts` in audit_summary.json is a partition. A is frozen Phase3.6; B is Phase5.3; C changes B's gap crossing only. All executed entries/exits shown are existing ledger records verified against freshly generated signals and raw entry bars, not new trades.

## C. Root causes

All failures are preserved per method and direction in `orb_predicate_observations.csv` and daily/. `predicate_frequency.csv` gives reached failures, latent failures and sole-gate sensitivities without treating unknown author direction as known. `predicate_frequency_missing_only.csv` restricts those counts to the50 evaluable no-signal dates. Previous-day unbroken is a source-supported Method1 exclusion; it does not disprove a possible Method2 setup. Inner selection and trendline failures reject the current construction; they do not prove no author-valid level exists. Strength percentages and nearMA distances are proposals. Gap crossing is a source conflict, not an unambiguous author exclusion. No root cause is forced from the method with fewest failed gates.

## D. ORB versus IRF

The count of dates withIRF is in the table above; every date is enumerated with first signals and exact failed gates in [selection timeline](orb_vs_irf_selection_timeline.csv), [readable chronology](orb_vs_irf_findings.md) and daily/. First selection was independently checked against freshly generated fillable signals and raw1m bars, without running the controller's exit model. No automatic strategy priority is added. The author's day's-lowIRF exclusion is absent and undefined; final-day hindsight is not used.

## E. Corrections and unresolved decisions

[Defects](orb_implementation_defects.md) separates confirmed optional-wrapper metadata defect, author-colour mismatch, source-conflicting gap interpretation, and undefined constructions. Green longs are explicitly clarified; activating that rule removes signals. Gap-candle is supported by figures but indicator/text still need author resolution. Level/trendline/strength changes require exact definitions. The corrective plan is in [author clarifications](orb_required_author_clarifications.md). No active correction was enabled under the audit-only instruction.

## F. Independent verification

Fresh raw aggregation, independent EMA recurrence, independent six-path predicate reconstruction, frozen/candidate signal parity and prefix invariance were checked. A/B/C confirmed signals were regenerated and compared to stored signals; all ledger fills were checked against raw1m opens. Whole-dataset first-entry chronological choice was checked without recalculating outcomes. [Independent review](independent_review.md) records results and limitations. No independent second person/agent is implied by that filename.

Examined **13 handwritten disputes** and all journalORB dates; **87 annotated actual-candle charts**, with daily1m/5m files and prior-five-session evidence. The13 handwritten source setups remain unproved where no exact level/direction exists; hypothetical candidate eligibility is distinguished from author validity.

Frequent failed gates on the50 evaluable frozen no-signal dates (both possible directions, overlapping counts; not author-direction attribution):

| method | direction | predicate | failed_dates | missing_evaluable_dates | reached_and_failed_dates |
|---|---|---|---|---|---|
| Method 1 | LONG | previous_level_close | 42 | 50 | 42 |
| Method 1 | SHORT | previous_level_close | 38 | 50 | 38 |
| Method 2 | LONG | trendline | 42 | 50 | 10 |
| Method 2 | SHORT | trendline | 41 | 50 | 5 |
| Gap/200DMA | LONG | gap_crossing | 42 | 50 | 26 |
| Gap/200DMA | SHORT | gap_crossing | 47 | 50 | 13 |

| variant | added_method_direction_signals | removed_method_direction_signals | changed_unique_dates | changed_handwritten_dates | authority |
|---|---|---|---|---|---|
| gap_candle | 3 | 0 | 3 | [] | SOURCE_SUPPORTED_CONFLICTING_TEXT |
| strength_loose | 13 | 0 | 8 | ['2025-12-12', '2025-12-30'] | NUMERIC_SENSITIVITY_ONLY |
| trend_current | 13 | 0 | 11 | [] | BASIC_FILTER_ONLY_STRUCTURE_UNRESOLVED |
| inner_extreme | 0 | 2 | 2 | [] | LEVEL_SELECTION_PROPOSAL |
| trendline_any3 | 16 | 0 | 16 | ['2025-11-28'] | CONSTRUCTION_PROPOSAL |
| colour | 0 | 3 | 3 | [] | AUTHOR_CLARIFIED_LONG_MIRRORED_SHORT |
| gap_daily_sma | 0 | 10 | 10 | [] | INDICATOR_SENSITIVITY_NOT_CORRECTION |
| inner_nearest | 2 | 8 | 10 | ['2025-12-24'] | LEVEL_SELECTION_PROPOSAL |

Signal differences count method/direction records, not unique dates or new trades. Every alternative changes one family; all are disabled. No candidate is chosen by journal agreement or profitability. False positives relative to an unrecorded discretionary author decision are unknowable; candidate rows disclose this rather than claiming higher agreement proves fidelity.

## Evidence and reproduction

`ORB_Forensic_Verification.xlsx` contains formula-linked counts and detailed source, journal, disputes, chronology, path observations and candidates. `charts/` covers all evaluableORB journal dates (including matched representatives), all13 handwritten dates and every journalORB/IRF-selected date; missing Saturday sessions have explicit no-data daily pages. Existing ledger exits are marked only for real simulated ledger trades. No manual price is fabricated.

Run only the new forensic scripts:

```sh
.venv/bin/python scripts/phase58_run.py
.venv/bin/python scripts/phase58_candidate_evidence.py
.venv/bin/python scripts/phase58_irf_context.py
.venv/bin/python scripts/phase58_docs.py
.venv/bin/python scripts/phase58_supplement.py
.venv/bin/python scripts/phase58_package.py
node reports/phase5/phase58_codex_orb_forensic_audit/build_workbook.mjs
.venv/bin/pytest -q
.venv/bin/ruff check src tests scripts
```

Do not rerun Phase5.5/5.7 to reproduce this audit. Phase5.8 reads existing ledgers and never calls exit/portfolio simulation. No commit/push or orders.

## Exact candidate evidence on handwritten dates

These are causal diagnostic alternatives, not author-confirmed entries. Each signal would be available at09:20; no variants were combined.

| Date | Path | Exact blocking rule and isolated sensitivity |
|---|---|---|
| 2025-11-28 | Method2 LONG | Inner26,228.20 already breaks. Last-two-pivot trendline fails; an alternative pair among the last3 produces a supportive line at26,213.55. Author anchors unknown. |
| 2025-12-12 | Method1 LONG | Previous high25,921.75 breaks; body52.24% fails60% minimum. LOOSE profile qualifies, but50% has no explicit ORB source authority. |
| 2025-12-24 | Method2 LONG | Latest inner26,206.65 is unbroken; a nearest pre-open eligible inner26,188.55 breaks at close26,198.25. Author's chosen inner level unknown. |
| 2025-12-30 | Method1/2 SHORT | Close25,908.05 breaks25,922.25 /25,924.95. Body76.15% passes; lower wick23.85% fails20% cap. LOOSE25% cap qualifies but is not an author-defined cutoff. |

All70 changed method/direction records now include baseline/candidate levels, line projections, signed distances, first-candle geometry and every changed-path gate in `orb_candidate_signal_differences.csv`. `orb_shape_components.csv` decomposes strong-versus-pin OR routes; `orb_level_measurements.csv` keeps body/wick/multisession context separate from signal levels.

IRF also needs a fidelity distinction: handwritten entry-body notes and the day's-low exclusion are not universal gates in the current IRF engines. `irf_rejection_context.md` and `irf_first_signal_context.csv` document actual first-IRF shapes and causally known lows. No new IRF filter was applied. The requested full pytest suite includes existing baseline historical-regression tests; no candidate profitability backtest or new profitability report was run.

## Final verification

- Complete pytest suite: **781 passed, 1 skipped, 1 strict expected failure** in 1,475.28 seconds. The skipped Phase 3.4 snapshot test is explicitly superseded by the Phase 3.5 snapshot test. The expected failure preserves the confirmed optional colour-wrapper metadata defect without changing strategy behaviour.
- New diagnostic tests: **8 passed, 1 expected failure** after the final reconstruction update.
- Ruff: **All checks passed** across `src`, `tests` and `scripts`.
- Saved workbook counts, formulas, candidate coverage and error-cell checks passed. Formula counts reacted to a temporary evidence change and were restored. All seven sheets were rendered and reviewed; native Excel was not opened.
- Independent signal parity, raw candle aggregation, EMA recurrence, first-selection chronology, ledger fill/target checks and source/data/ledger preservation checks passed. [Full review](independent_review.md).
- [All 13 disputes in one table](orb_13_disputes_readable.md) and [chart index](charts/README.md) provide direct access to the evidence. All 13 original PDF pages and all six handwritten pages were visually inspected.

Active strategy files match the original Phase 5.5 manifest. Previous data and ledgers remain unchanged. Phase 5.7 files were never written by this audit. No commit, push or orders were made.
