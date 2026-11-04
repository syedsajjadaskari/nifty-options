# B. Structure trend: EMA + confirmed swing structure (variant B); everything else as A

**Exploratory research result. Synthetic index-point P&L x quantity; the NIFTY 50 index is not tradable. Not optimised, not approved, not a forecast.**

Period 2025-09-01..2026-08-31; sessions evaluated 247; wholly excluded 1; evaluated only partially 1 (listed at the end).

## Combined strategy - gross (zero cost)

| metric | value |
|---|---|
| Entries | 203 |
| Days with a trade | 188 |
| First / second trades | 188 / 15 |
| Gross P&L (Rs, synthetic) | 115,577 |
| Win rate (P&L > 0) | 59.61% |
| Profit factor | 1.10 |
| Average trade (Rs) | 569 |
| Max drawdown (Rs) | 220,155 |
| Max consecutive losses | 5 |
| Target 2 | 54 |
| T1 then post-T1 stop | 67 |
| Initial full stop | 82 |
| Forced exits (15:14) | 0 |
| Unresolved executions | 0 |
| Average holding (minutes) | 48.10 |

## Illustrative net (Rs 500 per trade + 0.5 point slippage per fill)

Net P&L Rs -65,093; profit factor 0.94; max drawdown Rs 289,575; win rate 59.61%.

## Signals and days

| item | count |
|---|---|
| ignored_position_active | 189 |
| ignored_day_already_decided | 650 |
| rejected_cutoff_13_00 | 53 |
| rejected_not_pdr_pds_for_second_trade | 227 |
| notes | 15 |
| rejected_entry_blocked_or_diagnostic | 1 |
| simultaneous_conflicts | 3 |
| day final state DAY_FINISHED | 127 |
| day final state READY_FOR_FIRST_TRADE | 56 |
| day final state SECOND_TRADE_ELIGIBLE | 61 |
| day final state UNRESOLVED_EXECUTION | 3 |

## By strategy (gross)

| strategy | entries | 1st/2nd | gross P&L | win % | PF | avg | max DD | max consec. losses | contribution |
|---|---|---|---|---|---|---|---|---|---|
| IRF | 113 | 113/0 | -74,002 | 53.98 | 0.90 | -655 | 169,455 | 4 | -64.0% |
| ORB | 21 | 21/0 | 81,315 | 71.43 | 2.16 | 3,872 | 23,400 | 2 | 70.4% |
| PDR | 58 | 47/11 | 27,710 | 63.79 | 1.10 | 478 | 101,605 | 3 | 24.0% |
| PDS | 11 | 7/4 | 80,554 | 72.73 | 2.96 | 7,323 | 27,476 | 2 | 69.7% |
| RF | 0 | 0/0 | 0 | 0.0 | 0.00 | 0 | 0 | 0 | 0.0% |

## Monthly gross P&L (Rs; % of the report's assumed Rs 1,00,000 base)

| month | gross P&L | % of base |
|---|---|---|
| 2025-09 | 36,182 | 36.2% |
| 2025-10 | -2,145 | -2.1% |
| 2025-11 | 20,719 | 20.7% |
| 2025-12 | 62,585 | 62.6% |
| 2026-01 | -35,880 | -35.9% |
| 2026-02 | -24,180 | -24.2% |
| 2026-03 | 59,280 | 59.3% |
| 2026-04 | -74,100 | -74.1% |
| 2026-05 | -29,640 | -29.6% |
| 2026-06 | 0 | 0.0% |
| 2026-07 | 67,265 | 67.3% |
| 2026-08 | 35,490 | 35.5% |

## Cost x slippage sensitivity (net P&L Rs / profit factor)

| cost per trade \ slippage per fill | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 115,577 / 1.10 | 36,407 / 1.03 | -42,763 / 0.96 | -201,103 / 0.84 |
| Rs 500 | 14,077 / 1.01 | -65,093 / 0.94 | -144,263 / 0.88 | -302,603 / 0.76 |
| Rs 1,000 | -87,423 / 0.93 | -166,593 / 0.86 | -245,763 / 0.80 | -404,103 / 0.69 |
| Rs 1,500 | -188,923 / 0.85 | -268,093 / 0.79 | -347,263 / 0.73 | -505,603 / 0.63 |

Cost assumptions: a fixed Rs per round trip (the manual report's illustrative tiers) plus an adverse slippage of s points on every fill (entry of all units, exits of all units = 2 x quantity x s). These are placeholders: the index is not directly tradable, so no real brokerage/charges apply to it.

Forced exits: 0 trades. With no forced exit in this run the forced-exit price assumption (15:14 open) had no effect; this is a statement about an empty set, not a robustness result.

## Research settings and statuses behind these numbers (none is a verified original rule)

* trend: `STRUCTURE_EMA_SWING2`; PDR zone: `B_SWING_HIGH_REVERSAL`; candle thresholds: strong `MODERATE`, pin bar `OWNER_2X_CLOSE30`; zone proximity 0 (strict overlap); IRF Method 1: 1 candle after the breakout.
* previous-day levels and zones use `ALL_CANDLES`: on closing-auction days the previous session's auction print is part of its high/low (it moved the previous-day level on 5 of the 19 sessions that follow an auction day).
* Target 2: IRF 60 and ORB 60 source-verified; PDR/PDS 70 are CONFLICTING (the manual report has winners at 60); RF 60 is a PROPOSAL. Stops: 35 are USER_APPROVED research values; ORB 30 is source-verified.
* ORB Method 2 and the Gap/200DMA setup are research variants; the forced exit (15:14 open) and the unresolved-collision day are implementer assumptions awaiting the owner.
* In the second-trade state only PDR/PDS signals are considered, so another strategy's signal in the same minute as a PDR/PDS signal is rejected, not logged as a conflict.

## Sessions excluded

* 2025-10-21: VALID_SPECIAL_SESSION: NON_STANDARD_START:Diwali Laxmi Pujan Muhurat trading (evening, ~13:45-14:45 in the vendor data, 61 one-minute rows)

## Sessions evaluated only partially

* 2025-10-23: ORB: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDR: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDS: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); RF: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20))
