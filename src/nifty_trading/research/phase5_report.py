"""Phase 5: per-index and cross-index tables, built ONLY from the CSV files each run wrote (so every number can be recomputed from the files).

Primary metric = INDEX POINTS (weighted over the two exit legs: ``gross_pnl_points_weighted``). Rupee columns use the fixed 390-unit comparison multiplier of the frozen Phase 3.6 configuration; they are shown inside each
index's own tables only and are NEVER compared across indices (the index levels, and the point values of any real contract, differ). NIFTY reference rows are read from the Phase 4 window outputs and the unchanged
Phase 3.6 directory; nothing there is modified. Nothing in this module changes a strategy, a stop, a target, the cutoff or the controller.
"""

from __future__ import annotations

import csv
import math
import statistics
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase4 as F4
from nifty_trading.research import phase4_report as R4
from nifty_trading.research import phase5_data as D5
from nifty_trading.research.phase35 import write_csv

ROOT = D5.ROOT
OUT = ROOT / "reports" / "phase5"
P4 = ROOT / "reports" / "phase4"
INDEX_NAMES = ("NIFTY", "BANKNIFTY", "SENSEX")
fnum = F4.fnum

# (row id, label, window id, start, end, status, source note). Main-window slices are the same Sep-Aug years as Phase 4.
ROWS = [
    ("M_2022_23", "2022-09-01..2023-08-31", "M", date(2022, 9, 1), date(2023, 8, 31), "DATA_VALIDATED", "5paisa"),
    ("M_2023_24", "2023-09-01..2024-08-31", "M", date(2023, 9, 1), date(2024, 8, 31), "DATA_VALIDATED", "5paisa"),
    ("M_2024_25", "2024-09-01..2025-08-31", "M", date(2024, 9, 1), date(2025, 8, 31), "DATA_VALIDATED", "5paisa"),
    ("M_2025_26", "2025-09-01..2026-08-31", "M", date(2025, 9, 1), date(2026, 8, 31), "DATA_VALIDATED", "5paisa"),
    ("M_ALL", "2022-09-01..2026-08-31 (main window)", "M", date(2022, 9, 1), date(2026, 8, 31), "DATA_VALIDATED", "5paisa"),
    ("M_TO_2024_03_22", "2022-09-01..2024-03-22 (5paisa; same dates as the vendor run)", "M", date(2022, 9, 1), date(2024, 3, 22), "DATA_VALIDATED", "5paisa"),
    ("MS_2022_09_2024_03", "2022-09-01..2024-03-22 (secondary source)", "MS", date(2022, 9, 1), date(2024, 3, 22), "VENDOR_SENSITIVITY", "secondary"),
    ("C_2018", "2018-01-01..2018-12-31", "C", date(2018, 1, 1), date(2018, 12, 31), "EXPLORATORY", "secondary"),
    ("D_2019_5P_PARTIAL", "2019-03-01..2019-12-31 (PARTIAL YEAR)", "D_5P", date(2019, 3, 1), date(2019, 12, 31), "PARTIAL_YEAR", "5paisa"),
    ("D_2019_SECONDARY", "2019-01-01..2019-12-31", "D_TV", date(2019, 1, 1), date(2019, 12, 31), "EXPLORATORY", "secondary"),
]
# NIFTY reference windows: main = Phase 4 window B (2022-09..2025-08, 5paisa) + the unchanged Phase 3.6 window A (2025-09..2026-08); the vendor run is Phase 4's B_TV (a DIFFERENT secondary vendor than BANKNIFTY / SENSEX)
NIFTY_MAP = {"M": ("B", "A"), "MS": ("B_TV",), "C": ("C",), "D_5P": ("D_5P",), "D_TV": ("D_TV",)}
OUTCOMES = ("INITIAL_FULL_STOP", "T1_THEN_BUFFER_STOP", "TARGET", "FORCED_EXIT")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def load_index_window(index: str, wid: str) -> dict:
    """The rows of one run: for NIFTY from the Phase 4 / Phase 3.6 directories (read-only), for the others from reports/phase5/<index>/windows/<wid>/."""
    if index == "NIFTY":
        parts = [R4.load_window(w, P4) for w in NIFTY_MAP[wid]]
        out = {k: [r for p in parts for r in p[k]] for k in parts[0]}
        return out
    d = OUT / index.lower() / "windows" / wid
    return {"trades": rd(d / "all_trades_detailed.csv"), "legs": rd(d / "trade_exits_detailed.csv"), "daily": rd(d / "daily_summary.csv"), "signals": rd(d / "all_strategy_signals.csv"), "rejected": rd(d / "rejected_signals.csv")}


