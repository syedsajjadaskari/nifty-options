# Strategy rule resolution (Task 5/7)

> **PARTLY SUPERSEDED BY PHASE 2.2** (`phase22_rule_verification.md`, `phase22_author_decisions.md`): stops are now a USER_APPROVED research baseline (35; ORB 30); RF target 60 is a PROPOSED research value; the PDR zone bottom is the body TOP by default (`PDR-D01` text below said body bottom); strict zone intersection is the default; the trend default is the structure proposal; a new open item `DATA-OPEN-001` (session open price) was found. Where this file and the Phase 2.2 files differ, Phase 2.2 wins.

Every ambiguity from `ambiguous_rules.md` re-examined against the original PDFs. **No decision is APPROVED**: a rule becomes APPROVED only when a source explicitly confirms it or the strategy owner authorises it.
Evidence categories: **A** explicit PDF wording · **B** another page of the same PDF · **C** worked numerical example · **D** reference-chart annotation · **E** performance report / market evidence · **F** justified but unverified proposal · **G** author clarification only.
Quantitative effects are **record counts** over 247 evaluable sessions (single change, everything else default) - never profitability.

Decisions: **52** · by classification: {'CONFLICTING': 5, 'UNRESOLVED': 17, 'PROPOSED_FOR_REVIEW': 13, 'VERIFIED_QUALITATIVE': 16, 'VERIFIED_EXPLICIT': 1} · author approval required: **40**

