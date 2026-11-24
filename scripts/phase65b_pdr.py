"""Phase 6.5 continuation, stage 2: the 215 delayed PDR cycles (categories A-G), the PDR first-eligible audit, PDR-B/C/D and PDS second-confirmation signal comparisons and all PDR / PDS / changed-trade / replacement charts.
Reads the stage-1 pickle; read-only on every earlier report."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase62_charts as CH  # noqa: E402
from phase61_common import SCRATCH, window_data, write_csv  # noqa: E402

from nifty_trading.research import phase65 as H  # noqa: E402
from nifty_trading.strategies.definitions import to_candles  # noqa: E402

R65 = Path(__file__).resolve().parents[1] / "reports" / "phase6" / "phase65_author_feedback"
COL = {"retest": "#777777", "first_green": "#27ae60", "first_green_above": "#145a32", "engine": "#c0392b", "PDR_B1": "#2f80ed", "PDR_B2": "#8e44ad", "PDR_C": "#e67e22", "PDR_D": "#6d4c41"}


def cand_df(ctx):
    return ctx.candles.rename(columns={"bar_start": "start", "bar_end": "end", "ema200_5m": "ema"})[["start", "end", "open", "high", "low", "close", "ema"]].reset_index(drop=True)


def body_pct(c):
    return H.candle_metrics(c.o, c.h, c.l, c.c)


def main() -> int:  # noqa: C901
    runs = pickle.loads((SCRATCH / "runs65b.pkl").read_bytes())
    wd = {w: window_data(w) for w in ("A", "B")}
    cyc_rows, delayed = [], []
    (R65 / "charts_pdr").mkdir(exist_ok=True)
    (R65 / "charts_pds").mkdir(exist_ok=True)
    var_rows = {m: [] for m in ("PDR_B1", "PDR_B2", "PDR_C", "PDR_D")}
    n_ch = 0
    for w in ("A", "B"):
        ctxs = wd[w][0]
        base = [r for r in runs[w]["BASE"]["pdr_pds"] if r["strategy"] == "PDR"]
        by_date = defaultdict(list)
        for r in base:
            by_date[r["date"]].append(r)
        var = {m: defaultdict(dict) for m in var_rows}                   # variant -> date -> retest -> signal row
        for m in var_rows:
            for r in runs[w][m]["pdr_pds"]:
                if r["strategy"] == "PDR":
                    var[m][r["date"]][r["interaction_start"]] = r
        for d, rs in sorted(by_date.items()):
            ctx = ctxs[pd.Timestamp(d).date()]
            cs = to_candles(ctx.candles)
            idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
            starts = sorted(r["interaction_start"] for r in rs)
            for r in rs:
                rs0, sel = r["interaction_start"], r["candle_start"]
                nxt = next((x for x in starts if x > rs0), None)
                a = H.pdr_cycle_audit(cs, r["zone_floor"], r["zone_ceiling"], rs0, sel, nxt)
                j, s = idx[rs0], idx[sel]
                ceil_, floor_ = r["zone_ceiling"], r["zone_floor"]
                gaps = any(cs[k].start != cs[k - 1].end for k in range(j + 1, s + 1))
                skipped = []
                for k in range(j + 1, s):
                    c = cs[k]
                    m = body_pct(c)
                    why = ("green, close %.2f <= ceiling %.2f (strict close-above rule)" % (c.c, ceil_)) if (c.c > c.o and c.c <= ceil_) else ("red / not eligible" if c.c <= c.o else "green above ceiling (should have qualified)")
                    skipped.append(f"{c.start:%H:%M} {why} body {m['body_pct']:.0f}%" if m["body_pct"] is not None else f"{c.start:%H:%M} zero-range")
                rc = cs[j]
                retest_green_above = rc.c > rc.o and rc.c > ceil_
                fg = a.get("first_green_after_retest")
                is_delayed = fg is not None and fg < sel
                defect = a["classification"].startswith("DEFECT")
                if not is_delayed:                                                   # the category describes DELAYED cycles only
                    cat = ""
                elif gaps:
                    cat = "F_DATA_OR_TIMING_DISCREPANCY"
                elif [f for f in str(r.get("zone_flags") or "").split(";") if f and f != "CEILING_BELOW_WICK_HIGH"]:           # CEILING_BELOW_WICK_HIGH is informational (the body-based zone ignores the highest wick by design, PDR-B01a)
                    cat = "G_INSUFFICIENT_EVIDENCE (zone flags: " + str(r["zone_flags"]) + ")"
                elif defect:
                    cat = "D_ELIGIBLE_EARLIER_CANDLE_REJECTED_BY_DEFECT"
                elif retest_green_above:
                    cat = "C_EARLIER_GREEN_IS_THE_RETEST_CANDLE"
                elif is_delayed:
                    gc = cs[idx[fg]]
                    cat = "A_EARLIER_GREEN_CLOSES_BELOW_OR_WITHIN_THE_ZONE" if gc.c <= ceil_ else "B_EARLIER_GREEN_ABOVE_CEILING_FAILS_QUALITY (should not occur)"
                else:
                    cat = ""
                ent = {m: (var[m].get(d, {}).get(rs0) or {}) for m in var_rows}
                row = {"window": w, "date": d, "retest_candle": rs0, "zone_floor": floor_, "zone_ceiling": ceil_, "session_open": float(ctx.open_price), "opening_qualification": "09:15 (open strictly above the zone ceiling)", "first_zone_entry": rs0, "retest_complete": True,
                       "first_green_after_retest": fg or "", "first_green_closes_above_ceiling": (cs[idx[fg]].c > ceil_) if fg else "", "first_fully_eligible": a.get("first_fully_eligible") or "", "retest_candle_green_and_above_ceiling": retest_green_above,
                       "engine_first_accepted": sel, "engine_signal_tradable_before_13_00_cutoff": (int(sel[:2]) * 60 + int(sel[3:]) + 5) <= 13 * 60, "retest_before_13_00": (int(rs0[:2]) * 60 + int(rs0[3:])) < 13 * 60, "baseline_confirmation_route": r["patterns"], "candles_skipped": s - j - 1, "skipped_candle_reasons": " | ".join(skipped), "audit_classification": a["classification"], "delayed_earlier_green": is_delayed, "delay_category": cat,
                       "next_eligible_after_engine": a.get("next_eligible_after_engine") or "", **{f"{m}_signal": (ent[m].get("candle_start") or "") for m in var_rows}}
                cyc_rows.append(row)
                if is_delayed:
                    delayed.append(row)
                for m in var_rows:
                    v = ent[m]
                    if v:
                        vi = idx[v["candle_start"]]
                        mt = body_pct(cs[vi])
                        rel = "SAME" if v["candle_start"] == sel else ("EARLIER" if v["candle_start"] < sel else "LATER")
                        cause = []
                        if v.get("green_is_retest"):
                            cause.append("retest candle itself confirms")
                        if m in ("PDR_B1", "PDR_B2") and cs[vi].c <= ceil_:
                            cause.append("green close at/below the zone ceiling accepted (bypasses the close-above-ceiling rule)")
                        if m in ("PDR_B1", "PDR_B2", "PDR_C") and "GOOD_GREEN_BODY" not in r["patterns"].split("+"):
                            cause.append("the baseline entry used the lower-price-rejection route (non-green) which this green-only variant drops")
                        if m == "PDR_D":
                            cause.append("second independently eligible candle (first eligible " + str(v.get("first_eligible_start")) + ")")
                        var_rows[m].append({"window": w, "date": d, "retest_candle": rs0, "variant_signal_candle": v["candle_start"], "baseline_signal_candle": sel, "relation_to_baseline": rel, "variant_entry_reference_close": v["ref_close"],
                                            "baseline_entry_reference_close": next((x["ref_close"] for x in rs if x["candle_start"] == sel), ""), "baseline_confirmation_route": r["patterns"], "variant_signal_tradable_before_13_00_cutoff": (int(v["candle_start"][:2]) * 60 + int(v["candle_start"][3:]) + 5) <= 13 * 60, "body_pct": mt["body_pct"], "upper_wick_pct": mt["upper_wick_pct"], "lower_wick_pct": mt["lower_wick_pct"],
                                            "green_is_retest_candle": v.get("green_is_retest"), "close_above_ceiling": cs[vi].c > ceil_, "reason": "; ".join(cause) or "same rule outcome", "approval_status": "AUTHOR_CONFIRMATION_REQUIRED" if m != "PDR_D" else "MECHANICAL_RESEARCH_CONVENTION"})
                    else:
                        var_rows[m].append({"window": w, "date": d, "retest_candle": rs0, "variant_signal_candle": "", "baseline_signal_candle": sel, "relation_to_baseline": "REMOVED_BY_VARIANT", "baseline_confirmation_route": r["patterns"], "reason": "the variant produced no signal for this cycle" + ("; the baseline entry used the lower-price-rejection route (non-green) which this green-only variant drops" if m in ("PDR_B1", "PDR_B2", "PDR_C") and "GOOD_GREEN_BODY" not in r["patterns"].split("+") else ""), "approval_status": ""})
        # variant cycles with no baseline signal at the same retest
        for m in var_rows:
            for d, rd in var[m].items():
                base_retests = {r["interaction_start"] for r in by_date.get(d, [])}
                ctx = ctxs[pd.Timestamp(d).date()]
                cs = to_candles(ctx.candles)
                idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
                for rs0, v in rd.items():
                    if rs0 not in base_retests:
                        mt = body_pct(cs[idx[v["candle_start"]]])
                        var_rows[m].append({"window": w, "date": d, "retest_candle": rs0, "variant_signal_candle": v["candle_start"], "baseline_signal_candle": "", "relation_to_baseline": "NEW_SIGNAL (baseline had no confirmed signal for this cycle)", "variant_entry_reference_close": v["ref_close"],
                                            "body_pct": mt["body_pct"], "upper_wick_pct": mt["upper_wick_pct"], "lower_wick_pct": mt["lower_wick_pct"], "green_is_retest_candle": v.get("green_is_retest"), "close_above_ceiling": cs[idx[v["candle_start"]]].c > v["zone_ceiling"],
                                            "reason": "baseline cycle never confirmed (or no baseline cycle)", "approval_status": "AUTHOR_CONFIRMATION_REQUIRED" if m != "PDR_D" else "MECHANICAL_RESEARCH_CONVENTION"})
        # ---------------------------------------------------------------- charts for delayed cycles of this window
        for row in [x for x in delayed if x["window"] == w]:
            d = row["date"]
            ctx = ctxs[pd.Timestamp(d).date()]
            tz = ctx.candles["bar_start"].iloc[0].tz
            ts = lambda hm, d=d, tz=tz: pd.Timestamp(f"{d} {hm}").tz_localize(tz)  # noqa: E731
            cs = to_candles(ctx.candles)
            idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
            mk = [(ts(row["retest_candle"]), cs[idx[row["retest_candle"]]].c, f"RETEST candle {row['retest_candle']}", COL["retest"])]
            if row["first_green_after_retest"]:
                c = cs[idx[row["first_green_after_retest"]]]
                mk.append((ts(row["first_green_after_retest"]), c.c, f"FIRST GREEN after retest {row['first_green_after_retest']} (close {c.c}, body {body_pct(c)['body_pct']:.0f}%)", COL["first_green"]))
            mk.append((ts(row["engine_first_accepted"]), cs[idx[row["engine_first_accepted"]]].c, f"ENGINE entry (PDR-A) {row['engine_first_accepted']}", COL["engine"]))
            for m in var_rows:
                if row[f"{m}_signal"]:
                    mk.append((ts(row[f"{m}_signal"]), cs[idx[row[f"{m}_signal"]]].c, f"{m.replace('_', '-')} entry {row[f'{m}_signal']}", COL[m]))
            panel = [f"Category: {row['delay_category']}", f"Zone [{row['zone_floor']}, {row['zone_ceiling']}]; session open {row['session_open']}", f"Retest {row['retest_candle']} (green & above ceiling: {row['retest_candle_green_and_above_ceiling']}); first green after retest {row['first_green_after_retest']} (closes above ceiling: {row['first_green_closes_above_ceiling']})",
                     f"Engine first accepted {row['engine_first_accepted']} after skipping {row['candles_skipped']} candle(s)", "Skipped candles: " + (row["skipped_candle_reasons"] or "none"),
                     "Variants: " + ", ".join(f"{m.replace('_', '-')} {row[f'{m}_signal'] or 'no signal'}" for m in var_rows), "PDR-B1/B2/C are AUTHOR_CONFIRMATION_REQUIRED; PDR-D is a mechanical research convention. No variant is selected."]
            svg = CH.chart(f"PDR delayed cycle {d} ({w})", [f"{d} | zone {row['zone_floor']}-{row['zone_ceiling']} | category {row['delay_category'].split('_')[0]}", "Shaded = previous-day resistance zone; markers = candidate confirmations (counterfactual variants are research only)."], cand_df(ctx), panel, shade=[(row["zone_floor"], row["zone_ceiling"], "PDR zone", "#c0392b")], markers=mk)
            (R65 / "charts_pdr" / f"{w}_{d}_{row['retest_candle'].replace(':', '')}.svg").write_text(svg)
            n_ch += 1
    write_csv(R65 / "pdr_first_eligible_audit.csv", cyc_rows)
    write_csv(R65 / "pdr_215_delayed_cycles.csv", delayed)
    write_csv(R65 / "pdr_variant_B_signals.csv", var_rows["PDR_B1"] + var_rows["PDR_B2"])
    write_csv(R65 / "pdr_variant_C_signals.csv", var_rows["PDR_C"])
    write_csv(R65 / "pdr_variant_D_signals.csv", var_rows["PDR_D"])
    # ---------------------------------------------------------------- PDS first vs second
    pds_rows, pds_ch = [], 0
    for w in ("A", "B"):
        ctxs = wd[w][0]
        base = {(r["date"], r["method"], r["interaction_start"]): r for r in runs[w]["BASE"]["pdr_pds"] if r["strategy"] == "PDS"}
        sec = [r for r in runs[w]["PDS_SECOND"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] in ("Method 1", "Method 2")]     # Method 3 signals are not second confirmations
        bd = defaultdict(list)
        for r in runs[w]["BASE"]["pdr_pds"]:
            if r["strategy"] == "PDS":
                bd[r["date"]].append(r)
        seen = set()
        for r in sec:
            ctx = ctxs[pd.Timestamp(r["date"]).date()]
            cs = to_candles(ctx.candles)
            idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
            c2 = cs[idx[r["candle_start"]]]
            m2 = body_pct(c2)
            first = r["first_eligible_start"] or ""
            c1 = cs[idx[first]] if first in idx else None
            m1 = body_pct(c1) if c1 else None
            row = {"window": w, "date": r["date"], "pds_method": r["method"], "baseline_signal_candle": next((x["candle_start"] for x in bd[r["date"]] if x["method"] == r["method"]), ""), "first_eligible_confirmation": first, "second_eligible_confirmation": r["second_eligible_start"] or r["candle_start"],
                   "zone_low": r["zone_floor"], "zone_high": r["zone_ceiling"], "first_body_pct": m1["body_pct"] if m1 else "", "second_body_pct": m2["body_pct"], "second_upper_wick_pct": m2["upper_wick_pct"], "second_lower_wick_pct": m2["lower_wick_pct"],
                   "second_close_location_pct": m2["close_location_pct"], "time_difference_minutes": (int(r["time"][:2]) * 60 + int(r["time"][3:])) - (int(first[:2]) * 60 + int(first[3:]) + 5) if first else "", "entry_reference_difference_points": (r["ref_close"] - c1.c) if c1 else "",
                   "mandatory_support_break_bypassed": False, "approval_status": "MECHANICAL_RESEARCH_CONVENTION / AUTHOR_CONFIRMATION_REQUIRED", "executed_in_portfolio": r["executed"]}
            pds_rows.append(row)
            seen.add((w, r["date"], r["method"]))
        for r in base.values():
            if r["method"] in ("Method 1", "Method 2") and (w, r["date"], r["method"]) not in seen:
                pds_rows.append({"window": w, "date": r["date"], "pds_method": r["method"], "baseline_signal_candle": r["candle_start"], "second_eligible_confirmation": "", "approval_status": "NO SECOND CONFIRMATION in the variant (first eligible candle had no independently eligible follower before the zone was lost or the session ended)"})
        for m3 in ("Method 3",):
            nb = sum(1 for r in runs[w]["BASE"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] == m3)
            ns = sum(1 for r in runs[w]["PDS_SECOND"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] == m3)
            kb = {(r["date"], r["candle_start"]) for r in runs[w]["BASE"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] == m3}
            ks = {(r["date"], r["candle_start"]) for r in runs[w]["PDS_SECOND"]["pdr_pds"] if r["strategy"] == "PDS" and r["method"] == m3}
            pds_rows.append({"window": w, "pds_method": m3, "date": "ALL", "baseline_signal_candle": f"{nb} signals", "second_eligible_confirmation": "(not applicable to Method 3)", "approval_status": f"Method 3 trigger rule unchanged (the mandatory small-support break is never bypassed). Signals: baseline {nb}, variant {ns}; {len(kb - ks)} baseline-only and {len(ks - kb)} variant-only: a baseline-only Method 3 signal is one whose day / cycle was consumed by the second-confirmation path (a displacement, not a bypass)"})
        for row in [x for x in pds_rows if x["window"] == w and x.get("second_eligible_confirmation") and x["date"] != "ALL" and x.get("first_eligible_confirmation") is not None and x.get("zone_low") is not None]:
            d = row["date"]
            ctx = ctxs[pd.Timestamp(d).date()]
            tz = ctx.candles["bar_start"].iloc[0].tz
            cs = to_candles(ctx.candles)
            idx = {f"{c.start:%H:%M}": k for k, c in enumerate(cs)}
            mk = []
            if row["first_eligible_confirmation"] in idx:
                mk.append((pd.Timestamp(f"{d} {row['first_eligible_confirmation']}").tz_localize(tz), cs[idx[row["first_eligible_confirmation"]]].c, f"FIRST eligible bearish {row['first_eligible_confirmation']} (baseline entry)", "#e67e22"))
            hm = row["second_eligible_confirmation"]
            if hm in idx:
                mk.append((pd.Timestamp(f"{d} {hm}").tz_localize(tz), cs[idx[hm]].c, f"SECOND eligible {hm} (variant entry)", "#c0392b"))
            svg = CH.chart(f"PDS {row['pds_method']} first vs second {d} ({w})", [f"{d} | PDS {row['pds_method']} | time difference {row['time_difference_minutes']} min | approval: author confirmation required"], cand_df(ctx),
                           [f"Zone [{row['zone_low']}, {row['zone_high']}]", f"First eligible {row['first_eligible_confirmation']} body {row['first_body_pct']}%; second {hm} body {row['second_body_pct']}%, upper wick {row['second_upper_wick_pct']}%, lower wick {row['second_lower_wick_pct']}%",
                            f"Entry reference difference (second - first): {row['entry_reference_difference_points']}", "Method 3 (small-support break) is untouched; no mandatory support break is bypassed.", "Research variant; not selected."], shade=[(row["zone_low"], row["zone_high"], "PDS zone", "#1565c0")], markers=mk)
            (R65 / "charts_pds" / f"{w}_{d}_{row['pds_method'].replace(' ', '')}_{str(hm).replace(':', '')}.svg").write_text(svg)
            pds_ch += 1
    write_csv(R65 / "pds_confirmation_variants.csv", pds_rows)
    cats = Counter(r["delay_category"].split("_")[0] for r in delayed)
    uniq = {(r["window"], r["date"], r["retest_candle"]) for m in ("PDR_B1", "PDR_B2") for r in var_rows[m] if r["relation_to_baseline"] == "EARLIER" and "at/below the zone ceiling" in r["reason"]}
    route = {m: {rel: sum(1 for r in var_rows[m] if r["relation_to_baseline"].startswith(rel) and r.get("baseline_confirmation_route") and "GOOD_GREEN_BODY" not in r["baseline_confirmation_route"].split("+")) for rel in ("SAME", "EARLIER", "LATER", "REMOVED_BY_VARIANT")} for m in ("PDR_B1", "PDR_B2", "PDR_C")}
    state = {"b_ceiling_bypass_unique_cycles": len(uniq), "variant_changes_attributable_to_dropped_rejection_route": route, "tradable_before_cutoff": {"engine_signals_total": len(cyc_rows), "engine_signals_tradable": sum(1 for r in cyc_rows if r["engine_signal_tradable_before_13_00_cutoff"]),
             "delayed_total": len(delayed), "delayed_tradable": sum(1 for r in delayed if r["engine_signal_tradable_before_13_00_cutoff"])}, "cycles_total": len(cyc_rows), "confirmed_cycles": len(cyc_rows), "delayed_cycles": len(delayed), "delay_categories": dict(cats), "pdr_charts": n_ch, "pds_charts": pds_ch,
             "variant_relations": {m: dict(Counter(r["relation_to_baseline"].split(" ")[0] for r in rows)) for m, rows in var_rows.items()},
             "pds_second": {w: {"second_signals": sum(1 for r in pds_rows if r["window"] == w and r.get("second_eligible_confirmation") and r["date"] != "ALL" and r.get("zone_low") is not None)} for w in ("A", "B")}}
    (R65 / "continuation_pdr_state.json").write_text(json.dumps(state, indent=1, default=str))
    print(json.dumps(state, indent=1, default=str)[:2500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
