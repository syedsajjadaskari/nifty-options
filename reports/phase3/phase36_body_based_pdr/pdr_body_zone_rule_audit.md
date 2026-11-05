# PDR body-based zone: before-change audit and the new rules (Phase 3.6)

**Written for:** the strategy owner and reviewers. Part 1 documents what the Phase 3.4 / 3.5 engine (`pdr_revised.py`) actually did **before any change**; part 2 the new engine; part 3 the effect. The engine is named 'revised' but it did **not** implement the author's later wick-ignoring clarification.

## 1. Before-change audit of `src/nifty_trading/strategies/pdr_revised.py` (unchanged; still used by `--pdr-engine revised`)

| question | what the code did |
|---|---|
| Does the zone use raw candle High values? | Yes. `day_high_index` picks the first candle with the highest raw `High` (`c.h`); the zone ceiling is that candle's wick high. |
| Does the zone use max(Open, Close)? | Only for the lower boundary: `_body_top(c) = max(o, c)` of the day-high candle (candidate A) or the lowest member body top (candidate B). The ceiling never used a body. |
| Is the previous-day high the highest wick or body? | The highest WICK of the previous session (`zone.previous_day_high = cs[dh].h`). |
| How are multiple relevant highs detected? | Candidate B: local highs (k = 1, non-strict) of the raw `High`, within 5.0 points of the day's high, at least 2 touch groups (members closer than 2 candles merge). Wick-based. |
| Which boundaries derive from bodies? | The floor only. A wick spike therefore always set the ceiling (Example 3: a 14:50 wick to 25,095.70 became the ceiling although the drawn shelf was 25,081-25,084). |
| Which numerical pattern thresholds were active? | Profile RESEARCH_DEFAULT: green body >= 60% with upper wick <= 20%; rejection lower wick >= 2 x body, close in the top 30%, low <= ceiling; hammer lower wick >= 2 x body, upper wick <= 10%, body bottom >= 60% of the range - all PROPOSED_FOR_REVIEW (Phase 2.2 owner proposals), none author-approved. |
| Was the next day's open compared with the zone ceiling? | Yes: `open > zone.ceiling` (legacy PDR-011, labelled PROPOSED), i.e. against the WICK ceiling. It was not an author-approved rule in Phase 3.5. |
| Was the confirmation close strictly above the ceiling? | Yes: `close_above = c.c > zone_ceiling` (strict), applied to every pattern. |
| Were hammer and lower-price rejection alternatives? | Yes: `qualifies = any pattern passed AND close > ceiling` (OR logic; every passing pattern recorded, one signal per candle). |
| Colour handling of green / red / neutral candles | Good green body requires `close > open`. Rejection and hammer ignore colour, so a red or doji candle with a long lower wick can qualify; a zero-range candle passes nothing; a candle with zero body and a lower wick passes the wick tests (wick >= 2 x 0). |
| Did it ever use future candles? | No: classification uses the completed candle; the zone uses only the previous session; the Phase 3.4 prefix test and the independent rebuild confirmed it. |

## 2. The new rules (`PDR_BODY_RULES` in `pdr_body.py`)

