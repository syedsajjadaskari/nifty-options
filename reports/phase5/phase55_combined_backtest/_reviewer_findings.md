## Independent fresh-reviewer pass (Phase 5.5 + 5.6)

A fresh read-only reviewer re-computed the work from the raw candles. **No CRITICAL defect.** All 574 trades of A / B / C and all 1,808 robustness-window trades were recomputed (entry, exits, P&L, stop / T1 / T2 / post-T1 logic) with 0 mismatches; an independent controller selected exactly 196 / 188 / 190 trades; the report figures, cost scenarios, matching totals (one-to-one, 190 journal rows per configuration, date-only pairs never counted as matches, Saturday rows kept and flagged) and the baseline preservation (0 changed, 0 removed files) were confirmed.

Findings and disposition:

| # | finding | disposition |
|---|---|---|
| M1 | the claim "every weekday journal date has an automated trade" was false (19 / 29 / 27 rows in A / B / C are on sessions with no automated trade); the state field was always 0 because a lookup inserted empty days | FIXED (plain dict, state recomputed, sentence replaced by the real counts, new independent audit check and test) |
| M2 | stale "FAILURES PRESENT" / "pending" / "not recorded" text and a README line that said Phase 5.5 passed without reading the audit | FIXED (docs -> audit -> docs order; README derives the status from the audit result; real test / ruff results filled in) |
| M3 | second trades and rows already matched were described as "first valid signal" selections | FIXED (second trades are explained as controller re-entries after a full stop; only unmatched journal rows are compared); new audit check |
| M4 | RF opening-gap rejections were classified as UNRESOLVED_DISCRETIONARY_SELECTION | FIXED (OPENING_GAP_MISMATCH, RF-004; the unresolved wording no longer asserts a discretionary reading) |
| M5 | ORB primary cause decided by method order among ties, with a spurious gap secondary cause | FIXED (ties are flagged TIE-BROKEN in the evidence, the other tied cause is the secondary cause, counts of tie-broken rows are reported; the split is described as indicative) |
| minor | far-away signals labelled LATER / EARLIER (for example +210 minutes) | FIXED (more than 60 minutes: classified by why the engine has no signal near the manual entry, with the nearest signal quoted) |
| minor | controller table omitted MERGED_SAME_STRATEGY_METHOD; same-minute-group wording; exits in the entry minute described as stops only; "ranking" wording; tied days in the largest-difference table | FIXED in the generated text |
| minor | chart legend entry never drawn; docstring said "signal candle's end" | FIXED |
| minor | greedy matcher is not max-cardinality | DOCUMENTED (an exhaustive per-date assignment gives identical counts for A / B / C); no change to the matcher |
| minor | tautological / weak tests (fill >= signal time, factory type check, test name) | FIXED (second trade enters after the first exits; exact engine types pinned; names corrected; tolerant-stage test added) |
| minor | display rounding of two gross figures (662.95 shown as 663.0) | NOT CHANGED (display only; the CSVs hold the exact values) |
| minor | one A trade fills exactly at 13:00 (20260406-1-PDR) | NOTED: the cutoff is inclusive as in the frozen rule ENTRY-CUTOFF-001 |
| minor | the matcher is outcome-blind, so a journal 'BE' can pair with an automated full stop and be counted EXIT_MANAGEMENT_MISMATCH (for example PDR 2026-06-05 in B / C) | NOTED: by design (outcomes never choose pairs); the exit comparison is descriptive |
