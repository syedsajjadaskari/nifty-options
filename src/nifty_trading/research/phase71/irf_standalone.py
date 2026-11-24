"""Standalone IRF V3 comparison helpers for Phase 7.1 (Method 2 variants): the Phase 7.0 session data, execution and metrics are IMPORTED unchanged; only the Method 2 signal rule is swapped
(``irf_cycles.m2_cycles`` options). Synthetic index points; scenario labels as in Phase 7.0 (SL35/SL40, target 60, 15:14 forced exit, 13:00 cutoff, next-open fill)."""

from __future__ import annotations

import pandas as pd

from nifty_trading.research.irf_v3 import backtest as BT
from nifty_trading.research.irf_v3 import execution as X
from nifty_trading.research.irf_v3.config import SCENARIOS
from nifty_trading.research.phase71.irf_cycles import M2Opts, m1_cycles, m2_cycles


def first_signal(cs, method: str, opts: M2Opts | None = None):
    cyc = m1_cycles(cs) if method == "M1" else m2_cycles(cs, opts)
    return (cyc[0], cs[cyc[0]["fail_idx"]]) if cyc else (None, None)


def standalone(ds, opts: M2Opts, scenario: str = "SL40_T60") -> dict:
    """{'M1': rows, 'M2': rows, 'COMBINED': rows, 'sig': per-session records} for one dataset under the given Method 2 options."""
    cfg = SCENARIOS[scenario]
    books = {"M1": [], "M2": [], "COMBINED": []}
    sig = []
    for d, s in ds.sessions.items():
        if not s.evaluable:
            continue
        c1, k1 = first_signal(s.candles, "M1")
        c2, k2 = first_signal(s.candles, "M2", opts)
        rec = {"date": d, "m1_time": k1.end if k1 is not None else None, "m2_time": k2.end if k2 is not None else None, "m2_level": c2["level"] if c2 else None}
        trades = {}
        for m, k in (("M1", k1), ("M2", k2)):
            if k is None or not X.eligible_entry(k.end, cfg):
                continue
            res = X.simulate_short(s.minutes, ds.cal, k.end, k.close, cfg)
            if res.get("traded"):
                trades[m] = (k.end, res, k)
                books[m].append({"window": ds.window, "date": d, "signal_candle_start": f"{k.start:%H:%M}", "signal_time": f"{k.end:%H:%M}", "gross_points": res.get("gross_points"), "exit_reason": res.get("exit_reason"), "exit_status": res.get("exit_status"),
                                 "entry_price": res["entry_price"], "date_": str(d)})
        if trades:
            m = sorted(trades, key=lambda x: (trades[x][0], x))[0]
            t, res, k = trades[m]
            books["COMBINED"].append({"window": ds.window, "date": d, "credited": m, "signal_candle_start": f"{k.start:%H:%M}", "signal_time": f"{t:%H:%M}", "gross_points": res.get("gross_points"), "exit_reason": res.get("exit_reason"),
                                      "exit_status": res.get("exit_status"), "entry_price": res["entry_price"]})
            rec["combined_credit"], rec["combined_time"] = m, f"{t:%H:%M}"
        sig.append(rec)
    return {"books": books, "sig": sig}


def summarize(books: dict, n_sessions: int) -> dict:
    return {k: BT.metrics(v, n_sessions) for k, v in books.items()}


def df(rows) -> pd.DataFrame:
    return pd.DataFrame(rows)
