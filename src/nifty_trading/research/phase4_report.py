"""Phase 4: multi-period comparison, cost sensitivity, regime and robustness tables, vendor sensitivity and the multi-year workbook, built ONLY from the written trade / exit / daily tables of each window
(so every number can be recomputed from the CSV files). The Phase 3.6 reference window (A) is read from its own directory and is never modified.

Regime thresholds are fixed round numbers declared here BEFORE any regime table was produced (they were written after the five windows had been run once for sanity checks, but no regime or robustness
result had been looked at); they are not fitted. Nothing in this module changes a strategy, a stop, a target, the cutoff or the controller.
"""

from __future__ import annotations

import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from nifty_trading.data.sessions import load_daily_official
from nifty_trading.research import phase3 as P
from nifty_trading.research import phase4 as F
from nifty_trading.research import phase4_data as D
from nifty_trading.research.phase35 import write_csv

ROOT = D.ROOT
A_DIR = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
# predeclared regime measurements (annualised % / efficiency ratio); computed from index closes strictly BEFORE the session
RV_WINDOW, RV_LOW, RV_HIGH = 20, 10.0, 16.0
ER_WINDOW, ER_TREND = 60, 0.25
ENTRY_BUCKETS = (("09:20-09:59", "09:20", "09:59"), ("10:00-10:59", "10:00", "10:59"), ("11:00-11:59", "11:00", "11:59"), ("12:00-13:00", "12:00", "13:00"))

# (row id, label, window dir id, start, end, data source label, status, confidence tier)
ROWS = [
    ("C_2018", "2018 (2018-01-01..2018-12-31)", "C", date(2018, 1, 1), date(2018, 12, 31), "secondary vendor minutes + 5paisa daily", "EXPLORATORY", "EXPLORATORY_UNVERIFIABLE"),
    ("D_2019_SECONDARY", "2019 full year (secondary vendor)", "D_TV", date(2019, 1, 1), date(2019, 12, 31), "secondary vendor minutes + 5paisa daily", "EXPLORATORY", "EXPLORATORY_UNVERIFIABLE"),
    ("D_2019_5PAISA_PARTIAL", "2019-03-01..2019-12-31 (5paisa, PARTIAL YEAR)", "D_5P", date(2019, 3, 1), date(2019, 12, 31), "5paisa minutes + 5paisa daily", "PARTIAL_YEAR", "LOW"),
    ("B1_2022_23", "2022-09-01..2023-08-31", "B", date(2022, 9, 1), date(2023, 8, 31), "5paisa minutes + 5paisa daily", "DATA_VALIDATED", "MODERATE"),
    ("B2_2023_24", "2023-09-01..2024-08-31", "B", date(2023, 9, 1), date(2024, 8, 31), "5paisa minutes + 5paisa daily", "DATA_VALIDATED", "MODERATE"),
    ("B3_2024_25", "2024-09-01..2025-08-31", "B", date(2024, 9, 1), date(2025, 8, 31), "5paisa minutes + 5paisa daily", "DATA_VALIDATED", "MODERATE"),
    ("B_2022_25", "2022-09-01..2025-08-31 (three years)", "B", date(2022, 9, 1), date(2025, 8, 31), "5paisa minutes + 5paisa daily", "DATA_VALIDATED", "MODERATE"),
    ("A_2025_26", "2025-09-01..2026-08-31 (Phase 3.6 reference)", "A", date(2025, 9, 1), date(2026, 8, 31), "5paisa Phase 1 dataset", "REFERENCE", "HIGH"),
    ("B1_TV", "2022-09-01..2023-08-31 (secondary vendor)", "B_TV", date(2022, 9, 1), date(2023, 8, 31), "secondary vendor minutes + 5paisa daily", "VENDOR_SENSITIVITY", "MODERATE"),
    ("B2_TV", "2023-09-01..2024-08-31 (secondary vendor)", "B_TV", date(2023, 9, 1), date(2024, 8, 31), "secondary vendor minutes + 5paisa daily", "VENDOR_SENSITIVITY", "MODERATE"),
    ("B3_TV", "2024-09-01..2025-08-31 (secondary vendor)", "B_TV", date(2024, 9, 1), date(2025, 8, 31), "secondary vendor minutes + 5paisa daily", "VENDOR_SENSITIVITY", "MODERATE"),
    ("B_2022_25_TV", "2022-09-01..2025-08-31 (secondary vendor)", "B_TV", date(2022, 9, 1), date(2025, 8, 31), "secondary vendor minutes + 5paisa daily", "VENDOR_SENSITIVITY", "MODERATE"),
]
CONFIDENCE_RUBRIC = {
    "HIGH": "same provider as the Phase 3.6 baseline, full coverage, >= 99% of sessions usable, official daily closes, and a second vendor overlaps with mean |1-minute close difference| <= 0.10 point",
    "MODERATE": "same provider as the baseline, >= 98% of sessions usable, official daily closes, a second vendor overlaps but mean |difference| > 0.10 point (the vendors' minute bars differ)",
    "LOW": "single provider with a partial year and / or provider gaps, and a second vendor that differs materially",
    "EXPLORATORY_UNVERIFIABLE": "the minute source cannot be checked against an independent vendor for (part of) the period; treat as exploratory only",
}


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def load_window(wid: str, out: Path) -> dict:
    d = A_DIR if wid == "A" else out / "windows" / wid
    legs_name = "exit_details.csv" if wid == "A" else "trade_exits_detailed.csv"
    return {"trades": rd(d / "all_trades_detailed.csv"), "legs": rd(d / legs_name), "daily": rd(d / "daily_summary.csv"), "signals": rd(d / "all_strategy_signals.csv"), "rejected": rd(d / "rejected_signals.csv")}


