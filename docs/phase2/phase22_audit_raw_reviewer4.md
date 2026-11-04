# Reviewer 4 (Agent 6) QA review - Phase 2.2

Baseline: 297 tests pass on the repo (151 s here). Repo untouched; all probes in scratchpad/reviewer4.

## Findings so far (verified by running code)

### F1 CRITICAL (wrong exit outcome; small incidence) - entry bar with a clean Target-1 move is always resolved as BREAKEVEN (exit_policy.py:252-254, with selection.py:92-98)
`evaluate_exit` checks `hit_adverse(b, entry)` in the bar that books T1. simulate_exit fills at the OPEN of the first bar and passes that bar
as bars[0], so for that bar `b.l <= b.o == entry` (LONG) / `b.h >= b.o` (SHORT) is ALWAYS true. Any T1 hit in the entry bar is reported
"T1 and breakeven both touched ... resolved as BREAKEVEN (adverse)" even when price never traded against the entry.
Failing input: `evaluate_exit("LONG", 24000, [Bar("m0",24000,24030,24000,24029)], policy_for("IRF"))` -> BREAKEVEN (should be T1 booked, then continue; T2 at 24060 in
`Bar(24000,24061,24000,24060)` is also turned into BE). On real data 10 confirmed signals (IRF 8, PDR 1, ORB 1) have an entry bar whose own range reaches +27 favourably
(e.g. IRF 2025-12-05 10:30, ORB 2026-04-30 09:20, PDR 2026-04-06 09:35) and are all forced to BE.
Fix: for the entry bar use strict inequality / skip the breakeven test (price cannot have "touched" the entry before it was filled at that bar's open), or record it as an ambiguity but resolve per a stated rule; add a test.

### F2 MAJOR - UNRESOLVED_AT_CLOSING_AUCTION is raised on days that have no closing auction (exit_policy.py:274-277, 291; execution_eligibility.py:62-63)
Every bar with start >= 15:30 (the 15:30 stub row, present on 225 of the pre-2026-08-03 days) is non-executable (POST_CLOSE), so a position still open at EOD
on an ordinary pre-regime day gets `skipped=1`, the flag string "UNRESOLVED_AT_CLOSING_AUCTION: ... non-executable bar ... reached" and `unresolved_at_closing_auction=True`.
Measured with the default engines + simulate_exit over the 247 sessions: 75 IRF + 3 PDS INCOMPLETE_EOD results on PRE-REGIME dates carry the flag vs only 10 IRF on the 21 regime days.
So 78 of 88 flagged positions are mislabelled (no auction existed). Phase 3 would read the flag as an auction-specific problem.
Fix: flag only when the first non-executable bar is CLOSING_AUCTION_REFERENCE (carry the BarEligibility on Bar, or a separate `reason`), report POST_CLOSE separately.

### F3 MAJOR - Target 2 statuses contradict the owner's instruction and the registry (params.py:218-222, 311-313; exec_config; rule_data.py EXE-T2-001)
Owner brief: Target 2 IRF 60 / ORB 60 / PDR 70 / PDS 70 / RF 60 are PROPOSED_FOR_REVIEW, "never verified/approved". `T2_TABLE` labels IRF, ORB, PDR, PDS as
`VERIFIED_EXPLICIT`; only RF is PROPOSED. Every confirmed signal carries `target_2_status: VERIFIED_EXPLICIT` (1041 IRF, 355 ORB, 118 PDR, 89 PDS records)
and tests/test_phase22_rules.py::test_target_table_statuses_never_promote_rf_or_hide_the_pdr_pds_conflict ASSERTS it. The same registry has EXE-T2-001 classified UNRESOLVED
("60 or 70 as recorded, assignment rule absent"), so the code and the registry disagree. For PDR/PDS the conflict exists only in `ExitPolicyConfig.conflicts`; the
signal's `execution_config` has no conflict field, so a downstream reader of the signal sees PDR T2=70 "VERIFIED_EXPLICIT" with the report's 60-winners hidden. docs/phase2/phase22_assumptions.md A3 states this choice openly ("IRF/ORB/PDR/PDS VE") - so it is a documented deviation, not a hidden one, but it is a deviation.
Fix: label all five PROPOSED_FOR_REVIEW (keep the guide quote as evidence), add `target_2_conflict` to execution_config for PDR/PDS, update the test.

### F4 MAJOR - non-signal records carry `verification_status=VERIFIED` and `entry_rule_status=VERIFIED_EXPLICIT` (base.py:83-93, 195-197)
`verification_for` is evaluated on the rules satisfied SO FAR. Measured over 247 sessions with default engines: IRF INCOMPLETE_AT_EOD 130, RF INCOMPLETE_AT_EOD 38, ORB INVALIDATED 148
records are `VERIFIED` and their execution_config says `entry_rule_status: VERIFIED_EXPLICIT` while the SAME dict says `trend_mode: STRUCTURE_EMA_SWING2` (RF, ORB) and RF
`target_2_status: PROPOSED_FOR_REVIEW`. No CONFIRMED signal is VERIFIED (all 874+29+37+23+2 are PROPOSAL_DEPENDENT or RESEARCH_VARIANT) - so the owner's "never VERIFIED" holds for signals -
but 316 records advertise VERIFIED with a proposal-based configuration attached. Fix: entry_rule_status = "NOT_A_SIGNAL" (or the status of the full configuration) whenever status != CONFIRMED.

### F5 MAJOR (requirement gap) - signals do not carry the full rule configuration (base.py:145-157; orb.py:107-108,151,205; rf.py:81)
`execution_config`/`proposals_used` omit `swing_k` (sensitivity table shows swing_k=1 changes ORB 9->15 confirmed), the strong/pin/small candle thresholds (ORB M2 `props` has no strong_candle/pin_bar; ORB M1 has no pin_bar/orb_pin_bar_in_methods_1_2), `small_candle_body_ratio_max`,
`prev_close_source`, `prev_day_level_window`, `ma_mode` for M1/M2, `zone_tie_break`, `max_signals_per_session`, and any selection policy. Two signals produced under different thresholds/swing_k are indistinguishable. Evidence: scratch probe p7.py (RF/ORB records printed).
Fix: add `"proposal_config": ProposalConfig.to_dict()` (it exists) plus TradeConfig to every record.

### F6 MAJOR/MINOR - stale and contradictory labels inside signals (pdr.py:47-48; rf.py:6-8,89)
PDR `reference_levels` hard-codes `"stop_selection": "UNRESOLVED(PDR-009)"` and `"target_points_source": 70.0` on every PDR record while execution_config says stop 35 USER_APPROVED and the target is in conflict; RF levels say `stop_selection: UNRESOLVED(RF-009)`; RF module docstring still says `RF_TARGET_STATUS = UNRESOLVED`. `target_points_source: 70.0` presents the guide value as "source" with the conflict dropped.

### F7 MINOR - ORB Method 2 near-MA test uses yesterday's EMA under the default trend mode (orb.py:180-186, definitions.py:339)
`structure_trend` returns `ma_value = last.ema` of the PREVIOUS session; `_method2` uses `t.ma_value` as "the 200 EMA" for ORB-M2-004, whereas the EMA5M modes returned today's candle-0 EMA. Measured |EMA(today c0) - EMA(prev last)|: mean 1.44, max 10.6 points, against bands of 5/15 points. Fix: compute `ma_value(ctx,0,"EMA200_5M")` in M2 independent of the trend mode.

### F8 MINOR - float boundary handling is nondeterministic at exactly-on-threshold candles (definitions.py:107-110,131; also pre-existing strong_*)
`_pin` has no tolerance; `is_small` has `1e-12`, which is smaller than one ULP at 24,000 (3.6e-12). On a 0.05-tick grid of 400k random candles vs exact Fraction arithmetic: pin 464, small 301, strong 303 mismatches (all exactly-on-boundary).
Failing inputs: `Candle(o=24016.9,h=24017.05,l=24016.55,c=24016.75)` - body 0.15 = 30% of range 0.5: exact -> small, code -> NOT small; `bullish_pin(24003.1, 24003.25, 24002.9, 24003.2)` exact True, code False.
The unit tests only pass because they use values exactly representable in binary (0..100 integers). Fix: compare in integer ticks (round(x/0.05)) or use a tolerance of ~1e-9 relative to range, and add a boundary test at index-scale prices.

### F9 MINOR - closing-auction layer silently degrades (execution_eligibility.py:32-38; market_calendar.py:load_market_calendar)
If `data/metadata/nse_calendar_2025_2026.json` is missing, `load_market_calendar` returns `MarketCalendar(source="MISSING_FILE")` with `closing_auction=None`; `classify_bar` then labels every auction bar CONTINUOUS (fillable) with no error/warning. Also naive wall-clock use: a UTC-aware timestamp is classified with its UTC clock (04:00 UTC = 09:30 IST -> NON_TRADING). Fix: raise (or warn loudly) when closing_auction is None and a bar date is >= 2026-08-03; reject non-IST tz.

### F10 MINOR - EXIT_AT_LAST_CLOSE hides the auction truncation (exit_policy.py:278-288)
When skipped>0 the research flatten returns `unresolved_at_closing_auction=False` and the `UNRESOLVED_AT_CLOSING_AUCTION` text is only in `events`, not in `unresolved`; a consumer reading `unresolved`/the flag sees an ordinary EOD flatten at the 15:14 close on an auction day. Documented in docs as intended; I'd still carry `closing_auction_truncated=True`.

### F11 MINOR - SOURCE_35_40_BY_DISTANCE variant is unusable via simulate_exit (selection.py:107, exit_policy.py:118-134)
`simulate_exit` calls `policy_for(rec.strategy, trade=trade)` without `reference_price/entry`, so that TradeConfig variant always returns NOT_EVALUABLE (verified: p8.py). The stop-config "one place" claim is also not fully true: `select_stop_distance` hard-codes 35.0/40.0 (exit_policy.py:113-114) and pdr.py hard-codes 70.0.

### F12 MINOR - ONE_ACTIVE semantics (selection.py:59,68,78-87,110-114)
(a) Scope is per (strategy, day): positions of different strategies never block each other, and the docstring/rule text does not say so. (b) `position_end_from_result(None)` (no fillable entry/no bars) and NOT_EVALUABLE results are treated as "never closed" and block the rest of the day (reported, not hidden, but a no-fill is not a position). (c) Ties at identical timestamps are resolved by alphabetical method name. (d) No silent drops: every skipped record is returned with a reason - verified. (e) `fill_from_next_bar` takes `rest[0]` of an assumed-sorted list and has no staleness guard (fills at a later bar if the exact bar is missing); not triggered on the real data (0 of 956 fills had bar.ts != signal_ts, p5.py).

### F13 INFO - single definition of "swing" is not used everywhere
TREND-SWING-001 is strict k=2; ORB Method 2 inner level/trendline still use non-strict `pivot_highs/pivot_lows(k=2)` (orb.py:138-144), IRF uses non-strict k=1/2 pivots.
`orb.py:228` comment "a bullish pin's upper wick is always below the rejection threshold" is false for OWNER_2X_CLOSE30 with REJECTION_WICK=STRICT (0.25): a doji whose close is 30% below the high has upper wick 0.30.

### F14 MINOR - PDS default zone contradicts the repo's own chart-agreement criterion (params.py pds_zone_upper_boundary="ZONE_FULL")
The owner's rule is "zone candidates chosen only by agreement with the source charts". phase22_source_research_raw.md (PDS real-chart examples) finds all three drawn PDS zones thin (3.6-10 pt, "looks like the LOWER WICK only"), yet the default is ZONE_FULL (body + wick). Measured over the 246 session pairs: median zone height PDR(default wick) 8.2, PDR(full) 21.9, PDS(default full) 25.4, PDS(wick) 10.3 points. The PDS text does say "both the body and the lower wick belong to the zone" (p.3, verified), so text and charts conflict; the default follows the text and the asymmetry with PDR is not flagged next to the default (PDS-ZONE-002 says "not assumed to be an exact mirror"). PDS dating in the research is tentative (undated charts), so this is MINOR; it should be an explicit author decision.

## Task 5 - source-research claims vs PDFs (pdfplumber text + rendered pages)
Text quotes verified verbatim AND on the cited page (15 checked): PDR p1 "Find the high where price reached a peak and then reversed"; PDR p2 "Lower boundary: the relevant candle-body level"; PDR p2 "If price keeps rising without returning to the zone, there is no setup"; PDR p2 "Very close approach"; PDR p2 "wait for a green candle and take the long entry on that confirmation"; PDR p1 "Target 70 points"; PDR p2 "At a 35-point stop the reward-to-risk ratio is 2.0 : 1";
PDS p3 "Both the relevant candle body and the lower wick belong to the zone"; PDS p2 "PDS is not a breakdown strategy"; PDS p5 "Wick-to-body ratio is not specified" (the doc cites "5-6": ok); PDS p6 "Distance of exactly 35"; PDS p4 "All three methods target 70 points"; RF p2 "A wick poking below is not enough"; RF p8 "Exact entry price"; RF p2 "opposite of the IRF strategy". 15/15 found; no misquote or wrong page found. ORB p11 text (units "decide ... index points, instrument price units, or rupee P&L", chart tag "target 60.80, stop 30.90") also matches.
Images rendered and read by eye (pypdfium2, 2.2-2.5x):
(a) CONFIRMED. ORB p.7 annotated Method-2 long chart and p.12 image 1 (same chart, unannotated): rally to a flat "major resistance" plateau, sharp sell-off, then a base on the rising trendline; the broken "inner resistance" (dashed yellow) and the bounce highs are clearly BELOW the plateau highs, i.e. the most recent swing high is LOWER than the previous one, while the swing lows rise along the channel. So "last two swing highs rising" is contradicted as a NECESSARY condition by the author's own uptrend example (caveat: the chart is multi-day with no axis; the engine's rule looks only at the single previous session, so it is not a like-for-like test). The research doc states this correctly and params.py carries the caveat. I add: RF p.9 reference images 1 and 2 (the only RF trade charts; image 2 is labelled Target 60.80 / Stop 40.65) show, before the gap day, a peak followed by lower highs/a flat range, not rising swing highs either (image 1: peak then decline into the entry day; image 2: flat range under the blue line) - so the default STRUCTURE_EMA_SWING2 would probably reject the author's own RF examples too (not run; visual only). This caveat is recorded only for ORB.
(b) CONFIRMED with a precision caveat. Zone box vs axis tags measured from pixels. PDR p.3 chart 1: tags 24,724.20 (y=763) / 24,653.85 (y=912.5) -> 2.125 px/pt; purple box spans about y=940..955 -> [24,633.6, 24,640.9]; the 15:00 candle of 2025-09-01 is body-top 24,632.25, wick tip 24,635.00, body-bottom 24,625.10 -> bottom edge = body top +1.4, NOT body bottom (-8.5); top edge overshoots the wick tip by ~6 (the research says 4-5). Chart 2: 1.235 px/pt, box [24,901.9, ~24,907.6] vs candle body top 24,899.80 / wick 24,904.75 / body bottom 24,896.10: box is ~5.7 pt tall, a [body bottom, wick] box would be 8.65; bottom is +2.1 above the body top, +5.8 above the body bottom -> body-top reading favoured, all within +2..3 pt of drift. Chart 4 (p.4, "Resistance" label): box height 27 px vs green 70-pt box 155 px -> ~12.3 pt, matching [body top, wick tip] = 13.05 and ruling out [body bottom, wick tip] = 25.2. Caveats: chart 4 has no axis or date, it is dated by the researcher's shape-matching, and its scale comes from the 70-pt box (+/-1 pt); the registry text "exact in chart 4" is therefore stronger than the evidence ("consistent within ~1 pt of a tentatively dated candle"). Chart 3 (a shelf of equal highs) is thin (~3.6 pt) and is not reproduced by any of A/B/C (tested in the repo's own test).
Other sentences I could not check: "calibrated by two independent reviewers" (PDR-011 text) - no artefact; "chart 1 overshoots its wick tip by ~5 points" - I measure ~6.


