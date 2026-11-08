# Independent audit (Phase 5.4)

`scripts/phase54_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the original journal workbook (no `src/` imports). Result: **ALL 16 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | the 13 disputed dates: first candle OHLC (09:15 start), body and wick percentages, previous-day high / low / official close, opening gap and EMA(200) at the first candle equal an independent recomputation from the raw one-minute data | 13 | PASS |  |
| 2 | the 13 dates: the Method 1 'level broken' predicate, the strong-candle verdicts under the STRICT / MODERATE / LOOSE profiles (with the wick against the trade), and the trend numbers (previous close minus its EMA, first close minus the EMA) equal an independent recomputation | 13 | PASS |  |
| 3 | the 13 dates: the frozen Method 2 trendline (the last two previous-session k=2 fractal lows / highs; slope, extrapolated value at the open and the 'supportive' verdict) equals an independent recomputation | 13 | PASS |  |
| 4 | the level families on the 13 dates (previous-day extreme, the extreme of the last 2 / 3 / 5 sessions, the frozen latest inner fractal) and whether the first candle broke and closed beyond each equal an independent recomputation | 117 | PASS |  |
| 5 | population: the number of sessions on which the colour-direction first candle breaks and closes beyond the previous-day high / low equals an independent count | 247 | PASS | independent 69 vs reported 69 |
| 6 | the ten cases where the 'open crosses the 200 average' and 'the candle crosses the 200 average' readings of the Gap setup differ really differ (previous close on the wrong side, the candle closes beyond the average, the open does not) | 10 | PASS |  |
| 7 | the manual journal read from the original workbook: 190 rows, 89 ORB rows, 5 weekend-dated rows; the overlap with the Phase 3.6 ORB signal dates and the counts of ORB journal dates without an engine ORB signal equal an independent recount | 190 | PASS | in-session ORB journal dates 85; engine overlap 35; engine ORB dates without a journal ORB 6 |
| 8 | the journal cross-check table lists exactly the 89 ORB journal rows once each | 89 | PASS |  |
| 9 | the frozen ORB reference in the variant table has 53 confirmed signals equal to the Phase 3.6 ORB signals, and the frozen engine equals the Phase 3.6 table (summary flag) | 53 | PASS |  |
| 10 | variant table consistency: a single loosened gate removes no frozen signal, the stricter profile / colour / structure variants add none | 12 | PASS |  |
| 11 | no variant reproduces more than two of the thirteen disputed dates (each variant loosens or re-defines ONE unresolved construction; combinations were deliberately not searched) | 12 | PASS | {'orb-frozen': '0', 'orb-var-inner-highest-fractal': '0', 'orb-var-inner-nearest-from-open': '1', 'orb-var-inner-highest-broken': '1', 'orb-var-trendline-any-pair': '1',  |
| 12 | the source-rule registry uses only the six classification labels and never describes an implemented research variant as an explicit document rule | 47 | PASS |  |
| 13 | every required Phase 5.4 deliverable exists, with one chart-based case study (daily report + SVG chart) for each of the 13 disputed dates | 37 | PASS |  |
| 14 | every file in the Phase 5.4 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.3, the frozen strategy files, the historical datasets, the manual journal, the source PDFs) is byte-identical | 15283 | PASS |  |
| 15 | the only files added outside reports/phase5/phase54_orb_audit are the declared Phase 5.4 scripts, tests and new modules | 15291 | PASS |  |
| 16 | every file hashed in the Phase 4 freeze (engines incl. ORB, RF, controller, execution, session construction, framework) is unchanged | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |

**Independence caveat.** The audit script is a second implementation written in the same session; the fresh reviewer below is a separate pass.

## Tests and lint

* Before any change (existing suite): **717 passed, 1 skipped**.
* After implementation: **737 passed, 1 skipped (full suite; 717 passed / 1 skipped before; 20 new Phase 5.4 tests)**
* `ruff check src tests scripts`: **All checks passed**

## Fresh independent reviewer (read-only sub-agent; rebuilt the numbers from the raw one-minute files and re-rendered the PDF pages)

Verdict: no blockers. The reviewer reproduced all 13 dates' first-candle numbers, previous-day levels, gaps, inner levels and trendline values (EMA matched on 12 of 13 to the cent; the 13th, 2025-10-27, matches once the Muhurat session is excluded as the repository does), the missing-predicate distribution, the 3 colour-rule removals, the journal counts (190 / 89 / 5 / 85 / 35 / 41 / 50), the Gap-reading counts (40 / 50 / 10 and the same ten dates), the frozen hashes and the absence of look-ahead and hardcoded dates. Findings and what was done:

| # | severity | finding | disposition |
|---|---|---|---|
| M1 | MAJOR | the Gap-setup figures (p.8, p.9) and the real gap-up chart on p.12 were not analysed; the figures draw the CANDLE crossing the average, so 'genuinely ambiguous' understated the source | CONFIRMED by my own reading of pp.8, 9, 12. FIXED: figures added as evidence everywhere; the report now says the figures favour the candle-crossing reading and the frozen open-based reading is the stricter, unevidenced one; a disabled variant `orb-var-gap-candle-crossing` was BUILT and measured (56 signals, +3, none removed, none of the 13 changes) and R12 rewritten |
| M2 | MAJOR | two real charts on p.12 omitted; p.13 chart 3 mis-described | FIXED: p.12 charts added; the three p.13 charts described individually (chart 3: the band starts inside the previous session and runs past the entry; the trendline is far below price); the 'several sessions' reading is flagged as inferred |
| M3 | MAJOR | the per-chart level reconstruction was only partly delivered | FIXED: a 12-row per-figure table (p.3, 4, 5, 6, 7, 8, 9, p.12 x2, p.13 x3) with candle source, availability, horizontal / diagonal, bodies or wicks, zone boundaries, breakout confirmation and comparison with the algorithm; limitation stated: the real charts have no price axis, so band edges are described, not measured |
| M4 | MAJOR | registry status and diagram errors; missing rows | FIXED: explicit statements whose construction is undefined (ORB-M2-*-001, ORB-GAP-*-005 / -004) are now labelled EXPLICIT_DOCUMENT_RULE (qualitative) with the construction marked UNRESOLVED; ORB-GLOBAL-004 corrected; diagram references rebuilt per rule family; added rows for the p.4 table level definition, the p.12 wick rule, the p.12 gap / trend requirement, the p.8-9 and p.12 figures |
| M5 | MAJOR | the journal was used beyond 'descriptive only' (under-generation sentence, recall / precision-like columns, 'supporting dates', outcomes) | FIXED: columns renamed 'date overlap ... (descriptive)'; 'supporting dates' renamed 'dates on which the variant yields a signal (NOT support)'; the under-generation sentence replaced by a date-only description; the journal outcome counts (SL / Target / BE) removed from summary.json, the cross-check and the 13-date table |
| m1 | MINOR | 'pending' test / ruff results in the documents | FIXED: final results recorded |
| m2 | MINOR | 'reproduces the frozen engine exactly' overstated (records differed in props / levels / trace) | FIXED in code and test: with default arguments the candidate engine now produces records identical FIELD FOR FIELD to the frozen engine on every session (the regression test compares every record with `dataclasses.asdict`); docstring updated |
| m3 | MINOR | 'the rulebook allows the pin bar in any colour' is an inference | FIXED: reworded (no colour stated in the text; p.10 draws it green; 'any colour' is the engine's reading) |
| m4 | MINOR | the author's numeric body remarks (AC32 50%, AC07 40%, AC01 60+) missing from the strength evidence | FIXED: added as IRF-context evidence |
| m5 | MINOR | 'highest broken' variant chosen after seeing the close | FIXED: authority DIAGNOSTIC_ONLY |
| m6 | MINOR | the expected direction is an inference | FIXED: labelled 'ASSUMPTION (not author evidence)' in the CSV |
| m7 | MINOR | the Muhurat exclusion is undocumented | FIXED: documented (no predicate changes) |
| m8 | MINOR | pivots are non-strict | FIXED: documented |
| m9 | MINOR | the journal Summary sheet says 189 trades vs 190 rows | FIXED: noted, nothing corrected |
| m10 | MINOR | the candidate `_method2` carries no `@implements` tags | KEPT ON PURPOSE and documented: variants must never be counted as implementers of source rules |
| N | NOTE | 246 gap cases vs 247 non-zero gaps | the 246 are the evaluable cases (previous session verifiable); stated as 'evaluable' |

Independence caveat: the audit script and this reviewer were run from this session's instructions; neither is a human review.