| rule | status | text | source |
|---|---|---|---|
| PDR-B01 | AUTHOR_APPROVED | The previous trading day's high is considered and a zone is drawn (author: "the high should be considered, day's high should be considered and a zone should be drawn"). | strategy author's clarification (Phase 3.6 brief) |
| PDR-B01a | AUTHOR_APPROVED | Wick should be ignored, but body should be considered: a price that is only a wick is ignored; a body high is considered when drawing the zone. | strategy author's clarification (Phase 3.6 brief) |
| PDR-B01b | OWNER_INTERPRETATION | Reading of B01a: for every completed previous-session 5-minute candle body_high = max(open, close); the principal reference is the highest body_high; the wick-only high is never the active ceiling (it is kept as a diagnostic). | Phase 3.6 brief interpretation of the author's words |
| PDR-B02 | AUTHOR_APPROVED | If there are multiple highs, a zone that connects all of them is considered (principle only; the author gave no numbers). | strategy author's clarification (Phase 3.6 brief) |
| PDR-B02a | PROPOSED_FOR_REVIEW | How many body highs make 'multiple': distinct touch groups >= b_min_touches (default 2). | research parameter |
| PDR-B02b | PROPOSED_FOR_REVIEW | Maximum difference between body highs: a body-high pivot within b_tolerance_points (default 5.0) of the highest body high joins the cluster. | research parameter |
| PDR-B02c | PROPOSED_FOR_REVIEW | Minimum candle separation: members closer than b_min_separation_candles (default 2) count as one touch. | research parameter |
| PDR-B02d | PROPOSED_FOR_REVIEW | What counts as a body high of the cluster: a body-high pivot not lower than its b_local_high_k (default 1) neighbours on each side (non-strict). | research parameter |
| PDR-B02e | PROPOSED_FOR_REVIEW | A lone body spike above repeated body highs is never discarded (ALWAYS_INCLUDE_HIGHEST_BODY_HIGH); excluding it is a diagnostic option only. A wick-only spike is ignored by B01a, not by this policy. | research parameter |
| PDR-B02f | PROPOSED_FOR_REVIEW | Lower boundary: the zone is the hull of the member candles' bodies - floor = the lowest body_low among the members; for candidate A the member is the highest-body-high candle alone, so the floor is its body low. The author gave no lower-boundary rule. | research parameter |
| PDR-B02g | PROPOSED_FOR_REVIEW | Equal highest body highs: the first candle anchors the zone. | research parameter |
| PDR-B02h | PROPOSED_FOR_REVIEW | A zone with zero height (ceiling == floor) is detected and flagged ZERO_HEIGHT_ZONE; by default the setup is left UNRESOLVED (no signal) instead of inventing a width; TREAT_AS_LINE is a sensitivity option. | research parameter |
| PDR-B03 | AUTHOR_APPROVED | The next session's opening price must be strictly above the previous day's resistance-zone ceiling (session_open > zone_upper); an open inside the zone, below it or exactly at the ceiling rejects the setup. | strategy author's clarification (Phase 3.6 brief) |
| PDR-B03a | SOURCE_VERIFIED | The next day must also open gap up (open above the official previous close). | PDR_Strategy_Guide.pdf p.1 'Market must open gap up' |
| PDR-B03b | PRESERVED_FROM_PHASE2 | Price must return to / interact with the zone (any candle whose range overlaps the zone +/- proximity) before the confirmation candle; the confirmation comes strictly after the test candle. | PDR_Strategy_Guide.pdf pp.1-3; legacy PDR-005/006 |
| PDR-B04 | AUTHOR_APPROVED | A LONG entry needs one good green body candle OR a lower price rejection candle OR a hammer candle. | strategy author's clarification (Phase 3.6 brief) |
| PDR-B04a | AUTHOR_APPROVED | Fixed body-percentage and wick-size thresholds are not required by the author. | strategy author's clarification (Phase 3.6 brief) |
| PDR-B04b | OWNER_INTERPRETATION | Reading of B04: OR logic; every pattern that passes is recorded; one signal per candle; rejection and hammer need no particular colour. | Phase 3.6 brief interpretation of the author's words |
| PDR-B04c | PROPOSED_FOR_REVIEW | A deterministic research classification is unavoidable: profile RESEARCH_DEFAULT (carried from Phase 3.5 for comparability: good green body = bullish, body >= 60% and upper wick <= 20% of the range; rejection = lower wick >= 2x body, close in the top 30% of the range, low reached the zone ceiling; hammer = lower wick >= 2x body, upper wick <= 10%, body bottom at >= 60% of the range). NOT author-approved; chosen neither by profit nor by journal agreement. | research parameter |
| PDR-B05 | AUTHOR_APPROVED | The confirmation candle should close above the zone. | strategy author's clarification (Phase 3.6 brief) |
| PDR-B05a | OWNER_INTERPRETATION | Reading of B05: close > the zone CEILING, strictly; equal, inside the zone or below the floor is invalid; a lower wick may penetrate the zone. | Phase 3.6 brief interpretation of the author's words |
| PDR-B06 | USER_APPROVED | Entry only after the confirmation candle has completed; fill = open of the 1-minute bar that starts when it ends (existing EXE-FILL-001 convention). | existing execution convention |
| PDR-B07 | PROPOSED_FOR_REVIEW | The test stays armed until a candle qualifies or the session ends (wait_policy); the confirmation may not be the test candle (preserved legacy rule). | research parameter |

