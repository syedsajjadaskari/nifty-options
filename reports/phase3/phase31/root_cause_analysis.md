# Phase 3.1 - root-cause analysis (ranked by frequency, not profitability)

Method: every discrepancy gets a primary cause from its **rejection chain** (raw engine record -> controller decision) and, for trades with no engine record at all, from a base-condition probe. The mapping is a heuristic (`research/phase31.py::root_cause_manual`); `UNKNOWN` means the evidence does not decide. Strategy-level causes for the extras are dependencies of the signal on a proposal or an unresolved rule, **not** proof that a given trade differs from the journal for that reason. Nothing is attributed to 'discretion' without naming the mechanical decision that differs.

## 1. Manual trades the automated ledger does not contain (106)

| root_cause_primary | IRF | ORB | PDR | PDS | RF | TOTAL |
|---|---|---|---|---|---|---|
| SOURCE_AMBIGUITY | 0 | 21 | 0 | 0 | 8 | 29 |
| PORTFOLIO_COMPETITION | 19 | 0 | 0 | 0 | 4 | 23 |
| PROPOSED_NUMERICAL_THRESHOLD | 0 | 18 | 0 | 0 | 0 | 18 |
| TREND_FILTER | 0 | 10 | 0 | 0 | 2 | 12 |
| UNKNOWN | 10 | 0 | 0 | 2 | 0 | 12 |
| JOURNAL_INCONSISTENCY | 1 | 4 | 0 | 0 | 0 | 5 |
| ZONE_SELECTION | 0 | 0 | 4 | 0 | 0 | 4 |
| TIME_ALIGNMENT | 3 | 0 | 0 | 0 | 0 | 3 |

