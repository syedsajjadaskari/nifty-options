"""IRF V3 cycle enumerators for the PORTFOLIO adapter (Phase 7.1). They enumerate EVERY completed breakout->failure cycle (the Phase 7.0 modules stop at the first) and carry the Method 2 research options.
With default options the FIRST cycle equals the Phase 7.0 ``irf_v3.method1/method2`` result on every session (tested). Candles need ``start, end, open, high, low, close`` (irf_v3 ``Candle`` or any duck type).

Method 2 options (all OFF by default = Phase 7.0 headline, 'M2-A persistent setup'):
  invalidate   NONE | BEFORE_B | BEFORE_COMPLETION
               BEFORE_B          a close below Level A before Level B is marked kills the setup (the Phase 7.0 sensitivity)
               BEFORE_COMPLETION a close below Level A at any point before the sequence completes kills the setup. The completing candle itself is evaluated FIRST: a candle that is also the failure
                                 candle (close below B after the second breakout) completes the setup and is not 'before' completion.
  rearm        False: the invalidation is permanent for the day (M2-B). True: the setup resets and a new rally breakout above A may start a NEW setup (new first red candle, new Level B) (M2-B-rearm)
  min_margin   the failure close must be at least this many points below Level B (candidate, NOT a source rule)
  bearish_failure  the failure candle must itself be red (close < open) (candidate)
  extra_confirmation  one further completed candle must also close below Level B after the first break (candidate)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import time

FIRST = time(9, 15)


@dataclass(frozen=True)
class M2Opts:
    invalidate: str = "NONE"
    rearm: bool = False
    min_margin: float = 0.0
    bearish_failure: bool = False
    extra_confirmation: bool = False

    def tag(self) -> str:
        t = []
        if self.invalidate != "NONE":
            t.append(f"INV_{self.invalidate}" + ("_REARM" if self.rearm else "_PERM"))
        if self.min_margin:
            t.append(f"MARGIN{self.min_margin:g}")
        if self.bearish_failure:
            t.append("BEARISH")
        if self.extra_confirmation:
            t.append("EXTRA")
        return "+".join(t) or "M2-A"


def m1_cycles(cs) -> list[dict]:
    """Method 1: every completed (breakout, failure) pair. Closes exactly on the level are ignored."""
    if not cs or cs[0].start.time() != FIRST:
        return []
    lvl, out, brk = cs[0].high, [], None
    for i in range(1, len(cs)):
        c = cs[i]
        if brk is None:
            if c.close > lvl:
                brk = i
        elif c.close < lvl:
            out.append({"method": "M1", "cycle": len(out) + 1, "fail_idx": i, "breakout_idx": brk, "level": lvl, "level_a": lvl, "ref_idx": 0, "setup_idx": brk, "second_idx": None})
            brk = None
    return out


def m2_cycles(cs, o: M2Opts | None = None) -> list[dict]:  # noqa: C901
    """Method 2: every completed cycle. States: A (await rally breakout) -> RED (await first red candle) -> B2 (await second breakout) -> FAIL (await failure) [-> EXTRA] ; DEAD after a permanent invalidation."""
    o = o or M2Opts()
    if not cs or cs[0].start.time() != FIRST:
        return []
    A = cs[0].high
    out: list[dict] = []
    state, b_idx, r_idx, B, s_idx, first_break = "A", None, None, None, None, None

    def emit(i: int, fb: int) -> None:
        out.append({"method": "M2", "cycle": len(out) + 1, "fail_idx": i, "breakout_idx": b_idx, "level": B, "level_a": A, "ref_idx": r_idx, "setup_idx": s_idx, "second_idx": s_idx, "first_break_idx": fb})

    for i in range(1, len(cs)):
        c = cs[i]
        if state == "DEAD":
            continue
        if state == "FAIL" and c.close < B and (B - c.close) >= o.min_margin - 1e-9 and ((not o.bearish_failure) or c.close < c.open):
            if o.extra_confirmation:
                state, first_break = "EXTRA", i
            else:
                emit(i, i)
                state = "B2"
            continue
        if state == "EXTRA":
            if c.close < B:
                emit(i, first_break)
                state = "B2"
            else:
                state = "FAIL"          # the first break was not confirmed by the extra candle: the setup stays armed
            continue
        if o.invalidate != "NONE" and state in ("RED", "B2", "FAIL") and c.close < A and not (o.invalidate == "BEFORE_B" and state != "RED"):
            if o.rearm:
                state, b_idx, r_idx, B, s_idx = "A", None, None, None, None
            else:
                state = "DEAD"
            continue
        if state == "A":
            if c.close > A:
                b_idx, state = i, "RED"
        elif state == "RED":
            if c.close < c.open:
                r_idx, B, state = i, c.open, "B2"
        elif state == "B2":
            if c.close > B:
                s_idx, state = i, "FAIL"
    return out