def in_range(rows: list[dict], lo: date, hi: date) -> list[dict]:
    return [r for r in rows if str(lo) <= r["date"] <= str(hi)]


def flat(m: dict) -> dict:
    out = {k: v for k, v in m.items() if not isinstance(v, dict)}
    for k, v in m["strategy_gross_rs"].items():
        out[f"gross_rs_{k}"] = v
    return out


# ------------------------------------------------------------------------------------------------------------------------------ regimes
def daily_closes() -> list[tuple[date, float]]:
    p1 = {r.date: r.close for r in load_daily_official().itertuples(index=False)}
    p4 = {r.date: r.close for r in D.load_processed_daily(D.SRC_5P_DAILY).itertuples(index=False)}
    merged = {**p4, **p1}  # the same vendor; the Phase 1 series wins where they overlap
    return sorted(merged.items())


def regime_of(closes: list[tuple[date, float]], d: date) -> dict:
    prior = [c for dt, c in closes if dt < d]
    if len(prior) < ER_WINDOW + 1:
        return {"vol": "UNKNOWN", "trend": "UNKNOWN", "rv20": None, "er60": None}
    r = [math.log(prior[i] / prior[i - 1]) for i in range(len(prior) - RV_WINDOW, len(prior))]
    mean = sum(r) / len(r)
    rv = math.sqrt(sum((x - mean) ** 2 for x in r) / (len(r) - 1)) * math.sqrt(252) * 100.0
    seg = prior[-(ER_WINDOW + 1):]
    net = seg[-1] - seg[0]
    path = sum(abs(seg[i] - seg[i - 1]) for i in range(1, len(seg)))
    er = abs(net) / path if path else 0.0
    vol = "LOW_VOL" if rv < RV_LOW else ("HIGH_VOL" if rv >= RV_HIGH else "MID_VOL")
    trend = ("TRENDING_UP" if net > 0 else "TRENDING_DOWN") if er >= ER_TREND else "SIDEWAYS"
    return {"vol": vol, "trend": trend, "rv20": round(rv, 2), "er60": round(er, 4)}


