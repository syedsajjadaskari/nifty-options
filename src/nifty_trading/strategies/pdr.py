"""PDR - Previous Day Resistance, gap-up support retest (long). Source: ``PDR_Strategy_Guide.pdf``.

Sequence: previous-day high zone -> gap-up open -> price returns to the zone -> a green candle forms.
The stop (35 or 40 "depending on the situation") has no selection rule in the source (PDR-009):
the signal engine reports detection only.
"""

from __future__ import annotations

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import (
    Direction,
    SetupFSM,
    SignalEngine,
    SignalRecord,
    SignalStatus,
    State,
)
from nifty_trading.strategies.definitions import (
    Candle,
    gap_info,
    is_green,
    pdr_diagnostic_zone,
    pdr_zone,
    previous_day_reversal_ok,
)
from nifty_trading.strategies.rules import implements


class PDRStrategy(SignalEngine):
    STRATEGY = "PDR"
    METHODS = ("PDR",)
    REQUIRES_PREVIOUS_SESSION = True

    def _default_direction(self) -> str:
        return Direction.LONG.value

    def _execution_status(self, signal_ts) -> str:
        if self.p.pdr_zone_method == "A_HIGHEST_HIGH":
            return "DIAGNOSTIC_ONLY_NOT_TRADABLE"  # the absolute highest high is a diagnostic reference, never a tradable zone
        return super()._execution_status(signal_ts)

    @implements("PDR-001", "PDR-002", "PDR-003", "PDR-004", "PDR-005", "PDR-006", "PDR-007", "PDR-010", "PDR-011", "PDR-012")
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        p = self.p
        g = gap_info(ctx, p)
        if g.direction != "UP":
            return []  # PDR-004: no gap up, no setup (nothing is evaluated)
        zone = pdr_zone(ctx.previous, p)
        diag = pdr_diagnostic_zone(ctx.previous, p)
        if zone is None:  # the approved candidate found no zone: there is no setup (and no fallback to the highest high)
            return [self._rec(ctx, cs[0], "PDR", Direction.LONG, {"zone_method": p.pdr_zone_method, "diagnostic_highest_high_zone": [diag.low, diag.high],
                                                                  "gap_points": g.points}, ["PDR-001", "PDR-004"], ["PDR-002"], [],
                              SignalStatus.INVALIDATED, f"NO_ZONE_CANDIDATE({p.pdr_zone_method})", [], {"pdr_zone_method": p.pdr_zone_method})]
        rev_ok, rev_msg = previous_day_reversal_ok(ctx.previous, zone, p)
        levels = {"zone_low": zone.low, "zone_high": zone.high, "zone_candle_start": zone.candle_start,
                  "zone_method": zone.method, "zone_member_count": len(zone.members),
                  "zone_status": "DIAGNOSTIC_ONLY_NOT_TRADABLE" if zone.diagnostic_only else "OWNER_APPROVED_RESEARCH_CANDIDATE",
                  "diagnostic_highest_high_zone": [diag.low, diag.high],
                  "gap_points": g.points, "prev_close": ctx.previous.close_official, "stop_selection": "source rule unresolved (PDR-009); USER_APPROVED research baseline in execution_config",
                  "target_points_guide": 70.0, "target_conflict": "see execution_config.target_2_conflict"}
        props = {"pdr_zone_method": p.pdr_zone_method, "zone_lower_boundary": p.zone_lower_boundary, "zone_proximity_points": p.zone_proximity_points,
                 "pdr_green_may_be_interaction_candle": p.pdr_green_may_be_interaction_candle,
                 "pdr_reversal_filter": p.pdr_reversal_filter, "pdr_open_vs_zone": p.pdr_open_vs_zone,
                 "gap_min_points": p.gap_min_points}
        unresolved = ["PDR-010"] if rev_ok is None else []
        c0 = cs[0]
        if rev_ok is False:
            return [self._rec(ctx, c0, "PDR", Direction.LONG, levels, ["PDR-001", "PDR-002", "PDR-004"], ["PDR-010"], [],
                              SignalStatus.INVALIDATED, f"PREV_DAY_REVERSAL_NOT_CLEAR({rev_msg})", [], props)]
        bad = {"ABOVE_ZONE": not ctx.open_price > zone.high, "NOT_BELOW_ZONE": ctx.open_price < zone.low, "ANY": False}[p.pdr_open_vs_zone]
        if bad:
            why = "GAP_UP_OPEN_NOT_ABOVE_ZONE" if p.pdr_open_vs_zone == "ABOVE_ZONE" else "GAP_UP_OPEN_BELOW_ZONE"
            return [self._rec(ctx, c0, "PDR", Direction.LONG, levels, ["PDR-001", "PDR-002", "PDR-004"], ["PDR-011"], unresolved,
                              SignalStatus.INVALIDATED, why, [], props)]
        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j: int | None = None  # interaction candle
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._rec(ctx, cs[j], "PDR", Direction.LONG, levels, ["PDR-006"], [], unresolved,
                                     SignalStatus.INVALIDATED, "DATA_GAP", fsm.trace, props))
                fsm, j = None, None
            if j is None:
                if c.l <= zone.high + p.zone_proximity_points and c.h >= zone.low - p.zone_proximity_points:  # PDR-006: the candle's range intersects the zone (+/- proximity)
                    j = i
                    fsm = SetupFSM(f"PDR zone test@{c.end:%H:%M}")
                    fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.low}, {zone.high}] (+/- {p.zone_proximity_points})")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for a green candle")
                    if not p.pdr_green_may_be_interaction_candle:
                        continue  # PDR-007: green candle must come AFTER the interaction candle
                else:
                    continue
            if is_green(c) and (i > j or p.pdr_green_may_be_interaction_candle):
                fsm.to(State.SIGNAL_CONFIRMED, c.end, f"green candle after zone test (test candle {cs[j].end:%H:%M})")
                out.append(self._rec(
                    ctx, c, "PDR", Direction.LONG, {**levels, "entry_reference_price": c.c, "interaction_candle_start": cs[j].start},
                    ["PDR-001", "PDR-002", "PDR-003", "PDR-004", "PDR-005", "PDR-006", "PDR-007", "PDR-012"]
                    + (["PDR-011"] if p.pdr_open_vs_zone != "ANY" else []), [], unresolved,
                    SignalStatus.CONFIRMED, None, fsm.trace, props))
                if len([r for r in out if r.signal_status == SignalStatus.CONFIRMED.value]) >= p.max_signals_per_session:
                    break
                fsm, j = None, None
        if fsm is not None and not fsm.terminal:
            out.append(self._rec(ctx, cs[j], "PDR", Direction.LONG, levels, ["PDR-006"], [], unresolved,
                                 SignalStatus.INCOMPLETE_AT_EOD, "NO_GREEN_CANDLE_AFTER_ZONE_TEST_BEFORE_SESSION_END", fsm.trace, props))
        return out