def in_range(rows: list[dict], lo: date, hi: date) -> list[dict]:
    return [r for r in rows if str(lo) <= r["date"] <= str(hi)]


def order(trades: list[dict]) -> list[dict]:
    return sorted(trades, key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"])))


def pf(seq: list[float]):
    v = F4.profit_factor(seq)
    return None if v is None else ("inf" if v == math.inf else round(v, 4))


def rel(trades: list[dict]) -> dict:
    """Stop / target distances as a percentage of the entry price (the relative scale of the transferred index-point rules)."""
    def pct(key, t):
        return abs(fnum(t[key]) - fnum(t["entry_price"])) / fnum(t["entry_price"]) * 100.0
    if not trades:
        return {}
    return {"avg_entry_level": round(statistics.mean(fnum(t["entry_price"]) for t in trades), 1), "stop_pct_of_index": round(statistics.mean(pct("initial_stop", t) for t in trades), 4),
            "t1_pct_of_index": round(statistics.mean(pct("target_1", t) for t in trades), 4), "t2_pct_of_index": round(statistics.mean(pct("target_2", t) for t in trades), 4)}


def metrics(trades: list[dict], legs: list[dict], daily: list[dict], signals: list[dict], rejected: list[dict], cov: dict | None = None) -> dict:
    tr = order(trades)
    pts = [fnum(t["gross_pnl_points_weighted"]) for t in tr]
    n = len(tr)
    oc = Counter(t["outcome"] for t in tr)
    ids = {t["trade_id"] for t in tr}
    lg = [g for g in legs if g["trade_id"] in ids]
    l1 = Counter(g["exit_reason"] for g in lg if g["leg"] == "1")
    l2 = Counter(g["exit_reason"] for g in lg if g["leg"] == "2")
    hold = [fnum(t["bars_held"]) for t in tr if t.get("bars_held") not in (None, "")]
    dd, _ = F4.max_drawdown(pts)
    sessions = len(daily)
    conf = sum(int(fnum(d.get("confirmed_signals"))) for d in daily)
    valid = sum(int(fnum(d.get("fully_valid_signals"))) for d in daily)
    pdr = [t for t in tr if t["strategy"] == "PDR"]
    pdr_rej = Counter(r["failure_reason"].split("(")[0] for r in rejected if r["strategy"] == "PDR")
    row = {"sessions_evaluated": sessions, "confirmed_signals": conf, "fully_valid_signals": valid, "signals_per_session": round(conf / sessions, 3) if sessions else None, "executed_trades": n, "trades_per_session": round(n / sessions, 3) if sessions else None,
           "first_trades": sum(1 for t in tr if t["trade_no_of_day"] == "1"), "second_trades": sum(1 for t in tr if t["trade_no_of_day"] == "2"), **{f"trades_{s}": sum(1 for t in tr if t["strategy"] == s) for s in P.STRATEGIES},
           "win_rate_pct": round(100.0 * sum(1 for v in pts if v > 0) / n, 2) if n else None, "profit_factor_points": pf(pts), "gross_index_points": round(sum(pts), 2), "avg_points_per_trade": round(sum(pts) / n, 3) if n else None,
           "median_points_per_trade": round(statistics.median(pts), 3) if n else None, "max_drawdown_index_points": round(dd, 2), "max_consecutive_losses": F4.max_losing_streak(pts), "avg_holding_minutes": round(statistics.mean(hold), 1) if hold else None,
           "initial_full_stop_pct": round(100.0 * oc.get("INITIAL_FULL_STOP", 0) / n, 1) if n else None, "t1_reached_pct": round(100.0 * l1.get("TARGET_1", 0) / n, 1) if n else None, "t2_reached_pct": round(100.0 * l2.get("TARGET_2", 0) / n, 1) if n else None,
           "buffer_stop_after_t1_pct": round(100.0 * oc.get("T1_THEN_BUFFER_STOP", 0) / n, 1) if n else None, "forced_exit_pct": round(100.0 * oc.get("FORCED_EXIT", 0) / n, 1) if n else None,
           **{f"outcome_{k}": oc.get(k, 0) for k in OUTCOMES}, "same_minute_conflict_days": sum(1 for d in daily if d.get("day_end_portfolio_state") == "UNRESOLVED_EXECUTION"),
           "pdr_trades": len(pdr), "pdr_setups_rejected_total": sum(pdr_rej.values()), "pdr_open_not_above_zone": pdr_rej.get("OPEN_NOT_STRICTLY_ABOVE_ZONE", 0),
           "pdr_open_not_above_zone_per_pdr_trade": round(pdr_rej.get("OPEN_NOT_STRICTLY_ABOVE_ZONE", 0) / len(pdr), 2) if pdr else None, **rel(tr),
           "gross_rs_fixed_390_synthetic": round(sum(fnum(t["gross_pnl_rs"]) for t in tr), 2), "net_rs_fixed_390_illustrative": round(sum(fnum(t["illustrative_net_pnl_rs"]) for t in tr), 2)}
    if cov:
        row.update(cov)
    return row


def coverage_for(index: str, wid: str, lo: date, hi: date) -> dict:
    """Session coverage of the run window (expected, supplied, usable) restricted to the row's dates, from the quality table."""
    if index == "NIFTY":
        return {}
    d = OUT / index.lower() / "data"
    q = [r for r in rd(d / "session_quality_all_windows.csv") if r["window"] == wid and str(lo) <= r["date"] <= str(hi)]
    return {"sessions_in_source": len(q), "sessions_usable": sum(1 for r in q if r["usable"] == "True"), "sessions_excluded": sum(1 for r in q if r["usable"] != "True")}


def build_rows(index: str, windows: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict]]:
    ann, strat, cost = [], [], []
    for rid, _label, wid, lo, hi, status, src in ROWS:
        w = windows.get(wid)
        if w is None:
            continue
        tr, dl = in_range(w["trades"], lo, hi), in_range(w["daily"], lo, hi)
        ids = {t["trade_id"] for t in tr}
        lg = [g for g in w["legs"] if g["trade_id"] in ids]
        m = metrics(tr, lg, dl, in_range(w["signals"], lo, hi), in_range(w["rejected"], lo, hi), coverage_for(index, wid, lo, hi))
        ann.append({"index": index, "row_id": rid, "period": f"{lo}..{hi}", "status": status, "minute_source": src if index != "NIFTY" else ("5paisa + Phase 3.6 reference" if wid == "M" else src), **m})
        for s in P.STRATEGIES:
            st = [t for t in tr if t["strategy"] == s]
            sm = metrics(st, lg, [], [], [], None)
            strat.append({"index": index, "row_id": rid, "period": f"{lo}..{hi}", "status": status, "strategy": s, "trades": len(st), "first_trades": sm["first_trades"], "second_trades": sm["second_trades"], "win_rate_pct": sm["win_rate_pct"],
                          "profit_factor_points": sm["profit_factor_points"], "gross_index_points": sm["gross_index_points"], "avg_points_per_trade": sm["avg_points_per_trade"], "max_drawdown_index_points": sm["max_drawdown_index_points"],
                          "initial_full_stop_pct": sm["initial_full_stop_pct"], "t1_reached_pct": sm["t1_reached_pct"], "t2_reached_pct": sm["t2_reached_pct"], "avg_holding_minutes": sm["avg_holding_minutes"],
                          "stop_pct_of_index": sm.get("stop_pct_of_index"), "t1_pct_of_index": sm.get("t1_pct_of_index"), "gross_rs_fixed_390_synthetic": sm["gross_rs_fixed_390_synthetic"]})
        for r in F4.cost_scenarios(tr, lg):
            cost.append({"index": index, "row_id": rid, "period": f"{lo}..{hi}", "status": status, "unit_note": "synthetic: fixed 390 units; Rs figures are per-index comparison devices, not contract P&L", **r})
    return ann, strat, cost


