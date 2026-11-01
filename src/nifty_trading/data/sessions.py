"""Session classification, 5-minute candle construction and causal indicators.

Timestamp convention (verified against the Phase 1 dataset, see
``reports/phase2/dataset_verification.md``): a 1-minute row labelled ``HH:MM`` covers
``[HH:MM:00, HH:MM+1:00)``. The 09:15 row is a full-size bar and the 15:30 row is a
closing-print stub (74.8% zero-range). Hence a 5-minute candle labelled ``09:15``
aggregates the rows 09:15..09:19, is complete only at 09:20:00 and may not be used before.

Nothing here fabricates data: a 5-minute candle with fewer than five 1-minute rows is
dropped, never interpolated.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

SESSION_OPEN = time(9, 15)
LAST_MINUTE_LABEL = time(15, 29)  # last full 1-minute bar of a normal session
CLOSE_STUB_LABEL = time(15, 30)  # closing-print stub, excluded from candles
CANDLE_MINUTES = 5
EXPECTED_5M_CANDLES = 75  # 09:15 .. 15:25 start labels
EMA_PERIOD_DEFAULT = 200
STALE_RUN_MIN = 5  # consecutive identical flat 1-minute rows that mark a frozen feed
DAILY_MA_PERIOD = 200


class SessionStatus(str, Enum):
    USABLE = "USABLE"
    USABLE_WITH_FLAGS = "USABLE_WITH_FLAGS"
    EXCLUDED_NON_STANDARD_START = "EXCLUDED_NON_STANDARD_START"  # e.g. Muhurat session
    EXCLUDED_NO_OPENING_CANDLE = "EXCLUDED_NO_OPENING_CANDLE"  # 09:15 candle incomplete


@dataclass(frozen=True)
class SessionInfo:
    date: date
    status: SessionStatus
    flags: tuple[str, ...]
    n_1m_rows: int
    n_5m_candles: int
    official_close: float | None  # 15:30 stub close when present
    close_source: str  # "STUB_1530" | "LAST_1529" | "NONE"

    @property
    def usable(self) -> bool:
        return self.status in (SessionStatus.USABLE, SessionStatus.USABLE_WITH_FLAGS)


def load_one_minute(processed_dir: str | Path | None = None) -> pd.DataFrame:
    """Read every Phase 1 Parquet partition into one chronologically sorted frame."""
    if processed_dir is None:
        from nifty_trading.config.settings import settings

        processed_dir = settings.processed_data_dir
    pattern = str(Path(processed_dir) / "nifty50" / "year=*" / "month=*" / "candles.parquet")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no parquet partitions match {pattern}")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return df.sort_values("timestamp").reset_index(drop=True)


def stale_row_mask(rows: pd.DataFrame, min_run: int = STALE_RUN_MIN) -> pd.Series:
    """True for rows inside a run of >= ``min_run`` consecutive 1-minute rows that all equal one frozen price.

    A run of identical O=H=L=C rows is a frozen feed, not trading (the Phase 1 data has none before 2026-08-03,
    then 13-14 of them at the end of every session followed by a one-minute catch-up jump). Such rows are not
    market data; any 5-minute candle containing one is dropped, never repaired.
    """
    flat = ((rows["open"] == rows["high"]) & (rows["high"] == rows["low"]) & (rows["low"] == rows["close"])).to_numpy()
    price = rows["close"].to_numpy()
    mins = (rows["timestamp"].dt.hour * 60 + rows["timestamp"].dt.minute).to_numpy()
    out = np.zeros(len(rows), dtype=bool)
    i = 0
    while i < len(rows):
        if not flat[i]:
            i += 1
            continue
        j = i
        while j + 1 < len(rows) and flat[j + 1] and price[j + 1] == price[i] and mins[j + 1] == mins[j] + 1:
            j += 1
        if j - i + 1 >= min_run:
            out[i:j + 1] = True
        i = j + 1
    return pd.Series(out, index=rows.index)


def _day_5m(day_df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Aggregate one session's 1-minute rows. Returns (complete candles, dropped candle count)."""
    cols = ["bar_start", "bar_end", "open", "high", "low", "close", "n_minutes"]
    t = day_df["timestamp"]
    minute_of_day = t.dt.hour * 60 + t.dt.minute
    lo = SESSION_OPEN.hour * 60 + SESSION_OPEN.minute
    hi = LAST_MINUTE_LABEL.hour * 60 + LAST_MINUTE_LABEL.minute
    sel = day_df[(minute_of_day >= lo) & (minute_of_day <= hi)].copy()
    if sel.empty:
        return pd.DataFrame(columns=cols), 0
    sel["bucket"] = (minute_of_day[sel.index] - lo) // CANDLE_MINUTES
    sel = sel.sort_values("timestamp")
    stale = stale_row_mask(sel)
    stale_buckets = set(sel.loc[stale, "bucket"])
    sel = sel[~sel["bucket"].isin(stale_buckets)]
    if sel.empty:
        return pd.DataFrame(columns=cols), 0
    g = sel.groupby("bucket", sort=True)
    agg = g.agg(
        bar_start=("timestamp", "min"),
        open=("open", "first"),
        high=("high", "max"),
        low=("low", "min"),
        close=("close", "last"),
        n_minutes=("timestamp", "nunique"),
    ).reset_index(drop=True)
    complete = agg[agg["n_minutes"] == CANDLE_MINUTES].copy()
    dropped = len(agg) - len(complete)
    # bar_start must sit on the 5-minute grid (it is the earliest row of a full bucket)
    complete["bar_end"] = complete["bar_start"] + pd.Timedelta(minutes=CANDLE_MINUTES)
    return complete[cols].reset_index(drop=True), dropped


