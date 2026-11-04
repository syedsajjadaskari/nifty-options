# Phase 3.2 - explainable backtest, trade journals and daily verification (summary)

**Written for:** the strategy owner, who will check trades one day at a time. Nothing in this phase changes a rule, a parameter, a stop, a target, the cutoff or the selection controller, and nothing was tuned toward profit or toward the manual journal. The P&L is **synthetic NIFTY 50 index-point P&L x quantity** (the index is not tradable); the illustrative net applies Rs 500 per trade and 0.5 index point adverse on every fill (the Phase 3.0 headline assumption).

## 1. Prior figures re-verified from the repository artifacts

| figure quoted for Phase 3.1 | verified now | how |
|---|---|---|
| 213 automated entries | 213 | baseline re-run through the Phase 3.0 code path; every ledger field identical to the frozen `reports/phase3/baseline/trades.csv` (0 differences) |
| Rs 1,72,146 gross synthetic P&L | Rs 172,146 | sum of the 213 trades; also reproduced by an independent walk of the raw 1-minute bars |
| 190 manual journal rows | 190 | the workbook (the performance report prints 189; 5 rows are Saturday-dated) |
| 84 matches (67 exact + 17 within 15 minutes) | 84 (67 + 17) | Phase 3.1 matching rules unchanged; classifications equal Phase 3.1's |
| 129 extra automated trades | 129 | 213 - 84 |
| 106 unmatched manual trades | 106 | 190 - 84 |
| 413 passing tests after Phase 3.1 | 413 passed at the start of this phase | full suite, run again before any Phase 3.2 code was added (the current total is in `independent_audit.md`) |

## 2. Headline results (baseline, unchanged)

| item | value |
|---|---|
| Evaluable sessions | 247 |
| Executed trades (first / second) | 213 (197 / 16) |
| Days with a trade / no-trade days | 197 / 50 |
| Gross P&L (Rs) | 172,146 |
| Illustrative net P&L (Rs) | -17,424 |
| Win rate (trades with gross P&L > 0; this counts T1-then-post-T1-stop trades, which net a small gain, as wins) | 59.15% |
| Profit factor / max drawdown (gross, from the Phase 3.0 summary) | 1.15 / Rs 208,241 |
| Outcomes | INITIAL_FULL_STOP 87, T1_THEN_BUFFER_STOP 65, TARGET 61 |
| Same-minute execution ambiguities / provisional forced exits / unresolved exits | 0 / 0 / 0 |

### By strategy and method

| strategy | trades | wins | gross Rs | illustrative net Rs | methods |
|---|---|---|---|---|---|
| IRF | 102 | 55 | -56,062 | -146,842 | Method 1 62, Method 2A 16, Method 2B 24 |
| ORB | 41 | 27 | 138,470 | 101,980 | Gap/200DMA 10, Method 1 27, Method 2 4 |
| PDR | 54 | 34 | 29,074 | -18,986 | PDR 54 |
| PDS | 11 | 8 | 80,554 | 70,764 | Method 1 6, Method 2 1, Method 3 4 |
| RF | 5 | 2 | -19,890 | -24,340 | RF 5 |

### By month (gross Rs)

| month | 2025-09 | 2025-10 | 2025-11 | 2025-12 | 2026-01 | 2026-02 | 2026-03 | 2026-04 | 2026-05 | 2026-06 | 2026-07 | 2026-08 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gross | 6,737 | 16,770 | 22,669 | 106,070 | -48,360 | -7,215 | 31,220 | -68,835 | -29,640 | 17,745 | 103,145 | 21,840 |

No ranking of strategies or variants by these figures was made or used for any decision.

## 3. How completely the trades are explained

| measure | value |
|---|---|
| Trades with an entry explanation, a selection explanation and an exit explanation for both legs | 213 of 213 |
| Entry conditions recorded (each with rule id, calculation, observed values, requirement, result, status, availability time, reason) | 4769 |
| ... PASS / FAIL / UNRESOLVED / NOT_APPLICABLE | 3816 / 0 / 621 / 332 |
| Trades with a FAILED check or a recomputation mismatch against the engine's own record | 0 |
| Trades whose exit could not be reproduced from the raw bars | 0 |
| Trades that carry at least one OPEN SOURCE-RULE issue (disclosed, not a gap in the evidence) | 206 |
| Trades whose signal is verification-status PROPOSAL_DEPENDENT / RESEARCH_VARIANT | 199 / 14 (none is VERIFIED) |

**Evidence versus open rules.** 'Unresolved evidence' (a number that cannot be reproduced) is **zero**: every price traces to a raw 1-minute bar and every candle number to the raw data. What stays open are rules the sources leave undefined - they are listed in every trade and counted here:

| unresolved rule id | trades |
|---|---|
| IRF-GLOBAL-004 | 102 |
| PDR-009 | 54 |
| PDR-010 | 54 |
| PDR-007 | 54 |
| ORB-MA-001 | 41 |
| IRF-M2-006 | 40 |
| ORB-GAP-SHORT-004 | 6 |
| RF-010 | 5 |
| RF-012 | 5 |
| RF-009 | 5 |
| RF-011 | 5 |
| PDS-MISSING-001 | 4 |
| ORB-GAP-LONG-005 | 4 |

## 4. Journal agreement (Phase 3.1 matching rules, untouched)

| class | manual rows |
|---|---|
| EXACT_MATCH | 67 |
| MANUAL_JOURNAL_CONFLICT | 5 |
| MISSING_AUTOMATED_SIGNAL | 28 |
| SIGNAL_REJECTED_BY_ENTRY_RULE | 50 |
| SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER | 23 |
| TIME_SHIFTED_MATCH | 17 |

