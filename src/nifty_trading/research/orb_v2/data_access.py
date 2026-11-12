"""Window loading + session assembly for ORB V2.

Reuses verified infrastructure only: processed-parquet loaders, the NSE calendar, ``classify_session`` (usable / official close / closing-auction regime) and the
bar-executability classifier. All ORB logic (5-minute candles, EMA, previous-day structure, gap) is computed here from the raw one-minute rows.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, timedelta

import pandas as pd

from nifty_trading.data import sessions as S
from nifty_trading.data.market_calendar import load_market_calendar
from nifty_trading.research.orb_v2 import ema as E
from nifty_trading.research.orb_v2 import opening_candle as OC
from nifty_trading.research.orb_v2.models import SessionData

WINDOWS = {
    "A": {"label": "Primary 2025-09-01..2026-08-31 (5paisa minutes, Phase 1/2 store)", "start": date(2025, 9, 1), "end": date(2026, 8, 31)},
    "B": {"label": "Robustness 2022-09-01..2025-08-31 (5paisa minutes, Phase 4 store)", "start": date(2022, 9, 1), "end": date(2025, 8, 31)},
}
WARMUP_DAYS = 45


@dataclass
class WindowInputs:
    window: str
    label: str
    start: date
    end: date
    minutes: pd.DataFrame
    daily_close: dict
    cal: object
    infos: dict = field(default_factory=dict)
    chain: dict = field(default_factory=dict)       # date -> 5-minute candles incl. 'ema'
    day_frames: dict = field(default_factory=dict)  # date -> that day's 1-minute rows
    order: list = field(default_factory=list)       # usable dates in chronological order
    provenance: dict = field(default_factory=dict)
    warmup_rows: int = 0


def load_window(window: str, vendor: str = "5P") -> WindowInputs:
    """vendor '5P' = the verified 5paisa one-minute data (PRIMARY, the only source of headline results); 'TV' = the secondary vendor's minutes (VENDOR_SENSITIVITY: the feed the
    rulebook's screenshots match). Minute bars are never mixed inside one run; the OFFICIAL DAILY CLOSES (gap reference) are the 5paisa vendor series in both runs."""
    w = WINDOWS[window]
    if vendor == "TV":
        from nifty_trading.research import phase4_data as D4
        minutes_all = D4.load_processed_minutes(D4.SRC_TV_MIN)
        daily = S.load_daily_official() if window == "A" else D4.load_processed_daily(D4.SRC_5P_DAILY)
        cal = load_market_calendar() if window == "A" else load_market_calendar(D4.CAL_DIR / "phase4_calendar_derived.json")
        t = minutes_all["timestamp"].dt.date
        warm = minutes_all[(t >= w["start"] - timedelta(days=WARMUP_DAYS)) & (t < w["start"])]
        minutes = minutes_all[(t >= w["start"]) & (t <= w["end"])]
        src = f"data/phase4/processed/{D4.SRC_TV_MIN} (secondary vendor minutes) + official daily closes"
    elif window == "A":
        minutes = S.load_one_minute()
        warm = S.load_warmup_one_minute()
        daily = S.load_daily_official()
        cal = load_market_calendar()
        src = "data/processed/nifty50 + nifty50_warmup + nifty50_daily"
    else:
        from nifty_trading.research import phase4_data as D4
        minutes_all = D4.load_processed_minutes(D4.SRC_5P_MIN)
        daily = D4.load_processed_daily(D4.SRC_5P_DAILY)
        cal = load_market_calendar(D4.CAL_DIR / "phase4_calendar_derived.json")
        t = minutes_all["timestamp"].dt.date
        warm = minutes_all[(t >= w["start"] - timedelta(days=WARMUP_DAYS)) & (t < w["start"])]
        minutes = minutes_all[(t >= w["start"]) & (t <= w["end"])]
        src = f"data/phase4/processed/{D4.SRC_5P_MIN} + {D4.SRC_5P_DAILY}"
    keep = ["timestamp", "open", "high", "low", "close"]
    frames = [f[keep] for f in (warm, minutes) if f is not None and len(f)]
    allm = pd.concat(frames, ignore_index=True).sort_values("timestamp").reset_index(drop=True)
    t = allm["timestamp"].dt.date
    inwin = t[(t >= w["start"]) & (t <= w["end"])]
    daily_close = {} if daily is None else dict(zip(daily["date"], daily["close"].astype(float), strict=True))
    inp = WindowInputs(window + ("" if vendor == "5P" else "_TV"), w["label"] + ("" if vendor == "5P" else " [SECONDARY VENDOR - sensitivity only]"), w["start"], w["end"], allm, daily_close, cal,
                       warmup_rows=int((t < w["start"]).sum()))
    inp.provenance = {"source": src, "rows_total": int(len(allm)), "rows_in_window": int(len(inwin)), "warmup_rows": inp.warmup_rows, "sessions_with_rows_in_window": int(inwin.nunique()),
                      "first_row": str(allm["timestamp"].iloc[0]), "last_row": str(allm["timestamp"].iloc[-1])}
    _build_chain(inp)
    return inp


