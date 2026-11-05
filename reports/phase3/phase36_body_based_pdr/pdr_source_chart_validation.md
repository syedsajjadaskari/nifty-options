# PDR source-chart validation (the guide's dated examples)

**Written for:** the strategy owner. The PDF `PDR_Strategy_Guide.pdf` has five annotated examples; four are dated (their drawn zones and entry candles are the Phase 2.2 / 3.3 readings of the chart price tags). This file tests the Phase 3.6 body-based rules against them. Nothing was adjusted to make an example pass.

## What the source says versus the later author clarification

* PDF p.1-2: 'Zone: small box from candle body to upper wick at the previous day's high'; 'Upper boundary: the highest point of the upper wick. Lower boundary: the relevant candle-body level.'
* Author's later clarification (AUTHOR_APPROVED, treated as the later statement by the owner's brief): 'Wick should be ignored, but body should be considered. If a price is only a wick, it should be ignored. If it is a body high, that should be considered when drawing the zone.'
* **The two conflict.** The brief treats the clarification as the later, authoritative statement, but the owner should still confirm explicitly that it supersedes the PDF's wording and the boxes drawn in the PDF figures.

## Evidence from the figures

| example | date | drawn zone | previous-day wick high | previous-day highest body high | drawn ceiling follows | drawn ceiling - body ceiling | body-based zone A |
|---|---|---|---|---|---|---|---|
| Example 1 (p.3) | 2025-09-02 | [24,632.00, 24,640.00] | 24,635.00 (15:00) | 24,632.25 (15:00) | WICK_HIGH | +7.75 | [24,625.10, 24,632.25] |
| Example 2 (p.3) | 2025-10-06 | [24,901.90, 24,905.60] | 24,904.75 (15:05) | 24,899.80 (15:05) | WICK_HIGH | +5.80 | [24,896.10, 24,899.80] |
| Example 3 (p.4) | 2025-10-07 | [25,080.80, 25,084.40] | 25,095.70 (14:50) | 25,084.70 (15:00) | BODY_HIGH | -0.30 | [25,072.40, 25,084.70] |
| Example 4 (p.4) | 2025-11-20 | [26,061.80, 26,074.20] | 26,074.55 (14:40) | 26,062.65 (14:45) | WICK_HIGH | +11.55 | [26,058.60, 26,062.65] |

Examples 1, 2, 4 are drawn up to the wick high; Example(s) 3 up to the body high. Example 3 is the case that contradicted the wick-ceiling engine in Phase 3.4 (its 14:50 spike was a wick-only price); the body-based zone reproduces its drawn shelf.

## The engine against the four dated entry candles

| example | open above body ceiling | entry candle (author) | close above body ceiling | patterns: default thresholds | patterns: example-read thresholds | engine signal at the author's candle (default / example-read) | engine signals that day (default) |
|---|---|---|---|---|---|---|---|
| Example 1 (p.3) | True | 09:25 O 24640.8 H 24653.9 L 24631.65 C 24653.55 | True | none | GOOD_GREEN_BODY | False / False | 09:30 |
| Example 2 (p.3) | True | 09:30 O 24900.45 H 24914.35 L 24881.9 C 24910.8 | True | none | LOWER_PRICE_REJECTION+HAMMER | False / True | 09:35 |
| Example 3 (p.4) | True | 09:20 O 25083.7 H 25120.6 L 25077.1 C 25111.15 | True | none | GOOD_GREEN_BODY | False / True | 09:35 |
| Example 4 (p.4) | True | 09:45 O 26077.5 H 26093.2 L 26068.2 C 26088.65 | True | none | GOOD_GREEN_BODY | False / False | none |

### Reproduced and unresolved

* **Zone and opening:** in all four examples the session opens strictly above the body ceiling and the author's entry candle closes above it (4 of 4).
* **Entry candle accepted by the default (provisional) thresholds:** 0 of 4 - the default numbers pass none of the four author candles as a pattern. With the example-read thresholds (read off these same candles, so circular) the engine signals exactly at the author's candle in 2 of 4.
* **Unresolved:** where the engine does not signal at the author's candle even with the example-read thresholds (Examples with `False / False`), the author's candle is probably both the test and the confirmation (the engine, like Phase 3.5, requires the confirmation to come strictly after the test candle; allowing same-candle confirmation gives 100 signals instead of 87). Not adopted: it is not an author rule.
* **Example 5** is undated in the guide: not reproducible, not used as evidence. **But** Phase 3.3 observed, and the independent reviewer confirmed at 4x zoom, that its entry session's first candle appears to start INSIDE the drawn box with no visible gap above it. If that is right, the author's own example does not satisfy the now author-approved 'open strictly above the zone' rule. Unresolved: the owner should look at Example 5.
* **Floors:** the drawn floors of Examples 1, 2 and 4 are essentially the body top of the wick-high candle, so those boxes lie at or above the body zone and are almost disjoint from it (the body zone sits below them); only the CEILING of Example 3 is reproduced (25,084.70 against the drawn 25,084.40); its drawn floor (25,080.80) is 25055.80 points above the engine's floor (the body low of the anchor candle). The floor is a research convention and does not change any signal.
* The drawn boxes are readings of chart price tags (about +/- 1 point, Phase 3.3); the chart prices differ slightly from the repository data at the open.
