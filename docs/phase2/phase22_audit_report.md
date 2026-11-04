# Phase 2.2 - independent audit report

## 1. Who reviewed what (and what nobody reviewed)

| reviewer | independence | scope | raw report |
|---|---|---|---|
| **Agent 1 - source researcher** | fresh agent; read the PDFs *before* any earlier interpretation | all five PDFs incl. figures, performance report text; measured charts by pixel; compared itself with the Phase 2.1 records at the end | `phase22_source_research_raw.md` |
| **Agent 6 - QA reviewer ("Reviewer 4")** | fresh agent; read-only; ran its own mutants on a copy | all Phase 2.2 code (swings, structure trend, pins, zones, strict intersection, exit/auction layer, eligibility, selection, labels), tests, 15 quotes of the research notes, ORB p.7/p.12 and PDR charts 1, 2, 4 by eye | `phase22_audit_raw_reviewer4.md` |
| Phase 2.1 reviewers 1-3 | fresh agents | data layer, reconciliation, Phase 2.1 engines | `agent_review_report.md` |

**Not independently reviewed:** the final wording of `phase22_rule_verification.md`, `phase22_assumptions.md`, `phase22_author_decisions.md`, `phase22_execution_policy.md`, `phase3_readiness.md` (Reviewer 4 skimmed the matrix, execution policy and research notes only); IRF engine logic (unchanged in 2.2); the journal reconciliation (unchanged since 2.1); PDS charts and chart-4/PDS dating (no price axis; shape-matching only); the `on_candle` adapter under the new settings. Only 15 of the research notes' quotes were re-verified (15 of 15 verbatim and on the cited page); the rest (candle tables, pixel ratios) were not.

One brief of mine to the reviewer paraphrased the owner's Target-2 instruction wrongly ("proposed, never verified"); the owner's actual wording takes the guide values for IRF/ORB/PDR/PDS and only RF as a research proposal. That produced finding F3 below, which was still useful (see disposition).

## 2. Reviewer 4 findings and what was done

