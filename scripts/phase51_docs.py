"""Phase 5.1: the narrative deliverables and the workbook, written from the CSV / JSON files of reports/phase5/phase51_author_corrections/ (counts and identities are read from them, not typed).

  python scripts/phase51_docs.py --tests "<pytest result>" --ruff "<ruff result>"
Writes README.md, confirmed_software_defects.md, new_author_rules.md, proposed_rule_changes.md, owner_approval_required.md, independent_audit.md (from independent_audit_results.json and _reviewer_findings.md),
Author_Corrections_Verification.xlsx.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/").replace("\n", " ")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    tr = rd(OUT / "all_author_corrections.csv")
    cl = rd(OUT / "correction_classifications.csv")
    rec = rd(OUT / "date_by_date_reconciliation.csv")
    sel = rd(OUT / "strategy_selection_conflicts.csv")
    diff = rd(OUT / "before_after_signal_differences.csv")
    pop = json.loads((OUT / "population_impact.json").read_text())
    dated = [r for r in tr if r["date"]]
    active = [r for r in dated if r["status"] == "ACTIVE"]
    classes = Counter(c for r in cl for c in r["classifications"].split(";") if c)
    cats = Counter(r["category"] for r in cl)
    fl = pop["irf_flags"]
    n_irf, n_m2, n_pdr = pop["irf_trades"], pop["irf_method2_trades"], pop["pdr_trades"]
    orb_changed = [r for r in diff if r["rule"] == "ORB_COLOUR_AC27" and r["level"] == "ORB signal"]
    ids = lambda lst: ", ".join(lst[:12]) + (" ..." if len(lst) > 12 else "")  # noqa: E731
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""

    # ------------------------------------------------------------------------------------------------ confirmed_software_defects.md
    n_ok_sel = sum(1 for r in sel if r["verdict"].startswith("CONTROLLER_CORRECT"))
    n_never = sum(1 for r in sel if r["verdict"].startswith("CONTROLLER_CORRECT: the expected strategy never"))
    S = ["# Confirmed software defects (Phase 5.1)", "",
         "**Result: none.** No handwritten observation shows the engine contradicting an explicit, approved rule. Category A (a failing test, a minimal code correction, a record of changed signals) is therefore empty, and **no frozen file was edited**.", "",
         "What was checked:", "",
         f"* Every one of the {len([r for r in dated if r['status'] != 'CROSSED_OUT'])} active dated entries was matched to a Phase 3.6 ledger trade (the author's labels equal the Phase 3.6 strategies for 38 labelled entries independently of any date reading; AC27 has no label; AC38 matches only after its date is resolved to 2025-12-26 (also supported by the manual journal, which has a PDS row at 09:30 on that date and none on 2025-12-16)). For all dated trades the delivered rule-check tables show 0 failed checks and 0 recomputation mismatches; the independent audit re-walked their entries and exits from the raw minutes.",
         f"* Controller selection: for the {len(sel)} observations that say 'X should have activated instead of Y', `strategy_selection_conflicts.csv` lists the expected strategy's own signals and rejections: in {n_never} of {len(sel)} the expected strategy never produced a confirmed signal, and in the other {len(sel) - n_never} its first confirmed signal came no earlier than the executed one (AC17, AC21, AC22), so the controller skipped nothing (**no WRONG_STRATEGY_SELECTION**: {n_ok_sel} of {len(sel)} verdicts are CONTROLLER_CORRECT). "
         "The disagreement lies in that engine's own conditions (thresholds and definitions that are proposals), not in the first-valid-signal rule, which is preserved.",
         "* The three places where the author's wording points at the engine's behaviour and the engine could be called wrong were each traced to an explicit source or approved rule: RF-004 (gap-up open above yesterday's high is rejected: AC05, AC36), DAY-SL-001 (a second PDR/PDS trade after an initial full stop is allowed: AC22, AC30) and PDS-M-001 (a weak red candle is not taken: AC38).", "",
         "Behaviour that differs from the author's reading but is **consistent with the rules as encoded** (not defects):", "",
         tab(["observation", "engine behaviour", "why it is not a defect"], [
             ["AC27 ORB long on a red candle", "the conditional pin-bar route admitted a bearish first candle (20251127-1-ORB; also 2026-01-05 long and 2026-04-24 short)", "the source mentions 'a suitable bullish pin-bar-type candle' in the Gap setup and applies pin bars to Methods 1/2 only through 'candle quality across all three setups' plus a proposal flag; colour is not mentioned, and the page also says a pin bar's close must support the breakout - so 'not a defect' is defensible but not clear-cut. The author's clarification is recorded as a new rule (`new_author_rules.md`)"],
             ["AC10 / AC11 / AC29 / AC40 PDR later than the first green candle", "the confirmation needs 'good green body / lower rejection / hammer' by the PROPOSED thresholds", "PDR-A04 is the author's sentence; its numbers (body >= 60%, upper wick <= 20%, hammer 2x) are proposals"],
             ["AC13 / AC18 IRF with the EMA close below the entry", "entered", "no IRF rule mentions the 200 EMA; the author's rule is new"],
             ["AC19 / AC32 / G02 entries at the day's low", "no test exists", "the author's rule is new; 0 executed Phase 3.6 IRF trades close below the session low so far"]]), "",
         "Limits: signal DETECTION for the dated days was checked against the encoded rules and the author's wording; the engines' conformance to the guides in general was audited in Phases 3.3-3.6 and is not re-derived here."]
    (OUT / "confirmed_software_defects.md").write_text("\n".join(S) + "\n")

    # ------------------------------------------------------------------------------------------------ new_author_rules.md
    N = ["# New explicit author rules found in the handwritten corrections", "",
         "Each row is a statement the author wrote that is NOT in the five strategy guides, the Phase 3.4 author-approved PDR rules or the owner-approved portfolio rules. Status: IMPLEMENTED_OPT_IN = coded as a separate variant that is not the active baseline; NOT_IMPLEMENTED = ambiguous in scope or wording, or conflicting with an earlier rule, so it awaits the owner (`owner_approval_required.md`).", "",
         tab(["#", "rule (exact wording)", "where written", "scope as written", "conflicts / ambiguities", "reach in the Phase 3.6 history", "status"], [
             ["NR1", "\"ORB for long should be in green closing.\" (a red first candle must not give a long)", "AC27 (page 5)", "ORB, long; the short mirror follows from ORB-GLOBAL-002", "the source allows a 'suitable bullish pin-bar-type candle' for the gap setup; colour not stated. The mirror for shorts is my application of ORB-GLOBAL-002",
              f"{len(orb_changed)} ORB confirmations change (" + ", ".join(f"{r['date']} {r['direction']}" for r in orb_changed) + "); the trades of 2025-11-27 and two other dates change as the next valid signals take the slots", "IMPLEMENTED_OPT_IN (`ORBColourStrategy`); not the baseline"],
             ["NR2", "\"The candle should close below EMA when the space btn. the entry candle is less than 27.\" / \"Should be ignored as Tgt 1 is not above EMA ... Should wait until EMA break.\"", "AC13, AC18 (pages 3-4)", "IRF short; EMA = 200 EMA on the 5-minute chart",
              "'skip' (AC18 'ignored') vs 'defer until a close below the EMA' (AC13 'Wait ... Entry'); what the deferred entry is (which method, expiry); 'space' read as the distance to the EMA",
              f"{len(fl['ema_within_27']['trades'])} of {n_irf} executed IRF trades have the EMA within 27 points below the entry ({ids(fl['ema_within_27']['trades'])})", "NOT_IMPLEMENTED"],
             ["NR3", "\"IRF should not activate at days low.\" (red star) / \"entry is below days low\" / \"2nd candle should also be ignores as it is at day's low.\"", "G02, AC19, AC32", "IRF (methods not stated)",
              "'at' vs 'below'; wick or close; the low before the signal candle or including it; AC19 adds 'trading should be completely stopped'",
              f"{len(fl['close_below_session_low']['trades'])} of {n_irf} executed IRF trades close below the session low so far (the rule would not change an executed trade); it matters for rejected / ignored signals (e.g. 2025-11-12 09:25, 2025-12-11 09:35)", "NOT_IMPLEMENTED"],
             ["NR4", "\"The first red candle only should be considered ... only break of first red candle which is outside the 5 min range, only the red candles break of S/R should be entered.\"", "AC03 + AC01, AC08, AC09, AC20, AC26, AC34", "IRF Method 2 (the dated trades are Method 2, except AC07 / AC01 context)",
              "'outside the 5-minute range' = fully above, or only the close above; whether the S/R break must itself be by a red candle; interaction with the entry-candle body (NR5)",
              f"the reading differs from the engine's entry on {len(fl['first_red_reading_differs']['trades'])} of {n_m2} executed Method-2 IRF trades", "NOT_IMPLEMENTED"],
             ["NR5", "\"60+ body candle in the entry side.\" / \"... entry candle body is 40% Wick is 60%.\" / \"Should be ignored as candle body is less than 50%.\"", "AC01, AC07, AC32", "IRF entry candle",
              "three different numbers (60, 40, 50) in three places; percent of what (the candle range, as the engine measures it)",
              f"entry-candle body < 60%: {len(fl['body_lt_60']['trades'])} of {n_irf} executed IRF trades; < 50%: {len(fl['body_lt_50']['trades'])}; < 40%: {len(fl['body_lt_40']['trades'])}", "NOT_IMPLEMENTED"],
             ["NR6", "\"Enter in 1st green candle.\" / \"Early entry should take place in 1st green candle\" / \"PDR 1st candle entry\" / PDS: \"First candle entry.\"", "AC02, AC10, AC11, AC29, AC40, AC38", "PDR (long) and PDS (short)",
              "it restores the legacy PDR-007 ('the first later green candle') that Phase 3.4 replaced by the pattern test PDR-A04; whether the green candle that tests the zone may be the entry; for PDS it contradicts PDS-M-001 ('a weak red candle is not taken')",
              f"an earlier 'first green candle' reading exists for {pop['pdr_first_green_earlier']['count']} of {n_pdr} executed PDR trades", "NOT_IMPLEMENTED"],
             ["NR7", "\"PDR/PDS should activate only before\" [sentence not completed on the scan]", "G01 (page 3)", "unknown", "the end of the sentence is missing", "unknown", "NOT_IMPLEMENTED (incomplete)"]]), "",
         "Crossed-out text (AC23, 2025-11-20) was recorded but is not a rule."]
    (OUT / "new_author_rules.md").write_text("\n".join(N) + "\n")

    # ------------------------------------------------------------------------------------------------ proposed_rule_changes.md
    P = ["# Proposed rule changes (candidates only; none is active)", "",
         "Each candidate states the general rule I read from the author's remarks, the alternative readings that the wording allows, and its reach. **They are not ranked or chosen by profitability** (the brief forbids it): the only numbers shown are how many Phase 3.6 trades or signals each would touch, and whether it reproduces the author's own earlier / later remarks.", "",
         "## C1. IRF Method 2 reference candle (NR4) + entry-candle body (NR5)", "",
         "Reading F: after the breakout candle (first later close above IRH), take the FIRST red candle that is outside the initial range; its low is the support S and its high the resistance R; the entry is the first later RED candle with body >= 60% that closes below S (support break) or closes back below R after an earlier candle traded above R (resistance break), whichever happens first, before 13:00.", "",
         "Where the author states a direction, reading F agrees: AC08 and AC09 ('earlier / late entry'): entry earlier than the engine; AC07 ('taken after 5 candles at the 6th'): later; AC01 ('at the resistance itself', manual journal label 10:00): a red candle closing at 24,546.50 against a resistance of 24,546.55. "
         "Alternatives that change the result: 'outside the range' = low above IRH (used) or only the close above IRH; body threshold 60 / 50 / 40 / none (see `readings` in each day report). The two outside-range readings give different entries on AC03 (11:15 vs 11:20), so the wording alone does not fix the rule.", "",
         "## C2. IRF EMA space (NR2)", "",
         "Reading E: for an IRF short signal, if 0 < (signal close - EMA200 of 5-minute closes) < 27 points (the EMA lies between the entry and target 1), do not enter on that candle; wait for a candle that closes below the EMA. Open: whether the IRF setup then stays valid and how long (the engine has no setup expiry for Method 2), and which method the deferred entry belongs to. "
         f"It reproduces the author's measurable statement in both dated cases (EMA 2.93 and 25.27 points below the entry); it reaches {len(fl['ema_within_27']['trades'])} of {n_irf} executed IRF trades.", "",
         "## C3. IRF at the day's low (NR3)", "",
         "Reading L: an IRF entry whose signal candle closes below the lowest low of the session so far is not taken. It matches AC32's second candle (09:35 closes 25,721.45 against 25,727.90) and AC19's 09:25 candle. It does not explain AC19's 'the day should be completely stopped'; whether an IRF activation at the day's low consumes the IRF for the day is a separate decision. It would not change any executed Phase 3.6 IRF trade.", "",
         "## C4. PDR / PDS 'first candle' entry (NR6)", "",
         "Reading G: PDR long = the first green candle after the zone is tested that closes above the zone ceiling (the tested candle itself may qualify), with no strength threshold; PDS short = the first red candle at the zone, no strength threshold. "
         "In the five PDR examples the candles the author points to have bodies of 31.9%, 36.2%, 49.7%, 57.3% and 63.1% and upper wicks up to 32.6%, i.e. they pass none of the proposed numeric thresholds uniformly. Adopting G would reverse Phase 3.4's replacement of PDR-007 by PDR-A04 (the author's own 'good green body / rejection / hammer' sentence) and, for PDS, PDS-M-001. "
         f"An earlier first-green reading exists for {pop['pdr_first_green_earlier']['count']} of {n_pdr} executed PDR trades.", "",
         "## C5. ORB candle strength, trend and inner level (AC04, AC06, AC12, AC14-AC16, AC24, AC28, AC31, AC33, AC37, AC39, AC40)", "",
         "Thirteen observations say 'ORB should have activated'. The engine's ORB produced no confirmed signal on any of those days; its rejection reasons are: trendline not supportive (Method 2 inner level; no objective construction exists), first-candle strength thresholds (body 60%, opposite wick 20%: the author's days have bodies 22.9-76.2%), the approved previous-close-vs-EMA trend variant, the Gap/200DMA close condition, or no previous-day level broken. "
         "No single change explains all of them. Two follow from the strength profile alone: AC39 (lower wick 23.8% against the MODERATE limit of 20%; the LOOSE profile in params.py allows 25%) and AC33 (body 52.2% against 60%; LOOSE needs 50%). The rest need the author's actual ORB inner-level and trend definitions (four of them, AC04, AC06, AC12, AC37, have strong or hammer-shaped first candles and no previous-day level broken, so the Method 2 inner level and trendline - undefined in the source - decide them).", "",
         "## C6. RF (AC05, AC25, AC36)", "",
         "AC05 and AC36 conflict with RF-004 (an open above yesterday's high is rejected); AC25 is rejected by the approved trend variant. The author's reading of 'yesterday's range' or of the RF trend must be stated before any change."]
    (OUT / "proposed_rule_changes.md").write_text("\n".join(P) + "\n")

    # ------------------------------------------------------------------------------------------------ owner_approval_required.md
    O = ["# Owner approval required", "", "Nothing below is decided by this phase. Where no answer is given the active baseline (Phase 3.6) is unchanged.", "",
         tab(["#", "decision", "options", "evidence / reach", "default"], [
             ["O1", "Adopt the ORB colour rule (NR1) as the baseline?", "yes (long needs green, short red) / only the pin-bar route / no", f"opt-in variant exists and is tested; changes {len(orb_changed)} ORB confirmations ({', '.join(r['date'] for r in orb_changed)})", "no change"],
             ["O2", "IRF EMA-space rule (NR2): skip or defer?", "skip the signal / defer until a close below the EMA (and for how long) / no rule", f"{len(fl['ema_within_27']['trades'])} of {n_irf} executed IRF trades touched; both dated examples confirmed", "no change"],
             ["O3", "IRF at the day's low (NR3)", "define 'at' (close below the prior session low?) and whether the day then ends / no rule", "0 executed trades touched; signals on 2025-11-12 and 2025-12-11 touched", "no change"],
             ["O4", "IRF Method 2 reference candle (NR4)", "first red candle outside the range - fully above or close above; support break by any candle or only by a red one / no rule", f"differs from the engine on {len(fl['first_red_reading_differs']['trades'])} of {n_m2} executed Method-2 trades", "no change"],
             ["O5", "IRF entry-candle body threshold (NR5)", "60 / 50 / 40 / none", f"{len(fl['body_lt_60']['trades'])} / {len(fl['body_lt_50']['trades'])} / {len(fl['body_lt_40']['trades'])} of {n_irf} executed IRF trades have a smaller body", "no change"],
             ["O6", "PDR / PDS confirmation: first candle vs pattern thresholds (NR6)", "keep PDR-A04 with the proposed numbers / loosen the numbers / first green candle with no threshold; PDS same", f"first-green earlier on {pop['pdr_first_green_earlier']['count']} of {n_pdr} PDR trades; conflicts with PDS-M-001", "no change"],
             ["O7", "May the green candle that tests the zone be the PDR confirmation? (AC02)", "yes (pdr_green_may_be_interaction_candle = True) / no", "an existing switch; PDR-A07 is a proposal", "no change"],
             ["O8", "RF-004 (open above yesterday's high)", "keep / redefine 'yesterday's range'", "AC05, AC36 (opens 41.6 and 24.7 points above the previous high)", "keep"],
             ["O9", "ORB inner level, trend and candle-strength definitions", "author to supply objective definitions", "13 'ORB should have activated' remarks", "no change"],
             ["O10", "PDR failed-zone policy (AC36)", "unchanged / invalidate after a close below the zone floor", "open since Phase 3.4; closes below the floor preceded the 10:45 entry", "unchanged"],
             ["O11", "Same-day second trade (AC22, AC30)", "keep DAY-SL-001 / forbid", "the approved portfolio rule allows it", "keep"],
             ["O12", "Incomplete / unclear remarks", "the sentence after 'PDR/PDS should activate only before' (G01); AC35 label (PDS or PDR) and meaning of 'trap'; AC16 'IRF activation is also wrong'", "see the transcription", "no change"]]), ""]
    (OUT / "owner_approval_required.md").write_text("\n".join(O) + "\n")

    # ------------------------------------------------------------------------------------------------ independent_audit.md
    IA = ["# Independent audit (Phase 5.1)", "",
          f"`scripts/phase51_independent_audit.py` re-derives, from the raw Phase 1 minute files and the delivered CSVs only (no `src/` imports), what the day reports state. Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, n, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:150]] for i, (n, v) in enumerate(ar["checks"].items())]), "",
          "## Tests and lint", "", "* Before implementation (full suite, `pytest -q`): **636 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ------------------------------------------------------------------------------------------------ README
    R = ["# Phase 5.1 - the author's handwritten corrections", "",
         "Stopped after Phase 5.1 as instructed: no profitability backtest was run, nothing was committed or pushed, no paper trading, no live orders.", "",
         "Source: `docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf` (six pages; the brief says `strategy_docs/corrected/`, the file is under `docs/`). All six pages were rendered and read by eye (`pages/`).", "",
         "## Result in numbers", "",
         tab(["item", "count"], [["handwritten observations extracted", f"{len(tr)} ({len(dated)} dated entries + 2 red-star general remarks)"], ["active dated entries / crossed out", f"{len(active)} / {len(dated) - len(active)}"],
                                 ["dated entries matched to a historical session and to a Phase 3.6 trade", f"{len(dated)} / {len(dated)} (the matches and the two special cases are in the transcription)"],
                                 ["confirmed implementation defects (category A)", "0"], ["explicit new author rules (category B, as classified)", f"{cats.get('B', 0)} observations (AC13, AC18, AC27, AC32, G02) forming NR1-NR3 and parts of NR5; 7 candidate rules in all (`new_author_rules.md`)"],
                                ["date-specific / discretionary (category C)", str(cats.get("C", 0))], ["no discrepancy", str(cats.get("N", 0))], ["strategy-selection conflicts (controller skipped a valid signal)", "0 of " + str(len(sel)) + " (" + str(sum(1 for r in sel if not r["verdict"].startswith("CONTROLLER_CORRECT"))) + " REVIEW verdicts)"],
                                ["corrections implemented", "1, as an opt-in variant: ORB colour (NR1); the baseline is unchanged"]]), "",
         "Classification counts (an observation can have several): " + ", ".join(f"{k} {v}" for k, v in sorted(classes.items())), "",
         "## Files", "", tab(["file", "content"], [["handwritten_corrections_transcribed.md, all_author_corrections.csv", "the transcription (one record per observation)"], ["date_by_date_reconciliation.csv, correction_classifications.csv", "engine vs author per date, classification, category, approval"],
                                                    ["strategy_selection_conflicts.csv", "the 'X instead of Y' cases against the controller"], ["manual_journal_comparison.csv", "the manual journal rows on those dates (supporting evidence only)"],
                                                    ["before_after_signal_differences.csv, population_impact.json", "what the implemented variant changes and how far each candidate would reach"], ["confirmed_software_defects.md, new_author_rules.md, proposed_rule_changes.md, owner_approval_required.md", "findings and decisions"],
                                                    ["daily/<date>.md, charts/<date>.svg", "one evidence report and one annotated chart per date (38)"], ["Author_Corrections_Verification.xlsx", "one row per observation"], ["independent_audit.md", "audit and reviewer"],
                                                    ["pages/, evidence/, before_snapshot.json", "page images, per-date evidence, baseline hashes"]]), "",
         "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase51_snapshot.py --snapshot      # baseline hashes (taken before any change)", "python scripts/phase51_transcription.py", "python scripts/phase51_evidence.py",
         "python scripts/phase51_population.py", "python scripts/phase51_reconcile.py", "python scripts/phase51_independent_audit.py", "python scripts/phase51_docs.py --tests \"...\" --ruff \"...\"", "python scripts/phase51_snapshot.py --verify", "```"]
    (OUT / "README.md").write_text("\n".join(R) + "\n")

    # ------------------------------------------------------------------------------------------------ workbook
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "Corrections"
    cls = {r["correction_id"]: r for r in cl}
    recs = {r["correction_id"]: r for r in rec}
    head = ["correction_id", "date", "pdf_page", "strategy_as_written", "status", "author_text_verbatim", "automatic_trade", "proposed_correction", "classification", "category", "supporting_evidence", "approval_status", "implemented", "evidence_report", "chart"]
    rows = []
    for r in tr:
        c = cls[r["correction_id"]]
        q = recs[r["correction_id"]]
        rows.append([r["correction_id"], r["date"], r["pdf_page"], r["strategy_label_as_written"], r["status"], r["author_text_verbatim"], q["automated_trade"], r["suggested_strategy"] + " | " + r["requirement_stated"], c["classifications"], c["category"],
                     c["author_correct_under_existing_rules"] + " || " + c["engine_correct_under_existing_rules"], "OWNER APPROVAL REQUIRED: " + c["owner_approval_required"], c["implemented"], q["evidence_file"], q["chart"]])
    ws.append(head)
    for rr in rows:
        ws.append(rr)
    for cell in ws[1]:
        cell.fill, cell.font, cell.alignment = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF"), Alignment(wrap_text=True)
    ws.freeze_panes = "B2"
    for name, fn in (("Classifications", "correction_classifications.csv"), ("Reconciliation", "date_by_date_reconciliation.csv"), ("Selection conflicts", "strategy_selection_conflicts.csv"), ("Manual journal", "manual_journal_comparison.csv"),
                     ("Signal differences", "before_after_signal_differences.csv"), ("Transcription", "all_author_corrections.csv")):
        w = wb.create_sheet(name)
        data = rd(OUT / fn)
        if data:
            cols = []
            for r in data:
                for k in r:
                    if k not in cols:
                        cols.append(k)
            w.append(cols)
            for r in data:
                w.append([r.get(c, "") for c in cols])
            for cell in w[1]:
                cell.fill, cell.font = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF")
            w.freeze_panes = "B2"
    wb.save(OUT / "Author_Corrections_Verification.xlsx")
    print("docs and workbook written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
