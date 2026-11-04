# Phase 2.2 - decisions only the strategy owner can make

Plain language, most important first. "Today" is what the code does now; nothing below is approved by you except the stop-loss baseline. Numbers quoted are *counts of signals*, not results: they must not be used to pick an answer. Longer evidence is in `phase22_rule_verification.md`.

## Priority 1 - these change which trades exist

**1. Which candle marks the PDR resistance zone?**
Your charts 1, 2 and 4 draw the zone on the candle that made the previous day's high (15:00, 15:05 and 14:40 candles). Your chart 3 (2025-10-07) draws it on a shelf of equal highs around 25,080-25,085 and ignores the sharp 14:50 spike to 25,095.70. The code picks the highest-high candle; two alternatives (latest swing high with a red candle after it; a cluster of repeated highs) were tried and **neither** reproduces chart 3. *Today:* highest-high candle, zone from the candle body top to the wick tip (this fits charts 1, 2 and 4 within 5 points). *Needed from you:* how do you pick the candle - for example "ignore a single spike and use the shelf", or "always the day's high candle"? The same question applies to PDS (support).

**2. What is an "established trend" for ORB Methods 1-2 and RF?**
The guides say price above the 200 EMA is only a basic filter and the trend must be "supported by bullish price structure", with no rule. *Today (your recommendation, a proposal):* the previous session ended above its EMA(200) **and** its last two swing highs and last two swing lows were rising. Finding: your own ORB page-7 example chart (an uptrend) shows the recent swing highs *lower* than earlier ones while the lows rise - a strict "rising highs" rule would reject it. A visual check of RF's two trade charts (p.9) suggests the same: a peak followed by lower highs or a flat range before the gap day (not run through the engine). Effect on counts (not a reason to choose): ORB Method 1 confirmed 9 vs 27, RF 2 vs 12 with the older EMA-only test. *Needed:* keep the rule, drop the "rising highs" part (lows + EMA only), or give your own definition?

**3. Which "open" do your charts use?**
The first 1-minute print of the day and the vendor's published daily open differ by more than 5 points on 98 of 247 sessions (up to 64). Your PDR chart 1 (2025-09-02) shows the published open (24,653.00, a green first candle); our minute data opens at 24,683.25 (a red first candle). It would change the gap direction on 10 sessions and the first-candle colour on 13, which feeds IRF, ORB and RF. *Today:* first 1-minute print; data untouched. *Needed:* which open do you mean when you say "the 09:15 candle's open" and "gap"?

**4. IRF - how many trades, when, and may a failed setup start again?**
No guide says. The literal rules give 874 IRF events in the year (the report records 72 trades). *Today:* every event is logged, three evaluation policies exist (all events: 865 fillable; first per day: 174; one position at a time: 507 - counts only). *Needed:* a daily cap, a latest entry time, re-arming rule. Also: for Method 1, must the failure be the *very next* candle (pages 1, 5, 6, 9, 13) or "the next or following" candle (only the p.14 card)? *Today:* very next.

## Priority 2 - these change exits

**5. Stops.** You approved 35 (40 later) as a research baseline. Please note IRF and PDS guides do give a rule - 35 or 40 by the distance of the recent green candle - but leave the threshold ("exactly 35") and the measurement open; PDR and RF give none; one PDR chart shows a drawn stop of ~30.6. *Needed (optional):* should the baseline later be replaced by the guide's distance rule for IRF/PDS once you define it?

**6. RF target, entry price, direction, "return inside".** The guide says target and entry price are OPEN and never says long or short. *Today:* long; target 60 as a *proposal* (your chart box reads 60.80); entry reference = the close of the candle that closes back inside the range; "return" = a candle closing inside. *Needed:* confirm or replace each.

**7. PDR / PDS Target 2: 70 or 60?** Both guides say 70; the report shows 1 of 6 PDR winners and 2 of 3 PDS winners at 60. *Today:* 70, conflict recorded. *Needed:* a rule for when 60 applies (or which report trades are wrong).

## Priority 3 - candle quality and set-up details

**8. Candle thresholds.** Strong candle: body >= 60%, opposite wick <= 20%. Pin bar: rejection wick >= 2x body and close in the favourable 30%. Small candle: body <= 30%. None is in your guides (PDS says the numbers are undefined). Your drawn candles are far stronger than the limits, so the limits are lenient. Note: your IRF Method-3 picture shows "small candles" with bodies 23-37% of their range, so "body <= 30%" would reject some of your own - it is kept only as a variant; the default asks that the candles stay inside the initial range. *Needed:* approve, change, or define "small" by size.

**9. PDR "very close" to the zone.** Strict: the candle's range must overlap the zone (all four dated PDR charts did). Near-touch (5 points) is a labelled variant. *Needed:* a number, or "strict only".

**10. PDS.** Zone body + lower wick (the text) vs wick only (three example charts, dated tentatively); Method 3 - close below the small support or touch; may it stand alone; entry during or after the candle; size of the "small support".

**11. ORB.** Method 2 (inner level + trendline) cannot be built objectively from the guide; the gap setup's "excessively extended" has no number; the fill price at 09:20 is not stated (we simulate the next minute's open).

## Priority 4 - for Phase 3

**12. Closing auction.** From 2026-08-03 the bars 15:15-15:29 are real index data but cannot be filled. A position still open at 15:15 is reported as unresolved. *Needed:* carry it, exit it at some price, or never hold into 15:15.

**13. A corrected trade list** (journal vs report differ by three attributions; one August RF figure is irreproducible) is still the single best input for validating the engines.
