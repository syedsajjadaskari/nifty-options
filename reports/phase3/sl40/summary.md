# D. Alternative stop: 40 points for IRF/PDR/PDS/RF (ORB stays 30); everything else as A

**Exploratory research result. Synthetic index-point P&L x quantity; the NIFTY 50 index is not tradable. Not optimised, not approved, not a forecast.**

Period 2025-09-01..2026-08-31; sessions evaluated 247; wholly excluded 1; evaluated only partially 1 (listed at the end).

## Combined strategy - gross (zero cost)

| metric | value |
|---|---|
| Entries | 213 |
| Days with a trade | 197 |
| First / second trades | 197 / 16 |
| Gross P&L (Rs, synthetic) | 201,357 |
| Win rate (P&L > 0) | 61.97% |
| Profit factor | 1.17 |
| Average trade (Rs) | 945 |
| Max drawdown (Rs) | 195,780 |
| Max consecutive losses | 4 |
| Target 2 | 65 |
| T1 then post-T1 stop | 67 |
| Initial full stop | 81 |
| Forced exits (15:14) | 0 |
| Unresolved executions | 0 |
| Average holding (minutes) | 51.83 |

## Illustrative net (Rs 500 per trade + 0.5 point slippage per fill)

Net P&L Rs 11,787; profit factor 1.01; max drawdown Rs 267,870; win rate 61.97%.

## Signals and days

| item | count |
|---|---|
| ignored_position_active | 215 |
| ignored_day_already_decided | 687 |
| rejected_cutoff_13_00 | 40 |
| simultaneous_conflicts | 4 |
| rejected_not_pdr_pds_for_second_trade | 197 |
| notes | 18 |
| day final state DAY_FINISHED | 138 |
| day final state READY_FOR_FIRST_TRADE | 46 |
| day final state SECOND_TRADE_ELIGIBLE | 59 |
| day final state UNRESOLVED_EXECUTION | 4 |

## By strategy (gross)

| strategy | entries | 1st/2nd | gross P&L | win % | PF | avg | max DD | max consec. losses | contribution |
|---|---|---|---|---|---|---|---|---|---|
| IRF | 102 | 102/0 | -30,537 | 57.84 | 0.95 | -299 | 151,622 | 4 | -15.2% |
| ORB | 41 | 41/0 | 138,469 | 65.85 | 1.84 | 3,377 | 36,446 | 3 | 68.8% |
| PDR | 54 | 42/12 | 44,285 | 66.67 | 1.16 | 820 | 104,325 | 3 | 22.0% |
| PDS | 11 | 7/4 | 74,880 | 72.73 | 2.60 | 6,807 | 31,200 | 2 | 37.2% |
| RF | 5 | 5/0 | -25,740 | 40.0 | 0.45 | -5,148 | 31,200 | 2 | -12.8% |

## Monthly gross P&L (Rs; % of the report's assumed Rs 1,00,000 base)

| month | gross P&L | % of base |
|---|---|---|
| 2025-09 | 14,732 | 14.7% |
| 2025-10 | 7,020 | 7.0% |
| 2025-11 | 9,194 | 9.2% |
| 2025-12 | 96,320 | 96.3% |
| 2026-01 | -11,700 | -11.7% |
| 2026-02 | -20,865 | -20.9% |
| 2026-03 | 59,884 | 59.9% |
| 2026-04 | -54,034 | -54.0% |
| 2026-05 | -45,240 | -45.2% |
| 2026-06 | 4,095 | 4.1% |
| 2026-07 | 95,345 | 95.3% |
| 2026-08 | 46,605 | 46.6% |

## Cost x slippage sensitivity (net P&L Rs / profit factor)

| cost per trade \ slippage per fill | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 201,357 / 1.17 | 118,287 / 1.10 | 35,217 / 1.03 | -130,923 / 0.90 |
| Rs 500 | 94,857 / 1.08 | 11,787 / 1.01 | -71,283 / 0.95 | -237,423 / 0.83 |
| Rs 1,000 | -11,643 / 0.99 | -94,713 / 0.93 | -177,783 / 0.87 | -343,923 / 0.76 |
| Rs 1,500 | -118,143 / 0.91 | -201,213 / 0.85 | -284,283 / 0.80 | -450,423 / 0.69 |

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
