"""Mathematical definitions shared by the strategy engines.

Every function takes only data that is known at the evaluation candle (indices <= i, or <= i-1
where the docstring says so). No function receives future candles by construction: callers pass
``candles`` and an index, and functions never read beyond ``upto``.

Anything depending on a threshold uses :class:`ProposalConfig` and is PROPOSED_FOR_REVIEW.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import NamedTuple

import pandas as pd

from nifty_trading.data.sessions import PreviousSession, SessionContext
from nifty_trading.strategies.params import M3_WICK_SHARE_BAND, ProposalConfig
from nifty_trading.strategies.rules import implements


class Candle(NamedTuple):
    start: datetime  # bar_start
    end: datetime  # bar_end = first moment the candle may be used
    o: float
    h: float
    l: float
    c: float
    ema: float  # EMA(200) of 5m closes incl. this candle; NaN while warming up


def to_candles(df: pd.DataFrame) -> list[Candle]:
    ema = df["ema200_5m"].to_numpy() if "ema200_5m" in df else [math.nan] * len(df)
    return [Candle(r.bar_start, r.bar_end, float(r.open), float(r.high), float(r.low), float(r.close), float(e))
            for r, e in zip(df.itertuples(index=False), ema, strict=True)]


# ------------------------------------------------------------------ candle geometry
def body(c: Candle) -> float:
    return abs(c.c - c.o)


def rng(c: Candle) -> float:
    return c.h - c.l


def upper_wick(c: Candle) -> float:
    return c.h - max(c.o, c.c)


def lower_wick(c: Candle) -> float:
    return min(c.o, c.c) - c.l


def _ratio(x: float, c: Candle) -> float:
    r = rng(c)
    return 0.0 if r <= 0.0 else x / r  # zero-range candle: every ratio is 0 and no shape qualifies


def body_ratio(c: Candle) -> float:
    return _ratio(body(c), c)


def upper_ratio(c: Candle) -> float:
    return _ratio(upper_wick(c), c)


def lower_ratio(c: Candle) -> float:
    return _ratio(lower_wick(c), c)


@implements("IRF-DEF-001")
def is_green(c: Candle) -> bool:
    return c.c > c.o


@implements("IRF-DEF-001")
def is_red(c: Candle) -> bool:
    return c.c < c.o


@implements("ORB-M1-LONG-003", "ORB-M2-LONG-003", "ORB-CANDLE-001")
def strong_bullish(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED: green, body >= x of range, upper (opposite) wick <= y of range."""
    t = p.strong
    return rng(c) > 0 and is_green(c) and body_ratio(c) >= t["body_ratio_min"] and upper_ratio(c) <= t["opposite_wick_ratio_max"]


@implements("ORB-M1-SHORT-003", "ORB-M2-SHORT-003", "PDS-M1-001", "ORB-CANDLE-001")
def strong_bearish(c: Candle, p: ProposalConfig) -> bool:
    t = p.strong
    return rng(c) > 0 and is_red(c) and body_ratio(c) >= t["body_ratio_min"] and lower_ratio(c) <= t["opposite_wick_ratio_max"]


