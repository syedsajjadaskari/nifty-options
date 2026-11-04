# Independent QA review of Phase 2.1 (Reviewer 2 / Agent 5)

Repo state reviewed: /Users/syedaskari/algo/nifty-options (read-only; scratch copies under the reviewer2 scratch dir). Baseline: 225 tests pass.

Coverage disclosure: this run was interrupted once. COMPLETED: task 1 (central conclusion), task 2 (sessions.py/market_calendar.py/manifest/calendar), task 3(a)(b) (EMA legends, PDR dated examples), part of 3(e)/6, task 5 (22 mutation probes). NOT COMPLETED (not reviewed, no claim made either way): 3(c) journal reconciliation logic and its three "attribution differences", 3(d) Target-2 derivation, full page-citation audit of decision_records.yaml, task 4 for IRF/ORB/RF engines, core/exit_policy.py and exit arithmetic, scripts/phase21_build_data.py/provenance.py line-by-line.

## 1. Verdict on the central conclusion

AGREE: the 2026-08-03 frozen 15:15-15:29 window is NSE's Closing Auction Session (CAS), not corruption. It is real market structure, and keeping the candles is correct. Evidence I checked myself:

* Public sources (Sahi, Angel One, Groww, HDFC Sky, Bajaj Broking, Kotak Neo, multibagg): CAS starts 2026-08-03 for F&O-eligible stocks (all 50 Nifty constituents). Continuous trading ends 15:15. 15:20-15:30 order entry (random order-entry close between 15:28 and 15:30). 15:30-15:35 matching. F&O trades to 15:40 (NSE circular of 2026-05-29 reported by secondary sources; I did not read the circular).
* Day-one numbers independently reported: Nifty close 24,774.30; ~24,573 at 15:15; a 200.75-point move in the final 15 minutes (Bajaj Broking; implies 24,573.55 which equals the stored 15:14 close exactly). Stored data: 15:15-15:28 flat at 24,573.35, 15:29 bar closes 24,774.30. 2026-08-04: Trendlyne shows 24,614.90 (-159.40 from 24,774.30); stored 24,463.45 frozen then 24,614.90.
* Other published closes I located that equal the vendor daily series: 2026-08-28 24,175.65 (Trendlyne), 2026-08-31 24,080.40 (Navia), 2026-03-19 23,002.15 (Informist low), 2026-08-03 24,774.30 (multiple), 2026-08-04 24,614.90. All match to the cent.
* I recomputed reports/phase21/redownload_comparison.json from the raw files: stored vs fresh 1m for Aug/Jul/Jun = 7,916/8,648/7,896 rows, 0 differing (confirmed). Vendor 5m vs 5m aggregated from stored 1m: 18,538 candles matched (includes 13 Muhurat-session candles), 0 differing (confirmed). Flat-run detection on the FRESH raw files: Aug 21/21 sessions, Sep 21/21, Oct 19/19, Jun 0/21, Jul 0/23 (confirmed; start 15:15 or 15:16).
* Daily vs minute: 21/21 post-regime sessions have 15:30 print == vendor daily close (confirmed).

Caveats that the docs under-state (see findings F-01, F-02):
* The "stored vs fresh" identical result cannot distinguish a real market feature from a vendor-side artefact (the vendor would serve the same bytes either way). The discriminating evidence is the external closes and the rollout date, not the re-download. The docs lean on the re-download as if it were evidence about origin.
* The index value being frozen is real, but it is a stale, non-tradable value for the 15:15-15:28 minutes (derivatives trade to 15:40). Candles in that window are "real" as published index prints but are not an executable price series; and the catch-up step already shows on the vendor feed at 15:28/15:29, before the nominal 15:30-15:35 match, so the 15:25 five-minute candle's close is not knowable at 15:25 or 15:29:59 in real time. Any later exit/entry modelling on those candles (spot index) must treat them as non-fillable. I did not audit exit_policy.py for this.

## 2. Findings

### CRITICAL

