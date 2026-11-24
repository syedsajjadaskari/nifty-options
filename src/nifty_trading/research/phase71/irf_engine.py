"""IRF V3 as a signal engine for the FROZEN five-strategy controller (Phase 7.1 research adapter; never a paper-trading component).

Feeds ONLY the ENTRY decisions of the Phase 7.0 IRF V3 methods (Method 1 high-breakout failure, Method 2 first-red-candle resistance failure) into the shared controller: the portfolio exit model (stop 35,
T1 +27 on three lots, T2 +60 on three lots, post-T1 stop entry+6, forced exit before 15:15) is applied by the controller. The standalone SL35/SL40 Phase 7.0 exit ledgers are NOT used.
Every completed cycle of each method is emitted as a CONFIRMED record (``cycle_no``); the controller keeps the first valid signal of the day, so later cycles matter only when an earlier one is rejected
(by an opt-in EMA gate) or not fillable. Method labels 'V3-M1' / 'V3-M2'; the same-minute tie goes to the lower method name by the controller's existing convention (no new priority is introduced).
"""

from __future__ import annotations

import pandas as pd

from nifty_trading.research.irf_v3.models import Candle as V3Candle
from nifty_trading.research.phase71.irf_cycles import M2Opts, m1_cycles, m2_cycles
from nifty_trading.strategies.base import Direction, SignalEngine, SignalRecord, SignalStatus
from nifty_trading.strategies.definitions import to_candles

VERSION = "IRF-V3-PORTFOLIO-ADAPTER"


class IRFV3Strategy(SignalEngine):
    STRATEGY = "IRF"
    METHODS = ("V3-M1", "V3-M2")
    REQUIRES_PREVIOUS_SESSION = False

    def __init__(self, m2: M2Opts | None = None, name=None, params=None, proposals=None, trade=None):
        super().__init__(name or "IRF-V3", params, proposals, trade)
        self.m2 = m2 or M2Opts()
        self.log: list[dict] = []

    def _scan(self, ctx, cs, gap_before):  # not used: evaluate_session is overridden
        return []

    def evaluate_session(self, ctx) -> list[SignalRecord]:
        block = self._precheck(ctx)
        if block:
            return [self._blocked(ctx, block)]
        cs = to_candles(ctx.candles)
        if not cs:
            return [self._blocked(ctx, "NO_COMPLETE_5M_CANDLES")]
        v3 = [V3Candle(pd.Timestamp(c.start), pd.Timestamp(c.end), c.o, c.h, c.l, c.c) for c in cs]
        out: list[SignalRecord] = []
        for cyc in m1_cycles(v3) + m2_cycles(v3, self.m2):
            c = cs[cyc["fail_idx"]]
            label = "V3-M1" if cyc["method"] == "M1" else "V3-M2"
            ref = cs[cyc["ref_idx"]]
            levels = {"irf_version": VERSION, "irf_v3_method": cyc["method"], "cycle_no": cyc["cycle"], "level_a": cyc["level_a"], "level_b": cyc["level"] if cyc["method"] == "M2" else None,
                      "reference_level": cyc["level"], "initial_range_high": cs[0].h, "initial_range_low": cs[0].l, "reference_candle_start": f"{ref.start:%H:%M}", "breakout_candle_start": f"{cs[cyc['breakout_idx']].start:%H:%M}",
                      "setup_candle_start": f"{cs[cyc['setup_idx']].start:%H:%M}", "second_breakout_start": f"{cs[cyc['second_idx']].start:%H:%M}" if cyc.get("second_idx") is not None else "",
                      "signal_candle_start": f"{c.start:%H:%M}", "entry_reference_price": c.c, "m2_options": self.m2.tag() if cyc["method"] == "M2" else "", "standalone_irf_v3_exit_ledger_used": False}
            rec = self._rec(ctx, c, label, Direction.SHORT, levels, [], [], [], SignalStatus.CONFIRMED, None,
                            [f"{c.end:%H:%M} IRF V3 {cyc['method']} cycle {cyc['cycle']}: close {c.c} confirms the failure of level {cyc['level']}"],
                            {"irf_v3": "Phase 7.0 methods (entry decision only)", "m2_options": self.m2.tag()}, ["IRF_V3_RESEARCH_CONFIGURATION"])
            rec.verification_status = "RESEARCH_VARIANT"
            rec.execution_config["entry_rule_status"] = "RESEARCH_VARIANT"
            out.append(rec)
        return out
