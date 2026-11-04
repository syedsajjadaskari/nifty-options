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
from nifty_trading.strategies.params import DEFAULT_PROPOSALS, M3_WICK_SHARE_BAND, ProposalConfig
from nifty_trading.strategies.rules import implements

EPS = 1e-9  # tolerance for threshold comparisons: prices ~24,000 on a 0.05 grid carry ~4e-12 of float error, so exact-boundary candles must not flip


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
    return (rng(c) > 0 and is_green(c) and body_ratio(c) >= t["body_ratio_min"] - EPS
            and upper_ratio(c) <= t["opposite_wick_ratio_max"] + EPS)


@implements("ORB-M1-SHORT-003", "ORB-M2-SHORT-003", "PDS-M1-001", "ORB-CANDLE-001")
def strong_bearish(c: Candle, p: ProposalConfig) -> bool:
    t = p.strong
    return (rng(c) > 0 and is_red(c) and body_ratio(c) >= t["body_ratio_min"] - EPS
            and lower_ratio(c) <= t["opposite_wick_ratio_max"] + EPS)


def _pin(c: Candle, p: ProposalConfig, lower: bool) -> bool:
    """Pin bar rejecting lower prices (``lower``=True: long lower wick) or higher prices. Two PROPOSED encodings:
    ratio style (wick/body/opposite-wick shares of the range) or the owner's style (wick >= k x body AND the close inside
    the favourable ``close_fraction_max`` of the range)."""
    r = rng(c)
    if r <= 0:
        return False
    t = p.pin
    wick = lower_wick(c) if lower else upper_wick(c)
    if "wick_to_body_min" in t:
        if wick <= EPS or wick < t["wick_to_body_min"] * body(c) - EPS:
            return False
        dist_from_favourable_extreme = (c.h - c.c) if lower else (c.c - c.l)  # bullish: close near the high; bearish: near the low
        return dist_from_favourable_extreme <= t["close_fraction_max"] * r + EPS
    opp = upper_ratio(c) if lower else lower_ratio(c)
    return (_ratio(wick, c) >= t["wick_ratio_min"] - EPS and body_ratio(c) <= t["body_ratio_max"] + EPS
            and opp <= t["opposite_wick_ratio_max"] + EPS)


