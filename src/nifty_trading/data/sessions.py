"""Session classification, 5-minute candle construction and causal indicators.

Timestamp convention (verified against the Phase 1 dataset, see
``reports/phase2/dataset_verification.md``): a 1-minute row labelled ``HH:MM`` covers
``[HH:MM:00, HH:MM+1:00)``. The 09:15 row is a full-size bar and the 15:30 row is a
closing-print stub (74.8% zero-range). Hence a 5-minute candle labelled ``09:15``
aggregates the rows 09:15..09:19, is complete only at 09:20:00 and may not be used before.

Nothing here fabricates data: a 5-minute candle with fewer than five 1-minute rows is
dropped, never interpolated.

Phase 2.1 corrections (see ``docs/phase2/data_repair_report.md``):
* From 2026-08-03 NSE runs a Closing Auction Session: the index is frozen from 15:15 until the official
  close appears. Frozen rows inside that window on/after that date are REAL and are kept (flagged); a frozen
  run anywhere else is an anomaly and marks the session CORRUPT.
* The official close is the vendor DAILY close (confirmed against published closes); the 15:30 minute print is
  only a fallback because before the auction regime it is the last tick, not the official close.
* Pre-period 1-minute data may be supplied as WARM-UP ONLY: it seeds the EMA but is never evaluated.
"""

from __future__ import annotations

import glob
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from enum import Enum
from pathlib import Path

import numpy as np
import pandas as pd

from nifty_trading.data.market_calendar import MarketCalendar, load_market_calendar

SESSION_OPEN = time(9, 15)
LAST_MINUTE_LABEL = time(15, 29)  # last full 1-minute bar of a normal session
CLOSE_STUB_LABEL = time(15, 30)  # closing-print stub, excluded from candles
CANDLE_MINUTES = 5
EXPECTED_5M_CANDLES = 75  # 09:15 .. 15:25 start labels
EMA_PERIOD_DEFAULT = 200
STALE_RUN_MIN = 5  # consecutive identical flat 1-minute rows that mark a frozen index
DAILY_MA_PERIOD = 200
OFFICIAL_CLOSE_TOLERANCE = 0.05


class SessionStatus(str, Enum):
    USABLE = "USABLE"
    USABLE_WITH_FLAGS = "USABLE_WITH_FLAGS"
    EXCLUDED_NON_STANDARD_START = "EXCLUDED_NON_STANDARD_START"  # e.g. Muhurat session
    EXCLUDED_NO_OPENING_CANDLE = "EXCLUDED_NO_OPENING_CANDLE"  # 09:15 candle incomplete
    EXCLUDED_CORRUPT = "EXCLUDED_CORRUPT"
    EXCLUDED_UNVERIFIED = "EXCLUDED_UNVERIFIED"


class SessionQuality(str, Enum):
    """Per-day data-quality status (Phase 2.1)."""

    VALID = "VALID"
    VALID_SPECIAL_SESSION = "VALID_SPECIAL_SESSION"
    PARTIAL = "PARTIAL"
    CORRUPT = "CORRUPT"
    MISSING = "MISSING"
    UNVERIFIED = "UNVERIFIED"


@dataclass(frozen=True)
class SessionInfo:
    date: date
    status: SessionStatus
    flags: tuple[str, ...]
    n_1m_rows: int
    n_5m_candles: int
    official_close: float | None  # vendor daily close when supplied, else the 15:30 print
    close_source: str  # "DAILY_VENDOR" | "STUB_1530" | "LAST_1529" | "NONE"
    quality: SessionQuality = SessionQuality.VALID
    reasons: tuple[str, ...] = ()  # why the quality is not VALID (empty for VALID)
    cas_regime: bool = False  # closing-auction regime applies to this date
    stub_close: float | None = None  # the 15:30 minute print, kept for the official-close comparison

    @property
    def usable(self) -> bool:
        """True when strategies may evaluate this session."""
        return self.status in (SessionStatus.USABLE, SessionStatus.USABLE_WITH_FLAGS)


def _processed_dir(processed_dir: str | Path | None) -> Path:
    if processed_dir is None:
        from nifty_trading.config.settings import settings

        processed_dir = settings.processed_data_dir
    return Path(processed_dir)


