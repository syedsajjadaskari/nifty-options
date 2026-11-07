"""Phase 5.1 diagnostics: objective MEASUREMENTS on the historical candles that test what the author's handwritten remarks say. Nothing here is a strategy engine, nothing changes a rule, and no profit is computed
(the brief forbids comparing candidate rules by profitability): every function returns times, prices and candle geometry only.

Candle convention (unchanged from the engine): five-minute candles labelled by their START, complete at their end; a signal is usable at the END of the confirming candle; the engine fills at the open of the next
one-minute bar. ``first_red_reading`` and the other readings below are MY FORMALISATIONS of the author's wording, offered as candidate rules; each reading's alternatives are computed side by side so that the ambiguity
of the wording is visible rather than hidden.
"""

from __future__ import annotations

EMA_SPACE_POINTS = 27.0  # the author's number in AC13 / AC18 ('less than 27'); equals the target-1 distance of the frozen configuration
BODY_STRONG_PCT = 60.0  # the author's '60+' in AC01 (also the engine's MODERATE 'strong candle' body share)
CUTOFF = "13:00"


def geometry(c: dict) -> dict:
    return {"colour": c["colour"], "body_pct": c["body_pct"], "upper_wick_pct": c["upper_wick_pct"], "lower_wick_pct": c["lower_wick_pct"]}


def index_by_end(candles: list[dict]) -> dict[str, int]:
    return {c["end"]: i for i, c in enumerate(candles)}


def irf_trade_measures(candles: list[dict], signal_time: str, direction: str = "SHORT") -> dict:
    """Measurements on the signal (confirming) candle of an IRF short: its geometry, the EMA(200, 5-minute) space below the entry, and its position against the session low."""
    idx = index_by_end(candles).get(signal_time)
    if idx is None:
        return {"error": f"no five-minute candle ends at {signal_time}"}
    c = candles[idx]
    entry = c["c"]
    ema = c["ema200"]
    out = {"signal_candle_start": c["start"], **geometry(c), "signal_close": entry, "ema200": ema}
    if ema is not None:
        space = entry - ema
        out.update({"entry_minus_ema": round(space, 2), "ema_below_entry": space > 0, "ema_within_27_below_entry": 0 < space < EMA_SPACE_POINTS, "ema_between_entry_and_target1": entry - EMA_SPACE_POINTS < ema < entry,
                    "close_below_ema": space < 0})
    out.update({"session_low_before_candle": c["session_low_before_this_candle"], "close_below_prior_session_low": c["close_below_prior_session_low"],
                "candle_low_at_or_below_prior_session_low": c["session_low_before_this_candle"] is not None and c["l"] <= c["session_low_before_this_candle"],
                "points_above_prior_session_low": None if c["session_low_before_this_candle"] is None else round(c["c"] - c["session_low_before_this_candle"], 2)})
    out["body_pct_below_60"] = c["body_pct"] is not None and c["body_pct"] < BODY_STRONG_PCT
    out["body_pct_below_50"] = c["body_pct"] is not None and c["body_pct"] < 50.0
    return out


def first_red_reading(candles: list[dict], outside: str = "FULLY_ABOVE", body_min: float = BODY_STRONG_PCT) -> dict | None:
    """The author's 'first red candle' wording (AC03, AC08, AC09, AC20, AC26, AC34, AC01), as a candidate rule for IRF Method 2 (short):
      * IRH / IRL = high / low of the 09:15 candle; breakout candle b = first later candle that CLOSES above IRH;
      * r = the FIRST red candle after b that is 'outside the 5-minute range' - ``outside`` = FULLY_ABOVE (its low is above IRH) or CLOSE_ABOVE (only its close is above IRH);
      * support S = low(r), resistance R = high(r);
      * entry = the first later candle that is RED with body >= ``body_min`` percent ('60+ body candle in the entry side') and either (support break) closes below S, or (resistance break) closes below R after an
        earlier candle traded above R ('red candle closes back below resistance'); 'whichever happens first'.
    Returns the reading, or None when the sequence does not occur before the 13:00 cutoff. ``body_min`` = 0 removes the body condition."""
    if len(candles) < 3:
        return None
    irh = candles[0]["h"]
    b = next((i for i in range(1, len(candles)) if candles[i]["c"] > irh), None)
    if b is None:
        return None
    ok = (lambda c: c["colour"] == "R" and c["l"] > irh) if outside == "FULLY_ABOVE" else (lambda c: c["colour"] == "R" and c["c"] > irh)
    r = next((i for i in range(b + 1, len(candles)) if ok(candles[i])), None)
    if r is None:
        return None
    s_lvl, r_lvl = candles[r]["l"], candles[r]["h"]
    traded_above = False
    for k in range(r + 1, len(candles)):
        c = candles[k]
        if c["end"] > CUTOFF:
            return {"breakout_candle": candles[b]["start"], "first_red_candle": candles[r]["start"], "support": s_lvl, "resistance": r_lvl, "entry": None, "note": "no qualifying entry before the 13:00 cutoff"}
        strong = c["colour"] == "R" and (c["body_pct"] or 0) >= body_min
        if strong and c["c"] < s_lvl:
            return {"breakout_candle": candles[b]["start"], "first_red_candle": candles[r]["start"], "support": s_lvl, "resistance": r_lvl, "entry": {"signal_time": c["end"], "close": c["c"], "trigger": "SUPPORT_BREAK", "body_pct": c["body_pct"]}}
        if strong and traded_above and c["c"] < r_lvl:
            return {"breakout_candle": candles[b]["start"], "first_red_candle": candles[r]["start"], "support": s_lvl, "resistance": r_lvl, "entry": {"signal_time": c["end"], "close": c["c"], "trigger": "RESISTANCE_BREAK", "body_pct": c["body_pct"]}}
        if c["h"] > r_lvl:
            traded_above = True
    return {"breakout_candle": candles[b]["start"], "first_red_candle": candles[r]["start"], "support": s_lvl, "resistance": r_lvl, "entry": None, "note": "no qualifying entry in the session"}


def readings(candles: list[dict]) -> dict:
    return {f"{o}|body>={bm:.0f}": first_red_reading(candles, o, bm) for o in ("FULLY_ABOVE", "CLOSE_ABOVE") for bm in (BODY_STRONG_PCT, 0.0)}


def first_green_after_zone(candles: list[dict], zone_lo: float, zone_hi: float, start_after: str = "09:15") -> dict | None:
    """PDR (long) wording 'enter in 1st green candle' (AC10, AC11, AC29, AC40, AC02): after the first candle that interacts with the zone (its low <= the zone ceiling), the FIRST later candle that is green and closes
    above the zone ceiling. Returns that candle's geometry; the engine's own confirmation (GOOD_GREEN_BODY / lower-price rejection, thresholds provisional) is compared with it in the day report."""
    inter = next((i for i, c in enumerate(candles) if c["end"] > start_after and c["l"] <= zone_hi), None)
    if inter is None:
        return None
    for k in range(inter, len(candles)):
        c = candles[k]
        if c["colour"] == "G" and c["c"] > zone_hi:
            return {"interaction_candle": candles[inter]["start"], "first_green_close_above_ceiling": {"candle_start": c["start"], "signal_time": c["end"], **geometry(c), "close": c["c"], "points_above_ceiling": round(c["c"] - zone_hi, 2),
                                                                                                    "low_below_zone_floor": c["l"] < zone_lo}}
    return {"interaction_candle": candles[inter]["start"], "first_green_close_above_ceiling": None}
