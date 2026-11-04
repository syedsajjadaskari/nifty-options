# Phase 3.0 - comparison of the four exploratory scenarios and of the manual report

**Exploratory research, not optimised, not approved.** Synthetic index-point P&L x quantity (6 lots = 390 units at 65); the NIFTY 50 index is not tradable. Each scenario is a fixed, labelled configuration; the scenarios are **not** combined and no scenario was chosen because of its result. Settings that are research assumptions, not verified rules: EMA-only trend, the PDR zone candidates, candle thresholds, the RF 60-point target, the forced-exit time and price (15:14 open), and the unresolved-collision treatment.

## 1. Side by side (gross = zero cost)

| metric | A baseline | B structure trend | C PDR shelf | D 40-pt stop |
|---|---|---|---|---|
| Sessions evaluated | 247 | 247 | 247 | 247 |
| Days with a trade | 197 | 188 | 196 | 197 |
| Entries | 213 | 203 | 210 | 213 |
| First / second trades | 197 / 16 | 188 / 15 | 196 / 14 | 197 / 16 |
| Gross P&L (Rs) | 172,146 | 115,577 | 87,301 | 201,357 |
| Illustrative net P&L (Rs 500/trade + 0.5 pt/fill) | -17,424 | -65,093 | -99,599 | 11,787 |
| Win rate (P&L > 0), gross | 59.2% | 59.6% | 56.2% | 62.0% |
| Profit factor, gross | 1.15 | 1.10 | 1.07 | 1.17 |
| Profit factor, illustrative net | 0.99 | 0.94 | 0.92 | 1.01 |
| Average trade (Rs), gross | 808 | 569 | 416 | 945 |
| Max drawdown (Rs), gross | 208,241 | 220,155 | 207,071 | 195,780 |
| Max drawdown (Rs), illustrative net | 289,756 | 289,575 | 289,841 | 267,870 |
| Max consecutive losses | 5 | 5 | 6 | 4 |
| Target 2 | 61 | 54 | 63 | 65 |
| T1 then post-T1 stop | 65 | 67 | 55 | 67 |
| Initial full stop | 87 | 82 | 92 | 81 |
| Forced exits | 0 | 0 | 0 | 0 |
| Unresolved executions (trades) | 0 | 0 | 0 | 0 |
| Avg holding (min) | 47.33 | 48.10 | 47.54 | 51.83 |
| Signals rejected by the 13:00 cutoff | 40 | 53 | 38 | 40 |
| Signals ignored: another position active | 190 | 189 | 174 | 215 |
| Simultaneous-signal conflicts (days left unresolved) | 4 | 3 | 2 | 4 |
| Months with positive gross P&L (of 12) | 8 | 6 | 7 | 8 |

## 2. Strategy-wise gross P&L (Rs) and entries

| strategy | A baseline (n / P&L / PF) | B structure trend (n / P&L / PF) | C PDR shelf (n / P&L / PF) | D 40-pt stop (n / P&L / PF) |
|---|---|---|---|---|
| IRF | 102 / -56,062 / 0.91 | 113 / -74,002 / 0.90 | 117 / 6,728 / 1.01 | 102 / -30,537 / 0.95 |
| ORB | 41 / 138,469 / 1.84 | 21 / 81,315 / 2.16 | 41 / 138,469 / 1.84 | 41 / 138,469 / 1.84 |
| PDR | 54 / 29,075 / 1.11 | 58 / 27,710 / 1.10 | 33 / -113,100 / 0.56 | 54 / 44,285 / 1.16 |
| PDS | 11 / 80,554 / 2.96 | 11 / 80,554 / 2.96 | 11 / 80,554 / 2.96 | 11 / 74,880 / 2.60 |
| RF | 5 / -19,890 / 0.51 | 0 / 0 / 0.00 | 8 / -25,350 / 0.54 | 5 / -25,740 / 0.45 |

## 3. Monthly gross P&L (Rs)

