"""Independent ORB forensic measurements. Diagnostic only; never an engine factory.

This module deliberately reconstructs the frozen predicates without calling the
Phase 5.4/5.6 diagnostic helpers. Both directions are retained; journal direction
is unknown. Removing a gate below is a sensitivity experiment, not a source rule.
"""

from __future__ import annotations

import math
from itertools import combinations

EPS = 1e-9


def geometry(row) -> dict:
    o, h, l, c = (float(row[k]) for k in ("open", "high", "low", "close"))
    span = h - l
    return {"open": o, "high": h, "low": l, "close": c,
            "body_points": abs(c - o), "range_points": span,
            "body_pct": 100 * abs(c - o) / span if span else None,
            "upper_wick": h - max(o, c), "lower_wick": min(o, c) - l,
            "close_position_pct": 100 * (c - l) / span if span else None,
            "colour": "GREEN" if c > o else ("RED" if c < o else "DOJI")}


def pivots(frame, high: bool) -> list[int]:
    """Non-strict five-bar extremes, fully confirmed in the previous session."""
    vals = frame["high" if high else "low"].to_numpy()
    return [i for i in range(2, len(vals) - 2)
            if all(vals[i] >= vals[j] if high else vals[i] <= vals[j]
                   for j in (i - 2, i - 1, i + 1, i + 2))]


def shape(g: dict, long: bool, p) -> tuple[bool, bool, bool]:
    span = g["range_points"]
    if span <= 0:
        return False, False, False
    body = g["body_points"]
    opposite = g["upper_wick" if long else "lower_wick"]
    favourable = g["lower_wick" if long else "upper_wick"]
    colour = g["close"] > g["open"] if long else g["close"] < g["open"]
    strong = (colour and body / span >= p.strong["body_ratio_min"] - EPS
              and opposite / span <= p.strong["opposite_wick_ratio_max"] + EPS)
    if "wick_to_body_min" in p.pin:
        distance = g["high"] - g["close"] if long else g["close"] - g["low"]
        pin = (favourable > EPS and favourable >= p.pin["wick_to_body_min"] * body - EPS
               and distance <= p.pin["close_fraction_max"] * span + EPS)
    else:
        pin = (favourable / span >= p.pin["wick_ratio_min"] - EPS
               and body / span <= p.pin["body_ratio_max"] + EPS
               and opposite / span <= p.pin["opposite_wick_ratio_max"] + EPS)
    rejected = opposite / span >= p.reject["wick_ratio_min"] - EPS
    return bool(strong), bool(pin), bool(rejected)


