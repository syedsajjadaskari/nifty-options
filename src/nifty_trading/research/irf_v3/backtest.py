"""IRF V3 historical backtest: per window x scenario, standalone Method 1, standalone Method 2 and combined (one trade per day, no double counting).
Results are SYNTHETIC NIFTY-INDEX POINTS - not options or futures P&L. No parameter is tuned."""

from __future__ import annotations

import math

import pandas as pd

from nifty_trading.research.irf_v3.config import IrfV3Config
from nifty_trading.research.irf_v3.models import M1, M2
from nifty_trading.research.irf_v3.signal_engine import SessionEval, evaluate_session, overlap_class

SHORT = {M1: "M1", M2: "M2"}


def run_dataset(ds, cfg: IrfV3Config, *, m2_red_breakout_counts: bool | None = None) -> list[SessionEval]:
    return [evaluate_session(s, cfg, ds.cal, m2_red_breakout_counts=m2_red_breakout_counts) for s in ds.sessions.values()]


def _hm(ts) -> str:
    return "" if ts is None or pd.isna(ts) else pd.Timestamp(ts).strftime("%H:%M")


def trade_row(window: str, cfg: IrfV3Config, ev: SessionEval, method: str, *, label: str, credited: str = "") -> dict | None:
    tr, res = ev.traces[method], ev.trades.get(method)
    if res is None or not res.get("traded"):
        return None
    return {
        "window": window, "scenario": cfg.scenario_id, "book": label, "credited_method": credited or SHORT[method], "date": ev.date, "signal_candle_start": _hm(tr.confirmation_candle.start),
        "signal_time": _hm(tr.signal_time), "entry_time": res["entry_time"], "entry_price": res["entry_price"], "entry_vs_signal_close": res.get("entry_vs_signal_close"),
        "level": tr.reference_level, "initial_range_high": tr.initial_range_high, "stop": res["stop"], "target": res["target"], "exit_time": res.get("exit_time"), "exit_price": res.get("exit_price"),
        "exit_reason": res.get("exit_reason"), "gross_points": res.get("gross_points"), "mfe_points": res.get("mfe_points"), "mae_points": res.get("mae_points"),
        "holding_minutes": res.get("holding_minutes"), "same_window_both_touched": res.get("same_window_both_touched", False), "missing_minutes_while_open": res.get("missing_minutes_while_open", 0),
        "exit_status": res.get("exit_status", "")}


def books(window: str, cfg: IrfV3Config, evals: list[SessionEval]) -> dict[str, list[dict]]:
    out = {"M1": [], "M2": [], "COMBINED": []}
    for ev in evals:
        for m in (M1, M2):
            r = trade_row(window, cfg, ev, m, label=SHORT[m])
            if r:
                out[SHORT[m]].append(r)
        sel = ev.combined.get("selected_method")
        if sel:
            both = overlap_class(ev) == "BOTH_SAME_TIME"
            r = trade_row(window, cfg, ev, sel, label="COMBINED", credited=("M1+M2 (tie->M1)" if ev.combined.get("tie") else SHORT[sel]))
            if r:
                r["tie_same_instant"] = bool(ev.combined.get("tie")) or both
                out["COMBINED"].append(r)
    return out


def metrics(rows: list[dict], n_sessions: int, n_signals: int | None = None) -> dict:
    closed = [r for r in rows if r.get("exit_status") == "CLOSED"]
    g = [float(r["gross_points"]) for r in closed]
    wins, losses = [x for x in g if x > 0], [x for x in g if x < 0]
    flat = [x for x in g if x == 0]
    eq, peak, dd = 0.0, 0.0, 0.0
    for x in g:
        eq += x
        peak = max(peak, eq)
        dd = max(dd, peak - eq)
    pf = (sum(wins) / abs(sum(losses))) if losses else (math.inf if wins else float("nan"))
    return {"sessions": n_sessions, "signals": n_signals if n_signals is not None else len(rows), "executed_trades": len(rows), "closed_trades": len(closed), "unresolved_exits": len(rows) - len(closed),
            "wins": len(wins), "losses": len(losses), "flat": len(flat), "win_rate_pct": round(100 * len(wins) / len(closed), 2) if closed else float("nan"), "profit_factor": round(pf, 3) if pf == pf and pf != math.inf else pf,
            "gross_points": round(sum(g), 2), "avg_win": round(sum(wins) / len(wins), 2) if wins else 0.0, "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0.0,
            "max_drawdown_points": round(dd, 2), "stop_hits": sum(1 for r in closed if r["exit_reason"] == "STOP"), "target_hits": sum(1 for r in closed if r["exit_reason"] == "TARGET"),
            "forced_exits": sum(1 for r in closed if r["exit_reason"] == "FORCED_EXIT"), "same_window_stop_priority_cases": sum(1 for r in closed if r.get("same_window_both_touched"))}


def monthly(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["month", "trades", "points"])
    df = pd.DataFrame(rows)
    df["month"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m")
    return df.groupby("month").agg(trades=("gross_points", "size"), points=("gross_points", "sum")).reset_index().round({"points": 2})


def annual(rows: list[dict]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["year", "trades", "points"])
    df = pd.DataFrame(rows)
    df["year"] = pd.to_datetime(df["date"]).dt.year
    return df.groupby("year").agg(trades=("gross_points", "size"), points=("gross_points", "sum")).reset_index().round({"points": 2})


COSTS = (0.0, 1.0, 2.0, 3.0, 5.0)       # round-trip transaction cost, index points
SLIPS = (0.0, 0.5, 1.0, 2.0)            # adverse slippage per side, index points


def cost_slippage_grid(rows: list[dict]) -> pd.DataFrame:
    closed = [float(r["gross_points"]) for r in rows if r.get("exit_status") == "CLOSED"]
    out = []
    for c in COSTS:
        for s in SLIPS:
            net = [x - c - 2 * s for x in closed]
            w, lo = [x for x in net if x > 0], [x for x in net if x < 0]
            out.append({"round_trip_cost_pts": c, "slippage_pts_per_side": s, "net_points": round(sum(net), 2), "win_rate_pct": round(100 * len(w) / len(net), 2) if net else float("nan"),
                        "profit_factor": round(sum(w) / abs(sum(lo)), 3) if lo else float("inf")})
    return pd.DataFrame(out)