| ID | Strategy | Question | Class | Evidence | Recommended | Confidence | Author? |
|---|---|---|---|---|---|---|---|
| IRF-D01 | IRF | Method 1: the very next candle, or the next or the following candle? | CONFLICTING | A,B,D | very next candle | HIGH | yes |
| IRF-D02 | IRF | Method 1: what counts as 'closing back inside the range' at the edges? | UNRESOLVED | G | literal | MEDIUM | yes |
| IRF-D03 | IRF | How many IRF trades per day, until what time, and may a setup re-arm? | UNRESOLVED | G,E | keep reporting every occurrence; decide the selection policy at the trade layer once the author states it (do NOT invent 'one per day') | LOW | yes |
| IRF-D04 | IRF | Method 2: what does 'extends further upward' mean? | PROPOSED_FOR_REVIEW | F | E1 | LOW | yes |
| IRF-D05 | IRF | Method 2: order of the red candle and the level break | VERIFIED_QUALITATIVE | B,D | strict | MEDIUM | no |
| IRF-D06 | IRF | What is 'recent support'? | PROPOSED_FOR_REVIEW | F | SWING_K1 | LOW | yes |
| IRF-D07 | IRF | Recent resistance = 'the top of the first push' | VERIFIED_QUALITATIVE | A,B,C | first push top | MEDIUM | no |
| IRF-D08 | IRF | How long does a Method 2 setup stay alive? | UNRESOLVED | G | no expiry until stated | LOW | yes |
| IRF-D09 | IRF | Method 2B: may the push above resistance and the closing red candle be one candle? | PROPOSED_FOR_REVIEW | B,D | same candle allowed | LOW | yes |
| IRF-D10 | IRF | Method 3: how many 'small candles' inside the range? | PROPOSED_FOR_REVIEW | D,F | N = 2 | LOW | yes |
| IRF-D11 | IRF | Method 3: the 60-70% wick criterion | VERIFIED_QUALITATIVE | A,C,D | keep the literal 0.60-0.70 band (current default) unless you want stronger sweeps counted | MEDIUM | yes |
| IRF-D12 | IRF | Method 3: 'or a Higher price rejection candle also works' (p.14 card only) | UNRESOLVED | G | leave unimplemented | HIGH | yes |
| IRF-D13 | IRF | Stop 35 or 40: how is the green candle's distance measured? | PROPOSED_FOR_REVIEW | A,C,F | green high, <= 35 -> 35 | LOW | yes |
| ORB-D01 | ORB | '200 DMA', '200 EMA' or '200 MA'? | CONFLICTING | A,D,E | EMA(200) on 5-minute closes | HIGH (PDR/RF charts) / MEDIUM (ORB wording) | yes |
| ORB-D02 | ORB | What is an 'established' uptrend / downtrend? | VERIFIED_QUALITATIVE | A,B,F | EMA5M_PREV_SESSION (encodes only RF p.5's explicit rejection) | LOW | yes |
| ORB-D03 | ORB | Previous-day resistance / support: a line or a zone, and which candle? | VERIFIED_QUALITATIVE | A,D,F | previous high/low, all candles | MEDIUM | yes |
| ORB-D04 | ORB | Strong candle / pin bar / rejection thresholds | PROPOSED_FOR_REVIEW | A,F | MODERATE placeholder | LOW | yes |
| ORB-D05 | ORB | Does the conditional pin bar also apply to Methods 1 and 2? | VERIFIED_QUALITATIVE | B | applied | MEDIUM | no |
| ORB-D06 | ORB | Method 2: inner resistance/support and the trendline | UNRESOLVED | A,D | keep blocked | HIGH | yes |
| ORB-D07 | ORB | 'Near the EMA - wait for a convincing close' | UNRESOLVED | G | keep | LOW | yes |
| ORB-D08 | ORB | Gap-through-the-200-MA setup: 'excessively extended' and the crossing | UNRESOLVED | A,F | no cap; keep flagged | LOW | yes |
| ORB-D09 | ORB | Are 30 and 60 index points? | VERIFIED_QUALITATIVE | E | index points | HIGH | no |
| PDR-D01 | PDR | Zone lower boundary and which candle | VERIFIED_QUALITATIVE | A,B | body bottom to high | MEDIUM | no |
| PDR-D02 | PDR | Must the gap-up open lie above the zone? | VERIFIED_QUALITATIVE | A,B,C,D | ABOVE_ZONE | MEDIUM | yes |
| PDR-D09 | PDR | Zone construction: the engine's zone vs the zone drawn in Example 3 | PROPOSED_FOR_REVIEW | A,C,D | keep, flagged; ask the author how the reversal candle is chosen | LOW | yes |
| PDR-D03 | PDR | 'Very close approach' to the zone | PROPOSED_FOR_REVIEW | F | 5 points (placeholder) | LOW | yes |
| PDR-D04 | PDR | Green candle: after the touch, or may the touching candle be green? | VERIFIED_QUALITATIVE | A | strictly after | HIGH | no |
| PDR-D05 | PDR | 'Clear high and reversal identified' | UNRESOLVED | A,G | OFF until defined | LOW | yes |
| PDR-D06 | PDR | Stop 35 or 40 'depending on the situation' | UNRESOLVED | A,D | none until stated | LOW | yes |
| PDR-D07 | PDR | PDR target 70 - but the report records 60 on one PDR winner | CONFLICTING | A,D,E | 70 | MEDIUM | yes |
| PDR-D08 | PDR | Re-entries on the same day | PROPOSED_FOR_REVIEW | G | first only | LOW | yes |
| PDS-D01 | PDS | 'Good red candle' | PROPOSED_FOR_REVIEW | A,F | MODERATE placeholder | LOW | yes |
| PDS-D02 | PDS | HPR pin bar ratios | PROPOSED_FOR_REVIEW | A,F | MODERATE placeholder | LOW | yes |
| PDS-D03 | PDS | Method 3: size of the 'small support', close vs touch, stand-alone use | UNRESOLVED | A,G | as implemented | LOW | yes |
| PDS-D04 | PDS | Must the gap-down open lie below the zone? | VERIFIED_QUALITATIVE | A,B | BELOW_ZONE (text) pending the PDR decision | MEDIUM | yes |
| PDS-D05 | PDS | PDS stop 35/40: distance of the recent green candle | PROPOSED_FOR_REVIEW | A,F | as IRF-D13 | LOW | yes |
| PDS-D06 | PDS | PDS target 70 - but the report records 60 on two of three PDS winners | CONFLICTING | A,D,E | 70 | LOW | yes |
| PDS-D07 | PDS | PDS entry timing | UNRESOLVED | A | at the close | MEDIUM | no |
| RF-D01 | RF | RF trade direction | PROPOSED_FOR_REVIEW | B,D | long | HIGH | yes |
| RF-D02 | RF | 'Price returns inside the range' | VERIFIED_QUALITATIVE | A,D | R1 | MEDIUM | yes |
| RF-D03 | RF | Gap-up 'within yesterday's range' | VERIFIED_EXPLICIT | A | as implemented | HIGH | no |
| RF-D04 | RF | RF exact entry price | UNRESOLVED | A | close of the return candle | LOW | yes |
| RF-D05 | RF | RF stop: 35 or 40, fixed or the candle extreme | UNRESOLVED | A,D,E | none until stated | LOW | yes |
| RF-D06 | RF | RF TARGET (RF_TARGET_STATUS = UNRESOLVED) | UNRESOLVED | A,D,E | do NOT assign; ask the author (evidence leans to 60) | LOW | yes |
| DATA-D01 | DATA | 'Previous close' for gaps: official close or the last minute print? | VERIFIED_QUALITATIVE | A,E | official daily close | HIGH | no |
| DATA-D02 | DATA | August 2026 'frozen tail' = NSE Closing Auction Session (NOT corrupt data) | VERIFIED_QUALITATIVE | E | all candles | HIGH | no |
| DATA-D03 | DATA | Missing weekdays and the Phase 1 holiday list | VERIFIED_QUALITATIVE | E | as recorded | HIGH | no |
| DATA-D04 | DATA | Previous-day strategies on 2025-10-23 (a Muhurat session sits between) | UNRESOLVED | E,G | not evaluated | MEDIUM | yes |
| DATA-D05 | DATA | Indicator warm-up | VERIFIED_QUALITATIVE | E | as implemented | HIGH | no |
| EXE-D01 | EXEC | Target 2 per strategy | CONFLICTING | A,E | per guide | MEDIUM | yes |
| EXE-D02 | EXEC | Same-bar collisions, end of day, costs, lot size | UNRESOLVED | E | as implemented | MEDIUM | yes |
| EXE-D03 | EXEC | Trading journal reliability | UNRESOLVED | E | request a corrected trade list | HIGH | yes |

## IRF

### IRF-D01 - Method 1: the very next candle, or the next or the following candle?

* **Rules:** IRF-M1-C001, IRF-M1-002 · **Source:** IRF_Strategy_Guide Updated.pdf pp.5, 6, 13 vs p.14 · **Evidence:** A, B, D · **Classification:** CONFLICTING
* **Verified meaning:** pp.5 ('The very next candle ... closes back inside'), 6 ('The second candle must close back inside'), 13 ('Watch the very next candle. If it closes back inside the range, the setup is Method 1') and Figure 2 all say the very next candle. Only the p.14 quick card says 'the next candle or following candle'.
* **Existing implementation:** very next candle only (m1_max_candles_after_breakout = 1); the p.14 reading exists as a labelled variant
* **Candidate interpretations:** very next candle (4 of 5 passages + figure); next or following candle (p.14 card)
* **Quantitative effect (record counts):** Method 1 confirmed 349 -> 352; Method 2A 215 -> 197 (a later failure takes setups from Method 2)
* **Recommended interpretation:** very next candle (confidence HIGH) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D02 - Method 1: what counts as 'closing back inside the range' at the edges?

* **Rules:** IRF-M1-003 · **Source:** IRF pp.3, 5 · **Evidence:** G · **Classification:** UNRESOLVED
* **Verified meaning:** 'closing price is back below IRH, within the initial range'. A close exactly at IRH, or a close BELOW IRL, is not addressed.
* **Existing implementation:** IRL <= close < IRH; a close exactly at IRH never counts; a close below IRL does not count (variant available)
* **Candidate interpretations:** literal (above); a close below IRL also counts
* **Quantitative effect (record counts):** Method 1 confirmed 349 -> 356
* **Recommended interpretation:** literal (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D03 - How many IRF trades per day, until what time, and may a setup re-arm?

* **Rules:** IRF-GLOBAL-004, IRF-GLOBAL-005, IRF-M2-006 · **Source:** no passage in the guide · **Evidence:** G, E · **Classification:** UNRESOLVED
* **Verified meaning:** The guide is silent. DESCRIPTIVE ONLY (not a rule): in the journal every IRF entry label lies between 09:25 and 12:20 and no date has more than one IRF row. The journal is unreliable and NOT used as a rule.
* **Existing implementation:** every occurrence is reported; no cap, no time window; a Method 2 attempt is re-armed only after the previous attempt has resolved (confirmed or invalidated) and has no expiry, so it can fire hours after the breakout that started it; concurrent methods are cross-flagged
* **Candidate interpretations:** no cap (current); first signal per session; latest entry time; N per day
* **Quantitative effect (record counts):** 349 Method 1 + 215 Method 2A + 310 Method 2B events a year versus 72 IRF trades in the report; with a 6-candle expiry Method 2A 215 -> 84
* **Recommended interpretation:** keep reporting every occurrence; decide the selection policy at the trade layer once the author states it (do NOT invent 'one per day') (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D04 - Method 2: what does 'extends further upward' mean?

* **Rules:** IRF-M2-002 · **Source:** IRF p.7 step 3 · **Evidence:** F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** 'Price extends further upward beyond the initial range' - no size or time.
* **Existing implementation:** E1: a later candle makes a higher high than the breakout candle
* **Candidate interpretations:** E1 higher high than the breakout candle; E2 a later candle also closes above IRH
* **Quantitative effect (record counts):** Method 2A 215 -> 334; Method 2B 310 -> 321
* **Recommended interpretation:** E1 (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D05 - Method 2: order of the red candle and the level break

* **Rules:** IRF-M2-003, IRF-M2A-002 · **Source:** IRF p.8 steps 3-4, Figure 3 · **Evidence:** B, D · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** '3. A red candle forms. 4. A candle closes below recent support.' Figure 3 draws the red candle and the break candle as different candles.
* **Existing implementation:** strict order: the red candle comes strictly before the break candle; the extension candle cannot be the red candle
* **Candidate interpretations:** strict (current, matches Figure 3); break candle may itself be the first red candle
* **Quantitative effect (record counts):** Method 2A 215 -> 218
* **Recommended interpretation:** strict (confidence MEDIUM) · **Author approval required:** no · **Changes:** entry timing

### IRF-D06 - What is 'recent support'?

* **Rules:** IRF-M2A-001, IRF-M3-004 · **Source:** IRF pp.3, 8, 11 · **Evidence:** F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** 'a price level formed by recent candles where price has held or turned upward ... a pullback low' - no lookback, no swing size. The p.10 worked example does not define it numerically.
* **Existing implementation:** SWING_K1: the latest 3-candle fractal low confirmed before the signal candle
* **Candidate interpretations:** SWING_K1; SWING_K2 (5-candle fractal); LAST_N3 (lowest low of the last 3 candles)
* **Quantitative effect (record counts):** Method 2A 215 -> 154 (K2); 215 -> 309 (N3)
* **Recommended interpretation:** SWING_K1 (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D07 - Recent resistance = 'the top of the first push'

* **Rules:** IRF-M2B-001 · **Source:** IRF pp.8-10 (table, step 2, worked example 24,128.75) · **Evidence:** A, B, C · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** The worked example (p.10) calls 24,128.75 'the first push tops out' and Figure 4 shows the first push after the breakout. So it is the first swing high after the breakout, not the latest.
* **Existing implementation:** FIRST_PUSH_TOP: the earliest 3-candle fractal high at/after the breakout candle (reproduces the p.10 example exactly)
* **Candidate interpretations:** first push top (current); latest swing high
* **Quantitative effect (record counts):** Method 2B 310 -> 408 if the latest swing high were used
* **Recommended interpretation:** first push top (confidence MEDIUM) · **Author approval required:** no · **Changes:** entry

### IRF-D08 - How long does a Method 2 setup stay alive?

* **Rules:** IRF-M2-006 · **Source:** no passage · **Evidence:** G · **Classification:** UNRESOLVED
* **Verified meaning:** No expiry or invalidation is stated before a level breaks.
* **Existing implementation:** never expires before the end of the day; every later close above IRH starts a new attempt
* **Candidate interpretations:** no expiry (current); expire after N candles
* **Quantitative effect (record counts):** 6-candle expiry: Method 2A 215 -> 84, Method 2B 310 -> 211
* **Recommended interpretation:** no expiry until stated (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D09 - Method 2B: may the push above resistance and the closing red candle be one candle?

* **Rules:** IRF-M2B-002 · **Source:** IRF p.9 steps 3-5, Figure 4 · **Evidence:** B, D · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Steps: push back above resistance; a red candle forms; a red candle closes below it. Figure 4 draws separate candles.
* **Existing implementation:** the closing candle may itself be the one that traded above (m2b_push_must_precede_red_candle = False)
* **Candidate interpretations:** same candle allowed (current); an earlier candle must have pushed above
* **Quantitative effect (record counts):** measured on request (boundary tested)
* **Recommended interpretation:** same candle allowed (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### IRF-D10 - Method 3: how many 'small candles' inside the range?

* **Rules:** IRF-M3-001 · **Source:** IRF pp.11-12, Figure 5 · **Evidence:** D, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** 'Small candles form inside the initial range.' Figure 5 draws four small candles; the text only says plural.
* **Existing implementation:** the previous N = 2 candles lie fully inside [IRL, IRH]
* **Candidate interpretations:** N = 2 (literal minimum); N = 3; N = 4 (Figure 5); also require each range <= 50% of the IR height
* **Quantitative effect (record counts):** Method 3 sweeps passing compression 37 -> 27 (N=3); 37 -> 33 (size rule). Method 3 CONFIRMED signals: 0 under every candidate
* **Recommended interpretation:** N = 2 (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### IRF-D11 - Method 3: the 60-70% wick criterion

* **Rules:** IRF-M3-003 · **Source:** IRF pp.11-13, Figure 5 ('about 65%') · **Evidence:** A, C, D · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** The formula is explicit: share = (High - IRH) / (High - body top). The threshold is 'approximately 60-70%'; the example and Figure 5 show 65%. 'A wick that barely clears IRH' is rejected.
* **Existing implementation:** a literal 0.60-0.70 band (a 79% or 97% share would be rejected)
* **Candidate interpretations:** 0.60-0.70; >= 0.60; 0.55-0.75
* **Quantitative effect (record counts):** no change in confirmed counts (0 Method 3 confirmed under every band); of 37 candidate sweeps 32 have a share below 60%
* **Recommended interpretation:** keep the literal 0.60-0.70 band (current default) unless you want stronger sweeps counted (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry

### IRF-D12 - Method 3: 'or a Higher price rejection candle also works' (p.14 card only)

* **Rules:** IRF-M3-C001 · **Source:** IRF p.14 vs pp.11-12 · **Evidence:** G · **Classification:** UNRESOLVED
* **Verified meaning:** An alternative sweep-candle form that is defined nowhere. The trigger (support break) is unchanged.
* **Existing implementation:** not implemented
* **Candidate interpretations:** define it; delete it from the card
* **Quantitative effect (record counts):** not measurable
* **Recommended interpretation:** leave unimplemented (confidence HIGH) · **Author approval required:** yes · **Changes:** entry

### IRF-D13 - Stop 35 or 40: how is the green candle's distance measured?

* **Rules:** IRF-SL-001 · **Source:** IRF pp.2, 10, 14 · **Evidence:** A, C, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** '35 or 40 according to the most recent opposite (green) candle'; p.10: 'the most recent green candle is within 35 of entry, so the 35 stop applies'; p.14: 35 if the distance is below 35, 40 if above. The measuring point and the exact-35 case are not stated; the p.10 example is consistent with a high-based measure but does not discriminate.
* **Existing implementation:** |high of the most recent green candle - entry| <= 35 -> 35 else 40 (absolute value; signal candle included)
* **Candidate interpretations:** green high; green close; highest green high since the setup began; signed distance
* **Quantitative effect (record counts):** stop only; entries unchanged
* **Recommended interpretation:** green high, <= 35 -> 35 (confidence LOW) · **Author approval required:** yes · **Changes:** exit


## ORB

### ORB-D01 - '200 DMA', '200 EMA' or '200 MA'?

* **Rules:** ORB-MA-001 · **Source:** ORB pp.1,2,3,5,7,8,9,12 (three names); PDR pp.3-4 and RF (chart legends / '200 EMA') · **Evidence:** A, D, E · **Classification:** CONFLICTING
* **Verified meaning:** Verified directly from the source charts: the PDR chart legend reads 'EMA 200 close' on a 5-minute chart and EMA(200) of 5-minute closes reproduces it to within 0.005 point on BOTH examples (24,582.025 vs 24,582.02; 24,925.177 vs 24,925.18). A 200-day average is more than 400 points away. The ORB charts have no legend, so ORB's 'DMA' is inferred from the same curved line.
* **Existing implementation:** EMA(200) of completed 5-minute closes (ma_mode EMA200_5M); the daily readings exist as labelled research variants
* **Candidate interpretations:** EMA(200) on 5-minute closes; SMA(200) of daily closes; EMA(200) of daily closes
* **Quantitative effect (record counts):** ORB Method 1 confirmed 23 -> 13 under the daily SMA trend; Gap setup confirmed 9 -> 0 under the daily SMA
* **Recommended interpretation:** EMA(200) on 5-minute closes (confidence HIGH (PDR/RF charts) / MEDIUM (ORB wording)) · **Author approval required:** yes · **Changes:** entry, trade frequency

### ORB-D02 - What is an 'established' uptrend / downtrend?

* **Rules:** ORB-TREND-001, ORB-TREND-002, RF-001 · **Source:** ORB pp.1,3,4,12; RF pp.2,4,5 · **Evidence:** A, B, F · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** ORB: price above the 200 EMA is 'a basic confirmation, supported by bullish price structure'. RF p.5: above the EMA is never sufficient; a sudden gap above the EMA after a downtrend is rejected. 'Structure' is not quantified anywhere.
* **Existing implementation:** EMA5M_PREV_SESSION: the first candle closes beyond the EMA and the previous session also closed on the trend side of its EMA
* **Candidate interpretations:** EMA5M_BASIC; EMA5M_PREV_SESSION; EMA5M_PREV_3_SESSIONS; SMA200_DAILY; EMA200_DAILY
* **Quantitative effect (record counts):** ORB Method 1 confirmed 23 -> 31 (BASIC), 23 -> 8 (3 sessions); RF confirmed 12 -> 20 / 12 -> 6
* **Recommended interpretation:** EMA5M_PREV_SESSION (encodes only RF p.5's explicit rejection) (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### ORB-D03 - Previous-day resistance / support: a line or a zone, and which candle?

* **Rules:** ORB-M1-LONG-001, ORB-M1-SHORT-001 · **Source:** ORB p.3 step 2 ('horizontal line') vs charts pp.6-7, 12-13 (purple zones) · **Evidence:** A, D, F · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** The text says a horizontal line; every ORB chart draws it as a purple zone (like PDR/PDS). A close beyond the level is required either way.
* **Existing implementation:** previous session high / low (the outer edge of such a zone); only candles before the closing auction are an alternative
* **Candidate interpretations:** previous high/low (all candles); previous high/low (continuous session only); a PDR-style body-to-wick zone
* **Quantitative effect (record counts):** continuous-session-only level: ORB Method 1 invalidated 85 -> 88; confirmed unchanged
* **Recommended interpretation:** previous high/low, all candles (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry

### ORB-D04 - Strong candle / pin bar / rejection thresholds

* **Rules:** ORB-M1-LONG-003, ORB-CANDLE-001 · **Source:** ORB pp.3,4,8,10,12 · **Evidence:** A, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Qualitative only: 'strong green body', 'small upper wick', 'bullish pin bar - position and close must support the breakout'.
* **Existing implementation:** MODERATE: body >= 0.60 of range, opposite wick <= 0.20; pin bar wick >= 0.60, body <= 0.33, opposite wick <= 0.15; rejection wick >= 0.33
* **Candidate interpretations:** STRICT; MODERATE; LOOSE
* **Quantitative effect (record counts):** ORB Method 1 confirmed 23 -> 15 (strict), 23 -> 31 (loose)
* **Recommended interpretation:** MODERATE placeholder (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### ORB-D05 - Does the conditional pin bar also apply to Methods 1 and 2?

* **Rules:** ORB-CANDLE-001 · **Source:** ORB pp.9-10 ('across all three setups') · **Evidence:** B · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** p.9: 'Candle quality is an important filter across all three setups'; the p.10 table lists the bullish pin bar as 'Conditional' without restricting it to the gap setup. This is an INFERENCE from one generic sentence and that table, not an explicit statement for Methods 1 and 2.
* **Existing implementation:** applied to Methods 1 and 2 (orb_pin_bar_in_methods_1_2 = True)
* **Candidate interpretations:** applied (current); gap setup only
* **Quantitative effect (record counts):** ORB Method 1 confirmed 23 -> 18 if not applied
* **Recommended interpretation:** applied (confidence MEDIUM) · **Author approval required:** no · **Changes:** entry, trade frequency

### ORB-D06 - Method 2: inner resistance/support and the trendline

* **Rules:** ORB-M2-LONG-001, ORB-M2-SHORT-001 · **Source:** ORB pp.4-7 ('inner level drawn approximately') · **Evidence:** A, D · **Classification:** UNRESOLVED
* **Verified meaning:** No objective construction. The annotated chart (p.7) draws them by hand and the guide says 'verify the exact levels on your original chart'.
* **Existing implementation:** RESEARCH VARIANT ONLY: latest 5-candle fractal of the previous session inside its range; line through the last two fractals
* **Candidate interpretations:** define a construction rule; retire Method 2
* **Quantitative effect (record counts):** 16 research-variant confirmations (never presented as verified)
* **Recommended interpretation:** keep blocked (confidence HIGH) · **Author approval required:** yes · **Changes:** entry, trade frequency

### ORB-D07 - 'Near the EMA - wait for a convincing close'

* **Rules:** ORB-M2-LONG-004 · **Source:** ORB pp.5, 7 · **Evidence:** G · **Classification:** UNRESOLVED
* **Verified meaning:** 'near' and 'convincing' have no numbers, and at a 09:20 decision 'wait' has no obvious meaning.
* **Existing implementation:** near <= 15 points -> require a close >= 5 points beyond the EMA (Method 2 only)
* **Candidate interpretations:** as implemented; wait for the next candle
* **Quantitative effect (record counts):** Method 2 research variant only
* **Recommended interpretation:** keep (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### ORB-D08 - Gap-through-the-200-MA setup: 'excessively extended' and the crossing

* **Rules:** ORB-GAP-LONG-001, ORB-GAP-LONG-002, ORB-GAP-LONG-005, ORB-GAP-SHORT-004 · **Source:** ORB pp.7-9 · **Evidence:** A, F · **Classification:** UNRESOLVED
* **Verified meaning:** Gap required; price 'may have been below' the MA and the gap must bring it through; the first candle must close beyond the MA. 'If the opening move is excessively extended ... reject' is MANDATORY but has no number anywhere.
* **Existing implementation:** crossing required (previous close on one side of the MA, open on the other); 'excessively extended' filter OFF and reported unresolved (RESEARCH_VARIANT)
* **Candidate interpretations:** no cap; cap at 150 points
* **Quantitative effect (record counts):** Gap setup confirmed 9 -> 7 with a 150-point cap
* **Recommended interpretation:** no cap; keep flagged (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### ORB-D09 - Are 30 and 60 index points?

* **Rules:** ORB-UNIT-001 · **Source:** ORB p.11 ('standardize your units') + performance report · **Evidence:** E · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** The ORB guide leaves the unit to the user. The report settles it arithmetically: 36 ORB stop-losses total exactly Rs 4,21,200 = 36 x 30 x 390, so 30 is NIFTY index points on 390 quantity.
* **Existing implementation:** index points
* **Candidate interpretations:** index points
* **Quantitative effect (record counts):** none
* **Recommended interpretation:** index points (confidence HIGH) · **Author approval required:** no · **Changes:** exit


## PDR

### PDR-D01 - Zone lower boundary and which candle

* **Rules:** PDR-002 · **Source:** PDR pp.1-2; PDS p.3 · **Evidence:** A, B · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** 'Small box from candle body to upper wick'; 'Lower boundary: the relevant candle-body level'. PDS says 'body and wick' for its mirror zone.
* **Existing implementation:** [body bottom, high] of the first candle that made the previous day's high
* **Candidate interpretations:** body bottom to high; body top to high (wick only); first vs last candle sharing the high
* **Quantitative effect (record counts):** 39 -> 39 (the choice changes no signal in this data)
* **Recommended interpretation:** body bottom to high (confidence MEDIUM) · **Author approval required:** no · **Changes:** entry

### PDR-D02 - Must the gap-up open lie above the zone?

* **Rules:** PDR-011, PDR-004 · **Source:** PDR pp.1-2 (text); Example 3 on pp.3-4 · **Evidence:** A, B, C, D · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** Text: the market 'pulls back into the marked zone' (p.1) and 'comes back toward the zone ... if price keeps rising without returning there is no setup' (p.2): the open is above the zone, and a zone above price is resistance, not support. Example 3 (2025-10-07) does NOT contradict this: the zone the author DREW is only about 4-5 points tall (about 25,080.5-25,084.5, +/-1; pixel-calibrated on the chart's price axis, on the 69.90 and 40.60 position boxes and on known candle prices by two reviewers), while the engine's zone [25,057.10, 25,095.70] is 38.6 points tall (the 14:50 spike candle). The open 25,087.55 is about 3 points ABOVE the drawn zone and the 09:15 low (25,083.50) touches its top, so with the drawn zone the example matches the text sequence. (My own first measurement, ~14 points, 25,085-25,097, was wrong.) An earlier Phase 2.1 draft called this a conflict and made 'ANY' the default; that was an artefact of the engine's zone and has been withdrawn (found by the independent review).
* **Existing implementation:** pdr_open_vs_zone = ABOVE_ZONE (the text)
* **Candidate interpretations:** ABOVE_ZONE (text; default); NOT_BELOW_ZONE (open >= zone low); ANY (not recommended)
* **Quantitative effect (record counts):** PDR confirmed 39 (ABOVE_ZONE); 39 -> 53 (NOT_BELOW_ZONE); 39 -> 119 (ANY, of which 55% have the open BELOW the zone)
* **Recommended interpretation:** ABOVE_ZONE (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry, trade frequency

### PDR-D09 - Zone construction: the engine's zone vs the zone drawn in Example 3

* **Rules:** PDR-002, PDR-003 · **Source:** PDR pp.1-2 vs chart Example 3 (p.4) · **Evidence:** A, C, D · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Text: 'the high where price reached a peak and then reversed ... a small box from the candle body to the upper wick'. On 2025-10-06 the engine picks the highest-high candle (14:50 spike: body 25,057.10-25,077.25, wick to 25,095.70, a 38.6-point zone). The zone drawn in Example 3 is only about 4-5 points tall (about 25,080.5-25,084.5, +/-1) and sits on the late-day shelf, about 11 points below the spike's wick tip (25,095.70), so the author did NOT use the spike candle. Examples 1 and 2 are consistent with the engine's zone within chart-reading error. No objective rule reproduces the author's choice of candle.
* **Existing implementation:** the first candle that made the day's highest high; zone = [body bottom, high] (ZONE_FULL)
* **Candidate interpretations:** highest-high candle (current); ignore single-candle spikes (needs a spike rule); the shelf/cluster of late-day highs (not objectively defined)
* **Quantitative effect (record counts):** not measured (no objective alternative exists to count)
* **Recommended interpretation:** keep, flagged; ask the author how the reversal candle is chosen (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### PDR-D03 - 'Very close approach' to the zone

* **Rules:** PDR-006 · **Source:** PDR p.2; PDS p.4 · **Evidence:** F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Wick, body, inside, or 'very close' all count; no distance is given.
* **Existing implementation:** within 5 index points
* **Candidate interpretations:** 0; 5; 10 points
* **Quantitative effect (record counts):** PDR confirmed 39 -> 37 (0), 39 -> 41 (10)
* **Recommended interpretation:** 5 points (placeholder) (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### PDR-D04 - Green candle: after the touch, or may the touching candle be green?

* **Rules:** PDR-007 · **Source:** PDR pp.2-3 · **Evidence:** A · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** 'After the zone has been tested, wait for a green candle ... Green candle formed after the interaction'. Entry is on that confirmation; whether during or at the close is not stated.
* **Existing implementation:** a green candle strictly after the interaction candle; signal at its close
* **Candidate interpretations:** strictly after (current); same candle allowed
* **Quantitative effect (record counts):** 39 -> 39 (no signal changes)
* **Recommended interpretation:** strictly after (confidence HIGH) · **Author approval required:** no · **Changes:** entry timing

### PDR-D05 - 'Clear high and reversal identified'

* **Rules:** PDR-010 · **Source:** PDR p.3 checklist · **Evidence:** A, G · **Classification:** UNRESOLVED
* **Verified meaning:** A checklist item with no measure. It is the most likely selector between the many literal setups and the few trades taken.
* **Existing implementation:** filter OFF; every record carries PDR-010 as unresolved
* **Candidate interpretations:** OFF (current); previous-day reversal depth >= 25% of the day's range
* **Quantitative effect (record counts):** PDR confirmed 39 -> 21 with the 25% depth test
* **Recommended interpretation:** OFF until defined (confidence LOW) · **Author approval required:** yes · **Changes:** entry, trade frequency

### PDR-D06 - Stop 35 or 40 'depending on the situation'

* **Rules:** PDR-009 · **Source:** PDR pp.1-2; chart examples pp.3-4 · **Evidence:** A, D · **Classification:** UNRESOLVED
* **Verified meaning:** No criterion. The examples show both values: Example 3 stop 40.60, Example 5 stop 35.00.
* **Existing implementation:** not implemented: PDR exits are NOT_EVALUABLE
* **Candidate interpretations:** same green-candle rule as IRF/PDS; always 35; always 40
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** none until stated (confidence LOW) · **Author approval required:** yes · **Changes:** exit

### PDR-D07 - PDR target 70 - but the report records 60 on one PDR winner

* **Rules:** PDR-008, EXE-T2-001 · **Source:** PDR pp.1-3 and Examples (69.90, 70.40) vs the performance report · **Evidence:** A, D, E · **Classification:** CONFLICTING
* **Verified meaning:** The guide and both annotated examples say 70. The report's monthly cells imply PDR winners of 5 x 70 + 1 x 60 (exact, unique). The 60-point PDR winner sits in Feb-2026, a month where the JOURNAL has no PDR row and has one extra ORB Target (ORB's target is 60): an attribution difference between the two sources is the most likely explanation. It is not proven.
* **Existing implementation:** target 70 per the guide, flagged conflicting
* **Candidate interpretations:** 70 (guide + examples); 60 for the odd trade (report)
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** 70 (confidence MEDIUM) · **Author approval required:** yes · **Changes:** exit

### PDR-D08 - Re-entries on the same day

* **Rules:** PDR-012 · **Source:** silent · **Evidence:** G · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Not stated.
* **Existing implementation:** first signal per session only
* **Candidate interpretations:** first only; every retest
* **Quantitative effect (record counts):** not measured
* **Recommended interpretation:** first only (confidence LOW) · **Author approval required:** yes · **Changes:** trade frequency


## PDS

### PDS-D01 - 'Good red candle'

* **Rules:** PDS-M1-001 · **Source:** PDS p.5 (author's open item) · **Evidence:** A, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** 'A good body' with no numbers; the author lists it as an open item.
* **Existing implementation:** MODERATE strong bearish candle
* **Candidate interpretations:** STRICT; MODERATE; LOOSE
* **Quantitative effect (record counts):** PDS Method 1 confirmed 9 -> 3 (strict), 9 -> 11 (loose)
* **Recommended interpretation:** MODERATE placeholder (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### PDS-D02 - HPR pin bar ratios

* **Rules:** PDS-M2-001 · **Source:** PDS p.5 (author's open item) · **Evidence:** A, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** 'Wick-to-body ratio is not specified.'
* **Existing implementation:** MODERATE pin bar (upper wick >= 0.60 of range, body <= 0.33)
* **Candidate interpretations:** STRICT; MODERATE; LOOSE
* **Quantitative effect (record counts):** PDS Method 2 confirmed 0 under the default
* **Recommended interpretation:** MODERATE placeholder (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### PDS-D03 - Method 3: size of the 'small support', close vs touch, stand-alone use

* **Rules:** PDS-M3-001 · **Source:** PDS pp.4-6 (all three are the author's own open items) · **Evidence:** A, G · **Classification:** UNRESOLVED
* **Verified meaning:** Not defined by the author: how small the support is, whether a close or a touch breaks it (p.5), and whether Method 3 is used only after a weak red candle or also on its own (p.6).
* **Existing implementation:** latest 3-candle swing low near the zone; break on a CLOSE; only after a weak first red candle
* **Candidate interpretations:** close vs touch; after weak red only vs stand-alone
* **Quantitative effect (record counts):** PDS Method 3 confirmed 15 -> 16 (touch); 15 -> 16 (stand-alone)
* **Recommended interpretation:** as implemented (confidence LOW) · **Author approval required:** yes · **Changes:** entry

### PDS-D04 - Must the gap-down open lie below the zone?

* **Rules:** PDS-006 · **Source:** PDS pp.3-4 · **Evidence:** A, B · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** 'After the open, price is trading below the previous day's support zone' (p.3) and 'price must move back up toward the marked zone' (p.4). No contrary worked example exists (PDS charts are undated).
* **Existing implementation:** pds_open_vs_zone = BELOW_ZONE (the text)
* **Candidate interpretations:** BELOW_ZONE (current); NOT_ABOVE_ZONE; ANY
* **Quantitative effect (record counts):** PDS Method 1 confirmed 9 -> 34, Method 3 15 -> 35 with no condition
* **Recommended interpretation:** BELOW_ZONE (text) pending the PDR decision (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry, trade frequency

### PDS-D05 - PDS stop 35/40: distance of the recent green candle

* **Rules:** PDS-SL-001 · **Source:** PDS pp.2, 5, 6 (author's open items) · **Evidence:** A, F · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Based on 'the distance of the recent green candle'; the measuring point and the exact-35 case are the author's open items. The p.7 chart box reads stop 35.50 (target 70.10).
* **Existing implementation:** same as IRF-D13
* **Candidate interpretations:** as IRF-D13
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** as IRF-D13 (confidence LOW) · **Author approval required:** yes · **Changes:** exit

### PDS-D06 - PDS target 70 - but the report records 60 on two of three PDS winners

* **Rules:** PDS-TGT-001, EXE-T2-001 · **Source:** PDS pp.1,2,4,5,6; chart p.7 (70.10) vs the report · **Evidence:** A, D, E · **Classification:** CONFLICTING
* **Verified meaning:** The guide says 70 on five pages and the p.7 chart box reads 70.10. The report's cells imply PDS winners of 1 x 70 + 2 x 60. The journal's PDS counts equal the report's (3), so attribution does not explain it.
* **Existing implementation:** target 70 per the guide, flagged conflicting
* **Candidate interpretations:** 70 (guide); 60 (report); author's discretionary change
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** 70 (confidence LOW) · **Author approval required:** yes · **Changes:** exit

### PDS-D07 - PDS entry timing

* **Rules:** PDS-MISSING-001 · **Source:** PDS p.6 · **Evidence:** A · **Classification:** UNRESOLVED
* **Verified meaning:** 'Not specified whether entry is during the candle or after it closes.'
* **Existing implementation:** signal at candle close (the only moment the colour is known)
* **Candidate interpretations:** at the close
* **Quantitative effect (record counts):** timing only
* **Recommended interpretation:** at the close (confidence MEDIUM) · **Author approval required:** no · **Changes:** entry timing


## RF

### RF-D01 - RF trade direction

* **Rules:** RF-012 · **Source:** RF pp.1,2,9 · **Evidence:** B, D · **Classification:** PROPOSED_FOR_REVIEW
* **Verified meaning:** Never stated. 'The opposite of the IRF strategy' (p.2) and 'uptrend only' (p.1) imply long; the p.9 reference chart is a LONG position tool (target box 60.80 above, stop 40.65 below, closed at the stop).
* **Existing implementation:** LONG, flagged RF_DIRECTION_IMPLIED_NOT_STATED
* **Candidate interpretations:** long
* **Quantitative effect (record counts):** direction only
* **Recommended interpretation:** long (confidence HIGH) · **Author approval required:** yes · **Changes:** entry

### RF-D02 - 'Price returns inside the range'

* **Rules:** RF-006 · **Source:** RF pp.2, 4 (Figure 2 shows the very next candle inside) · **Evidence:** A, D · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** After a close below RF Low, price 'must come back inside the original 5-minute range'. Figure 2 shows the candle right after the close-below sitting inside. Close vs touch and how many candles may elapse are not stated.
* **Existing implementation:** R1: the first later candle whose CLOSE is back inside [RF Low, RF High]
* **Candidate interpretations:** R1 close inside; R2 touch of RF Low; R3 only the very next candle
* **Quantitative effect (record counts):** RF confirmed 12 -> 14 (R2), 12 -> 7 (R3)
* **Recommended interpretation:** R1 (confidence MEDIUM) · **Author approval required:** yes · **Changes:** entry, trade frequency

### RF-D03 - Gap-up 'within yesterday's range'

* **Rules:** RF-004 · **Source:** RF pp.2, 4, 6, 7 · **Evidence:** A · **Classification:** VERIFIED_EXPLICIT
* **Verified meaning:** A gap that carries the open above yesterday's HIGH is rejected; a gap-down is rejected.
* **Existing implementation:** PrevLow <= open <= PrevHigh and open above the previous official close
* **Candidate interpretations:** as implemented
* **Quantitative effect (record counts):** RF levels unchanged by the auction-candle choice (12 -> 12)
* **Recommended interpretation:** as implemented (confidence HIGH) · **Author approval required:** no · **Changes:** entry

### RF-D04 - RF exact entry price

* **Rules:** RF-010 · **Source:** RF p.8 ('Exact entry price: OPEN') · **Evidence:** A · **Classification:** UNRESOLVED
* **Verified meaning:** The author marks it OPEN.
* **Existing implementation:** reference price = close of the return-inside candle
* **Candidate interpretations:** close of the return candle; next candle open
* **Quantitative effect (record counts):** entry price only
* **Recommended interpretation:** close of the return candle (confidence LOW) · **Author approval required:** yes · **Changes:** entry timing

### RF-D05 - RF stop: 35 or 40, fixed or the candle extreme

* **Rules:** RF-009 · **Source:** RF pp.2, 8 (rated PARTIAL by the author) · **Evidence:** A, D, E · **Classification:** UNRESOLVED
* **Verified meaning:** 'Pick 35 or 40 depending on what is logical'. The p.9 chart's stop is 40.65. Against the report: 11 of the 12 RF monthly cells reproduce exactly with stops of 35 or 40. Only the August-2026 cell does not: its stop-loss loss of Rs 17,550 is 45 points in total, which two stops of at least 35 points cannot produce (the report's overall average of 33.1 points per RF stop comes solely from that cell).
* **Existing implementation:** not implemented: RF exits are NOT_EVALUABLE
* **Candidate interpretations:** fixed 35; fixed 40; beyond the candle extreme; other
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** none until stated (confidence LOW) · **Author approval required:** yes · **Changes:** exit

### RF-D06 - RF TARGET (RF_TARGET_STATUS = UNRESOLVED)

* **Rules:** RF-011 · **Source:** RF p.8 ('Target: OPEN') · **Evidence:** A, D, E · **Classification:** UNRESOLVED
* **Verified meaning:** The guide says OPEN. Two non-rule pieces of evidence point to 60: the p.9 example chart's target box (60.80) and the report's arithmetic (all six RF winners booked Target 2 = 60, each cell decomposing uniquely). Neither is a stated rule.
* **Existing implementation:** no target assigned anywhere (policy_for('RF').t2_points is None; evaluate_exit returns NotEvaluable)
* **Candidate interpretations:** 60 (evidence only); 70; other
* **Quantitative effect (record counts):** exit only; does not affect signal detection
* **Recommended interpretation:** do NOT assign; ask the author (evidence leans to 60) (confidence LOW) · **Author approval required:** yes · **Changes:** exit


## DATA

### DATA-D01 - 'Previous close' for gaps: official close or the last minute print?

* **Rules:** DATA-OFFICIAL-CLOSE-001 · **Source:** ORB p.8; RF p.2; market evidence · **Evidence:** A, E · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** The guides say 'previous close'. The official NSE close = the vendor daily close (9 of 9 externally published closes match - 8 quoted directly, 1 (2026-07-31) derived by subtracting the published point change from the next day's close; the 15:30 minute print matches only 2 of 9 and misses by up to 88 points before the auction regime).
* **Existing implementation:** vendor daily close (prev_close_source = OFFICIAL_DAILY)
* **Candidate interpretations:** official daily close; last 1-minute print at 15:30
* **Quantitative effect (record counts):** PDR confirmed 39 -> 39; PDS invalidated 61 -> 65 if the last print were used (gap direction differs on 9 of 247 sessions)
* **Recommended interpretation:** official daily close (confidence HIGH) · **Author approval required:** no · **Changes:** entry

### DATA-D02 - August 2026 'frozen tail' = NSE Closing Auction Session (NOT corrupt data)

* **Rules:** DATA-CAS-001 · **Source:** market evidence; vendor data · **Evidence:** E · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** From 2026-08-03 the index is frozen 15:15-15:29 and then steps to the official close; 21/21 sessions show it, 0 before; the fresh re-download is identical; Sep/Oct 2026 show the same; the published closes match. Phase 2's 'critical defect' diagnosis was wrong.
* **Existing implementation:** frozen rows inside the window on/after 2026-08-03 are KEPT and flagged; elsewhere they make a session CORRUPT; previous-day levels use ALL candles by default
* **Candidate interpretations:** all candles (chart-faithful, current); continuous session only for previous-day levels
* **Quantitative effect (record counts):** 5 of the 21 auction sessions have their high or low inside the auction candles; the choice changes the output of exactly one PDR/PDS session (2026-08-26: the PDR signal moves from the 09:20 candle to 12:10, zone [24,260.05, 24,334.55] -> [24,247.05, 24,266.85]) and no RF signal; ORB Method 1 invalidated 85 -> 88
* **Recommended interpretation:** all candles (confidence HIGH) · **Author approval required:** no · **Changes:** entry

### DATA-D03 - Missing weekdays and the Phase 1 holiday list

* **Rules:** DATA-QUAL-001 · **Source:** NSE closures (secondary sources) · **Evidence:** E · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** 2026-01-15, 03-26, 03-31 and 05-28 are confirmed closures (NSE circular cited by several sources; not read directly). Phase 1's list wrongly marks 02-17, 03-20, 03-27, 05-27 as holidays (all have full sessions).
* **Existing implementation:** evidence-tiered calendar file
* **Candidate interpretations:** as recorded
* **Quantitative effect (record counts):** none
* **Recommended interpretation:** as recorded (confidence HIGH) · **Author approval required:** no · **Changes:** -

### DATA-D04 - Previous-day strategies on 2025-10-23 (a Muhurat session sits between)

* **Rules:** DATA-QUAL-001 · **Source:** calendar; vendor daily · **Evidence:** E, G · **Classification:** UNRESOLVED
* **Verified meaning:** The previous regular session is 2025-10-20 but the previous closing value is the Muhurat close of 2025-10-21 (25,868.60). Which one the author's chart uses is unknown.
* **Existing implementation:** that one session is NOT evaluated by previous-day strategies
* **Candidate interpretations:** not evaluated (current); zone from 10-20, close from the Muhurat session
* **Quantitative effect (record counts):** 1 session
* **Recommended interpretation:** not evaluated (confidence MEDIUM) · **Author approval required:** yes · **Changes:** trade frequency

### DATA-D05 - Indicator warm-up

* **Rules:** DATA-WARM-001 · **Source:** strategy PDFs are silent · **Evidence:** E · **Classification:** VERIFIED_QUALITATIVE
* **Verified meaning:** Resolved with data: 2025-07/08 minute data (15,789 rows) is loaded as WARM-UP ONLY so every session's EMA(200) is initialised (it reproduces the charts to 0.005 point even on 2025-09-01), and 248 official daily bars precede the first session for the daily 200-day average.
* **Existing implementation:** warm-up data seeds indicators but is never evaluated
* **Candidate interpretations:** as implemented
* **Quantitative effect (record counts):** 3 sessions that were unevaluable are now evaluable
* **Recommended interpretation:** as implemented (confidence HIGH) · **Author approval required:** no · **Changes:** -


## EXEC

### EXE-D01 - Target 2 per strategy

* **Rules:** EXE-T2-001 · **Source:** performance report; strategy guides · **Evidence:** A, E · **Classification:** CONFLICTING
* **Verified meaning:** The report only says 'Target 2 (60 or 70 points, as recorded)'. Guides: IRF 60, ORB 60, PDR 70, PDS 70, RF open. Derived from the report: winners at 70 = 6 (PDR 5, PDS 1); all 74 other winners at 60. See PDR-D07, PDS-D06, RF-D06.
* **Existing implementation:** per-guide values; RF unresolved
* **Candidate interpretations:** per guide; 60 everywhere; per-trade
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** per guide (confidence MEDIUM) · **Author approval required:** yes · **Changes:** exit

### EXE-D02 - Same-bar collisions, end of day, costs, lot size

* **Rules:** EXE-MISSING-001 · **Source:** performance report · **Evidence:** E · **Classification:** UNRESOLVED
* **Verified meaning:** No intrabar rule, no end-of-day outcome, costs excluded. The report applies 65 per lot to the whole year, but NSE's NIFTY lot size was 75 until the Dec-2025/Jan-2026 revision to 65 (secondary sources), so the report's rupee figures for Sep-Dec 2025 are not what 6 real lots would have produced; index-point results are unaffected.
* **Existing implementation:** adverse resolution (stop before target, no favourable fill, breakeven gap at the worse of entry/open); end of day leaves the position open
* **Candidate interpretations:** as implemented
* **Quantitative effect (record counts):** exit only
* **Recommended interpretation:** as implemented (confidence MEDIUM) · **Author approval required:** yes · **Changes:** exit

### EXE-D03 - Trading journal reliability

* **Rules:** EXE-OUT-001 · **Source:** journal workbook vs report · **Evidence:** E · **Classification:** UNRESOLVED
* **Verified meaning:** 190 rows vs a Summary of 189; 5 weekend-dated rows; 6 of 60 strategy-month cells irreproducible. Three attribution differences (Feb ORB<->PDR, Jun IRF<->ORB, Aug extra ORB Target) explain every count difference exactly. RF August (-Rs 17,550) is irreproducible with any 30/35/40 stop.
* **Existing implementation:** journal NOT used as ground truth
* **Candidate interpretations:** author supplies a corrected, timestamped trade list
* **Quantitative effect (record counts):** n/a
* **Recommended interpretation:** request a corrected trade list (confidence HIGH) · **Author approval required:** yes · **Changes:** -