# ------------------------------------------------------------------------------------------------------------------------------ builders
def annual_tables(win: dict[str, dict]) -> tuple[list[dict], list[dict], list[dict], list[dict], list[dict]]:
    annual, strat, costs, monthly, coverage = [], [], [], [], []
    for rid, label, wid, lo, hi, src, status, conf in ROWS:
        w = win[wid]
        trades, daily = in_range(w["trades"], lo, hi), in_range(w["daily"], lo, hi)
        legs_ids = {t["trade_id"] for t in trades}
        legs = [g for g in w["legs"] if g["trade_id"] in legs_ids]
        m = F.window_metrics(trades, daily, label)
        annual.append({"row_id": rid, "window_dir": wid, "period": f"{lo}..{hi}", "data_source": src, "status": conf and status, "data_quality_confidence": conf, **flat(m)})
        for s in P.STRATEGIES:
            st = [t for t in trades if t["strategy"] == s]
            seq = F.pnl_seq(st)
            pf = F.profit_factor(seq)
            strat.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "strategy": s, "trades": len(st), "first_trades": sum(1 for t in st if t["trade_no_of_day"] == "1"), "second_trades": sum(1 for t in st if t["trade_no_of_day"] == "2"),
                          "gross_pnl_rs": round(sum(seq), 2), "net_pnl_rs": round(sum(F.pnl_seq(st, "illustrative_net_pnl_rs")), 2), "win_rate_pct": round(100.0 * sum(1 for v in seq if v > 0) / len(seq), 2) if seq else None,
                          "profit_factor_gross": None if pf is None else ("inf" if pf == math.inf else round(pf, 4)), "avg_trade_rs": round(sum(seq) / len(seq), 2) if seq else None,
                          "max_drawdown_rs": round(F.max_drawdown(seq)[0], 2), "share_of_window_gross_pct": round(100.0 * sum(seq) / m["gross_pnl_rs_fixed_390"], 1) if m["gross_pnl_rs_fixed_390"] > 0 else None})  # blank when the window total is not positive: a share of a zero or negative total is meaningless
        for r in F.cost_scenarios(trades, legs):
            costs.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, **r})
        for mo in m["monthly_gross_rs"]:
            monthly.append({"row_id": rid, "month": mo, "gross_pnl_rs": m["monthly_gross_rs"][mo], "net_pnl_rs": m["monthly_net_rs"][mo], "status": status})
    return annual, strat, costs, monthly, coverage


def regime_tables(win: dict[str, dict]) -> list[dict]:
    closes = daily_closes()
    cache: dict[date, dict] = {}
    rows = []
    for rid, _label, wid, lo, hi, _src, status, _conf in ROWS:
        if rid in ("B_2022_25", "B_2022_25_TV"):
            continue  # the annual slices cover it
        w = win[wid]
        trades, daily = in_range(w["trades"], lo, hi), in_range(w["daily"], lo, hi)
        by = defaultdict(lambda: {"sessions": 0, "trades": 0, "gross": 0.0, "wins": 0})
        for dd in daily:
            d = date.fromisoformat(dd["date"])
            cache.setdefault(d, regime_of(closes, d))
            rg = cache[d]
            for key in (("VOL", rg["vol"]), ("TREND", rg["trend"]), ("CELL", f"{rg['vol']}|{rg['trend']}")):
                by[key]["sessions"] += 1
        for t in trades:
            d = date.fromisoformat(t["date"])
            rg = cache.setdefault(d, regime_of(closes, d))
            for key in (("VOL", rg["vol"]), ("TREND", rg["trend"]), ("CELL", f"{rg['vol']}|{rg['trend']}")):
                by[key]["trades"] += 1
                by[key]["gross"] += F.fnum(t["gross_pnl_rs"])
                by[key]["wins"] += F.fnum(t["gross_pnl_rs"]) > 0
        for (kind, name), v in sorted(by.items()):
            rows.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "regime_dimension": kind, "regime": name, "sessions": v["sessions"], "trades": v["trades"], "gross_pnl_rs": round(v["gross"], 2),
                         "avg_trade_rs": round(v["gross"] / v["trades"], 2) if v["trades"] else None, "win_rate_pct": round(100.0 * v["wins"] / v["trades"], 2) if v["trades"] else None})
    return rows


def session_regimes(win: dict[str, dict]) -> list[dict]:
    closes = daily_closes()
    out = []
    for rid, _label, wid, lo, hi, _src, _status, _conf in ROWS:
        if rid.startswith(("B1", "B2", "B3")):
            continue  # the annual slices are subsets of the whole-window rows
        for dd in in_range(win[wid]["daily"], lo, hi):
            rg = regime_of(closes, date.fromisoformat(dd["date"]))
            out.append({"row_id": rid, "date": dd["date"], **rg})
    return out


