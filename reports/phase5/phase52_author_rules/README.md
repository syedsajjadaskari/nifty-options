# Phase 5.2 - the author's latest clarifications

> Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules.

Stopped after Phase 5.2: no revised profitability backtest, nothing committed or pushed, no paper trading, no live orders.

## Result

| item | result |
|---|---|
| PDR entries shifted to the first eligible candle | 0 - no late entry relative to the preserved proposals (retest-candle convention PDR-A07, numeric thresholds); 33 sessions with a first PDR signal. The author's own example candles are NOT eligible under them (see the sensitivity table: looser readings would move many entries) |
| PDS entries shifted to the first eligible candle | 0 - no late entry relative to the preserved quality rule (PDS-M-001); 23 sessions with a first PDS signal; co-confirmed methods now recorded (0 occur); later strong red candles after a weak first red are listed |
| IRF first red candle | candidates only (level undefined); low: 486 signal changes (earlier/later/added/removed), body low: 598 |
| IRF day's low | source statement not found in the documents; 8 readings measured; none activated (D2 touches 3 signals, D6 352, D7 227, D8 95) |
| IRF 28-point EMA | unresolved; readings measured (E1 70 signals / 12 executed; 27 vs 28 differ on 5) |
| Missing ORB entries explained | 13 of 13 (no ORB signal existed; causes: {'METHOD2_TRENDLINE': 2, 'LEVEL_CONSTRUCTION (no previous-day level broken; Method 2 inner level undefined in the source)': 6, 'STRONG_CANDLE_THRESHOLD': 3, 'EMA_REQUIREMENT': 2}) |
| confirmed signals (frozen / approved / ORB colour / IRF low / IRF body low) | 1083 / 1083 / 1080 / 1148 / 1234 |

## Files

`author_call_clarifications.md`, `rule_authority_matrix.md`, `pdr_first_eligible_audit.md`, `pds_first_eligible_audit.md`, `irf_first_red_candle_audit.md`, `irf_ema_28_point_audit.md`, `irf_day_low_audit.md`, `orb_missing_signal_audit.md`, `before_after_signals.csv`, `dated_corrections_comparison.csv`, `remaining_owner_decisions.md`, `source_to_code_traceability.md`, `independent_audit.md`, `Phase52_Trade_Corrections_Verification.xlsx`, `daily/` (one report per Phase 5.1 date), `charts/`; supporting: `all_confirmed_signals.csv`, `daily_first_signal_comparison.csv`, `irf_signal_diagnostics.csv`, `irf_first_red_comparison.csv`, `pdr/pds_first_eligible_setups.csv`, `orb_missing_signal_audit.csv`, `signal_counts.json`, `before_snapshot.json`.

## Reproduce

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase52_snapshot.py --snapshot       # baseline hashes (taken before any change)
python scripts/phase52_run.py --list               # the selectable configurations
python scripts/phase52_run.py                      # signal-only comparison (all configurations) + diagnostics + day reports + workbook
python scripts/phase52_independent_audit.py
python scripts/phase52_docs.py --tests "..." --ruff "..."
python scripts/phase52_snapshot.py --verify
```
