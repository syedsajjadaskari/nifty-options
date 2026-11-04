"""ORB - Opening Range Breakout (both directions). Source: ``ORB_Strategy_Rulebook-2.pdf``.

Decision time is 09:20, after the first 5-minute candle closes (ORB-GLOBAL-001). Setups:
  Method 1      previous-day level break (long: resistance, short: support)
  Method 2      inner level + trendline  -> RESEARCH_VARIANT only: the source gives no objective
                construction for the inner level or the trendline (rules ORB-M2-*-001 are MISSING)
  Gap/200 MA    gap through the 200-period MA with the first candle closing beyond it

Records are emitted only when the *trigger event* occurred (level broken / gap crossed the MA);
days on which nothing triggered produce no record.
"""

from __future__ import annotations

import math

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import (
    Direction,
    SetupFSM,
    SignalEngine,
    SignalRecord,
    SignalStatus,
    State,
)
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
    trend_check,
    upper_rejection,
)
from nifty_trading.strategies.rules import implements

_G = ["ORB-GLOBAL-001", "ORB-GLOBAL-002"]


class ORBStrategy(SignalEngine):
    STRATEGY = "ORB"
    METHODS = ("Method 1", "Method 2", "Gap/200DMA")
    TREND_METHODS = ("Method 1", "Method 2")
    REQUIRES_PREVIOUS_SESSION = True

    def _default_direction(self) -> str:
        return "BOTH"

    @implements("ORB-GLOBAL-001", "ORB-GLOBAL-002")
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        out: list[SignalRecord] = []
        for d in (Direction.LONG, Direction.SHORT):
            for fn in (self._method1, self._method2, self._gap_setup):
                r = fn(ctx, cs[0], d)
                if r is not None:
                    out.append(r)
        return out

    # ------------------------------------------------------------------ helpers
    def _base_levels(self, ctx: SessionContext, c: Candle) -> dict:
        prev = ctx.previous
        ph, pl = prev_high_low(prev, self.p)
        return {"entry_reference_price": c.c, "first_candle_high": c.h, "first_candle_low": c.l,
                "prev_day_high": ph, "prev_day_low": pl, "prev_close": prev.close_official}

    def _quality(self, c: Candle, d: Direction) -> bool:
        """Strong body, or (ORB pp.9-10 'across all three setups') the conditional pin bar. The pin bar's
        'position and close must support the breakout' is already guaranteed: the level was broken and closed beyond."""
        if d is Direction.LONG:
            return strong_bullish(c, self.p) or (self.p.orb_pin_bar_in_methods_1_2 and bullish_pin(c, self.p))
        return strong_bearish(c, self.p) or (self.p.orb_pin_bar_in_methods_1_2 and bearish_pin(c, self.p))

    def _near_ma_value(self, ctx: SessionContext, t) -> float:
        """The moving average for the Method-2 'near the MA' test. The structure trend reports the PREVIOUS session's EMA in
        ``t.ma_value``; 'near the MA' concerns the EMA at the opening candle, so that mode uses today's first-candle EMA."""
        if self.p.trend_mode in ("STRUCTURE_EMA_SWING2", "EMA_PREV_SESSION_CLOSE"):
            return float(ctx.candles["ema200_5m"].iloc[0])
        return t.ma_value

    def _trend_gate(self, ctx, c, d, method, levels, sat, fsm, props):
        """Returns (record_or_None_to_stop, trend_result)."""
        t = trend_check(ctx, 0, d.value, self.p.trend_mode, self.p)
        props["trend_mode"] = self.p.trend_mode
        if t.ok is None:
            fsm.to(State.SETUP_INVALIDATED, c.end, f"trend not evaluable: {t.reason}")
            return self._rec(ctx, c, method, d, levels, sat, [], ["ORB-TREND-001"], SignalStatus.NOT_EVALUATED, t.reason,
                             fsm.trace, props), t
        if not t.ok:
            fsm.to(State.SETUP_INVALIDATED, c.end, f"trend filter failed: {t.reason}")
            return self._rec(ctx, c, method, d, levels, sat, ["ORB-TREND-001", "ORB-TREND-002"], [], SignalStatus.INVALIDATED,
                             f"TREND:{t.reason}", fsm.trace, props), t
        return None, t

    # ------------------------------------------------------------------ Method 1
    @implements("ORB-M1-LONG-001", "ORB-M1-LONG-002", "ORB-M1-LONG-003", "ORB-M1-SHORT-001", "ORB-M1-SHORT-002",
                "ORB-M1-SHORT-003", "ORB-TREND-001", "ORB-TREND-002", "ORB-GLOBAL-004")
    def _method1(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
        long = d is Direction.LONG
        pre = "ORB-M1-LONG" if long else "ORB-M1-SHORT"
        ph, pl = prev_high_low(ctx.previous, self.p)
        level = ph if long else pl
        broke = (c.h > level and c.c > level) if long else (c.l < level and c.c < level)
        if not broke:
            return None
        levels = {**self._base_levels(ctx, c), "level_broken": level, "level_kind": "prev_day_high" if long else "prev_day_low"}
        props = {"orb_prev_day_level_def": "PREV_DAY_HL", "strong_candle": self.p.strong_candle,
                 "rejection_wick": self.p.rejection_wick}
        fsm = SetupFSM(f"ORB M1 {d.value}")
        fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond {level}")
        sat = _G + [f"{pre}-001", f"{pre}-002", "ORB-GLOBAL-004"]
        stop, _ = self._trend_gate(ctx, c, d, "Method 1", levels, sat, fsm, props)
        if stop:
            return stop
        sat += ["ORB-TREND-001", "ORB-TREND-002"]
        if not self._quality(c, d):
            fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
            return self._rec(ctx, c, "Method 1", d, levels, sat, [f"{pre}-003"], [], SignalStatus.INVALIDATED,
                             "CANDLE_QUALITY(not a strong body / wick too large)", fsm.trace, props)
        fsm.to(State.SIGNAL_CONFIRMED, c.end, "level broken, trend ok, candle strong")
        return self._rec(ctx, c, "Method 1", d, levels, sat + [f"{pre}-003"], [], ["ORB-MA-001"], SignalStatus.CONFIRMED, None,
                         fsm.trace, props)

    # ------------------------------------------------------------------ Method 2 (research variant)
    @implements("ORB-M2-LONG-001", "ORB-M2-LONG-002", "ORB-M2-LONG-003", "ORB-M2-LONG-004", "ORB-M2-LONG-005",
                "ORB-M2-SHORT-001", "ORB-M2-SHORT-002", "ORB-M2-SHORT-003", "ORB-M2-SHORT-004")
    def _method2(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
        """RESEARCH VARIANT. Inner level = latest 5-candle fractal extreme of the previous session inside its
        range; trendline = line through the last two previous-session fractal lows (long) / highs (short).
        Neither construction is in the source documents."""
        long = d is Direction.LONG
        pre = "ORB-M2-LONG" if long else "ORB-M2-SHORT"
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        n = len(pcs)
        ph, pl = prev_high_low(prev, self.p)
        if long:
            piv = [j for j in pivot_highs(pcs, 0, n, 2) if pcs[j].h < ph]
            lvl = pcs[piv[-1]].h if piv else None
            tl_idx = pivot_lows(pcs, 0, n, 2)
        else:
            piv = [j for j in pivot_lows(pcs, 0, n, 2) if pcs[j].l > pl]
            lvl = pcs[piv[-1]].l if piv else None
            tl_idx = pivot_highs(pcs, 0, n, 2)
        if lvl is None:
            return None
        broke = (c.h > lvl and c.c > lvl) if long else (c.l < lvl and c.c < lvl)
        if not broke:
            return None
        levels = {**self._base_levels(ctx, c), "inner_level": lvl, "inner_level_def": "latest fractal(k=2) of previous session"}
        props = {"orb_inner_level_def": "LATEST_FRACTAL_K2", "orb_trendline_def": "LAST_TWO_FRACTALS_K2"}
        fsm = SetupFSM(f"ORB M2 {d.value}")
        fsm.to(State.SETUP_DETECTED, c.end, f"09:15 candle broke and closed beyond inner level {lvl}")
        sat = _G + [f"{pre}-002"]
        unresolved = [f"{pre}-001"]
        stop, t = self._trend_gate(ctx, c, d, "Method 2", levels, sat, fsm, props)
        if stop:
            stop.rule_ids_unresolved = unresolved
            return stop
        # trendline: rising (long) / falling (short) line through the last two fractals; price must be on the trend side
        if len(tl_idx) < 2:
            fsm.to(State.SETUP_INVALIDATED, c.end, "no trendline constructible")
            return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED,
                             "NO_TRENDLINE", fsm.trace, props)
        j1, j2 = tl_idx[-2], tl_idx[-1]
        y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
        slope = (y2 - y1) / (j2 - j1)
        line_now = y2 + slope * (n - j2)  # candle 0 of today sits at index n of the concatenated sequence
        levels["trendline_value_at_open"] = line_now
        ok_dir = slope > 0 if long else slope < 0
        on_side = c.c > line_now if long else c.c < line_now
        if not (ok_dir and on_side):
            fsm.to(State.SETUP_INVALIDATED, c.end, "trendline direction/side not supportive")
            return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-001"], unresolved, SignalStatus.INVALIDATED,
                             "TRENDLINE_NOT_SUPPORTIVE", fsm.trace, props)
        if not self._quality(c, d):
            fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality not strong")
            return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-003"], unresolved, SignalStatus.INVALIDATED,
                             "CANDLE_QUALITY", fsm.trace, props)
        ema = self._near_ma_value(ctx, t)
        if not math.isnan(ema) and abs(c.c - ema) <= self.p.ma_near_band_points:
            beyond = (c.c - ema) if long else (ema - c.c)
            if beyond < self.p.ma_close_margin_points:
                fsm.to(State.SETUP_INVALIDATED, c.end, "near the MA without a convincing close")
                return self._rec(ctx, c, "Method 2", d, levels, sat, [f"{pre}-004"], unresolved, SignalStatus.INVALIDATED,
                                 "NEAR_MA_NOT_CONVINCING", fsm.trace, {**props, "ma_near_band_points": self.p.ma_near_band_points})
        fsm.to(State.SIGNAL_CONFIRMED, c.end, "inner level broken, trendline supportive, candle strong")
        return self._rec(ctx, c, "Method 2", d, levels,
                         sat + [f"{pre}-003", f"{pre}-004", "ORB-TREND-001", "ORB-TREND-002", f"{pre}-001"],
                         [], unresolved + ["ORB-MA-001"], SignalStatus.CONFIRMED, None, fsm.trace, props)

    # ------------------------------------------------------------------ Gap + 200 MA
    @implements("ORB-GAP-LONG-001", "ORB-GAP-LONG-002", "ORB-GAP-LONG-003", "ORB-GAP-LONG-004", "ORB-GAP-LONG-005",
                "ORB-GAP-SHORT-001", "ORB-GAP-SHORT-002", "ORB-GAP-SHORT-003", "ORB-GAP-SHORT-004", "ORB-MA-001")
    def _gap_setup(self, ctx: SessionContext, c: Candle, d: Direction) -> SignalRecord | None:
        long = d is Direction.LONG
        pre = "ORB-GAP-LONG" if long else "ORB-GAP-SHORT"
        g = gap_info(ctx, self.p)
        if not g.evaluable or g.direction != ("UP" if long else "DOWN"):
            return None
        mode = self.p.ma_mode
        ma = ma_value(ctx, 0, mode)
        ma_prev = ctx.previous.ema_at_last_candle if mode == "EMA200_5M" else ma
        levels = {**self._base_levels(ctx, c), "gap_points": g.points, "ma_mode": mode, "ma_value": ma, "ma_prev": ma_prev}
        props = {"ma_mode": mode, "strong_candle": self.p.strong_candle, "pin_bar": self.p.pin_bar,
                 "rejection_wick": self.p.rejection_wick, "gap_min_points": self.p.gap_min_points,
                 "gap_max_points": self.p.gap_max_points}
        fsm = SetupFSM(f"ORB GAP {d.value}")
        sat = _G + [f"{pre}-001"]
        if math.isnan(ma) or math.isnan(ma_prev):
            fsm.to(State.SETUP_DETECTED, c.end, "gap in direction")
            fsm.to(State.SETUP_INVALIDATED, c.end, "MA warm-up incomplete")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [], [f"{pre}-002"], SignalStatus.NOT_EVALUATED,
                             f"MA_WARMUP({mode})", fsm.trace, props)
        prev_close = ctx.previous.close_official
        crossed = (prev_close < ma_prev and ctx.open_price > ma) if long else (prev_close > ma_prev and ctx.open_price < ma)
        closed_beyond = c.c > ma if long else c.c < ma
        if not crossed:
            return None  # the gap did not push price through the MA: the special setup does not apply
        fsm.to(State.SETUP_DETECTED, c.end, f"gap {g.points:+.2f} crosses MA {ma:.2f}")
        sat.append(f"{pre}-002")
        if not closed_beyond:
            fsm.to(State.SETUP_INVALIDATED, c.end, "first candle did not close beyond the MA")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, ["ORB-GAP-LONG-003" if long else f"{pre}-003"], ["ORB-MA-001"],
                             SignalStatus.INVALIDATED, "CLOSE_NOT_BEYOND_MA", fsm.trace, props)
        if long:
            shape_ok = strong_bullish(c, self.p) or bullish_pin(c, self.p)
            rejected = upper_rejection(c, self.p)  # with the default MODERATE rejection (33%) an owner-style pin's upper wick (<= 30%) never trips it; STRICT (25%) could
        else:
            shape_ok = strong_bearish(c, self.p) or bearish_pin(c, self.p)
            rejected = lower_rejection(c, self.p)
        qid = f"{pre}-004" if long else f"{pre}-003"
        if not shape_ok or rejected:
            fsm.to(State.SETUP_INVALIDATED, c.end, "candle quality / rejection wick")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003"], [qid],
                             ["ORB-MA-001"], SignalStatus.INVALIDATED, "CANDLE_QUALITY_OR_REJECTION_WICK", fsm.trace, props)
        ext_id = "ORB-GAP-LONG-005" if long else "ORB-GAP-SHORT-004"
        if self.p.gap_max_points is not None and abs(g.points) > self.p.gap_max_points:
            fsm.to(State.SETUP_INVALIDATED, c.end, "gap excessively extended (proposed cap)")
            return self._rec(ctx, c, "Gap/200DMA", d, levels, sat, [ext_id], ["ORB-MA-001"], SignalStatus.INVALIDATED,
                             "GAP_EXCEEDS_PROPOSED_CAP", fsm.trace, props)
        fsm.to(State.SIGNAL_CONFIRMED, c.end, "gap crossed MA, close beyond, quality ok")
        unresolved = ["ORB-MA-001"]
        if self.p.gap_max_points is None:
            unresolved.append(ext_id)  # mandatory 'not excessively extended' filter has no definition -> not applied
        return self._rec(ctx, c, "Gap/200DMA", d, levels, sat + ["ORB-GAP-LONG-003" if long else f"{pre}-003", qid], [], unresolved,
                         SignalStatus.CONFIRMED, None, fsm.trace, props)
