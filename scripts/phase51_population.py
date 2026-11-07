"""Phase 5.1: what each candidate rule WOULD change in the Phase 3.6 history (signal level, counts and identities only - no P&L is computed or compared).

1. ORB colour clarification (implemented as an OPT-IN variant, ``strategies/orb_colour.py``): every ORB record whose status changes across all evaluated sessions, and the executed-trade identities that change when the
   frozen controller is re-run with the variant (same engines otherwise).
2. NOT implemented, counts only: for every executed Phase 3.6 IRF trade, the measurements behind the author's remarks (EMA space below the entry < 27, entry candle closing below the session low so far, entry-candle body
   < 60 / < 50 / < 40 percent) and, for every executed PDR / PDS trade, whether an earlier 'first green / first red candle at the zone' exists. These show how far each remark would reach; they are not evidence for adopting it.
Writes before_after_signal_differences.csv and population_impact.json under reports/phase5/phase51_author_corrections/.
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase51_diagnostics as D  # noqa: E402
import phase51_evidence as E  # noqa: E402

from nifty_trading.core.execution_eligibility import bars_from_frame  # noqa: E402
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase51 as F51  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def main() -> int:
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    rows: list[dict] = []
    # ------------------------------------------------------------------ 1. ORB colour variant
    sig_diff = F51.orb_signal_differences(ctxs, sc)
    for r in sig_diff:
        rows.append({"rule": "ORB_COLOUR_AC27", "status": "IMPLEMENTED_OPT_IN_VARIANT (not the active baseline)", "level": "ORB signal", **r})
    base_res = P.run_scenario(sc, ctxs, infos, bars)
    var_res = F51.run_scenario_orb_colour(sc, ctxs, infos, bars)
    key = lambda x: (x["date"], x["trade_no"], x["strategy"], x["method"], x["direction"], x["signal_time"], x["entry_time"])  # noqa: E731
    kb, kv = {key(x) for x in base_res.ledger}, {key(x) for x in var_res.ledger}
    p36 = {(r["date"], r["trade_no_of_day"], r["strategy"], r["method"], r["direction"]) for r in rd(P36 / "all_trades_detailed.csv")}
    regress = {(x["date"], str(x["trade_no"]), x["strategy"], x["method"], x["direction"]) for x in base_res.ledger} == p36
    for k in sorted(kb - kv):
        rows.append({"rule": "ORB_COLOUR_AC27", "status": "IMPLEMENTED_OPT_IN_VARIANT (not the active baseline)", "level": "executed trade removed by the variant", "date": k[0], "strategy": k[2], "method": k[3], "direction": k[4], "signal_time": k[5],
                     "baseline_status": "EXECUTED", "variant_status": "NOT EXECUTED"})
    for k in sorted(kv - kb):
        rows.append({"rule": "ORB_COLOUR_AC27", "status": "IMPLEMENTED_OPT_IN_VARIANT (not the active baseline)", "level": "executed trade added by the variant (the next valid signal takes the slot)", "date": k[0], "strategy": k[2], "method": k[3],
                     "direction": k[4], "signal_time": k[5], "baseline_status": "NOT EXECUTED", "variant_status": "EXECUTED"})
    # ------------------------------------------------------------------ 2. counts-only candidate rules on the executed Phase 3.6 trades
    trades = rd(P36 / "all_trades_detailed.csv")
    sigs = rd(P36 / "all_strategy_signals.csv")
    pop = {"phase36_trades": len(trades), "orb_colour_regression_ledger_equals_phase36": regress, "orb_records_changed": len(sig_diff), "variant_trades": len(var_res.ledger), "baseline_trades": len(base_res.ledger)}
    irf = [t for t in trades if t["strategy"] == "IRF"]
    flags = {"ema_within_27": [], "close_below_session_low": [], "body_lt_60": [], "body_lt_50": [], "body_lt_40": [], "first_red_reading_differs": []}
    for t in irf:
        d = date.fromisoformat(t["date"])
        c = ctxs.get(d)
        if c is None:
            continue
        cr = E.candle_rows(c)
        st = t["signal_confirmed_at"][-5:]
        m = D.irf_trade_measures(cr, st)
        if m.get("error"):
            continue
        for k, cond in (("ema_within_27", m.get("ema_within_27_below_entry")), ("close_below_session_low", m.get("close_below_prior_session_low")), ("body_lt_60", m.get("body_pct_below_60")), ("body_lt_50", m.get("body_pct_below_50")),
                        ("body_lt_40", (m.get("body_pct") or 100) < 40)):
            if cond:
                flags[k].append(t["trade_id"])
        rd_ = D.first_red_reading(cr, "FULLY_ABOVE", D.BODY_STRONG_PCT)
        if t["method"].startswith("Method 2") and (rd_ is None or rd_.get("entry") is None or rd_["entry"]["signal_time"] != st):
            flags["first_red_reading_differs"].append(t["trade_id"])
    pop["irf_trades"] = len(irf)
    pop["irf_method2_trades"] = sum(1 for t in irf if t["method"].startswith("Method 2"))
    pop["irf_flags"] = {k: {"count": len(v), "trades": v} for k, v in flags.items()}
    for k, v in flags.items():
        for tid in v:
            rows.append({"rule": f"IRF_{k.upper()}", "status": "NOT_IMPLEMENTED (counts only, owner approval needed)", "level": "executed Phase 3.6 IRF trade that the candidate rule would affect", "date": tid[:4] + "-" + tid[4:6] + "-" + tid[6:8],
                         "strategy": "IRF", "method": next(t["method"] for t in irf if t["trade_id"] == tid), "direction": "SHORT", "signal_time": next(t["signal_confirmed_at"][-5:] for t in irf if t["trade_id"] == tid), "baseline_status": "EXECUTED",
                         "variant_status": "would be rejected / deferred under the candidate reading"})
    first_green = {"PDR_first_green_earlier_than_engine": []}
    for t in trades:
        if t["strategy"] != "PDR":
            continue
        s = next((x for x in sigs if x["trade_id"] == t["trade_id"]), None)
        c = ctxs.get(date.fromisoformat(t["date"]))
        if s is None or c is None:
            continue
        lv = json.loads(s["reference_levels"])
        if not lv.get("zone_low"):
            continue
        g = D.first_green_after_zone(E.candle_rows(c), lv["zone_low"], lv["zone_high"])
        if g and g.get("first_green_close_above_ceiling") and g["first_green_close_above_ceiling"]["signal_time"] < t["signal_confirmed_at"][-5:]:
            first_green["PDR_first_green_earlier_than_engine"].append(t["trade_id"])
            rows.append({"rule": "PDR_FIRST_GREEN_CANDLE", "status": "NOT_IMPLEMENTED (counts only, owner approval needed)", "level": "executed Phase 3.6 PDR trade with an earlier 'first green candle' reading", "date": t["date"], "strategy": "PDR",
                         "method": "PDR", "direction": "LONG", "signal_time": t["signal_confirmed_at"][-5:], "baseline_status": "EXECUTED at that time", "variant_status": f"first green close above the ceiling at {g['first_green_close_above_ceiling']['signal_time']}"})
    pop["pdr_trades"] = sum(1 for t in trades if t["strategy"] == "PDR")
    pop["pdr_first_green_earlier"] = {"count": len(first_green["PDR_first_green_earlier_than_engine"]), "trades": first_green["PDR_first_green_earlier_than_engine"]}
    write_csv(OUT / "before_after_signal_differences.csv", rows)
    (OUT / "population_impact.json").write_text(json.dumps(pop, indent=1, default=str))
    print(json.dumps({k: (v if not isinstance(v, dict) else v.get("count", v)) for k, v in pop.items() if k != "irf_flags"}, indent=0, default=str))
    print({k: len(v) for k, v in flags.items()})
    print("ORB signal changes:", [(r["date"], r["method"], r["direction"], r["baseline_status"], r["variant_status"]) for r in sig_diff][:20])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
