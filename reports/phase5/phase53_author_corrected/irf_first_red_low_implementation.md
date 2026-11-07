# IRF - the first red candle's LOW as support (implementation)

Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning.

## The rule as implemented

1. Method 2A (`Confirmation A`): breakout candle (close above the opening-range high) -> extension candle (high above the breakout candle's high) -> the **earliest completed red candle after the extension** is the reference candle -> its **LOW (wick included)** is the support -> the entry is the first LATER completed candle that closes below that low, activated at that candle's close (signals after 13:00 are flagged `within_13_00_cutoff=False` in the outputs and are excluded by the unchanged controller; the engine does not filter them at signal level).
2. The reference candle's timestamp, OHLC index and low are stored on the signal (`first_red_candle_start`, `first_red_candle_low`, `red_candle_index`, `support_candle_index`). A later red candle never replaces it; the body low and the close are not used.
3. **Scope: Method 2A only.** The IRF guide's Method 2B reference is a *resistance* (the top of the first push; the red candle is the confirming candle, not the creator of a level), Method 1 has no support level (failure back inside the range) and Method 3's support is 'formed by the preceding candles' - none of these is changed. The independent audit confirms that Method 1 and Method 3 signals are identical to Phase 3.6.
4. **Provisional assumption `first_red_search_start`.** The guide fixes the step order breakout -> extension -> pullback low -> red candle -> close below, so the search starts after the extension (the engine's existing bookkeeping). The alternative `AFTER_BREAKOUT` (first red after the breakout candle, even before the extension) is a selectable variant (`phase53-var-irf-first-red-after-breakout`).

## Effect on Method 2A signals (2025-09-01..2026-08-31, against Phase 3.6)

| Method 2A signals | count |
|---|---|
| Phase 3.6 | 215 |
| unchanged (same time, same support) | 8 |
| same time, **changed reference support level** | 26 |
| earlier | 122 |
| later | 23 |
| newly generated | 119 |
| removed | 36 |
| **Method 2A signals using a different reference than Phase 3.6** (level changed + earlier + later + new) | 290 |

Methods 1, 2B and 3 (history effects only): Method 1: no change; Method 2B: time_shifted_earlier 34, time_shifted_later 46, added 44, removed 62; Method 3: no change (Method 3 produces no confirmed IRF signal in any configuration, so its unchanged status is vacuous, not tested by data). Method 2B and Method 3 signals can change only because an earlier or later 2A confirmation ends or re-arms an attempt (Method 1 and 3 are history-independent: audit check). Total IRF confirmed signals: Phase 3.6 874, first-red-low 939 (a count increase is not an improvement).

## The 42 executed Phase 3.6 Method-2 trades (`irf_first_red_low_comparison.csv`)

| outcome under first-red-low | trades |
|---|---|
| unchanged (same time and method) | 27 |
| first IRF signal of the day earlier | 8 |
| first IRF signal of the day later | 2 |
| no IRF signal within 13:00 | 5 |

Red-search-start assumption: 4 of the 42 trades give a different result when the first red candle is searched from the breakout candle; at signal level the variant has 292 changed Method 2A signals (against 326 for the default).

## Handwritten dates involving the first red candle

| correction | date | author's expectation | outcome | status |
|---|---|---|---|---|
| AC01 | 2025-09-01 | IRF (same strategy, different entry point) / earlier (at the resistanc | UNCHANGED (same time and method) | NOT_RECONCILED_METHOD_OUT_OF_SCOPE |
| AC03 | 2025-09-10 | IRF (same strategy, correct reference candle) / not stated | UNCHANGED (same time and method) | NOT_RECONCILED_METHOD_OUT_OF_SCOPE |
| AC08 | 2025-09-22 | IRF (earlier entry) / earlier | later (11:10 -> 11:25 Method 2A) | NOT_RECONCILED |
| AC09 | 2025-09-29 | IRF (earlier entry) / earlier | earlier (10:40 -> 10:10 Method 2A) | RECONCILED_DIRECTION |
| AC20 | 2025-11-13 | IRF (same strategy, correct reference candle) / not stated | NO IRF SIGNAL within 13:00 | APPLIED_NO_OBSERVABLE_EXPECTATION |
| AC26 | 2025-11-26 | IRF (same strategy, correct reference candle) / not stated | NO IRF SIGNAL within 13:00 | APPLIED_NO_OBSERVABLE_EXPECTATION |
| AC34 | 2025-12-15 | IRF (same strategy, correct reference candle) / not stated | UNCHANGED (same time and method) | NOT_RECONCILED_METHOD_OUT_OF_SCOPE |

Reading: AC09 moves earlier as the author wrote; AC08 (the author expects earlier) moves **later** under the first-red-low rule, so it is not reconciled; AC01, AC03 and AC34 are Method 2B signals whose reference is a resistance, so the rule does not apply (scope verification required); AC20 and AC26 state only the reference candle and the 2A signal does not reproduce (no IRF signal within 13:00). No outcome was compared with profit.

## Remaining decisions

O4: apply the rule to Method 2B / Method 3 (needs source support); confirm the search start (after the extension or after the breakout); AC08 contradicts the stated direction.