def classify_session(day_df: pd.DataFrame) -> tuple[SessionInfo, pd.DataFrame]:
    """Classify one calendar day of 1-minute rows and build its complete 5-minute candles."""
    d = day_df["timestamp"].iloc[0].date()
    flags: list[str] = []
    times = day_df["timestamp"].dt.time
    first = times.min()
    if first != SESSION_OPEN:
        info = SessionInfo(d, SessionStatus.EXCLUDED_NON_STANDARD_START, ("NON_STANDARD_START",),
                           len(day_df), 0, None, "NONE")
        return info, pd.DataFrame()
    if d.weekday() >= 5:
        flags.append("WEEKEND_SPECIAL_SESSION")
    after_close = int((times > CLOSE_STUB_LABEL).sum())
    if after_close:
        flags.append(f"EXTENDED_RECORDS_AFTER_1530_CLIPPED:{after_close}")
    in_window = day_df[(times >= SESSION_OPEN) & (times <= LAST_MINUTE_LABEL)].sort_values("timestamp")
    n_stale = int(stale_row_mask(in_window).sum()) if len(in_window) else 0
    candles, dropped = _day_5m(day_df)
    if n_stale:
        flags.append(f"STALE_FEED_ROWS_EXCLUDED:{n_stale}")
    if dropped:
        flags.append(f"INCOMPLETE_5M_CANDLES_DROPPED:{dropped}")
    stub = day_df[times == CLOSE_STUB_LABEL]
    if len(stub):
        official, src = float(stub["close"].iloc[0]), "STUB_1530"
    else:
        flags.append("MISSING_1530_CLOSE_STUB")
        last = day_df[times == LAST_MINUTE_LABEL]
        official, src = (float(last["close"].iloc[0]), "LAST_1529") if len(last) else (None, "NONE")
    if candles.empty or candles["bar_start"].iloc[0].time() != SESSION_OPEN:
        info = SessionInfo(d, SessionStatus.EXCLUDED_NO_OPENING_CANDLE,
                           tuple(flags + ["NO_COMPLETE_OPENING_CANDLE"]), len(day_df), len(candles),
                           official, src)
        return info, candles
    status = SessionStatus.USABLE_WITH_FLAGS if flags else SessionStatus.USABLE
    return SessionInfo(d, status, tuple(flags), len(day_df), len(candles), official, src), candles


def causal_ema(values: np.ndarray, period: int) -> np.ndarray:
    """EMA seeded with the SMA of the first ``period`` values.

    Output is NaN for the first ``period - 1`` positions: no partially-initialised value is
    ever returned. Each output depends only on values at or before its own position.
    """
    n = len(values)
    out = np.full(n, np.nan)
    if n < period:
        return out
    alpha = 2.0 / (period + 1.0)
    out[period - 1] = float(np.mean(values[:period]))
    for i in range(period, n):
        out[i] = alpha * values[i] + (1.0 - alpha) * out[i - 1]
    return out


def causal_sma(values: np.ndarray, period: int) -> np.ndarray:
    n = len(values)
    out = np.full(n, np.nan)
    if n < period:
        return out
    c = np.cumsum(np.insert(values, 0, 0.0))
    out[period - 1:] = (c[period:] - c[:-period]) / period
    return out


@dataclass
class PreviousSession:
    date: date
    open: float
    high: float  # 5-minute-candle based (15:30 stub excluded)
    low: float
    close_official: float | None
    last_5m_close: float
    candles: pd.DataFrame
    ema_at_last_candle: float  # NaN when EMA warm-up was incomplete
    gap_to_this_session_unverified: bool  # weekday(s) without data between prev and today


@dataclass
class SessionContext:
    """Everything a strategy may know at/after 09:20 of one session. Causal by construction."""

    date: date
    info: SessionInfo
    candles: pd.DataFrame  # complete 5-minute candles + ``ema200_5m`` column
    previous: PreviousSession | None
    open_price: float  # first 1-minute open (09:15 row)
    daily_history_count: int  # number of usable prior daily bars
    daily_sma200_prev: float  # SMA of last 200 daily closes up to PREVIOUS session (NaN if <200)
    daily_ema200_prev: float
    prior_session_ema_above: tuple[bool | None, ...]  # per prior session (newest first): last 5m close > EMA?
    data_flags: tuple[str, ...] = field(default_factory=tuple)

    @property
    def prev_close(self) -> float | None:
        return None if self.previous is None else self.previous.close_official

    def prefix(self, n_candles: int) -> SessionContext:
        """The same session as it looked after ``n_candles`` candles had closed (for look-ahead tests)."""
        return SessionContext(**{**self.__dict__, "candles": self.candles.iloc[:n_candles].reset_index(drop=True)})


