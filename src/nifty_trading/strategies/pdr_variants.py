"""Phase 6.5 continuation: PDR confirmation RESEARCH variants (opt-in classes; the current baseline ``PDRFirstEligibleStrategy`` and the frozen engines are not modified).

Common to every variant: previous-day body-based zone, the open strictly above the zone ceiling, a completed retest (the first candle whose range meets the zone), chronological processing, one signal per setup cycle, the 13:00 cutoff.

  PDR-A  (baseline, not here)  green candle OR lower-price rejection, AND close strictly above the zone ceiling; the retest candle may NOT confirm
  PDR-B1 first GREEN candle after the retest; NO ceiling requirement (a green close inside / below the zone qualifies)       -> bypasses an owner-approved rule: AUTHOR_CONFIRMATION_REQUIRED
  PDR-B2 as B1 but the retest candle itself may be the first green candle                                                      -> AUTHOR_CONFIRMATION_REQUIRED
  PDR-C  first GREEN candle closing strictly above the ceiling; the retest candle MAY simultaneously confirm                   -> the retest/confirmation sequencing is an unresolved convention: AUTHOR_CONFIRMATION_REQUIRED
  PDR-D  SECOND eligible confirmation: the first baseline-eligible candle is registered but does NOT trigger; a LATER completed candle that independently satisfies the baseline eligibility test triggers (entry after
         that candle closes). Not 'the next candle': any later independently eligible candle. MECHANICAL RESEARCH CONVENTION - the author has not defined second-confirmation conditions.
"""

from __future__ import annotations

from typing import Any

from nifty_trading.data.sessions import SessionContext
from nifty_trading.strategies.base import SetupFSM, SignalRecord, SignalStatus, State
from nifty_trading.strategies.definitions import Candle, gap_info, prev_candles, to_candles
from nifty_trading.strategies.first_eligible_phase53 import (
    PDRFirstEligibleStrategy,
    pdr_minimal_confirmation,
)
from nifty_trading.strategies.pdr_body import build_zone

MODES = ("B1", "B2", "C", "D")
APPROVAL = {"B1": "AUTHOR_CONFIRMATION_REQUIRED (bypasses the owner-approved close-above-ceiling rule)", "B2": "AUTHOR_CONFIRMATION_REQUIRED (bypasses the close-above-ceiling rule; retest candle may confirm)",
            "C": "AUTHOR_CONFIRMATION_REQUIRED (retest-then-confirmation sequencing is unresolved)", "D": "MECHANICAL_RESEARCH_CONVENTION (second-confirmation conditions are not defined by the author)"}


class PDRVariantStrategy(PDRFirstEligibleStrategy):
    def __init__(self, mode: str, **kw):
        super().__init__(**kw)
        if mode not in MODES:
            raise ValueError(mode)
        self.mode = mode
        self.cycle_log: list[dict[str, Any]] = []     # every setup cycle (read and cleared by the runner)

    def _eligible(self, c: Candle, floor: float, ceiling: float, prox: float) -> tuple[bool, dict]:
        r = pdr_minimal_confirmation(c, floor, ceiling, prox)
        if self.mode in ("B1", "B2"):
            return r["green"], r
        if self.mode == "C":
            return r["green"] and r["close_above_ceiling"], r
        return r["qualifies"], r

    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:  # noqa: C901
        g = gap_info(ctx, self.p)
        if g.direction != "UP":
            return []
        prev = ctx.previous
        pcs = to_candles(prev_candles(prev, self.p))
        zone = build_zone(pcs, self.rev)
        base = {"zone_candidate": self.rev.zone_candidate, "zone_kind": zone.kind, "zone_floor": zone.floor, "zone_ceiling": zone.ceiling, "zone_low": zone.floor, "zone_high": zone.ceiling, "zone_width": zone.width,
                "gap_points": g.points, "session_open": ctx.open_price, "prev_close": prev.close_official, "pattern_profile": f"PDR_VARIANT_{self.mode}", "pdr_variant": self.mode, "approval_status": APPROVAL[self.mode]}
        flags = [f"PDR_VARIANT_{self.mode}", APPROVAL[self.mode].split(" ")[0]]
        if (zone.zero_height and self.rev.zero_height_policy == "UNRESOLVED_NO_SETUP") or (self.rev.open_vs_zone == "ABOVE_ZONE" and not ctx.open_price > zone.ceiling):
            return []
        retest_may_confirm = self.mode in ("B2", "C")
        out: list[SignalRecord] = []
        fsm: SetupFSM | None = None
        j: int | None = None
        first_elig: int | None = None
        prox = self.rev.proximity_points
        for i, c in enumerate(cs):
            if gap_before[i] and fsm is not None:
                fsm, j, first_elig = None, None, None
            if j is None:
                if c.l <= zone.ceiling + prox and c.h >= zone.floor - prox:
                    j = i
                    fsm = SetupFSM(f"PDR {self.mode}@{c.end:%H:%M}")
                    fsm.to(State.SETUP_DETECTED, c.end, f"range [{c.l}, {c.h}] intersects zone [{zone.floor}, {zone.ceiling}]")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for the variant's confirmation")
                    if not retest_may_confirm:
                        continue
                else:
                    continue
            ok, r = self._eligible(c, zone.floor, zone.ceiling, prox)
            if not ok or not (i > j or retest_may_confirm):
                continue
            if self.mode == "D" and first_elig is None:
                first_elig = i                                            # the first eligible candle is registered; the trigger is a LATER independently eligible candle
                continue
            fsm.to(State.SIGNAL_CONFIRMED, c.end, f"{self.mode}: green={r['green']} close {c.c} vs ceiling {zone.ceiling}")
            lv = {**base, "entry_reference_price": c.c, "interaction_candle_start": f"{cs[j].start:%H:%M}", "patterns_passed": r["patterns_passed"], "close_minus_ceiling": r["close_minus_ceiling"], "green_candle_is_retest_candle": i == j,
                  "close_above_ceiling": r["close_above_ceiling"], "first_eligible_candle_start": f"{cs[first_elig].start:%H:%M}" if first_elig is not None else f"{c.start:%H:%M}"}
            out.append(self._record(ctx, c, SignalStatus.CONFIRMED, None, lv, fsm.trace, flags))
            self.cycle_log.append({"date": str(ctx.date), "retest": f"{cs[j].start:%H:%M}", "signal_candle": f"{c.start:%H:%M}", "variant": self.mode})
            fsm, j, first_elig = None, None, None
        return out
