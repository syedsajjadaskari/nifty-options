# Data repair report (Phase 2.1)

## Headline

**The "August 2026 critical data defect" reported in Phase 2 is not a data defect.** It is a real change in how NSE closes the market. **No candle needed repair and none was changed.** Phase 2's diagnosis (and my own, in the Phase 2 summary) was wrong; this report says why, what the evidence is, and what actually did need fixing (our handling of it, plus several genuine problems found while re-validating).

## 1. What was investigated

| Item | Detail |
|---|---|
| Dates | all 248 sessions of 2025-09-01 … 2026-08-31 (full revalidation), with the 21 sessions 2026-08-03 … 08-31 examined minute by minute; Sep and Oct 2026 (21 + 19 sessions, outside the analysis period) as diagnostics; June 2026 as a control |
| Raw vs processed | the stored Parquet was compared with a fresh read-only download of the same request (same login, endpoint, parameters) |
| Origin tested | 5paisa feed, timestamp conversion, download parsing (`clean_and_validate_raw_df` only drops invalid rows, de-duplicates and sorts: it forward-fills nothing), 5-minute aggregation, storage |
| Reference data | the vendor's own 5-minute and daily candles; 9 published closing values from independent websites |

## 2. The symptom, precisely (confirmed)

* **21 of 21** sessions from 2026-08-03 have one frozen price from **15:15** (17 sessions) or **15:16** (4) to **15:27/15:28**, then a single catch-up bar - at **15:29 in 12 sessions and at 15:28 in 9** - whose close equals the 15:30 print (21/21) with a median range of **33.2 points** (201 points on 08-03). The first one: 24,573.35 from 15:15 to 15:28, then 24,774.30.
* **0** sessions before 2026-08-03 have any frozen run. Outside the auction window the whole year contains exactly **one** zero-range regular-hours minute (in the Muhurat session).
* 2026-08-03 and 08-04 also carry 10 flat rows 15:31–15:40; 2026-03-10 carries 29 rows after 15:30 (a different, unrelated event: see §5).

## 3. Why it is real: NSE's Closing Auction Session

From **2026-08-03** continuous trading in F&O-eligible stocks (all 50 NIFTY constituents) ends at 15:15 and a Closing Auction Session follows; the index cannot move continuously during the auction and the official closing value appears when it completes. Every observation fits:

| Prediction of the auction explanation | Observed |
|---|---|
| begins exactly on the rollout date | first frozen session 2026-08-03; none before |
| frozen from 15:15 | start 15:15 / 15:16 |
| ends with a step to the official close | catch-up bar close == 15:30 print == published close (24,774.30 on 08-03; 24,614.90 on 08-04) |
| persists afterwards | Sep 2026: 21/21 sessions; Oct 2026: 19/19 sessions |
| the vendor's daily close, an official value, then equals the minute print | pre-regime the two differ (median 8 points, up to 88); from 08-03 they are identical on all 21 sessions |
| F&O hours extended to 15:40 | flat rows 15:31–15:40 on 08-03 and 08-04 |

The rollout is described by two secondary sources (Groww, Sahi) and the published closes by Oquilia/IIFL; **I did not read the NSE circular itself.** The regime start date, the pattern and the exact external close make this high-confidence, not certain.

*Alternative considered and rejected:* a vendor "recency" artefact (2026-08-03 is exactly 90 days before the download date). It cannot explain why the catch-up bar equals the real published close, why the pattern begins on a documented rollout date, or why the daily close changes behaviour on that day. A re-download after ~2026-11-30 is a cheap confirmation (expect no change).

## 4. Fresh downloads and comparisons

22 read-only requests were made, all successful (`data_provenance.md` lists each with its hash).

| Comparison | Result |
|---|---|
| stored vs fresh 1-minute, **August** (target) | 7,916 vs 7,916 rows, **0** differing rows |
| stored vs fresh, **July** and **June** (controls) | 8,648 and 7,896 rows, **0** differences each |
| vendor 5-minute candles vs our aggregation of the stored 1-minute rows, **whole year** | **18,525 of 18,525** candles identical (the only vendor candles we lack are the 15:30 prints, the 63 auction-window candles an earlier version of our code dropped, post-close rows and the Muhurat session) |
| vendor daily close vs **9 externally published closes** (2026-07-31, 08-03, 08-04, 01-27, 03-10, 03-19, 03-25, 03-30, 05-27) | **9 of 9** match to the cent; the 15:30 minute print matches only 2 |
| original Phase 1 partitions vs the unchanged archive | byte-identical (14 files) |

Caution on what the re-download proves: identical bytes show only that our pipeline did not create the pattern; they cannot tell a real market feature from a vendor-side artefact (a vendor would serve the same rows either way). **The discriminating evidence is the external closes and the documented rollout date**, not the re-download. (Independent review: the closes 24,175.65 on 08-28 and 24,080.40 on 08-31 also match.)

