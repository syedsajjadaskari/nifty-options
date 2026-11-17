"""Independent audit of IRF Method 2A (Phase 6.1): re-derives every Method 2 attempt and its Method 2A signals from RAW five-minute candles built by the Phase 6.0 independent chain (pandas resample, recursive EMA),
without the engine's state machine, the repository's candles or the repository's EMA. Shared by design (and disclosed): the Method 2B resistance helper (``definitions.recent_resistance``, needed only to know when an attempt
ends) and the proposal defaults. Output: the set of (date, signal time, support) for Method 2A confirmations <= 13:00 (and the 28-point gate)."""

from __future__ import annotations

from nifty_trading.strategies.definitions import Candle, recent_resistance
from nifty_trading.strategies.params import DEFAULT_PROPOSALS


def audit_day(c, p=DEFAULT_PROPOSALS, min_clear: float | None = 28.0, cutoff: str = "13:00"):
    """c: DataFrame start/end/open/high/low/close/ema (one session). Returns [(HH:MM, support, reference HH:MM)] for Method 2A confirmations."""
    o, h, lo, cl = (c[k].to_numpy(float) for k in ("open", "high", "low", "close"))
    em = c["ema"].to_numpy(float)
    cs = [Candle(c["start"].iloc[i], c["end"].iloc[i], o[i], h[i], lo[i], cl[i], em[i]) for i in range(len(c))]
    irh, irl = h[0], lo[0]
    out, att = [], None
    inside = lambda x: (irl <= x < irh) or (p.m1_close_below_irl_counts_as_inside and x < irl)  # noqa: E731
    gap = [False] + [c["start"].iloc[k] != c["end"].iloc[k - 1] for k in range(1, len(c))]   # a missing candle invalidates an open attempt (frozen DATA_GAP rule)
    for i in range(1, len(c)):
        if gap[i] and att is not None:
            att = None
        if inside(cl[i]) and cl[i - 1] > irh and i - 1 >= 1 and att is not None and att["b"] == i - 1:
            att = None                                                  # a Method 1 failure on the very next candle makes it Method 1, not Method 2
        if att is not None:
            b = att["b"]
            if att["e"] is None and i > b and h[i] > h[b]:
                att["e"] = i
            if att["r"] is None and att["e"] is not None and i >= att["e"] + 1 and cl[i] < o[i]:
                att["r"] = i                                            # first red candle AFTER the extension candle; never replaced
                continue_flag = True
            else:
                continue_flag = False
            hit_a = False
            if att["r"] is not None and not continue_flag and i > att["r"] and att["e"] is not None:
                hit_a = cl[i] < lo[att["r"]]                            # strict close below the reference candle's wick low
            res = recent_resistance(cs, b, i, p)
            hit_b = False
            if res is not None and cl[i] < o[i] and cl[i] < res[1]:
                j, rl = res
                last_push = i if not p.m2b_push_must_precede_red_candle else i - 1
                hit_b = any(h[m] > rl for m in range(j + 1, last_push + 1))
            kept_a = hit_a
            if hit_a and min_clear is not None:
                e = em[i]
                dist = (e - h[i]) if e > h[i] else ((lo[i] - e) if e < lo[i] else 0.0)
                kept_a = dist >= min_clear - 1e-9
            kept_b = hit_b
            if hit_b and min_clear is not None:
                e = em[i]
                dist = (e - h[i]) if e > h[i] else ((lo[i] - e) if e < lo[i] else 0.0)
                kept_b = dist >= min_clear - 1e-9
            if kept_a and f"{c['end'].iloc[i]:%H:%M}" <= cutoff:
                out.append((f"{c['end'].iloc[i]:%H:%M}", float(lo[att["r"]]), f"{c['start'].iloc[att['r']]:%H:%M}"))
            elif kept_a:
                pass
            if kept_a or kept_b:
                att = None
        if att is None and cl[i] > irh and not gap[i]:
            att = {"b": i, "e": None, "r": None}
    return out


def audit_window(chain: dict, dates, **kw) -> dict:
    return {d: audit_day(chain[d], **kw) for d in dates if d in chain}