def vendor_sensitivity(index: str, windows: dict[str, dict]) -> list[dict]:
    """The same frozen system on the same dates with the two minute sources (5paisa vs the secondary repository): how much of the trade set and the result is a property of the data source."""
    rows = []
    pairs = (("M", "MS", date(2022, 9, 1), date(2024, 3, 22), "2022-09-01..2024-03-22: 5paisa vs secondary-source minutes"), ("D_5P", "D_TV", date(2019, 3, 1), date(2019, 12, 31), "2019-03..12: 5paisa vs secondary-source minutes (sessions of both)"))
    for a, b, lo, hi, label in pairs:
        ta, tb = in_range(windows[a]["trades"], lo, hi), in_range(windows[b]["trades"], lo, hi)
        have_a, have_b = {d["date"] for d in in_range(windows[a]["daily"], lo, hi)}, {d["date"] for d in in_range(windows[b]["daily"], lo, hi)}
        both = have_a & have_b
        ta, tb = [t for t in ta if t["date"] in both], [t for t in tb if t["date"] in both]
        key = lambda t: (t["date"], t["trade_no_of_day"], t["strategy"], t["method"], t["direction"], t["signal_candle_end"])  # noqa: E731
        ka, kb = {key(t): t for t in ta}, {key(t): t for t in tb}
        common = set(ka) & set(kb)
        sa = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in in_range(windows[a]["signals"], lo, hi) if s["date"] in both}
        sb = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in in_range(windows[b]["signals"], lo, hi) if s["date"] in both}
        pts = lambda rows_: round(sum(fnum(t["gross_pnl_points_weighted"]) for t in rows_), 2)  # noqa: E731
        rows.append({"index": index, "comparison": label, "sessions_in_both": len(both), "trades_5paisa": len(ta), "trades_secondary": len(tb), "identical_trade_signals": len(common),
                     "same_outcome_among_identical": sum(1 for k in common if ka[k]["outcome"] == kb[k]["outcome"]), "trades_only_5paisa": len(set(ka) - set(kb)), "trades_only_secondary": len(set(kb) - set(ka)),
                     "gross_index_points_5paisa": pts(ta), "gross_index_points_secondary": pts(tb), "points_on_identical_trades_5paisa": pts([ka[k] for k in common]), "points_on_identical_trades_secondary": pts([kb[k] for k in common]),
                     "points_on_trades_only_5paisa": pts([ka[k] for k in set(ka) - set(kb)]), "points_on_trades_only_secondary": pts([kb[k] for k in set(kb) - set(ka)]),
                     "confirmed_signals_5paisa": len(sa), "confirmed_signals_secondary": len(sb), "signals_in_both": len(sa & sb), "signal_agreement_pct_of_union": round(100.0 * len(sa & sb) / len(sa | sb), 1) if (sa | sb) else None})
    return rows


