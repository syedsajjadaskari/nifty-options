"""Phase 5.5: the three configurations of the complete five-strategy backtest and the cost scenarios (SYNTHETIC index-point P&L; no real option P&L, no live or paper orders).

Nothing about the controller, the exit policy, the stops, the targets, the cutoff or the sizing is touched: the frozen Phase 3.6 pipeline (``phase31.run_timelines`` -> ``trading_day.run_trading_day`` -> ``exit_policy``) is reused as is and
only the ENGINE FACTORY is swapped at run time (``patched_engines``; no file is edited):

  A  phase36-frozen                            the frozen Phase 3.6 engines
  B  phase53-author-corrected                  IRF first-red-candle LOW support + provisional 28-point EMA range clearance, PDR / PDS earliest eligible confirmation (provisional conventions), ORB and RF frozen
  C  phase53-author-corrected + ORB gap crossing   B plus the Phase 5.4 candidate: the Gap / 200 DMA setup lets the first CANDLE (not only the open) cross the average. PROVISIONAL research scenario: the indicator stays the
                                               repository's EMA(200) of completed five-minute closes (the rulebook mixes '200 DMA' and '200 EMA'; see ORB-MA-001); no relaxed ORB variant is included

The configurations are never combined. Costs (``cost_rows``) are illustrative and are computed from the ACTUAL filled quantities of every trade.
"""

from __future__ import annotations

import contextlib
import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from datetime import date

from nifty_trading.research import phase3 as P
from nifty_trading.research import phase31 as P31
from nifty_trading.research import phase53 as F53
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy

KEYS = ("A", "B", "C")
TITLES = {"A": "Configuration A - frozen Phase 3.6 (FROZEN-PHASE36-42cea2600bd4)", "B": "Configuration B - Phase 5.3 author-corrected (provisional conventions)",
          "C": "Configuration C - Phase 5.3 + ORB gap crossing (provisional research scenario)"}
EXPECTED_SIGNALS = {"A": {"total": 1083, "IRF": 874, "ORB": 53, "PDR": 87, "PDS": 57, "RF": 12}, "B": {"total": 1109, "IRF": 786, "ORB": 53, "PDR": 147, "PDS": 111, "RF": 12}}
FIXED_COST_RS = 70.0  # the owner's indicative estimate per completed trade (brokerage ~30 + other charges ~40); NOT a verified broker bill
SLIPPAGE_POINTS = (0.0, 0.25, 0.5, 1.0)
COST_SCENARIOS = (("A", "Gross P&L without costs", 0.0, 0.0), ("B", "Rs 70 per trade, zero slippage", FIXED_COST_RS, 0.0), ("C", "Rs 70 per trade + 0.25 point slippage per side", FIXED_COST_RS, 0.25),
                  ("D", "Rs 70 per trade + 0.5 point slippage per side", FIXED_COST_RS, 0.5), ("E", "Rs 70 per trade + 1.0 point slippage per side", FIXED_COST_RS, 1.0))


def engines_for(key: str, p, t, pdr_engine: str = "BODY_BASED_PHASE36", pdr_revision=None) -> list:
    """The five engines in their fixed order for configuration ``key`` (only the engines a configuration changes are replaced; RF is never replaced)."""
    if key == "A":
        return P.make_engines(p, t, pdr_engine, pdr_revision)
    engines = F53.make_engines53(F53.COMBINED_KEY, p, t, pdr_engine, pdr_revision)
    if key == "B":
        return engines
    if key == "C":
        return [ORBCandidateStrategy(proposals=p, trade=t, gap_crossing_def="CANDLE_CROSSES_AVERAGE") if type(e) is ORBStrategy else e for e in engines]
    raise ValueError(key)


@contextlib.contextmanager
def patched_engines(key: str):
    """Run the unchanged Phase 3.1 / 3.2 pipeline with configuration ``key``'s engines (module-level factory swap; restored on exit; no source file is edited)."""
    saved = (P31.make_engines, P.make_engines)

    def factory(p, t, pdr_engine="LEGACY", pdr_revision=None):
        return engines_for(key, p, t, pdr_engine, pdr_revision)
    P31.make_engines = factory
    try:
        yield
    finally:
        P31.make_engines, P.make_engines = saved


def run_timelines_cfg(key: str, sc, ctxs: dict, bars: dict):
    """{date: DayTimeline} for configuration ``key`` through the frozen controller (all five strategies together; no strategy priority)."""
    with patched_engines(key):
        return P31.run_timelines(sc, ctxs, bars)


# ------------------------------------------------------------------------------------------------------------------------------ costs and metrics
def filled_units(row: dict) -> tuple[float, float]:
    """(entry units, exit units) actually filled: the entry fills the whole position; each exit leg that has an exit price fills its own quantity once (a leg without a fillable exit has no fill)."""
    entry_units = float(row["qty_total"])
    exit_units = sum(float(row[q]) for q, px in (("qty_leg1", "leg1_exit_price"), ("qty_leg2", "leg2_exit_price")) if row.get(px) not in (None, ""))
    return entry_units, exit_units


