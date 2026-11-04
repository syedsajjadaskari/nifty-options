# PDR - what the original guide actually requires (source-rule verification)

**Written for:** the strategy owner. Source: `docs/strategy_docs/PDR_Strategy_Guide.pdf` (4 pages). I read the text layer of every page and rendered all four pages to images; **pages 1-2 contain text and tables only (no figures)**, pages 3-4 contain the checklist and the five chart examples. Earlier AI summaries (Phase 2.2 research, registry rows PDR-001..012) were consulted only after reading the PDF. Every statement below is tagged **EXPLICIT** (the words are on the page), **FIGURE** (read off a chart; calibrated reading, +/- 1 point) or **UNRESOLVED** (the guide does not say).

## 1. The text, page by page

| page / section | what it says (quotation) | kind |
|---|---|---|
| p.1 table 'Strategy at a Glance' | 'Concept: Yesterday's resistance zone is expected to act as support after a gap-up open.' 'Zone: Small box from candle body to upper wick at the previous day's high/reversal.' 'Next-day condition: Market must open gap up.' 'Trigger: Price returns to the zone, then a green candle forms.' 'Target 70 points (fixed).' 'Stop-loss 35 or 40 points, depending on the situation.' | EXPLICIT |
| p.1 s2 Overview | 'When the market opens gap up and then pulls back into the marked zone, the zone is watched to see whether it now works as support. If a green candle forms after the zone is tested, the trade is taken.' 'Sequence: Previous day's high and reversal -> Mark zone -> Gap-up open -> Price returns to zone -> Support test -> Green candle -> Entry.' | EXPLICIT (purpose + sequence) |
| p.1 s3.1 | 'Find the high where price reached a peak and then reversed. Locate the candle associated with that high. Note the candle's body and upper wick.' | EXPLICIT |
| p.2 s3.2 | 'Upper boundary: the highest point of the upper wick. Lower boundary: the relevant candle-body level. Draw a small rectangle ... Extend the rectangle to the right so it stays visible on the next trading day.' 'The zone is an area, not a single exact price. Mark only the actual resistance shown by price action, not the whole surrounding move.' | EXPLICIT (which body edge: UNRESOLVED) |
| p.2 s4.1 | 'The market must open gap up. Do not enter at the open. Wait for price to come back toward the marked zone. If price keeps rising without returning to the zone, there is no setup.' | EXPLICIT (gap size, reference close: UNRESOLVED) |
| p.2 s4.2 | Interaction table: 'Wick touches zone / Body touches zone / Price enters zone (Price moves inside the rectangle) / Very close approach (Price comes close enough to count as a test of the zone)'. 'Price does not need to hit one exact level. A move that stays far from the zone does not qualify.' | EXPLICIT ('very close': UNRESOLVED) |
| p.2 s4.3 | 'After the zone has been tested, wait for a green candle and take the long entry on that confirmation.' | EXPLICIT - no wording about where the green candle closes |
| p.3 s6 checklist | 'Previous day: clear high and reversal identified' / 'Zone drawn from candle body to upper wick and extended forward' / 'Next day opens gap up' / 'Price returned to the zone (wick, body, inside, or very close)' / 'Green candle formed after the interaction' / 'Entry taken; target 70 points; stop-loss 35 or 40 points' | EXPLICIT |

## 2. The four questions of the audit

### A. How is the resistance zone built?

