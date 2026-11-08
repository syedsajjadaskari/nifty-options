# Phase 5.6 - manual journal reconciliation

> SYNTHETIC index-point P&L; no real option P&L. The journal has no direction, price or exit time: matching uses only date, strategy and the entry-time label, and every automated-trade explanation rests on the actual candles and the documented rules.

The automated trades of configurations A (frozen Phase 3.6), B (Phase 5.3 author-corrected) and C (B + ORB gap crossing) of Phase 5.5 were reconciled one-to-one with the ORIGINAL manual journal, separately per configuration.

The 'date + strategy only' column is a subset of the 'manual-only rows' and 'automated-only trades' columns (those pairs are NOT matches): matched + manual-only = 190 journal rows.

| configuration | automated trades | strict | time-tolerant | matched | date + strategy only | manual-only rows | automated-only trades |
|---|---|---|---|---|---|---|---|
| A - frozen Phase 3.6 | 196 | 66 | 21 | 87 | 18 | 103 | 109 |
| B - Phase 5.3 author-corrected | 188 | 64 | 14 | 78 | 17 | 112 | 110 |
| C - B + ORB gap crossing | 190 | 67 | 14 | 81 | 17 | 109 | 109 |

* Journal: 190 data rows (Summary sheet says 189), 89 ORB rows, 5 Saturday-dated rows (no sessions; kept as written). No direction, price or exit is recorded.
* Every mismatch is classified by its earliest cause with evidence (`mismatch_root_causes.csv`); the strategy rules were NOT changed to raise the match count.
* 247 session explanations (`daily/`), 143 charts of material mismatches (`charts/`).

## Files

`manual_journal_source_audit.md`, `manual_vs_automated_matching.csv`, `strict_matches.csv`, `time_tolerant_matches.csv`, `manual_only_trades.csv`, `automated_only_trades.csv`, `wrong_strategy_dates.csv`, `orb_unmatched_dates.csv`, `irf_unmatched_dates.csv`, `pdr_pds_unmatched_dates.csv`, `mismatch_root_causes.csv`, `cross_configuration_reconciliation.md`, `handwritten_author_corrections_comparison.csv`, `independent_audit.md`, `Manual_vs_Automated_Trading_Audit.xlsx`, `daily/`, `charts/`, `phase56_state.json`.

## Reproduce

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase55_run.py                     # the Phase 5.5 backtest (inputs)
python scripts/phase56_run.py                     # matching, causes, daily reports, charts, workbook
python scripts/phase56_independent_audit.py
python scripts/phase56_docs.py --tests "..." --ruff "..."
```

(Phase 5.5 independent audit: all checks pass.)