def net_pnl(row: dict, fixed: float, slip: float, per_fill: bool = False) -> float:
    """Gross synthetic rupees less the illustrative fixed cost and the slippage. ``slip`` index points adverse on every unit of every fill (entry once, each exited leg once: no unit is charged twice). The fixed cost is charged ONCE per executed
    trade (the owner's Rs 70 per completed round trip); ``per_fill=True`` is the alternative reading 'Rs 70 per order fill' (entry + each exit leg), reported only as a sensitivity."""
    eu, xu = filled_units(row)
    fills = 1 + sum(1 for px in ("leg1_exit_price", "leg2_exit_price") if row.get(px) not in (None, ""))
    return float(row["gross_pnl_rs"]) - (fixed * fills if per_fill else fixed) - slip * (eu + xu)


def profit_factor(seq: Sequence[float]) -> float | None:
    gp = sum(x for x in seq if x > 0)
    gl = -sum(x for x in seq if x < 0)
    if gl > 0:
        return gp / gl
    return math.inf if gp > 0 else None


def max_drawdown(seq: Sequence[float]) -> float:
    cum = peak = worst = 0.0
    for x in seq:
        cum += x
        peak = max(peak, cum)
        worst = max(worst, peak - cum)
    return worst


def trade_order(rows: Sequence[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["date"], r["entry_time"], int(r["trade_no"])))


def metrics(rows: Sequence[dict], fixed: float = 0.0, slip: float = 0.0) -> dict:
    """Metrics for a set of executed trades under one cost scenario (the same trades, the same order)."""
    rows = trade_order(rows)
    seq = [net_pnl(r, fixed, slip) for r in rows]
    n = len(rows)
    wins = [x for x in seq if x > 0]
    oc = Counter(r["outcome"] for r in rows)
    pts = [float(r["gross_points_weighted"]) for r in rows]
    hold = [float(r["holding_minutes"]) for r in rows if r.get("holding_minutes") not in (None, "")]
    pf = profit_factor(seq)
    return {"trades": n, "first_trades": sum(1 for r in rows if int(r["trade_no"]) == 1), "second_trades": sum(1 for r in rows if int(r["trade_no"]) == 2), "winning_trades": len(wins), "losing_trades": sum(1 for x in seq if x < 0),
            "win_rate_pct": round(100 * len(wins) / n, 2) if n else None, "net_pnl_rs": round(sum(seq), 2), "gross_points_total": round(sum(pts), 3), "avg_points_per_trade": round(sum(pts) / n, 3) if n else None,
            "profit_factor": None if pf is None else ("inf" if pf == math.inf else round(pf, 3)), "max_drawdown_rs": round(max_drawdown(seq), 2),
            "t2_hits": oc.get("TARGET", 0), "t1_then_post_t1_stop": oc.get("T1_THEN_BUFFER_STOP", 0), "initial_full_stops": oc.get("INITIAL_FULL_STOP", 0), "forced_exits": oc.get("FORCED_EXIT", 0),
            "unresolved_exits": oc.get("INCOMPLETE_EOD", 0) + oc.get("NOT_EVALUABLE", 0), "t1_hits": sum(1 for r in rows if str(r.get("t1_booked")) == "True"),
            "avg_holding_minutes": round(sum(hold) / len(hold), 1) if hold else None, "ambiguous_trades": sum(1 for r in rows if int(r.get("ambiguities") or 0) > 0)}


def signal_counts(timelines: dict) -> dict:
    """Confirmed-signal counts of a configuration (every record with signal_status CONFIRMED), by strategy and by strategy / method."""
    by_s: Counter = Counter()
    by_m: Counter = Counter()
    for tl in timelines.values():
        for r in tl.records:
            if r.signal_status == "CONFIRMED":
                by_s[r.strategy] += 1
                by_m[f"{r.strategy}/{r.method}"] += 1
    return {"total": sum(by_s.values()), **{s: by_s.get(s, 0) for s in P.STRATEGIES}, "by_method": dict(sorted(by_m.items()))}


def ledger_rows(key: str, timelines: dict) -> list[dict]:
    out = []
    for d in sorted(timelines):
        tl = timelines[d]
        for tr in tl.result.trades:
            row = P.ledger_row(key, d, tr, tl.result)
            row["trade_id"] = f"{d:%Y%m%d}-{tr.trade_no}-{tr.signal.strategy}"
            row["config"] = key
            row["ambiguity_notes"] = " || ".join(tr.result.ambiguities)
            out.append(row)
    return out


def group(rows: Sequence[dict], keyfn) -> dict:
    g: dict = defaultdict(list)
    for r in rows:
        g[keyfn(r)].append(r)
    return dict(sorted(g.items()))


def sessions_summary(timelines: dict) -> dict:
    c = Counter(tl.result.final_state.value for tl in timelines.values())
    traded = sum(1 for tl in timelines.values() if tl.result.trades)
    return {"sessions": len(timelines), "sessions_with_a_trade": traded, "no_trade_sessions": len(timelines) - traded, "final_states": dict(c)}


def day_label(d: date) -> str:
    return f"{d:%Y-%m-%d}"
