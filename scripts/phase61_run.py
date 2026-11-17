"""Phase 6.1: IRF-V2-SUPPORT-BREAK signal-level work: frozen (A) vs Phase 5.3 (B) vs V2 (C) signal comparison, reference-candle audit, EMA-28 diagnostics, handwritten IRF cases, independent audit and charts.
Signals only: no controller, no fills, no P&L here (the combined backtest is Phase 6.2)."""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase60_common as P60  # noqa: E402
from phase61_common import R61, ROOT, window_data, write_csv  # noqa: E402

from nifty_trading.research import irf_v2_audit as AUD  # noqa: E402
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research.orb_v2.models import Level  # noqa: E402
from nifty_trading.research.orb_v2.reporting import svg_chart, write_workbook  # noqa: E402
from nifty_trading.strategies.irf import IRFStrategy  # noqa: E402
from nifty_trading.strategies.irf_phase53 import IRFPhase53Strategy  # noqa: E402
from nifty_trading.strategies.irf_v2 import IRFV2SupportBreakStrategy  # noqa: E402

CUT = "13:00"


def sig_row(r):
    lv = r.reference_levels
    return {"date": str(r.signal_date), "time": f"{r.signal_timestamp:%H:%M}", "method": r.method, "direction": r.direction, "support": lv.get("recent_support"), "resistance": lv.get("recent_resistance"),
            "reference_close": r.signal_candle_close, "first_red_candle_start": lv.get("first_red_candle_start"), "first_red_candle_ohlc": lv.get("first_red_candle_ohlc"), "lv": lv}


def run_window(win, sc):
    ctxs, infos, bars, cal, label = window_data(win)
    frozen = IRFStrategy(proposals=sc.proposals, trade=sc.trade)
    p53 = IRFPhase53Strategy(proposals=sc.proposals, trade=sc.trade, support_ref="FIRST_RED_LOW", ema_min_clearance=28.0, ema_scope="ALL_METHODS", ema_measure="RANGE")
    v2 = IRFV2SupportBreakStrategy(proposals=sc.proposals, trade=sc.trade)
    out = {"frozen": [], "p53": [], "v2": []}
    for d in sorted(ctxs):
        for k, e in (("frozen", frozen), ("p53", p53), ("v2", v2)):
            out[k] += [sig_row(r) for r in e.evaluate_session(ctxs[d]) if r.signal_status == "CONFIRMED"]
    return out, v2.attempt_log, v2.rejections, ctxs