@implements("ORB-GAP-LONG-004", "ORB-CANDLE-001")
def bullish_pin(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED: long LOWER wick (rejection of lower prices), small body, small upper wick."""
    t = p.pin
    return (rng(c) > 0 and lower_ratio(c) >= t["wick_ratio_min"] and body_ratio(c) <= t["body_ratio_max"]
            and upper_ratio(c) <= t["opposite_wick_ratio_max"])


@implements("PDS-M2-001", "ORB-GAP-SHORT-003", "ORB-CANDLE-001")
def bearish_pin(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED higher-price-rejection pin bar. Colour is checked by the caller where the rule demands red."""
    t = p.pin
    return (rng(c) > 0 and upper_ratio(c) >= t["wick_ratio_min"] and body_ratio(c) <= t["body_ratio_max"]
            and lower_ratio(c) <= t["opposite_wick_ratio_max"])


def upper_rejection(c: Candle, p: ProposalConfig) -> bool:
    return rng(c) > 0 and upper_ratio(c) >= p.reject["wick_ratio_min"]


def lower_rejection(c: Candle, p: ProposalConfig) -> bool:
    return rng(c) > 0 and lower_ratio(c) >= p.reject["wick_ratio_min"]


# ------------------------------------------------------------------ swings and levels
def _pivot_low(cs: list[Candle], j: int, k: int) -> bool:
    return all(cs[j].l <= cs[j - m].l and cs[j].l <= cs[j + m].l for m in range(1, k + 1))


def _pivot_high(cs: list[Candle], j: int, k: int) -> bool:
    return all(cs[j].h >= cs[j - m].h and cs[j].h >= cs[j + m].h for m in range(1, k + 1))


def pivot_lows(cs: list[Candle], lo: int, i: int, k: int) -> list[int]:
    """Indices j in [lo, i-1-k] that are k-fractal lows. Confirmation needs candles up to j+k <= i-1."""
    return [j for j in range(max(lo, k), i - k) if _pivot_low(cs, j, k)]


def pivot_highs(cs: list[Candle], lo: int, i: int, k: int) -> list[int]:
    return [j for j in range(max(lo, k), i - k) if _pivot_high(cs, j, k)]


@implements("IRF-M2A-001", "IRF-M3-004")
def recent_support(cs: list[Candle], lo: int, i: int, p: ProposalConfig) -> tuple[int, float] | None:
    """(index, level) of the recent support known BEFORE candle i, using candles lo..i-1 only."""
    d = p.irf_support_def
    if d in ("SWING_K1", "SWING_K2"):
        k = 1 if d == "SWING_K1" else 2
        js = pivot_lows(cs, lo, i, k)
        return (js[-1], cs[js[-1]].l) if js else None
    if d == "LAST_N3":
        if i - 3 < lo:
            return None
        j = min(range(i - 3, i), key=lambda x: cs[x].l)
        return j, cs[j].l
    raise ValueError(d)


@implements("IRF-M2B-001")
def recent_resistance(cs: list[Candle], lo: int, i: int, p: ProposalConfig) -> tuple[int, float] | None:
    js = pivot_highs(cs, lo, i, 1)
    if not js:
        return None
    j = js[0] if p.irf_resistance_def == "FIRST_PUSH_TOP" else js[-1]
    return j, cs[j].h


def most_recent_colour(cs: list[Candle], upto: int, green: bool) -> int | None:
    """Index of the most recent green (or red) candle at index <= upto."""
    for j in range(upto, -1, -1):
        if (is_green(cs[j]) if green else is_red(cs[j])):
            return j
    return None


# ------------------------------------------------------------------ inside-range / sweep helpers
@implements("IRF-M3-003")
def wick_share_outside(c: Candle, irh: float) -> float | None:
    """(High - IRH) / (High - top_of_body); None when there is no upper wick."""
    uw = upper_wick(c)
    if uw <= 0.0:
        return None
    return (c.h - irh) / uw


def wick_share_in_band(share: float | None, p: ProposalConfig) -> bool:
    if share is None:
        return False
    lo, hi = M3_WICK_SHARE_BAND[p.m3_wick_share_band]
    return lo - 1e-12 <= share <= hi + 1e-12


@implements("IRF-M3-001")
def compression_ok(cs: list[Candle], s: int, irl: float, irh: float, p: ProposalConfig) -> bool:
    """The N candles before sweep candle s lie inside the initial range (and are 'small' in variant C2)."""
    n = p.m3_compression_n
    if s - n < 1:  # candle 0 is the initial range itself and is not part of the compression
        return False
    window = cs[s - n:s]
    if not all(x.l >= irl and x.h <= irh for x in window):
        return False
    if p.m3_compression_def == "C2":
        ir_h = irh - irl
        return all(rng(x) <= p.m3_compression_size_frac * ir_h for x in window)
    return True


# ------------------------------------------------------------------ gap
@dataclass(frozen=True)
class GapInfo:
    evaluable: bool
    reason: str
    points: float
    direction: str  # UP | DOWN | NONE


@implements("ORB-GAP-LONG-001", "ORB-GAP-SHORT-001", "PDR-004", "PDS-003", "RF-003")
def gap_info(ctx: SessionContext, p: ProposalConfig) -> GapInfo:
    prev = ctx.previous
    if prev is None or prev.close_official is None:
        return GapInfo(False, "NO_PREVIOUS_CLOSE", math.nan, "NONE")
    if prev.gap_to_this_session_unverified and not p.allow_unverified_prev_session:
        return GapInfo(False, "PREV_SESSION_UNVERIFIED", math.nan, "NONE")
    pts = ctx.open_price - prev.close_official
    if pts > p.gap_min_points:
        d = "UP"
    elif pts < -p.gap_min_points:
        d = "DOWN"
    else:
        d = "NONE"
    return GapInfo(True, "OK", pts, d)


# ------------------------------------------------------------------ trend / moving average
@dataclass(frozen=True)
class TrendResult:
    ok: bool | None  # None = not evaluable (warm-up); never silently True
    reason: str
    ma_value: float = math.nan


@implements("ORB-TREND-001", "ORB-TREND-002", "RF-001", "RF-008", "DATA-WARM-001")
def trend_check(ctx: SessionContext, i: int, direction: str, mode: str) -> TrendResult:
    """Is the market in an established trend in ``direction`` ('LONG'/'SHORT') at candle i's close?"""
    cs = ctx.candles
    close = float(cs["close"].iloc[i])
    long = direction == "LONG"
    if mode in ("SMA200_DAILY", "EMA200_DAILY"):
        ma = ctx.daily_sma200_prev if mode == "SMA200_DAILY" else ctx.daily_ema200_prev
        if math.isnan(ma):
            return TrendResult(None, f"DAILY_MA_WARMUP(prior_daily_bars={ctx.daily_history_count}<200)")
        ok = close > ma if long else close < ma
        return TrendResult(ok, f"{mode} {'above' if long else 'below'}" if ok else f"{mode} wrong side", ma)
    ema = float(cs["ema200_5m"].iloc[i])
    if math.isnan(ema):
        return TrendResult(None, "EMA200_5M_WARMUP(<200 completed 5m candles)")
    basic = close > ema if long else close < ema
    if not basic:
        return TrendResult(False, "EMA5M_BASIC wrong side", ema)
    if mode == "EMA5M_BASIC":
        return TrendResult(True, "EMA5M_BASIC", ema)
    n = 1 if mode == "EMA5M_PREV_SESSION" else 3
    hist = ctx.prior_session_ema_above[:n]
    if len(hist) < n or any(h is None for h in hist):
        return TrendResult(None, f"PRIOR_SESSIONS_EMA_UNAVAILABLE(need {n})", ema)
    on_side = all(h if long else (not h) for h in hist)
    return TrendResult(on_side, mode if on_side else f"{mode}: previous session(s) were on the other side of the EMA", ema)


def ma_value(ctx: SessionContext, i: int, mode: str) -> float:
    if mode == "SMA200_DAILY":
        return ctx.daily_sma200_prev
    if mode == "EMA200_DAILY":
        return ctx.daily_ema200_prev
    return float(ctx.candles["ema200_5m"].iloc[i])


# ------------------------------------------------------------------ previous-day zones (PDR / PDS)
@dataclass(frozen=True)
class Zone:
    low: float
    high: float
    candle_index: int
    candle_start: datetime


def _pick(idxs: list[int], tie: str) -> int:
    return idxs[0] if tie == "FIRST" else idxs[-1]


@implements("PDR-002", "PDR-003")
def pdr_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
    cs = to_candles(prev.candles)
    top = max(c.h for c in cs)
    j = _pick([k for k, c in enumerate(cs) if c.h == top], p.zone_tie_break)
    c = cs[j]
    low = min(c.o, c.c) if p.zone_lower_boundary == "ZONE_FULL" else max(c.o, c.c)
    return Zone(low=low, high=c.h, candle_index=j, candle_start=c.start)


@implements("PDS-002")
def pds_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
    cs = to_candles(prev.candles)
    bot = min(c.l for c in cs)
    j = _pick([k for k, c in enumerate(cs) if c.l == bot], p.zone_tie_break)
    c = cs[j]
    return Zone(low=c.l, high=max(c.o, c.c), candle_index=j, candle_start=c.start)


@implements("PDR-010")
def previous_day_reversal_ok(prev: PreviousSession, zone: Zone, p: ProposalConfig) -> tuple[bool | None, str]:
    """Research filter for 'clear high and reversal identified'. OFF => (None, 'NOT_EVALUATED')."""
    if p.pdr_reversal_filter == "OFF":
        return None, "REVERSAL_FILTER_OFF"
    cs = to_candles(prev.candles)
    after = cs[zone.candle_index + 1:]
    if not after:
        return False, "NO_CANDLES_AFTER_HIGH"
    depth = zone.high - min(c.l for c in after)
    day_range = prev.high - prev.low
    return depth >= 0.25 * day_range, f"depth={depth:.2f} vs 25% of range={0.25 * day_range:.2f}"


def green_refs(cs: list[Candle], i: int, setup_start: int = 0) -> dict[str, float | int | None]:
    """Inputs for the 35/40 stop rule (IRF-SL-001, PDS-SL-001): most recent green candle at index <= i."""
    gj = most_recent_colour(cs, i, True)
    greens = [cs[j] for j in range(setup_start, i + 1) if is_green(cs[j])]
    return {
        "recent_green_high": cs[gj].h if gj is not None else None,
        "recent_green_close": cs[gj].c if gj is not None else None,
        "setup_green_high": max((g.h for g in greens), default=None),
    }
