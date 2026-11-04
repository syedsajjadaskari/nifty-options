# Phase 3.4 - PDR revision with the author's clarified rules (summary)

**Written for:** the strategy owner, for manual review. This phase changes the PDR **signal** engine only (zone selection and entry qualification). It did **not** run a portfolio back-test, compute any P&L, change another engine, the controller, stops, targets, sizing or the cutoff, or overwrite any earlier ledger, report or data file (a hash snapshot taken before the first edit proves it). Nothing was tuned: where the author gave no numbers, the numbers are labelled research parameters.

## What the author's three sentences now require (AUTHOR_APPROVED)

1. **Previous-day high + a zone, connecting multiple highs.** The zone must contain the previous session's highest high (its ceiling), and repeated highs are connected into one zone.
2. **One of three confirmation candles:** a good green-body candle OR a lower-price-rejection candle OR a hammer (OR logic; every pattern that passes is recorded; one signal per candle).
3. **The confirmation candle must close strictly ABOVE the zone ceiling** (equal, inside the zone or below the floor is invalid; a lower wick may dip into or below the zone).

Everything else the author did not define (how many highs, tolerance, separation, width, spike handling, lower boundary, the numeric shape of the patterns, candle colour of the rejection and hammer, how long a setup stays armed) is a research parameter recorded on every signal; **no zone candidate is source-verified**. The engine is `src/nifty_trading/strategies/pdr_revised.py`; the legacy engine `pdr.py` is untouched and still reproduces the old stream exactly (383 signals, identical to the Phase 3.2 export).

## Results (signal level, 247 sessions)

| question | answer |
|---|---|
| A. Original PDR signals | 383 confirmed raw signals on 61 days; the Phase 3.0 portfolio executed 54 of them |
| B. Revised PDR candidate signals (default patterns) | candidate A (day-high zone): 81 signals on 31 days; candidate B (multiple-high zone): 81 signals on 31 days. Co-equal row: with thresholds read off the guide's own four examples, 103 (A) / 103 (B). Neither number is validated. These are RAW signals: 23 of the 81 (A) are timed after 13:00 and the controller's entry cutoff would drop them |
| C. Old signals removed by the close-above-ceiling rule | 310 of 383 old signals fail the test (candidate A; 310 for B); 35 fail ONLY this rule (the other tags are explanatory and overlap) |
| D. Removed / added by the zone construction | removed with a zone-selection tag: 191 (A) / 191 (B), of which 4 only by the zone; newly valid because of the zone: 42 (A) / 50 (B) |
| E. Signals added by the three patterns | 17 (A) / 10 (B) new signals owe their validity to the pattern rule; 7 new signals are on a candle that is not green (hammer / rejection). Patterns over all 81 valid signals (A): GOOD_GREEN_BODY 66, LOWER_PRICE_REJECTION+HAMMER 7, LOWER_PRICE_REJECTION 6, HAMMER 2 |
| F. Days with a different PDR signal outcome | 66 of 247 sessions for A (66 for B): 61 days had an old signal, 31 have a revised one, 26 have both |
| G. Manual PDR journal | old stream 4 exact + 0 time-shifted of 8 PDR rows; revised A 1 exact + 2 shifted; revised B 1 + 2. Thresholds x open rule (candidate A, agreement observation only, see the table below): default/open-above 1 exact + 2 shifted = 3; default/open-anywhere 1 exact + 4 shifted = 5; example-read/open-above 4 exact + 1 shifted = 5; example-read/open-anywhere 6 exact + 1 shifted = 7. Disputed-attribution rows: 4 |
| H. Unresolved source interpretations | see `pdr_unresolved_cases.md` (the first one matters most: the proposed default pattern thresholds reject all four of the guide's own dated entry candles) |
| I. Tests and independent audit | see `independent_audit.md` |
| J. Paths | `reports/phase3/phase34_pdr_revision/` (README lists every file) |

## In plain English, with numbers

* **A removed old entry.** The old engine entered `20260113-1-PDR` on a candle that closed at 25,739.20. The previous day's high - now the zone ceiling - is 25,813.15, so the close is 73.95 points BELOW it. Tags: REMOVED_BY_PATTERN_RULE;REMOVED_BY_CLOSE_RULE. (The old zone was [25,810.45, 25,813.15] - the same candle here, but its close was already below that zone's floor.)
* **The guide's own Example 2.** The author entered on the 09:30 candle on 2025-10-06: O 24900.45, H 24914.35, L 24881.9, C 24910.8. It closes 5.20 points above the drawn ceiling (the close rule is met) but its body is 32% of the range and the lower wick is 1.79 x the body, so with the proposed default thresholds (body >= 60%, wick >= 2 x body) it passes **no** pattern. With the example-read thresholds (body >= 40%, wick >= 1.5 x body) it passes LOWER_PRICE_REJECTION+HAMMER. Under the default thresholds the revised engine therefore fires one candle later (09:35).
* **A newly valid signal.** PDRSIG-20251117-1110-A: candle 11:05, patterns LOWER_PRICE_REJECTION+HAMMER, close 25,948.70 = 9.05 points above the ceiling 25,939.65; the old engine produced nothing on it (the zone equals the legacy zone but the candle is not bullish and passes LOWER_PRICE_REJECTION+HAMMER with its close 9.05 above the ceiling; the legacy rule fired on a different candle or not at all).
* **Why so many signals disappear.** The ceiling is now the previous day's high, and the preserved PDR-011 rule asks the session to open above the zone: that excludes most gap-ups that open inside yesterday's range. Allowing any open would raise candidate A from 81 to 158 signals (a sensitivity, not an author rule).
* **Candidate B versus A - they cannot differ in signals.** The multiple-high zone differs from the day-high zone on 53 of 247 days, but only in its FLOOR; the ceiling is always the previous-day high, because the day's high is always a member. The close rule, the rejection pattern and (under the active open-above-zone rule) the interaction test look only at the ceiling, so A and B give the identical 81 signals (tolerance 10 and 15 also give 81). The floor matters only in the open-anywhere sensitivity (A 158 vs B 159). The only zone choice that can move the ceiling is the spike policy (Example 3), which is a diagnostic option contradicting PDR-A01.

