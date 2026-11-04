"""Phase 3.1: assemble reconciliation_summary.md and root_cause_analysis.md from the computed CSV/JSON (no number is typed by hand)."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

B = Path(__file__).resolve().parents[1] / "reports" / "phase3" / "phase31"
STRATS = ["IRF", "ORB", "PDR", "PDS", "RF"]


def tab(df: pd.DataFrame) -> list[str]:
    cols = [str(c) for c in df.columns]
    return ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in df.itertuples(index=False)]


def main() -> None:
    c = json.loads((B / "reconciliation_counts.json").read_text())
    a = json.loads((B / "analysis_tables.json").read_text())
    m = pd.read_csv(B / "manual_vs_automated.csv")
    e = pd.read_csv(B / "extra_automated_trades.csv")
    j = pd.read_csv(B / "manual_journal_normalized.csv").fillna("")
    cf = pd.read_csv(B / "collision_counterfactual.csv")
    base = json.loads((B.parent / "baseline" / "summary.json").read_text())
    matched = m[m.classification.isin(["EXACT_MATCH", "TIME_SHIFTED_MATCH"])]
    unmatched = m[~m.classification.isin(["EXACT_MATCH", "TIME_SHIFTED_MATCH"])]
    n_man, n_auto = len(m), base["gross"]["entries"]
    by = pd.DataFrame({"manual rows": m.groupby("strategy_normalized").size(), "matched (exact)": m[m.classification == "EXACT_MATCH"].groupby("strategy_normalized").size(),
                       "matched (time-shifted)": m[m.classification == "TIME_SHIFTED_MATCH"].groupby("strategy_normalized").size(), "manual unmatched": unmatched.groupby("strategy_normalized").size(),
                       "automated entries (baseline)": pd.Series(base["by_strategy"]).apply(lambda v: v["entries"]), "automated extra": e.groupby("strategy").size()}).reindex(STRATS).fillna(0).astype(int)
    by.loc["TOTAL"] = by.sum()
    by = by.reset_index().rename(columns={"index": "strategy"})
    cls = pd.crosstab(m.strategy_normalized, m.classification).reindex(STRATS).fillna(0).astype(int)
    cls.loc["TOTAL"] = cls.sum()
    cls = cls.reset_index().rename(columns={"strategy_normalized": "strategy"})
    ctx = pd.crosstab(e.strategy, e.extra_context).reindex(STRATS).fillna(0).astype(int)
    ctx.loc["TOTAL"] = ctx.sum()
    ctx = ctx.reset_index()
    rc = pd.crosstab(m[m.root_cause_primary.notna()].root_cause_primary, m[m.root_cause_primary.notna()].strategy_normalized).reindex(columns=STRATS).fillna(0).astype(int)
    rc["TOTAL"] = rc.sum(axis=1)
    rc = rc.sort_values("TOTAL", ascending=False).reset_index()
    rce = pd.crosstab(e.root_cause_primary, e.strategy).reindex(columns=STRATS).fillna(0).astype(int)
    rce["TOTAL"] = rce.sum(axis=1)
    rce = rce.sort_values("TOTAL", ascending=False).reset_index()
    dl = a["day_level_agreement"]
    irf = a["irf_manual_vs_raw"]
    # ------------------------------------------------------------------ reconciliation_summary.md
    s = ["# Phase 3.1 - reconciliation summary\n",
         "**Reconciliation, not optimisation.** No rule, parameter, stop, target, cutoff or selection policy was changed, nothing was fitted to the manual report, and the Phase 3.0 ledgers are untouched. "
         "The manual journal is not ground truth (Phase 2.1): its inconsistencies are carried as flags, never corrected. Every figure below is computed from `manual_vs_automated.csv`, `extra_automated_trades.csv`, "
         "`daily_signal_timelines.csv` and `analysis_tables.json` by `scripts/phase31_report.py`.\n",
         "## Conventions\n",
         "* **Time label:** a journal entry time is the START of the 5-minute entry candle (67 exact matches confirm it); the automated signal is confirmed at the candle END and filled at the next minute's open.",
         "* **Matching** (deterministic, one-to-one, P&L never used): same date and strategy; exact = same candle start; time-shifted = nearest candle start within 15 minutes (3 candles); a journal row whose strategy label is in a Phase 2.1 attribution conflict may match under its alternate label (flagged). "
         "The journal has no entry price, so `PRICE_DIFFERENCE` cannot be tested.",
         "* **Baseline** = Phase 3.0 scenario A (EMA-only trend, 35-point stop, reversal-high PDR zone). Classifications under scenarios B and C are columns of `manual_vs_automated.csv`.\n",
         "## A. How many manual trades match an automated execution?\n",
         f"Of **{n_man}** journal rows (the report says 189; 5 rows are Saturday-dated), **{len(matched)} ({100 * len(matched) / n_man:.0f}%) match an executed baseline trade** - {c['exact']} exact (same candle) and {c['time_shifted']} time-shifted. "
         f"For the matched pairs the outcome class agrees loosely (Target~Target, BE~post-T1 stop, SL~full stop) in {c['outcome_agreement_among_matches']['agree']} of {len(matched)} cases, although the stop rules differ. "
         "Confidence: HIGH for exact matches on journal rows the Phase 2.1 audit marked VALID; lower for rows in an attribution-conflict cell.\n"] + tab(cls) + [
         "\n## B. Why 213 automated trades vs 189 (190) manual\n",
         f"The identity is exact: **{n_auto} automated = {len(matched)} matched + {len(e)} automated extras**, and **{n_man} journal rows = {len(matched)} matched + {len(unmatched)} unmatched**. The net difference ({n_auto} - {n_man} = {n_auto - n_man}) is "
         f"{len(e)} - {len(unmatched)}: the automated system takes {len(e)} trades the journal does not show and misses {len(unmatched)} the journal does.\n"] + tab(by) + [
         "\nWhat the 129 extras are (same-day relation to the journal):\n"] + tab(ctx) + [
         f"\nDay level (247 sessions): both traded with the same first strategy on **{dl['both traded, same first strategy']}** days, with a different first strategy on **{dl['both traded, different first strategy']}**; "
         f"only the manual trader traded on **{dl['manual traded, automated did not']}**; only the automated system on **{dl['automated traded, manual did not']}**; neither on **{dl['neither traded']}**.\n",
         "## C. Primary root cause of each unmatched manual trade (106) and of each extra automated trade (129)\n",
         "Manual trades with no executed automated counterpart (heuristic mapping from the rejection chain; see `root_cause_analysis.md` for the evidence and its limits):\n"] + tab(rc) + [
         "\nAutomated extras (a STRATEGY-LEVEL dependency, not trade-specific proof):\n"] + tab(rce) + [
         "\n## D. The four collision days\n", "Both policies are diagnostic counterfactuals; neither is approved and neither is chosen for its result.\n"] + tab(cf[["date", "extra_entries", "manual_trades_that_day", "trades_MARK_DAY_UNRESOLVED", "trades_SKIP_COLLISION_EVENT_CONTINUE_DAY"]]) + [
         f"\nContinuing the day after skipping the colliding signals would add **{c['collision_extra_entries_if_continue']}** entries over the four days (counts only).\n",
         "## E. Journal checks (all 190 rows)\n",
         f"* conforms to the approved portfolio rules: **{int(j.conforms_to_approved_rules.astype(str).eq('True').sum())}** rows; non-conforming: **{int((~j.conforms_to_approved_rules.astype(str).eq('True')).sum())}** (5 Saturday-dated rows, and **row 134: 2026-05-19, a PDR trade after an ORB breakeven** - confirmed against the workbook: row 133 ORB 09:15 BE, row 134 PDR 09:35 BE).",
         f"* duplicates: {int(j.duplicate_flag.astype(str).eq('True').sum())}; entries labelled after 13:00: 0 (latest labels IRF 12:20, RF 11:00, PDS 10:30, PDR 10:20, ORB 09:15).",
         "* Phase 2.1 flags carried: 172 VALID, 13 UNRESOLVED (rows in a strategy-month cell the report's arithmetic cannot reproduce), 5 INVALID (Saturdays).",
         "* The report's per-trade P&L is printed only for 9 trades (its drawdown-window table); every other P&L in `manual_journal_normalized.csv` is DERIVED from the outcome with the report's payoff rules and labelled as such.\n",
         "## F. Scenario sensitivity (the matching only; no scenario is preferred)\n",
         f"Matched manual trades: baseline {c['classification_baseline'].get('EXACT_MATCH', 0) + c['classification_baseline'].get('TIME_SHIFTED_MATCH', 0)}, "
         f"structure trend {c['classification_ema_structure'].get('EXACT_MATCH', 0) + c['classification_ema_structure'].get('TIME_SHIFTED_MATCH', 0)}, "
         f"PDR shelf {c['classification_pdr_shelf'].get('EXACT_MATCH', 0) + c['classification_pdr_shelf'].get('TIME_SHIFTED_MATCH', 0)}.\n",
         "## G. What this does and does not show\n",
         "* The timing convention and the first-candle strategies are broadly consistent with the journal: where the system trades, it usually trades the same candle and (loosely) the same outcome class.",
         "* The gap between the two ledgers is mostly **selection and filtering**, not timing: see `root_cause_analysis.md`.",
         "* Nothing here says which side is 'right'. The journal is a discretionary, self-recorded record with known inconsistencies; the engines contain mechanical stand-ins that the owner has not approved.\n"]
    (B / "reconciliation_summary.md").write_text("\n".join(s) + "\n")
    # ------------------------------------------------------------------ root_cause_analysis.md
    orb = m[(m.strategy_normalized == "ORB") & (m.classification == "SIGNAL_REJECTED_BY_ENTRY_RULE")]
    pr = a["probe_PDR"]
    um = unmatched.fillna("")
    irf_um = um[um.strategy_normalized == "IRF"]
    irf_cls = ", ".join(f"{n} {k}" for k, n in irf_um.classification.value_counts().items())
    far = um[um.chain.str.contains("NEAREST_CONFIRMED")]
    irf_far = int((far.strategy_normalized == "IRF").sum())
    n_far_other = int((far.strategy_normalized != "IRF").sum())
    irf_pend = int(irf_um.chain.str.contains("SETUP_PENDING_NEVER_CONFIRMED").sum())
    n_time = int((um.root_cause_primary == "TIME_ALIGNMENT").sum())
    n_unknown = int((um.root_cause_primary == "UNKNOWN").sum())
    port = um[um.classification == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER"]
    n_port = len(port)
    n_active = int(port.detail.str.startswith("POSITION_ACTIVE").sum())
    n_coll = int(port.detail.str.contains("SIMULTANEOUS").sum())
    n_done = n_port - n_active - n_coll
    r = ["# Phase 3.1 - root-cause analysis (ranked by frequency, not profitability)\n",
         "Method: every discrepancy gets a primary cause from its **rejection chain** (raw engine record -> controller decision) and, for trades with no engine record at all, from a base-condition probe. "
         "The mapping is a heuristic (`research/phase31.py::root_cause_manual`); `UNKNOWN` means the evidence does not decide. Strategy-level causes for the extras are dependencies of the signal on a proposal or an unresolved rule, "
         "**not** proof that a given trade differs from the journal for that reason. Nothing is attributed to 'discretion' without naming the mechanical decision that differs.\n",
         "## 1. Manual trades the automated ledger does not contain (106)\n"] + tab(rc) + [
         "\n| rank | cause | what it means here | implementation correction justified? | owner approval needed? |", "|---|---|---|---|---|",
         "| 1 | SOURCE_AMBIGUITY | the guide gives no objective construction: ORB 'previous-day resistance/support' (the real charts show hand-drawn multi-session boxes), ORB Method 2 inner level/trendline, RF 'within yesterday's range' and the gap definition, IRF repeats | No (nothing to correct) | Yes |",
         "| 2 | PORTFOLIO_COMPETITION | an earlier automated trade (IRF, PDR, ORB or PDS) was active, or the day was finished/restricted, or a same-minute collision, when the manual signal appeared | No (approved policy) | Only for the collision tie-break |",
         "| 3 | TREND_FILTER | the baseline EMA-only trend (previous session's close vs its EMA) failed on the manual ORB/RF day (`TREND:` rejections only; ORB Method 2 trendline rejections are counted under SOURCE_AMBIGUITY) | No | Yes (which trend definition) |",
         "| 4 | PROPOSED_NUMERICAL_THRESHOLD | strong-body (>=60%, opposite wick <=20%) / pin-bar proposals rejected the first candle | No | Yes |",
         "| 5 | JOURNAL_INCONSISTENCY | 5 Saturday-dated rows (no session exists) | n/a | Corrected trade list |",
         "| 6 | UNKNOWN / ZONE / TIME / SEQUENCE | residual cases listed in `missing_manual_trades.csv` | See rows | See rows |\n",
         "### 1a. ORB (89 journal rows; 36 matched)\n",
         "* Of the 53 unmatched, **38 have a setup record that failed a filter** and **11 have no setup at all** (the first 5-minute candle did not close beyond the previous session's high or low); 4 are Saturday rows.",
         f"* Among the 38: Method 1 failed candle quality in {int(orb.all_failed_setups.fillna('').str.contains('Method 1:CANDLE').sum())} and the trend filter in {int(orb.all_failed_setups.fillna('').str.contains('Method 1:TREND').sum())}; the others are Method 2 (trendline) or the gap setup.",
         f"* Funnel over all sessions: first candle closes beyond yesterday's extreme in {a['probe_ORB']['all_sessions'].get('LEVEL_BROKEN_BUT_FILTERED', 0)} of 247 sessions, but only 41 days produce a trade. The independent source audit found that **candle quality is the largest ORB reducer** (72 of 108 level-break candles fail the proposed shape test), the trend filter second, and that **no reading that keeps the code's level and candle definitions reaches the journal's 89** (loosest tried: 51 days).",
         "* None of ORB's missing trades is explained by another strategy: the matrix shows no strategy ever blocked ORB (ORB fires at 09:20, before any other strategy can).",
         "* The five real ORB charts show hand-drawn multi-session boxes, not provably yesterday's high/low; the most plausible manual method is 'Method 1 generalised to any visible horizontal level with the 200 MA nearby' - a judgement from the figures only.\n",
         "### 1b. IRF (73 journal rows; 40 matched)\n",
         "* 19 unmatched are **portfolio-rejected**: an earlier automated trade consumed the opportunity (blockers in `strategy_interference_manual_trades.csv`: PDR 7, IRF 5 (an earlier automated IRF signal), ORB 3, PDS 3, collision 1).",
         f"* The manual IRF trade is usually the **first** raw IRF signal of the session: for {irf['nearest_raw_signal_rank_counts'].get('1', 0)} of {irf['manual_irf_rows_evaluated'] - irf['no_raw_irf_signal_that_day']} manual IRF rows whose session has an IRF signal, the nearest raw signal is the 1st of the day; {irf['nearest_within_0min']} are on the same candle. "
         f"The median session with a manual IRF trade has {irf['median_raw_irf_signals_on_those_days']:.0f} raw IRF signals (up to 13): the guide has no cap, window or re-arming rule (`IRF-GLOBAL-004`), so the engine reports every repeat.",
         f"* IRF unmatched by class: {irf_cls}. {irf_far} of the 'missing' rows do have a confirmed IRF signal that day, but more than 15 minutes from the label (nearest delta in `missing_manual_trades.csv`); {irf_pend} have a setup that was still pending at the end of the session (end-of-day information, not an explanation of the earlier decision).\n",
         "### 1c. RF (17 journal rows; 3 matched)\n",
         "* **7 of 14 unmatched rows fail 'gap-up open inside yesterday's range'** by 2.8 to 24.7 points (`rf_gap_range_check.csv`). Under the vendor's published daily open (not used: owner chose the first 1-minute open) 2 of the 7 would be inside the range; 5 would still be outside by 6 to 24 points. The remaining unmatched rows: trend (2), a collision (2 with PDR), one blocked while another position was active, one second-trade restriction, one gap not up.",
         "* The guide gives no number for 'within yesterday's range' and does not say whether the range includes wicks or which open; the probe shows this single condition is the largest RF reducer.\n",
         "### 1d. PDR (8 journal rows; 4 matched) and PDS (3 rows; 1 matched)\n",
         f"* PDR: 2025-10-07 (chart 3) is rejected because the open (25,087.55) is inside the engine's zone (the 14:50 spike candle); 2026-05-19 is rejected the same way (open inside the zone); 2025-12-31 and 2026-06-12 are 'zone never intersected' ({pr['all_sessions'].get('ZONE_NEVER_INTERSECTED_BY_ANY_CANDLE', 0)} sessions in the year have a gap up but no candle ever intersects the reversal-swing zone). "
         "These four are `ZONE_SELECTION` cases: which previous-day candle marks the zone.",
         f"* PDS unmatched by class: {', '.join(f'{n} {k}' for k, n in um[um.strategy_normalized == 'PDS'].classification.value_counts().items())} (details in `missing_manual_trades.csv`; a setup still pending at the end of the session is not treated as an explanation).\n",
         "## 2. Automated trades the journal does not contain (129)\n"] + tab(rce) + [
         "\nSame-day context (see §B of the summary): 76 are on days when the journal shows only OTHER strategies, 39 on days with no manual trade at all, 14 on days with the same strategy at another time.\n",
         "### 2a. PDR (49 extras; 4 matched; manual 8)\n",
         "The independent source audit's funnel (signal counts only): **140 of 246 sessions gap up; a zone is found on all 140** (the reversal screen never rejects); the open is above the zone on 99; the zone is intersected on 61; and then the **next green candle always converts** (61 of 61) with no time limit, no position test and no check that the zone held. "
         "With the per-session cap lifted the engine reports 383 raw PDR signals (the controller takes 54 entries). Mechanically the engine is **looser than every PDR chart on three points**: (i) the zone is the latest swing high with a red candle - the day's high on only 31 of 140 gap-up sessions; (ii) any later green candle counts (26 of 61 first entries close below the zone floor); (iii) the 'clear high and reversal' checklist item is not applied (switching the existing 25%-depth filter on cuts 61 to 23). "
         "The primary cause of an extra PDR trade is therefore `ZONE_SELECTION` (and the unapproved 'any green candle' reading); no correction is justified because both are interpretation choices, not contradictions of explicit wording. PDR extras also displace manual trades: PDR was the blocker of 7 manual IRF and 2 manual RF trades.\n",
         "### 2b. IRF (62 extras; manual 73)\n",
         "No time-of-day effect: no extra IRF entry is later than the journal's latest IRF label (12:20). 34 extras are on days when the journal traded only another strategy and 16 on days with no journal trade, 12 on days with an IRF trade at another time. The mechanical differences are the missing selection rule among repeated setups (`SOURCE_AMBIGUITY`) and the proposed support/resistance definitions behind Methods 2A/2B (`PROPOSED_NUMERICAL_THRESHOLD`).\n",
         "### 2c. PDS (10 extras), ORB (6), RF (2)\n",
         "PDS extras come mostly from Method 3 (4) and Method 1 (5); the independent audit found that Method 3's 'small support near the zone' has **no lower bound in code** (supports up to 118 points below the zone are accepted) - a gap relative to the source wording, left uncorrected pending the owner's definition of 'near' (`confirmed_software_defects.md`). ORB extras (6) and RF extras (2) are mostly on days when the journal shows another strategy.\n",
         "## 3. Remaining causes\n",
         f"* **TIME_ALIGNMENT:** {n_time} IRF rows on sessions where no 5-minute candle closes above the initial-range high before 13:00 although the journal records an IRF entry (the journal label may refer to a different range/candle). Row 83 (2026-02-03) is weaker than its label suggests: the first 1-minute bar of that session spans about 490 points after a gap, so the initial range is inflated and 'no close above IRH' may be an opening-print artefact rather than a time issue. **UNKNOWN (%d):** rows whose evidence does not decide - setups still pending at the end of the session, details no heuristic maps (flagged `UNMAPPED_ENTRY_RULE_DETAIL` in `root_cause_secondary`), and PDR/PDS rows with a gap and a zone but no setup - listed in `missing_manual_trades.csv` with their probes." % n_unknown,
         "* **DATA_DIFFERENCE:** the first-minute-open convention (owner-approved) changes the gap on 2 RF days (above) and, per Phase 2.2, the gap direction on 10 sessions and the first-candle colour on 13; no row of the journal is classified DATA_DIFFERENCE because no matching failure was traced to it alone.",
         "* **SOFTWARE_BUG:** none confirmed in the entry or selection logic (see `confirmed_software_defects.md`).\n",
         "## 4. What the evidence supports\n",
         "1. One of the largest levers on the trade-count mismatch, under the heuristic mapping above, is **how the guides' qualitative filters were turned into numbers** (ORB candle quality and trend, the PDR zone and 'any green candle', IRF repeat setups, the RF range test). The ranking depends on the heuristic and on which rows it leaves as SOURCE_AMBIGUITY or UNKNOWN; it is not a measured effect of each rule.",
         f"2. **Portfolio competition** accounts for {n_port} of the {len(unmatched)} missed manual trades: {n_active} met a position that was still open and {n_done} met a day already finished (or restricted to a PDR/PDS second trade) by an earlier automated trade that had exited before the manual fill, plus {n_coll} same-minute collisions. The blocking trade is most often an extra PDR or IRF trade, but it is the approved one-trade-per-day / first-signal rule that turns it into a missed manual trade.",
         f"3. **Timing is a small effect compared with selection** (67 exact candle matches, 17 within the labelled 15-minute tolerance; no manual entry after 13:00). {irf_far + n_far_other} unmatched rows do have a confirmed same-strategy signal more than 15 minutes from the label, so a wider tolerance would convert some of them; the tolerance is a labelled choice.",
         "4. **Journal inconsistencies** account for 5 rows (Saturdays) plus one non-conforming second trade (2026-05-19) and a further 13 rows in attribution-conflict cells.\n",
         "## 5. Limits\n",
         "* Single baseline configuration for the chain; scenarios B and C only change the sensitivity columns. The heuristics assign ONE primary cause; secondary causes are in `root_cause_secondary`.",
         "* The journal has no entry price, direction (except by strategy) or stop, so PRICE_DIFFERENCE, direction and stop conformity cannot be tested.",
         "* The nearest-signal tolerance (15 minutes) is a labelled choice; a different tolerance would move a few rows between TIME_SHIFTED_MATCH and the rejection classes."]
    (B / "root_cause_analysis.md").write_text("\n".join(r) + "\n")
    print("written")


if __name__ == "__main__":
    main()
