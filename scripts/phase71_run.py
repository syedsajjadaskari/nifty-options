"""Phase 7.1 driver, stage 'portfolio': the predeclared configurations through the FROZEN controller / exit policy on both windows (synthetic index P&L), plus the all-strategy EMA signal diagnostics.
Nothing is selected; no configuration is promoted; no frozen file is edited. Outputs to a scratch cache (pickles) and are tabulated by phase71_tables.py.
Usage: python scripts/phase71_run.py portfolio [A|B]"""

from __future__ import annotations

import json
import pickle
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase60_common as P60  # noqa: E402
import phase61_common as C61  # noqa: E402

SP = Path("/private/tmp/claude-501/-Users-syedaskari-algo-nifty-options/5505d9ee-8ad7-4481-ab19-61c164361bc6/scratchpad")
C61.CACHE = SP / "p71cache"
from nifty_trading.core.exit_policy import evaluate_exit  # noqa: E402, F401
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase31 as P31  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase62 as X2  # noqa: E402
from nifty_trading.research.orb_v2 import config as OC  # noqa: E402
from nifty_trading.research.phase71 import ema_rule as ER  # noqa: E402
from nifty_trading.research.phase71.irf_cycles import M2Opts  # noqa: E402
from nifty_trading.research.phase71.irf_engine import IRFV3Strategy  # noqa: E402
from nifty_trading.strategies import orb_v2_adapter as OA  # noqa: E402
from nifty_trading.strategies.first_eligible_phase53 import (  # noqa: E402
    PDRFirstEligibleStrategy,
    PDSFirstEligibleStrategy,
)
from nifty_trading.strategies.irf_v2 import IRFV2SupportBreakStrategy  # noqa: E402
from nifty_trading.strategies.pdr_variants import PDRVariantStrategy  # noqa: E402
from nifty_trading.strategies.pds import PDSStrategy  # noqa: E402
from nifty_trading.strategies.pds_variants import PDSSecondConfirmationStrategy  # noqa: E402
from nifty_trading.strategies.selection import fill_from_next_bar  # noqa: E402
from nifty_trading.strategies.strength_gate import StrengthGateEngine  # noqa: E402

SC = P.combined_scenario("BODY_BASED_PHASE36")
M2_PERM = M2Opts("BEFORE_COMPLETION", rearm=False)
M2_REARM = M2Opts("BEFORE_COMPLETION", rearm=True)
CONFIGS = {
    "A": "A - existing frozen combined configuration (Phase 3.6 frozen engines; Phase 6.2 key A)",
    "B": "B - IRF V3 (Method 1 + Method 2, Phase 7.0) + ORB V2-A + PDR/PDS first-eligible + RF; no universal EMA rule",
    "C": "C - B with Method 2 invalidated permanently by a close below Level A before the sequence completes (M2-B)",
    "C2": "C2 - B with Method 2 invalidation that RE-ARMS (a new rally breakout may start a new setup)",
    "D": "D - B + universal EMA-1: minimum 27-point |close - EMA| (all five strategies)",
    "E": "E - B + universal EMA-2: minimum 27-point candle-range clearance (all five strategies)",
    "F": "F - B + universal EMA-3: maximum 27-point |close - EMA| proximity (all five strategies)",
    "K": "K - B + EMA-4: 28-point candle-range clearance (Phase 5.3 historical convention, comparator; all five strategies)",
    "L": "L - B + EMA-5: target-side (EMA not within 27 points in the trade's path; handwritten AC13/AC18 reading; all five strategies)",
    "G1": "G1 - B with PDR-B1 (first green candle after the retest, no ceiling requirement; owner confirmation required)",
    "G2": "G2 - B with PDR-B2 (first green candle, retest candle may confirm, no ceiling requirement)",
    "G3": "G3 - B with PDR-C (first green candle closing above the zone ceiling, retest candle may confirm)",
    "H": "H - B with PDR-D (second eligible confirmation)",
    "I1": "I1 - B with the frozen numeric-threshold PDS (source-consistent reference)",
    "I2": "I2 - B with PDS second confirmation (Methods 1/2 only)",
    "J60": "J60 - B + candle-strength gate 60% body (Phase 6.5 variant B)",
    "J70": "J70 - B + candle-strength gate 70% body (Phase 6.5 variant C)",
    "JD": "JD - B + pattern-aware candle-strength gate (Phase 6.5 variant D)",
}
EMA_OF = {"D": "EMA-1", "E": "EMA-2", "F": "EMA-3", "K": "EMA-4", "L": "EMA-5"}


