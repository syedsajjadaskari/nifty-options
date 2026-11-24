# Phase 7.0 IRF V3 overlap inventory (read-only)

Taken 2026-11-18 14:44. The Phase 7.0 files are owned by another process and may still be changing; nothing here modifies, copies, stages, imports or executes them, and Phase 6.5 integrates none of their outputs.

## Source documents (shared by both efforts)

| document | sha256 |
|---|---|
| IRF_Inverse_Retest_Failure_Rulebook.pdf (Method 1) | `39b9dd226c5dabd321a57855e23317e101f49e5a76f56ee4a5180ec10a69cec2` |
| IRF_Method2_First_Red_Candle_Rulebook.pdf (Method 2) | `5ad283df82c81eefaf2bef7277318ad38cafa7d4d5e8ad5147fbf98ec8276dc4` |

## Phase 6.5 interfaces (detectors only)

* `research/phase65.new_irf_method1(cs, cutoff='13:00') -> dict | None`: level = first-candle high; first later close back below it after any earlier close above it; entry reference = failure close; times are candle END times.
* `research/phase65.new_irf_method2(cs, cutoff='13:00', breakout_candle_may_be_first_red=False) -> dict | None`: Level B = open of the first red candle after the rally breakout; second breakout then failure close. Detectors and a standalone hypothetical diagnostic only: **no engine, no controller integration, no backtest of the new methods as specified**.

## Phase 7.0 files observed

`src/nifty_trading/research/irf_v3/` (14 modules), `reports/phase7/` (1397 files), `scripts/phase70_run.py`, `scripts/phase70_docs.py`, `scripts/phase70_preserve.py`, `tests/test_phase70_irf_v3.py`.

| file | bytes | modified | sha256 |
|---|---|---|---|
| __init__.py | 337 | 11-18 13:56 | 7aef74b6f192 |
| audit.py | 6924 | 11-18 14:27 | b81a855a910e |
| backtest.py | 5886 | 11-18 13:58 | 29ff1fe6e5d0 |
| charts.py | 6212 | 11-18 14:08 | 8d7aee359610 |
| config.py | 12149 | 11-18 14:20 | 6d8aad503549 |
| data_access.py | 6336 | 11-18 13:57 | 6282e99f07db |
| examples.py | 11769 | 11-18 14:10 | 0250d626ed12 |
| execution.py | 5813 | 11-18 14:20 | 053d2df0da97 |
| method1.py | 3560 | 11-18 14:20 | c914dc305ee5 |
| method2.py | 5456 | 11-18 14:20 | 69b0e15db6de |
| models.py | 2353 | 11-18 13:56 | 4720105c7faf |
| recon.py | 3953 | 11-18 14:04 | 5ca62c3df5c9 |
| reporting.py | 10497 | 11-18 14:04 | 30b246e1293b |
| signal_engine.py | 4846 | 11-18 14:20 | 7bbb457f85c1 |


Top-level callables (from the source text): `method1.py`: run_method1(d, candles); `method2.py`: run_method2(d, candles); `signal_engine.py`: evaluate_session(s, cfg, cal), overlap_class(ev); `config.py`: 

## Phase 7.0's own published test / audit results (not re-run by Phase 6.5)

`audit_results.json` reports an independent re-implementation with **0 mismatches** over its scenarios; its README states a three-implementation structure (production state machines, a separate NumPy/resample audit, reports). Phase 6.5 did not run their tests (running them would write into their package directory) and does not vouch for these numbers.

## Signal-level comparison with the Phase 6.5 detectors (window 2025-09..2026-08, to the extent both publish a signal)

| method | phase65_signals | phase70_signals | same_date_same_time | same_date_different_time | phase65_only | phase70_only |
|---|---|---|---|---|---|---|
| M1 | 126 | 153 | 125 | 0 | 1 | 28 |
| M2 | 87 | 113 | 86 | 0 | 1 | 27 |


Differences are expected where the two efforts read the rulebooks differently (eligibility statuses, cutoff handling, the 'breakout candle may be the first red candle' convention, level-tie conventions). `phase7_signal_comparison.csv` lists every date. **The two implementations are NOT claimed to agree**: the comparison above is a read of their published CSV at the time stated; where times differ nobody has determined which reading is intended.

## Potential overlap and unresolved interpretation differences

* Both detect the same two methods from the same two PDFs; Phase 7.0 additionally implements execution, backtests and a journal reconciliation, Phase 6.5 does not.
* Rule choices to be reconciled by the owner: whether the Method 2 breakout candle itself can be the first red candle; whether the 13:00 cutoff applies to the candle end or the fill; stop 35 vs 40; same-candle stop/target order; end-of-day exit.
* Phase 7.0's own list of open questions (first lines, read-only):

  > # Unresolved author questions (Phase 7.0)
  > 
  > None of these was answered by either PDF. Each implemented choice is labelled and (where it matters) run as a separate scenario. No choice is approved by the owner.
  > 
  > ## Both methods
  > 1. **Stop distance** - 35 or 40 points? The PDFs say 'about 35 to 40' and the examples show 35.2-40.75. Run as `SL35_T60` and `SL40_T60`.
  > 2. **Entry price** - the failure candle's close (M1 TO CONFIRM; M2 silent) or the first executable price after it? Primary: open of the next one-minute bar; the close convention is run as `SL40_ENTRY_SIGNAL_CLOSE`.
  > 3. **Exit clock** - M1: 'end of the session, time to be confirmed'; M2 row 'Latest entry time and exit time = 1 pm'. Primary: forced exit at the 15:14 bar open; `*_FORCED_EXIT_1300` scenarios test a 13:00 exit.
  > 4. **Entry cutoff** - 'no entry after 1 pm': is a fill at exactly 13:00 allowed? Implemented inclusive (13:00:00 allowed), consistent with the repository's ENTRY-CUTOFF-001.
  > 5. **Stop-vs-target in one candle** - SL first (M1, TO CONFIRM); M2 silent; the 5-minute-window reading is primary, chronological one-minute order is `SL40_TIE_MINUTE_ORDER`.
  > 6. **Trades per day** - 1 (TO CONFIRM). Is the day finished after a stop-loss (M1 says so, TO CONFIRM), or may a later failure be traded? Later cycles are only counted.
  > 7. **Priority when both methods fire** - not stated. Earliest signal; same instant -> Method 1 label (P&L unaffected).
  > 8. **Exactly-equal closes** - ignored (TO CONFIRM in both).
  > 9. **Setup expiry** - does an armed setup expire (time of day, distance, number of candles)? Neither PDF says so.
  > 
  > ## Method 1
  > 10. First-candle colour - no rule (TO CONFIRM). 11. Is there a minimum depth of the failure close below the level? (examples: 1.80-18.55 points) - none implemented.
  > 
  > ## Method 2
  > 12. Can the red rally-breakout candle itself be the first red candle? Primary no; variant `M2_ALT_BREAKOUT_RED` reported.
  > 13. Must the rally stay above Level A until Level B breaks? Primary: no condition. 14. If price closes back below Level A (or below B) before the second breakout, is the setup dead? Primary: no (source silent).
  > 15. Must the first red candle have its open above Level A? Not required here.

The final integration decision belongs to the owner. Neither effort's signals feed the combined portfolio.