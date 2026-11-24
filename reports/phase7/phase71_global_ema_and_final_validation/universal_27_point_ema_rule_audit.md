# Universal 27-point EMA rule - audit (Priority 0)

**Conclusion first.** The sentence cannot be turned into ONE mechanical rule from the sources. It is therefore implemented as a shared, opt-in research component (`src/nifty_trading/research/phase71/ema_rule.py`) with five labelled readings (EMA-1..EMA-5); the default (EMA-0) is unchanged. **No reading is confirmed, none is active in any paper-trading configuration, and nothing is selected by P&L.** Which reading the author means, and whether it overrides the explicit 'no EMA filter' text of the two IRF PDFs, are owner decisions.

## 1. Source-authority matrix (`ema_source_conflict_matrix.csv`)

| strategy | existing_EMA_rule_and_source | new_27_point_statement | possible_conflict | decision_needed |
|---|---|---|---|---|
| IRF (Method 1 / 2, Phase 7.0 PDFs) | IRF_Inverse_Retest_Failure_Rulebook.pdf p2; IRF_Method2_First_Red_Candle_Rulebook.pdf p2: 'IRF has no 200 EMA filter ... a SHORT can be taken whether price is above or below the 200 EMA' | Applies to IRF (author message, undated, relayed by the owner) | YES - direct contradiction of the explicit no-EMA statement; the PDFs say 'as you described it', i.e. an earlier description | Owner: does the universal statement supersede the no-EMA statement for IRF V3? |
| IRF (earlier: phone call + handwritten pages) | reports/phase5/phase52_author_rules/author_call_clarifications.md C3: 'the gap between the EMA and the candle should be 28 points' (call); handwritten AC13/AC18 (docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf p3-4): 'EMA space less than 27 -> wait for the EMA break' | 27 (now universal) | 28 (call) vs 27 (handwritten) vs 27 (new) - the handwritten pages and the new statement agree on 27; the call said 28 | Owner: 27 or 28; distance definition |
| ORB (Nifty_920_ORB_Rulebook docx / ORB_Strategy_Rulebook-2.pdf) | 200 EMA DIRECTION filter on the 5-minute chart: BUY only above, SELL only below; 'a fresh cross of the EMA is allowed' (9:15 candle may cross); close exactly on the EMA = no trade; 'near the EMA wait for a convincing close' (ORB pdf p5/p7) | Additional 27-point rule for ORB | POTENTIAL - a minimum-distance reading would reject fresh-cross entries the rulebook permits; the rulebook's 'near the EMA ... convincing close' wording is itself undefined | Owner: is the 27-point rule the definition of 'near the EMA' for ORB? minimum or maximum? |
| PDR (PDR_Strategy_Guide.pdf) | no EMA / 200 text in the 4-page guide | Applies to PDR | No stated conflict; no baseline EMA rule exists | Owner: confirm applicability and meaning (a trend-continuation retest strategy) |
| PDS (PDS strategy.pdf) | no EMA / 200 text in the 7-page guide | Applies to PDS | No stated conflict; no baseline EMA rule exists | Owner: confirm applicability and meaning |
| RF (RF strategy.pdf) | 200 EMA is 'a basic trend filter ... never the only proof of an uptrend' (p2, p4, p5, p8: 'established uptrend, not just above the EMA'); no distance number | Applies to RF | Potential: a different, qualitative use of the EMA | Owner: does the 27-point gap add to or replace the trend filter? |

## 2. The five readings (all evaluated for every strategy from ONE geometry function)

| Config | Reading | Definition at the confirming candle (N = 27 unless stated) | Source evidence |
|---|---|---|---|
| EMA-0 | baseline | no universal EMA rule | - |
| EMA-1 | A/D: minimum close distance | pass iff abs(close - EMA) >= N | the word 'gap'; D (absolute close-to-EMA difference) is the same quantity, reported once |
| EMA-2 | C: minimum range clearance | pass iff the nearest point of the high-low range to the EMA >= N (0 when the EMA lies inside the candle) | Phase 5.3 owner-approved NUMBER 28 with this PROVISIONAL measure; 'gap between the EMA and the candle' |
| EMA-3 | B: maximum proximity | pass iff abs(close - EMA) <= N | 'gap NEAR the 200 EMA' read as a proximity zone; ORB 'near the EMA' wording |
| EMA-4 | 28-point comparator | EMA-2 at N = 28 | the phone call / Phase 5.3 convention |
| EMA-5 | E: target-side | fail iff the EMA lies in the trade's path within N points of the entry reference (SHORT: 0 <= entry - EMA < N) | handwritten AC13/AC18 ('Tgt 1 is not above EMA'; 27 = Target 1) - the only reading with a worked drawing |

EMA-1 and EMA-3 are exact complements of each other; EMA-1/EMA-2/EMA-4 are minimum-distance readings, EMA-3 is a maximum-distance reading, EMA-5 is direction-aware (a short below the EMA is never blocked by it). They cannot all be the author's meaning.

