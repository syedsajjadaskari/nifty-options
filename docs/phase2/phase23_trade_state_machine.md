# Phase 2.3 - the trading-day state machine

Implemented in `src/nifty_trading/strategies/trading_day.py::run_trading_day`. The entry logic of the five engines is unchanged (the only engine-side change is the PDR zone default, see `phase23_signal_selection.md`): they emit signals; this controller decides, for the whole day and across all five strategies, which signal becomes a trade. It consumes one session's signal records and 1-minute bars (with their `executable` flags) and returns the trades, the complete diagnostic log and the state trace. It is deterministic and runs **no** historical backtest (the P&L it carries is the synthetic index-point P&L of the exit model, shown only in synthetic tests).

## States

| state | meaning |
|---|---|
| `READY_FOR_FIRST_TRADE` | no position yet today |
| `FIRST_TRADE_ACTIVE` | the first position is open; every signal is ignored (logged) |
| `SECOND_TRADE_ELIGIBLE` | the first trade ended in `INITIAL_FULL_STOP`; only a **PDR or PDS** signal confirmed **after** that exit may be traded |
| `SECOND_TRADE_ACTIVE` | the second position is open; every signal is ignored (logged) |
| `DAY_FINISHED` | no further trade today |
| `UNRESOLVED_EXECUTION` | an exit or a collision cannot be resolved without inventing something; no further trade today |

## Transitions

```
READY_FOR_FIRST_TRADE --(first eligible signal)--------------------------> FIRST_TRADE_ACTIVE
READY_FOR_FIRST_TRADE --(same-timestamp collision, no approved tie-break)-> UNRESOLVED_EXECUTION
FIRST_TRADE_ACTIVE ----(Target 2 booked)--------------------------------> DAY_FINISHED          [DAY-T2-001]
FIRST_TRADE_ACTIVE ----(T1, then the post-T1 stop: T1_THEN_BUFFER_STOP)--> DAY_FINISHED          [DAY-BUF-001]
FIRST_TRADE_ACTIVE ----(original stop before T1: INITIAL_FULL_STOP)------> SECOND_TRADE_ELIGIBLE [DAY-SL-001]
FIRST_TRADE_ACTIVE ----(open at end of data / auction; NOT_EVALUABLE)----> UNRESOLVED_EXECUTION  [DAY-UNRES-001]
SECOND_TRADE_ELIGIBLE -(first eligible PDR/PDS signal after the exit)-----> SECOND_TRADE_ACTIVE
SECOND_TRADE_ACTIVE ---(any resolved outcome)---------------------------> DAY_FINISHED          [DAY-MAX-001]
SECOND_TRADE_ACTIVE ---(unresolved exit)--------------------------------> UNRESOLVED_EXECUTION
```
A legacy `BREAKEVEN` outcome (only in the superseded `ENTRY_BREAKEVEN` mode) also finishes the day.

## Decision order for a group of signals confirmed at the same timestamp
1. A position that has closed by this timestamp is settled first (state moves per its outcome).
2. `DAY_FINISHED` / `UNRESOLVED_EXECUTION` -> every signal is logged `IGNORED`. An active position -> `IGNORED (POSITION_ACTIVE)`; the signal is **never reused**.
3. Otherwise each signal is tested: second-trade restriction (PDR/PDS only), `is_valid` (not a diagnostic-only or entry-blocked signal), the **13:00 IST cutoff**, a **fillable** bar that starts exactly at the signal candle's end. Failures are logged `REJECTED` with the reason.
4. One survivor, or several of the **same strategy and direction** (identical stop and target; the other methods are listed), becomes the trade. Survivors of **different strategies or directions** are a `CONFLICT`: with no approved `TieBreakPolicy` the day becomes `UNRESOLVED_EXECUTION` and nothing is traded.

## Interpretations I made explicit (please confirm)
* **Position end = the minute after the exit bar.** A position that exits inside the 09:40 bar is still "active" for a signal confirmed at 09:40 (ignored) and free for one at 09:41.
* **Same strategy, same direction, same timestamp** (for example IRF Method 1 and Method 2A) is one trade, not a conflict. Different strategies at one timestamp always are.
* **Engines under the controller run with the per-session cap lifted.** `max_signals_per_session = 1` (a Phase 2 proposal) would stop a PDR/PDS engine from ever producing the second-trade signal after its first one was ignored; for controller runs use `ProposalConfig(max_signals_per_session=99)` (as `scripts/phase23_signal_diagnostics.py` does). The engines' own logic is unchanged.
* **`NOT_EVALUABLE` exit policy** (for example RF with no configured target) counts as an unresolved exit.
* **Records for another session are rejected, naive signal timestamps are read as IST.**
* **A signal ignored while a position was active can never be the second trade**, even if it is a PDR/PDS signal that would have been valid afterwards.

## Reading `final_state`
`SECOND_TRADE_ELIGIBLE` at the end of a day means "the first trade was fully stopped out and no later PDR/PDS signal appeared" - it is **not** a pending trade. (Reviewer 5 saw this final state on 61 of the 188 real days that had a trade: a state count only, no P&L.) `SEL-TIE-003` lists the two controller interpretations the owner has not yet confirmed.

## Scenarios A-F (all in `tests/test_phase23_day_controller.py`, synthetic paths)
| scenario | test |
|---|---|
| A: T2 reached -> day finished | `test_scenario_a_target_2_finishes_the_day_and_a_later_signal_is_ignored` |
| B: ORB stopped out, later PDR trades, then finished | `test_scenario_b_initial_full_stop_allows_one_pdr_trade_and_then_the_day_is_finished` |
| C: T1 then buffer stop -> finished, no second trade | `test_scenario_c_t1_then_buffer_stop_finishes_the_day_without_a_second_trade` |
| D: after a full stop an IRF signal is not eligible | `test_scenario_d_only_pdr_or_pds_may_be_the_second_trade` |
| E: 13:05 signal -> `ENTRY_CUTOFF_EXCEEDED` | `test_scenario_e_a_signal_confirmed_after_13_00_is_not_entered` |
| F: simultaneous signals -> conflict logged, unresolved | `test_simultaneous_signals_of_different_strategies_are_a_logged_conflict_not_an_arbitrary_choice` |
