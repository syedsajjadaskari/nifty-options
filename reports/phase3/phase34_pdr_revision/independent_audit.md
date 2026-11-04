# Phase 3.4 - independent audit

**Written for:** the strategy owner and any reviewer who must decide whether the revised PDR signals can be trusted. Two independent checks were run: (1) a second implementation written by me from the raw data that imports nothing from the engine, and (2) a read-only review by a separate subagent (an AI reviewer with no write access to the repo, working in a scratch directory). Neither is a human review and neither verifies the *source rules* - they verify that the code does what the written rules say and that nothing else changed.

## 1. Second implementation (`scripts/phase34_independent_audit.py`) - ALL PASS

It re-resamples the 1-minute parquet to 5-minute candles with pandas, rebuilds zones A and B with vectorised swing logic, re-applies the three patterns and the close rule, and compares the result with the delivered CSVs. Results (`independent_audit_results.json`):

| check | n | result |
|---|---|---|
| candidate A signal stream equals the engine's (default patterns) | 81 | PASS |
| candidate A zone floor / ceiling / close / patterns / interaction candle per signal | 81 | PASS |
| candidate A EXAMPLE_LENIENT sensitivity count | 103 | PASS |
| candidate A zone of every session = independent zone, ceiling = previous-day high | 247 | PASS |
| the same four checks for candidate B | 81 / 81 / 103 / 247 | PASS |
| all 383 old signals and all 54 old trades compared for both candidates | 766 rows | PASS |
| removal tags of every old signal not valid under the revision equal an independent evaluation | 766 | PASS |
| journal: nearest candidate-A signal within 15 minutes of every PDR / disputed row | 12 | PASS |
| journal 2x2 table (thresholds x open rule, both candidates) recomputed incl. the open-anywhere runs | 8 | PASS (added after the review) |
| every source / test / script / data / Phase 3.0-3.3 report / PDF / journal file in the before-snapshot is byte-identical | 810 | PASS |
| the only new source file is `pdr_revised.py` | 1 | PASS |

Limits: I wrote both implementations, so a *shared misreading of a rule* would not be caught; the second check exists to catch coding errors, not interpretation errors.

## 2. Tests and static checks

* Full suite: **521 passed** (467 before Phase 3.4 + 54 in `tests/test_phase34_pdr_revision.py`); `ruff check src tests scripts`: clean.
* The reviewer applied 44 mutants (deliberate small bugs) to a scratch copy of the engine: 23 were caught, 21 survived. The survivors were real test gaps (red hammer, the green-colour requirement, threshold boundaries, the open-above-zone rule, the interaction test, a data gap, two signals in one session, tie-breaks, the lower-boundary option, the profile values). I added 16 tests for them and re-ran 19 of those mutants against the new tests: **18 are now caught; 1 survives and is equivalent** (the `i > j` guard on the confirmation is redundant because the loop already skips the test candle; the behaviour it protects is tested through the `confirmation_may_be_interaction_candle` option). I did not mutation-run every one of the 21 individually (the profile-values test is a direct equality assertion).
* One-time snapshot tests: `test_other_engines...`, `test_no_source_test_or_script_file...` and `test_stops_targets...` compare against `before_snapshot.json`. They will fail on any later legitimate edit of an earlier file; they honour `PHASE34_ALLOW_LATER_EDITS=1` (documented in the test file). The snapshot must not be refreshed.

## 3. Reviewer findings and what was done

The reviewer found **no blocking (S1) defect**. It rebuilt every signal from the raw parquet with its own integer-cent implementation (81 / 81 / 103, identical sets, fills and zones for 246 sessions, 766 tag rows, 12 journal rows), viewed 10 charts and parsed the captions of all 54 NEW charts, confirmed the 810 snapshot hashes, and found no profit/P&L figure anywhere.