def build_engines(key: str, orb) -> list:
    if key == "A":
        return X2.engines_for("A", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision, orb)
    base = X2.engines_for("C", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision, orb)
    m2 = M2_PERM if key == "C" else (M2_REARM if key == "C2" else M2Opts())
    out = []
    for e in base:
        if isinstance(e, IRFV2SupportBreakStrategy):
            e = IRFV3Strategy(m2, proposals=SC.proposals, trade=SC.trade)
        elif key.startswith("G") or key == "H":
            if isinstance(e, PDRFirstEligibleStrategy):
                e = PDRVariantStrategy({"G1": "B1", "G2": "B2", "G3": "C", "H": "D"}[key], proposals=SC.proposals, trade=SC.trade, revision=e.rev)
        elif key == "I1" and isinstance(e, PDSFirstEligibleStrategy):
            e = PDSStrategy(proposals=SC.proposals, trade=SC.trade)
        elif key == "I2" and isinstance(e, PDSFirstEligibleStrategy):
            e = PDSSecondConfirmationStrategy(proposals=SC.proposals, trade=SC.trade)
        out.append(e)
    if key in EMA_OF:
        out = [ER.EmaGateEngine(e, EMA_OF[key]) for e in out]
    if key in ("J60", "J70", "JD"):
        out = [StrengthGateEngine(e, {"J60": "B", "J70": "C", "JD": "D"}[key]) for e in out]
    return out


def sig_rows(tls) -> list[dict]:
    rows = []
    for d, tl in tls.items():
        used = {id(tr.signal): tr for tr in tl.result.trades}
        for r in tl.records:
            if r.signal_status != "CONFIRMED":
                continue
            lv = r.reference_levels
            rows.append({"date": str(d), "time": f"{r.signal_timestamp:%H:%M}", "candle_start": f"{r.signal_candle_start:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction,
                         "ref_close": r.signal_candle_close, "executed": id(r) in used, "cycle_no": lv.get("cycle_no", ""), "execution_status": r.execution_config.get("execution_status", ""),
                         "within_13_00": f"{r.signal_timestamp:%H:%M}" <= "13:00", "level": lv.get("reference_level") or lv.get("primary_level") or lv.get("recent_support") or lv.get("recent_resistance") or ""})
    return rows


