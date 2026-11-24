"""Independent re-implementation (NO shared code with method1/method2/execution/data_access aggregation).

Signals are rebuilt from raw one-minute rows with pandas ``resample`` (origin 09:15) and NumPy index searches instead of the production state machines;
trades are rebuilt with array arithmetic over one-minute NumPy vectors. ``compare`` diffs every session/method/scenario against the production engine.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

AUCTION = pd.Timestamp("2026-08-03")


def five_min(day: pd.DataFrame) -> pd.DataFrame:
    d = day.set_index("ts").sort_index()
    d = d.between_time("09:15", "15:29")
    r = d.resample("5min", origin="start_day", offset="9h15min").agg({"open": "first", "high": "max", "low": "min", "close": "last"})
    r["n"] = d["open"].resample("5min", origin="start_day", offset="9h15min").count()
    r = r[r["n"] == 5].drop(columns="n")
    cutoff = pd.Timedelta(hours=15, minutes=15) if d.index[0].normalize() >= AUCTION else pd.Timedelta(hours=15, minutes=30)
    r = r[(r.index + pd.Timedelta(minutes=5) - r.index.normalize()) <= cutoff]
    return r


def _first(mask: np.ndarray, start: int) -> int:
    idx = np.flatnonzero(mask[start:])
    return -1 if idx.size == 0 else int(start + idx[0])


def signals(day: pd.DataFrame, red_breakout_counts: bool = False, invalidate_below_a: bool = False) -> dict:
    r = five_min(day)
    out = {"M1": None, "M2": None}
    if r.empty or r.index[0].time() != pd.Timestamp("09:15").time():
        return out
    o, h, c = r["open"].to_numpy(), r["high"].to_numpy(), r["close"].to_numpy()
    A = h[0]
    ends = r.index + pd.Timedelta(minutes=5)
    b = _first(c > A, 1)
    if b >= 0:
        f = _first(c < A, b + 1)
        if f >= 0:
            out["M1"] = {"signal_time": ends[f], "level": A, "breakout": r.index[b], "failure": r.index[f], "close": c[f]}
    if b >= 0:
        red_from = b if (red_breakout_counts and c[b] < o[b]) else b + 1
        red_idx = _first(c < o, red_from) if not (red_breakout_counts and c[b] < o[b]) else b
        if invalidate_below_a and red_idx >= 0:
            dead = _first(c < A, b + 1)
            if 0 <= dead <= red_idx:
                red_idx = -1
        if red_idx >= 0:
            B = o[red_idx]
            s2 = _first(c > B, red_idx + 1)
            if s2 >= 0:
                f2 = _first(c < B, s2 + 1)
                if f2 >= 0:
                    out["M2"] = {"signal_time": ends[f2], "level": B, "breakout": r.index[b], "red": r.index[red_idx], "second_breakout": r.index[s2], "failure": r.index[f2], "close": c[f2]}
    return out


def trade(day: pd.DataFrame, signal_time, stop: float, target: float, *, entry_convention="NEXT_1M_OPEN", signal_close=None, tie="STOP_FIRST_5M", forced="15:14", cutoff="13:00") -> dict | None:
    d = day.sort_values("ts")
    ts = d["ts"].to_numpy()
    st = np.datetime64(pd.Timestamp(signal_time))
    if pd.Timestamp(signal_time).time() > pd.Timestamp(cutoff).time():
        return None
    i0 = np.flatnonzero(ts == st)
    if i0.size == 0:
        return None
    i0 = int(i0[0])
    clock = (d["ts"].dt.hour * 60 + d["ts"].dt.minute).to_numpy()
    fx = int(forced[:2]) * 60 + int(forced[3:])
    end_cont = (15 * 60 + 15) if d["ts"].iloc[0].normalize() >= AUCTION else (15 * 60 + 30)
    o, h, l = d["open"].to_numpy(), d["high"].to_numpy(), d["low"].to_numpy()
    if not (clock[i0] < end_cont):
        return None
    entry = o[i0] if entry_convention == "NEXT_1M_OPEN" else float(signal_close)
    sl, tp = entry + stop, entry - target
    last = np.flatnonzero(clock >= fx)
    j_end = int(last[0]) if last.size else len(d)
    idx = np.arange(i0, j_end)
    idx = idx[clock[idx] < end_cont]
    win = (clock[idx] - 555) // 5 if tie == "STOP_FIRST_5M" else idx
    for w in np.unique(win):
        sel = idx[win == w]
        sl_hits = sel[h[sel] >= sl]
        tp_hits = sel[l[sel] <= tp]
        if sl_hits.size:
            j = int(sl_hits[0])
            px = o[j] if (o[j] >= sl and j != i0) else sl
            return {"entry_time": pd.Timestamp(ts[i0]), "entry": entry, "exit_time": pd.Timestamp(ts[j]), "exit": px, "reason": "STOP", "points": entry - px}
        if tp_hits.size:
            j = int(tp_hits[0])
            return {"entry_time": pd.Timestamp(ts[i0]), "entry": entry, "exit_time": pd.Timestamp(ts[j]), "exit": tp, "reason": "TARGET", "points": entry - tp}
    if last.size and int(last[0]) < len(d) and clock[int(last[0])] == fx:
        j = int(last[0])
        return {"entry_time": pd.Timestamp(ts[i0]), "entry": entry, "exit_time": pd.Timestamp(ts[j]), "exit": o[j], "reason": "FORCED_EXIT", "points": entry - o[j]}
    return {"entry_time": pd.Timestamp(ts[i0]), "entry": entry, "reason": "UNRESOLVED_EXIT", "points": float("nan")}


def compare(ds, evals, cfg) -> dict:
    """Diff signals and trades of production vs the independent rebuild. Returns counts and the list of mismatches."""
    mism, n_sig, n_trd = [], 0, 0
    for ev in evals:
        s = ev.session
        if not s.evaluable:
            continue
        ind = signals(s.minutes, cfg.allow_red_breakout_candle_as_first_red, cfg.m2_invalidate_close_below_a)
        for key, m in (("M1", "IRF_V3_METHOD_1"), ("M2", "IRF_V3_METHOD_2")):
            tr, a = ev.traces[m], ind[key]
            n_sig += 1
            if (tr.status == "SIGNAL") != (a is not None):
                mism.append((ev.date, key, "signal_presence", tr.status, a))
                continue
            if a is None:
                continue
            if tr.signal_time != a["signal_time"] or abs(tr.reference_level - a["level"]) > 1e-9 or abs(tr.confirmation_candle.close - a["close"]) > 1e-9:
                mism.append((ev.date, key, "signal_fields", (tr.signal_time, tr.reference_level), (a["signal_time"], a["level"])))
                continue
            res = ev.trades.get(m)
            t = trade(s.minutes, a["signal_time"], cfg.stop_points, cfg.target_points, entry_convention=cfg.entry_convention, signal_close=a["close"], tie=cfg.tie_policy,
                      forced=cfg.forced_exit.strftime("%H:%M"), cutoff=cfg.entry_cutoff.strftime("%H:%M"))
            n_trd += 1
            if (res is not None and res.get("traded")) != (t is not None):
                mism.append((ev.date, key, "trade_presence", res, t))
                continue
            if t is None:
                continue
            if (abs(res["entry_price"] - t["entry"]) > 1e-9 or res["exit_reason"] != t["reason"] or abs(res.get("gross_points", float("nan")) - t["points"]) > 1e-9
                    or pd.Timestamp(res.get("exit_time", pd.NaT)) != t.get("exit_time", pd.NaT)):
                mism.append((ev.date, key, "trade_fields", {k: res.get(k) for k in ("entry_price", "exit_reason", "gross_points", "exit_time")}, t))
    return {"signal_comparisons": n_sig, "trade_comparisons": n_trd, "mismatches": mism}