def reconstruct(ctx, p, variant="frozen") -> list[dict]:
    """All gates, including ones short-circuited by the engine. Baseline is EMA_PREV_SESSION_CLOSE.

    Variants each replace one family: gap crossing; strong shape; trend timestamp;
    inner-level choice; trendline pair; colour; or gap indicator. No fills/exits.
    """
    if p.trend_mode != "EMA_PREV_SESSION_CLOSE":
        raise ValueError("Phase 5.8 reference must explicitly select previous-session EMA trend")
    if ctx.previous is None:
        return []
    prev = ctx.previous
    pc = prev.candles
    if p.prev_day_level_window == "CONTINUOUS_ONLY" and prev.continuous_candles is not None:
        pc = prev.continuous_candles
    g = geometry(ctx.candles.iloc[0])
    ph, pl = float(pc.high.max()), float(pc.low.min())
    e = float(ctx.candles.ema200_5m.iloc[0])
    pe = float(pc.ema200_5m.iloc[-1])
    last = float(pc.close.iloc[-1])
    prev_close = prev.close_official
    gap = ctx.open_price - prev_close if prev_close is not None else math.nan
    rows = []
    precheck = (ctx.info.usable and not (prev.gap_to_this_session_unverified
                                        and not p.allow_unverified_prev_session))
    for long in (True, False):
        direction, sign = ("LONG", 1) if long else ("SHORT", -1)
        strong, pin, reject = shape(g, long, p)
        if variant == "strength_loose":
            span = g["range_points"]
            opposite = g["upper_wick" if long else "lower_wick"]
            strong = (span > 0 and sign * (g["close"] - g["open"]) > 0
                      and g["body_points"] / span >= 0.5 - EPS
                      and opposite / span <= 0.25 + EPS)
        quality = strong or (p.orb_pin_bar_in_methods_1_2 and pin)
        trend = (None if math.isnan(pe) else sign * (last - pe) > 0)
        if variant == "trend_current":
            trend = None if math.isnan(e) else sign * (g["close"] - e) > 0
        colour = sign * (g["close"] - g["open"]) > 0
        highs, lows = pivots(pc, True), pivots(pc, False)
        inner_idxs = ([j for j in highs if float(pc.high.iloc[j]) < ph] if long
                      else [j for j in lows if float(pc.low.iloc[j]) > pl])
        inner_vals = [float(pc.iloc[j]["high" if long else "low"]) for j in inner_idxs]
        inner = inner_vals[-1] if inner_vals else None
        if variant == "inner_extreme" and inner_vals:
            inner = max(inner_vals) if long else min(inner_vals)
        if variant == "inner_nearest":
            ahead = [v for v in inner_vals if sign * (v - g["open"]) > 0]
            inner = (min(ahead) if long else max(ahead)) if ahead else None
        ti = lows if long else highs
        tl, slope, anchors, tl_ok = None, None, [], False
        pairs = list(combinations(ti[-3:], 2)) if variant == "trendline_any3" else ([tuple(ti[-2:])] if len(ti) >= 2 else [])
        for j1, j2 in pairs:
            y1, y2 = (float(pc.iloc[j]["low" if long else "high"]) for j in (j1, j2))
            slope = (y2 - y1) / (j2 - j1)
            tl = y2 + slope * (len(pc) - j2)
            anchors = [j1, j2]
            tl_ok = sign * slope > 0 and sign * (g["close"] - tl) > 0
            if tl_ok:
                break
        methods = {}
        major = ph if long else pl
        methods["Method 1"] = [
            ("previous_level_close", sign * (g["close"] - major) > 0,
             f"close={g['close']:.8f}; level={major:.8f}; signed distance={sign * (g['close'] - major):.8f}", "PREVIOUS_DAY_LEVEL_NOT_BROKEN", "PDF pp.3-4; p.4 major-level table", "SOURCE_EXPLICIT"),
            ("trend", trend, f"previous last 5m close={last:.8f}; EMA={pe:.8f}; current close={g['close']:.8f}; EMA={e:.8f}", "EMA_TREND_REJECTION", "PDF pp.3-4 trend step; research/phase3.py:47", "OWNER_RESEARCH_VARIANT_RECORDED_IN_REPO"),
            ("quality", quality, f"strong={strong}; pin={pin}; body={g['body_pct']}; upper={g['upper_wick']}; lower={g['lower_wick']}", "CANDLE_STRENGTH_REJECTION", "PDF pp.9-10; params.py:26-44", "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL"),
        ]
        near_ok = math.isnan(e) or abs(g["close"] - e) > p.ma_near_band_points or sign * (g["close"] - e) >= p.ma_close_margin_points
        methods["Method 2"] = [
            ("inner_defined", inner is not None, str(inner), "INNER_LEVEL_UNDEFINED", "PDF pp.4-7; no mechanical construction", "ENGINEERING_ASSUMPTION"),
            ("inner_close", inner is not None and sign * (g["close"] - inner) > 0,
             f"close={g['close']}; inner={inner}; signed distance={sign * (g['close'] - inner) if inner is not None else 'n.a.'}", "INNER_LEVEL_NOT_BROKEN", "PDF p.5 step 5 / p.6 mirror; latest k2 not specified", "SOURCE_BREAK_ASSUMED_LEVEL"),
            ("trend", trend, f"previous close={last}; previous EMA={pe}", "EMA_TREND_REJECTION", "PDF pp.5-7; research/phase3.py:47", "OWNER_RESEARCH_VARIANT_RECORDED_IN_REPO"),
            ("trendline", tl_ok, f"anchors={anchors}; slope={slope}; opening line={tl}; close={g['close']}", "TRENDLINE_REJECTION", "PDF pp.5-7; last two k2 not specified", "QUALITATIVE_SOURCE_ASSUMED_CONSTRUCTION"),
            ("quality", quality, f"strong={strong}; pin={pin}; body={g['body_pct']}", "CANDLE_STRENGTH_REJECTION", "PDF pp.9-10", "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL"),
            ("near_ma", near_ok, f"EMA={e}; close={g['close']}; near band={p.ma_near_band_points}; margin={p.ma_close_margin_points}", "EMA_TREND_REJECTION", "PDF p.5 step 7 / p.7 EMA row", "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL"),
        ]
        ma = ctx.daily_sma200_prev if variant == "gap_daily_sma" else e
        ma_prev = ma if variant == "gap_daily_sma" else prev.ema_at_last_candle
        warm = not (math.isnan(ma) or math.isnan(ma_prev))
        prev_wrong = warm and prev_close is not None and sign * (prev_close - ma_prev) < 0
        open_beyond = warm and sign * (ctx.open_price - ma) > 0
        reaches = warm and (g["low"] <= ma if long else g["high"] >= ma)
        crossing = prev_wrong and (open_beyond or (variant == "gap_candle" and reaches))
        methods["Gap/200DMA"] = [
            ("gap_direction", not math.isnan(gap) and sign * gap > p.gap_min_points, f"gap={gap}; minimum={p.gap_min_points}", "GAP_CROSSING_MISMATCH", "PDF pp.8-9 first step", "SOURCE_EXPLICIT"),
            ("ma_available", warm, f"MA={ma}; previous MA={ma_prev}", "DATA_DIFFERENCE", "sessions.py causal_ema; PDF MA unspecified", "CAUSAL_DATA_REQUIREMENT"),
            ("gap_crossing", crossing, f"prev wrong={prev_wrong}; open beyond={open_beyond}; candle reaches={reaches}; EMA={ma}", "GAP_CROSSING_MISMATCH", "PDF pp.8-9 diagrams vs wording; p.12 lower real chart", "SOURCE_CONFLICT_OPEN_REQUIREMENT_NARROWER_THAN_FIGURES"),
            ("ma_close", warm and sign * (g["close"] - ma) > 0, f"close={g['close']}; MA={ma}", "GAP_CROSSING_MISMATCH", "PDF pp.8-9 first-candle close", "SOURCE_EXPLICIT"),
            ("quality", (strong or pin) and not reject, f"strong={strong}; pin={pin}; rejection={reject}", "CANDLE_STRENGTH_REJECTION", "PDF pp.8-10", "QUALITATIVE_SOURCE_NUMERIC_PROPOSAL"),
            ("gap_cap", p.gap_max_points is None or abs(gap) <= p.gap_max_points,
             f"configured cap={p.gap_max_points}; source extended-move exclusion unimplemented when None", "GAP_CROSSING_MISMATCH", "PDF p.9 rejection box", "SOURCE_QUALITATIVE_UNDEFINED_CAP_DISABLED"),
        ]
        for method, gates in methods.items():
            if variant == "colour":
                gates.append(("colour", colour, g["colour"], "OPENING_CANDLE_COLOUR", "Handwritten p.5 20251127-1; PDF p.1 symmetry", "AUTHOR_CLARIFICATION_LONG_SHORT_MIRROR"))
            reached = precheck
            details = []
            for name, passed, observed, cause, source, authority in gates:
                details.append({"predicate": name, "passed": None if passed is None else bool(passed),
                                "observed": observed, "reached_in_code": reached, "cause": cause,
                                "source": source, "authority": authority})
                reached = reached and passed is True
            failed = [x for x in details if x["passed"] is not True]
            rows.append({"date": str(ctx.date), "direction": direction, "method": method,
                         "variant": variant, "eligible": precheck and not failed,
                         "precheck": precheck, "failed": [x["predicate"] for x in failed],
                         "first_failure": "DATA_PRECHECK" if not precheck else (failed[0]["predicate"] if failed else ""),
                         "causes": sorted({x["cause"] for x in failed}), "gates": details,
                         "level": major if method == "Method 1" else (inner if method == "Method 2" else ma),
                         "inner_level": inner, "trendline": tl, "trendline_slope": slope,
                         "trendline_anchors": anchors, "inner_indices": inner_idxs,
                         "geometry": g, "ema": e, "prev_ema": pe, "gap": gap,
                         "signed_breakout_distance": sign * (g["close"] - (major if method == "Method 1" else (inner if method == "Method 2" else ma))) if method != "Method 2" or inner is not None else None})
    return rows


