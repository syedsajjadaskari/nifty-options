# PDR confirmation-pattern classification (Phase 3.6)

**Written for:** the strategy owner. The author requires ONE of three candles and a close above the zone, and says that **fixed body-percentage and wick-size thresholds are not required**. A program still needs a deterministic classification, so the numbers below are a **research convention, not an author rule**: they were carried over from Phase 3.5 (profile `RESEARCH_DEFAULT`) so that the Phase 3.6 difference is only the zone and the opening rule. They were not chosen by profit or by journal agreement.

| pattern | profile RESEARCH_DEFAULT (active, PROVISIONAL) | profile EXAMPLE_LENIENT (sensitivity only) | colour |
|---|---|---|---|
| good green body | bullish; body >= 60% of the range; upper wick <= 20% | body >= 40%; upper wick <= 25% | must be green (a 'green-body' candle) |
| lower-price rejection | lower wick >= 2 x body; close in the top 30% of the range; the low reached the zone ceiling (low <= ceiling) | wick >= 1.5 x body; top 40% | not required (author silent) |
| hammer | lower wick >= 2 x body; upper wick <= 10% of the range; body bottom at >= 60% of the range (a bullish LOWER-wick shape, not the old bearish upper-wick pin bar) | wick >= 1.5 x body; upper wick <= 15%; body position >= 55% | not required (author silent) |

Mandatory for all three: `close > zone ceiling`, strictly (a lower wick may penetrate the zone). When several patterns pass on one candle all are recorded and **one** signal is produced. A zero-range candle passes no pattern (ratios are undefined); a candle with a tiny body and a long lower wick can pass rejection and hammer whatever its colour; a thin candle with no body-percentage, wick or location that fits none of the three is **not** a signal - the classifier never returns True by default.

Every pattern calculation of every executed trade (body %, wicks, wick / body, close position, body position, thresholds, close minus ceiling) is in `entry_condition_details.csv` (rule PDR-B04c rows) and in each trade's daily journal.

## Pattern use among the 87 signals

| sensitivity (signals only) | signals | days |
|---|---|---|
| A, RESEARCH_DEFAULT patterns (ACTIVE) | 87 | 33 |
| B, RESEARCH_DEFAULT patterns | 87 | 33 |
| A, EXAMPLE_LENIENT patterns | 113 | 33 |
| B, EXAMPLE_LENIENT patterns | 113 | 33 |
| A, good green body only | 81 | 33 |
| A, lower-price rejection only | 14 | 10 |
| A, hammer only | 28 | 20 |

The traded PDR signals passed: GOOD_GREEN_BODY 22, LOWER_PRICE_REJECTION 1, HAMMER 1, LOWER_PRICE_REJECTION, HAMMER 1.

Reconciliation of the sensitivity: 87 default signals + 44 lenient-only signals - 18 default signals that disappear under the lenient profile (a different pattern on an earlier candle changes the re-arming sequence) = 113 lenient signals.

## Ambiguous candles preserved for manual review (44)

These candles come after a test of the body zone and close above the body ceiling, but pass a pattern **only** under the example-read thresholds. The default thresholds reject them; the author's 'no fixed threshold' statement means neither answer is wrong. They are **not traded**; they are listed so the owner can judge them (`old_vs_new_pdr_signals.csv`, `row_type = AMBIGUOUS_PATTERN_PROFILE_DEPENDENT`).

| date | candle | lenient pattern(s) | close - ceiling |
|---|---|---|---|
| 2025-09-18 | 14:35 | LOWER_PRICE_REJECTION | +2.90 |
| 2025-10-06 | 09:30 | LOWER_PRICE_REJECTION+HAMMER | +11.00 |
| 2025-10-07 | 09:20 | GOOD_GREEN_BODY | +26.45 |
| 2025-11-17 | 09:40 | GOOD_GREEN_BODY | +33.95 |
| 2025-11-17 | 10:55 | GOOD_GREEN_BODY | +5.75 |
| 2025-11-17 | 11:20 | LOWER_PRICE_REJECTION+HAMMER | +3.90 |
| 2025-11-27 | 09:30 | HAMMER | +64.80 |
| 2025-11-27 | 14:35 | GOOD_GREEN_BODY | +3.60 |
| 2025-11-27 | 15:15 | GOOD_GREEN_BODY | +8.45 |
| 2025-12-23 | 10:05 | GOOD_GREEN_BODY | +10.05 |
| 2025-12-23 | 14:45 | GOOD_GREEN_BODY | +3.45 |
| 2026-01-28 | 09:55 | GOOD_GREEN_BODY | +69.60 |
| 2026-01-28 | 10:15 | GOOD_GREEN_BODY | +26.30 |
| 2026-02-10 | 14:10 | GOOD_GREEN_BODY | +15.60 |
| 2026-02-23 | 10:50 | GOOD_GREEN_BODY | +18.35 |
| 2026-02-23 | 11:10 | GOOD_GREEN_BODY | +42.65 |
| 2026-02-23 | 11:50 | LOWER_PRICE_REJECTION | +5.35 |
| 2026-02-23 | 12:00 | GOOD_GREEN_BODY | +7.05 |
| 2026-02-23 | 13:40 | GOOD_GREEN_BODY | +9.65 |
| 2026-03-05 | 12:05 | LOWER_PRICE_REJECTION | +1.90 |
| 2026-03-05 | 12:25 | GOOD_GREEN_BODY | +62.50 |
| 2026-03-17 | 09:45 | GOOD_GREEN_BODY | +20.75 |
| 2026-03-17 | 10:15 | GOOD_GREEN_BODY | +90.55 |
| 2026-03-17 | 10:40 | LOWER_PRICE_REJECTION+HAMMER | +20.15 |
| 2026-03-17 | 12:55 | GOOD_GREEN_BODY | +13.80 |

... and 19 more in `old_vs_new_pdr_signals.csv`.

## Author decision needed

Numeric definitions of the three patterns, or a handful of labelled example candles, or confirmation that a manual review of the ambiguous candles above is the intended process. Until then no profile is validated.
