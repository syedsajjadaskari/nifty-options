"""Phase 3.6: PDR signal-level comparison (Phase 3.5 wick-ceiling stream vs the Phase 3.6 body-based stream), per-session zone comparison, sensitivity counts and the source-chart validation.

Writes into reports/phase3/phase36_body_based_pdr/ (new files only). Run after scripts/phase36_run.py:  .venv/bin/python scripts/phase36_pdr_compare.py
No profit, P&L or journal outcome is used to choose anything; the sensitivity rows are counts of signals.
"""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

import phase34_run as W34  # noqa: E402  (World34 loader and the guide's dated examples)

from nifty_trading.data.sessions import load_daily_official  # noqa: E402
from nifty_trading.strategies.definitions import prev_candles, to_candles  # noqa: E402
from nifty_trading.strategies.pdr_body import (  # noqa: E402
    PDR_BODY_RULES,
    PDRBodyConfig,
    PDRBodyStrategy,
    build_zone,
    build_zone_a,
    build_zone_b,
)
from nifty_trading.strategies.pdr_revised import (  # noqa: E402
    PDRRevisedStrategy,
    PDRRevisionConfig,
    classify_confirmation,
)

OUT = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P35 = ROOT / "reports" / "phase3" / "phase35_combined"
P32 = ROOT / "reports" / "phase3" / "phase32"
A_, B_ = "A_HIGHEST_BODY_HIGH", "B_MULTIPLE_BODY_HIGH_CLUSTER"


def hm(ts) -> str:
    return f"{ts:%H:%M}"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def wcsv(path: Path, rows: list[dict]) -> None:
    fields: list[str] = []
    for r in rows:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: ("" if r.get(k) is None else r.get(k)) for k in fields})


def confirmed(recs: dict) -> dict[tuple[str, str], object]:
    return {(str(d), hm(r.signal_timestamp)): r for d, rs in recs.items() for r in rs if r.signal_status == "CONFIRMED"}