@implements("ORB-GAP-LONG-004", "ORB-CANDLE-001", "CANDLE-DEF-001")
def bullish_pin(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED: long LOWER wick (rejection of lower prices) with the close in the favourable part of the range."""
    return _pin(c, p, lower=True)


@implements("PDS-M2-001", "ORB-GAP-SHORT-003", "ORB-CANDLE-001", "CANDLE-DEF-001")
def bearish_pin(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED higher-price-rejection pin bar. Colour is checked by the caller where the rule demands red."""
    return _pin(c, p, lower=False)


@implements("CANDLE-DEF-001")
def is_small(c: Candle, p: ProposalConfig) -> bool:
    """PROPOSED small candle: body <= 30% of its range (a zero-range candle is small)."""
    r = rng(c)
    return True if r <= 0 else body(c) <= p.small_candle_body_ratio_max * r + EPS


def upper_rejection(c: Candle, p: ProposalConfig) -> bool:
    return rng(c) > 0 and upper_ratio(c) >= p.reject["wick_ratio_min"] - EPS


def lower_rejection(c: Candle, p: ProposalConfig) -> bool:
    return rng(c) > 0 and lower_ratio(c) >= p.reject["wick_ratio_min"] - EPS


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


@implements("TREND-SWING-001")
def confirmed_swing_highs(cs: list[Candle], upto: int, k: int = 2, lo: int = 0) -> list[int]:
    """Indices j of swing highs KNOWN once candle ``upto`` (inclusive) has closed: ``high[j]`` is strictly greater than the highs of the
    k candles before and the k candles after it. A swing at j is confirmed only when candle j+k has closed, so j <= upto - k."""
    return [j for j in range(max(lo, k), upto - k + 1)
            if all(cs[j].h > cs[j - m].h and cs[j].h > cs[j + m].h for m in range(1, k + 1))]


@implements("TREND-SWING-001")
def confirmed_swing_lows(cs: list[Candle], upto: int, k: int = 2, lo: int = 0) -> list[int]:
    return [j for j in range(max(lo, k), upto - k + 1)
            if all(cs[j].l < cs[j - m].l and cs[j].l < cs[j + m].l for m in range(1, k + 1))]


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
    if p.m3_compression_def == "C3":
        return all(is_small(x, p) for x in window)
    return True


# ------------------------------------------------------------------ gap
@dataclass(frozen=True)
class GapInfo:
    evaluable: bool
    reason: str
    points: float
    direction: str  # UP | DOWN | NONE


@implements("ORB-GAP-LONG-001", "ORB-GAP-SHORT-001", "PDR-004", "PDS-003", "RF-003", "DATA-OFFICIAL-CLOSE-001", "DATA-OPEN-001")
def gap_info(ctx: SessionContext, p: ProposalConfig) -> GapInfo:
    prev = ctx.previous
    prev_close = prev.close_official if prev is not None else None
    if prev is not None and p.prev_close_source == "LAST_PRINT_1530" and prev.close_1530_print is not None:
        prev_close = prev.close_1530_print
    if prev is None or prev_close is None:
        return GapInfo(False, "NO_PREVIOUS_CLOSE", math.nan, "NONE")
    if prev.gap_to_this_session_unverified and not p.allow_unverified_prev_session:
        return GapInfo(False, "PREV_SESSION_UNVERIFIED", math.nan, "NONE")
    pts = ctx.open_price - prev_close
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
def trend_check(ctx: SessionContext, i: int, direction: str, mode: str, p: ProposalConfig | None = None) -> TrendResult:
    """Is the market in an established trend in ``direction`` ('LONG'/'SHORT') at candle i's close?"""
    if mode == "STRUCTURE_EMA_SWING2":
        return structure_trend(ctx, direction, p or DEFAULT_PROPOSALS)
    if mode == "EMA_PREV_SESSION_CLOSE":
        return ema_prev_session_trend(ctx, direction, p or DEFAULT_PROPOSALS)
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


@implements("TREND-EMA-001", "RF-001", "ORB-TREND-001", "DATA-WARM-001")
def ema_prev_session_trend(ctx: SessionContext, direction: str, p: ProposalConfig) -> TrendResult:
    """Research VARIANT A (owner-approved): the five-minute EMA(200) price location only, from PREVIOUS-session information, so the
    opening gap can never establish the trend. long: last close > its EMA; short: last close < its EMA. ``ok=None`` while the EMA warms up."""
    prev = ctx.previous
    if prev is None:
        return TrendResult(None, "NO_PREVIOUS_SESSION")
    cs = to_candles(prev_candles(prev, p))
    if not cs:
        return TrendResult(None, "NO_PREVIOUS_CANDLES")
    last = cs[-1]
    if math.isnan(last.ema):
        return TrendResult(None, "EMA200_5M_WARMUP(previous session)")
    ok = last.c > last.ema if direction == "LONG" else last.c < last.ema
    return TrendResult(ok, "EMA_PREV_SESSION_CLOSE " + ("on the trend side" if ok else "wrong side"), last.ema)


@implements("TREND-STRUCT-001", "TREND-SWING-001", "RF-001", "ORB-TREND-001", "DATA-WARM-001")
def structure_trend(ctx: SessionContext, direction: str, p: ProposalConfig) -> TrendResult:
    """PROPOSED established trend, from PREVIOUS-session information only (the opening gap can never establish it):

    up:   last close > its EMA(200)  AND  SH[-1] > SH[-2]  AND  SL[-1] > SL[-2]
    down: last close < its EMA(200)  AND  SH[-1] < SH[-2]  AND  SL[-1] < SL[-2]

    SH/SL are the confirmed swing highs/lows (``p.swing_k`` candles each side, strict) of the previous session's candles, so every
    swing was already confirmed by the time that session ended. Returns ``ok=None`` while the EMA is warming up, ``ok=False`` when
    fewer than two swing highs or lows exist (a trend cannot be called established from less).
    """
    prev = ctx.previous
    if prev is None:
        return TrendResult(None, "NO_PREVIOUS_SESSION")
    cs = to_candles(prev_candles(prev, p))
    if not cs:
        return TrendResult(None, "NO_PREVIOUS_CANDLES")
    last = cs[-1]
    if math.isnan(last.ema):
        return TrendResult(None, "EMA200_5M_WARMUP(previous session)")
    long = direction == "LONG"
    side = last.c > last.ema if long else last.c < last.ema
    if not side:
        return TrendResult(False, "STRUCTURE: previous close on the wrong side of EMA(200)", last.ema)
    sh = confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)
    sl = confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)
    if len(sh) < 2 or len(sl) < 2:
        return TrendResult(False, f"STRUCTURE: fewer than two confirmed swing highs/lows ({len(sh)}/{len(sl)})", last.ema)
    h1, h2, l1, l2 = cs[sh[-2]].h, cs[sh[-1]].h, cs[sl[-2]].l, cs[sl[-1]].l
    ok = (h2 > h1 and l2 > l1) if long else (h2 < h1 and l2 < l1)
    why = f"STRUCTURE swing highs {h1}->{h2}, swing lows {l1}->{l2}"
    return TrendResult(ok, why if ok else why + " (not " + ("higher-high/higher-low)" if long else "lower-high/lower-low)"), last.ema)


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
    method: str = "A_HIGHEST_HIGH"
    members: tuple[int, ...] = ()
    fallback: bool = False  # legacy (PDS only): the configured method found no candidate and method A was used
    diagnostic_only: bool = False  # PDR method A (absolute highest high): a diagnostic reference, never tradable


