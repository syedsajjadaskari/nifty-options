"""Candle metrics and pattern conventions for the 09:20 candle (independent implementation).

EXPLICIT in the rulebook: colour, the wrong-side wick formula, the 20 % limit (whole-range denominator), the full-body rule (total wick <= 20 % of range) and the pattern names.
PROVISIONAL (not defined by the rulebook; configurable and labelled): hammer / shooting-star proportions and the engulfing reference candle at 09:20.
"""

from __future__ import annotations

from nifty_trading.research.orb_v2.config import EPS, OrbV2Config

BUY, SELL = "BUY", "SELL"


def metrics(o: float, h: float, l: float, c: float) -> dict:
    rng = h - l
    zero = rng <= 1e-9
    body = abs(c - o)
    upper = h - max(o, c)
    lower = min(o, c) - l
    colour = "GREEN" if c > o else ("RED" if c < o else "DOJI")

    def pct(x: float) -> float | None:
        return None if zero else x / rng

    return {"open": o, "high": h, "low": l, "close": c, "range": rng, "zero_range": zero, "body": body, "upper_wick": upper, "lower_wick": lower, "colour": colour,
            "body_pct": pct(body), "upper_pct": pct(upper), "lower_pct": pct(lower), "close_position_pct": pct(c - l), "body_low": min(o, c), "body_high": max(o, c)}


def bad_wick_pct(m: dict, direction: str) -> float | None:
    """BUY: upper wick / range; SELL: lower wick / range (whole candle range as denominator)."""
    return m["upper_pct"] if direction == BUY else m["lower_pct"]


def wick_ok(m: dict, direction: str, cfg: OrbV2Config) -> bool:
    p = bad_wick_pct(m, direction)
    return p is not None and p <= cfg.max_bad_wick_pct + EPS


def colour_ok(m: dict, direction: str) -> bool:
    return m["colour"] == ("GREEN" if direction == BUY else "RED")


def full_body(m: dict, direction: str, cfg: OrbV2Config) -> bool:
    if m["zero_range"] or not colour_ok(m, direction):
        return False
    return (m["upper_pct"] + m["lower_pct"]) <= cfg.full_body_max_total_wick_pct + EPS


def pin_bar(m: dict, direction: str, cfg: OrbV2Config) -> bool:
    """Hammer (BUY) / shooting star (SELL): the long wick is on the GOOD side (>= k x body), the opposite wick is little or none. PROVISIONAL proportions."""
    if m["zero_range"] or not colour_ok(m, direction) or m["body"] <= 0:
        return False
    long_w, opp_pct = (m["lower_wick"], m["upper_pct"]) if direction == BUY else (m["upper_wick"], m["lower_pct"])
    return long_w >= cfg.hammer_min_pin_wick_to_body * m["body"] - EPS and opp_pct <= cfg.hammer_max_opposite_wick_pct + EPS


def engulfing(m: dict, ref: dict | None, direction: str, cfg: OrbV2Config) -> bool | None:
    """True/False, or None when the pattern cannot be evaluated (no reference candle under the configured convention)."""
    if ref is None:
        return None
    if m["zero_range"] or not colour_ok(m, direction):
        return False
    rm = metrics(ref["open"], ref["high"], ref["low"], ref["close"])
    if rm["body"] <= 0:
        return False  # a doji body is engulfed trivially but carries no information: not counted
    if cfg.engulf_requires_opposite_colour and rm["colour"] == m["colour"]:
        return False
    return m["body_low"] <= rm["body_low"] + 1e-9 and m["body_high"] >= rm["body_high"] - 1e-9 and m["body"] > rm["body"]


def evaluate(m: dict, ref: dict | None, direction: str, cfg: OrbV2Config) -> dict:
    eng = engulfing(m, ref if cfg.engulf_reference != "NONE" else None, direction, cfg)
    pats = {"pin_bar": pin_bar(m, direction, cfg), "engulfing": eng, "full_body": full_body(m, direction, cfg)}
    names = [k for k, v in pats.items() if v]
    return {"patterns": pats, "matched": names, "any": bool(names)}