def common_session_dates(per_index: dict[str, dict[str, dict]], wid: str, lo: date, hi: date) -> set[str]:
    sets = [{d["date"] for d in in_range(per_index[i][wid]["daily"], lo, hi)} for i in INDEX_NAMES]
    return set.intersection(*sets)


def common_comparison(per_index: dict[str, dict[str, dict]]) -> tuple[list[dict], list[dict]]:
    """The three indices over EXACTLY the same sessions (those evaluated on all three), per Sep-Aug year and for the whole main window; plus the daily agreement between indices."""
    rows, agree = [], []
    spans = [("M_2022_23", date(2022, 9, 1), date(2023, 8, 31)), ("M_2023_24", date(2023, 9, 1), date(2024, 8, 31)), ("M_2024_25", date(2024, 9, 1), date(2025, 8, 31)), ("M_2025_26", date(2025, 9, 1), date(2026, 8, 31)),
             ("M_ALL", date(2022, 9, 1), date(2026, 8, 31))]
    for rid, lo, hi in spans:
        common = common_session_dates(per_index, "M", lo, hi)
        for i in INDEX_NAMES:
            w = per_index[i]["M"]
            tr = [t for t in in_range(w["trades"], lo, hi) if t["date"] in common]
            dl = [d for d in in_range(w["daily"], lo, hi) if d["date"] in common]
            ids = {t["trade_id"] for t in tr}
            lg = [g for g in w["legs"] if g["trade_id"] in ids]
            m = metrics(tr, lg, dl, [s for s in in_range(w["signals"], lo, hi) if s["date"] in common], [r for r in in_range(w["rejected"], lo, hi) if r["date"] in common])
            rows.append({"row_id": rid, "index": i, "common_sessions": len(common), **{k: m[k] for k in ("executed_trades", "win_rate_pct", "profit_factor_points", "gross_index_points", "avg_points_per_trade", "max_drawdown_index_points", "initial_full_stop_pct",
                                                                                                         "t1_reached_pct", "t2_reached_pct", "avg_holding_minutes", "same_minute_conflict_days", "stop_pct_of_index", "t1_pct_of_index", "avg_entry_level")}})
    # daily agreement on the common sessions of the whole main window
    common = common_session_dates(per_index, "M", date(2022, 9, 1), date(2026, 8, 31))
    by = {}
    for i in INDEX_NAMES:
        day = defaultdict(lambda: {"n": 0, "pts": 0.0, "dirs": set(), "first_strat": ""})
        for t in order(per_index[i]["M"]["trades"]):
            if t["date"] in common:
                x = day[t["date"]]
                x["n"] += 1
                x["pts"] += fnum(t["gross_pnl_points_weighted"])
                x["dirs"].add(t["direction"])
                if t["trade_no_of_day"] == "1":
                    x["first_strat"] = t["strategy"] + ":" + t["direction"]
        by[i] = day
    pairs = (("NIFTY", "BANKNIFTY"), ("NIFTY", "SENSEX"), ("BANKNIFTY", "SENSEX"))
    ds = sorted(common)
    for a, b in pairs:
        xa = [by[a][d]["pts"] if d in by[a] else 0.0 for d in ds]
        xb = [by[b][d]["pts"] if d in by[b] else 0.0 for d in ds]
        both = [d for d in ds if d in by[a] and d in by[b]]
        either = [d for d in ds if d in by[a] or d in by[b]]
        same_first = sum(1 for d in both if by[a][d]["first_strat"] and by[a][d]["first_strat"] == by[b][d]["first_strat"])
        same_dir = sum(1 for d in both if by[a][d]["dirs"] == by[b][d]["dirs"])
        same_sign = sum(1 for d in both if (by[a][d]["pts"] > 0) == (by[b][d]["pts"] > 0))
        ma, mb = statistics.mean(xa), statistics.mean(xb)
        sa, sb = statistics.pstdev(xa), statistics.pstdev(xb)
        corr = (sum((p - ma) * (q - mb) for p, q in zip(xa, xb, strict=True)) / len(xa)) / (sa * sb) if sa and sb else None
        agree.append({"pair": f"{a} vs {b}", "common_sessions": len(ds), "sessions_with_a_trade_on_either": len(either), "sessions_with_a_trade_on_both": len(both),
                      "both_first_trade_same_strategy_and_direction": same_first, "both_same_set_of_directions": same_dir, "both_same_sign_of_day_result": same_sign,
                      "pct_of_both_same_first_signal": round(100.0 * same_first / len(both), 1) if both else None, "pct_of_both_same_sign": round(100.0 * same_sign / len(both), 1) if both else None,
                      "correlation_of_daily_index_points": None if corr is None else round(corr, 3), "note": "daily index-point results on the common sessions (0 when no trade); correlation of points across different index levels is a rough co-movement measure only"})
    return rows, agree


