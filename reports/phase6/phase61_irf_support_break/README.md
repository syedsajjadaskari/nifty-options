# Phase 6.1 - IRF-V2-SUPPORT-BREAK

**Written for:** the strategy owner. Signal level only (no fills or P&L here). Primary window 2025-09-01..2026-08-31; the 2022-25 window is in the CSVs.

* Confirmed IRF signals (all times): frozen Phase 3.6 874, Phase 5.3 786, IRF V2 786; V2 == Phase 5.3 exactly (both windows).
* Frozen -> V2: unchanged 447, same time but different support level 36, removed 391, added 303. Removed by cause: {'SUPPORT_REFERENCE_CHANGED (first red candle low)': 127, 'EMA_28_CLEARANCE_REJECTED': 126, 'ATTEMPT_LIFECYCLE / DOWNSTREAM': 138}; added: {'SUPPORT_REFERENCE_CHANGED': 228, 'ATTEMPT_LIFECYCLE / DOWNSTREAM': 75}. Method 2A first-signal shifts per session: {'EARLIER': 243, 'LATER': 59}.
* EMA-28: 514 candidate confirmations rejected (primary); on the 786 confirmed signals the EMA lies between the entry reference and Target 1 on 0 (never, because the 28-point range clearance keeps it beyond 28 points while T1 is 27).
* Day's-low restriction: NOT applied; a causal running-low diagnostic is recorded on every signal (3 signals close below the prior running low).
* Independent audit: {'A': {'sessions': 247, 'independent_method2a_signals': 168, 'engine_method2a_signals': 168, 'sessions_with_mismatch': 0}, 'B': {'sessions': 738, 'independent_method2a_signals': 477, 'engine_method2a_signals': 477, 'sessions_with_mismatch': 0}}.

Files: `irf_source_reconstruction.md`, `irf_support_break_rule.md`, `irf_method_scope.md`, `irf_reference_candle_audit.csv` (every Method 2 attempt), `irf_before_after_signals.csv`, `irf_handwritten_cases.csv`, `irf_ema_28_diagnostics.csv`, `audit_mismatches.csv`, `independent_audit.md`, `IRF_V2_Verification.xlsx`, `charts/` (dates where Method 2A changed and handwritten dates).