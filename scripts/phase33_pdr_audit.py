"""Phase 3.3: independent PDR entry-validation audit (READ-ONLY). Writes reports/phase3/phase33_pdr_audit/.

Question: of the PDR trades of the Phase 3.2 baseline, which entered LONG on a green confirmation candle that CLOSED BELOW the selected resistance-zone floor, and do the
original PDR guide, its figures and the data support, contradict or leave open that entry? Nothing here changes a rule, a ledger, a stop, a target, the controller or the
cutoff, and no P&L is used for any classification.

The reconstruction uses only the raw parquet files (see ``phase33_lib.py``, which imports nothing from the strategy engine); the Phase 3.2 CSV exports are inputs to compare with.
"""

from __future__ import annotations

import csv
import re
import sys
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from phase33_lib import (  # noqa: E402
    CAS_FIRST_AUCTION_MIN,
    CAS_START,
    P32,
    World,
    config,
    geometry,
    hm,
    rows,
    run_state_machine,
    zone_a_day_high,
    zone_c_shelf,
    zone_engine_b,
)

OUT = ROOT / "reports" / "phase3" / "phase33_pdr_audit"
# Drawn zones of the PDR guide's dated examples (Phase 2.2 pixel calibration against the chart price tags, +/- 1 point; docs/phase2/phase22_source_research_raw.md)
SOURCE_EXAMPLES = [("Example 1 (p.3)", date(2025, 9, 2), 24632.0, 24640.0, "2025-09-01 15:00 session-high candle"),
                   ("Example 2 (p.3)", date(2025, 10, 6), 24901.9, 24905.6, "2025-10-03 15:05 session-high candle"),
                   ("Example 3 (p.4)", date(2025, 10, 7), 25080.8, 25084.4, "2025-10-06 late-session shelf of equal highs (not the 14:50 spike)"),
                   ("Example 4 (p.4)", date(2025, 11, 20), 26061.8, 26074.2, "2025-11-19 14:40 session-high candle")]


def wcsv(path: Path, data: list[dict]) -> None:
    fields: list[str] = []
    for r in data:
        for k in r:
            if k not in fields:
                fields.append(k)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        for r in data:
            w.writerow({k: ("" if r.get(k) is None else (round(r[k], 4) if isinstance(r[k], float) else r[k])) for k in fields})


def r2(x):
    return None if x is None else round(float(x), 2)


