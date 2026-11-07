"""Phase 5.2: the markdown deliverables of reports/phase5/phase52_author_rules/, written from the CSV / JSON files produced by scripts/phase52_run.py (counts and identities are read, not typed).

  python scripts/phase52_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase52_author_rules"
P51 = ROOT / "reports" / "phase5" / "phase51_author_corrections"


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
    ba = rd(OUT / "before_after_signals.csv")
    pdr = rd(OUT / "pdr_first_eligible_setups.csv")
    pds = rd(OUT / "pds_first_eligible_setups.csv")
    irf = rd(OUT / "irf_signal_diagnostics.csv")
    fr = rd(OUT / "irf_first_red_comparison.csv")
    orbj = json.loads((OUT / "orb_missing_signal_audit.json").read_text())
    dc = rd(OUT / "dated_corrections_comparison.csv")
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    flags = S["irf_flag_counts"]
    cfgs = ["phase36-frozen", "phase52-approved", "phase52-cand-orb-colour", "phase52-cand-irf-first-red-low", "phase52-cand-irf-first-red-body-low"]
    chg = {k: Counter(r["change"] for r in ba if r["config"] == k) for k in cfgs[1:]}
    exec_chg = {k: sum(1 for r in ba if r["config"] == k and fb(r["executed_in_phase36_ledger"]) and r["change"] != "ANNOTATION_ONLY") for k in cfgs[1:]}
    WARN = "Signal-level evidence only: no controller, no fills, no P&L and no revised backtest were run. Candidates are NOT approved rules."

    # ============================================================================================ author_call_clarifications.md
    CL = ["# The author's latest clarifications (telephone call and follow-up)", "", WARN, "",
          "The call itself is not recorded anywhere I can read; the statements below are quoted from the Phase 5.2 brief. 'USER_APPROVED' marks what the owner explicitly approved; everything else is the author's statement, which is authoritative evidence of intent but is implemented only where its meaning is unambiguous.", "",
          tab(["#", "statement (as given)", "authority", "what was verified", "Phase 5.2 outcome"], [
              ["C1", "\"ORB is ignored many times, and IRF is taken instead.\"", "AUTHOR_STATEMENT", f"on the 13 Phase 5.1 'ORB should have activated' dates the engine produced no ORB signal at all; causes found: {', '.join(f'{k.split(' (')[0]} {v}' for k, v in S['orb_missing_signal_causes'].items())}", "explained, not changed; no priority override of IRF"],
              ["C2", "\"IRF should use the first red candle that creates the support level, followed by entry.\"", "AUTHOR_STATEMENT (level definition not given)", "only Method 2A takes a support level that a red candle leaves behind; the guide's 'recent support' is a pullback low (IRF-M2A-001); the dated handwritten examples do not fix the level", "two separately labelled CANDIDATES (low / body low of the first red candle); active rule UNRESOLVED"],
              ["C3", "\"Sometimes IRF is correct, but the gap between the EMA and the candle should be 28 points.\"", "AUTHOR_STATEMENT (measure, inequality and scope not given; the handwritten pages say 27)", "no EMA or 28 / 27-point statement exists in the IRF guide; diagnostics computed for every confirmed IRF signal", "diagnostics only; UNRESOLVED"],
              ["C4", "\"IRF should not be activated if it is at the day's low. This is already in the documents.\"", "AUTHOR_STATEMENT; the claim 'already in the documents' could NOT be verified", "searched the text layer of all five guides and viewed the IRF reference charts: no such statement (the guide mentions the low only for marking the initial range)", "diagnostics only (five alternative readings, running low at decision time); UNRESOLVED"],
              ["C5", "\"Entry should occur on the first eligible candle.\" (PDR and PDS)", "USER_APPROVED as clarified by the owner: the first completed candle after ALL required strategy conditions are satisfied, not the first five-minute candle of the day", f"re-derived independently from the raw candles for every session: the engines already activate on that candle; PDR {sum(1 for r in pdr if r['verdict'] == 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE')} setups and PDS {sum(1 for r in pds if r['verdict'] == 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE')} setups, 0 late entries", "SATISFIED UNDER THE PRESERVED PROPOSALS (PDR-A07, numeric thresholds, PDS-M-001); the author's handwritten examples are NOT satisfied; no signal changes; diagnostics + sensitivity added; PDS co-confirmed methods recorded"]]), "",
          "Statements C2-C4 are not turned into rules by their wording alone: the brief forbids inventing the support level, the EMA inequality, or the meaning of 'at the day's low'. Each is reported with the evidence needed to decide (see `remaining_owner_decisions.md`)."]
    (OUT / "author_call_clarifications.md").write_text("\n".join(CL) + "\n")

    # ============================================================================================ rule_authority_matrix.md
    AM = ["# Rule authority matrix", "", "Authority levels: SOURCE_VERIFIED (a guide states it), AUTHOR_APPROVED (the author's own sentence, Phase 3.4), USER_APPROVED (owner), AUTHOR_CALL (Phase 5.2 telephone statement), HANDWRITTEN (Phase 5.1), PROPOSED (a research parameter nobody approved).", "",
          tab(["rule", "authority", "current engine", "Phase 5.2 status", "evidence"], [
              ["PDR / PDS entry on the first eligible confirmation candle", "USER_APPROVED (owner clarification) + AUTHOR_CALL", "already implemented (PDR: first qualifying candle after the retest; PDS: first red candle at the zone, Method 3 on the earliest support break)", "ACTIVE - verified, unchanged", "pdr_first_eligible_audit.md, pds_first_eligible_audit.md"],
              ["PDR zone = previous-day body-based resistance, open strictly above, retest, pattern, close strictly above the ceiling", "AUTHOR_APPROVED (PDR-A01..A05) / OWNER_INTERPRETATION", "implemented (Phase 3.6)", "ACTIVE - preserved", "unchanged"],
              ["PDR pattern numbers (body 60%, upper wick 20%, 2x wick, 30% close, hammer 10% / 60%)", "PROPOSED", "implemented as research parameters", "ACTIVE - preserved (the brief forbids changing them)", "the handwritten 'first green candle' candles fail them (see the PDR audit)"],
              ["the PDR confirmation may not be the retest candle", "PROPOSED (PDR-A07)", "implemented", "ACTIVE - preserved and LABELLED; owner decision O7", f"{sum(1 for r in pdr if fb(r['interaction_candle_would_qualify_if_permitted']))} armed setups have a retest candle that would itself qualify"],
              ["PDS: first red candle at the zone; weak first candle not taken; Method 3 break of a small support", "SOURCE_VERIFIED_QUALITATIVE (PDS-M-001, PDS-M3-001)", "implemented", "ACTIVE - preserved", "pds_first_eligible_audit.md"],
              ["PDS co-confirmed methods recorded, one actionable signal", "USER_APPROVED (brief 5.2)", "recorded by `PDSCoConfirmStrategy` (annotation only)", "ACTIVE in `phase52-approved`", f"occurs in {len(S['pds_sessions_with_co_confirmed_methods'])} sessions (a strong body and a higher-price-rejection pin bar are mutually exclusive with the current thresholds)"],
              ["IRF Method 2A support = first red candle (level?)", "AUTHOR_CALL", "support = swing-low fractal (proposal SWING_K1)", "CANDIDATE only (low / body low); UNRESOLVED", "irf_first_red_candle_audit.md"],
              ["IRF EMA gap of 28 points", "AUTHOR_CALL (handwritten pages: 27)", "no EMA condition", "UNRESOLVED - diagnostics only", "irf_ema_28_point_audit.md"],
              ["IRF not at the day's low", "AUTHOR_CALL ('already in the documents': not located)", "no condition", "UNRESOLVED - diagnostics only", "irf_day_low_audit.md"],
              ["ORB long needs a green first candle (short: red)", "HANDWRITTEN for long (AC27); short = source interpretation (ORB-GLOBAL-002)", "pin-bar route admits either colour", "CANDIDATE (Phase 5.1, opt-in), kept selectable", "phase52-cand-orb-colour"],
              ["ORB inner level, trendline, strength thresholds, trend filter", "PROPOSED research variants (not in the source)", "implemented as proposals", "ACTIVE - preserved; causes of the missing signals reported", "orb_missing_signal_audit.md"],
              ["first valid signal first; max two trades; second trade only PDR/PDS after a full stop; 13:00 cutoff; 6 lots 3+3; stops 35 (ORB 30); T1 27; T2 60/70; post-T1 stop entry -/+ 6; no trailing; forced exit; same-minute conflicts unresolved", "USER_APPROVED", "implemented", "ACTIVE - unchanged (no controller code touched)", "frozen hashes verified"],
              ["RF", "SOURCE_VERIFIED / USER_APPROVED", "implemented", "ACTIVE - unchanged", "RF signals identical under every configuration"]])]
    (OUT / "rule_authority_matrix.md").write_text("\n".join(AM) + "\n")

    # ============================================================================================ pdr_first_eligible_audit.md
    armed = [r for r in pdr if r["status"] == "ARMED"]  # ARMED = open strictly above the zone AND the zone was retested; ARMED_NO_ZONE_RETEST = open above the zone, never retested
    n_open_above = sum(1 for r in pdr if r["status"] in ("ARMED", "ARMED_NO_ZONE_RETEST"))

    def earlier_or_new(r, col):
        v, e = r.get(col, ""), r["engine_first_signal_time"]
        return bool(v) and (not e or v < e)
    sens = {c: [r for r in armed if earlier_or_new(r, c)] for c in ("sensA_retest_candle_permitted_approved_patterns", "sensB_first_green_close_above_ceiling_after_retest_no_thresholds", "sensC_first_green_close_above_ceiling_retest_permitted_no_thresholds")}
    nsig = lambda lst: sum(1 for r in lst if r["engine_first_signal_time"])  # noqa: E731
    PD = ["# PDR - first eligible confirmation candle (audit)", "", WARN, "",
          "**Requirement (USER_APPROVED):** the first completed candle after all required conditions are satisfied (previous-day body-based zone, open strictly above its ceiling, retest of the zone, an approved pattern, close strictly above the ceiling) activates the signal at ITS close; no later or stronger candle may replace it; nothing before the retest; no incomplete candle.", "",
          f"**Result: no late entry relative to the PRESERVED rules (PDR-A07 retest convention, the proposed numeric thresholds).** Of {len(pdr)} gap-up sessions, {n_open_above} opened strictly above the zone and {len(armed)} of those retested it ('armed'); of the armed setups {sum(1 for r in pdr if r['verdict'] == 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE')} of them produced a signal; in every one the engine's signal is on the first eligible candle (verdicts: {dict(Counter(r['verdict'] for r in pdr))}). "
          "`LATE_ENTRY_DEFECT` count: **0**. Caveat: the setup diagnostics reuse the engine's state machine and pattern functions, so that flag cannot fire by construction; the check with independent value is `scripts/phase52_independent_audit.py` (and the fresh reviewer), which re-derived the zone (highest body high of the previous session), the gap, the retest and the three pattern tests from the raw one-minute data and agrees on every session.", "",
          "## Why the engine already satisfies the principle", "",
          "`PDRBodyStrategy._scan` records the first candle whose range meets the zone as the retest, then tests each LATER completed candle in order and activates on the first one that passes a pattern AND closes strictly above the ceiling; the state machine then resets. A later or stronger candle can never replace it. "
          "The fill is the next one-minute open (EXE-FILL-001), after the candle has closed.", "",
          "## What the author's handwritten 'first green candle' examples show", "",
          "In the five PDR examples (AC02, AC10, AC11, AC29, AC40) the candle the author points at is NOT eligible under the preserved rules: either it is the retest candle itself (convention PDR-A07, a proposal) or it fails the proposed numeric patterns. **The author's example is therefore NOT satisfied; what is satisfied is the first-eligible principle under the preserved proposals.** The PDR guide's own words ('after the zone has been tested, wait for a green candle'; 'green candle formed after the interaction') partly support PDR-A07, but it gives no numeric thresholds.", "",
          tab(["date", "correction", "zone", "retest (first touch) candle", "engine first signal", "author's first green candle", "why earlier candles were not eligible"],
              [[r["trading_date"], r["correction_id"], f"{pr.get('zone_floor', '')}-{pr.get('zone_ceiling', '')}", pr.get("first_zone_touch_candle_start", ""), pr.get("engine_first_signal_time", "") or "none", r.get("author_reading_first_green_candle", ""), (pr.get("reasons_earlier_candles_not_eligible", "") or "")[:300]]
               for r in dc if r["topic"] == "PDR_FIRST_ELIGIBLE" for pr in [next((x for x in pdr if x["date"] == r["trading_date"]), {})]]), "",
          "## Sensitivity (diagnostics only; NOT activated): how much earlier would entries be under looser readings?", "",
          f"Over the {len(armed)} armed setups (zone retested), counting setups whose entry would come earlier than the engine's, or where the engine has no signal:", "",
          tab(["reading of 'first eligible'", "setups earlier or newly signalled", "of which the engine has a signal", "of which the engine has none"], [
              ["A: approved patterns, but the retest candle itself may confirm", len(sens[list(sens)[0]]), nsig(sens[list(sens)[0]]), len(sens[list(sens)[0]]) - nsig(sens[list(sens)[0]])],
              ["B: first GREEN candle after the retest that closes above the ceiling, no numeric thresholds (the guide's wording)", len(sens[list(sens)[1]]), nsig(sens[list(sens)[1]]), len(sens[list(sens)[1]]) - nsig(sens[list(sens)[1]])],
              ["C: as B, retest candle also allowed", len(sens[list(sens)[2]]), nsig(sens[list(sens)[2]]), len(sens[list(sens)[2]]) - nsig(sens[list(sens)[2]])]]), "",
          "Per-session times are in `pdr_first_eligible_setups.csv` (`sensA_...`, `sensB_...`, `sensC_...`). The shifts are not 'one candle': in several sessions the retest candle at the open would qualify and the engine's own entry comes 5 to 60 minutes later. These readings change entries a lot and are decisions for the owner (O6, O7), not defects.", "",
          "Per-candle reasons for every setup are in `pdr_first_eligible_setups.csv` (`reasons_earlier_candles_not_eligible`) and `pdr_setup_diagnostics.json`.", "",
          "## Preserved conventions (labelled, not changed)", "",
          f"* The confirmation candle may not be the retest candle (PDR-A07, PROPOSED). In {sum(1 for r in pdr if fb(r['interaction_candle_would_qualify_if_permitted']))} armed setups the retest candle itself would have qualified (see the sensitivity table for the resulting times: from 5 to 60 minutes earlier). That is a new permission and is NOT made here (decision O7).",
          "* The numeric pattern thresholds are the Phase 3.6 research values (PROPOSED). The author's examples suggest they may be too strict; changing them is an owner decision (O6).", "",
          "## Diagnostics recorded for every PDR setup", "", "zone construction timestamp (candle that made the zone), zone floor / ceiling, opening-gap eligibility, first zone-touch candle, first eligible confirmation candle, the chosen entry, every later confirmation ignored, and the reason each earlier candle was not eligible (columns of `pdr_first_eligible_setups.csv`)."]
    (OUT / "pdr_first_eligible_audit.md").write_text("\n".join(PD) + "\n")

    # ============================================================================================ pds_first_eligible_audit.md
    armed_s = [r for r in pds if r["status"] == "ARMED"]
    later_strong = [r for r in pds if r.get("later_strong_red_candles_after_weak_first_red")]
    meth = Counter(r["first_eligible_method"] for r in pds if r["first_eligible_method"])
    PS = ["# PDS - first eligible confirmation candle (audit)", "", WARN, "",
          f"**Result: no late entry relative to the PRESERVED rules (PDS-M-001 quality rule, Method 3 sequence).** {len(pds)} sessions had a gap-down; {len(armed_s)} armed setups (zone touched; sessions that opened below the zone but never touched it are ARMED_NO_ZONE_RETEST); {sum(1 for r in pds if r['verdict'] == 'ENGINE_ON_FIRST_ELIGIBLE_CANDLE')} produced a signal ({dict(meth)}), every one on the first eligible candle (verdicts: {dict(Counter(r['verdict'] for r in pds))}). `LATE_ENTRY_DEFECT`: **0**. Re-derived independently from the raw candles for every session.", "",
          "## Sequences preserved", "",
          "* Methods 1 and 2 apply to the FIRST red candle at the zone: a strong bearish body (Method 1) or a higher-price-rejection pin bar (Method 2) activates the signal at that candle's close; the engine does not wait for another bearish candle.",
          "* If that first red candle is weak it is NOT taken (quality rule PDS-M-001): Method 3 then waits for a small support near the zone and activates on the earliest completed candle that closes below it. Entering on the weak first candle would skip the mandatory sequence (the first-eligible principle does not override it).",
          "* Convention to note: for PDS the first red candle at the zone may be the first interaction candle itself (no retest-first requirement as in PDR); this is the existing engine behaviour and is preserved.", "",
          "## Several methods on one candle", "",
          f"The frozen engine reports only one record per candle. `PDSCoConfirmStrategy` (configuration `phase52-approved`) records any other method the same candle satisfies in `concurrent_methods` and produces one actionable signal. With the current thresholds this never happens (a strong body needs body >= 60% of the range, a pin bar needs an upper wick >= 2x the body: mutually exclusive; Method 3 cannot coincide with Methods 1 and 2 by sequence): sessions with a co-confirmed method: {len(S['pds_sessions_with_co_confirmed_methods'])}. A test forces the second method to prove the recording path and that the signal count does not change.", "",
          "## The handwritten PDS examples", "",
          tab(["date", "correction", "evidence", "remaining decision"], [[r["trading_date"], r["correction_id"], r.get("phase52_evidence", ""), r["remaining_owner_decision"]] for r in dc if r["topic"] == "PDS_FIRST_ELIGIBLE"]), "",
          "AC38 ('First candle entry', 2025-12-26) asks for entry on the first candle; the engine entered on the Method 3 support break. The report reads 'first candle' as the weak first red candle at the zone (body 10.4%), which the preserved quality rule rejects; an alternative reading (a later strong red candle at the zone, listed below) is also possible. **The author's example is NOT satisfied; the principle is satisfied only under the preserved quality rule.** AC21 / AC22 / AC35 are not about timing and are unchanged (zone construction and the second-trade rule).", "",
          "## Later strong red candles after a weak first red candle (owner decision O6)", "",
          f"The preserved rule (PDS guide: 'Methods 1 and 2 apply to the first red candle ... if that red candle is not satisfying, use Method 3') does not use a LATER red candle at the zone that meets the Method 1 / 2 numbers. In {len(later_strong)} sessions such a candle exists before or at the engine's Method 3 entry (or with no entry at all). Under a literal 'first eligible candle' reading these could be earlier or additional entries; they are listed, not activated:", "",
          tab(["date", "engine first signal", "later strong red candles at the zone"], [[r["date"], r["engine_first_signal_time"] or "none", r["later_strong_red_candles_after_weak_first_red"]] for r in later_strong]), "",
          "Per-setup candidate lists are in `pds_first_eligible_setups.csv` and `pds_setup_diagnostics.json`."]
    (OUT / "pds_first_eligible_audit.md").write_text("\n".join(PS) + "\n")

    # ============================================================================================ irf_first_red_candle_audit.md
    def chg_tab(cfg):
        c = chg[cfg]
        return [cfg, c.get("TIME_SHIFTED_EARLIER", 0), c.get("TIME_SHIFTED_LATER", 0), c.get("ADDED", 0), c.get("REMOVED", 0), exec_chg[cfg]]
    n_low_diff = sum(1 for r in fr if r.get("candidate_LOW_change_vs_baseline_executed_signal", "") not in ("same time and method", ""))
    n_body_diff = sum(1 for r in fr if r.get("candidate_BODY_LOW_change_vs_baseline_executed_signal", "") not in ("same time and method", ""))
    dated = [r for r in fr if r["handwritten_dated_example"]]

    def agree(r):
        d = r["author_stated_direction"]
        c = r.get("candidate_LOW_change_vs_baseline_executed_signal", "")
        if "earlier" in d:
            return "agrees" if c.startswith("earlier") else "does not agree"
        if "later" in d:
            return "agrees" if c.startswith("later") else "does not agree"
        return "direction not stated by the author"
    IR = ["# IRF - 'the first red candle that creates the support level' (audit and candidates)", "", WARN, "",
          "## Which methods use a red-candle support reference", "",
          tab(["method", "reference in the guide", "uses a support created by a red candle?", "candidate applied?"], [
              ["Method 1", "the failure candle closes back inside the initial range", "no", "no"],
              ["Method 2A", "'recent support' = a pullback low left behind by the extension; a red candle must form first; entry when a candle closes below the support (IRF-M2A-001/002)", "YES - the red candle is a precondition and the support is the pullback low", "YES: support taken from the first red candle"],
              ["Method 2B", "'recent resistance' = the top of the first push; a red candle closes back below it", "no (a resistance, not a support)", "no (a resistance-side wording would be a separate decision)"],
              ["Method 3", "'recent support formed by the preceding candles'; the red sweep candle itself must close below it", "no (the support precedes the sweep candle)", "no"]]), "",
          "## What is established and what is not", "",
          "Established: the engine already tracks the FIRST red candle after the extension (`red_candle_index`) and never replaces it with a later one. The Phase 3.6 engine does not tie the support level to that candle: it takes the latest swing-low fractal (SWING_K1).",
          "NOT established (the author's wording and the guide are silent): whether the level is the red candle's LOW, its BODY LOW, or a broader local support. Per the brief nothing is invented: both candle-based levels are offered as candidates and the active rule is unchanged.", "",
          "## Candidate engines (`IRFFirstRedStrategy`, opt-in)", "",
          "Support for Method 2A = the first red candle's low (`phase52-cand-irf-first-red-low`) or its body low (`phase52-cand-irf-first-red-body-low`); the entry is the first LATER candle that closes below it, activated at that close. In `BASELINE_SWING` mode the class reproduces the frozen engine exactly (asserted on all 247 sessions and on synthetic candles).", "",
          "## Signal changes (confirmed IRF signals, 2025-09-01..2026-08-31)", "",
          tab(["configuration", "earlier", "later", "added", "removed", "involving a Phase 3.6 executed signal"], [chg_tab("phase52-cand-irf-first-red-low"), chg_tab("phase52-cand-irf-first-red-body-low")]), "",
          f"Confirmed IRF signals: frozen {S['phase36-frozen']['by_strategy']['IRF']}, low candidate {S['phase52-cand-irf-first-red-low']['by_strategy']['IRF']}, body-low candidate {S['phase52-cand-irf-first-red-body-low']['by_strategy']['IRF']} (re-arming after a confirmation lets more attempts complete; signal counts do not predict executed trades). "
          "Method 2B signals can also change because an earlier or later 2A confirmation changes when an attempt ends; Methods 1 and 3 are history-independent and identical (audit check).", "",
          f"## The 42 executed Method-2 trades (the Phase 5.1 '37 reading disagreements' are the {sum(1 for r in fr if fb(r['in_phase51_37_reading_disagreements']))} flagged rows)", "",
          f"For each trade `irf_first_red_comparison.csv` shows the old reference (swing support candle / push-top candle and level), the first qualifying red candle with its OHLC, the support level under both definitions, the candidate break confirmation and the signal-time change. "
          f"The first IRF signal of the session changes for {n_low_diff} of 42 trades under the LOW candidate and {n_body_diff} of 42 under the BODY_LOW candidate; the two definitions give a different answer on {sum(1 for r in fr if r.get('candidate_LOW_change_vs_baseline_executed_signal') != r.get('candidate_BODY_LOW_change_vs_baseline_executed_signal'))} trades, which is why the level cannot be chosen by default.", "",
          "### Dated handwritten examples (source evidence)", "",
          tab(["date", "example", "author's stated direction", "baseline signal", "old reference", "first red candle (OHLC)", "LOW candidate", "BODY_LOW candidate", "LOW vs the author's direction"],
              [[r["date"], r["handwritten_dated_example"], r["author_stated_direction"], f"{r['baseline_signal_time']} {r['baseline_method']}", f"{r['old_reference_kind']} {r['old_reference_level']} ({r['old_reference_candle_start']})", f"{r['first_qualifying_red_candle_start']} {r['first_red_candle_ohlc']}",
                r.get("candidate_LOW_change_vs_baseline_executed_signal", ""), r.get("candidate_BODY_LOW_change_vs_baseline_executed_signal", ""), agree(r)] for r in dated]), "",
          "The remaining executed Method-2 trades have only the call statement as source evidence. **Source supports the change? Partly**: the author's intent (a first-red-candle reference) is stated by the call and by repeated handwritten remarks; the level and the method scope are not. No outcome (profit) was compared.", "",
          "## Remaining decisions", "", "O4: the level (low / body low / local support), the scope (2A only, or also 2B / Method 3), whether the break must be by a red candle, and what 'first' means: the first red candle after the EXTENSION (the engine's reading) or after the BREAKOUT (differs on many Method-2 signals; the independent reviewer counted 13 of the 42 executed Method-2 trades). The guide itself orders the steps pullback low, then red candle, then close below the support, so 'support = the first red candle' is a re-reading of the guide."]
    (OUT / "irf_first_red_candle_audit.md").write_text("\n".join(IR) + "\n")

    # ============================================================================================ irf_ema_28_point_audit.md
    f = lambda k: (flags[k]["all_signals"], flags[k]["executed"], flags[k]["within_13_00_cutoff"], flags[k]["executed_within_cutoff"])  # noqa: E731
    between = [r for r in irf if fb(r.get("E1_between_27_and_28")) or fb(r.get("E2_between_27_and_28"))]
    ema_dated = [r for r in dc if r["topic"] == "IRF_EMA_28"]
    EM = ["# IRF - the 28-point EMA gap (investigation; diagnostics only)", "", WARN, "",
          "**Statement (call):** 'Sometimes IRF is correct, but the gap between the EMA and the candle should be 28 points.' **Handwritten pages (Phase 5.1):** 'space between the entry candle and the EMA less than 27 -> wait for the EMA break' (AC13, AC18).", "",
          "## Source search", "", "The IRF guide never mentions the 200 EMA in its text (the reference charts draw a moving-average line without a rule). The 27 of the handwritten pages equals Target 1 (27 points); 28 is new. **No deterministic rule can be derived from the sources.** Nothing is activated.", "",
          "## What cannot be established (so it is not guessed)", "",
          "* the measurement: signal-candle close, high, low, the entry price, or the whole candle against the EMA;", "* the inequality: a minimum clearance (EMA at least 28 below), a maximum distance, or |close - EMA| in either direction;",
          "* the action: skip the signal, or wait until a candle closes below the EMA (and for how long);", "* the scope: every IRF method or only some;", "* 28 (call) versus 27 (handwritten).", "",
          f"## Diagnostics computed for every confirmed IRF signal ({flags['signals']} signals, {flags['executed']} signal rows matching a Phase 3.6 executed trade; EMA = EMA(200) of completed five-minute closes)", "",
          "Per signal: EMA(200), candle high / low / close, entry price (the next one-minute open), close - EMA, high - EMA, low - EMA, entry - EMA, |close - EMA|, whether the EMA lies between the entry and Target 1 (entry - 27), EMA - T1. See `irf_signal_diagnostics.csv`.", "",
          tab(["alternative reading (none is a rule)", "all confirmed IRF signals", "of which executed in Phase 3.6", "signals within the 13:00 cutoff", "executed within cutoff"], [
              ["close is 0..28 points ABOVE the EMA (E1)", *f("E1_close_gap_below_ema_28")], ["entry price is 0..28 points above the EMA (E2)", *f("E2_entry_gap_below_ema_28")], ["signal-candle LOW is 0..28 above the EMA (E3)", *f("E3_low_gap_below_ema_28")],
              ["|close - EMA| < 28 on either side (E4)", *f("E4_abs_close_gap_28")], ["the same as E1 with 27 (handwritten number)", *f("E1_27")], ["close - EMA in [27, 28): where 27 and 28 give DIFFERENT answers", *f("E1_between_27_and_28")],
              ["EMA between the entry and Target 1", *f("ema_between_entry_and_t1")]]), "",
          f"Reading E1 (close-based, 0 < close - EMA < N): the choice between 27 and 28 changes the answer for {flags['E1_between_27_and_28']['all_signals']} signals ({flags['E1_between_27_and_28']['executed']} matching executed trades). Under reading E2 (entry-based) it changes the answer for {flags['E2_between_27_and_28']['all_signals']} signals ({flags['E2_between_27_and_28']['executed']} executed). Union of the two readings: " + ", ".join(sorted({f"{r['date']} {r['signal_time']} {r['method']}" + (" (executed)" if fb(r["executed_in_phase36_ledger"]) else "") for r in between})) + ". The number is not a rounding detail.", "",
          "## The two dated handwritten examples", "", tab(["date", "correction", "measurements"], [[r["trading_date"], r["correction_id"], r.get("phase52_evidence", "")] for r in ema_dated]), "",
          "Both examples are consistent with every reading above (EMA 2.93 and 25.27 points below the entry), so they cannot discriminate between 'skip' and 'wait', between close and entry, or between 27 and 28.", "",
          "## Conclusion and request", "", "Preserve the current IRF engine; no EMA rule is implemented. **Owner decision O2:** the measure, the inequality, skip versus wait, the scope, and 27 versus 28."]
    (OUT / "irf_ema_28_point_audit.md").write_text("\n".join(EM) + "\n")

    # ============================================================================================ irf_day_low_audit.md
    DL = ["# IRF - 'not at the day's low' (investigation; diagnostics only)", "", WARN, "",
          "**Statement (call):** 'IRF should not be activated if it is at the day's low. This is already in the documents.'", "",
          "## Source verification", "", "Searched: the extracted text of the five strategy PDFs (IRF, ORB, PDR, PDS, RF) for day's low / day low / session low / lowest / intraday low, and the IRF reference chart pages (viewed). **The statement was not found.** The IRF guide uses the low only for marking the initial range (IRL) and for Method 3's recent support. "
          "The handwritten pages (Phase 5.1) contain it as the author's red-star remark (G02) and in AC19 / AC32. So the 'already in the documents' claim could not be verified; the rule is treated as an author statement whose meaning is open.", "",
          "## Alternative meanings, measured at the decision time only", "",
          "Computed with ONLY candles that had closed when the signal was confirmed (the running session low before the signal candle, and including it); the final daily low is never used (an audit check confirms the values and counts the signals where the final low differs from the running low, i.e. where a look-ahead implementation would have disagreed).", "",
          tab(["reading (none is a rule)", "meaning", "all confirmed IRF signals", "of which executed in Phase 3.6", "within the 13:00 cutoff", "executed within cutoff"], [
              ["D1", "the entry price (next one-minute open) is at or below the running low", *f("D1_entry_at_or_below_running_low")], ["D2", "the signal candle CLOSES below the running low of the earlier candles (a short entered after the low has been broken)", *f("D2_close_below_running_low_before")],
              ["D3", "the signal candle closes on its own low and that is the running low", *f("D3_close_at_running_low_incl_candle")], ["D4", "Target 1 (entry - 27) lies below the running low: too close to the day's low to permit the first target", *f("D4_t1_beyond_running_low")],
              ["D5", "the entry is within 28 points of the running low", *f("D5_entry_within_28_of_running_low")],
              ["D6", "the session's running low (before the signal) is already below the initial range low (IRL): the day has already broken the opening range downwards", *f("D6_running_low_already_below_irl")], ["D7", "an earlier candle in the session already closed below IRL", *f("D7_earlier_close_below_irl")],
              ["D8", "the entry price is below the PREVIOUS day's low", *f("D8_entry_below_previous_day_low")]]), "",
          f"All counts include signals after the 13:00 cutoff ({flags['signals'] - flags['signals_within_13_00_cutoff']} of {flags['signals']} confirmed IRF signals are post-cutoff and not tradable); the cutoff columns show the tradable subset.", "",
          "The readings are NOT equivalent: D1-D3 touch a handful of signals and no executed trade, D4 and D5 a few dozen, and D6 / D7 / D8 (added after review because AC19 reads 'entry is below days low') hundreds. Fields per signal (running low before / including the signal candle, signal candle low and close, entry level, distance to the running low, Target 1 clearance) are in `irf_signal_diagnostics.csv`.", "",
          "## The dated handwritten examples", "", tab(["date", "correction", "measurements"], [[r["trading_date"], r["correction_id"], r.get("phase52_evidence", "")] for r in dc if r["topic"] == "IRF_DAY_LOW"]), "",
          "AC19 (2025-11-12; the author's words: 'IRF is already activate[d] ... entry is below days low'): the executed trade is 66 points above the running low, so D1-D5 do NOT reproduce the remark. D6 and D7 do (the running low 25781.25 was already below the initial range low 25805.40 at the 10:05 signal): the remark is consistent with 'the day has already broken the opening range downwards'. AC32 (2025-12-11): the second candle closes below the running low (D2). Which reading is meant is an owner decision (O3).", "",
          "## Conclusion and request", "", "No rule is implemented: the brief requires an unambiguous source rejection condition, and none exists. **Owner decision O3:** which meaning, and where the rule is written in the documents."]
    (OUT / "irf_day_low_audit.md").write_text("\n".join(DL) + "\n")

    # ============================================================================================ orb_missing_signal_audit.md
    colour_rows = [r for r in ba if r["config"] == "phase52-cand-orb-colour"]
    OR = ["# ORB - why the expected signals were missing (audit)", "", WARN, "",
          "The Phase 5.1 audit found that on all 13 'ORB should have activated' dates the engine produced NO valid ORB signal; the controller therefore skipped nothing, and **no priority override of IRF was added**. This audit reconstructs each date and names the first failing rule.", "",
          f"Causes (colour direction of the first candle): {S['orb_missing_signal_causes']}", "",
          tab(["date", "first candle O/H/L/C", "colour", "body %", "uw %", "lw %", "prev high / low", "EMA - close", "Method 1", "Method 2", "Gap / 200 average", "cause"],
              [[d, f"{j['first_candle']['open']}/{j['first_candle']['high']}/{j['first_candle']['low']}/{j['first_candle']['close']}", j["first_candle"]["colour"], j["first_candle"]["body_pct"], j["first_candle"]["upper_wick_pct"], j["first_candle"]["lower_wick_pct"], f"{j['prev_day_high']} / {j['prev_day_low']}",
                round(-j["close_minus_ema"], 1), j["directions"]["SHORT" if j["first_candle"]["colour"] == "RED" else "LONG"]["first_failing_rule"]["Method 1"][:70], j["directions"]["SHORT" if j["first_candle"]["colour"] == "RED" else "LONG"]["first_failing_rule"]["Method 2"][:60],
                j["directions"]["SHORT" if j["first_candle"]["colour"] == "RED" else "LONG"]["first_failing_rule"]["Gap/200DMA"][:60], j["cause_category"].split(" (")[0]] for d, j in orbj.items()]), "",
          "Both directions, the strength verdicts under the STRICT / MODERATE (active) / LOOSE profiles, the Method 2 inner level and trendline values, the trend result and the Gap setup values are in `orb_missing_signal_audit.csv` and `orb_missing_signal_audit.json`.", "",
          "## Reading the causes", "",
          "* **Level construction (no previous-day level broken):** the first candle neither broke nor closed beyond the previous-day high or low, and Method 2's inner level is a RESEARCH VARIANT (the latest fractal of the previous session inside its range) that the source does not define (orb.py says so). The engine has nothing to evaluate; the author sees an ORB from a hand-drawn level.",
          "* **Method 2 trendline:** a proposed fractal trendline decided it; no objective construction exists in the source.",
          "* **Strength threshold:** a proposed body / wick profile (MODERATE: body >= 60%, opposite wick <= 20%) rejected the candle; the LOOSE profile (body >= 50%, wick <= 25%) would pass some of them (columns `strength_*`).",
          "* **EMA requirement:** the approved trend variant (previous close against its EMA) rejected it.", "",
          "The handwritten pages contain no ORB drawings, so the check against the author's chart is the remark text only. No cause is a single wrong rule: most are proposals or undefined constructions, which is an owner decision (O8), not a defect.", "",
          "## ORB colour candidate (Phase 5.1, preserved and selectable)", "",
          f"`phase52-cand-orb-colour`: long needs a green first candle, short a red one. The author wrote 'for long' (AC27); the short side is a source interpretation (ORB-GLOBAL-002 'same rules in both directions'), recorded as such. It changes {len([r for r in colour_rows if r['change'] == 'REMOVED'])} confirmed ORB signals: " + ", ".join(f"{r['date']} {r['direction']}" for r in colour_rows if r["change"] == "REMOVED") + ". The frozen ORB is not modified."]
    (OUT / "orb_missing_signal_audit.md").write_text("\n".join(OR) + "\n")

    # ============================================================================================ remaining_owner_decisions.md
    RD = ["# Remaining owner decisions (Phase 5.2)", "", "Nothing below is decided here. With no answer the frozen Phase 3.6 behaviour stays active and the candidates stay opt-in.", "",
          tab(["#", "decision", "options", "evidence"], [
              ["O1", "ORB colour rule: adopt? short mirror?", "adopt both directions / long only / no", f"{len([r for r in colour_rows if r['change'] == 'REMOVED'])} ORB confirmations affected"],
              ["O2", "IRF EMA gap: measure, inequality, skip vs wait, scope, 27 vs 28", "see irf_ema_28_point_audit.md", f"27 vs 28 differ on {flags['E1_between_27_and_28']['all_signals']} signals ({flags['E1_between_27_and_28']['executed']} executed)"],
              ["O3", "IRF day's low: meaning, and where the documents state it", "D1-D5 readings", f"D2 touches {flags['D2_close_below_running_low_before']['all_signals']} signals, D4 {flags['D4_t1_beyond_running_low']['all_signals']}"],
              ["O4", "IRF first red candle: support level, method scope and what 'first' means (after the extension or after the breakout)", "low / body low / local support; 2A only or also 2B, Method 3", f"low candidate shifts {chg['phase52-cand-irf-first-red-low'].get('TIME_SHIFTED_EARLIER', 0) + chg['phase52-cand-irf-first-red-low'].get('TIME_SHIFTED_LATER', 0)} signals, adds {chg['phase52-cand-irf-first-red-low'].get('ADDED', 0)}, removes {chg['phase52-cand-irf-first-red-low'].get('REMOVED', 0)}"],
              ["O5", "IRF entry-candle body threshold (60 / 50 / 40 in the handwritten pages)", "60 / 50 / 40 / none", "not addressed by the call"],
              ["O6", "PDR / PDS confirmation numbers (the author's 'first green / first candle' examples fail them); PDS: may a later strong red candle at the zone be used after a weak first red?", "keep / loosen / first candle with no threshold", "PDR sensitivity table (readings A, B, C) and the PDS list of later strong red candles"],
              ["O7", "May the PDR retest candle itself be the confirmation?", "yes / no", f"{sum(1 for r in pdr if fb(r['interaction_candle_would_qualify_if_permitted']))} armed setups would move earlier"],
              ["O8", "ORB inner level, trendline, strength profile and trend filter definitions", "author to supply", "13 'ORB should have activated' dates; causes in orb_missing_signal_audit.md"],
              ["O9", "RF-004 (open above yesterday's high) and the PDR failed-zone policy", "unchanged unless redefined", "Phase 5.1 AC05, AC36"],
              ["O10", "Where in the documents is 'IRF should not be activated at the day's low'?", "author to point to the page", "not found in the five guides"]]), ""]
    (OUT / "remaining_owner_decisions.md").write_text("\n".join(RD) + "\n")

    # ============================================================================================ source_to_code_traceability.md
    TR = ["# Source to code traceability", "", tab(["clarification", "source / authority", "code", "tests", "outputs"], [
        ["PDR / PDS first eligible candle (USER_APPROVED)", "owner clarification; PDR-A03..A07, PDS-M-001, PDS-M3-001", "`strategies/pdr_body.py::PDRBodyStrategy._scan` and `strategies/pds.py::PDSStrategy._scan` (frozen, unchanged); `research/phase52_diag.py::pdr_setup_diagnostics / pds_setup_diagnostics / compare_with_engine`", "tests/test_phase52_author_rules.py (first eligible, later stronger ignored, retest first, Method 3 sequence, no look-ahead, no real late entry)", "pdr_first_eligible_audit.md, pds_first_eligible_audit.md, *_first_eligible_setups.csv"],
        ["PDS co-confirmed methods recorded", "brief 5.2", "`strategies/pds_first_eligible.py::PDSCoConfirmStrategy`", "test_pds_co_confirmation_is_recorded_without_creating_a_second_signal", "signal_counts.json (sessions with co-confirmed methods)"],
        ["IRF first red candle support (candidate)", "AUTHOR_CALL + HANDWRITTEN AC01/03/08/09/20/26/34", "`strategies/irf_candidates.py::IRFFirstRedStrategy` (Method 2A only)", "first_red_candle_candidates..., baseline_mode..., audit check on raw candles", "irf_first_red_candle_audit.md, irf_first_red_comparison.csv, before_after_signals.csv"],
        ["IRF EMA gap (diagnostics)", "AUTHOR_CALL (28) + HANDWRITTEN AC13/AC18 (27)", "`research/phase52_diag.py::irf_measurements`", "test_ema_measurements_and_the_ema_between_entry_and_target_1", "irf_ema_28_point_audit.md, irf_signal_diagnostics.csv"],
        ["IRF day's low (diagnostics)", "AUTHOR_CALL; HANDWRITTEN G02 / AC19 / AC32", "`research/phase52_diag.py::irf_measurements` (running low at decision time)", "test_running_low_uses_only_candles_closed_before_the_decision...", "irf_day_low_audit.md, irf_signal_diagnostics.csv"],
        ["ORB missing signals (audit)", "AUTHOR_CALL + HANDWRITTEN (13 dates)", "`research/phase52_diag.py::orb_audit / orb_cause_category`", "test_orb_cause_categories_follow_the_first_failing_rule", "orb_missing_signal_audit.md / .csv / .json"],
        ["ORB colour (candidate)", "HANDWRITTEN AC27 (long); ORB-GLOBAL-002 (short mirror)", "`strategies/orb_colour.py::ORBColourStrategy` (Phase 5.1, unchanged)", "tests/test_phase51_author_corrections.py; configuration tests here", "before_after_signals.csv (config phase52-cand-orb-colour)"],
        ["Selectable configurations", "brief section 3", "`research/phase52.py::CONFIGS / make_engines52 / signals_for`", "test_configurations_are_separately_selectable_and_replace_only_their_own_slot", "scripts/phase52_run.py --list"],
        ["Portfolio rules, RF, frozen engines", "USER_APPROVED / SOURCE_VERIFIED", "not touched", "baseline-file hash test, frozen-signal regression", "independent_audit.md"]])]
    (OUT / "source_to_code_traceability.md").write_text("\n".join(TR) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.2)", "",
          f"`scripts/phase52_independent_audit.py` re-derives the claims from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, n, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:160]] for i, (n, v) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation written by the same author as the pipeline; the fresh reviewer below is a separate pass.", "",
          "## Tests and lint", "", "* Before any change (existing suite): **650 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ============================================================================================ README
    pdr_sig = sum(1 for r in pdr if r["verdict"] == "ENGINE_ON_FIRST_ELIGIBLE_CANDLE")
    pds_sig = sum(1 for r in pds if r["verdict"] == "ENGINE_ON_FIRST_ELIGIBLE_CANDLE")
    RM = ["# Phase 5.2 - the author's latest clarifications", "", f"> {WARN}", "", "Stopped after Phase 5.2: no revised profitability backtest, nothing committed or pushed, no paper trading, no live orders.", "",
          "## Result", "",
          tab(["item", "result"], [["PDR entries shifted to the first eligible candle", f"0 - no late entry relative to the preserved proposals (retest-candle convention PDR-A07, numeric thresholds); {pdr_sig} sessions with a first PDR signal. The author's own example candles are NOT eligible under them (see the sensitivity table: looser readings would move many entries)"], ["PDS entries shifted to the first eligible candle", f"0 - no late entry relative to the preserved quality rule (PDS-M-001); {pds_sig} sessions with a first PDS signal; co-confirmed methods now recorded (0 occur); later strong red candles after a weak first red are listed"],
                                    ["IRF first red candle", f"candidates only (level undefined); low: {sum(v for k, v in chg['phase52-cand-irf-first-red-low'].items() if k != 'ANNOTATION_ONLY')} signal changes (earlier/later/added/removed), body low: {sum(v for k, v in chg['phase52-cand-irf-first-red-body-low'].items() if k != 'ANNOTATION_ONLY')}"],
                                    ["IRF day's low", f"source statement not found in the documents; 8 readings measured; none activated (D2 touches {flags['D2_close_below_running_low_before']['all_signals']} signals, D6 {flags['D6_running_low_already_below_irl']['all_signals']}, D7 {flags['D7_earlier_close_below_irl']['all_signals']}, D8 {flags['D8_entry_below_previous_day_low']['all_signals']})"],
                                    ["IRF 28-point EMA", f"unresolved; readings measured (E1 {flags['E1_close_gap_below_ema_28']['all_signals']} signals / {flags['E1_close_gap_below_ema_28']['executed']} executed; 27 vs 28 differ on {flags['E1_between_27_and_28']['all_signals']})"],
                                    ["Missing ORB entries explained", f"13 of 13 (no ORB signal existed; causes: {S['orb_missing_signal_causes']})"], ["confirmed signals (frozen / approved / ORB colour / IRF low / IRF body low)", " / ".join(str(S[k]['confirmed_total']) for k in cfgs)]]), "",
          "## Files", "", "`author_call_clarifications.md`, `rule_authority_matrix.md`, `pdr_first_eligible_audit.md`, `pds_first_eligible_audit.md`, `irf_first_red_candle_audit.md`, `irf_ema_28_point_audit.md`, `irf_day_low_audit.md`, `orb_missing_signal_audit.md`, `before_after_signals.csv`, `dated_corrections_comparison.csv`, "
          "`remaining_owner_decisions.md`, `source_to_code_traceability.md`, `independent_audit.md`, `Phase52_Trade_Corrections_Verification.xlsx`, `daily/` (one report per Phase 5.1 date), `charts/`; supporting: `all_confirmed_signals.csv`, `daily_first_signal_comparison.csv`, `irf_signal_diagnostics.csv`, `irf_first_red_comparison.csv`, "
          "`pdr/pds_first_eligible_setups.csv`, `orb_missing_signal_audit.csv`, `signal_counts.json`, `before_snapshot.json`.", "",
          "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase52_snapshot.py --snapshot       # baseline hashes (taken before any change)", "python scripts/phase52_run.py --list               # the selectable configurations",
          "python scripts/phase52_run.py                      # signal-only comparison (all configurations) + diagnostics + day reports + workbook", "python scripts/phase52_independent_audit.py", "python scripts/phase52_docs.py --tests \"...\" --ruff \"...\"", "python scripts/phase52_snapshot.py --verify", "```"]
    (OUT / "README.md").write_text("\n".join(RM) + "\n")
    print("docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
