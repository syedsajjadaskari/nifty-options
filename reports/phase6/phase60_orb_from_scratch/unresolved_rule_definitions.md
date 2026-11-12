# Unresolved rule definitions and owner decisions

Nothing below was decided by the engine. Each item is either a source gap, a source conflict or a provisional convention. Counts are from the primary 5paisa window unless stated and are shown only to size the impact, never to choose.

| id | topic | question | size of impact |
|---|---|---|---|
| OD-1 | FEED | Which data feed is the author's candle: 5paisa or the secondary (TradingView/FYERS-type) feed? The first one-minute print differs (24 Sep 2025: 25,142.55 vs 25,108.75) and the wick, full-body and pin tests, and the gap, depend on it. The rulebook's measured percentages reproduce exactly on the secondary feed only. | Example 1 passes on the secondary feed (BUY) and fails the pattern rule on 5paisa; primary-window signals 39 (5paisa) vs 31 (secondary). |
| OD-2 | BREAK DEFINITION | Must the opening candle CROSS a level (open on the old side, close beyond) or is 'close beyond the level' enough, including after a gap? Not stated. | signals 39 (literal) vs 27 (crossing) in the primary window; 93 vs 59 in 2022-25. |
| OD-3 | INNER LEVELS / 'MAJOR' | How are inner levels found, and is 'major' the previous-day high/low or the prominent late-day zone the author drew (Example 1: the drawn major zone is NOT the day high)? | A vs C (cluster zones): signals 39 vs 37 primary. |
| OD-4 | PATTERNS | Exact hammer / shooting-star proportions and the engulfing reference candle at 09:20. | NO_PATTERN is the largest gate: 120 -> 44 sessions in the primary window; config D (no engulfing) 34 signals. |
| OD-5 | WICK RULE vs EXAMPLES | Example 2 (upper wick 47%) fails the 20% BUY rule; Example 3 (upper wick 66%) passes the SELL rule although the author said it must not be taken. Which is wrong - the rule direction/threshold or the examples? | see original_examples_reconstruction.md |
| OD-6 | GAP LIMIT | 250 or 300 points? | differs on 1 date(s) in 2022-25 and 0 in the primary window (5paisa). |
| OD-7 | ENTRY PRICE | Rulebook: close of the 9:15 candle. V2 uses the first executable price (open of the 09:20 minute bar). Which is intended (a limit at the close is not guaranteed executable)? | /entry - candle close/ averages 1.05 points (max 6.75) across V2-A trades. |
| OD-8 | END-OF-DAY EXIT | The rulebook leaves the time open (example 3:15 PM, which is not an executable continuous-session fill); V2 uses the provisional 15:14 bar-open convention. | forced exits: 0 (primary), 3 (2022-25) of the V2-A trades. |
| OD-9 | SAME-CANDLE STOP/TARGET | The rulebook speaks of the same 5-minute candle; V2 resolves on one-minute bars (stop first). | no same-minute collision occurred in the primary run |
| OD-10 | EMA VALUE / CROSS TYPES | Same-candle EMA value (TO CONFIRM) and whether an intrabar cross and an overnight-gap cross are equivalent. | labels A/B/C are recorded; nothing is rejected by them |
| OD-11 | ZONE BOUNDARY | Is a close exactly on the zone edge a break (V2: no, STRICT)? | configurable; not exercised by the data |
| OD-12 | QUANTITY / COST | Synthetic quantity (75, the rulebook's example) and the Rs 70 indicative charge are not verified. | only affects rupee columns |
| OD-13 | JOURNAL EVIDENCE | The journal records no direction, price or level; the 13 handwritten notes give no level or direction. Exact trade matching is impossible without them. | 38 strict-timing matches are date + strategy + time label only. |
| OD-15 | GAP REFERENCE CLOSE | 'Previous day close': V2 uses the vendor OFFICIAL daily close (differs from the last 5-minute chart close by a mean 12.7 points, max 88.9, in 2025-26). Using the last chart close flips the 250-point gap decision on 2 primary-window sessions (2026-03-30, 2026-06-12); neither would have signalled. | no effect on the primary-window signals |
| OD-14 | PORTFOLIO | ORB V2 is not integrated; priority between a 09:20 ORB and IRF/PDR/PDS/RF is undefined. | no controller change was made |


## Approvals needed before ORB V2 can replace the old ORB engine

1. Decide OD-1 (feed), OD-2 (break), OD-3 (inner levels / major), OD-4 (patterns) and OD-5 (wick rule): together they decide the signals.
2. Approve or amend the execution conventions OD-7 to OD-9.
3. Confirm the gap limit (OD-6).
4. Supply direction / level / price for journal ORB dates (or accept date-level evidence only) so exact matching is possible (OD-13).
5. Decide the portfolio priority and approve any integration (OD-14); then re-run the frozen-baseline regression.
6. Obtain historical option data before any CE/PE statement is made.