"""Phase 6.5 research helpers (signal level, independent of the portfolio controller): candle strength metrics, the two newer IRF methods from the author's rulebooks (detectors only), and the independent PDR
first-eligible-candle audit. Nothing here is wired into a live or paper configuration."""

from __future__ import annotations

from nifty_trading.strategies.definitions import Candle

EPS = 1e-9


def candle_metrics(o: float, h: float, l: float, c: float) -> dict:  # noqa: E741
    """body_percentage = |close - open| / (high - low) * 100. A zero-range candle has NO defined percentages (None) and is flagged explicitly; it is never silently treated as 0 or 100."""
    rng = h - l
    zero = rng <= EPS
    colour = "GREEN" if c > o else ("RED" if c < o else "DOJI")
    body, up, lo_ = abs(c - o), h - max(o, c), min(o, c) - l
    pct = (lambda x: None if zero else 100.0 * x / rng)  # noqa: E731
    return {"range": rng, "zero_range": zero, "colour": colour, "body_pct": pct(body), "upper_wick_pct": pct(up), "lower_wick_pct": pct(lo_), "close_location_pct": pct(c - l)}


def geometric_pattern(m: dict, direction: str) -> str:
    """DIAGNOSTIC geometric label of a confirming candle (not a source rule): STRONG_BODY (>= 60% body), HAMMER_LIKE / SHOOTING_STAR_LIKE (the long wick dominates body and the other wick), DOJI_OR_SMALL, ZERO_RANGE."""
    if m["zero_range"]:
        return "ZERO_RANGE"
    b, u, lw = m["body_pct"], m["upper_wick_pct"], m["lower_wick_pct"]
    if lw > b and lw > u:
        return "HAMMER_LIKE (long lower wick)"
    if u > b and u > lw:
        return "SHOOTING_STAR_LIKE (long upper wick)"
    return "STRONG_BODY" if b >= 60.0 else "MODERATE_BODY"


# --------------------------------------------------------------------------------------------------------------- the two newer IRF methods (author rulebooks, Nov 2026)
def _hhmm(c: Candle) -> str:
    return f"{c.end:%H:%M}"


def new_irf_method1(cs: list[Candle], cutoff: str = "13:00") -> dict | None:
    """IRF Method 1 'High Breakout Failure' (IRF_Inverse_Retest_Failure_Rulebook.pdf): level = high of the 09:15 candle (wick included); a later candle CLOSES above it (green or red); the FIRST later candle that CLOSES back below
    it - immediately or many candles later - is the failure; SHORT at that close; one trade per day; no entry after 13:00. A close exactly on the level is ignored (TO CONFIRM). A missing candle resets an open breakout (frozen DATA_GAP rule)."""
    if len(cs) < 3:
        return None
    level, broke = cs[0].h, None
    for i in range(1, len(cs)):
        if cs[i].start != cs[i - 1].end:
            broke = None
        c = cs[i]
        if broke is None:
            if c.c > level + EPS:
                broke = i
        elif c.c < level - EPS:
            return {"method": "NEW-M1", "index": i, "time": _hhmm(c), "level_a": level, "breakout_time": _hhmm(cs[broke]), "entry_reference": c.c, "within_cutoff": _hhmm(c) <= cutoff}
    return None