| ID | Severity | Finding | Disposition |
|---|---|---|---|
| F1 | **CRITICAL** | In the entry bar any Target-1 hit was scored BREAKEVEN (the fill *is* the bar's open, so the bar always "touched" the entry); 10 real entries affected | **Fixed.** `evaluate_exit(..., entry_at_first_bar_open=True)` (used by `simulate_exit`): in the entry bar breakeven is touched only by trading *strictly* beyond the entry; later bars unchanged; the generic call stays conservative. Tests for long/short, T1+T2, strict-beyond ambiguity. |
| F2 | MAJOR | `UNRESOLVED_AT_CLOSING_AUCTION` raised on ordinary days whose 15:30 stub row is non-fillable (78 of 88 flags false) | **Fixed.** `Bar.ineligible` carries the `BarEligibility`; only `CLOSING_AUCTION_REFERENCE` bars set the flag; post-close rows are skipped without it. Test. |
| F3 | MAJOR | Target-2 statuses VERIFIED_EXPLICIT for IRF/ORB/PDR/PDS; PDR/PDS conflict invisible on the signal | **Partly accepted.** IRF/ORB keep VERIFIED_EXPLICIT (the guides state them). PDR/PDS are now **`CONFLICTING`** and every signal carries `target_2_conflict`. RF stays PROPOSED_FOR_REVIEW. |
| F4 | MAJOR | Non-signal records stamped `VERIFIED` / `entry_rule_status = VERIFIED_EXPLICIT` (316 records) | **Fixed for `entry_rule_status`/`execution_status`** (`NOT_A_CONFIRMED_SIGNAL`). The legacy `verification_status` field on non-signals is documented as describing only the rules satisfied before the setup ended. |
| F5 | MAJOR | Signals did not carry the full configuration (swing_k, candle thresholds, ...) | **Fixed.** `execution_config.proposal_config` (all `ProposalConfig` values) and `trade_config`. Test that different settings give different records. |
| F6 | MAJOR/MINOR | Stale hard-coded labels in PDR/RF levels and RF docstring | **Fixed.** |
| F7 | MINOR | ORB Method 2 "near the MA" used yesterday's EMA under the structure trend | **Fixed** (`_near_ma_value`, unit-tested). |
| F8 | MINOR | Float error flips candles exactly on a threshold (pin 464, small 301, strong 303 of 400k random boundary candles) | **Fixed.** `EPS = 1e-9` on all candle-threshold comparisons; index-scale boundary tests. |
| F9 | MINOR | Missing calendar silently makes auction bars fillable; UTC timestamps classified by UTC clock | **Fixed.** Converts to IST; raises if the calendar lacks the auction regime for a date on/after 2026-08-03. |
| F10 | MINOR | `EXIT_AT_LAST_CLOSE` hid the auction truncation | **Fixed** (`closing_auction_truncated`). |
| F11 | MINOR | `SOURCE_35_40_BY_DISTANCE` unusable through `simulate_exit`; 35/40 literals in `select_stop_distance` | **Fixed** (green-candle reference passed; literals read from `SOURCE`). A 70 literal in `pdr.py` (`target_points_guide`) remains as a label only. |
| F12 | MINOR | ONE_ACTIVE: scope per strategy-day undocumented; no-fill treated as "never closed"; no stale-fill guard | **Fixed/documented.** `NO_POSITION` sentinel (skipped with a reason, blocks nothing); the exact next bar must exist; scope and tie order documented. |
| F13 | INFO | Non-strict pivots remain in ORB Method 2 (research variant) and IRF; ORB comment about pin vs rejection false for STRICT rejection | **Comment corrected.** The non-strict pivots are a documented difference (IRF's worked examples need the 3-candle swing; ORB M2 is a research variant). |
| F14 | MINOR | PDS default `ZONE_FULL` disagrees with the research's own chart reading (three thin PDS zones) | **Accepted and flagged.** The text ("both the body and the lower wick belong to the zone") wins until the owner decides; asymmetry with PDR is now stated next to the default (assumptions A16, author decision #10). |
| - | INFO | Registry wording "exact in chart 4" and "calibrated by two independent reviewers" overstated | **Reworded** (chart 4 is dated only by shape-matching; ~1-2 points). |
| - | INFO | RF p.9 images 1-2 also show no rising swing highs before the gap day (visual) | **Recorded** in `phase22_author_decisions.md` #2; not run through the engine. |

Source-research checks by Reviewer 4: ORB p.7 / p.12 image 1 - **confirmed**, the author's own uptrend example has *lower* recent swing highs (caveat: multi-day chart, no axis, while the engine rule looks at one session). PDR charts 1, 2, 4 - **confirmed** that the drawn zone's bottom is the body top (+1.4 / +2.1 points; chart 1's top overshoots the wick tip by ~6, not 4-5).

## 3. Test and mutation results (final files)

* **Tests:** see section 4 for the last full run. Lint: `ruff check` clean.
* **Reviewer 4's own mutation run:** 62 single-edit mutants of the new code; 48 of 59 non-equivalent killed (81%); 14 survived - 3 judged equivalent, 11 real gaps (single-sided swing-low strictness, `len(sh)<2 or len(sl)<2`, SHORT-side trend `and`->`or`, compression C3 `all`->`any`, zone-B reversal window, `candle_index` of cluster zones, cluster tolerance boundary, proximity sign on the zone bottom, the VERIFIED branch of `entry_rule_status`). Tests were added for every one.
* **My Phase 2.2 mutation set (65 mutants, run against the final files):** 59 killed, 5 survived, 1 invalid patch target. Survivors: swing-low lower index bound, PDS one-sided first interaction, ORB near-MA EMA (all three **fixed with tests** and re-run killed), pin close-fraction `<=`->`<` and "drop the `wick <= EPS` guard" (**equivalent** now that a tolerance `EPS` dominates and a zero-wick candle cannot satisfy the close-position test).
* **Round 2 (16 mutants aimed at the reviewer's gaps and the three fixed survivors):** 16 of 16 killed.
* **Phase 2.1 mutation set (143 mutants) re-run on the final files:** 127 killed, 7 survived, 9 invalid (their patch targets were rewritten in Phase 2.2). Survivors: IRF11, P2, R7, B1, X16, X17 (judged equivalent or defence-in-depth in Phase 2.1; unchanged) and P4 (a flat open treated as a gap up) - **P4 is now covered by a new test**. The 9 invalid targets were re-expressed against the new code in round 3.
* **Round 3 (6 mutants):** 4 killed outright (flat open, 35/40 boundary, RF trend candle, PDR open strictness); 2 survived: the strong-candle `>=`->`>` mutant is **equivalent** (a tolerance `EPS` dominates the comparison) and the PDS Method-2 `c.h >= zone.low` mutant exposed a real boundary gap, **fixed with a test and re-run killed**.

Honest limits: mutation scores are against my own mutants and Reviewer 4's; "equivalent" verdicts were made by me and the reviewer, not proven; no mutant exercised the docs.

## 4. What stays open (not hidden)

* `DATA-OPEN-001` - which session open the author's charts use - affects gap direction (10 sessions) and first-candle colour (13).
* No mechanical zone method reproduces PDR chart 3.
* The structure-trend default is partly contradicted by the author's own charts (ORB p.7; visually RF p.9).
* Closing-auction handling of open positions is flagged, not resolved.
* Every signal remains `PROPOSAL_DEPENDENT` or `RESEARCH_VARIANT`; none is `VERIFIED`.

**Final run on the final files:** 318 tests passed, ruff clean (the mutation runs above were made on copies taken before the last two tests were added; those two tests only add coverage).
