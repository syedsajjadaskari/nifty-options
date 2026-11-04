# Author decisions required

> **PARTLY SUPERSEDED BY PHASE 2.2** (`phase22_rule_verification.md`, `phase22_author_decisions.md`): stops are now a USER_APPROVED research baseline (35; ORB 30); RF target 60 is a PROPOSED research value; the PDR zone bottom is the body TOP by default (`PDR-D01` text below said body bottom); strict zone intersection is the default; the trend default is the structure proposal; a new open item `DATA-OPEN-001` (session open price) was found. Where this file and the Phase 2.2 files differ, Phase 2.2 wins.

Plain-language questions, most important first. Each has a **recommended research default** (what the engine uses now). **None of these defaults is approved**; they are not chosen for profit.

`changes` tells you whether the answer alters entries, exits or how many trades occur.


## PRIORITY 1 - decides which trades exist (entry selection) or blocks a strategy

### IRF-D03 (IRF) - How many IRF trades per day, until what time, and may a setup re-arm?
* **What needs deciding:** The written rules produce far more IRF setups than you actually trade. What else decides which setup you take: only the first of the day, a cut-off time, or something else?
* **Why it matters:** 349 Method 1 + 215 Method 2A + 310 Method 2B events a year versus 72 IRF trades in the report; with a 6-candle expiry Method 2A 215 -> 84
* **Choices:** no cap (current); first signal per session; latest entry time; N per day
* **Recommended research default:** keep reporting every occurrence; decide the selection policy at the trade layer once the author states it (do NOT invent 'one per day') (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** UNRESOLVED

### ORB-D02 (ORB) - What is an 'established' uptrend / downtrend?
* **What needs deciding:** How do you decide the market is 'already in an established trend'? Price above the 200 EMA is a start, but what else counts?
* **Why it matters:** ORB Method 1 confirmed 23 -> 31 (BASIC), 23 -> 8 (3 sessions); RF confirmed 12 -> 20 / 12 -> 6
* **Choices:** EMA5M_BASIC; EMA5M_PREV_SESSION; EMA5M_PREV_3_SESSIONS; SMA200_DAILY; EMA200_DAILY
* **Recommended research default:** EMA5M_PREV_SESSION (encodes only RF p.5's explicit rejection) (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** VERIFIED_QUALITATIVE

### PDR-D09 (PDR) - Zone construction: the engine's zone vs the zone drawn in Example 3
* **What needs deciding:** On 2025-10-06 the day's highest candle was a brief spike, but your Example 3 zone sits lower on the late-day shelf. How do you choose which candle marks the zone?
* **Why it matters:** not measured (no objective alternative exists to count)
* **Choices:** highest-high candle (current); ignore single-candle spikes (needs a spike rule); the shelf/cluster of late-day highs (not objectively defined)
* **Recommended research default:** keep, flagged; ask the author how the reversal candle is chosen (confidence LOW)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDR-D05 (PDR) - 'Clear high and reversal identified'
* **What needs deciding:** What makes yesterday's high a 'clear high with reversal' worth marking?
* **Why it matters:** PDR confirmed 39 -> 21 with the 25% depth test
* **Choices:** OFF (current); previous-day reversal depth >= 25% of the day's range
* **Recommended research default:** OFF until defined (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** UNRESOLVED

### RF-D05 (RF) - RF stop: 35 or 40, fixed or the candle extreme
* **What needs deciding:** How do you place the RF stop? The report's RF numbers fit 35/40 in every month except August 2026, where the loss is smaller than two full stops. Was a stop tighter there?
* **Why it matters:** exit only
* **Choices:** fixed 35; fixed 40; beyond the candle extreme; other
* **Recommended research default:** none until stated (confidence LOW)
* **Changes:** exit · **Evidence classification:** UNRESOLVED

### RF-D06 (RF) - RF TARGET (RF_TARGET_STATUS = UNRESOLVED)
* **What needs deciding:** What is the RF target? Your chart box and your results both look like 60 points, but the guide says open.
* **Why it matters:** exit only; does not affect signal detection
* **Choices:** 60 (evidence only); 70; other
* **Recommended research default:** do NOT assign; ask the author (evidence leans to 60) (confidence LOW)
* **Changes:** exit · **Evidence classification:** UNRESOLVED

### EXE-D03 (EXEC) - Trading journal reliability
* **What needs deciding:** Please provide a corrected trade list with date, entry time, strategy AND method, direction, prices, stop and Target-2 used.
* **Why it matters:** n/a
* **Choices:** author supplies a corrected, timestamped trade list
* **Recommended research default:** request a corrected trade list (confidence HIGH)
* **Changes:** nothing in the strategy · **Evidence classification:** UNRESOLVED


## PRIORITY 2 - decides exits / blocks complete-trade backtests

### IRF-D08 (IRF) - How long does a Method 2 setup stay alive?
* **What needs deciding:** If the reversal takes hours to show up, is it still a Method 2 setup?
* **Why it matters:** 6-candle expiry: Method 2A 215 -> 84, Method 2B 310 -> 211
* **Choices:** no expiry (current); expire after N candles
* **Recommended research default:** no expiry until stated (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** UNRESOLVED

### IRF-D13 (IRF) - Stop 35 or 40: how is the green candle's distance measured?
* **What needs deciding:** Which price of the last green candle do you measure from, and is a distance of exactly 35 a 35 or a 40?
* **Why it matters:** stop only; entries unchanged
* **Choices:** green high; green close; highest green high since the setup began; signed distance
* **Recommended research default:** green high, <= 35 -> 35 (confidence LOW)
* **Changes:** exit · **Evidence classification:** PROPOSED_FOR_REVIEW

### ORB-D06 (ORB) - Method 2: inner resistance/support and the trendline
* **What needs deciding:** How exactly do you pick the 'inner' level and draw the trendline? Without a rule Method 2 cannot be tested.
* **Why it matters:** 16 research-variant confirmations (never presented as verified)
* **Choices:** define a construction rule; retire Method 2
* **Recommended research default:** keep blocked (confidence HIGH)
* **Changes:** entry, trade frequency · **Evidence classification:** UNRESOLVED

### ORB-D08 (ORB) - Gap-through-the-200-MA setup: 'excessively extended' and the crossing
* **What needs deciding:** What gap size is 'excessively extended' for the 200-MA gap setup?
* **Why it matters:** Gap setup confirmed 9 -> 7 with a 150-point cap
* **Choices:** no cap; cap at 150 points
* **Recommended research default:** no cap; keep flagged (confidence LOW)
* **Changes:** entry · **Evidence classification:** UNRESOLVED

### PDR-D02 (PDR) - Must the gap-up open lie above the zone?
* **What needs deciding:** Does PDR need the gap-up to open above yesterday's zone (the text), or may it open at/inside it?
* **Why it matters:** PDR confirmed 39 (ABOVE_ZONE); 39 -> 53 (NOT_BELOW_ZONE); 39 -> 119 (ANY, of which 55% have the open BELOW the zone)
* **Choices:** ABOVE_ZONE (text; default); NOT_BELOW_ZONE (open >= zone low); ANY (not recommended)
* **Recommended research default:** ABOVE_ZONE (confidence MEDIUM)
* **Changes:** entry, trade frequency · **Evidence classification:** VERIFIED_QUALITATIVE

### PDR-D06 (PDR) - Stop 35 or 40 'depending on the situation'
* **What needs deciding:** When do you use a 35-point stop for PDR and when 40?
* **Why it matters:** exit only
* **Choices:** same green-candle rule as IRF/PDS; always 35; always 40
* **Recommended research default:** none until stated (confidence LOW)
* **Changes:** exit · **Evidence classification:** UNRESOLVED

### PDR-D07 (PDR) - PDR target 70 - but the report records 60 on one PDR winner
* **What needs deciding:** Was the one PDR winner booked at 60 really a PDR trade? (The journal calls it ORB.)
* **Why it matters:** exit only
* **Choices:** 70 (guide + examples); 60 for the odd trade (report)
* **Recommended research default:** 70 (confidence MEDIUM)
* **Changes:** exit · **Evidence classification:** CONFLICTING

### PDS-D04 (PDS) - Must the gap-down open lie below the zone?
* **What needs deciding:** Must the gap-down open be below yesterday's support zone (the text), or may it open at/inside it?
* **Why it matters:** PDS Method 1 confirmed 9 -> 34, Method 3 15 -> 35 with no condition
* **Choices:** BELOW_ZONE (current); NOT_ABOVE_ZONE; ANY
* **Recommended research default:** BELOW_ZONE (text) pending the PDR decision (confidence MEDIUM)
* **Changes:** entry, trade frequency · **Evidence classification:** VERIFIED_QUALITATIVE

### PDS-D05 (PDS) - PDS stop 35/40: distance of the recent green candle
* **What needs deciding:** See the IRF stop question.
* **Why it matters:** exit only
* **Choices:** as IRF-D13
* **Recommended research default:** as IRF-D13 (confidence LOW)
* **Changes:** exit · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDS-D06 (PDS) - PDS target 70 - but the report records 60 on two of three PDS winners
* **What needs deciding:** Two PDS trades were booked at 60 points although the guide says 70. Did the PDS target change, or were those exits discretionary?
* **Why it matters:** exit only
* **Choices:** 70 (guide); 60 (report); author's discretionary change
* **Recommended research default:** 70 (confidence LOW)
* **Changes:** exit · **Evidence classification:** CONFLICTING

### RF-D04 (RF) - RF exact entry price
* **What needs deciding:** At what price do you enter RF once price is back inside the range?
* **Why it matters:** entry price only
* **Choices:** close of the return candle; next candle open
* **Recommended research default:** close of the return candle (confidence LOW)
* **Changes:** entry timing · **Evidence classification:** UNRESOLVED

### EXE-D01 (EXEC) - Target 2 per strategy
* **What needs deciding:** State the Target-2 distance for each strategy.
* **Why it matters:** exit only
* **Choices:** per guide; 60 everywhere; per-trade
* **Recommended research default:** per guide (confidence MEDIUM)
* **Changes:** exit · **Evidence classification:** CONFLICTING


## PRIORITY 3 - entry thresholds (placeholders in use)

### IRF-D04 (IRF) - Method 2: what does 'extends further upward' mean?
* **What needs deciding:** How far or how long must price keep rising after the breakout before a reversal counts as Method 2?
* **Why it matters:** Method 2A 215 -> 334; Method 2B 310 -> 321
* **Choices:** E1 higher high than the breakout candle; E2 a later candle also closes above IRH
* **Recommended research default:** E1 (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** PROPOSED_FOR_REVIEW

### IRF-D06 (IRF) - What is 'recent support'?
* **What needs deciding:** Which low counts as 'recent support': the last small pullback low, a bigger swing low, or the lowest of the last few candles?
* **Why it matters:** Method 2A 215 -> 154 (K2); 215 -> 309 (N3)
* **Choices:** SWING_K1; SWING_K2 (5-candle fractal); LAST_N3 (lowest low of the last 3 candles)
* **Recommended research default:** SWING_K1 (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** PROPOSED_FOR_REVIEW

### IRF-D10 (IRF) - Method 3: how many 'small candles' inside the range?
* **What needs deciding:** How many small candles inside the opening range must precede the sweep, and how small is small?
* **Why it matters:** Method 3 sweeps passing compression 37 -> 27 (N=3); 37 -> 33 (size rule). Method 3 CONFIRMED signals: 0 under every candidate
* **Choices:** N = 2 (literal minimum); N = 3; N = 4 (Figure 5); also require each range <= 50% of the IR height
* **Recommended research default:** N = 2 (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** PROPOSED_FOR_REVIEW

### ORB-D04 (ORB) - Strong candle / pin bar / rejection thresholds
* **What needs deciding:** What makes a first candle 'strong' - give a body-to-range ratio and the largest acceptable wick.
* **Why it matters:** ORB Method 1 confirmed 23 -> 15 (strict), 23 -> 31 (loose)
* **Choices:** STRICT; MODERATE; LOOSE
* **Recommended research default:** MODERATE placeholder (confidence LOW)
* **Changes:** entry, trade frequency · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDS-D01 (PDS) - 'Good red candle'
* **What needs deciding:** What body size makes a red candle 'good' at the PDS zone?
* **Why it matters:** PDS Method 1 confirmed 9 -> 3 (strict), 9 -> 11 (loose)
* **Choices:** STRICT; MODERATE; LOOSE
* **Recommended research default:** MODERATE placeholder (confidence LOW)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDS-D02 (PDS) - HPR pin bar ratios
* **What needs deciding:** How long must the upper wick be, relative to the body, for the PDS pin bar?
* **Why it matters:** PDS Method 2 confirmed 0 under the default
* **Choices:** STRICT; MODERATE; LOOSE
* **Recommended research default:** MODERATE placeholder (confidence LOW)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDS-D03 (PDS) - Method 3: size of the 'small support', close vs touch, stand-alone use
* **What needs deciding:** For PDS Method 3: how small is the small support, does a close or a touch break it, and can it be used without a weak red candle first?
* **Why it matters:** PDS Method 3 confirmed 15 -> 16 (touch); 15 -> 16 (stand-alone)
* **Choices:** close vs touch; after weak red only vs stand-alone
* **Recommended research default:** as implemented (confidence LOW)
* **Changes:** entry · **Evidence classification:** UNRESOLVED

### RF-D02 (RF) - 'Price returns inside the range'
* **What needs deciding:** After the close below the opening range, must price close back inside, merely touch it, or do it on the very next candle?
* **Why it matters:** RF confirmed 12 -> 14 (R2), 12 -> 7 (R3)
* **Choices:** R1 close inside; R2 touch of RF Low; R3 only the very next candle
* **Recommended research default:** R1 (confidence MEDIUM)
* **Changes:** entry, trade frequency · **Evidence classification:** VERIFIED_QUALITATIVE

### EXE-D02 (EXEC) - Same-bar collisions, end of day, costs, lot size
* **What needs deciding:** What happens to a trade still open at the close, and was the lot size really 65 all year?
* **Why it matters:** exit only
* **Choices:** as implemented
* **Recommended research default:** as implemented (confidence MEDIUM)
* **Changes:** exit · **Evidence classification:** UNRESOLVED


## PRIORITY 4 - quick confirmations of conflicts and wording

### IRF-D01 (IRF) - Method 1: the very next candle, or the next or the following candle?
* **What needs deciding:** Does Method 1 need the failure on the immediately following candle, or may it come one candle later?
* **Why it matters:** Method 1 confirmed 349 -> 352; Method 2A 215 -> 197 (a later failure takes setups from Method 2)
* **Choices:** very next candle (4 of 5 passages + figure); next or following candle (p.14 card)
* **Recommended research default:** very next candle (confidence HIGH)
* **Changes:** entry, trade frequency · **Evidence classification:** CONFLICTING

### IRF-D02 (IRF) - Method 1: what counts as 'closing back inside the range' at the edges?
* **What needs deciding:** If the failure candle closes not just back inside the range but all the way below its low, does it still count as Method 1?
* **Why it matters:** Method 1 confirmed 349 -> 356
* **Choices:** literal (above); a close below IRL also counts
* **Recommended research default:** literal (confidence MEDIUM)
* **Changes:** entry, trade frequency · **Evidence classification:** UNRESOLVED

### IRF-D09 (IRF) - Method 2B: may the push above resistance and the closing red candle be one candle?
* **What needs deciding:** Must the push above resistance happen on an earlier candle than the red candle that closes back below it?
* **Why it matters:** measured on request (boundary tested)
* **Choices:** same candle allowed (current); an earlier candle must have pushed above
* **Recommended research default:** same candle allowed (confidence LOW)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW

### IRF-D11 (IRF) - Method 3: the 60-70% wick criterion
* **What needs deciding:** 'About 60-70% of the wick above the range': is a bigger sweep (say 90%) also fine?
* **Why it matters:** no change in confirmed counts (0 Method 3 confirmed under every band); of 37 candidate sweeps 32 have a share below 60%
* **Choices:** 0.60-0.70; >= 0.60; 0.55-0.75
* **Recommended research default:** keep the literal 0.60-0.70 band (current default) unless you want stronger sweeps counted (confidence MEDIUM)
* **Changes:** entry · **Evidence classification:** VERIFIED_QUALITATIVE

### IRF-D12 (IRF) - Method 3: 'or a Higher price rejection candle also works' (p.14 card only)
* **What needs deciding:** The quick card mentions a 'higher price rejection candle' for Method 3 but no page defines it. What is it, or should it be removed?
* **Why it matters:** not measurable
* **Choices:** define it; delete it from the card
* **Recommended research default:** leave unimplemented (confidence HIGH)
* **Changes:** entry · **Evidence classification:** UNRESOLVED

### ORB-D01 (ORB) - '200 DMA', '200 EMA' or '200 MA'?
* **What needs deciding:** Is the '200 DMA' in the ORB guide the same 200-period line as the 200 EMA on your 5-minute chart? (The PDR charts say yes.)
* **Why it matters:** ORB Method 1 confirmed 23 -> 13 under the daily SMA trend; Gap setup confirmed 9 -> 0 under the daily SMA
* **Choices:** EMA(200) on 5-minute closes; SMA(200) of daily closes; EMA(200) of daily closes
* **Recommended research default:** EMA(200) on 5-minute closes (confidence HIGH (PDR/RF charts) / MEDIUM (ORB wording))
* **Changes:** entry, trade frequency · **Evidence classification:** CONFLICTING

### ORB-D03 (ORB) - Previous-day resistance / support: a line or a zone, and which candle?
* **What needs deciding:** Is 'previous-day resistance' simply yesterday's high, or a zone you draw around yesterday's reversal?
* **Why it matters:** continuous-session-only level: ORB Method 1 invalidated 85 -> 88; confirmed unchanged
* **Choices:** previous high/low (all candles); previous high/low (continuous session only); a PDR-style body-to-wick zone
* **Recommended research default:** previous high/low, all candles (confidence MEDIUM)
* **Changes:** entry · **Evidence classification:** VERIFIED_QUALITATIVE

### ORB-D07 (ORB) - 'Near the EMA - wait for a convincing close'
* **What needs deciding:** How close to the EMA is 'near', and what does 'wait for a convincing close' mean when the decision is at 09:20?
* **Why it matters:** Method 2 research variant only
* **Choices:** as implemented; wait for the next candle
* **Recommended research default:** keep (confidence LOW)
* **Changes:** entry · **Evidence classification:** UNRESOLVED

### PDR-D03 (PDR) - 'Very close approach' to the zone
* **What needs deciding:** How many points away still counts as 'a test of the zone'?
* **Why it matters:** PDR confirmed 39 -> 37 (0), 39 -> 41 (10)
* **Choices:** 0; 5; 10 points
* **Recommended research default:** 5 points (placeholder) (confidence LOW)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW

### PDR-D08 (PDR) - Re-entries on the same day
* **What needs deciding:** After a PDR trade, may a second retest the same day be traded?
* **Why it matters:** not measured
* **Choices:** first only; every retest
* **Recommended research default:** first only (confidence LOW)
* **Changes:** trade frequency · **Evidence classification:** PROPOSED_FOR_REVIEW

### RF-D01 (RF) - RF trade direction
* **What needs deciding:** Confirm that RF is a long-only setup.
* **Why it matters:** direction only
* **Choices:** long
* **Recommended research default:** long (confidence HIGH)
* **Changes:** entry · **Evidence classification:** PROPOSED_FOR_REVIEW


## PRIORITY 5 - resolved from evidence; confirm only if you disagree

### DATA-D04 (DATA) - Previous-day strategies on 2025-10-23 (a Muhurat session sits between)
* **What needs deciding:** For the day after Diwali Muhurat trading, which close and which session's high/low do you use?
* **Why it matters:** 1 session
* **Choices:** not evaluated (current); zone from 10-20, close from the Muhurat session
* **Recommended research default:** not evaluated (confidence MEDIUM)
* **Changes:** trade frequency · **Evidence classification:** UNRESOLVED