def analyse() -> dict:  # noqa: C901
    W = World()
    cfg = config()
    k, prox, tol, mt = cfg["swing_k"], cfg["zone_proximity_points"], cfg["zone_cluster_tolerance_points"], cfg["zone_cluster_min_touches"]
    trades = [t for t in rows(P32 / "automated_trades_detailed.csv") if t["strategy"] == "PDR" and t["direction"] == "LONG"]
    checks = defaultdict(dict)
    for c in rows(P32 / "trade_entry_conditions.csv"):
        checks[c["trade_id"]].setdefault(c["rule_id"], []).append(c)
    cand_rows = defaultdict(dict)
    for c in rows(P32 / "candle_analysis.csv"):
        cand_rows[c["trade_id"]][c["role"]] = c
    cmp_by_trade = {c["trade_id"]: c for c in rows(P32 / "manual_vs_automated.csv") if c["trade_id"]}
    manual_all = defaultdict(list)
    for m in rows(P32 / "manual_journal_normalized.csv"):
        manual_all[m["date"]].append(m)
    signals_by_day = defaultdict(list)
    for s in rows(P32 / "all_strategy_signals.csv"):
        if s["strategy"] == "PDR":
            signals_by_day[s["date"]].append(s)

    allrows: list[dict] = []
    for t in trades:
        d = date.fromisoformat(t["date"])
        p = W.prev(d)
        cs, pcs = W.candles[d], W.candles[p]
        zb = zone_engine_b(pcs, k)
        za = zone_a_day_high(pcs)
        zc = zone_c_shelf(pcs, k, tol, mt)
        ci = next(i for i, c in enumerate(cs) if hm(c.start) == t["signal_candle_start"])
        conf = cs[ci]
        seq = run_state_machine(cs, zb, prox)
        pair = next((s for s in seq if s["i"] == ci), None)
        ji = pair["j"] if pair else None
        jc = cs[ji] if ji is not None else None
        src = zb.source
        pc_open = W.official_close[p]
        op = W.first_open(d)
        day_high = max(c.high for c in pcs)
        dh_idx = next(i for i, c in enumerate(pcs) if c.high == day_high)
        in_auction = bool(p >= CAS_START and (src.start.hour * 60 + src.start.minute) >= CAS_FIRST_AUCTION_MIN)
        fill_bar = W.minute_bar(conf.end)
        # retest low: lowest price from the interaction candle through the confirmation candle (5-minute candles and the underlying 1-minute bars)
        retest_low_5m = min(c.low for c in cs[ji:ci + 1]) if ji is not None else None
        retest_low_before_conf = min(c.low for c in cs[ji:ci]) if ji is not None else None  # excludes the confirmation candle itself
        mm = W.minutes[d]
        window = mm[(mm.timestamp >= __import__("pandas").Timestamp(cs[ji].start)) & (mm.timestamp < __import__("pandas").Timestamp(conf.end))] if ji is not None else None
        retest_low_1m = float(window.low.min()) if window is not None else None
        g = geometry(conf)
        close_vs_floor, close_vs_ceiling = conf.close - zb.lo, conf.close - zb.hi
        pos = "ABOVE_CEILING" if conf.close > zb.hi else ("INSIDE_ZONE" if conf.close >= zb.lo else "BELOW_FLOOR")
        nxt = cs[ci + 1] if ci + 1 < len(cs) else None
        # engine cross-check (Phase 3.2 exports)
        eng_zone = re.findall(r"zone \[([\d,\.]+), ([\d,\.]+)\]", checks[t["trade_id"]]["PDR-002"][0]["observed"])[0]
        eng_lo, eng_hi = (float(x.replace(",", "")) for x in eng_zone)
        e_conf = cand_rows[t["trade_id"]]["confirmation_candle"]
        e_int = cand_rows[t["trade_id"]]["interaction_candle"]
        agree = {"zone": abs(eng_lo - zb.lo) < 1e-6 and abs(eng_hi - zb.hi) < 1e-6,
                 "confirmation_ohlc": all(abs(float(e_conf[k_]) - getattr(conf, k_)) < 1e-6 for k_ in ("open", "high", "low", "close")),
                 "interaction_candle": jc is not None and e_int["candle_start"][-5:] == hm(jc.start) and abs(float(e_int["low"]) - jc.low) < 1e-6,
                 "entry_price_equals_raw_minute_open": fill_bar is not None and abs(float(fill_bar.open) - float(t["entry_price"])) < 1e-6,
                 "signal_reproduced_by_state_machine": pair is not None}
        # alternative zone candidates evaluated with the same sequence rule
        alts = {}
        for nm, z in (("A_previous_day_high", za), ("C_repeated_shelf", zc)):
            if z is None:
                alts[nm] = {"exists": False}
                continue
            seq_z = run_state_machine(cs, z, prox)
            fires = any(s["i"] == ci for s in seq_z)
            alts[nm] = {"exists": True, "lo": z.lo, "hi": z.hi, "same_as_selected": abs(z.lo - zb.lo) < 1e-6 and abs(z.hi - zb.hi) < 1e-6, "open_above_zone": op > z.hi,
                        "fires_on_same_candle": bool(fires and op > z.hi and (op - W.official_close[p]) > 0), "conf_close_minus_floor": conf.close - z.lo, "source": hm(z.source.start)}
        # explicit written conditions of the guide, tested per trade
        explicit = {"gap_up_open_p1_p2": (op - pc_open) > 0, "not_entered_at_the_open_p2": conf.end.hour * 60 + conf.end.minute > SESSION_OPEN_END,
                    "zone_interaction_candle_before_confirmation_p2": jc is not None and ji < ci and jc.low <= zb.hi + prox and jc.high >= zb.lo - prox,
                    "green_candle_after_interaction_p2_p3": conf.green and ji is not None and ci > ji}
        allrows.append({
            "trade_id": t["trade_id"], "date": t["date"], "weekday": t["weekday"], "trade_no_of_day": t["trade_no_of_day"], "rule_configuration_id": t["rule_configuration_id"],
            "zone_method": zb.name, "swing_k": k, "zone_lower_boundary": cfg["zone_lower_boundary"], "zone_proximity_points": prox,
            "previous_session": str(p), "zone_source_candle_start": f"{src.start:%Y-%m-%d %H:%M}", "zone_source_open": src.open, "zone_source_high": src.high, "zone_source_low": src.low, "zone_source_close": src.close,
            "zone_floor": zb.lo, "zone_ceiling": zb.hi, "zone_height": zb.hi - zb.lo, "previous_day_high": day_high, "previous_day_high_candle_start": f"{pcs[dh_idx].start:%H:%M}",
            "zone_is_previous_day_high_candle": zb.members[-1] == dh_idx, "zone_ceiling_below_previous_day_high": day_high - zb.hi, "zone_source_in_closing_auction_window": in_auction,
            "official_previous_close": pc_open, "session_open": op, "gap_points": op - pc_open, "open_above_zone_ceiling_points": op - zb.hi,
            "interaction_candle_start": f"{jc.start:%H:%M}" if jc else "", "interaction_open": jc.open if jc else None, "interaction_high": jc.high if jc else None, "interaction_low": jc.low if jc else None,
            "interaction_close": jc.close if jc else None, "interaction_close_below_floor": (jc.close < zb.lo) if jc else None, "candle_index_difference_confirmation_minus_interaction": (ci - ji) if jc else None,
            "retest_low_5m": retest_low_5m, "retest_low_before_confirmation_candle_5m": retest_low_before_conf, "retest_low_1m": retest_low_1m, "zone_penetration_depth_below_floor_5m": max(0.0, zb.lo - retest_low_5m) if retest_low_5m is not None else None,
            "zone_penetration_depth_below_floor_1m": max(0.0, zb.lo - retest_low_1m) if retest_low_1m is not None else None,
            "confirmation_candle_start": f"{conf.start:%Y-%m-%d %H:%M}", "confirmation_candle_end": f"{conf.end:%Y-%m-%d %H:%M}", "confirmation_open": conf.open, "confirmation_high": conf.high,
            "confirmation_low": conf.low, "confirmation_close": conf.close, "confirmation_direction": g["direction"], "confirmation_body_pct": g["body_pct"], "confirmation_upper_wick": g["upper_wick"],
            "confirmation_upper_wick_pct": g["upper_wick_pct"], "confirmation_lower_wick": g["lower_wick"], "confirmation_lower_wick_pct": g["lower_wick_pct"],
            "confirmation_close_minus_floor": close_vs_floor, "confirmation_close_minus_ceiling": close_vs_ceiling, "confirmation_close_position": pos,
            "signal_confirmed_at": f"{conf.end:%Y-%m-%d %H:%M}", "earliest_fill_timestamp": f"{conf.end:%Y-%m-%d %H:%M}", "ledger_fill_timestamp": t["fill_timestamp"], "entry_price": float(t["entry_price"]),
            "raw_minute_bar_open_at_fill": float(fill_bar.open) if fill_bar is not None else None,
            "POST_ENTRY_next_candle_start": hm(nxt.start) if nxt else "", "POST_ENTRY_next_candle_intersects_zone": (nxt.low <= zb.hi + prox and nxt.high >= zb.lo - prox) if nxt else None,
            "POST_ENTRY_next_candle_low": nxt.low if nxt else None, "POST_ENTRY_next_candle_close": nxt.close if nxt else None,
            "engine_agreement": agree, "alternatives": alts, "explicit": explicit,
            "close_below_floor": close_vs_floor < 0, "ledger_outcome_NOT_USED_FOR_CLASSIFICATION": t["outcome"],
            "journal_match": (cmp_by_trade.get(t["trade_id"]) or {}).get("match_classification", "EXTRA_AUTOMATED_TRADE")})
        allrows[-1]["_cmp"] = cmp_by_trade.get(t["trade_id"])
        allrows[-1]["_manual_day"] = manual_all.get(t["date"], [])
        allrows[-1]["_signals_today"] = signals_by_day.get(t["date"], [])
        allrows[-1]["_checks"] = {r: v for r, v in checks[t["trade_id"]].items()}
    return {"world": W, "cfg": cfg, "rows": allrows, "trades": trades}