def _pick(idxs: list[int], tie: str) -> int:
    return idxs[0] if tie == "FIRST" else idxs[-1]


@implements("DATA-CAS-001")
def prev_candles(prev: PreviousSession, p: ProposalConfig) -> pd.DataFrame:
    """Previous-session candles used for levels/zones: all of them, or (proposal) only those before the closing auction."""
    if p.prev_day_level_window == "CONTINUOUS_ONLY" and prev.continuous_candles is not None:
        return prev.continuous_candles
    return prev.candles


def prev_high_low(prev: PreviousSession, p: ProposalConfig) -> tuple[float, float]:
    c = prev_candles(prev, p)
    return float(c["high"].max()), float(c["low"].min())


def _cluster(cs: list[Candle], idxs: list[int], key, tol: float, min_touches: int, top: bool) -> list[int] | None:
    """Cluster swing indices whose ``key`` lies within ``tol`` of the cluster's extreme; return the members of the most extreme
    cluster with at least ``min_touches`` members (``top``: highest; else lowest), or None. Greedy from the extreme downward."""
    pool = sorted(idxs, key=lambda j: key(cs[j]), reverse=top)
    used: set[int] = set()
    for j0 in pool:
        if j0 in used:
            continue
        ext = key(cs[j0])
        members = [j for j in pool if j not in used and abs(key(cs[j]) - ext) <= tol + 1e-9]
        used.update(members)
        if len(members) >= min_touches:
            return sorted(members)
    return None