| month | A baseline | B structure trend | C PDR shelf | D 40-pt stop |
|---|---|---|---|---|
| 2025-09 | 6,737 | 36,182 | 3,617 | 14,732 |
| 2025-10 | 16,770 | -2,145 | -15,795 | 7,020 |
| 2025-11 | 22,669 | 20,719 | -28,256 | 9,194 |
| 2025-12 | 106,070 | 62,585 | 123,630 | 96,320 |
| 2026-01 | -48,360 | -35,880 | -52,455 | -11,700 |
| 2026-02 | -7,215 | -24,180 | -25,740 | -20,865 |
| 2026-03 | 31,219 | 59,280 | 11,524 | 59,884 |
| 2026-04 | -68,835 | -74,100 | -72,930 | -54,034 |
| 2026-05 | -29,640 | -29,640 | 15,795 | -45,240 |
| 2026-06 | 17,745 | 0 | 2,925 | 4,095 |
| 2026-07 | 103,145 | 67,265 | 117,965 | 95,345 |
| 2026-08 | 21,840 | 35,490 | 7,020 | 46,605 |

## 4. Cost and slippage sensitivity (net P&L Rs, profit factor) - illustrative

Fixed cost per trade (the manual report's own tiers) and adverse slippage per fill on every unit in and out. The index is not directly tradable: these are placeholders, not confirmed product costs.


**A baseline**

| cost \ slippage | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 172,146 / 1.15 | 89,076 / 1.07 | 6,006 / 1.00 | -160,134 / 0.88 |
| Rs 500 | 65,646 / 1.05 | -17,424 / 0.99 | -100,494 / 0.92 | -266,634 / 0.80 |
| Rs 1,000 | -40,854 / 0.97 | -123,924 / 0.90 | -206,994 / 0.84 | -373,134 / 0.73 |
| Rs 1,500 | -147,354 / 0.89 | -230,424 / 0.83 | -313,494 / 0.77 | -479,634 / 0.66 |

**B structure trend**

| cost \ slippage | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 115,577 / 1.10 | 36,407 / 1.03 | -42,763 / 0.96 | -201,103 / 0.84 |
| Rs 500 | 14,077 / 1.01 | -65,093 / 0.94 | -144,263 / 0.88 | -302,603 / 0.76 |
| Rs 1,000 | -87,423 / 0.93 | -166,593 / 0.86 | -245,763 / 0.80 | -404,103 / 0.69 |
| Rs 1,500 | -188,923 / 0.85 | -268,093 / 0.79 | -347,263 / 0.73 | -505,603 / 0.63 |

**C PDR shelf**

| cost \ slippage | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 87,301 / 1.07 | 5,401 / 1.00 | -76,499 / 0.94 | -240,299 / 0.83 |
| Rs 500 | -17,699 / 0.99 | -99,599 / 0.92 | -181,499 / 0.87 | -345,299 / 0.76 |
| Rs 1,000 | -122,699 / 0.91 | -204,599 / 0.85 | -286,499 / 0.79 | -450,299 / 0.69 |
| Rs 1,500 | -227,699 / 0.83 | -309,599 / 0.78 | -391,499 / 0.73 | -555,299 / 0.63 |

**D 40-pt stop**

| cost \ slippage | 0 pt | 0.5 pt | 1 pt | 2 pt |
|---|---|---|---|---|
| Rs 0 | 201,357 / 1.17 | 118,287 / 1.10 | 35,217 / 1.03 | -130,923 / 0.90 |
| Rs 500 | 94,857 / 1.08 | 11,787 / 1.01 | -71,283 / 0.95 | -237,423 / 0.83 |
| Rs 1,000 | -11,643 / 0.99 | -94,713 / 0.93 | -177,783 / 0.87 | -343,923 / 0.76 |
| Rs 1,500 | -118,143 / 0.91 | -201,213 / 0.85 | -284,283 / 0.80 | -450,423 / 0.69 |

## 5. Comparison with the manual performance report (baseline scenario)

The manual report (189 trades on 180 days, Rs 7,69,860, profit factor 1.93) used an exact-entry breakeven stop, discretionary trade selection, and its own entries. The automated system uses the owner's rules (entry -/+ 6 post-T1 stop, first-signal priority, 13:00 cutoff, forced exit) and *mechanical* proxies for discretionary judgments. **Nothing was changed to force a match**; differences below are descriptive.

| item | manual report | automated baseline |
|---|---|---|
| trades (entries) | 189 | 213 |
| days with a trade | 180 | 197 |
| gross P&L (Rs) | 769,860 | 172,146 |
| profit factor | 1.93 | 1.15 |
| average trade (Rs) | 4,073 | 808 |
| max drawdown (Rs) | 68,055 | 208,241 |
| Target (T1 + T2) | 80 | 61 |
| exact-entry breakeven / post-T1 stop | 44 (BE, +Rs 5,265 each) | 65 (entry -/+ 6) |
| full stop-loss | 65 | 87 |
| win rate excluding BE / post-T1 stops: Target / (Target + SL) | 55.17% | 41.22% |

### Strategy allocation

| strategy | manual trades | automated entries | automated gross P&L (Rs) |
|---|---|---|---|
| IRF | 72 | 102 | -56,062 |
| ORB | 88 | 41 | 138,469 |
| PDR | 9 | 54 | 29,075 |
| PDS | 3 | 11 | 80,554 |
| RF | 17 | 5 | -19,890 |

### Average P&L per outcome class (Rs)

| class | manual | automated |
|---|---|---|
| Target | 17,111 (80 trades) | 17,508 (61 trades) |
| exact-entry BE / post-T1 stop | 5,265 (44) | 4,091 (65) |
| full stop | -12,780 (65) | -13,354 (87) |

### Diagnostic (not a scenario): the same baseline with the superseded exact-entry breakeven stop

Isolates how much of the gap to the manual report comes from the owner's new post-T1 stop. Not a result to rely on, not combined with anything.

| metric | baseline (entry -/+ 6) | diagnostic (exact-entry BE) |
|---|---|---|
| entries | 213 | 213 |
| gross P&L (Rs) | 172,146 | 141,219 |
| Target | 61 | 52 |
| exact-entry BE (legacy class) / entry -/+ 6 class | 0 / 65 | 74 / 0 |
| full stop | 87 | 87 |

## 6. Why the results differ (analysis)

All statements below are descriptive and about **one in-sample year**; none is a conclusion about the strategies' real quality, and no setting was changed because of them.

**1. The automated result is far below the manual report.** Baseline gross Rs 1,72,146 on 213 entries (profit factor 1.15, average Rs 808/trade) against Rs 7,69,860 on 189 trades (profit factor 1.93, Rs 4,073/trade). After the illustrative costs (Rs 500 per trade + 0.5 point per fill) the baseline is about break-even (Rs -17,424; profit factor 0.99). Taken at face value this means the mechanical rules do not reproduce the manual trader's edge; it does **not** show that the manual figures were wrong (see 7).

**2. The per-class accounting agrees; the hit rates do not.** The average Rs per outcome is close to the manual report's: Target Rs 17,508 vs 17,111; full stop Rs -13,354 vs -12,780; the 27-point partial plus a small adverse leg Rs 4,091 vs the old exact-entry Rs 5,265 (the difference is the owner's 6-point buffer and gap fills). What differs is how often each class occurs: Target 28.6% of automated entries (61/213) vs 42.3% of manual trades (80/189); full stop 40.8% (87) vs 34.4% (65); the post-T1-stop class 30.5% (65) vs 23.3% (44). Target / (Target + full stop) is 41.2% against the report's 55.17% (excluding BE).