def entry_time_table(win: dict[str, dict]) -> list[dict]:
    rows = []
    for rid, _label, wid, lo, hi, _src, status, _conf in ROWS:
        if rid in ("B_2022_25", "B_2022_25_TV"):
            continue
        trades = in_range(win[wid]["trades"], lo, hi)
        for name, a, b in ENTRY_BUCKETS:
            sel = [t for t in trades if a <= t["fill_timestamp"][-5:] <= b]
            seq = F.pnl_seq(sel)
            rows.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "entry_time_bucket": name, "trades": len(sel), "gross_pnl_rs": round(sum(seq), 2), "avg_trade_rs": round(sum(seq) / len(seq), 2) if seq else None,
                         "win_rate_pct": round(100.0 * sum(1 for v in seq if v > 0) / len(seq), 2) if seq else None, "initial_full_stops": sum(1 for t in sel if t["outcome"] == "INITIAL_FULL_STOP")})
    return rows


def concentration_table(win: dict[str, dict]) -> list[dict]:
    rows = []
    for rid, _label, wid, lo, hi, _src, status, _conf in ROWS:
        trades = in_range(win[wid]["trades"], lo, hi)
        seq = sorted(F.pnl_seq(trades), reverse=True)
        total = sum(seq)
        gp = sum(v for v in seq if v > 0)
        n = len(seq)
        top = lambda k, s=seq: sum(s[:k])  # noqa: E731
        rows.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "trades": n, "gross_pnl_rs": round(total, 2), "gross_profit_rs": round(gp, 2), "top1_win_rs": round(top(1), 2) if n else None, "top5_wins_rs": round(top(5), 2) if n else None,
                     "top10_wins_rs": round(top(10), 2) if n else None, "top5_share_of_gross_profit_pct": round(100.0 * top(5) / gp, 1) if gp else None, "top10pct_trades_share_of_gross_profit_pct": round(100.0 * top(max(1, n // 10)) / gp, 1) if gp else None,
                     "gross_pnl_excluding_top5_wins_rs": round(total - top(5), 2) if n else None, "gross_pnl_excluding_top10pct_wins_rs": round(total - top(max(1, n // 10)), 2) if n else None,
                     "positive_trades_needed_for_half_of_gross_profit": next((i + 1 for i in range(n) if sum(seq[:i + 1]) >= gp / 2), None) if gp else None})
    return rows


def data_quality_table(win: dict[str, dict], out: Path) -> list[dict]:
    """Trades on sessions with a PREDECLARED data issue (missing regular minutes, a frozen-price run, an abnormal 09:15 bar, or an extreme 1-minute candle) versus the rest. The generic pipeline flag
    'official close differs from the last print' is on ~99% of sessions and is deliberately NOT used here."""
    q = rd(out / "data" / "session_quality_all_windows.csv")
    issue = {(r["window"], r["date"]) for r in q if int(float(r["missing_regular_minutes"] or 0)) > 0 or int(float(r["frozen_rows_ge5"] or 0)) > 0 or r["abnormal_first_bar"] == "True" or int(float(r["extreme_1m_candles"] or 0)) > 0}
    rows = []
    for rid, _label, wid, lo, hi, _src, status, _conf in ROWS:
        if wid == "A":
            rows.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "sessions_with_data_issue": "n/a", "note": "no Phase 4 session-quality table exists for the Phase 1 dataset (validated in Phase 2.1)"})
            continue
        flagged = {d for (w, d) in issue if w == wid and str(lo) <= d <= str(hi)}
        trades = in_range(win[wid]["trades"], lo, hi)
        a = [t for t in trades if t["date"] in flagged]
        b = [t for t in trades if t["date"] not in flagged]
        rows.append({"row_id": rid, "period": f"{lo}..{hi}", "status": status, "sessions_with_data_issue": len(flagged), "trades_on_issue_sessions": len(a), "gross_on_issue_sessions_rs": round(sum(F.pnl_seq(a)), 2),
                     "trades_on_other_sessions": len(b), "gross_on_other_sessions_rs": round(sum(F.pnl_seq(b)), 2),
                     "note": "data issue = missing regular minutes, frozen-price run, abnormal 09:15 bar or an extreme 1-minute candle (predeclared); the sets are small, so this is a disclosure, not evidence; no session is excluded from the main result"})
    return rows


def not_evaluated_table(win: dict[str, dict]) -> list[dict]:
    rows = []
    for wid in ("B", "B_TV", "C", "D_5P", "D_TV", "A"):
        rej = [r for r in win[wid]["rejected"] if r["category"] == "ENGINE_NOT_EVALUATED"]
        c = Counter((r["strategy"], r["failure_reason"].split("(")[0][:60], r["failure_reason"][len(r["failure_reason"].split("(")[0]) + 1:].split(")")[0][:90]) for r in rej)
        for (s, why, detail), n in sorted(c.items()):
            rows.append({"window_dir": wid, "strategy": s, "reason": why, "detail": detail, "strategy_sessions": n})
    return rows


def vendor_sensitivity(win: dict[str, dict]) -> list[dict]:
    rows = []
    pairs = (("B", "B_TV", date(2022, 9, 1), date(2025, 8, 31), "Window B: 5paisa vs secondary-vendor minutes"), ("D_5P", "D_TV", date(2019, 3, 1), date(2019, 12, 31), "2019-03..12: 5paisa vs secondary-vendor minutes (sessions of both)"))
    for a, b, lo, hi, label in pairs:
        ta, tb = in_range(win[a]["trades"], lo, hi), in_range(win[b]["trades"], lo, hi)
        if a == "D_5P":
            have = {d["date"] for d in win[a]["daily"]}
            tb = [t for t in tb if t["date"] in have]
        key = lambda t: (t["date"], t["trade_no_of_day"], t["strategy"], t["method"], t["direction"], t["signal_candle_end"])  # noqa: E731
        ka, kb = {key(t): t for t in ta}, {key(t): t for t in tb}
        common = set(ka) & set(kb)
        same_out = sum(1 for k in common if ka[k]["outcome"] == kb[k]["outcome"])
        sa = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in win[a]["signals"] if lo <= date.fromisoformat(s["date"]) <= hi}
        sb = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in win[b]["signals"] if lo <= date.fromisoformat(s["date"]) <= hi}
        if a == "D_5P":
            have = {d["date"] for d in win[a]["daily"]}
            sb = {x for x in sb if x[0] in have}
        rows.append({"comparison": label, "trades_vendor_a": len(ta), "trades_vendor_b": len(tb), "identical_trade_signals": len(common), "same_outcome_among_identical": same_out,
                     "trades_only_vendor_a": len(set(ka) - set(kb)), "trades_only_vendor_b": len(set(kb) - set(ka)), "gross_rs_vendor_a": round(sum(F.pnl_seq(ta)), 2), "gross_rs_vendor_b": round(sum(F.pnl_seq(tb)), 2),
                     "net_rs_vendor_a": round(sum(F.pnl_seq(ta, "illustrative_net_pnl_rs")), 2), "net_rs_vendor_b": round(sum(F.pnl_seq(tb, "illustrative_net_pnl_rs")), 2), "confirmed_signals_vendor_a": len(sa),
                     "confirmed_signals_vendor_b": len(sb), "signals_in_both": len(sa & sb), "signal_agreement_pct_of_union": round(100.0 * len(sa & sb) / len(sa | sb), 1) if (sa | sb) else None,
                     "gross_rs_on_trades_only_a": round(sum(F.fnum(ka[k]["gross_pnl_rs"]) for k in set(ka) - set(kb)), 2), "gross_rs_on_trades_only_b": round(sum(F.fnum(kb[k]["gross_pnl_rs"]) for k in set(kb) - set(ka)), 2),
                     "gross_rs_on_identical_trades_a": round(sum(F.fnum(ka[k]["gross_pnl_rs"]) for k in common), 2), "gross_rs_on_identical_trades_b": round(sum(F.fnum(kb[k]["gross_pnl_rs"]) for k in common), 2)})
    return rows