**F-01 (CRITICAL) PDR default `pdr_open_vs_zone = "ANY"` emits signals where the "support" zone is above the open.**
Files: src/nifty_trading/strategies/params.py (pdr_open_vs_zone default), src/nifty_trading/strategies/pdr.py (interaction test `c.l <= zone.high + proximity`, with "bad" for ANY = False).
Evidence (run on the repo data, correct call `PDRStrategy(proposals=ProposalConfig(...))`; note the first constructor argument is `name`): confirmed PDR signals under ANY = 119, of which 66 (55%) have the session open BELOW the zone low, 14 inside, 39 above. NOT_BELOW_ZONE = 53 signals (0 below). ABOVE_ZONE = 39. Because the interaction condition is satisfied by the very first candle whenever price starts below the zone, ANY fires a "zone retest" and a long on the first green candle while price has never been above the zone, i.e. the previous-day-high zone is overhead resistance, not support. None of the three dated examples opens below the zone, so ANY is not what the examples support; NOT_BELOW_ZONE is equally consistent with them. The docs call ANY "consistent with all three dated examples" and choose it as default, which is the most permissive choice and unsupported by source text ("pulls back into the zone", "come back toward the zone").
Fix: default to the text-faithful ABOVE_ZONE or at minimum NOT_BELOW_ZONE; require price to have traded above the zone before the test; keep ANY as a labelled variant only. Correct docs/phase2/signal_counts_default.md (PDR 119 is inflated).

**F-02 (CRITICAL, materially false claim) "Example 3 opens INSIDE the zone and conflicts with the text" is an artefact of the engine's own zone, not of the author's chart.**
Files: docs/phase2/rule_registry.md:96 (PDR-011), docs/phase2/strategy_rule_resolution.md:281, docs/phase2/strategy_rules_final_draft.md:39, docs/phase2/phase3_readiness.md (PDR-D02), params.py comment above pdr_open_vs_zone, tests/test_phase21_source_examples.py (`test_pdr_example_3_conflicts_...`).
Evidence: I rendered PDR_Strategy_Guide.pdf p.4 at 8x and calibrated pixels on the position box (entry 25,111.80 and stop 25,071.20 give about 4.0 px per point). The purple zone the author actually drew on Example 3 spans roughly 25,080.4 to 25,084.6 (about 4 points tall, roughly +-1 point measurement error). The engine's zone for 2025-10-06 is [25,057.10, 25,095.70] (the 14:50 spike candle, body bottom to wick tip), 38 points tall, which is NOT what the author drew (the author ignored the 14:50 spike and marked the ~25,085 shelf). 2025-10-07 opens at 25,087.55, i.e. about 3 points ABOVE the drawn zone; the 09:15 candle's low is 25,083.50 (touches the zone top) and the 09:20 candle (low 25,077.10, close 25,111.15, entry marked 25,111.80) enters it and closes green. That is exactly the textual sequence "gap up, open above, pull back into zone, green candle". So Example 3 does NOT contradict the text when read with the author's drawn zone. The statement "all three dated examples reproduce only if the open is not required above the zone" is therefore false as a statement about the guide; it is true only for the engine's zone definition. The real finding is different: the engine's zone definition (single highest-high candle, body to wick tip) does not reproduce the author's Example 3 zone, which is a PDR-002/003 question, not PDR-011.
Verdict on the legitimacy question: the change was not profitability leakage (I found no use of P&L). It is a source-based change, but based on a mis-measured premise, and it moved the default to the most permissive reading (see F-01). Reproducing the engine signal at 09:20 on 2025-10-07 under ABOVE_ZONE is impossible only because the engine's zone is wrong, so the "test" is circular.
Fix: re-derive Example 3's zone from the chart, record the mismatch with the engine zone as the open item, restore ABOVE_ZONE (text) as default, withdraw the "conflicts" wording and the PDR-D02 blocker as stated.

### MAJOR

**F-03 (MAJOR) Readiness overclaim for PDR.** docs/phase2/phase3_readiness.md lists "the PDR gap-up + zone-test + green-candle sequence" as "fully automatic (verified, no assumption)". Given F-01/F-02 and the default open-vs-zone setting, this is not verified; it depends on a zone definition that fails to reproduce Example 3's drawn zone.

**F-04 (MAJOR) Weak runner test lets "never silently skipped" regress.** tests/test_phase21_source_examples.py:88-97 asserts only that the Muhurat date has a NOT_EVALUATED record and that the set of NOT_EVALUATED "ALL" dates contains it (`>=`). Mutants (single edit): `if d in ctxs:` -> `if False:` (every session reported NOT_EVALUATED, no signals ever) SURVIVES the full 225-test suite; `for d in sorted(infos)` -> `[:-1]` (silently drops the last session) SURVIVES. src/nifty_trading/strategies/runner.py has no direct test of "evaluable sessions produce engine records / exactly one record per non-evaluable day / no day dropped".
Fix: assert set of dates covered == set(infos); assert counts by status; assert evaluable sessions contribute engine output.