| # | finding | disposition |
|---|---|---|
| S2-1 | The journal gap was attributed to the pattern thresholds only; the open-above-zone rule (PDR-011) matters as much. Rows 22 (2025-10-07, the guide's Example 3) and 134 (2026-05-19) are lost to PDR-011, not to the thresholds. | **Fixed.** `pdr_journal_agreement_2x2.csv`, a 2x2 table in the summary and a per-row attribution column (`candidate_A_gap_attribution`). Reproduced independently (A: 1+2, 1+4, 4+1, 6+1 exact+shifted). Labelled an agreement observation only: the lenient thresholds were read off four of these rows (circular); nothing is selected by it. |
| S2-2 | Tests would not catch many plausible defects (21 surviving mutants). | **Fixed** (section 2). |
| S2-3 | Candidates A and B are signal-equivalent by construction; the docs said the floor changes the test and the rejection pattern, and quoted 135 tolerance-sensitive days (the measured figure is 107; 135 is the union with "differs from A"). | **Fixed in the docs.** Stated plainly that B cannot differ from A in signals under the active rules; item 7 corrected; item 2 now gives 107 / 53 / 135 with their meaning. The tag UNRESOLVED_ZONE is kept but explained as concerning the drawn floor only. The reviewer's alternatives that invent no numbers (an exactly-repeated-highs variant; an author-hand-marked zone file for the ~31 signal days) are listed in `pdr_zone_construction.md` as options and **not implemented** (no new rule without the owner). |
| S2-4 | Rows A01 / A04 / A05 bundled the author's words with the brief's interpretation; candidate A's lower boundary, k = 1, the equal-high tie-break, `gap_min_points` and EPS had no status row. | **Fixed.** Author sentences stay `AUTHOR_APPROVED` (A01, A02 principle, A04, A05); their readings are new `OWNER_INTERPRETATION` rows (A01a, A04z, A05a); new `PROPOSED_FOR_REVIEW` rows A02g, A02h, A02i, A03b, A05b. All are in `rule_ids_unresolved` / the recorded rule status of every signal. |
| S3-1 | The 2025-10-23 (NOT_EVALUATED) rows carried a zone, gap and "price never interacted" text. | **Fixed:** gap, open-above and retest columns blank / "NOT EVALUATED"; zone notes prefixed "INFORMATIONAL, NOT EVALUATED". Test added. |
| S3-2 | The 81 signals are raw; 23 are timed after 13:00. | **Fixed:** stated in the summary (headline row B). |
| S3-3 | SEQUENCE_STATE_DIFFERENCE text mixed candle start and signal time. | **Fixed:** "candle starting HH:MM, confirmed HH:MM". |
| S3-4 | README omitted `_run_summary.json`, `independent_audit_results.json`; listed this file before it existed. | **Fixed.** |
| S3-5 | Fragile snapshot test. | **Mitigated** (section 2). |
| S3-6 | `PROFILES` duplicates the Phase 2.2 numbers. | **Partly:** a drift test now asserts the default profile equals `STRONG_CANDLE["MODERATE"]` and `PIN_BAR["OWNER_2X_CLOSE30"]` in `params.py`. The engine was deliberately **not** rewired to read `ProposalConfig` (that would change the config ids of every signal). |
| S3-7 | Chart cosmetics. | **Fixed:** multiple-high charts now use gap-up days only (the two non-gap days with unrelated zoom panels are gone); the clipped entry label is right-aligned; "-> INVALID" became "does NOT qualify (no pattern passes / close not above the ceiling)". **Not fixed:** journal-marker text still overlaps the legend on some example charts (cosmetic). |
| S3-8 | "The author skipped the spike" presumes intent. | **Fixed:** "the drawn box excludes the spike; it is not stated whether that was intended". |
| S3-9 | The author's drawn Example 3 shelf ceiling (25,084.40) is below the open (25,087.55), so PDR-011 passes on the drawn zone; wide zones stretch "small box". | **Added** to `pdr_unresolved_cases.md` (items 4 and 10: 14 days (A) / 17 (B) wider than 30 points, maximum 82.25). |

### Design challenges raised by the reviewer
* **(a) Candidate B anchored on the day high, tolerance 5:** defensible but not verifiable, and cannot change signals. Reported as such; the only live question it leaves is the spike policy (Example 3: 81 vs 82 signals).
* **(b) Preserving PDR-011:** consistent with the brief's wording but tuned for a zone below the day's high. Kept as the active setting; the open-anywhere stream (158 / 159) and the journal 2x2 are shown beside it.
* **(c) Default thresholds:** the reviewer recommended renaming the profile `PLACEHOLDER_DEFAULT`. **Not renamed** (the name is inside every config id and the earlier artefacts); instead every document now calls it a placeholder, reports 81 and 103 as co-equal, says the lenient numbers were read off four candles so "passes all four" is true by construction, and asks the owner for numeric pattern definitions or labelled example candles.

## 4. Not verified
* The strategy author's intent for anything marked `PROPOSED_FOR_REVIEW` or `OWNER_INTERPRETATION`.
* Guide Example 5 (undated); the PDF image candles beyond visual agreement; the Example 2 box, which appears to start before the previous session (not examined).
* The shared trading-day controller on the revised stream: **deliberately not re-run** (no portfolio back-test in this phase), so no claim is made about which executed trades would change.
* Whether the 13:00 cutoff is inclusive of exactly 13:00 (unchanged utility).
* The workbook `PDR_Revision_Day_by_Day.xlsx` beyond its sheets and headers (it contains no P&L column).
* The reviewer did not review the audit, docs or chart scripts line by line.
