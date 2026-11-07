# Phase 5.3 - owner-approved author corrections

> Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

Stopped after Phase 5.3: no profitability backtest, nothing committed or pushed, no paper or live orders. The frozen Phase 3.6 default is unchanged; the new configuration is `phase53-author-corrected`.

## Confirmed signals: Phase 3.6 versus Phase 5.3 (2025-09-01..2026-08-31, signal level)

| strategy | Phase 3.6 | Phase 5.3 | earlier | later | new | removed | same time, level changed | unchanged |
|---|---|---|---|---|---|---|---|---|
| IRF | 874 | 786 | 128 | 85 | 144 | 232 | 22 | 407 |
| ORB | 53 | 53 | 0 | 0 | 0 | 0 | 0 | 53 |
| PDR | 87 | 147 | 64 | 0 | 60 | 0 | 0 | 23 |
| PDS | 57 | 111 | 6 | 4 | 69 | 15 | 0 | 32 |
| RF | 12 | 12 | 0 | 0 | 0 | 0 | 0 | 12 |
| **total** | 1083 | 1109 |  |  |  |  |  |  |

A change in the count is not an improvement. PDR and PDS counts rise because a looser confirmation lets the setup re-arm more often; the controller still takes the first valid signal.

## Headline results

| item | result |
|---|---|
| IRF Method 2A signals using a different reference (first red candle LOW) | 290 (26 same time with a new level, 122 earlier, 23 later, 119 new); 36 removed; 8 unchanged |
| IRF signals failing the 28-point rule | 167 of 874 Phase 3.6 signals (30 of the 115 executed trades); net IRF confirmed signals 874 -> 745 with the rule alone |
| PDR first signals moved earlier | 21 sessions earlier, 3 newly signalled (of 42 armed setups) |
| PDS first signals moved earlier | 11 sessions earlier (of 25 armed sessions with a retest and a red candle); of the 20 sessions: 10 newly eligible, 5 already eligible, 5 remain weak (Method 3) |
| handwritten observations | 42 rows: 5 reconciled, 2 partly reconciled, 2 rule applied without an observable expectation; statuses {'NOT_RECONCILED_METHOD_OUT_OF_SCOPE': 3, 'NOT_RECONCILED_RETEST_CONVENTION': 1, 'UNRESOLVED_MISSING_DEFINITION': 12, 'NOT_IN_SCOPE_UNCHANGED': 10, 'NOT_ADDRESSED_PENDING_OWNER': 1, 'NOT_RECONCILED': 1, 'RECONCILED_DIRECTION': 1, 'RECONCILED': 4, 'PARTIAL_REJECTED_NOT_DELAYED': 2, 'PENDING_OWNER_DEFINITION': 3, 'APPLIED_NO_OBSERVABLE_EXPECTATION': 2, 'VARIANT_AVAILABLE_NOT_ACTIVE': 1, 'NOT_RECONCILED_CONFLICT_WITH_SOURCE_RULE': 1} |
| ORB disputed dates still unresolved | 13 of 13 (no ORB signal ever existed; definitions listed) |
| IRF day's low | PENDING_OWNER_DEFINITION - not applied; eight readings measured |

## Files

`approved_author_decisions.md`, `rule_authority_matrix.md`, `irf_first_red_low_implementation.md`, `irf_ema_28_implementation.md`, `pdr_first_eligible_implementation.md`, `pds_first_eligible_implementation.md`, `orb_unresolved_entries.md`, `irf_day_low_unresolved.md`, `source_to_code_traceability.md`, `signal_comparison.csv`, `dated_author_corrections.csv`, `remaining_owner_decisions.md`, `independent_audit.md`, `Phase53_Author_Corrections_Verification.xlsx`, `daily/`, `charts/`; supporting: `all_confirmed_signals.csv`, `daily_first_signal_comparison.csv`, `irf_first_red_low_comparison.csv`, `irf_ema_signals.csv`, `irf_ema_rejections.csv`, `pdr_first_eligible_setups.csv`, `pds_first_eligible_setups.csv`, `pds_20_sessions.csv`, `orb_unresolved_entries.csv`, `irf_day_low_diagnostics.csv`, `signal_counts.json`, `before_snapshot.json`.

## Reproduce

```
cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate
python scripts/phase53_snapshot.py --snapshot       # baseline hashes (taken before any change)
python scripts/phase53_run.py --list               # the selectable configurations
python scripts/phase53_run.py                      # signal-only comparison + diagnostics + day reports + workbook
python scripts/phase53_independent_audit.py
python scripts/phase53_docs.py --tests "..." --ruff "..."
python scripts/phase53_snapshot.py --verify
```