SESSION_OPEN_END = 9 * 60 + 20  # an entry confirmed at/before 09:20 would be "at the open" (the first 5-minute candle closes at 09:20)


def classify(r: dict) -> dict:
    """Evidence-based classification of an affected trade. NO P&L or outcome is read. Rules (documented in pdr_source_rule_verification.md):
    1. DATA_OR_IMPLEMENTATION_ISSUE: an engine export disagrees with the raw-data reconstruction, or the zone source candle lies in the closing-auction window.
    2. SOURCE_CONTRADICTED: an explicit written condition of the guide is violated (gap-up, not at the open, interaction before confirmation, green after interaction).
    3. ZONE_SELECTION_DISPUTED: another source-plausible zone (previous-day-high candle A, or the repeated shelf C) would produce the SAME confirmation candle with a close at/above its floor,
       i.e. the entry is acceptable under another reading of 'which resistance'.
    4. INSUFFICIENT_EVIDENCE: the reconstruction could not locate the interaction/confirmation sequence.
    5. otherwise SOURCE_AMBIGUOUS: every written condition holds, the guide never says where the green candle must close, and no alternative zone changes that."""
    agree, expl, alts = r["engine_agreement"], r["explicit"], r["alternatives"]
    if not all(agree.values()):
        return {"classification": "DATA_OR_IMPLEMENTATION_ISSUE", "basis": "engine export differs from raw reconstruction: " + ", ".join(k for k, v in agree.items() if not v), "confidence": "HIGH", "owner_clarification": "no - a defect to fix (not fixed in Phase 3.3)"}
    if r["zone_source_in_closing_auction_window"]:
        return {"classification": "DATA_OR_IMPLEMENTATION_ISSUE", "basis": "the zone source candle lies in the closing-auction window (>= 15:15 on an auction-regime day)", "confidence": "HIGH", "owner_clarification": "yes"}
    broken = [k for k, v in expl.items() if not v]
    if broken:
        return {"classification": "SOURCE_CONTRADICTED", "basis": "explicit written condition violated: " + ", ".join(broken), "confidence": "HIGH", "owner_clarification": "no"}
    flips = [nm for nm, a in alts.items() if a.get("exists") and not a.get("same_as_selected") and a.get("fires_on_same_candle") and a["conf_close_minus_floor"] >= 0]
    if flips:
        return {"classification": "ZONE_SELECTION_DISPUTED", "basis": "the same confirmation candle also fires under " + " and ".join(flips) + " with its close at/above that zone's floor: the entry would be acceptable under another source-plausible zone IF a close at/above the floor is the test (reading B, which is itself not written in the guide)",
                "confidence": "MEDIUM", "owner_clarification": "yes - which previous-day candle marks the zone"}
    if r["interaction_candle_start"] == "":
        return {"classification": "INSUFFICIENT_EVIDENCE", "basis": "interaction candle not reconstructed", "confidence": "LOW", "owner_clarification": "yes"}
    return {"classification": "SOURCE_AMBIGUOUS", "basis": "all written conditions hold (gap-up, not at the open, zone interaction, green candle after it) but the guide never says whether the green candle must close at/above the zone; "
            "no alternative source-plausible zone changes the result", "confidence": "MEDIUM", "owner_clarification": "yes - is a zone-hold (close at/above the floor) required"}