## 3. Moving-average definition and timing
* **Timeframe:** the handwritten drawing says '200 EMA [5 min TF]'; the ORB rulebook uses the 200-period EMA on the 5-minute NIFTY chart; the earlier note 'Gap/200DMA' in the ORB document is the same 5-minute EMA (Phase 5.1 AC31). No source supports a daily 200-day average. All research uses the frozen contexts' `ema200_5m` (5-minute EMA(200), 200-value SMA seed, warm-up from 2025-07-01 / the Phase 4 warm-up month, causal: it includes the candle's own close and nothing later).
* **Warm-up / look-ahead:** an unavailable EMA is never a rejection (UNAVAILABLE). The independent audit rebuilds the EMA from raw one-minute rows (`independent_audit.md`).
* **Measurement time:** CONFIRMATION (the confirming candle) is the reference. SETUP and REFERENCE candle measurements are available where an engine records them (IRF V3, PDR/PDS interaction candle); at ENTRY the EMA value is identical to the confirmation value (no new candle has completed), only the price differs. **EMA-5 uses the confirming candle's CLOSE as the entry reference everywhere (gate and diagnostics) - causal at signal time; measuring from the next-bar fill price instead changes about 15 of 3,618 decisions (14 IRF, 1 PDS).** Decisions that change with the timing (window A, 27 points):

| window | strategy | interpretation | timing_compared | signals_with_both | decision_differs |
|---|---|---|---|---|---|
| A | IRF | MIN_CLOSE | SETUP vs CONFIRMATION | 633 | 70 |
| A | IRF | MIN_CLOSE | REFERENCE vs CONFIRMATION | 633 | 49 |
| A | IRF | MIN_RANGE | SETUP vs CONFIRMATION | 633 | 37 |
| A | IRF | MIN_RANGE | REFERENCE vs CONFIRMATION | 633 | 70 |
| A | IRF | MAX_CLOSE | SETUP vs CONFIRMATION | 633 | 70 |
| A | IRF | MAX_CLOSE | REFERENCE vs CONFIRMATION | 633 | 49 |
| A | IRF | TARGET_SIDE | SETUP vs CONFIRMATION | 633 | 12 |
| A | IRF | TARGET_SIDE | REFERENCE vs CONFIRMATION | 633 | 26 |
| A | PDR | MIN_CLOSE | SETUP vs CONFIRMATION | 147 | 18 |
| A | PDR | MIN_RANGE | SETUP vs CONFIRMATION | 147 | 19 |
| A | PDR | MAX_CLOSE | SETUP vs CONFIRMATION | 147 | 18 |
| A | PDR | TARGET_SIDE | SETUP vs CONFIRMATION | 147 | 1 |

## 4. Effect on each of the five strategies (signals failing each reading; baseline B signals; no EMA value -> not counted)

Window A:

| strategy | confirmed signals (baseline B, all IRF cycles) | EMA-1 | EMA-2 | EMA-3 | EMA-4 | EMA-5 |
|---|---|---|---|---|---|---|
| IRF | 633 | 92 | 135 | 541 | 140 | 53 |
| ORB | 39 | 3 | 18 | 36 | 18 | 0 |
| PDR | 147 | 23 | 38 | 124 | 40 | 3 |
| PDS | 111 | 23 | 44 | 88 | 46 | 9 |
| RF | 12 | 3 | 5 | 9 | 5 | 1 |

Window B:

| strategy | confirmed signals (baseline B, all IRF cycles) | EMA-1 | EMA-2 | EMA-3 | EMA-4 | EMA-5 |
|---|---|---|---|---|---|---|
| IRF | 1793 | 326 | 456 | 1467 | 464 | 189 |
| ORB | 93 | 11 | 35 | 82 | 35 | 0 |
| PDR | 453 | 37 | 74 | 416 | 78 | 6 |
| PDS | 257 | 86 | 123 | 171 | 123 | 32 |
| RF | 80 | 16 | 35 | 64 | 37 | 4 |

**These are signal-RECORD counts, not trade counts:** the IRF V3 adapter emits every completed cycle of both methods (M1 and M2 records can share one candle), including signals after 13:00 and signals blocked by an open position. Restricted to the first cycle of each IRF method (window A / window B):

| window | first-cycle IRF records | EMA-1 fail | EMA-2 fail | EMA-3 fail | EMA-4 fail | EMA-5 fail |
|---|---|---|---|---|---|---|
| A | 268 | 43 | 63 | 225 | 65 | 29 |
| B | 767 | 125 | 192 | 642 | 196 | 69 |

## 5. 27 versus 28 points (signal level; where the decision differs)

