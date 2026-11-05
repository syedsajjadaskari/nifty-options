# Phase 3.5 - combined five-strategy backtest

**Written for:** the strategy owner. Start with `backtest_summary.md`.

## Rerun it independently (macOS terminal)

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase35_run.py --pdr-engine revised
```

Then, optionally: `python scripts/phase35_docs.py` (regenerates this README and the summary from the CSV files) and `python scripts/phase35_independent_audit.py` (the independent audit).

`python scripts/phase35_run.py --help` lists the options. `--pdr-engine revised` (default) uses `src/nifty_trading/strategies/pdr_revised.py`; `--pdr-engine legacy` re-runs the Phase 3.0 baseline into `reports/phase3/phase35_legacy_check/` and exits non-zero if the frozen Phase 3.0 ledger is not reproduced field by field. `--out DIR` changes the output directory; the runner refuses to write into an earlier phase's directory.

The run takes about 30 seconds and reads only `data/processed/` and `docs/trading journal/`; it writes only inside `reports/phase3/phase35_*`. Configuration id of this run: `CFG-phase35_combined-1a0f4fca27`.

| file | content |
|---|---|
| `README.md` | this file |
| `backtest_summary.md` | results in plain English with the comparison against Phase 3.0 - start here |
| `daily_summary.csv` | one row per evaluable session (247), including no-trade days |
| `all_trades_detailed.csv` | one row per executed trade: setup, selection, entry, levels, exits, gross and illustrative net P&L, journal match |
| `trade_entry_conditions.csv` | every entry condition of every trade with its numbers, rule id, approval status and result |
| `trade_exits_detailed.csv` | one row per exit leg with the raw 1-minute exit bar |
| `manual_journal_comparison.csv` | the 190 manual journal rows and every extra automated trade, with the match class and the explanation of each mismatch |
| `strategy_performance.csv` | per-strategy and total performance |
| `NIFTY_Daily_Trade_Verification.xlsx` | all of the above in one workbook with review columns |
| `daily/` | one Markdown journal per evaluable session |
| `charts/` | one SVG chart per executed trade on the real candles |
| `configuration_snapshot.json` | every setting used, with the provisional PDR assumptions labelled |
| `independent_audit.md` | independent re-implementation and file-integrity audit |
| `comparison_vs_phase30.csv` | per-strategy comparison with Phase 3.0 |
| `comparison_vs_phase30_by_day.csv` | every session whose trades changed, with the explanation |
| `manual_pdr_rows_phase30_vs_phase35.csv` | the PDR (and disputed) journal rows under both runs |
| `engine_contribution.csv` | signals, valid signals and trades contributed by each of the five engines |
| `all_strategy_signals.csv / ignored_signals.csv / rejected_signals.csv / candle_analysis.csv / manual_verification_issues.csv / manual_journal_normalized.csv` | supporting detail (Phase 3.2 framework) |
| `data_provenance.json / build_counts.json / independent_audit_results.json / before_snapshot.json` | hashes of the data and code used, counts, machine-readable audit results, hashes recorded before the first Phase 3.5 edit |

All P&L is synthetic index-point P&L x quantity. The PDR pattern thresholds and the open-above-zone requirement are provisional research assumptions, not approved by the strategy author.