def manual_comparison(rows_: list[dict]) -> list[dict]:
    """The Phase 3.1 matching result (exact / within 15 minutes / none), restated per PDR trade next to every journal row of that day. The journal records no zone, no entry price and no exit price."""
    out = []
    for r in rows_:
        cmp_ = r["_cmp"] or {}
        man = r["_manual_day"]
        pdr = [m for m in man if m["strategy_normalized"] == "PDR"]
        label = int(r["confirmation_candle_start"][-5:-3]) * 60 + int(r["confirmation_candle_start"][-2:])
        deltas = [(m["journal_row"], int(m["entry_time_label"][:2]) * 60 + int(m["entry_time_label"][3:]) - label) for m in pdr]
        klass = cmp_.get("match_classification", "EXTRA_AUTOMATED_TRADE")
        if klass in ("EXACT_MATCH", "TIME_SHIFTED_MATCH"):
            why = f"matched journal row {cmp_['journal_row']} ({klass}, difference {cmp_.get('delta_minutes')} minutes)"
        elif pdr:
            why = ("the journal has PDR row(s) that day but none within the 15-minute tolerance of this candle: "
                   + "; ".join(f"row {jr} at {m['entry_time_label']} ({d:+d} min)" for (jr, d), m in zip(deltas, pdr, strict=True)) + " - the automated trade is an extra entry; the journal does not record why a later/earlier PDR was or was not taken")
        elif man:
            why = "no PDR row in the journal that day; the journal shows other strategy(ies): " + "; ".join(f"{m['strategy_normalized']} {m['entry_time_label']} {m['exit_classification_entered']}" for m in man)
        else:
            why = "no journal trade of any strategy that day"
        out.append({"trade_id": r["trade_id"], "date": r["date"], "affected_close_below_floor": r["close_below_floor"], "trade_no_of_day": r["trade_no_of_day"], "automated_candle_start": r["confirmation_candle_start"][-5:],
                    "automated_entry_time": r["earliest_fill_timestamp"][-5:], "automated_entry_price": r["entry_price"], "automated_direction": "LONG", "automated_zone": f"[{r['zone_floor']:.2f}, {r['zone_ceiling']:.2f}]",
                    "journal_match_class": klass, "matched_journal_row": cmp_.get("journal_row", ""), "matched_via_alternate_label": cmp_.get("matched_via_alternate_label", ""), "time_difference_minutes": cmp_.get("delta_minutes", ""),
                    "journal_outcome_if_matched": cmp_.get("manual_outcome", ""), "automated_outcome_class": r["ledger_outcome_NOT_USED_FOR_CLASSIFICATION"],
                    "journal_pdr_rows_that_day": "; ".join(f"row {m['journal_row']} {m['entry_time_label']} {m['exit_classification_entered']}" for m in pdr),
                    "journal_all_rows_that_day": "; ".join(f"row {m['journal_row']} {m['strategy_normalized']} {m['entry_time_label']} {m['exit_classification_entered']}" for m in man),
                    "journal_direction": "LONG (implied by the PDR strategy; the journal has no direction column)" if pdr else "", "journal_entry_price": "NOT_RECORDED", "journal_selected_zone": "NOT_RECORDED",
                    "reason_or_note": why, "phase32_comparison_explanation": cmp_.get("explanation", "")})
    return out