* **EXPLICIT:** the zone belongs to 'the high where price reached a peak and then reversed' of the previous day; it is a small rectangle from the candle's body level up to the highest point of its upper wick (p.1 s3.1, p.2 s3.2).
* **UNRESOLVED:** the text never says 'the absolute highest candle of the day'; it never says 'repeated shelf' or 'several candles'; it does not say which body edge ('the relevant candle-body level'); it gives no definition of 'clear high and reversal'.
* **FIGURE (calibrated in Phase 2.2 and re-checked against the data in `source_example_checks.csv`):** Example 1 (2025-09-02), Example 2 (2025-10-06) and Example 4 (2025-11-20) draw the zone on the candle that made the previous session's high, from its body top to its wick tip (Example 4 within 0.4 point). Example 3 (2025-10-07) draws a thin box on a late-session **shelf of equal highs** (about 25,081-25,084) and skips the single 14:50 spike candle (25,095.70): the only figure that uses several candles. A PDR-style picture on page 9 of the RF guide (not part of the PDR guide) shows a long entry far below its zone; it is **not used as evidence**. So the figures support 'the candle at a clear high' (and, once, a shelf), not one mechanical rule.
* **Engine reading (owner-approved research candidate B):** the latest confirmed swing high (2 candles each side) that has a red candle among the peak and the next two; [body top, wick high]. It is the previous day's high candle in only 13 of the 54 PDR trades (41 differ); among the 27 affected trades 22 differ. Whether that is 'the high where price reached a peak and then reversed' is exactly what the guide leaves open.

### B. Opening conditions

* **EXPLICIT:** the market must open gap up (p.1 table, p.2 s4.1); do not enter at the open; wait for a return toward the zone; no setup if price keeps rising.
* **UNRESOLVED:** gap size (any gap qualifies in the code), the reference price of the gap (the code uses the official previous close), whether the **open must lie above the zone** (the overview says the market 'pulls back into the marked zone', which implies it; it is stated nowhere as a rule), and any requirement on the first candle (none is stated).

### C. Retest conditions

* **EXPLICIT:** a wick touch, a body touch, price inside the rectangle, or a 'very close approach' all count as the zone being tested; the price does not have to hit one exact level; a move that stays far from the zone does not qualify (p.2 s4.2, p.3 checklist).
* **Not addressed at all:** price crossing **below the zone floor**; price returning to the zone **from below**; how far a candle may trade through the zone; whether a candle that closes through the zone still counts as a test. The checklist item 'Price returned to the zone (wick, body, inside, or very close)' is satisfied by any candle whose range overlaps the rectangle, which every one of the audited trades has.
* **FIGURE:** price does trade below the drawn floor in the author's examples, but mostly in the **confirmation candle's own lower wick**: Example 2's green candle wicks 20.0 points below the drawn floor and Example 3's 3.7 (Example 1: 0.35, inside the calibration error); the candles BEFORE the confirmation candle (the retest proper) have their lowest low Example 1 +1.20, Example 2 -3.25, Example 3 +2.70, Example 4 +2.25 points from the drawn floor (negative = below). Example 2's last test candle also closes 0.05 below the drawn floor (inside the +/-1 reading error). So the figures show wick penetration of the floor on the confirmation candle, and a retest that holds above the floor in three of four examples (Example 2 breaks it by 3.25 points on a 3.7-point box).

### D. The confirmation candle

* **EXPLICIT:** 'a green candle' formed 'after the zone has been tested' / 'after the interaction' (p.1 overview, p.2 s4.3, p.3 checklist). No candle-strength threshold, no body or wick size.
* **UNRESOLVED:** any requirement that the green candle close above the floor, or above the ceiling, or that the zone 'held'. The only wording in this direction is the **purpose** statement - the zone is watched 'to see whether it now works as support' (p.1 s2) and the sequence has a 'Support test' step - which describes why the setup exists but does not define a numerical or positional test.
* **FIGURE:** in all four dated examples the green confirmation candle closes **above the drawn ceiling** Example 1 by 13.6, Example 2 by 5.2, Example 3 by 26.8, Example 4 by 14.4 points (and well above the floor); Example 5 (undated) is drawn the same way. No figure shows a confirmation close below the floor.

## 3. Source evidence on whether a zone-hold confirmation is required

