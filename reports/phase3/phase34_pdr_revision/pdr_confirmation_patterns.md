# PDR confirmation patterns

**Written for:** the strategy owner. The author requires ONE of three candles (OR logic) and a close strictly above the zone ceiling. The shapes are not numerically defined by the author; the numbers below are PROPOSED_FOR_REVIEW.

| pattern | default rule (RESEARCH_DEFAULT) | example-read profile (EXAMPLE_LENIENT, sensitivity only) | colour |
|---|---|---|---|
| good green body | bullish; body >= 60% of the range; upper wick <= 20% | body >= 40%; upper wick <= 25% | must be green |
| lower-price rejection | lower wick >= 2 x body; close in the top 30% of the range; the low reached the zone (low <= ceiling) | wick >= 1.5 x body; top 40% | NOT required (author silent) |
| hammer | lower wick >= 2 x body; upper wick <= 10% of the range; body bottom at >= 60% of the range (a bullish LOWER-wick shape - not the bearish upper-wick pin bar) | wick >= 1.5 x body; upper wick <= 15%; body position >= 55% | NOT required (author silent) |

Common mandatory condition (PDR-A05, AUTHOR_APPROVED): `close > zone ceiling`, strictly. No pattern overrides it. A lower wick may penetrate the zone; the whole candle need not stay above it. Zero-range candles pass no pattern (ratios are undefined) and the engine never divides by zero. When several patterns pass on one candle all are recorded and one signal is produced.

## The guide's four dated entry candles against both profiles

| example | profile | body / upper wick / lower wick | close vs drawn ceiling | patterns passed | qualifies (drawn zone) |
|---|---|---|---|---|---|
| Example 1 (p.3) | RESEARCH_DEFAULT | 57% / 2% / 41% | 13.55 | none | False |
| Example 1 (p.3) | EXAMPLE_LENIENT | 57% / 2% / 41% | 13.55 | GOOD_GREEN_BODY | True |
| Example 2 (p.3) | RESEARCH_DEFAULT | 32% / 11% / 57% | 5.2 | none | False |
| Example 2 (p.3) | EXAMPLE_LENIENT | 32% / 11% / 57% | 5.2 | LOWER_PRICE_REJECTION+HAMMER | True |
| Example 3 (p.4) | RESEARCH_DEFAULT | 63% / 22% / 15% | 26.75 | none | False |
| Example 3 (p.4) | EXAMPLE_LENIENT | 63% / 22% / 15% | 26.75 | GOOD_GREEN_BODY | True |
| Example 4 (p.4) | RESEARCH_DEFAULT | 45% / 18% / 37% | 14.45 | none | False |
| Example 4 (p.4) | EXAMPLE_LENIENT | 45% / 18% / 37% | 14.45 | GOOD_GREEN_BODY | True |

Under the default thresholds none of the four candles passes a pattern although all four close above the drawn ceiling; under the example-read thresholds all four pass (Example 2 via rejection + hammer, the others via the green body). Those example-read numbers are a sensitivity read off four candles, **not** an author approval and not tuned on any result.

## Pattern use among the 81 valid signals (candidate A)

| patterns passed | signals |
|---|---|
| GOOD_GREEN_BODY | 66 |
| LOWER_PRICE_REJECTION+HAMMER | 7 |
| LOWER_PRICE_REJECTION | 6 |
| HAMMER | 2 |

Diagnostics: green body alone 72, rejection alone 15, hammer alone 30 signals.