def severity_band(r: dict) -> str:
    """Informational only (not used by the classification): how far through the zone the confirmation closed, and whether the test candle itself closed through it."""
    d = -r["confirmation_close_minus_floor"]
    if d <= 0:
        return "not below the floor"
    band = "NEAR_MISS (<= 5 points)" if d <= 5 else ("MODERATE (5-25 points)" if d <= 25 else "FAR (> 25 points)")
    return band + ("; the test candle itself closed below the floor" if r["interaction_close_below_floor"] else "; the test candle closed at/above the floor")


def nearest_figure(r: dict) -> str:
    """Qualitative, LOW-confidence resemblance to the guide's figures. No figure shows a confirmation close below the floor, so none is an exact match."""
    pen = r["zone_penetration_depth_below_floor_5m"] or 0.0
    if r["interaction_close_below_floor"]:
        return ("none: the test candle itself CLOSED below the floor (price traded through the zone); Examples 2 and 3 also wick through the floor but their candles close back above it; "
                "all four dated examples end with a confirmation close ABOVE the ceiling")
    if pen > 0:
        return "Examples 2/3 in the wick (price dips below the floor on the test) - DIFFERS: their confirmation candles close above the ceiling, this one closes below the floor"
    return "Examples 4/5 in the dip into the zone - DIFFERS: their confirmation candles close above the ceiling"


