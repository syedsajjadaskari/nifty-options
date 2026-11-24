# Independent audit (Phase 7.1)

## 1. Second implementations (no shared logic with the production modules) - `scripts/phase71_audit.py`
**Method 2 variants.** `irf_cycles.m2_cycles` (state machine) versus an index-search implementation (`m2_independent`, `m2_independent_bc`: no state machine) on every evaluable session of both windows (982 sessions) for nine variants (M2-A, BEFORE_B, BEFORE_COMPLETION permanent / re-arm, margin 1 / 2 / 5, bearish failure, extra confirming candle). First-cycle mismatches: **{'A': 0, 'B0': 0, 'B': 0, 'B_REARM': 0, 'M1': 0, 'M2': 0, 'M5': 0, 'BEAR': 0, 'EXTRA': 0}**. (A first audit run showed 91 / 131 mismatches for the BEFORE_COMPLETION variants; the cause was a gap in the INDEPENDENT implementation, which only checked the close-below-A window before Level B was marked and between the second breakout and the failure, not between B and the second breakout; the production state machine was right. The audit function was corrected and re-run.)
**Phase 7.0 parity.** On all 1,964 session-method pairs of both windows the first cycle of the new enumerators equals the Phase 7.0 `irf_v3.method1/method2` result (signal time, level, later-cycle count); BEFORE_B equals the Phase 7.0 invalidation variant.
**EMA geometry.** Rebuilt from raw one-minute rows with `pandas.resample` and a recursive `ewm(span=200, adjust=False)` over the same warm-up: 942 baseline window-A signals compared; geometry (|close-EMA|, range clearance) recomputed from raw OHLC: **0 mismatches**; mean |EMA difference| 0.16 points, maximum 17.57 (seed effect early in the series); decisions that would flip at 27 points if the recursive EMA replaced the frozen SMA-seeded EMA: {'MIN_CLOSE': 1, 'MIN_RANGE': 0, 'MAX_CLOSE': 1, 'TARGET_SIDE': 0}.

## 2. Reproduction of the frozen result
Configuration A through the unchanged controller reproduces the saved Phase 6.2 configuration A exactly: window A 196 trades / Rs +297,765, window B 609 / Rs +509,398.

## 3. Test suite and lint
`tests/test_phase71_global_ema.py` (15 tests: boundary and direction behaviour of every EMA reading, 27 vs 28, unavailable EMA, gate wrapper using only the confirming candle's EMA, Phase 7.0 parity of the first cycle, multiple cycles, invalidation vs the completing candle, re-arm, margin / bearish / extra-confirmation candidates, November quality checker) plus the Phase 7.0 suite. Full-suite result in `preservation_verification.md`.

## 4. Checks listed in the brief
| Check | Result |
|---|---|
| Historical data validation (November store) | `november_2026_data_quality.csv`: 375 in-session rows per full session, 0 missing minutes, 0 duplicates, 0 OHLC violations |
| Candle alignment | five-minute candles from complete five-row groups only; bar-start labels (verified Phase 2) |
| EMA warm-up | frozen contexts carry the warm-up months; unavailable EMA is never a rejection (tested) |
| No look-ahead | each decision uses the confirming candle's own EMA and OHLC; signals from the Phase 7.0 modules are causal (1,031 signals truncation-tested in 7.0); the adapter emits record timestamps = candle end |
| Shared arbitration / second-trade eligibility | the frozen controller is unchanged; configuration A reproduces Phase 6.2 exactly |
| Execution and P&L | the frozen exit policy reconstructs fills from one-minute bars; reconciliations in `trade_set_attribution.csv`; independent reviewer recomputation in `reviewer_findings.md` |
| Journal recount | 190 rows, Summary 189, 5 weekend rows, SHA-256 unchanged (`mismatch_root_causes.md`) |
| Chart correctness | rejected trades drawn as NOT EXECUTED with dashed outlines; executed charts carry the EMA path, levels and both leg exits |

## 5. Limits
* The EMA gate is a post-hoc filter on emitted signals (as the Phase 6.5 strength gate); IRF V3 emits every completed cycle so a rejected cycle can release a later one - an inference, not an author decision.
* Edge cases of the research options (not used by any portfolio configuration): with `extra_confirmation` an extra candle closing between B and A is not tested for invalidation; with `bearish_failure` + BEFORE_COMPLETION a green candle closing below both B and A invalidates instead of being ignored.
* The second implementations were written by the same author; a separate read-only reviewer was also run (`reviewer_findings.md`).
* Window B uses the Phase 4 5paisa store; ORB V2 conventions remain PROVISIONAL (Phase 6.0/6.5).