| points towards requiring a hold (close at/above the zone) | points towards NOT requiring one |
|---|---|
| p.1: 'expected to act as support'; 'watched to see whether it now works as support'; the sequence has a 'Support test' before the green candle | p.2 s4.3 and the p.3 checklist state only 'a green candle after the interaction' - nothing about where it closes |
| All four dated examples (and Example 5's drawing) end with a confirmation close above the ceiling | 'Price enters zone' is a valid interaction; 'Price does not need to hit one exact level' |
| p.2: 'A move that stays far from the zone does not qualify' - the zone is meant to be where the action is | In Examples 2 and 3 the confirmation candle's own wick trades below the drawn floor (20.0 and 3.7 points) before it closes above the ceiling; Example 2's last test candle closes at the floor |
| p.2 s4.1: do not enter at the open; wait for price to come back TOWARD the zone (a pullback from above) | The guide never says what a close through the zone means, nor gives a threshold; any rule here would be invented |

**Conclusion (unchanged by any profit consideration):** the guide neither **requires** nor **forbids** a zone-hold confirmation. It is **UNRESOLVED in the source**. A hold condition is consistent with the *purpose* and with every dated figure, but it is not written, so adding it would be a new rule that only the owner can approve.

## 4. The 27 affected trades against these questions

Independent count from the raw data: **27 of 54** PDR trades (long, bullish confirmation candle) closed below the selected zone floor (derived, not hard-coded; `independent_audit.md` repeats the derivation by a second route). Confirmation close position over all 54 trades: above the ceiling 20, inside the zone 7, below the floor 27.

| written condition (page) | holds for the 27? |
|---|---|
| gap-up open (p.1, p.2 s4.1) | 27 of 27 satisfy all four written conditions below |
| not entered at the open (p.2 s4.1) | all (the earliest possible fill is 09:25) |
| zone interaction before the confirmation (p.2 s4.2, p.3) | all (the test candle's range overlaps the rectangle) |
| green candle after the interaction (p.2 s4.3, p.3) | all |
| close at/above the floor or ceiling | **not written anywhere** |

Distance of the confirmation close below the floor (points): min 2.30, median 23.85, max 91.10. Distribution: <= 5 points 2, 5-10 3, 10-25 9, 25-50 6, > 50 7. The test candle itself closed below the floor in 14 of the 27; the lowest price of the retest was 17.90-169.65 points (median 47.00) below the floor, against 0.35 / 20.0 / 3.7 / none in the author's Examples 1-4.

## 5. Classification (decision rule)

Applied in this order, to each affected trade, **without reading any outcome or P&L**: (1) DATA_OR_IMPLEMENTATION_ISSUE if an engine export differs from the raw reconstruction or the zone's source candle lies in the closing-auction window; (2) SOURCE_CONTRADICTED if an explicit written condition is violated; (3) ZONE_SELECTION_DISPUTED if another source-plausible zone (the previous-day-high candle A, or the repeated-highs shelf C) would fire on the SAME confirmation candle with its close at/above that zone's floor - the entry would then be acceptable under another reading of 'which resistance'; (4) INSUFFICIENT_EVIDENCE if the sequence cannot be reconstructed; (5) otherwise SOURCE_AMBIGUOUS. SOURCE_SUPPORTED is reserved for a sequence the guide clearly allows **and** that matches what its figures show; every written checklist item is satisfied by all 27, but no text or figure addresses a close through the zone, so none qualifies.

| classification | trades |
|---|---|
| SOURCE_AMBIGUOUS | 26 |
| ZONE_SELECTION_DISPUTED | 1 |
| SOURCE_SUPPORTED | 0 |
| SOURCE_CONTRADICTED | 0 |
| DATA_OR_IMPLEMENTATION_ISSUE | 0 |
| INSUFFICIENT_EVIDENCE | 0 |

A secondary flag marks the 22 affected trades whose zone is not the previous-day-high candle (the zone-selection question is open for them too, even where it does not change the result). **Reading the zero counts:** SOURCE_SUPPORTED and SOURCE_CONTRADICTED are zero by the nature of the rule and the evidence - the four written conditions are guaranteed by how a PDR signal is generated, and no figure shows a close through the zone - they are not a measured finding. The ZONE_SELECTION_DISPUTED test assumes reading B (close at/above the floor) for the alternative zone; the one trade it flags (20260506-1-PDR) closes inside zone C, 7.5 points below that zone's ceiling, and would not pass reading C. Because 26 trades share one label, an informational severity column separates them (it is not used by the classification):

| severity of the close below the floor | trades |
|---|---|
| FAR (> 25 points); the test candle closed at/above the floor | 4 |
| FAR (> 25 points); the test candle itself closed below the floor | 9 |
| MODERATE (5-25 points); the test candle closed at/above the floor | 8 |
| MODERATE (5-25 points); the test candle itself closed below the floor | 4 |
| NEAR_MISS (<= 5 points); the test candle closed at/above the floor | 1 |
| NEAR_MISS (<= 5 points); the test candle itself closed below the floor | 1 |

## 6. Counterfactual diagnostic (counts only; no re-run, no P&L, no recommendation)

| reading | definition | of 54 trades satisfying | of the 27 affected satisfying | source evidence |
|---|---|---|---|---|
| A | existing rule: zone interaction followed by any green candle | 54 | 27 | the written text (pp.1-3: 'After the zone has been tested, wait for a green candle'); no close-location wording |
| B | green confirmation closes at or above the zone floor | 27 | 0 | PROPOSED: not written in the guide; consistent with all four dated examples (every confirmation closes above the ceiling) but never stated |
| C | green confirmation closes above the zone ceiling | 20 | 0 | PROPOSED: not written in the guide; consistent with all four dated examples (every confirmation closes above the drawn ceiling) - the strictest reading that still fits them; but 1 of the 5 journal-matched PDR trades (20260605-1) closes inside the zone and would not satisfy it |
| D | confirmation closes at/above the floor AND the retest low stays at/above the floor | 8 | 0 | PROPOSED: includes the confirmation candle's own wick, which in the author's Examples 2 and 3 trades 20.0 and 3.7 points below the drawn floor before closing above the ceiling (see source_example_checks.csv), so D would not have accepted those two examples |
| D2 | sensitivity of D: the retest low is taken over the candles BEFORE the confirmation candle only | 10 | 0 | PROPOSED (sensitivity row, not one of the four requested readings): the retest low excludes the confirmation candle's own wick; it holds for Examples 1, 3 and 4 and fails Example 2 by 3.25 points on a 3.7-point box, so the figures cannot separate D2 from a tolerant D2 |

By construction none of the 27 affected trades can satisfy B, C or D (their close is below the floor), so the counts also show how many of the other trades each reading would keep. A is the written text; B and C are not written but fit all four dated figures (C is the strictest reading that still fits them; yet one of the five journal-matched trades, 20260605-1, closes inside the zone and would fail C). D includes the confirmation candle's own wick, which trades below the drawn floor in Examples 2 and 3, so D would not have accepted those two examples; the sensitivity D2 (retest low before the confirmation candle) holds for Examples 1, 3 and 4 and fails Example 2 by 3.25 points, so the figures cannot separate D2 from a tolerant D2. None of these is recommended, and none was chosen by its win rate or profit.

## 7. Source figures versus the data

| example | date | zone reading | zone [floor, ceiling] | retest low vs floor | confirmation close vs floor | vs ceiling | position |
|---|---|---|---|---|---|---|---|
| Example 1 (p.3) | 2025-09-02 | drawn zone | [24632.00, 24640.00] | -0.35 (before the confirmation candle: 1.2) | 21.55 | 13.55 | ABOVE_CEILING |
| Example 1 (p.3) | 2025-09-02 | engine zone B | [24632.25, 24635.00] | -0.6 (before the confirmation candle: 0.95) | 21.3 | 18.55 | ABOVE_CEILING |
| Example 1 (p.3) | 2025-09-02 | previous-day-high zone A | [24632.25, 24635.00] | -0.6 (before the confirmation candle: 0.95) | 21.3 | 18.55 | ABOVE_CEILING |
| Example 1 (p.3) | 2025-09-02 | shelf zone C (not the example's own entry) | [24617.10, 24623.00] | -79.7 (before the confirmation candle: -61.7) | -52.5 | -58.4 | BELOW_FLOOR |
| Example 2 (p.3) | 2025-10-06 | drawn zone | [24901.90, 24905.60] | -20.0 (before the confirmation candle: -3.25) | 8.9 | 5.2 | ABOVE_CEILING |
| Example 2 (p.3) | 2025-10-06 | engine zone B | [24899.80, 24904.75] | -17.9 (before the confirmation candle: -1.15) | 11.0 | 6.05 | ABOVE_CEILING |
| Example 2 (p.3) | 2025-10-06 | previous-day-high zone A | [24899.80, 24904.75] | -17.9 (before the confirmation candle: -1.15) | 11.0 | 6.05 | ABOVE_CEILING |
| Example 2 (p.3) | 2025-10-06 | shelf zone C (no sequence) | [24842.15, 24850.75] |  (before the confirmation candle: ) |  |  |  |
| Example 3 (p.4) | 2025-10-07 | drawn zone | [25080.80, 25084.40] | -3.7 (before the confirmation candle: 2.7) | 30.35 | 26.75 | ABOVE_CEILING |
| Example 3 (p.4) | 2025-10-07 | engine zone B | [25077.25, 25095.70] | -0.15 (before the confirmation candle: 6.25) | 33.9 | 15.45 | ABOVE_CEILING |
| Example 3 (p.4) | 2025-10-07 | previous-day-high zone A | [25077.25, 25095.70] | -0.15 (before the confirmation candle: 6.25) | 33.9 | 15.45 | ABOVE_CEILING |
| Example 3 (p.4) | 2025-10-07 | shelf zone C | [25072.20, 25088.20] | 4.9 (before the confirmation candle: 11.3) | 38.95 | 22.95 | ABOVE_CEILING |
| Example 4 (p.4) | 2025-11-20 | drawn zone | [26061.80, 26074.20] | 2.25 (before the confirmation candle: 2.25) | 26.85 | 14.45 | ABOVE_CEILING |
| Example 4 (p.4) | 2025-11-20 | engine zone B | [26061.50, 26074.55] | 2.55 (before the confirmation candle: 2.55) | 27.15 | 14.1 | ABOVE_CEILING |
| Example 4 (p.4) | 2025-11-20 | previous-day-high zone A | [26061.50, 26074.55] | 2.55 (before the confirmation candle: 2.55) | 27.15 | 14.1 | ABOVE_CEILING |
| Example 4 (p.4) | 2025-11-20 | shelf zone C (no sequence) | [26025.35, 26031.45] |  (before the confirmation candle: ) |  |  |  |

Rows whose confirmation candle is not the example's own entry candle (`is_the_examples_own_entry_candle` = False, typically the shelf zone C on another part of the day) are unrelated sequences and say nothing about the example. The drawn zones are the Phase 2.2 readings of the chart price tags (about +/- 1 point), but the drawn edges also deviate from the candle edges: Example 1's drawn ceiling (24,640) is 5.0 above the previous day's wick tip (24,635.0) and Example 2's drawn floor is 2.1 above the candle's body top. The figures' own candles also differ from the repo data at the open (Example 1's first candle is green in the figure and red in the data, Example 4's first candle shows a small upper wick the data does not have); the sequences are unaffected. Example 3's engine zone is [25,077.25, 25,095.70] (18.45 points, built from the 14:50 spike candle), against the drawn 3.6-point shelf; the engine rejects that day because the open (25,087.55) is inside its zone (an earlier registry note quoting a 38.6-point box is not reproduced). **Example 5** (undated, no axis) could not be matched to the data. Read at 5x zoom: its zone starts at a peak candle about one session earlier, and the entry session appears to open roughly flat inside/at the zone with no visible gap-up above it, which would bear on the gap-up rule and on PDR-011 (open above the zone). This is a low-resolution reading and **the owner should look at it**. The three examples the engine reproduces (1, 2, 4) all match a journal PDR trade exactly (`manual_journal_comparison.csv`); the journal also has a PDR row on 2025-10-07 09:20, the Example 3 date and its confirmation candle, which the engine does not trade.