@implements("PDR-002", "PDR-003", "PDR-ZONE-002")
def pdr_zone(prev: PreviousSession, p: ProposalConfig) -> Zone | None:
    """Previous-day resistance zone (PDR-D09, Phase 2.3). The owner approved two independent research candidates - B_SWING_HIGH_REVERSAL
    and C_REPEATED_TOUCHES; a candidate that finds nothing returns ``None`` (NO setup - it never silently falls back to the absolute
    highest high). A_HIGHEST_HIGH is a DIAGNOSTIC reference only (``Zone.diagnostic_only``). Only previous-session candles are read."""
    cs = to_candles(prev_candles(prev, p))
    method = p.pdr_zone_method
    members: list[int] = []
    if method == "B_SWING_HIGH_REVERSAL":
        for j in reversed(confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)):
            if any(is_red(cs[m]) for m in range(j, min(len(cs), j + p.swing_k + 1))):
                members = [j]
                break
    elif method == "C_REPEATED_TOUCHES":
        sh = confirmed_swing_highs(cs, len(cs) - 1, p.swing_k)
        members = _cluster(cs, sh, lambda c: c.h, p.zone_cluster_tolerance_points, p.zone_cluster_min_touches, True) or []
    if method == "A_HIGHEST_HIGH":
        top = max(c.h for c in cs)
        members = [_pick([k for k, c in enumerate(cs) if c.h == top], p.zone_tie_break)]
    if not members:
        return None
    high = max(cs[m].h for m in members)
    lows = [min(cs[m].o, cs[m].c) if p.zone_lower_boundary == "ZONE_FULL" else max(cs[m].o, cs[m].c) for m in members]
    j = members[-1] if method != "A_HIGHEST_HIGH" else members[0]
    return Zone(low=min(lows), high=high, candle_index=j, candle_start=cs[j].start, method=method,
                members=tuple(members), diagnostic_only=method == "A_HIGHEST_HIGH")


@implements("PDR-ZONE-002")
def pdr_diagnostic_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
    """The absolute highest-high zone, computed for COMPARISON on every PDR record (never used to trade)."""
    z = pdr_zone(prev, replace_method(p, "A_HIGHEST_HIGH"))
    assert z is not None
    return z


def replace_method(p: ProposalConfig, method: str) -> ProposalConfig:
    from dataclasses import replace
    return replace(p, pdr_zone_method=method)


@implements("PDS-002", "PDS-ZONE-002")
def pds_zone(prev: PreviousSession, p: ProposalConfig) -> Zone:
    """Previous-day support zone (mirror of the PDR methods; NOT assumed to be an exact mirror of the PDR zone)."""
    cs = to_candles(prev_candles(prev, p))
    method = p.pds_zone_method
    members: list[int] = []
    fallback = False
    if method == "B_SWING_LOW_REVERSAL":
        for j in reversed(confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)):
            if any(is_green(cs[m]) for m in range(j, min(len(cs), j + p.swing_k + 1))):
                members = [j]
                break
    elif method == "C_REPEATED_TOUCHES":
        sl = confirmed_swing_lows(cs, len(cs) - 1, p.swing_k)
        members = _cluster(cs, sl, lambda c: c.l, p.zone_cluster_tolerance_points, p.zone_cluster_min_touches, False) or []
    if not members:
        fallback = method != "A_LOWEST_LOW"
        method_used = "A_LOWEST_LOW"
        bot = min(c.l for c in cs)
        members = [_pick([k for k, c in enumerate(cs) if c.l == bot], p.zone_tie_break)]
    else:
        method_used = method
    low = min(cs[m].l for m in members)
    tops = [max(cs[m].o, cs[m].c) if p.pds_zone_upper_boundary == "ZONE_FULL" else min(cs[m].o, cs[m].c) for m in members]
    j = members[-1] if method_used != "A_LOWEST_LOW" else members[0]
    return Zone(low=low, high=max(tops), candle_index=j, candle_start=cs[j].start, method=method_used,
                members=tuple(members), fallback=fallback)


@implements("PDR-010")
def previous_day_reversal_ok(prev: PreviousSession, zone: Zone, p: ProposalConfig) -> tuple[bool | None, str]:
    """Research filter for 'clear high and reversal identified'. OFF => (None, 'NOT_EVALUATED')."""
    if p.pdr_reversal_filter == "OFF":
        return None, "REVERSAL_FILTER_OFF"
    cs = to_candles(prev_candles(prev, p))
    after = cs[zone.candle_index + 1:]
    if not after:
        return False, "NO_CANDLES_AFTER_HIGH"
    depth = zone.high - min(c.l for c in after)
    ph, pl = prev_high_low(prev, p)
    day_range = ph - pl
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
