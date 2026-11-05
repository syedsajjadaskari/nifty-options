# Phase 3.6 - body-based PDR + complete five-strategy backtest

**Written for:** the strategy owner. Start with `backtest_summary.md`.

## Rerun it independently (macOS terminal)

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase36_run.py
```

Equivalent: `python scripts/phase35_run.py --pdr-engine body-based`.
`python scripts/phase35_run.py --help` lists the options: `--pdr-engine revised` (default; the Phase 3.5 wick-ceiling configuration - its meaning is unchanged), `legacy` (Phase 3.0 regression check) and `body-based` (this phase). `--out DIR` changes the output directory; the runner refuses to write the Phase 3.6 results into a Phase 3.5 directory or into any earlier phase's directory.

Then, optionally (in this order): `python scripts/phase36_pdr_compare.py` (PDR signal comparison, sensitivities, source-chart validation), `python scripts/phase36_independent_audit.py`, `python scripts/phase36_docs.py --tests "..." --ruff "..."` (regenerates the reports).

The run takes about a minute; it reads only `data/processed/` and `docs/trading journal/` and writes only inside `reports/phase3/phase36_*`. Configuration id: `CFG-phase36_body_based-866f954e55`; PDR configuration id: `A` / profile `RESEARCH_DEFAULT` (recorded on every signal).

| file | content |
|---|---|
| `README.md` | this file |
| `backtest_summary.md` | results, the Phase 3.0 / 3.5 / 3.6 comparison, monthly P&L - start here |
| `pdr_body_zone_rule_audit.md` | before-change audit of `pdr_revised.py`, the new body-based rules, effect |
| `pdr_pattern_classification.md` | the three patterns, the provisional thresholds, ambiguous candles |
| `pdr_source_chart_validation.md` | the guide's dated examples against the body-based rules |
| `old_vs_new_pdr_signals.csv` | every Phase 3.5 PDR signal and every new Phase 3.6 signal with tags and reasons; lenient-only candles as AMBIGUOUS |
| `pdr_daily_zone_comparison.csv` | every session: wick vs body zone, opening test, signals per phase, day difference |
| `pdr_sensitivity_counts.csv` | PDR signal counts under each unresolved setting (counts only) |
| `source_chart_validation.csv / pdr_signal_statistics.json / pdr_body_rules.csv` | supporting data |
| `all_trades_detailed.csv` | one row per executed trade (stable Trade ID `YYYYMMDD-n-STRATEGY`) |
| `entry_condition_details.csv` | every entry condition of every trade with its numbers, rule id, approval status, result |
| `exit_details.csv` | one row per exit leg with the raw 1-minute exit bar |
| `daily_summary.csv` | one row per evaluable session (247) |
| `strategy_performance.csv / engine_contribution.csv / monthly_pnl.csv` | performance tables |
| `comparison_3way_by_strategy.csv, comparison_vs_phase35_*.csv, comparison_vs_phase30_*.csv` | Phase 3.0 / 3.5 / 3.6 comparisons, per strategy and per changed session |
| `manual_journal_comparison.csv / manual_pdr_rows_three_phases.csv` | the 190 journal rows + extra automated trades; PDR rows under all three runs |
| `NIFTY_Daily_Trade_Verification.xlsx` | the workbook (review columns blank) |
| `daily/` | one Markdown journal per evaluable session |
| `charts/` | one SVG chart per executed trade on the real candles |
| `configuration_snapshot.json / data_provenance.json` | every setting used (provisional PDR assumptions labelled); hashes of data and code |
| `independent_audit.md` | independent re-implementation, the fresh reviewer's findings, file-integrity proof |
| `before_snapshot.json / independent_audit_results.json / build_counts.json` | hashes recorded before the first Phase 3.6 edit; machine-readable results |

All P&L is synthetic index-point P&L x quantity. Author statements: the previous day's high is considered and a zone drawn (multiple highs connected); wicks are ignored and bodies considered; the session must open strictly above the zone; one good green body OR lower price rejection OR hammer candle is required (no fixed percentage / wick-size threshold is required); the candle should close above the zone. Provisional research assumptions (NOT approved by the author): the numeric thresholds of the three patterns (RESEARCH_DEFAULT, carried from Phase 3.5 for comparability), reading 'body high' as max(open, close), the zone lower boundary (hull of the member bodies), the multiple-body-high cluster parameters, the zero-height policy and the wait policy. No signal is VERIFIED.
