# C. PDR repeated-resistance shelf candidate; everything else as A

**Exploratory research result. Synthetic index-point P&L x quantity; the NIFTY 50 index is not tradable. Not optimised, not approved, not a forecast.**

Period 2025-09-01..2026-08-31; sessions evaluated 247; wholly excluded 1; evaluated only partially 1 (listed at the end).

## Combined strategy - gross (zero cost)

| metric | value |
|---|---|
| Entries | 210 |
| Days with a trade | 196 |
| First / second trades | 196 / 14 |
| Gross P&L (Rs, synthetic) | 87,301 |
| Win rate (P&L > 0) | 56.19% |
| Profit factor | 1.07 |
| Average trade (Rs) | 416 |
| Max drawdown (Rs) | 207,071 |
| Max consecutive losses | 6 |
| Target 2 | 63 |
| T1 then post-T1 stop | 55 |
| Initial full stop | 92 |
| Forced exits (15:14) | 0 |
| Unresolved executions | 0 |
| Average holding (minutes) | 47.54 |

## Illustrative net (Rs 500 per trade + 0.5 point slippage per fill)

Net P&L Rs -99,599; profit factor 0.92; max drawdown Rs 289,841; win rate 56.19%.

## Signals and days

| item | count |
|---|---|
| ignored_position_active | 174 |
| ignored_day_already_decided | 474 |
| rejected_not_pdr_pds_for_second_trade | 245 |
| rejected_cutoff_13_00 | 38 |
| notes | 19 |
| simultaneous_conflicts | 2 |
| rejected_entry_blocked_or_diagnostic | 1 |
| day final state DAY_FINISHED | 127 |
| day final state READY_FOR_FIRST_TRADE | 49 |
| day final state SECOND_TRADE_ELIGIBLE | 69 |
| day final state UNRESOLVED_EXECUTION | 2 |

## By strategy (gross)

| strategy | entries | 1st/2nd | gross P&L | win % | PF | avg | max DD | max consec. losses | contribution |
|---|---|---|---|---|---|---|---|---|---|
| IRF | 117 | 117/0 | 6,728 | 55.56 | 1.01 | 58 | 125,190 | 5 | 7.7% |
| ORB | 41 | 41/0 | 138,469 | 65.85 | 1.84 | 3,377 | 36,446 | 3 | 158.6% |
| PDR | 33 | 23/10 | -113,100 | 42.42 | 0.56 | -3,427 | 168,480 | 4 | -129.6% |
| PDS | 11 | 7/4 | 80,554 | 72.73 | 2.96 | 7,323 | 27,476 | 2 | 92.3% |
| RF | 8 | 8/0 | -25,350 | 50.0 | 0.54 | -3,169 | 40,950 | 3 | -29.0% |

## Monthly gross P&L (Rs; % of the report's assumed Rs 1,00,000 base)

| month | gross P&L | % of base |
|---|---|---|
| 2025-09 | 3,617 | 3.6% |
| 2025-10 | -15,795 | -15.8% |
| 2025-11 | -28,256 | -28.3% |
| 2025-12 | 123,630 | 123.6% |
| 2026-01 | -52,455 | -52.5% |
| 2026-02 | -25,740 | -25.7% |
| 2026-03 | 11,524 | 11.5% |
| 2026-04 | -72,930 | -72.9% |
| 2026-05 | 15,795 | 15.8% |
| 2026-06 | 2,925 | 2.9% |
| 2026-07 | 117,965 | 118.0% |
| 2026-08 | 7,020 | 7.0% |

## Cost x slippage sensitivity (net P&L Rs / profit factor)

| cost per trade \ slippage per fill | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 87,301 / 1.07 | 5,401 / 1.00 | -76,499 / 0.94 | -240,299 / 0.83 |
| Rs 500 | -17,699 / 0.99 | -99,599 / 0.92 | -181,499 / 0.87 | -345,299 / 0.76 |
| Rs 1,000 | -122,699 / 0.91 | -204,599 / 0.85 | -286,499 / 0.79 | -450,299 / 0.69 |
| Rs 1,500 | -227,699 / 0.83 | -309,599 / 0.78 | -391,499 / 0.73 | -555,299 / 0.63 |

Cost assumptions: a fixed Rs per round trip (the manual report's illustrative tiers) plus an adverse slippage of s points on every fill (entry of all units, exits of all units = 2 x quantity x s). These are placeholders: the index is not directly tradable, so no real brokerage/charges apply to it.

Forced exits: 0 trades. With no forced exit in this run the forced-exit price assumption (15:14 open) had no effect; this is a statement about an empty set, not a robustness result.

## Research settings and statuses behind these numbers (none is a verified original rule)

* trend: `EMA_PREV_SESSION_CLOSE`; PDR zone: `C_REPEATED_TOUCHES`; candle thresholds: strong `MODERATE`, pin bar `OWNER_2X_CLOSE30`; zone proximity 0 (strict overlap); IRF Method 1: 1 candle after the breakout.
* previous-day levels and zones use `ALL_CANDLES`: on closing-auction days the previous session's auction print is part of its high/low (it moved the previous-day level on 5 of the 19 sessions that follow an auction day).
* Target 2: IRF 60 and ORB 60 source-verified; PDR/PDS 70 are CONFLICTING (the manual report has winners at 60); RF 60 is a PROPOSAL. Stops: 35 are USER_APPROVED research values; ORB 30 is source-verified.
* ORB Method 2 and the Gap/200DMA setup are research variants; the forced exit (15:14 open) and the unresolved-collision day are implementer assumptions awaiting the owner.
* In the second-trade state only PDR/PDS signals are considered, so another strategy's signal in the same minute as a PDR/PDS signal is rejected, not logged as a conflict.

## Sessions excluded

* 2025-10-21: VALID_SPECIAL_SESSION: NON_STANDARD_START:Diwali Laxmi Pujan Muhurat trading (evening, ~13:45-14:45 in the vendor data, 61 one-minute rows)

## Sessions evaluated only partially

* 2025-10-23: ORB: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDR: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); PDS: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20)); RF: PREV_SESSION_UNVERIFIED(PREV_SESSION_SKIPS_EXCLUDED_SESSION:2025-10-21; PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION(2025-10-20))
