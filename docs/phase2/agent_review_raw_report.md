# Independent QA review: NIFTY 50 Phase 2 signal engine (Agent 5)

Scope read: all 5 PDFs (text + rendered chart pages), performance DOCX, journal XLSX; then src/nifty_trading/strategies/*, data/sessions.py, core/exit_policy.py, tests/test_phase2_*.py, tests/synthetic.py, docs/phase2/*, reports/phase2/*. Nothing in the repo was edited (all mutation work done on copies under the scratchpad `mut/` directory). Baseline: `pytest tests` = 162 passed.

Verdict: **1 CRITICAL (unflagged data corruption that produces a wrong signal), several MAJOR (one favourable exit fill, large test-coverage holes, unbounded IRF signal volume), no look-ahead defect found in the engine, no false VERIFIED_EXPLICIT label found.** The strategy logic is largely faithful to the sources; the registry is honest about almost every ambiguity. The weaknesses are in the data layer, exit fills, and test strength.

---------------------------------------------------------------------------------------------------

## 0. Findings (ordered by severity)

### CRITICAL

**C-1  Unflagged stale-feed tail in 21 sessions (2026-08-03 .. 2026-08-31) feeds fabricated candles into previous-day zones and a confirmed PDR signal**
- Where: `src/nifty_trading/data/sessions.py:243-250` (PreviousSession built from whatever complete candles exist), `_day_5m` (line ~68), and `reports/phase2/dataset_verification.md` (audit only mentions "extended records after 15:30" for 08-03/08-04; no stale-data check).
- Evidence: from 2026-08-03 onward every session has 13-14 consecutive 1-minute rows with O=H=L=C (15:15/15:16 .. 15:28) followed by a jump on 15:29. Example 2026-08-03: 15:15-15:28 all 24573.35, then 15:29 = O 24573.35 / H 24774.30 / C 24774.30 (a 201-point "move" in one minute; the dataset's 4th-largest 1-minute range). 2026-08-18: flat 24166.35 for 14 min then 24154.90. Before 2026-08-03 the maximum zero-range minutes per session is 0-1. So the 15:15 and 15:20 5-minute candles are zero-range and the 15:25 candle is a flat stub plus a step, on 21 sessions (the Aug 03/04 "extended records" are the same freeze showing up after 15:30).
- Consequences found: (a) the fabricated 15:25 candle sets the day high/low on 08-03, 08-18, 08-25, 08-26, 08-27, so the next-day PDR/PDS zone is built from it: PDR zone for 2026-08-04 = [24573.35, 24774.30] (201 points wide, candle 15:25); PDS zones for 08-19, 08-27, 08-28 start at candle 15:25. (b) `probe3`: `PDRStrategy` emits a CONFIRMED signal on 2026-08-26 09:25 on zone [24260.05, 24334.55] whose source candle is the stale 15:25 candle. (c) EMA/last_5m_close and `prior_session_ema_above` for those sessions use the stale closes.
- Document says: nothing about data; PDR/PDS zones must come from real previous-day price action (PDR p.1-2, PDS p.3).
- Failing input: `build_session_contexts(load_one_minute())`, `PDRStrategy().evaluate_session(ctxs[date(2026,8,26)])`.
- Fix: add a stale-run detector in `classify_session` (>= N consecutive identical O=H=L=C rows, or zero-range 5m candles before 15:25) -> flag `STALE_TAIL_FEED`, drop affected candles (treat as incomplete) and make `REQUIRES_PREVIOUS_SESSION` strategies return NOT_EVALUATED for the following session; escalate to the data owner (re-download Aug 2026). Add the check to the dataset audit and a test on a synthetic frozen tail.

### MAJOR

**M-1  Breakeven stop fills at entry even when the bar gaps through it (favourable fill)**
- Where: `src/nifty_trading/core/exit_policy.py:264-270` (`_be`: `px = entry if stop2 is None else stop2`) and the Leg-2 branch (lines ~232-241). `stop_fill` (line 203) is applied only to the original stop.
- Document (performance report, "Strategy Framework"): Leg-2 stop moves to the entry price; the module docstring promises "a stop gapped through fills at the worse of (level, bar open)" and "no favourable fills".
- Failing input (probe1): LONG entry 24000, bar0 = O24000 H24028 L24005 C24020 (T1 booked), bar1 = O23980 H23990 L23975 C23988 (opens 20 below entry). Code returns BREAKEVEN, leg2_exit 24000, pnl Rs 5,265. A no-favourable-fill result is leg2 at 23980 -> 27x195 - 20x195 = Rs 1,365. Short mirror gives the same 5,265.
- Fix: `px = min(entry, bar.o)` (long) / `max(entry, bar.o)` (short) for the BE exit; add a test (none exists; mutants E9 and the BE-gap case are unkilled).

**M-2  Test suite is much weaker than the "162 passed" suggests: 74 of 116 mutants survived**
- Method: 116 single-edit mutants (comparisons, indices, sets of lines) applied to a copy and run against `tests/test_phase2_*.py` (141 tests, `-x`). 89-mutant batch: 33 killed, 56 survived; 27-mutant batch: 9 killed, 18 survived. After removing the obviously equivalent ones (listed in section 3) roughly 65 real survivors remain.
- Worst holes (all in section 3): the real `build_session_contexts` wiring is never value-tested (previous session pick, previous high/low/last close, `open_price`, `prior_session_ema_above` ordering, daily-MA index/divisor); IRF equality boundaries (M2A/M2B/M3 `<` vs `<=`, close == IRH for attempt start); M3 compression/support; RF boundaries (`<` vs `<=` on RF Low/High and yesterday's range); PDR/PDS zone-touch and open-clear boundaries; recent-resistance FIRST vs LATEST selection (the default is untested, the opposite default passes all tests).
- The `-x` real-data tests (`needs_data`) check counts and invariants only (47 evaluable daily-MA sessions, no value assertions).
- Fix: add boundary tests listed in section 3; add one test that builds a 3-session synthetic 1-minute frame and asserts `previous.high/low/close_official/last_5m_close`, `open_price`, gap sign, `prior_session_ema_above[0]` is the previous session, and `daily_sma200_prev` equals the SMA of the closes strictly before the session.

**M-3  IRF volume is unbounded; one failure is reported as several signals; Method 1 is labelled VERIFIED**
- Where: `irf.py:52-85` (`_scan`), `irf.py:69-73`, `base.py:verification_for`.
- Evidence (probe2, 247 real sessions): confirmed IRF signals per session histogram 0:73, 1:9, 2:29, 3:24, 4:22, 5:18, 6:26 ... up to 13; 325 confirmed signals have bar_end >= 13:00; 130 carry `concurrent_methods`. Versus 72 IRF trades in the performance report over 12 months. The registry flags this (AMB-IRF-03/08), but every Method 1 record is stamped `verification_status = VERIFIED` (349 of them), which reads as "tradable per the guide", while the guide gives no per-day cap, time window or re-arm rule.
- Document: IRF p.13/14 "Apply one method's rules at a time"; "Apply only the rules of the method that is forming". This golden rule is not in the registry and the engine does the opposite on purpose (concurrent M1+M2A on one candle).
- Failing input (probe1 B): `[IR(95,100,90,98), (98,104,97,103), (103,106,102,105), (105,106.5,101,102), (102,105,101.5,104), (104,104.2,99,99.5)]` -> Method 1 and Method 2A both CONFIRMED at 09:45. M1 treats candle index 4 as a fresh "breakout candle" (it closed above IRH, as did candle 2), while the M2 attempt keyed to candle 1 is still alive; `att.b == m1[1]` consumption (irf.py:72) only fires when the same candle is both.
- Fix: rename status to `PATTERN_VERIFIED` (or add `rule_ids_unresolved=["IRF-M1-SCOPE"]`) until the author decides scope; add the "one method at a time" rule to the registry as an unresolved item; provide a one-signal-per-attempt de-duplication field.

### MINOR

**m-1  IRF Method 2B drops source steps 3-4 as separate conditions**
`irf.py:146-153`. IRF p.9 lists: (3) pull back, then push back above resistance, (4) a red candle forms, (5) a red candle closes back below resistance. Code needs only: latest-candle red, close < R, and any candle in (pivot, i] (including candle i itself) with High > R. No pullback check; steps 4 and 5 may be one candle (Fig. 4 on p.9 draws two separate red candles). Registry IRF-M2B-002 documents `m <= i`, but the signal record claims IRF-M2-003 ("a red candle forms during the extension") as satisfied without evaluating it (it is satisfied only because candle i is red). Survivors IRF8/IRF12 show no test constrains this. Fix: record as a proposal flag (`m2b_same_candle_push_and_close`), add tests.

**m-2  IRF default wick-share band rejects stronger sweeps**
`params.py:38-40,112`, `irf.py:178-181`. IRF p.12: "approximately 60-70% of the upper wick is outside" and "a wick that barely clears IRH" is the failure case. Default `BAND_60_70` rejects 79% and 97% shares (probe1 D: H=130, O=92 -> share 79% -> `WICK_SHARE_OUT_OF_BAND`). Labelled PROPOSED so not a false claim, and on the 2025-26 data MIN_60 yields no change (0 M3 confirmed in 247 sessions, 37 candidates), but the default makes the stronger sweep disqualify itself. Suggest default `MIN_60`.

**m-3  `select_stop_distance` uses `abs()`**
`exit_policy.py:99`. IRF p.2/p.10: stop chosen by the distance from entry to the most recent green candle (above entry for a short). `abs()` hides the sign: a green high 50 points BELOW the short entry returns 40, 20 below returns 35. Signed distance would send both to 35. Rare, undefined in the source; make it explicit (proposal flag) and test the sign. Survivor X8 shows no test notices.

**m-4  ORB conditional pin-bar rule not applied to Methods 1 and 2; not listed as open**
`orb.py:70-71`. ORB p.9 "Candle quality is an important filter across all three setups" and p.10 table "Conditional: bullish/bearish pin bar" are general; Methods 1/2 steps (pp.3-5) say "strong body, small wick". Code applies the pin-bar alternative only to the Gap setup. Registry ORB-CANDLE-001 says IMPLEMENTED_WITH_PROPOSAL but no ambiguity entry says M1/M2 ignore the conditional pin bar. Add to ambiguous_rules.md.

**m-5  Page citation errors in the registry (small)**
Checked every rule's cited pages against the pages. All substantive citations are right. Exceptions: `PDS-M3-001` unresolved text says "(p.6 open items)" for three items; "Size of the small support" and "Support break: close or touch?" are on **p.5**, only "Method 3 trigger" is on p.6. `tests/test_phase2_integrity.py::test_source_pages_do_not_exceed_the_actual_document_page_counts` checks only max(page) <= page count, so wrong pages could never fail it.

**m-6  Previous-session semantics around special sessions are silent**
`sessions.py:243-245`. `missing_weekdays` treats any date present in `infos` as explained, including EXCLUDED sessions. 2025-10-23's previous session is 2025-10-20 although a Muhurat session (2025-10-21, close 25826.25) exists; no flag (gap +207.7 vs +232.3). Separately 2026-03-10 has 29 post-close rows frozen at 24261.60 while the 15:30 stub is 24288.15; 2026-03-11 opens 24262.70, so the gap flips from -25.45 (stub, what the code uses) to +1.10 (final print). The rows are clipped and flagged on 03-10 but nothing flags 03-11's gap as ambiguous; this can flip a PDS/RF/ORB-gap eligibility. Fix: flag `PREV_SESSION_HAS_EXCLUDED_SESSION_BETWEEN` and `PREV_CLOSE_AMBIGUOUS(stub vs post-close)`.

**m-7  Overclaims in documentation and test names**
- `master`/`params.py` say defaults are "the most literal reading". `zone_proximity_points=5`, `ma_near_band_points=15`, `ma_close_margin_points=5`, `strong_candle=MODERATE`, `m3_compression_n=2` are mid-range choices, not literal readings (literal would be 0 proximity). They are labelled proposals, so low risk, but the sentence is wrong.
- `test_verified_explicit_rules_are_never_marked_as_proposal_based_without_a_reason` only tests PROPOSED != IMPLEMENTED_VERIFIED (duplicate of the previous test); the name claims more.
- `test_on_candle_...ignores_future_rows`: removing the look-ahead guard `hist[hist.timestamp <= now]` (base.py, mutant B1) does not fail it because the engine is causal; the guard is untested defence in depth (INFORMATIONAL).

**m-8  PDR/PDS proposals change counts materially (flagged, but note)**
`require_open_clear_of_zone` default True: PDR 39 -> 113, PDS M1 9 -> 34 / M3 15 -> 36 if off. The PDFs do not require it (PDR p.2 interaction list includes "price enters zone"). Correctly labelled PR; the 3x effect deserves author sign-off before it is relied on.

### INFORMATIONAL
- I-1: `exit_policy` BE-in-T1-bar rule (`exit_policy.py:227`) classifies any T1 bar whose low touches entry as BE; the first bar after a signal opens at/near entry, so a one-minute 27-point move is always BE. Conservative, not favourable.
- I-2: PDR/PDS have no "zone failed" invalidation (price closing far through the zone) and the awaited green/red candle may arrive hours after the touch. Source silent; registry PDR-005 does not mention.
- I-3: RF "return inside" has no time limit (R1). Source silent; flagged AMB-RF-02.
- I-4: Journal ORB entry time is "09:15" (candle label) while the guide decides at 09:20; code uses 09:20 (bar_end). Consistent with the design fact, just a labelling mismatch in the journal.
- I-5: The strategy PDFs describe a single target on the whole position; the exit model (T1 27 / BE / T2) is the report's, not the guides'. `exit_policy` implements only the report model. Fine for Phase 2 but note the guides' own exits are not evaluable.
- I-6: EMA(200) is SMA-seeded on the first 200 dataset candles and continuous across sessions (excluding the Muhurat session), so the first ~3 sessions are NaN and Sept-2025 values differ slightly from TradingView (convergence ~600 candles).

---------------------------------------------------------------------------------------------------

## 1. My own independent reading of the sources (done before reading the code)

**IRF (short only; p.1-14).** Initial range = high/low of the 09:15-09:20 candle, wicks included, final at 09:20 (p.3). Red = close<open, green = close>open (p.3). Closes confirm, wicks do not (p.3, 9, 14).
- Method 1 (pp.5-6, 13): a candle closes above IRH; the VERY next candle closes back inside the range -> short at that close; no S/R break required. Conflict: p.14 card says "next candle or following candle".
- Method 2 (pp.7-10): close above IRH, further upward extension, a red candle, then either (A) a candle closes below recent support (pullback low), or (B) price pulls back, pushes back above recent resistance (top of first push), a red candle forms and a red candle closes back below the resistance. An immediate close back inside after the breakout is Method 1, not 2 (p.9). Recommended: confirm on closes.
- Method 3 (pp.11-12): small candles inside the range; a red sweep candle with a significant upper wick above IRH (about 60-70% of the wick above IRH; wick = high - open for a red candle); it must close below recent support (compulsory). p.14 card adds an undefined "higher price rejection candle also works".
- Stop 35 or 40 by the distance of the most recent green candle (35 if within/below 35, 40 if above; p.2, 10, 14); target 60 from entry for all methods; never widen the stop. Worked examples p.6 (IRH 100: 103 then 99) and p.10 (entry 24,123.50, SL 24,158.50, T 24,063.50). Missing: numeric support/resistance, "small", expiry, trades/day, time window, EOD.

**ORB (long and short; pp.1-12).** Decision at 09:20 after the first candle closes; never pre-empt the close. SL 30 / target 60 (RR 1:2) for every setup; unit left to the user (p.11).
- Method 1: established trend (price vs 200 EMA plus structure) and the 09:20 candle breaks AND closes beyond previous-day resistance (long) / support (short), strong body, small opposite wick.
- Method 2: same but the level is an inner resistance/support inside the previous day's range with a trendline; near the EMA wait for a convincing close; major level may still be unbroken.
- Gap + 200 DMA: gap in direction, through the 200 DMA, 09:20 candle closes beyond it, strong body or suitable pin bar, reject extended/rejection-wick candles; exempt from the established-trend rule.
- Candle quality (p.10): preferred strong body, conditional pin bar, reject strong wick against the trade. Terminology conflict "200 DMA / EMA / DMA".

**PDR (long; pp.1-3).** Zone = previous day's high/reversal candle from body to upper wick. Next day must gap up; do not enter at the open; wait for price to return to the zone (wick, body, inside, or very close); then a green candle -> long. Target 70 fixed; stop 35 or 40 "depending on the situation" (no criterion).

**PDS (short; pp.1-6).** Zone = previous day's support low candle, body plus lower wick, extended forward. Gap down; price rises from below into the zone (same four interaction types). Entry: Method 1 first red candle at the zone with a good body; Method 2 red pin bar with higher-price rejection; Method 3 break of a small support when the first red candle is not satisfying. Target 70; stop 35/40 by recent green candle distance. Self-declared open items (p.5-6): good body, pin ratio, small-support size, close vs touch, M3 stand-alone, exactly 35, measurement of distance, entry timing.

**RF (direction never stated; implied long; pp.1-8).** Opposite of IRF. Established uptrend (200 EMA basic filter, never sole proof), gap up that stays within yesterday's range (gap down or gap beyond yesterday's high rejects; sudden large gap after a downtrend rejects), first 5-minute candle wicks included, then in order: a proper CLOSE below RF Low, then price returns inside the range. Stop 35-40 (partial), entry price OPEN, target OPEN. p.9 chart boxes show target 60.80 / stop 40.65 on the example (evidence, not a rule).

**Performance report.** 6 lots = 390 qty (65/lot); Leg 1 (195) exits at T1 = 27 points; Leg 2 at T2 = "60 or 70 points, as recorded"; after T1 the Leg-2 stop = entry; SL = full 390. P&L = points x qty, costs excluded; no per-strategy T2 rule is stated. I verified from the monthly strategy table that PDR winners were 5x T2=70 and 1x T2=60 and PDS winners 1x70 + 2x60 (unique decompositions: 87 pts x 195 = Rs 16,965 vs 97 x 195 = 18,915), all 74 IRF/ORB/RF winners 60; the RF 8 stop-losses (Rs 103,350 = 33.1 pts avg) cannot all be 35-40; ORB SLs are all exactly 30 (Rs 11,700 each). The registry's claim "report gives no per-strategy T2 rule" is true of the text; its derived mix is correct.

**Chart legends.** PDR pp.3-4 headers read "NIFTY50-INDEX . 5 . NSE" and "EMA 200 close 0" (value 24,582.02 on p.3; "...MA 200 close 0 24,925.18" on p.4, left letter cropped). The ORB p.7/13 and RF/IRF charts show one smooth curved line on a 5-minute chart.

---------------------------------------------------------------------------------------------------

## 2. Things I checked and found correct

1. **200 EMA vs 200 DMA (task item g): the code's EMA(200) on 5-minute closes is justified and reproduces the author's chart.** PDR p.4 Example 3 legend value 24,925.18 at the bar with O 25,131.60 / L 25,131.60 / C 25,146 (2025-10-07 09:40). The code's `ema200_5m` for that candle is 24,925.1768 (O and L equal, C 25,146.05, H differs by 0.35: 25,147.80 vs 25,148.15). A 200-day SMA cannot be reproduced from this data (only 25 prior sessions exist at that date). Daily-MA modes are correctly NaN until 200 prior daily bars (47 sessions evaluable).
2. 5-minute candle indexing: start-of-minute labels, rows 09:15..09:19 form the 09:15 candle usable at 09:20; 15:30 stub excluded; candle needs exactly 5 rows (missing minute drops the candle); real-data check confirmed (O/H/L/C of first candle = rows 09:15..09:19).
3. Pivot confirmation is correctly strictly-before (`pivot_lows/highs`, j <= i-1-k); mutants D3/D4 (confirm one candle early = look-ahead) are killed; random-walk prefix-invariance test (40 seeds x 75 prefixes x 5 strategies) plus real-data sample passes. I could not find any look-ahead in indicators, previous-day values (`PreviousSession`), daily MAs (index k-1 by inspection), gap computation or `on_candle` (history clipped to `current_time`, emits only on the 5th minute).
4. Entry timing: IRF/PDR/PDS/RF at the trigger candle's close (bar_end); ORB at 09:20. `signal_timestamp = c.end` (mutant X6 killed). A signal is never a fill (`reference_price_is_fill=False`).
5. IRF worked examples p.6 and p.10 reproduce exactly (entry 99; 24,123.50 / SL 24,158.50 / T 24,063.50; share 15/23). Close-vs-wick comparisons are strict where the guides say "above/below" (IRH, support, resistance, RF Low, ORB level, ORB MA close), tests exist for IRH equality on the breakout side.
6. ORB: previous-day level broken and closed beyond, candle quality, trend, gap-through-MA, cap, M2 research variant clearly labelled RESEARCH_VARIANT; trend and gap evaluated at candle 0 with causal EMA.
7. PDR/PDS first-red-candle-at-zone scoping, Method 1/2 mutual exclusivity (guarded in `ProposalConfig.__post_init__`), Method 3 only after a weak red candle by default.
8. RF sequence strictly ordered (close below, then later close inside), gap-down and gap-above-yesterday's-high rejected, direction flagged `RF_DIRECTION_IMPLIED_NOT_STATED`, target/stop/entry UNRESOLVED and not silently filled (test exists and I confirmed no 60/70 leaks into `reference_levels`).
9. Registry: every citation substantively right (only m-5 above); no VERIFIED_EXPLICIT rule found that the source does not explicitly state; PROPOSED rules carry `PR`; qualitative thresholds live only in `params.py`.
10. Performance report arithmetic (net, PF, win rate, BE share, drawdown, 5,265 BE, 17,111 avg target, SL by strategy) re-derived by me; the journal-vs-report disagreements the Phase 2 report lists are real (journal 190 rows vs Summary 189, IRF 73/ORB 89/PDR 8, 5 Saturday rows).
11. Exit policy: same-bar stop vs T1 resolved as STOP; T1+T2 same bar allowed only if no BE touch; stop gap fills at open; targets never better than level; NOT_EVALUABLE when parameters are unresolved; RF/PDR policies stay NOT_EVALUABLE.
12. Real data: 5 flagged sessions and the Muhurat exclusion behave as described; no duplicate timestamps; weekend 2026-02-01 session is handled as a normal prior session.

---------------------------------------------------------------------------------------------------

## 3. Surviving mutations (tests still pass) - each is a coverage defect

Harness: copy of src+tests in `scratchpad/reviewer/mut/`, single-string replace, run `tests/test_phase2_*.py -x`. Raw results: `scratchpad/reviewer/mut_results.txt`, `mut_results2.txt`; mutant lists `muts.json`, `muts2.json`.

Genuine survivors (should be killed):
- IRF: `x.c` lower boundary `irl <= x.c` -> `irl < x.c` (close exactly at IRL); attempt start `c.c > irh` -> `>=`; M2A `c.c < support` -> `<=`; M2B `c.c < resistance` -> `<=`; M2B own-candle push (`range(j+1, i+1)` -> `range(j+1, i)`); M2B no red-candle requirement; M3 `c.h > irh` -> `>=`; M3 `c.c < support` -> `<=`; extension `c.h > cs[b].h` -> `>=`; `m2_red_may_be_extension_candle` default branch (first_ok); compression `x.l >= irl and x.h <= irh` -> strict; compression window start `s-n < 1` -> `< 0`; pivot ties (`<=` -> `<`); most-recent green candle excluding/including the signal candle (X9, X10: stop reference).
- Selection: `recent_resistance` FIRST_PUSH_TOP vs LATEST swing high swapped (D18) - the registry's default is untested; zone tie-break FIRST/LAST (D17).
- Trend/gap: `close >= ema` (equality); PREV_3_SESSIONS `n=3` -> 2; gap `>=`/`<=` for zero gap partly covered; `ORB crossed` uses `prev_close < ma_prev` -> `<= / ma` (O3, X5); gap `closed_beyond` `>`->`>=`; gap cap `>` -> `>=`; M2 near-band `<=`/`<`; M2 margin `<`/`<=`; `rejected` ignores `not bullish_pin`; `pcs[j].h < prev.high` -> `<=`; strong-candle body ratio `>=` -> `>`.
- PDR/PDS: touch `<=` -> `<`; `i > j` -> `i >= j`; open-clear `>` -> `>=`; PDR gap condition `!= "UP"` -> `== "DOWN"` (flat open not tested for PDR/RF); PDS touch `>=`; PDS M3 `close < support` -> `<=`; PDS `at_zone` upper bound removed (X26 +100 points); PDS Method 2 `c.h >= zone.low` removed; small-support ceiling removed; PDR first-interaction candle 0 skipped (X27).
- RF: close-below `<` -> `<=`; return-inside lower/upper `<=` -> `<`; yesterday's range boundaries `<=` -> `<`; gap direction `!= UP` -> `== DOWN`.
- Exit: `hit_adverse` and `hit_high` `<=` -> `<` (exact touch of stop/target); `select_stop_distance` signed (X8).
- Session builder (largest hole): `daily_sma200_prev = sma_d[k-1]` -> `sma_d[k]` (look-ahead, S-5); `prior_session_ema_above` order reversed (S-6, makes "previous session" the oldest); `previous` session = two back (X18); `PreviousSession.high/low` = min/max swapped (S-9, X22); `last_5m_close` first vs last (X23); `ema_at_last_candle` first vs last (X21); `open_price` = first CLOSE instead of first open (S-10); `daily_history_count` shifted (X24); SMA divisor wrong (X2); `above` sign inverted (X7); official close fallback wrong (X20); weekend/missing-weekday rule (S-8, X19); `signal_window_end` cutoff `<=` boundary (B3).

Equivalent or low-value survivors (ignored above): IRF11 (`lo=0` vs 1 in M3 support: pivot loop starts at k anyway), E5 reorder, E9 (leg-2 BE contributes 0), R5/R6 (lower bound of yesterday's range is implied by a gap-up above the previous close), R7 (candle 0 cannot close below its own low), S-7 official close = stub open (stub rows mostly flat), X16 (concurrent same direction: IRF is short-only), B1 (guard redundant because the engine is causal), B4 (verification logic: covered indirectly).

Mutants killed (good): comparison inversions on M1 inside/breakout, pivot confirmation, candle geometry, wick-share arithmetic and band, ORB level selection, PDR/PDS zone construction, exit stop-fill and quantity maths, 5-minute bucketing, bar_end, EMA alpha/seed, `gap_before`, signal timestamp.

---------------------------------------------------------------------------------------------------

## 4. Answers to the checklist

(a) Rules in PDFs missing from registry/code: IRF "apply one method's rules at a time" (pp.13-14); ORB conditional pin bar for M1/M2 (pp.9-10) not applied and not listed; IRF M2 steps 3-4 of confirmation B (pullback, separate red candle) weakened (m-1). Everything else I read is present.
(b) Unsupported or mislabelled: none presented as VERIFIED_EXPLICIT that is not; thresholds all `PROPOSED_FOR_REVIEW` in params.py. Overstated: Method 1 `VERIFIED` status on 349 uncapped signals (M-3), "most literal reading" wording (m-7). Page cites: m-5 only.
(c) Off-by-one: none found; pivot confirmation `j <= i-1-k` correct; M1 `b = i-k` with `inside` strict at IRH correct.
(d) Look-ahead: none found. Test coverage of the context builder is missing (M-2).
(e) Comparisons: match each document (close for confirmation, strict above/below). Equality boundaries mostly untested (M-2).
(f) Timing: correct per document / documented proposals.
(g) EMA vs DMA: EMA(200, 5m) justified and numerically matches the author's chart (section 2.1).
(h) Stops/targets: ORB 30/60, IRF 60 + 35/40, PDR/PDS 70 + 35/40, RF 35-40 with target open, T1 27 - all match the sources; report gives no per-strategy T2 rule (true); derived T2 mix verified; RF stop < 35 and PDR/PDS 60-point winners are real conflicts and are recorded.
(i) Overlap/state machine: M1 vs M2 handled for the same breakout candle but a different breakout candle yields concurrent M1+M2A (M-3); PDS M3 vs M1/2 ordering correct (weak first red -> M3 only).
(j) Missing boundary tests: section 3.
(k) Vacuous or weak tests: `test_verified_explicit...` (duplicate), page-count test (cannot detect wrong pages), `test_rf_wrong_order...` passes on empty output, `test_m2b_page10...` passes under any stop-distance measure, real-data tests assert invariants only, `on_candle` future-row test cannot detect removal of the guard.
(l) exit_policy: M-1 (BE gap fill is favourable); same-bar ambiguity resolved adversely (OK); I-1.
(m) Data layer: C-1 (stale tail), m-6 (Muhurat/03-10 previous-close ambiguity), extended records on 03-10/08-03/08-04 are clipped and flagged correctly but 08-03/04 are symptoms of the freeze; gap definition (open vs previous 15:30 stub close) is consistent, no look-ahead.

Scratch artifacts: `/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/b71999ee-8aa6-4788-b61f-c9da5ef602df/scratchpad/reviewer/` (probe1-3.py, muts*.json, mut_results*.txt, extracted PDF text, rendered PNGs).
