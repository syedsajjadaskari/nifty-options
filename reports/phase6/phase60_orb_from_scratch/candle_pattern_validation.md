# Candle pattern validation (ORB V2)

Independent functions compute colour, range, body, wicks, percentages, hammer / shooting star, engulfing and full-body, with zero-range, doji and floating-point handling (`patterns.py`; unit-tested). Wrong-side wick uses the WHOLE candle range as the denominator; the 20% limit is a setting (`max_bad_wick_pct`), never silently changed.

## What is explicit and what is provisional

| item | status |
|---|---|
| colour matches direction | EXPLICIT |
| wrong-side wick <= 20% of range | EXPLICIT (adjustable) |
| full-body: green/red with (upper+lower wick) <= 20% of range | EXPLICIT |
| hammer / shooting star proportions | NOT DEFINED -> PROVISIONAL: long-side wick >= 2 x body and opposite wick <= 10% of range |
| engulfing: body engulfs previous candle body | pattern EXPLICIT, REFERENCE CANDLE at 09:20 UNDEFINED -> A/B/C use the previous session's last continuous 5-minute candle (labelled), D disables engulfing |

## Pattern attribution (colour-matching sessions)

| window | colour_ok_sessions | full_body | pin_bar | engulfing | none_of_the_three | wrong_side_wick_fail_among_colour_ok | signals | signal_route_full_body_only | signal_route_engulfing_only | signal_route_pin_only | signal_multiple_patterns |
|---|---|---|---|---|---|---|---|---|---|---|---|
| A | 145 | 30 | 10 | 21 | 95 | 67 | 39 | 16 | 5 | 8 | 10 |
| B | 368 | 82 | 15 | 41 | 255 | 166 | 93 | 50 | 8 | 14 | 21 |
| A_TV | 142 | 20 | 8 | 21 | 101 | 70 | 31 | 10 | 7 | 7 | 7 |
| B_TV | 350 | 52 | 9 | 45 | 263 | 162 | 72 | 31 | 15 | 9 | 17 |


## Wrong-side wick distribution (colour-matching sessions)

| window | n | <=10% | 10-20% | 20-25% | 25-30% | >30% | zero_range_sessions |
|---|---|---|---|---|---|---|---|
| A | 145 | 50 | 28 | 12 | 10 | 45 | 0 |
| B | 368 | 107 | 95 | 25 | 24 | 117 | 0 |


## How much of config A rests on provisional pattern conventions?

| window | pattern basis | trades | win_rate_pct | total_points | profit_factor |
|---|---|---|---|---|---|
| A | explicit full-body rule matched (alone or with others) | 26 | 42.31 | 206.55 | 1.456 |
| A | provisional-only: hammer/shooting-star and/or engulfing, no full-body | 13 | 23.08 | -120.0 | 0.6 |
| B | explicit full-body rule matched (alone or with others) | 71 | 46.48 | 816.25 | 1.73 |
| B | provisional-only: hammer/shooting-star and/or engulfing, no full-body | 22 | 40.91 | 104.75 | 1.267 |


The explicit full-body rule and the provisional hammer / shooting-star / engulfing conventions are reported separately because only the first is defined by the rulebook. Config A is a reference reading, not a purely written-rule result.

## Feed dependence

The first one-minute bar of a session can carry an opening print that the secondary feed does not (e.g. 24 Sep 2025: open 25,142.55 on 5paisa vs 25,108.75). Because the opening candle's wicks and body are measured from that open, the wick rule, the full-body test and the pin-bar test are feed-dependent. Funnel counts on the secondary feed are in the table below (labelled sensitivity; never mixed with the primary result).

| window | step | condition (cumulative, in rulebook order) | sessions_remaining |
|---|---|---|---|
| A | 0 | evaluable sessions | 247 |
| A | 1 | close not on the EMA (direction defined) | 247 |
| A | 2 | gap within limit | 230 |
| A | 3 | previous-day level broken | 206 |
| A | 4 | candle colour matches | 120 |
| A | 5 | at least one pattern | 44 |
| A | 6 | wrong-side wick <= 20% | 39 |
| B | 0 | evaluable sessions | 738 |
| B | 1 | close not on the EMA (direction defined) | 738 |
| B | 2 | gap within limit | 718 |
| B | 3 | previous-day level broken | 630 |
| B | 4 | candle colour matches | 326 |
| B | 5 | at least one pattern | 100 |
| B | 6 | wrong-side wick <= 20% | 93 |
| A_TV | 0 | evaluable sessions | 247 |
| A_TV | 1 | close not on the EMA (direction defined) | 247 |
| A_TV | 2 | gap within limit | 229 |
| A_TV | 3 | previous-day level broken | 205 |
| A_TV | 4 | candle colour matches | 116 |
| A_TV | 5 | at least one pattern | 37 |
| A_TV | 6 | wrong-side wick <= 20% | 31 |
| B_TV | 0 | evaluable sessions | 739 |
| B_TV | 1 | close not on the EMA (direction defined) | 739 |
| B_TV | 2 | gap within limit | 718 |
| B_TV | 3 | previous-day level broken | 631 |
| B_TV | 4 | candle colour matches | 308 |
| B_TV | 5 | at least one pattern | 79 |
| B_TV | 6 | wrong-side wick <= 20% | 72 |


Examples 1-3 are validated in `original_examples_reconstruction.md`.