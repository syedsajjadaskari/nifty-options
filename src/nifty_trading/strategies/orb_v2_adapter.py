"""Adapter that feeds the Phase 6.0 ORB V2 ENTRY signals into the five-strategy portfolio controller (Phase 6.2).

Only the ENTRY decision of ORB V2 is imported: a CONFIRMED ``SignalRecord`` for strategy "ORB" at 09:20 (the close of the 09:15-09:20 candle). The standalone 30/60 exit ledger of Phase 6.0 is NOT used: the shared
controller and exit policy apply the portfolio exit model (ORB stop 30, T1 27 on three lots, T2 60 on three lots, post-T1 stop entry -/+ 6, forced exit before 15:15). The decision itself comes from
``research.orb_v2.signal_engine.evaluate_session`` (independent of the legacy ORB engines) on the same 5paisa one-minute data; the opening candle is cross-checked against the controller's own session context.

Configuration: ORB-V2-A is the provisional reference (no later owner selection exists). Its unresolved source conventions travel with every signal (``proposals_used`` / ``reference_levels``).
"""

from __future__ import annotations

from nifty_trading.data.sessions import SessionContext
from nifty_trading.research.orb_v2 import config as OC
from nifty_trading.research.orb_v2 import data_access as DA
from nifty_trading.research.orb_v2 import signal_engine as SE
from nifty_trading.strategies.base import Direction, SignalEngine, SignalRecord, SignalStatus
from nifty_trading.strategies.definitions import to_candles

UNRESOLVED = ("OD-1 data feed (5paisa vs secondary)", "OD-2 break definition (close beyond vs candle crosses)", "OD-3 inner-level construction / meaning of 'major'", "OD-4 hammer / shooting-star proportions and engulfing reference at 09:20",
              "OD-5 wick rule vs rulebook Examples 2/3", "OD-6 gap limit 250 vs 300", "OD-7 entry price (rulebook: close of the 9:15 candle; used: first executable fill)", "OD-15 gap reference close")


def build_decisions(inp, cfg: OC.OrbV2Config) -> dict:
    """{date: (Decision, SessionData)} for every session ORB V2 can assemble (Phase 6.0 data access, same sessions as the controller)."""
    DA.index_positions(inp)
    out = {}
    for d in DA.evaluable_dates(inp):
        sd, why = DA.session_data(inp, d)
        out[d] = (SE.evaluate_session(sd, cfg), sd) if sd is not None else (None, why)
    return out


class ORBV2Strategy(SignalEngine):
    STRATEGY = "ORB"
    METHODS = ("ORB-V2",)
    REQUIRES_PREVIOUS_SESSION = False

    def __init__(self, decisions: dict, cfg: OC.OrbV2Config, name=None, params=None, proposals=None, trade=None):
        super().__init__(name or "ORB-V2", params, proposals, trade)
        self.decisions = decisions
        self.cfg = cfg
        self.rejections: list[dict] = []     # sessions on which ORB V2 evaluated and rejected (read by the runner)
        self.integration_checks: list[dict] = []

    def _scan(self, ctx, cs, gap_before):  # not used: evaluate_session is overridden
        return []

    def evaluate_session(self, ctx: SessionContext) -> list[SignalRecord]:
        block = self._precheck(ctx)
        if block:
            return [self._blocked(ctx, block)]
        item = self.decisions.get(ctx.date)
        if item is None or item[0] is None:
            return [self._blocked(ctx, f"ORB_V2_NOT_EVALUABLE:{item[1] if item else 'NO_SESSION_DATA'}")]
        dec, sd = item
        cs = to_candles(ctx.candles)
        if not cs:
            return [self._blocked(ctx, "NO_COMPLETE_5M_CANDLES")]
        c = cs[0]
        o = sd.opening
        same = abs(c.o - o["open"]) < 1e-9 and abs(c.h - o["high"]) < 1e-9 and abs(c.l - o["low"]) < 1e-9 and abs(c.c - o["close"]) < 1e-9
        ok_time = f"{c.start:%H:%M}" == "09:15" and f"{c.end:%H:%M}" == "09:20"
        self.integration_checks.append({"date": str(ctx.date), "opening_candle_equals_context": same, "signal_candle_09_15_to_09_20": ok_time, "ema_ctx_minus_orbv2": float(c.ema - dec.detail["ema_now"])})
        if not dec.signal:
            self.rejections.append({"date": str(ctx.date), "failed": ";".join(dec.failed), **{k: dec.detail.get(k) for k in ("gap_points", "ema_scenario", "levels_broken_n", "patterns_matched", "wrong_side_wick_pct", "colour")}})
            return []
        d = dec.detail
        direction = Direction.LONG if dec.signal == "BUY" else Direction.SHORT
        levels = {"orb_v2_config_id": self.cfg.config_id, "orb_v2_config_sha256": self.cfg.to_manifest()["config_sha256"], "orb_v2_direction": dec.signal, "signal_candle_start": f"{c.start:%H:%M}",
                  "primary_level": d.get("primary_level"), "primary_level_kind": d.get("primary_level_kind"), "levels_broken": d.get("levels_broken_n"), "qualifying_category": d.get("qualifying_category"),
                  "level_construction": self.cfg.inner_method, "ema_now": d.get("ema_now"), "ema_scenario": d.get("ema_scenario"), "gap_points": d.get("gap_points"), "gap_limit": self.cfg.max_gap_points,
                  "patterns_matched": d.get("patterns_matched"), "colour": d.get("colour"), "body_pct": d.get("body_pct"), "upper_wick_pct": d.get("upper_wick_pct"), "lower_wick_pct": d.get("lower_wick_pct"),
                  "wrong_side_wick_pct": d.get("wrong_side_wick_pct"), "prev_high": d.get("prev_high"), "prev_low": d.get("prev_low"), "prev_close": d.get("prev_close"), "entry_reference_price": c.c,
                  "standalone_30_60_exit_ledger_used": False, "unresolved_assumptions": "; ".join(UNRESOLVED)}
        rec = self._rec(ctx, c, "ORB-V2", direction, levels, [], [], [], SignalStatus.CONFIRMED, None,
                        [f"09:20 ORB V2 ({self.cfg.config_id}) {dec.signal}: all conditions passed on the completed 09:15-09:20 candle (no failed condition)"],
                        {"orb_v2_config": self.cfg.config_id, "provisional_reference": "ORB-V2-A is a clearly labelled provisional reference (no owner selection exists)", "unresolved": list(UNRESOLVED)}, ["ORB_V2_PROVISIONAL_CONFIGURATION"])
        rec.verification_status = "RESEARCH_VARIANT"                      # never VERIFIED: the level construction and pattern conventions are provisional
        rec.execution_config["entry_rule_status"] = "RESEARCH_VARIANT"
        if not (same and ok_time):
            rec.flags.append("ORB_V2_OPENING_CANDLE_DIFFERS_FROM_CONTEXT")
        return [rec]
