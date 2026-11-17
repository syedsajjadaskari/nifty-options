# Phase 6.2 - combined five-strategy backtest

**Written for:** the strategy owner. Research only; synthetic index P&L; nothing selected, optimised, committed or traded.

Start with `combined_backtest_summary.md`, then `configuration_comparison.md`. New combined configuration id: `phase62-irfv2-orbv2-combined` (configuration C), kept separate from the frozen configurations; its ORB V2 component is the provisional ORB-V2-A (no owner selection exists; no relaxed variant was combined).

Files: `configuration_manifest.json`, `all_signals.csv`, `all_executed_trades.csv`, `all_trade_legs.csv`, `strategy_performance.csv`, `monthly_performance.csv`, `annual_performance.csv`, `cost_sensitivity.csv`, `intrabar_ambiguities.csv`, `strategy_signal_funnel.csv` (standalone signal funnels), `trade_differences_between_configurations.csv`, `orb_v2_rejections_config_c.csv`, `orb_v2_integration_checks.csv`, `execution_audit_*`, `Combined_Five_Strategy_Backtest.xlsx`, `daily/` (one report per evaluable session of configuration C), `charts/` (one chart per executed C trade; the 2022-25 robustness window has ledgers and tables but no per-trade charts).

Reproduce: `python scripts/phase62_run.py && python scripts/phase63_run.py && python scripts/phase62_daily_charts.py && python scripts/phase62_audit.py && python scripts/phase62_docs.py`.