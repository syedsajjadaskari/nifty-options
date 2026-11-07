"""Phase 5.3 diagnostics: MEASUREMENTS around the owner-approved corrections. Nothing here is a strategy rule and nothing computes profit.

* IRF EMA: for every confirmed IRF signal, where the EMA(200) lies relative to the signal candle (above / below / inside the high-low range, between entry and Target 1), the range distance and the close distance,
  and the pass/fail outcome of the four readings that are compared (range >= 28, range >= 27, |close - EMA| >= 28, |close - EMA| >= 27). Also the day's-low measurements for the pending restriction.
* PDR: the per-session setup under the Phase 5.3 minimal confirmation (zone, retest, every candle's verdict, the first eligible one, whether the retest candle itself would have qualified).
* PDS: the first red candle at the zone with its geometry, the Phase 5.3 quality verdict and the method that applies.
"""

from __future__ import annotations

import math
from typing import Any

from nifty_trading.data.sessions import SessionContext
from nifty_trading.research import phase52_diag as D52
from nifty_trading.strategies.definitions import (
    Candle,
    gap_info,
    is_red,
    lower_wick,
    pds_zone,
    prev_candles,
    to_candles,
    upper_wick,
)
from nifty_trading.strategies.first_eligible_phase53 import (
    pdr_minimal_confirmation,
    pds_good_red,
    pds_red_pin,
)
from nifty_trading.strategies.irf_phase53 import EPS, ema_geometry
from nifty_trading.strategies.pdr_body import build_zone

T1 = 27.0


def _hm(ts) -> str:
    return f"{ts:%H:%M}"


def _num(x):
    return None if x is None or (isinstance(x, float) and math.isnan(x)) else float(x)


# ============================================================================================================== IRF
def irf_geometry(ctx: SessionContext, cs: list[Candle], signal_end, fill_open: float | None) -> dict[str, Any]:
    """EMA geometry + day's-low measurements for an IRF signal confirmed at ``signal_end`` (only candles closed by then are used)."""
    m = D52.irf_measurements(ctx, cs, signal_end, fill_open)
    if "error" in m:
        return m
    idx = next(k for k, c in enumerate(cs) if c.end == signal_end)
    c = cs[idx]
    e = _num(ctx.candles["ema200_5m"].iloc[idx])
    entry = m["entry_price"]
    m["entry_below_irl"] = entry < cs[0].l
    if e is None:
        m.update({"ema_available": False})
        return m
    g = ema_geometry(c.h, c.l, c.c, e)
    e_prev = _num(ctx.candles["ema200_5m"].iloc[idx - 1]) if idx > 0 else None
    prev_clear = None if e_prev is None else ema_geometry(c.h, c.l, c.c, e_prev)["range_clearance"]
    m.update({"ema_available": True, "ema_relation": g["relation"], "range_clearance": g["range_clearance"], "close_distance": g["close_distance"],
              "pass_range_28": g["range_clearance"] >= 28.0 - EPS, "pass_range_27": g["range_clearance"] >= 27.0 - EPS,
              "pass_close_28": g["close_distance"] >= 28.0 - EPS, "pass_close_27": g["close_distance"] >= 27.0 - EPS,
              "range_clearance_using_previous_candle_ema": prev_clear, "pass_range_28_using_previous_candle_ema": None if prev_clear is None else prev_clear >= 28.0 - EPS,
              "ema_between_entry_and_t1": (entry - T1) < e < entry, "ema_above_entry": e >= entry, "ema_below_t1": e <= entry - T1,
              "t1_blocked_by_ema_within_28": (entry - T1) < e < entry or (0 <= entry - e < 28.0)})
    return m


