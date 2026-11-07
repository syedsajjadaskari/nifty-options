"""Phase 5.1: helpers for the author-corrections audit.

* ``engines_orb_colour`` / ``run_scenario_orb_colour``: the frozen five engines of Phase 3.6 with ONLY the ORB slot replaced by ``ORBColourStrategy`` (an opt-in variant; the frozen modules and the baseline are not edited).
  The scenario runner temporarily swaps ``phase3.make_engines`` and restores it, so the controller, the exits and the ledger code are the frozen ones.
* ``orb_signal_differences``: the exact ORB signals (per session) whose status changes between the baseline and the variant. Signals only: no profit is computed or compared (the brief forbids selecting rules by P&L).
"""

from __future__ import annotations

from contextlib import contextmanager

from nifty_trading.research import phase3 as P
from nifty_trading.strategies.orb import ORBStrategy
from nifty_trading.strategies.orb_colour import ORBColourStrategy


def engines_orb_colour(p, t, pdr_engine="LEGACY", pdr_revision=None):
    """``phase3.make_engines`` with the ORB engine replaced (same constructor arguments, same fixed order IRF, ORB, PDR, PDS, RF)."""
    engines = _ORIGINAL_MAKE(p, t, pdr_engine, pdr_revision)
    return [ORBColourStrategy(proposals=p, trade=t) if isinstance(e, ORBStrategy) else e for e in engines]


_ORIGINAL_MAKE = P.make_engines


@contextmanager
def orb_colour_engines():
    """Within the block ``phase3.run_scenario`` builds the ORB colour variant; the original factory is always restored."""
    P.make_engines = engines_orb_colour
    try:
        yield
    finally:
        P.make_engines = _ORIGINAL_MAKE


def run_scenario_orb_colour(sc, ctxs, infos, bars_by_day):
    with orb_colour_engines():
        return P.run_scenario(sc, ctxs, infos, bars_by_day)


def orb_signal_differences(ctxs: dict, sc) -> list[dict]:
    """Per session: every ORB record of the baseline engine and of the variant; rows where the status differs."""
    base, var = ORBStrategy(proposals=sc.proposals, trade=sc.trade), ORBColourStrategy(proposals=sc.proposals, trade=sc.trade)
    rows = []
    for d in sorted(ctxs):
        a = {(r.method, r.direction): r for r in base.evaluate_session(ctxs[d])}
        b = {(r.method, r.direction): r for r in var.evaluate_session(ctxs[d])}
        for k, ra in a.items():
            rb = b[k]
            if ra.signal_status != rb.signal_status:
                rows.append({"date": str(d), "strategy": "ORB", "method": k[0], "direction": k[1], "signal_time": "" if ra.signal_timestamp is None else f"{ra.signal_timestamp:%H:%M}",
                             "first_candle_open": ra.signal_candle_open, "first_candle_close": ra.signal_candle_close, "baseline_status": ra.signal_status, "variant_status": rb.signal_status, "variant_reason": rb.invalidation_reason})
    return rows