## Journal agreement: thresholds x open rule (candidate A; B is identical)

|  | open must be above the zone (active) | open anywhere (sensitivity) |
|---|---|---|
| default thresholds | 1 exact + 2 shifted = 3 | 1 exact + 4 shifted = 5 |
| example-read thresholds | 4 exact + 1 shifted = 5 | 6 exact + 1 shifted = 7 |

Over the 8 journal rows attributed to PDR (exact = same candle start; shifted = within 15 minutes). Reading: the loss of rows 4, 21 and 44 is explained by the pattern thresholds (the example-read thresholds recover them), but rows 22 (2025-10-07, the guide's Example 3) and 134 (2026-05-19) are lost to the preserved open-above-zone rule, not to the thresholds: they appear only when both are relaxed. **This is an agreement observation only, not a selection criterion:** the example-read thresholds were read off four of these very rows, so their agreement is circular; the journal records no prices or zones; and no setting is chosen because it matches the journal better. Per-row detail: `pdr_journal_agreement_2x2.csv`.

## The most important open point

The author gave no numbers for 'good green body', 'lower price rejection' or 'hammer'. The profile named RESEARCH_DEFAULT is a **placeholder**, not a recommendation: the Phase 2.2 owner-recommended 60%/20% candle and 2x-wick pin definitions plus a hammer shape, kept because the brief said to reuse the existing definitions. It rejects **all four** of the guide's dated entry candles. The EXAMPLE_LENIENT thresholds (40%/25%, 1.5x wick) were read off those same four candles, so their accepting all four is true by construction and proves nothing else. Both counts (81 and 103) are co-equal research outputs; **no setting is validated**. The owner needs to obtain from the author numeric definitions of the three patterns, or a handful of labelled example candles (the profile keeps its historical name RESEARCH_DEFAULT in the files so that earlier config ids stay comparable).

## Not done, by design

No combined five-strategy back-test, no P&L (the comparison is at signal level: a removed signal is not a removed executed trade until the shared controller is re-run), no change to other engines, the controller, stops, targets, sizing or the cutoff, no forward test, no Phase 3.5.
