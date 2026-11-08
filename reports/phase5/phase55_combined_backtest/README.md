# Phase 5.5 - complete five-strategy backtest

> SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill).

Three configurations were run independently through the unchanged Phase 3.6 controller and exit policy (only the engine factory differs, swapped at run time; no source file edited):

|  | configuration | id | signals | trades | gross Rs | net Rs (Rs 70, 0 slip) | net Rs (Rs 70, 1.0 slip) |
|---|---|---|---|---|---|---|---|
| A | A - frozen Phase 3.6 | FROZEN-PHASE36-42cea2600bd4 | 1083 | 196 | 297,765 | 284,045 | 131,165 |
| B | B - Phase 5.3 author-corrected | PHASE55-B-a3ca4d04dd11 | 1109 | 188 | 258,550 | 245,390 | 98,750 |
| C | C - B + ORB gap crossing | PHASE55-C-144ceb6b28b1 | 1112 | 190 | 250,946 | 237,646 | 89,446 |

* **Baseline:** configuration A reproduces Phase 3.6 exactly (196 trades, 1,083 signals, identical gross P&L) and, on 2022-2025, the Phase 4 window-B backtest (609 trades).
* **B and C rest on PROVISIONAL conventions** (see `configuration_manifest.json`): none is verified by the strategy author. C is B plus the isolated ORB Gap candle-crossing candidate; the DMA-versus-EMA question of the rulebook stays unresolved.
* **No configuration is selected or approved;** no parameter was tuned.

## Files

`configuration_manifest.json`, `signal_validation.md`, `combined_backtest_summary.md`, `entry_exit_execution_audit.md`, `cross_configuration_comparison.md`, `independent_audit.md`, `all_executed_trades.csv`, `all_trade_legs.csv`, `strategy_performance.csv`, `strategy_signal_funnel.csv`, `monthly_performance.csv`, `annual_performance.csv`, `cost_sensitivity.csv`, `intrabar_ambiguities.csv`, `Combined_Strategy_Backtest.xlsx`, `daily/`, `charts/`; supporting: `all_confirmed_signals.csv`, `signal_differences.csv`, `failed_entry_checks.csv`, `trade_differences_between_configurations.csv`, `multi_year_trades.csv`, `multi_year_by_year.csv`, `phase55_state.json`, `before_snapshot.json`.

## Reproduce

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase55_snapshot.py --snapshot      # baseline hashes (before any change)
python scripts/phase55_run.py                     # A, B, C: signals, controller, exits, costs, robustness window
python scripts/phase55_independent_audit.py
python scripts/phase55_docs.py --tests "..." --ruff "..."
python scripts/phase55_snapshot.py --verify
```
