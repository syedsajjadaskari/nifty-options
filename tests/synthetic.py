"""Deterministic synthetic-candle builders for the Phase 2 strategy tests."""

from __future__ import annotations

import math
from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

import pandas as pd

from nifty_trading.data.sessions import (
    PreviousSession,
    SessionContext,
    SessionInfo,
    SessionStatus,
)

IST = ZoneInfo("Asia/Kolkata")
DAY = date(2026, 1, 12)
PREV_DAY = date(2026, 1, 9)


def frame(cands, day=DAY, ema=math.nan) -> pd.DataFrame:
    """cands: list of (o, h, l, c) 5-minute candles starting 09:15."""
    t0 = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    rows = []
    emas = ema if isinstance(ema, (list, tuple)) else [ema] * len(cands)
    for k, (o, h, l, c) in enumerate(cands):
        s = t0 + timedelta(minutes=5 * k)
        rows.append({"bar_start": s, "bar_end": s + timedelta(minutes=5), "open": o, "high": h, "low": l,
                     "close": c, "n_minutes": 5, "ema200_5m": emas[k]})
    return pd.DataFrame(rows)


def ctx(cands, *, prev=None, ema=math.nan, prior_above=(True,), day=DAY, usable=True, open_price=None,
        flags=(), daily_sma=math.nan, daily_ema=math.nan, daily_count=0) -> SessionContext:
    """prev: dict(cands, close, ema_last, unverified) or None."""
    f = frame(cands, day, ema)
    previous = None
    if prev is not None:
        pf = frame(prev["cands"], PREV_DAY, prev.get("ema_last", math.nan))
        previous = PreviousSession(
            date=PREV_DAY, open=float(pf["open"].iloc[0]), high=float(pf["high"].max()), low=float(pf["low"].min()),
            close_official=prev.get("close"), last_5m_close=float(pf["close"].iloc[-1]), candles=pf,
            ema_at_last_candle=float(prev.get("ema_last", math.nan)),
            gap_to_this_session_unverified=bool(prev.get("unverified", False)),
        )
    info = SessionInfo(day, SessionStatus.USABLE if usable else SessionStatus.EXCLUDED_NON_STANDARD_START, (),
                       len(cands) * 5, len(cands), None, "NONE")
    return SessionContext(
        date=day, info=info, candles=f, previous=previous,
        open_price=float(f["open"].iloc[0]) if open_price is None else open_price,
        daily_history_count=daily_count, daily_sma200_prev=daily_sma, daily_ema200_prev=daily_ema,
        prior_session_ema_above=tuple(prior_above), data_flags=tuple(flags),
    )


def minute_rows(cands, day=DAY) -> pd.DataFrame:
    """Expand 5-minute (o, h, l, c) candles into five 1-minute rows each.

    The five rows aggregate back to exactly (o, h, l, c): open o, high h reached on minute 2,
    low l reached on minute 3, close c on minute 5. Requires h >= max(o, c) and l <= min(o, c).
    """
    t0 = datetime(day.year, day.month, day.day, 9, 15, tzinfo=IST)
    rows = []
    for k, (o, h, l, c) in enumerate(cands):
        assert h >= max(o, c) and l <= min(o, c), f"invalid candle {k}: {(o, h, l, c)}"
        vals = [(o, o, o, o), (o, h, o, h), (h, h, l, l), (l, l, l, l), (l, max(l, c), min(l, c), c)]
        for m, (oo, hh, ll, cc) in enumerate(vals):
            rows.append({"timestamp": t0 + timedelta(minutes=5 * k + m), "open": oo, "high": hh, "low": ll,
                         "close": cc, "volume": 0})
    return pd.DataFrame(rows)
