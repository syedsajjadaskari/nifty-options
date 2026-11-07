# Phase 5.0 - BANKNIFTY and SENSEX cross-index backtest with option-execution feasibility

> HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.

Stopped after Phase 5.0 as instructed: no option paper trading, no live orders, nothing committed or pushed.

| file / directory | what it is |
|---|---|
| data_discovery.md | instrument identification, API probes, sources, licensing, vendor overlap |
| data_quality_report.md | coverage, exclusions, calendar, closing-auction evidence, checks, confidence tiers |
| banknifty/banknifty_backtest_summary.md, sensex/sensex_backtest_summary.md | index-point results per index |
| comparison/cross_index_comparison.md (copy at root) | NIFTY vs BANKNIFTY vs SENSEX |
| options_feasibility/option_data_availability.md, option_contract_selection_decisions.md, option_probe_results.json | whether option premiums are obtainable; owner decisions |
| <index>/trade_level_signals.csv, daily_summary.csv, strategy_performance.csv, entry_explanations.csv, exit_explanations.csv, cost_sensitivity.csv | compiled tables (window_id first column) |
| <index>/<INDEX>_Daily_Verification.xlsx | workbook written from the CSV files |
| <index>/daily/, charts/ | one journal per evaluated session; one chart per trade |
| configuration_snapshot.json, data_provenance.json, before_snapshot.json | frozen configuration, sources and hashes, the NIFTY before-state |
| independent_audit.md, independent_audit_results.json, _sample_review.md | audit |

## Reproduce (tested commands)

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase5_discover.py                       # resolve the instruments from the broker master + small API probes
python scripts/phase5_fetch.py --index BANKNIFTY --source 5paisa --minutes --daily
python scripts/phase5_fetch.py --index SENSEX --source 5paisa --minutes --daily
python scripts/phase5_fetch.py --index BANKNIFTY --source secondary   # 2018 / 2019 exploratory source
python scripts/phase5_fetch.py --index SENSEX --source secondary
python scripts/phase5_build_data.py                     # processed Parquet (ZSTD), calendars, quality tables, overlaps
python scripts/phase5_run.py --index BANKNIFTY --strategy-config phase36-frozen --window all
python scripts/phase5_run.py --index SENSEX --strategy-config phase36-frozen --window all
python scripts/phase5_compare.py                        # per-index tables, cross-index comparison, workbooks
python scripts/phase5_options_probe.py             # option-data availability probe
python scripts/phase5_independent_audit.py && python scripts/phase5_docs.py --tests "..." --ruff "..."
```