**F-05 (MAJOR) PDS open-vs-zone `ANY` mode is untested.** Mutant `"ANY": False` -> `True` in pds.py survives the whole suite. The new pds_open_vs_zone modes have no test on the ANY branch (coordinator's P20/P23 cover only edge equality).

### MINOR

**F-06 (MINOR) Doc/report inconsistencies in the data-repair evidence.**
* docs/phase2/data_repair_report.md:18 says "a single catch-up bar at 15:29 ... median range of 22.5 points". Data: the catch-up bar is at 15:29 in 12 sessions but at 15:28 in 9 (e.g., 2026-08-04: 24,463.45 -> 24,614.90 in the 15:28 bar); the median catch-up range in the analysis year is 33.2 (the 22.5 figure in reports/phase21/redownload_comparison.json belongs to a diagnostic month, not the analysis year). Same stale phrase is in nse_calendar_2025_2026.json ("one catch-up bar at 15:29").
* data_repair_report.md section 4 says "18,462 of 18,462" vendor-5m candles identical; the JSON says 18,525 of 18,525 (the 63-candle difference is the auction candles an earlier version dropped). Stale number.

**F-07 (MINOR) Quality-layer blind spots (src/nifty_trading/data/sessions.py).**
* classify_session accepts ANY run of >= 5 flat identical minutes inside 15:15-15:29 on/after 2026-08-03 as "expected" (flag CAS_FROZEN_WINDOW_KEPT) without checking that it ends with a catch-up bar whose close equals the daily close or that it starts at 15:15/15:16. A genuine feed stall inside that window would be silently kept as VALID.
* Frozen runs of 1-4 minutes are never detected (STALE_RUN_MIN = 5), anywhere.
* A session with dropped 5m candles becomes quality PARTIAL but its status is still USABLE_WITH_FLAGS (sessions.py line ~283 keys status on `flags`, not quality) and it is evaluated. Currently 0 such sessions, so no output impact; confirm the intended policy for PARTIAL (the manifest policy says only evaluable_by_strategies=true sessions are evaluated).
* Official close falls back silently to the 15:30 print when a daily row is missing (pre-regime error up to 88 points). Currently all 248 sessions are DAILY_VENDOR, so no impact; recommend a flag.

**F-08 (MINOR) Calendar/manifest evidence thinness.** nse_calendar_2025_2026.json: 10 of 14 holidays are tier B with no evidence strings; manifest non_trading_days carry `evidence: []` for them. I confirmed by web search: 2026-01-15 closure (Maharashtra civic polls, NSE circular 2026-01-12), 2026-03-26 Ram Navami, 2026-03-31 Mahavir Jayanti. I could NOT confirm 2026-05-28 (Bakri Id) in my search results (not contradicted; my recollection is that it is on the published list). Phase 1 wrong dates: 2026-03-27 (full session; holiday was 03-26), 2026-03-20 (Id-ul-Fitr fell on Saturday 03-21) and 2026-02-17 (Maha Shivratri was Sunday 02-15) are consistent with public calendars; 2026-05-27 (close 23,907.15) not independently re-checked by me. Internal consistency: 261 weekdays - 14 closures = 247 weekday sessions + Budget Sunday 2026-02-01 = 248 (verified).

### INFORMATIONAL

* EMA legend reproduction (task 3a): CONFIRMED. I rendered PDR pp.3-4 and read the legends: p.3 Example 1 "EMA 200 close 0 24,582.02" with crosshair bar O 24,566.35 H 24,571.35 L 24,557.25; p.4 Example 3 "24,925.18" with O 25,131.60 H 25,148.15 L 25,131.60. Independent pandas `ewm(span=200, adjust=False)` over all complete 5m candles from the warm-up start gives 24,582.025 (2025-09-01 12:50) and 24,925.177 (2025-10-07 09:40). Minor input differences the docs do not list for p.3: legend open 24,566.35 vs stored 24,565.60 (0.75 point); p.4 H 25,148.15 vs stored 25,147.80. These are immaterial to the EMA. Note the p.3 Example 2 legend (EMA 22,950.51, O 23,119.00) is from a bar not in the dataset and is not reproducible; the docs correctly cite only Examples 1 and 3.
* PDR dated examples (task 3b): engine signals reproduce on 09:25 (2025-09-02), 09:30 (2025-10-06), 09:20 (2025-10-07) with the engine zones [24,625.10, 24,635.00], [24,896.10, 24,904.75], [25,057.10, 25,095.70]. Examples 1 and 2 are consistent with the drawn zones within chart-reading error; only Example 3's drawn zone differs (F-02). Opens: 24,683.25, 24,923.90, 25,087.55 vs prev closes 24,625.05, 24,894.25, 25,077.65 (gap-ups 58.2, 29.65, 9.9). The test expectations (09:25/09:30/09:20) come from the journal's labels, so they are a consistency check, not independent evidence of the rule.
* The daily series: 496 bars 2024-09-02..2026-08-31, no duplicates, OHLC internally consistent, no bar on any listed closure, includes one Saturday and one Sunday special session and Muhurat days (acceptable as official daily closes). Vendor daily open differs from the first 1-minute open by up to 64 points (mean 6.5), high/low by up to 51/47 points vs minute extremes in the warm-up period; daily open/high/low are not used by any engine as far as I read, so no impact. The daily-vs-minute high/low differences were not explained in the docs.
* No look-ahead found in sessions.py: EMA is causal (SMA seed at index 199, each value depends on earlier closes only; warm-up sessions precede the analysis window); daily MA index = `bisect_left(dd_dates, d) - 1` uses only dates strictly before the session (the coordinator's survivor P10 is a test gap, not a code defect); previous session = previous USABLE session with explicit flags for skipped sessions, missing weekdays and prev-close-day mismatch; 2025-10-23 correctly becomes not evaluable by previous-day strategies (Muhurat day in between).
* Phase 1 files: archive hash check was not independently re-run by me.

## 3. Verified correct (independently)

* Closing-auction regime and start date; 24,774.30 close; 24,573.35/24,573.55 pre-auction level; 24,614.90; 24,175.65; 24,080.40; 23,002.15.
* 0 differing rows stored-vs-fresh for Aug/Jul/Jun; 0 differing vendor-5m vs aggregation; 21/21, 21/21, 19/19 frozen sessions in Aug/Sep/Oct, 0 in Jun/Jul; 21/21 post-regime sessions have 15:30 print equal to daily close.
* Manifest: 248 sessions, 246 VALID + 2 VALID_SPECIAL_SESSION, 247 evaluable, 14 non-trading weekdays, all official closes DAILY_VENDOR; weekday arithmetic consistent.
* EMA(200) legends on PDR pp.3-4 (to 0.005); EMA warm-up complete from the first analysis session.
* Calendar: closures 2026-01-15, 03-26, 03-31 and the Phase 1 errors on 03-27, 03-20, 02-17.

## 4. Mutation probes on new code (22 single-edit mutants on copies; relevant phase2/phase21 tests, survivors re-run against the full 225-test suite; baseline green)

Killed (14): CONTINUOUS_ONLY window end (M3), prev-close-day-differs off (M4), daily history count off by one (M5), PARTIAL never assigned (M6), official close taken from the 15:30 print (M7), stale-run minimum 5 -> 8 (M9), prev_candles ignoring CONTINUOUS_ONLY (M11), prev_close_source ignored (M12), unverified-gap check removed (M13), gap computed from 15:30 print (M14), PDR ANY blocks (M15), CAS ignored in classification (M20), SMA period 199 (M21), missing-weekday detection removed (M22).

SURVIVORS (8, full suite):
* M1 remove the `OFFICIAL_CLOSE_DIFFERS_FROM_1530_PRINT` flag (sessions.py classify_session) - the flag that tells the user the official close differs from the last print has no test.
* M2 OFFICIAL_CLOSE_TOLERANCE 0.05 -> 500 - same flag, tolerance untested.
* M8 `close_1530_print=infos[pd_].stub_close` -> official close (build_session_contexts): the LAST_PRINT_1530 alternative would silently use the official close; the existing test sets the attribute by hand and never exercises the wiring.
* M10 `above.append(... close > e_end)` -> `>=` (prior_session_ema_above boundary).
* M16 PDS `"ANY": False` -> True (F-05).
* M17 drop PDR-011 from `rule_ids_satisfied` when open mode != ANY (pdr.py) - the satisfied-rule list for PDR-011 is not asserted.
* M18 runner `if d in ctxs:` -> `if False:` (F-04).
* M19 runner drops last session (F-04).
(Coordinator's separately-found survivors IRF11, P2, R7, B1, X16, X17, P4, P10, P20, P23 not repeated.)

## 5. Honesty / readiness assessment

* The Phase 2.1 reversal of the "critical data defect" is well supported and honestly caveated (circular not read; secondary sources). I agree with it.
* Overstated: (a) PDR "verified" sequence and the claim that Example 3 forces ANY (F-02, F-03); (b) re-download "no change" presented as evidence of origin (see section 1); (c) stale figures in data_repair_report.md (F-06). Readiness verdicts "BLOCKED_BY_UNRESOLVED_RULES" for all five strategies and "no strategy approved" are conservative and justified; the "data foundation ready: Yes" is justified for the data layer, with the PARTIAL-status and auction-window blind spots in F-07 noted.
* I found no use of profitability or journal P&L to choose a rule in the code and docs I read (params.py states none; signal_counts_default.md disclaims it). I did not audit phase21_reconcile.py, so the claim "no journal row was used to choose any rule" is unverified by me beyond the PDR example-time test expectations (journal times used as check values).