def coverage_exceptions(out: Path) -> list[dict]:
    q = rd(out / "data" / "session_quality_all_windows.csv")
    rows = []
    for r in q:
        if r["usable"] != "True" or int(float(r["missing_regular_minutes"] or 0)) > 0 or int(float(r["frozen_rows_ge5"] or 0)) > 0 or r["pipeline_flags"] or r["abnormal_first_bar"] == "True":
            rows.append({"window": r["window"], "date": r["date"], "usable": r["usable"], "status": r["pipeline_status"], "reasons": r["pipeline_reasons"], "flags": r["pipeline_flags"], "missing_regular_minutes": r["missing_regular_minutes"],
                         "missing_ranges": r["missing_minute_ranges"], "frozen_rows_ge5": r["frozen_rows_ge5"], "extreme_1m_candles": r["extreme_1m_candles"], "abnormal_first_bar": r["abnormal_first_bar"]})
    return rows


def trade_universe(win: dict[str, dict]) -> list[dict]:
    """One flat table of every trade of every window (Phase 3.6 reference included) for the workbook; composite key = window_id | trade_id."""
    rows = []
    for wid in ("A", "B", "B_TV", "C", "D_5P", "D_TV"):
        for t in win[wid]["trades"]:
            rows.append({"window_id": wid, "composite_key": f"{wid}|{t['trade_id']}", "trade_id": t["trade_id"], "date": t["date"], "strategy": t["strategy"], "method": t["method"], "direction": t["direction"], "trade_no_of_day": t["trade_no_of_day"],
                         "signal_confirmed_at": t["signal_confirmed_at"], "fill_timestamp": t["fill_timestamp"], "entry_price": t["entry_price"], "initial_stop": t["initial_stop"], "target_1": t["target_1"], "target_2": t["target_2"],
                         "outcome": t["outcome"], "leg1_exit_time": t["leg1_exit_time"], "leg1_exit_price": t["leg1_exit_price"], "leg2_exit_time": t["leg2_exit_time"], "leg2_exit_price": t["leg2_exit_price"],
                         "gross_pnl_points_weighted": t["gross_pnl_points_weighted"], "gross_pnl_rs": t["gross_pnl_rs"], "illustrative_net_pnl_rs": t["illustrative_net_pnl_rs"], "bars_held": t["bars_held"],
                         "data_source_id": t.get("data_source_id", "FIVEPAISA_PHASE1 (Phase 3.6 reference)"), "data_source_partition_sha256": t.get("data_source_partition_sha256", ""), "raw_source_sha256": t.get("raw_source_sha256", ""),
                         "window_status": t.get("window_status", "REFERENCE"), "daily_journal": f"daily/{wid}/{t['date'][:7]}/{t['date']}.md" if wid != "A" else f"../phase3/phase36_body_based_pdr/daily/{t['date'][:7]}/{t['date']}.md",
                         "chart": f"charts/{wid}/{t['trade_id']}.svg" if wid != "A" else f"../phase3/phase36_body_based_pdr/charts/{t['trade_id']}.svg"})
    return rows


