"""Phase 5.2 diagnostics: MEASUREMENTS that test the author's clarifications on the historical candles. Nothing here is a strategy rule and nothing computes profit.

* PDR / PDS: every setup's zone, first interaction, every candidate confirmation candle with its pattern measurements, the first fully eligible confirmation, and a comparison with the candle the engine actually chose
  (``LATE_ENTRY_DEFECT`` when the engine's entry is later than the first eligible candle). The setup loops mirror the engine's own sequence (the same retest-first conventions and the same pattern functions) so that the
  comparison tests the engine's choice of candle; ``scripts/phase52_independent_audit.py`` re-derives the same answer from the raw one-minute files without importing ``src/``.
* IRF: for each confirmed signal the EMA(200) distances, the position of the EMA between entry and Target 1, and the running session low using ONLY information available at the signal's decision time.
  The alternative readings of 'the gap between the EMA and the candle should be 28 points' and 'not at the day's low' are reported side by side as flags; none of them is a rule.
* ORB: for each disputed date, the first failing rule of every method and direction, with the numbers.
"""

from __future__ import annotations

import math
from dataclasses import replace
from typing import Any

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import SignalRecord
from nifty_trading.strategies.definitions import (
    Candle,
    bearish_pin,
    bullish_pin,
    gap_info,
    ma_value,
    pds_zone,
    pivot_highs,
    pivot_lows,
    prev_candles,
    prev_high_low,
    strong_bearish,
    strong_bullish,
    to_candles,
    trend_check,
)
from nifty_trading.strategies.pdr_body import build_zone
from nifty_trading.strategies.pdr_revised import classify_confirmation

T1_POINTS = 27.0  # the frozen Target 1 distance (EXE-T1-001)


def _hm(ts) -> str:
    return f"{ts:%H:%M}"


def _why_pattern_failed(res: dict[str, Any]) -> str:
    """The failing sub-tests of each approved confirmation pattern, in words."""
    parts = []
    g = res["patterns"]["GOOD_GREEN_BODY"]
    if not g["passed"]:
        bad = [n for n, k in (("not green", "bullish"), ("body below minimum", "body_ok"), ("upper wick above maximum", "upper_wick_ok")) if k in g and not g[k]]
        parts.append("GOOD_GREEN_BODY[" + ("; ".join(bad) or g.get("reason", "failed")) + "]")
    r = res["patterns"]["LOWER_PRICE_REJECTION"]
    if not r["passed"]:
        bad = [n for n, k in (("lower wick < 2x body", "wick_ok"), ("close not in top 30% of range", "close_location_ok"), ("low did not reach the zone", "low_reached_zone")) if k in r and not r[k]]
        parts.append("LOWER_PRICE_REJECTION[" + ("; ".join(bad) or r.get("reason", "failed")) + "]")
    h = res["patterns"]["HAMMER"]
    if not h["passed"]:
        bad = [n for n, k in (("lower wick < 2x body", "wick_ok"), ("upper wick above maximum", "upper_wick_ok"), ("body not in upper part", "body_position_ok")) if k in h and not h[k]]
        parts.append("HAMMER[" + ("; ".join(bad) or h.get("reason", "failed")) + "]")
    return " | ".join(parts)


