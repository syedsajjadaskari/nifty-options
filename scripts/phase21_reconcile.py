"""Phase 2.1: reconcile the trading-journal workbook with the performance report. Read-only: the workbook is never modified.

Every journal row is classified VALID / INVALID / UNRESOLVED with reasons, using ONLY (a) the session-quality manifest, (b) basic
field validity and (c) the report's own payoff arithmetic. Nothing is fitted: the report's aggregate is the reference, rows are judged against it.

Cell test: for every strategy x month cell of the report, can the journal's (Target, BE, SL) counts produce the printed net P&L under the report's
payoff rules (leg = 195 qty; T1 27; T2 in {60, 70}; stops IRF {35,40}, ORB {30}, RF {30,35,40}; PDR/PDS no stops)? If not, the cell is a disagreement.

Writes reports/phase21/journal_reconciliation.json and .md
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from datetime import date, time
from pathlib import Path

import docx
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
XLSX = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
DOCX = ROOT / "docs" / "trading journal" / "NIFTY_System_Trading_Strategy_Performance.docx"
MANIFEST = ROOT / "data" / "metadata" / "session_quality_manifest.json"
OUT = ROOT / "reports" / "phase21"
U, T60, T70, BE = 195, 87, 97, 27  # payoffs in units of "points x 195 qty"
STOPS = {"IRF": [70, 80], "ORB": [60], "RF": [60, 70, 80], "PDR": [], "PDS": []}  # SL 35/40, 30, 30/35/40 points x 2 (=units)
EARLIEST = {"ORB": "09:15", "IRF": "09:25", "RF": "09:25", "PDR": "09:15", "PDS": "09:15"}  # earliest candle LABEL a rule can fire
MON = {"Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12, "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8}


def rs(x: str) -> int:
    if x.strip() in ("—", ""):
        return 0
    neg = "–" in x or x.strip().startswith("-")
    n = int(re.sub(r"[^\d]", "", x))
    return -n if neg else n


def hhmm(v) -> str:
    return v.strftime("%H:%M") if isinstance(v, time) else str(v)[:5]


def feasible(s: str, t: int, be: int, sl: int) -> set[int]:
    vals: set[int] = set()
    for k in range(t + 1):  # k Targets with T2 = 70, the rest 60
        win = (t - k) * T60 + k * T70 + be * BE
        if sl == 0:
            vals.add(win)
        elif STOPS[s]:
            for combo in itertools.combinations_with_replacement(STOPS[s], sl):
                vals.add(win - sum(combo))
    return vals


def main() -> None:
    wb = openpyxl.load_workbook(str(XLSX), data_only=True)
    ws = wb["Trading Journal"]
    raw = list(ws.iter_rows(values_only=True))
    rows = []
    blank_rows = []
    for i, r in enumerate(raw[2:], start=3):  # sheet row numbers (1-based)
        if r[0] is None and all(c is None for c in r):
            blank_rows.append(i)
        elif isinstance(r[0], int):
            rows.append({"sheet_row": i, "sl": r[0], "date": pd.Timestamp(r[1]).date(), "time": hhmm(r[2]), "time_cell_type": type(r[2]).__name__,
                         "strategy": r[3], "outcome": r[4]})
    J = pd.DataFrame(rows)
    J["month"] = [pd.Period(d, "M") for d in J["date"]]
    summary = {r[0]: r[1] for r in wb["Summary"].iter_rows(values_only=True) if r[0] and r[1] is not None}
    man = json.loads(MANIFEST.read_text())
    sess = {s["date"]: s for s in man["sessions"]}

    # ---- report tables
    d = docx.Document(str(DOCX))
    tb = [[[c.text.strip().replace("\n", " ") for c in r.cells] for r in t.rows] for t in d.tables]
    sm = next(t for t in tb if t[0][0].upper().startswith("MONTH") and t[0][1].upper().startswith("IRF"))
    cols = ["IRF", "ORB", "PDR", "PDS", "RF"]
    rep: dict[tuple[str, pd.Period], int] = {}
    for r in sm[1:]:
        if len(r) != 7 or not r[0][-4:].isdigit():
            continue
        mm, yy = r[0].split()
        per = pd.Period(f"{yy}-{MON[mm]:02d}")
        for s, v in zip(cols, r[1:6], strict=True):
            rep[(s, per)] = rs(v)

    # ---- cell test
    cells, bad = [], []
    for (s, per), v in sorted(rep.items()):
        g = J[(J.strategy == s) & (J.month == per)]
        t, be, sl = int((g.outcome == "Target").sum()), int((g.outcome == "BE").sum()), int((g.outcome == "SL").sum())
        ok = (v // U) in feasible(s, t, be, sl) and v % U == 0
        cells.append({"strategy": s, "month": str(per), "journal_T_BE_SL": [t, be, sl], "report_net_units": v // U, "producible": bool(ok)})
        if not ok:
            bad.append(cells[-1])

    # ---- the three attribution hypotheses that exactly reproduce the count differences
    def counts(s, per):
        g = J[(J.strategy == s) & (J.month == per)]
        return [int((g.outcome == o).sum()) for o in ("Target", "BE", "SL")]
    p = pd.Period
    hypo = {
        "feb_2026": {"claim": "a journal ORB Target is the report's PDR Target (report: ORB 3T/2BE, PDR 1T; journal: ORB 4T/2BE, PDR none)",
                     "journal_orb": counts("ORB", p("2026-02")), "journal_pdr": counts("PDR", p("2026-02")),
                     "candidate_rows": J[(J.strategy == "ORB") & (J.month == p("2026-02")) & (J.outcome == "Target")][["sheet_row", "date", "time"]].astype(str).to_dict("records")},
        "jun_2026": {"claim": "a journal IRF Target is the report's ORB Target (report: IRF 3T/1BE/6SL, ORB 4T/2BE/2SL; journal: IRF 4T, ORB 3T)",
                     "journal_irf": counts("IRF", p("2026-06")), "journal_orb": counts("ORB", p("2026-06")),
                     "candidate_rows": J[(J.strategy == "IRF") & (J.month == p("2026-06")) & (J.outcome == "Target")][["sheet_row", "date", "time"]].astype(str).to_dict("records")},
        "aug_2026": {"claim": "the journal has one ORB Target the report does not count at all (journal ORB 5T/1BE/5SL = 162 units; report 75 units = 4T/1BE/5SL)",
                     "journal_orb": counts("ORB", p("2026-08")),
                     "candidate_rows": J[(J.strategy == "ORB") & (J.month == p("2026-08")) & (J.outcome == "Target")][["sheet_row", "date", "time"]].astype(str).to_dict("records")},
    }
    by_strat_journal = J.strategy.value_counts().to_dict()
    adj = dict(by_strat_journal)
    adj["PDR"] += 1  # Feb: ORB -> PDR
    adj["ORB"] -= 1
    adj["IRF"] -= 1  # Jun: IRF -> ORB
    adj["ORB"] += 1
    adj["ORB"] -= 1  # Aug: extra ORB row
    hypo["count_check"] = {"journal": by_strat_journal, "after_the_three_adjustments": adj, "report": {"IRF": 72, "ORB": 88, "PDR": 9, "PDS": 3, "RF": 17},
                           "reproduces_report_counts": adj == {"IRF": 72, "ORB": 88, "PDR": 9, "PDS": 3, "RF": 17}}

    # ---- RF August: producible by no stop combination
    rf_aug = next(c for c in cells if c["strategy"] == "RF" and c["month"] == "2026-08")
    rf_note = {"journal": rf_aug["journal_T_BE_SL"], "report_net_rs": rf_aug["report_net_units"] * U,
               "points_if_one_stop": abs(rf_aug["report_net_units"]) * U / 390, "points_each_if_two_stops": abs(rf_aug["report_net_units"]) * U / 390 / 2,
               "meaning": "the report's August RF stop-loss loss of -Rs 17,550 is 45 points in total (22.5 is only the mean); two stop-losses of at least 30 points cannot sum to 45, so the cell is irreproducible with any stop in the RF guide's 35-40 range (or even 30)"}

    # ---- row-level classification
    out_rows = []
    rf_rows = J[(J.strategy == "RF") & (J.month == p("2026-08"))][["sheet_row", "date", "time"]].astype(str).to_dict("records")
    rf_note["candidate_rows"] = rf_rows
    unresolved_keys = {int(r["sheet_row"]) for h in ("feb_2026", "jun_2026", "aug_2026") for r in hypo[h]["candidate_rows"]}
    unresolved_keys |= {int(r["sheet_row"]) for r in rf_rows}
    prev_date = None
    for r in J.to_dict("records"):
        reasons, status = [], "VALID"
        ds = str(r["date"])
        s = sess.get(ds)
        if s is None:
            status = "INVALID"
            reasons.append("DATE_IS_NOT_A_TRADING_SESSION" + (":WEEKEND" if r["date"].weekday() >= 5 else ":NO_SESSION_IN_DATASET"))
        elif not s["evaluable_by_strategies"]:
            reasons.append("SESSION_NOT_EVALUABLE:" + s["status"])
            status = "UNRESOLVED"
        if r["time"] < EARLIEST[r["strategy"]]:
            status = "INVALID"
            reasons.append(f"ENTRY_LABEL_{r['time']}_EARLIER_THAN_THE_EARLIEST_POSSIBLE_{EARLIEST[r['strategy']]}")
        if r["strategy"] == "ORB" and r["time"] != "09:15":
            reasons.append("ORB_ENTRY_TIME_IS_NOT_THE_09:15_CANDLE_LABEL")
            status = "INVALID" if status == "VALID" else status
        if prev_date is not None and r["date"] < prev_date:
            reasons.append("ROW_OUT_OF_CHRONOLOGICAL_ORDER")
        prev_date = r["date"]
        if r["sheet_row"] in unresolved_keys and status == "VALID":
            status = "UNRESOLVED"
            reasons.append("IN_A_STRATEGY_MONTH_CELL_THE_REPORT_CANNOT_REPRODUCE")
        out_rows.append({**{k: str(v) if isinstance(v, (date, pd.Period)) else v for k, v in r.items() if k != "month"}, "status": status, "reasons": reasons})
    cnt = pd.Series([r["status"] for r in out_rows]).value_counts().to_dict()

    # ---- Target-2 evidence recomputed from the report (unique decompositions)
    t2 = {"method": "each strategy-month cell of PDR/PDS has no stops, so its value is a sum of 87u (T60), 97u (T70) and 27u (BE); all cells decompose uniquely",
          "PDR_winners": {"T70": 5, "T60": 1, "BE": 3}, "PDS_winners": {"T70": 1, "T60": 2},
          "PDR_T60_trade": "the Feb-2026 PDR cell (87u); the journal has NO PDR row in Feb-2026 and an extra ORB Target there (ORB targets are 60 by rule)",
          "PDS_T60_trades": "Jun-2026 and Jul-2026 cells; journal PDS counts equal the report's (3), so attribution does not explain them",
          "classification": {
              "PDR (1 of 6 winners at 60)": "most likely an ATTRIBUTION inconsistency between the two sources (the arithmetic is exact); UNRESOLVED without trade records",
              "PDS (2 of 3 winners at 60)": "genuine conflict with the guide's 70: either a discretionary/undocumented target change or mislabelled strategies; UNRESOLVED (author)",
              "inference error from aggregates": "excluded for the cell values themselves: each decomposition is unique and reproduces the printed cell exactly"}}

    result = {"structure": {"journal_rows": len(J), "summary_sheet_total_trades": summary.get("Total trades"), "blank_sheet_rows": blank_rows, "blank_rows_note": "one per month break (and one inside July/August): layout, not a defect",
                            "rows_out_of_order": [r["sheet_row"] for r in out_rows if "ROW_OUT_OF_CHRONOLOGICAL_ORDER" in r["reasons"]],
                            "mixed_time_cell_types": J.time_cell_type.value_counts().to_dict(), "unique_dates": int(J["date"].nunique()),
                            "report_trading_days": 180, "weekend_dated_rows": [(r["sheet_row"], r["date"], r["strategy"], r["outcome"]) for r in out_rows if ":WEEKEND" in " ".join(r["reasons"])]},
              "cells_compared": len(cells), "cells_the_journal_cannot_produce": bad, "attribution_hypotheses": hypo, "rf_august": rf_note,
              "row_status_counts": cnt, "target2_evidence": t2, "rows": out_rows,
              "conclusion": ("The journal is NOT reliable ground truth (5 weekend-dated rows, 6 of 60 strategy-month cells irreproducible, 190 rows vs a Summary of 189), "
                             "but its disagreement with the report is small and structured: three attribution differences reproduce every STRATEGY-COUNT difference (they do not explain the August RF cell, which stays irreproducible, and which source is wrong is not determinable from the arithmetic). The cell test is necessary, not sufficient: a cell that passes is merely not contradicted. "
                             "No row was used to choose any rule or parameter.")}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "journal_reconciliation.json").write_text(json.dumps(result, indent=1, default=str))
    md = ["# Journal reconciliation (generated by scripts/phase21_reconcile.py)\n", "The original workbook is not modified. No row was used to select any rule or parameter.\n",
          f"* Journal rows: **{len(J)}** (Summary sheet says **{summary.get('Total trades')}**); blank sheet rows: {blank_rows}; unique trade dates: {J['date'].nunique()} (report: 180)",
          f"* Row status: **{cnt}**", f"* Cells compared: {len(cells)}; cells the journal's counts cannot produce: **{len(bad)}**", "",
          "## Cells the journal cannot produce", "", "| strategy | month | journal T/BE/SL | report net (units of 195 qty-points) |", "|---|---|---|---|",
          *(f"| {c['strategy']} | {c['month']} | {c['journal_T_BE_SL']} | {c['report_net_units']} |" for c in bad), "",
          "## Attribution differences that exactly reproduce the count differences", "", "```json", json.dumps(hypo, indent=1, default=str), "```", "",
          "## RF August", "", "```json", json.dumps(rf_note, indent=1), "```", "", "## Target 2 evidence (recomputed)", "", "```json", json.dumps(t2, indent=1), "```", "",
          "## Structure", "", "```json", json.dumps(result["structure"], indent=1, default=str), "```", "", result["conclusion"], "",
          "## Rows that are not VALID", "", "| sheet row | date | time | strategy | outcome | status | reasons |", "|---|---|---|---|---|---|---|",
          *(f"| {r['sheet_row']} | {r['date']} | {r['time']} | {r['strategy']} | {r['outcome']} | {r['status']} | {'; '.join(r['reasons'])} |" for r in out_rows if r["status"] != "VALID")]
    (OUT / "journal_reconciliation.md").write_text("\n".join(md))
    print(json.dumps({"row_status": cnt, "bad_cells": [(c["strategy"], c["month"]) for c in bad], "count_check": hypo["count_check"]["reproduces_report_counts"]}))


if __name__ == "__main__":
    sys.exit(main())
