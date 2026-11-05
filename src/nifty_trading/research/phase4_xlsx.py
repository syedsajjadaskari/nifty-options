"""Phase 4: the multi-year verification workbook. Every sheet is written from the CSV files of reports/phase4/ (no value is computed here), so the workbook and the CSV files cannot disagree; a test and the
independent audit compare them cell by cell. This workbook does not replace any earlier workbook."""

from __future__ import annotations

import csv
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from nifty_trading.research.phase32_excel import cell_text

HEAD = PatternFill("solid", fgColor="1F3864")
WINDOWS_NEW = ("B", "B_TV", "C", "D_5P", "D_TV")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def typed(v: str):
    if v == "":
        return ""
    if v in ("True", "False"):
        return v == "True"
    try:
        if v.lstrip("-").replace(".", "", 1).isdigit() and not (len(v) > 1 and v[0] == "0" and "." not in v[:2]):
            return float(v) if "." in v else int(v)
    except ValueError:
        pass
    return v


def sheet(wb: Workbook, name: str, rows: list[dict], widths: dict[str, int] | None = None) -> None:
    ws = wb.create_sheet(name[:31])
    if not rows:
        ws["A1"] = "(no rows)"
        return
    cols: list[str] = []
    for r in rows:
        for k in r:
            if k not in cols:
                cols.append(k)
    for ci, c in enumerate(cols, 1):
        h = ws.cell(row=1, column=ci, value=c)
        h.fill, h.font, h.alignment = HEAD, Font(bold=True, color="FFFFFF"), Alignment(wrap_text=True, vertical="center")
        longest = max([len(c)] + [len(str(r.get(c, ""))) for r in rows[:200]])
        ws.column_dimensions[get_column_letter(ci)].width = min(max(10, longest + 2), (widths or {}).get(c, 40))
    for ri, r in enumerate(rows, 2):
        for ci, c in enumerate(cols, 1):
            ws.cell(row=ri, column=ci, value=cell_text(typed(str(r.get(c, "")))))
    ws.freeze_panes = "B2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"


def write_workbook(out: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    lines = ["NIFTY 50 multi-year backtest verification workbook (Phase 4)",
             "FROZEN Phase 3.6 configuration (IRF, ORB, PDR body-based, PDS, RF; shared controller) on historical windows. HISTORICAL RESEARCH ONLY: the strategy was developed using later data.",
             "All P&L is SYNTHETIC index-point P&L x a fixed 390-unit comparison multiplier (the NIFTY 50 index is not tradable; historical lot sizes differ). Illustrative net = Rs 500 per trade + 0.5 point adverse slippage per fill.",
             "Window status: DATA_VALIDATED (5paisa, same provider as Phase 3.6; the DATA window passed the quality gate - this says nothing about the strategy), EXPLORATORY (secondary vendor only, cannot be checked against another vendor), PARTIAL_YEAR (5paisa 2019-03-01..2019-12-31), VENDOR_SENSITIVITY, REFERENCE (Phase 3.6).",
             "Every sheet is written from the CSV files of this directory; composite trade key = window_id | trade_id; daily journals and charts are under daily/<window>/ and charts/<window>/.",
             "No parameter was tuned; no window or period was selected after seeing results; loss-making periods are shown."]
    for i, line in enumerate(lines, 1):
        ws.cell(row=i, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 160
    sheet(wb, "Annual Comparison", rd(out / "annual_comparison.csv"))
    sheet(wb, "Strategy Comparison", rd(out / "strategy_comparison.csv"))
    sheet(wb, "Cost Sensitivity", rd(out / "cost_sensitivity.csv"))
    sheet(wb, "Monthly PnL", rd(out / "monthly_pnl_all_windows.csv"))
    sheet(wb, "Regimes", rd(out / "robustness_regimes.csv"))
    sheet(wb, "Entry Time", rd(out / "robustness_entry_time.csv"))
    sheet(wb, "Concentration", rd(out / "robustness_concentration.csv"))
    sheet(wb, "Data Quality Sensitivity", rd(out / "robustness_data_quality.csv"))
    sheet(wb, "Vendor Sensitivity", rd(out / "vendor_sensitivity.csv"))
    sheet(wb, "Coverage", rd(out / "data" / "historical_coverage_by_window.csv"))
    sheet(wb, "Coverage Exceptions", rd(out / "coverage_exceptions.csv"))
    sheet(wb, "Not Evaluated", rd(out / "not_evaluated_strategy_sessions.csv"))
    sheet(wb, "Vendor Overlap Monthly", rd(out / "data" / "vendor_overlap_by_month.csv"))
    sheet(wb, "Session Quality", rd(out / "data" / "session_quality_all_windows.csv"))
    sheet(wb, "All Trades", rd(out / "all_trades_all_windows.csv"))
    for name, fn, _extra in (("Daily Summary", "daily_summary.csv", None), ("Entry Conditions", "trade_entry_conditions.csv", None), ("Exit Details", "trade_exits_detailed.csv", None)):
        rows = []
        for w in WINDOWS_NEW:
            p = out / "windows" / w / fn
            if p.exists():
                rows += [{"window_id": w, **r} for r in rd(p)]
        sheet(wb, name, rows, {"calculation": 60, "observed": 80, "required": 40, "why_it_matters": 50})
    path = out / "NIFTY_MultiYear_Backtest_Verification.xlsx"
    wb.save(path)
    return path