# ============================================================================================================== PDR
def pdr_setup_diagnostics(ctx: SessionContext, sc) -> dict[str, Any]:
    """Zone, eligibility, every candidate confirmation candle and the first eligible one for the session's PDR setup(s). Mirrors the engine's sequence: the first candle whose range meets the zone is the retest
    ('interaction') candle; confirmation candidates are the candles AFTER it (the existing convention, PDR-A07, a proposal that is preserved and labelled)."""
    p, rev = sc.proposals, sc.pdr_revision
    g = gap_info(ctx, p)
    out: dict[str, Any] = {"date": str(ctx.date), "gap_direction": g.direction, "gap_points": g.points, "session_open": ctx.open_price, "interaction_convention": "CONFIRMATION_MAY_NOT_BE_THE_INTERACTION_CANDLE (PDR-A07, proposal, preserved)"}
    if g.direction != "UP":
        return {**out, "status": "NO_SETUP_NO_GAP_UP", "cycles": []}
    prev = ctx.previous
    zone = build_zone(to_candles(prev_candles(prev, p)), rev)
    out.update({"zone_construction_candle_start": f"{zone.source_starts[0]:%Y-%m-%d %H:%M}", "zone_known_from": f"{zone.source_starts[0]:%Y-%m-%d} previous session close", "zone_floor": zone.floor, "zone_ceiling": zone.ceiling,
                "zone_width": zone.width, "zone_flags": list(zone.flags), "open_strictly_above_ceiling": ctx.open_price > zone.ceiling})
    if zone.zero_height and rev.zero_height_policy == "UNRESOLVED_NO_SETUP":
        return {**out, "status": "NOT_ARMED_ZERO_HEIGHT_ZONE", "cycles": []}
    if rev.open_vs_zone == "ABOVE_ZONE" and not ctx.open_price > zone.ceiling:
        return {**out, "status": "NOT_ARMED_OPEN_NOT_STRICTLY_ABOVE_ZONE", "cycles": []}
    cs = to_candles(ctx.candles)
    pcfg = rev.pattern_config()
    prox = rev.proximity_points
    cycles: list[dict[str, Any]] = []
    j: int | None = None
    rows: list[dict[str, Any]] = []
    for i, c in enumerate(cs):
        if j is None:
            if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox:
                j = i
                rows = []
                if not rev.confirmation_may_be_interaction_candle:
                    res0 = classify_confirmation(c, zone.floor, zone.ceiling, pcfg)
                    rows.append({"candle_start": _hm(c.start), "signal_time_if_chosen": _hm(c.end), "open": c.o, "high": c.h, "low": c.l, "close": c.c, "close_minus_ceiling": round(res0["close_minus_ceiling"], 4), "patterns_passed": res0["patterns_passed"],
                                 "qualifies": False, "qualifies_if_the_retest_candle_were_permitted": bool(res0["qualifies"]),
                                 "reason_not_eligible": "IS_THE_RETEST_CANDLE (existing convention PDR-A07: the confirmation may not be the interaction candle)"})
                    cycles.append({"interaction_candle_start": _hm(c.start), "interaction_candle_would_qualify": bool(res0["qualifies"]), "candidates": rows, "first_eligible_candle_start": None})
                    continue
                cycles.append({"interaction_candle_start": _hm(c.start), "interaction_candle_would_qualify": None, "candidates": rows, "first_eligible_candle_start": None})
            else:
                continue
        res = classify_confirmation(c, zone.floor, zone.ceiling, pcfg)
        row = {"candle_start": _hm(c.start), "signal_time_if_chosen": _hm(c.end), "open": c.o, "high": c.h, "low": c.l, "close": c.c, "close_minus_ceiling": round(res["close_minus_ceiling"], 4), "patterns_passed": res["patterns_passed"],
               "qualifies": bool(res["qualifies"]), "reason_not_eligible": "" if res["qualifies"] else ("CLOSE_NOT_ABOVE_CEILING (close <= zone ceiling)" if not res["close_above_ceiling"] else "NO_PATTERN: " + _why_pattern_failed(res))}
        rows.append(row)
        if res["qualifies"] and (i > j or rev.confirmation_may_be_interaction_candle):
            cycles[-1]["first_eligible_candle_start"] = _hm(c.start)
            cycles[-1]["first_eligible_signal_time"] = _hm(c.end)
            j = None
    out["status"] = "ARMED" if cycles else "ARMED_NO_ZONE_RETEST"
    out["cycles"] = cycles
    first = next((cy for cy in cycles if cy["first_eligible_candle_start"]), None)
    out["first_eligible_signal_time"] = None if first is None else first["first_eligible_signal_time"]
    out["first_zone_touch_candle_start"] = cycles[0]["interaction_candle_start"] if cycles else None
    if cycles:
        out["sensitivity"] = _pdr_sensitivity(cs, zone, pcfg, prox)
    return out