VARIANTS = {
    "gap_candle": ("PDF pp.8-9 schematics and p.12 lower chart: first candle crosses MA; retain gap direction and prior-close side", "SOURCE_SUPPORTED_CONFLICTING_TEXT"),
    "strength_loose": ("PDF p.10 qualitative big body/small wick; 50%/25% illustrative replacement for 60%/20%", "NUMERIC_SENSITIVITY_ONLY"),
    "trend_current": ("PDF pp.3-7 price above/below EMA; current 09:20 close instead of prior-session location", "BASIC_FILTER_ONLY_STRUCTURE_UNRESOLVED"),
    "inner_extreme": ("PDF p.4 minor swing high/consolidation top: most extreme confirmed inner fractal instead of latest", "LEVEL_SELECTION_PROPOSAL"),
    "inner_nearest": ("PDF pp.4-7 smaller inner resistance/support: nearest previous-session confirmed inner level ahead of opening price; chosen before first close, not by which level breaks", "LEVEL_SELECTION_PROPOSAL"),
    "trendline_any3": ("PDF p.5 relevant swing lows: any pair among last three confirmed pivots, retaining supportive slope/side", "CONSTRUCTION_PROPOSAL"),
    "colour": ("Handwritten p.5 20251127-1: ORB long must close green; PDF p.1 short mirror", "AUTHOR_CLARIFIED_LONG_MIRRORED_SHORT"),
    "gap_daily_sma": ("PDF pp.8-9 term 200 DMA: literal daily SMA, kept separate; not confirmed author intent", "INDICATOR_SENSITIVITY_NOT_CORRECTION"),
}
