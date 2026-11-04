"""Phase 3.2: the manual-verification Excel workbook. Every data sheet is written from exactly the same row lists as the CSV files (reconciled by a test);
the Dashboard holds computed values (no formulas) so that it reads the same in every spreadsheet program. Owner review fields are left blank."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import asdict
from pathlib import Path

from openpyxl import Workbook
from openpyxl.formatting.rule import CellIsRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter
from openpyxl.worksheet.datavalidation import DataValidation

from nifty_trading.research import phase3 as P
from nifty_trading.research.phase32_build import Bundle, counts_vs_phase31
from nifty_trading.strategies.params import DEFAULT_PROPOSALS
from nifty_trading.strategies.rule_data import RULES

INR = '[$₹-4009]#,##0.00;[Red]-[$₹-4009]#,##0.00'
PTS = '#,##0.00" pts"'
PRICE = "#,##0.00"
HEAD_FILL = PatternFill("solid", fgColor="1F3864")
HEAD_FONT = Font(bold=True, color="FFFFFF")
TITLE = Font(bold=True, size=16, color="1F3864")
GREEN, RED, AMBER, GREY = (PatternFill("solid", fgColor=c) for c in ("C6EFCE", "FFC7CE", "FFEB9C", "E7E6E6"))
THIN = Side(style="thin", color="BBBBBB")
LONG_TEXT = {"explanation", "setup_explanation", "selection_explanation", "exit_narrative", "calculation", "observed", "required", "why_it_matters", "exit_trigger_evidence", "description", "evidence",
             "reference_levels", "state_trace", "failed_rule_names", "rule_name", "validity_note", "controller_reason", "mathematical_condition", "unresolved_items", "recomputation_mismatches",
             "used_for", "failure_reason", "last_state", "entry_fill_assumption", "exit_execution_rule", "detail", "chain", "nonconformity", "owner_comment", "suggested_owner_action", "source"}
RESULT_COLS = {"result", "match_classification", "match_manual", "severity"}
SHEETS = [("Dashboard", None), ("Daily Summary", "daily"), ("Automated Trades", "trades"), ("Entry Reasons", "checks"), ("Exit Details", "legs"), ("Candle Analysis", "candles"),
          ("Strategy Signals", "signals"), ("Ignored Signals", "ignored"), ("Rejected Signals", "rejected"), ("Manual Journal", "manual_norm"), ("Journal Comparison", "manual_cmp"),
          ("Daily Review Checklist", None), ("Rule Definitions", None), ("Verification Issues", "issues")]


def fmt_for(col: str):
    c = col.lower()
    if c.endswith("_rs") or c in ("gross_pnl_rs", "illustrative_net_pnl_rs", "leg1_pnl_rs", "leg2_pnl_rs") or "pnl_rs" in c or c in ("illustrative_cost_rs", "illustrative_slippage_rs"):
        return INR
    if "points" in c or c.endswith("_pts") or c.endswith("_pct") or c in ("delta_minutes",):
        return "#,##0.00"
    if any(k in c for k in ("price", "stop", "target", "entry_bar_", "exit_bar_", "_open", "_high", "_low", "_close", "open", "high", "low", "close", "ema", "range", "body", "wick")) and not c.endswith("_ts"):
        return PRICE
    return None


def style_header(ws, ncols: int) -> None:
    for c in range(1, ncols + 1):
        cell = ws.cell(row=1, column=c)
        cell.fill, cell.font = HEAD_FILL, HEAD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="center")
    ws.row_dimensions[1].height = 32


def write_table(ws, rows: list[dict], freeze_cols: int = 1) -> dict[str, int]:
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    for ci, f in enumerate(fields, 1):
        ws.cell(row=1, column=ci, value=f)
    for ri, r in enumerate(rows, 2):
        for ci, f in enumerate(fields, 1):
            v = r.get(f)
            if isinstance(v, (list, tuple, dict, set)):
                v = str(v)  # identical to what the CSV writer stores
            if isinstance(v, bool):
                v = "TRUE" if v else "FALSE"
            c = ws.cell(row=ri, column=ci, value=("" if v is None else v))
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                nf = fmt_for(f)
                if nf:
                    c.number_format = nf
    style_header(ws, len(fields))
    for ci, f in enumerate(fields, 1):
        letter = get_column_letter(ci)
        if f in LONG_TEXT:
            ws.column_dimensions[letter].width = 70
            for ri in range(2, len(rows) + 2):
                ws.cell(row=ri, column=ci).alignment = Alignment(wrap_text=True, vertical="top")
        else:
            longest = max([len(str(f))] + [len(str(r.get(f, ""))) for r in rows[:300]])
            ws.column_dimensions[letter].width = min(max(10, longest + 2), 34)
    ws.freeze_panes = ws.cell(row=2, column=freeze_cols + 1)
    ws.auto_filter.ref = f"A1:{get_column_letter(len(fields))}{max(len(rows) + 1, 2)}"
    for f in fields:
        if f in RESULT_COLS or f in ("outcome", "controller_event", "automated_review_flag"):
            ci = fields.index(f) + 1
            rng = f"{get_column_letter(ci)}2:{get_column_letter(ci)}{len(rows) + 1}"
            for text, fill in (("PASS", GREEN), ("EXACT_MATCH", GREEN), ("TARGET", GREEN), ("FAIL", RED), ("UNRESOLVED", AMBER), ("NOT_APPLICABLE", GREY), ("TIME_SHIFTED_MATCH", AMBER),
                               ("HIGH", RED), ("MEDIUM", AMBER), ("INITIAL_FULL_STOP", RED), ("EXTRA_AUTOMATED_TRADE", AMBER), ("T1_THEN_BUFFER_STOP", AMBER)):
                ws.conditional_formatting.add(rng, CellIsRule(operator="equal", formula=[f'"{text}"'], fill=fill))
    return {f: i + 1 for i, f in enumerate(fields)}


def param_status(key: str) -> str:
    approved = {"trend_mode": "USER_APPROVED (research variant A, EMA-only)", "pdr_zone_method": "USER_APPROVED (research candidate B, confirmed reversal swing high)",
                "stop_variant": "USER_APPROVED (baseline stops IRF/PDR/PDS/RF 35, ORB 30)", "t1_points": "SOURCE_VERIFIED (performance report) / USER_APPROVED", "total_lots": "USER_APPROVED",
                "leg1_lots": "USER_APPROVED", "lot_size": "SOURCE_VERIFIED (report) - configurable", "post_t1_buffer_points": "USER_APPROVED", "post_t1_stop_mode": "USER_APPROVED (BUFFER)",
                "rf_t2_points": "PROPOSED_FOR_REVIEW (RF target is OPEN in the guide)", "forced_exit_time": "PROVISIONAL (implementer assumption FORCED-EXIT-002)",
                "max_signals_per_session": "controller runs lift the engine cap to 99; the shared controller limits entries (USER_APPROVED portfolio rules)",
                "strong_candle": "PROPOSED_FOR_REVIEW (owner recommendation)", "pin_bar": "PROPOSED_FOR_REVIEW (owner recommendation)"}
    return approved.get(key, "PROPOSED_FOR_REVIEW (research setting)")


def dashboard(wb: Workbook, b: Bundle) -> None:
    ws = wb["Dashboard"]
    ws["A1"], ws["A1"].font = "NIFTY 50 - explainable backtest and daily verification (Phase 3.2)", TITLE
    ws["A2"] = (f"Period 2025-09-01 .. 2026-08-31 | rule configuration {b.cfg_id} | synthetic index-point P&L (the index is not tradable) | owner review fields are blank | "
                "no parameter was tuned; this is a verification aid, not a recommendation")
    rows = sorted(b.ledger, key=P.sequence_key)
    gross = [r["gross_pnl_rs"] for r in rows]
    net = P.apply_costs(rows, 500.0, 0.5)
    sg, sn = P.summarize(rows, gross), P.summarize(rows, net)
    cv = counts_vs_phase31(b)
    n_ok = sum(1 for t in b.trades if not t["recomputation_mismatches"])
    r0 = 4

    def block(title: str, items: list[tuple], row: int, col: int = 1) -> int:
        ws.cell(row=row, column=col, value=title).font = Font(bold=True, size=12, color="1F3864")
        for i, (k, v, nf) in enumerate(items, 1):
            ws.cell(row=row + i, column=col, value=k)
            c = ws.cell(row=row + i, column=col + 1, value=v)
            if nf:
                c.number_format = nf
        return row + len(items) + 2
    r = block("Annual results (baseline)", [
        ("Evaluable trading sessions", len(b.days), None), ("Executed trades", sg["entries"], None), ("Days with a trade", sg["days_traded"], None), ("First / second trades", f"{sg['first_trades']} / {sg['second_trades']}", None),
        ("Gross P&L", sg["total_pnl_rs"], INR), ("Illustrative net P&L (Rs 500/trade + 0.5 pt per fill)", sn["total_pnl_rs"], INR), ("Win rate (gross P&L > 0)", sg["win_rate_pct"] / 100, "0.00%"),
        ("Profit factor (gross)", sg["profit_factor"], "0.00"), ("Average trade (gross)", sg["avg_trade_rs"], INR), ("Max drawdown (gross)", sg["max_drawdown_rs"], INR),
        ("Target 2", sg["target2"], None), ("T1 then post-T1 stop", sg["t1_then_buffer_stop"], None), ("Initial full stop", sg["initial_full_stop"], None), ("Forced exit (provisional 15:14)", sg["forced_exit"], None),
        ("Unresolved executions", sg["unresolved"], None)], r0)
    strat_items = []
    for s in P.STRATEGIES:
        sub = [x for x in rows if x["strategy"] == s]
        strat_items.append((s, f"{len(sub)} trades | gross Rs {sum(x['gross_pnl_rs'] for x in sub):,.0f}", None))
    r = block("Trades by strategy", strat_items, r)
    r = block("Journal agreement (Phase 3.1 methodology, unchanged)", [
        ("Manual journal rows", cv["manual_rows"], None), ("Exact matches (same candle)", cv["exact"], None), ("Time-shifted matches (<= 15 min)", cv["time_shifted"], None),
        ("Unmatched manual trades", cv["manual_rows"] - cv["exact"] - cv["time_shifted"], None), ("Extra automated trades", cv["extras"], None),
        ("Matches equal Phase 3.1 figures", "YES" if cv["classification_equal_to_phase31"] else "NO - see data_provenance.json", None)], r)
    chk = Counter(c["result"] for c in b.checks)
    r = block("Explanation completeness", [
        ("Executed trades with a full entry explanation", f"{len(b.trades)} / {len(b.trades)}", None), ("Exit explanations (both legs)", f"{len({g['trade_id'] for g in b.legs})} / {len(b.trades)} trades", None),
        ("Entry conditions recorded", len(b.checks), None), ("... PASS / FAIL / UNRESOLVED / NOT_APPLICABLE", f"{chk['PASS']} / {chk['FAIL']} / {chk['UNRESOLVED']} / {chk['NOT_APPLICABLE']}", None),
        ("Trades whose recomputation matches the engine's own record", f"{n_ok} / {len(b.trades)}", None),
        ("Phase 3.0 baseline ledger reproduced field by field", "IDENTICAL" if b.ledger_check["identical"] else f"{b.ledger_check['n_differences']} DIFFERENCES", None)], r)
    ws.cell(row=r, column=1, value="Navigation").font = Font(bold=True, size=12, color="1F3864")
    for i, (name, _) in enumerate(SHEETS[1:], 1):
        c = ws.cell(row=r + i, column=1, value=name)
        c.hyperlink = f"#'{name}'!A1"
        c.font = Font(color="0563C1", underline="single")
    ws.column_dimensions["A"].width = 58
    ws.column_dimensions["B"].width = 44
    monthly = P.monthly(rows, gross)
    ws.cell(row=4, column=4, value="Monthly gross P&L").font = Font(bold=True, size=12, color="1F3864")
    for i, (mth, v) in enumerate(monthly.items(), 5):
        ws.cell(row=i, column=4, value=mth)
        ws.cell(row=i, column=5, value=v).number_format = INR
    ws.column_dimensions["D"].width = 12
    ws.column_dimensions["E"].width = 18


def review_checklist(wb: Workbook, b: Bundle) -> None:
    ws = wb["Daily Review Checklist"]
    rows = []
    for d in b.daily:
        rows.append({"date": d["date"], "weekday": d["weekday"], "executed_trades": d["executed_trades"], "trade_ids": d["trade_ids"], "manual_journal_trades": d["manual_journal_trades"],
                     "manual_unmatched": d["manual_unmatched"], "extra_automated_trades": d["extra_automated_trades"], "automated_review_flag": d["automated_review_flag"],
                     "daily_journal": f"daily/{d['date'][:7]}/{d['date']}.md", "owner_review_status": "", "reviewer": "", "reviewed_on": "", "owner_comment": ""})
    cols = write_table(ws, rows)
    dv = DataValidation(type="list", formula1='"APPROVED,NEEDS_CLARIFICATION,DISPUTED,NOT_REVIEWED"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{get_column_letter(cols['owner_review_status'])}2:{get_column_letter(cols['owner_review_status'])}{len(rows) + 1}")
    edit = PatternFill("solid", fgColor="FFF2CC")
    for ri in range(2, len(rows) + 2):
        for k in ("owner_review_status", "reviewer", "reviewed_on", "owner_comment"):
            ws.cell(row=ri, column=cols[k]).fill = edit
        c = ws.cell(row=ri, column=cols["daily_journal"])
        c.hyperlink = c.value
        c.font = Font(color="0563C1", underline="single")


def rule_definitions(wb: Workbook, b: Bundle) -> None:
    ws = wb["Rule Definitions"]
    rows = []
    for r in RULES:
        rows.append({"kind": "RULE", "id": r["rule_id"], "strategy": r["strategy"], "method": r["method"], "description": r["description"], "source": f"{r['source_document']} p.{r['source_page']}",
                     "approval_status": r["classification"], "implementation_status": r["implementation_status"], "mathematical_condition": r["mathematical_condition"],
                     "proposal": r.get("proposal_parameter", "") or "", "unresolved_dependencies": ";".join(r.get("unresolved_dependencies", []) or [])})
    for k, v in b.scenario.proposals.to_dict().items():
        rows.append({"kind": "PARAMETER (ProposalConfig)", "id": k, "strategy": "", "method": "", "description": f"active value: {v}  (shipped default: {getattr(DEFAULT_PROPOSALS, k, 'n/a')})", "source": "src/nifty_trading/strategies/params.py",
                     "approval_status": param_status(k), "implementation_status": "ACTIVE", "mathematical_condition": "", "proposal": "", "unresolved_dependencies": ""})
    for k, v in asdict(b.scenario.trade).items():
        rows.append({"kind": "PARAMETER (TradeConfig)", "id": k, "strategy": "", "method": "", "description": f"active value: {v}", "source": "src/nifty_trading/strategies/params.py",
                     "approval_status": param_status(k), "implementation_status": "ACTIVE", "mathematical_condition": "", "proposal": "", "unresolved_dependencies": ""})
    write_table(ws, rows, 2)


def write_workbook(b: Bundle, path: Path) -> None:
    wb = Workbook()
    wb.active.title = "Dashboard"
    for name, attr in SHEETS[1:]:
        ws = wb.create_sheet(name)
        if attr:
            write_table(ws, getattr(b, attr), 2 if attr in ("checks", "legs", "candles", "signals", "ignored", "rejected", "manual_cmp", "issues") else 1)
    dashboard(wb, b)
    review_checklist(wb, b)
    rule_definitions(wb, b)
    # navigation inside the data sheets: trade id -> its first Entry Reasons row; date -> daily journal
    first_row: dict[str, int] = {}
    ws_e = wb["Entry Reasons"]
    for ri in range(2, ws_e.max_row + 1):
        first_row.setdefault(str(ws_e.cell(row=ri, column=1).value), ri)
    ws_t = wb["Automated Trades"]
    for ri in range(2, ws_t.max_row + 1):
        c = ws_t.cell(row=ri, column=1)
        if str(c.value) in first_row:
            c.hyperlink = f"#'Entry Reasons'!A{first_row[str(c.value)]}"
            c.font = Font(color="0563C1", underline="single")
    head_t = [c.value for c in ws_t[1]]
    for col in ("chart_file", "daily_journal"):
        if col in head_t:
            ci = head_t.index(col) + 1
            for ri in range(2, ws_t.max_row + 1):
                c = ws_t.cell(row=ri, column=ci)
                c.hyperlink = str(c.value)
                c.font = Font(color="0563C1", underline="single")
    ws_d = wb["Daily Summary"]
    for ri in range(2, ws_d.max_row + 1):
        c = ws_d.cell(row=ri, column=1)
        c.hyperlink = f"daily/{str(c.value)[:7]}/{c.value}.md"
        c.font = Font(color="0563C1", underline="single")
    by_day = defaultdict(int)
    for t in b.trades:
        by_day[t["date"]] += 1
    for ws in wb.worksheets:
        ws.sheet_view.zoomScale = 90
        for row in ws.iter_rows(min_row=1, max_row=1):
            for c in row:
                c.border = Border(bottom=THIN)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(str(path))
