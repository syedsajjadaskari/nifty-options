"""Phase 6.5: author-feedback validation. (1) the two newer IRF methods vs the existing IRF; (2) ORB-vs-IRF disputed days with separate executed / counterfactual scenarios; (3) candle body-strength research and variants
A-D through the frozen controller; (4) independent PDR first-eligible-candle audit. Research only: no live or paper configuration is touched; synthetic index P&L."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase60_common as P60  # noqa: E402
import phase62_charts as CH  # noqa: E402
from phase61_common import JOURNAL, R63, ROOT, SCRATCH, window_data, write_csv  # noqa: E402

from nifty_trading.core.exit_policy import evaluate_exit, policy_for  # noqa: E402
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase31 as P31  # noqa: E402
from nifty_trading.research import phase55 as X  # noqa: E402
from nifty_trading.research import phase56 as M  # noqa: E402
from nifty_trading.research import phase62 as X2  # noqa: E402
from nifty_trading.research import phase65 as H  # noqa: E402
from nifty_trading.research.orb_v2 import config as OC  # noqa: E402
from nifty_trading.strategies import orb_v2_adapter as OA  # noqa: E402
from nifty_trading.strategies.definitions import to_candles  # noqa: E402
from nifty_trading.strategies.first_eligible_phase53 import PDRFirstEligibleStrategy  # noqa: E402
from nifty_trading.strategies.strength_gate import VARIANTS, StrengthGateEngine  # noqa: E402
from nifty_trading.strategies.trading_day import _CLASS  # noqa: E402

R65 = ROOT / "reports" / "phase6" / "phase65_author_feedback"
SC = P.combined_scenario("BODY_BASED_PHASE36")
CUT = "13:00"
ORB_CAUSE = {"COLOUR_MISMATCH": "SOURCE_SUPPORTED_RULE (candle colour)", "WRONG_SIDE_WICK": "SOURCE_SUPPORTED_RULE (wrong-side wick <= 20%)", "EMA_EQUAL": "SOURCE_SUPPORTED_RULE (close on EMA)",
             "ZERO_RANGE_CANDLE": "SOURCE_SUPPORTED_RULE", "GAP_TOO_LARGE": "SOURCE_RULE_WITH_UNCONFIRMED_LIMIT (250 or 300)", "LEVEL_NOT_BROKEN": "PROVISIONAL_LEVEL_CONSTRUCTION", "NO_PATTERN": "PROVISIONAL_PATTERN_CONVENTION"}


def hypo(bars, d, direction, strategy, signal_end):
    """Exit path of a candidate with the SAME approved portfolio exit rules as the ledger (frozen exit policy). Fill = open of the first one-minute bar at/after the signal candle's end."""
    bl = bars[d]
    fi = next((i for i, b in enumerate(bl) if b.ts >= signal_end), None)
    if fi is None or not bl[fi].executable or f"{bl[fi].ts:%H:%M}" > CUT:
        return None
    entry = float(bl[fi].o)
    res = evaluate_exit(direction, entry, bl[fi:], policy_for(strategy, trade=SC.trade), entry_at_first_bar_open=True)
    return {"entry_time": bl[fi].ts, "entry_price": entry, "res": res, "outcome": _CLASS.get(res.outcome, str(res.outcome)), "gross_pnl_rs": res.pnl_rupees, "gross_points": res.pnl_points_weighted}


def trade_dict(h, direction):
    r = h["res"]
    cls = h["outcome"]
    l1 = {"INITIAL_FULL_STOP": "STOP", "T1_THEN_BUFFER_STOP": "T1", "TARGET": "T1"}.get(cls, "T1" if r.post_t1_stop_level is not None else "FORCED")
    l2 = {"INITIAL_FULL_STOP": "STOP", "T1_THEN_BUFFER_STOP": "POST-T1 STOP", "TARGET": "T2"}.get(cls, "FORCED 15:14 OPEN")
    return {"direction": direction, "entry_time": h["entry_time"], "entry_price": h["entry_price"], "stop": r.stop_level, "t1": r.t1_level, "t2": r.t2_level, "post_t1_stop": r.post_t1_stop_level if cls in ("T1_THEN_BUFFER_STOP", "TARGET", "FORCED_EXIT") else None,
            "leg1_time": r.leg1_ts if r.leg1_exit is not None else None, "leg1_price": r.leg1_exit, "leg1_reason": l1, "leg2_time": r.leg2_ts if r.leg2_exit is not None else None, "leg2_price": r.leg2_exit, "leg2_reason": l2}


def candles_of(ctx):
    return ctx.candles.rename(columns={"bar_start": "start", "bar_end": "end", "ema200_5m": "ema"})[["start", "end", "open", "high", "low", "close", "ema"]].reset_index(drop=True)