def load_one_minute(processed_dir: str | Path | None = None) -> pd.DataFrame:
    """Read every Phase 1 Parquet partition into one chronologically sorted frame."""
    pattern = str(_processed_dir(processed_dir) / "nifty50" / "year=*" / "month=*" / "candles.parquet")
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"no parquet partitions match {pattern}")
    df = pd.concat([pd.read_parquet(f) for f in files], ignore_index=True)
    return df.sort_values("timestamp").reset_index(drop=True)


def load_warmup_one_minute(processed_dir: str | Path | None = None) -> pd.DataFrame | None:
    """Pre-period 1-minute data (WARM-UP ONLY: seeds indicators, never evaluated). None when not present."""
    files = sorted(glob.glob(str(_processed_dir(processed_dir) / "nifty50_warmup" / "year=*" / "month=*" / "candles.parquet")))
    if not files:
        return None
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def load_daily_official(processed_dir: str | Path | None = None) -> pd.DataFrame | None:
    """Vendor daily candles (official closes) with columns date, open, high, low, close. None when not present."""
    f = _processed_dir(processed_dir) / "nifty50_daily" / "candles.parquet"
    if not f.exists():
        return None
    df = pd.read_parquet(f)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date").reset_index(drop=True)


def stale_row_mask(rows: pd.DataFrame, min_run: int = STALE_RUN_MIN) -> pd.Series:
    """True for rows inside a run of >= ``min_run`` consecutive 1-minute rows that all equal one frozen price.

    Whether such a run is an anomaly or the expected closing-auction freeze is decided by the caller
    (``classify_session``): inside 15:15-15:29 on/after 2026-08-03 it is expected; anywhere else it is not.
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


def _day_5m(day_df: pd.DataFrame, exclude_buckets_of: pd.Series | None = None) -> tuple[pd.DataFrame, int]:
    """Aggregate one session's 1-minute rows. Returns (complete candles, dropped candle count).

    ``exclude_buckets_of``: optional boolean mask (aligned to ``day_df``) of rows whose whole 5-minute candle must be
    dropped (used for anomalous frozen runs). Dropped candles are never repaired.
    """
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
    if exclude_buckets_of is not None and exclude_buckets_of.any():
        bad = set(sel.loc[exclude_buckets_of.reindex(sel.index, fill_value=False), "bucket"])
        sel = sel[~sel["bucket"].isin(bad)]
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
    complete["bar_end"] = complete["bar_start"] + pd.Timedelta(minutes=CANDLE_MINUTES)
    return complete[cols].reset_index(drop=True), dropped


def _info(d, status, quality, reasons, flags, n_rows, n_candles, official, src, cas, stub):
    return SessionInfo(d, status, tuple(flags), n_rows, n_candles, official, src, quality, tuple(reasons), cas, stub)


def classify_session(
    day_df: pd.DataFrame,
    calendar: MarketCalendar | None = None,
    daily_close: float | None = None,
) -> tuple[SessionInfo, pd.DataFrame]:
    """Classify one calendar day of 1-minute rows, assign its quality status and build its complete 5-minute candles.

    ``calendar`` defaults to an empty calendar (no special sessions, no closing-auction regime), which keeps the
    behaviour of a bare call conservative. ``daily_close`` is the vendor's official daily close for the date, if known.
    """
    cal = calendar or MarketCalendar()
    d = day_df["timestamp"].iloc[0].date()
    flags: list[str] = []
    reasons: list[str] = []
    times = day_df["timestamp"].dt.time
    n_rows = len(day_df)
    cas = bool(cal.closing_auction and cal.closing_auction.applies(d))

    stub = day_df[times == CLOSE_STUB_LABEL]
    stub_close = float(stub["close"].iloc[0]) if len(stub) else None
    if daily_close is not None:
        official, src = float(daily_close), "DAILY_VENDOR"
        if stub_close is not None and abs(stub_close - official) > OFFICIAL_CLOSE_TOLERANCE:
            flags.append(f"OFFICIAL_CLOSE_DIFFERS_FROM_1530_PRINT:{official - stub_close:+.2f}")
    elif stub_close is not None:
        official, src = stub_close, "STUB_1530"
    else:
        last = day_df[times == LAST_MINUTE_LABEL]
        official, src = (float(last["close"].iloc[0]), "LAST_1529") if len(last) else (None, "NONE")

    # --- non-standard start (special evening sessions etc.)
    if times.min() != SESSION_OPEN:
        entry = cal.special_sessions.get(d)
        q = SessionQuality.VALID_SPECIAL_SESSION if entry else SessionQuality.UNVERIFIED
        return _info(d, SessionStatus.EXCLUDED_NON_STANDARD_START, q,
                     ["NON_STANDARD_START" + (":" + entry.name if entry else ":not in calendar")],
                     ["NON_STANDARD_START"], n_rows, 0, official, src, cas, stub_close), pd.DataFrame()

    # --- weekend sessions must be known special sessions
    quality = SessionQuality.VALID
    if d.weekday() >= 5:
        entry = cal.special_sessions.get(d)
        flags.append("WEEKEND_SPECIAL_SESSION")
        if entry is None:
            return _info(d, SessionStatus.EXCLUDED_UNVERIFIED, SessionQuality.UNVERIFIED, ["WEEKEND_SESSION_NOT_IN_CALENDAR"],
                         flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()
        quality = SessionQuality.VALID_SPECIAL_SESSION
        if not entry.evaluable_by_strategies:
            return _info(d, SessionStatus.EXCLUDED_NON_STANDARD_START, quality, ["SPECIAL_SESSION_NOT_EVALUABLE"],
                         flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()

    # --- structural integrity
    if day_df["timestamp"].duplicated().any():
        return _info(d, SessionStatus.EXCLUDED_CORRUPT, SessionQuality.CORRUPT, ["DUPLICATE_TIMESTAMPS"], flags, n_rows, 0,
                     official, src, cas, stub_close), pd.DataFrame()
    bad_ohlc = ((day_df["high"] < day_df[["open", "close"]].max(axis=1)) | (day_df["low"] > day_df[["open", "close"]].min(axis=1))
                | day_df[["open", "high", "low", "close"]].isna().any(axis=1))
    if bad_ohlc.any():
        return _info(d, SessionStatus.EXCLUDED_CORRUPT, SessionQuality.CORRUPT, [f"OHLC_INCONSISTENT_ROWS:{int(bad_ohlc.sum())}"],
                     flags, n_rows, 0, official, src, cas, stub_close), pd.DataFrame()

    after_close = int((times > CLOSE_STUB_LABEL).sum())
    if after_close:
        flags.append(f"POST_CLOSE_RECORDS_CLIPPED:{after_close}")

    # --- frozen runs: expected inside the auction window on/after the regime date, an anomaly anywhere else
    in_window = day_df[(times >= SESSION_OPEN) & (times <= LAST_MINUTE_LABEL)].sort_values("timestamp")
    frozen = stale_row_mask(in_window) if len(in_window) else pd.Series(dtype=bool)
    anomalous = pd.Series(False, index=day_df.index)
    if frozen.any():
        fr = in_window[frozen]
        ftimes = fr["timestamp"].dt.time
        if cas and cal.closing_auction is not None:
            inside = (ftimes >= cal.closing_auction.frozen_start) & (ftimes <= cal.closing_auction.frozen_end)
            flags.append(f"CAS_FROZEN_WINDOW_KEPT:{int(inside.sum())}")
            outside = fr[~inside.to_numpy()]
            # the expected auction freeze starts at 15:15/15:16 (the index stops updating when continuous trading ends); a run that starts
            # later inside the window is a feed stall that merely looks similar, so the session cannot be called VALID
            late_start = fr[inside.to_numpy()]["timestamp"].dt.time.min() > time(15, 16) if inside.any() else False
            if late_start:
                reasons.append("FROZEN_RUN_INSIDE_AUCTION_WINDOW_STARTS_AFTER_1516")
                return _info(d, SessionStatus.EXCLUDED_UNVERIFIED, SessionQuality.UNVERIFIED, reasons, flags, n_rows, 0, official, src, cas,
                             stub_close), pd.DataFrame()
        else:
            outside = fr
        if len(outside):
            anomalous.loc[outside.index] = True
            reasons.append(f"FROZEN_FEED_OUTSIDE_AUCTION_WINDOW:{len(outside)}")
            quality = SessionQuality.CORRUPT

    candles, dropped = _day_5m(day_df, anomalous)
    if dropped:
        flags.append(f"INCOMPLETE_5M_CANDLES_DROPPED:{dropped}")
        reasons.append(f"MISSING_MINUTE_BARS_IN_{dropped}_CANDLES")
        if quality is SessionQuality.VALID or quality is SessionQuality.VALID_SPECIAL_SESSION:
            quality = SessionQuality.PARTIAL
    if stub_close is None:
        flags.append("MISSING_1530_CLOSE_STUB")  # non-critical: the official close comes from the daily series

    if quality is SessionQuality.CORRUPT:
        return _info(d, SessionStatus.EXCLUDED_CORRUPT, quality, reasons, flags, n_rows, len(candles), official, src, cas,
                     stub_close), candles
    if candles.empty or candles["bar_start"].iloc[0].time() != SESSION_OPEN:
        return _info(d, SessionStatus.EXCLUDED_NO_OPENING_CANDLE, SessionQuality.PARTIAL, reasons + ["NO_COMPLETE_OPENING_CANDLE"],
                     flags + ["NO_COMPLETE_OPENING_CANDLE"], n_rows, len(candles), official, src, cas, stub_close), candles
    status = SessionStatus.USABLE_WITH_FLAGS if flags else SessionStatus.USABLE
    return _info(d, status, quality, reasons, flags, n_rows, len(candles), official, src, cas, stub_close), candles


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
    high: float  # of ALL complete 5-minute candles (the 15:30 print is never a candle)
    low: float
    close_official: float | None
    last_5m_close: float
    candles: pd.DataFrame
    ema_at_last_candle: float  # NaN when EMA warm-up was incomplete
    gap_to_this_session_unverified: bool  # something between prev and today makes 'previous day' uncertain
    continuous_candles: pd.DataFrame | None = None  # candles before the closing auction (== candles outside the regime)
    close_source: str = "STUB_1530"
    close_1530_print: float | None = None  # last 1-minute print at 15:30 (alternative previous-close definition)

    @property
    def high_continuous(self) -> float:
        c = self.continuous_candles if self.continuous_candles is not None else self.candles
        return float(c["high"].max())

    @property
    def low_continuous(self) -> float:
        c = self.continuous_candles if self.continuous_candles is not None else self.candles
        return float(c["low"].min())


@dataclass
class SessionContext:
    """Everything a strategy may know at/after 09:20 of one session. Causal by construction."""

    date: date
    info: SessionInfo
    candles: pd.DataFrame  # complete 5-minute candles + ``ema200_5m`` column
    previous: PreviousSession | None
    open_price: float  # first 1-minute open (09:15 row)
    daily_history_count: int  # number of prior OFFICIAL daily bars available (>= 200 needed for the daily MA)
    daily_sma200_prev: float  # SMA of the last 200 official daily closes strictly before this session (NaN if <200)
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
    *,
    calendar: MarketCalendar | None = None,
    daily_df: pd.DataFrame | None = None,
    warmup_1m: pd.DataFrame | None = None,
) -> tuple[dict[date, SessionContext], dict[date, SessionInfo]]:
    """Classify all sessions, build 5-minute candles and the causal indicator inputs.

    ``warmup_1m`` rows precede ``df_1m``: they seed the EMA and supply the previous session of the first evaluated day,
    but no context or info is produced for them. ``daily_df`` (date, open, high, low, close) supplies official closes and
    the daily moving averages (which need >= 200 earlier daily bars).
    """
    cal = calendar if calendar is not None else load_market_calendar()
    if verified_holidays is None:
        verified_holidays = set(cal.holidays)
    analysis_start = df_1m["timestamp"].dt.date.min()
    frames = [warmup_1m, df_1m] if warmup_1m is not None else [df_1m]
    df = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    df["_d"] = df["timestamp"].dt.date
    daily_close_by_date: dict[date, float] = {}
    if daily_df is not None:
        daily_close_by_date = dict(zip(daily_df["date"], daily_df["close"].astype(float), strict=True))
    infos: dict[date, SessionInfo] = {}
    candles_by_day: dict[date, pd.DataFrame] = {}
    for d, day_df in df.groupby("_d", sort=True):
        info, c = classify_session(day_df.drop(columns="_d"), cal, daily_close_by_date.get(d))
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

    # ---- daily moving averages: official daily closes strictly BEFORE the session (never including its own close)
    if daily_df is not None and len(daily_df):
        dd_dates = list(daily_df["date"])
        dd_close = daily_df["close"].to_numpy(dtype=float)
    else:  # fall back to the closes of the evaluated sessions themselves
        dd_dates = usable
        dd_close = np.array([infos[d].official_close if infos[d].official_close is not None
                             else candles_by_day[d]["close"].iloc[-1] for d in usable], dtype=float)
    sma_d = causal_sma(dd_close, DAILY_MA_PERIOD)
    ema_d = causal_ema(dd_close, DAILY_MA_PERIOD)

    import bisect

    ctxs: dict[date, SessionContext] = {}
    out_infos: dict[date, SessionInfo] = {d: i for d, i in infos.items() if d >= analysis_start}
    above: list[bool | None] = []  # chronological: last 5m close > EMA for each usable session
    for k, d in enumerate(usable):
        c = candles_by_day[d]
        e_end = float(c["ema200_5m"].iloc[-1])
        flags: list[str] = []
        prev: PreviousSession | None = None
        if k > 0:
            pd_ = usable[k - 1]
            pc = candles_by_day[pd_]
            between = pd.date_range(pd_ + timedelta(days=1), d - timedelta(days=1)).date
            missing_weekdays = [x for x in between if x.weekday() < 5 and x not in infos and x not in verified_holidays]
            excluded_between = [x for x in between if x in infos and not infos[x].usable]
            prev_close_day_differs = False
            if daily_close_by_date:
                prior_rows = [x for x in dd_dates if x < d]
                prev_close_day_differs = bool(prior_rows) and prior_rows[-1] != pd_
            close_fallback = bool(daily_close_by_date) and infos[pd_].close_source != "DAILY_VENDOR"
            close_doubt: list[str] = []
            if not daily_close_by_date:  # without the official daily close, post-close prints make the close ambiguous
                close_doubt = [f for f in infos[pd_].flags if f.startswith("POST_CLOSE_RECORDS")]
            cont = pc
            if infos[pd_].cas_regime and cal.closing_auction is not None:
                cont = pc[pc["bar_end"].dt.time <= cal.closing_auction.frozen_start].reset_index(drop=True)
            prev = PreviousSession(
                date=pd_, open=float(pc["open"].iloc[0]), high=float(pc["high"].max()), low=float(pc["low"].min()),
                close_official=infos[pd_].official_close, last_5m_close=float(pc["close"].iloc[-1]), candles=pc,
                ema_at_last_candle=float(pc["ema200_5m"].iloc[-1]),
                gap_to_this_session_unverified=bool(missing_weekdays or excluded_between or prev_close_day_differs or close_doubt or close_fallback),
                continuous_candles=cont, close_source=infos[pd_].close_source, close_1530_print=infos[pd_].stub_close,
            )
            if missing_weekdays:
                flags.append("PREV_SESSION_GAP_UNVERIFIED:" + ",".join(map(str, missing_weekdays)))
            if excluded_between:
                flags.append("PREV_SESSION_SKIPS_EXCLUDED_SESSION:" + ",".join(map(str, excluded_between)))
            if prev_close_day_differs:
                flags.append(f"PREV_CLOSE_DAY_DIFFERS_FROM_PREV_SESSION({pd_})")
            if close_fallback:  # the official close fell back to the 15:30 print (error up to 88 points before the auction regime)
                flags.append(f"PREV_CLOSE_FALLBACK_TO_1530_PRINT({pd_})")
            if close_doubt:
                flags.append(f"PREV_CLOSE_UNRELIABLE({pd_}:{'|'.join(close_doubt)})")
        else:
            flags.append("NO_PREVIOUS_SESSION_IN_DATASET")
        if d >= analysis_start:
            idx = bisect.bisect_left(dd_dates, d) - 1 if daily_df is not None else k - 1
            sma_v = float(sma_d[idx]) if idx >= 0 and not np.isnan(sma_d[idx]) else float("nan")
            ema_v = float(ema_d[idx]) if idx >= 0 and not np.isnan(ema_d[idx]) else float("nan")
            ctxs[d] = SessionContext(
                date=d, info=infos[d], candles=c, previous=prev, open_price=float(c["open"].iloc[0]),
                daily_history_count=max(idx + 1, 0), daily_sma200_prev=sma_v, daily_ema200_prev=ema_v,
                prior_session_ema_above=tuple(reversed(above)),
                data_flags=tuple(flags) + tuple(f"SESSION:{f}" for f in infos[d].flags),
            )
        above.append(None if np.isnan(e_end) else bool(c["close"].iloc[-1] > e_end))
    return ctxs, out_infos
