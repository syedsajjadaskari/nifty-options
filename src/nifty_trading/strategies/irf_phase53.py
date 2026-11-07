"""Phase 5.3 IRF: the owner-approved corrections as an opt-in, separately versioned engine (the frozen ``IRFStrategy`` and the Phase 5.2 candidate class are not modified).

Owner decisions implemented (Phase 5.3 brief):

1. FIRST RED CANDLE'S LOW is the support of Method 2A (``support_ref="FIRST_RED_LOW"``; the actual low including the wick, never the body low or the close). The reference candle is the earliest qualifying
   completed red candle of the attempt and is never replaced by a later one. Scope: Method 2A ONLY. Method 2B's reference is a RESISTANCE (the top of the first push; the red candle is the confirming candle, not
   the creator of a level), Method 1 has no support level and Method 3's support is "formed by the preceding candles" (IRF guide); none of them is changed.
   Provisional assumption ``first_red_search_start``: the guide orders the steps breakout -> extension -> pullback low -> red candle -> close below, so the search starts AFTER THE EXTENSION candle (the engine's
   existing bookkeeping, default). The alternative ``AFTER_BREAKOUT`` (the first red candle after the breakout candle, even before the extension) is kept as a selectable variant so its effect can be reported.

2. MINIMUM 28-POINT EMA CLEARANCE (``ema_min_clearance=28.0``, convention ``PROVISIONAL_EMA_RANGE_DISTANCE``): the nearest point of the completed signal candle's high-low range must be at least 28 points from the
   latest causally available EMA(200) of completed five-minute candles (the value that includes the signal candle's own close, which exists when the candle ends = the decision time; never a later value). The 28 is inclusive
   (a distance of exactly 28.0 passes). A candidate that fails is REJECTED and logged in ``self.rejections``. For Method 2 the attempt stays alive after a rejection (a later candle of the same attempt may still qualify);
   Methods 1 and 3 are history-independent per candle, so their rejected candidates are simply removed. The convention is NOT confirmed as the author's meaning; the range distance does not guarantee price space towards
   Target 1 (the diagnostics report where the EMA lies relative to the candle and between entry and Target 1).
   ``ema_scope``: ``ALL_METHODS`` (the clarification is about IRF as a whole; the guide has no EMA text, so no method is excluded) or ``METHOD2_ONLY`` (a selectable variant).

Everything else (extension, the first-red bookkeeping, the entry on the close of the confirming candle, the 13:00 cutoff applied by the base class, stops and targets) is the frozen behaviour.
"""

from __future__ import annotations

import math
from typing import Any

from nifty_trading.strategies.base import SignalRecord, SignalStatus, State
from nifty_trading.strategies.definitions import is_red, recent_resistance
from nifty_trading.strategies.irf import _GLOBAL, _Attempt
from nifty_trading.strategies.irf_candidates import SUPPORT_REFS, IRFFirstRedStrategy

RED_SEARCH_STARTS = ("AFTER_EXTENSION", "AFTER_BREAKOUT")
EMA_SCOPES = ("ALL_METHODS", "METHOD2_ONLY")
EMA_MEASURES = ("RANGE", "CLOSE")  # RANGE = nearest point of the candle's high-low range (the Phase 5.3 convention); CLOSE = |close - EMA| (diagnostic variant)
EPS = 1e-9


def ema_geometry(h: float, l: float, c: float, ema: float) -> dict[str, Any]:
    """Where the EMA lies relative to the candle and the two candidate distances. ``range_clearance`` is 0 when the EMA lies inside the candle's high-low range."""
    if ema > h:
        rel, rng = "EMA_ABOVE_CANDLE", ema - h
    elif ema < l:
        rel, rng = "EMA_BELOW_CANDLE", l - ema
    else:
        rel, rng = "EMA_INSIDE_CANDLE", 0.0
    return {"relation": rel, "range_clearance": rng, "close_distance": abs(c - ema)}


