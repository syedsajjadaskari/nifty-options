# Phase 2.3 - independent audit

## 1. Who reviewed what
| reviewer | independence | scope | raw report |
|---|---|---|---|
| **Reviewer 5 (QA)** | fresh agent, read-only, ran its own harnesses on copies | the controller, exit model, eligibility layer, selection helpers, params, registry/traceability, the new tests; diffed the five engines' output against the Phase 2.2 snapshot over all 248 sessions; fuzzed the controller (1,500 random days + an independent oracle on 3,000 more); recomputed 50 hand-built bar sequences; 65 mutants of its own | `phase23_audit_raw_reviewer5.md` |
| Phase 2.2 source research (re-used) | fresh agent in Phase 2.2 | the five PDFs and the performance report | `phase22_source_research_raw.md` |

I re-read the performance-report passages that this phase touches myself (`[P2] [P7] [P11] [P14]`, table 3): 6 lots = 390 units at 65, 3 lots at Target 1 = 27 points, the rest at Target 2 "60 or 70, as recorded", "the stop on Leg 2 moves to the entry price", results exclude slippage. The PDFs were not re-read page by page in this phase; the Phase 2.2 independent reading (unchanged files) stands.

**Not covered by any reviewer:** entry-rule logic against the PDFs (Reviewer 5 took the owner's brief as the specification and compared engine output only); Variant B swing causality (not re-fuzzed); special sessions (Muhurat); the SOURCE_35_40 variant beyond one probe; aggregate real-data P&L (deliberately not computed); my five narrative documents were read by the reviewer while still being written.

## 2. The 12 audit points from the brief
| # | point | result |
|---|---|---|
| 1 | all approved rules implemented | yes: 14 new rules, each with an implementing function and a test marker; 5 more re-authorised (`phase23_user_approved_rules.md`) |
| 2 | state machine handles every outcome | yes: TARGET, T1_THEN_BUFFER_STOP, INITIAL_FULL_STOP, INCOMPLETE_EOD, NOT_EVALUABLE and the legacy BREAKEVEN (the last one tested after the review) |
| 3 | no second trade when prohibited | fuzz: 0 violations in 1,500 days; real data: no second trade except PDR/PDS after an INITIAL_FULL_STOP |
| 4 | PDR/PDS-only second trade | yes (tested; fuzz invariant) |
| 5 | no new trade after the cutoff | yes: 13:00:00 IST inclusive, tz-converted, also for the second trade; no fill after 13:00 in any fuzz or real day; passes under three different machine timezones |
| 6 | six-lot split | yes; equal legs are now enforced in `ExitPolicyConfig` too (after the review) |
| 7 | post-T1 stop exactly 6 points against the entry | yes: 50 hand recomputations, 0 mismatches; exact touches inclusive at E-6 / E+6, 5.99 not a touch |
| 8 | no trailing stop | yes: the level is computed once from the entry; "trail" appears only in comments/tests |
| 9 | non-executable auction bars cannot produce fills | yes (entry and exit), fuzz invariant |
| 10 | unresolved source rules documented | `phase23_source_conflicts.md`, registry authority fields |
| 11 | original strategies not unintentionally modified | IRF, ORB, PDS and RF output identical to the Phase 2.2 snapshot over all sessions (cap 1 and cap 99, three trend modes for ORB/RF); PDR differs only through the owner-approved zone default |
| 12 | no profit backtest started | confirmed by grep of scripts/src/reports; `reports/phase23` holds selection counts only |

## 3. Findings and dispositions
No CRITICAL or MAJOR finding. All items are MINOR/INFO.
| ID | Finding | Disposition |
|---|---|---|
| R5-01 | When Target 1 and the post-T1 stop fall in the same bar, the fill used the bar's open even though that open came before the stop existed (spurious slippage, over-conservative) | **Fixed**: fills at the stop level; test; the older boundary test was re-expressed |
| R5-02 | An approved tie-break winner that signals both directions was resolved by method-name order | **Fixed**: stays a conflict; test |
| R5-03 | Test gaps: legacy BREAKEVEN through the controller, signals during the second trade, `entry_price`, buffer < 0 | **Fixed** with tests |
| R5-04 | "100+ new tests" overclaim | **Fixed** (reworded; the true count is below) |
| R5-05 | Two Phase 2/2.2 docs and the registry row `EXE-OUT-001` still showed the old breakeven as current | **Fixed**: supersession banners and a registry amendment |
| R5-06 | `EXE-SEL-001` lacked `superseded_by`; `SEL-TIE-001` mixed owner rules with two controller interpretations | **Fixed**: `superseded_by` set; the interpretations are now a separate `PROPOSED_FOR_REVIEW` rule `SEL-TIE-003` awaiting the owner |
| R5-07 | `final_state = SECOND_TRADE_ELIGIBLE` at day end is easy to misread | **Documented** in the state-machine doc |
| R5-08 | records of another day were not rejected; naive signal timestamps raised | **Fixed** (rejected / read as IST) with tests |
| R5-09 | unequal legs and a post-T1 buffer wider than the stop were accepted by `ExitPolicyConfig` | **Fixed** (validation + tests) |
| R5-10 | Variant A for ORB means "previous session's last close vs its EMA(200)", not the first-candle location | **Documented**; owner to confirm; wiring regression test added |
| R5-11 | "reproduces" had no stated tolerance | **Fixed** (stated in `phase23_signal_selection.md`) |
| - | the state-machine doc said "the five engines are unchanged" | **Corrected**: entry logic unchanged; the PDR zone default changed |

Reviewer 5 also disclosed that, while stopping its own mutation harness, it sent SIGTERM to two pytest processes belonging to my concurrent mutation run; the affected mutants (`D16`, `D18`, exit code -15) were re-run and their results are the ones reported.

## 4. Tests and mutation testing
* **Full suite on the final files:** 372 passed; `ruff check` clean. (Baseline before any Phase 2.3 change, run on the preserved Phase 2.2 copy: 318 passed.)
* **My Phase 2.3 mutation set against the final files:** 57 single-edit mutants of `trading_day.py`, `exit_policy.py`, `execution_eligibility.py`, `selection.py`, `params.py`, `definitions.py` and `pdr.py` - **all 57 killed** (one pattern needed re-expressing after a refactor and its replacement was killed). Earlier in the phase the first 46 gave 41 killed, 3 survivors and 2 interrupted runs; the survivors exposed real test gaps (same-direction collisions between different strategies, the NOT_EVALUABLE sentinel, the causal entry-bar flag) that now have tests, and the interrupted runs were re-run.
* **Reviewer 5's own 65 mutants:** 55 killed, 9 survived (some overlap with mine): 5 equivalent (`max_entries` 2->3, the `> 99` guard, the entry-bar flag in the default mode, two leg-quantity swaps that TradeConfig makes identical) and 4 real gaps (legacy BREAKEVEN, POSITION_ACTIVE during the second trade, `entry_price`, the buffer < 0 check) - all four now covered, and the equivalence of the guard and the flag was replaced by real tests (`DayRules(max_entries=1)`, the legacy-mode causal-entry test).
* **Not re-run in Phase 2.3:** the Phase 2.1/2.2 mutation sets (143 + 65 mutants); the code they target changed only in `exit_policy.py` (post-T1 stop) and `definitions.py` (PDR zone), both covered by the new sets.
* "Equivalent" verdicts are judgements by the reviewer and me, not proofs.
