# Proposed rule changes (candidates only; none is active)

Each candidate states the general rule I read from the author's remarks, the alternative readings that the wording allows, and its reach. **They are not ranked or chosen by profitability** (the brief forbids it): the only numbers shown are how many Phase 3.6 trades or signals each would touch, and whether it reproduces the author's own earlier / later remarks.

## C1. IRF Method 2 reference candle (NR4) + entry-candle body (NR5)

Reading F: after the breakout candle (first later close above IRH), take the FIRST red candle that is outside the initial range; its low is the support S and its high the resistance R; the entry is the first later RED candle with body >= 60% that closes below S (support break) or closes back below R after an earlier candle traded above R (resistance break), whichever happens first, before 13:00.

Where the author states a direction, reading F agrees: AC08 and AC09 ('earlier / late entry'): entry earlier than the engine; AC07 ('taken after 5 candles at the 6th'): later; AC01 ('at the resistance itself', manual journal label 10:00): a red candle closing at 24,546.50 against a resistance of 24,546.55. Alternatives that change the result: 'outside the range' = low above IRH (used) or only the close above IRH; body threshold 60 / 50 / 40 / none (see `readings` in each day report). The two outside-range readings give different entries on AC03 (11:15 vs 11:20), so the wording alone does not fix the rule.

## C2. IRF EMA space (NR2)

Reading E: for an IRF short signal, if 0 < (signal close - EMA200 of 5-minute closes) < 27 points (the EMA lies between the entry and target 1), do not enter on that candle; wait for a candle that closes below the EMA. Open: whether the IRF setup then stays valid and how long (the engine has no setup expiry for Method 2), and which method the deferred entry belongs to. It reproduces the author's measurable statement in both dated cases (EMA 2.93 and 25.27 points below the entry); it reaches 9 of 109 executed IRF trades.

## C3. IRF at the day's low (NR3)

Reading L: an IRF entry whose signal candle closes below the lowest low of the session so far is not taken. It matches AC32's second candle (09:35 closes 25,721.45 against 25,727.90) and AC19's 09:25 candle. It does not explain AC19's 'the day should be completely stopped'; whether an IRF activation at the day's low consumes the IRF for the day is a separate decision. It would not change any executed Phase 3.6 IRF trade.

## C4. PDR / PDS 'first candle' entry (NR6)

Reading G: PDR long = the first green candle after the zone is tested that closes above the zone ceiling (the tested candle itself may qualify), with no strength threshold; PDS short = the first red candle at the zone, no strength threshold. In the five PDR examples the candles the author points to have bodies of 31.9%, 36.2%, 49.7%, 57.3% and 63.1% and upper wicks up to 32.6%, i.e. they pass none of the proposed numeric thresholds uniformly. Adopting G would reverse Phase 3.4's replacement of PDR-007 by PDR-A04 (the author's own 'good green body / rejection / hammer' sentence) and, for PDS, PDS-M-001. An earlier first-green reading exists for 19 of 25 executed PDR trades.

## C5. ORB candle strength, trend and inner level (AC04, AC06, AC12, AC14-AC16, AC24, AC28, AC31, AC33, AC37, AC39, AC40)

Thirteen observations say 'ORB should have activated'. The engine's ORB produced no confirmed signal on any of those days; its rejection reasons are: trendline not supportive (Method 2 inner level; no objective construction exists), first-candle strength thresholds (body 60%, opposite wick 20%: the author's days have bodies 22.9-76.2%), the approved previous-close-vs-EMA trend variant, the Gap/200DMA close condition, or no previous-day level broken. No single change explains all of them. Two follow from the strength profile alone: AC39 (lower wick 23.8% against the MODERATE limit of 20%; the LOOSE profile in params.py allows 25%) and AC33 (body 52.2% against 60%; LOOSE needs 50%). The rest need the author's actual ORB inner-level and trend definitions (four of them, AC04, AC06, AC12, AC37, have strong or hammer-shaped first candles and no previous-day level broken, so the Method 2 inner level and trendline - undefined in the source - decide them).

## C6. RF (AC05, AC25, AC36)

AC05 and AC36 conflict with RF-004 (an open above yesterday's high is rejected); AC25 is rejected by the approved trend variant. The author's reading of 'yesterday's range' or of the RF trend must be stated before any change.