**3. Strategy allocation is very different.** Automated entries vs manual trades: IRF 102 vs 72, ORB 41 vs 88, PDR 54 vs 9, PDS 11 vs 3, RF 5 vs 17. The engines apply *mechanical proxies* for rules the guides state only qualitatively (trend, candle quality, zone choice, "very close", the "return inside" for RF); those proxies fire more often than the manual trader on IRF and PDR and less often on ORB and RF. ORB's Methods 2 and the gap setup are research variants and fire rarely. These are exactly the unresolved items listed in `docs/phase2/phase3_readiness.md`.

**4. Trade frequency and selection.** 213 entries on 197 trading days (197 first trades, 16 second trades, all PDR/PDS after an original full stop) vs 189 trades on 180 trading days in the report (the journal itself has 190 rows on 185 dates, 5 of them with two trades). The first-signal rule means a strategy that fires early (ORB at 09:20) blocks later ones; 190 later signals were ignored while a position was open, 40 were rejected by the 13:00 cutoff, and 4 days with same-minute collisions between different strategies were left unresolved (no tie-break is approved).

**5. Entry timing and data conventions.** The automated fill is the open of the minute after a 5-minute candle completes; the manual PDR charts show the entry at the signal candle's *close*. The gap and first candle use the original first 1-minute open (owner-approved), whereas the manual charts use the vendor's published open (10 gap directions and 13 first-candle colours differ, `DATA-OPEN-001`). The previous close is the official close.

