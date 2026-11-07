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