## Task 4 - mutation testing (62 single-edit mutants of NEW code; copy of src+tests in scratchpad/reviewer4/mut/r1..r3; baseline verified passing in the copy)
Mutants were run first against tests/test_phase22_rules.py (-x), survivors against the other test_phase2* files (and test_phase21_source_examples).
KILLED by test_phase22_rules.py (37): M01/M02 swing-high strictness before/after; M05 swing-high upper bound; M06 swing-low upper bound; M09 `h2>=h1`; M10 `close>=ema`; M11 wrong swing index; M12 EMA-NaN guard removed; M14 pin 30% boundary; M15 pin 2x boundary; M17 is_small boundary; M20 PDS-B green window; M23/M24 zone boundary selection; M26 cluster min_touches; M27 PDR intersection `and`->`or`; M32 `_execution_status`; M33 trend_mode NOT_APPLICABLE; M36 stop_status for the 40 variant; M40 RF target promoted to VERIFIED; M41 non-executable-bar skip; M42 EOD flatten on non-executable bar; M43 unresolved_at_closing_auction flag; M44 conflicts dropped; M46 15:30 boundary; M47 15:15 boundary; M48 weekend; M49 Muhurat; M50 ONE_ACTIVE `<` vs `<=`; M51 fill bar `>=`; M52 per-strategy key; M53 position_end +1 min; M54 is_valid blocked check; M58 pin close-distance direction (bearish); M60 auction flag text; M63/M64 swing lower bound.
KILLED only by older test files (11): M22 (tie-break), M29/M30 (PDS intersection), M37 (ORB stop), M39 (exclusivity guard `a+b`), M45 (breakeven check), M55/M56 (ORB/RF trend direction), M57 (open>zone.high), M62 (PDS M2 `c.h>=zone.low`), M65 (leg-2 stop = entry).
SURVIVED all tests (14):
| id | edit | verdict |
|---|---|---|
| M03, M04 | swing LOW strictness (`<` -> `<=` on the before-side / after-side) definitions.py:171 | REAL GAP - only swing highs have an equal-neighbour test; TREND-SWING-001 says "strictly" for lows too |
| M07 | `len(sh)<2 or len(sl)<2` -> `and` | REAL GAP - the "one swing high but two swing lows" case is untested (mutant would raise IndexError instead of ok=False) |
| M61 | `<2` -> `<1` in the same guard | REAL GAP (same case) |
| M08 | short-side trend `and` -> `or` (lower-high OR lower-low) | REAL GAP - the SHORT mirror is only tested for the all-true and wrong-side-of-EMA cases, never for a single failing condition |
| M18 | C3 compression `all(is_small)` -> `any` | REAL GAP - no test drives m3_compression_def="C3" through compression_ok/IRF Method 3 (only is_small unit tests) |
| M19 | zone method B: reversal window excludes the peak candle itself | REAL GAP - no fixture where only the peak candle is red |
| M21 | `Zone.candle_index` = first member instead of last for B/C | gap (metadata + reversal-depth input; not asserted for cluster zones) |
| M25 | cluster tolerance `<=` -> `<` | gap - the exact-tolerance boundary is untested |
| M28 | PDR proximity sign on the zone-bottom side (`zone.low - prox` -> `+ prox`) | REAL GAP - the only "below the zone" test sits 6 points under with prox 5, so the flipped sign gives the same answer |
| M34 | entry_rule_status mapping `{"VERIFIED":"VERIFIED_EXPLICIT"}` -> constant PROPOSAL_DEPENDENT | REAL GAP - the VERIFIED branch (the one that mislabels 316 records, F4) is never asserted |
| M16 | drop `wick <= 0 or` in `_pin` | EQUIVALENT (wick 0 with body 0 already fails the close-in-30% test) |
| M31 | drop `i > j` in PDR green check | EQUIVALENT (the preceding `continue` already guarantees i>j when the flag is off) |
| M38 | exclusivity guard for OWNER pin -> False | EQUIVALENT today (k=2 and a>=0.5 are constants, the branch cannot fire); the ratio-style branch is killed by M39 in the older tests |
Mutation score on non-equivalent mutants: 48/59 killed (81%). Note M01-M02/M05/M06 show highs are well covered; lows and the SHORT side are not.
Other test-quality observations:
 - tests/test_phase22_rules.py::test_target_table_statuses_never_promote_rf_or_hide_the_pdr_pds_conflict asserts IRF/ORB/PDR/PDS T2 == VERIFIED_EXPLICIT (the status the owner brief forbids; F3) and only checks that `policy.conflicts` exists - nothing asserts the conflict reaches the signal.
 - test_orb_and_rf_with_structure_trend_never_use_candles_beyond_the_prefix is non-vacuous (RF and ORB-M2 each confirm in the fixture, probe p6) but one-directional (prefix signals must be in the whole run; the reverse is not checked) and ORB only ever reads candle 0, so it adds little for ORB.
 - Boundary tests use binary-exact numbers (0, 100, 30.01...) - they pass while real tick data at the boundary mis-classifies (F8).
 - No test covers `evaluate_exit` on an entry bar that reaches T1 (F1), or an INCOMPLETE_EOD on a pre-regime day with a 15:30 stub row (F2), or `simulate_exit` with the SOURCE_35_40 variant (F11), or `classify_bar` with a missing calendar / non-IST tz (F9).
 - tests/test_phase22_rules.py::test_signal_in_the_auction_window_is_flagged_entry_blocked calls the private `_execution_status`; the same-minute path through `_rec` is exercised only by the dataset-wide count script.
 - The real-data tests (needs_data) tolerate +/-5.5 / 2.5 points versus hand-calibrated chart coordinates (circular for chart 4, which was itself dated by the researcher's shape matching).

## Task 1-2 results that PASSED my checks (no defect found)
 - Swing detection (definitions.py:160-171): index range `[max(lo,k), upto-k]` is right; j+k <= upto so confirmation needs candle j+k closed; strict on both sides; ties give no swing; prefix-invariant (the test's property also holds in my reading). structure_trend uses only `ctx.previous` (no today candles, gap never enters); direction mirror correct (SHORT: close<EMA and both SH and SL falling); NaN EMA -> None, <2 swings -> False, no previous session -> None. Real data: 48 LONG / 41 SHORT True, the rest False, 0 None over the 247 sessions.
 - trend_check wiring: orb.py:83 and rf.py:99 pass the right direction and prior-session data; ORB Gap/200DMA never calls it, correctly reported NOT_APPLICABLE; RF calls it at finalise time with data known at 09:20.
 - _pin: zero range -> False, wick<=0 -> False, doji OK; `>=` 2x and `<=` 30% as specified (float caveat F8). Exclusivity guard algebra correct (overlap possible iff a + k*a <= 1) and the exhaustive grid test agrees.
 - Zone methods: A first/last tie-break correct, B uses the latest confirmed swing high with a red candle in [j, j+k] (all known), C greedy clustering is correct (a rejected single cannot hide a later cluster because a single has no partner within tol), fallback flagged in `Zone.fallback`; PDR/PDS strict intersection is `c.l <= zone.high+prox and c.h >= zone.low-prox` (both sides, proximity applied symmetrically; PDS-M2 adds `c.h >= zone.low`); first interaction candle then green strictly after it (flag off). `pdr_open_vs_zone=ABOVE_ZONE` default strict `open > zone.high`.
 - classify_bar: holiday > special(non-evaluable) > weekend-without-special > pre-open > >=15:30 POST_CLOSE > auction (>=15:15 on/after 2026-08-03) > CONTINUOUS. Regime date inclusive (tested), 15:29 inside, 15:30 outside, Budget Sunday fillable. entry_executable(signal_ts) is the right bar (the next 1m bar starts at bar_end). Real data: 315 reference rows, 21 regime days, 9 IRF signals blocked, 0 others - matches the docs.
 - Causality of the fill: entry = open of the first 1m bar starting at bar_end (information available at the candle close), entry bar is evaluated for stop/targets consistently from its full range (F1 is the only problem there). Within-bar order, stop-before-target and gap-through fills as documented.
 - selection.apply_policy: sort key (None last, then ts, strategy, method) is safe; FIRST_VALID counts only valid events (an earlier ENTRY_BLOCKED does not consume the day); everything not accepted is returned in `skipped` with a reason (nothing silently dropped).
 - Labelling: no CONFIRMED signal is VERIFIED (all PROPOSAL_DEPENDENT/RESEARCH_VARIANT); RF target_2_status PROPOSED_FOR_REVIEW (never VERIFIED/USER_APPROVED, kept so even when rf_t2_points is changed; None -> UNRESOLVED -> NOT_EVALUABLE); stop_status USER_APPROVED only for the BASELINE variant, 40 -> PROPOSED_FOR_REVIEW, ORB VERIFIED_EXPLICIT (30 in every variant); PDR/PDS conflict text preserved in policy_for().conflicts, registry and docs.

## Task 6 - contradictions with the owner's instructions
 1. Target 2 labelled VERIFIED_EXPLICIT for IRF/ORB/PDR/PDS (owner: PROPOSED_FOR_REVIEW, never verified) - F3.
 2. "each signal carries the rule configuration that produced it" only partly met - F5; and non-signal records are stamped VERIFIED/VERIFIED_EXPLICIT - F4.
 3. "no look-ahead": none found in the new code. "no invented candles / historical data unchanged": no code path writes data; no invented closing price - but F1 (wrong BE) and F2 (false auction flag) affect the exit layer.
 4. "stops configurable in ONE place": mostly (params.TradeConfig), except `select_stop_distance` literals and the unusable SOURCE_35_40 variant - F11. ORB 30 preserved in all variants (verified).
 5. "zone candidates chosen only by agreement with source charts": PDS default ZONE_FULL disagrees with the research's own chart reading - F14; PDR default A with body-top boundary agrees (b above).
 6. "opening gap never establishes the trend": satisfied.
 7. Strict intersection default with near-touch as a labelled variant: satisfied (prox 0.0 default; 5.0 variant recorded in `proposals_used.zone_proximity_points`).

## Summary of severities
CRITICAL: F1 (entry-bar T1 always turned into BREAKEVEN; 10 real entries affected).
MAJOR: F2 (78/88 auction flags on days with no auction), F3 (T2 statuses vs owner), F4 (VERIFIED on 316 non-signal records), F5 (config incomplete on signals), F6 (stale UNRESOLVED/70 labels; MAJOR/MINOR).
MINOR: F7-F12, F14, test gaps (M03/M04/M07/M08/M18/M19/M28/M34/M61). INFO: F13, registry wording "exact in chart 4", "calibrated by two independent reviewers" unverifiable.

## NOT covered
 - IRF engine logic beyond the C3 compression hook and the shared helpers (irf.py unchanged in 2.2); IRF/ORB PDF figures other than ORB p7/p12, RF p9, PDR p3-4 (not re-read: IRF figures, PDS p4/p7 charts, performance-report claims, journal reconciliation).
 - scripts/phase22_build_docs.py output vs docs (only skimmed); docs other than phase22_source_research_raw.md, phase22_execution_policy.md, final_rule_matrix, strategy_rules_final_draft headers; the 12 other quotes of the research notes (RF/ORB candle tables, IRF section, measured pixel ratios of PDS charts) were not verified.
 - Chart 4 date identity and PDS chart dating (cannot be verified without price axes); chart-1 dating and entry-candle matching verified only through the researcher's own numbers.
 - Full 297-test run in the repo: passes (151 s); I did not run the mutants against the 21 non-phase2 tests (auth/config/storage), which cannot exercise this code.
 - No Phase 3-style P&L was computed; exit simulation was used only to count flags/outcome classes and entry-bar excursions (counts reported, no P&L).
 - Look-ahead via the BaseStrategy `on_candle` adapter (rebuilds contexts from history) was read but not stress-tested with this phase's changes.