def cumulative_points(per_index: dict[str, dict[str, dict]]) -> dict[str, list[tuple[str, float]]]:
    out = {}
    for i in INDEX_NAMES:
        cum, pts = 0.0, []
        for t in order(per_index[i]["M"]["trades"]):
            cum += fnum(t["gross_pnl_points_weighted"])
            pts.append((t["date"], cum))
        out[i] = pts
    return out


def line_chart_svg(series: dict[str, list[tuple[str, float]]], title: str, ylabel: str) -> str:
    W, H, L, Rg, T, Bt = 900, 420, 70, 20, 40, 40
    allv = [v for s in series.values() for _d, v in s] or [0.0]
    ymin, ymax = min(min(allv), 0.0), max(max(allv), 0.0)
    pad = (ymax - ymin) * 0.05 or 1.0
    ymin, ymax = ymin - pad, ymax + pad
    dates = sorted({d for s in series.values() for d, _v in s})
    x0 = date.fromisoformat(dates[0]).toordinal() if dates else 0
    x1 = date.fromisoformat(dates[-1]).toordinal() if dates else 1
    sx = lambda d: L + (date.fromisoformat(d).toordinal() - x0) / max(x1 - x0, 1) * (W - L - Rg)  # noqa: E731
    sy = lambda v: T + (ymax - v) / (ymax - ymin) * (H - T - Bt)  # noqa: E731
    colors = {"NIFTY": "#1565c0", "BANKNIFTY": "#c62828", "SENSEX": "#2e7d32"}
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="12">', f'<rect width="{W}" height="{H}" fill="white"/>', f'<text x="{L}" y="22" font-size="14" font-weight="bold">{title}</text>']
    for k in range(6):
        v = ymin + (ymax - ymin) * k / 5
        parts.append(f'<line x1="{L}" y1="{sy(v):.1f}" x2="{W - Rg}" y2="{sy(v):.1f}" stroke="#e0e0e0"/><text x="{L - 6}" y="{sy(v) + 4:.1f}" text-anchor="end">{v:,.0f}</text>')
    parts.append(f'<line x1="{L}" y1="{sy(0):.1f}" x2="{W - Rg}" y2="{sy(0):.1f}" stroke="#555"/>')
    for yr in range(date.fromisoformat(dates[0]).year, date.fromisoformat(dates[-1]).year + 1) if dates else []:
        d = f"{yr}-01-01"
        if dates[0] <= d <= dates[-1]:
            parts.append(f'<line x1="{sx(d):.1f}" y1="{T}" x2="{sx(d):.1f}" y2="{H - Bt}" stroke="#eee"/><text x="{sx(d):.1f}" y="{H - 20}" text-anchor="middle">{yr}</text>')
    for k, (name, s) in enumerate(series.items()):
        if s:
            pts = " ".join(f"{sx(d):.1f},{sy(v):.1f}" for d, v in s)
            parts.append(f'<polyline fill="none" stroke="{colors.get(name, "#000")}" stroke-width="1.6" points="{pts}"/><text x="{L + 10 + 150 * k}" y="{T + 14}" fill="{colors.get(name, "#000")}">&#9632; {name}</text>')
    parts.append(f'<text x="14" y="{(T + H - Bt) / 2:.0f}" transform="rotate(-90 14 {(T + H - Bt) / 2:.0f})" text-anchor="middle">{ylabel}</text></svg>')
    return "\n".join(parts)


