"""Phase 5.4 (CANDIDATES, DISABLED BY DEFAULT): alternative constructions of the ORB Method 2 inner level and trendline.

The ORB rulebook (pp.4-7) defines Method 2 only in words and schematic / annotated charts: *the inner resistance (support) is a smaller level inside the previous day's range - a minor swing high or consolidation top - near
a rising (falling) trendline through swing lows (highs)*; no algorithm is given (rules ORB-M2-*-001 are MISSING in the registry). The frozen engine (``orb.ORBStrategy._method2``) uses ONE research construction: the latest
5-candle fractal of the previous session inside its range, and a trendline through the last two previous-session fractal lows (highs). This module exposes the other deterministic readings of the same words as selectable
variants so that their historical signal impact can be measured; NONE of them is source-defined or approved, and the default arguments reproduce the frozen engine exactly (asserted by a regression test over every session).

  inner_level_def  LATEST_FRACTAL_K2 (frozen) | HIGHEST_FRACTAL_K2 (the inner swing nearest the major level) | NEAREST_FRACTAL_FROM_OPEN_K2 (the first inner swing the price must cross from the open)
                   | HIGHEST_BROKEN_FRACTAL_K2 (the most distant inner swing the first candle broke and closed beyond)
  trendline_def    LAST_TWO_FRACTALS_K2 (frozen) | ANY_RISING_PAIR_OF_LAST_THREE_K2 (any two of the last three fractals) | NONE (the unresolved trendline condition is not applied: a diagnostic, not a proposal)

  gap_crossing_def OPEN_BEYOND_AVERAGE (frozen: the OPEN must already be beyond the 200 average) | CANDLE_CROSSES_AVERAGE (the first CANDLE may cross it: previous close on the wrong side, the candle closes beyond the
                   average and its range reaches it). The rulebook's p.8 / p.9 schematics and the real gap-up chart on p.12 draw the candle opening on the old side of the average, crossing it and closing beyond; the text ('the gap
                   must bring price above [the average]'; 'a candle that only crosses the line but closes below it does not qualify') does not settle it.

Everything else - Method 1, the trend gate, the strength gate, the near-EMA rule, the 09:20 timing, stops and targets - is the frozen code (inherited). The candidate overrides carry no ``@implements`` tags on purpose: they are research variants and
must never be counted as implementers of the source rules. With the default arguments the produced records equal the frozen engine's records field for field (a regression test compares every record of every session).
"""

from __future__ import annotations

import math

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import Direction, SetupFSM, SignalRecord, SignalStatus, State
from nifty_trading.strategies.definitions import (
    Candle,
    bearish_pin,
    bullish_pin,
    gap_info,
    lower_rejection,
    ma_value,
    pivot_highs,
    pivot_lows,
    prev_candles,
    prev_high_low,
    strong_bearish,
    strong_bullish,
    to_candles,
    upper_rejection,
)
from nifty_trading.strategies.orb import _G, ORBStrategy

INNER_LEVEL_DEFS = ("LATEST_FRACTAL_K2", "HIGHEST_FRACTAL_K2", "NEAREST_FRACTAL_FROM_OPEN_K2", "HIGHEST_BROKEN_FRACTAL_K2")
TRENDLINE_DEFS = ("LAST_TWO_FRACTALS_K2", "ANY_RISING_PAIR_OF_LAST_THREE_K2", "NONE")
GAP_CROSSING_DEFS = ("OPEN_BEYOND_AVERAGE", "CANDLE_CROSSES_AVERAGE")


def inner_levels(pcs: list[Candle], ph: float, pl: float, long: bool) -> list[float]:
    """The k=2 fractal levels of the previous session lying INSIDE its range (long: swing highs below the day's high; short: swing lows above the day's low), oldest first."""
    n = len(pcs)
    if long:
        return [pcs[j].h for j in pivot_highs(pcs, 0, n, 2) if pcs[j].h < ph]
    return [pcs[j].l for j in pivot_lows(pcs, 0, n, 2) if pcs[j].l > pl]


def select_inner_level(levels: list[float], c: Candle, long: bool, definition: str) -> float | None:
    """The inner level the first candle ``c`` is tested against, or None when the definition yields no level."""
    if not levels:
        return None
    if definition == "LATEST_FRACTAL_K2":
        return levels[-1]
    if definition == "HIGHEST_FRACTAL_K2":
        return max(levels) if long else min(levels)
    if definition == "NEAREST_FRACTAL_FROM_OPEN_K2":
        ahead = [x for x in levels if (x > c.o if long else x < c.o)]
        return (min(ahead) if long else max(ahead)) if ahead else None
    if definition == "HIGHEST_BROKEN_FRACTAL_K2":
        broken = [x for x in levels if ((c.h > x and c.c > x) if long else (c.l < x and c.c < x))]
        return (max(broken) if long else min(broken)) if broken else None
    raise ValueError(definition)