def _pdr_sensitivity(cs: list[Candle], zone, pcfg, prox: float) -> dict[str, Any]:
    """DIAGNOSTICS ONLY (no rule): when would the FIRST retest's confirmation have come under other readings of 'first eligible'? A = the approved patterns, retest candle itself permitted; B = the first green candle
    AFTER the retest that closes above the ceiling, with no numeric pattern threshold (the guide's wording 'wait for a green candle after the zone has been tested'); C = as B but the retest candle itself permitted."""
    j0 = next((i for i, c in enumerate(cs) if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox), None)
    if j0 is None:
        return {}

    def first(pred, start: int):
        return next((_hm(cs[i].end) for i in range(start, len(cs)) if pred(cs[i])), None)
    green_above = lambda c: c.c > c.o and c.c > zone.ceiling  # noqa: E731
    return {"A_retest_candle_permitted_approved_patterns": first(lambda c: classify_confirmation(c, zone.floor, zone.ceiling, pcfg)["qualifies"], j0),
            "B_first_green_close_above_ceiling_after_retest_no_thresholds": first(green_above, j0 + 1), "C_first_green_close_above_ceiling_retest_permitted_no_thresholds": first(green_above, j0)}


# ============================================================================================================== PDS
def pds_setup_diagnostics(ctx: SessionContext, sc) -> dict[str, Any]:
    """Zone, retest and the sequence of PDS confirmation events in the engine's order (Methods 1 / 2 on the FIRST red candle at the zone; Method 3 only after a weak first red candle). Events are the candles on which a
    method completes; the first event is the first fully eligible confirmation."""
    p = sc.proposals
    g = gap_info(ctx, p)
    out: dict[str, Any] = {"date": str(ctx.date), "gap_direction": g.direction, "gap_points": g.points, "session_open": ctx.open_price}
    if g.direction != "DOWN":
        return {**out, "status": "NO_SETUP_NO_GAP_DOWN", "events": [], "candidates": []}
    zone = pds_zone(ctx.previous, p)
    prox = p.zone_proximity_points
    out.update({"zone_candle_start": zone.candle_start, "zone_low": zone.low, "zone_high": zone.high, "zone_method": zone.method, "open_below_zone_low": ctx.open_price < zone.low})
    bad = {"BELOW_ZONE": not ctx.open_price < zone.low, "NOT_ABOVE_ZONE": ctx.open_price > zone.high, "ANY": False}[p.pds_open_vs_zone]
    if bad:
        return {**out, "status": "NOT_ARMED_OPEN_NOT_BELOW_ZONE", "events": [], "candidates": []}
    cs = to_candles(ctx.candles)

    def at_zone(c: Candle) -> bool:
        return c.h >= zone.low - prox and c.l <= zone.high + prox

    def small_support(start: int, i: int):
        near = zone.high + prox
        if p.pds_small_support_def == "LAST_N2":
            if i - 2 < start:
                return None
            lvl = min(cs[i - 2].l, cs[i - 1].l)
            return lvl if lvl <= near else None
        js = [jj for jj in pivot_lows(cs, start, i, 1) if cs[jj].l <= near]
        return cs[js[-1]].l if js else None
    events: list[dict[str, Any]] = []
    cands: list[dict[str, Any]] = []
    later_strong: list[str] = []
    j0 = weak_r = None
    m3 = False
    for i, c in enumerate(cs):
        if j0 is None:
            if not at_zone(c):
                continue
            j0 = i
            m3 = p.pds_m3_standalone
            cands.append({"candle_start": _hm(c.start), "role": "FIRST_ZONE_INTERACTION"})
        red = c.c < c.o
        if weak_r is not None and i > weak_r and red and at_zone(c) and (strong_bearish(c, p) or (bearish_pin(c, p) and c.h >= zone.low)):
            later_strong.append(f"{_hm(c.start)} (signal {_hm(c.end)})")  # a LATER red candle at the zone that meets the Method 1 / 2 numbers after the first red candle was weak: preserved rule says Method 3, see the audit
        if weak_r is None and red and at_zone(c):
            strong, pin = strong_bearish(c, p), bearish_pin(c, p) and c.h >= zone.low
            cands.append({"candle_start": _hm(c.start), "role": "FIRST_RED_CANDLE_AT_ZONE", "strong_bearish": strong, "bearish_pin_hpr": pin, "open": c.o, "high": c.h, "low": c.l, "close": c.c})
            if strong or pin:
                events.append({"method": "Method 1" if strong else "Method 2", "candle_start": _hm(c.start), "signal_time": _hm(c.end), "entry_reference_close": c.c, "also_satisfied": ["Method 2"] if (strong and pin) else []})
                j0, m3 = None, False
                continue
            weak_r, m3 = i, True
            cands[-1]["outcome"] = "WEAK_FIRST_RED_CANDLE: not taken (quality rule PDS-M-001); Method 3 path armed"
        if m3 and j0 is not None:
            start = weak_r if weak_r is not None else j0
            sup = small_support(start, i)
            if sup is not None:
                hit = (c.c < sup) if p.pds_m3_break_basis == "CLOSE" else (c.l < sup)
                cands.append({"candle_start": _hm(c.start), "role": "METHOD_3_SUPPORT_BREAK_TEST", "small_support": sup, "close": c.c, "breaks_support": bool(hit)})
                if hit:
                    events.append({"method": "Method 3", "candle_start": _hm(c.start), "signal_time": _hm(c.end), "entry_reference_close": c.c, "small_support": sup, "also_satisfied": []})
                    j0, weak_r, m3 = None, None, False
    return {**out, "status": "ARMED" if cands else "ARMED_NO_ZONE_RETEST", "events": events, "candidates": cands, "later_strong_red_candles_after_weak_first_red": later_strong,
            "first_eligible_signal_time": events[0]["signal_time"] if events else None, "first_eligible_method": events[0]["method"] if events else None}


