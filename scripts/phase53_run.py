"""Phase 5.3: signal-only comparison and diagnostics for the owner-approved author corrections (NO controller, NO fills, NO P&L, NO profitability backtest).

  python scripts/phase53_run.py                    all configurations (the default)
  python scripts/phase53_run.py --list             list the selectable configurations

Configurations (``research/phase53.py``): phase36-frozen and phase52-approved (references), the four independently selectable Phase 5.3 rules (IRF first-red-candle LOW support, IRF minimum 28-point EMA clearance,
PDR first eligible confirmation, PDS first eligible confirmation), the combined ``phase53-author-corrected`` configuration and the assumption / comparison variants. Period: the existing NIFTY 2025-09-01..2026-08-31
dataset. Nothing under data/ or any earlier report is written.

Writes under reports/phase5/phase53_author_corrected/: signal_counts.json, all_confirmed_signals.csv, signal_comparison.csv, daily_first_signal_comparison.csv, irf_first_red_low_comparison.csv,
irf_ema_signals.csv, irf_ema_rejections.csv, pdr_first_eligible_setups.csv, pds_first_eligible_setups.csv, pds_20_sessions.csv, orb_unresolved_entries.csv, irf_day_low_diagnostics.csv,
dated_author_corrections.csv, daily/<date>.md, charts/<date>.svg, Phase53_Author_Corrections_Verification.xlsx.
"""

from __future__ import annotations

import argparse
import json
import sys
import warnings
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase51_reconcile as R51  # noqa: E402
from phase52_run import CUTOFF, ORB_DATES, conf, hm, levels_brief, rd  # noqa: E402

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase53 as F  # noqa: E402
from nifty_trading.research import phase53_diag as D  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402
from nifty_trading.strategies.definitions import to_candles  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase53_author_corrected"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P51 = ROOT / "reports" / "phase5" / "phase51_author_corrections"
P52 = ROOT / "reports" / "phase5" / "phase52_author_rules"
COMB = F.COMBINED_KEY
FROZEN = F.FROZEN_KEY
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")

CAUSE = {
    "phase53-irf-first-red-low": "IRF Method 2A support = LOW of the first red candle (owner approved); red search starts after the extension candle (provisional)",
    "phase53-irf-ema28": "IRF candidate rejected: signal candle range is closer than 28 points to EMA(200) (PROVISIONAL_EMA_RANGE_DISTANCE); a rejected Method 2 attempt stays alive",
    "phase53-pdr-first-eligible": "PDR earliest eligible confirmation: green candle (guide s.4.3) or lower-price rejection, close above the ceiling, after the retest candle (PROVISIONAL_PDR_MINIMAL_CONFIRMATION)",
    "phase53-pds-first-eligible": "PDS parameter-free quality tests for Methods 1/2 (PROVISIONAL_PDS_MINIMAL_QUALITY); weak first red candle still goes to Method 3",
    COMB: "all four Phase 5.3 rules together",
    "phase53-var-irf-first-red-after-breakout": "assumption variant: first red candle searched after the breakout candle",
    "phase53-var-irf-ema28-method2-only": "scope variant: EMA clearance applies to Methods 2A / 2B only",
    "phase53-var-irf-ema27": "comparison variant: 27-point clearance",
    "phase53-var-irf-ema28-close": "comparison variant: |close - EMA| >= 28",
    "phase53-var-orb-colour": "Phase 5.1 ORB colour rule (opt-in; not part of the combined configuration)",
    "phase52-approved": "co-confirmed PDS methods recorded (annotation only)",
}


