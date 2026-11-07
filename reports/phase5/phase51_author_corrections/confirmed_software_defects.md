# Confirmed software defects (Phase 5.1)

**Result: none.** No handwritten observation shows the engine contradicting an explicit, approved rule. Category A (a failing test, a minimal code correction, a record of changed signals) is therefore empty, and **no frozen file was edited**.

What was checked:

* Every one of the 39 active dated entries was matched to a Phase 3.6 ledger trade (the author's labels equal the Phase 3.6 strategies for 38 labelled entries independently of any date reading; AC27 has no label; AC38 matches only after its date is resolved to 2025-12-26 (also supported by the manual journal, which has a PDS row at 09:30 on that date and none on 2025-12-16)). For all dated trades the delivered rule-check tables show 0 failed checks and 0 recomputation mismatches; the independent audit re-walked their entries and exits from the raw minutes.
* Controller selection: for the 19 observations that say 'X should have activated instead of Y', `strategy_selection_conflicts.csv` lists the expected strategy's own signals and rejections: in 16 of 19 the expected strategy never produced a confirmed signal, and in the other 3 its first confirmed signal came no earlier than the executed one (AC17, AC21, AC22), so the controller skipped nothing (**no WRONG_STRATEGY_SELECTION**: 19 of 19 verdicts are CONTROLLER_CORRECT). The disagreement lies in that engine's own conditions (thresholds and definitions that are proposals), not in the first-valid-signal rule, which is preserved.
* The three places where the author's wording points at the engine's behaviour and the engine could be called wrong were each traced to an explicit source or approved rule: RF-004 (gap-up open above yesterday's high is rejected: AC05, AC36), DAY-SL-001 (a second PDR/PDS trade after an initial full stop is allowed: AC22, AC30) and PDS-M-001 (a weak red candle is not taken: AC38).

Behaviour that differs from the author's reading but is **consistent with the rules as encoded** (not defects):

| observation | engine behaviour | why it is not a defect |
|---|---|---|
| AC27 ORB long on a red candle | the conditional pin-bar route admitted a bearish first candle (20251127-1-ORB; also 2026-01-05 long and 2026-04-24 short) | the source mentions 'a suitable bullish pin-bar-type candle' in the Gap setup and applies pin bars to Methods 1/2 only through 'candle quality across all three setups' plus a proposal flag; colour is not mentioned, and the page also says a pin bar's close must support the breakout - so 'not a defect' is defensible but not clear-cut. The author's clarification is recorded as a new rule (`new_author_rules.md`) |
| AC10 / AC11 / AC29 / AC40 PDR later than the first green candle | the confirmation needs 'good green body / lower rejection / hammer' by the PROPOSED thresholds | PDR-A04 is the author's sentence; its numbers (body >= 60%, upper wick <= 20%, hammer 2x) are proposals |
| AC13 / AC18 IRF with the EMA close below the entry | entered | no IRF rule mentions the 200 EMA; the author's rule is new |
| AC19 / AC32 / G02 entries at the day's low | no test exists | the author's rule is new; 0 executed Phase 3.6 IRF trades close below the session low so far |

Limits: signal DETECTION for the dated days was checked against the encoded rules and the author's wording; the engines' conformance to the guides in general was audited in Phases 3.3-3.6 and is not re-derived here.
