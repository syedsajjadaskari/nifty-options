# Phase 7.1 - global EMA rule, IRF validation, PDR/PDS reconciliation and five-strategy backtest

**Written for:** the strategy owner. Research only; nothing selected or activated; no paper-trading or frozen file changed; nothing committed, staged or pushed. **Start with `FINAL_PHASE71_RESEARCH_REPORT.md` (answers to the 40 questions).**

## What was done (priority order)
0. **Universal 27-point EMA clarification** - source audit, five readings in one shared component, impact on all five strategies, 27 vs 28, ORB conflict: `latest_author_clarification.md`, `universal_27_point_ema_rule_audit.md`, `ema_*.csv`.
1. **IRF Method 2 Level-A invalidation** (persistent vs permanent vs re-arm): `irf_method2_level_a_invalidation.csv`, `irf_method_comparison.csv`.
2. **3 Nov entry-time discrepancy** - resolved as a data-feed effect; close-below-B candidates (diagnostic): `irf_method2_timing_audit.md`.
3. **November 2026 data** retrieved (new raw namespace `data/raw/phase71_5paisa_nov2026/`, processed `data/phase71/`) and every dated IRF example reconstructed: `november_2026_example_reconstruction.md`, `charts/EX_*`.
4. **PDR / PDS**: 215 delayed cases explained, first-vs-second confirmation, candle-strength comparison: `pdr_215_delayed_cases.csv`, `pdr_first_vs_second_confirmation.csv`, `pds_confirmation_comparison.csv`, `candle_strength_reference_comparison.csv`.
5. **Five-strategy backtest of 18 predeclared configurations on both windows** (frozen controller): `configuration_comparison.md`, `full_five_strategy_backtest.csv`, `strategy_win_rates.csv`, `all_executed_trades.csv`, `all_trade_legs.csv`, `all_daily_signals.csv`, monthly / annual / cost files, journal reconciliation files and `mismatch_root_causes.md`.
Verification: `independent_audit.md`, `reviewer_findings.md`, `preservation_verification.md`, `Phase71_Final_Strategy_Verification.xlsx`; charts in `charts/` (subfolders per purpose), per-day files in `daily/` (window A).

## Key numbers (window A 2025-09..2026-08 | window B 2022-09..2025-08; gross win rate, PF, gross Rs)
| cfg | win | trades | win% | PF | gross pts | gross Rs | net Rs (70/trade) | max DD Rs |
|---|---|---|---|---|---|---|---|---|
| A | A | 196 | 59.69 | 1.269 | 763.5 | 297765.0 | 284045.0 | 133450.0 |
| A | B | 609 | 57.8 | 1.136 | 1306.15 | 509398.0 | 466768.0 | 194503.0 |
| B | A | 190 | 58.42 | 1.212 | 594.5 | 231855.0 | 218555.0 | 107866.0 |
| B | B | 614 | 57.98 | 1.151 | 1449.17 | 565178.0 | 522198.0 | 316898.0 |
| C | A | 190 | 58.42 | 1.212 | 594.5 | 231855.0 | 218555.0 | 107866.0 |
| C | B | 614 | 57.98 | 1.151 | 1449.17 | 565178.0 | 522198.0 | 316898.0 |
| D | A | 175 | 56.57 | 1.101 | 289.5 | 112905.0 | 100655.0 | 104421.0 |
| D | B | 543 | 57.83 | 1.127 | 1095.95 | 427420.0 | 389410.0 | 311826.0 |
| E | A | 145 | 55.86 | 1.05 | 135.5 | 52845.0 | 42695.0 | 124671.0 |
| E | B | 491 | 56.42 | 1.066 | 579.55 | 226024.0 | 191654.0 | 383163.0 |
| F | A | 33 | 72.73 | 2.38 | 429.0 | 167310.0 | 165000.0 | 39210.0 |
| F | B | 131 | 54.96 | 0.981 | -15.4 | -6006.0 | -15176.0 | 169387.0 |
| K | A | 143 | 55.94 | 1.047 | 127.0 | 49530.0 | 39520.0 | 124671.0 |
| K | B | 486 | 56.58 | 1.074 | 629.22 | 245398.0 | 211378.0 | 373134.0 |
| L | A | 184 | 57.61 | 1.168 | 473.0 | 184470.0 | 171590.0 | 116066.0 |
| L | B | 588 | 58.16 | 1.163 | 1484.15 | 578818.0 | 537658.0 | 322471.0 |

Reproduce: `python scripts/phase71_fetch_nov2026.py` (read-only fetch, already done) -> `scripts/phase71_irf.py` -> `scripts/phase71_run.py portfolio A` and `... B` -> `scripts/phase71_tables.py` -> `scripts/phase71_derived.py` -> `scripts/phase71_audit.py` -> `scripts/phase71_charts.py` -> `scripts/phase71_docs.py` -> `scripts/phase71_preserve.py`.
