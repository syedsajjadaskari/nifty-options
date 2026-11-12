"""Five-minute aggregation built from raw one-minute rows (independent of data/sessions.py candle construction).

Timestamp convention (verified in Phase 2): a 1-minute row labelled HH:MM covers [HH:MM:00, HH:MM+1:00). A 5-minute candle labelled 09:15 aggregates the rows
09:15..09:19 and is COMPLETE ONLY AT 09:20:00; it may not be used earlier. A candle with fewer than five rows is dropped, never interpolated.
"""

from __future__ import annotations

from datetime import time

import pandas as pd

SESSION_OPEN = time(9, 15)


def aggregate_5m(day: pd.DataFrame) -> pd.DataFrame:
    """Complete 5-minute candles of one session from its 1-minute rows (naive IST ``ts`` column required). Columns: start, end, open, high, low, close, n."""
    d = day.sort_values("ts")
    d = d[(d["ts"].dt.time >= SESSION_OPEN) & (d["ts"].dt.time < time(15, 30))]  # the 15:30 row is a closing-print stub: never part of a candle
    if d.empty:
        return pd.DataFrame(columns=["start", "end", "open", "high", "low", "close", "n"])
    minutes_since_open = (d["ts"].dt.hour * 60 + d["ts"].dt.minute) - (9 * 60 + 15)
    d = d.assign(_b=(minutes_since_open // 5).to_numpy())
    g = d.groupby("_b", sort=True)
    out = pd.DataFrame({"open": g["open"].first(), "high": g["high"].max(), "low": g["low"].min(), "close": g["close"].last(), "n": g["open"].size(), "start": g["ts"].first()})
    out["start"] = [pd.Timestamp(d["ts"].iloc[0].normalize()) + pd.Timedelta(minutes=9 * 60 + 15 + 5 * int(b)) for b in out.index]
    out["end"] = out["start"] + pd.Timedelta(minutes=5)
    out = out[out["n"] == 5].reset_index(drop=True)
    return out[["start", "end", "open", "high", "low", "close", "n"]]


def opening_candle(day: pd.DataFrame) -> dict | None:
    """The 09:15-09:20 candle (None when any of its five minutes is missing). ``confirmed_at`` is 09:20:00."""
    d = day.sort_values("ts")
    t0 = pd.Timestamp(d["ts"].iloc[0].normalize()) + pd.Timedelta(hours=9, minutes=15)
    rows = d[(d["ts"] >= t0) & (d["ts"] < t0 + pd.Timedelta(minutes=5))]
    if len(rows) != 5 or rows["ts"].iloc[0] != t0:
        return None
    return {"start": t0, "confirmed_at": t0 + pd.Timedelta(minutes=5), "open": float(rows["open"].iloc[0]), "high": float(rows["high"].max()), "low": float(rows["low"].min()),
            "close": float(rows["close"].iloc[-1])}