def counterfactual(rows_: list[dict]) -> list[dict]:
    """How many of the existing PDR trades satisfy each reading. Diagnostic classification only: no portfolio re-run, no P&L, no recommendation."""
    n = len(rows_)
    aff = [r for r in rows_ if r["close_below_floor"]]
    defs = [("A", "existing rule: zone interaction followed by any green candle", lambda r: True,
             "the written text (pp.1-3: 'After the zone has been tested, wait for a green candle'); no close-location wording"),
            ("B", "green confirmation closes at or above the zone floor", lambda r: r["confirmation_close"] >= r["zone_floor"],
             "PROPOSED: not written in the guide; consistent with all four dated examples (every confirmation closes above the ceiling) but never stated"),
            ("C", "green confirmation closes above the zone ceiling", lambda r: r["confirmation_close"] > r["zone_ceiling"],
             "PROPOSED: not written in the guide; consistent with all four dated examples (every confirmation closes above the drawn ceiling) - the strictest reading that still fits them; but 1 of the 5 journal-matched PDR trades (20260605-1) closes inside the zone and would not satisfy it"),
            ("D", "confirmation closes at/above the floor AND the retest low stays at/above the floor", lambda r: r["confirmation_close"] >= r["zone_floor"] and r["retest_low_5m"] >= r["zone_floor"],
             "PROPOSED: includes the confirmation candle's own wick, which in the author's Examples 2 and 3 trades 20.0 and 3.7 points below the drawn floor before closing above the ceiling (see source_example_checks.csv), so D would not have accepted those two examples"),
            ("D2", "sensitivity of D: the retest low is taken over the candles BEFORE the confirmation candle only", lambda r: r["confirmation_close"] >= r["zone_floor"] and r["retest_low_before_confirmation_candle_5m"] >= r["zone_floor"],
             "PROPOSED (sensitivity row, not one of the four requested readings): the retest low excludes the confirmation candle's own wick; it holds for Examples 1, 3 and 4 and fails Example 2 by 3.25 points on a 3.7-point box, so the figures cannot separate D2 from a tolerant D2")]
    out = []
    for key, desc, fn, ev in defs:
        sat = [r for r in rows_ if fn(r)]
        out.append({"reading": key, "definition": desc, "pdr_trades_audited": n, "trades_satisfying": len(sat), "trades_not_satisfying": n - len(sat),
                    "affected_trades_satisfying": sum(1 for r in aff if fn(r)), "affected_trades_not_satisfying": sum(1 for r in aff if not fn(r)), "affected_trades_total": len(aff),
                    "unaffected_trades_not_satisfying": sum(1 for r in rows_ if not r["close_below_floor"] and not fn(r)),
                    "first_trades_not_satisfying": sum(1 for r in rows_ if r["trade_no_of_day"] == "1" and not fn(r)), "second_trades_not_satisfying": sum(1 for r in rows_ if r["trade_no_of_day"] == "2" and not fn(r)),
                    "source_evidence_status": ev, "status": "EXISTING_RULE (engine)" if key == "A" else "PROPOSED_DIAGNOSTIC_ONLY - not an approved strategy change"})
    return out