def compare_with_engine(diag: dict[str, Any], records: list[SignalRecord], strategy: str) -> dict[str, Any]:
    """Compare the first eligible signal time with the first CONFIRMED engine record of the strategy; ``LATE_ENTRY_DEFECT`` if the engine is later."""
    conf = sorted((r for r in records if r.strategy == strategy and r.signal_status == "CONFIRMED"), key=lambda r: r.signal_timestamp)
    eng = None if not conf else _hm(conf[0].signal_timestamp)
    first = diag.get("first_eligible_signal_time")
    if first is None and eng is None:
        verdict = "NO_SIGNAL_EITHER"
    elif first is None:
        verdict = "ENGINE_SIGNAL_WITHOUT_DIAGNOSTIC_ELIGIBLE_CANDLE"
    elif eng is None:
        verdict = "ELIGIBLE_CANDLE_BUT_NO_ENGINE_SIGNAL"
    elif eng == first:
        verdict = "ENGINE_ON_FIRST_ELIGIBLE_CANDLE"
    elif eng > first:
        verdict = "LATE_ENTRY_DEFECT"
    else:
        verdict = "ENGINE_EARLIER_THAN_DIAGNOSTIC"
    return {"engine_first_signal_time": eng, "diagnostic_first_eligible_signal_time": first, "verdict": verdict, "engine_signals_later_ignored": [_hm(r.signal_timestamp) for r in conf[1:]]}


