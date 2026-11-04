# Phase 3.1 - confirmed software defects

Only objectively provable defects are listed. A difference between the automated result and the manual journal is **not** a defect, and no rule was changed because of it.

**Result: one defect confirmed (latent, non-default configuration only), fixed with a regression test. No defect found in any default or Phase 3.0 scenario configuration. No Phase 3.0 number changes.**

## D-IRF-1 - the Method 1 window variant blinds Method 2 (FIXED)

| item | detail |
|---|---|
| Found by | the IRF/RF source-to-code auditor (Appendix A of `source_to_code_audit.md`), confirmed independently by running the failing input |
| Code | `src/nifty_trading/strategies/irf.py`, `_scan` and `_m2_step` |
| Source | IRF guide p.7 step 3 ("Price extends further upward") and step 4 (red candle during the extension). These Method 2 steps do not depend on how many candles Method 1 may wait (the p.14 "next or following candle" reading is a labelled research variant, `m1_max_candles_after_breakout`) |
| Defect | `win = m1_max_candles_after_breakout` was also used as the first candle at which the Method 2 state machine ran (`if i - att.b >= win`). With `win >= 2` the extension and red-candle bookkeeping for candles `b+1 ... b+win-1` was skipped, so a valid Method 2A (or 2B) could be lost although no Method 1 had occurred, and a later extension could be mis-recorded |
| Evidence (failing input, IRH = 100) | candles `[(95,100,90,98), (98,104,97,103), (103,106,102,105), (105,105.5,101,102), (102,103,101.5,102.5), (102.5,103,101.2,102.8), (102.8,103,100,100.5)]`: default and window 1 produce Method 2A at the 09:45 candle (close 100.5); window 2 and 3 produced no signal |
| Regression test | `tests/test_phase2_irf.py::test_regression_d_irf_1_the_method_1_window_variant_must_not_blind_method_2_to_the_extension` (windows 1, 2, 3). Written first: windows 2 and 3 failed, window 1 passed. All three pass after the fix |
| Minimal correction | the Method 2 machine now runs for every candle after the breakout (extension and red-candle bookkeeping); only the *confirmation* (and the `SETUP_DETECTED -> WAITING_FOR_CONFIRMATION` transition) is still held back while Method 1 may fire (`may_confirm=i - att.b >= win`). Nothing else changed: no threshold, no parameter default |
| Tests after | `ruff` clean; full suite 409 passed |

### Before / after comparison (all IRF engine records, 247 sessions; script output kept in the scratch directory, hashes of the record lists)

| IRF configuration | records before | records after | confirmed before -> after | verdict |
|---|---|---|---|---|
| shipped default (window 1) | 1041 | 1041 | 874 -> 874 | **identical** (hash `f3d093128697` both) |
| Phase 3.0 controller setting (`max_signals_per_session=99`) | 1041 | 1041 | 874 -> 874 | **identical** |
| window 2 (p.14 variant) | 1027 | 1043 | 855 -> 877 | changed: +19 Method 2A, +7 Method 2B, -1 Method 2A, -3 Method 2B (net +22 confirmed) plus incomplete-setup relabelling |
| window 3 | 1005 | 1041 | 829 -> 875 | changed: +47 / +16 Method 2A/2B, -8 / -9 |
| window 2 + 6-candle expiry | 1485 | 1489 | 634 -> 647 | changed |

### Impact

* **Phase 3.0 ledgers (baseline, ema_structure, pdr_shelf, sl40): none.** Every Phase 3.0 scenario uses window 1 (`scripts/phase3_run_backtests.py` only prints it); the sha256 of each ledger is unchanged (`phase30_ledger_hashes.json`, checked by `test_phase30_ledgers_are_untouched`).
* **Phase 3.1 reconciliation: none.** It was run on the default window; the signal record lists are identical, so no output was regenerated.
* **Earlier Phase 2/2.1 documents:** the "window 2" variant counts printed by `scripts/phase2_signal_counts.py` and `scripts/phase21_decisions.py` (for example Method 2A 215 -> 197) were computed with the defective code. They are historical and were **not** overwritten; they will be different if those scripts are rerun. Nothing in the approved rules or Phase 3.0 depends on them.
* This is a correctness repair of a research variant, not a profit-driven change; the variant is not adopted.

## Candidate defects examined and NOT confirmed

| id | what | why it is not classed as a defect |
|---|---|---|
| C-PDS-M3 | PDS Method 3 "small support near the zone" has no lower bound (13 of 33 raw signals use a support more than 10 points below the zone floor; one 118 points below). Source p.5 says "near the zone" but defines neither size, distance nor the number of candles; the guide's own "items to define" list leaves the support size open | "near" has no number, so any bound would be an invented parameter. Recorded as owner decision O-6; the code was **not** changed |
| C-PDR-P6 | PDR enters on the next green candle after a zone touch even when price has closed below the zone floor (26 of 61 first signals) | no sentence of the guide says the zone must hold; interpretation difference, owner decision O-3 |
| C-IRF-M2-004 | IRF-M2-004 is registered as implemented, but a breakout followed by a close **below IRL** neither fires Method 1 (literal reading, "inside the range") nor ends the Method 2 attempt (seven cases a year) | the close-below-IRL edge is itself unresolved in the source (IRF-M1-003); counts only, no change |
| C-RF-P1 | the audit could not reproduce "5 RF trades" from the shipped default (2 signals) | not a defect: the Phase 3.0 baseline uses a different trend mode; no code contradicts the source |

## Things checked and found correct

* Confirmed-swing and pivot helpers use only candles that have closed (`j <= i-k-1`); the 5-minute EMA is causal; every signal engine's confirmed signals are identical when the session is truncated at the signal candle (zero mismatches in all replays).
* Candle labelling: 09:15 candle usable at 09:20; the fill is the next 1-minute open (67 journal rows confirm the start-of-candle label).
* The same-minute collision handling and the two collision policies behave as documented (`tests/test_phase23_day_controller.py`, 54 tests).

## Test-suite note

One run of the full suite during this phase reported `test_the_yaml_registry_is_in_sync_with_the_python_registry` failing (1 failed, 385 passed). The test passes on rerun, in isolation and in the final full run (409 passed); the registry files had been modified by concurrent documentation updates in the working tree at that moment. The cause was not investigated further; the final state is green.