| rank | cause | what it means here | implementation correction justified? | owner approval needed? |
|---|---|---|---|---|
| 1 | SOURCE_AMBIGUITY | the guide gives no objective construction: ORB 'previous-day resistance/support' (the real charts show hand-drawn multi-session boxes), ORB Method 2 inner level/trendline, RF 'within yesterday's range' and the gap definition, IRF repeats | No (nothing to correct) | Yes |
| 2 | PORTFOLIO_COMPETITION | an earlier automated trade (IRF, PDR, ORB or PDS) was active, or the day was finished/restricted, or a same-minute collision, when the manual signal appeared | No (approved policy) | Only for the collision tie-break |
| 3 | TREND_FILTER | the baseline EMA-only trend (previous session's close vs its EMA) failed on the manual ORB/RF day (`TREND:` rejections only; ORB Method 2 trendline rejections are counted under SOURCE_AMBIGUITY) | No | Yes (which trend definition) |
| 4 | PROPOSED_NUMERICAL_THRESHOLD | strong-body (>=60%, opposite wick <=20%) / pin-bar proposals rejected the first candle | No | Yes |
| 5 | JOURNAL_INCONSISTENCY | 5 Saturday-dated rows (no session exists) | n/a | Corrected trade list |
| 6 | UNKNOWN / ZONE / TIME / SEQUENCE | residual cases listed in `missing_manual_trades.csv` | See rows | See rows |

### 1a. ORB (89 journal rows; 36 matched)

* Of the 53 unmatched, **38 have a setup record that failed a filter** and **11 have no setup at all** (the first 5-minute candle did not close beyond the previous session's high or low); 4 are Saturday rows.
* Among the 38: Method 1 failed candle quality in 12 and the trend filter in 7; the others are Method 2 (trendline) or the gap setup.
* Funnel over all sessions: first candle closes beyond yesterday's extreme in 109 of 247 sessions, but only 41 days produce a trade. The independent source audit found that **candle quality is the largest ORB reducer** (72 of 108 level-break candles fail the proposed shape test), the trend filter second, and that **no reading that keeps the code's level and candle definitions reaches the journal's 89** (loosest tried: 51 days).
* None of ORB's missing trades is explained by another strategy: the matrix shows no strategy ever blocked ORB (ORB fires at 09:20, before any other strategy can).
* The five real ORB charts show hand-drawn multi-session boxes, not provably yesterday's high/low; the most plausible manual method is 'Method 1 generalised to any visible horizontal level with the 200 MA nearby' - a judgement from the figures only.

### 1b. IRF (73 journal rows; 40 matched)

* 19 unmatched are **portfolio-rejected**: an earlier automated trade consumed the opportunity (blockers in `strategy_interference_manual_trades.csv`: PDR 7, IRF 5 (an earlier automated IRF signal), ORB 3, PDS 3, collision 1).
* The manual IRF trade is usually the **first** raw IRF signal of the session: for 54 of 69 manual IRF rows whose session has an IRF signal, the nearest raw signal is the 1st of the day; 43 are on the same candle. The median session with a manual IRF trade has 5 raw IRF signals (up to 13): the guide has no cap, window or re-arming rule (`IRF-GLOBAL-004`), so the engine reports every repeat.
* IRF unmatched by class: 19 SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER, 13 MISSING_AUTOMATED_SIGNAL, 1 MANUAL_JOURNAL_CONFLICT. 10 of the 'missing' rows do have a confirmed IRF signal that day, but more than 15 minutes from the label (nearest delta in `missing_manual_trades.csv`); 8 have a setup that was still pending at the end of the session (end-of-day information, not an explanation of the earlier decision).

### 1c. RF (17 journal rows; 3 matched)

* **7 of 14 unmatched rows fail 'gap-up open inside yesterday's range'** by 2.8 to 24.7 points (`rf_gap_range_check.csv`). Under the vendor's published daily open (not used: owner chose the first 1-minute open) 2 of the 7 would be inside the range; 5 would still be outside by 6 to 24 points. The remaining unmatched rows: trend (2), a collision (2 with PDR), one blocked while another position was active, one second-trade restriction, one gap not up.
* The guide gives no number for 'within yesterday's range' and does not say whether the range includes wicks or which open; the probe shows this single condition is the largest RF reducer.

### 1d. PDR (8 journal rows; 4 matched) and PDS (3 rows; 1 matched)

* PDR: 2025-10-07 (chart 3) is rejected because the open (25,087.55) is inside the engine's zone (the 14:50 spike candle); 2026-05-19 is rejected the same way (open inside the zone); 2025-12-31 and 2026-06-12 are 'zone never intersected' (38 sessions in the year have a gap up but no candle ever intersects the reversal-swing zone). These four are `ZONE_SELECTION` cases: which previous-day candle marks the zone.
* PDS unmatched by class: 2 MISSING_AUTOMATED_SIGNAL (details in `missing_manual_trades.csv`; a setup still pending at the end of the session is not treated as an explanation).

## 2. Automated trades the journal does not contain (129)

| root_cause_primary | IRF | ORB | PDR | PDS | RF | TOTAL |
|---|---|---|---|---|---|---|
| ZONE_SELECTION | 0 | 0 | 49 | 0 | 0 | 49 |
| PROPOSED_NUMERICAL_THRESHOLD | 27 | 0 | 0 | 10 | 0 | 37 |
| SOURCE_AMBIGUITY | 35 | 1 | 0 | 0 | 0 | 36 |
| TREND_FILTER | 0 | 5 | 0 | 0 | 2 | 7 |

Same-day context (see §B of the summary): 76 are on days when the journal shows only OTHER strategies, 39 on days with no manual trade at all, 14 on days with the same strategy at another time.

### 2a. PDR (49 extras; 4 matched; manual 8)

The independent source audit's funnel (signal counts only): **140 of 246 sessions gap up; a zone is found on all 140** (the reversal screen never rejects); the open is above the zone on 99; the zone is intersected on 61; and then the **next green candle always converts** (61 of 61) with no time limit, no position test and no check that the zone held. With the per-session cap lifted the engine reports 383 raw PDR signals (the controller takes 54 entries). Mechanically the engine is **looser than every PDR chart on three points**: (i) the zone is the latest swing high with a red candle - the day's high on only 31 of 140 gap-up sessions; (ii) any later green candle counts (26 of 61 first entries close below the zone floor); (iii) the 'clear high and reversal' checklist item is not applied (switching the existing 25%-depth filter on cuts 61 to 23). The primary cause of an extra PDR trade is therefore `ZONE_SELECTION` (and the unapproved 'any green candle' reading); no correction is justified because both are interpretation choices, not contradictions of explicit wording. PDR extras also displace manual trades: PDR was the blocker of 7 manual IRF and 2 manual RF trades.

### 2b. IRF (62 extras; manual 73)

No time-of-day effect: no extra IRF entry is later than the journal's latest IRF label (12:20). 34 extras are on days when the journal traded only another strategy and 16 on days with no journal trade, 12 on days with an IRF trade at another time. The mechanical differences are the missing selection rule among repeated setups (`SOURCE_AMBIGUITY`) and the proposed support/resistance definitions behind Methods 2A/2B (`PROPOSED_NUMERICAL_THRESHOLD`).

### 2c. PDS (10 extras), ORB (6), RF (2)

PDS extras come mostly from Method 3 (4) and Method 1 (5); the independent audit found that Method 3's 'small support near the zone' has **no lower bound in code** (supports up to 118 points below the zone are accepted) - a gap relative to the source wording, left uncorrected pending the owner's definition of 'near' (`confirmed_software_defects.md`). ORB extras (6) and RF extras (2) are mostly on days when the journal shows another strategy.

## 3. Remaining causes

* **TIME_ALIGNMENT:** 3 IRF rows on sessions where no 5-minute candle closes above the initial-range high before 13:00 although the journal records an IRF entry (the journal label may refer to a different range/candle). Row 83 (2026-02-03) is weaker than its label suggests: the first 1-minute bar of that session spans about 490 points after a gap, so the initial range is inflated and 'no close above IRH' may be an opening-print artefact rather than a time issue. **UNKNOWN (12):** rows whose evidence does not decide - setups still pending at the end of the session, details no heuristic maps (flagged `UNMAPPED_ENTRY_RULE_DETAIL` in `root_cause_secondary`), and PDR/PDS rows with a gap and a zone but no setup - listed in `missing_manual_trades.csv` with their probes.
* **DATA_DIFFERENCE:** the first-minute-open convention (owner-approved) changes the gap on 2 RF days (above) and, per Phase 2.2, the gap direction on 10 sessions and the first-candle colour on 13; no row of the journal is classified DATA_DIFFERENCE because no matching failure was traced to it alone.
* **SOFTWARE_BUG:** none confirmed in the entry or selection logic (see `confirmed_software_defects.md`).

## 4. What the evidence supports

1. One of the largest levers on the trade-count mismatch, under the heuristic mapping above, is **how the guides' qualitative filters were turned into numbers** (ORB candle quality and trend, the PDR zone and 'any green candle', IRF repeat setups, the RF range test). The ranking depends on the heuristic and on which rows it leaves as SOURCE_AMBIGUITY or UNKNOWN; it is not a measured effect of each rule.
2. **Portfolio competition** accounts for 23 of the 106 missed manual trades: 8 met a position that was still open and 12 met a day already finished (or restricted to a PDR/PDS second trade) by an earlier automated trade that had exited before the manual fill, plus 3 same-minute collisions. The blocking trade is most often an extra PDR or IRF trade, but it is the approved one-trade-per-day / first-signal rule that turns it into a missed manual trade.
3. **Timing is a small effect compared with selection** (67 exact candle matches, 17 within the labelled 15-minute tolerance; no manual entry after 13:00). 12 unmatched rows do have a confirmed same-strategy signal more than 15 minutes from the label, so a wider tolerance would convert some of them; the tolerance is a labelled choice.
4. **Journal inconsistencies** account for 5 rows (Saturdays) plus one non-conforming second trade (2026-05-19) and a further 13 rows in attribution-conflict cells.

## 5. Limits

* Single baseline configuration for the chain; scenarios B and C only change the sensitivity columns. The heuristics assign ONE primary cause; secondary causes are in `root_cause_secondary`.
* The journal has no entry price, direction (except by strategy) or stop, so PRICE_DIFFERENCE, direction and stop conformity cannot be tested.
* The nearest-signal tolerance (15 minutes) is a labelled choice; a different tolerance would move a few rows between TIME_SHIFTED_MATCH and the rejection classes.
