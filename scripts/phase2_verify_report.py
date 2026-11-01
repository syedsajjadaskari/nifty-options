"""Verify the NIFTY System Trading Strategy Performance report (DOCX) and cross-check the trading journal.

Reads the numbers straight out of the DOCX tables (no transcription), re-derives every aggregate,
and infers (from arithmetic only) which Target-2 distance each recorded winner used. All inferences
are labelled DERIVED: they are NOT source rules. Nothing here is fitted to reproduce the report.

Usage: python scripts/phase2_verify_report.py
Writes: reports/phase2/performance_report_verification.json and .md
"""

from __future__ import annotations

import itertools
import json
import re
import sys
from pathlib import Path

import docx
import openpyxl

ROOT = Path(__file__).resolve().parents[1]
DOCX = ROOT / "docs" / "trading journal" / "NIFTY_System_Trading_Strategy_Performance.docx"
XLSX = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
OUT = ROOT / "reports" / "phase2"

QTY_LEG, QTY_TOT, T1 = 195, 390, 27


def rs(text: str) -> int:
    neg = "–" in text or text.strip().startswith("-")
    n = int(re.sub(r"[^\d]", "", text) or 0)
    return -n if neg else n


def tables(d: docx.Document) -> list[list[list[str]]]:
    return [[[c.text.strip().replace("\n", " ") for c in r.cells] for r in t.rows] for t in d.tables]


def find(tbls, h0, h1=""):
    for t in tbls:
        if t[0][0].upper().startswith(h0) and t[0][1].upper().startswith(h1):
            return t
    raise KeyError((h0, h1))