def wr(rows):
    n = len(rows)
    w = sum(1 for r in rows if float(r["gross_pnl_rs"]) > 0)
    pf = X.profit_factor([float(r["gross_pnl_rs"]) for r in rows])
    return {"trades": n, "win_rate_pct": round(100 * w / n, 2) if n else None, "profit_factor": None if pf is None else ("inf" if pf == float("inf") else round(pf, 3)), "gross_rs": round(sum(float(r["gross_pnl_rs"]) for r in rows), 0),
            "net_rs_70": round(sum(float(r["gross_pnl_rs"]) - 70 for r in rows), 0)}


def main() -> int:  # noqa: C901
    R65.mkdir(parents=True, exist_ok=True)
    res62 = pickle.loads((SCRATCH / "results62.pkl").read_bytes())
    state: dict = {}
    wd = {w: window_data(w) for w in ("A", "B")}
    # =============================================================================================== (1) newer IRF methods vs the existing IRF
    rows_new, hyp_rows = [], []
    for w in ("A", "B"):
        ctxs, infos, bars, cal, label = wd[w]
        ex = {k: defaultdict(list) for k in ("A", "C")}
        for k in ("A", "C"):
            for s in res62[w]["signals"][k]:
                if s["strategy"] == "IRF" and s["time"] <= CUT:
                    ex[k][s["date"]].append((s["time"], s["method"]))
        for d in sorted(ctxs):
            ds = str(d)
            cs = to_candles(ctxs[d].candles)
            n1, n2, n2b = H.new_irf_method1(cs), H.new_irf_method2(cs), H.new_irf_method2(cs, breakout_candle_may_be_first_red=True)
            fz = sorted(ex["A"].get(ds, []))
            v2 = sorted(ex["C"].get(ds, []))
            row = {"window": w, "date": ds, "new_m1_time": n1["time"] if n1 and n1["within_cutoff"] else "", "new_m1_level_a": n1["level_a"] if n1 else "", "new_m2_time": n2["time"] if n2 and n2["within_cutoff"] else "",
                   "new_m2_level_a": n2["level_a"] if n2 else "", "new_m2_level_b": n2["level_b"] if n2 else "", "new_m2_first_red": n2["first_red_time"] if n2 else "", "new_m2_second_breakout": n2["second_breakout_time"] if n2 else "",
                   "new_m2_variant_breakout_candle_may_be_first_red": n2b["time"] if n2b and n2b["within_cutoff"] else "", "frozen_irf_first": f"{fz[0][0]} {fz[0][1]}" if fz else "", "frozen_irf_methods_to_13_00": "; ".join(f"{t} {m}" for t, m in fz),
                   "irfv2_first": f"{v2[0][0]} {v2[0][1]}" if v2 else "", "irfv2_signals_to_13_00": len(v2)}
            for nm, key in (("m1", "new_m1_time"), ("m2", "new_m2_time")):
                t = row[key]
                if not t:
                    row[f"{nm}_vs_frozen"] = "NO_NEW_SIGNAL" if True else ""
                elif not fz:
                    row[f"{nm}_vs_frozen"] = "NEW_SIGNAL_NO_EXISTING_IRF_SIGNAL"
                elif t == fz[0][0]:
                    row[f"{nm}_vs_frozen"] = "SAME_TIME_AS_FIRST_EXISTING"
                elif t < fz[0][0]:
                    row[f"{nm}_vs_frozen"] = "EARLIER_THAN_FIRST_EXISTING"
                else:
                    row[f"{nm}_vs_frozen"] = "LATER_THAN_FIRST_EXISTING" + ("" if t not in {x[0] for x in fz} else " (but equals a later existing signal time)")
            rows_new.append(row)
            for lab, sig, dr in (("NEW-M1", n1, "SHORT"), ("NEW-M2", n2, "SHORT")):
                if sig and sig["within_cutoff"]:
                    h = hypo(bars, d, dr, "IRF", ctxs[d].candles["bar_end"].iloc[sig["index"]])
                    if h:
                        hyp_rows.append({"window": w, "date": ds, "method": lab, "signal_time": sig["time"], "outcome": h["outcome"], "gross_pnl_rs": h["gross_pnl_rs"]})
            for lab, lst in (("FROZEN-IRF first signal", fz), ("IRF-V2 first signal", v2)):
                if lst:
                    t = lst[0][0]
                    cc = ctxs[d].candles
                    idx = cc.index[cc["bar_end"].dt.strftime("%H:%M") == t]
                    if len(idx):
                        h = hypo(bars, d, "SHORT", "IRF", cc["bar_end"].loc[idx[0]])
                        if h:
                            hyp_rows.append({"window": w, "date": ds, "method": lab, "signal_time": t, "outcome": h["outcome"], "gross_pnl_rs": h["gross_pnl_rs"]})
    write_csv(R65 / "irf_new_methods_vs_existing.csv", rows_new)
    hs = []
    for w in ("A", "B"):
        for m in ("NEW-M1", "NEW-M2", "FROZEN-IRF first signal", "IRF-V2 first signal"):
            sel = [r for r in hyp_rows if r["window"] == w and r["method"] == m]
            hs.append({"window": w, "method": m, **wr(sel)})
    write_csv(R65 / "irf_new_methods_standalone_diagnostic.csv", hs)
    state["new_irf"] = {"summary": hs, "counts": {w: {k: sum(1 for r in rows_new if r["window"] == w and r[k]) for k in ("new_m1_time", "new_m2_time", "new_m2_variant_breakout_candle_may_be_first_red")} | {"sessions": sum(1 for r in rows_new if r["window"] == w)} for w in ("A", "B")},
                        "relation_m1": dict(Counter(r["m1_vs_frozen"] for r in rows_new if r["window"] == "A")), "relation_m2": dict(Counter(r["m2_vs_frozen"] for r in rows_new if r["window"] == "A"))}
    print("new IRF done", state["new_irf"]["counts"], flush=True)
    # =============================================================================================== (2) ORB vs IRF disputed days
    ctxs, infos, bars, cal, label = wd["A"]
    orb_cmp = pd.read_csv(R63 / "orb_vs_irf_comparison.csv", dtype=str, keep_default_na=False)
    p60 = pd.read_csv(ROOT / "reports/phase6/phase60_orb_from_scratch/all_orb_signals.csv", dtype=str, keep_default_na=False)
    p60tv = pd.read_csv(ROOT / "reports/phase6/phase60_orb_from_scratch/vendor_sensitivity_all_orb_signals.csv", dtype=str, keep_default_na=False)
    led = {k: {(r["date"], r["strategy"], r["signal_time"]): r for r in res62["A"]["ledgers"][k]} for k in ("A", "B", "C")}
    first_tr = {k: {} for k in ("A", "B", "C")}
    for k in first_tr:
        for r in sorted(res62["A"]["ledgers"][k], key=lambda x: (x["date"], x["entry_time"], int(x["trade_no"]))):
            first_tr[k].setdefault(r["date"], r)
    sigs_c = defaultdict(list)
    for s in res62["A"]["signals"]["C"]:
        sigs_c[s["date"]].append(s)
    disp, charts_n = [], 0
    (R65 / "charts_orb_vs_irf").mkdir(exist_ok=True)
    for r in orb_cmp.itertuples():
        if r.classification.startswith("NO ELIGIBLE TRADE (non"):
            continue
        d = r.date
        fa, fb, fc = first_tr["A"].get(d), first_tr["B"].get(d), first_tr["C"].get(d)
        if not (r.irf_executed_A == "True" or r.irf_executed_B == "True" or (fc and fc["strategy"] == "IRF")):
            continue
        dd = pd.Timestamp(d).date()
        o = p60[(p60.config_id == "ORB-V2-A") & (p60.window == "A") & (p60.date == d)].iloc[0]
        otv = p60tv[(p60tv.config_id == "ORB-V2-A") & (p60tv.date == d)]
        otherv = {c: p60[(p60.config_id == c) & (p60.window == "A") & (p60.date == d)].signal.iloc[0] for c in ("ORB-V2-B", "ORB-V2-C", "ORB-V2-D", "DIAG-A-OLDSIDE")}
        failed = [x for x in o.failed.split(";") if x]
        cause = sorted({ORB_CAUSE[x] for x in failed})
        if not o.signal and not failed:
            cause = ["NO_FAILED_CONDITION_RECORDED (investigate)"]
        feed_diff = bool(len(otv) and otv.signal.iloc[0] in ("BUY", "SELL") and not o.signal)
        orb_sig = o.signal in ("BUY", "SELL")
        irf_sigs = sorted((s["time"], s["method"], s) for s in sigs_c.get(d, []) if s["strategy"] == "IRF" and s["time"] <= CUT)
        ctx = ctxs[dd]
        cc = ctx.candles
        # ORB candidate (09:20 fill); direction = the signal's, else the EMA-side direction (hypothetical, clearly labelled)
        dir_orb = ("LONG" if o.signal == "BUY" else "SHORT") if orb_sig else ("LONG" if o.direction_by_ema == "BUY" else ("SHORT" if o.direction_by_ema == "SELL" else None))
        h_orb = hypo(bars, dd, dir_orb, "ORB", cc["bar_end"].iloc[0]) if dir_orb else None
        h_irf = None
        irf_pick = None
        if irf_sigs:
            exec_irf = fc if (fc and fc["strategy"] == "IRF") else None
            irf_pick = next((x for x in irf_sigs if exec_irf and x[0] == exec_irf["signal_time"]), irf_sigs[0])
            idx = cc.index[cc["bar_end"].dt.strftime("%H:%M") == irf_pick[0]]
            h_irf = hypo(bars, dd, "SHORT", "IRF", cc["bar_end"].loc[idx[0]])
        executed = (fc["strategy"] + "@" + fc["entry_time"] + " " + fc["outcome"]) if fc else "no trade"
        orb_exec_c = bool(fc and fc["strategy"] == "ORB")
        irf_exec_c = bool(fc and fc["strategy"] == "IRF")
        if h_irf and irf_exec_c:
            assert abs(h_irf["gross_pnl_rs"] - float(fc["gross_pnl_rs"])) < 1e-6, ("hypothetical IRF path differs from the ledger", d)
        defect = bool(orb_sig and fc and fc["strategy"] != "ORB")
        disp.append({"date": d, "journal_orb_row": r.journal_row, "journal_outcome": r.journal_outcome, "A_first_trade": f"{fa['strategy']}@{fa['entry_time']} {fa['outcome']}" if fa else "none", "B_first_trade": f"{fb['strategy']}@{fb['entry_time']} {fb['outcome']}" if fb else "none",
                     "C_first_trade": executed, "orb_v2_signal": o.signal or "none", "orb_v2_failed_conditions": o.failed, "orb_cause_class": "; ".join(cause) if not orb_sig else "ORB V2 VALID (signal at 09:20)", "orb_data_feed_difference": feed_diff,
                     "orb_v2_other_configs": json.dumps(otherv), "orb_candle": f"O{o.candle_open} H{o.candle_high} L{o.candle_low} C{o.candle_close} {o.colour}", "ema_0920": o.ema_now, "gap_points": o.gap_points, "prev_high": o.prev_high, "prev_low": o.prev_low,
                     "levels_broken": f"{o.levels_broken_n}/{o.levels_total}", "primary_level": o.primary_level, "patterns": o.patterns_matched, "wrong_side_wick_pct": o.wrong_side_wick_pct, "direction_by_ema": o.direction_by_ema,
                     "earliest_valid_orb": "09:20" if orb_sig else "none", "earliest_valid_irf_C": f"{irf_sigs[0][0]} {irf_sigs[0][1]}" if irf_sigs else "none", "orb_first_executable": f"{h_orb['entry_time']:%H:%M} @ {h_orb['entry_price']}" if h_orb and orb_sig else "n/a (no valid ORB)",
                     "irf_first_executable": f"{h_irf['entry_time']:%H:%M} @ {h_irf['entry_price']}" if h_irf else "n/a", "orb_path": ("EXECUTED" if orb_exec_c else ("COUNTERFACTUAL (valid ORB not selected: DEFECT)" if orb_sig else "COUNTERFACTUAL (ORB V2 rejected; direction assumed EMA side)")),
                     "orb_outcome": h_orb["outcome"] if h_orb else "", "orb_gross_rs": h_orb["gross_pnl_rs"] if h_orb else "", "irf_path": "EXECUTED" if irf_exec_c else "COUNTERFACTUAL (not selected)", "irf_outcome": h_irf["outcome"] if h_irf else "", "irf_gross_rs": h_irf["gross_pnl_rs"] if h_irf else "",
                     "author_pattern_orb_target_irf_stop": bool(h_orb and h_irf and not orb_exec_c and irf_exec_c and h_orb["outcome"] == "TARGET" and h_irf["outcome"] == "INITIAL_FULL_STOP"),
                     "valid_orb_depends_on_provisional_convention": bool(orb_sig and (("full_body" not in str(o.patterns_matched)) or o.qualifying_category == "INNER_ONLY" or any(v != o.signal for v in otherv.values()))), "controller_rule": "first valid signal wins; no ORB/IRF priority", "software_defect_valid_orb_not_selected": defect,
                     "classification_phase63": r.classification})
        for lab, h, dr, par in (("ORB", h_orb, dir_orb, ("EXECUTED" if orb_exec_c else "COUNTERFACTUAL")), ("IRF", h_irf, "SHORT", ("EXECUTED" if irf_exec_c else "COUNTERFACTUAL"))):
            if not h:
                continue
            td = trade_dict(h, dr)
            note = ([f"{par} SCENARIO ({lab}) - " + ("this trade was selected by the controller in configuration C" if par == "EXECUTED" else "NOT EXECUTED: hypothetical path under the same approved exit rules; it must not replace the executed decision")] +
                    ([f"ORB V2 {'valid signal 09:20' if orb_sig else 'REJECTED: ' + o.failed + ' | direction assumed from the EMA side (' + str(o.direction_by_ema) + ')'}"] if lab == "ORB" else [f"IRF signals to 13:00 (C): {', '.join(f'{x[0]} {x[1]}' for x in irf_sigs)}"]) +
                    [f"Candidate entry {h['entry_time']:%H:%M} @ {h['entry_price']} -> {h['outcome']} (gross Rs {h['gross_pnl_rs']:+,.0f}, 390 units)", f"Controller C first trade: {executed}", "Journal: ORB row " + str(r.journal_row) + f" outcome {r.journal_outcome}; no direction recorded", "No automatic ORB priority is applied."])
            svg = CH.chart(f"{d} | {lab} candidate | {par}", [f"{'EXECUTED' if par == 'EXECUTED' else 'COUNTERFACTUAL (unexecuted)'} {lab} scenario | classification {r.classification}"], candles_of(ctx), note, trade=td,
                           hlines=[(float(o.prev_high), "prev-day high", "#777"), (float(o.prev_low), "prev-day low", "#777")] + ([(float(candles_of(ctx)['high'].iloc[0]), "IRH", "#555")] if lab == "IRF" else []))
            (R65 / "charts_orb_vs_irf" / f"{d}_{lab}_{par.lower()}.svg").write_text(svg)
            charts_n += 1
    write_csv(R65 / "orb_vs_irf_disputed_days.csv", disp)
    D = pd.DataFrame(disp)
    state["disputes"] = {"dates": len(D), "orb_valid": int((D.orb_v2_signal != "none").sum()), "orb_valid_but_not_selected_defects": int(D.software_defect_valid_orb_not_selected.sum()), "feed_difference": int(D.orb_data_feed_difference.sum()),
                         "author_pattern_orb_target_irf_stop": int(D.author_pattern_orb_target_irf_stop.sum()), "valid_orb_depends_on_provisional_convention": int(D.valid_orb_depends_on_provisional_convention.sum()), "cause_counts": dict(Counter(x for c in D.orb_cause_class for x in c.split("; "))),
                         "irf_executed_C": int((D.irf_path == "EXECUTED").sum()), "irf_outcome_C_executed": dict(Counter(D[D.irf_path == "EXECUTED"].irf_outcome)), "orb_cf_outcomes": dict(Counter(D[D.orb_path.str.startswith("COUNTERFACTUAL")].orb_outcome)), "charts": charts_n}
    print("disputes", state["disputes"], flush=True)
    # =============================================================================================== (3) candle strength
    jrows, _ = M.load_journal(JOURNAL)
    sig_rows = []
    cand = {str(d): ctxs[d].candles.set_index(ctxs[d].candles["bar_start"].dt.strftime("%H:%M")) for d in ctxs}
    for k in ("A", "B", "C"):
        for s in res62["A"]["signals"][k]:
            c = cand[s["date"]].loc[s["candle_start"]]
            m = H.candle_metrics(float(c["open"]), float(c["high"]), float(c["low"]), float(c["close"]))
            lv = res62["A"]["levels"][k].get((s["date"], s["time"], s["strategy"], s["method"], s["direction"]), ({}, [], []))[0]
            ex = lv.get("patterns_matched") or "+".join(lv.get("patterns_passed") or []) or ""
            sig_rows.append({"config": k, "date": s["date"], "time": s["time"], "strategy": s["strategy"], "method": s["method"], "direction": s["direction"], "candle_open": float(c["open"]), "candle_high": float(c["high"]), "candle_low": float(c["low"]), "candle_close": float(c["close"]),
                             "colour": m["colour"], "zero_range": m["zero_range"], "body_pct": m["body_pct"], "upper_wick_pct": m["upper_wick_pct"], "lower_wick_pct": m["lower_wick_pct"], "close_location_pct": m["close_location_pct"], "existing_pattern": ex or "(method-defined)",
                             "geometric_pattern_diagnostic": H.geometric_pattern(m, "LONG" if s["direction"] == "LONG" else "SHORT"), "controller_event": s["controller_event"][:60], "trade_id": s["trade_id"]})
    write_csv(R65 / "candle_strength_signals.csv", sig_rows)
    SD = pd.DataFrame(sig_rows)
    SD = SD[SD.config == "C"]
    dist = []
    for (s, mth), g in SD.groupby(["strategy", "method"]):
        b = pd.to_numeric(g.body_pct, errors="coerce").dropna()
        dist.append({"strategy": s, "method": mth, "signals": len(g), "zero_range": int(g.zero_range.sum()), "mean_body_pct": round(b.mean(), 1) if len(b) else None, "median_body_pct": round(b.median(), 1) if len(b) else None,
                     "share_below_60_pct": round(100 * (b < 60).mean(), 1) if len(b) else None, "share_below_70_pct": round(100 * (b < 70).mean(), 1) if len(b) else None, "colour_matches_direction_pct": round(100 * ((g.colour == "GREEN") == (g.direction == "LONG")).mean(), 1)})
    write_csv(R65 / "candle_strength_distribution_by_method.csv", dist)
    exe = SD[SD.trade_id != ""].merge(pd.DataFrame(res62["A"]["ledgers"]["C"])[["trade_id", "gross_pnl_rs"]], on="trade_id")
    exe["bucket"] = pd.cut(pd.to_numeric(exe.body_pct, errors="coerce"), [-0.1, 60, 70, 100.1], labels=["<60%", "60-70%", ">=70%"])
    bk = [{"strategy": s, "bucket": str(b), **wr([{"gross_pnl_rs": x} for x in g.gross_pnl_rs])} for (s, b), g in exe.groupby(["strategy", "bucket"], observed=True)]
    write_csv(R65 / "candle_strength_winrate_by_body_bucket_DIAGNOSTIC.csv", bk)
    auth = [
        {"strategy": "IRF", "method": "Method 1 (frozen) / new Method 1 rulebook", "confirming_candle": "close back inside / below IRH", "body_strength_in_source": "none", "later_candle_required": "yes: the candle after the breakout (frozen) or any later candle (new rulebook)", "threshold_status": "DIAGNOSTIC_ONLY", "note": "no body rule in either IRF guide or the new rulebooks"},
        {"strategy": "IRF", "method": "Method 2A (first red candle support break)", "confirming_candle": "a later candle closes below the first red candle's wick low", "body_strength_in_source": "none", "later_candle_required": "yes (after the reference red candle)", "threshold_status": "DIAGNOSTIC_ONLY", "note": "colour/size of the breaking candle is not specified"},
        {"strategy": "IRF", "method": "Method 2B (resistance break)", "confirming_candle": "a red candle closes back below resistance", "body_strength_in_source": "colour only (red)", "later_candle_required": "yes", "threshold_status": "DIAGNOSTIC_ONLY", "note": "'red candle' has no size requirement"},
        {"strategy": "IRF", "method": "Method 3 (sweep)", "confirming_candle": "red sweep candle closing below support", "body_strength_in_source": "NO body rule; the 60-70% is the share of the UPPER WICK outside IRH", "later_candle_required": "no (the sweep candle itself confirms)", "threshold_status": "NOT_A_BODY_RULE (exempt)", "note": "must not be read as a 60-70% body requirement"},
        {"strategy": "IRF (new rulebooks)", "method": "New Method 1 / New Method 2", "confirming_candle": "failure candle closing back below the level", "body_strength_in_source": "none", "later_candle_required": "yes", "threshold_status": "DIAGNOSTIC_ONLY", "note": "both rulebooks specify closes only"},
        {"strategy": "ORB V2", "method": "09:20 decision", "confirming_candle": "the 09:15 candle", "body_strength_in_source": "full-body route = total wick <= 20% (=> body >= 80%); other routes: pin bar / engulfing", "later_candle_required": "no", "threshold_status": "SOURCE_SUPPORTED for the full-body route (already stricter than 60/70)", "note": "a 60/70% gate cannot remove a full-body ORB signal; pin-bar / engulfing routes are exempt"},
        {"strategy": "PDR", "method": "confirmation after the zone retest", "confirming_candle": "a green candle (or lower-price rejection) closing strictly above the ceiling", "body_strength_in_source": "colour only; the guide and the author say no fixed percentage or wick size is required", "later_candle_required": "yes (after the retest)", "threshold_status": "AUTHOR_PROPOSED (60/70%) - not in the source", "note": "hammer / rejection route exempt; the owner asked for the FIRST eligible candle"},
        {"strategy": "PDS", "method": "Method 1 good red candle", "confirming_candle": "a red candle at the zone with a good body", "body_strength_in_source": "'good body' is required but NOT numerically defined", "later_candle_required": "the first red candle at the zone", "threshold_status": "SOURCE_SUPPORTED_REQUIREMENT, threshold undefined (60% is a candidate)", "note": "weak first red candle -> Method 3"},
        {"strategy": "PDS", "method": "Method 2 pin bar / Method 3 small-support break", "confirming_candle": "red pin bar with higher price rejection / break of a small support", "body_strength_in_source": "none (pin-bar ratio unspecified)", "later_candle_required": "Method 3: yes", "threshold_status": "NOT_A_BODY_RULE (exempt)", "note": "a small body is normal for a pin bar"},
        {"strategy": "RF", "method": "RF confirmation", "confirming_candle": "see RF guide", "body_strength_in_source": "not specified (the guide only says to measure the whole candle including wicks)", "later_candle_required": "n/a", "threshold_status": "DIAGNOSTIC_ONLY", "note": "no strength statement found in the RF guide"}]
    write_csv(R65 / "candle_strength_authority_matrix.csv", auth)
    # ------------------------------------------------------------------ variants A-D through the frozen controller (both windows)
    var_rows, rem_rows, jr_rows = [], [], []
    ledgers_v = {}
    for w in ("A", "B"):
        ctxs_w, _, bars_w, _, _ = wd[w]
        inp = P60.get_window(w, "5P")
        orb = OA.ORBV2Strategy(OA.build_decisions(inp, OC.A), OC.A, proposals=SC.proposals, trade=SC.trade)
        for v in VARIANTS:
            engines = [StrengthGateEngine(e, v) for e in X2.engines_for("C", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision, orb)]
            saved = (P31.make_engines, P.make_engines)
            P31.make_engines = lambda p, t, pe="LEGACY", pr=None, _e=engines: _e
            try:
                tls = P31.run_timelines(SC, ctxs_w, bars_w)
            finally:
                P31.make_engines, P.make_engines = saved
            led = X.ledger_rows(f"S-{v}", tls)
            ledgers_v[(w, v)] = led
            for strat in ("ALL",) + P.STRATEGIES:
                sel = led if strat == "ALL" else [r for r in led if r["strategy"] == strat]
                var_rows.append({"window": w, "variant": v, "strategy": strat, **wr(sel), "max_drawdown_rs": round(X.max_drawdown([float(r["gross_pnl_rs"]) for r in X.trade_order(sel)]), 0) if sel else 0})
            logs = [x for e in engines for x in e.log]
            cnt = Counter((x["strategy"], x["method"], x["gate_applies"], x["kept"]) for x in logs)
            for (s, m_, ap, kept), n in sorted(cnt.items()):
                rem_rows.append({"window": w, "variant": v, "strategy": s, "method": m_, "gate_applies": ap, "kept": kept, "signals": n})
            if w == "A":
                for t in led:
                    t["signal_candle_start"] = f"{(int(t['signal_time'][:2]) * 60 + int(t['signal_time'][3:]) - 5) // 60:02d}:{(int(t['signal_time'][:2]) * 60 + int(t['signal_time'][3:]) - 5) % 60:02d}"
                mm = M.match(jrows, led)
                jr_rows.append({"variant": v, "trades": len(led), "strict": len(mm["strict"]), "time_tolerant": len(mm["tolerant"]), "date_strategy_only": len(mm["date_strategy_only"]), "manual_only": len(mm["manual_unmatched"]), "automated_only": len(mm["trades_unmatched"]),
                                **{f"strict_{s}": sum(1 for p in mm["strict"] if p.manual.strategy == s) for s in P.STRATEGIES}, **{f"tolerant_{s}": sum(1 for p in mm["tolerant"] if p.manual.strategy == s) for s in P.STRATEGIES},
                                "outcome_label_agree_strict_tolerant": sum(1 for p in mm["strict"] + mm["tolerant"] if M.outcome_agrees(p.manual.outcome, p.trade["outcome"]))})
            print("variant", w, v, len(led), flush=True)
    diff_rows, led_rows = [], []
    for w in ("A", "B"):
        b0 = {r["trade_id"]: r for r in ledgers_v[(w, "A")]}
        for v in ("A", "B", "C", "D"):
            cur = {r["trade_id"]: r for r in ledgers_v[(w, v)]}
            led_rows += [{"window": w, "variant": v, **{k: r[k] for k in ("trade_id", "date", "strategy", "method", "direction", "signal_time", "entry_time", "entry_price", "outcome", "gross_pnl_rs")}} for r in X.trade_order(list(cur.values()))]
            if v == "A":
                continue
            rem_ = sorted(set(b0) - set(cur))
            add_ = sorted(set(cur) - set(b0))
            same_ = [t for t in set(b0) & set(cur) if abs(float(b0[t]["gross_pnl_rs"]) - float(cur[t]["gross_pnl_rs"])) < 1e-6]
            diff_rows.append({"window": w, "variant": v, "baseline_trades": len(b0), "variant_trades": len(cur), "baseline_trades_kept_identical": len(same_), "baseline_trades_removed": len(rem_), "new_trades_added_by_resequencing": len(add_),
                              "removed_by_strategy": json.dumps(dict(Counter(b0[t]["strategy"] for t in rem_))), "added_by_strategy": json.dumps(dict(Counter(cur[t]["strategy"] for t in add_))),
                              "gross_rs_of_removed_baseline_trades": round(sum(float(b0[t]["gross_pnl_rs"]) for t in rem_), 0), "gross_rs_of_added_trades": round(sum(float(cur[t]["gross_pnl_rs"]) for t in add_), 0),
                              "net_gross_change_rs": round(sum(float(r["gross_pnl_rs"]) for r in cur.values()) - sum(float(r["gross_pnl_rs"]) for r in b0.values()), 0)})
    write_csv(R65 / "candle_strength_variant_ledgers.csv", led_rows)
    write_csv(R65 / "candle_strength_variants_trade_set_changes.csv", diff_rows)
    state["strength_trade_set_changes"] = diff_rows
    base = {r["trade_id"]: r for r in res62["A"]["ledgers"]["C"]}
    same = sorted(base) == sorted(r["trade_id"] for r in ledgers_v[("A", "A")]) and abs(sum(float(r["gross_pnl_rs"]) for r in ledgers_v[("A", "A")]) - sum(float(r["gross_pnl_rs"]) for r in base.values())) < 1e-6
    write_csv(R65 / "candle_strength_variants_performance.csv", var_rows)
    write_csv(R65 / "candle_strength_signals_gated.csv", rem_rows)
    write_csv(R65 / "candle_strength_variants_journal.csv", jr_rows)
    state["strength"] = {"variant_A_equals_config_C": same, "distribution": dist, "variants": [r for r in var_rows if r["strategy"] == "ALL"], "journal": jr_rows}
    print("strength done; variant A == C:", same, flush=True)
    # =============================================================================================== (4) PDR first-eligible audit
    audit_rows = []
    for w in ("A", "B"):
        ctxs_w, _, _, _, _ = wd[w]
        inp = P60.get_window(w, "5P")
        orb = OA.ORBV2Strategy({}, OC.A, proposals=SC.proposals, trade=SC.trade)
        pdr = next(e for e in X2.engines_for("C", SC.proposals, SC.trade, SC.pdr_engine, SC.pdr_revision, orb) if isinstance(e, PDRFirstEligibleStrategy))
        for d in sorted(ctxs_w):
            recs = [r for r in pdr.evaluate_session(ctxs_w[d]) if r.strategy == "PDR" and r.reference_levels.get("interaction_candle_start")]
            if not recs:
                continue
            cs = to_candles(ctxs_w[d].candles)
            starts = sorted(r.reference_levels["interaction_candle_start"] for r in recs)
            for r in recs:
                lv = r.reference_levels
                rs = lv["interaction_candle_start"]
                nxt = next((x for x in starts if x > rs), None)
                a = H.pdr_cycle_audit(cs, lv["zone_floor"], lv["zone_ceiling"], rs, f"{r.signal_candle_start:%H:%M}" if r.signal_status == "CONFIRMED" else None, nxt)
                a.update({"window": w, "date": str(d), "status": r.signal_status, "zone_floor": lv["zone_floor"], "zone_ceiling": lv["zone_ceiling"], "engine_signal_time": f"{r.signal_timestamp:%H:%M}" if r.signal_status == "CONFIRMED" else ""})
                if a.get("first_fully_eligible") and a.get("engine_selected") and a["first_fully_eligible"] == a["engine_selected"] and a.get("first_green_after_retest") and a["first_green_after_retest"] < a["engine_selected"]:
                    a["entry_delay_minutes_vs_first_green_after_retest"] = int((pd.Timestamp(f"2000-01-01 {a['engine_selected']}") - pd.Timestamp(f"2000-01-01 {a['first_green_after_retest']}")).total_seconds() // 60)
                audit_rows.append(a)
    write_csv(R65 / "pdr_setup_audit.csv", audit_rows)
    A_ = pd.DataFrame(audit_rows)
    A_["cls"] = A_.classification.str.split(" \\(").str[0]
    state["pdr"] = {w: {"cycles": int((A_.window == w).sum()), **dict(Counter(A_[A_.window == w].cls)), "earlier_green_failed_strict_close": int(A_[(A_.window == w)].classification.str.contains("earlier green").sum()),
                        "retest_candle_would_qualify": int(A_[(A_.window == w) & (A_.status == "CONFIRMED")].retest_candle_would_qualify.fillna(False).astype(bool).sum()),
                        "with_next_eligible_candle": int(A_[(A_.window == w)].next_eligible_after_engine.notna().sum())} for w in ("A", "B")}
    print("pdr", state["pdr"], flush=True)
    (R65 / "phase65_state.json").write_text(json.dumps(state, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
