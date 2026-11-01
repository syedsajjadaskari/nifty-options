# Independent agent review (Task 12)

**Who reviewed.** One fresh agent with no access to my reasoning (Agent 5, QA). It was instructed to read the six source documents *first* (text and rendered pages), write down its own reading of each rule, and only then read the registry, code and tests. It was read-only, ran
mutation probes on copies under a scratch directory, and returned a written report, kept verbatim as `agent_review_raw_report.md` (it describes the code *as reviewed*, before the fixes below). My own sequential passes (research → verification → engineering → data audit → tests) were not independent and are not counted as the review.

**What I did with it.** I verified the critical claim myself against the raw data before acting, fixed every CRITICAL and MAJOR finding, then re-ran the reviewer's mutation harness against the strengthened tests. Nothing below was accepted on the reviewer's word alone.

## 1. Findings and resolution

| ID | Severity | Finding | My verification | Resolution |
|---|---|---|---|---|
| **C-1** | **CRITICAL** | **Unflagged frozen-feed tail in 21 sessions (2026-08-03 … 08-31)**: 13–14 consecutive identical O=H=L=C minutes ending 15:15–15:28, then one bar jumping 150–200 points. The fabricated 15:25 candle set day highs/lows that became next-day PDR/PDS zones (a 201-point-wide zone for 08-04) and produced a CONFIRMED PDR signal on 2026-08-26. | **Confirmed independently**: 08-03 15:15–15:28 all 24,573.35, 15:29 jumps to 24,774.30; 21 sessions affected; 0 before 08-03 (median zero-range rows per session = 0). | **FIXED.** `stale_row_mask` (≥5 consecutive identical flat rows) excludes the rows and drops every 5-minute candle containing one (15:15/15:20/15:25); the *next* session is flagged `PREV_CLOSE_UNRELIABLE` and is not evaluated by strategies needing a previous-day reference (`DATA-QUAL-001`). Audit script now reports it. Verified: the 08-26 PDR signal is gone (`NOT_EVALUATED`). **Open:** the data itself must be re-downloaded or confirmed by the data owner. |
| **M-1** | MAJOR | Breakeven (Leg 2) stop filled at the entry price even when the bar gapped through it — a favourable fill (Rs 5,265 vs the no-favourable-fill Rs 1,365). | Reproduced. | **FIXED.** Leg-2/breakeven stops fill at the worse of (level, bar open), including the same-bar T1+BE case. Tests added; the same-bar variant was found by my follow-up mutant N7 (Rs 4,290 case). |
| **M-2** | MAJOR | Tests far weaker than 162 passing suggests: 74 of 116 single-edit mutants survived, including look-ahead-style mutants in `build_session_contexts` (daily-SMA index shifted to include today's close) and wrong previous-session picks. | Re-ran the harness. | **FIXED** (see §2): value-level `build_session_contexts` tests and ~40 boundary tests added. |
| **M-3** | MAJOR | IRF volume is unbounded (up to 13 signals/session, 325 at/after 13:00 vs 72 IRF trades in the report); every Method 1 signal was labelled `VERIFIED`; one failure can be reported as concurrent M1 and M2A; the "apply one method's rules at a time" rule was missing from the registry. | Reproduced (349 M1 events). | **FIXED as labelling, not as behaviour:** new registry rules `IRF-GLOBAL-004` (MISSING: per-day cap / time window / re-arming) and `IRF-GLOBAL-005` (one method at a time). Every IRF signal now carries `IRF-GLOBAL-004` unresolved, so **no IRF signal is ever `VERIFIED`**. Concurrent methods stay separate and cross-flagged. **Open:** the cap/window needs the author (AMB-IRF-13/14). |
| m-1 | MINOR | Method 2B drops the separate pullback/red-candle steps; record claimed `IRF-M2-003` without evaluating it. | Agreed. | Removed the unevaluated claim; added proposal `m2b_push_must_precede_red_candle` + boundary tests; AMB-IRF-15. |
| m-2 | MINOR | Default wick band 60–70 % rejects stronger sweeps (a synthetic 79 % / 97 % share). | Agreed; no effect on this data. | **Kept literal** (the guide says "approximately 60–70 %"); effect documented in AMB-IRF-10; decision left to the author. |
| m-3 | MINOR | `select_stop_distance` uses `abs()`. | Agreed. | Documented as an interpretation (AMB-IRF-12b) and tested. |
| m-4 | MINOR | ORB's conditional pin bar (pp.9–10 "across all three setups") was applied only to the Gap setup. | Agreed. | **FIXED**: applied to Methods 1/2 as a labelled proposal (`orb_pin_bar_in_methods_1_2`); registry/ambiguity updated. |
| m-5 | MINOR | One wrong page in `PDS-M3-001` (open items are on p.5, not p.6). | Agreed. | Corrected. |
| m-6 | MINOR | Previous-session semantics silent around a Muhurat session between sessions (2025-10-23) and around post-close prints (2026-03-11: gap −25.45 vs +1.10 depending on the close used). | Agreed. | **FIXED**: both now mark the next session's previous close as unverified and are not evaluated (AMB-DATA-06). |
| m-7 | MINOR | Overclaim: "defaults are the most literal reading" (false for proximity 5, near-band 15, MODERATE shapes); one test name claimed more than it asserted. | Agreed. | Wording corrected in code and docs; the duplicate test was removed from the claim, and the guard tests rewritten. |
| m-8 | MINOR | PDR/PDS "open must clear the zone" proposal changes counts ≈ 3× (PDR 35 → 102 if off). | Agreed. | Kept as a labelled PROPOSED rule; **flagged for author sign-off** (AMB-PDR-05). |
| I-1…I-6 | INFO | BE-in-T1-bar is conservative; PDR/PDS have no "zone failed" invalidation; RF return-inside has no time limit; journal "09:15" = candle label; guides' own single-target exits are not modelled (only the report's); EMA seeding differs slightly from TradingView. | — | Recorded in the ambiguity register (AMB-RF-02, AMB-DATA-04, AMB-EXE-03). |