class IRFPhase53Strategy(IRFFirstRedStrategy):
    """IRF with the Phase 5.3 owner-approved corrections (see the module docstring). With the default arguments it equals the frozen engine."""

    def __init__(self, name=None, params=None, proposals=None, trade=None, support_ref: str = "BASELINE_SWING", red_search_start: str = "AFTER_EXTENSION",
                 ema_min_clearance: float | None = None, ema_scope: str = "ALL_METHODS", ema_measure: str = "RANGE"):
        super().__init__(name, params, proposals, trade, support_ref=support_ref)
        if support_ref not in SUPPORT_REFS:
            raise ValueError(support_ref)
        if red_search_start not in RED_SEARCH_STARTS or ema_scope not in EMA_SCOPES or ema_measure not in EMA_MEASURES:
            raise ValueError((red_search_start, ema_scope, ema_measure))
        self.red_search_start = red_search_start
        self.ema_min_clearance = ema_min_clearance
        self.ema_scope = ema_scope
        self.ema_measure = ema_measure
        self.rejections: list[dict[str, Any]] = []  # candidates rejected by the EMA clearance (read and cleared by the runner after each session)

    # ------------------------------------------------------------------ the EMA clearance gate
    def _ema_gate(self, ctx, cs, i: int, method: str) -> tuple[bool, dict[str, Any]]:
        """(passes, info) for the completed candle ``i`` as the confirming candle of ``method``. No EMA value (warm-up) -> the candidate is NOT rejected (unknown is not 'less than 28') and the case is flagged."""
        c = cs[i]
        e = ctx.candles["ema200_5m"].iloc[i]
        if e is None or (isinstance(e, float) and math.isnan(e)):
            return True, {"ema_available": False}
        e = float(e)
        g = ema_geometry(c.h, c.l, c.c, e)
        dist = g["range_clearance"] if self.ema_measure == "RANGE" else g["close_distance"]
        info = {"ema_available": True, "ema200": e, "measure": self.ema_measure, "distance": dist, **g, "method": method, "signal_time": f"{c.end:%H:%M}",
                "candle_ohlc": f"{c.o}/{c.h}/{c.l}/{c.c}", "min_clearance": self.ema_min_clearance}
        return dist >= self.ema_min_clearance - EPS, info

    def _gated_methods(self) -> tuple[str, ...]:
        return ("Method 1", "Method 2A", "Method 2B", "Method 3") if self.ema_scope == "ALL_METHODS" else ("Method 2A", "Method 2B")

    def _scan(self, ctx, cs, gap_before) -> list[SignalRecord]:
        out = super()._scan(ctx, cs, gap_before)
        if self.ema_min_clearance is None:
            return out
        kept: list[SignalRecord] = []
        for r in out:
            if r.signal_status == SignalStatus.CONFIRMED.value and r.method in ("Method 1", "Method 3") and r.method in self._gated_methods():
                i = next((k for k, c in enumerate(cs) if c.end == r.signal_timestamp), None)
                if i is not None:
                    ok, info = self._ema_gate(ctx, cs, i, r.method)
                    if not ok:
                        self.rejections.append({"date": str(ctx.date), **info})
                        continue
                    r.flags.append(f"PHASE53_EMA_{self.ema_measure}_DISTANCE={info.get('distance', 'NA') if info.get('ema_available') else 'EMA_UNAVAILABLE'}")
            kept.append(r)
        return kept

    # ------------------------------------------------------------------ Method 2 (a copy of the Phase 5.2 step with TWO changes: the red-candle search start and the EMA veto)
    def _m2_step(self, ctx, cs, att: _Attempt, i: int, irh: float, irl: float, may_confirm: bool = True):
        c, b = cs[i], att.b
        if may_confirm and att.fsm.state is State.SETUP_DETECTED:
            att.fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "Method 1 window passed; Method 2 path (IRF-M2-004)")
        if self.p.m2_expiry_candles is not None and i - b > self.p.m2_expiry_candles:
            att.fsm.to(State.SETUP_INVALIDATED, c.end, "M2_EXPIRED(proposal)")
            return None, [self._setup_record(ctx, cs, att, "M2_EXPIRED", i)]
        if att.e is None and i > b:
            ext = (c.h > cs[b].h) if self.p.m2_extension_definition == "E1" else (c.c > irh)
            if ext:
                att.e = i
        if att.r is None:
            if self.red_search_start == "AFTER_BREAKOUT":  # variant: the first red candle after the breakout candle, whether or not the extension has happened yet
                if i > b and is_red(c):
                    att.r = i
            elif att.e is not None:  # default / frozen: the first red candle after the extension candle
                first_ok = att.e if self.p.m2_red_may_be_extension_candle else att.e + 1
                if i >= first_ok and is_red(c):
                    att.r = i
        if not may_confirm:
            return att, []
        recs: list[SignalRecord] = []
        proposals = {"irf_support_def": self.p.irf_support_def, "irf_resistance_def": self.p.irf_resistance_def, "m2_extension_definition": self.p.m2_extension_definition,
                     "phase53_support_ref": self.support_ref, "phase53_red_search_start": self.red_search_start, "phase53_ema_min_clearance": self.ema_min_clearance, "phase53_ema_scope": self.ema_scope,
                     "phase53_ema_convention": "PROVISIONAL_EMA_RANGE_DISTANCE" if self.ema_min_clearance is not None else None}
        red_ok = att.r is not None and (att.r <= i if self.p.m2a_break_may_be_red_candle else att.r < i)
        if red_ok and att.e is not None:
            sup = self._support_level(cs, att, b, i)
            if sup is not None and c.c < sup[1]:
                recs.append(("Method 2A", {"recent_support": sup[1], "support_candle_index": sup[0], "support_ref": self.support_ref, "first_red_candle_start": f"{cs[att.r].start:%H:%M}",
                                           "first_red_candle_low": cs[att.r].l},
                             ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
        res = recent_resistance(cs, b, i, self.p)
        if res is not None and is_red(c) and c.c < res[1]:
            j, rlvl = res
            last_push = i if not self.p.m2b_push_must_precede_red_candle else i - 1
            pushed = any(cs[m].h > rlvl for m in range(j + 1, last_push + 1))
            if pushed:
                recs.append(("Method 2B", {"recent_resistance": rlvl, "resistance_candle_index": j}, ["IRF-M2-001", "IRF-M2B-001", "IRF-M2B-002", "IRF-M2B-003"]))
        if not recs:
            return att, []
        flags: list[str] = []
        if self.ema_min_clearance is not None:
            kept = []
            for m, extra, sat in recs:
                if m in self._gated_methods():
                    ok, info = self._ema_gate(ctx, cs, i, m)
                    if not ok:
                        self.rejections.append({"date": str(ctx.date), **info})  # rejected: the attempt stays alive; a later candle of the same attempt may still qualify
                        continue
                    flags = [f"PHASE53_EMA_{self.ema_measure}_DISTANCE={info.get('distance', 'NA') if info.get('ema_available') else 'EMA_UNAVAILABLE'}"]
                kept.append((m, extra, sat))
            recs = kept
            if not recs:
                return att, []
        att.fsm.to(State.SIGNAL_CONFIRMED, c.end, "; ".join(m for m, _, _ in recs) + " trigger on close")
        out = [self._confirmed(ctx, cs, i, m, b, irh, irl, _GLOBAL + sat + ["IRF-M2-005"], att.fsm.trace, list(flags),
                               {**extra, "breakout_close": cs[b].c, "extension_index": att.e, "red_candle_index": att.r}, proposals=proposals)
               for m, extra, sat in recs]
        return None, out