Two further limits from that review: (1) inside the frozen window the published index is a *stale, non-tradable* value (derivatives trade to 15:40), and the catch-up appears on the feed before the nominal 15:30-15:35 match, so those candles are real prints but **not executable prices**; (2) the quality layer accepts a frozen run inside 15:15-15:29 only if it **starts at 15:15/15:16** (a later-starting stall makes the session UNVERIFIED), and it cannot detect freezes shorter than 5 minutes anywhere.

## 5. Other findings from the full revalidation (genuine)

| Finding | Evidence | Resolution |
|---|---|---|
| The **official close ≠ the 15:30 minute print** before the auction regime | 227 sessions: median difference 8 points, up to 88 (2026-03-19: print 23,090.55 vs published 23,002.15) | previous close now comes from the vendor **daily** series (verified 9/9); gap direction differs on 9 of 247 sessions depending on the choice (`DATA-D01`) |
| 2026-03-10 "post-close records" | 15:31 prints the official close 24,261.60 and holds it; matches the published close and the vendor daily | real, clipped from candles, no longer treated as an ambiguity once the daily close is used |
| **Phase 1 holiday list wrong** | 2026-02-17, 03-20, 03-27, 05-27 have full sessions (May 27 close 23,907.15 confirmed externally); closures missed: 2026-01-15, 03-26, 03-31, 05-28 (confirmed by several sources) | evidence-tiered calendar `data/metadata/nse_calendar_2025_2026.json`; the 4 "unverified missing weekdays" are now confirmed closures |
| EMA(200) not initialised for the first 3 sessions; daily 200-day average evaluable on only 47 of 247 sessions | `phase2` audit | 2025-07/08 minute data (15,789 rows) fetched as **warm-up only**; 248 earlier official daily bars fetched; every session now has an initialised EMA and daily SMA |
| Largest non-auction ranges (up to 205 points, 2026-02-01 12:31) | all on the Union Budget Sunday | reviewed event, real, flagged |
| Phase 1 metadata contains a leaked `MagicMock` string; Phase 1's audit called the four missing weekdays "API data unavailable" | file contents | reported, **not modified** |

## 6. What changed in code (corrections to *our* handling)

| Change | Reason |
|---|---|
| Frozen rows **inside 15:15–15:29 on/after 2026-08-03 are kept and flagged**; a frozen run anywhere else marks the session `CORRUPT` and is excluded | the data is real; the safety net for genuine freezes stays |
| The 63 auction-window candles are **kept** (every session has 75 candles) | they are real prints |
| Previous close = official daily close | verified against external closes |
| `PREV_CLOSE_UNRELIABLE` for frozen tails / post-close prints removed (kept only as a fallback when no daily series exists) | it was caused by the misdiagnosis |
| Previous-day levels: new labelled proposal `prev_day_level_window` (`ALL_CANDLES` default / `CONTINUOUS_ONLY`) | the 15:25 auction candle holds the step to the close, which is not a "peak and reversal"; it matters on 5 of 21 auction sessions and changes one session's output (2026-08-26) |
| Six-value session status, machine-readable manifest, `evaluate_dataset` records every non-evaluable session | Task 3 |

**Effect of the correction on Phase 2's numbers:** sessions unevaluable by previous-day strategies fell from **27 to 1** (2025-10-23: a Muhurat session sits between); The PDR signal on 2026-08-26 that Phase 2 attributed to a "fabricated zone" uses a zone [24,260.05, 24,334.55] taken from the real 15:25 auction candle of 2026-08-25. That is the **one** session where the new `prev_day_level_window` proposal matters: under `CONTINUOUS_ONLY` the zone is [24,247.05, 24,266.85] and the signal moves from the 09:20 candle to 12:10. Across the 21 auction sessions, 5 have their day high or low inside the auction candles; the choice changes the output of exactly 1 PDR/PDS session and 3 ORB rejections, and no RF signal.

## 7. Updated session-quality counts

| Status | Sessions | Evaluable |
|---|---|---|
| VALID | 246 | 246 |
| VALID_SPECIAL_SESSION | 2 (Muhurat 2025-10-21: not a standard session; Budget Sunday 2026-02-01: normal hours) | 1 |
| PARTIAL / CORRUPT / MISSING / UNVERIFIED | 0 | 0 |
| **Total with data** | **248** | **247** |
| Confirmed non-trading weekdays | 14 (listed with evidence in the manifest) | - |
| Closing-auction-regime sessions (VALID, flagged) | 21 | 21 |

## 8. Candles corrected and periods still unsuitable

* **Candles corrected: 0.** Candles added: none to the analysis period (the new files are the daily series and *warm-up-only* minutes).
* **Unresolved periods:** none unsuitable for backtesting on data grounds. One *rule* question remains data-adjacent: **2025-10-23** is not evaluated by previous-day strategies (which close/session to use after a Muhurat day; `DATA-D04`).
* **Not done:** the NSE circulars were not read directly; vendor data for Sep–Oct 2026 was fetched only as a diagnostic and is not part of any dataset.
