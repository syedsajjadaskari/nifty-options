# Phase 2.1 independent review (Reviewer 2) - dispositions

**Who.** A fresh agent that had not seen my reasoning. Its report is kept verbatim as `agent_review_raw_report_phase21.md` (it describes the repo *as reviewed*, 225 tests). It was cut off once by a network error, so its **coverage was partial**: it did NOT review the journal-reconciliation logic, the Target-2 derivation, the page citations in `decision_records.yaml`, the IRF/ORB/RF engines, `core/exit_policy.py`, or `phase21_build_data.py`/`phase21_provenance.py`. A third reviewer was assigned that remaining scope (section below, "Reviewer 3").

**Central conclusion: independently AGREED.** The 2026-08-03 frozen 15:15-15:29 window is NSE's Closing Auction Session, not corruption; keeping the candles is right. The reviewer re-computed the stored-vs-fresh comparison (0 differing rows), the 21/21 - 21/21 - 19/19 frozen-session counts in Aug/Sep/Oct 2026 (0 in Jun/Jul), reproduced the EMA(200) values on both PDR chart legends, and found several further published closes (2026-08-28 and 08-31) that equal the vendor daily series.

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F-01 | CRITICAL | PDR default `pdr_open_vs_zone = ANY` emitted 119 signals, 66 of them with the open *below* the zone (the zone is overhead resistance, not support) | **Accepted and fixed.** Default restored to the text reading `ABOVE_ZONE`; `ANY` kept as a labelled variant; PDR default count is now 39. |
| F-02 | CRITICAL | "Example 3 conflicts with the text" was an artefact of the engine's zone (38.6 points, from a 14:50 spike), not of the zone the author drew (~4 points) | **Accepted.** My own measurement (~14 points, 25,085-25,097) was wrong; Reviewer 3 re-calibrated the chart three ways (axis ticks, the 69.90/40.60 position boxes, known candle prices) and confirmed about 4-5 points (25,080.5-25,084.5, +/-1) with the open ~3 points above it. Claim withdrawn: PDR-011 reclassified VERIFIED_QUALITATIVE (text: open is above the zone; Example 3 does not discriminate). The real open item is *which candle marks the zone* (`PDR-D09`). Tests replaced. |
| F-03 | MAJOR | Readiness listed the PDR sequence as "fully automatic, verified" | **Fixed** (readiness and final draft reworded; PDR blocked by D09/D05/D06). |
| F-04 | MAJOR | Runner test too weak (two mutants survived) | **Fixed**: coverage test asserts one record per day and engine output for evaluable days; both mutants now killed. |
| F-05 | MAJOR | PDS `ANY` open-mode untested | **Fixed** (test added, mutant killed). |
| F-06 | MINOR | Stale numbers in the repair report (catch-up bar 15:29 vs 15:28; median range; 18,462 vs 18,525) | **Fixed** in the report and calendar JSON. |
| F-07 | MINOR | Quality-layer blind spots | **Partly fixed**: a frozen run inside the auction window must start at 15:15/15:16 (else UNVERIFIED); a silent fallback to the 15:30 print for the official close now flags the session. **Still open and documented:** freezes of 1-4 minutes are undetected anywhere (threshold is 5); a `PARTIAL` session stays evaluable (none exists today; policy to be decided before any session ever becomes PARTIAL). |
| F-08 | MINOR | 10 of 14 holidays had no evidence strings | **Fixed** (evidence strings added; 2026-05-28 remains tier B - the reviewer could not confirm it by search, and it was not contradicted). |
| Info | - | Index values in 15:15-15:28 are real prints but not executable prices; `exit_policy` does not enforce this | **Documented** as a known limitation (`execution_rules.md` section 6, `phase3_readiness.md`); must be handled before any backtest. |
| Info | - | Re-download "no change" cannot discriminate real vs vendor-side artefact | **Accepted**: the data-repair report now says the discriminating evidence is the external closes and the rollout date. |

**Reviewer 2 mutation probes on the new code (22 mutants):** 14 killed, 8 survived (flag/tolerance of the official-close difference, close_1530 wiring, the strict EMA boundary, PDS ANY, PDR-011 satisfied-rule, two runner mutants). All eight now have tests that kill them (see the mutation section of the final report for the re-run against the final files).

---

# Phase 2.1 independent review (Reviewer 3) - dispositions

**Who / scope.** A third fresh agent, assigned exactly the scope Reviewer 2 did not reach. Raw report: `agent_review_raw_report_phase21_reviewer3.md`. **No CRITICAL finding** (no wrong signal, exit or look-ahead) in the IRF/ORB/RF engines or `exit_policy.py`. **Not completed by this reviewer:** it did not run the engines on the *drawn* Example-3 zone; PDS/PDR internals were only skimmed; it did not review `phase21_compare/redownload/build_manifests`, the calendar JSON or the 18,525-candle comparison; it re-checked only 2 of the 9 external closes and spot-checked (not exhaustively) the 52 page citations; IRF p.5 and ORB pp.6/12 figures were not viewed.