## 2. Mutation testing (test strength), measured

| Stage | Result |
|---|---|
| Reviewer's original run, 116 single-edit mutants against the Phase 2 tests | **74 survived** (≈65 after discarding equivalents) |
| After the first round of fixes (all 116 re-run, tests at that point) | 89 killed · 25 survived · 2 patch targets no longer exist |
| Second run: the 19 named survivors + 12 new mutants aimed at the new code (frozen-feed, previous-session flags, BE fill, IRF scope flag, ORB pin bar) | 25 killed · 6 survived |
| Follow-up: tests for the real gaps (N7, X19, X20, X25) | all four killed |
| **Remaining survivors (8)** | IRF11, P2, R5, R7, B1, X16, X17, O8 — judged equivalent or removed, reasons below |

Reasons for the eight: **IRF11** (`lo=0` vs 1 in M3 support — the pivot loop starts at `k` anyway); **P2** (`i>j` vs `i>=j` — an earlier `continue` makes both identical); **R5** (lower bound of yesterday's range is implied for consistent data because a gap-up opens above the previous close ≥ previous low); **R7** (candle 0 cannot close below its own low); **B1** (`on_candle` history clip — the engine is causal, so the guard is defence in depth and cannot change an output); **X16** (concurrent same-direction check — IRF is short-only and ORB's long/short cannot both confirm); **X17** (`trend_check` index — every current caller passes index 0 for ORB; RF's index choice is covered by X25); **O8** (the redundant `not bullish_pin` term — removed, since a pin bar's wick can never reach the rejection threshold).
**Not done:** a full 116-mutant re-run against the *final* test file set. Later changes only added tests and rewrote one fixture, so earlier kills should hold, but I have not re-measured that.

## 3. Things the reviewer checked and found correct

* **200 EMA vs 200 DMA:** the 5-minute EMA(200) is justified and *numerically reproduces the author's own chart*: PDR p.4 legend 24,925.18 vs the code's 24,925.1768 on the 2025-10-07 09:40 candle. A 200-day SMA could not be reproduced (only 25 prior sessions existed then).
* No off-by-one in pivot confirmation; no look-ahead found in indicators, previous-day values, daily-MA indexing, gap computation or `on_candle` (by inspection and by the prefix-invariance property tests).
* IRF p.6 and p.10 worked examples reproduce exactly. Entry timing, close-vs-wick comparisons and the RF sequence match their documents.
* Every registry citation was substantively right (one page slip, fixed); no VERIFIED_EXPLICIT label that the source does not support.
* Stops/targets: ORB 30/60, IRF 60 with 35/40, PDR/PDS 70 with 35/40, RF 35–40 with an open target, T1 27 — all match. The report really gives **no** per-strategy Target-2 rule (derived mix: PDR 5×70 + 1×60, PDS 1×70 + 2×60, all other winners 60).

## 4. Unresolved after review (not concealed)

1. **Aug-2026 data is corrupt at the source** (frozen tail). Until re-downloaded, 27 sessions cannot be evaluated by PDR/PDS/RF/ORB.
2. **No strategy has a complete, objective rule set.** Every emitted signal is `PROPOSAL_DEPENDENT` or `RESEARCH_VARIANT`; none is `VERIFIED`.
3. IRF has no per-day cap/time window; the literal rules emit 874 events a year (349 + 215 + 310) vs 72 IRF trades in the report.
4. RF target, RF stop, PDR stop selection are UNRESOLVED; PDR/PDS target 70 conflicts with the report's recorded 60 on three winners.
5. The conflicts and ambiguities in `ambiguous_rules.md` need the strategy author.
6. Reviewer coverage of purely schematic figure pages is not itemised in its report (it states it read all PDFs including rendered chart pages); my own visual inspection list is in `source_document_inventory.md`.
