# Independent audit (Phase 5.2)

`scripts/phase52_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports). Result: **ALL 17 CHECKS PASS**.

| # | check | n | result | detail |
|---|---|---|---|---|
| 1 | the three PDR patterns audited are the ones enabled in the Phase 3.6 configuration snapshot | 3 | PASS | pattern names are in the frozen snapshot; the numeric values are the Phase 3.5/3.6 research defaults in strategies/pdr_revised.py::PROFILES (read here as consta |
| 2 | PDR: for every evaluated session the first eligible confirmation candle re-derived from the raw candles (body-based zone, strict open above, retest, patterns, close strictly above the ceiling) equals the engine's first PDR signal: no LATE_ENTRY_DEFECT and no missed entry | 247 | PASS | 67 armed setups, 33 first-eligible signals |
| 3 | PDS: for every evaluated session the first eligible confirmation (Method 1 / 2 on the first red candle at the zone, Method 3 only after a weak first candle and on the first support break) re-derived from the raw candles equals the engine's first PDS signal and method | 247 | PASS | 45 armed setups, 23 first-eligible signals |
| 4 | no setup in the PDR / PDS diagnostics is flagged LATE_ENTRY_DEFECT or ELIGIBLE_CANDLE_BUT_NO_ENGINE_SIGNAL | 246 | PASS | {'NO_SIGNAL_EITHER': 190, 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE': 56} |
| 5 | IRF diagnostics: EMA(200), entry price (next one-minute open), entry-EMA distance, EMA between entry and Target 1 and the running session low equal an independent recomputation for every confirmed IRF signal; the running low uses only candles closed before the signal | 874 | PASS | 272 signals where the final daily low is lower than the running low (a look-ahead implementation would differ) |
| 6 | IRF readings D6 (running low already below the initial range low), D7 (an earlier close below it), D8 (entry below the previous day's low) and the 13:00 cutoff flag equal an independent recomputation for every confirmed IRF signal | 874 | PASS |  |
| 7 | IRF flag counts quoted in signal_counts.json (28- and 27-point EMA readings, close below the running low, Target 1 beyond the running low) equal recomputation from the diagnostics table | 5 | PASS |  |
| 8 | candidate IRF Method 2A signals: each one's breakout, extension, FIRST red candle after the extension, support level (low or body low of that candle) and the FIRST later close below it match the raw candle sequence (the reference candle is never replaced by a later one) | 697 | PASS |  |
| 9 | the approved configuration's confirmed signals equal the frozen Phase 3.6 reference on date, strategy, method, direction and time (first-eligible principle already satisfied; only the PDS co-confirmation annotation differs) | 1083 | PASS |  |
| 10 | every candidate changes only its own strategy: RF, PDR, PDS and the other strategy are identical to the frozen signals under every candidate (no change to RF; no cross-strategy priority) | 3 | PASS |  |
| 11 | IRF Method 1 and Method 3 signals are identical under the first-red candidate (scope: Method 2A only) | 349 | PASS |  |
| 12 | ORB audit: first-candle OHLC, previous-day level, Method 1 level-broken flag, EMA and colour-matches-direction equal an independent recomputation on the 13 disputed dates, both directions | 26 | PASS |  |
| 13 | the Phase 3.6 signal table has no confirmed ORB signal on any of the 13 disputed dates (the engine produced none, so the controller could not have skipped one) | 13 | PASS |  |
| 14 | every required Phase 5.2 deliverable exists | 17 | PASS |  |
| 15 | every file in the Phase 5.2 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.1 reports, the frozen strategy files, the historical datasets, the manual journal, the handwritten PDF) is byte-identical | 15055 | PASS |  |
| 16 | the only files added outside reports/phase5/phase52_author_rules are the declared Phase 5.2 scripts, tests and new modules | 15063 | PASS |  |
| 17 | every file hashed in the Phase 4 freeze (engines incl. RF, controller, execution, session construction, framework) is unchanged | 26 | PASS | FROZEN-PHASE36-42cea2600bd4 |

**Independence caveat.** The audit script is a second implementation written by the same author as the pipeline; the fresh reviewer below is a separate pass.

## Tests and lint

* Before any change (existing suite): **650 passed, 1 skipped**.
* After implementation: **678 passed, 1 skipped (full suite; 650 passed/1 skipped before; 28 new Phase 5.2 tests)**
* `ruff check src tests scripts`: **All checks passed**

## Fresh independent reviewer (read-only sub-agent, separate implementation from the Phase 1 one-minute files)

Verdict: no blockers. The reviewer's own implementation reproduced the PDR (140 gap-up sessions) and PDS (106 gap-down sessions) first signals, all 874 IRF diagnostic rows (EMA(200), entry price, running low without look-ahead), the IRF candidate signal sets (939 / 1025), the 26 frozen-file hashes, the empty diff of the approved configuration, the absence of the day's-low / EMA-28 statements in all five guide PDFs, and three ORB dates by hand. Findings and what was done:

| # | severity | finding | disposition |
|---|---|---|---|
| 1 | MAJOR | 'first eligible candle: satisfied' holds only under the PRESERVED proposals (PDR-A07, numeric thresholds, PDS-M-001); 'by one candle' was wrong; looser readings not quantified; AC38 / AC02-AC40 'resolved YES' overclaimed; the `LATE_ENTRY_DEFECT` flag is circular by construction | FIXED: headlines, C5 and the AC rows now say 'satisfied under the preserved proposals; the author's example is NOT satisfied'; wrong sentence replaced; a diagnostics-only sensitivity table (readings A / B / C) added to the PDR audit and CSV; circularity disclosed (the independent audit and this review are the real checks) |
| 2 | MAJOR | day's-low readings D1-D5 do not reproduce AC19 ('entry is below days low') | FIXED: D6 (running low already below the initial range low), D7 (an earlier close below it), D8 (entry below the previous day's low) added as diagnostics, with an independent audit check; AC19 restated; nothing activated |
| 3 | MAJOR | ORB cause precedence mis-labelled 2025-10-16 and 2025-12-12 (Method 1 triggered and failed on candle quality, labelled trendline) | FIXED: causes are taken in method order (Method 1, Method 2, Gap) and a method whose level was broken outranks 'no level broken'; counts regenerated; unit test added |
| 4 | MINOR | PDR audit table had empty columns | FIXED (filled from the CSV) |
| 5 | MINOR | 27-vs-28 sentence inconsistent | FIXED (E1 and E2 readings stated separately, set listed) |
| 6 | MINOR | owner-decision numbering inconsistent (ORB O8 vs O9) | FIXED (ORB definitions = O8 everywhere) |
| 7 | MINOR | 'armed' used for two populations | FIXED in the audit texts ('armed' = retested; opened-above-zone counted separately); `independent_audit` check details keep the two counts labelled |
| 8 | MINOR | `IRFFirstRedStrategy` defaulted to a candidate; `_m2_step` is a verbatim copy | FIXED: default is now `BASELINE_SWING`; test added; the copy is documented and guarded by the baseline-equality tests and the 247-session equality check |
| 9 | MINOR | flag counts mixed tradable and post-13:00 signals | FIXED: cutoff columns added to the EMA and day's-low tables |
| 10 | MINOR | PDS: later strong red candles after a weak first red are not disclosed | FIXED: listed per session in the PDS audit and CSV; decision O6 widened |
| 11 | MINOR | 'first red candle' has a third ambiguity (after the extension vs after the breakout) | FIXED: added to O4 and the IRF audit (reviewer's count: 13 of 42 executed Method-2 trades differ) |
| N1 | NOTE | hardcoded dates exist only in reporting scripts, not in `src/` | no action (as designed; test covers `src/`) |
| N2 | NOTE | `PDSCoConfirmStrategy` can never annotate with current thresholds | disclosed already; forced test covers the path |
| N3 | NOTE | IRF Method 3 produced no confirmed signals in 247 sessions, so 'Methods 1 and 3 identical' covers only Method 1 in practice | noted here |
| N4 | NOTE | IRF reference charts draw an unlabelled moving average with empty Notes boxes | consistent with 'no rule in the guide' |

Independence caveat: both the audit script and this reviewer were run from this session's instructions; neither is a human review.

