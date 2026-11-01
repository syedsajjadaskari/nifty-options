"""PDS - Previous Day Support, gap-down resistance retest (short). Source: ``PDS strategy.pdf``.

Entry methods at the zone (kept separate):
  Method 1  first red candle at the zone is a good (strong-bodied) red candle
  Method 2  first red candle at the zone is a red higher-price-rejection pin bar
  Method 3  the first red candle was not satisfying -> wait for a small support near the zone to break
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
    bearish_pin,
    gap_info,
    green_refs,
    is_red,
    pds_zone,
    pivot_lows,
    strong_bearish,
)
from nifty_trading.strategies.rules import implements

_BASE = ["PDS-001", "PDS-002", "PDS-003", "PDS-004", "PDS-005"]


class PDSStrategy(SignalEngine):
    STRATEGY = "PDS"
    METHODS = ("Method 1", "Method 2", "Method 3")
    REQUIRES_PREVIOUS_SESSION = True

    @implements("PDS-001", "PDS-002", "PDS-003", "PDS-004", "PDS-005", "PDS-006", "PDS-007", "PDS-M-001", "PDS-M1-001",
                "PDS-M2-001", "PDS-M3-001", "PDS-SL-001", "PDS-MISSING-001")
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        p = self.p
        g = gap_info(ctx, p)
        if g.direction != "DOWN":
            return []  # PDS-003
        zone = pds_zone(ctx.previous, p)
        prox = p.zone_proximity_points
        levels = {"zone_low": zone.low, "zone_high": zone.high, "zone_candle_start": zone.candle_start,
                  "gap_points": g.points, "prev_close": ctx.previous.close_official}
        props = {"strong_candle": p.strong_candle, "pin_bar": p.pin_bar, "zone_proximity_points": prox,
                 "pds_small_support_def": p.pds_small_support_def, "pds_m3_break_basis": p.pds_m3_break_basis,
                 "pds_m3_standalone": p.pds_m3_standalone, "require_open_clear_of_zone": p.require_open_clear_of_zone}
        if p.require_open_clear_of_zone and not ctx.open_price < zone.low:
            return [self._rec(ctx, cs[0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-001", "PDS-002", "PDS-003"], ["PDS-006"], [],
                              SignalStatus.INVALIDATED, "GAP_DOWN_OPEN_NOT_BELOW_ZONE", [], props)]

        def at_zone(c: Candle) -> bool:
            return c.h >= zone.low - prox and c.l <= zone.high + prox

        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j0: int | None = None  # first interaction candle
        weak_r: int | None = None  # first red candle at the zone that failed the quality rule
        m3_active = False
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._rec(ctx, cs[j0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-005"], [], [],
                                     SignalStatus.INVALIDATED, "DATA_GAP", fsm.trace, props))
                fsm, j0, weak_r, m3_active = None, None, None, False
            if j0 is None:
                if not c.h >= zone.low - prox:  # PDS-005: has price come up to the zone yet?
                    continue
                j0 = i
                fsm = SetupFSM(f"PDS zone test@{c.end:%H:%M}")
                fsm.to(State.SETUP_DETECTED, c.end, f"high {c.h} >= zone_low {zone.low} - {prox}")
                fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for the first red candle at the zone")
                m3_active = p.pds_m3_standalone
            # ---- Methods 1 & 2: the FIRST red candle at the zone (PDS-M-001)
            if weak_r is None and is_red(c) and at_zone(c):
                refs = green_refs(cs, i)
                lv = {**levels, "entry_reference_price": c.c, **refs, "first_red_candle_start": c.start}
                if strong_bearish(c, p):
                    out.append(self._confirm(ctx, c, "Method 1", lv, fsm, props, ["PDS-M-001", "PDS-M1-001"]))
                elif bearish_pin(c, p) and c.h >= zone.low:
                    out.append(self._confirm(ctx, c, "Method 2", lv, fsm, props, ["PDS-M-001", "PDS-M2-001"]))
                else:
                    weak_r = i
                    m3_active = True  # quality rule: do not take a weak red candle; wait for the small support (Method 3)
                    fsm.trace.append(f"{c.end:%H:%M} weak first red candle -> Method 3 path")
                if out and out[-1].signal_status == SignalStatus.CONFIRMED.value and weak_r is None:
                    if len([r for r in out if r.signal_status == SignalStatus.CONFIRMED.value]) >= p.max_signals_per_session:
                        return out
                    fsm, j0, m3_active = None, None, False
                    continue
            # ---- Method 3: break of a small support near the zone
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
            out.append(self._rec(ctx, cs[j0], "Method 1/2/3", Direction.SHORT, levels, ["PDS-005"], [], [],
                                 SignalStatus.INCOMPLETE_AT_EOD, "NO_QUALIFYING_ENTRY_BEFORE_SESSION_END", fsm.trace, props))
        return out

    def _small_support(self, cs: list[Candle], start: int, i: int, near_ceiling: float) -> float | None:
        """PROPOSED small support formed at/after ``start`` and before candle i, near the zone (low <= near_ceiling)."""
        if self.p.pds_small_support_def == "LAST_N2":
            if i - 2 < start:
                return None
            lvl = min(cs[i - 2].l, cs[i - 1].l)
            return lvl if lvl <= near_ceiling else None
        js = [j for j in pivot_lows(cs, start, i, 1) if cs[j].l <= near_ceiling]
        return cs[js[-1]].l if js else None

    def _confirm(self, ctx, c, method, levels, fsm, props, extra_rules) -> SignalRecord:
        fsm.to(State.SIGNAL_CONFIRMED, c.end, f"{method} confirmed on candle close")
        return self._rec(ctx, c, method, Direction.SHORT, levels,
                         _BASE + ["PDS-006", "PDS-007"] + extra_rules, [], [], SignalStatus.CONFIRMED, None, fsm.trace, props)