def build_all(out: Path = OUT) -> dict:
    per_index: dict[str, dict[str, dict]] = {}
    for i in INDEX_NAMES:
        per_index[i] = {w: load_index_window(i, w) for w in (NIFTY_MAP if i == "NIFTY" else ("M", "MS", "C", "D_5P", "D_TV"))}
    comp_dir = out / "comparison"
    comp_dir.mkdir(parents=True, exist_ok=True)
    all_ann, all_strat, all_cost = [], [], []
    for i in INDEX_NAMES:
        ann, strat, cost = build_rows(i, per_index[i])
        all_ann += ann
        all_strat += strat
        all_cost += cost
        if i != "NIFTY":
            d = out / i.lower()
            write_csv(d / "annual_comparison.csv", ann)
            write_csv(d / "strategy_performance.csv", strat)
            write_csv(d / "cost_sensitivity.csv", cost)
            write_csv(d / "vendor_sensitivity.csv", vendor_sensitivity(i, per_index[i]))
            # compiled per-index views of the per-window files (window_id first column)
            for src, dst in (("all_trades_detailed.csv", "trade_level_signals.csv"), ("daily_summary.csv", "daily_summary.csv"), ("trade_entry_conditions.csv", "entry_explanations.csv"), ("trade_exits_detailed.csv", "exit_explanations.csv")):
                rows = []
                for w in ("M", "MS", "C", "D_5P", "D_TV"):
                    rows += [{"window_id": w, **r} for r in rd(d / "windows" / w / src)]
                write_csv(d / dst, rows)
            mp = []
            win = per_index[i]
            for rid, _label, wid, lo, hi, status, _src in ROWS:
                months: dict[str, float] = defaultdict(float)
                for t in in_range(win[wid]["trades"], lo, hi):
                    months[t["date"][:7]] += fnum(t["gross_pnl_points_weighted"])
                mp += [{"index": i, "row_id": rid, "month": m, "gross_index_points": round(v, 2), "status": status} for m, v in sorted(months.items())]
            write_csv(d / "monthly_index_points.csv", mp)
    write_csv(comp_dir / "cross_index_by_period.csv", all_ann)
    write_csv(comp_dir / "cross_index_by_strategy.csv", all_strat)
    write_csv(comp_dir / "cost_sensitivity_all_indices.csv", all_cost)
    common, agree = common_comparison(per_index)
    write_csv(comp_dir / "common_sessions_comparison.csv", common)
    write_csv(comp_dir / "daily_agreement_between_indices.csv", agree)
    cum = cumulative_points(per_index)
    (comp_dir / "cumulative_index_points_main_window.svg").write_text(line_chart_svg(cum, "Cumulative weighted index points, main window 2022-09..2026-08 (each index in its OWN points; frozen NIFTY point rules)", "index points"))
    return {"periods": len(all_ann), "common": len(common), "agree": len(agree)}


