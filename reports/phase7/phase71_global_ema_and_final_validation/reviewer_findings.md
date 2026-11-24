# Independent read-only reviewer - findings and actions (Phase 7.1)

A separate agent (read-only; it created and edited nothing in the repository) read the Phase 7.1 code and outputs, recomputed numbers from the cached runs and raw data, and wrote its own checks (scratch only). Summary of its report and what was done:

| # | Finding | Class | Action |
|---|---|---|---|
| 1 | The EMA-5 gate measured the entry reference at the confirming candle's close, while the diagnostics CSV measured it from the next-bar fill price (15 of 3,618 rows differ: IRF 14, PDS 1; `ema_signal_impact_by_strategy.csv` disagreed with config L's own gate log, e.g. IRF window A 54 vs 53) | CONFIRMED DEFECT (inconsistency) | Fixed: diagnostics now use the confirming candle's close everywhere (causal at signal time, as the audit text already stated); baseline B was re-run for both windows and all dependent tables regenerated |
| 2 | `EmaGateEngine.timing` was declared but never read (`SETUP` silently behaved as `CONFIRMATION`) | CONFIRMED DEFECT (minor) | Field removed; the gate is documented as confirming-candle only. Setup / reference timing remains a diagnostic (`ema_measurement_timing_sensitivity.csv`) |
| 3 | Geometry and evaluation (EMA-1..EMA-5, boundaries, SHORT/LONG signs, EMA inside candle, unavailable EMA, causality of `ema200_5m`, safe invalidation for other consumers) - recomputed for all 3,618 rows, 0 mismatches | NO ISSUE | - |
| 4 | `__getattr__` could recurse if `inner` were unset (copy / pickle) | NO ISSUE (robustness) | Guard added |
| 5 | `irf_cycles` vs Phase 7.0 `irf_v3` modules on 30,000 random sessions: first cycle, later-cycle counts and the BEFORE_B variant identical; the completing failure candle is evaluated before the close-below-A invalidation; re-arm restarts at state A | NO ISSUE | - |
| 6 | Edge cases: with `extra_confirmation` an extra candle closing between B and A is not tested for invalidation; with `bearish_failure` + BEFORE_COMPLETION a green candle below both B and A invalidates instead of being ignored. Neither combination is used by any configuration | AMBIGUITY (edge case) | Documented in `independent_audit.md` |
| 7 | `irf_engine` adapter: signal timestamp = failure candle end for all 633 records, no duplicates, sequential (causal), all executed IRF trades are cycle 1 | NO ISSUE | - |
| 8 | IRF 'signals failing EMA' counts are signal RECORDS (every cycle, both methods, after-13:00 and blocked signals), not trades | DISCLOSURE GAP | Stated in `universal_27_point_ema_rule_audit.md`; a first-cycle-only table added |
| 9 | J60 / J70 / JD wrap IRF V3 although the IRF PDFs contain no body-size rule | DISCLOSURE GAP | Noted in `configuration_comparison.md` |
| 10 | `build_engines()` matches `CONFIGS` (H = PDR-D, G1 = B1, G2 = B2, G3 = C; I1/I2 replace only first-eligible PDS; EMA and strength gates wrap all five engines; no state leakage through the shared ORB object) | NO ISSUE | - |
| 11 | `phase71_tables.py`: metrics, strategy-wise table, one-to-one journal match, DIRECT vs PORTFOLIO attribution sound; the wording 'strict 70-72' for PDR/PDS variants was imprecise (H is 67) | NO ISSUE / cosmetic | Wording now computed from the table |
| 12 | Numbers reproduce: B window A 190 trades / +231,855 / 58.42%; config A matches Phase 6.2 'A' row by row in both windows; C and C2 ledgers identical to B; three changed trades (2026-08-10, 2026-04-28, 2025-12-31) confirmed from raw data | NO ISSUE | - |
| 13 | November spot checks (M1-E2 11 Nov; M2-E4 3 Nov) recomputed from the raw file: match | NO ISSUE | - |
| 14 | The reconstruction text listed only the 6 Nov and 16 Nov Level-A mismatches; 3 Nov is also outside 1 point on the 5paisa feed (-3.85) | DISCLOSURE GAP | Added (feed difference; the secondary feed gives -0.45) |
| 15 | README / final report cited audit, reviewer and preservation files that did not yet exist; Q38 showed 'n/a'; trade counts printed as floats | DISCLOSURE GAP | Files generated; placeholders removed |
| 16 | Claims hygiene: the 27-point statement is treated as unconfirmed everywhere, EMA-0 is default, nothing selected by P&L. Soft spot: the 'journal strict rises 67 -> 71 / 73' narrative | NO ISSUE | Kept explicitly non-selective |

**Reviewer verdict:** implementation sound; the cycle enumerators reproduce Phase 7.0 exactly, the adapter is causal, the EMA gate wraps all five strategies, frozen configuration A reproduces Phase 6.2, the November examples recompute from raw data, and the 27-point statement is treated as unconfirmed throughout. The one inconsistency (EMA-5 entry reference) was fixed before this report was finalised.
