# Independent audit (Phase 5.1)

`scripts/phase51_independent_audit.py` re-derives, from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports), what the day reports state. Result: **ALL 22 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | the handwritten PDF has six pages, all six rendered page images exist, and the PDF is byte-identical to its baseline hash | 6 | PASS |  |
| 2 | all 40 dated entries are weekdays, resolve to exactly one Phase 3.6 trade, and the strategy label written beside the date equals that trade's strategy (AC27 has no label) | 40 | PASS |  |
| 3 | transcription: 40 dated entries, 2 general remarks, exactly one crossed-out entry (AC23) and it has no classification | 42 | PASS |  |
| 4 | every evidence candle (38 dates) equals an independent 5-minute aggregation of the raw one-minute rows: OHLC, colour, body %, and the causal EMA(200) of 5-minute closes | 2850 | PASS |  |
| 5 | previous-session high and low in the evidence equal the independent previous-session 5-minute extremes | 38 | PASS |  |
| 6 | each dated automated trade: entry = raw 1-minute open at the fill minute, outcome and both exit times equal an independent exit walk, and its delivered rule checks show 0 failures (supports 'no confirmed implementation defect') | 40 | PASS |  |
| 7 | the IRF population counts behind the candidate rules (EMA within 27 below the entry, close below the session low so far, entry-candle body < 60 / 50 / 40) equal an independent recomputation, trade by trade | 109 | PASS | {'body_lt_60': 55, 'body_lt_50': 35, 'body_lt_40': 28, 'ema_within_27': 9, 'close_below_session_low': 0} |
| 8 | the 'first red candle' reading (re-implemented from the author's wording) differs from the engine's entry on exactly the Method-2 IRF trades listed in population_impact.json | 42 | PASS | 37 of 42 |
| 9 | for every dated IRF entry the 'first red candle (fully above, body >= 60)' entry printed in the day report equals the independent computation | 27 | PASS |  |
| 10 | the PDR 'first green candle' counts (earlier than the engine's confirmation) equal an independent recomputation from the zone in the Phase 3.6 signals and the raw candles | 25 | PASS | 19 of 25 |
| 11 | the ORB signals changed by the colour variant are exactly the confirmed Phase 3.6 ORB signals whose first candle colour contradicts the direction (independent recomputation from the raw first candle) | 53 | PASS | [('2025-11-27', 'Method 1', 'LONG'), ('2026-01-05', 'Method 1', 'LONG'), ('2026-04-24', 'Method 1', 'SHORT')] |
| 12 | every executed trade the variant removes is either one of those ORB trades or a later trade on the same day (no other day is touched) | 4 | PASS |  |
| 13 | the frozen scenario re-run through the unchanged controller reproduces the Phase 3.6 ledger identities (196 trades) before the variant is applied | 196 | PASS |  |
| 14 | every active observation has at least one classification and all classifications belong to the required set (plus NO_DISCREPANCY_FOUND); no observation is classified CONFIRMED_SOFTWARE_BUG or WRONG_STRATEGY_SELECTION | 42 | PASS |  |
| 15 | only AC27 is implemented, and only as an opt-in variant | 1 | PASS |  |
| 16 | in strategy_selection_conflicts.csv the 'expected strategy produced confirmed signals' column equals the Phase 3.6 signal table, row by row | 19 | PASS |  |
| 17 | every dated observation has a day report and a chart | 40 | PASS |  |
| 18 | confirmed_software_defects.md states 'none' and no frozen file differs from its hash (strategy, controller, framework) | 1 | PASS |  |
| 19 | every file in the baseline snapshot (all of src, scripts, tests, docs, data, reports: the strategy files, the Phase 3.6 / 4 / 5 reports, the historical datasets, the manual journal and the handwritten PDF) is byte-identical | 14888 | PASS |  |
| 20 | the only files added outside reports/phase5/phase51_author_corrections are the declared Phase 5.1 scripts, tests and the two new modules (orb_colour.py, phase51.py) | 14898 | PASS |  |
| 21 | every file hashed in the Phase 4 freeze (engines, controller, execution, session construction, framework) is unchanged | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |
| 22 | the variant is a subclass that only post-filters confirmed records (it contains no stop, target, level or threshold value) | 1 | PASS |  |

## Tests and lint

* Before implementation (full suite, `pytest -q`): **636 passed, 1 skipped**.
* After implementation: **650 passed, 1 skipped (full suite, pytest -q, run after the review fixes; 636 passed, 1 skipped before any change)**
* `ruff check src tests scripts`: **ruff check src tests scripts: All checks passed**

## Fresh independent reviewer

A reviewer with no prior context read all six page images, re-derived numbers from the minute data, and tried to refute the findings (read-only; scratch files outside the repository).

**Verdicts:** transcription - PASS with minor omissions; implemented change - PASS with a scope caveat; unimplemented corrections - the sampled numbers are correct but some 'engine correct' wording was overstated; claims - no genuine implementation defect found and no profit-based selection; preservation - PASS (all 14,888 baseline hashes re-checked). Verified independently: the first candle of 2025-11-27 is red (open 26,261.25, close 26,253.60) and its Method 1 LONG is the confirmation invalidated; 2026-01-05 LONG and 2026-04-24 SHORT also contradict their direction by colour; the EMA(200) recomputation with the engine's method reproduces '9 of 109' IRF trades (a plain pandas EWM gives 10 - the count is boundary-sensitive, 2026-05-27 sits 26.58 points above its EMA); the 19 selection cases agree with the signal table.

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | major (wording) | 'Engine correct under existing rules' for ORB days AC04, AC06, AC12, AC37 rests on Method 2's inner level / trendline, which the source does not define (orb.py says so); AC39 fails only the proposed 20% lower-wick limit (LOOSE profile 25% would pass) and AC33 only the 60% body (LOOSE 50%); 'no single change explains them' was too strong | Fixed: those four now read 'not decidable either way'; AC39 and AC33 name the strength profile; the C5 paragraph is rewritten |
| 2 | minor (scope) | the short mirror (red required for a short) is my reading of ORB-GLOBAL-002; the author wrote 'long' only; the pin-bar quote came from the Gap setup, while Method 1 admits pin bars through ORB-CANDLE-001 and a proposal flag, and the page says a pin bar's close must support the breakout | Disclosed already as 'my application'; the defect table and AC27 now cite the right source and say 'not a defect' is defensible but not clear-cut. The variant stays opt-in, so no baseline effect |
| 3 | minor (test) | a vacuous `or True` assertion in the EMA-space test | Fixed (the assertion now checks entry - EMA = 16.0) |
| 4 | minor | 'consistent with PDR-007' although Phase 3.4 replaced PDR-007 by PDR-A04 | Reworded: 'legacy PDR-007 wording, replaced by PDR-A04 in Phase 3.4' (NR6 already states the conflict) |
| 5 | minor | AC19: 'engine correct' depends on the proposal default m1_close_below_irl_counts_as_inside = False | Stated in the AC19 conclusion; classified as a missing rule, not a defect |
| 6 | minor | transcription: AC40 'PPR' normalised silently; a scribbled word in AC27; stray red marks beside G01; the AC38 date reading is partly circular for the label-match count | Added to the uncertain-phrase notes; the label-match statement now says 38 entries match independently of any date reading and AC38 only after resolution (supported by the manual journal's 09:30 PDS row on 2025-12-26 and no trade on 2025-12-16) |
| 7 | minor (docs) | test / ruff results missing in independent_audit.md; the README reproduce line has a placeholder; gendered pronoun for the author | Results recorded below; pronouns replaced by 'the author'; the placeholder is a usage template for the docs script |
| 8 | info | conclusions and their numbers are hand-written per correction id (not regenerated if data change) | Stated: the audit script recomputes the numbers they quote; they are analysis text, not computed output |

**Not verified by the reviewer:** the PDR / PDS zone construction (taken from the engine's own signal records), the 'Gap/200DMA' average (it is the 5-minute EMA(200), ma_mode EMA200_5M - now said in AC31), the full per-trade body / day's-low populations (recomputed by the audit script: 55 / 35 / 28 and 0), the workbook and the remaining daily reports (the audit script cross-checks the CSV tables and every day report's candles).

