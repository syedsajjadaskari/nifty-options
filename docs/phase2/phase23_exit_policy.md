# Phase 2.3 - exit policy (six lots, two targets, the post-T1 stop)

Index-point research model: **not** an executable index order, **not** live trading. Code: `core/exit_policy.py` (`policy_for`, `evaluate_exit`), configuration in `strategies/params.py::TradeConfig` (the only place stop and target distances live).

## Position
6 lots in two equal legs of 3 lots (`SIZE-LOT-001`, USER_APPROVED; the report's `[P2] [P7]` agree). The lot multiplier is configurable (`TradeConfig.lot_size`, default 65 = the historical value): 6 x 65 = 390 units, 195 per leg. Totals must split into two EQUAL legs (a 5-lot or 3+2 configuration is rejected). Position size is recorded in `execution_config.trade_config` on every signal.

## Levels (entry E)
| strategy | initial stop | alternative | Target 1 | Target 2 | stop authority | T2 authority |
|---|---|---|---|---|---|---|
| IRF | 35 | 40 | 27 | 60 | USER_APPROVED | SOURCE_VERIFIED (IRF p.1-2, 13-14) |
| ORB | 30 | 30 (unchanged) | 27 | 60 | SOURCE_VERIFIED (ORB p.1-2) | SOURCE_VERIFIED |
| PDR | 35 | 40 | 27 | 70 | USER_APPROVED | **CONFLICTING**: guide 70; the report has 1 of 6 PDR winners at 60 |
| PDS | 35 | 40 | 27 | 70 | USER_APPROVED | **CONFLICTING**: guide 70; the report has 2 of 3 PDS winners at 60 |
| RF | 35 | 40 | 27 | 60 | USER_APPROVED | **PROPOSED_FOR_REVIEW** (the RF guide says OPEN); `rf_t2_points=None` makes RF exits unresolved |

Target 1 = 27 points exits the first 3 lots (`[P2] [P7] [P11]`). The 35-vs-40 comparison is **not** run in this phase.

## After Target 1: the post-T1 stop (`POST-T1-STOP-006`, USER_APPROVED)
The remaining 3 lots are protected by a stop **6 index points against the original entry**: LONG entry - 6, SHORT entry + 6. It is fixed:
no trailing, no further adjustment, no move back to entry, no widening. This **replaces** the report's rule "the stop on Leg 2 moves to the entry price" (`[P7] [P11]`, rule `EXE-BE-001`), which stays in the registry as `SUPERSEDED_BY_USER_APPROVED_RULE` and survives only as the labelled legacy mode `post_t1_stop_mode="ENTRY_BREAKEVEN"` for reconciling the report.

Worked examples (tested): LONG E=25,000, stop 35 -> SL 24,965, T1 25,027, T2 25,060 (RF/IRF-style 60), post-T1 stop **24,994**. SHORT E=25,000 -> SL 25,035, T1 24,973, T2 24,940, post-T1 stop **25,006**.

| event | outcome | P&L (units x points) |
|---|---|---|
| original stop before T1 | `INITIAL_FULL_STOP` (all 6 lots; the only outcome that allows a second PDR/PDS trade) | -stop x 390 (worse after a gap) |
| T1, then the post-T1 stop | `T1_THEN_BUFFER_STOP` (day finished) | +27 x 195 - 6 x 195 = **+4,095** (a gap makes the Leg-2 part worse) |
| T1, then T2 | `TARGET` (day finished) | 27 x 195 + T2 x 195 |
| still open when the fillable bars end | `INCOMPLETE_EOD` -> day `UNRESOLVED_EXECUTION` | only a booked Leg 1 is realised |

The "6 points" are NIFTY index points, not a guaranteed 6-rupee loss per contract; the 4,095 above is the synthetic points x quantity of this model.

## Conventions (conservative; PROPOSED, not source rules)
* **Same bar:** stop before target. Initial stop and T1 in one bar -> `INITIAL_FULL_STOP`; T1 and the post-T1 stop in one bar -> `T1_THEN_BUFFER_STOP`; the post-T1 stop and T2 in one bar -> the stop. Each is recorded in `ExitResult.ambiguities`.
* **Gaps:** a stop gapped through fills at the **worse** of its level and the bar's open; a target fills at its level, never better. The adverse slippage (fill vs level, in points) is logged in `ExitResult.adverse_slippage_points`, e.g. LONG stop 24,994 with a bar opening at 24,985 -> filled 24,985, slippage 9.
* **Entry bar:** the fill is the open of the bar that starts at the signal candle's end (`EXE-FILL-001`); that bar already counts for the stops and targets. (The legacy exact-entry mode needs "strictly beyond the entry" in that bar so that merely opening at the entry is not a touch; the 6-point buffer makes this moot in the default mode.)
* **Non-fillable bars (closing auction 15:15-15:29 from 2026-08-03, post-close rows):** no stop, target or entry can fill there; a touch is only recorded. A position still open when such a bar is reached is `INCOMPLETE_EOD` with `unresolved_at_closing_auction` (for auction bars) and the day becomes `UNRESOLVED_EXECUTION`. **No end-of-day fill is invented**; the official close is not used as an exit. The research option `EXIT_AT_LAST_CLOSE` flattens at the last *executable* close and is off by default.
* **Not covered:** costs, brokerage, taxes and (apart from the logged gap slippage) slippage; the report's figures exclude them too (`[P14]`).

## Reconciling with the performance report
The report's `BE` outcome (Leg 2 out at the entry, +Rs 5,265) cannot occur under the owner's rule; its `Target` and `SL` arithmetic is unchanged. Nothing in this phase claims to replicate the report's profit figures.
