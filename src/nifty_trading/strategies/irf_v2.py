"""IRF-V2-SUPPORT-BREAK (Phase 6.1): the owner-approved first-red-candle support-break rule as an explicit, testable reference-candle state machine.

Owner-approved rule (Phase 6.1 brief): identify the FIRST QUALIFYING RED CANDLE that establishes support; its LOWEST WICK PRICE is the support; SELL after a SUBSEQUENT COMPLETED candle CLOSES STRICTLY BELOW that support;
no retest is required; the signal exists when the breaking candle closes and the earliest fill is afterwards. Never: enter on a red candle alone, before support exists, on a wick-only break, on the reference candle itself,
replace the first reference candle with a later one, wait for a retest, or use a later candle to establish support.

SCOPE (from the IRF guide, verified in Phase 5.3 and again here): only Method 2A has a red-candle-created support ("a low formed by recent candles during the extension, such as a pullback low"). Method 1 needs no level,
Method 2B breaks a RESISTANCE (the red candle confirms, it does not create a level) and Method 3 breaks "the recent support formed by the preceding candles". Those methods keep their source-defined (frozen) mechanisms.

Separate layers (never mixed): OWNER_APPROVED entry logic (first red candle low, strict close below, no retest, 28-point number); SOURCE rules (breakout above IRH, extension, red candle, methods 1/2B/3, 35/60 exits);
PROVISIONAL geometric conventions (the red-candle SEARCH START = after the extension candle; the 28-point measure = nearest point of the signal candle's high-low range to the EMA(200), inclusive; the 28-point scope = all methods);
UNRESOLVED (the day's-low restriction: diagnostics only, NEVER applied).

The frozen Phase 3.6 ``IRFStrategy`` and the Phase 5.3 ``IRFPhase53Strategy`` are not modified; this class derives from the latter ONLY for the unchanged methods (1, 2B, 3, the EMA gate) and replaces the Method 2 step by the explicit machine below.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from nifty_trading.strategies.base import SignalRecord, State
from nifty_trading.strategies.definitions import is_red, recent_resistance
from nifty_trading.strategies.irf import _GLOBAL, _Attempt
from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy, ema_geometry

VERSION = "IRF-V2-SUPPORT-BREAK"
EPS = 1e-9


@dataclass
class SupportBreakMachine:
    """Reference-candle state machine of ONE Method 2 attempt (breakout candle ``b``). States: AWAIT_EXTENSION -> AWAIT_RED_CANDLE -> SUPPORT_SET -> SUPPORT_BROKEN. Causal: ``step(i)`` reads only candles <= i."""

    b: int
    red_search_start: str = "AFTER_EXTENSION"
    state: str = "AWAIT_EXTENSION"
    extension: int | None = None
    search_start: int | None = None
    reference: int | None = None
    support: float | None = None
    broken_at: int | None = None
    first_below: int | None = None
    ema_rejected: bool = False
    ema_rejection: dict | None = None
    trace: list[str] = field(default_factory=list)
    closes_after_reference: list[tuple[int, float, bool]] = field(default_factory=list)

    def step(self, cs, i: int, irh: float, ext_def: str, red_may_be_extension: bool) -> None:
        c = cs[i]
        if self.extension is None and i > self.b:
            ext = (c.h > cs[self.b].h) if ext_def == "E1" else (c.c > irh)
            if ext:
                self.extension = i
                self.trace.append(f"{c.end:%H:%M} extension candle (high {c.h})")
                if self.red_search_start == "AFTER_EXTENSION":
                    self.search_start = i if red_may_be_extension else i + 1
                    self.state = "AWAIT_RED_CANDLE"
        if self.search_start is None and self.red_search_start == "AFTER_BREAKOUT" and i > self.b:
            self.search_start = i
            self.state = "AWAIT_RED_CANDLE"
        if self.reference is None:
            if self.search_start is not None and i >= self.search_start and is_red(c):
                self.reference, self.support, self.state = i, c.l, "SUPPORT_SET"
                self.trace.append(f"{c.end:%H:%M} FIRST red candle O{c.o} H{c.h} L{c.l} C{c.c}: support = wick low {c.l}")
            return                                          # the reference candle can never be its own breaking candle
        if i > self.reference and self.broken_at is None:
            below = c.c < self.support - EPS                # strict close below the wick low; a wick-only break is not a break
            self.closes_after_reference.append((i, c.c, below))
            if below and self.first_below is None:
                self.first_below = i
            self.trace.append(f"{c.end:%H:%M} close {c.c} {'BELOW' if below else 'not below'} support {self.support}" + ("" if below else f" (low {c.l})"))
            if below:
                self.broken_at, self.state = i, "SUPPORT_BROKEN"


class IRFV2SupportBreakStrategy(IRFPhase53Strategy):
    """IRF-V2-SUPPORT-BREAK. Defaults: first-red-candle low (search after the extension), EMA(200) clearance 28 points (range distance, all methods)."""

    VERSION = VERSION

    def __init__(self, name=None, params=None, proposals=None, trade=None, red_search_start: str = "AFTER_EXTENSION", ema_min_clearance: float | None = 28.0,
                 ema_scope: str = "ALL_METHODS", ema_measure: str = "RANGE"):
        super().__init__(name, params, proposals, trade, support_ref="FIRST_RED_LOW", red_search_start=red_search_start, ema_min_clearance=ema_min_clearance, ema_scope=ema_scope, ema_measure=ema_measure)
        self.attempt_log: list[dict[str, Any]] = []          # every Method 2 attempt (read and cleared by the runner)
        self._machines: list[SupportBreakMachine] = []

    # ------------------------------------------------------------------ Method 2: explicit machine for 2A; the 2B logic and the EMA veto are the source / Phase 5.3 behaviour
    def _m2_step(self, ctx, cs, att: _Attempt, i: int, irh: float, irl: float, may_confirm: bool = True):
        c, b = cs[i], att.b
        if not hasattr(att, "sb"):
            att.sb = SupportBreakMachine(b, self.red_search_start)
            self._machines.append(att.sb)
            att.sb.trace.append(f"{cs[b].end:%H:%M} breakout close {cs[b].c} > IRH {irh} (attempt activated)")
        sb: SupportBreakMachine = att.sb
        if may_confirm and att.fsm.state is State.SETUP_DETECTED:
            att.fsm.to(State.WAITING_FOR_CONFIRMATION, c.end, "Method 1 window passed; Method 2 path (IRF-M2-004)")
        if self.p.m2_expiry_candles is not None and i - b > self.p.m2_expiry_candles:
            att.fsm.to(State.SETUP_INVALIDATED, c.end, "M2_EXPIRED(proposal)")
            return None, [self._setup_record(ctx, cs, att, "M2_EXPIRED", i)]
        sb.step(cs, i, irh, self.p.m2_extension_definition, self.p.m2_red_may_be_extension_candle)
        att.e, att.r = sb.extension, sb.reference                      # keep the frozen bookkeeping fields consistent (used by the record builders / diagnostics)
        if not may_confirm:
            return att, []
        recs: list[tuple[str, dict, list[str]]] = []
        proposals = {"irf_version": VERSION, "support_rule": "OWNER_APPROVED: first red candle wick low; strict close below; no retest", "red_search_start": f"{self.red_search_start} (PROVISIONAL)",
                     "ema_min_clearance": self.ema_min_clearance, "ema_convention": "PROVISIONAL_EMA_RANGE_DISTANCE" if self.ema_min_clearance is not None else None, "ema_scope": self.ema_scope,
                     "irf_resistance_def": self.p.irf_resistance_def, "m2_extension_definition": self.p.m2_extension_definition, "days_low_restriction": "NOT_APPLIED (PENDING_OWNER_DEFINITION)"}
        if sb.broken_at == i and sb.extension is not None:
            ref = cs[sb.reference]
            recs.append(("Method 2A", {"recent_support": sb.support, "support_candle_index": sb.reference, "support_ref": "FIRST_RED_LOW", "first_red_candle_start": f"{ref.start:%H:%M}", "first_red_candle_low": ref.l,
                                       "first_red_candle_ohlc": f"{ref.o}/{ref.h}/{ref.l}/{ref.c}", "candles_between_reference_and_break": i - sb.reference - 1, "support_break_candle_start": f"{c.start:%H:%M}",
                                       "support_break_close": c.c, "close_below_support_points": round(sb.support - c.c, 4)},
                         ["IRF-M2-001", "IRF-M2-002", "IRF-M2-003", "IRF-M2A-001", "IRF-M2A-002"]))
        res = recent_resistance(cs, b, i, self.p)
        if res is not None and is_red(c) and c.c < res[1]:
            j, rlvl = res
            last_push = i if not self.p.m2b_push_must_precede_red_candle else i - 1
            if any(cs[m].h > rlvl for m in range(j + 1, last_push + 1)):
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
                        self.rejections.append({"date": str(ctx.date), **info})   # rejected: the attempt stays alive; the SAME reference support stays in force and a later close below it may still qualify
                        if m == "Method 2A":
                            sb.ema_rejected, sb.ema_rejection = True, info
                            sb.state = "SUPPORT_SET"                                      # the break was vetoed: the support stays in force                                      # allow a later candle to be the first VALID close below support (the machine already recorded this close as 'below')
                            sb.broken_at = None
                        continue
                    flags = [f"PHASE53_EMA_{self.ema_measure}_DISTANCE={info.get('distance', 'NA') if info.get('ema_available') else 'EMA_UNAVAILABLE'}"]
                kept.append((m, extra, sat))
            recs = kept
            if not recs:
                return att, []
        att.fsm.to(State.SIGNAL_CONFIRMED, c.end, "; ".join(m for m, _, _ in recs) + " trigger on close")
        out = [self._confirmed(ctx, cs, i, m, b, irh, irl, _GLOBAL + sat + ["IRF-M2-005"], att.fsm.trace + sb.trace, list(flags),
                               {**extra, "breakout_close": cs[b].c, "extension_index": sb.extension, "red_candle_index": sb.reference}, proposals=proposals) for m, extra, sat in recs]
        return None, out

    # ------------------------------------------------------------------ diagnostics on every confirmed signal (never used to accept or reject)
    def _scan(self, ctx, cs, gap_before) -> list[SignalRecord]:
        self._machines: list[SupportBreakMachine] = []
        out = super()._scan(ctx, cs, gap_before)
        sig_idx = {r.reference_levels.get("red_candle_index") for r in out if r.signal_status == "CONFIRMED" and r.method == "Method 2A"}
        for sb in self._machines:                           # one audit row per Method 2 attempt, including attempts that never produced a signal
            ref = cs[sb.reference] if sb.reference is not None else None
            self.attempt_log.append({"date": str(ctx.date), "breakout_candle_start": f"{cs[sb.b].start:%H:%M}", "breakout_close": cs[sb.b].c, "irh": cs[0].h, "extension_candle_start": f"{cs[sb.extension].start:%H:%M}" if sb.extension is not None else "",
                                     "search_start_rule": self.red_search_start, "reference_candle_start": f"{ref.start:%H:%M}" if ref else "", "reference_ohlc": f"{ref.o}/{ref.h}/{ref.l}/{ref.c}" if ref else "", "support_wick_low": sb.support,
                                     "closes_after_reference": " ".join(f"{cs[n].start:%H:%M}:{px}{'<' if b else ''}" for n, px, b in sb.closes_after_reference),
                                     "first_close_below_support": f"{cs[sb.first_below].start:%H:%M}" if sb.first_below is not None else "",
                                     "ema_28_rejected_a_break": sb.ema_rejected, "ema_rejection_distance": (sb.ema_rejection or {}).get("distance", ""), "signal_confirmed_from_this_attempt": sb.reference in sig_idx, "final_state": sb.state})
        k = self.trade.t1_points
        for r in out:
            if r.signal_status != "CONFIRMED":
                continue
            i = next((n for n, c in enumerate(cs) if c.end == r.signal_timestamp), None)
            if i is None:
                continue
            c = cs[i]
            e = ctx.candles["ema200_5m"].iloc[i]
            d: dict[str, Any] = {"irf_version": VERSION}
            if e == e and e is not None:
                e = float(e)
                g = ema_geometry(c.h, c.l, c.c, e)
                entry_ref, t1 = c.c, c.c - k
                d.update({"ema_at_confirmation": e, "ema_relation_to_confirmation_candle": g["relation"], "ema_range_clearance": g["range_clearance"], "ema_close_distance": g["close_distance"],
                          "entry_reference_price": entry_ref, "target1_level": t1, "ema_between_entry_and_t1": bool(min(entry_ref, t1) <= e <= max(entry_ref, t1)),
                          "ema_below_entry_reference": e < entry_ref})
                ri = r.reference_levels.get("red_candle_index")
                if r.method == "Method 2A" and ri is not None:
                    re_ = ctx.candles["ema200_5m"].iloc[ri]
                    rc = cs[ri]
                    gr = ema_geometry(rc.h, rc.l, rc.c, float(re_))
                    d.update({"ema_at_reference": float(re_), "ema_relation_to_reference_candle": gr["relation"], "ema_range_clearance_reference": gr["range_clearance"]})
            prior_low = min((x.l for x in cs[:i]), default=None)
            d.update({"running_low_through_signal_candle": min(x.l for x in cs[:i + 1]), "running_low_before_signal_candle": prior_low, "signal_close_below_prior_running_low": (prior_low is not None and c.c < prior_low),
                      "days_low_diagnostic_note": "causal running low only; the day's-low restriction is NOT applied (PENDING_OWNER_DEFINITION)"})
            r.reference_levels.update(d)
        return out
