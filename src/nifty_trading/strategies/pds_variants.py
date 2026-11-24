"""Phase 6.5 continuation: PDS confirmation research variant (opt-in; the baseline ``PDSFirstEligibleStrategy`` and the frozen ``PDSStrategy`` are not modified).

PDS methods are NOT interchangeable, so the first-versus-second comparison is applied per method:
  Method 1 (good red candle) and Method 2 (red pin bar, higher-price rejection): the source entry is the FIRST red candle at the zone that passes the quality test. PDS-SECOND (this class) registers that first eligible
         bearish candle but does not trade it; a LATER completed candle at the zone that independently passes a bearish test (good red body for Method 1, red pin bar for Method 2) triggers. If price closes above the zone
         (zone high + proximity) before a second candle appears the cycle is abandoned. MECHANICAL RESEARCH CONVENTION - the author has not defined second-confirmation conditions: AUTHOR_CONFIRMATION_REQUIRED.
  Method 3 (small-support break): the mandatory support break IS the trigger; there is no 'first red candle' entry and no source-supported alternative, so Method 3 is left exactly as in the baseline (never bypassed).
"""

from __future__ import annotations

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import SetupFSM, SignalRecord, State
from nifty_trading.strategies.definitions import Candle, gap_info, green_refs, is_red, pds_zone
from nifty_trading.strategies.first_eligible_phase53 import (
    PDSFirstEligibleStrategy,
    pds_good_red,
    pds_red_pin,
)


class PDSSecondConfirmationStrategy(PDSFirstEligibleStrategy):
    def __init__(self, **kw):
        super().__init__(**kw)
        self.cycle_log: list[dict] = []

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:  # noqa: C901
        p = self.p
        g = gap_info(ctx, p)
        if g.direction != "DOWN":
            return []
        zone = pds_zone(ctx.previous, p)
        prox = p.zone_proximity_points
        levels = {"zone_low": zone.low, "zone_high": zone.high, "zone_candle_start": zone.candle_start, "zone_method": zone.method, "gap_points": g.points, "prev_close": ctx.previous.close_official}
        props = {"pds_variant": "SECOND_CONFIRMATION", "approval_status": "MECHANICAL_RESEARCH_CONVENTION / AUTHOR_CONFIRMATION_REQUIRED", "pds_small_support_def": p.pds_small_support_def, "pds_m3_break_basis": p.pds_m3_break_basis}
        bad = {"BELOW_ZONE": not ctx.open_price < zone.low, "NOT_ABOVE_ZONE": ctx.open_price > zone.high, "ANY": False}[p.pds_open_vs_zone]
        if bad:
            return []

        def at_zone(c: Candle) -> bool:
            return c.h >= zone.low - prox and c.l <= zone.high + prox

        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j0: int | None = None
        weak_r: int | None = None
        m3_active = False
        first: tuple[int, str] | None = None
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm, j0, weak_r, m3_active, first = None, None, None, False, None
            if j0 is None:
                if not at_zone(c):
                    continue
                j0 = i
                fsm = SetupFSM(f"PDS second@{c.end:%H:%M}")
                fsm.to(State.SETUP_DETECTED, c.end, "zone test")
                fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for the first and then a second eligible bearish candle")
                m3_active = p.pds_m3_standalone
            if first is not None and c.c > zone.high + prox:
                fsm, j0, weak_r, m3_active, first = None, None, None, False, None            # the zone was lost to the upside: cycle abandoned
                continue
            if weak_r is None and is_red(c) and at_zone(c):
                meth = "Method 1" if pds_good_red(c) else ("Method 2" if pds_red_pin(c, zone.low) else None)
                if meth is None:
                    weak_r, m3_active = i, True                                               # weak first red candle -> Method 3 (unchanged source rule)
                elif first is None:
                    first = (i, meth)                                                         # first eligible bearish candle: registered, NOT traded
                    continue
                else:
                    lv = {**levels, "entry_reference_price": c.c, **green_refs(cs, i), "first_red_candle_start": cs[first[0]].start, "first_eligible_candle_start": f"{cs[first[0]].start:%H:%M}", "second_eligible_candle_start": f"{c.start:%H:%M}"}
                    rec = self._confirm(ctx, c, meth, lv, fsm, props, ["PDS-M-001", "PDS-M1-001" if meth == "Method 1" else "PDS-M2-001"])
                    rec.flags.append("PDS_SECOND_CONFIRMATION_VARIANT")
                    out.append(rec)
                    self.cycle_log.append({"date": str(ctx.date), "method": meth, "first": f"{cs[first[0]].start:%H:%M}", "second": f"{c.start:%H:%M}"})
                    fsm, j0, m3_active, first, weak_r = None, None, False, None, None
                    continue
            if m3_active and fsm is not None and not fsm.terminal:
                start = weak_r if weak_r is not None else j0
                sup = self._small_support(cs, start, i, zone.high + prox)
                if sup is not None and ((c.c < sup) if p.pds_m3_break_basis == "CLOSE" else (c.l < sup)):
                    lv = {**levels, "entry_reference_price": c.c, "small_support": sup, **green_refs(cs, i)}
                    out.append(self._confirm(ctx, c, "Method 3", lv, fsm, props, ["PDS-M3-001"]))      # Method 3 is untouched: the mandatory support break is the trigger
                    fsm, j0, weak_r, m3_active, first = None, None, None, False, None
        return out
