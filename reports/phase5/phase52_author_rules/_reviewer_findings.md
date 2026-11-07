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
