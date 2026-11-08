# Entry and exit execution audit (Phase 5.5)

SYNTHETIC index-point P&L x 390 units (6 lots x 65). The index is not tradable and historical lot sizes differ: this is NOT option P&L and not evidence for live orders. Costs are illustrative (Rs 70 per trade is the owner's indicative estimate, not a broker bill).

## Rules applied (the frozen controller and exit policy, unchanged)

* **Signal** on a completed five-minute candle; **fill** = the open of the one-minute bar that STARTS when the candle ends (EXE-FILL-001); no fill if that exact bar does not exist or is not fillable; the entry (fill) must not be later than 13:00 IST.
* **Position**: 6 lots x 65 = 390 synthetic units in two legs of 195. **Stops** 30 points (ORB), 35 (IRF, PDR, PDS, RF). **Target 1** 27 points: leg 1 exits; the remaining stop moves to entry -/+ 6 (no trailing). **Target 2** 60 (IRF, ORB, RF) / 70 (PDR, PDS).
* **Intrabar order** is unknowable from one-minute OHLC: when a bar touches both the stop and a target the stop is assumed first (conservative convention, not a source rule); a stop gapped through fills at the worse of the level and the bar open (adverse slippage recorded); targets fill at their level.
* **Forced exit** (provisional implementer assumption): a position still open at the 15:14 minute is closed at that bar's open, before 15:15; closing-auction bars are never fillable and nothing is filled at / after 15:15.

## How it was verified

The independent audit (`scripts/phase55_independent_audit.py`, no `src/` imports) re-implements the controller and the exit model and recomputes from the RAW one-minute candles every entry price, both exit prices and times, the exit class, the gross P&L and the five cost-scenario net P&Ls of all 574 trades of A, B and C and of all 1808 trades of the robustness window. Result: ALL 27 CHECKS PASS. The same independent controller re-selects exactly the same trades from the signal tables (no strategy priority: ORB receives none).

## Findings

| measure | A | B | C |
|---|---|---|---|
| trades | 196 | 188 | 190 |
| entries later than 13:00 | 0 | 0 | 0 |
| entry price != raw open of the entry minute (audit) | 0 | 0 | 0 |
| TARGET (T1 then T2) | 65 | 62 | 62 |
| T1 then post-T1 stop | 52 | 47 | 48 |
| INITIAL_FULL_STOP | 78 | 77 | 78 |
| FORCED_EXIT at the 15:14 open | 1 | 2 | 2 |
| unresolved exits (INCOMPLETE_EOD / NOT_EVALUABLE) | 0 | 0 | 0 |
| second trades (PDR / PDS only, after an original full stop) | 8 | 13 | 13 |
| stops filled through a gap (adverse slippage > 0) | 4 | 4 | 4 |
| total adverse gap slippage (points, summed) | 4.4 | 4.25 | 4.25 |
| exits in the entry minute | 6 | 6 | 6 |
| trades with a same-minute stop / target conflict (intrabar ambiguity) | 0 | 0 | 0 |

**Intrabar convention dependence:** 0 trades of 574 have a one-minute bar touching both the stop and a target, so NO outcome depends on the stop-first convention in this history (`intrabar_ambiguities.csv` is empty; the independent audit recomputed this from the raw bars and would have written `intrabar_sensitivity.csv` with the favourable-ordering counterfactual).

Entries and stops inside the same minute: A: 6 exits in the entry minute; B: 6 exits in the entry minute; C: 6 exits in the entry minute (a stop or a first-target level touched after the open of the entry bar is a normal exit, not an ordering ambiguity; the count includes both kinds, see `all_trade_legs.csv`).

## Provisional execution assumptions (not source rules)

* forced exit at the 15:14 open; * stop-first inside a one-minute bar; * the Rs 70 cost and its coverage; * 390-unit synthetic position (historical lot sizes differ); * no tie-break for same-minute signals of different strategies.

## Per-trade evidence

`all_executed_trades.csv` (one row per trade: signal candle start / end, signal timeframe, signal and first-eligible-execution timestamps, entry source bar and price, stop / T1 / T2, both exit times and prices, outcome, setup and selection explanations, entry-check counts, unresolved items, five cost-scenario net P&Ls) and `all_trade_legs.csv` (each leg with the one-minute exit bar and the trigger evidence). Daily reports: `daily/<date>.md`; charts of every trade that differs from configuration A: `charts/`.