# ============================================================================================================== PDR
def pdr_phase53_setup(ctx: SessionContext, sc) -> dict[str, Any]:
    """The PDR setup of the session under the Phase 5.3 minimal confirmation: zone, retest (first candle meeting the zone), every later candle's verdict, the first eligible candle and whether the RETEST candle
    itself would have qualified (the sequencing convention preserved from the frozen engine forbids it)."""
    p, rev = sc.proposals, sc.pdr_revision
    g = gap_info(ctx, p)
    out: dict[str, Any] = {"date": str(ctx.date), "gap_direction": g.direction, "gap_points": g.points, "session_open": ctx.open_price}
    if g.direction != "UP":
        return {**out, "status": "NO_SETUP_NO_GAP_UP"}
    zone = build_zone(to_candles(prev_candles(ctx.previous, p)), rev)
    out.update({"zone_floor": zone.floor, "zone_ceiling": zone.ceiling, "open_strictly_above_ceiling": ctx.open_price > zone.ceiling})
    if not ctx.open_price > zone.ceiling or (zone.zero_height and rev.zero_height_policy == "UNRESOLVED_NO_SETUP"):
        return {**out, "status": "NOT_ARMED"}
    cs = to_candles(ctx.candles)
    prox = rev.proximity_points
    j = next((i for i, c in enumerate(cs) if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox), None)
    if j is None:
        return {**out, "status": "ARMED_NO_ZONE_RETEST"}
    rows = []
    first = None
    for i in range(j, len(cs)):
        c = cs[i]
        r = pdr_minimal_confirmation(c, zone.floor, zone.ceiling, prox)
        permitted = i > j
        rows.append({"candle_start": _hm(c.start), "signal_time_if_chosen": _hm(c.end), "role": "RETEST_CANDLE" if i == j else "CONFIRMATION_CANDIDATE", "ohlc": f"{c.o}/{c.h}/{c.l}/{c.c}", "green": r["green"],
                     "close_minus_ceiling": round(r["close_minus_ceiling"], 4), "patterns": r["patterns_passed"], "qualifies_by_pattern_and_close": r["qualifies"], "eligible": r["qualifies"] and permitted,
                     "reason_if_not": "" if (r["qualifies"] and permitted) else ("IS_THE_RETEST_CANDLE (sequencing convention preserved)" if i == j else ("CLOSE_NOT_ABOVE_CEILING" if not r["close_above_ceiling"] else "NO_GREEN_OR_REJECTION_PATTERN"))})
        if first is None and r["qualifies"] and permitted:
            first = i
    retest_res = pdr_minimal_confirmation(cs[j], zone.floor, zone.ceiling, prox)
    out.update({"status": "ARMED", "retest_candle_start": _hm(cs[j].start), "retest_candle_ohlc": f"{cs[j].o}/{cs[j].h}/{cs[j].l}/{cs[j].c}", "retest_candle_would_qualify_if_permitted": retest_res["qualifies"],
                "first_eligible_candle_start": None if first is None else _hm(cs[first].start), "first_eligible_signal_time": None if first is None else _hm(cs[first].end),
                "first_retest_confirmation_if_retest_permitted": _hm(cs[j].end) if retest_res["qualifies"] else (None if first is None else _hm(cs[first].end)), "rows": rows})
    return out


# ============================================================================================================== PDS
def pds_phase53_first_red(ctx: SessionContext, sc) -> dict[str, Any]:
    """The first red candle at the zone (the candle Methods 1 / 2 apply to) with its geometry and the Phase 5.3 quality verdict; ``None`` fields when there is none."""
    p = sc.proposals
    g = gap_info(ctx, p)
    out: dict[str, Any] = {"date": str(ctx.date), "gap_direction": g.direction}
    if g.direction != "DOWN":
        return {**out, "status": "NO_SETUP_NO_GAP_DOWN"}
    zone = pds_zone(ctx.previous, p)
    if p.pds_open_vs_zone == "BELOW_ZONE" and not ctx.open_price < zone.low:
        return {**out, "status": "NOT_ARMED_OPEN_NOT_BELOW_ZONE"}
    prox = p.zone_proximity_points
    cs = to_candles(ctx.candles)

    def at_zone(c: Candle) -> bool:
        return c.h >= zone.low - prox and c.l <= zone.high + prox
    touched = any(at_zone(c) for c in cs)
    for c in cs:
        if is_red(c) and at_zone(c):
            rg = c.h - c.l
            body = abs(c.c - c.o)
            good, pin = pds_good_red(c), pds_red_pin(c, zone.low)
            return {**out, "status": "ARMED", "zone_low": zone.low, "zone_high": zone.high, "first_red_candle_start": _hm(c.start), "first_red_signal_time_if_chosen": _hm(c.end), "ohlc": f"{c.o}/{c.h}/{c.l}/{c.c}",
                    "body_pct": None if rg <= 0 else round(100 * body / rg, 1), "upper_wick_pct": None if rg <= 0 else round(100 * upper_wick(c) / rg, 1), "lower_wick_pct": None if rg <= 0 else round(100 * lower_wick(c) / rg, 1),
                    "frozen_numeric_verdict": "STRONG(Method 1)" if D52.strong_bearish(c, p) else ("PIN(Method 2)" if D52.bearish_pin(c, p) and c.h >= zone.low else "WEAK(Method 3 path)"),
                    "phase53_verdict": "GOOD_RED(Method 1)" if good else ("RED_PIN(Method 2)" if pin else "WEAK(Method 3 path - source quality rule)")}
    return {**out, "status": "ARMED_NO_RED_CANDLE_AT_ZONE" if touched else "ARMED_NO_ZONE_RETEST"}
