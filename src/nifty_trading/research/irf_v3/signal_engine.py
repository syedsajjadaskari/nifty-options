"""Combined IRF V3 signal engine: both method state machines evaluate the same session independently; the combined view keeps the earliest causally executable signal.

Selection rules (the source documents define NO priority between the methods):
  1. a method's signal is ELIGIBLE when the fill bar (start == failure-candle end) is <= 13:00:00 and the fill is possible (bar exists and is executable);
  2. the combined engine selects the eligible signal with the earliest signal_time;
  3. SAME-INSTANT TIE: both signals share one failure candle. Deterministic research policy TIE_METHOD_1 (labelled, NOT author-approved): Method 1 is credited. Entry, stop and target are identical
     for both methods (same time, same price, same scenario), so the trade and its P&L do not depend on this label; it only attributes the trade.
Ledger: every signal of both methods stays in the ledger whether or not it is eligible / selected.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from nifty_trading.research.irf_v3 import execution as X
from nifty_trading.research.irf_v3.config import IrfV3Config
from nifty_trading.research.irf_v3.data_access import Session
from nifty_trading.research.irf_v3.method1 import run_method1
from nifty_trading.research.irf_v3.method2 import run_method2
from nifty_trading.research.irf_v3.models import M1, M2, MethodTrace

TIE_POLICY = "TIE_METHOD_1"


@dataclass
class SessionEval:
    date: object
    session: Session
    traces: dict = field(default_factory=dict)       # method -> MethodTrace
    trades: dict = field(default_factory=dict)       # method -> simulate_short result (None when no signal)
    status: dict = field(default_factory=dict)       # method -> NO_SIGNAL | SIGNAL_ELIGIBLE | SIGNAL_AFTER_CUTOFF | SIGNAL_NOT_FILLABLE
    combined: dict = field(default_factory=dict)     # selection record


def evaluate_session(s: Session, cfg: IrfV3Config, cal=None, *, m2_red_breakout_counts: bool | None = None, simulate: bool = True) -> SessionEval:
    ev = SessionEval(s.date, s)
    if not s.evaluable:
        for m in (M1, M2):
            ev.traces[m] = MethodTrace(method=m, date=s.date, status="NO_SIGNAL", no_signal_reason="NOT_EVALUATED:" + s.reason)
            ev.trades[m] = None
            ev.status[m] = "NOT_EVALUATED"
        ev.combined = {"selected_method": "", "outcome": "NOT_EVALUATED", "tie": False, "reason": s.reason}
        return ev
    red = cfg.allow_red_breakout_candle_as_first_red if m2_red_breakout_counts is None else m2_red_breakout_counts
    ev.traces[M1] = run_method1(s.date, s.candles)
    ev.traces[M2] = run_method2(s.date, s.candles, red_breakout_candle_counts=red, invalidate_close_below_a=cfg.m2_invalidate_close_below_a)
    for m, tr in ev.traces.items():
        if tr.status != "SIGNAL":
            ev.trades[m], ev.status[m] = None, "NO_SIGNAL"
            continue
        if not X.eligible_entry(tr.signal_time, cfg):
            ev.trades[m], ev.status[m] = {"traded": False, "entry_status": "AFTER_ENTRY_CUTOFF"}, "SIGNAL_AFTER_CUTOFF"
            continue
        res = X.simulate_short(s.minutes, cal, tr.signal_time, tr.confirmation_candle.close, cfg) if simulate else {"traded": True}
        ev.trades[m] = res
        ev.status[m] = "SIGNAL_ELIGIBLE" if res.get("traded") else "SIGNAL_NOT_FILLABLE"
    elig = [(ev.traces[m].signal_time, m) for m in (M1, M2) if ev.status[m] == "SIGNAL_ELIGIBLE"]
    if not elig:
        anysig = [m for m in (M1, M2) if ev.traces[m].status == "SIGNAL"]
        ev.combined = {"selected_method": "", "outcome": "NO_ELIGIBLE_SIGNAL" if anysig else "NO_SIGNAL", "tie": False, "reason": "; ".join(f"{m}:{ev.status[m]}" for m in (M1, M2))}
        return ev
    elig.sort(key=lambda x: (x[0], 0 if x[1] == M1 else 1))
    first_t = elig[0][0]
    same = [m for t, m in elig if t == first_t]
    ev.combined = {"selected_method": elig[0][1], "tie": len(same) > 1, "tie_policy": TIE_POLICY if len(same) > 1 else "",
                   "outcome": "BOTH_SAME_INSTANT" if len(same) > 1 else ("ONLY_" + elig[0][1] if len(elig) == 1 else "EARLIEST_OF_BOTH"),
                   "reason": "same failure candle; Method 1 credited by deterministic tie policy" if len(same) > 1 else ""}
    return ev


def overlap_class(ev: SessionEval) -> str:
    """Relationship of the two methods' FIRST signals on a session (independent of cutoff / fillability)."""
    a, b = ev.traces.get(M1), ev.traces.get(M2)
    if a is None or b is None or ev.status.get(M1) == "NOT_EVALUATED":
        return "NOT_EVALUATED"
    sa, sb = a.status == "SIGNAL", b.status == "SIGNAL"
    if sa and sb:
        return "BOTH_SAME_TIME" if a.signal_time == b.signal_time else ("BOTH_M1_FIRST" if a.signal_time < b.signal_time else "BOTH_M2_FIRST")
    return "ONLY_M1" if sa else ("ONLY_M2" if sb else "NEITHER")
