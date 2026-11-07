"""Phase 5.2 (CANDIDATE, not active): IRF Method 2A with the support level taken from the FIRST red candle.

Author (telephone clarification): "IRF should use the first red candle that creates the support level, followed by entry."
The wording does not say whether the support level is that candle's LOW, its BODY LOW, or a broader local support, and the guide does not define it (IRF-M2A-001 is VERIFIED_QUALITATIVE: 'recent support = a pullback low
left behind by the extension'). Per the Phase 5.2 brief nothing is invented: this module offers the candidates as separately labelled, opt-in engines for the signal-only comparison. The active rule stays unresolved.

``IRFFirstRedStrategy`` is the frozen ``IRFStrategy`` with ONE change inside the Method 2 step: the support used by Confirmation A (``Method 2A``) comes from the first red candle (the engine already records it as
``_Attempt.r``: the first red candle at/after the extension) instead of the swing-low fractal:

  support_ref = "BASELINE_SWING"    the frozen behaviour (this branch is the original code; a regression test asserts identical output over the whole history)
  support_ref = "FIRST_RED_LOW"     support = low of the first red candle
  support_ref = "FIRST_RED_BODY_LOW" support = min(open, close) of the first red candle

Everything else is untouched: Method 1, Method 2B (resistance), Method 3, the extension and red-candle bookkeeping, the entry on the close of the breaking candle, and the 'first red candle' itself is never replaced by a
later candle. Scope note: only Method 2A uses a red-candle-created support in the guide; Method 2B's reference is a resistance (a push top) and Method 3's support is 'formed by the preceding candles', so the candidate
is NOT applied to them (see reports/phase5/phase52_author_rules/irf_first_red_candle_audit.md).
"""

from __future__ import annotations

from nifty_trading.strategies.base import SignalRecord, State
from nifty_trading.strategies.definitions import is_red, recent_resistance, recent_support
from nifty_trading.strategies.irf import _GLOBAL, IRFStrategy, _Attempt

SUPPORT_REFS = ("BASELINE_SWING", "FIRST_RED_LOW", "FIRST_RED_BODY_LOW")


class IRFFirstRedStrategy(IRFStrategy):
    """IRF with a selectable support reference for Method 2A (see the module docstring)."""

    def __init__(self, name=None, params=None, proposals=None, trade=None, support_ref: str = "BASELINE_SWING"):
        super().__init__(name, params, proposals, trade)
        if support_ref not in SUPPORT_REFS:
            raise ValueError(f"support_ref must be one of {SUPPORT_REFS}, got {support_ref!r}")
        self.support_ref = support_ref

    def _support_level(self, cs, att: _Attempt, b: int, i: int):
        """(candle index, level) of the support known BEFORE candle i. The first-red variants use only the red candle's own OHLC (known when it closed)."""
        if self.support_ref == "BASELINE_SWING" or att.r is None:
            return recent_support(cs, b + 1, i, self.p)
        r = cs[att.r]
        return (att.r, r.l) if self.support_ref == "FIRST_RED_LOW" else (att.r, min(r.o, r.c))

    # a copy of IRFStrategy._m2_step with exactly one line changed (the support lookup); no other statement differs
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
        if att.e is not None and att.r is None:
            first_ok = att.e if self.p.m2_red_may_be_extension_candle else att.e + 1
            if i >= first_ok and is_red(c):
                att.r = i
        if not may_confirm:
            return att, []
        recs: list[SignalRecord] = []
        proposals = {"irf_support_def": self.p.irf_support_def, "irf_resistance_def": self.p.irf_resistance_def,
                     "m2_extension_definition": self.p.m2_extension_definition, "phase52_support_ref": self.support_ref}
        red_ok = att.r is not None and (att.r <= i if self.p.m2a_break_may_be_red_candle else att.r < i)
        if red_ok and att.e is not None:
            sup = self._support_level(cs, att, b, i)  # <- the only changed line (baseline: recent_support(cs, b + 1, i, self.p))
            if sup is not None and c.c < sup[1]:
                recs.append(("Method 2A", {"recent_support": sup[1], "support_candle_index": sup[0], "support_ref": self.support_ref},
                             ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
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
                               {**extra, "breakout_close": cs[b].c, "extension_index": att.e, "red_candle_index": att.r}, proposals=proposals)
               for m, extra, sat in recs]
        return None, out