def main() -> None:  # noqa: C901
    w = W34.World34()
    body = lambda **kw: PDRBodyStrategy(proposals=w.p, trade=w.trade, revision=PDRBodyConfig(**kw))  # noqa: E731
    runs = {"A_default": w.run_engine(body()), "B_default": w.run_engine(body(zone_candidate=B_)), "A_lenient": w.run_engine(body(pattern_profile="EXAMPLE_LENIENT")),
            "B_lenient": w.run_engine(body(zone_candidate=B_, pattern_profile="EXAMPLE_LENIENT"))}
    wick = w.run_engine(PDRRevisedStrategy(proposals=w.p, trade=w.trade, revision=PDRRevisionConfig(zone_candidate="A_DAY_HIGH_ANCHORED")))  # the Phase 3.5 engine, re-run read-only
    s35_csv = {(r["date"], r["time"]) for r in rd(P35 / "all_strategy_signals.csv") if r["strategy"] == "PDR"}
    s35 = confirmed(wick)
    assert set(s35) == s35_csv, "the re-run Phase 3.5 stream differs from the delivered Phase 3.5 export"
    s36 = confirmed(runs["A_default"])
    s36_csv = {(r["date"], r["time"]) for r in rd(OUT / "all_strategy_signals.csv") if r["strategy"] == "PDR"}
    assert set(s36) == s36_csv, "the signal stream of this script differs from the delivered Phase 3.6 backtest"
    legacy = {(r["date"], r["time"]) for r in rd(P32 / "all_strategy_signals.csv") if r["strategy"] == "PDR"}
    t35 = {(t["date"], t["signal_candle_end"]): t["trade_id"] for t in rd(P35 / "all_trades_detailed.csv") if t["strategy"] == "PDR"}
    t36 = {(t["date"], t["signal_candle_end"]): t["trade_id"] for t in rd(OUT / "all_trades_detailed.csv") if t["strategy"] == "PDR"}

    def zone_of(d: date, cfg: PDRBodyConfig):
        return build_zone(to_candles(prev_candles(w.ctxs[d].previous, w.p)), cfg)

    def eval_at(recs: dict, d: date, start: str):
        for r in recs.get(d, []):
            for e in r.reference_levels.get("evaluations", []):
                if e["candle_start"] == start:
                    return e
        return None

    # ---------------------------------------------------------------------------------------------------------- signal-level comparison
    rows: list[dict] = []
    for (ds, ts), r in sorted(s35.items()):
        d = date.fromisoformat(ds)
        lv = r.reference_levels
        start = hm(r.signal_candle_start)
        z = zone_of(d, PDRBodyConfig())
        row = {"row_type": "PHASE35_SIGNAL", "date": ds, "confirmation_candle_start": start, "signal_time": ts, "phase35_zone_floor": lv["zone_floor"], "phase35_zone_ceiling_wick_high": lv["zone_ceiling"],
               "phase35_patterns": "+".join(lv["patterns_passed"]), "phase35_close_minus_ceiling": lv["close_minus_ceiling"], "phase36_body_zone_floor": z.floor, "phase36_body_zone_ceiling": z.ceiling,
               "wick_ignored_points": z.previous_day_wick_high - z.ceiling, "in_phase36": (ds, ts) in s36, "phase35_trade_id": t35.get((ds, ts), ""), "phase36_trade_id": t36.get((ds, ts), ""),
               "legacy_phase30_signal": (ds, ts) in legacy}
        if (ds, ts) in s36:
            n = s36[(ds, ts)].reference_levels
            row.update({"change_tags": "UNCHANGED_VALID" + (";ZONE_CEILING_LOWERED" if z.ceiling < lv["zone_ceiling"] else ""), "phase36_patterns": "+".join(n["patterns_passed"]),
                        "phase36_close_minus_ceiling": n["close_minus_ceiling"], "reason": f"the same candle qualifies under both zones; the ceiling moves from the wick high {lv['zone_ceiling']:,.2f} to the body high {z.ceiling:,.2f}"})
        else:
            e = eval_at(runs["A_default"], d, start)
            if e is None:
                tag = "REMOVED_BY_BODY_ZONE_NO_ARMED_TEST"
                why = (f"under the body zone [{z.floor:,.2f}, {z.ceiling:,.2f}] no test of the zone had armed the setup before this candle (the test candle, or an earlier signal that re-armed the sequence, differs)")
            elif not e["patterns_passed"]:
                tag, why = "REMOVED_BY_BODY_ZONE_PATTERN", "no pattern passes against the body ceiling (the rejection pattern needs the low to reach the zone ceiling)"
            elif not e["close_above_ceiling"]:
                tag, why = "REMOVED_BY_BODY_ZONE_CLOSE", "the close is not above the body ceiling"
            else:
                tag, why = "REMOVED_BY_SEQUENCE_STATE", "the candle itself qualifies but the armed test was consumed by an earlier body-zone signal"
            row.update({"change_tags": tag, "reason": why})
        rows.append(row)
    for (ds, ts), r in sorted(s36.items()):
        if (ds, ts) in s35:
            continue
        d = date.fromisoformat(ds)
        lv = r.reference_levels
        start = hm(r.signal_candle_start)
        old_day = wick[d]
        inv = [x for x in old_day if x.signal_status == "INVALIDATED"]
        e_old = eval_at(wick, d, start)
        zw = inv[0].reference_levels["zone_ceiling"] if inv else (old_day[0].reference_levels.get("zone_ceiling") if old_day else None)
        if inv and inv[0].invalidation_reason == "GAP_UP_OPEN_NOT_ABOVE_ZONE":
            tag, why = "NEWLY_VALID_OPEN_ABOVE_BODY_ZONE", f"Phase 3.5 rejected the day: the open {w.ctxs[d].open_price:,.2f} was not above the wick ceiling {zw:,.2f}; it is above the body ceiling {lv['zone_ceiling']:,.2f}"
        elif e_old is not None and not e_old["close_above_ceiling"]:
            tag, why = "NEWLY_VALID_CLOSE_ABOVE_BODY_CEILING", f"the close is above the body ceiling {lv['zone_ceiling']:,.2f} but was not above the Phase 3.5 wick ceiling {zw:,.2f}"
        elif e_old is not None and not e_old["patterns_passed"]:
            tag, why = "NEWLY_VALID_PATTERN_VS_BODY_CEILING", "the rejection pattern reaches the (lower) body ceiling"
        else:
            tag, why = "NEWLY_VALID_SEQUENCE", "the test / re-arming sequence differs under the body zone"
        rows.append({"row_type": "PHASE36_NEW_SIGNAL", "date": ds, "confirmation_candle_start": start, "signal_time": ts, "phase35_zone_ceiling_wick_high": zw, "phase36_body_zone_floor": lv["zone_floor"],
                     "phase36_body_zone_ceiling": lv["zone_ceiling"], "wick_ignored_points": lv["wick_ignored_points"], "in_phase36": True, "phase36_patterns": "+".join(lv["patterns_passed"]),
                     "phase36_close_minus_ceiling": lv["close_minus_ceiling"], "phase36_trade_id": t36.get((ds, ts), ""), "legacy_phase30_signal": (ds, ts) in legacy, "change_tags": tag, "reason": why})
    # signals that exist only under the research-profile alternative: ambiguous, preserved for manual review (never traded)
    lenient = confirmed(runs["A_lenient"])
    amb = []
    for (ds, ts), r in sorted(lenient.items()):
        if (ds, ts) in s36:
            continue
        lv = r.reference_levels
        amb.append({"row_type": "AMBIGUOUS_PATTERN_PROFILE_DEPENDENT", "date": ds, "confirmation_candle_start": hm(r.signal_candle_start), "signal_time": ts, "phase36_body_zone_floor": lv["zone_floor"],
                    "phase36_body_zone_ceiling": lv["zone_ceiling"], "lenient_patterns": "+".join(lv["patterns_passed"]), "phase36_close_minus_ceiling": lv["close_minus_ceiling"], "in_phase36": False,
                    "change_tags": "AMBIGUOUS_PATTERN_PROFILE_DEPENDENT", "reason": "closes above the body ceiling after a test and passes a pattern only under the example-read thresholds (EXAMPLE_LENIENT): the default research thresholds reject it. NOT traded; preserved for manual review"})
    wcsv(OUT / "old_vs_new_pdr_signals.csv", rows + amb)

    # ---------------------------------------------------------------------------------------------------------- per-session zone comparison (every evaluable session)
    daily = []
    wick35 = {str(d): rs for d, rs in wick.items()}
    for d in w.days:
        if d not in w.ctxs:
            continue
        c = w.ctxs[d]
        if c.previous is None:
            continue
        pcs = to_candles(prev_candles(c.previous, w.p))
        za, zb = build_zone_a(pcs), build_zone_b(pcs, PDRBodyConfig(zone_candidate=B_))
        recs = runs["A_default"][d]
        st = [r for r in recs if r.signal_status == "NOT_EVALUATED"]
        gap = None if c.previous.close_official is None else c.open_price - c.previous.close_official
        n35 = sum(1 for r in wick35[str(d)] if r.signal_status == "CONFIRMED")
        n36 = sum(1 for r in recs if r.signal_status == "CONFIRMED")
        inv36 = [r.invalidation_reason for r in recs if r.signal_status == "INVALIDATED"]
        wick_ceiling = za.previous_day_wick_high
        daily.append({"date": str(d), "previous_session": str(c.previous.date), "previous_day_wick_high": wick_ceiling, "previous_day_body_high": za.ceiling, "wick_minus_body": round(wick_ceiling - za.ceiling, 4),
                      "body_zone_A_floor": za.floor, "body_zone_A_ceiling": za.ceiling, "body_zone_A_kind": za.kind, "body_zone_B_floor": zb.floor, "body_zone_B_kind": zb.kind, "body_zone_B_touches": zb.touches,
                      "zone_flags": ";".join(za.flags), "session_open": c.open_price, "gap_points": None if gap is None else round(gap, 4), "gap_up": bool(gap and gap > 0),
                      "open_above_wick_ceiling_phase35": c.open_price > wick_ceiling, "open_above_body_ceiling_phase36": c.open_price > za.ceiling,
                      "open_above_zone_status_changed": (c.open_price > wick_ceiling) != (c.open_price > za.ceiling), "phase30_legacy_signals": sum(1 for (x, _) in legacy if x == str(d)),
                      "phase35_signals": n35, "phase36_signals": n36, "phase36_setup_status": ("NOT_EVALUATED" if st else (";".join(sorted(set(inv36))) if inv36 and not n36 else f"{n36} confirmed signal(s)" if n36 else "no setup / no completed confirmation")),
                      "day_difference": ("NEW_PDR_SIGNAL_DAY" if n36 and not n35 else "PDR_SIGNAL_DAY_REMOVED" if n35 and not n36 else "SIGNALS_CHANGED" if n35 != n36 or {t for (x, t) in s35 if x == str(d)} != {t for (x, t) in s36 if x == str(d)} else "UNCHANGED")})
    wcsv(OUT / "pdr_daily_zone_comparison.csv", daily)

    # ---------------------------------------------------------------------------------------------------------- sensitivity counts (signals only, no P&L)
    def cnt(recs):
        s = confirmed(recs)
        return len(s), len({d for d, _ in s})
    sens = []
    for name, recs, note in (("Phase 3.0 legacy engine (reversal swing zone, any green candle)", None, "reference: Phase 3.2 export"), ("Phase 3.5 wick-ceiling engine (candidate A)", wick, "reference: re-run read-only, identical to the Phase 3.5 export"),
                             ("Phase 3.6 body-based A, RESEARCH_DEFAULT patterns (ACTIVE)", runs["A_default"], "active research configuration"), ("Phase 3.6 body-based B, RESEARCH_DEFAULT patterns", runs["B_default"], "candidate B (multiple-body-high zone): same ceiling, different floor"),
                             ("Phase 3.6 body-based A, EXAMPLE_LENIENT patterns", runs["A_lenient"], "sensitivity: thresholds read off the guide's four dated entry candles (circular for those candles); not an approval"),
                             ("Phase 3.6 body-based B, EXAMPLE_LENIENT patterns", runs["B_lenient"], "sensitivity")):
        if recs is None:
            sens.append({"variant": name, "signals": len(legacy), "days_with_a_signal": len({d for d, _ in legacy}), "note": note})
        else:
            n, dd = cnt(recs)
            sens.append({"variant": name, "signals": n, "days_with_a_signal": dd, "note": note})
    extra = {"A, TREAT_AS_LINE zero-height policy": body(zero_height_policy="TREAT_AS_LINE"), "A, open may be anywhere (sensitivity; NOT the author rule)": body(open_vs_zone="ANY"),
             "A, confirmation may be the test candle (sensitivity)": body(confirmation_may_be_interaction_candle=True), "A, good green body only": body(patterns_enabled=("GOOD_GREEN_BODY",)),
             "A, lower-price rejection only": body(patterns_enabled=("LOWER_PRICE_REJECTION",)), "A, hammer only": body(patterns_enabled=("HAMMER",)),
             "B, body spike excluded when above a shelf (diagnostic)": body(zone_candidate=B_, b_spike_policy="EXCLUDE_ISOLATED_BODY_SPIKE_ABOVE_SHELF")}
    for t in (5.0, 10.0, 15.0):
        extra[f"B, tolerance {t:g} points"] = body(zone_candidate=B_, b_tolerance_points=t)
    for name, eng in extra.items():
        n, dd = cnt(w.run_engine(eng))
        sens.append({"variant": "Phase 3.6 body-based " + name, "signals": n, "days_with_a_signal": dd, "note": ("diagnostic and NOT meaningful: the shelf flag fires for nearly every session because a shelf of repeated body highs can lie anywhere in the day (counts only)" if "spike excluded" in name else "sensitivity / diagnostic (counts only)")})
    wcsv(OUT / "pdr_sensitivity_counts.csv", sens)

    # ---------------------------------------------------------------------------------------------------------- source-chart validation (the guide's dated examples)
    val = []
    for name, d, lo_d, hi_d, entry in W34.EXAMPLES:
        c = w.ctxs[d]
        cs = w.cs[d]
        pcs = to_candles(prev_candles(c.previous, w.p))
        za = build_zone_a(pcs)
        zb = build_zone_b(pcs, PDRBodyConfig(zone_candidate=B_))
        wick_j = max(range(len(pcs)), key=lambda k: pcs[k].h)
        ec = next(x for x in cs if hm(x.start) == entry)
        row = {"example": name, "date": str(d), "drawn_zone_floor": lo_d, "drawn_zone_ceiling": hi_d, "author_entry_candle": entry, "previous_day_wick_high": za.previous_day_wick_high, "wick_high_candle": hm(pcs[wick_j].start),
               "previous_day_body_high": za.ceiling, "body_high_candle": hm(za.source_starts[0]), "body_zone_A": f"[{za.floor:,.2f}, {za.ceiling:,.2f}]", "body_zone_B": f"[{zb.floor:,.2f}, {zb.ceiling:,.2f}] {zb.kind}",
               "drawn_ceiling_minus_body_ceiling": round(hi_d - za.ceiling, 2), "drawn_ceiling_minus_wick_high": round(hi_d - za.previous_day_wick_high, 2),
               "drawn_ceiling_follows": ("BODY_HIGH" if abs(hi_d - za.ceiling) <= abs(hi_d - za.previous_day_wick_high) else "WICK_HIGH"), "session_open": c.open_price, "open_above_body_ceiling": c.open_price > za.ceiling,
               "open_above_drawn_ceiling": c.open_price > hi_d, "entry_candle_ohlc": f"O {ec.o} H {ec.h} L {ec.l} C {ec.c}", "entry_close_above_body_ceiling": ec.c > za.ceiling, "entry_close_above_drawn_ceiling": ec.c > hi_d}
        for prof in ("RESEARCH_DEFAULT", "EXAMPLE_LENIENT"):
            res = classify_confirmation(ec, za.floor, za.ceiling, PDRBodyConfig(pattern_profile=prof).pattern_config())
            row[f"patterns_{prof}"] = "+".join(res["patterns_passed"]) or "none"
            recs = [r for r in runs["A_default" if prof == "RESEARCH_DEFAULT" else "A_lenient"][d] if r.signal_status == "CONFIRMED"]
            row[f"engine_signal_at_authors_candle_{prof}"] = any(hm(r.signal_candle_start) == entry for r in recs)
            row[f"engine_signals_that_day_{prof}"] = ";".join(hm(r.signal_candle_start) for r in recs)
        inv = [r.invalidation_reason for r in runs["A_default"][d] if r.signal_status == "INVALIDATED"]
        row["engine_setup_status_default"] = "; ".join(inv) if inv else "setup not rejected at the open (gap up, open above the body ceiling)"
        val.append(row)
    wcsv(OUT / "source_chart_validation.csv", val)

    # ---------------------------------------------------------------------------------------------------------- wick-versus-body statistics
    diffs = [float(r["wick_minus_body"]) for r in daily]
    ds_ = sorted(diffs)
    stats = {"sessions": len(diffs), "median_points": ds_[len(ds_) // 2], "mean_points": sum(diffs) / len(diffs), "max_points": max(diffs), "zero_difference": sum(1 for x in diffs if x == 0),
             "above_5_points": sum(1 for x in diffs if x > 5), "open_above_zone_status_changed": sum(1 for r in daily if r["open_above_zone_status_changed"]),
             "open_above_wick_ceiling": sum(1 for r in daily if r["open_above_wick_ceiling_phase35"]), "open_above_body_ceiling": sum(1 for r in daily if r["open_above_body_ceiling_phase36"]),
             "gap_up_sessions": sum(1 for r in daily if r["gap_up"]), "zero_height_zones": sum(1 for r in daily if "ZERO_HEIGHT_ZONE" in r["zone_flags"]),
             "phase30_legacy_signals": len(legacy), "phase35_signals": len(s35), "phase36_signals": len(s36), "phase36_signal_days": len({d for d, _ in s36}), "phase35_signal_days": len({d for d, _ in s35}),
             "common_signals": len(set(s35) & set(s36)), "removed_signals": len(set(s35) - set(s36)), "new_signals": len(set(s36) - set(s35)), "ambiguous_pattern_profile_dependent": len(amb)}
    # ---- how the signals sit relative to the zone (review S2-1): a candle may close below the zone floor between the test and the confirmation
    broken = []
    for (ds, ts), r in sorted(s36.items()):
        d = date.fromisoformat(ds)
        cs = w.cs[d]
        lv = r.reference_levels
        ji = next(k for k, c in enumerate(cs) if hm(c.start) == lv["interaction_candle_start"])
        ci = next(k for k, c in enumerate(cs) if c.start == r.signal_candle_start)
        low_close = min((c.c for c in cs[ji:ci]), default=None)
        broken.append({"date": ds, "signal_time": ts, "trade_id": t36.get((ds, ts), ""), "test_candle": lv["interaction_candle_start"], "candles_waited": ci - ji, "zone_floor": lv["zone_floor"], "zone_ceiling": lv["zone_ceiling"],
                       "zone_width": lv["zone_width"], "lowest_close_between_test_and_confirmation": low_close, "closed_below_floor_before_confirmation": bool(low_close is not None and low_close < lv["zone_floor"]),
                       "test_candle_is_the_opening_candle": lv["interaction_candle_start"] == "09:15"})
    wcsv(OUT / "pdr_signal_zone_state.csv", broken)
    stats.update({"signals_after_zone_closed_through": sum(1 for b in broken if b["closed_below_floor_before_confirmation"]), "trades_after_zone_closed_through": sum(1 for b in broken if b["trade_id"] and b["closed_below_floor_before_confirmation"]),
                  "executed_pdr_trades": sum(1 for b in broken if b["trade_id"]), "max_candles_waited": max(b["candles_waited"] for b in broken), "signals_with_opening_candle_as_test": sum(1 for b in broken if b["test_candle_is_the_opening_candle"]),
                  "max_zone_width": max(float(b["zone_width"]) for b in broken)})
    # ---- margin of the open above the ceiling and the vendor-open sensitivity (review S2-2)
    vend = {str(x["date"])[:10]: float(x["open"]) for x in load_daily_official().to_dict("records")}
    zones = {r["date"]: r for r in daily}
    margins = []
    for (ds, ts), tid in sorted(t36.items()):
        z = zones[ds]
        margins.append({"trade_id": tid, "date": ds, "signal_time": ts, "first_1min_open": float(z["session_open"]), "body_ceiling": float(z["body_zone_A_ceiling"]), "open_minus_ceiling": round(float(z["session_open"]) - float(z["body_zone_A_ceiling"]), 2),
                        "vendor_daily_open": vend.get(ds), "vendor_open_minus_ceiling": None if vend.get(ds) is None else round(vend[ds] - float(z["body_zone_A_ceiling"]), 2),
                        "in_phase35_trades": (ds, ts) in t35})
    margins.sort(key=lambda m: m["open_minus_ceiling"])
    wcsv(OUT / "pdr_trade_open_margins.csv", margins)
    flips = [r["date"] for r in daily if r["date"] in vend and (float(r["session_open"]) > float(r["body_zone_A_ceiling"])) != (vend[r["date"]] > float(r["body_zone_A_ceiling"]))]
    stats.update({"open_margin_smallest_three": [m["open_minus_ceiling"] for m in margins[:3]], "vendor_open_differs_over_0_05": sum(1 for r in daily if r["date"] in vend and abs(vend[r["date"]] - float(r["session_open"])) > 0.05),
                  "vendor_open_flips_open_above_zone": flips, "default_signals_absent_under_lenient": len(set(s36) - set(lenient)), "lenient_signals": len(lenient), "lenient_only_signals": len(amb)})
    (OUT / "pdr_signal_statistics.json").write_text(json.dumps(stats, indent=2))
    wcsv(OUT / "pdr_body_rules.csv", [{**r, "supersedes": ";".join(r.get("supersedes", [])), "implemented_by": r.get("implemented_by", ""), "parameter": r.get("parameter", "")} for r in PDR_BODY_RULES])
    print(json.dumps(stats))


if __name__ == "__main__":
    main()