def main() -> int:  # noqa: C901
    R61.mkdir(parents=True, exist_ok=True)
    sc = P.combined_scenario("BODY_BASED_PHASE36")
    state: dict = {}
    allres = {}
    for win in ("A", "B"):
        allres[win] = run_window(win, sc)
        o = allres[win][0]
        print(win, {k: len(v) for k, v in o.items()}, "attempts", len(allres[win][1]), "ema rejections", len(allres[win][2]), flush=True)
    out, attempts, rejections, ctxs = allres["A"]
    # ------------------------------------------------------------------ before/after (primary window)
    kf = {(r["date"], r["time"], r["method"]): r for r in out["frozen"]}
    kp = {(r["date"], r["time"], r["method"]): r for r in out["p53"]}
    kv = {(r["date"], r["time"], r["method"]): r for r in out["v2"]}
    rej = {(x["date"], x["signal_time"], x["method"]): x for x in rejections}
    a2_v = defaultdict(list)
    a2_f = defaultdict(list)
    for (d, t, m) in kv:
        if m == "Method 2A":
            a2_v[d].append(t)
    for (d, t, m) in kf:
        if m == "Method 2A":
            a2_f[d].append(t)
    rows, cnt = [], Counter()
    for key in sorted(set(kf) | set(kp) | set(kv)):
        d, t, m = key
        inf, inp_, inv = key in kf, key in kp, key in kv
        if inf and inv:
            ct = "UNCHANGED"
            if m == "Method 2A" and kf[key]["support"] != kv[key]["support"]:
                ct = "SUPPORT_LEVEL_CHANGED_SAME_TIME"
            cause = ""
        elif inf:
            ct = "REMOVED"
            if key in rej:
                cause = "EMA_28_CLEARANCE_REJECTED"
            elif m == "Method 2A" and a2_v.get(d):
                cause = "SUPPORT_REFERENCE_CHANGED (first red candle low)"
            else:
                cause = "ATTEMPT_LIFECYCLE / DOWNSTREAM"
        else:
            ct = "ADDED"
            if m == "Method 2A":
                cause = "SUPPORT_REFERENCE_CHANGED (first red candle low)"
            else:
                cause = "ATTEMPT_LIFECYCLE / DOWNSTREAM (a frozen attempt ended differently, so a later setup of the same session can now start)"
        shift = ""
        if m == "Method 2A" and a2_f.get(d) and a2_v.get(d) and ct in ("ADDED", "REMOVED"):
            shift = "EARLIER" if min(a2_v[d]) < min(a2_f[d]) else ("LATER" if min(a2_v[d]) > min(a2_f[d]) else "")
        cnt[ct + ("" if not cause else "|" + cause.split(" ")[0])] += 1
        rows.append({"date": d, "time": t, "method": m, "within_13_00": t <= CUT, "frozen_phase36": inf, "phase53": inp_, "irf_v2": inv, "v2_equals_phase53": inp_ == inv, "change_frozen_to_v2": ct, "cause": cause, "method2a_first_signal_shift": shift,
                     "frozen_support": kf[key]["support"] if inf else "", "v2_support": kv[key]["support"] if inv else "", "v2_first_red_candle": kv[key]["first_red_candle_ohlc"] if inv else "", "ema_rejection_distance": rej[key]["distance"] if key in rej else ""})
    write_csv(R61 / "irf_before_after_signals.csv", rows)
    def tot(win, k): return len(allres[win][0][k])  # noqa: E704
    chg = Counter(r["change_frozen_to_v2"] for r in rows)
    shifts = Counter(r["method2a_first_signal_shift"] for r in rows if r["method2a_first_signal_shift"])
    state["signal_comparison"] = {"A": {k: tot("A", k) for k in ("frozen", "p53", "v2")}, "B": {k: tot("B", k) for k in ("frozen", "p53", "v2")}, "v2_equals_phase53_A": kp.keys() == kv.keys(), "v2_equals_phase53_B": {(r["date"], r["time"], r["method"]) for r in allres["B"][0]["p53"]} == {(r["date"], r["time"], r["method"]) for r in allres["B"][0]["v2"]},
                                  "changes_frozen_to_v2": dict(chg), "removed_causes": dict(Counter(r["cause"] for r in rows if r["change_frozen_to_v2"] == "REMOVED")), "added_causes": dict(Counter(r["cause"].split(" (")[0] for r in rows if r["change_frozen_to_v2"] == "ADDED")),
                                  "by_method_frozen": dict(Counter(m for (_, _, m) in kf)), "by_method_v2": dict(Counter(m for (_, _, m) in kv)), "method2a_shifts": dict(shifts),
                                  "support_level_changed_same_time": chg.get("SUPPORT_LEVEL_CHANGED_SAME_TIME", 0), "ema_rejections": len(rejections), "ema_rejections_by_method": dict(Counter(x["method"] for x in rejections)),
                                  "within_13_00": {k: sum(1 for r in out[k] if r["time"] <= CUT) for k in out}}
    # ------------------------------------------------------------------ reference candle audit (every Method 2 attempt)
    write_csv(R61 / "irf_reference_candle_audit.csv", [{"window": w, **a} for w in ("A", "B") for a in allres[w][1]])
    # ------------------------------------------------------------------ EMA-28 diagnostics: every V2 confirmed signal plus every rejected candidate
    ema_rows = []
    for w in ("A", "B"):
        for r in allres[w][0]["v2"]:
            lv = r["lv"]
            ema_rows.append({"window": w, "date": r["date"], "time": r["time"], "method": r["method"], "status": "PASSED_AND_CONFIRMED", "ema_at_confirmation": lv.get("ema_at_confirmation"), "relation_to_confirmation_candle": lv.get("ema_relation_to_confirmation_candle"),
                             "range_clearance": lv.get("ema_range_clearance"), "close_distance": lv.get("ema_close_distance"), "ema_at_reference": lv.get("ema_at_reference"), "relation_to_reference_candle": lv.get("ema_relation_to_reference_candle"),
                             "entry_reference_price": lv.get("entry_reference_price"), "target1_level": lv.get("target1_level"), "ema_between_entry_and_t1": lv.get("ema_between_entry_and_t1"), "ema_below_entry_reference": lv.get("ema_below_entry_reference"),
                             "running_low_before_signal_candle": lv.get("running_low_before_signal_candle"), "signal_close_below_prior_running_low": lv.get("signal_close_below_prior_running_low")})
        for x in allres[w][2]:
            ema_rows.append({"window": w, "date": x["date"], "time": x["signal_time"], "method": x["method"], "status": "REJECTED_BY_28_POINT_RULE", "ema_at_confirmation": x.get("ema200"), "relation_to_confirmation_candle": x.get("relation"),
                             "range_clearance": x.get("range_clearance"), "close_distance": x.get("close_distance")})
    write_csv(R61 / "irf_ema_28_diagnostics.csv", ema_rows)
    st = [r for r in ema_rows if r["status"] == "PASSED_AND_CONFIRMED" and r["window"] == "A"]
    state["ema_diag_A"] = {"confirmed": len(st), "ema_between_entry_and_t1": sum(1 for r in st if r["ema_between_entry_and_t1"] is True), "relation": dict(Counter(r["relation_to_confirmation_candle"] for r in st)),
                           "rejected": sum(1 for r in ema_rows if r["window"] == "A" and r["status"].startswith("REJECTED")), "close_below_prior_running_low": sum(1 for r in st if r["signal_close_below_prior_running_low"] is True)}
    # ------------------------------------------------------------------ independent audit of Method 2A (raw chain from Phase 6.0)
    audit = {}
    mism = []
    for w in ("A", "B"):
        inp = P60.get_window(w, "5P")
        dates = sorted({pd.Timestamp(r["date"]).date() for r in allres[w][0]["v2"]} | set(d for d in inp.chain if inp.start <= d <= inp.end))
        ind = AUD.audit_window(inp.chain, [d for d in dates if inp.start <= d <= inp.end])
        eng = defaultdict(list)
        for r in allres[w][0]["v2"]:
            if r["method"] == "Method 2A" and r["time"] <= CUT:
                eng[pd.Timestamp(r["date"]).date()].append((r["time"], float(r["support"]), r["first_red_candle_start"]))
        n_ind = sum(len(v) for v in ind.values())
        n_eng = sum(len(v) for d, v in eng.items() if inp.start <= d <= inp.end)
        bad = 0
        for d in sorted(set(ind) | set(eng)):
            if not (inp.start <= d <= inp.end):
                continue
            a, b = sorted(ind.get(d, [])), sorted(eng.get(d, []))
            ok = len(a) == len(b) and all(x[0] == y[0] and abs(x[1] - y[1]) < 1e-9 and x[2] == y[2] for x, y in zip(a, b, strict=True))
            if not ok:
                bad += 1
                mism.append({"window": w, "date": str(d), "independent": str(a), "engine": str(b)})
        audit[w] = {"sessions": len([d for d in ind]), "independent_method2a_signals": n_ind, "engine_method2a_signals": n_eng, "sessions_with_mismatch": bad}
    write_csv(R61 / "audit_mismatches.csv", mism, ["window", "date", "independent", "engine"])
    state["independent_audit"] = audit
    print("AUDIT", audit, flush=True)
    # ------------------------------------------------------------------ handwritten IRF cases
    hc = pd.read_csv(ROOT / "reports/phase5/phase53_author_corrected/dated_author_corrections.csv")
    hc = hc[hc.topic.astype(str).str.startswith("IRF") & hc.trading_date.notna()]
    hrows = []
    for r in hc.itertuples():
        d = r.trading_date
        fz = sorted((t, m, kf[(d, t, m)]["support"]) for (dd, t, m) in kf if dd == d and t <= CUT)
        v2s = sorted((t, m, kv[(d, t, m)]["support"]) for (dd, t, m) in kv if dd == d and t <= CUT)
        first_f, first_v = (fz[0] if fz else None), (v2s[0] if v2s else None)
        att = [a for a in attempts if a["date"] == d]
        status = ("OUT_OF_SCOPE_METHOD_2B (the approved rule applies to Method 2A; extension needs owner approval)" if "2B" in str(r.original_strategy) else
                  ("DAY_LOW_PREDICATE_UNRESOLVED (not applied)" if r.topic == "IRF_DAY_LOW" else ("EMA_28_RULE_APPLIED (see diagnostics)" if r.topic == "IRF_EMA_28" else ("ENTRY_BODY_RULE_NOT_IN_THE_CALL" if "BODY" in r.topic else "FIRST_RED_RULE_APPLIED"))))
        hrows.append({"correction_id": r.correction_id, "date": d, "handwritten_page": r.handwritten_pdf_page, "author_comment": r.original_author_comment, "topic": r.topic, "original_strategy": r.original_strategy, "original_signal_time": r.original_signal_timestamp,
                      "frozen_first_irf_signal_to_13_00": f"{first_f[0]} {first_f[1]} support={first_f[2]}" if first_f else "none", "v2_first_irf_signal_to_13_00": f"{first_v[0]} {first_v[1]} support={first_v[2]}" if first_v else "none",
                      "v2_method2_attempts": len(att), "v2_reference_candles": "; ".join(f"{a['reference_candle_start']} {a['reference_ohlc']} support={a['support_wick_low']}" for a in att if a["reference_candle_start"]),
                      "v2_changes_first_entry": (first_f != first_v), "status": status,
                      "reconciled_with_author_evidence": "NO: the handwritten note gives no numeric entry price/level; the engine result is reported, not claimed as the author's"})
    write_csv(R61 / "irf_handwritten_cases.csv", hrows)
    state["handwritten"] = {"cases": len(hrows), "first_entry_changed_by_v2": sum(1 for r in hrows if r["v2_changes_first_entry"]), "out_of_scope_2b": sum(1 for r in hrows if r["status"].startswith("OUT_OF_SCOPE"))}
    # ------------------------------------------------------------------ charts for dates where V2 changed a Method 2A signal and for the handwritten IRF dates
    (R61 / "charts").mkdir(exist_ok=True)
    chart_dates = sorted({r["date"] for r in rows if r["method"] == "Method 2A" and r["change_frozen_to_v2"] != "UNCHANGED"} | {r["date"] for r in hrows})
    n_ch = 0
    for ds in chart_dates:
        d = pd.Timestamp(ds).date()
        if d not in ctxs:
            continue
        ctx = ctxs[d]
        c = ctx.candles.rename(columns={"bar_start": "start", "bar_end": "end", "ema200_5m": "ema"})[["start", "end", "open", "high", "low", "close", "ema"]]
        c = c[c["end"].dt.time <= pd.Timestamp("14:30").time()].reset_index(drop=True)
        levels = [Level("RESISTANCE", "MAJOR", "IRH", float(c["high"].iloc[0]), float(c["high"].iloc[0]), (), "initial range high"), Level("SUPPORT", "MAJOR", "IRL", float(c["low"].iloc[0]), float(c["low"].iloc[0]), (), "initial range low")]
        marks, panel = [], []
        for a in [x for x in attempts if x["date"] == ds and x["reference_candle_start"]]:
            levels.append(Level("SUPPORT", "INNER", "V2_SUPPORT", a["support_wick_low"], a["support_wick_low"], (a["reference_candle_start"],), "first red candle wick low"))
            rt = pd.Timestamp(f"{ds} {a['reference_candle_start']}").tz_localize(c["start"].iloc[0].tz)
            marks.append((rt, a["support_wick_low"], f"V2 reference red candle {a['reference_candle_start']} low {a['support_wick_low']}", "#8e44ad"))
            panel.append(f"V2 attempt: breakout {a['breakout_candle_start']}, extension {a['extension_candle_start']}, reference {a['reference_candle_start']} ({a['reference_ohlc']}), support {a['support_wick_low']}; closes after reference: {a['closes_after_reference']}; first close below: {a['first_close_below_support'] or 'none'}; EMA-28 rejected a break: {a['ema_28_rejected_a_break']}")
        for (dd, t, m), r in kv.items():
            if dd == ds:
                bt = pd.Timestamp(f"{ds} {t}").tz_localize(c["start"].iloc[0].tz) - pd.Timedelta(minutes=5)
                marks.append((bt, r["reference_close"], f"V2 {m} {t} (close {r['reference_close']})", "#c0392b"))
        for (dd, t, m), r in kf.items():
            if dd == ds:
                bt = pd.Timestamp(f"{ds} {t}").tz_localize(c["start"].iloc[0].tz) - pd.Timedelta(minutes=5)
                marks.append((bt, r["reference_close"], f"frozen {m} {t}", "#e67e22"))
        panel += ["Frozen Phase 3.6 IRF signals: " + (", ".join(f"{t} {m}" for (dd, t, m) in sorted(kf) if dd == ds) or "none"), "IRF V2 signals: " + (", ".join(f"{t} {m}" for (dd, t, m) in sorted(kv) if dd == ds) or "none"),
                  "Rules: first red candle wick low = support; strict close below by a LATER completed candle; no retest; 28-pt EMA clearance (provisional measure); day's-low restriction NOT applied."]
        hh = [r for r in hrows if r["date"] == ds]
        if hh:
            panel.insert(0, "HANDWRITTEN NOTE: " + " | ".join(str(h["author_comment"]) for h in hh))
        svg = svg_chart({"title": f"IRF V2 support-break {ds}", "header": ["Purple = IRL/IRH (initial range) and the V2 first-red-candle support; orange = frozen signal; red = V2 signal; blue = EMA(200)."], "candles": c, "open_start": c["start"].iloc[0],
                         "levels": levels, "trade": None, "panel": panel, "extra_markers": marks, "label_inner": True})
        (R61 / "charts" / f"{ds}.svg").write_text(svg)
        n_ch += 1
    state["charts"] = n_ch
    (R61 / "phase61_state.json").write_text(json.dumps(state, indent=1, default=str))
    write_workbook(R61 / "IRF_V2_Verification.xlsx", {"Before_after": rows, "Reference_candle_audit": [{"window": w, **a} for w in ("A", "B") for a in allres[w][1]], "EMA_28": ema_rows, "Handwritten": hrows, "Audit_mismatches": mism},
                   {"purpose": "IRF-V2-SUPPORT-BREAK signal-level verification (primary window 2025-09..2026-08 and 2022-25 robustness); signals only, no P&L", "authority": "OWNER_APPROVED first-red-candle low / strict close / no retest; 28-pt number approved, measure PROVISIONAL; day's-low NOT applied"})
    print(json.dumps(state, indent=1, default=str)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