Extra automated trades: 129. Every unmatched row carries the concrete reason from the Phase 3.1 rejection chain; where the evidence does not decide, the cause is stated as **UNKNOWN** (12 rows). The journal records no entry or exit price, so only date, strategy, candle start and outcome class can be compared; P&L is never used to match.

## 5. Things the explanations make visible (for the owner's judgement - none was changed)

* **PDR zone hold:** the engine accepts the next green candle after a zone touch without checking that the zone held. In 27 of the 54 PDR entries the confirmation candle closed below the zone floor (`PDR_ZONE_DID_NOT_HOLD_BUT_ENTERED` in `manual_verification_issues.csv`).
* **PDS Method 3:** 3 of the 4 Method 3 entries used a 'small support' more than 10 points below the zone floor; the guide defines no 'near' distance.
* **IRF repeats:** every IRF trade is the day's first executable signal, but the engine re-arms on every later breakout and the guide is silent on re-arming (IRF-GLOBAL-004): 98 of the 102 IRF trades were followed by further IRF signals the same day (427 in total, each logged as ignored or rejected and visible in that day's journal).
* **PDR zone provenance:** in 41 of the 54 PDR trades the engine's zone (the owner-approved research candidate 'latest confirmed swing high with a red follower') is **not** the previous day's high (the guide says 'previous day's high/reversal'); in 23 of 54 the interaction candle closed below the zone floor (price traded through the zone, not a hold) and in 27 the confirmation close was also below it. The registry also records that the dated PDR Example 3 (2025-10-07) is not reproduced: the author drew a zone about 4-5 points tall, the engine's is 38.6 points. The audit's 'zone equals an independent construction' check validates the engine's research definition, not the author's drawn zone.
* **ORB candle route:** 11 ORB trades failed the strong-body test and were admitted through the conditional pin-bar alternative (3 of them on a candle of the opposite colour; the pin route accepts either colour because the level break carries the direction); each trade's setup text says so.
* **Engine readings that differ from the guide's wording:** 7 IRF Method 2B trades accept the push above resistance and the red close on the same candle (the guide's figure shows three candles); all 16 IRF Method 2A trades require the break candle to follow the red candle (stricter than the text). Check rows carry a `source_fidelity` column for these.
* **Trend filter:** 36 trades (ORB Methods 1/2 and RF) rest on the previous session's last 5-minute close versus its EMA(200) alone; the guides call the EMA a basic filter that is never the sole proof of a trend.
* **35 versus 40 stop:** the guide's own selection rule (35 if the most recent opposite candle is within 35 points of entry, else 40) would have chosen 40 on 35 of the 102 IRF trades and 4 of the 11 PDS trades; the approved baseline uses a fixed 35 (the 40-point variant is a separate Phase 3.0 scenario). This changes losses, not entries.
* **Days lost to unresolved same-minute conflicts:** 4 (2025-09-08, 2026-02-18, 2026-06-23, 2026-07-13); the day is marked unresolved and nothing is traded (no tie-break priority is approved).
* **IRF Method 3** (sweep above the range after compression) is evaluated every day but produced no confirmed signal (37 Method 3 setups were rejected: WICK_SHARE_OUT_OF_BAND 34, SUPPORT_NOT_BROKEN 3); it is not part of any trade.
* **ORB and RF:** the level, candle-strength thresholds and trend are mechanical stand-ins for hand-drawn levels and discretionary judgement; each trade states the numbers used.
* **Second trades:** only PDR/PDS signals confirmed after the first trade's original full stop; 16 such trades.

## 6. Rules in force (unchanged)

First valid signal of IRF/ORB/PDR/PDS/RF takes the day's first trade; none while a trade is active; second trade only after an original full stop before T1 and only a newly confirmed PDR/PDS signal; at most 2 trades a day; no fill after 13:00:00 IST; 6 lots x 65 (3 + 3); stops ORB 30, IRF/PDR/PDS/RF 35; T1 27; T2 IRF 60, ORB 60, PDR 70, PDS 70 (the performance report suggests 60 - recorded as CONFLICTING), RF 60 (research proposal); after T1 the remaining legs stop at entry -6 (LONG) / +6 (SHORT), no trailing; same-minute stop/target is resolved adversely and flagged; the forced exit at the 15:14 minute open is a **provisional** implementer assumption (it was never exercised by this ledger); simultaneous different-strategy signals mark the day unresolved (no priority assigned). Full values: `configuration_snapshot.json`, worksheet *Rule Definitions*.

## 7. Limits

* Explanations are produced by recomputing every condition with the engines' own definition functions and the active configuration, and are cross-checked against the values each engine stored on its signal record; the engines were **not modified** (no tracing code was added), and the unchanged Phase 3.0 ledger proves the re-run is identical. Numeric evidence exists for the 213 executed trades; for the other signals the engine's rule-id lists, levels and state traces are exported (`all_strategy_signals.csv`, `rejected_signals.csv`).
* Previous-day levels and zones use all candles of the previous session (including the auction print on auction days) - disclosed in Phase 3.0 and unchanged. On 2025-10-23 four engines cannot be evaluated because their previous session is the unverifiable Muhurat session (that day's journal says so).
* Invalidated engine setups on days without a trade are exported with the engine's reason code and failed rule ids (`rejected_signals.csv`), without per-condition numbers: numeric evidence is produced for executed trades only.
* `rule_status` says what kind of rule a condition is in the registry; read it together with `definition_status` and `source_fidelity`: about half of the SOURCE_VERIFIED rows rest on a qualitative wording whose numbers are proposals.
* The charts and the Excel workbook are verification aids; the numerical journals are authoritative.
