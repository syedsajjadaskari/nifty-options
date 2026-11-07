"""Phase 5.2: signal-only comparison and diagnostics for the author's latest clarifications (NO controller, NO fills, NO P&L).

  python scripts/phase52_run.py                       all configurations (the default)
  python scripts/phase52_run.py --config phase52-approved --config phase52-cand-orb-colour      a subset (the frozen reference is always included)
  python scripts/phase52_run.py --list                list the selectable configurations

Configurations (``research/phase52.py``): phase36-frozen (reference), phase52-approved (first eligible confirmation candle for PDR / PDS: verified, plus co-confirmed PDS methods recorded), and three opt-in
CANDIDATES (ORB colour, IRF Method 2A support = first red candle LOW / BODY LOW). The period is the existing NIFTY 2025-09-01..2026-08-31 dataset (Phase 1). Nothing under data/ or any earlier report is written.

Writes under reports/phase5/phase52_author_rules/: signal_counts.json, all_confirmed_signals.csv, before_after_signals.csv, daily_first_signal_comparison.csv, pdr_setup_diagnostics.json / pdr_first_eligible_setups.csv,
pds_setup_diagnostics.json / pds_first_eligible_setups.csv, irf_signal_diagnostics.csv, irf_first_red_comparison.csv, orb_missing_signal_audit.csv / .json, dated_corrections_comparison.csv, daily/<date>.md,
charts/<date>.svg, Phase52_Trade_Corrections_Verification.xlsx.
"""

from __future__ import annotations

import argparse
import csv
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

import phase51_diagnostics as D51  # noqa: E402
import phase51_evidence as E51  # noqa: E402
import phase51_reconcile as R51  # noqa: E402

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase52 as F  # noqa: E402
from nifty_trading.research import phase52_diag as D  # noqa: E402
from nifty_trading.research.phase35 import write_csv  # noqa: E402
from nifty_trading.strategies.definitions import to_candles  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase52_author_rules"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P51 = ROOT / "reports" / "phase5" / "phase51_author_corrections"
ORB_DATES = ["2025-09-11", "2025-09-16", "2025-10-08", "2025-10-16", "2025-10-17", "2025-10-27", "2025-11-21", "2025-11-28", "2025-12-05", "2025-12-12", "2025-12-24", "2025-12-30", "2025-12-31"]  # the 13 'ORB should have activated' dates of Phase 5.1
CUTOFF = "13:00"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def hm(ts) -> str:
    return f"{ts:%H:%M}"


def conf(records, strategy=None):
    return sorted((r for r in records if r.signal_status == "CONFIRMED" and (strategy is None or r.strategy == strategy)), key=lambda r: (r.signal_timestamp, r.strategy, r.method))


