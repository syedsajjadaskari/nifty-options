"""Phase 5.4 ORB audit measurements. Everything here MEASURES the first five-minute candle against the rulebook's conditions on the historical sessions; nothing is a strategy rule and nothing computes profit.

* ``geometry`` / ``strength_table``: the first candle's OHLC, body and wick shares and the verdict under each numeric approximation of 'strong' (STRICT / MODERATE / LOOSE), the pin-bar and rejection-wick tests, with signed margins.
* ``predicate_matrix``: for one direction, every predicate of Method 1, Method 2 and the Gap / 200-average setup in the ENGINE'S order, each with the observed value, the rule text, its source rule id and a signed margin
  (positive = satisfied by that much, negative = missed by that much); the first failing predicate per method.
* ``trend_variants``: the trend readings (the active previous-session EMA test, the structure variant and the literal 'price above the 200 EMA' at 09:20) with the numbers behind them.
* ``level_families``: every deterministic construction of 'the level that must break' that can be computed from information available at 09:15 (the previous day's extreme, the inner-swing readings, multi-session extremes and swings),
  with whether the first candle broke and closed beyond it. Families that are not in the source are labelled as such.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from nifty_trading.data.sessions import SessionContext
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
from nifty_trading.strategies.orb_candidates import (
    INNER_LEVEL_DEFS,
    inner_levels,
    select_inner_level,
    trendline_supportive,
)

PROFILES = ("STRICT", "MODERATE", "LOOSE")


def _pct(x: float, rg: float) -> float | None:
    return None if rg <= 0 else 100.0 * x / rg


def geometry(c: Candle) -> dict[str, Any]:
    rg = c.h - c.l
    body = abs(c.c - c.o)
    uw, lw = c.h - max(c.o, c.c), min(c.o, c.c) - c.l
    return {"open": c.o, "high": c.h, "low": c.l, "close": c.c, "range": rg, "body": body, "colour": "GREEN" if c.c > c.o else ("RED" if c.c < c.o else "DOJI"),
            "body_pct": _pct(body, rg), "upper_wick": uw, "upper_wick_pct": _pct(uw, rg), "lower_wick": lw, "lower_wick_pct": _pct(lw, rg),
            "close_location_pct": _pct(c.c - c.l, rg)}  # 100 = closed on the high, 0 = closed on the low


def strength_table(c: Candle, long: bool, p) -> dict[str, Any]:
    """Verdicts and margins of the first candle for the trade direction. ``opp_wick`` is the wick against the trade (upper for a long)."""
    g = geometry(c)
    opp = g["upper_wick_pct"] if long else g["lower_wick_pct"]
    fn = strong_bullish if long else strong_bearish
    out: dict[str, Any] = {"colour": g["colour"], "body_pct": g["body_pct"], "opposite_wick_pct": opp, "same_side_wick_pct": g["lower_wick_pct"] if long else g["upper_wick_pct"], "close_location_pct": g["close_location_pct"]}
    from nifty_trading.strategies.params import STRONG_CANDLE
    for prof in PROFILES:
        pv = replace(p, strong_candle=prof)
        th = STRONG_CANDLE[prof]
        out[f"strong_{prof}"] = bool(fn(c, pv))
        out[f"body_margin_{prof}"] = None if g["body_pct"] is None else g["body_pct"] - 100 * th["body_ratio_min"]
        out[f"opp_wick_margin_{prof}"] = None if opp is None else 100 * th["opposite_wick_ratio_max"] - opp
    pin_fn = bullish_pin if long else bearish_pin
    out["pin_bar_active_definition"] = bool(pin_fn(c, p))
    wick = g["lower_wick"] if long else g["upper_wick"]
    out["pin_wick_to_body"] = None if g["body"] <= 1e-12 else wick / g["body"]
    out["pin_close_distance_from_favourable_extreme_pct"] = _pct((c.h - c.c) if long else (c.c - c.l), g["range"])  # the owner pin test needs <= 30
    rej_fn = upper_rejection if long else lower_rejection
    out["rejection_wick_flag_active_definition"] = bool(rej_fn(c, p))
    return out


def _pass(ok: bool | None, observed: Any, rule: str, rid: str, margin: float | None = None) -> dict[str, Any]:
    return {"pass": ok, "observed": observed, "rule": rule, "rule_id": rid, "margin": margin}


def trend_variants(ctx: SessionContext, long: bool, p) -> dict[str, Any]:
    """The trend readings with their numbers. ``active`` is the mode of the frozen configuration."""
    d = "LONG" if long else "SHORT"
    prev = to_candles(prev_candles(ctx.previous, p))
    last = prev[-1]
    first_ema = float(ctx.candles["ema200_5m"].iloc[0])
    c0 = float(ctx.candles["close"].iloc[0])
    out: dict[str, Any] = {"active_mode": p.trend_mode, "prev_session_last_close": last.c, "prev_session_last_ema": last.ema, "prev_close_minus_ema": last.c - last.ema if not math.isnan(last.ema) else None,
                           "first_candle_close": c0, "ema_at_first_candle": first_ema, "first_close_minus_ema": c0 - first_ema if not math.isnan(first_ema) else None, "open_minus_ema_at_first_candle": float(ctx.open_price) - first_ema if not math.isnan(first_ema) else None}
    k = 12
    if len(prev) > k and not math.isnan(prev[-1].ema) and not math.isnan(prev[-1 - k].ema):
        out["ema_change_over_last_hour_of_previous_session"] = prev[-1].ema - prev[-1 - k].ema  # EMA direction: rising (+) / falling (-)
    for label, mode in (("active", p.trend_mode), ("prev_session_close_vs_ema", "EMA_PREV_SESSION_CLOSE"), ("structure_ema_swing2", "STRUCTURE_EMA_SWING2"), ("first_candle_close_vs_ema_basic", "EMA5M_BASIC")):
        t = trend_check(ctx, 0, d, mode, p)
        out[label] = {"ok": t.ok, "reason": t.reason}
    return out


def predicate_matrix(ctx: SessionContext, p, long: bool) -> dict[str, list[dict[str, Any]]]:
    """{method: [predicate rows in the engine's order]} for one direction. A row: name, pass (True / False / None = not evaluable), observed, rule, rule_id, margin."""
    cs = to_candles(ctx.candles)
    c = cs[0]
    prev = ctx.previous
    pcs = to_candles(prev_candles(prev, p))
    ph, pl = prev_high_low(prev, p)
    d = "LONG" if long else "SHORT"
    pre1, pre2, preg = ("ORB-M1-LONG", "ORB-M2-LONG", "ORB-GAP-LONG") if long else ("ORB-M1-SHORT", "ORB-M2-SHORT", "ORB-GAP-SHORT")
    st = strength_table(c, long, p)
    quality = bool(st[f"strong_{p.strong_candle}"])
    quality_ok = quality or (p.orb_pin_bar_in_methods_1_2 and st["pin_bar_active_definition"])
    q_obs = f"body {st['body_pct']:.1f}% opposite wick {st['opposite_wick_pct']:.1f}% close location {st['close_location_pct']:.1f}%" if st["body_pct"] is not None else "zero-range candle"
    q_margin = None if st["body_pct"] is None else min(st[f"body_margin_{p.strong_candle}"], st[f"opp_wick_margin_{p.strong_candle}"])
    tr = trend_check(ctx, 0, d, p.trend_mode, p)
    tv = trend_variants(ctx, long, p)
    trend_margin = tv["prev_close_minus_ema"] if p.trend_mode in ("EMA_PREV_SESSION_CLOSE", "STRUCTURE_EMA_SWING2") else tv["first_close_minus_ema"]
    if trend_margin is not None and not long:
        trend_margin = -trend_margin
    trend_row = _pass(tr.ok, tr.reason, f"established trend in the trade direction (active mode {p.trend_mode})", "ORB-TREND-001", trend_margin)
    out: dict[str, list[dict[str, Any]]] = {}
    # ---------------------------------------------------------------- Method 1
    lvl = ph if long else pl
    broke1 = (c.h > lvl and c.c > lvl) if long else (c.l < lvl and c.c < lvl)
    m1_margin = (c.c - lvl) if long else (lvl - c.c)
    out["Method 1"] = [{"name": "level_broken", **_pass(bool(broke1), f"{'previous-day high' if long else 'previous-day low'} {lvl}; candle high/low {c.h if long else c.l}, close {c.c}", "the first candle breaks AND closes beyond the previous-day level", f"{pre1}-002", m1_margin)},
                       {"name": "trend", **trend_row}, {"name": "candle_quality", **_pass(bool(quality_ok), q_obs, "strong body with limited opposite wick, or the conditional pin bar", f"{pre1}-003", q_margin)}]
    # ---------------------------------------------------------------- Method 2 (the frozen construction)
    levels = inner_levels(pcs, ph, pl, long)
    ilvl = select_inner_level(levels, c, long, "LATEST_FRACTAL_K2")
    if ilvl is None:
        broke2, m2_obs, m2_margin = False, "no inner swing inside the previous range", None
    else:
        broke2 = (c.h > ilvl and c.c > ilvl) if long else (c.l < ilvl and c.c < ilvl)
        m2_obs, m2_margin = f"latest inner swing {ilvl}; close {c.c}", ((c.c - ilvl) if long else (ilvl - c.c))
    tl_idx = pivot_lows(pcs, 0, len(pcs), 2) if long else pivot_highs(pcs, 0, len(pcs), 2)
    ok_tl, tl_reason, line_now = trendline_supportive(pcs, tl_idx, c, long, "LAST_TWO_FRACTALS_K2")
    tl_margin = None if line_now is None else ((c.c - line_now) if long else (line_now - c.c))
    ema = float(ctx.candles["ema200_5m"].iloc[0])
    near_ok = True
    near_obs = "EMA not near"
    near_margin = None
    if not math.isnan(ema) and abs(c.c - ema) <= p.ma_near_band_points:
        beyond = (c.c - ema) if long else (ema - c.c)
        near_ok, near_obs, near_margin = beyond >= p.ma_close_margin_points, f"close within {p.ma_near_band_points} of the EMA; beyond it by {beyond:.2f}", beyond - p.ma_close_margin_points
    out["Method 2"] = [{"name": "inner_level_broken", **_pass(bool(broke2), m2_obs, "the first candle breaks AND closes beyond the inner level (frozen construction: latest fractal inside the previous range)", f"{pre2}-002", m2_margin)},
                       {"name": "trend", **trend_row},
                       {"name": "trendline", **_pass(bool(ok_tl), f"{tl_reason}; line at the open {None if line_now is None else round(line_now, 2)}", "trendline through the last two previous-session fractal lows (highs): rising (falling) and the close on the trend side", f"{pre2}-001", tl_margin)},
                       {"name": "candle_quality", **_pass(bool(quality_ok), q_obs, "strong body with limited opposite wick, or the conditional pin bar", f"{pre2}-003", q_margin)},
                       {"name": "near_ema_close", **_pass(bool(near_ok), near_obs, "near the EMA: a convincing close beyond it is required", f"{pre2}-004", near_margin)}]
    # ---------------------------------------------------------------- Gap / 200 average
    g = gap_info(ctx, p)
    ma = ma_value(ctx, 0, p.ma_mode)
    ma_prev = prev.ema_at_last_candle if p.ma_mode == "EMA200_5M" else ma
    gap_dir = g.direction
    gap_ok = g.evaluable and gap_dir == ("UP" if long else "DOWN")
    rows: list[dict[str, Any]] = [{"name": "gap_in_direction", **_pass(bool(gap_ok), f"gap {g.points:+.2f} ({gap_dir})", "the market opens beyond the previous close in the trade direction", f"{preg}-001", (g.points if long else -g.points) if g.evaluable else None)}]
    pc = prev.close_official
    crossed = (pc < ma_prev and ctx.open_price > ma) if long else (pc > ma_prev and ctx.open_price < ma)
    cross_margin = min(ma_prev - pc, ctx.open_price - ma) if long else min(pc - ma_prev, ma - ctx.open_price)
    rows.append({"name": "gap_crosses_200_average", **_pass(bool(crossed), f"previous close {pc} vs previous EMA {ma_prev:.2f}; open {ctx.open_price} vs EMA {ma:.2f}", "the gap brings price from the wrong side of the 200 average to the right side AT THE OPEN (frozen reading)", f"{preg}-002", cross_margin)})
    beyond = (c.c > ma) if long else (c.c < ma)
    rows.append({"name": "first_candle_closes_beyond_average", **_pass(bool(beyond), f"close {c.c} vs EMA {ma:.2f}", "the first candle closes beyond the 200 average", f"{preg}-003", (c.c - ma) if long else (ma - c.c))})
    shape_ok = (strong_bullish(c, p) or bullish_pin(c, p)) if long else (strong_bearish(c, p) or bearish_pin(c, p))
    rejected = upper_rejection(c, p) if long else lower_rejection(c, p)
    rows.append({"name": "candle_shape", **_pass(bool(shape_ok and not rejected), q_obs + f"; rejection wick flag {rejected}", "strong body or suitable pin bar, and no strong rejection wick", f"{preg}-004" if long else f"{preg}-003", q_margin)})
    out["Gap/200DMA"] = rows
    return out


def first_failing(rows: list[dict[str, Any]]) -> str:
    for r in rows:
        if r["pass"] is False:
            return r["name"]
    return "NONE (all predicates pass)" if all(r["pass"] for r in rows) else "NOT_EVALUABLE"


# ============================================================================================================== level families
def _sessions_before(sessions: list[list[Candle]], k: int) -> list[Candle]:
    return [x for s in sessions[:k] for x in s]


def _broken(c: Candle, level: float, long: bool) -> bool:
    return (c.h > level and c.c > level) if long else (c.l < level and c.c < level)


def level_families(ctx: SessionContext, p, prior_sessions: list[list[Candle]], long: bool) -> list[dict[str, Any]]:
    """Every causally available construction of 'the level to break'. ``prior_sessions``: the previous sessions' candles, most recent first (used for the multi-session families). A row: family, level (None = the
    construction yields no level), broken (the first candle breaks AND closes beyond it), open_beyond_level (the open is already beyond it), close_minus_level (signed in the trade direction), source status."""
    c = to_candles(ctx.candles)[0]
    pcs = to_candles(prev_candles(ctx.previous, p))
    ph, pl = prev_high_low(ctx.previous, p)
    out: list[dict[str, Any]] = []

    def add(family: str, level: float | None, status: str, note: str) -> None:
        if level is None:
            out.append({"family": family, "level": None, "broken": False, "open_beyond_level": None, "close_minus_level": None, "source_status": status, "note": note})
            return
        out.append({"family": family, "level": level, "broken": _broken(c, level, long), "open_beyond_level": (c.o > level) if long else (c.o < level), "close_minus_level": (c.c - level) if long else (level - c.c),
                    "source_status": status, "note": note})
    add("M1_PREVIOUS_DAY_EXTREME", ph if long else pl, "EXPLICIT_DOCUMENT_RULE (Method 1)", "horizontal line at the previous day's resistance / support")
    levels = inner_levels(pcs, ph, pl, long)
    for dfn in INNER_LEVEL_DEFS:
        add(f"M2_{dfn}", select_inner_level(levels, c, long, dfn), "CURRENT_ENGINE_ASSUMPTION" if dfn == "LATEST_FRACTAL_K2" else "RESEARCH_PROPOSAL", "an inner level inside the previous day's range (the rulebook gives no construction)")
    for n in (2, 3, 5):
        cs_n = _sessions_before(prior_sessions, n)
        if cs_n:
            add(f"MS_EXTREME_{n}_SESSIONS", max(x.h for x in cs_n) if long else min(x.l for x in cs_n), "RESEARCH_PROPOSAL (not in the written rules; the page-13 reference charts draw zones that extend across sessions)", f"extreme of the last {n} sessions")
    sw: list[float] = []
    for s in prior_sessions[:3]:
        sw += [s[j].h for j in pivot_highs(s, 0, len(s), 2)] if long else [s[j].l for j in pivot_lows(s, 0, len(s), 2)]
    if sw:
        ahead = [x for x in sw if (x > c.o if long else x < c.o)]
        add("MS_SWING_NEAREST_FROM_OPEN_3_SESSIONS", (min(ahead) if long else max(ahead)) if ahead else None, "RESEARCH_PROPOSAL", "nearest swing of the last 3 sessions the price must cross from the open")
    return out


def gap_crossing_readings(ctx: SessionContext, p, long: bool) -> dict[str, Any]:
    """Two readings of the Gap / 200-average condition (rulebook pp.7-9: 'the gap must bring price above [the average]'; 'a candle that only crosses the line but closes below it does not qualify').
    frozen  = the previous close on the wrong side of its average AND the OPEN already on the right side of the average (strictly), and the first candle closes beyond it.
    alt     = the same gap and previous-close conditions, but the first CANDLE (not only the open) may cross the average: it closes beyond it and its range reaches it. Pure reading difference: no threshold."""
    c = to_candles(ctx.candles)[0]
    g = gap_info(ctx, p)
    ma = ma_value(ctx, 0, p.ma_mode)
    ma_prev = ctx.previous.ema_at_last_candle if p.ma_mode == "EMA200_5M" else ma
    pc = ctx.previous.close_official
    gap_ok = g.evaluable and g.direction == ("UP" if long else "DOWN")
    if not gap_ok or math.isnan(ma) or math.isnan(ma_prev):
        return {"gap_in_direction": bool(gap_ok), "frozen_crossing": False, "alt_candle_crossing": False, "differs": False, "open_minus_ma": None}
    prev_wrong_side = pc < ma_prev if long else pc > ma_prev
    open_beyond = ctx.open_price > ma if long else ctx.open_price < ma
    closed_beyond = c.c > ma if long else c.c < ma
    reaches = (c.l <= ma) if long else (c.h >= ma)
    frozen = bool(prev_wrong_side and open_beyond and closed_beyond)
    alt = bool(prev_wrong_side and closed_beyond and (open_beyond or reaches))
    return {"gap_in_direction": True, "frozen_crossing": frozen, "alt_candle_crossing": alt, "differs": alt != frozen, "open_minus_ma": (ctx.open_price - ma) if long else (ma - ctx.open_price)}
