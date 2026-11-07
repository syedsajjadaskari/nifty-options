"""Phase 5.3 PDR and PDS: earliest eligible confirmation, without numeric strength thresholds (opt-in engines; the frozen engines are not modified).

Owner decision: PDR and PDS must activate on the first eligible confirmation candle; a numerically 'too weak' first candle must not delay the entry. Everything else of the setup is preserved.

PDR (``PDRFirstEligibleStrategy``). Preserved: the previous-day body-based zone, the open strictly above the zone ceiling, the retest (the first candle whose range meets the zone; the confirmation must come AFTER it
- the retest/confirmation sequencing is an unresolved convention, so the retest candle may NOT confirm), the close strictly above the zone ceiling, chronological processing, one signal per setup cycle, the 13:00 cutoff.
Replaced: the numeric pattern thresholds (body 60% / wick 20% / 2x / 30% / 10% / 60%, all PROPOSED research values) by the SMALLEST transparent conventions, marked ``PROVISIONAL_PDR_MINIMAL_CONFIRMATION``:
  GOOD_GREEN_BODY             a green candle (close > open), any size. This is the guide's own wording: "After the zone has been tested, wait for a green candle and take the long entry on that confirmation"
                              (PDR guide s.4.3), and the author's note that no fixed percentage or wick size is required.
  LOWER_PRICE_REJECTION       (covers the hammer) a candle of any colour whose lower wick is strictly larger than both its body and its upper wick and whose low reached the zone (low <= ceiling + proximity).
A candidate additionally needs ``close > zone ceiling`` (strictly). Not every green candle is valid: one that closes at or below the ceiling, or that is the retest candle, or that comes before the retest, is not.

PDS (``PDSFirstEligibleStrategy``). Preserved: the previous-day support zone, gap-down open below the zone, the retest, the SEQUENCE of the guide (Methods 1 and 2 apply to the FIRST red candle at the zone; "Quality rule:
do not take a weak red candle ... if it is not [good], wait for a small support to form and break (Method 3)"), Method 3's mandatory small-support break, the 13:00 cutoff. A weak first red candle is NOT silently accepted:
that would override a source-defined rule, so the author's 'first candle entry' on a weak candle is reported for approval instead.
Replaced: the numeric thresholds of 'good red candle' / 'pin bar' (PROPOSED) by structural dominance tests that contain no percentage but still act as an implicit threshold (a body larger than each wick means a body above roughly a third of the range), marked ``PROVISIONAL_PDS_MINIMAL_QUALITY``:
  Method 1  a red candle whose body is strictly larger than each of its wicks (the body dominates the candle).
  Method 2  a red candle whose upper wick is strictly larger than its body and its lower wick (higher-price rejection) and whose high reached the zone.
Anything else is a weak candle: Method 3 applies. The two tests are mutually exclusive, so no candle can confirm two methods.
"""

from __future__ import annotations

from typing import Any

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import (
    Direction,
    SetupFSM,
    SignalRecord,
    SignalStatus,
    State,
)
from nifty_trading.strategies.definitions import (
    Candle,
    gap_info,
    green_refs,
    is_red,
    lower_wick,
    pds_zone,
    prev_candles,
    to_candles,
    upper_wick,
)
from nifty_trading.strategies.pdr_body import PDRBodyStrategy, build_zone
from nifty_trading.strategies.pds import PDSStrategy


# ============================================================================================================== PDR
def pdr_minimal_confirmation(c: Candle, zone_floor: float, zone_ceiling: float, proximity: float = 0.0) -> dict[str, Any]:
    """The Phase 5.3 PDR confirmation test (see the module docstring). ``qualifies`` = at least one pattern AND close strictly above the zone ceiling."""
    body = abs(c.c - c.o)
    uw, lw = upper_wick(c), lower_wick(c)
    green = c.c > c.o
    rejection = lw > body and lw > uw and c.l <= zone_ceiling + proximity
    passed = (["GOOD_GREEN_BODY"] if green else []) + (["LOWER_PRICE_REJECTION"] if rejection else [])
    close_above = c.c > zone_ceiling
    return {"patterns_passed": passed, "close_above_ceiling": close_above, "close_minus_ceiling": c.c - zone_ceiling, "close_minus_floor": c.c - zone_floor, "qualifies": bool(passed) and close_above,
            "green": green, "lower_price_rejection": rejection, "body": body, "upper_wick": uw, "lower_wick": lw}