def levels_brief(r) -> str:
    lv = r.reference_levels or {}
    keys = ("recent_support", "support_candle_index", "recent_resistance", "resistance_candle_index", "extension_index", "red_candle_index", "zone_floor", "zone_ceiling", "zone_low", "zone_high", "small_support", "level_broken", "IRH", "IRL")
    return "; ".join(f"{k}={lv[k]}" for k in keys if k in lv and lv[k] is not None)


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0], formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__.split("\n\n", 1)[1])
    ap.add_argument("--config", action="append", choices=sorted(F.CONFIGS), help="configuration(s) to run besides the frozen reference (default: all)")
    ap.add_argument("--list", action="store_true", help="list the selectable configurations and exit")
    a = ap.parse_args()
    if a.list:
        for c in F.CONFIGS.values():
            print(f"{c.key:40} {c.authority:26} {c.title}")
        return 0
    keys = [F.FROZEN_KEY] + [k for k in (a.config or list(F.CONFIGS)) if k != F.FROZEN_KEY]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "daily").mkdir(exist_ok=True)
    (OUT / "charts").mkdir(exist_ok=True)
    m1 = load_one_minute()
    ctxs, _infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    opens = dict(zip(m1["timestamp"], m1["open"], strict=True))
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    sig = {k: F.signals_for(ctxs, sc, k) for k in keys}
    base = sig[F.FROZEN_KEY]
    trades = rd(P36 / "all_trades_detailed.csv")
    executed = {(t["date"], t["signal_confirmed_at"][-5:], t["strategy"]) for t in trades}

    # ============================================================================================ counts and all confirmed signals
    counts = {k: Counter((r.strategy, r.method) for d in sig[k] for r in conf(sig[k][d])) for k in keys}
    summary = {k: {"confirmed_total": sum(v.values()), "by_strategy": dict(Counter({s: sum(n for (st, _m), n in v.items() if st == s) for s in ("IRF", "ORB", "PDR", "PDS", "RF")})), "by_method": {f"{s}/{m}": n for (s, m), n in sorted(v.items())},
                   "authority": F.CONFIGS[k].authority} for k, v in counts.items()}
    rows_all = []
    for k in keys:
        for d in sorted(sig[k]):
            for r in conf(sig[k][d]):
                rows_all.append({"config": k, "date": str(d), "strategy": r.strategy, "method": r.method, "direction": r.direction, "signal_time": hm(r.signal_timestamp), "signal_candle_start": hm(r.signal_candle_start), "entry_reference_close": r.signal_candle_close,
                                 "within_13_00_cutoff": hm(r.signal_timestamp) <= CUTOFF, "levels": levels_brief(r), "concurrent_methods": ";".join(r.concurrent_methods), "flags": ";".join(f for f in r.flags if f.startswith("PHASE")),
                                 "executed_in_phase36_ledger": (str(d), hm(r.signal_timestamp), r.strategy) in executed and k == F.FROZEN_KEY})
    write_csv(OUT / "all_confirmed_signals.csv", rows_all)

    # ============================================================================================ before / after
    def keyed(records):
        out = defaultdict(list)
        for r in conf(records):
            out[(r.strategy, r.method, r.direction)].append(r)
        return out
    cause = {"phase52-approved": "co-confirmed PDS methods recorded (annotation only)", "phase52-cand-orb-colour": "ORB colour candidate: first candle colour contradicts the direction (ORB-GLOBAL-002 mirror for shorts is a source interpretation)",
             "phase52-cand-irf-first-red-low": "IRF 2A candidate: support = LOW of the first red candle (level definition not established)", "phase52-cand-irf-first-red-body-low": "IRF 2A candidate: support = BODY LOW of the first red candle (level definition not established)"}
    ba = []
    for k in keys[1:]:
        for d in sorted(ctxs):
            kb, kc = keyed(base[d]), keyed(sig[k][d])
            for key in sorted(set(kb) | set(kc)):
                lb, lc = kb.get(key, []), kc.get(key, [])
                for n in range(max(len(lb), len(lc))):
                    rb = lb[n] if n < len(lb) else None
                    rc = lc[n] if n < len(lc) else None
                    tb, tc = (None if rb is None else hm(rb.signal_timestamp)), (None if rc is None else hm(rc.signal_timestamp))
                    if rb is not None and rc is not None and tb == tc:
                        ctype = "UNCHANGED_TIME" if "concurrent" not in (";".join(rc.flags)) and not rc.concurrent_methods or rb.concurrent_methods == rc.concurrent_methods else "ANNOTATION_ONLY"
                        if ctype == "UNCHANGED_TIME":
                            continue
                    else:
                        ctype = "REMOVED" if rc is None else ("ADDED" if rb is None else "TIME_SHIFTED_EARLIER" if tc < tb else "TIME_SHIFTED_LATER")
                    ba.append({"config": k, "date": str(d), "strategy": key[0], "method": key[1], "direction": key[2], "change": ctype, "baseline_signal_time": tb or "", "candidate_signal_time": tc or "",
                               "baseline_levels": "" if rb is None else levels_brief(rb), "candidate_levels": "" if rc is None else levels_brief(rc), "rule_cause": cause[k], "executed_in_phase36_ledger": bool(rb is not None and (str(d), tb, key[0]) in executed),
                               "same_minute_collision_with_other_strategy": any(x.strategy != key[0] and hm(x.signal_timestamp) == (tc or tb) for x in conf(sig[k][d]))})
    write_csv(OUT / "before_after_signals.csv", ba)
    # earliest actionable signal per day
    dfs = []
    for k in keys[1:]:
        for d in sorted(ctxs):
            def first(records):
                c = [r for r in conf(records) if hm(r.signal_timestamp) <= CUTOFF]
                if not c:
                    return None, []
                t0 = c[0].signal_timestamp
                same = [r for r in c if r.signal_timestamp == t0]
                return c[0], same
            fb, sb = first(base[d])
            fc, scn = first(sig[k][d])
            tb, tc = (hm(fb.signal_timestamp) if fb else ""), (hm(fc.signal_timestamp) if fc else "")
            sb_s, sc_s = sorted({(r.strategy, r.method) for r in sb}), sorted({(r.strategy, r.method) for r in scn})
            if tb != tc or sb_s != sc_s:
                dfs.append({"config": k, "date": str(d), "baseline_first_signal": f"{tb} {';'.join(f'{s}/{m}' for s, m in sb_s)}", "candidate_first_signal": f"{tc} {';'.join(f'{s}/{m}' for s, m in sc_s)}",
                            "candidate_qualifies_earlier": bool(tb and tc and tc < tb) or bool(tc and not tb), "baseline_same_minute_collision": len({s for s, _ in sb_s}) > 1, "candidate_same_minute_collision": len({s for s, _ in sc_s}) > 1,
                            "note": "signal level only; the controller's policy (first valid signal; same-minute conflicts unresolved) is not applied here"})
    write_csv(OUT / "daily_first_signal_comparison.csv", dfs)

    # ============================================================================================ PDR / PDS first-eligible diagnostics
    pdr_all, pds_all = {}, {}
    pdr_rows, pds_rows = [], []
    verdicts = Counter()
    appr = sig["phase52-approved"] if "phase52-approved" in sig else base
    for d, c in sorted(ctxs.items()):
        pd_ = D.pdr_setup_diagnostics(c, sc)
        cmp_ = D.compare_with_engine(pd_, base[d], "PDR")
        pds_ = D.pds_setup_diagnostics(c, sc)
        cmp2 = D.compare_with_engine(pds_, base[d], "PDS")
        pdr_all[str(d)] = {**pd_, "comparison": cmp_}
        pds_all[str(d)] = {**pds_, "comparison": cmp2}
        verdicts[("PDR", cmp_["verdict"])] += 1
        verdicts[("PDS", cmp2["verdict"])] += 1
        if pd_["status"] != "NO_SETUP_NO_GAP_UP":
            cy = pd_["cycles"][0] if pd_.get("cycles") else {}
            pdr_rows.append({"date": str(d), "status": pd_["status"], "gap_points": pd_["gap_points"], "zone_construction_candle_start": pd_.get("zone_construction_candle_start", ""), "zone_floor": pd_.get("zone_floor", ""), "zone_ceiling": pd_.get("zone_ceiling", ""),
                             "open_strictly_above_ceiling": pd_.get("open_strictly_above_ceiling", ""), "first_zone_touch_candle_start": pd_.get("first_zone_touch_candle_start") or "", "interaction_candle_would_qualify_if_permitted": cy.get("interaction_candle_would_qualify", ""),
                             "first_eligible_candle_start": cy.get("first_eligible_candle_start") or "", "first_eligible_signal_time": pd_.get("first_eligible_signal_time") or "", "engine_first_signal_time": cmp_["engine_first_signal_time"] or "",
                             "later_confirmations_ignored": ";".join(cmp_["engine_signals_later_ignored"]), "verdict": cmp_["verdict"],
                             "sensA_retest_candle_permitted_approved_patterns": (pd_.get("sensitivity") or {}).get("A_retest_candle_permitted_approved_patterns") or "", "sensB_first_green_close_above_ceiling_after_retest_no_thresholds": (pd_.get("sensitivity") or {}).get("B_first_green_close_above_ceiling_after_retest_no_thresholds") or "",
                             "sensC_first_green_close_above_ceiling_retest_permitted_no_thresholds": (pd_.get("sensitivity") or {}).get("C_first_green_close_above_ceiling_retest_permitted_no_thresholds") or "",
                             "reasons_earlier_candles_not_eligible": " || ".join(f"{r['candle_start']}: {r['reason_not_eligible']}" for r in (cy.get("candidates") or []) if not r["qualifies"])[:1500]})
        if pds_["status"] != "NO_SETUP_NO_GAP_DOWN":
            ev = pds_.get("events") or []
            pds_rows.append({"date": str(d), "status": pds_["status"], "gap_points": pds_["gap_points"], "zone_low": pds_.get("zone_low", ""), "zone_high": pds_.get("zone_high", ""), "open_below_zone_low": pds_.get("open_below_zone_low", ""),
                             "first_eligible_method": pds_.get("first_eligible_method") or "", "first_eligible_signal_time": pds_.get("first_eligible_signal_time") or "", "co_confirmed_methods": ";".join(ev[0]["also_satisfied"]) if ev else "",
                             "engine_first_signal_time": cmp2["engine_first_signal_time"] or "", "later_events_ignored": ";".join(f"{e['method']}@{e['signal_time']}" for e in ev[1:]), "verdict": cmp2["verdict"], "later_strong_red_candles_after_weak_first_red": "; ".join(pds_.get("later_strong_red_candles_after_weak_first_red") or []),
                             "candidate_roles": " || ".join(f"{r['candle_start']} {r['role']}" + (f" strong={r.get('strong_bearish')} pin={r.get('bearish_pin_hpr')}" if "strong_bearish" in r else "") for r in pds_["candidates"])[:1200]})
    (OUT / "pdr_setup_diagnostics.json").write_text(json.dumps(pdr_all, indent=1, default=str))
    (OUT / "pds_setup_diagnostics.json").write_text(json.dumps(pds_all, indent=1, default=str))
    write_csv(OUT / "pdr_first_eligible_setups.csv", pdr_rows)
    write_csv(OUT / "pds_first_eligible_setups.csv", pds_rows)
    summary["first_eligible_verdicts"] = {f"{s}:{v}": n for (s, v), n in sorted(verdicts.items())}
    summary["pds_sessions_with_co_confirmed_methods"] = [r["date"] for r in pds_rows if r["co_confirmed_methods"]]
    summary["approved_equals_frozen_on_every_signal_key"] = all([(r.strategy, r.method, r.direction, r.signal_status, str(r.signal_timestamp)) for r in conf(base[d])] == [(r.strategy, r.method, r.direction, r.signal_status, str(r.signal_timestamp)) for r in conf(appr[d])] for d in ctxs)

    # ============================================================================================ IRF diagnostics (EMA 28, day's low) on every confirmed baseline IRF signal
    irf_rows = []
    for d, c in sorted(ctxs.items()):
        cs = to_candles(c.candles)
        for r in conf(base[d], "IRF"):
            fill = opens.get(r.signal_timestamp)
            m = D.irf_measurements(c, cs, r.signal_timestamp, fill)
            m.update({"date": str(d), "method": r.method, "executed_in_phase36_ledger": (str(d), hm(r.signal_timestamp), "IRF") in executed, "within_13_00_cutoff": hm(r.signal_timestamp) <= CUTOFF})
            irf_rows.append(m)
    write_csv(OUT / "irf_signal_diagnostics.csv", irf_rows)
    flag_keys = ["E1_close_gap_below_ema_28", "E2_entry_gap_below_ema_28", "E3_low_gap_below_ema_28", "E4_abs_close_gap_28", "E1_27", "E2_27", "E1_between_27_and_28", "E2_between_27_and_28", "ema_between_entry_and_t1",
                 "D1_entry_at_or_below_running_low", "D2_close_below_running_low_before", "D3_close_at_running_low_incl_candle", "D4_t1_beyond_running_low", "D5_entry_within_28_of_running_low", "D6_running_low_already_below_irl", "D7_earlier_close_below_irl", "D8_entry_below_previous_day_low"]
    irf_flag_counts = {"signals": len(irf_rows), "executed": sum(1 for r in irf_rows if r["executed_in_phase36_ledger"]), "signals_within_13_00_cutoff": sum(1 for r in irf_rows if r["within_13_00_cutoff"])}
    for fk in flag_keys:
        irf_flag_counts[fk] = {"all_signals": sum(1 for r in irf_rows if r.get(fk)), "executed": sum(1 for r in irf_rows if r.get(fk) and r["executed_in_phase36_ledger"]), "within_13_00_cutoff": sum(1 for r in irf_rows if r.get(fk) and r["within_13_00_cutoff"]), "executed_within_cutoff": sum(1 for r in irf_rows if r.get(fk) and r["executed_in_phase36_ledger"] and r["within_13_00_cutoff"]),
                              "all_signals_by_method": dict(Counter(r["method"] for r in irf_rows if r.get(fk)))}
    summary["irf_flag_counts"] = irf_flag_counts

    # ============================================================================================ IRF first-red comparison on the executed Method-2 trades
    flagged = set(json.loads((P51 / "population_impact.json").read_text())["irf_flags"]["first_red_reading_differs"]["trades"])
    first_red_dated = {"2025-09-01": "AC01", "2025-09-10": "AC03", "2025-09-22": "AC08", "2025-09-29": "AC09", "2025-11-13": "AC20", "2025-11-26": "AC26", "2025-12-15": "AC34"}
    author_dir = {r["correction_id"]: r["earlier_later_or_not_at_all"] for r in rd(P51 / "all_author_corrections.csv")}
    fr_rows = []
    for t in trades:
        if t["strategy"] != "IRF" or not t["method"].startswith("Method 2"):
            continue
        d = date.fromisoformat(t["date"])
        c = ctxs[d]
        cs = to_candles(c.candles)
        st = t["signal_confirmed_at"][-5:]
        rb = next(r for r in conf(base[d], "IRF") if hm(r.signal_timestamp) == st and r.method == t["method"])
        lv = rb.reference_levels
        ri = lv.get("red_candle_index")
        red = cs[ri] if ri is not None else None
        oldref = None
        if "support_candle_index" in lv:
            oldref = ("support", cs[lv["support_candle_index"]], lv["recent_support"])
        elif "resistance_candle_index" in lv:
            oldref = ("resistance", cs[lv["resistance_candle_index"]], lv["recent_resistance"])
        row = {"trade_id": t["trade_id"], "date": t["date"], "baseline_method": t["method"], "baseline_signal_time": st, "baseline_entry_reference_close": rb.signal_candle_close,
               "old_reference_kind": "" if oldref is None else oldref[0], "old_reference_candle_start": "" if oldref is None else hm(oldref[1].start), "old_reference_level": "" if oldref is None else oldref[2],
               "old_reference_candle_ohlc": "" if oldref is None else f"{oldref[1].o}/{oldref[1].h}/{oldref[1].l}/{oldref[1].c}",
               "first_qualifying_red_candle_start": "" if red is None else hm(red.start), "first_red_candle_ohlc": "" if red is None else f"{red.o}/{red.h}/{red.l}/{red.c}", "support_level_if_LOW": "" if red is None else red.l, "support_level_if_BODY_LOW": "" if red is None else min(red.o, red.c),
               "in_phase51_37_reading_disagreements": t["trade_id"] in flagged}
        for k, tag in (("phase52-cand-irf-first-red-low", "LOW"), ("phase52-cand-irf-first-red-body-low", "BODY_LOW")):
            if k not in sig:
                continue
            c2a = [r for r in conf(sig[k][d], "IRF") if r.method == "Method 2A"]
            cfirst = conf(sig[k][d], "IRF")
            row[f"candidate_{tag}_2A_break_signal_time"] = hm(c2a[0].signal_timestamp) if c2a else ""
            row[f"candidate_{tag}_2A_break_close"] = c2a[0].signal_candle_close if c2a else ""
            row[f"candidate_{tag}_first_IRF_signal"] = f"{hm(cfirst[0].signal_timestamp)} {cfirst[0].method}" if cfirst else ""
            row[f"candidate_{tag}_change_vs_baseline_executed_signal"] = ("no IRF signal" if not cfirst else ("same time and method" if (hm(cfirst[0].signal_timestamp), cfirst[0].method) == (st, t["method"]) else
                                                                    f"{'earlier' if hm(cfirst[0].signal_timestamp) < st else 'later' if hm(cfirst[0].signal_timestamp) > st else 'same minute'} ({st} -> {hm(cfirst[0].signal_timestamp)} {cfirst[0].method})"))
        ac = first_red_dated.get(t["date"])
        row["handwritten_dated_example"] = ac or ""
        row["author_stated_direction"] = author_dir.get(ac, "") if ac else ""
        row["source_evidence"] = ("DATED EXAMPLE " + ac + " (author: " + author_dir.get(ac, "") + ") + the call statement; the LEVEL (low / body low / local support) is not stated" if ac else "call statement only (no dated handwritten example); the level is not stated")
        fr_rows.append(row)
    write_csv(OUT / "irf_first_red_comparison.csv", fr_rows)

    # ============================================================================================ ORB missing-signal audit
    orb_rows, orb_json = [], {}
    for ds in ORB_DATES:
        d = date.fromisoformat(ds)
        au = D.orb_audit(ctxs[d], sc, base[d])
        au["cause_category"] = D.orb_cause_category(au)
        orb_json[ds] = au
        fc = au["first_candle"]
        for dirn in ("LONG", "SHORT"):
            it = au["directions"][dirn]
            orb_rows.append({"date": ds, "direction": dirn, "first_candle_colour": fc["colour"], "first_candle_ohlc": f"{fc['open']}/{fc['high']}/{fc['low']}/{fc['close']}", "body_pct": fc["body_pct"], "upper_wick_pct": fc["upper_wick_pct"], "lower_wick_pct": fc["lower_wick_pct"],
                             "prev_day_high": au["prev_day_high"], "prev_day_low": au["prev_day_low"], "ema200": round(au["ema200_first_candle"], 2), "close_minus_ema": round(au["close_minus_ema"], 2), "gap_points": au["gap"]["points"],
                             "M1_level": it["M1_prev_day_level"], "M1_level_broken": it["M1_level_broken"], "M2_inner_level": it["M2_inner_level"], "M2_inner_level_broken": it["M2_inner_level_broken"], "M2_trendline_supportive": it["M2_trendline_supportive"],
                             "trend_ok": it["trend_ok"], "trend_reason": it["trend_reason"], "colour_matches_direction": it["colour_matches_direction"],
                             "strength_STRICT": it["strength_profiles"]["STRICT"], "strength_MODERATE_active": it["strength_profiles"]["MODERATE"], "strength_LOOSE": it["strength_profiles"]["LOOSE"], "gap_setup_gap_crosses_ma": it["gap_setup_gap_crosses_ma"],
                             "first_failing_M1": it["first_failing_rule"]["Method 1"], "first_failing_M2": it["first_failing_rule"]["Method 2"], "first_failing_Gap": it["first_failing_rule"]["Gap/200DMA"], "cause_category_for_colour_direction": au["cause_category"]})
    write_csv(OUT / "orb_missing_signal_audit.csv", orb_rows)
    (OUT / "orb_missing_signal_audit.json").write_text(json.dumps(orb_json, indent=1, default=str))
    summary["orb_missing_signal_causes"] = dict(Counter(v["cause_category"] for v in orb_json.values()))
    (OUT / "signal_counts.json").write_text(json.dumps(summary, indent=1, default=str))

    # ============================================================================================ dated corrections comparison (Phase 5.1 observations)
    topic = {}
    for ac in ("AC01", "AC03", "AC08", "AC09", "AC20", "AC26", "AC34"):
        topic[ac] = "IRF_FIRST_RED_CANDLE"
    for ac in ("AC13", "AC18"):
        topic[ac] = "IRF_EMA_28"
    for ac in ("AC19", "AC32", "G02"):
        topic[ac] = "IRF_DAY_LOW"
    for ac in ("AC02", "AC10", "AC11", "AC29", "AC40"):
        topic[ac] = "PDR_FIRST_ELIGIBLE"
    for ac in ("AC38",):
        topic[ac] = "PDS_FIRST_ELIGIBLE"
    for ac in ("AC04", "AC06", "AC12", "AC14", "AC15", "AC16", "AC24", "AC28", "AC31", "AC33", "AC37", "AC39"):
        topic[ac] = "ORB_MISSING"
    topic["AC27"] = "ORB_COLOUR"
    for ac in ("AC07",):
        topic[ac] = "IRF_ENTRY_BODY (not in the call)"
    cur = {"IRF_FIRST_RED_CANDLE": "Method 2A: a candle closes below the swing-low fractal support left by the extension (SWING_K1) after a red candle has formed; Method 2B: a red candle closes back below the first push top after trading above it",
           "IRF_EMA_28": "no EMA condition exists in the IRF guide or the engine", "IRF_DAY_LOW": "no day's-low condition exists in the IRF guide or the engine",
           "PDR_FIRST_ELIGIBLE": "zone retest, then the first later candle with GOOD_GREEN_BODY (body >= 60%, upper wick <= 20%) or LOWER_PRICE_REJECTION or HAMMER that closes strictly above the zone ceiling; the retest candle itself is not a confirmation (PDR-A07)",
           "PDS_FIRST_ELIGIBLE": "Methods 1/2 on the FIRST red candle at the zone (strong body, or higher-price-rejection pin); a weak first red candle is not taken (PDS-M-001) and Method 3 waits for the small-support break",
           "ORB_MISSING": "Methods 1 / 2 / gap setup as encoded (Method 2 inner level and trendline are research variants); strength profile MODERATE (body >= 60%, opposite wick <= 20%) with a conditional pin bar",
           "ORB_COLOUR": "the pin-bar route admits a first candle of either colour", "IRF_ENTRY_BODY (not in the call)": "no entry-candle body test for IRF"}
    prop = {"IRF_FIRST_RED_CANDLE": "candidate (not active): Method 2A support = first red candle's LOW or BODY LOW; first red candle never replaced by a later one", "IRF_EMA_28": "diagnostics only: 28-point reading and inequality not established",
            "IRF_DAY_LOW": "diagnostics only: running-low readings computed at decision time; the source statement is not located", "PDR_FIRST_ELIGIBLE": "already satisfied: the engine activates on the first eligible candle; the numeric thresholds and the retest-candle convention are preserved",
            "PDS_FIRST_ELIGIBLE": "already satisfied for Methods 1/2/3; the weak-first-candle quality rule is preserved", "ORB_MISSING": "audit only: the first failing rule per date; no priority override and no threshold change", "ORB_COLOUR": "candidate (opt-in, Phase 5.1): long needs green, short red",
            "IRF_ENTRY_BODY (not in the call)": "not addressed by the call; remains an owner decision"}
    resolved = {"IRF_FIRST_RED_CANDLE": "NO - candidate only; level and method scope unresolved", "IRF_EMA_28": "NO - diagnostics only", "IRF_DAY_LOW": "NO - diagnostics only", "PDR_FIRST_ELIGIBLE": "PARTLY - the engine is on the first eligible candle only under the PRESERVED proposals (PDR-A07 retest convention, numeric thresholds); the author's example candle is not eligible under them",
                "PDS_FIRST_ELIGIBLE": "PARTLY - satisfied under the preserved quality rule (PDS-M-001, Method 3 after a weak first red candle); the author's 'first candle' example is not satisfied", "ORB_MISSING": "EXPLAINED (cause identified); not changed", "ORB_COLOUR": "CANDIDATE selectable; not active", "IRF_ENTRY_BODY (not in the call)": "NO"}
    explicit = {"IRF_FIRST_RED_CANDLE": "ambiguous (level)", "IRF_EMA_28": "ambiguous (measure, inequality, scope; 28 vs the handwritten 27)", "IRF_DAY_LOW": "ambiguous (meaning); source location unverified", "PDR_FIRST_ELIGIBLE": "explicit and USER_APPROVED", "PDS_FIRST_ELIGIBLE": "explicit and USER_APPROVED",
                "ORB_MISSING": "explicit complaint; cause not a single rule", "ORB_COLOUR": "explicit for long; short is an interpretation", "IRF_ENTRY_BODY (not in the call)": "n/a"}
    owner = {"IRF_FIRST_RED_CANDLE": "O4 (level definition: low / body low / local support; scope 2A only or also 2B / Method 3)", "IRF_EMA_28": "O2 (distance measure, inequality, skip vs wait, scope, 27 vs 28)", "IRF_DAY_LOW": "O3 (meaning; where in the documents)",
             "PDR_FIRST_ELIGIBLE": "O6/O7 (loosen the numeric thresholds? may the retest candle be the confirmation?)", "PDS_FIRST_ELIGIBLE": "O6 (the weak-first-red-candle quality rule)", "ORB_MISSING": "O8 (ORB inner level, trendline, strength profile, trend filter)",
             "ORB_COLOUR": "O1 (adopt? short mirror)", "IRF_ENTRY_BODY (not in the call)": "O5 (body threshold)"}
    corr = rd(P51 / "all_author_corrections.csv")
    cls = {r["correction_id"]: r for r in rd(P51 / "correction_classifications.csv")}
    dc_rows = []
    first_by_date = {}
    for r in corr:
        ds = r["date"]
        tp = topic.get(r["correction_id"], "NOT_ADDRESSED_BY_THE_CALL")
        row = {"correction_id": r["correction_id"], "trading_date": ds, "handwritten_pdf_page": r["pdf_page"], "original_author_comment": r["author_text_verbatim"], "topic": tp}
        if ds:
            d = date.fromisoformat(ds)
            c = ctxs[d]
            cs = to_candles(c.candles)
            tr = next((t for t in trades if t["date"] == ds and t["trade_no_of_day"] == r["trade_no"]), None)
            row.update({"original_strategy": "" if tr is None else f"{tr['strategy']} {tr['method']}", "original_signal_timestamp": "" if tr is None else tr["signal_confirmed_at"][-5:], "expected_strategy_or_candle": r["suggested_strategy"] + " | " + r["earlier_later_or_not_at_all"]})
            if tr is not None:
                end = tr["signal_confirmed_at"][-5:]
                cd = next((x for x in cs if hm(x.end) == end), None)
                idx = next((k for k, x in enumerate(cs) if hm(x.end) == end), None)
                ema = None if idx is None else float(c.candles["ema200_5m"].iloc[idx])
                row.update({"entry_candle_ohlc": "" if cd is None else f"{cd.o}/{cd.h}/{cd.l}/{cd.c}", "ema200_at_entry_candle": "" if ema is None else round(ema, 2), "entry_price": tr["entry_price"], "stop_t1_t2": f"{tr['initial_stop']} / {tr['target_1']} / {tr['target_2']}"})
            row["levels"] = "; ".join(f"{k}={v}" for k, v in {"prev_high": c.previous.high, "prev_low": c.previous.low, "prev_close": c.previous.close_official, "open": c.open_price, "IRH": cs[0].h, "IRL": cs[0].l}.items())
            if tp == "PDR_FIRST_ELIGIBLE":
                dg = pdr_all.get(ds, {})
                row["phase52_evidence"] = f"zone [{dg.get('zone_floor')}, {dg.get('zone_ceiling')}], first touch {dg.get('first_zone_touch_candle_start')}, first eligible signal {dg.get('first_eligible_signal_time')}, engine {dg.get('comparison', {}).get('engine_first_signal_time')}, verdict {dg.get('comparison', {}).get('verdict')}"
                z = (dg.get("zone_floor"), dg.get("zone_ceiling"))
                if z[0]:
                    g = D51.first_green_after_zone(E51.candle_rows(c), z[0], z[1])
                    if g and g.get("first_green_close_above_ceiling"):
                        fg = g["first_green_close_above_ceiling"]
                        row["author_reading_first_green_candle"] = f"{fg['candle_start']} (body {fg['body_pct']}%, upper wick {fg['upper_wick_pct']}%, lower wick {fg['lower_wick_pct']}%)"
            elif tp == "PDS_FIRST_ELIGIBLE":
                dg = pds_all.get(ds, {})
                row["phase52_evidence"] = f"zone [{dg.get('zone_low')}, {dg.get('zone_high')}], first eligible {dg.get('first_eligible_method')} at {dg.get('first_eligible_signal_time')}, engine {dg.get('comparison', {}).get('engine_first_signal_time')}, verdict {dg.get('comparison', {}).get('verdict')}"
            elif tp == "IRF_FIRST_RED_CANDLE":
                fr = next((x for x in fr_rows if x["date"] == ds), None)
                row["phase52_evidence"] = "" if fr is None else f"old reference {fr['old_reference_kind']} {fr['old_reference_level']} (candle {fr['old_reference_candle_start']}); first red candle {fr['first_qualifying_red_candle_start']} OHLC {fr['first_red_candle_ohlc']}; candidate LOW: {fr.get('candidate_LOW_change_vs_baseline_executed_signal', '')}; candidate BODY_LOW: {fr.get('candidate_BODY_LOW_change_vs_baseline_executed_signal', '')}"
            elif tp in ("IRF_EMA_28", "IRF_DAY_LOW"):
                m = next((x for x in irf_rows if x["date"] == ds and x.get("executed_in_phase36_ledger")), None) or next((x for x in irf_rows if x["date"] == ds), None)
                if m:
                    keysel = ["close_minus_ema", "entry_minus_ema", "ema_between_entry_and_t1", "ema_minus_t1", "E1_close_gap_below_ema_28", "E2_entry_gap_below_ema_28"] if tp == "IRF_EMA_28" else ["running_low_before_signal_candle", "entry_minus_running_low_before", "t1_clearance_above_running_low", "D1_entry_at_or_below_running_low", "D2_close_below_running_low_before", "D4_t1_beyond_running_low", "irl", "D6_running_low_already_below_irl", "D7_earlier_close_below_irl", "previous_day_low", "D8_entry_below_previous_day_low"]
                    row["phase52_evidence"] = "; ".join(f"{k}={m.get(k)}" for k in keysel)
            elif tp == "ORB_MISSING":
                au = orb_json.get(ds)
                if au:
                    row["phase52_evidence"] = f"cause {au['cause_category']}; first candle {au['first_candle']['colour']} body {au['first_candle']['body_pct']}%; first failing (colour direction): " + "; ".join(f"{k}: {v}" for k, v in au["directions"]["LONG" if au["first_candle"]["colour"] != "RED" else "SHORT"]["first_failing_rule"].items())
            elif tp == "ORB_COLOUR":
                row["phase52_evidence"] = "ORB colour candidate invalidates this confirmation (see before_after_signals.csv, config phase52-cand-orb-colour)"
        else:
            row.update({"original_strategy": "", "original_signal_timestamp": "", "expected_strategy_or_candle": r["suggested_strategy"], "phase52_evidence": "general remark (no date)"})
        row.update({"current_entry_conditions": cur.get(tp, "not addressed by the call; unchanged"), "proposed_corrected_entry_conditions": prop.get(tp, "none"), "new_instruction_explicit_or_ambiguous": explicit.get(tp, "n/a"), "phase52_resolves": resolved.get(tp, "NO - not addressed"),
                    "remaining_owner_decision": owner.get(tp, "see phase51 owner_approval_required.md"), "phase51_classification": cls[r["correction_id"]]["classifications"]})
        dc_rows.append(row)
        if ds:
            first_by_date.setdefault(ds, []).append(row)
    write_csv(OUT / "dated_corrections_comparison.csv", dc_rows)

    # ============================================================================================ day reports and charts
    def mark_candidates(d, marks):
        for k, tagc in (("phase52-cand-irf-first-red-low", "#6a1b9a"), ("phase52-cand-irf-first-red-body-low", "#00897b")):
            if k in sig:
                cf = conf(sig[k][d], "IRF")
                if cf:
                    marks.append({"time": hm(cf[0].signal_timestamp), "price": cf[0].signal_candle_close, "colour": tagc, "label": f"{k.split('cand-')[1]} first IRF {cf[0].method}"})
    for ds, items in sorted(first_by_date.items()):
        d = date.fromisoformat(ds)
        ev = json.loads((P51 / "evidence" / f"{ds}.json").read_text())
        marks = []
        for t in [t for t in trades if t["date"] == ds][:2]:
            marks.append({"time": t["signal_confirmed_at"][-5:], "price": float(t["entry_price"]), "colour": "#d81b60", "label": f"baseline {t['strategy']} {t['method'][-2:].strip()}"})
        mark_candidates(d, marks)
        zone = None
        if ds in pdr_all and pdr_all[ds].get("zone_floor") and any(i["topic"] == "PDR_FIRST_ELIGIBLE" for i in items):
            zone = (pdr_all[ds]["zone_floor"], pdr_all[ds]["zone_ceiling"])
            fe = pdr_all[ds].get("first_eligible_signal_time")
            if fe:
                marks.append({"time": fe, "price": next((c["c"] for c in ev["candles"] if c["end"] == fe), 0.0), "colour": "#2e7d32", "label": "first eligible PDR confirmation"})
        if ds in pds_all and pds_all[ds].get("zone_low") and any(i["topic"] == "PDS_FIRST_ELIGIBLE" for i in items):
            zone = (pds_all[ds]["zone_low"], pds_all[ds]["zone_high"])
        if ev.get("candles"):
            (OUT / "charts" / f"{ds}.svg").write_text(R51.candle_svg(ev, marks, zone, f"{ds} Phase 5.2: " + " / ".join(i["correction_id"] for i in items)))
        md = [f"# {ds} - Phase 5.2 original versus corrected signals", "", "> Signal-level comparison only: no controller, no fills, no P&L. Candidates are NOT approved rules.", ""]
        for i in items:
            md += [f"## {i['correction_id']} (PDF page {i['handwritten_pdf_page']}) - topic `{i['topic']}`", "", f"> {i['original_author_comment']}", "", f"* Original automated trade: {i.get('original_strategy', '')} signal {i.get('original_signal_timestamp', '')}; entry candle OHLC {i.get('entry_candle_ohlc', '')}; EMA200 at that candle {i.get('ema200_at_entry_candle', '')}; {i.get('levels', '')}",
                   f"* Expected (author): {i['expected_strategy_or_candle']}", f"* Current entry conditions: {i['current_entry_conditions']}", f"* Phase 5.2: {i['proposed_corrected_entry_conditions']}", f"* Evidence: {i.get('phase52_evidence', '')}" + (f"; author's reading: {i['author_reading_first_green_candle']}" if i.get("author_reading_first_green_candle") else ""),
                   f"* Explicit or ambiguous: {i['new_instruction_explicit_or_ambiguous']}; resolved by Phase 5.2: {i['phase52_resolves']}; remaining decision: {i['remaining_owner_decision']}", ""]
        chg = [r for r in ba if r["date"] == ds]
        md += ["### Signal changes under the candidate configurations (this date)", ""]
        md += (["| config | strategy | method | change | baseline | candidate | rule cause |", "|---|---|---|---|---|---|---|"] + [f"| {r['config']} | {r['strategy']} | {r['method']} | {r['change']} | {r['baseline_signal_time']} | {r['candidate_signal_time']} | {r['rule_cause'][:70]} |" for r in chg]) if chg else ["No confirmed-signal difference under any candidate on this date."]
        md += ["", f"![{ds}](../charts/{ds}.svg)", ""]
        (OUT / "daily" / f"{ds}.md").write_text("\n".join(md) + "\n")

    # ============================================================================================ workbook
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill
    wb = Workbook()
    ws = wb.active
    ws.title = "README"
    for n, line in enumerate(["Phase 5.2 - original versus corrected signals (signal level only: no controller, no fills, no P&L)",
                              "Active reference = frozen Phase 3.6. 'phase52-approved' = first eligible confirmation candle for PDR / PDS (already satisfied by the frozen engines; co-confirmed PDS methods recorded). Candidates (ORB colour, IRF first-red LOW / BODY_LOW) are NOT approved.",
                              "Sheets: Dated Corrections (one row per handwritten observation), Before After Signals, First Signal Per Day, IRF First Red, IRF Diagnostics, PDR Setups, PDS Setups, ORB Audit, Signal Counts."], 1):
        ws.cell(row=n, column=1, value=line)
    ws["A1"].font = Font(bold=True, size=13)
    ws.column_dimensions["A"].width = 160

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
    add("Dated Corrections", dc_rows)
    add("Before After Signals", ba)
    add("First Signal Per Day", dfs)
    add("IRF First Red", fr_rows)
    add("IRF Diagnostics", irf_rows)
    add("PDR Setups", pdr_rows)
    add("PDS Setups", pds_rows)
    add("ORB Audit", orb_rows)
    add("Signal Counts", [{"config": k, "authority": v["authority"], "confirmed_total": v["confirmed_total"], **{f"{s}": n for s, n in v["by_strategy"].items()}} for k, v in summary.items() if isinstance(v, dict) and "confirmed_total" in v])
    wb.save(OUT / "Phase52_Trade_Corrections_Verification.xlsx")
    print(json.dumps({k: v for k, v in summary.items() if k in ("first_eligible_verdicts", "approved_equals_frozen_on_every_signal_key", "orb_missing_signal_causes")}, indent=0))
    print({k: (v["confirmed_total"], v["by_strategy"]) for k, v in summary.items() if isinstance(v, dict) and "confirmed_total" in v})
    print(f"{len(ba)} before/after rows, {len(dfs)} first-signal differences, {len(fr_rows)} IRF M2 comparisons, {len(dc_rows)} dated rows, {len(list((OUT / 'daily').glob('*.md')))} day reports")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