**Independently verified correct by Reviewer 3:** the journal numbers (190 rows vs 189, 5 Saturday rows, exactly 6 of 60 irreproducible cells, the three attribution differences by brute force over every single-row edit, 172/13/5 row statuses); the Target-2 derivation (PDR 5x70 + 1x60, PDS 1x70 + 2x60 unique; ORB 36 stops x 30 x 390 = 421,200; IRF 11x35 + 10x40); figure-based claims in the decision records (IRF Fig 3/4/5, RF p.9, PDS p.7); all live partition hashes equal the archive; raw re-download hashes and row counts equal the request log; engine timing, operators, pivot confirmation, M1/M2/M3 ordering, RF's strict sequence, ORB's 09:20 decision, and the exit arithmetic (stop before target on the same bar, worse-of(level, open) gap fills, 195+195, T1+BE same bar).

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| R3-06 | MAJOR | PDR Example 3 correction incomplete: files still said "~4-14 points" and "two independent measurements" and "open within chart-reading error". Reviewer 3 calibrated three ways (axis ticks, the 69.90/40.60 boxes, known candle prices): the drawn zone is about **4-5 points (25,080.5-25,084.5, +/-1)**, the open is **~3 points above** it, the 09:15 low touches its top. My ~14-point figure was wrong. | **Fixed** everywhere (rule data, decision records, final draft, params comment, test docstring, registry). Conclusion unchanged: default stays the text reading `ABOVE_ZONE`; the open item is which candle marks the zone (`PDR-D09`). **Caveat:** the engine was not run on the drawn zone, so "reproduces under the text with the drawn zone" is a reading of the chart, not an executed test. |
| R3-01 | MAJOR | "RF stops are too small for 35/40 (33.1 points each)" is wrong: 11 of 12 RF monthly cells reproduce with 35/40; only Aug-2026 (-Rs 17,550 = 45 points for 2 stops) does not. | **Fixed** (`RF-D05`, `execution_rules.md`, `ambiguous_rules.md`). |
| R3-12 | MAJOR | `tests/test_instruments.py` overwrote the live `data/metadata/nifty50_instrument.json` on every pytest run, contradicting "untouched / byte-identical". | **Fixed**: tests write to `tmp_path`; the file was restored from the unchanged archive (hash verified equal); provenance now *compares hashes* instead of asserting "untouched". |
| R3-14 | MAJOR | Readiness listed IRF M1, RF sequence and exit arithmetic as "fully automatic, no assumption". | **Fixed**: reworded to building blocks vs complete strategies; same-bar handling stated as a proposed convention. |
| R3-03 | MINOR | "22.5 each, or one 45-point stop" is loose (the report's August SL count needs two RF stops; 22.5 is only the mean). | **Fixed** (reconcile note and `RF-D05`). |
| R3-04, R3-21 | MINOR | "VALID" means only "no defect detected"; the count check hand-applies the three adjustments, so it confirms but does not derive; "three attribution errors" presumes which source is wrong; RF Aug stays unexplained. | **Fixed** in the conclusion text and readiness wording. |
| R3-13 | MINOR | `phase21_build_data.py`: an unguarded provenance write could leave a half-built, un-rerunnable state. | **Fixed**: all targets checked up front; provenance written atomically. |
| R3-16 | MINOR | "every trigger on a completed close, never a wick" is overgeneral; ORB units tagged VE although the record is VQ. | **Fixed.** |
| R3-17 | INFO | Decision text said a Method 2 attempt "re-arms on every later close above IRH"; the code re-arms only after the previous attempt resolves, with no expiry. | **Fixed** (text now matches the code). |
| R3-07, R3-09, R3-18 | MINOR | IRF-D11 recommended ">= 0.60" while the code uses the literal 0.60-0.70 band; ORB-D05 (pin bar in Methods 1/2) is an inference; ORB pin-bar assumption moves confirmations 23 -> 18. | **Fixed** (recommendation now matches the code; ORB-D05 labelled an inference). The count effect was already disclosed. |
| R3-20 | MINOR | "9 published closes" is 8 quoted directly + 1 (2026-07-31) derived by subtraction. | **Fixed** in the decision record. |
| R3-08, R3-19, R3-02, R3-05 | MINOR/INFO | A few quotation-marked phrases are paraphrases (meaning preserved); EARLIEST for PDR/PDS is 09:15 while the engine's earliest is 09:20 (no row affected); RF stop list includes an unneeded 30; "180 trading days" = 185 unique journal dates minus 5 Saturdays. | **Noted, not changed** (no effect on any output); the last is a useful reconciliation fact. |

---

# Final mutation run (Phase 2.1, against the FINAL code and tests)

143 single-edit mutants, each applied to a copy of the final `src/` and `tests/` (baseline verified green first: 215 phase tests), run against the `test_phase2*` files. **136 killed, 6 survived, 1 patch target no longer exists** (the old `ANY` default, which was reverted). The 6 survivors were examined earlier and judged equivalent or defence-in-depth (not re-judged by an independent reviewer): IRF11 (`lo=0` vs 1 in the Method 3 support pivot loop: the loop starts at `k` anyway), P2 (`i>j` vs `i>=j` in PDR: an earlier `continue` makes them identical), R7 (RF candle 0 cannot close below its own low), B1 (`on_candle` history clip: engines are causal, so it cannot change an output), X16 (a concurrent same-direction check that cannot trigger for short-only IRF / ORB's exclusive directions), X17 (the `trend_check` index: every ORB caller passes 0). Raw output: kept in the session scratchpad, not in the repo. This replaces the earlier partial re-runs; no earlier mutation figure should be quoted as final.

---

> **SUPERSEDED (Phase 2.1).** Finding **C-1 (CRITICAL, "frozen-feed defect") was a misdiagnosis that I confirmed too quickly**: the reviewer correctly found a pattern and I verified it exists, but both of us read real market structure (NSE Closing Auction Session from 2026-08-03) as corruption. The fix I made at the time (dropping candles and marking the following session unreliable) discarded real data and blocked 26 sessions. It has been reversed in Phase 2.1; the other findings (M-1, M-2, M-3, minors) stand. See `docs/phase2/data_repair_report.md`. The text below is kept unchanged as the historical Phase 2 record.

# Independent agent review (Task 12) - Phase 2 (historical)

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