def new_irf_method2(cs: list[Candle], cutoff: str = "13:00", breakout_candle_may_be_first_red: bool = False) -> dict | None:
    """IRF Method 2 'First Red Candle Resistance Failure' (IRF_Method2_First_Red_Candle_Rulebook.pdf): Level A = high of the 09:15 candle; a candle closes above A (rally breakout, any colour); Level B = TOP OF THE BODY (the open) of the
    FIRST RED candle of the rally - a red candle that forms before any close above A is ignored, later red candles never replace it; a LATER candle closes above B (second breakout, no entry); a still later candle CLOSES back below B =
    failure; SHORT at that close; one trade per day; no entry after 13:00. Convention (TO CONFIRM in the rulebook): the breakout candle itself is not 'in the rally' unless ``breakout_candle_may_be_first_red``."""
    if len(cs) < 4:
        return None
    a = cs[0].h
    b = r = lb = second = None
    for i in range(1, len(cs)):
        if cs[i].start != cs[i - 1].end:
            b = r = lb = second = None
        c = cs[i]
        if b is None:
            if c.c > a + EPS:
                b = i
                if breakout_candle_may_be_first_red and c.c < c.o:
                    r, lb = i, c.o
            continue
        if r is None:
            if c.c < c.o:
                r, lb = i, c.o                       # top of the body of a red candle = its open; the wick is ignored
            continue
        if second is None:
            if c.c > lb + EPS:
                second = i
            continue
        if c.c < lb - EPS:
            return {"method": "NEW-M2", "index": i, "time": _hhmm(c), "level_a": a, "level_b": lb, "breakout_time": _hhmm(cs[b]), "first_red_time": _hhmm(cs[r]), "second_breakout_time": _hhmm(cs[second]),
                    "entry_reference": c.c, "within_cutoff": _hhmm(c) <= cutoff}
    return None


# --------------------------------------------------------------------------------------------------------------- independent PDR first-eligible audit
def pdr_cycle_audit(cs: list[Candle], floor: float, ceiling: float, retest_start: str, engine_start: str | None, end_start: str | None = None, prox: float = 0.0) -> dict:
    """Re-derives, from raw candles and the engine's zone, the candidates of ONE PDR setup cycle that began with the retest candle ``retest_start``: first green after the retest, first green closing strictly above the ceiling,
    first fully eligible confirmation (green OR lower-price rejection, AND a close strictly above the ceiling), the engine's selected candle and the next eligible one."""
    idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
    j = idx.get(retest_start)
    if j is None:
        return {"error": "retest candle not found"}
    stop = idx.get(end_start, len(cs)) if end_start else len(cs)

    def feats(c: Candle):
        body = abs(c.c - c.o)
        uw, lw = c.h - max(c.o, c.c), min(c.o, c.c) - c.l
        green = c.c > c.o
        rej = lw > body and lw > uw and c.l <= ceiling + prox
        return green, rej, c.c > ceiling

    first_green = first_green_above = first_elig = next_elig = None
    elig_idx = []
    for k in range(j + 1, stop):
        g, rej, above = feats(cs[k])
        if g and first_green is None:
            first_green = k
        if g and above and first_green_above is None:
            first_green_above = k
        if (g or rej) and above:
            elig_idx.append(k)
            if first_elig is None:
                first_elig = k
    sel = idx.get(engine_start) if engine_start else None
    if sel is not None:
        later = [k for k in elig_idx if k > sel]
        next_elig = later[0] if later else None
    g0, rej0, above0 = feats(cs[j])
    t = lambda k: None if k is None else f"{cs[k].start:%H:%M}"  # noqa: E731
    out = {"retest": retest_start, "first_green_after_retest": t(first_green), "first_green_closing_above_ceiling": t(first_green_above), "first_fully_eligible": t(first_elig), "engine_selected": engine_start,
           "next_eligible_after_engine": t(next_elig), "retest_candle_green": g0, "retest_candle_close_above_ceiling": above0, "retest_candle_would_qualify": bool((g0 or rej0) and above0)}
    if sel is None:
        out["classification"] = "NO_CONFIRMATION_IN_CYCLE" if first_elig is None else "DEFECT_ENGINE_MISSED_AN_ELIGIBLE_CANDLE"
    elif first_elig == sel:
        out["classification"] = "ENGINE_EQUALS_FIRST_ELIGIBLE" + (" (an earlier green candle existed but failed the strict close-above-ceiling rule)" if first_green is not None and first_green < sel else "")
        if first_green is not None and first_green < sel:
            out["earlier_green_failed_because"] = "closed at or below the zone ceiling" if cs[first_green].c <= ceiling else "other"
    else:
        out["classification"] = "DEFECT_ENGINE_NOT_FIRST_ELIGIBLE" if (first_elig is None or sel > first_elig) else "ENGINE_EARLIER_THAN_AUDIT"
    if out["retest_candle_would_qualify"] and sel is not None:
        out["convention_note"] = "the retest candle itself would qualify; the engine excludes it by the preserved (unresolved) retest-then-confirmation sequencing convention"
    return out