def trendline_supportive(pcs: list[Candle], tl_idx: list[int], c: Candle, long: bool, definition: str) -> tuple[bool, str, float | None]:
    """(supportive, reason, line value at the open). ``tl_idx`` are the previous session's fractal lows (long) / highs (short). The line value is the extrapolation to candle index n (today's first candle)."""
    n = len(pcs)
    if definition == "NONE":
        return True, "TRENDLINE_NOT_APPLIED(diagnostic)", None

    def test(j1: int, j2: int) -> tuple[bool, float]:
        y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
        slope = (y2 - y1) / (j2 - j1)
        line_now = y2 + slope * (n - j2)
        ok_dir = slope > 0 if long else slope < 0
        on_side = c.c > line_now if long else c.c < line_now
        return bool(ok_dir and on_side), line_now
    if definition == "LAST_TWO_FRACTALS_K2":
        if len(tl_idx) < 2:
            return False, "NO_TRENDLINE", None
        ok, line = test(tl_idx[-2], tl_idx[-1])
        return ok, "TRENDLINE_SUPPORTIVE" if ok else "TRENDLINE_NOT_SUPPORTIVE", line
    if definition == "ANY_RISING_PAIR_OF_LAST_THREE_K2":
        last3 = tl_idx[-3:]
        if len(last3) < 2:
            return False, "NO_TRENDLINE", None
        pairs = [(last3[a], last3[b]) for a in range(len(last3)) for b in range(a + 1, len(last3))]
        res = [test(j1, j2) for j1, j2 in pairs]
        for ok, line in res:
            if ok:
                return True, "TRENDLINE_SUPPORTIVE", line
        return False, "TRENDLINE_NOT_SUPPORTIVE", res[-1][1]
    raise ValueError(definition)