Window A: | strategy | interpretation | signals_with_ema | fail_at_27 | fail_at_28 | decision_differs_27_vs_28 |
|---|---|---|---|---|---|
| IRF | MIN_CLOSE | 633 | 92 | 95 | 3 |
| ORB | MIN_CLOSE | 39 | 3 | 3 | 0 |
| PDR | MIN_CLOSE | 147 | 23 | 23 | 0 |
| PDS | MIN_CLOSE | 111 | 23 | 24 | 1 |
| RF | MIN_CLOSE | 12 | 3 | 3 | 0 |
| IRF | MIN_RANGE | 633 | 135 | 140 | 5 |
| ORB | MIN_RANGE | 39 | 18 | 18 | 0 |
| PDR | MIN_RANGE | 147 | 38 | 40 | 2 |
| PDS | MIN_RANGE | 111 | 44 | 46 | 2 |
| RF | MIN_RANGE | 12 | 5 | 5 | 0 |
| IRF | MAX_CLOSE | 633 | 541 | 538 | 3 |
| ORB | MAX_CLOSE | 39 | 36 | 36 | 0 |
| PDR | MAX_CLOSE | 147 | 124 | 124 | 0 |
| PDS | MAX_CLOSE | 111 | 88 | 87 | 1 |
| RF | MAX_CLOSE | 12 | 9 | 9 | 0 |
| IRF | TARGET_SIDE | 633 | 53 | 56 | 3 |
| ORB | TARGET_SIDE | 39 | 0 | 0 | 0 |
| PDR | TARGET_SIDE | 147 | 3 | 3 | 0 |
| PDS | TARGET_SIDE | 111 | 9 | 9 | 0 |
| RF | TARGET_SIDE | 12 | 1 | 1 | 0 |

Window B (sum over the window):

| interpretation | signals_with_ema | fail_at_27 | fail_at_28 | decision_differs_27_vs_28 |
|---|---|---|---|---|
| MAX_CLOSE | 2676 | 2200 | 2181 | 19 |
| MIN_CLOSE | 2676 | 476 | 495 | 19 |
| MIN_RANGE | 2676 | 723 | 737 | 14 |
| TARGET_SIDE | 2676 | 231 | 239 | 8 |

Portfolio level (EMA-2 at 27 = config E vs EMA-4 at 28 = config K): window A: 2 trade(s) only with 27, 0 only with 28 (2026-07-13 PDS 10:05, 2026-07-16 IRF 11:15); window B: 5 only with 27, 0 only with 28 (2023-09-01 IRF 10:05, 2023-11-28 PDR 09:25, 2024-05-02 IRF 10:25, 2024-07-24 IRF 10:30, 2024-10-29 RF 12:05). The two numbers rarely change a decision, but they are not interchangeable; neither is retained by default.

## 6. Conflict with ORB's documented fresh EMA crossing (`ema_crossing_conflicts.csv`)

The ORB V2 rulebook permits a 9:15 candle that crosses the EMA (scenarios A already beyond / B intrabar cross / C overnight gap crosses) and says 'near the EMA wait for a convincing close' without a number. ORB V2 signals in the baseline: window A 39 (scenario mix {'A_ALREADY_BEYOND_EMA': 26, 'B_INTRABAR_CROSS_OF_EMA': 8, 'C_OVERNIGHT_GAP_CROSSES_EMA': 5}), of which 11 have the EMA inside the opening candle's range. Rejections: window A {'EMA-1_MIN_CLOSE_27': 3, 'EMA-2_MIN_RANGE_27': 18, 'EMA-3_MAX_CLOSE_27': 36, 'EMA-4_MIN_RANGE_28': 18, 'EMA-5_TARGET_SIDE_27': 0}; window B (93 ORB signals) {'EMA-1_MIN_CLOSE_27': 11, 'EMA-2_MIN_RANGE_27': 35, 'EMA-3_MAX_CLOSE_27': 82, 'EMA-4_MIN_RANGE_28': 35, 'EMA-5_TARGET_SIDE_27': 0}. A minimum-distance reading (EMA-1/2/4) removes valid fresh-cross ORB entries; a maximum-proximity reading (EMA-3) removes nearly all ORB entries (they are usually far from the EMA); EMA-5 removes none. Charts of every affected window-A day: `charts/orb_ema_conflicts/`. No previously validated ORB trade was silently dropped: all removals appear in `trade_set_attribution.csv` and as 'NOT EXECUTED' charts.

## 7. Conflict with the latest IRF PDFs
Both PDFs state explicitly that IRF has no EMA filter ('as you described it'); the new sentence says the 27-point gap is common to all strategies. Phase 7.0's IRF V3 therefore has NO EMA rule; the EMA configurations D/E/F/K/L are the only place it enters, and each is labelled research.

## 8. What would make the rule mechanical
(1) measure - close, candle range, or room in the trade's path; (2) inequality - minimum or maximum; (3) action - skip, or wait for a close beyond the EMA (and for how long); (4) scope - all methods of all strategies, or only trend-continuation ones (ORB has its own EMA direction rule; RF uses the EMA only as a qualitative trend filter); (5) 27 or 28; (6) whether it overrides the IRF PDFs. See `remaining_author_questions.md`.