### Construction

* `body_high = max(open, close)`, `body_low = min(open, close)` of every completed previous-session 5-minute candle (the same candle set the earlier engines used).
* **Candidate A (active):** ceiling = the highest `body_high` of the session (first occurrence); floor = that candle's `body_low`. **Candidate B:** the highest body high is joined with body-high pivots (k = 1, non-strict) within 5.0 points, at least 2 touch groups (members closer than 2 candles count once); the zone is the hull of the member bodies (floor = lowest member body low), ceiling = the highest body high; otherwise it equals A.
* The illustrative example of the brief (wicks 25,095 / 25,089 / 25,110, body highs 25,080 / 25,084 / 25,082): the highest body high is 25,084, so the ceiling is 25,084 and the 25,110 wick plays no part (covered by `test_an_isolated_wick_spike...` and `test_the_raw_wick_high_is_ignored...`).
* **A and B give identical signals by construction** (the highest body high is always a member, so both ceilings are equal and only the floor can differ): 87 signals each; B's floor differs from A's on 46 of 247 sessions; tolerance 5 / 10 / 15 points also give 87. The only choice that moves the ceiling is the lone-body-spike policy (diagnostic option, contradicts 'do not discard a genuine highest body price': 67 signals).
* **Zero-height zones:** detected (`ZERO_HEIGHT_ZONE`); by default the setup is left UNRESOLVED instead of inventing a width. 0 of 247 sessions have one (the Phase 3.5 run had one, trade 20260826-1-PDR).
* **Opening:** `session_open > zone ceiling`, strictly, using the original first one-minute open; recorded with the distance above the ceiling (PDR-B03 row of every trade). The separate gap-up condition of the guide (open above the official previous close) is preserved.

## 3. Effect of using bodies

| measure (247 sessions) | value |
|---|---|
| Previous-day wick high minus highest body high: median / mean / maximum (points) | 6.60 / 9.42 / 79.15 |
| ... equal (no wick above the highest body) | 20 |
| ... larger than 5 points | 158 |
| Sessions opening above the wick ceiling (Phase 3.5) / above the body ceiling (Phase 3.6) | 61 / 68 |
| Sessions whose open-above-zone status changes | 7 |
| Gap-up sessions | 141 |
| PDR signals: Phase 3.0 / 3.5 / 3.6 | 383 / 81 / 87 |

## 4. Still unresolved (author decisions)

1. Numeric shape of the three patterns (or a manual-review process) - `pdr_pattern_classification.md`.
2. Whether the clarification supersedes the PDF's wick-topped boxes in Examples 1, 2 and 4 - `pdr_source_chart_validation.md`.
3. The zone's lower boundary (hull of the member bodies is a research convention) and the multiple-body-high numbers (tolerance, touches, separation).
4. Whether a zone with zero height should be a line, a minimum width or no setup.
5. Whether the confirmation may be the test candle itself (the author's examples suggest it can be).
6. The wait policy: a tested setup stays armed until a candle qualifies. 35 of 87 signals (14 of 25 executed PDR trades) fire after a candle had CLOSED BELOW the zone floor between the test and the confirmation (`pdr_signal_zone_state.csv`; longest wait 49 candles; 22 signals use the 09:15 candle as the test; widest zone 149.75 points). The guide is silent on price crossing below the zone (Phase 3.3).

## 5. Things that do not affect the signals (stated plainly)

* **The zone floor.** Under the author's opening rule the floor only decides whether a candle counts as a test; every floor variant tried by the independent reviewer (minus infinity, ceiling minus 5, the hull, the anchor candle's body low) and the first / last tie-break gave the same signals. Candidate B differs from A in the floor only.
* **The gap-up condition** is redundant in this data: no session opens above the body ceiling without also opening above the official previous close.
* **The shelf flag** `BODY_SPIKE_ABOVE_SHELF` fires for almost every session (a shelf of repeated body highs can lie anywhere in the day), so the diagnostic 'spike excluded' row of `pdr_sensitivity_counts.csv` is not meaningful; it never affects the active run.