**6. Stop outcomes and the new post-T1 stop.** The diagnostic above re-runs the baseline with the superseded exact-entry breakeven stop: gross Rs 1,41,219 (profit factor 1.12) vs Rs 1,72,146 with the owner's entry -/+ 6 stop. So the 6-point buffer is **not** the reason for the gap to the manual report; in this sample it helped (probably because it no longer closes the second leg on small retracements to the entry; the mechanism was not isolated further). Target 2 differs per strategy (PDR/PDS 70 vs the report's recorded 60 on some winners) but PDR/PDS are 65 of 213 entries and cannot explain the size of the gap.

**7. Why the manual number should not be treated as a benchmark.** The manual report is the trader's own discretionary, self-recorded journal (the journal has 190 rows against 189 in the report, five rows dated on Saturdays, and three attribution differences found in Phase 2.1). It excludes costs and slippage and contains discretionary selection and exits that no rule describes.

**8. Concentration (this sample).** Baseline gross by month: December 2025 (+Rs 1,06,070) and July 2026 (+Rs 1,03,145) together contribute Rs 2,09,215, more than the whole year (Rs 1,72,146); the other ten months sum to Rs -37,070. Only 8 of 12 months are positive. By strategy, ORB (+Rs 1,38,469) and PDS (+Rs 80,554) carry the result while IRF (Rs -56,062) and RF (Rs -19,890) lose. Strategy-level numbers are **not** additive across scenarios because the first-signal rule makes the strategies compete for the same day.

**9. Scenarios B-D relative to A (not a ranking).** B (structure trend) halves the ORB trades (21) and removes RF (0 trades): gross Rs 1,15,577. C (PDR shelf) cuts PDR entries to 33 with a loss on them (Rs -1,13,100) while IRF's entries rise to 117 because the PDR candidate wins the first slot on fewer days: gross Rs 87,301. D (40-point stop, same signals) gives gross Rs 2,01,357 (profit factor 1.17): PDR and IRF are higher, PDS and RF lower. No scenario was chosen for its result, no combination was run, and 35 vs 40 is one sample year of evidence at most.

**10. Forced exit.** No trade was still open at 15:14 in any scenario, so the forced-exit price assumption (15:14 open) had no effect (sensitivity Rs 0); the path is exercised only by synthetic tests. Unresolved trades: 0.

**11. What the day-state labels mean.** `DAY_FINISHED` = a Target 2, post-T1 stop or second trade ended the day. `READY_FOR_FIRST_TRADE` = no eligible signal all day (also days with every signal after 13:00). `SECOND_TRADE_ELIGIBLE` = the first trade was fully stopped out and no later PDR/PDS signal appeared (not a pending trade). `UNRESOLVED_EXECUTION` = a same-minute collision between different strategies was left unresolved (nothing traded).


## 7. Limits

* One 12-month in-sample window, parameters fixed beforehand, no out-of-sample test, no significance testing: nothing here is evidence of an edge.
* Synthetic point P&L x quantity on a non-tradable index; costs/slippage are placeholders; no margin, financing or liquidity model.
* The forced-exit time/price (15:14 open) and the treatment of simultaneous signals (the day is left unresolved) are implementer assumptions awaiting the owner; no trade was force-exited in any scenario, so that assumption did not matter for these numbers.
* 2025-10-23 is evaluated only for IRF (its previous session, the Muhurat day, is not verifiable), so ORB/PDR/PDS/RF could not trade that day; 2025-10-21 (Muhurat) is excluded.
* Previous-day levels use all candles of the previous session, including the closing-auction print on auction days (`prev_day_level_window=ALL_CANDLES`).
* In the second-trade state only PDR/PDS signals are considered, so another strategy's same-minute signal is rejected rather than logged as a conflict (1 of 16 second trades in each scenario).
* Independent audit: all 839 trades of the four ledgers were re-simulated from the raw 1-minute data with 0 mismatches (`phase3_audit.md`).
