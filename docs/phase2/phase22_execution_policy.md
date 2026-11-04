> **SUPERSEDED IN PART (Phase 2.3):** every mention below of a breakeven / stop-to-entry after Target 1 is the old convention; the rule in force is the entry -/+ 6 stop of `phase23_exit_policy.md`. Selection across strategies, the 13:00 cutoff and the second-trade rules are in `phase23_signal_selection.md`.

# Phase 2.2 - execution policy (index-point simulation, not live trading)

Everything is **research**. The NIFTY 50 index is not tradable; all quantities are index points x quantity. Nothing here places or enables an order, and nothing here is approved for live use (`execution_status = RESEARCH_ONLY` on every signal).

## 1. Position and exits (performance report, VE)
6 lots x 65 = 390 quantity in two legs of 195. Target 1 = 27 points books Leg 1; the stop on Leg 2 then moves to the entry price; Leg 2 exits at Target 2 or at that breakeven stop. Outcomes: `Target` (T1+T2), `BE` (T1 then entry), `SL` (both legs at the stop, 390 quantity), `Incomplete` (still open).

| strategy | stop | stop status | Target 2 | T2 status |
|---|---|---|---|---|
| IRF | 35 (alt 40) | USER_APPROVED research baseline | 60 | VE |
| ORB | 30 | VE | 60 | VE |
| PDR | 35 (alt 40) | USER_APPROVED | 70 | **CONFLICTING** (guide 70; report has 1 of 6 winners at 60) |
| PDS | 35 (alt 40) | USER_APPROVED | 70 | **CONFLICTING** (guide 70; report has 2 of 3 winners at 60) |
| RF | 35 (alt 40) | USER_APPROVED | 60 | **PROPOSED_FOR_REVIEW** (guide: OPEN) |

The 35 is a research baseline; it does not explain how the historical manual trader chose stops (IRF/PDS guides: 35 or 40 by the recent green candle's distance). 35-vs-40 is **not** compared in this phase.

## 2. Causal fill convention (A22, PR)
A signal is confirmed when its 5-minute candle has **closed** (the first candle: 09:20). The candle's close is a *reference price*, never a fill. Entry is simulated at the **open of the first 1-minute bar that starts at the candle's end** (`selection.fill_from_next_bar`); that bar is already exposed to the stop and targets. Because the fill *is* that bar's open, the bar cannot touch the entry price merely by opening there: in the entry bar the breakeven stop is touched only by trading *strictly* beyond the entry (`entry_at_first_bar_open`); in every other bar the touch test is inclusive and ambiguities resolve adversely. If that bar is not fillable the entry is blocked (`ENTRY_BLOCKED_*` in `execution_config`). Nothing is filled inside the signal candle and nothing uses a later candle's information.

## 3. Same-bar ambiguity and gaps (A23, PR)
One-minute OHLC cannot show the intrabar order. Every ambiguity is resolved **adversely** and recorded in `ExitResult.ambiguities`: stop (or breakeven) before target; a stop and Target 1 in one bar = stop; Target 1 and the breakeven stop in one bar = breakeven. A stop or breakeven gapped through fills at the **worse of its level and the bar's open**; a target fills at its level, never better. Target 1 then Target 2 in one bar is allowed unless that bar also touches breakeven.

## 4. Closing-auction eligibility (A25, PR)
`core/execution_eligibility.classify_bar` labels each 1-minute bar by its start time and the evidence-tiered calendar:

| class | when | fillable |
|---|---|---|
| `CONTINUOUS` | 09:15-15:14 (and 15:15-15:29 before 2026-08-03; special sessions with normal hours such as Budget Sunday) | yes |
| `CLOSING_AUCTION_REFERENCE` | on/after 2026-08-03, bars starting 15:15-15:29 | **no** |
| `POST_CLOSE` | bars starting at/after 15:30 (closing-print stub, flat rows to 15:40) | no |
| `SPECIAL_SESSION_NONSTANDARD` | non-standard-hours special sessions (Muhurat) | no |
| `NON_TRADING` | confirmed holidays, ordinary weekends, pre-open | no |

Consequences, all enforced in `exit_policy.evaluate_exit` and tested:
* A stop, breakeven or target touched in a non-executable bar is **not filled**; the touch is recorded as an ambiguity.
* A position still open when the first such **closing-auction** bar is reached is returned as `INCOMPLETE_EOD` with `unresolved_at_closing_auction = True` (an ordinary day's 15:30 stub row is `POST_CLOSE`: skipped, but not flagged as an auction problem; `closing_auction_truncated` is also set when a research flatten replaced the exit) and the note `UNRESOLVED_AT_CLOSING_AUCTION: ... explicit Phase 3 treatment required`. **No closing price is invented**; the official close is not used as an exit.
* The research `EXIT_AT_LAST_CLOSE` option flattens at the last *executable* bar's close, never at the catch-up bar.
* A signal whose candle ends at 15:15 or later on an auction day is flagged `ENTRY_BLOCKED_CLOSING_AUCTION_REFERENCE` (9 IRF events in the data; none for the other strategies).
* The data itself is untouched and remains available for analysis, previous-day levels (`prev_day_level_window`) and context.

The auction's exact matching mechanics are **not modelled**. Whether positions should be carried, exited at the auction price or treated as filled at the official close is a Phase 3 decision for the owner.

## 5. Repeated signals (A26, PR)
The engines keep the complete event log. Three **evaluation policies** (`strategies/selection.py`) decide which events a later simulation would take; none comes from a source document and none is approved:

| policy | rule |
|---|---|
| `ALL_VALID_SIGNALS` | every CONFIRMED signal whose entry is fillable |
| `FIRST_VALID_SIGNAL_PER_DAY` | the earliest per day and strategy |
| `ONE_ACTIVE_POSITION_AT_A_TIME` | skip a signal while an earlier accepted position is open; the end time comes from the exit simulation; a position that never closes blocks the rest of that session visibly |

Event counts per policy are in `reports/phase22/signal_counts_phase22.md` (counts only; no profit; not compared with the report's trade counts).

## 6. Not done here
No profit backtest, no 35-vs-40 comparison, no cost model, no slippage, no position carry across sessions, no auction price model, no live or paper order path.
