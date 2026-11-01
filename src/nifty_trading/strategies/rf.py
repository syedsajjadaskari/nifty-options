"""RF - Reverse Failure (long, implied). Source: ``RF strategy.pdf``.

Activation, strictly in order: established uptrend -> gap-up open within yesterday's range ->
a candle CLOSES below the first candle's low (RF Low) -> price returns inside the first candle's range.

Entry price, stop selection and TARGET are not defined in the document (RF-009/010/011):
``RF_TARGET_STATUS = UNRESOLVED``. Signal detection does not depend on them.
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
from nifty_trading.strategies.definitions import Candle, gap_info, trend_check
from nifty_trading.strategies.params import RF_TARGET_STATUS
from nifty_trading.strategies.rules import implements


class RFStrategy(SignalEngine):
    STRATEGY = "RF"
    METHODS = ("RF",)
    REQUIRES_PREVIOUS_SESSION = True

    def _default_direction(self) -> str:
        return Direction.LONG.value

    @implements("RF-001", "RF-002", "RF-003", "RF-004", "RF-005", "RF-006", "RF-007", "RF-008", "RF-010", "RF-012", "RF-013", "RF-014")
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        p = self.p
        rf_h, rf_l = cs[0].h, cs[0].l
        prev = ctx.previous
        out: list[SignalRecord] = []
        fsm = SetupFSM("RF activation")
        c_close_below: int | None = None
        for i in range(1, len(cs)):
            c = cs[i]
            if gap_before[i] and c_close_below is not None:
                fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._rec(ctx, cs[c_close_below], "RF", Direction.LONG, self._levels(ctx, rf_h, rf_l), ["RF-005"], [], [],
                                     SignalStatus.INVALIDATED, "DATA_GAP", fsm.trace, self._props()))
                fsm, c_close_below = SetupFSM("RF activation (restarted after data gap)"), None
            if c_close_below is None:
                if c.c < rf_l:  # RF-005: a proper close below RF Low (a wick is not enough)
                    c_close_below = i
                    fsm.to(State.SETUP_DETECTED, c.end, f"close {c.c} < RF_L {rf_l}")
                    fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "waiting for return inside the first-candle range")
                continue
            # RF-006: return inside, per candidate definition
            d = p.rf_return_inside_def
            k = i - c_close_below
            if d == "R1":
                back = rf_l <= c.c <= rf_h
            elif d == "R2":
                back = c.h >= rf_l
            else:  # R3: only the very next candle
                back = rf_l <= c.c <= rf_h if k == 1 else False
            if d == "R3" and k > 1:
                fsm.to(State.SETUP_INVALIDATED, c.end, "R3: next candle did not return inside")
                out.append(self._gated(ctx, cs, i, fsm, SignalStatus.INVALIDATED, "NO_RETURN_ON_NEXT_CANDLE(R3)", [], ["RF-006"]))
                return out
            if not back:
                continue
            out.append(self._finalise(ctx, cs, i, c_close_below, fsm, rf_h, rf_l, prev))
            return out  # RF-014: first activation per session
        if c_close_below is not None and not fsm.terminal:
            out.append(self._rec(ctx, cs[c_close_below], "RF", Direction.LONG, self._levels(ctx, rf_h, rf_l), ["RF-002", "RF-005"], [], [],
                                 SignalStatus.INCOMPLETE_AT_EOD, "NO_RETURN_INSIDE_BEFORE_SESSION_END", fsm.trace, self._props()))
        return out

    # ------------------------------------------------------------------ helpers
    def _props(self) -> dict:
        p = self.p
        return {"trend_mode": p.trend_mode, "rf_return_inside_def": p.rf_return_inside_def, "rf_direction": p.rf_direction,
                "gap_min_points": p.gap_min_points}

    def _levels(self, ctx: SessionContext, rf_h: float, rf_l: float) -> dict:
        prev = ctx.previous
        return {"RF_High": rf_h, "RF_Low": rf_l, "prev_day_high": prev.high, "prev_day_low": prev.low,
                "prev_close": prev.close_official, "open_price": ctx.open_price,
                "RF_TARGET_STATUS": RF_TARGET_STATUS, "stop_selection": "UNRESOLVED(RF-009)", "entry_price_rule": "OPEN(RF-010)"}

    def _gated(self, ctx, cs, i, fsm, status, why, sat, failed):
        return self._rec(ctx, cs[i], "RF", Direction.LONG, self._levels(ctx, cs[0].h, cs[0].l), ["RF-002", "RF-005"] + sat, failed,
                         ["RF-011"], status, why, fsm.trace, self._props())

    def _finalise(self, ctx: SessionContext, cs: list[Candle], i: int, cb: int, fsm: SetupFSM, rf_h: float, rf_l: float, prev):
        """Sequence complete at candle i. Apply the preconditions in document order (RF-007): trend, gap, range."""
        c = cs[i]
        sat = ["RF-002", "RF-005", "RF-006", "RF-007", "RF-013"]
        t = trend_check(ctx, 0, "LONG", self.p.trend_mode)
        if t.ok is None:
            fsm.to(State.SETUP_INVALIDATED, c.end, f"trend not evaluable: {t.reason}")
            return self._gated(ctx, cs, i, fsm, SignalStatus.NOT_EVALUATED, t.reason, sat, [])
        if not t.ok:
            fsm.to(State.SETUP_INVALIDATED, c.end, f"trend: {t.reason}")
            return self._gated(ctx, cs, i, fsm, SignalStatus.INVALIDATED, f"TREND:{t.reason}", sat, ["RF-001", "RF-008"])
        sat += ["RF-001"]
        g = gap_info(ctx, self.p)
        if g.direction != "UP":
            fsm.to(State.SETUP_INVALIDATED, c.end, f"gap direction {g.direction}")
            return self._gated(ctx, cs, i, fsm, SignalStatus.INVALIDATED, f"GAP_NOT_UP({g.direction})", sat, ["RF-003"])
        if not (prev.low <= ctx.open_price <= prev.high):
            fsm.to(State.SETUP_INVALIDATED, c.end, "gap-up open outside yesterday's range")
            return self._gated(ctx, cs, i, fsm, SignalStatus.INVALIDATED, "GAP_UP_OUTSIDE_YESTERDAYS_RANGE", sat + ["RF-003"], ["RF-004"])
        fsm.to(State.SIGNAL_CONFIRMED, c.end, f"close {c.c} back inside [{rf_l},{rf_h}] after close below at {cs[cb].end:%H:%M}")
        lv = {**self._levels(ctx, rf_h, rf_l), "entry_reference_price": c.c, "close_below_candle_start": cs[cb].start,
              "gap_points": g.points}
        return self._rec(ctx, c, "RF", Direction.LONG, lv, sat + ["RF-003", "RF-004", "RF-010", "RF-012", "RF-014"], [],
                         ["RF-009", "RF-011"], SignalStatus.CONFIRMED, None, fsm.trace, self._props(),
                         ["RF_DIRECTION_IMPLIED_NOT_STATED"])
