"""Phase 3.0 exploratory backtest: runs the five signal engines through the shared trading-day controller over the verified history.

Everything is chronological and causal (see ``strategies/trading_day.py`` and ``core/exit_policy.py``). The P&L is SYNTHETIC index-point
P&L x quantity: the NIFTY 50 index is not tradable, so this is a research metric, not executable brokerage profit.
No parameter is tuned here: the scenarios are fixed, labelled configurations and are never combined.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from collections.abc import Sequence
from dataclasses import dataclass, field, replace
from datetime import date, time

from nifty_trading.core.exit_policy import ExitResult, TradeOutcome
from nifty_trading.strategies import (
    DEFAULT_PROPOSALS,
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    RFStrategy,
)
from nifty_trading.strategies.params import DEFAULT_TRADE, ProposalConfig, TradeConfig
from nifty_trading.strategies.trading_day import DayResult, DayRules, run_trading_day

FORCED_EXIT_TIME = time(15, 14)  # FORCED-EXIT-002 (assumption): closed at the OPEN of the 15:14 minute, i.e. before 15:15
CAPITAL_BASE = 100000.0  # the manual report's assumed capital base, used only for return ratios
STRATEGIES = ("IRF", "ORB", "PDR", "PDS", "RF")


@dataclass(frozen=True)
class Scenario:
    key: str
    title: str
    proposals: ProposalConfig
    trade: TradeConfig
    notes: str = ""


def _base_proposals() -> ProposalConfig:
    # engines run with the per-session cap lifted: the shared controller, not the engine, decides how many signals matter (a Phase 2 proposal of 1/session is superseded)
    return replace(DEFAULT_PROPOSALS, trend_mode="EMA_PREV_SESSION_CLOSE", pdr_zone_method="B_SWING_HIGH_REVERSAL", max_signals_per_session=99)


def scenarios() -> dict[str, Scenario]:
    base_trade = replace(DEFAULT_TRADE, forced_exit_time=FORCED_EXIT_TIME)
    base = _base_proposals()
    return {
        "baseline": Scenario("baseline", "A. Baseline: EMA-only trend (variant A), 35-point stop (ORB 30), reversal-high PDR zone", base, base_trade),
        "ema_structure": Scenario("ema_structure", "B. Structure trend: EMA + confirmed swing structure (variant B); everything else as A",
                                  replace(base, trend_mode="STRUCTURE_EMA_SWING2"), base_trade),
        "pdr_shelf": Scenario("pdr_shelf", "C. PDR repeated-resistance shelf candidate; everything else as A",
                              replace(base, pdr_zone_method="C_REPEATED_TOUCHES"), base_trade),
        "sl40": Scenario("sl40", "D. Alternative stop: 40 points for IRF/PDR/PDS/RF (ORB stays 30); everything else as A", base,
                         replace(base_trade, stop_variant="ALTERNATE_40")),
    }


def make_engines(p: ProposalConfig, t: TradeConfig):
    return [IRFStrategy(proposals=p, trade=t), ORBStrategy(proposals=p, trade=t), PDRStrategy(proposals=p, trade=t),
            PDSStrategy(proposals=p, trade=t), RFStrategy(proposals=p, trade=t)]


# ---------------------------------------------------------------------------------------------------------------- run
@dataclass
class ScenarioResult:
    scenario: Scenario
    days: list[DayResult] = field(default_factory=list)
    excluded: list[tuple[date, str]] = field(default_factory=list)  # sessions not evaluated, with the reason
    ledger: list[dict] = field(default_factory=list)
    signals_log: list[dict] = field(default_factory=list)  # rejected / ignored / conflict / note entries
    ambiguities: list[dict] = field(default_factory=list)
    partial_coverage: list[tuple[date, str]] = field(default_factory=list)  # evaluated sessions on which some strategies could not be evaluated


def run_scenario(sc: Scenario, ctxs: dict, infos: dict, bars_by_day: dict) -> ScenarioResult:
    out = ScenarioResult(sc)
    engines = make_engines(sc.proposals, sc.trade)
    for d in sorted(infos):
        if d not in ctxs:
            info = infos[d]
            out.excluded.append((d, f"{info.quality.value}: {'; '.join(info.reasons) or info.status.value}"))
            continue
        recs = [r for e in engines for r in e.evaluate_session(ctxs[d])]
        blocked = sorted({f"{r.strategy}: {r.invalidation_reason}" for r in recs if r.signal_status == "NOT_EVALUATED"})
        if blocked:
            out.partial_coverage.append((d, "; ".join(blocked)))
        res = run_trading_day(d, recs, bars_by_day[d], sc.trade, DayRules())
        out.days.append(res)
        for tr in res.trades:
            out.ledger.append(ledger_row(sc.key, d, tr, res))
            for a in tr.result.ambiguities:
                out.ambiguities.append({"date": str(d), "trade_no": tr.trade_no, "strategy": tr.signal.strategy, "note": a})
        for x in res.diagnostics:
            out.signals_log.append({"date": str(d), "time": f"{x.timestamp:%H:%M}" if x.timestamp is not None else "", "strategy": x.strategy, "method": x.method,
                                    "direction": x.direction, "event": x.event, "reason": x.reason})
    return out


def ledger_row(scenario: str, d: date, tr, day: DayResult) -> dict:
    r: ExitResult = tr.result
    sig = tr.signal
    cfg = sig.execution_config.get("trade_config", {})
    q_total = cfg.get("total_lots", 6) * cfg.get("lot_size", 65)
    q1 = cfg.get("leg1_lots", 3) * cfg.get("lot_size", 65)
    q2 = q_total - q1
    final_ts = r.leg2_ts or r.leg1_ts
    t1_done = (r.outcome in (TradeOutcome.TARGET, TradeOutcome.T1_THEN_BUFFER_STOP, TradeOutcome.BREAKEVEN)
               or (r.outcome is TradeOutcome.FORCED_EXIT and r.post_t1_stop_level is not None)
               or (r.outcome is TradeOutcome.INCOMPLETE_EOD and r.leg1_exit is not None and r.leg2_exit is None))
    holding = None if (final_ts is None or r.leg2_exit is None) else (final_ts - tr.fill_timestamp).total_seconds() / 60.0 + 1.0
    return {
        "scenario": scenario, "date": str(d), "trade_no": tr.trade_no, "is_second_trade": tr.trade_no == 2,
        "strategy": sig.strategy, "method": sig.method, "direction": sig.direction,
        "signal_time": f"{sig.signal_timestamp:%H:%M}", "entry_time": f"{tr.fill_timestamp:%H:%M}", "entry_price": tr.entry_price,
        "concurrent_methods": ";".join(tr.concurrent_methods),
        "stop_level": r.stop_level, "t1_level": r.t1_level, "t2_level": r.t2_level, "post_t1_stop_level": r.post_t1_stop_level,
        "qty_total": q_total, "qty_leg1": q1, "qty_leg2": q2,
        "leg1_exit_time": f"{r.leg1_ts:%H:%M}" if r.leg1_ts is not None and r.leg1_exit is not None else "",
        "leg1_exit_price": r.leg1_exit, "leg2_exit_time": f"{r.leg2_ts:%H:%M}" if r.leg2_ts is not None and r.leg2_exit is not None else "",
        "leg2_exit_price": r.leg2_exit,
        "outcome": tr.classification, "reason_code": reason_code(tr.classification, r),
        "gross_points_weighted": r.pnl_points_weighted, "gross_pnl_rs": r.pnl_rupees,
        "adverse_slippage_points": r.adverse_slippage_points, "ambiguities": len(r.ambiguities),
        "holding_minutes": holding, "forced_exit_reference_close": r.forced_exit_reference_close,
        "target2_status": sig.execution_config.get("target_2_status"), "day_final_state": day.final_state.value,
        "resolved": r.leg2_exit is not None, "t1_booked": bool(t1_done),
    }


def reason_code(cls: str, r: ExitResult) -> str:
    return {"TARGET": "T1_AND_T2_HIT", "T1_THEN_BUFFER_STOP": "T1_THEN_POST_T1_STOP_ENTRY_MINUS_PLUS_6", "INITIAL_FULL_STOP": "ORIGINAL_STOP_BEFORE_T1",
            "FORCED_EXIT": "FORCED_EXIT_AT_1514_OPEN", "INCOMPLETE_EOD": "UNRESOLVED_NO_FILLABLE_EXIT", "NOT_EVALUABLE": "EXIT_POLICY_NOT_EVALUABLE",
            "BREAKEVEN": "LEGACY_EXACT_ENTRY_STOP"}.get(cls, cls)


# ------------------------------------------------------------------------------------------------------------ metrics
def sequence_key(row: dict):
    return (row["date"], row["entry_time"], row["trade_no"])


def apply_costs(rows: Sequence[dict], cost_per_trade: float = 0.0, slippage_points_per_fill: float = 0.0) -> list[float]:
    """Net P&L per trade = gross - fixed cost per trade - slippage. Slippage s points adverse on every fill: entry (all units) plus the exit
    legs (all units): s x 2 x qty_total. Illustrative only; the index is not tradable."""
    return [r["gross_pnl_rs"] - cost_per_trade - slippage_points_per_fill * 2 * r["qty_total"] for r in rows]


def drawdown(pnls: Sequence[float]) -> tuple[float, int]:
    """Maximum drawdown of the cumulative P&L after each trade (the running high starts at 0). Returns (rupees, index of the trade at the trough)."""
    cum = peak = 0.0
    worst, at = 0.0, -1
    for i, p in enumerate(pnls):
        cum += p
        peak = max(peak, cum)
        if peak - cum > worst:
            worst, at = peak - cum, i
    return worst, at


def max_consecutive_losses(pnls: Sequence[float]) -> int:
    best = cur = 0
    for p in pnls:
        cur = cur + 1 if p < 0 else 0
        best = max(best, cur)
    return best


def summarize(rows: Sequence[dict], pnls: Sequence[float] | None = None) -> dict:
    rows = sorted(rows, key=sequence_key)
    p = list(pnls) if pnls is not None else [r["gross_pnl_rs"] for r in rows]
    # `pnls` must be given in the same order as `rows`; callers pass costs applied to the sorted rows
    wins = [x for x in p if x > 0]
    losses = [x for x in p if x < 0]
    gp, gl = sum(wins), -sum(losses)
    dd, _ = drawdown(p)
    oc = Counter(r["outcome"] for r in rows)
    hold = [r["holding_minutes"] for r in rows if r["holding_minutes"] is not None]
    n = len(rows)
    return {
        "entries": n, "days_traded": len({r["date"] for r in rows}), "first_trades": sum(1 for r in rows if r["trade_no"] == 1),
        "second_trades": sum(1 for r in rows if r["trade_no"] == 2), "total_pnl_rs": sum(p), "gross_profit_rs": gp, "gross_loss_rs": -gl,
        "win_rate_pct": 100.0 * len(wins) / n if n else 0.0, "loss_rate_pct": 100.0 * len(losses) / n if n else 0.0,
        "profit_factor": (gp / gl) if gl > 0 else (math.inf if gp > 0 else 0.0), "avg_trade_rs": (sum(p) / n) if n else 0.0,
        "max_drawdown_rs": dd, "max_consecutive_losses": max_consecutive_losses(p),
        "target2": oc.get("TARGET", 0), "t1_then_buffer_stop": oc.get("T1_THEN_BUFFER_STOP", 0), "initial_full_stop": oc.get("INITIAL_FULL_STOP", 0),
        "forced_exit": oc.get("FORCED_EXIT", 0), "legacy_breakeven": oc.get("BREAKEVEN", 0), "unresolved": oc.get("INCOMPLETE_EOD", 0) + oc.get("NOT_EVALUABLE", 0),
        "avg_holding_minutes": (sum(hold) / len(hold)) if hold else None,
    }


def monthly(rows: Sequence[dict], pnls: Sequence[float]) -> dict[str, float]:
    m: dict[str, float] = defaultdict(float)
    for r, x in zip(sorted(rows, key=sequence_key), pnls, strict=True):
        m[r["date"][:7]] += x
    return dict(sorted(m.items()))


def equity_curve(rows: Sequence[dict], pnls: Sequence[float], all_days: Sequence[str]) -> list[dict]:
    daily: dict[str, float] = defaultdict(float)
    for r, x in zip(sorted(rows, key=sequence_key), pnls, strict=True):
        daily[r["date"]] += x
    cum = peak = 0.0
    out = []
    for d in all_days:
        cum += daily.get(d, 0.0)
        peak = max(peak, cum)
        out.append({"date": d, "daily_pnl_rs": daily.get(d, 0.0), "cumulative_pnl_rs": cum, "drawdown_rs": peak - cum})
    return out


def day_state_counts(days: Sequence[DayResult]) -> Counter:
    return Counter(d.final_state.value for d in days)


def signal_counts(log: Sequence[dict]) -> dict:
    """Counts for the required report lines, from the diagnostic log."""
    c: Counter = Counter()
    by_strategy: dict[str, Counter] = defaultdict(Counter)
    for x in log:
        reason = x["reason"]
        key = None
        if reason.startswith("ENTRY_CUTOFF_EXCEEDED"):
            key = "rejected_cutoff_13_00"
        elif reason.startswith("POSITION_ACTIVE"):
            key = "ignored_position_active"
        elif x["event"] == "CONFLICT":
            key = "simultaneous_conflicts"
        elif reason.startswith("SECOND_TRADE_RESTRICTED"):
            key = "rejected_not_pdr_pds_for_second_trade"
        elif reason in ("DAY_FINISHED", "DAY_UNRESOLVED_EXECUTION"):
            key = "ignored_day_already_decided"
        elif reason.startswith("ENTRY_NOT_FILLABLE"):
            key = "rejected_entry_not_fillable"
        elif reason.startswith("ENTRY_BLOCKED") or reason.startswith("DIAGNOSTIC_ONLY"):
            key = "rejected_entry_blocked_or_diagnostic"
        elif x["event"] == "NOTE":
            key = "notes"
        else:
            key = "other"
        c[key] += 1
        by_strategy[x["strategy"]][key] += 1
    return {"total": dict(c), "by_strategy": {k: dict(v) for k, v in by_strategy.items()}}
