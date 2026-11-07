# Independent audit (Phase 5.3)

`scripts/phase53_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports). Result: **ALL 20 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | IRF EMA table: EMA(200), the EMA's position relative to the signal candle (above / below / inside), the range distance, the close distance and the four pass flags (range / close, 28 / 27) equal an independent recomputation from the raw candles for every confirmed IRF signal | 1813 | PASS |  |
| 2 | every surviving IRF signal of the EMA configurations has at least 28 points of range clearance from the EMA(200) of its own (completed) signal candle | 1531 | PASS |  |
| 3 | every logged EMA rejection really has less than 28 points of range clearance, using the EMA value of the signal candle itself (no later value) | 921 | PASS |  |
| 4 | boundary cases near exactly 28.0 points are decided inclusively (>= 28 passes) | 3 | PASS | 3 signals within 0.05 of the boundary |
| 5 | IRF Method 2A under the first-red-low rule: breakout, extension, the FIRST red candle after the extension (never replaced), support = that candle's LOW (wick included) and the FIRST later close below it (earlier closes below it are allowed only where the EMA gate logged a rejection) match the raw candle sequence | 569 | PASS |  |
| 6 | PDR (Phase 5.3): for every session the first eligible confirmation candle re-derived from the raw candles (body-based zone, strict open above, retest first, green candle or lower-price rejection, close strictly above the ceiling) equals the engine's first PDR signal | 68 | PASS | 36 sessions with a signal |
| 7 | PDR (Phase 5.3): the first signal is never later than the frozen engine's first signal on the same session | 36 | PASS |  |
| 8 | PDS (Phase 5.3): for every session the first eligible confirmation (Methods 1 / 2 on the FIRST red candle at the zone with the body-dominance / upper-wick-dominance tests; a weak first red candle is NOT taken and Method 3 needs the small-support break) re-derived from the raw candles equals the engine's first PDS signal and method | 45 | PASS | 23 sessions with a signal |
| 9 | PDS (Phase 5.3): no signal is ever taken on a weak first red candle (every session whose first red candle is weak has either no signal or a Method 3 signal) | 45 | PASS |  |
| 10 | every Phase 5.3 configuration changes only its own strategies: RF and every other strategy are identical to the frozen signals (no cross-strategy priority; ORB and RF are untouched in the combined configuration) | 10 | PASS |  |
| 11 | the Phase 5.2 approved configuration still equals the frozen Phase 3.6 signal set | 1083 | PASS |  |
| 12 | the frozen reference reproduces the Phase 3.6 signal table (1,083 confirmed signals) | 1083 | PASS |  |
| 13 | IRF Method 1 and Method 3 signals are identical under the first-red-low rule alone (scope: Method 2A only; Method 2B is resistance-based) | 349 | PASS |  |
| 14 | no confirmed ORB signal exists on any of the 13 disputed dates in the Phase 3.6 or the Phase 5.3 author-corrected configuration (the controller skipped nothing) | 13 | PASS |  |
| 15 | confirmed-signal totals per configuration and strategy quoted in signal_counts.json equal the delivered signal table | 12 | PASS |  |
| 16 | the change counts quoted in signal_counts.json equal the rows of signal_comparison.csv | 5 | PASS |  |
| 17 | every required Phase 5.3 deliverable exists | 17 | PASS |  |
| 18 | every file in the Phase 5.3 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.2 reports, the frozen strategy files, the historical datasets, the manual journal, the handwritten PDF) is byte-identical | 15169 | PASS |  |
| 19 | the only files added outside reports/phase5/phase53_author_corrected are the declared Phase 5.3 scripts, tests and new modules | 15177 | PASS |  |
| 20 | every file hashed in the Phase 4 freeze (engines incl. RF, controller, execution, session construction, framework) is unchanged | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |

**Independence caveat.** The audit script is a second implementation written in the same session as the pipeline; the fresh reviewer below is a separate pass.

## Tests and lint

* Before any change (existing suite): **678 passed, 1 skipped**.
* After implementation: **717 passed, 1 skipped (full suite; 678 passed/1 skipped before; 39 new Phase 5.3 tests)**
* `ruff check src tests scripts`: **All checks passed**

## Fresh independent reviewer (read-only sub-agent; own simulator written from the Phase 1 one-minute files)

Verdict: no blockers. The reviewer's own implementation reproduced every IRF Method 2A / 2B signal (date, time, method, level) in five configurations (590 first-red-low, 525 frozen, 478 EMA-28, 519 combined, 526 after-breakout) with zero missing and zero extra; all 1,813 EMA table rows (maximum difference 0.0) and all 921 rejection rows; all 42 armed PDR sessions including re-armed signals; the first red candle, verdict and first signal on every PDS session tried; the guide quotations (PDR s.4.3, PDS quality rule); the 26 frozen-file hashes; and the per-configuration strategy sets. Findings and what was done:

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MAJOR | `independent_audit.md` stale ("FAILURES PRESENT", empty table, 'pending') | FIXED: regenerated after the final audit, tests and lint |
| 2 | MAJOR | '15 first red candles now eligible' overclaims: 5 were already strong / pin under the frozen thresholds | FIXED: reported as 10 newly eligible, 5 already eligible, 5 still weak; the '20 sessions' framing corrected (5 were never 'weak first red' cases) |
| 3 | MAJOR (judgement) | PDS 'good red' (body larger than each wick) is a threshold in disguise (~a third of the range); 'parameter-free' too strong | FIXED: reworded everywhere to 'structural dominance tests = an implicit threshold'; examples quoted (body 37% / 28%); kept PROVISIONAL; owner decision O6 |
| 4 | MAJOR (judgement) | the PDR lower-price-rejection pattern is not in the guide's 'wait for a green candle' | FIXED: the doc states it comes from the author's Phase 3.4 statement; the number of first and re-armed signals triggered by each pattern is now reported (`patterns_passed` counts) |
| 5 | MINOR | '13:00 cutoff applied by the base class' is wrong (flagged, excluded by the controller) | FIXED: reworded |
| 6 | MINOR | inconsistent denominators (PDR 'armed 42' vs 'same 43'; PDS '11 of 45 armed') | FIXED: tables restricted to armed sessions (PDS: 25 with a retest and a red candle) |
| 7 | MINOR | 'no signal passes ... because Target 1 is only 27 away' is empirical, not structural | FIXED: 'in this history' + the gap caveat |
| 8 | MINOR | Method 3 has no confirmed IRF signals in any configuration | FIXED: documented as vacuous, not tested by data |
| 9 | MINOR | cosmetic blanks (empty Method fields, missing G02 date, empty ORB column) | FIXED |
| N1 | NOTE | EMA warm-up / Muhurat session handling not documented | FIXED: one line added (no decision changes) |
| N2 | NOTE | near-28 cases handled consistently (27.965 and 27.978 rejected; 28.053, 28.142, 28.170 pass; no exact tie) | no action |
| N3 | NOTE | after a rejection the Method 2 attempt stays alive (40 delayed signals in the combined configuration) | documented as an inference; O2 (skip vs wait) |

Independence caveat: the audit script and this reviewer were run from this session's instructions; neither is a human review.

