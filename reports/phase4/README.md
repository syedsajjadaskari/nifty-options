# Phase 4 - multi-year historical validation of the frozen Phase 3.6 strategy

**Written for:** the strategy owner. **Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.

The Phase 3.6 configuration was frozen (`strategy_freeze.json`, id `FROZEN-PHASE36-42cea2600bd4`) and run, unchanged, on four additional historical windows. Nothing was tuned, no window was chosen after seeing results, and loss-making periods are reported.

## Rerun commands (macOS terminal)

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase4_run.py --strategy-config phase36-frozen --window three-year     # Window B, 2022-09-01..2025-08-31
python scripts/phase4_run.py --strategy-config phase36-frozen --window 2018           # Window C (exploratory)
python scripts/phase4_run.py --strategy-config phase36-frozen --window 2019           # Window D (5paisa partial year + secondary full year)
python scripts/phase4_run.py --strategy-config phase36-frozen --window all            # everything + comparison, robustness, workbook
python scripts/phase4_run.py --help
```

`--strategy-config phase36-frozen` is the only accepted value: the run is **refused** if any strategy, controller, execution or session-construction file or any parameter differs from the freeze record. `--window custom --window-id X --start D --end D --minute-source 5paisa|secondary` runs any other range the processed data covers.

Data preparation (needs the broker session; not needed to rerun the backtests): `python scripts/phase4_fetch_5paisa.py --probe-empty --daily --minutes`, `python scripts/phase4_fetch_secondary.py --with-2026`, `python scripts/phase4_build_data.py`. Freeze check: `python scripts/phase4_freeze.py`. Independent audit: `python scripts/phase4_independent_audit.py`. This report: `python scripts/phase4_docs.py --tests "..." --ruff "..."`.

## Headline

| period | status | confidence | trades | gross Rs (390 units) | net Rs (illustrative) | profit factor | max drawdown Rs |
|---|---|---|---|---|---|---|---|
| C_2018 | EXPLORATORY | EXPLORATORY_UNVERIFIABLE | 185 | -102,063 | -266,713 | 0.9074 | 157,287 |
| D_2019_SECONDARY | EXPLORATORY | EXPLORATORY_UNVERIFIABLE | 182 | 301,314 | 139,334 | 1.3565 | 99,508 |
| D_2019_5PAISA_PARTIAL | PARTIAL_YEAR | LOW | 149 | 352,609 | 219,999 | 1.5356 | 74,246 |
| B1_2022_23 | DATA_VALIDATED | MODERATE | 198 | 288,454 | 112,234 | 1.268 | 188,341 |
| B2_2023_24 | DATA_VALIDATED | MODERATE | 219 | -3,851 | -198,761 | 0.9971 | 186,313 |
| B3_2024_25 | DATA_VALIDATED | MODERATE | 192 | 224,796 | 53,916 | 1.2213 | 173,706 |
| B_2022_25 | DATA_VALIDATED | MODERATE | 609 | 509,398 | -32,612 | 1.1492 | 188,341 |
| A_2025_26 | REFERENCE | HIGH | 196 | 297,765 | 123,325 | 1.2839 | 130,650 |

**Status labels:** `DATA_VALIDATED` = the data window passed the quality gate (it says nothing about the strategy); `EXPLORATORY` = a single vendor that cannot be checked against another; `PARTIAL_YEAR`; `VENDOR_SENSITIVITY`; `REFERENCE` = the unchanged Phase 3.6 result.

Trade IDs are `YYYYMMDD-n-STRATEGY` within a window; the composite key `window_id|trade_id` is unique across the workbook; every trade row records the minute-source id, the daily-source id, the SHA-256 of its processed partition and of the raw source file(s).

| file | content |
|---|---|
| `README.md` | this file |
| `strategy_freeze.json` | the frozen Phase 3.6 configuration: id, source snapshot, file hashes, parameters, costs, unresolved rules, regression check |
| `data_source_discovery.md` | what each source can supply, probe results, secondary-source provenance, overlap audit, contract sizes |
| `data_quality_by_year.md` | validation of every window, derived calendar, exclusions, confidence tiers |
| `historical_coverage.csv` | coverage per window and source |
| `three_year_backtest_summary.md` | Window B and its three annual slices, vendor sensitivity |
| `2018_backtest_summary.md` | Window C (exploratory) |
| `2019_backtest_summary.md` | Window D (5paisa partial year and secondary full year) |
| `annual_comparison.csv` | every metric of section 9 for every period, with status and confidence |
| `strategy_comparison.csv` | per period and strategy |
| `cost_sensitivity.csv` | cost x slippage grid per period |
| `drawdown_analysis.md` | drawdowns with dates and hypothetical-capital multiples |
| `robustness_report.md` | the ten robustness diagnostics |
| `paper_trading_readiness.md` | readiness assessment (no implementation) |
| `independent_audit.md` | independent re-implementation, fresh reviewer, file-integrity proof |
| `NIFTY_MultiYear_Backtest_Verification.xlsx` | all tables, all trades, session quality (written from the CSV files) |
| `daily/<window>/YYYY-MM/` | one journal per evaluable session |
| `charts/<window>/` | one chart per executed trade |
| `windows/<window>/` | per-window CSVs (trades, entry conditions, exits, signals, rejected, issues, candle analysis), configuration and provenance |
| `data/` | per-session quality tables, coverage, derived-calendar summaries, overlap audits (by day and month), probe log |
| `robustness_*.csv, vendor_sensitivity.csv, monthly_pnl_all_windows.csv, session_regimes.csv, regime_definitions.json, coverage_exceptions.csv, not_evaluated_strategy_sessions.csv, all_trades_all_windows.csv` | supporting tables |
| `before_snapshot.json` | hashes of every earlier file recorded before the first Phase 4 edit |