# ============================================================================================================== IRF
def irf_measurements(ctx: SessionContext, cs: list[Candle], signal_end, fill_open: float | None) -> dict[str, Any]:
    """Measurements for an IRF short signal confirmed at ``signal_end``. Only candles that had CLOSED by then are used: the running session low is the lowest low of the candles before the signal candle (and, separately,
    including the signal candle itself); the final daily low is never touched."""
    idx = next((k for k, c in enumerate(cs) if c.end == signal_end), None)
    if idx is None:
        return {"error": "signal candle not found"}
    c = cs[idx]
    ema_s = ctx.candles["ema200_5m"].iloc[idx]
    ema = None if (isinstance(ema_s, float) and math.isnan(ema_s)) else float(ema_s)
    entry = fill_open if fill_open is not None else c.c
    before = min((x.l for x in cs[:idx]), default=None)
    incl = c.l if before is None else min(before, c.l)
    irl = cs[0].l
    prev_low = None if ctx.previous is None else float(ctx.previous.low)
    m: dict[str, Any] = {"signal_candle_start": _hm(c.start), "signal_time": _hm(c.end), "candle_open": c.o, "candle_high": c.h, "candle_low": c.l, "candle_close": c.c, "entry_price": entry, "entry_price_basis": "next one-minute open" if fill_open is not None else "signal candle close (no fill price available)",
                         "t1_level": entry - T1_POINTS, "ema200": ema, "running_low_before_signal_candle": before, "running_low_including_signal_candle": incl, "n_closed_candles_used": idx + 1}
    if ema is not None:
        cm, hm_, lm, em = c.c - ema, c.h - ema, c.l - ema, entry - ema
        m.update({"close_minus_ema": cm, "high_minus_ema": hm_, "low_minus_ema": lm, "entry_minus_ema": em, "abs_close_minus_ema": abs(cm), "ema_minus_t1": ema - (entry - T1_POINTS), "ema_between_entry_and_t1": (entry - T1_POINTS) < ema < entry,
                  # alternative readings of 'the gap between the EMA and the candle should be 28 points' (none is a rule); the same at 27 for comparison with the handwritten pages
                  "E1_close_gap_below_ema_28": 0 < cm < 28, "E2_entry_gap_below_ema_28": 0 < em < 28, "E3_low_gap_below_ema_28": 0 < lm < 28, "E4_abs_close_gap_28": abs(cm) < 28,
                  "E1_27": 0 < cm < 27, "E2_27": 0 < em < 27, "E1_between_27_and_28": 27 <= cm < 28, "E2_between_27_and_28": 27 <= em < 28})
    if before is not None:
        m.update({"entry_minus_running_low_before": entry - before, "close_minus_running_low_before": c.c - before, "t1_clearance_above_running_low": (entry - T1_POINTS) - before,
                  # alternative readings of 'not at the day's low' (none is a rule)
                  "D1_entry_at_or_below_running_low": entry <= before, "D2_close_below_running_low_before": c.c < before, "D3_close_at_running_low_incl_candle": c.c <= incl and c.l <= before and c.c <= c.l + 1e-9,
                  "D4_t1_beyond_running_low": (entry - T1_POINTS) < before, "D5_entry_within_28_of_running_low": 0 <= entry - before < 28,
                  # further readings suggested by the review (AC19: 'entry is below days low'): the day's low already lies below the opening range / a candle already closed below the initial range low / the entry is below the previous day's low
                  "D6_running_low_already_below_irl": before < irl, "D7_earlier_close_below_irl": any(x.c < irl for x in cs[1:idx]), "D8_entry_below_previous_day_low": prev_low is not None and entry < prev_low})
        m.update({"irl": irl, "previous_day_low": prev_low})
    return m


# ============================================================================================================== ORB
def _profiles(sc, c: Candle, long: bool) -> dict[str, dict[str, bool]]:
    out = {}
    for name in ("STRICT", "MODERATE", "LOOSE"):
        pp = replace(sc.proposals, strong_candle=name, pin_bar="OWNER_2X_CLOSE30")
        out[name] = {"strong": bool(strong_bullish(c, pp) if long else strong_bearish(c, pp)), "pin": bool(bullish_pin(c, pp) if long else bearish_pin(c, pp))}
    return out