# ------------------------------------------------------------------------------------------------------------------------------ per-index verification workbooks
def write_index_workbook(index: str, out: Path = OUT) -> Path:
    """<INDEX>_Daily_Verification.xlsx, written from the CSV files of reports/phase5/<index>/ (no value is computed here)."""
    from openpyxl import Workbook
    from openpyxl.styles import Font

    from nifty_trading.research.phase4_xlsx import sheet
    d = out / index.lower()
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    lines = [f"{index} ({D5.INDEXES[index].display}) - Phase 5 cross-index backtest verification workbook",
             "FROZEN Phase 3.6 configuration (IRF, ORB, PDR body-based, PDS, RF; shared controller) with the NIFTY index-POINT stops and targets UNCHANGED on this index. HISTORICAL RESEARCH ONLY: the strategy was developed using later NIFTY data.",
             "INDEX-POINT RESULTS ONLY. No option premium is used or estimated; an index-point gain is not an option-premium gain. Rupee columns use a fixed 390-unit comparison multiplier and are not contract P&L and not comparable across indices.",
             "Window status: DATA_VALIDATED (5paisa; the DATA window passed the quality gate - this says nothing about the strategy), VENDOR_SENSITIVITY, EXPLORATORY (secondary source only), PARTIAL_YEAR.",
             "Sheets are written from the CSV files of this directory; composite trade key = window_id | trade_id; daily journals and charts are under daily/<window>/ and charts/<window>/."]
    for i, line in enumerate(lines, 1):
        ws.cell(row=i, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=14)
    ws.column_dimensions["A"].width = 170
    for name, fn in (("Annual", "annual_comparison.csv"), ("Strategy", "strategy_performance.csv"), ("Cost Sensitivity", "cost_sensitivity.csv"), ("Monthly Points", "monthly_index_points.csv"), ("Daily Summary", "daily_summary.csv"),
                     ("Trades", "trade_level_signals.csv"), ("Exits", "exit_explanations.csv"), ("Entry Conditions", "entry_explanations.csv"), ("Coverage", "data/historical_coverage_by_window.csv"), ("Session Quality", "data/session_quality_all_windows.csv"),
                     ("Vendor Overlap Monthly", "data/vendor_overlap_by_month.csv")):
        sheet(wb, name, rd(d / fn), {"calculation": 60, "observed": 80, "required": 40, "why_it_matters": 50})
    path = d / f"{index}_Daily_Verification.xlsx"
    wb.save(path)
    return path