def ema_rows(tls, ctxs, bars) -> list[dict]:
    """EMA diagnostics for EVERY confirmed signal of the baseline portfolio (all five strategies), measured at the confirmation candle, the setup candle (when the record names one) and the entry."""
    out = []
    for d, tl in tls.items():
        ctx = ctxs[d]
        cand = ctx.candles.set_index("bar_start")
        for r in tl.records:
            if r.signal_status != "CONFIRMED" or r.signal_candle_start not in cand.index:
                continue
            lv = r.reference_levels
            row = cand.loc[r.signal_candle_start]
            ema_c = float(row["ema200_5m"]) if row["ema200_5m"] == row["ema200_5m"] else None
            fill = fill_from_next_bar(bars.get(d, []), r.signal_timestamp)
            entry = float(fill[0]) if fill else None
            g = ER.geometry(r.direction, float(row["open"]), float(row["high"]), float(row["low"]), float(row["close"]), ema_c)   # entry reference = the confirming candle's close (causal at signal time; identical to the gate)
            rec = {"date": str(d), "time": f"{r.signal_timestamp:%H:%M}", "candle_start": f"{r.signal_candle_start:%H:%M}", "strategy": r.strategy, "method": r.method, "direction": r.direction, "cycle_no": lv.get("cycle_no", ""),
                   "within_13_00": f"{r.signal_timestamp:%H:%M}" <= "13:00", "entry_price": entry, **{k: g.get(k) for k in ("ema_available", "ema", "open", "high", "low", "close", "close_minus_ema", "abs_close_dist", "range_clearance", "relation",
                   "candle_touches_or_crosses_ema", "entry_minus_ema", "path_room_to_ema", "ema_between_entry_and_t1")}}
            for cfg, (it, n) in ((k, v) for k, v in ER.CONFIG_OF.items() if v):
                rec[f"{cfg}_{it}_{n:g}"] = ER.evaluate(it, n, g)[0]
            for it in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE"):
                for n in (27.0, 28.0):
                    rec[f"R_{it}_{n:g}"] = ER.evaluate(it, n, g)[0]
            # setup-candle timing (only when the engine records one)
            sc = lv.get("setup_candle_start") or (lv.get("interaction_candle_start") and f"{lv['interaction_candle_start']:%H:%M}" if hasattr(lv.get("interaction_candle_start"), "hour") else lv.get("interaction_candle_start"))
            rc = lv.get("reference_candle_start")
            for tag, cs_ in (("SETUP", sc), ("REFERENCE", rc)):
                cell = None
                if cs_:
                    t = next((i for i in cand.index if f"{i:%H:%M}" == str(cs_)), None)
                    if t is not None:
                        rw = cand.loc[t]
                        e2 = float(rw["ema200_5m"]) if rw["ema200_5m"] == rw["ema200_5m"] else None
                        g2 = ER.geometry(r.direction, float(rw["open"]), float(rw["high"]), float(rw["low"]), float(rw["close"]), e2, float(row["close"]))
                        cell = {f"{k}": ER.evaluate(k, 27.0, g2)[0] for k in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE")}
                for k in ("MIN_CLOSE", "MIN_RANGE", "MAX_CLOSE", "TARGET_SIDE"):
                    rec[f"{tag}_{k}_27"] = cell[k] if cell else "NOT_RECORDED"
            ori = lv.get("ema_scenario")
            if ori is not None:
                rec["orb_ema_scenario"] = ori
            out.append(rec)
    return out


def run_config(key, ctxs, bars, orb):
    engines = build_engines(key, orb)
    saved = (P31.make_engines, P.make_engines)
    P31.make_engines = lambda p, t, pe="LEGACY", pr=None, _e=engines: _e
    try:
        tls = P31.run_timelines(SC, ctxs, bars)
    finally:
        P31.make_engines, P.make_engines = saved
    led = X.ledger_rows(key, tls)
    days = {str(d): {"final_state": tl.result.final_state.value, "n_trades": len(tl.result.trades)} for d, tl in tls.items()}
    res = {"ledger": led, "signals": sig_rows(tls), "days": days, "gate_log": [x for e in engines for x in getattr(e, "log", [])]}
    return res, tls


def portfolio(windows: str) -> None:
    for w in windows:
        t0 = time.time()
        ctxs, infos, bars, cal, label = C61.window_data(w)
        inp = P60.get_window(w, "5P")
        orb = OA.ORBV2Strategy(OA.build_decisions(inp, OC.A), OC.A, proposals=SC.proposals, trade=SC.trade)
        print(w, "data ready", round(time.time() - t0), "s", flush=True)
        for key in CONFIGS:
            f = SP / "p71cache" / f"run71_{w}_{key}.pkl"
            if f.exists():
                continue
            res, tls = run_config(key, ctxs, bars, orb)
            if key == "B":
                res["ema_rows"] = ema_rows(tls, ctxs, bars)
            f.write_bytes(pickle.dumps(res, protocol=4))
            print(w, key, len(res["ledger"]), round(sum(float(r["gross_pnl_rs"]) for r in res["ledger"])), round(time.time() - t0), "s", flush=True)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "portfolio"
    if stage == "portfolio":
        portfolio(sys.argv[2] if len(sys.argv) > 2 else "AB")
    (SP / "p71cache" / "configs.json").write_text(json.dumps(CONFIGS, indent=1))
