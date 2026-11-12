"""Standalone ORB backtest runner + performance metrics. One decision per session, at most one trade per session, no re-entry, no portfolio controller, no other strategy.
SYNTHETIC NIFTY index-point P&L x a declared fixed quantity; the index is not tradable and this is not option P&L."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field

from nifty_trading.research.orb_v2 import data_access as DA
from nifty_trading.research.orb_v2 import execution as EX
from nifty_trading.research.orb_v2 import signal_engine as SE
from nifty_trading.research.orb_v2.config import OrbV2Config

FIXED_COST_RS = 70.0      # the owner's indicative estimate per completed trade (NOT a verified broker bill)
SLIPPAGE_POINTS = (0.0, 0.25, 0.5, 1.0)  # adverse points per side


@dataclass
class RunResult:
    config: OrbV2Config
    window: str
    sessions: list = field(default_factory=list)   # one dict per calendar session of the window (evaluated or not)
    trades: list = field(default_factory=list)     # one dict per executed trade


def run(inp: DA.WindowInputs, cfg: OrbV2Config) -> RunResult:
    DA.index_positions(inp)
    rr = RunResult(cfg, inp.window)
    for d in DA.evaluable_dates(inp):
        sd, why = DA.session_data(inp, d)
        if sd is None:
            rr.sessions.append({"date": d, "config_id": cfg.config_id, "window": inp.window, "evaluable": False, "not_evaluated_reason": why, "signal": "", "failed": ""})
            continue
        dec = SE.evaluate_session(sd, cfg)
        row = {"date": d, "config_id": cfg.config_id, "window": inp.window, "evaluable": True, "not_evaluated_reason": "", "signal": dec.signal, "failed": ";".join(dec.failed), "n_failed": len(dec.failed), **dec.detail}
        if dec.signal:
            ex = EX.simulate(sd, dec.signal, cfg, inp.cal)
            row["entry_status"] = ex.get("entry_status", "")
            if ex.get("traded"):
                tr = {"trade_id": f"{d:%Y%m%d}-1-ORBV2", "date": d, "config_id": cfg.config_id, "window": inp.window, "direction": dec.signal, "weekday": d.strftime("%a"), "signal_confirmed_at": dec.detail["signal_confirmed_at"],
                      "ema_scenario": dec.detail["ema_scenario"], "qualifying_category": dec.detail["qualifying_category"], "major_broken": dec.detail["major_broken"], "inner_broken_n": dec.detail["inner_broken_n"],
                      "gap_beyond_prev_range": dec.detail["gap_beyond_prev_range"], "gap_points": dec.detail["gap_points"], "patterns_matched": dec.detail["patterns_matched"], "primary_level": dec.detail["primary_level"], **ex}
                rr.trades.append(tr)
        rr.sessions.append(row)
    return rr


# --------------------------------------------------------------------------------------------------------------------------------- metrics
def net_points(t: dict, slippage: float) -> float:
    return t["gross_points"] - 2.0 * slippage


def net_rs(t: dict, qty: int, cost: float, slippage: float) -> float:
    return net_points(t, slippage) * qty - cost


def drawdown(pnls: list[float]) -> float:
    peak = cum = dd = 0.0
    for x in pnls:
        cum += x
        peak = max(peak, cum)
        dd = max(dd, peak - cum)
    return dd


def longest_losing_streak(pnls: list[float]) -> int:
    best = cur = 0
    for x in pnls:
        cur = cur + 1 if x <= 0 else 0
        best = max(best, cur)
    return best


def metrics(trades: list[dict], qty: int, cost: float = 0.0, slippage: float = 0.0) -> dict:
    closed = [t for t in sorted(trades, key=lambda r: r["date"]) if t.get("exit_status") == "CLOSED"]
    pts = [net_points(t, slippage) for t in closed]
    rs = [net_rs(t, qty, cost, slippage) for t in closed]
    n = len(closed)
    wins, losses = [x for x in rs if x > 0], [x for x in rs if x <= 0]
    gp, gl = sum(x for x in rs if x > 0), -sum(x for x in rs if x < 0)
    reasons = Counter(t["exit_reason"] for t in closed)
    return {"trades": n, "long": sum(1 for t in closed if t["direction"] == "BUY"), "short": sum(1 for t in closed if t["direction"] == "SELL"), "wins": len(wins), "losses": len(losses),
            "win_rate_pct": round(100 * len(wins) / n, 2) if n else None, "profit_factor": round(gp / gl, 3) if gl > 0 else (None if not n else float("inf")),
            "avg_win_rs": round(sum(wins) / len(wins), 1) if wins else None, "avg_loss_rs": round(sum(losses) / len(losses), 1) if losses else None,
            "avg_points_per_trade": round(sum(pts) / n, 3) if n else None, "total_points": round(sum(pts), 2), "total_rs": round(sum(rs), 1), "max_drawdown_rs": round(drawdown(rs), 1),
            "max_drawdown_points": round(drawdown(pts), 2), "longest_losing_streak": longest_losing_streak(rs), "target_hits": reasons["TARGET"], "stop_hits": reasons["STOP"], "forced_exits": reasons["FORCED_EXIT"],
            "target_pct": round(100 * reasons["TARGET"] / n, 1) if n else None, "stop_pct": round(100 * reasons["STOP"] / n, 1) if n else None, "forced_pct": round(100 * reasons["FORCED_EXIT"] / n, 1) if n else None,
            "avg_hold_minutes": round(sum(t["bars_held"] for t in closed) / n, 1) if n else None, "ambiguous_same_bar": sum(1 for t in closed if t.get("ambiguous_same_bar")),
            "unresolved_exits": sum(1 for t in trades if t.get("exit_status") != "CLOSED")}


def alt_policy_points(trades: list[dict]) -> float:
    """Total gross points if every same-bar stop/target ambiguity had resolved the OTHER way (sensitivity only)."""
    return sum(t["alt_gross_points"] if t.get("ambiguous_same_bar") else t["gross_points"] for t in trades if t.get("exit_status") == "CLOSED")


def grouped(trades: list[dict], key: str, qty: int) -> dict:
    g = defaultdict(list)
    for t in trades:
        g[key(t) if callable(key) else t[key]].append(t)
    return {k: metrics(v, qty) for k, v in sorted(g.items())}


def cost_grid(trades: list[dict], qty: int) -> list[dict]:
    out = []
    for cost in (0.0, FIXED_COST_RS):
        for s in SLIPPAGE_POINTS:
            m = metrics(trades, qty, cost, s)
            out.append({"cost_rs_per_trade": cost, "slippage_points_per_side": s, **{k: m[k] for k in ("trades", "win_rate_pct", "profit_factor", "avg_points_per_trade", "total_points", "total_rs", "max_drawdown_rs", "longest_losing_streak")}})
    return out


def signal_counts(rr: RunResult) -> dict:
    ev = [s for s in rr.sessions if s["evaluable"]]
    sig = [s for s in ev if s["signal"]]
    fails = Counter(c for s in ev for c in (s["failed"].split(";") if s["failed"] else []))
    sole = Counter(s["failed"] for s in ev if s["n_failed"] == 1)
    return {"sessions_in_window": len(rr.sessions), "evaluable_sessions": len(ev), "not_evaluated": len(rr.sessions) - len(ev), "signals": len(sig), "buy": sum(1 for s in sig if s["signal"] == "BUY"),
            "sell": sum(1 for s in sig if s["signal"] == "SELL"), "executed_trades": len(rr.trades), "failed_condition_frequency": dict(fails), "sole_failed_condition": dict(sole)}
