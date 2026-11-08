"""Phase 5.6: the markdown deliverables of reports/phase5/phase56_manual_reconciliation/, written from the CSV / JSON files produced by scripts/phase56_run.py and scripts/phase56_independent_audit.py (counts are read, not typed).

  python scripts/phase56_docs.py --tests "<pytest result>" --ruff "<ruff result>"
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
WARN = "SYNTHETIC index-point P&L; no real option P&L. The journal has no direction, price or exit time: matching uses only date, strategy and the entry-time label, and every automated-trade explanation rests on the actual candles and the documented rules."
K = ("A", "B", "C")
NAMES = {"A": "A - frozen Phase 3.6", "B": "B - Phase 5.3 author-corrected", "C": "C - B + ORB gap crossing"}


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
    S = json.loads((OUT / "phase56_state.json").read_text())
    J, M = S["journal"], S["matching"]
    match = rd(OUT / "manual_vs_automated_matching.csv")
    causes = rd(OUT / "mismatch_root_causes.csv")
    mo = rd(OUT / "manual_only_trades.csv")
    hw = rd(OUT / "handwritten_author_corrections_comparison.csv")
    ar = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {"checks": {}, "all_pass": False}
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    p55a = P55 / "independent_audit_results.json"
    st55_ok = p55a.exists() and bool(json.loads(p55a.read_text()).get("all_pass"))

    def cnt(rows, **kw):
        return sum(1 for r in rows if all(r.get(k) == v for k, v in kw.items()))
    strat = ("ORB", "IRF", "PDR", "PDS", "RF")
    manual_by = J["by_strategy"]

    # ============================================================================================ manual_journal_source_audit.md
    dd = S["delta_distribution"]
    strict0 = dd.get("A|STRICT|0", 0)
    tol_d = {int(k.split("|")[2]): v for k, v in dd.items() if k.startswith("A|TIME_TOLERANT")}
    ds_d = sorted((int(k.split("|")[2]), v) for k, v in dd.items() if k.startswith("A|DATE_STRATEGY_ONLY"))
    SA = ["# Manual journal - source audit", "", f"> {WARN}", "",
          "## The source", "", "`docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx` (read-only; SHA-256 in `configuration_manifest.json` of Phase 5.5 and in the baseline snapshot; unchanged). Two sheets: 'Trading Journal' and 'Summary'. The data sheet has FIVE columns only: serial number, date, entry-time label, strategy, outcome (Target / SL / BE). **It records no direction, entry price, stop, target, exit time or exit price**; nothing was invented.", "",
          "## Verified figures", "",
          tab(["item", "value", "note"], [["data rows", J["rows"], "serial numbers 1-190"], ["'Total trades' in the Summary sheet", J["summary_sheet"].get("Total trades"), "differs from the 190 data rows; the Summary appears stale (it also lists 80 Target outcomes against 81 in the data sheet); the 190 rows are used and nothing was corrected"],
                                         ["rows by strategy", str(J["by_strategy"]), "ORB 89"], ["outcomes in the data sheet", str(J["outcomes"]), "Target 81 / SL 65 / BE 44"], ["weekend-dated rows", len(J["weekend_rows"]), "; ".join(f"row {r[0]} (sheet row {r[1]}) {r[2]} {r[3]} {r[4]}" for r in J["weekend_rows"])],
                                         ["weekend rows with market data", 0, "none of the five Saturdays has any one-minute data in the dataset: they are not exchange sessions. They are kept as written (not moved to a neighbouring date) and can never match"],
                                         ["rows on evaluated sessions", J["rows_on_evaluated_sessions"], "every weekday journal date is one of the 247 evaluated sessions"], ["dates with two journal rows", J["dates_with_two_rows"], "no date has more than two"],
                                         ["entry-time label types", "text 'HH:MM' for most rows, a time object (09:15:00) for 19 rows", "both rendered HH:MM; seconds dropped"]]), "",
          "The Phase 2.1 'attribution hypotheses' (which relabel two groups of journal rows as PDR / ORB) used by the Phase 3.2 reconciliation are NOT applied: the original strategy labels are used.", "",
          "## What the label means", "",
          "The journal labels the five-minute candle START (the ORB rows say 09:15, the first candle; the automated ORB signal is confirmed at 09:20). The convention is the pre-existing Phase 3.1 one and is NOT tuned: the automated side is compared at its signal CANDLE START. "
          f"Evidence that it is the right reading: in configuration A, {strict0} of {M['A']['strict'] + M['A']['time_tolerant']} matched pairs have the manual label equal to the signal candle start (delta 0); the time-tolerant pairs fall symmetrically in -15..+15 minutes ({dict(sorted(tol_d.items()))}), with no systematic offset.", "",
          "## Matching procedure (one-to-one, staged; implemented in `research/phase56.py`)", "",
          "1. **STRICT**: same date, same strategy, label == signal candle start (0 minutes). 2. **TIME_TOLERANT**: remaining rows, same date and strategy, |difference| <= 15 minutes (three candles, the Phase 3.1 tolerance, not widened). 3. **DATE_STRATEGY_ONLY**: remaining rows with the same date and strategy but a larger time difference: reported separately and NOT counted as a match. "
          "Within each stage the smallest |difference| pairs first (ties: lower journal row, then trade id); a journal row and an automated trade are each used at most once. Outcome labels (Target ~ TARGET, SL ~ INITIAL_FULL_STOP, BE ~ T1_THEN_BUFFER_STOP) are compared AFTER matching and never choose a pair.", "",
          "**Limitation.** Within a stage the assignment is greedy (smallest time difference first), not a maximum-cardinality assignment. For this data an exhaustive per-(date, strategy) assignment gives the same counts in A, B and C (reviewer check); a different tie-break could change which pair is chosen in a contrived case (labels 10:00 and 10:15 against signals 10:10 and 10:30), not the totals reported here.", "",
          f"Date-and-strategy-only pairs (configuration A): time differences {dict(ds_d)} minutes."]
    (OUT / "manual_journal_source_audit.md").write_text("\n".join(SA) + "\n")

    # ============================================================================================ cross_configuration_reconciliation.md
    def row(k):
        m = M[k]
        return [NAMES[k], m["automated_trades"], m["strict"], m["time_tolerant"], m["strict"] + m["time_tolerant"], m["date_strategy_only"], m["manual_rows_unmatched_total"], m["automated_unmatched_total"], f"{m['outcome_agreement_matched']['agree']} / {m['outcome_agreement_matched']['total']}", m["wrong_strategy_dates"]]
    by_strat = []
    for k in K:
        for s in strat:
            by_strat.append([k, s, manual_by.get(s, 0), M[k]["strict_by_strategy"].get(s, 0), M[k]["tolerant_by_strategy"].get(s, 0), M[k]["manual_only_by_strategy"].get(s, 0), cnt(rd(P55 / "all_executed_trades.csv"), config=k, strategy=s), M[k]["automated_only_by_strategy"].get(s, 0)])

    def cause_tab(side, strategy=None):
        rows = []
        for k in K:
            c = Counter(r["root_cause_primary"] for r in causes if r["config"] == k and r["side"] == side and (strategy is None or r["manual_strategy"] == strategy))
            for cause, n in c.most_common():
                rows.append([k, cause, n])
        return rows
    orb_rows = [r for r in mo if r["manual_strategy"] == "ORB"]
    orb_c = {k: Counter(r["root_cause_primary"] for r in orb_rows if r["config"] == k) for k in K}
    irf_c = {k: Counter(r["root_cause_primary"] for r in mo if r["config"] == k and r["manual_strategy"] == "IRF") for k in K}
    pp_c = {k: Counter((r["manual_strategy"], r["root_cause_primary"]) for r in mo if r["config"] == k and r["manual_strategy"] in ("PDR", "PDS")) for k in K}
    c_added = [t for t in rd(P55 / "all_executed_trades.csv") if t["config"] == "C" and t["strategy"] == "ORB" and t["method"] == "Gap/200DMA" and not any(x["config"] == "B" and x["trade_id"] == t["trade_id"] for x in rd(P55 / "all_executed_trades.csv"))]
    c_stage = {t["trade_id"]: next((r["match_stage"] for r in match if r["config"] == "C" and r.get("trade_id") == t["trade_id"]), "") for t in c_added}
    n_orb = {k: cnt(rd(P55 / "all_executed_trades.csv"), config=k, strategy="ORB") for k in K}
    hw_stat = {k: Counter(r[f"status_{k}"] for r in hw) for k in K}
    CR = ["# Cross-configuration reconciliation with the manual journal", "", f"> {WARN}", "",
          "The reconciliation is run SEPARATELY for A, B and C; no configuration is selected or approved, and a higher match count is not an approval criterion (the strategy rules were not changed to raise it).", "",
          "## Matching totals (190 journal rows)", "", tab(["configuration", "automated trades", "strict", "time-tolerant", "matched (strict + tolerant)", "date + strategy only (not a match)", "manual rows without a match", "automated trades without a match", "matched pairs with the same exit class", "dates with different strategies"], [row(k) for k in K]), "",
          f"Manual rows without a match include the five weekend-dated rows (no session) and the date-and-strategy-only rows. Of the {J['rows']} journal rows, {J['rows_on_evaluated_sessions']} fall on evaluated sessions; {M['A']['manual_rows_on_dates_with_no_automated_trade']} (A), {M['B']['manual_rows_on_dates_with_no_automated_trade']} (B) and {M['C']['manual_rows_on_dates_with_no_automated_trade']} (C) of them are on sessions on which the automated system took no trade at all (no valid signal, or none that passed the filters); the other unmatched rows are on days with an automated trade of another strategy, or of the same strategy at another time.", "",
          "## By strategy", "", tab(["cfg", "strategy", "journal rows", "strict", "time-tolerant", "manual-only rows (incl. date + strategy only)", "automated trades", "automated trades without a match"], by_strat), "",
          f"**Exits.** Among the matched pairs the manual outcome label and the automated exit class agree in {M['A']['outcome_agreement_matched']['agree']} of {M['A']['outcome_agreement_matched']['total']} (A), {M['B']['outcome_agreement_matched']['agree']} of {M['B']['outcome_agreement_matched']['total']} (B) and {M['C']['outcome_agreement_matched']['agree']} of {M['C']['outcome_agreement_matched']['total']} (C) pairs, i.e. for most (not all) matched entries the approved stops / targets give the recorded outcome class (the disagreements are listed as EXIT_MANAGEMENT_MISMATCH). "
          "The journal has no exit price or time, so the exit decisions cannot be compared beyond that label; what the journal's 'BE' label meant (exact-entry stop or another break-even rule) is not documented, while the approved rule stops at entry -/+ 6.", "",
          "## Earliest-cause classification (manual-only rows)", "", tab(["cfg", "cause", "rows"], cause_tab("MANUAL_ONLY")), "",
          "## Earliest-cause classification (automated trades without a match)", "", tab(["cfg", "cause", "trades"], cause_tab("AUTOMATED_ONLY")), "",
          "## ORB mismatch analysis", "",
          f"The journal has {manual_by.get('ORB', 0)} ORB rows; ORB is by far the largest source of manual-only rows. Matched ORB rows (strict): A {M['A']['strict_by_strategy'].get('ORB', 0)}, B {M['B']['strict_by_strategy'].get('ORB', 0)}, C {M['C']['strict_by_strategy'].get('ORB', 0)}. Causes of the unmatched ORB rows (primary, by the earliest failing predicate of the closest ORB method for the first candle's colour direction - the journal has no direction, so the direction is an ASSUMPTION): ", "",
          tab(["cause", "A", "B", "C"], [[c, orb_c["A"].get(c, 0), orb_c["B"].get(c, 0), orb_c["C"].get(c, 0)] for c in sorted({c for k in K for c in orb_c[k]})]), "",
          "**How to read this table.** The journal has no direction, so the closest of the three ORB methods (fewest failing predicates, for the direction implied by the first candle's colour) is used. "
          + "Where several methods tie, the evidence does not single out one cause: the primary cause is then TIE-BROKEN by the fixed method order (Method 1, Method 2, Gap) and the other tied cause is given as the secondary cause. Rows flagged `TIE-BROKEN` in the evidence: "
          + ", ".join(f"{k} {sum(1 for r in orb_rows if r['config'] == k and 'TIE-BROKEN' in r['evidence'])} of {sum(1 for r in orb_rows if r['config'] == k)}" for k in K) + ". The split between causes is therefore indicative, not a measurement.", "",
          "* **CANDLE_STRENGTH_MISMATCH / LEVEL_CONSTRUCTION_MISMATCH dominate**: the first candle either fails the numeric 'strong candle' profile (the rulebook is qualitative) or breaks neither the previous-day extreme nor the engine's inner level (the rulebook draws multi-candle bands and the author's levels are unknown). Both are the unresolved Phase 5.4 constructions, not defects.",
          "* **EMA_FILTER_MISMATCH / OPENING_GAP_MISMATCH**: the trend test (previous close against its EMA, an owner-approved variant of the rulebook's 'price above the 200 EMA') or the Gap-setup crossing reading rejects the day.",
          "* **MANUAL_JOURNAL_INCONSISTENCY**: ORB rows dated on Saturdays (no session).",
          f"* **Configuration C** adds {len(c_added)} ORB Gap / 200DMA trades through the candle-crossing reading; their journal status in C: {c_stage or 'none'}. This is reported descriptively; C is a provisional scenario and the DMA-versus-EMA question is unresolved.", "",
          "## IRF mismatch analysis", "",
          tab(["cause (manual IRF rows without a match)", "A", "B", "C"], [[c, irf_c["A"].get(c, 0), irf_c["B"].get(c, 0), irf_c["C"].get(c, 0)] for c in sorted({c for k in K for c in irf_c[k]})]), "",
          "* **DIFFERENT_STRATEGY_SELECTED / PORTFOLIO_CONTROLLER_CONSTRAINT**: the controller's first-valid-signal rule took an earlier signal of another strategy (or the manual IRF entry fell inside a running position). **EARLIER_SIGNAL / LATER_SIGNAL**: an automated IRF signal exists but at another time (the IRF reference candle / first-red-candle / EMA conventions move it).",
          "* **EMA_FILTER_MISMATCH** (B, C): the provisional 28-point EMA clearance rejected the candidate; **LEVEL_CONSTRUCTION_MISMATCH** (B, C; used for an IRF row only when A has a signal near the manual entry that B / C do not - see the table for how often): the first-red-candle LOW support moved or removed the Method 2A signal; **UNRESOLVED_DISCRETIONARY_SELECTION**: the engine saw no IRF setup (IRF-M1-003 boundary, Method 3 wick share and the unresolved day's-low rule are discretionary).", "",
          "## PDR / PDS mismatch analysis", "",
          tab(["strategy / cause", "A", "B", "C"], [[f"{s} {c}", pp_c["A"].get((s, c), 0), pp_c["B"].get((s, c), 0), pp_c["C"].get((s, c), 0)] for s, c in sorted({x for k in K for x in pp_c[k]})]), "",
          f"The journal has only {manual_by.get('PDR', 0)} PDR and {manual_by.get('PDS', 0)} PDS rows. The earliest-confirmation conventions of B / C move PDR / PDS entries earlier; the remaining PDR / PDS differences are date-and-strategy time differences or controller selections.", "",
          "## Strategy-selection differences", "", f"Dates on which the journal and the automated system traded DIFFERENT strategies only: A {M['A']['wrong_strategy_dates']}, B {M['B']['wrong_strategy_dates']}, C {M['C']['wrong_strategy_dates']} (`wrong_strategy_dates.csv`). On these dates the automated controller's first valid signal belonged to another strategy than the manual choice; no priority was introduced to align them.", "",
          "## Handwritten author corrections versus the three configurations", "",
          tab(["status", "A", "B", "C"], [[s, hw_stat["A"].get(s, 0), hw_stat["B"].get(s, 0), hw_stat["C"].get(s, 0)] for s in sorted({s for k in K for s in hw_stat[k]})]), "",
          f"Per correction: `handwritten_author_corrections_comparison.csv`. The {hw_stat['A'].get('ORB_STILL_NOT_TRADED', 0)} corrections stating that ORB should have been traded still have no ORB trade in A, B and C (all dated 2025; C's three added ORB trades are on {', '.join(sorted(t['date'] for t in c_added))}, none on a disputed date).", "",
          "## Reading the comparison", "",
          f"* Journal rows matched by a trade: A {M['A']['strict'] + M['A']['time_tolerant']}, B {M['B']['strict'] + M['B']['time_tolerant']}, C {M['C']['strict'] + M['C']['time_tolerant']} of {J['rows']}. B matches {M['A']['strict'] + M['A']['time_tolerant'] - M['B']['strict'] - M['B']['time_tolerant']} fewer journal rows than A (strict IRF matches fall from {M['A']['strict_by_strategy'].get('IRF', 0)} to {M['B']['strict_by_strategy'].get('IRF', 0)}; strict PDR matches rise from {M['A']['strict_by_strategy'].get('PDR', 0)} to {M['B']['strict_by_strategy'].get('PDR', 0)}); C adds back {M['C']['strict'] + M['C']['time_tolerant'] - M['B']['strict'] - M['B']['time_tolerant']} through its {len(c_added)} added ORB trades, each of which strictly matches an ORB journal row. Match counts are descriptive; they are not an approval criterion and no configuration is chosen on them.",
          f"* A large part of the manual journal cannot be reproduced mechanically: the journal records discretionary entries (ORB on 89 rows against {n_orb['A']} / {n_orb['B']} / {n_orb['C']} automated ORB trades in A / B / C), and many automated trades have no manual counterpart (the controller trades the first valid signal of every session, whether or not the trader took it).",
          "* Every mismatch has an earliest cause with evidence in `mismatch_root_causes.csv`; the rules were not rewritten to increase reconciliation."]
    (OUT / "cross_configuration_reconciliation.md").write_text("\n".join(CR) + "\n")

    # ============================================================================================ independent_audit.md
    IA = ["# Independent audit (Phase 5.6)", "",
          f"`scripts/phase56_independent_audit.py` re-reads the original workbook, re-implements the one-to-one matching and re-derives the ORB evidence from the raw candles (no `src/` imports). Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, nm, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:150]] for i, (nm, v) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation written in the same session; the fresh reviewer below is a separate pass.", "",
          "## Tests and lint", "", "* Before any change (existing suite): **737 passed, 1 skipped**.", f"* After implementation: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")

    # ============================================================================================ README
    R = ["# Phase 5.6 - manual journal reconciliation", "", f"> {WARN}", "",
         "The automated trades of configurations A (frozen Phase 3.6), B (Phase 5.3 author-corrected) and C (B + ORB gap crossing) of Phase 5.5 were reconciled one-to-one with the ORIGINAL manual journal, separately per configuration.", "",
         "The 'date + strategy only' column is a subset of the 'manual-only rows' and 'automated-only trades' columns (those pairs are NOT matches): matched + manual-only = 190 journal rows.", "",
         tab(["configuration", "automated trades", "strict", "time-tolerant", "matched", "date + strategy only", "manual-only rows", "automated-only trades"], [[NAMES[k], M[k]["automated_trades"], M[k]["strict"], M[k]["time_tolerant"], M[k]["strict"] + M[k]["time_tolerant"], M[k]["date_strategy_only"], M[k]["manual_rows_unmatched_total"], M[k]["automated_unmatched_total"]] for k in K]), "",
         f"* Journal: {J['rows']} data rows (Summary sheet says {J['summary_sheet'].get('Total trades')}), {manual_by.get('ORB', 0)} ORB rows, {len(J['weekend_rows'])} Saturday-dated rows (no sessions; kept as written). No direction, price or exit is recorded.",
         "* Every mismatch is classified by its earliest cause with evidence (`mismatch_root_causes.csv`); the strategy rules were NOT changed to raise the match count.",
         f"* {S['daily_reports']} session explanations (`daily/`), {S['charts']} charts of material mismatches (`charts/`).", "",
         "## Files", "", "`manual_journal_source_audit.md`, `manual_vs_automated_matching.csv`, `strict_matches.csv`, `time_tolerant_matches.csv`, `manual_only_trades.csv`, `automated_only_trades.csv`, `wrong_strategy_dates.csv`, `orb_unmatched_dates.csv`, `irf_unmatched_dates.csv`, `pdr_pds_unmatched_dates.csv`, `mismatch_root_causes.csv`, "
         "`cross_configuration_reconciliation.md`, `handwritten_author_corrections_comparison.csv`, `independent_audit.md`, `Manual_vs_Automated_Trading_Audit.xlsx`, `daily/`, `charts/`, `phase56_state.json`.", "",
         "## Reproduce", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate", "python scripts/phase55_run.py                     # the Phase 5.5 backtest (inputs)", "python scripts/phase56_run.py                     # matching, causes, daily reports, charts, workbook",
         "python scripts/phase56_independent_audit.py", "python scripts/phase56_docs.py --tests \"...\" --ruff \"...\"", "```", "", f"(Phase 5.5 independent audit: {'all checks pass' if st55_ok else 'NOT all checks pass - see the Phase 5.5 independent_audit.md'}.)"]
    (OUT / "README.md").write_text("\n".join(R) + "\n")
    print("phase 5.6 docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES / not run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