def example_checks(W: World, cfg: dict) -> list[dict]:
    k, prox, tol, mt = cfg["swing_k"], cfg["zone_proximity_points"], cfg["zone_cluster_tolerance_points"], cfg["zone_cluster_min_touches"]
    out = []
    for name, d, lo, hi, note in SOURCE_EXAMPLES:
        p = W.prev(d)
        cs, pcs = W.candles[d], W.candles[p]
        from phase33_lib import Zone
        drawn = Zone("DRAWN_BY_AUTHOR (calibrated)", lo, hi, (0,), [])
        for zname, z in (("drawn zone", drawn), ("engine zone B", zone_engine_b(pcs, k)), ("previous-day-high zone A", zone_a_day_high(pcs)), ("shelf zone C", zone_c_shelf(pcs, k, tol, mt))):
            if z is None:
                continue
            seq = run_state_machine(cs, z, prox)
            first = seq[0] if seq else None
            row = {"example": name, "date": str(d), "zone_reading": zname, "zone_floor": z.lo, "zone_ceiling": z.hi, "source_note": note, "open": W.first_open(d), "official_previous_close": W.official_close[p],
                   "gap_points": W.first_open(d) - W.official_close[p]}
            if first:
                j, i = first["j"], first["i"]
                own = {"Example 1 (p.3)": "09:25", "Example 2 (p.3)": "09:30", "Example 3 (p.4)": "09:20", "Example 4 (p.4)": "09:45"}[name]
                jc, ci = cs[j], cs[i]
                row.update({"interaction_candle": hm(jc.start), "interaction_low": jc.low, "interaction_low_minus_floor": jc.low - z.lo, "retest_low_5m": min(c.low for c in cs[j:i + 1]),
                            "retest_low_minus_floor": min(c.low for c in cs[j:i + 1]) - z.lo, "retest_low_before_confirmation_candle_minus_floor": min(c.low for c in cs[j:i]) - z.lo,
                            "is_the_examples_own_entry_candle": hm(cs[i].start) == own, "confirmation_candle": hm(ci.start), "confirmation_close": ci.close, "confirmation_close_minus_floor": ci.close - z.lo,
                            "confirmation_close_minus_ceiling": ci.close - z.hi, "confirmation_position": "ABOVE_CEILING" if ci.close > z.hi else ("INSIDE_ZONE" if ci.close >= z.lo else "BELOW_FLOOR"),
                            "open_above_zone": W.first_open(d) > z.hi})
            else:
                row.update({"interaction_candle": "none (no sequence)", "open_above_zone": W.first_open(d) > z.hi})
            out.append(row)
    return out


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    res = analyse()
    rows_ = res["rows"]
    affected = [r for r in rows_ if r["close_below_floor"]]
    print(f"PDR trades audited: {len(rows_)}; confirmation closed below the zone floor: {len(affected)}")
    for r in rows_:
        r.update(classify(r) if r["close_below_floor"] else {"classification": "NOT_AFFECTED", "basis": "", "confidence": "", "owner_clarification": ""})
        r["zone_selection_open_question_secondary"] = not r["zone_is_previous_day_high_candle"]
        r["nearest_source_figure"] = nearest_figure(r) if r["close_below_floor"] else "n/a (not an affected trade)"
        r["close_below_floor_severity_band"] = severity_band(r)
    ex = example_checks(res["world"], res["cfg"])
    cf = counterfactual(rows_)
    pub = [{k: v for k, v in r.items() if not k.startswith("_") and k not in ("engine_agreement", "alternatives", "explicit")} for r in rows_]
    for r, p in zip(rows_, pub, strict=True):
        for nm, a in r["alternatives"].items():
            p[f"alt_{nm}_zone"] = f"[{a['lo']:.2f}, {a['hi']:.2f}]" if a.get("exists") else "none"
            p[f"alt_{nm}_fires_on_same_candle"] = a.get("fires_on_same_candle")
            p[f"alt_{nm}_confirmation_close_minus_floor"] = a.get("conf_close_minus_floor")
        p["explicit_conditions_all_hold"] = all(r["explicit"].values())
        p["engine_cross_check_all_agree"] = all(r["engine_agreement"].values())
    aff_pub = [p for p in pub if p["close_below_floor"]]
    wcsv(OUT / "affected_27_trades.csv", [{k: p[k] for k in (
        "date", "trade_id", "confirmation_candle_start", "confirmation_candle_end", "confirmation_open", "confirmation_high", "confirmation_low", "confirmation_close", "zone_source_candle_start", "zone_source_open",
        "zone_source_high", "zone_source_low", "zone_source_close", "zone_floor", "zone_ceiling", "confirmation_close_minus_floor", "earliest_fill_timestamp", "entry_price", "zone_method", "swing_k",
        "zone_lower_boundary", "zone_proximity_points", "rule_configuration_id", "journal_match")} | {"distance_below_zone_floor": -p["confirmation_close_minus_floor"],
        "source_rule_status": "green-candle-after-test: SOURCE_VERIFIED_QUALITATIVE (PDR-007); close-location / zone-hold requirement: NOT A SOURCE RULE and NOT TESTED by the engine (UNRESOLVED)"} for p in aff_pub])
    wcsv(OUT / "pdr_confirmation_calculations.csv", pub)
    wcsv(OUT / "pdr_trade_classifications.csv", [{k: p[k] for k in ("trade_id", "date", "close_below_floor", "classification", "confidence", "owner_clarification", "basis", "explicit_conditions_all_hold",
                                                                       "engine_cross_check_all_agree", "zone_is_previous_day_high_candle", "alt_A_previous_day_high_fires_on_same_candle",
                                                                       "alt_C_repeated_shelf_fires_on_same_candle", "confirmation_close_minus_floor", "zone_penetration_depth_below_floor_5m",
                                                                       "zone_selection_open_question_secondary", "close_below_floor_severity_band", "nearest_source_figure")} for p in pub])
    wcsv(OUT / "zone_rule_counterfactual_counts.csv", cf)
    wcsv(OUT / "source_example_checks.csv", ex)
    wcsv(OUT / "manual_journal_comparison.csv", manual_comparison(rows_))
    from phase33_charts import trade_chart
    (OUT / "charts").mkdir(exist_ok=True)
    for r, p_ in zip(rows_, pub, strict=True):
        if r["close_below_floor"]:
            (OUT / "charts" / f"{r['trade_id']}.svg").write_text(trade_chart(res["world"], p_, r["_manual_day"]))
    print(Counter(p["classification"] for p in pub))
    print([(c["reading"], c["trades_satisfying"], c["affected_trades_satisfying"]) for c in cf])


if __name__ == "__main__":
    main()
