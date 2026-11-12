"""ORB V2 signal engine: one decision per session at 09:20 on the completed 09:15-09:20 candle. Every condition is evaluated and EVERY failed condition is recorded (not only the first).

Condition order follows the rulebook's decision flow (gap, EMA direction, previous-day level, candle colour + pattern, wrong-side wick, zero range) but evaluation never short-circuits.
Nothing here reads a price after 09:20 or any intraday candle other than the opening candle.
"""

from __future__ import annotations

from nifty_trading.research.orb_v2 import gap_filter as G
from nifty_trading.research.orb_v2 import levels as L
from nifty_trading.research.orb_v2 import patterns as P
from nifty_trading.research.orb_v2 import zones as Z
from nifty_trading.research.orb_v2.config import OrbV2Config
from nifty_trading.research.orb_v2.models import Decision, SessionData

FAIL_CODES = ("GAP_TOO_LARGE", "EMA_EQUAL", "LEVEL_NOT_BROKEN", "COLOUR_MISMATCH", "NO_PATTERN", "WRONG_SIDE_WICK", "ZERO_RANGE_CANDLE")


def ema_scenario(sd: SessionData, direction: str) -> str:
    """A: already beyond the EMA at the open (previous session on the same side); B: candle starts on the wrong side (at/below for BUY) and closes beyond (intrabar cross);
    C: overnight gap jumps across the EMA (previous session on the other side, the open already beyond). All three are eligible under the close-based filter (rulebook)."""
    o = sd.opening["open"]
    if direction == "BUY":
        open_beyond, prev_beyond = o > sd.ema_prev, sd.prev_last_5m_close > sd.prev_ema_last
    else:
        open_beyond, prev_beyond = o < sd.ema_prev, sd.prev_last_5m_close < sd.prev_ema_last
    if open_beyond and prev_beyond:
        return "A_ALREADY_BEYOND_EMA"
    if open_beyond:
        return "C_OVERNIGHT_GAP_CROSSES_EMA"
    return "B_INTRABAR_CROSS_OF_EMA"


def evaluate_session(sd: SessionData, cfg: OrbV2Config) -> Decision:
    oc = sd.opening
    m = P.metrics(oc["open"], oc["high"], oc["low"], oc["close"])
    gap = G.gap_points(sd.open_1m, sd.prev_close)
    failed: list[str] = []
    det: dict = {"signal_candle_start": oc["start"], "signal_confirmed_at": oc["confirmed_at"], "open_1m": sd.open_1m, "candle_open": oc["open"], "candle_high": oc["high"], "candle_low": oc["low"],
                 "candle_close": oc["close"], "colour": m["colour"], "body_pct": m["body_pct"], "upper_wick_pct": m["upper_pct"], "lower_wick_pct": m["lower_pct"], "range_points": m["range"],
                 "prev_date": sd.prev_date, "prev_high": sd.prev_high, "prev_low": sd.prev_low, "prev_close": sd.prev_close, "prev_close_source": sd.prev_close_source,
                 "gap_points": gap, "ema_now": sd.ema_now, "ema_prev": sd.ema_prev, "close_minus_ema": oc["close"] - sd.ema_now, "data_flags": ";".join(sd.flags)}
    det["gap_ok"] = G.gap_ok(gap, cfg.max_gap_points)
    if not det["gap_ok"]:
        failed.append("GAP_TOO_LARGE")
    diff = oc["close"] - sd.ema_now
    direction = "BUY" if diff > 1e-9 else ("SELL" if diff < -1e-9 else None)
    det["direction_by_ema"] = direction or ""
    if direction is None:
        failed.append("EMA_EQUAL")
    if m["zero_range"]:
        failed.append("ZERO_RANGE_CANDLE")
    if direction is None:
        det.update({"ema_scenario": "", "levels_total": "", "levels_broken_n": "", "major_broken": "", "inner_broken_n": "", "qualifying_category": "", "primary_level": "", "primary_level_kind": "",
                    "gap_beyond_prev_range": "", "colour_ok": "", "patterns_matched": "", "engulf_evaluable": "", "wrong_side_wick_pct": "", "wick_ok": "", "pattern_ok": "", "level_ok": ""})
        return Decision(sd.date, cfg.config_id, True, "", "", failed, det)
    det["ema_scenario"] = ema_scenario(sd, direction)
    lv = L.all_levels(sd.prev_candles, cfg)
    side = "RESISTANCE" if direction == "BUY" else "SUPPORT"
    brk = [x for x in lv if x.side == side and Z.broken(x, direction, oc["open"], oc["close"], cfg)]
    det["levels_total"] = sum(1 for x in lv if x.side == side)
    det["levels_broken_n"] = len(brk)
    det["major_broken"] = any(x.kind == "MAJOR" for x in brk)
    det["inner_broken_n"] = sum(1 for x in brk if x.kind == "INNER")
    det["qualifying_category"] = "" if not brk else ("MAJOR_AND_INNER" if det["major_broken"] and det["inner_broken_n"] else ("MAJOR_ONLY" if det["major_broken"] else "INNER_ONLY"))
    if brk:
        prim = max(brk, key=lambda x: x.ceiling) if direction == "BUY" else min(brk, key=lambda x: x.floor)  # the broken level nearest to the close
        det["primary_level"] = Z.describe(prim)
        det["primary_level_kind"] = prim.kind
        det["primary_crossed_from_old_side"] = (oc["open"] <= prim.ceiling) if direction == "BUY" else (oc["open"] >= prim.floor)
        det["broken_levels"] = " | ".join(Z.describe(x) for x in brk)
    else:
        det["primary_level"] = det["primary_level_kind"] = det["broken_levels"] = ""
        det["primary_crossed_from_old_side"] = ""
    det["gap_beyond_prev_range"] = (sd.open_1m > sd.prev_high) if direction == "BUY" else (sd.open_1m < sd.prev_low)
    det["level_ok"] = bool(brk)
    if not brk:
        failed.append("LEVEL_NOT_BROKEN")
    det["colour_ok"] = P.colour_ok(m, direction)
    if not det["colour_ok"]:
        failed.append("COLOUR_MISMATCH")
    ref = sd.prev_engulf_candle if cfg.engulf_reference == "PREV_SESSION_LAST_CONTINUOUS_5M" else None
    pe = P.evaluate(m, ref, direction, cfg)
    det["patterns_matched"] = "+".join(pe["matched"])
    det["pin_bar"], det["engulfing"], det["full_body"] = pe["patterns"]["pin_bar"], pe["patterns"]["engulfing"], pe["patterns"]["full_body"]
    det["engulf_evaluable"] = ref is not None
    det["pattern_ok"] = pe["any"]
    if not pe["any"]:
        failed.append("NO_PATTERN")
    w = P.bad_wick_pct(m, direction)
    det["wrong_side_wick_pct"] = w
    det["wick_ok"] = (not m["zero_range"]) and P.wick_ok(m, direction, cfg)
    if not m["zero_range"] and not det["wick_ok"]:
        failed.append("WRONG_SIDE_WICK")
    sig = direction if not failed else ""
    return Decision(sd.date, cfg.config_id, True, "", sig, failed, det)