class PDRFirstEligibleStrategy(PDRBodyStrategy):
    """PDRBodyStrategy with the Phase 5.3 minimal confirmation test. A copy of the frozen scan in which only the classification call differs."""

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        g = gap_info(ctx, self.p)
        if g.direction != "UP":
            return []
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        zone = build_zone(pcs, self.rev)
        base = {"zone_candidate": self.rev.zone_candidate, "zone_kind": zone.kind, "zone_floor": zone.floor, "zone_ceiling": zone.ceiling, "zone_low": zone.floor, "zone_high": zone.ceiling, "zone_width": zone.width,
                "zone_member_candle_starts": [f"{s:%Y-%m-%d %H:%M}" for s in zone.source_starts], "zone_flags": zone.flags, "gap_points": g.points, "session_open": ctx.open_price, "prev_close": prev.close_official,
                "config_id": self.rev.config_id(self.p), "pattern_profile": "PHASE53_MINIMAL_CONFIRMATION"}
        flags = ["PHASE53_PDR_FIRST_ELIGIBLE", "PROVISIONAL_PDR_MINIMAL_CONFIRMATION"] + [f"ZONE_{f}" for f in zone.flags]
        if zone.zero_height and self.rev.zero_height_policy == "UNRESOLVED_NO_SETUP":
            return [self._record(ctx, cs[0], SignalStatus.INVALIDATED, "ZERO_HEIGHT_ZONE_UNRESOLVED", base, [], flags)]
        if self.rev.open_vs_zone == "ABOVE_ZONE" and not ctx.open_price > zone.ceiling:
            return [self._record(ctx, cs[0], SignalStatus.INVALIDATED, "OPEN_NOT_STRICTLY_ABOVE_ZONE", base, [], flags)]
        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j: int | None = None
        evals: list[dict[str, Any]] = []
        prox = self.rev.proximity_points
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._record(ctx, cs[j], SignalStatus.INVALIDATED, "DATA_GAP", {**base, "evaluations": evals}, fsm.trace, flags))
                fsm, j, evals = None, None, []
            if j is None:
                if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox:
                    j = i
                    fsm = SetupFSM(f"PDR body test@{c.end:%H:%M}")
                    fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.floor}, {zone.ceiling}] (+/- {prox})")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for a confirmation candle that closes above the zone")
                    if not self.rev.confirmation_may_be_interaction_candle:
                        continue  # the retest candle may not confirm (unresolved sequencing convention, preserved)
                else:
                    continue
            res = pdr_minimal_confirmation(c, zone.floor, zone.ceiling, prox)
            evals.append({"candle_start": f"{c.start:%H:%M}", "open": c.o, "high": c.h, "low": c.l, "close": c.c, "close_minus_ceiling": res["close_minus_ceiling"], "close_above_ceiling": res["close_above_ceiling"],
                          "patterns_passed": res["patterns_passed"], "qualifies": res["qualifies"]})
            if res["qualifies"] and (i > j or self.rev.confirmation_may_be_interaction_candle):
                fsm.to(State.SIGNAL_CONFIRMED, c.end, f"patterns {res['patterns_passed']} and close {c.c} > zone ceiling {zone.ceiling} (test candle {cs[j].end:%H:%M})")
                lv = {**base, "entry_reference_price": c.c, "interaction_candle_start": f"{cs[j].start:%H:%M}", "patterns_passed": res["patterns_passed"], "close_minus_ceiling": res["close_minus_ceiling"],
                      "close_minus_floor": res["close_minus_floor"], "evaluations": evals}
                out.append(self._record(ctx, c, SignalStatus.CONFIRMED, None, lv, fsm.trace, flags))
                fsm, j, evals = None, None, []
        if fsm is not None and not fsm.terminal:
            out.append(self._record(ctx, cs[j], SignalStatus.INCOMPLETE_AT_EOD, "NO_QUALIFYING_CONFIRMATION_BEFORE_SESSION_END",
                                    {**base, "interaction_candle_start": f"{cs[j].start:%H:%M}", "evaluations": evals}, fsm.trace, flags))
        return out


# ============================================================================================================== PDS
def pds_good_red(c: Candle) -> bool:
    """PROVISIONAL_PDS_MINIMAL_QUALITY Method 1: a red candle whose body is strictly larger than each of its wicks."""
    body = abs(c.c - c.o)
    return is_red(c) and body > upper_wick(c) and body > lower_wick(c)


def pds_red_pin(c: Candle, zone_low: float) -> bool:
    """PROVISIONAL_PDS_MINIMAL_QUALITY Method 2: a red candle whose upper wick is strictly larger than its body and its lower wick, and whose high reached the zone."""
    body = abs(c.c - c.o)
    return is_red(c) and upper_wick(c) > body and upper_wick(c) > lower_wick(c) and c.h >= zone_low


