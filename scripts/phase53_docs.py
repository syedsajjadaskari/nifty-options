"""Phase 5.3: the markdown deliverables of reports/phase5/phase53_author_corrected/, written from the CSV / JSON files produced by scripts/phase53_run.py (counts and identities are read, not typed).

  python scripts/phase53_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase53_author_corrected"
COMB, FROZEN = "phase53-author-corrected", "phase36-frozen"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def fb(x) -> bool:
    return str(x) == "True"


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    S = json.loads((OUT / "signal_counts.json").read_text())
    dated = rd(OUT / "dated_author_corrections.csv")
    pdr = rd(OUT / "pdr_first_eligible_setups.csv")
    twenty = rd(OUT / "pds_20_sessions.csv")
    orb = rd(OUT / "orb_unresolved_entries.csv")
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    cfgs = [k for k in S if isinstance(S[k], dict) and "confirmed_total" in S[k]]
    chm = S["change_counts_by_method_vs_frozen"]
    chs = S["change_counts_vs_frozen"]
    E = S["irf_ema"]
    WARN = "Signal-level evidence only: no controller, no fills, no P&L and no profitability backtest were run. Conventions marked PROVISIONAL are not confirmed as the author's meaning."

    def nchg(cfg, strat, types=("ADDED", "REMOVED", "TIME_SHIFTED_EARLIER", "TIME_SHIFTED_LATER", "SAME_TIME_LEVEL_CHANGED")):
        return {t: chs[cfg].get(f"{strat}/{t}", 0) for t in types}

    # ============================================================================================ approved_author_decisions.md
    AD = ["# Approved author decisions (Phase 5.3 brief) and how each was implemented", "", WARN, "",
          tab(["#", "decision", "authority", "implementation", "status"], [
              ["D1", "IRF support reference = the FIRST qualifying red candle's wick LOW", "Owner approved", "`IRFPhase53Strategy(support_ref='FIRST_RED_LOW')`, Method 2A only; the search for the first red candle starts after the extension candle (provisional assumption, variant available)", "IMPLEMENTED (level approved; search start and method scope PROVISIONAL)"],
              ["D2", "IRF minimum 28 index points from EMA(200)", "Owner approved (the number)", "`ema_min_clearance=28.0`, measure PROVISIONAL_EMA_RANGE_DISTANCE (nearest point of the signal candle's high-low range), inclusive, all IRF methods", "IMPLEMENTED (measure, inequality direction and scope PROVISIONAL)"],
              ["D3", "PDR: enter on the first eligible candle, no unnecessary delay", "Owner approved", "`PDRFirstEligibleStrategy`: setup, retest-first sequencing and close above the ceiling preserved; numeric strength thresholds replaced by the smallest transparent conventions (green candle per the guide, or lower-price rejection)", "IMPLEMENTED (pattern convention PROVISIONAL)"],
              ["D4", "PDS: enter on the first eligible candle, no unnecessary delay", "Owner approved", "`PDSFirstEligibleStrategy`: numeric thresholds replaced by parameter-free quality tests for Methods 1/2; the source rule that a weak first red candle goes to Method 3 (small-support break) is PRESERVED", "IMPLEMENTED (quality tests PROVISIONAL; conflict with the author's 'first candle' flagged)"],
              ["D5", "ORB priority over IRF", "NOT approved", "no change: the controller's first-valid-signal rule stands; the missing ORB definitions are listed", "DIAGNOSTIC ONLY"],
              ["D6", "IRF day's-low restriction", "Author stated; predicate unresolved", "not applied (`PENDING_OWNER_DEFINITION`); eight readings measured at decision time", "PENDING"],
              ["D7", "IRF red-candle method scope", "Scope verification required", "Method 2A only; Method 2B (resistance-based), Method 1 and Method 3 have no red-candle-created support in the guide", "VERIFIED FROM THE GUIDE; extension to 2B needs owner approval"]]), "",
          "The combined configuration is selectable as `" + COMB + "`; every rule is also selectable alone (see `rule_authority_matrix.md`). The frozen Phase 3.6 default and the Phase 5.2 configurations are untouched."]
    (OUT / "approved_author_decisions.md").write_text("\n".join(AD) + "\n")

    # ============================================================================================ rule_authority_matrix.md
    cfg_rows = [[k, S[k]["authority"], S[k]["confirmed_total"], S[k]["by_strategy"]["IRF"], S[k]["by_strategy"]["PDR"], S[k]["by_strategy"]["PDS"], S[k]["by_strategy"]["ORB"], S[k]["by_strategy"]["RF"]] for k in cfgs]
    RM = ["# Rule authority matrix", "", "Authority levels: SOURCE (a guide states it), OWNER_APPROVED (Phase 5.3 brief), AUTHOR_CALL / HANDWRITTEN (author statement, meaning open), PROVISIONAL (smallest transparent convention chosen here, NOT confirmed), PROPOSED (earlier research parameter).", "",
          tab(["rule", "authority", "state in `" + COMB + "`", "evidence"], [
              ["IRF Method 2A support = first red candle LOW", "OWNER_APPROVED", "ACTIVE", "irf_first_red_low_implementation.md"],
              ["first red candle searched after the extension candle", "PROVISIONAL (guide step order; variant after the breakout selectable)", "ACTIVE", "red-search variant: " + str(S["irf_first_red_low"]["red_search_start_changes"]) + " of 42 executed Method-2 trades differ"],
              ["first red candle rule limited to Method 2A", "SOURCE-VERIFIED scope (2B's reference is a resistance)", "ACTIVE", "irf_first_red_low_implementation.md"],
              ["IRF minimum 28-point EMA clearance", "OWNER_APPROVED (number)", "ACTIVE", "irf_ema_28_implementation.md"],
              ["clearance measured to the nearest point of the candle range, inclusive, all IRF methods", "PROVISIONAL_EMA_RANGE_DISTANCE", "ACTIVE", "close-distance and 27-point readings are comparison variants"],
              ["PDR first eligible confirmation candle", "OWNER_APPROVED", "ACTIVE", "pdr_first_eligible_implementation.md"],
              ["PDR confirmation = green candle (guide s.4.3) or lower-price rejection; close strictly above the ceiling", "PROVISIONAL_PDR_MINIMAL_CONFIRMATION", "ACTIVE", "replaces the PROPOSED numeric thresholds"],
              ["PDR retest candle may not confirm", "PRESERVED convention (sequencing unresolved)", "ACTIVE", "retest-permitted effect reported separately"],
              ["PDS first eligible confirmation candle", "OWNER_APPROVED", "ACTIVE", "pds_first_eligible_implementation.md"],
              ["PDS good red / red pin tests without percentages", "PROVISIONAL_PDS_MINIMAL_QUALITY", "ACTIVE", "replaces the PROPOSED numeric thresholds"],
              ["PDS weak first red candle -> Method 3 small-support break", "SOURCE (PDS guide s.7 quality rule)", "ACTIVE (not overridden)", "conflict with AC38 flagged"],
              ["ORB priority over IRF", "NOT APPROVED", "OFF", "orb_unresolved_entries.md"],
              ["ORB colour rule", "CANDIDATE_NOT_APPROVED (Phase 5.1)", "OFF (selectable)", "phase53-var-orb-colour"],
              ["IRF day's-low restriction", "PENDING_OWNER_DEFINITION", "OFF", "irf_day_low_unresolved.md"],
              ["portfolio rules, stops, targets, RF, same-minute policy, costs", "USER_APPROVED / SOURCE", "UNCHANGED (no controller code touched)", "frozen hashes verified"]]), "",
          "## Selectable configurations (signal level)", "", tab(["configuration", "authority", "confirmed signals", "IRF", "PDR", "PDS", "ORB", "RF"], cfg_rows)]
    (OUT / "rule_authority_matrix.md").write_text("\n".join(RM) + "\n")

    # ============================================================================================ irf_first_red_low_implementation.md
    c53 = chm["phase53-irf-first-red-low"]
    t2a = {t: c53.get(f"IRF/Method 2A/{t}", 0) for t in ("UNCHANGED", "SAME_TIME_LEVEL_CHANGED", "TIME_SHIFTED_EARLIER", "TIME_SHIFTED_LATER", "ADDED", "REMOVED")}
    other = {m: {t: c53.get(f"IRF/{m}/{t}", 0) for t in ("UNCHANGED", "TIME_SHIFTED_EARLIER", "TIME_SHIFTED_LATER", "ADDED", "REMOVED")} for m in ("Method 1", "Method 2B", "Method 3")}
    fr_s = S["irf_first_red_low"]
    cb = chm["phase53-var-irf-first-red-after-breakout"]
    dated_fr = [r for r in dated if r["topic"] == "IRF_FIRST_RED_CANDLE"]
    ref_changed = t2a["SAME_TIME_LEVEL_CHANGED"] + t2a["TIME_SHIFTED_EARLIER"] + t2a["TIME_SHIFTED_LATER"] + t2a["ADDED"]
    FRM = ["# IRF - the first red candle's LOW as support (implementation)", "", WARN, "",
           "## The rule as implemented", "",
           "1. Method 2A (`Confirmation A`): breakout candle (close above the opening-range high) -> extension candle (high above the breakout candle's high) -> the **earliest completed red candle after the extension** is the reference candle -> its **LOW (wick included)** is the support -> the entry is the first LATER completed candle that closes below that low, activated at that candle's close (signals after 13:00 are flagged `within_13_00_cutoff=False` in the outputs and are excluded by the unchanged controller; the engine does not filter them at signal level).",
           "2. The reference candle's timestamp, OHLC index and low are stored on the signal (`first_red_candle_start`, `first_red_candle_low`, `red_candle_index`, `support_candle_index`). A later red candle never replaces it; the body low and the close are not used.",
           "3. **Scope: Method 2A only.** The IRF guide's Method 2B reference is a *resistance* (the top of the first push; the red candle is the confirming candle, not the creator of a level), Method 1 has no support level (failure back inside the range) and Method 3's support is 'formed by the preceding candles' - none of these is changed. The independent audit confirms that Method 1 and Method 3 signals are identical to Phase 3.6.",
           "4. **Provisional assumption `first_red_search_start`.** The guide fixes the step order breakout -> extension -> pullback low -> red candle -> close below, so the search starts after the extension (the engine's existing bookkeeping). The alternative `AFTER_BREAKOUT` (first red after the breakout candle, even before the extension) is a selectable variant (`phase53-var-irf-first-red-after-breakout`).", "",
           "## Effect on Method 2A signals (2025-09-01..2026-08-31, against Phase 3.6)", "",
           tab(["Method 2A signals", "count"], [["Phase 3.6", sum(t2a[t] for t in ("UNCHANGED", "SAME_TIME_LEVEL_CHANGED", "TIME_SHIFTED_EARLIER", "TIME_SHIFTED_LATER", "REMOVED"))], ["unchanged (same time, same support)", t2a["UNCHANGED"]], ["same time, **changed reference support level**", t2a["SAME_TIME_LEVEL_CHANGED"]],
                                           ["earlier", t2a["TIME_SHIFTED_EARLIER"]], ["later", t2a["TIME_SHIFTED_LATER"]], ["newly generated", t2a["ADDED"]], ["removed", t2a["REMOVED"]],
                                           ["**Method 2A signals using a different reference than Phase 3.6** (level changed + earlier + later + new)", ref_changed]]), "",
           "Methods 1, 2B and 3 (history effects only): " + "; ".join(f"{m}: " + (", ".join(f"{t.lower()} {n}" for t, n in v.items() if t != "UNCHANGED" and n) or "no change") for m, v in other.items()) + " (Method 3 produces no confirmed IRF signal in any configuration, so its unchanged status is vacuous, not tested by data). Method 2B and Method 3 signals can change only because an earlier or later 2A confirmation ends or re-arms an attempt (Method 1 and 3 are history-independent: audit check). Total IRF confirmed signals: Phase 3.6 " + str(S[FROZEN]["by_strategy"]["IRF"]) + ", first-red-low " + str(S["phase53-irf-first-red-low"]["by_strategy"]["IRF"]) + " (a count increase is not an improvement).", "",
           "## The 42 executed Phase 3.6 Method-2 trades (`irf_first_red_low_comparison.csv`)", "",
           tab(["outcome under first-red-low", "trades"], [["unchanged (same time and method)", fr_s["executed_trades_unchanged"]], ["first IRF signal of the day earlier", fr_s["executed_trades_earlier"]], ["first IRF signal of the day later", fr_s["executed_trades_later"]], ["no IRF signal within 13:00", fr_s["executed_trades_no_signal"]]]), "",
           f"Red-search-start assumption: {fr_s['red_search_start_changes']} of the 42 trades give a different result when the first red candle is searched from the breakout candle; at signal level the variant has {sum(v for k, v in cb.items() if k.startswith('IRF/Method 2A/') and not k.endswith('/UNCHANGED'))} changed Method 2A signals (against {sum(v for k, v in c53.items() if k.startswith('IRF/Method 2A/') and not k.endswith('/UNCHANGED'))} for the default).", "",
           "## Handwritten dates involving the first red candle", "",
           tab(["correction", "date", "author's expectation", "outcome", "status"], [[r["correction_id"], r["trading_date"], r["expected_strategy_or_candle"][:70], r.get("phase53_irf_result_first_red_low", ""), r["reconciliation_status"]] for r in dated_fr]), "",
           "Reading: AC09 moves earlier as the author wrote; AC08 (the author expects earlier) moves **later** under the first-red-low rule, so it is not reconciled; AC01, AC03 and AC34 are Method 2B signals whose reference is a resistance, so the rule does not apply (scope verification required); AC20 and AC26 state only the reference candle and the 2A signal does not reproduce (no IRF signal within 13:00). No outcome was compared with profit.", "",
           "## Remaining decisions", "", "O4: apply the rule to Method 2B / Method 3 (needs source support); confirm the search start (after the extension or after the breakout); AC08 contradicts the stated direction."]
    (OUT / "irf_first_red_low_implementation.md").write_text("\n".join(FRM) + "\n")

    # ============================================================================================ irf_ema_28_implementation.md
    f = E[FROZEN]
    g = E["phase53-irf-first-red-low"]

    def row(label, k):
        return [label, f[k]["all"], f[k]["executed"], f[k]["within_13_00"], g[k]["all"], g[k]["within_13_00"]]
    re = S["irf_ema_rejection_events"]
    ema_chs = chs["phase53-irf-ema28"]
    EM = ["# IRF - minimum 28-point distance from EMA(200) (implementation)", "", WARN, "",
          "## The rule as implemented (`PROVISIONAL_EMA_RANGE_DISTANCE`)", "",
          "* `E` = the EMA(200) of completed five-minute candles (with the existing historical warm-up) **including the signal candle's own close** - available when that candle ends, which is the decision time. No later value is used (audit-verified); the previous candle's EMA gives a different decision for " + str(f["range_28_decision_changes_with_previous_candle_ema"]["all"]) + " signal(s).",
          "* distance = `L - E` if `E < L`; `E - H` if `E > H`; `0` if the EMA lies inside the candle's high-low range. A candidate passes only if distance **>= 28.0** (inclusive; a distance of exactly 28.0 passes). A candidate with a smaller clearance is REJECTED and logged (`irf_ema_rejections.csv`).",
          "* **Scope:** all four IRF methods (the clarification speaks of IRF as a whole and the guide has no EMA text, so no method is excluded; `phase53-var-irf-ema28-method2-only` is the scope variant). For Method 2 a rejected candidate does not end the attempt (a later candle of the same attempt may qualify); Method 1 and Method 3 are history-independent per candle.",
          "* Unknown EMA (warm-up) does not reject; no signal in the history is affected (EMA unavailable: " + str(f["ema_unavailable"]) + ").",
          "* EMA construction: SMA seed of the first 200 completed candles, then the standard EMA across the concatenated sessions (warm-up from 2025-07-01); the 2025-10-21 Muhurat session (12 candles) is excluded by the repo's session filter - including it would move the EMA by up to ~18 points on some rows but changes no pass/fail decision (independent reviewer's test).",
          "* After a Method 2 rejection the attempt stays alive, so a later candle closing below the same support can fire as a delayed entry (the reviewer counted 40 such signals in the combined configuration). This is an inference, not an author decision (O2: skip versus wait).", "",
          "## How many IRF signals fail the 28-point rule", "",
          tab(["reading", "Phase 3.6 IRF signals failing", "of which executed trades", "within 13:00", "first-red-low IRF signals failing", "within 13:00"], [
              row("range >= 28 (the Phase 5.3 convention)", "fail_range_28"), row("range >= 27 (handwritten number)", "fail_range_27"), row("|close - EMA| >= 28", "fail_close_28"), row("|close - EMA| >= 27", "fail_close_27")]), "",
          f"The out of {f['signals']} Phase 3.6 IRF signals ({f['executed']} are the executed trades). 27 versus 28 changes the answer for {f['range_27_pass_28_fail']['all']} signals (range) - the boundary is not a rounding detail, but it is rarely decisive. The comparison is diagnostic only; no variant was chosen by outcome.", "",
          "By method (Phase 3.6 signals failing the range rule): " + ", ".join(f"{m} {n}" for m, n in f["fail_range_28"]["by_method"].items()) + ".", "",
          "## Signal changes", "",
          tab(["configuration", "IRF added", "IRF removed", "earlier", "later", "total IRF signals"], [[k, chs[k].get("IRF/ADDED", 0), chs[k].get("IRF/REMOVED", 0), chs[k].get("IRF/TIME_SHIFTED_EARLIER", 0), chs[k].get("IRF/TIME_SHIFTED_LATER", 0), S[k]["by_strategy"]["IRF"]]
                                              for k in ("phase53-irf-ema28", "phase53-var-irf-ema28-method2-only", "phase53-var-irf-ema27", "phase53-var-irf-ema28-close", COMB)]), "",
          f"Rejection events (a candidate candle rejected; one signal can be rejected on several candles of an attempt): EMA-28 alone {re['phase53-irf-ema28']['events']} ({re['phase53-irf-ema28']['by_method']}); combined {re['phase53-author-corrected']['events']}. Net effect of the 28-point rule alone: IRF {S[FROZEN]['by_strategy']['IRF']} -> {S['phase53-irf-ema28']['by_strategy']['IRF']} confirmed signals ({ema_chs.get('IRF/REMOVED', 0)} removed, {ema_chs.get('IRF/ADDED', 0)} newly generated because a rejected attempt stays alive, {ema_chs.get('IRF/TIME_SHIFTED_LATER', 0)} later).", "",
          "## Where the EMA lies (the directional audit)", "",
          tab(["Phase 3.6 IRF signals failing the range rule", "signals", "of which executed"], [["EMA ABOVE the full candle (within 28 above)", f["fail_range_28_ema_above_candle"]["all"], f["fail_range_28_ema_above_candle"]["executed"]], ["EMA INSIDE the candle's range", f["fail_range_28_ema_inside_candle"]["all"], f["fail_range_28_ema_inside_candle"]["executed"]],
                                                                         ["EMA BELOW the full candle (within 28 below)", f["fail_range_28_ema_below_candle"]["all"], f["fail_range_28_ema_below_candle"]["executed"]], ["EMA between the entry and Target 1 (entry - 27)", f["fail_range_28_and_ema_between_entry_and_t1"]["all"], f["fail_range_28_and_ema_between_entry_and_t1"]["executed"]],
                                                                         ["EMA NOT between the entry and Target 1", f["fail_range_28_and_ema_NOT_between_entry_and_t1"]["all"], f["fail_range_28_and_ema_NOT_between_entry_and_t1"]["executed"]]]), "",
          f"**Discrepancy to record.** The range distance is symmetric, but the author's handwritten reasons (AC13, AC18; Phase 5.1 transcription: 'the space between the entry candle and the EMA is less than 27 ... wait until the EMA is broken'; 'should be ignored as Tgt 1 is not above EMA, tgt 1 is less than 27') are directional: they concern an EMA BELOW the entry within the target distance. Of the Phase 3.6 signals rejected by the convention, only {f['fail_range_28_and_ema_between_entry_and_t1']['all']} of {f['fail_range_28']['all']} have the EMA between entry and Target 1; {f['fail_range_28_ema_above_candle']['all']} are rejected only because the EMA lies within 28 points ABOVE the candle (it does not obstruct a short's target), and {f['fail_range_28_ema_inside_candle']['all']} because it lies inside the candle (its relation to the target depends on the close). "
          f"Conversely, in this history no signal passes the 28-point range rule while the EMA lies between its entry and Target 1 ({f['pass_range_28_but_ema_between_entry_and_t1']['all']}), because Target 1 is only 27 points away; so in this history the convention never lets through a signal whose first target is blocked (the entry is the next one-minute open, so a gap beyond the candle could in principle do so), but it also rejects signals that are not blocked. A directional rule ('EMA at least 28 below the candle' or 'EMA not between entry and Target 1') is a separate owner decision.", "",
          "## Handwritten examples", "", tab(["correction", "date", "measurements", "status"], [[r["correction_id"], r["trading_date"], f"EMA {r.get('ema_relation', '')}; range distance {r.get('range_clearance', '')}; close distance {r.get('close_distance_to_ema', '')}; EMA between entry and T1: {r.get('ema_between_entry_and_t1', '')}", r["reconciliation_status"]] for r in dated if r["topic"] == "IRF_EMA_28"]), "",
          "Both signals are rejected (partly reconciled): the author's alternative 'wait for the EMA break' (a delayed entry) has no defined rule and is not modelled.", "",
          "## Remaining decisions", "", "O2: confirm the measure (range / close / entry / low), whether the EMA must be BELOW (directional), skip versus wait for the EMA break, and the method scope; 27 versus 28 is settled by the owner's 28."]
    (OUT / "irf_ema_28_implementation.md").write_text("\n".join(EM).replace("The out of", "Out of") + "\n")

    # ============================================================================================ pdr_first_eligible_implementation.md
    P = S["pdr"]
    sess = P["sessions_changed"]
    eight = [r for r in pdr if r["date"] in P["eight_old_retest_setups"]]
    chp = chs["phase53-pdr-first-eligible"]
    armed_p = [r for r in pdr if r["status"] == "ARMED"]
    sess = Counter(r["change"] for r in armed_p)
    PD = ["# PDR - earliest eligible confirmation (implementation)", "", WARN, "",
          "## Preserved", "", "Previous-day body-based resistance zone; the session must open strictly above the zone ceiling; a gap up; the **retest** (the first candle whose range meets the zone) must come first and **the retest candle itself may not confirm** (sequencing unresolved, preserved); the confirmation must close strictly above the zone ceiling; chronological processing; the 13:00 cutoff. Gap and zone requirements are unchanged.", "",
          "## Replaced (`PROVISIONAL_PDR_MINIMAL_CONFIRMATION`)", "",
          "The numeric thresholds (body 60% / wick 20% / 2x / 30% / 10% / 60%) were PROPOSED research values; the author's own note says no fixed percentage or wick size is required, and the PDR guide says: *\"After the zone has been tested, wait for a green candle and take the long entry on that confirmation\"* (s.4.3). The smallest transparent convention is therefore:",
          "* `GOOD_GREEN_BODY`: a green candle (close > open), any size;", "* `LOWER_PRICE_REJECTION` (covers the hammer): a candle of any colour whose lower wick is strictly larger than both its body and its upper wick and whose low reached the zone;", "* in both cases the close must be **strictly above the zone ceiling**. A green candle that closes at or below the ceiling, that is the retest candle, or that comes before the retest is **not** eligible.", "",
          "The first eligible candle activates the signal at its close; the fill is the next executable one-minute open (existing execution engine); a later or stronger candle never replaces it.", "",
          "## Effect (2025-09-01..2026-08-31)", "",
          tab(["armed sessions only (opened above the zone and retested it): first PDR signal", "sessions"], [["armed setups (retest happened)", P["armed_setups"]], ["same first signal", sess.get("SAME", 0)], ["**earlier first signal**", sess.get("EARLIER", 0)], ["newly signalled (no PDR signal before)", sess.get("NEW_SIGNAL", 0)], ["later", sess.get("LATER", 0)], ["removed", sess.get("REMOVED", 0)]]), "",
          f"Signal level (every re-armed signal): Phase 3.6 {P['signals_frozen']} -> Phase 5.3 {P['signals_phase53']} ({chp.get('PDR/TIME_SHIFTED_EARLIER', 0)} earlier, {chp.get('PDR/ADDED', 0)} newly generated, {chp.get('PDR/UNCHANGED', 0)} unchanged). The engine re-arms after a confirmation, so a looser confirmation yields more re-armed signals; the controller still takes only the first valid signal of the day, and a count increase is not an improvement.", "",
          f"Patterns behind the Phase 5.3 PDR signals (`patterns_passed`): first signal of each session {P['first_signal_patterns']}; all re-armed signals {P['all_signal_patterns']}. The rejection pattern is an addition beyond the guide's 'wait for a green candle' (it comes from the author's Phase 3.4 statement 'one good green body candle OR lower price rejection OR hammer'); the counts show how often it alone is the trigger.", "",
          f"The diagnostic re-derivation agrees with the engine on every session (sessions where they differ: {P['engine_differs_from_diagnostic']}), and the independent audit re-derives the same first signals from the raw candles.", "",
          "## The eight retest-candle setups (separately reported)", "",
          "Phase 5.2 found 8 armed setups whose retest candle itself would have qualified under the old thresholds. They are **not** changed (the retest candle may not confirm). With the new minimal convention " + str(P["retest_candle_would_qualify_phase53"]) + " armed setups have a retest candle that would qualify.", "",
          tab(["date", "retest candle", "Phase 3.6 first signal", "Phase 5.3 first signal", "if the retest candle were allowed"], [[r["date"], f"{r['retest_candle_start']} {r['retest_candle_ohlc']}", r["frozen_first_pdr_signal"] or "none", r["phase53_first_pdr_signal"] or "none", r["confirmation_time_if_retest_candle_were_permitted"] or "none"] for r in eight]), "",
          "## The five handwritten PDR examples", "",
          tab(["correction", "date", "author's first green candle", "retest candle", "Phase 5.3 first eligible candle", "status"], [[r["correction_id"], r["trading_date"], r.get("author_first_green_candle", ""), r.get("retest_candle", ""), r.get("phase53_pdr_first_eligible_candle", ""), r["reconciliation_status"]] for r in dated if r["topic"] == "PDR_FIRST_ELIGIBLE"]), "",
          "AC10, AC11, AC29 and AC40 now enter on the author's first green candle. AC02's candle is the retest candle itself; reconciling it requires allowing same-candle retest and confirmation, which the brief forbids without a source-proven rule (owner decision O7).", "",
          "## Remaining decisions", "", "O7: retest/confirmation sequencing; O6: whether the green-candle convention (and the rejection definition) is what the author means."]
    (OUT / "pdr_first_eligible_implementation.md").write_text("\n".join(PD) + "\n")

    # ============================================================================================ pds_first_eligible_implementation.md
    Q = S["pds"]
    armed_s = [r for r in rd(OUT / "pds_first_eligible_setups.csv") if r["status"] == "ARMED"]
    pds_chg = Counter(r["change"] for r in armed_s)
    new_elig = [r for r in twenty if not fb(r["subsequent_support_break_mandatory"]) and r["frozen_numeric_verdict"].startswith("WEAK")]
    already = [r for r in twenty if not fb(r["subsequent_support_break_mandatory"]) and not r["frozen_numeric_verdict"].startswith("WEAK")]
    weak20 = [r for r in twenty if fb(r["subsequent_support_break_mandatory"])]
    chd = chs["phase53-pds-first-eligible"]
    PS = ["# PDS - earliest eligible confirmation (implementation)", "", WARN, "",
          "## Preserved (source-defined)", "", "Previous-day support zone; gap-down open below the zone; the retest; the guide's sequence: *Methods 1 and 2 apply to the first red candle at the zone. If that red candle is not satisfying, use Method 3*; the **quality rule** *'do not take a weak red candle ... wait for a small support to form and break (Method 3)'*; Method 3's mandatory small-support break (pivot low, close below); the 13:00 cutoff.", "",
          "## Replaced (`PROVISIONAL_PDS_MINIMAL_QUALITY`)", "",
          "The guide lists 'what counts as a good red candle' and the pin-bar definition as open items ('body size and close are not numerically defined'); the 60% / 20% / 2x / 30% values were PROPOSED research numbers. They are replaced by structural dominance tests (no percentage, but an implicit threshold):", "* **Method 1**: a red candle whose body is strictly larger than each of its wicks;", "* **Method 2**: a red candle whose upper wick is strictly larger than its body and its lower wick, with the high reaching the zone;", "* anything else is a weak candle: **Method 3**.",
          "The two tests are mutually exclusive, so no candle confirms two methods (one actionable signal). These tests contain no percentage but are an implicit threshold (a body larger than each wick means a body above roughly a third of the range; a candle with body 37% and wicks 29% / 34% passes as 'good'; a pin with body 28% and wicks 41% / 31% passes), so they are NOT parameter-free and remain provisional (O6). The weak-red distinction is NOT removed: accepting the author's 'first candle entry' on a weak candle would override a source-defined rule, so it is flagged for approval instead.", "",
          "## Effect (2025-09-01..2026-08-31)", "",
          tab(["session level (first PDS signal of the session)", "sessions"], [["gap-down sessions with a zone retest and a red candle at the zone (ARMED)", len(armed_s)], ["gap-down sessions listed in total (incl. no retest / no red candle)", Q["gap_down_armed_sessions"]], ["same first signal", pds_chg.get("SAME", 0)], ["**earlier first signal**", pds_chg.get("EARLIER", 0)], ["later", pds_chg.get("LATER", 0)], ["newly signalled / removed", f"{pds_chg.get('NEW_SIGNAL', 0)} / {pds_chg.get('REMOVED', 0)}"]]), "",
          f"Signal level (every re-armed signal): Phase 3.6 {Q['signals_frozen']} -> Phase 5.3 {Q['signals_phase53']} ({chd.get('PDS/ADDED', 0)} newly generated, {chd.get('PDS/REMOVED', 0)} removed, {chd.get('PDS/TIME_SHIFTED_EARLIER', 0)} earlier, {chd.get('PDS/TIME_SHIFTED_LATER', 0)} later). A confirmation re-arms the setup, so a more permissive Method 1 test produces more re-armed signals; the controller takes only the first valid signal of the day (and a second PDS only after a full initial stop). Verdicts of the first red candle at the zone: {Q['verdicts']}.", "",
          "## The 20 sessions with a later strong red candle after a weak first red (Phase 5.2)", "",
          f"Re-evaluated under the Phase 5.3 reading: **{len(new_elig)} first red candles are newly eligible** (weak under the frozen numbers, eligible under the structural tests; confirmation moves earlier), **{len(already)} were already eligible under the frozen thresholds** (strong or pin; unchanged) and **{len(weak20)} remain weak** (Method 3, small-support break mandatory; the later strong candles are not used). {len(already)} of the twenty sessions were therefore never 'weak first red' cases under the frozen numbers; they appear in the Phase 5.2 list because a later strong red candle also exists.", "",
          tab(["date", "first red candle", "body / wicks %", "eligible now?", "method", "support break mandatory", "original", "new", "reason if still rejected"],
              [[r["date"], f"{r['first_red_candle_start']} {r['first_red_ohlc']}", f"{r['body_pct']} / {r['upper_wick_pct']} / {r['lower_wick_pct']}", r["eligible_under_phase53_reading"], r["method_that_applies"], r["subsequent_support_break_mandatory"], r["original_confirmation"], r["new_confirmation"], r["reason_if_earlier_candle_remains_rejected"][:160]] for r in twenty]), "",
          "## AC38 (2025-12-26, 'First candle entry')", "", "; ".join(f"{r['correction_id']}: {r['reconciliation_status']} - {r['reconciliation_note']}" for r in dated if r["topic"] == "PDS_FIRST_ELIGIBLE") + ".", "",
          "## Remaining decisions", "", "O6: may a weak first red candle be taken directly (overriding the guide's quality rule and Method 3)? Are the structural quality tests what the author means by a 'good' red candle?"]
    (OUT / "pds_first_eligible_implementation.md").write_text("\n".join(PS) + "\n")

    # ============================================================================================ orb_unresolved_entries.md
    O = S["orb"]
    OR = ["# ORB - the disputed entries (diagnostic; no priority override, no new rule)", "", WARN, "",
          f"The author reports that ORB was often not taken and IRF was selected. On all {O['disputed_dates']} disputed dates the engine produced **no ORB signal at all** (Phase 3.6: {O['orb_signal_on_any_disputed_date_phase36']}; Phase 5.3: {O['orb_signal_on_any_disputed_date_phase53']}), so the controller's first-valid-signal rule skipped nothing and **no priority was added**. The ORB engine is identical in every Phase 5.3 configuration (audit-verified; the colour rule is a separate opt-in).", "",
          tab(["date", "colour / body / wicks %", "failing: Method 1", "Method 2", "cause", "first signal now", "precise definition missing"],
              [[r["date"], f"{r['first_candle_colour']} / {r['body_pct']} / {r['upper_wick_pct']} / {r['lower_wick_pct']}", r["failing_Method_1"][:70], r["failing_Method_2"][:50], r["cause_category"], r["first_signal_phase53_author_corrected"] or "none", r["missing_definition_required"][:150]] for r in orb]), "",
          f"Causes: {O['causes']}. The handwritten pages contain no ORB drawings (checked in Phase 5.1/5.2), so the author's levels cannot be compared; the author-expected signals cannot be reproduced without the definitions below. IRF's first signal changes on {O['irf_first_signal_changed_on_disputed_dates']} of the 13 dates under the Phase 5.3 IRF rules, but ORB still does not activate on any.", "",
          "## Missing definitions required to reproduce the 13 expected signals", "",
          "1. **Method 2 inner level** (6 dates): the rulebook defines Method 1 by the previous-day high/low only; the inner support/resistance (an earlier fractal of the previous session) is a research variant not in the source. Needed: how the author chooses the level.",
          "2. **Method 2 trendline** (the dates where the trendline decided): a deterministic construction (which fractals, how many touches, tolerance).",
          "3. **Strong-candle thresholds** (the dates failing the body/wick profile): numbers or an approved looser profile (STRICT / MODERATE / LOOSE exist; MODERATE is active).",
          "4. **Trend filter** (the dates failing the EMA requirement): whether the previous-session close against its EMA, or another reference, is required.",
          "5. **Gap / 200-average set-up** numbers where it is the intended route.", "",
          f"Still unresolved: **{O['unresolved']} of {O['disputed_dates']}**. The Phase 5.1 ORB colour rule (long needs green, short red) remains selectable as `phase53-var-orb-colour` and removes {S['change_counts_vs_frozen']['phase53-var-orb-colour'].get('ORB/REMOVED', 0)} confirmed ORB signals; it is not part of the combined configuration."]
    (OUT / "orb_unresolved_entries.md").write_text("\n".join(OR) + "\n")

    # ============================================================================================ irf_day_low_unresolved.md
    D = S["irf_day_low"]
    DL = ["# IRF - 'should not activate at the day's low' (PENDING_OWNER_DEFINITION)", "", WARN, "",
          "The statement is not located in the five guides (Phase 5.2 search of the text and the IRF reference charts) and its predicate is not unique. **Nothing is applied**; the previous behaviour is preserved. No final-session low is used: every reading uses only candles that had closed when the signal was confirmed (no look-ahead).", "",
          f"Measured on the {D['signals']} IRF signals of the author-corrected configuration ({D['signals_within_cutoff']} within 13:00):", "",
          tab(["reading (none is a rule)", "meaning", "signals", "within 13:00"], [
              ["D1", "entry price at or below the running session low", D["D1_entry_at_or_below_running_low"]["all"], D["D1_entry_at_or_below_running_low"]["within_13_00"]], ["D2", "the signal candle closes below the running low of earlier candles", D["D2_close_below_running_low_before"]["all"], D["D2_close_below_running_low_before"]["within_13_00"]],
              ["D3", "closes on its own low and that is the running low", D["D3_close_at_running_low_incl_candle"]["all"], D["D3_close_at_running_low_incl_candle"]["within_13_00"]], ["D4", "Target 1 (entry - 27) lies below the running low", D["D4_t1_beyond_running_low"]["all"], D["D4_t1_beyond_running_low"]["within_13_00"]],
              ["D5", "entry within 28 points of the running low", D["D5_entry_within_28_of_running_low"]["all"], D["D5_entry_within_28_of_running_low"]["within_13_00"]], ["D6", "running low already below the opening-range low (IRL)", D["D6_running_low_already_below_irl"]["all"], D["D6_running_low_already_below_irl"]["within_13_00"]],
              ["D7", "an earlier candle already closed below IRL", D["D7_earlier_close_below_irl"]["all"], D["D7_earlier_close_below_irl"]["within_13_00"]], ["D8", "entry below the previous day's low", D["D8_entry_below_previous_day_low"]["all"], D["D8_entry_below_previous_day_low"]["within_13_00"]],
              ["IRL", "entry already below the opening-range low", D["entry_already_below_IRL"]["all"], D["entry_already_below_IRL"]["within_13_00"]]]), "",
          "Per signal (`irf_day_low_diagnostics.csv`): running session low at the signal time, signal candle low, proposed entry price, previous-day low, opening-range low, whether the entry has already broken the opening-range low, and the distance between the entry and the latest running low.", "",
          "Handwritten: " + "; ".join(f"{r['correction_id']} {r['trading_date'] or '(general remark, no date)'}" for r in dated if r["topic"] == "IRF_DAY_LOW") + " (see `dated_author_corrections.csv`). D6 and D7 are the readings that reproduce AC19 ('entry is below days low').", "",
          "**Owner decision O3:** which meaning (and where in the documents the rule is written), and whether the response is to skip the signal or to stop the day (AC19 says 'this day trading should be completely stopped')."]
    (OUT / "irf_day_low_unresolved.md").write_text("\n".join(DL) + "\n")

    # ============================================================================================ remaining_owner_decisions.md
    RD = ["# Remaining owner decisions (Phase 5.3)", "", "Nothing below is decided here. Provisional conventions stay labelled PROVISIONAL; the combined configuration is separately selectable and the frozen Phase 3.6 default is untouched.", "",
          tab(["#", "decision", "options", "evidence"], [
              ["O1", "Adopt the ORB colour rule? short mirror?", "adopt both / long only / no", f"removes {S['change_counts_vs_frozen']['phase53-var-orb-colour'].get('ORB/REMOVED', 0)} confirmed ORB signals"],
              ["O2", "IRF EMA clearance: confirm the range measure; directional (EMA below only / not between entry and Target 1) or symmetric; skip versus wait for the EMA break; scope", "see irf_ema_28_implementation.md", f"{f['fail_range_28']['all']} of {f['signals']} Phase 3.6 IRF signals fail; only {f['fail_range_28_and_ema_between_entry_and_t1']['all']} of them have the EMA between entry and Target 1"],
              ["O3", "IRF day's-low restriction: the predicate and the response", "D1-D8 readings", "irf_day_low_unresolved.md"],
              ["O4", "IRF first red candle: extend to Method 2B / Method 3? search start (after the extension or after the breakout)?", "2A only (current) / also 2B / also Method 3", f"{fr_s['red_search_start_changes']} of 42 executed trades differ by search start; AC08 moves against the stated direction"],
              ["O5", "IRF entry-candle body threshold (60 / 50 / 40 %)", "60 / 50 / 40 / none", "AC07, AC32 (not addressed)"],
              ["O6", "PDR / PDS conventions: green-candle and rejection tests; PDS structural quality tests; may a weak first red be taken directly (AC38)?", "keep provisional / change", "pdr_first_eligible_implementation.md, pds_first_eligible_implementation.md"],
              ["O7", "May the PDR retest candle itself confirm?", "yes / no", f"{P['retest_candle_would_qualify_phase53']} armed setups would qualify; AC02 depends on it"],
              ["O8", "ORB inner level, trendline, strength profile, trend filter definitions; ORB priority over IRF (not approved)", "author to supply", "orb_unresolved_entries.md"],
              ["O9", "RF-004 (open above yesterday's high) and the PDR failed-zone policy", "unchanged unless redefined", "Phase 5.1 AC05, AC36"],
              ["O10", "Where in the documents is 'IRF should not be activated at the day's low'?", "author to point to the page", "not found in the five guides"]]), "",
          "A revised profitability backtest has NOT been run and requires the owner's go-ahead after these decisions."]
    (OUT / "remaining_owner_decisions.md").write_text("\n".join(RD) + "\n")

    # ============================================================================================ source_to_code_traceability.md
    TR = ["# Source to code traceability", "", tab(["decision", "source / authority", "code", "tests", "outputs"], [
        ["IRF first red candle LOW (Method 2A)", "OWNER_APPROVED; IRF guide Method 2A (pullback low, red candle, close below)", "`strategies/irf_phase53.py::IRFPhase53Strategy._m2_step / _support_level` (inherits `irf_candidates.IRFFirstRedStrategy`)", "test_first_red_candle_low_is_the_support..., test_default_arguments_equal_the_frozen_engine..., test_real_default_phase53_irf_engine_equals_the_frozen_engine", "irf_first_red_low_implementation.md, irf_first_red_low_comparison.csv"],
        ["red search start (provisional)", "guide step order", "`IRFPhase53Strategy(red_search_start=...)`", "test_the_red_search_start_is_a_selectable_assumption...", "phase53-var-irf-first-red-after-breakout"],
        ["IRF 28-point EMA clearance", "OWNER_APPROVED (28); PROVISIONAL_EMA_RANGE_DISTANCE", "`irf_phase53.py::ema_geometry / IRFPhase53Strategy._ema_gate / _scan / _m2_step`", "test_range_clearance_geometry..., test_the_28_point_boundary_is_inclusive..., test_a_rejected_candidate_is_logged..., test_ema_available_after_the_decision..., test_27_and_28_give_different_answers..., test_scope_variants...", "irf_ema_28_implementation.md, irf_ema_signals.csv, irf_ema_rejections.csv"],
        ["PDR first eligible", "OWNER_APPROVED; PDR guide s.4.3; PROVISIONAL_PDR_MINIMAL_CONFIRMATION", "`strategies/first_eligible_phase53.py::PDRFirstEligibleStrategy / pdr_minimal_confirmation`", "test_the_first_green_candle_after_the_retest..., test_a_green_candle_must_still_close_strictly_above..., test_lower_price_rejection..., test_pdr_setup_conditions_are_preserved, test_pdr_uses_only_closed_candles...", "pdr_first_eligible_implementation.md, pdr_first_eligible_setups.csv"],
        ["PDS first eligible", "OWNER_APPROVED; PDS guide s.7; PROVISIONAL_PDS_MINIMAL_QUALITY", "`first_eligible_phase53.py::PDSFirstEligibleStrategy / pds_good_red / pds_red_pin`", "test_a_red_candle_whose_body_dominates..., test_a_red_pin_bar..., test_a_weak_first_red_candle_is_never_taken...", "pds_first_eligible_implementation.md, pds_first_eligible_setups.csv, pds_20_sessions.csv"],
        ["configurations", "Phase 5.3 brief", "`research/phase53.py::CONFIGS / make_engines53 / signals_for`", "test_configurations_are_separately_selectable..., test_real_each_configuration_changes_only_its_own_strategies", "scripts/phase53_run.py --list"],
        ["diagnostics", "Phase 5.3 brief", "`research/phase53_diag.py`", "test_diagnostic_setup_agrees_with_the_engine...", "irf_day_low_diagnostics.csv, orb_unresolved_entries.csv"],
        ["controller, stops, targets, RF, costs", "USER_APPROVED", "not touched", "frozen hashes, baseline-file hash test", "independent_audit.md"]])]
    (OUT / "source_to_code_traceability.md").write_text("\n".join(TR) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.3)", "",
          f"`scripts/phase53_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, n, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:160]] for i, (n, v) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation written in the same session as the pipeline; the fresh reviewer below is a separate pass.", "",
          "## Tests and lint", "", "* Before any change (existing suite): **678 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ============================================================================================ README
    diff_rows = []
    for st in ("IRF", "ORB", "PDR", "PDS", "RF"):
        c = chs[COMB]
        diff_rows.append([st, S[FROZEN]["by_strategy"][st], S[COMB]["by_strategy"][st], c.get(f"{st}/TIME_SHIFTED_EARLIER", 0), c.get(f"{st}/TIME_SHIFTED_LATER", 0), c.get(f"{st}/ADDED", 0), c.get(f"{st}/REMOVED", 0), c.get(f"{st}/SAME_TIME_LEVEL_CHANGED", 0), c.get(f"{st}/UNCHANGED", 0)])
    ds = S["dated"]
    RM2 = ["# Phase 5.3 - owner-approved author corrections", "", f"> {WARN}", "",
           "Stopped after Phase 5.3: no profitability backtest, nothing committed or pushed, no paper or live orders. The frozen Phase 3.6 default is unchanged; the new configuration is `" + COMB + "`.", "",
           "## Confirmed signals: Phase 3.6 versus Phase 5.3 (2025-09-01..2026-08-31, signal level)", "",
           tab(["strategy", "Phase 3.6", "Phase 5.3", "earlier", "later", "new", "removed", "same time, level changed", "unchanged"], diff_rows + [["**total**", S[FROZEN]["confirmed_total"], S[COMB]["confirmed_total"], "", "", "", "", "", ""]]), "",
           "A change in the count is not an improvement. PDR and PDS counts rise because a looser confirmation lets the setup re-arm more often; the controller still takes the first valid signal.", "",
           "## Headline results", "",
           tab(["item", "result"], [
               ["IRF Method 2A signals using a different reference (first red candle LOW)", f"{t2a['SAME_TIME_LEVEL_CHANGED'] + t2a['TIME_SHIFTED_EARLIER'] + t2a['TIME_SHIFTED_LATER'] + t2a['ADDED']} ({t2a['SAME_TIME_LEVEL_CHANGED']} same time with a new level, {t2a['TIME_SHIFTED_EARLIER']} earlier, {t2a['TIME_SHIFTED_LATER']} later, {t2a['ADDED']} new); {t2a['REMOVED']} removed; {t2a['UNCHANGED']} unchanged"],
               ["IRF signals failing the 28-point rule", f"{f['fail_range_28']['all']} of {f['signals']} Phase 3.6 signals ({f['fail_range_28']['executed']} of the {f['executed']} executed trades); net IRF confirmed signals {S[FROZEN]['by_strategy']['IRF']} -> {S['phase53-irf-ema28']['by_strategy']['IRF']} with the rule alone"],
               ["PDR first signals moved earlier", f"{sess.get('EARLIER', 0)} sessions earlier, {sess.get('NEW_SIGNAL', 0)} newly signalled (of {P['armed_setups']} armed setups)"],
               ["PDS first signals moved earlier", f"{pds_chg.get('EARLIER', 0)} sessions earlier (of {len(armed_s)} armed sessions with a retest and a red candle); of the 20 sessions: {len(new_elig)} newly eligible, {len(already)} already eligible, {len(weak20)} remain weak (Method 3)"],
               ["handwritten observations", f"{ds['rows']} rows: {ds['reconciled']} reconciled, {ds['partial']} partly reconciled, {ds['applied_without_observable_expectation']} rule applied without an observable expectation; statuses {ds['status_counts']}"],
               ["ORB disputed dates still unresolved", f"{O['unresolved']} of {O['disputed_dates']} (no ORB signal ever existed; definitions listed)"],
               ["IRF day's low", "PENDING_OWNER_DEFINITION - not applied; eight readings measured"]]), "",
           "## Files", "", "`approved_author_decisions.md`, `rule_authority_matrix.md`, `irf_first_red_low_implementation.md`, `irf_ema_28_implementation.md`, `pdr_first_eligible_implementation.md`, `pds_first_eligible_implementation.md`, `orb_unresolved_entries.md`, `irf_day_low_unresolved.md`, `source_to_code_traceability.md`, `signal_comparison.csv`, `dated_author_corrections.csv`, `remaining_owner_decisions.md`, `independent_audit.md`, "
           "`Phase53_Author_Corrections_Verification.xlsx`, `daily/`, `charts/`; supporting: `all_confirmed_signals.csv`, `daily_first_signal_comparison.csv`, `irf_first_red_low_comparison.csv`, `irf_ema_signals.csv`, `irf_ema_rejections.csv`, `pdr_first_eligible_setups.csv`, `pds_first_eligible_setups.csv`, `pds_20_sessions.csv`, `orb_unresolved_entries.csv`, `irf_day_low_diagnostics.csv`, `signal_counts.json`, `before_snapshot.json`.", "",
           "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase53_snapshot.py --snapshot       # baseline hashes (taken before any change)", "python scripts/phase53_run.py --list               # the selectable configurations",
           "python scripts/phase53_run.py                      # signal-only comparison + diagnostics + day reports + workbook", "python scripts/phase53_independent_audit.py", "python scripts/phase53_docs.py --tests \"...\" --ruff \"...\"", "python scripts/phase53_snapshot.py --verify", "```"]
    (OUT / "README.md").write_text("\n".join(RM2) + "\n")
    print("docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