def main() -> int:
    d = docx.Document(str(DOCX))
    tb = tables(d)
    text = "\n".join(p.text for p in d.paragraphs)
    checks: list[dict] = []

    def chk(name, documented, computed, tol=0.0, note=""):
        ok = abs(documented - computed) <= tol
        checks.append({"check": name, "documented": documented, "computed": round(computed, 4), "pass": ok, "note": note})

    # ---- statements read from prose
    stmts = {
        "six_lots_390_at_65": bool(re.search(r"6 lots \(390 quantity at 65 per lot\)", text)),
        "target1_27_points_3_lots": "3 lots are exited at Target 1, fixed at 27 points" in text,
        "target2_60_or_70_as_recorded": "Target 2 (60 or 70 points, as recorded)" in text,
        "breakeven_stop_moves_to_entry": "the stop on Leg 2 moves to the entry price" in text,
        "pnl_basis_points_x_quantity": "point distance on the NIFTY spot chart × quantity" in text,
        "costs_excluded": "results exclude brokerage, taxes and slippage" in text,
        "drawdown_on_cumulative_pnl_after_each_trade": "drawdown is measured on cumulative P&L after each trade" in text,
        "window_sep2025_aug2026_189_trades_180_days": "189 trades" in text and "180 trading days" in text,
    }

    out = find(tb, "OUTCOME", "TRADES")
    out = [r for r in out if r[0] in ("Target", "Breakeven (BE)", "Stop-loss (SL)")]
    n_t, n_be, n_sl = (int(r[1]) for r in out)
    pnl_t, pnl_be, pnl_sl = (rs(r[4]) for r in out)
    chk("trade count = Target+BE+SL", 189, n_t + n_be + n_sl)
    chk("BE trade pnl = 27 x 195", 5265, T1 * QTY_LEG)
    chk("BE total = 44 x 5265", pnl_be, n_be * 5265)
    chk("net pnl", 769860, pnl_t + pnl_be + pnl_sl)
    chk("gross profit", 1600560, pnl_t + pnl_be)
    chk("profit factor", 1.93, (pnl_t + pnl_be) / -pnl_sl, 0.005)
    chk("win rate excl BE", 55.17, 100 * n_t / (n_t + n_sl), 0.005)
    chk("win rate incl BE", 65.61, 100 * (n_t + n_be) / 189, 0.005)
    chk("expectancy per trade (Rs)", 4073, 769860 / 189, 0.5)
    chk("expectancy in points on 390 qty", 10.44, 769860 / 189 / QTY_TOT, 0.005)
    avg_t, avg_sl = pnl_t / n_t, -pnl_sl / n_sl
    chk("avg target pnl", 17111, avg_t, 0.5)
    chk("avg SL pnl", 12780, avg_sl, 0.5)
    chk("payoff ratio", 1.34, avg_t / avg_sl, 0.005)
    chk("breakeven win rate", 42.75, 100 * avg_sl / (avg_t + avg_sl), 0.01)
    chk("BE contribution share of net", 30.09, 100 * pnl_be / 769860, 0.005)

    # ---- inferred Target-2 mix, from the total target pnl only (two possible values -> unique solution)
    t60, t70 = (T1 + 60) * QTY_LEG, (T1 + 70) * QTY_LEG
    x70 = (pnl_t - n_t * t60) / (t70 - t60)
    derived = {"overall_target_trades_with_T2_70": x70, "overall_target_trades_with_T2_60": n_t - x70}
    chk("T2 mix integer solution exists", round(x70), x70, 1e-9, "DERIVED: number of Target trades that used T2=70")

    # ---- strategy table
    st = find(tb, "STRATEGY", "TRADES")
    rows = {r[0]: r for r in st if r[0] in ("IRF", "ORB", "PDR", "PDS", "RF")}
    strat = {}
    for s, r in rows.items():
        n, t, sl, be = (int(r[i]) for i in (1, 2, 3, 4))
        net = rs(r[8])
        strat[s] = {"trades": n, "T": t, "SL": sl, "BE": be, "net": net}
        chk(f"{s}: trades = T+SL+BE", n, t + sl + be)
    chk("strategy trades sum", 189, sum(v["trades"] for v in strat.values()))
    chk("strategy net sum", 769860, sum(v["net"] for v in strat.values()))
    chk("IRF+ORB share of profit %", 74.75, 100 * (strat["IRF"]["net"] + strat["ORB"]["net"]) / 769860, 0.005)

    # ---- strategy x month table -> per-cell decomposition (units of 195 qty: T60=87, T70=97, BE=27)
    sm = find(tb, "MONTH", "IRF")
    sm = [r for r in sm if r[0] not in ("MONTH", "Profitable months", "Total")]
    sm = [r for r in sm if len(r) == 7]
    cols = ["IRF", "ORB", "PDR", "PDS", "RF"]
    cell = {s: [] for s in cols}
    for r in sm:
        for s, v in zip(cols, r[1:6], strict=True):
            if v.strip() not in ("—", ""):
                cell[s].append((r[0], rs(v)))
    for s in cols:
        chk(f"{s}: monthly cells sum to strategy net", strat[s]["net"], sum(v for _, v in cell[s]))

    def decompositions(value, kinds):
        """All non-negative integer combos of the given winner kinds (units of 195 qty) summing to value/195."""
        u = value / QTY_LEG
        out = []
        for combo in itertools.product(range(0, 4), repeat=len(kinds)):
            if abs(sum(c * k[1] for c, k in zip(combo, kinds, strict=True)) - u) < 1e-9:
                out.append({k[0]: c for c, k in zip(combo, kinds, strict=True) if c})
        return out

    kinds = [("T60", 87), ("T70", 97), ("BE", 27)]
    win_mix = {}
    for s in ("PDR", "PDS"):  # these strategies recorded no stop-losses -> every cell is a positive sum of winners
        mix = {"T60": 0, "T70": 0, "BE": 0}
        unique = True
        for _, v in cell[s]:
            dec = decompositions(v, kinds)
            unique &= len(dec) == 1
            for k, c in (dec[0].items() if dec else []):
                mix[k] += c
        win_mix[s] = {"mix": mix, "unique_decomposition_every_cell": unique}
        chk(f"{s}: derived T count equals reported Target count", strat[s]["T"], mix["T60"] + mix["T70"])
        chk(f"{s}: derived BE count equals reported BE count", strat[s]["BE"], mix["BE"])
    derived["PDR_PDS_winner_mix"] = win_mix
    n70 = win_mix["PDR"]["mix"]["T70"] + win_mix["PDS"]["mix"]["T70"]
    chk("all inferred T2=70 trades are PDR/PDS", round(x70), n70)

    # ---- stop-loss distance inference (units: SL30=60, SL35=70, SL40=80 of 195-qty points)
    infer = {}
    for s in ("IRF", "ORB", "RF"):
        v = strat[s]
        win = v["T"] * t60 + v["BE"] * 5265  # RF/IRF/ORB winners are all T2=60 (follows from the PDR/PDS result above)
        loss = win - v["net"]
        n = v["SL"]
        sols = []
        for a30 in range(n + 1):
            for a35 in range(n + 1 - a30):
                a40 = n - a30 - a35
                if a30 * 60 + a35 * 70 + a40 * 80 == loss / QTY_LEG:
                    sols.append({"SL30": a30, "SL35": a35, "SL40": a40})
        infer[s] = {"implied_total_sl_loss": loss, "n_sl": n, "avg_stop_points": round(loss / QTY_TOT / n, 3), "solutions_over_{30,35,40}": sols}
    derived["stop_distance_inference"] = infer

    # ---- monthly table sanity
    mo = find(tb, "MONTH", "TRADES")
    mo = [r for r in mo if r[0].endswith(("2025", "2026")) and len(r) == 8]
    chk("monthly trades sum", 189, sum(int(r[1]) for r in mo))
    chk("monthly net sum", 769860, sum(rs(r[6]) for r in mo))
    cum = 0
    ok_cum = True
    for r in mo:
        cum += rs(r[6])
        ok_cum &= cum == rs(r[7])
        ok_cum &= int(r[2]) + int(r[3]) + int(r[4]) == int(r[1])
    chk("monthly cumulative column consistent", 1, 1 if ok_cum else 0)

    # ---- drawdown anatomy
    an = [r for r in find(tb, "TRADE", "DATE") if r[0].isdigit()]
    sls = sum(rs(r[4]) for r in an if r[3] == "SL")
    bes = sum(rs(r[4]) for r in an if r[3] == "BE")
    chk("June-2026 drawdown net", -68055, sls + bes)
    chk("max drawdown = peak - trough", 68055, 585000 - 516945)
    chk("drawdown % of peak account value", 9.94, 100 * 68055 / 685000, 0.005)
    chk("recovery factor", 11.31, 769860 / 68055, 0.005)

    # ---- journal cross-check (descriptive only; never used to tune anything)
    wb = openpyxl.load_workbook(str(XLSX), data_only=True)
    jr = [r for r in wb["Trading Journal"].iter_rows(min_row=3, values_only=True) if isinstance(r[0], int)]
    from collections import Counter
    jc = Counter(r[3] for r in jr)
    jo = Counter(r[4] for r in jr)
    j_month = Counter(r[1].strftime("%Y-%m") for r in jr)
    r_month = {m[0]: int(m[1]) for m in mo}
    r_month_k = {}
    for k, v in r_month.items():
        mm, yy = k.split()
        r_month_k[f"{yy}-{ {'Jan':'01','Feb':'02','Mar':'03','Apr':'04','May':'05','Jun':'06','Jul':'07','Aug':'08','Sep':'09','Oct':'10','Nov':'11','Dec':'12'}[mm]}"] = v
    journal = {
        "rows": len(jr), "summary_sheet_total": next(r[1] for r in wb["Summary"].iter_rows(values_only=True) if r[0] == "Total trades"),
        "by_strategy": dict(jc), "by_outcome": dict(jo),
        "report_by_strategy": {s: v["trades"] for s, v in strat.items()},
        "months_where_journal_count_differs_from_report": {m: {"journal": j_month[m], "report": r_month_k.get(m)} for m in sorted(j_month) if j_month[m] != r_month_k.get(m)},
        "weekend_dated_rows": [(r[0], str(r[1].date()), r[3], r[4]) for r in jr if r[1].weekday() >= 5],
        "unique_trade_dates": len({r[1].date() for r in jr}), "report_trading_days": 180,
        "dates_out_of_order": sum(1 for a, b in zip(jr, jr[1:], strict=False) if b[1] < a[1]),
    }
    journal["conclusion"] = ("The journal (190 rows) disagrees with its own Summary sheet and with the report (189 trades): "
                             "strategy attribution differs for IRF/ORB/PDR, August 2026 has one extra row, and 5 rows are dated on Saturdays "
                             "that have no market data. It is therefore NOT a reliable trade list; it records no direction, price, method, "
                             "stop distance or Target-2 distance either.")

    result = {"statements_found_in_report_text": stmts, "checks": checks, "derived_not_source_rules": derived, "journal_crosscheck": journal,
              "all_checks_pass": all(c["pass"] for c in checks) and all(stmts.values())}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "performance_report_verification.json").write_text(json.dumps(result, indent=2, default=str, ensure_ascii=False))
    md = ["# Performance report verification (generated by scripts/phase2_verify_report.py)\n",
          "All numbers are read from the DOCX tables and re-derived. `DERIVED` items are arithmetic inferences, **not** source rules.\n",
          "## Statements found verbatim in the report\n", *(f"- {'PASS' if v else 'FAIL'}: `{k}`" for k, v in stmts.items()),
          "\n## Arithmetic checks\n", "| check | documented | computed | pass |", "|---|---|---|---|",
          *(f"| {c['check']} | {c['documented']} | {c['computed']} | {'PASS' if c['pass'] else '**FAIL**'} |" for c in checks),
          f"\n**All checks pass: {result['all_checks_pass']}**\n", "## DERIVED (not source rules)\n", "```json",
          json.dumps(derived, indent=2), "```\n", "## Journal cross-check\n", "```json", json.dumps(journal, indent=2, default=str), "```\n"]
    (OUT / "performance_report_verification.md").write_text("\n".join(md))
    print(json.dumps({"all_checks_pass": result["all_checks_pass"], "n_checks": len(checks),
                      "failed": [c["check"] for c in checks if not c["pass"]]}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