def _build_chain(inp: WindowInputs) -> None:
    m = inp.minutes
    m = m.assign(ts=m["timestamp"].dt.tz_localize(None), _d=m["timestamp"].dt.date)
    inp.minutes = m
    closes, owners = [], []
    for d, g in m.groupby("_d", sort=True):
        inp.day_frames[d] = g
        info, _ = S.classify_session(g[["timestamp", "open", "high", "low", "close"]], inp.cal, inp.daily_close.get(d))
        inp.infos[d] = info
        if not info.usable:
            continue
        c = OC.aggregate_5m(g)
        if c.empty:
            continue
        inp.chain[d] = c
        inp.order.append(d)
        closes.extend(c["close"].tolist())
        owners.extend([d] * len(c))
    ema = E.ema_series(pd.Series(closes).to_numpy(float))
    pos = 0
    for d in inp.order:
        n = len(inp.chain[d])
        inp.chain[d]["ema"] = ema[pos:pos + n]
        pos += n


def _continuous(c: pd.DataFrame, info, cal) -> pd.DataFrame:
    """Candles of continuous trading only: on closing-auction days (frozen index from 15:15) candles that end after 15:15 are dropped."""
    if info.cas_regime and cal.closing_auction is not None:
        return c[c["end"].dt.time <= cal.closing_auction.frozen_start].reset_index(drop=True)
    return c.reset_index(drop=True)


def session_data(inp: WindowInputs, d: date) -> tuple[SessionData | None, str]:
    """(SessionData, "") or (None, reason) for a date inside the window."""
    info = inp.infos.get(d)
    if info is None:
        return None, "NO_DATA"
    if not info.usable:
        return None, f"SESSION_NOT_USABLE:{info.status.value}"
    if d not in inp.chain:
        return None, "NO_COMPLETE_CANDLES"
    k = inp.order.index(d) if not hasattr(inp, "_pos") else inp._pos[d]
    if k == 0:
        return None, "NO_PREVIOUS_SESSION"
    pd_ = inp.order[k - 1]
    day = inp.day_frames[d]
    oc = OC.opening_candle(day)
    if oc is None:
        return None, "OPENING_CANDLE_INCOMPLETE"
    c_today, c_prev_all, pinfo = inp.chain[d], inp.chain[pd_], inp.infos[pd_]
    prev = _continuous(c_prev_all, pinfo, inp.cal)
    flags = []
    between = [x for x in pd.date_range(pd_ + timedelta(days=1), d - timedelta(days=1)).date if x.weekday() < 5 and x not in inp.cal.holidays]
    if between:
        flags.append("PREV_SESSION_GAP_UNVERIFIED:" + ",".join(map(str, between)))
    if pinfo.close_source != "DAILY_VENDOR":
        flags.append(f"PREV_CLOSE_FALLBACK:{pinfo.close_source}")
    if info.flags:
        flags.extend(f"SESSION_FLAG:{f}" for f in info.flags)
    prev_close = pinfo.official_close if pinfo.official_close is not None else float(prev["close"].iloc[-1])
    sd = SessionData(
        date=d, day_minutes=day, opening=oc, open_1m=float(day["open"].iloc[0]), ema_now=float(c_today["ema"].iloc[0]), ema_prev=float(prev["ema"].iloc[-1]), prev_date=pd_,
        prev_high=float(prev["high"].max()), prev_low=float(prev["low"].min()), prev_close=float(prev_close), prev_close_source=pinfo.close_source,
        prev_last_5m_close=float(prev["close"].iloc[-1]), prev_candles=prev, prev_ema_last=float(prev["ema"].iloc[-1]),
        prev_engulf_candle={c: (prev[c].iloc[-1] if c in ("start", "end") else float(prev[c].iloc[-1])) for c in ("start", "end", "open", "high", "low", "close")}, flags=tuple(flags))
    return sd, ""


def index_positions(inp: WindowInputs) -> None:
    inp._pos = {d: i for i, d in enumerate(inp.order)}  # type: ignore[attr-defined]


def evaluable_dates(inp: WindowInputs) -> list[date]:
    """Calendar sessions of the window that have 1-minute rows (the session universe; each is evaluated or reported NOT_EVALUATED)."""
    return [d for d in sorted(inp.infos) if inp.start <= d <= inp.end]