def build_all(out: Path) -> dict:
    win = {wid: load_window(wid, out) for wid in ("A", "B", "B_TV", "C", "D_5P", "D_TV")}
    annual, strat, costs, monthly, _ = annual_tables(win)
    write_csv(out / "annual_comparison.csv", annual)
    write_csv(out / "strategy_comparison.csv", strat)
    write_csv(out / "cost_sensitivity.csv", costs)
    write_csv(out / "monthly_pnl_all_windows.csv", monthly)
    write_csv(out / "robustness_regimes.csv", regime_tables(win))
    write_csv(out / "session_regimes.csv", session_regimes(win))
    write_csv(out / "robustness_entry_time.csv", entry_time_table(win))
    write_csv(out / "robustness_concentration.csv", concentration_table(win))
    write_csv(out / "robustness_data_quality.csv", data_quality_table(win, out))
    write_csv(out / "not_evaluated_strategy_sessions.csv", not_evaluated_table(win))
    write_csv(out / "vendor_sensitivity.csv", vendor_sensitivity(win))
    write_csv(out / "coverage_exceptions.csv", coverage_exceptions(out))
    write_csv(out / "all_trades_all_windows.csv", trade_universe(win))
    (out / "regime_definitions.json").write_text(json.dumps({"volatility": f"annualised standard deviation (%) of the last {RV_WINDOW} daily log returns before the session: LOW_VOL < {RV_LOW}, MID_VOL {RV_LOW}-{RV_HIGH}, HIGH_VOL >= {RV_HIGH}",
                                                             "trend": f"Kaufman efficiency ratio of the last {ER_WINDOW} daily closes before the session (|net change| / sum of |daily changes|): TRENDING_UP / TRENDING_DOWN if >= {ER_TREND} (sign of the net change), else SIDEWAYS",
                                                             "causal": "only closes strictly before the session date are used", "declared": "round numbers written after the windows had been run once for sanity checks (their totals had been seen) but before any regime or robustness table existed; not fitted, but post-hoc diagnostics on five windows with small cells", "confidence_rubric": CONFIDENCE_RUBRIC}, indent=1))
    from nifty_trading.research import phase4_xlsx
    phase4_xlsx.write_workbook(out)
    return {"rows": len(annual)}
