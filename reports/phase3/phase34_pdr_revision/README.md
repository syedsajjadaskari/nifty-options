# Phase 3.4 - PDR revision (author-approved entry rules)

**Written for:** the strategy owner, for manual review. Start with `phase34_summary.md`.

The strategy author's clarifications - previous-day high (+ connected multiple highs), one of three confirmation candles, close strictly above the zone ceiling - are implemented in a **new, versioned engine** (`src/nifty_trading/strategies/pdr_revised.py`); the legacy PDR engine and every earlier result are untouched. Comparison is at **signal level only**: no portfolio back-test, no P&L. Every signal carries a configuration id and the approval status of each rule; numeric details the author did not give are research parameters.

| file | content |
|---|---|
| `README.md` | this file |
| `author_approved_pdr_rules.md` | the author's clarifications as rules with statuses |
| `pdr_zone_construction.md` | candidates A and B, parameters, Example 3 discrepancy |
| `pdr_confirmation_patterns.md` | the three patterns, thresholds, the guide's example candles |
| `old_vs_new_pdr_signals.csv` | every old signal (383) x candidate and every newly valid signal, with tags and reasons; the 54 old trades are flagged |
| `pdr_daily_signal_comparison.csv` | one row per session per candidate (494): zone, gap, retest, patterns, signals, old vs revised status, tags, reason |
| `pdr_entry_condition_details.csv` | every candle examined after a test, accepted or rejected, with pattern details, close vs ceiling, fill |
| `pdr_manual_journal_comparison.csv` | PDR and disputed journal rows against the old and revised signals |
| `pdr_unresolved_cases.md` | open interpretations with the size of their effect |
| `pdr_sensitivity_counts.csv` | signal counts under each unresolved setting (counts only) |
| `source_example_validation.csv` | the guide's dated examples under the revised rules |
| `charts/` | 117 annotated charts on real candles + `charts_index.csv` |
| `source_to_code_traceability.md` | rule -> code -> tests |
| `independent_audit.md` | second implementation + second reviewer |
| `phase34_summary.md` | results in plain English |
| `PDR_Revision_Day_by_Day.xlsx` | workbook for day-by-day checking (does not replace the Phase 3.2 master workbook) |
| `before_snapshot.json` | hashes, git head and test status recorded before the first edit |
| `pdr_revision_rules.csv` | the rules as data |
| `pdr_journal_agreement_2x2.csv` | journal agreement by pattern thresholds x open rule (agreement observation only) |
| `_run_summary.json` | machine-readable headline counts of the run |
| `independent_audit_results.json` | machine-readable results of scripts/phase34_independent_audit.py |

## Reproduce

```
.venv/bin/python scripts/phase34_run.py                 # engines, CSVs, charts
.venv/bin/python scripts/phase34_independent_audit.py   # second implementation from the raw data
.venv/bin/python scripts/phase34_docs.py                # markdown + workbook
.venv/bin/python -m pytest -q && .venv/bin/ruff check .
```