class ORBCandidateStrategy(ORBStrategy):
    """ORB with selectable Method 2 inner-level and trendline constructions (see the module docstring). With the default arguments it equals the frozen engine."""

    def __init__(self, name=None, params=None, proposals=None, trade=None, inner_level_def: str = "LATEST_FRACTAL_K2", trendline_def: str = "LAST_TWO_FRACTALS_K2", gap_crossing_def: str = "OPEN_BEYOND_AVERAGE"):
        super().__init__(name, params, proposals, trade)
        if inner_level_def not in INNER_LEVEL_DEFS or trendline_def not in TRENDLINE_DEFS or gap_crossing_def not in GAP_CROSSING_DEFS:
            raise ValueError((inner_level_def, trendline_def, gap_crossing_def))
        self.inner_level_def = inner_level_def
        self.trendline_def = trendline_def
        self.gap_crossing_def = gap_crossing_def
        self._is_default = (inner_level_def, trendline_def, gap_crossing_def) == ("LATEST_FRACTAL_K2", "LAST_TWO_FRACTALS_K2", "OPEN_BEYOND_AVERAGE")

    # a copy of ORBStrategy._method2 in which ONLY the inner-level selection and the trendline test are replaced by the selectable definitions
    def _method2(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
        long = d is Direction.LONG
        pre = "ORB-M2-LONG" if long else "ORB-M2-SHORT"
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        n = len(pcs)
        ph, pl = prev_high_low(prev, self.p)
        lvl = select_inner_level(inner_levels(pcs, ph, pl, long), c, long, self.inner_level_def)
        tl_idx = pivot_lows(pcs, 0, n, 2) if long else pivot_highs(pcs, 0, n, 2)
        if lvl is None:
            return None
        broke = (c.h > lvl and c.c > lvl) if long else (c.l < lvl and c.c < lvl)
        if not broke:
            return None
        levels = {**self._base_levels(ctx, c), "inner_level": lvl, "inner_level_def": "latest fractal(k=2) of previous session" if self.inner_level_def == "LATEST_FRACTAL_K2" else self.inner_level_def}
        props = {"orb_inner_level_def": self.inner_level_def, "orb_trendline_def": self.trendline_def}
        if not self._is_default:
            props["phase54_candidate"] = True
        fsm = SetupFSM(f"ORB M2 {d.value}")
        fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond inner level {lvl}")
        sat = _G + [f"{pre}-002"]
        unresolved = [f"{pre}-001"]
        stop, t = self._trend_gate(ctx, c, d, "Method 2", levels, sat, fsm, props)
        if stop:
            stop.rule_ids_unresolved = unresolved
            return stop
        ok, reason, line_now = trendline_supportive(pcs, tl_idx, c, long, self.trendline_def)
        if line_now is not None:
            levels["trendline_value_at_open"] = line_now
        if not ok:
            fsm.to(State.SETUP_INVALIDATED, c.end, "no trendline constructible" if reason == "NO_TRENDLINE" else "trendline direction/side not supportive")
            return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED, reason, fsm.trace, props)
        if not self._quality(c, d):
            fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
            return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-003"], unresolved, SignalStatus.INVALIDATED, "CANDLE_QUALITY", fsm.trace, props)
        ema = self._near_ma_value(ctx, t)
        if not math.isnan(ema) and abs(c.c - ema) <= self.p.ma_near_band_points:
            beyond = (c.c - ema) if long else (ema - c.c)
            if beyond < self.p.ma_close_margin_points:
                fsm.to(State.SETUP_INVALIDATED, c.end, "near the MA without a convincing close")
                return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-004"], unresolved, SignalStatus.INVALIDATED, "NEAR_MA_NOT_CONVINCING", fsm.trace,
                                 {**props, "ma_near_band_points": self.p.ma_near_band_points})
        fsm.to(State.SIGNAL_CONFIRMED, c.end, "inner level broken, trendline supportive, candle strong")
        return self._rec(ctx, c, "Method 2", d, levels, sat + [f"{pre}-003", f"{pre}-004", "ORB-TREND-001", "ORB-TREND-002", f"{pre}-001"], [], unresolved + ["ORB-MA-001"], SignalStatus.CONFIRMED, None, fsm.trace, props)

    # a copy of ORBStrategy._gap_setup in which ONLY the crossing condition differs (used when gap_crossing_def != OPEN_BEYOND_AVERAGE)
    def _gap_setup(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
        if self.gap_crossing_def == "OPEN_BEYOND_AVERAGE":
            return super()._gap_setup(ctx, c, d)
        long = d is Direction.LONG
        pre = "ORB-GAP-LONG" if long else "ORB-GAP-SHORT"
        g = gap_info(ctx, self.p)
        if not g.evaluable or g.direction != ("UP" if long else "DOWN"):
            return None
        mode = self.p.ma_mode
        ma = ma_value(ctx, 0, mode)
        ma_prev = ctx.previous.ema_at_last_candle if mode == "EMA200_5M" else ma
        levels = {**self._base_levels(ctx, c), "gap_points": g.points, "ma_mode": mode, "ma_value": ma, "ma_prev": ma_prev}
        props = {"ma_mode": mode, "strong_candle": self.p.strong_candle, "pin_bar": self.p.pin_bar, "rejection_wick": self.p.rejection_wick, "gap_min_points": self.p.gap_min_points, "gap_max_points": self.p.gap_max_points,
                 "gap_crossing_def": self.gap_crossing_def, "phase54_candidate": True}
        fsm = SetupFSM(f"ORB GAP {d.value}")
        sat = _G + [f"{pre}-001"]
        if math.isnan(ma) or math.isnan(ma_prev):
            fsm.to(State.SETUP_DETECTED, c.end, "gap in direction")
            fsm.to(State.SETUP_INVALIDATED, c.end, "MA warm-up incomplete")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [], [f"{pre}-002"], SignalStatus.NOT_EVALUATED, f"MA_WARMUP({mode})", fsm.trace, props)
        prev_close = ctx.previous.close_official
        prev_wrong = prev_close < ma_prev if long else prev_close > ma_prev
        open_beyond = ctx.open_price > ma if long else ctx.open_price < ma
        reaches = (c.l <= ma) if long else (c.h >= ma)
        crossed = prev_wrong and (open_beyond or reaches)  # the candle (not only the open) may cross the average
        closed_beyond = c.c > ma if long else c.c < ma
        if not crossed:
            return None
        fsm.to(State.SETUP_DETECTED, c.end, f"gap {g.points:+.2f} crosses MA {ma:.2f}")
        sat.append(f"{pre}-002")
        if not closed_beyond:
            fsm.to(State.SETUP_INVALIDATED, c.end, "first candle did not close beyond the MA")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, ["ORB-GAP-LONG-003" if long else f"{pre}-003"], ["ORB-MA-001"], SignalStatus.INVALIDATED, "CLOSE_NOT_BEYOND_MA", fsm.trace, props)
        if long:
            shape_ok = strong_bullish(c, self.p) or bullish_pin(c, self.p)
            rejected = upper_rejection(c, self.p)
        else:
            shape_ok = strong_bearish(c, self.p) or bearish_pin(c, self.p)
            rejected = lower_rejection(c, self.p)
        qid = f"{pre}-004" if long else f"{pre}-003"
        if not shape_ok or rejected:
            fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality / rejection wick")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003"], [qid], ["ORB-MA-001"], SignalStatus.INVALIDATED, "CANDLE_QUALITY_OR_REJECTION_WICK", fsm.trace, props)
        ext_id = "ORB-GAP-LONG-005" if long else "ORB-GAP-SHORT-004"
        if self.p.gap_max_points is not None and abs(g.points) > self.p.gap_max_points:
            fsm.to(State.SETUP_INVALIDATED, c.end, "gap excessively extended (proposed cap)")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [ext_id], ["ORB-MA-001"], SignalStatus.INVALIDATED, "GAP_EXCEEDS_PROPOSED_CAP", fsm.trace, props)
        fsm.to(State.SIGNAL_CONFIRMED, c.end, "gap crossed MA, close beyond, quality ok")
        unresolved = ["ORB-MA-001"]
        if self.p.gap_max_points is None:
            unresolved.append(ext_id)
        return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003", qid], [], unresolved, SignalStatus.CONFIRMED, None, fsm.trace, props)