def build_session_contexts(
    df_1m: pd.DataFrame,
    ema_period: int = EMA_PERIOD_DEFAULT,
    verified_holidays: set[date] | None = None,
) -> tuple[dict[date, SessionContext], dict[date, SessionInfo]]:
    """Classify all sessions, build 5-minute candles and the causal indicator inputs."""
    if verified_holidays is None:
        # Phase 1 calendar list. It is itself unverified against NSE circulars (see the Phase 2
        # dataset audit); it is used only to decide which missing weekdays are *explained*.
        from nifty_trading.data.calendar import NSE_HOLIDAYS

        verified_holidays = {date.fromisoformat(x) for x in NSE_HOLIDAYS}
    df = df_1m.sort_values("timestamp").reset_index(drop=True)  # callers may pass concatenated frames with repeated labels
    df["_d"] = df["timestamp"].dt.date
    infos: dict[date, SessionInfo] = {}
    candles_by_day: dict[date, pd.DataFrame] = {}
    for d, day_df in df.groupby("_d", sort=True):
        info, c = classify_session(day_df.drop(columns="_d"))
        infos[d] = info
        if info.usable:
            candles_by_day[d] = c

    usable = sorted(candles_by_day)
    # ---- 5-minute EMA over the concatenated, chronologically ordered, complete candles
    if usable:
        closes = np.concatenate([candles_by_day[d]["close"].to_numpy() for d in usable])
        ema = causal_ema(closes, ema_period)
        pos = 0
        for d in usable:
            n = len(candles_by_day[d])
            candles_by_day[d]["ema200_5m"] = ema[pos:pos + n]
            pos += n

    # ---- daily bars (official close) -> daily MAs that use only PREVIOUS sessions
    daily_close = np.array([infos[d].official_close if infos[d].official_close is not None
                            else candles_by_day[d]["close"].iloc[-1] for d in usable], dtype=float)
    sma_d = causal_sma(daily_close, DAILY_MA_PERIOD)
    ema_d = causal_ema(daily_close, DAILY_MA_PERIOD)

    ctxs: dict[date, SessionContext] = {}
    above: list[bool | None] = []  # chronological: last 5m close > EMA for each usable session
    for k, d in enumerate(usable):
        c = candles_by_day[d]
        prev: PreviousSession | None = None
        flags: list[str] = []
        if k > 0:
            pd_ = usable[k - 1]
            pc = candles_by_day[pd_]
            between = pd.date_range(pd_ + timedelta(days=1), d - timedelta(days=1)).date
            missing_weekdays = [x for x in between if x.weekday() < 5 and x not in infos
                                and x not in verified_holidays]
            excluded_between = [x for x in between if x in infos and not infos[x].usable]
            close_doubt = [f for f in infos[pd_].flags
                           if f.startswith(("STALE_FEED", "EXTENDED_RECORDS"))]
            e_last = float(pc["ema200_5m"].iloc[-1])
            prev = PreviousSession(
                date=pd_, open=float(pc["open"].iloc[0]), high=float(pc["high"].max()),
                low=float(pc["low"].min()), close_official=infos[pd_].official_close,
                last_5m_close=float(pc["close"].iloc[-1]), candles=pc, ema_at_last_candle=e_last,
                gap_to_this_session_unverified=bool(missing_weekdays or excluded_between or close_doubt),
            )
            if missing_weekdays:
                flags.append("PREV_SESSION_GAP_UNVERIFIED:" + ",".join(map(str, missing_weekdays)))
            if excluded_between:  # e.g. a Muhurat session sits between: which close is 'previous close' is unknown
                flags.append("PREV_SESSION_SKIPS_EXCLUDED_SESSION:" + ",".join(map(str, excluded_between)))
            if close_doubt:  # frozen-feed tail or post-close prints: the previous official close is not trustworthy
                flags.append(f"PREV_CLOSE_UNRELIABLE({pd_}:{'|'.join(close_doubt)})")
        else:
            flags.append("NO_PREVIOUS_SESSION_IN_DATASET")
        hist = tuple(reversed(above))  # newest first
        ctxs[d] = SessionContext(
            date=d, info=infos[d], candles=c, previous=prev, open_price=float(c["open"].iloc[0]),
            daily_history_count=k,
            daily_sma200_prev=float(sma_d[k - 1]) if k >= 1 and not np.isnan(sma_d[k - 1]) else float("nan"),
            daily_ema200_prev=float(ema_d[k - 1]) if k >= 1 and not np.isnan(ema_d[k - 1]) else float("nan"),
            prior_session_ema_above=hist, data_flags=tuple(flags) + tuple(f"SESSION:{f}" for f in infos[d].flags),
        )
        e_end = float(c["ema200_5m"].iloc[-1])
        above.append(None if np.isnan(e_end) else bool(c["close"].iloc[-1] > e_end))
    return ctxs, infos
