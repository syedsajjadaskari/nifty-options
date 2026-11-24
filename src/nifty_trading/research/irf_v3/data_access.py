"""Session assembly for IRF V3.

Reuses ONLY verified generic infrastructure: the processed one-minute stores, the NSE calendar and ``classify_session`` (session usability) through ``orb_v2.data_access.load_window``.
Everything IRF-related - the 5-minute aggregation below included - is computed here from the raw one-minute rows.

Timestamp convention (verified in Phase 2): a one-minute row labelled HH:MM covers [HH:MM:00, HH:MM+1:00). A 5-minute candle labelled 09:15 aggregates rows 09:15..09:19 and may be used only from 09:20:00.
A candle lacking any of its five rows is dropped, never interpolated.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta

import pandas as pd

from nifty_trading.research.irf_v3.models import Candle

OPEN_MIN = 9 * 60 + 15
CLOSE_MIN = 15 * 60 + 30


def aggregate_candles(day: pd.DataFrame, continuous_until: time | None = None) -> list[Candle]:
    """Complete 5-minute candles from naive-IST ``ts`` rows. ``continuous_until``: drop candles ending after it (closing-auction regime days: 15:15)."""
    d = day.sort_values("ts")
    mm = d["ts"].dt.hour * 60 + d["ts"].dt.minute
    d = d[(mm >= OPEN_MIN) & (mm < CLOSE_MIN)]
    out: list[Candle] = []
    if d.empty:
        return out
    base = pd.Timestamp(d["ts"].iloc[0].normalize())
    bucket = ((d["ts"].dt.hour * 60 + d["ts"].dt.minute) - OPEN_MIN) // 5
    for b, g in d.groupby(bucket, sort=True):
        if len(g) != 5:
            continue
        start = base + pd.Timedelta(minutes=OPEN_MIN + 5 * int(b))
        end = start + pd.Timedelta(minutes=5)
        if continuous_until is not None and end.time() > continuous_until:
            continue
        out.append(Candle(start, end, float(g["open"].iloc[0]), float(g["high"].max()), float(g["low"].min()), float(g["close"].iloc[-1])))
    return out


@dataclass
class Session:
    date: date
    evaluable: bool
    reason: str = ""                # NOT_EVALUATED reason when not evaluable
    minutes: pd.DataFrame | None = None
    candles: list = field(default_factory=list)
    flags: tuple = ()
    gap_in_candles: bool = False    # a missing 5-minute candle between the first and the last one


@dataclass
class Dataset:
    window: str
    vendor: str
    label: str
    start: date
    end: date
    cal: object
    sessions: dict
    provenance: dict


def _expected_sessions(start: date, end: date, cal) -> list[date]:
    days = pd.date_range(start, end).date
    return [x for x in days if x.weekday() < 5 and x not in cal.holidays]


def build_session(d: date, day: pd.DataFrame, info, cal) -> Session:
    if info is not None and not info.usable:
        return Session(d, False, f"SESSION_NOT_USABLE:{info.status.value}", day, [], tuple(info.flags))
    until = cal.closing_auction.frozen_start if (info is not None and info.cas_regime and cal.closing_auction is not None) else None
    candles = aggregate_candles(day, until)
    if not candles:
        return Session(d, False, "NO_COMPLETE_CANDLES", day, [], tuple(info.flags) if info else ())
    gap = any((b.start - a.start) != pd.Timedelta(minutes=5) for a, b in zip(candles, candles[1:], strict=False))
    return Session(d, True, "", day, candles, tuple(info.flags) if info else (), gap)


def load_dataset(window: str, vendor: str = "5P") -> Dataset:
    from nifty_trading.research.orb_v2 import data_access as DA

    inp = DA.load_window(window, vendor)
    sessions: dict[date, Session] = {}
    for d in _expected_sessions(inp.start, inp.end, inp.cal):
        day = inp.day_frames.get(d)
        if day is None:
            sessions[d] = Session(d, False, "NO_DATA")
            continue
        sessions[d] = build_session(d, day, inp.infos.get(d), inp.cal)
    for d, day in inp.day_frames.items():  # rows on dates the calendar does not list as sessions (kept visible, not silently dropped)
        if d not in sessions and inp.start <= d <= inp.end:
            sessions[d] = Session(d, False, "DATE_NOT_A_CALENDAR_SESSION", day)
    return Dataset(window if vendor == "5P" else f"{window}_{vendor}", vendor, inp.label, inp.start, inp.end, inp.cal, dict(sorted(sessions.items())), inp.provenance)


def load_vendor_days(days: list[date], vendor: str = "TV") -> dict[date, Session]:
    """Individual sessions of a vendor store with no classify_session (used for the November-2026 source-example dates, where only the secondary vendor has data).
    A day is evaluable only when it has all 375 one-minute rows 09:15..15:29."""
    from nifty_trading.research import phase4_data as D4

    src = D4.SRC_TV_MIN if vendor == "TV" else D4.SRC_5P_MIN
    m = D4.load_processed_minutes(src)
    m = m.assign(ts=m["timestamp"].dt.tz_localize(None))
    m["_d"] = m["ts"].dt.date
    out = {}
    for d in days:
        g = m[m["_d"] == d]
        if g.empty:
            out[d] = Session(d, False, "NO_DATA_IN_" + vendor + "_STORE")
            continue
        n = len(g[(g["ts"].dt.hour * 60 + g["ts"].dt.minute >= OPEN_MIN) & (g["ts"].dt.hour * 60 + g["ts"].dt.minute < CLOSE_MIN)])
        out[d] = Session(d, True, "", g, aggregate_candles(g), (f"ROWS_{n}_OF_375",))
    return out


def synthetic_session(d: date, five_min: list[tuple], tz_aware: bool = False) -> Session:
    """A session built from 5-minute candle tuples ``(open, high, low, close)`` starting at 09:15. Each candle becomes five coherent one-minute rows
    (o -> first extreme -> second extreme -> c) whose aggregate reproduces the tuple exactly. Used by the unit tests and the illustrative rulebook figures."""
    rows = []
    t0 = pd.Timestamp(d) + pd.Timedelta(minutes=OPEN_MIN)
    for i, (o, h, lo, c) in enumerate(five_min):
        assert h >= max(o, c) and lo <= min(o, c), "inconsistent candle tuple"
        e1, e2 = (lo, h) if c >= o else (h, lo)
        pts = [(o, o), (o, e1), (e1, e2), (e2, c), (c, c)]
        for j, (op, cl) in enumerate(pts):
            rows.append({"ts": t0 + pd.Timedelta(minutes=5 * i + j), "open": op, "high": max(op, cl), "low": min(op, cl), "close": cl})
    df = pd.DataFrame(rows)
    df["timestamp"] = df["ts"].dt.tz_localize("Asia/Kolkata") if tz_aware else df["ts"]
    return Session(d, True, "", df, aggregate_candles(df), ())


def prev_calendar_day(d: date) -> date:
    return d - timedelta(days=1)
