# A. Baseline: EMA-only trend (variant A), 35-point stop (ORB 30), reversal-high PDR zone

**Exploratory research result. Synthetic index-point P&L x quantity; the NIFTY 50 index is not tradable. Not optimised, not approved, not a forecast.**

Period 2025-09-01..2026-08-31; sessions evaluated 247; wholly excluded 1; evaluated only partially 1 (listed at the end).

## Combined strategy - gross (zero cost)

| metric | value |
|---|---|
| Entries | 213 |
| Days with a trade | 197 |
| First / second trades | 197 / 16 |
| Gross P&L (Rs, synthetic) | 172,146 |
| Win rate (P&L > 0) | 59.15% |
| Profit factor | 1.15 |
| Average trade (Rs) | 808 |
| Max drawdown (Rs) | 208,241 |
| Max consecutive losses | 5 |
| Target 2 | 61 |
| T1 then post-T1 stop | 65 |
| Initial full stop | 87 |
| Forced exits (15:14) | 0 |
| Unresolved executions | 0 |
| Average holding (minutes) | 47.33 |

## Illustrative net (Rs 500 per trade + 0.5 point slippage per fill)

Net P&L Rs -17,424; profit factor 0.99; max drawdown Rs 289,756; win rate 59.15%.

## Signals and days

| item | count |
|---|---|
| ignored_position_active | 190 |
| ignored_day_already_decided | 685 |
| rejected_cutoff_13_00 | 40 |
| simultaneous_conflicts | 4 |
| rejected_not_pdr_pds_for_second_trade | 224 |
| notes | 18 |
| day final state DAY_FINISHED | 134 |
| day final state READY_FOR_FIRST_TRADE | 46 |
| day final state SECOND_TRADE_ELIGIBLE | 63 |
| day final state UNRESOLVED_EXECUTION | 4 |

## By strategy (gross)

| strategy | entries | 1st/2nd | gross P&L | win % | PF | avg | max DD | max consec. losses | contribution |
|---|---|---|---|---|---|---|---|---|---|
| IRF | 102 | 102/0 | -56,062 | 53.92 | 0.91 | -550 | 180,180 | 5 | -32.6% |
| ORB | 41 | 41/0 | 138,469 | 65.85 | 1.84 | 3,377 | 36,446 | 3 | 80.4% |
| PDR | 54 | 42/12 | 29,075 | 62.96 | 1.11 | 538 | 96,145 | 3 | 16.9% |
| PDS | 11 | 7/4 | 80,554 | 72.73 | 2.96 | 7,323 | 27,476 | 2 | 46.8% |
| RF | 5 | 5/0 | -19,890 | 40.0 | 0.51 | -3,978 | 27,300 | 2 | -11.6% |

## Monthly gross P&L (Rs; % of the report's assumed Rs 1,00,000 base)

| month | gross P&L | % of base |
|---|---|---|
| 2025-09 | 6,737 | 6.7% |
| 2025-10 | 16,770 | 16.8% |
| 2025-11 | 22,669 | 22.7% |
| 2025-12 | 106,070 | 106.1% |
| 2026-01 | -48,360 | -48.4% |
| 2026-02 | -7,215 | -7.2% |
| 2026-03 | 31,219 | 31.2% |
| 2026-04 | -68,835 | -68.8% |
| 2026-05 | -29,640 | -29.6% |
| 2026-06 | 17,745 | 17.7% |
| 2026-07 | 103,145 | 103.1% |
| 2026-08 | 21,840 | 21.8% |

## Cost x slippage sensitivity (net P&L Rs / profit factor)

| cost per trade \ slippage per fill | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 172,146 / 1.15 | 89,076 / 1.07 | 6,006 / 1.00 | -160,134 / 0.88 |
| Rs 500 | 65,646 / 1.05 | -17,424 / 0.99 | -100,494 / 0.92 | -266,634 / 0.80 |
| Rs 1,000 | -40,854 / 0.97 | -123,924 / 0.90 | -206,994 / 0.84 | -373,134 / 0.73 |
| Rs 1,500 | -147,354 / 0.89 | -230,424 / 0.83 | -313,494 / 0.77 | -479,634 / 0.66 |

Cost assumptions: a fixed Rs per round trip (the manual report's illustrative tiers) plus an adverse slippage of s points on every fill (entry of all units, exits of all units = 2 x quantity x s). These are placeholders: the index is not directly tradable, so no real brokerage/charges apply to it.

Forced exits: 0 trades. With no forced exit in this run the forced-exit price assumption (15:14 open) had no effect; this is a statement about an empty set, not a robustness result.

## Research settings and statuses behind these numbers (none is a verified original rule)

* trend: `EMA_PREV_SESSION_CLOSE`; PDR zone: `B_SWING_HIGH_REVERSAL`; candle thresholds: strong `MODERATE`, pin bar `OWNER_2X_CLOSE30`; zone proximity 0 (strict overlap); IRF Method 1: 1 candle after the breakout.
* previous-day levels and zones use `ALL_CANDLES`: on closing-auction days the previous session's auction print is part of its high/low (it moved the previous-day level on 5 of the 19 sessions that follow an auction day).
* Target 2: IRF 60 and ORB 60 source-verified; PDR/PDS 70 are CONFLICTING (the manual report has winners at 60); RF 60 is a PROPOSAL. Stops: 35 are USER_APPROVED research values; ORB 30 is source-verified.
* ORB Method 2 and the Gap/200DMA setup are research variants; the forced exit (15:14 open) and the unresolved-collision day are implementer assumptions awaiting the owner.
* In the second-trade state only PDR/PDS signals are considered, so another strategy's signal in the same minute as a PDR/PDS signal is rejected, not logged as a conflict.

## Sessions excluded

* 2025-10-21: VALID_SPECIAL_SESSION: NON_STANDARD_START:Diwali Laxmi Pujan Muhurat trading (evening, ~13:45-14:45 in the vendor data, 61 one-minute rows)

## Sessions evaluated only partially

* 2025-10-23: ORB: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDR: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDS: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); RF: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20))
