# Reconstruction of the rulebook examples (16, 17 and 24 September 2025)

Source: `Nifty_920_ORB_Rulebook (2) (1).docx` (identical bytes to `(2).docx`; SHA-256 8504fb6f...). The four embedded images were extracted at native resolution (`charts_examples/doc_images/`). Prices were never overwritten to match a screenshot. Every number below is recomputed from one-minute candles.

## Key finding: the screenshots come from the secondary-vendor feed, not from 5paisa

The rulebook's measured wick percentages (Example 2: 47% / 3%; Example 3: 66% / 27% / 7%) and the EMA labels in the screenshots are reproduced **exactly** by the secondary vendor's minute data and **not** by 5paisa. The first 09:15 one-minute bar differs between feeds (24 Sep: 5paisa opens 25,142.55 - an opening print - while the secondary feed opens 25,108.75). The wrong-side-wick and pattern tests are therefore feed-dependent. Which feed defines the author's candle is the most important unresolved data decision (see `unresolved_rule_definitions.md`).

## Verdicts

| example | date | classification | detail |
|---|---|---|---|
| 1 | 2025-09-16 | REPRODUCED ON THE SECONDARY FEED; FAILS THE PATTERN RULE ON 5paisa | On the secondary feed (the screenshot's feed) the candle is O 25073.6 H 25111.25 L 25070.45 C 25106.75: upper wick 11.0% (rulebook ~11%), total wick 18.7% -> full-body (<=20%) passes -> SIGNAL BUY. On 5paisa the first minute opens at 25079.5 (secondary 25073.6), lower wick 19.1%, total wick 28.3% -> no pattern -> NO SIGNAL: NO_PATTERN. Author's zones match engine swing-zones within ~2 points (see zone table). |
| 2 | 2025-09-17 | VIOLATES THE WRITTEN WICK RULE ON BOTH FEEDS (genuine contradiction; not a measurement error) | Secondary feed upper wick 47.1% / lower 3.0% reproduces the rulebook's 47% / 3% exactly; 5paisa gives 43.4% / 0.0%. Both exceed the 20% limit -> NO SIGNAL: NO_PATTERN, WRONG_SIDE_WICK. The EMA, gap and level conditions pass (the open is above the previous day's high, so the close is beyond the major level; the rulebook says no previous-day level is drawn on this screenshot - a likely but UNCONFIRMED explanation is that nothing lies above the candle). Not a different candle, not an approximate measurement: the rule or the example needs author correction. |
| 3 | 2025-09-24 | PASSES THE WRITTEN RULES ON THE SECONDARY FEED (via the shooting-star pattern); the author's 'must not be taken' remark contradicts the rulebook table | Secondary feed: upper 66.2%, body 26.5%, lower 7.3% reproduces the rulebook's 66/27/7 exactly. Colour red, below the EMA, wrong-side (lower) wick 7.3% <= 20%, pattern pin_bar (shooting-star proportions are PROVISIONAL) -> SIGNAL SELL. On 5paisa the candle is a different shape (O 25142.55 - an opening print 32 points above the secondary feed's open; upper wick 6.4%, body 86.6%) and passes via full-body. The disagreement is therefore about the RULE (is a long upper wick on a SELL bad?), not the candle: requires author clarification; no pass/fail is assumed. |


## Candle, EMA and decision per example and feed

| example_date | feed | O | H | L | C | colour | body_pct | upper_wick_pct | lower_wick_pct | total_wick_pct | ema_at_0920 | gap_points | levels_broken | patterns | written_rule_verdict(V2-A) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 2025-09-16 | 5P | 25079.5 | 25110.25 | 25072.25 | 25106.75 | GREEN | 71.7 | 9.2 | 19.1 | 28.3 | 25062.82 | 10.3 | 3/10 |  | NO SIGNAL: NO_PATTERN |
| 2025-09-16 | TV | 25073.6 | 25111.25 | 25070.45 | 25106.75 | GREEN | 81.3 | 11.0 | 7.7 | 18.7 | 25062.84 | 4.4 | 3/10 | full_body | SIGNAL BUY |
| 2025-09-17 | 5P | 25276.6 | 25313.15 | 25276.6 | 25297.3 | GREEN | 56.6 | 43.4 | 0.0 | 43.4 | 25128.56 | 37.5 | 9/9 |  | NO SIGNAL: NO_PATTERN, WRONG_SIDE_WICK |
| 2025-09-17 | TV | 25276.6 | 25316.35 | 25275.35 | 25297.05 | GREEN | 49.9 | 47.1 | 3.0 | 50.1 | 25128.58 | 37.5 | 9/9 |  | NO SIGNAL: NO_PATTERN, WRONG_SIDE_WICK |
| 2025-09-24 | 5P | 25142.55 | 25146.25 | 25088.25 | 25092.3 | RED | 86.6 | 6.4 | 7.0 | 13.4 | 25228.06 | -26.95 | 8/10 | full_body | SIGNAL SELL |
| 2025-09-24 | TV | 25108.75 | 25149.85 | 25087.75 | 25092.3 | RED | 26.5 | 66.2 | 7.3 | 73.5 | 25228.19 | -60.75 | 8/10 | pin_bar | SIGNAL SELL |


## Rulebook numbers versus actual

| example_date | feed | measure | rulebook | actual | difference |
|---|---|---|---|---|---|
| 2025-09-16 | 5P | upper wick % | 11 | 9.2 | -1.8 |
| 2025-09-16 | TV | upper wick % | 11 | 11.0 | 0.0 |
| 2025-09-17 | 5P | upper wick % | 47 | 43.4 | -3.6 |
| 2025-09-17 | 5P | lower wick % | 3 | 0.0 | -3.0 |
| 2025-09-17 | TV | upper wick % | 47 | 47.1 | 0.1 |
| 2025-09-17 | TV | lower wick % | 3 | 3.0 | 0.0 |
| 2025-09-24 | 5P | upper wick % | 66 | 6.4 | -59.6 |
| 2025-09-24 | 5P | lower wick % | 7 | 7.0 | -0.0 |
| 2025-09-24 | 5P | body % | 27 | 86.6 | 59.6 |
| 2025-09-24 | TV | upper wick % | 66 | 66.2 | 0.2 |
| 2025-09-24 | TV | lower wick % | 7 | 7.3 | 0.3 |
| 2025-09-24 | TV | body % | 27 | 26.5 | -0.5 |


## EMA check against the screenshot labels

| example_date | feed | ema_at_screenshot_hover | screenshot_ema_label | ema_diff_vs_screenshot |
|---|---|---|---|---|
| 2025-09-16 | 5P | 25047.58 | 25047.63 | -0.05 |
| 2025-09-16 | TV | 25047.63 | 25047.63 | 0.0 |
| 2025-09-17 | 5P | 25206.77 | 25206.8 | -0.03 |
| 2025-09-17 | TV | 25206.8 | 25206.8 | -0.0 |
| 2025-09-24 | 5P | 25233.61 | 25233.85 | -0.24 |
| 2025-09-24 | TV | 25233.75 | 25233.85 | -0.1 |

The independent EMA(200) agrees with the TradingView/FYERS labels to within a quarter of a point on all three hover candles (the rulebook's 'about 25,050 / 25,207 / 25,234' are the same labels read at the hover time, not the 09:20 value).

## Author's purple zones versus engine swing zones

| example_date | feed | author_zone | author_floor_px | author_ceiling_px | nearest_engine_zone | engine_evidence | mid_distance_pts |
|---|---|---|---|---|---|---|---|
| 2025-09-16 | 5P | lower purple zone | 25092.2 | 25095.8 | INNER RESISTANCE 25094.40-25097.05 | swing high k=2 at 11:30 | 1.72 |
| 2025-09-16 | 5P | upper purple zone | 25111.8 | 25114.8 | INNER RESISTANCE 25108.60-25118.35 | swing high k=2 at 12:00 | 0.17 |
| 2025-09-16 | TV | lower purple zone | 25092.2 | 25095.8 | INNER RESISTANCE 25094.40-25097.05 | swing high k=2 at 11:30 | 1.72 |
| 2025-09-16 | TV | upper purple zone | 25111.8 | 25114.8 | INNER RESISTANCE 25108.60-25118.35 | swing high k=2 at 12:00 | 0.17 |
| 2025-09-24 | 5P | top purple zone | 25177.4 | 25182.6 | INNER SUPPORT 25173.85-25184.85 | swing low k=2 at 12:45 | 0.65 |
| 2025-09-24 | 5P | middle purple zone | 25135.7 | 25140.4 | INNER RESISTANCE 25137.75-25138.70 | swing high k=2 at 10:35 | 0.17 |
| 2025-09-24 | 5P | lower purple zone | 25084.0 | 25087.0 | INNER SUPPORT 25084.85-25086.85 | swing low k=2 at 11:20 | 0.35 |
| 2025-09-24 | TV | top purple zone | 25177.4 | 25182.6 | INNER SUPPORT 25173.85-25184.85 | swing low k=2 at 12:45 | 0.65 |
| 2025-09-24 | TV | middle purple zone | 25135.7 | 25140.4 | INNER RESISTANCE 25137.75-25138.70 | swing high k=2 at 10:35 | 0.17 |
| 2025-09-24 | TV | lower purple zone | 25084.0 | 25087.0 | MAJOR SUPPORT 25084.65-25084.65 | previous-day low 25084.65 | 0.85 |


Zones were read from the screenshots by pixel position against the price axis (+/-1.5 points) and are visual evidence only; the general construction rule remains undefined. Because the engine produces roughly ten zones per side, a small nearest-zone distance is WEAK evidence (several engine zones lie within a few points of any price) and does not validate the swing-zone construction. In Example 1 the author's 'major' upper zone (~25,112-25,115) is **not** the previous-day high (25,137.45, off the left edge of the screenshot): the author's 'major' appears to mean the prominent late-day zone, which the rulebook does not define.

## Per-example condition matrix

| example_date | feed | condition | observed | requirement | verdict | authority |
|---|---|---|---|---|---|---|
| 2025-09-16 | 5P | Gap filter | gap +10.30 (open 25079.50 vs official prev close 25069.20) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-16 | 5P | 200 EMA direction | close 25106.75 vs EMA 25062.82 -> BUY (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-16 | 5P | Previous-day level break | 3/10 broken (INNER_ONLY); nearest: INNER RESISTANCE [SWING_FRACTAL_WICK_ZONE] 25097.45-25102.75 (swing high k=2 at 10:35) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-16 | 5P | Candle colour | GREEN | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-16 | 5P | Accepted pattern | none (full-body False, pin False, engulfing False) | hammer/shooting star, engulfing or full-body | FAIL | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-16 | 5P | Wrong-side wick | 9.2% of range | <= 20% of the whole range | PASS | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-16 | 5P | Zero-range candle | range 38.00 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-16 | TV | Gap filter | gap +4.40 (open 25073.60 vs official prev close 25069.20) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-16 | TV | 200 EMA direction | close 25106.75 vs EMA 25062.84 -> BUY (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-16 | TV | Previous-day level break | 3/10 broken (INNER_ONLY); nearest: INNER RESISTANCE [SWING_FRACTAL_WICK_ZONE] 25097.45-25102.75 (swing high k=2 at 10:35) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-16 | TV | Candle colour | GREEN | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-16 | TV | Accepted pattern | full_body (full-body True, pin False, engulfing False) | hammer/shooting star, engulfing or full-body | PASS | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-16 | TV | Wrong-side wick | 11.0% of range | <= 20% of the whole range | PASS | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-16 | TV | Zero-range candle | range 40.80 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-17 | 5P | Gap filter | gap +37.50 (open 25276.60 vs official prev close 25239.10) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-17 | 5P | 200 EMA direction | close 25297.30 vs EMA 25128.56 -> BUY (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-17 | 5P | Previous-day level break | 9/9 broken (MAJOR_AND_INNER); nearest: MAJOR RESISTANCE [PREV_DAY_HIGH] 25260.50 (previous-day high 25260.50) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-17 | 5P | Candle colour | GREEN | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-17 | 5P | Accepted pattern | none (full-body False, pin False, engulfing False) | hammer/shooting star, engulfing or full-body | FAIL | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-17 | 5P | Wrong-side wick | 43.4% of range | <= 20% of the whole range | FAIL | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-17 | 5P | Zero-range candle | range 36.55 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-17 | TV | Gap filter | gap +37.50 (open 25276.60 vs official prev close 25239.10) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-17 | TV | 200 EMA direction | close 25297.05 vs EMA 25128.58 -> BUY (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-17 | TV | Previous-day level break | 9/9 broken (MAJOR_AND_INNER); nearest: MAJOR RESISTANCE [PREV_DAY_HIGH] 25261.40 (previous-day high 25261.40) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-17 | TV | Candle colour | GREEN | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-17 | TV | Accepted pattern | none (full-body False, pin False, engulfing False) | hammer/shooting star, engulfing or full-body | FAIL | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-17 | TV | Wrong-side wick | 47.1% of range | <= 20% of the whole range | FAIL | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-17 | TV | Zero-range candle | range 41.00 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-24 | 5P | Gap filter | gap -26.95 (open 25142.55 vs official prev close 25169.50) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-24 | 5P | 200 EMA direction | close 25092.30 vs EMA 25228.06 -> SELL (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-24 | 5P | Previous-day level break | 8/10 broken (INNER_ONLY); nearest: INNER SUPPORT [SWING_FRACTAL_WICK_ZONE] 25110.30-25121.05 (swing low k=2 at 09:50) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-24 | 5P | Candle colour | RED | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-24 | 5P | Accepted pattern | full_body (full-body True, pin False, engulfing False) | hammer/shooting star, engulfing or full-body | PASS | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-24 | 5P | Wrong-side wick | 7.0% of range | <= 20% of the whole range | PASS | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-24 | 5P | Zero-range candle | range 58.00 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-24 | TV | Gap filter | gap -60.75 (open 25108.75 vs official prev close 25169.50) | /gap/ <= 250 (or 300) | PASS | TO_CONFIRM (250 or 300) |
| 2025-09-24 | TV | 200 EMA direction | close 25092.30 vs EMA 25228.19 -> SELL (A_ALREADY_BEYOND_EMA) | BUY above / SELL below the 5-min EMA(200) | PASS | EXPLICIT_LATEST_RULEBOOK (same-candle EMA value: TO_CONFIRM) |
| 2025-09-24 | TV | Previous-day level break | 8/10 broken (INNER_ONLY); nearest: INNER SUPPORT [SWING_FRACTAL_WICK_ZONE] 25110.05-25121.05 (swing low k=2 at 09:50) | close beyond any previous-day level, major or inner | PASS | EXPLICIT (break = close beyond; zone edge TO_CONFIRM); inner-level construction PROVISIONAL |
| 2025-09-24 | TV | Candle colour | RED | green for BUY, red for SELL | PASS | EXPLICIT_LATEST_RULEBOOK |
| 2025-09-24 | TV | Accepted pattern | pin_bar (full-body False, pin True, engulfing False) | hammer/shooting star, engulfing or full-body | PASS | full-body EXPLICIT; pin proportions and engulfing reference PROVISIONAL |
| 2025-09-24 | TV | Wrong-side wick | 7.3% of range | <= 20% of the whole range | PASS | EXPLICIT_LATEST_RULEBOOK (20% adjustable) |
| 2025-09-24 | TV | Zero-range candle | range 62.10 | high != low | PASS | EXPLICIT_LATEST_RULEBOOK |


## What needs author confirmation

1. Which feed is the author's candle (5paisa vs the TradingView/FYERS-type secondary feed)? The first-minute opening print differs and flips Example 1 and the pattern outcome of Example 3.
2. Example 2: the written 20% rule fails the example on every feed. Is the rule direction/threshold wrong, or the example mislabeled?
3. Example 3: is a long upper wick on a SELL good (rulebook table) or bad (the author's remark)?
4. Example 1: what does 'major' mean when it is not the previous-day high?

Charts: `charts_examples/example_<date>_<feed>.svg` (screenshot above, reconstructed chart below).