def orb_audit(ctx: SessionContext, sc, records: list[SignalRecord]) -> dict[str, Any]:
    """Every ORB check, per direction, for the first candle of the session, with the first failing rule per method."""
    p = sc.proposals
    cs = to_candles(ctx.candles)
    c = cs[0]
    prev = ctx.previous
    ph, pl = prev_high_low(prev, p)
    rng = c.h - c.l
    out: dict[str, Any] = {"date": str(ctx.date), "first_candle": {"open": c.o, "high": c.h, "low": c.l, "close": c.c, "colour": "GREEN" if c.c > c.o else ("RED" if c.c < c.o else "DOJI"),
                                                                    "body_pct": None if rng <= 0 else round(100 * abs(c.c - c.o) / rng, 1), "upper_wick_pct": None if rng <= 0 else round(100 * (c.h - max(c.o, c.c)) / rng, 1),
                                                                    "lower_wick_pct": None if rng <= 0 else round(100 * (min(c.o, c.c) - c.l) / rng, 1)},
                           "prev_day_high": ph, "prev_day_low": pl, "prev_close": prev.close_official, "ema200_first_candle": float(ctx.candles["ema200_5m"].iloc[0]), "close_minus_ema": c.c - float(ctx.candles["ema200_5m"].iloc[0]),
                           "gap": None, "directions": {}}
    g = gap_info(ctx, p)
    out["gap"] = {"direction": g.direction, "points": g.points, "evaluable": g.evaluable}
    pcs = to_candles(prev_candles(prev, p))
    n = len(pcs)
    by = {(r.method, r.direction): r for r in records if r.strategy == "ORB"}
    for d in ("LONG", "SHORT"):
        long = d == "LONG"
        item: dict[str, Any] = {}
        # Method 1
        level = ph if long else pl
        broke1 = (c.h > level and c.c > level) if long else (c.l < level and c.c < level)
        item["M1_prev_day_level"] = level
        item["M1_level_broken"] = bool(broke1)
        # Method 2 (research variant: latest fractal inside the previous range + a fractal trendline)
        if long:
            piv = [j for j in pivot_highs(pcs, 0, n, 2) if pcs[j].h < ph]
            lvl2 = pcs[piv[-1]].h if piv else None
            tl = pivot_lows(pcs, 0, n, 2)
        else:
            piv = [j for j in pivot_lows(pcs, 0, n, 2) if pcs[j].l > pl]
            lvl2 = pcs[piv[-1]].l if piv else None
            tl = pivot_highs(pcs, 0, n, 2)
        item["M2_inner_level"] = lvl2
        item["M2_inner_level_broken"] = None if lvl2 is None else bool((c.h > lvl2 and c.c > lvl2) if long else (c.l < lvl2 and c.c < lvl2))
        if len(tl) >= 2:
            j1, j2 = tl[-2], tl[-1]
            y1, y2 = (pcs[j1].l, pcs[j2].l) if long else (pcs[j1].h, pcs[j2].h)
            slope = (y2 - y1) / (j2 - j1)
            now = y2 + slope * (n - j2)
            item.update({"M2_trendline_value_at_open": now, "M2_trendline_slope": slope, "M2_trendline_supportive": bool((slope > 0 if long else slope < 0) and (c.c > now if long else c.c < now))})
        else:
            item.update({"M2_trendline_value_at_open": None, "M2_trendline_slope": None, "M2_trendline_supportive": None})
        t = trend_check(ctx, 0, d, p.trend_mode, p)
        item.update({"trend_ok": t.ok, "trend_reason": t.reason, "trend_mode": p.trend_mode})
        item["colour_matches_direction"] = (c.c > c.o) if long else (c.c < c.o)
        item["strength_profiles"] = _profiles(sc, c, long)
        mode = p.ma_mode
        ma = ma_value(ctx, 0, mode)
        ma_prev = prev.ema_at_last_candle if mode == "EMA200_5M" else ma
        gap_dir_ok = g.evaluable and g.direction == ("UP" if long else "DOWN")
        crossed = bool(gap_dir_ok and ((prev.close_official < ma_prev and ctx.open_price > ma) if long else (prev.close_official > ma_prev and ctx.open_price < ma)))
        item.update({"gap_setup_gap_in_direction": bool(gap_dir_ok), "gap_setup_ma_mode": mode, "gap_setup_ma": ma, "gap_setup_gap_crosses_ma": crossed, "gap_setup_closed_beyond_ma": bool(c.c > ma if long else c.c < ma)})
        # engine records and the first failing rule per method
        for mname in ("Method 1", "Method 2", "Gap/200DMA"):
            r = by.get((mname, d))
            item[f"engine_{mname}"] = None if r is None else {"status": r.signal_status, "reason": r.invalidation_reason}
        first_fail: dict[str, str] = {}
        r1, r2, rg = by.get(("Method 1", d)), by.get(("Method 2", d)), by.get(("Gap/200DMA", d))
        first_fail["Method 1"] = ("CONFIRMED" if r1 is not None and r1.signal_status == "CONFIRMED" else (r1.invalidation_reason if r1 is not None else f"NO_SETUP: first candle did not break and close beyond the previous-day {'high' if long else 'low'} {level}"))
        first_fail["Method 2"] = ("CONFIRMED" if r2 is not None and r2.signal_status == "CONFIRMED" else (r2.invalidation_reason if r2 is not None else
                                  ("NO_SETUP: no inner level (fractal) inside the previous range" if lvl2 is None else f"NO_SETUP: first candle did not break and close beyond the inner level {lvl2:,.2f}")))
        first_fail["Gap/200DMA"] = ("CONFIRMED" if rg is not None and rg.signal_status == "CONFIRMED" else (rg.invalidation_reason if rg is not None else
                                    ("NO_SETUP: no gap in this direction" if not gap_dir_ok else "NO_SETUP: the gap did not push price through the 200 average")))
        item["first_failing_rule"] = first_fail
        out["directions"][d] = item
    return out


