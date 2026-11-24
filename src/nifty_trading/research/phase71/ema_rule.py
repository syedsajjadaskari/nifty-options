"""Shared EMA(200) research component for the author's clarification 'the 27-point gap near the 200 EMA is common for all the strategies'.

ONE geometry function evaluates EVERY interpretation for EVERY strategy; nothing is duplicated per strategy. The meaning of the sentence is NOT established by any source (see the audit),
so each interpretation is a separately labelled research reading and none is active by default (EMA-0). Measurements use only the completed candle's own EMA(200) value (the 5-minute EMA of the
frozen contexts, ``ema200_5m``, causal: it includes the candle's own close and nothing later).

Interpretations (N = threshold, 27 or 28):
  MIN_CLOSE    A/D  |close - EMA| >= N            (minimum close-to-EMA distance)                       -> EMA-1
  MIN_RANGE    C    nearest point of the candle's high-low range to the EMA >= N (0 if EMA inside it)   -> EMA-2 (N=27) / EMA-4 (N=28, the Phase 5.3 historical convention)
  MAX_CLOSE    B    |close - EMA| <= N            (maximum close-to-EMA proximity)                       -> EMA-3
  TARGET_SIDE  E    the EMA must not lie in the trade's path within N points of the entry reference
                    (SHORT: fail when 0 <= entry - EMA < N; LONG: fail when 0 <= EMA - entry < N). Evidence: the handwritten pages AC13/AC18 ('Tgt 1 is not above EMA ... tgt 1 is less than 27'); N=27 equals Target 1.  -> EMA-5
Interpretation D (the absolute close-to-EMA difference 'meeting 27') is the same quantity as A/B and is therefore reported once under MIN_CLOSE / MAX_CLOSE, not as an independent reading.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

EPS = 1e-9
INTERPS = ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE")
CONFIG_OF = {"EMA-0": None, "EMA-1": ("MIN_CLOSE", 27.0), "EMA-2": ("MIN_RANGE", 27.0), "EMA-3": ("MAX_CLOSE", 27.0), "EMA-4": ("MIN_RANGE", 28.0), "EMA-5": ("TARGET_SIDE", 27.0)}
LABEL = {"EMA-0": "no universal EMA rule (baseline)", "EMA-1": "minimum 27-point |close - EMA|", "EMA-2": "minimum 27-point candle-range clearance", "EMA-3": "maximum 27-point |close - EMA| proximity",
         "EMA-4": "28-point candle-range clearance (Phase 5.3 historical convention, comparator)", "EMA-5": "target-side: EMA not within 27 points in the trade's path (handwritten AC13/AC18 reading)"}


def geometry(direction: str, o: float, h: float, l: float, c: float, ema: float | None, entry: float | None = None, t1: float = 27.0) -> dict:  # noqa: E741
    """All EMA measurements for one candle / signal. ``entry`` defaults to the candle close (the rulebooks' entry-reference convention)."""
    entry = c if entry is None else entry
    if ema is None or (isinstance(ema, float) and math.isnan(ema)):
        return {"ema_available": False}
    if ema > h:
        rel, rng = "EMA_ABOVE_CANDLE", ema - h
    elif ema < l:
        rel, rng = "EMA_BELOW_CANDLE", l - ema
    else:
        rel, rng = "EMA_INSIDE_CANDLE", 0.0
    short = direction == "SHORT"
    room = (entry - ema) if short else (ema - entry)            # >0: the EMA lies in the trade's path (below a short / above a long)
    return {"ema_available": True, "ema": ema, "open": o, "high": h, "low": l, "close": c, "close_minus_ema": c - ema, "abs_close_dist": abs(c - ema), "range_clearance": rng, "relation": rel,
            "candle_touches_or_crosses_ema": rel == "EMA_INSIDE_CANDLE", "entry_ref": entry, "entry_minus_ema": entry - ema, "path_room_to_ema": room if room >= 0 else None,
            "ema_between_entry_and_t1": 0 <= room <= t1 + EPS}


def evaluate(interp: str, n: float, g: dict) -> tuple[str, str]:
    """(PASS | FAIL | UNAVAILABLE, reason) of one interpretation at threshold n for a ``geometry`` dict."""
    if not g.get("ema_available"):
        return "UNAVAILABLE", "EMA(200) not available (warm-up): unknown is never treated as a failure"
    if interp == "MIN_CLOSE":
        ok = g["abs_close_dist"] >= n - EPS
        return ("PASS" if ok else "FAIL"), f"|close-EMA| {g['abs_close_dist']:.2f} {'>=' if ok else '<'} {n:g}"
    if interp == "MIN_RANGE":
        ok = g["range_clearance"] >= n - EPS
        return ("PASS" if ok else "FAIL"), f"range clearance {g['range_clearance']:.2f} ({g['relation']}) {'>=' if ok else '<'} {n:g}"
    if interp == "MAX_CLOSE":
        ok = g["abs_close_dist"] <= n + EPS
        return ("PASS" if ok else "FAIL"), f"|close-EMA| {g['abs_close_dist']:.2f} {'<=' if ok else '>'} {n:g}"
    if interp == "TARGET_SIDE":
        room = g["path_room_to_ema"]
        bad = room is not None and room < n - EPS
        return ("FAIL" if bad else "PASS"), ("EMA in the trade's path only %.2f points from the entry reference (< %g)" % (room, n) if bad else "EMA not within %g points in the trade's path" % n)
    raise ValueError(interp)


@dataclass
class EmaGateEngine:
    """Opt-in wrapper (never active by default): invalidates CONFIRMED records of ANY engine whose confirming candle fails the chosen interpretation. Same limitation as the Phase 6.5 strength gate
    (a post-hoc filter on what the engine emitted); the IRF V3 adapter emits every completed cycle, so a rejected IRF cycle leaves later cycles available (documented inference, as in Phase 5.3)."""
    inner: object
    config: str                        # EMA-1 .. EMA-5 (always measured at the CONFIRMING candle; entry reference = its close)

    def __post_init__(self):
        self.interp, self.n = CONFIG_OF[self.config]
        self.STRATEGY = self.inner.STRATEGY
        self.log: list[dict] = []

    def __getattr__(self, name):
        if name == "inner":
            raise AttributeError(name)
        return getattr(self.inner, name)

    def evaluate_session(self, ctx):
        recs = self.inner.evaluate_session(ctx)
        cand = ctx.candles.set_index("bar_start")
        for r in recs:
            if r.signal_status != "CONFIRMED" or r.signal_candle_start not in cand.index:
                continue
            row = cand.loc[r.signal_candle_start]
            g = geometry(r.direction, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), float(row["ema200_5m"]) if row["ema200_5m"] == row["ema200_5m"] else None)
            res, why = evaluate(self.interp, self.n, g)
            self.log.append({"date": str(r.signal_date), "time": f"{r.signal_timestamp:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction, "config": self.config,
                             "result": res, "why": why, **{k: g.get(k) for k in ("ema", "close", "abs_close_dist", "range_clearance", "relation", "entry_minus_ema")}})
            if res == "FAIL":
                r.signal_status = "INVALIDATED"
                r.invalidation_reason = f"EMA_RULE_{self.config}: {why}"
        return recs