def sup_level(r):
    return (r.reference_levels or {}).get("recent_support")


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--list", action="store_true", help="list the selectable configurations and exit")
    a = ap.parse_args()
    if a.list:
        for c in F.CONFIGS.values():
            print(f"{c.key:44} {c.authority:62} {c.title}")
        return 0
    keys = list(F.CONFIGS)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    m1 = load_one_minute()
    ctxs, _ = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    opens = dict(zip(m1["timestamp"], m1["open"], strict=True))
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    rejections: list[dict] = []
    sig = {k: F.signals_for(ctxs, sc, k, rejections) for k in keys}
    base = sig[FROZEN]
    trades = rd(P36 / "all_trades_detailed.csv")
    executed = {(t["date"], t["signal_confirmed_at"][-5:], t["strategy"]) for t in trades}

    # ============================================================================================ counts and all confirmed signals
    counts = {k: Counter((r.strategy, r.method) for d in sig[k] for r in conf(sig[k][d])) for k in keys}
    first_sessions = {k: Counter(s for d in sig[k] for s in {r.strategy for r in conf(sig[k][d])}) for k in keys}
    summary: dict = {}
    for k, v in counts.items():
        summary[k] = {"confirmed_total": sum(v.values()), "by_strategy": {s: sum(n for (st, _m), n in v.items() if st == s) for s in STRATS}, "sessions_with_a_signal_by_strategy": {s: first_sessions[k][s] for s in STRATS},
                      "by_method": {f"{s}/{m}": n for (s, m), n in sorted(v.items())}, "authority": F.CONFIGS[k].authority,
                      "confirmed_within_13_00": sum(1 for d in sig[k] for r in conf(sig[k][d]) if hm(r.signal_timestamp) <= CUTOFF)}
    rows_all = []
    for k in keys:
        for d in sorted(sig[k]):
            for r in conf(sig[k][d]):
                rows_all.append({"config": k, "date": str(d), "strategy": r.strategy, "method": r.method, "direction": r.direction, "signal_time": hm(r.signal_timestamp), "signal_candle_start": hm(r.signal_candle_start),
                                 "entry_reference_close": r.signal_candle_close, "within_13_00_cutoff": hm(r.signal_timestamp) <= CUTOFF, "levels": levels_brief(r), "flags": ";".join(f for f in r.flags if f.startswith(("PHASE", "PROVISIONAL"))),
                                 "executed_in_phase36_ledger": (str(d), hm(r.signal_timestamp), r.strategy) in executed and k == FROZEN})
    write_csv(OUT / "all_confirmed_signals.csv", rows_all)

    # ============================================================================================ comparison against the frozen reference
    def keyed(records):
        out = defaultdict(list)
        for r in conf(records):
            out[(r.strategy, r.method, r.direction)].append(r)
        return out
    cmp_rows = []
    change_counts: dict = {}
    change_counts_m: dict = {}
    for k in keys:
        if k in (FROZEN, "phase52-approved"):
            continue
        cc = Counter()
        ccm = Counter()
        for d in sorted(ctxs):
            kb, kc = keyed(base[d]), keyed(sig[k][d])
            for key in sorted(set(kb) | set(kc)):
                lb, lc = kb.get(key, []), kc.get(key, [])
                for n in range(max(len(lb), len(lc))):
                    rb = lb[n] if n < len(lb) else None
                    rc = lc[n] if n < len(lc) else None
                    tb, tc = (None if rb is None else hm(rb.signal_timestamp)), (None if rc is None else hm(rc.signal_timestamp))
                    if rb is not None and rc is not None and tb == tc:
                        ctype = "SAME_TIME_LEVEL_CHANGED" if sup_level(rb) != sup_level(rc) and key[1] == "Method 2A" else "UNCHANGED"
                    else:
                        ctype = "REMOVED" if rc is None else ("ADDED" if rb is None else "TIME_SHIFTED_EARLIER" if tc < tb else "TIME_SHIFTED_LATER")
                    cc[(key[0], ctype)] += 1
                    ccm[(key[0], key[1], ctype)] += 1
                    if ctype == "UNCHANGED":
                        continue
                    cmp_rows.append({"config": k, "date": str(d), "strategy": key[0], "method": key[1], "direction": key[2], "change": ctype, "baseline_signal_time": tb or "", "candidate_signal_time": tc or "",
                                     "baseline_levels": "" if rb is None else levels_brief(rb), "candidate_levels": "" if rc is None else levels_brief(rc), "rule_cause": CAUSE[k],
                                     "executed_in_phase36_ledger": bool(rb is not None and (str(d), tb, key[0]) in executed), "within_13_00_cutoff": hm((rc or rb).signal_timestamp) <= CUTOFF,
                                     "same_minute_collision_with_other_strategy": any(x.strategy != key[0] and hm(x.signal_timestamp) == (tc or tb) for x in conf(sig[k][d]))})
        change_counts[k] = {f"{s}/{t}": n for (s, t), n in sorted(cc.items())}
        change_counts_m[k] = {f"{s}/{m}/{t}": n for (s, m, t), n in sorted(ccm.items())}
    write_csv(OUT / "signal_comparison.csv", cmp_rows)
    summary["change_counts_vs_frozen"] = change_counts
    summary["change_counts_by_method_vs_frozen"] = change_counts_m
    # earliest actionable signal per day
    dfs = []
    for k in keys:
        if k in (FROZEN, "phase52-approved"):
            continue
        for d in sorted(ctxs):
            def first(records):
                c = [r for r in conf(records) if hm(r.signal_timestamp) <= CUTOFF]
                if not c:
                    return None, []
                same = [r for r in c if r.signal_timestamp == c[0].signal_timestamp]
                return c[0], same
            fb, sb = first(base[d])
            fc, scn = first(sig[k][d])
            tb, tc = (hm(fb.signal_timestamp) if fb else ""), (hm(fc.signal_timestamp) if fc else "")
            sb_s, sc_s = sorted({(r.strategy, r.method) for r in sb}), sorted({(r.strategy, r.method) for r in scn})
            if tb != tc or sb_s != sc_s:
                dfs.append({"config": k, "date": str(d), "baseline_first_signal": f"{tb} {';'.join(f'{s}/{m}' for s, m in sb_s)}", "candidate_first_signal": f"{tc} {';'.join(f'{s}/{m}' for s, m in sc_s)}",
                            "candidate_earlier": bool(tb and tc and tc < tb), "candidate_new_first_signal": bool(tc and not tb), "candidate_no_signal_now": bool(tb and not tc), "strategy_changed": sorted({s for s, _ in sb_s}) != sorted({s for s, _ in sc_s}),
                            "baseline_same_minute_collision": len({s for s, _ in sb_s}) > 1, "candidate_same_minute_collision": len({s for s, _ in sc_s}) > 1,
                            "note": "signal level only; the controller (first valid signal; same-minute conflicts unresolved) is not applied here"})
    write_csv(OUT / "daily_first_signal_comparison.csv", dfs)
    summary["first_signal_changes_by_config"] = {k: dict(Counter(("earlier" if r["candidate_earlier"] else "new" if r["candidate_new_first_signal"] else "none_now" if r["candidate_no_signal_now"] else "later_or_other") for r in dfs if r["config"] == k)) for k in keys if k not in (FROZEN, "phase52-approved")}

    # ============================================================================================ IRF: EMA geometry for the signals of the no-EMA IRF engines, rejections
    irf_rows = []
    for k in (FROZEN, "phase53-irf-first-red-low"):
        for d, c in sorted(ctxs.items()):
            cs = to_candles(c.candles)
            for r in conf(sig[k][d], "IRF"):
                m = D.irf_geometry(c, cs, r.signal_timestamp, opens.get(r.signal_timestamp))
                m.update({"config": k, "date": str(d), "method": r.method, "executed_in_phase36_ledger": k == FROZEN and (str(d), hm(r.signal_timestamp), "IRF") in executed, "within_13_00_cutoff": hm(r.signal_timestamp) <= CUTOFF})
                irf_rows.append(m)
    write_csv(OUT / "irf_ema_signals.csv", irf_rows)
    write_csv(OUT / "irf_ema_rejections.csv", [r for r in rejections if r["config"] in (COMB, "phase53-irf-ema28")])

    def tally(rows, pred):
        sel = [r for r in rows if r.get("ema_available") and pred(r)]
        return {"all": len(sel), "executed": sum(1 for r in sel if r["executed_in_phase36_ledger"]), "within_13_00": sum(1 for r in sel if r["within_13_00_cutoff"]),
                "by_method": dict(Counter(r["method"] for r in sel)), "by_relation": dict(Counter(r["ema_relation"] for r in sel))}
    ema_summary = {}
    for k in (FROZEN, "phase53-irf-first-red-low"):
        rr = [r for r in irf_rows if r["config"] == k]
        ema_summary[k] = {"signals": len(rr), "executed": sum(1 for r in rr if r["executed_in_phase36_ledger"]), "ema_unavailable": sum(1 for r in rr if not r.get("ema_available")),
                          "fail_range_28": tally(rr, lambda r: not r["pass_range_28"]), "fail_range_27": tally(rr, lambda r: not r["pass_range_27"]), "fail_close_28": tally(rr, lambda r: not r["pass_close_28"]),
                          "fail_close_27": tally(rr, lambda r: not r["pass_close_27"]), "range_27_pass_28_fail": tally(rr, lambda r: r["pass_range_27"] and not r["pass_range_28"]),
                          "fail_range_28_ema_above_candle": tally(rr, lambda r: not r["pass_range_28"] and r["ema_relation"] == "EMA_ABOVE_CANDLE"),
                          "fail_range_28_ema_inside_candle": tally(rr, lambda r: not r["pass_range_28"] and r["ema_relation"] == "EMA_INSIDE_CANDLE"),
                          "fail_range_28_ema_below_candle": tally(rr, lambda r: not r["pass_range_28"] and r["ema_relation"] == "EMA_BELOW_CANDLE"),
                          "fail_range_28_and_ema_between_entry_and_t1": tally(rr, lambda r: not r["pass_range_28"] and r["ema_between_entry_and_t1"]),
                          "fail_range_28_and_ema_NOT_between_entry_and_t1": tally(rr, lambda r: not r["pass_range_28"] and not r["ema_between_entry_and_t1"]),
                          "pass_range_28_but_ema_between_entry_and_t1": tally(rr, lambda r: r["pass_range_28"] and r["ema_between_entry_and_t1"]),
                          "pass_range_28_but_ema_within_28_below_entry_obstructs": tally(rr, lambda r: r["pass_range_28"] and r["t1_blocked_by_ema_within_28"]),
                          "range_28_decision_changes_with_previous_candle_ema": tally(rr, lambda r: r["pass_range_28_using_previous_candle_ema"] is not None and r["pass_range_28_using_previous_candle_ema"] != r["pass_range_28"])}
    summary["irf_ema"] = ema_summary
    summary["irf_ema_rejection_events"] = {k: {"events": sum(1 for r in rejections if r["config"] == k), "by_method": dict(Counter(r["method"] for r in rejections if r["config"] == k)),
                                              "by_relation": dict(Counter(r["relation"] for r in rejections if r["config"] == k and r.get("ema_available")))} for k in ("phase53-irf-ema28", COMB, "phase53-var-irf-ema27", "phase53-var-irf-ema28-method2-only", "phase53-var-irf-ema28-close")}

    # ============================================================================================ IRF: first red candle LOW on the 42 executed Method-2 trades
    old42 = rd(P52 / "irf_first_red_comparison.csv")
    fr_rows = []
    for t in old42:
        d = date.fromisoformat(t["date"])

        def classify(k, d=d, t=t):
            cf = [r for r in conf(sig[k][d], "IRF") if hm(r.signal_timestamp) <= CUTOFF]
            same = next((r for r in cf if r.method == t["baseline_method"] and hm(r.signal_timestamp) == t["baseline_signal_time"]), None)
            if same is not None:
                return "UNCHANGED (same time and method)" + (f"; support {sup_level(same)}" if t["baseline_method"] == "Method 2A" else ""), same
            if not cf:
                return "NO IRF SIGNAL within 13:00", None
            f0 = cf[0]
            rel = "earlier" if hm(f0.signal_timestamp) < t["baseline_signal_time"] else "later"
            return f"{rel} ({t['baseline_signal_time']} -> {hm(f0.signal_timestamp)} {f0.method})", f0
        low_c, low_r = classify("phase53-irf-first-red-low")
        brk_c, brk_r = classify("phase53-var-irf-first-red-after-breakout")
        lv = (low_r.reference_levels or {}) if low_r is not None else {}
        fr_rows.append({**{k: t[k] for k in ("trade_id", "date", "baseline_method", "baseline_signal_time", "old_reference_kind", "old_reference_candle_start", "old_reference_level", "first_qualifying_red_candle_start", "first_red_candle_ohlc",
                                              "in_phase51_37_reading_disagreements", "handwritten_dated_example", "author_stated_direction")},
                        "phase53_first_red_LOW_level": t["support_level_if_LOW"], "phase53_result_first_red_low": low_c, "phase53_reference_candle_used": lv.get("first_red_candle_start", ""),
                        "phase53_result_red_search_after_breakout": brk_c, "red_search_start_changes_the_result": low_c != brk_c})
    write_csv(OUT / "irf_first_red_low_comparison.csv", fr_rows)
    m2a_b = {(r["date"], r["signal_time"]): r for r in rows_all if r["config"] == FROZEN and r["strategy"] == "IRF" and r["method"] == "Method 2A"}
    summary["irf_first_red_low"] = {"changes_by_type": change_counts["phase53-irf-first-red-low"], "changes_after_breakout_variant": change_counts["phase53-var-irf-first-red-after-breakout"],
                                    "frozen_method_2A_signals": len(m2a_b), "frozen_irf_signals": summary[FROZEN]["by_strategy"]["IRF"], "phase53_irf_signals": summary["phase53-irf-first-red-low"]["by_strategy"]["IRF"],
                                    "executed_trades_unchanged": sum(1 for r in fr_rows if r["phase53_result_first_red_low"].startswith("UNCHANGED")), "executed_trades_earlier": sum(1 for r in fr_rows if " earlier" in " " + r["phase53_result_first_red_low"]),
                                    "executed_trades_later": sum(1 for r in fr_rows if r["phase53_result_first_red_low"].startswith("later")), "executed_trades_no_signal": sum(1 for r in fr_rows if r["phase53_result_first_red_low"].startswith("NO IRF")),
                                    "red_search_start_changes": sum(1 for r in fr_rows if r["red_search_start_changes_the_result"])}

    # ============================================================================================ PDR
    pdr_rows, pdr_diag = [], {}
    old_pdr = {r["date"]: r for r in rd(P52 / "pdr_first_eligible_setups.csv")}
    for d, c in sorted(ctxs.items()):
        dg = D.pdr_phase53_setup(c, sc)
        pdr_diag[str(d)] = dg
        if dg["status"] in ("NO_SETUP_NO_GAP_UP", "NOT_ARMED"):
            continue
        fb, fn = conf(base[d], "PDR"), conf(sig["phase53-pdr-first-eligible"][d], "PDR")
        tb, tn = (hm(fb[0].signal_timestamp) if fb else ""), (hm(fn[0].signal_timestamp) if fn else "")
        chg = "SAME" if tb == tn else ("NEW_SIGNAL" if not tb else "REMOVED" if not tn else "EARLIER" if tn < tb else "LATER")
        o = old_pdr.get(str(d), {})
        pdr_rows.append({"date": str(d), "status": dg["status"], "zone_floor": dg.get("zone_floor", ""), "zone_ceiling": dg.get("zone_ceiling", ""), "retest_candle_start": dg.get("retest_candle_start", ""), "retest_candle_ohlc": dg.get("retest_candle_ohlc", ""),
                         "frozen_first_pdr_signal": tb, "phase53_first_pdr_signal": tn, "phase53_diagnostic_first_eligible": dg.get("first_eligible_signal_time") or "", "engine_equals_diagnostic": (dg.get("first_eligible_signal_time") or "") == tn,
                         "change": chg, "phase53_signals_total": len(fn), "frozen_signals_total": len(fb), "retest_candle_would_qualify_under_phase53_convention": dg.get("retest_candle_would_qualify_if_permitted", ""),
                         "confirmation_time_if_retest_candle_were_permitted": dg.get("first_retest_confirmation_if_retest_permitted") or "", "phase52_retest_candle_would_qualify_old_thresholds": o.get("interaction_candle_would_qualify_if_permitted", ""),
                         "candidate_verdicts": " || ".join(f"{r['candle_start']} {r['role']} eligible={r['eligible']} {r['reason_if_not']}" for r in dg.get("rows", []))[:1500]})
    write_csv(OUT / "pdr_first_eligible_setups.csv", pdr_rows)
    def pat(records, first_only):
        c = Counter()
        for d in sig["phase53-pdr-first-eligible"]:
            fn = conf(records[d], "PDR")
            for r in (fn[:1] if first_only else fn):
                pp = (r.reference_levels or {}).get("patterns_passed", [])
                c["+".join(pp)] += 1
        return dict(c)
    summary["pdr"] = {"first_signal_patterns": pat(sig["phase53-pdr-first-eligible"], True), "all_signal_patterns": pat(sig["phase53-pdr-first-eligible"], False), "armed_setups": sum(1 for r in pdr_rows if r["status"] == "ARMED"), "sessions_changed": dict(Counter(r["change"] for r in pdr_rows)),
                      "engine_differs_from_diagnostic": sum(1 for r in pdr_rows if not r["engine_equals_diagnostic"]),
                      "eight_old_retest_setups": [r["date"] for r in pdr_rows if str(r["phase52_retest_candle_would_qualify_old_thresholds"]) == "True"],
                      "retest_candle_would_qualify_phase53": sum(1 for r in pdr_rows if str(r["retest_candle_would_qualify_under_phase53_convention"]) == "True"),
                      "signals_frozen": summary[FROZEN]["by_strategy"]["PDR"], "signals_phase53": summary["phase53-pdr-first-eligible"]["by_strategy"]["PDR"]}

    # ============================================================================================ PDS
    pds_rows, pds_diag = [], {}
    old_pds = {r["date"]: r for r in rd(P52 / "pds_first_eligible_setups.csv")}
    for d, c in sorted(ctxs.items()):
        dg = D.pds_phase53_first_red(c, sc)
        pds_diag[str(d)] = dg
        if dg["status"] in ("NO_SETUP_NO_GAP_DOWN", "NOT_ARMED_OPEN_NOT_BELOW_ZONE"):
            continue
        fb, fn = conf(base[d], "PDS"), conf(sig["phase53-pds-first-eligible"][d], "PDS")
        tb, tn = (hm(fb[0].signal_timestamp) if fb else ""), (hm(fn[0].signal_timestamp) if fn else "")
        chg = "SAME" if tb == tn else ("NEW_SIGNAL" if not tb else "REMOVED" if not tn else "EARLIER" if tn < tb else "LATER")
        o = old_pds.get(str(d), {})
        pds_rows.append({"date": str(d), "status": dg["status"], "first_red_candle_start": dg.get("first_red_candle_start", ""), "first_red_ohlc": dg.get("ohlc", ""), "body_pct": dg.get("body_pct", ""), "upper_wick_pct": dg.get("upper_wick_pct", ""),
                         "lower_wick_pct": dg.get("lower_wick_pct", ""), "frozen_numeric_verdict": dg.get("frozen_numeric_verdict", ""), "phase53_verdict": dg.get("phase53_verdict", ""),
                         "frozen_first_pds_signal": f"{tb} {fb[0].method}" if fb else "", "phase53_first_pds_signal": f"{tn} {fn[0].method}" if fn else "", "change": chg,
                         "frozen_signals_total": len(fb), "phase53_signals_total": len(fn), "later_strong_red_candles_after_weak_first_red": o.get("later_strong_red_candles_after_weak_first_red", "")})
    write_csv(OUT / "pds_first_eligible_setups.csv", pds_rows)
    twenty = []
    for r in pds_rows:
        if not r["later_strong_red_candles_after_weak_first_red"]:
            continue
        weak = str(r["phase53_verdict"]).startswith("WEAK")
        if weak:
            reason = (f"first red candle {r['first_red_candle_start']} is weak (body {r['body_pct']}%, wicks {r['upper_wick_pct']}% / {r['lower_wick_pct']}%: the body does not exceed both wicks and it is not a red pin bar). "
                      "Source quality rule (PDS guide s.7): 'do not take a weak red candle ... wait for a small support to form and break (Method 3)'. Later strong red candles are not used: Methods 1/2 apply to the FIRST red candle only.")
            method = "Method 3 (mandatory small-support break)"
        else:
            reason = f"first red candle is eligible under the Phase 5.3 quality test ({r['phase53_verdict']}); it was rejected only by the frozen numeric thresholds (verdict {r['frozen_numeric_verdict']})."
            method = r["phase53_verdict"].split("(")[1].rstrip(")")
        twenty.append({"date": r["date"], "first_red_candle_start": r["first_red_candle_start"], "first_red_ohlc": r["first_red_ohlc"], "body_pct": r["body_pct"], "upper_wick_pct": r["upper_wick_pct"], "lower_wick_pct": r["lower_wick_pct"],
                       "frozen_numeric_verdict": r["frozen_numeric_verdict"], "eligible_under_phase53_reading": r["phase53_verdict"], "method_that_applies": method, "subsequent_support_break_mandatory": weak,
                       "later_strong_red_candles_not_used": r["later_strong_red_candles_after_weak_first_red"], "original_confirmation": r["frozen_first_pds_signal"], "new_confirmation": r["phase53_first_pds_signal"], "change": r["change"],
                       "reason_if_earlier_candle_remains_rejected": reason if weak else ""})
    write_csv(OUT / "pds_20_sessions.csv", twenty)
    summary["pds"] = {"gap_down_armed_sessions": len(pds_rows), "sessions_changed": dict(Counter(r["change"] for r in pds_rows)), "twenty_sessions": len(twenty), "twenty_sessions_now_eligible_first_red": sum(1 for r in twenty if not r["subsequent_support_break_mandatory"]),
                      "twenty_sessions_still_weak": sum(1 for r in twenty if r["subsequent_support_break_mandatory"]), "twenty_sessions_changed": dict(Counter(r["change"] for r in twenty)),
                      "signals_frozen": summary[FROZEN]["by_strategy"]["PDS"], "signals_phase53": summary["phase53-pds-first-eligible"]["by_strategy"]["PDS"],
                      "verdicts": dict(Counter(r["phase53_verdict"].split("(")[0] for r in pds_rows if r["phase53_verdict"]))}

    # ============================================================================================ ORB (unchanged engine): the 13 disputed dates and the precise missing definitions
    orb_audit = rd(P52 / "orb_missing_signal_audit.csv")
    orb_json = json.loads((P52 / "orb_missing_signal_audit.json").read_text())
    needed = {"METHOD2_TRENDLINE": "an objective construction of the Method 2 trendline (which fractals, how many touches, slope tolerance) - the source only draws it",
              "STRONG_CANDLE_THRESHOLD": "the ORB strong-candle definition (body %, opposite-wick %) or an approval of a looser profile - the rulebook gives no numbers",
              "EMA_REQUIREMENT": "the exact trend filter (previous-session close against its EMA, or the first candle's close against EMA(200), or none)",
              "LEVEL_CONSTRUCTION": "the level the author drew: Method 2's inner support/resistance is not defined in the rulebook (the engine has no level to break when the first candle does not break the previous-day high/low)",
              "GAP_OR_MA_CALCULATION": "the Gap / 200-average set-up numbers"}
    orb_rows = []
    for ds in ORB_DATES:
        j = orb_json[ds]
        cat = j["cause_category"].split(" (")[0]
        col = j["first_candle"]["colour"]
        dr = "SHORT" if col == "RED" else "LONG"
        ff = j["directions"][dr]["first_failing_rule"]
        orb_rows.append({"date": ds, "first_candle_colour": col, "body_pct": j["first_candle"]["body_pct"], "upper_wick_pct": j["first_candle"]["upper_wick_pct"], "lower_wick_pct": j["first_candle"]["lower_wick_pct"],
                         "prev_day_high": j["prev_day_high"], "prev_day_low": j["prev_day_low"], "ema200_first_candle": j["ema200_first_candle"], "failing_Method_1": ff["Method 1"], "failing_Method_2": ff["Method 2"], "failing_Gap_200": ff["Gap/200DMA"],
                         "cause_category": cat, "orb_signal_in_phase36": any(r.strategy == "ORB" for r in conf(base[date.fromisoformat(ds)])), "orb_signal_in_phase53_author_corrected": any(r.strategy == "ORB" for r in conf(sig[COMB][date.fromisoformat(ds)])),
                         "first_signal_phase36": next((f"{hm(r.signal_timestamp)} {r.strategy}/{r.method}" for r in conf(base[date.fromisoformat(ds)])), ""), "first_signal_phase53_author_corrected": next((f"{hm(r.signal_timestamp)} {r.strategy}/{r.method}" for r in conf(sig[COMB][date.fromisoformat(ds)])), ""),
                         "missing_definition_required": needed.get(cat, "see audit"), "reproducible_without_new_rules": False})
    write_csv(OUT / "orb_unresolved_entries.csv", orb_rows)
    summary["orb"] = {"disputed_dates": len(orb_rows), "unresolved": sum(1 for r in orb_rows if not r["reproducible_without_new_rules"]), "causes": dict(Counter(r["cause_category"] for r in orb_rows)),
                      "orb_signal_on_any_disputed_date_phase36": sum(1 for r in orb_rows if r["orb_signal_in_phase36"]), "orb_signal_on_any_disputed_date_phase53": sum(1 for r in orb_rows if r["orb_signal_in_phase53_author_corrected"]),
                      "orb_signals_identical_in_combined": all(sorted((str(d), r.method, hm(r.signal_timestamp)) for d in sig[COMB] for r in conf(sig[COMB][d], "ORB")) == sorted((str(d), r.method, hm(r.signal_timestamp)) for d in base for r in conf(base[d], "ORB")) for _ in [0]),
                      "irf_first_signal_changed_on_disputed_dates": sum(1 for r in orb_rows if r["first_signal_phase36"] != r["first_signal_phase53_author_corrected"]), "audit_rows": len(orb_audit)}

    # ============================================================================================ IRF day's low (pending): measurements for the combined configuration's signals
    dl_rows = []
    for d, c in sorted(ctxs.items()):
        cs = to_candles(c.candles)
        for r in conf(sig[COMB][d], "IRF"):
            m = D.irf_geometry(c, cs, r.signal_timestamp, opens.get(r.signal_timestamp))
            dl_rows.append({"date": str(d), "method": r.method, "signal_time": hm(r.signal_timestamp), "within_13_00_cutoff": hm(r.signal_timestamp) <= CUTOFF, "signal_candle_low": m.get("candle_low"), "entry_price": m.get("entry_price"),
                            "running_session_low_before_signal": m.get("running_low_before_signal_candle"), "running_session_low_including_signal_candle": m.get("running_low_including_signal_candle"), "previous_day_low": m.get("previous_day_low"),
                            "opening_range_low_IRL": m.get("irl"), "entry_already_below_IRL": m.get("entry_below_irl"), "entry_minus_running_low": m.get("entry_minus_running_low_before"),
                            **{k: m.get(k) for k in ("D1_entry_at_or_below_running_low", "D2_close_below_running_low_before", "D3_close_at_running_low_incl_candle", "D4_t1_beyond_running_low", "D5_entry_within_28_of_running_low",
                                                     "D6_running_low_already_below_irl", "D7_earlier_close_below_irl", "D8_entry_below_previous_day_low")}})
    write_csv(OUT / "irf_day_low_diagnostics.csv", dl_rows)
    dlk = ["D1_entry_at_or_below_running_low", "D2_close_below_running_low_before", "D3_close_at_running_low_incl_candle", "D4_t1_beyond_running_low", "D5_entry_within_28_of_running_low", "D6_running_low_already_below_irl", "D7_earlier_close_below_irl",
           "D8_entry_below_previous_day_low", "entry_already_below_IRL"]
    summary["irf_day_low"] = {"status": "PENDING_OWNER_DEFINITION", "signals": len(dl_rows), "signals_within_cutoff": sum(1 for r in dl_rows if r["within_13_00_cutoff"]),
                              **{k: {"all": sum(1 for r in dl_rows if r.get(k)), "within_13_00": sum(1 for r in dl_rows if r.get(k) and r["within_13_00_cutoff"])} for k in dlk}}
    write_csv_json = json.dumps(summary, indent=1, default=str)
    (OUT / "signal_counts.json").write_text(write_csv_json)

    # ============================================================================================ dated author corrections
    corr = rd(P52 / "dated_corrections_comparison.csv")
    dated = []
    first_by_date: dict[str, list] = {}
    for r in corr:
        ds = r["trading_date"]
        topic = r["topic"]
        row = {k: r[k] for k in ("correction_id", "trading_date", "handwritten_pdf_page", "original_author_comment", "topic", "original_strategy", "original_signal_timestamp", "expected_strategy_or_candle", "entry_candle_ohlc")}
        status, note = "NOT_IN_SCOPE_UNCHANGED", "not addressed by the Phase 5.3 corrections; behaviour unchanged"
        d = date.fromisoformat(ds) if ds else None
        if d is not None:
            f_all = [(hm(x.signal_timestamp), x.strategy, x.method) for x in conf(base[d]) if hm(x.signal_timestamp) <= CUTOFF]
            c_all = [(hm(x.signal_timestamp), x.strategy, x.method) for x in conf(sig[COMB][d]) if hm(x.signal_timestamp) <= CUTOFF]
            row["frozen_signals_to_13_00"] = "; ".join(f"{t} {s}/{m}" for t, s, m in f_all)
            row["phase53_signals_to_13_00"] = "; ".join(f"{t} {s}/{m}" for t, s, m in c_all)
            c = ctxs[d]
            cs = to_candles(c.candles)
        if topic == "PDR_FIRST_ELIGIBLE":
            dg = pdr_diag[ds]
            author = (r.get("author_reading_first_green_candle") or "")[:5]
            mine = dg.get("first_eligible_candle_start") or ""
            ret = dg.get("retest_candle_start") or ""
            if mine and author == mine:
                status, note = "RECONCILED", f"Phase 5.3 first eligible confirmation candle {mine} = the author's first green candle {author}"
            elif author and author == ret:
                status, note = "NOT_RECONCILED_RETEST_CONVENTION", f"the author's candle {author} is the RETEST candle; the retest/confirmation sequencing is unresolved and preserved, so the first eligible candle is {mine or 'none'} (owner decision)"
            elif mine and author and mine < author:
                status, note = "RECONCILED_EARLIER_THAN_AUTHOR_READING", f"Phase 5.3 first eligible candle {mine} is before the author-reading candle {author}"
            else:
                status, note = "NOT_RECONCILED", f"author's candle {author or 'n/a'} vs Phase 5.3 {mine or 'none'}"
            row.update({"phase53_pdr_first_eligible_candle": mine, "phase53_pdr_signal": dg.get("first_eligible_signal_time") or "", "author_first_green_candle": author, "retest_candle": ret, "retest_candle_would_qualify": dg.get("retest_candle_would_qualify_if_permitted", "")})
        elif topic == "PDS_FIRST_ELIGIBLE":
            dg = pds_diag[ds]
            row.update({"phase53_pds_first_red_candle": dg.get("first_red_candle_start", ""), "phase53_pds_first_red_geometry": f"body {dg.get('body_pct')}% / wicks {dg.get('upper_wick_pct')}% / {dg.get('lower_wick_pct')}%", "phase53_pds_verdict": dg.get("phase53_verdict", "")})
            if str(dg.get("phase53_verdict", "")).startswith("WEAK"):
                status, note = "NOT_RECONCILED_CONFLICT_WITH_SOURCE_RULE", "the author's 'first candle entry' is a weak first red candle; the PDS guide says do not take a weak red candle (Method 3); flagged for owner approval rather than overridden"
            else:
                status, note = "RECONCILED", "first red candle is eligible under the Phase 5.3 quality test"
        elif topic == "IRF_FIRST_RED_CANDLE":
            fr = next((x for x in fr_rows if x["date"] == ds), None)
            res = fr["phase53_result_first_red_low"] if fr else ""
            direction = (r["expected_strategy_or_candle"] or "")
            row.update({"phase53_irf_result_first_red_low": res, "phase53_irf_result_red_search_after_breakout": fr["phase53_result_red_search_after_breakout"] if fr else "", "first_red_candle": fr["first_qualifying_red_candle_start"] if fr else "",
                        "first_red_candle_low": fr["phase53_first_red_LOW_level"] if fr else ""})
            bm = fr["baseline_method"] if fr else ""
            stated_earlier, stated_later = "earlier" in direction, "later" in direction
            if bm != "Method 2A" and res.startswith("UNCHANGED"):
                status, note = "NOT_RECONCILED_METHOD_OUT_OF_SCOPE", f"{bm} has no red-candle-created support (Method 2B's reference is a resistance); the rule is not applied there without source support (scope verification required)"
            elif stated_earlier or stated_later:
                ok = (stated_earlier and res.startswith("earlier")) or (stated_later and res.startswith("later"))
                status, note = ("RECONCILED_DIRECTION", res) if ok else ("NOT_RECONCILED", f"author expects {'earlier' if stated_earlier else 'later'}; first-red-low gives: {res}")
            else:
                status, note = "APPLIED_NO_OBSERVABLE_EXPECTATION", f"the author states only 'first red candle'; Method 2A support is now that candle's LOW; outcome on this date: {res}"
        elif topic == "IRF_EMA_28":
            mrow = next((x for x in irf_rows if x["config"] == FROZEN and x["date"] == ds and x.get("executed_in_phase36_ledger")), None)
            if mrow:
                row.update({"close_distance_to_ema": mrow.get("close_distance"), "range_clearance": mrow.get("range_clearance"), "ema_relation": mrow.get("ema_relation"), "ema_between_entry_and_t1": mrow.get("ema_between_entry_and_t1")})
                killed = not any(x[1] == "IRF" and x[0] == r["original_signal_timestamp"] for x in [(hm(y.signal_timestamp), y.strategy, y.method) for y in conf(sig["phase53-irf-ema28"][d])])
                if not mrow["pass_range_28"] and killed:
                    status, note = ("PARTIAL_REJECTED_NOT_DELAYED" if "wait" in r["expected_strategy_or_candle"] else "RECONCILED"), f"the signal is rejected (range clearance {mrow['range_clearance']:.2f} < 28); the author's 'wait for the EMA break' alternative is not modelled (no rule defined)"
                else:
                    status, note = "NOT_RECONCILED", "the 28-point range convention does not reject the executed signal"
        elif topic == "IRF_DAY_LOW":
            status, note = "PENDING_OWNER_DEFINITION", "the day's-low predicate is unresolved; the previous behaviour is preserved (diagnostics in irf_day_low_diagnostics.csv)"
        elif topic == "IRF_ENTRY_BODY (not in the call)":
            status, note = "NOT_ADDRESSED_PENDING_OWNER", "entry-candle body threshold (60/50/40 %) is not part of the Phase 5.3 approvals"
        elif topic == "ORB_MISSING":
            orow = next((x for x in orb_rows if x["date"] == ds), None)
            status, note = "UNRESOLVED_MISSING_DEFINITION", (orow["missing_definition_required"] if orow else "see orb_unresolved_entries.md")
            if orow:
                row.update({"orb_cause": orow["cause_category"], "first_signal_phase53": orow["first_signal_phase53_author_corrected"]})
        elif topic == "ORB_COLOUR":
            status, note = "VARIANT_AVAILABLE_NOT_ACTIVE", "ORB colour rule (Phase 5.1) is selectable as phase53-var-orb-colour; not part of the combined configuration"
        row.update({"reconciliation_status": status, "reconciliation_note": note})
        dated.append(row)
        if ds:
            first_by_date.setdefault(ds, []).append(row)
    write_csv(OUT / "dated_author_corrections.csv", dated)
    summary["dated"] = {"rows": len(dated), "status_counts": dict(Counter(r["reconciliation_status"] for r in dated)),
                        "reconciled": sum(1 for r in dated if r["reconciliation_status"].startswith("RECONCILED")), "applied_without_observable_expectation": sum(1 for r in dated if r["reconciliation_status"].startswith("APPLIED")),
                        "partial": sum(1 for r in dated if r["reconciliation_status"].startswith("PARTIAL"))}
    (OUT / "signal_counts.json").write_text(json.dumps(summary, indent=1, default=str))

    # ============================================================================================ day reports and charts
    for ds, items in sorted(first_by_date.items()):
        d = date.fromisoformat(ds)
        ev = json.loads((P51 / "evidence" / f"{ds}.json").read_text())
        marks = []
        for t in [t for t in trades if t["date"] == ds][:2]:
            marks.append({"time": t["signal_confirmed_at"][-5:], "price": float(t["entry_price"]), "colour": "#d81b60", "label": f"Phase 3.6 {t['strategy']} {t['method'][-2:].strip()}"})
        for r in conf(sig[COMB][d])[:3]:
            if hm(r.signal_timestamp) <= CUTOFF:
                marks.append({"time": hm(r.signal_timestamp), "price": r.signal_candle_close, "colour": "#2e7d32", "label": f"Phase 5.3 {r.strategy} {r.method[-2:].strip()}"})
        zone = None
        pg = pdr_diag.get(ds, {})
        if pg.get("zone_floor") and any(i["topic"] == "PDR_FIRST_ELIGIBLE" for i in items):
            zone = (pg["zone_floor"], pg["zone_ceiling"])
        sg = pds_diag.get(ds, {})
        if sg.get("zone_low") and any(i["topic"] == "PDS_FIRST_ELIGIBLE" for i in items):
            zone = (sg["zone_low"], sg["zone_high"])
        if ev.get("candles"):
            (OUT / "charts" / f"{ds}.svg").write_text(R51.candle_svg(ev, marks, zone, f"{ds} Phase 5.3: " + " / ".join(i["correction_id"] for i in items)))
        md = [f"# {ds} - Phase 5.3 original versus author-corrected signals", "", "> Signal-level comparison only: no controller, no fills, no P&L. Provisional conventions are labelled.", ""]
        for i in items:
            md += [f"## {i['correction_id']} (PDF page {i['handwritten_pdf_page']}) - topic `{i['topic']}`", "", f"> {i['original_author_comment']}", "",
                   f"* Phase 3.6 automated signal: {i.get('original_strategy', '')} {i.get('original_signal_timestamp', '')}; entry candle OHLC {i.get('entry_candle_ohlc', '')}",
                   f"* Phase 3.6 signals to 13:00: {i.get('frozen_signals_to_13_00', '')}", f"* Phase 5.3 author-corrected signals to 13:00: {i.get('phase53_signals_to_13_00', '')}",
                   f"* Reconciliation: **{i['reconciliation_status']}** - {i['reconciliation_note']}", ""]
            extra = {k: v for k, v in i.items() if k.startswith(("phase53_", "author_first", "retest", "close_distance", "range_clearance", "ema_", "first_red", "orb_"))}
            if extra:
                md += ["| measurement | value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in extra.items()] + [""]
        chg = [r for r in cmp_rows if r["date"] == ds and r["config"] in (COMB,)]
        md += ["### Changes in the author-corrected configuration on this date (against Phase 3.6)", ""]
        md += (["| strategy | method | change | Phase 3.6 | Phase 5.3 | cause |", "|---|---|---|---|---|---|"] + [f"| {r['strategy']} | {r['method']} | {r['change']} | {r['baseline_signal_time']} | {r['candidate_signal_time']} | {r['rule_cause']} |" for r in chg]) if chg else ["(no signal changes on this date)"]
        rej = [r for r in rejections if r["config"] == COMB and r["date"] == ds]
        if rej:
            md += ["", "### IRF candidates rejected by the 28-point EMA clearance this date", "", "| method | candle | EMA | relation | range distance |", "|---|---|---|---|---|"] + [f"| {r['method']} | {r['signal_time']} {r.get('candle_ohlc', '')} | {r.get('ema200', 0):.2f} | {r.get('relation')} | {r.get('distance', 0):.2f} |" for r in rej]
        md += ["", f"![{ds}](../charts/{ds}.svg)", ""]
        (OUT / "daily" / f"{ds}.md").write_text("\n".join(md) + "\n")

    # ============================================================================================ workbook
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    for n, line in enumerate(["Phase 5.3 - original versus author-corrected signals (signal level only: no controller, no fills, no P&L, no profitability backtest)",
                              "Active reference = frozen Phase 3.6. 'phase53-author-corrected' = IRF Method 2A support = first red candle LOW + IRF minimum 28-point EMA(200) range clearance (PROVISIONAL_EMA_RANGE_DISTANCE) + PDR / PDS earliest eligible confirmation (provisional minimal conventions). ORB and RF frozen; the IRF day's-low restriction is PENDING_OWNER_DEFINITION and not applied.",
                              "Sheets: Dated Corrections, Signal Comparison, First Signal Per Day, IRF First Red LOW, IRF EMA Signals, IRF EMA Rejections, PDR Setups, PDS Setups, PDS 20 Sessions, ORB Unresolved, IRF Day Low, Signal Counts."], 1):
        ws.cell(row=n, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 170

    def add(name, rows_):
        w = wb.create_sheet(name[:31])
        if not rows_:
            w["A1"] = "(no rows)"
            return
        cols = []
        for r in rows_:
            for k in r:
                if k not in cols:
                    cols.append(k)
        w.append(cols)
        for r in rows_:
            w.append([("" if r.get(c) is None else (str(r[c]) if isinstance(r[c], (dict, list)) else r[c])) for c in cols])
        for cell in w[1]:
            cell.fill, cell.font = PatternFill("solid", fgColor="1F3864"), Font(bold=True, color="FFFFFF")
        w.freeze_panes = "B2"
    add("Dated Corrections", dated)
    add("Signal Comparison", cmp_rows)
    add("First Signal Per Day", dfs)
    add("IRF First Red LOW", fr_rows)
    add("IRF EMA Signals", irf_rows)
    add("IRF EMA Rejections", [r for r in rejections if r["config"] in (COMB, "phase53-irf-ema28")])
    add("PDR Setups", pdr_rows)
    add("PDS Setups", pds_rows)
    add("PDS 20 Sessions", twenty)
    add("ORB Unresolved", orb_rows)
    add("IRF Day Low", dl_rows)
    add("Signal Counts", [{"config": k, "authority": summary[k]["authority"], "confirmed_total": summary[k]["confirmed_total"], **summary[k]["by_strategy"]} for k in keys])
    wb.save(OUT / "Phase53_Author_Corrections_Verification.xlsx")
    print({k: (summary[k]["confirmed_total"], summary[k]["by_strategy"]) for k in keys})
    print(json.dumps({k: summary[k] for k in ("pdr", "pds", "orb", "dated", "irf_first_red_low")}, indent=0, default=str)[:3000])
    print(f"{len(cmp_rows)} comparison rows, {len(dfs)} first-signal differences, {len(fr_rows)} IRF M2 comparisons, {len(dated)} dated rows, {len(list((OUT / 'daily').glob('*.md')))} day reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