class PDSFirstEligibleStrategy(PDSStrategy):
    """PDSStrategy with the Phase 5.3 parameter-free quality tests for Methods 1 and 2. A copy of the frozen scan in which only the two quality tests differ; Method 3 and the sequence are unchanged."""

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        p = self.p
        g = gap_info(ctx, p)
        if g.direction != "DOWN":
            return []
        zone = pds_zone(ctx.previous, p)
        prox = p.zone_proximity_points
        levels = {"zone_low": zone.low, "zone_high": zone.high, "zone_candle_start": zone.candle_start, "zone_method": zone.method, "zone_method_fell_back_to_A": zone.fallback, "zone_member_count": len(zone.members),
                  "gap_points": g.points, "prev_close": ctx.previous.close_official}
        props = {"pds_zone_method": p.pds_zone_method, "pds_zone_upper_boundary": p.pds_zone_upper_boundary, "phase53_quality": "PROVISIONAL_PDS_MINIMAL_QUALITY", "zone_proximity_points": prox,
                 "pds_small_support_def": p.pds_small_support_def, "pds_m3_break_basis": p.pds_m3_break_basis, "pds_m3_standalone": p.pds_m3_standalone, "pds_open_vs_zone": p.pds_open_vs_zone}
        bad = {"BELOW_ZONE": not ctx.open_price < zone.low, "NOT_ABOVE_ZONE": ctx.open_price > zone.high, "ANY": False}[p.pds_open_vs_zone]
        if bad:
            why = "GAP_DOWN_OPEN_NOT_BELOW_ZONE" if p.pds_open_vs_zone == "BELOW_ZONE" else "GAP_DOWN_OPEN_ABOVE_ZONE"
            return [self._rec(ctx, cs[0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-001", "PDS-002", "PDS-003"], ["PDS-006"], [], SignalStatus.INVALIDATED, why, [], props)]

        def at_zone(c: Candle) -> bool:
            return c.h >= zone.low - prox and c.l <= zone.high + prox

        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j0: int | None = None
        weak_r: int | None = None
        m3_active = False
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._rec(ctx, cs[j0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-005"], [], [], SignalStatus.INVALIDATED, "DATA_GAP", fsm.trace, props))
                fsm, j0, weak_r, m3_active = None, None, None, False
            if j0 is None:
                if not at_zone(c):
                    continue
                j0 = i
                fsm = SetupFSM(f"PDS zone test@{c.end:%H:%M}")
                fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.low}, {zone.high}] (+/- {prox})")
                fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for the first red candle at the zone")
                m3_active = p.pds_m3_standalone
            if weak_r is None and is_red(c) and at_zone(c):
                refs = green_refs(cs, i)
                lv = {**levels, "entry_reference_price": c.c, **refs, "first_red_candle_start": c.start}
                if pds_good_red(c):
                    out.append(self._confirm(ctx, c, "Method 1", lv, fsm, props, ["PDS-M-001", "PDS-M1-001"]))
                elif pds_red_pin(c, zone.low):
                    out.append(self._confirm(ctx, c, "Method 2", lv, fsm, props, ["PDS-M-001", "PDS-M2-001"]))
                else:
                    weak_r = i
                    m3_active = True
                    fsm.trace.append(f"{c.end:%H:%M} weak first red candle -> Method 3 path (source quality rule)")
                if out and out[-1].signal_status == SignalStatus.CONFIRMED.value and weak_r is None:
                    if len([r for r in out if r.signal_status == SignalStatus.CONFIRMED.value]) >= p.max_signals_per_session:
                        return out
                    fsm, j0, m3_active = None, None, False
                    continue
            if m3_active and fsm is not None and not fsm.terminal:
                start = weak_r if weak_r is not None else j0
                sup = self._small_support(cs, start, i, zone.high + prox)
                if sup is not None:
                    hit = (c.c < sup) if p.pds_m3_break_basis == "CLOSE" else (c.l < sup)
                    if hit:
                        refs = green_refs(cs, i)
                        lv = {**levels, "entry_reference_price": c.c, "small_support": sup, **refs}
                        out.append(self._confirm(ctx, c, "Method 3", lv, fsm, props, ["PDS-M3-001"]))
                        if len([r for r in out if r.signal_status == SignalStatus.CONFIRMED.value]) >= p.max_signals_per_session:
                            return out
                        fsm, j0, weak_r, m3_active = None, None, None, False
        if fsm is not None and not fsm.terminal:
            out.append(self._rec(ctx, cs[j0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-005"], [], [], SignalStatus.INCOMPLETE_AT_EOD, "NO_QUALIFYING_ENTRY_BEFORE_SESSION_END", fsm.trace, props))
        return out

    def _confirm(self, ctx, c, method, levels, fsm, props, extra_rules) -> SignalRecord:
        rec = super()._confirm(ctx, c, method, levels, fsm, props, extra_rules)
        rec.flags.append("PHASE53_PDS_FIRST_ELIGIBLE")
        rec.flags.append("PROVISIONAL_PDS_MINIMAL_QUALITY")
        return rec


__all__ = ["PDRFirstEligibleStrategy", "PDSFirstEligibleStrategy", "pdr_minimal_confirmation", "pds_good_red", "pds_red_pin"]
