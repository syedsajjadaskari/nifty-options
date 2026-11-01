"""IRF - Initial Range Failure (short only). Source: ``IRF_Strategy_Guide Updated.pdf``.

Three source-defined entry methods are kept separate:
  Method 1   breakout close above IRH, the very next candle closes back inside the range.
  Method 2A  extension + red candle, then a candle closes below recent support.
  Method 2B  extension + red candle, then a red candle closes back below recent resistance.
  Method 3   liquidity sweep: compression inside the range, then a red candle with a long upper wick
             above IRH that closes below recent support (compulsory).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

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
    compression_ok,
    is_green,
    is_red,
    most_recent_colour,
    recent_resistance,
    recent_support,
    wick_share_in_band,
    wick_share_outside,
)
from nifty_trading.strategies.rules import implements

_GLOBAL = ["IRF-GLOBAL-001", "IRF-GLOBAL-002", "IRF-GLOBAL-003"]


@dataclass
class _Attempt:
    b: int  # breakout candle index
    fsm: SetupFSM
    e: int | None = None  # extension candle index
    r: int | None = None  # first red candle at/after the extension
    pending_flags: list[str] = field(default_factory=list)


class IRFStrategy(SignalEngine):
    STRATEGY = "IRF"
    METHODS = ("Method 1", "Method 2A", "Method 2B", "Method 3")
    REQUIRES_PREVIOUS_SESSION = False  # IRF uses only the opening range and intraday candles

    # ------------------------------------------------------------------ main scan
    @implements("IRF-GLOBAL-001", "IRF-GLOBAL-002", "IRF-GLOBAL-003", "IRF-GLOBAL-004", "IRF-GLOBAL-005", "IRF-M2-004", "IRF-M2-006", "IRF-SL-001")
    def _scan(self, ctx: SessionContext, cs: list[Candle], gap_before: list[bool]) -> list[SignalRecord]:
        irh, irl = cs[0].h, cs[0].l
        out: list[SignalRecord] = []
        att: _Attempt | None = None  # Method 2 attempt keyed to one breakout close
        win = self.p.m1_max_candles_after_breakout
        for i in range(1, len(cs)):
            c = cs[i]
            if gap_before[i] and att is not None:
                att.fsm.to(State.SETUP_INVALIDATED, c.start, "DATA_GAP")
                out.append(self._setup_record(ctx, cs, att, "DATA_GAP", i))
                att = None
            out.extend(self._method3(ctx, cs, i, irh, irl, gap_before))
            m1 = self._method1(ctx, cs, i, irh, irl, gap_before)  # Method 1 is history-independent
            if m1 is not None:
                out.append(m1[0])
                if att is not None and att.b == m1[1]:
                    att = None  # IRF p.9: immediate close back inside makes it Method 1, not Method 2
            if att is not None and i - att.b >= win:
                att, recs = self._m2_step(ctx, cs, att, i, irh, irl)
                out.extend(recs)
            if att is None and c.c > irh and not gap_before[i]:
                fsm = SetupFSM(f"IRF breakout@{c.end:%H:%M}")
                fsm.to(State.SETUP_DETECTED, c.end, f"close {c.c} > IRH {irh} (IRF-M1-001/M2-001)")
                att = _Attempt(b=i, fsm=fsm)
        if att is not None and not att.fsm.terminal:
            out.append(self._setup_record(ctx, cs, att, "SESSION_ENDED_BEFORE_CONFIRMATION", len(cs) - 1,
                                          status=SignalStatus.INCOMPLETE_AT_EOD))
        return out

    # ------------------------------------------------------------------ Method 1
    @implements("IRF-M1-001", "IRF-M1-002", "IRF-M1-004", "IRF-M1-003", "IRF-M1-C001")
    def _method1(self, ctx, cs, i: int, irh: float, irl: float, gap_before: list[bool]):
        """Candle b closes above IRH and candle b+1 (== i) closes back inside the range."""
        below_irl_ok = self.p.m1_close_below_irl_counts_as_inside

        def inside(x: Candle) -> bool:
            return (irl <= x.c < irh) or (below_irl_ok and x.c < irl)

        if not inside(cs[i]):
            return None
        for k in range(1, self.p.m1_max_candles_after_breakout + 1):
            b = i - k
            if b < 1 or any(gap_before[b + 1:i + 1]):
                break
            if cs[b].c > irh and all(not inside(cs[m]) for m in range(b + 1, i)):
                sat = _GLOBAL + ["IRF-M1-001", "IRF-M1-002", "IRF-M1-004"]
                flags: list[str] = []
                if cs[i].c < irl:
                    sat.append("IRF-M1-003")
                    flags.append("M1_CLOSE_BELOW_IRL_COUNTED_AS_INSIDE(proposal)")
                if k > 1:
                    sat.append("IRF-M1-C001")
                    flags.append(f"M1_FAILURE_ON_CANDLE_{k}_AFTER_BREAKOUT(research variant of p.14)")
                fsm = SetupFSM(f"IRF M1@{cs[i].end:%H:%M}")
                fsm.to(State.SETUP_DETECTED, cs[b].end, f"close {cs[b].c} > IRH {irh}")
                fsm.to(State.SIGNAL_CONFIRMED, cs[i].end, f"candle +{k} closes {cs[i].c} back inside [{irl},{irh})")
                return self._confirmed(ctx, cs, i, "Method 1", b, irh, irl, sat, fsm.trace, flags,
                                       {"breakout_close": cs[b].c, "breakout_candle_start": cs[b].start}), b
        return None

    # ------------------------------------------------------------------ Method 2 (A and B)
    @implements("IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2-005", "IRF-M2A-002", "IRF-M2B-002", "IRF-M2B-003")
    def _m2_step(self, ctx, cs, att: _Attempt, i: int, irh: float, irl: float):
        c, b = cs[i], att.b
        if att.fsm.state is State.SETUP_DETECTED:
            att.fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "Method 1 window passed; Method 2 path (IRF-M2-004)")
        if self.p.m2_expiry_candles is not None and i - b > self.p.m2_expiry_candles:
            att.fsm.to(State.SETUP_INVALIDATED, c.end, "M2_EXPIRED(proposal)")
            return None, [self._setup_record(ctx, cs, att, "M2_EXPIRED", i)]
        # --- extension (IRF-M2-002) and red candle (IRF-M2-003), both recorded causally
        if att.e is None and i > b:
            ext = (c.h > cs[b].h) if self.p.m2_extension_definition == "E1" else (c.c > irh)
            if ext:
                att.e = i
        if att.e is not None and att.r is None:
            first_ok = att.e if self.p.m2_red_may_be_extension_candle else att.e + 1
            if i >= first_ok and is_red(c):
                att.r = i
        recs: list[SignalRecord] = []
        proposals = {"irf_support_def": self.p.irf_support_def, "irf_resistance_def": self.p.irf_resistance_def,
                     "m2_extension_definition": self.p.m2_extension_definition}
        # ---- Confirmation A: a candle closes below recent support
        red_ok = att.r is not None and (att.r <= i if self.p.m2a_break_may_be_red_candle else att.r < i)
        if red_ok and att.e is not None:
            sup = recent_support(cs, b + 1, i, self.p)
            if sup is not None and c.c < sup[1]:
                recs.append(("Method 2A", {"recent_support": sup[1], "support_candle_index": sup[0]},
                             ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
        # ---- Confirmation B: red candle closes back below recent resistance after trading above it
        res = recent_resistance(cs, b, i, self.p)
        if res is not None and is_red(c) and c.c < res[1]:
            j, rlvl = res
            last_push = i if not self.p.m2b_push_must_precede_red_candle else i - 1
            pushed = any(cs[m].h > rlvl for m in range(j + 1, last_push + 1))
            if pushed:
                recs.append(("Method 2B", {"recent_resistance": rlvl, "resistance_candle_index": j},
                             ["IRF-M2-001", "IRF-M2B-001", "IRF-M2B-002", "IRF-M2B-003"]))
        if not recs:
            return att, []
        att.fsm.to(State.SIGNAL_CONFIRMED, c.end, "; ".join(m for m, _, _ in recs) + " trigger on close")
        out = [self._confirmed(ctx, cs, i, m, b, irh, irl, _GLOBAL + sat + ["IRF-M2-005"], att.fsm.trace, [],
                               {**extra, "breakout_close": cs[b].c, "extension_index": att.e, "red_candle_index": att.r},
                               proposals=proposals)
               for m, extra, sat in recs]
        return None, out

    # ------------------------------------------------------------------ Method 3
    @implements("IRF-M3-001", "IRF-M3-002", "IRF-M3-003", "IRF-M3-004", "IRF-M3-005", "IRF-M3-006")
    def _method3(self, ctx, cs, i: int, irh: float, irl: float, gap_before: list[bool]) -> list[SignalRecord]:
        c = cs[i]
        n = self.p.m3_compression_n
        if not (is_red(c) and c.h > irh):  # IRF-M3-002
            return []
        if any(gap_before[i - n + 1:i + 1]) if i - n >= 0 else True:
            return []
        if not compression_ok(cs, i, irl, irh, self.p):  # IRF-M3-001
            return []
        fsm = SetupFSM(f"IRF sweep@{c.end:%H:%M}")
        fsm.to(State.SETUP_DETECTED, c.end, "red candle with high above IRH after compression inside range")
        share = wick_share_outside(c, irh)
        props = {"m3_compression_def": self.p.m3_compression_def, "m3_compression_n": n,
                 "m3_wick_share_band": self.p.m3_wick_share_band, "irf_support_def": self.p.irf_support_def}
        levels = {"IRH": irh, "IRL": irl, "wick_share_outside_irh": share}
        sat = _GLOBAL + ["IRF-M3-001", "IRF-M3-002"]
        if not wick_share_in_band(share, self.p):
            fsm.to(State.SETUP_INVALIDATED, c.end, f"wick share {share} outside band (IRF-M3-003/006)")
            return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-003"], [], SignalStatus.INVALIDATED,
                              "WICK_SHARE_OUT_OF_BAND", fsm.trace, props)]
        sat.append("IRF-M3-003")
        sup = recent_support(cs, 1, i, self.p)
        if sup is None:
            fsm.to(State.SETUP_INVALIDATED, c.end, "no recent support identifiable")
            return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-004"], [], SignalStatus.INVALIDATED,
                              "NO_RECENT_SUPPORT", fsm.trace, props)]
        levels["recent_support"] = sup[1]
        sat.append("IRF-M3-004")
        if not (c.c < sup[1]):  # IRF-M3-005 compulsory
            fsm.to(State.SETUP_INVALIDATED, c.end, f"close {c.c} not below support {sup[1]}")
            return [self._rec(ctx, c, "Method 3", Direction.SHORT, levels, sat, ["IRF-M3-005"], [], SignalStatus.INVALIDATED,
                              "SUPPORT_NOT_BROKEN(sweep alone is never enough)", fsm.trace, props)]
        fsm.to(State.SIGNAL_CONFIRMED, c.end, f"close {c.c} < support {sup[1]}")
        sat.append("IRF-M3-005")
        return [self._confirmed(ctx, cs, i, "Method 3", 0, irh, irl, sat, fsm.trace, [], levels, proposals=props)]

    # ------------------------------------------------------------------ record builders
    def _confirmed(self, ctx, cs, i, method, setup_start, irh, irl, sat, trace, flags, extra, proposals=None):
        c = cs[i]
        gj = most_recent_colour(cs, i, True)
        greens = [cs[j] for j in range(setup_start, i + 1) if is_green(cs[j])]
        levels: dict[str, Any] = {
            "IRH": irh, "IRL": irl, "entry_reference_price": c.c,
            "recent_green_high": cs[gj].h if gj is not None else None,
            "recent_green_close": cs[gj].c if gj is not None else None,
            "setup_green_high": max((g.h for g in greens), default=None),
            **extra,
        }
        # IRF-GLOBAL-004: trades per day / time window / re-arming are not defined in the guide, so no IRF signal
        # can be called verified. IRF-GLOBAL-005: concurrent methods are reported separately, never merged.
        return self._rec(ctx, c, method, Direction.SHORT, levels, sat, [], ["IRF-GLOBAL-004"], SignalStatus.CONFIRMED, None,
                         trace, proposals or {}, flags)

    def _setup_record(self, ctx, cs, att: _Attempt, why: str, i: int, status=SignalStatus.INVALIDATED):
        c = cs[att.b]
        return self._rec(ctx, c, "Method 1/2", Direction.SHORT, {"IRH": cs[0].h, "IRL": cs[0].l},
                         ["IRF-M1-001"], [], [], status, why, att.fsm.trace)