def _orb_text_category(txt: str) -> str | None:
    if "TRENDLINE_NOT_SUPPORTIVE" in txt or "NO_TRENDLINE" in txt:
        return "METHOD2_TRENDLINE"
    if "CANDLE_QUALITY" in txt:
        return "STRONG_CANDLE_THRESHOLD"
    if "TREND:" in txt:
        return "EMA_REQUIREMENT"
    if "CLOSE_NOT_BEYOND_MA" in txt:
        return "GAP_OR_MA_CALCULATION"
    return None


def orb_cause_category(row: dict[str, Any]) -> str:
    """One category per disputed date: the first failing rule of the direction that matches the first candle's colour (the author's direction is not stated), taking the methods in order Method 1, Method 2, Gap / 200 average.
    A method whose LEVEL was broken (a setup formed and a later rule failed) outranks 'no previous-day level broken'. The per-method failing rules are all listed in the audit table."""
    col = row["first_candle"]["colour"]
    d = "LONG" if col != "RED" else "SHORT"
    ff = row["directions"][d]["first_failing_rule"]
    if "CONFIRMED" in ff.values():
        return "ENGINE_SIGNAL_EXISTS"
    for method in ("Method 1", "Method 2", "Gap/200DMA"):
        cat = _orb_text_category(str(ff.get(method, "")))
        if cat is not None:
            return cat
    if "NO_SETUP: first candle did not break and close beyond the previous-day" in " | ".join(ff.values()):
        return "LEVEL_CONSTRUCTION (no previous-day level broken; Method 2 inner level undefined in the source)"
    return "SOURCE_AMBIGUITY"
