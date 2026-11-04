"""Phase 3.4: run the revised PDR engine (candidates A and B) beside the untouched legacy engine over all sessions and write the comparison CSVs.

READ-ONLY with respect to every earlier result: the legacy engine, the controller, the exit model, the other four engines and all ledgers are used exactly as they are
(or not at all); no portfolio back-test is run and no P&L is computed. Writes reports/phase3/phase34_pdr_revision/*.csv and a pickle-free JSON of the run for the charts/docs.
"""

from __future__ import annotations

import csv
import json
import sys
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from nifty_trading.core.execution_eligibility import (  # noqa: E402
    ENTRY_CUTOFF,
    bars_from_frame,
    entry_within_cutoff,
)
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase31 as R  # noqa: E402
from nifty_trading.strategies import PDRStrategy  # noqa: E402
from nifty_trading.strategies.definitions import pdr_zone, prev_candles, to_candles  # noqa: E402
from nifty_trading.strategies.pdr_revised import (  # noqa: E402
    PDR_REVISION_RULES,
    RULE_STATUS,
    PDRRevisedStrategy,
    PDRRevisionConfig,
    build_zone,
    classify_confirmation,
)
from nifty_trading.strategies.selection import fill_from_next_bar  # noqa: E402

OUT = ROOT / "reports" / "phase3" / "phase34_pdr_revision"
P32 = ROOT / "reports" / "phase3" / "phase32"
P33 = ROOT / "reports" / "phase3" / "phase33_pdr_audit"
TOL = 15  # the Phase 3.1 matching tolerance in minutes (unchanged)
CANDS = {"A": "A_DAY_HIGH_ANCHORED", "B": "B_MULTIPLE_HIGH_CLUSTER"}
# drawn zones of the PDR guide's dated examples (Phase 2.2 calibration of the chart price tags, +/- 1 point) and the author's entry candle start
EXAMPLES = [("Example 1 (p.3)", date(2025, 9, 2), 24632.0, 24640.0, "09:25"), ("Example 2 (p.3)", date(2025, 10, 6), 24901.9, 24905.6, "09:30"),
            ("Example 3 (p.4)", date(2025, 10, 7), 25080.8, 25084.4, "09:20"), ("Example 4 (p.4)", date(2025, 11, 20), 26061.8, 26074.2, "09:45")]


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


def hm(ts) -> str:
    return f"{ts:%H:%M}"


def mins(s: str) -> int:
    return int(s[:2]) * 60 + int(s[3:])


def intersects(c, z) -> bool:
    return c.l <= z.ceiling and c.h >= z.floor


class World34:
    def __init__(self) -> None:
        m1 = load_one_minute()
        self.ctxs, self.infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
        m1 = m1.assign(_d=m1.timestamp.dt.date)
        self.bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
        self.sc = P.scenarios()["baseline"]
        self.p = self.sc.proposals
        self.trade = self.sc.trade
        self.days = sorted(self.infos)
        self.cs = {d: to_candles(c.candles) for d, c in self.ctxs.items()}

    def run_engine(self, eng) -> dict[date, list]:
        return {d: eng.evaluate_session(self.ctxs[d]) for d in self.days if d in self.ctxs}


def eng_for(w: World34, cand: str, **kw) -> PDRRevisedStrategy:
    return PDRRevisedStrategy(proposals=w.p, trade=w.trade, revision=PDRRevisionConfig(zone_candidate=CANDS[cand], **kw))


def sig_set(recs: dict[date, list]) -> set[tuple[str, str]]:
    return {(str(d), hm(r.signal_timestamp)) for d, rs in recs.items() for r in rs if r.signal_status == "CONFIRMED"}


def first_per_day(recs: dict[date, list]) -> set[tuple[str, str]]:
    out = set()
    for d, rs in recs.items():
        c = sorted((r.signal_timestamp for r in rs if r.signal_status == "CONFIRMED"))
        if c:
            out.add((str(d), hm(c[0])))
    return out


def fill_info(w: World34, d: date, ts) -> dict:
    f = fill_from_next_bar(w.bars[d], ts)
    if f is None:
        return {"eligibility": "NOT_FILLABLE (no executable bar starts at the candle end)", "fill_ts": "", "fill_price": None}
    entry, bars = f
    return {"eligibility": "ELIGIBLE", "fill_ts": f"{bars[0].ts:%Y-%m-%d %H:%M}", "fill_price": entry}


def main() -> None:  # noqa: C901
    OUT.mkdir(parents=True, exist_ok=True)
    w = World34()
    legacy_eng = PDRStrategy(proposals=w.p, trade=w.trade)
    old = w.run_engine(legacy_eng)
    runs = {("A", "RESEARCH_DEFAULT"): w.run_engine(eng_for(w, "A")), ("B", "RESEARCH_DEFAULT"): w.run_engine(eng_for(w, "B")),
            ("A", "EXAMPLE_LENIENT"): w.run_engine(eng_for(w, "A", pattern_profile="EXAMPLE_LENIENT")), ("B", "EXAMPLE_LENIENT"): w.run_engine(eng_for(w, "B", pattern_profile="EXAMPLE_LENIENT"))}
    # sensitivity runs for the journal 2x2 table: thresholds x open rule (the open-anywhere runs are NOT an author rule; they show how much of the journal gap belongs to the preserved PDR-011 proposal)
    runs_any = {(c, prof): w.run_engine(eng_for(w, c, pattern_profile=prof, open_vs_zone="ANY")) for c in "AB" for prof in ("RESEARCH_DEFAULT", "EXAMPLE_LENIENT")}
    # ---- legacy stream verification against the Phase 3.2 export
    eng32 = {(r["date"], r["time"]) for r in csv.DictReader(open(P32 / "all_strategy_signals.csv", newline="")) if r["strategy"] == "PDR"}
    old_set = sig_set(old)
    legacy_ok = old_set == eng32
    print(f"legacy PDR signals re-run: {len(old_set)}; Phase 3.2 export: {len(eng32)}; identical: {legacy_ok}")
    ledger = [r for r in csv.DictReader(open(P32 / "automated_trades_detailed.csv", newline="")) if r["strategy"] == "PDR"]
    trade_by_key = {(t["date"], t["signal_confirmed_at"][-5:]): t for t in ledger}
    # ---- manual journal (Phase 3.1 conventions)
    sessions = {str(d): w.infos[d].quality.value for d in w.infos}
    p21 = json.loads((ROOT / "reports" / "phase21" / "journal_reconciliation.json").read_text())
    alt = {}
    for k, v in p21["attribution_hypotheses"].items():
        for c in v.get("candidate_rows", []):
            alt[int(c["sheet_row"])] = "PDR" if k == "feb_2026" else ("ORB" if k == "jun_2026" else "")
    manual = R.normalize_journal(R.load_journal(), p21["rows"], {k: v for k, v in alt.items() if v}, sessions)
    cmp32 = {c["trade_id"]: c for c in csv.DictReader(open(P32 / "manual_vs_automated.csv", newline="")) if c["trade_id"]}

    # ---- per-signal rows: every old signal x candidate, plus new signals the old engine did not produce
    rows_sig: list[dict] = []
    cfgs = {c: replace(PDRRevisionConfig(zone_candidate=CANDS[c])) for c in "AB"}
    sess_cache: dict[tuple[date, str], dict] = {}

    def zone_for(d: date, cand: str):
        key = (d, cand)
        if key not in sess_cache:
            ctx = w.ctxs[d]
            if ctx.previous is None:
                sess_cache[key] = {"zone": None}
            else:
                pcs = to_candles(prev_candles(ctx.previous, w.p))
                z = build_zone(pcs, cfgs[cand])
                legacy = pdr_zone(ctx.previous, replace(w.p, pdr_zone_method="B_SWING_HIGH_REVERSAL"))
                dh = max(c.h for c in pcs)
                dhc = next(c for c in pcs if c.h == dh)
                sess_cache[key] = {"zone": z, "legacy": legacy, "pcs": pcs, "prev_high": dh, "prev_high_candle": hm(dhc.start)}
        return sess_cache[key]

    def tags_old(d: date, cand: str, rec, in_new: bool) -> tuple[list[str], list[str]]:
        zc = zone_for(d, cand)
        z, cs, ctx = zc["zone"], w.cs[d], w.ctxs[d]
        x = next(i for i, c in enumerate(cs) if c.start == rec.signal_candle_start)
        lv = rec.reference_levels
        zone_changed = abs(z.floor - lv["zone_low"]) > 1e-6 or abs(z.ceiling - lv["zone_high"]) > 1e-6
        res = classify_confirmation(cs[x], z.floor, z.ceiling, cfgs[cand])
        open_ok = ctx.open_price > z.ceiling
        j_exists = any(intersects(cs[m], z) for m in range(0, x))
        tags: list[str] = []
        why: list[str] = []
        if in_new:
            return ["UNCHANGED_VALID"], ["the same candle qualifies under the revised rules" + (" (the zone differs: old [{:.2f}, {:.2f}] -> new [{:.2f}, {:.2f}])".format(lv["zone_low"], lv["zone_high"], z.floor, z.ceiling) if zone_changed else "")]
        if not (open_ok and j_exists):
            tags.append("REMOVED_BY_ZONE_SELECTION")
            why.append((f"the session opened {ctx.open_price:,.2f}, not above the new zone ceiling {z.ceiling:,.2f}" if not open_ok else f"no candle had interacted with the new zone [{z.floor:,.2f}, {z.ceiling:,.2f}] before this candle"))
        if not res["patterns_passed"]:
            tags.append("REMOVED_BY_PATTERN_RULE")
            why.append("none of good-green-body / lower-price-rejection / hammer passes")
        if not res["close_above_ceiling"]:
            tags.append("REMOVED_BY_CLOSE_RULE")
            why.append(f"the close {cs[x].c:,.2f} is {-res['close_minus_ceiling']:,.2f} points {'below' if res['close_minus_ceiling'] < 0 else 'at'} the new ceiling {z.ceiling:,.2f} (strictly above is required)")
        if not tags:
            tags.append("SEQUENCE_STATE_DIFFERENCE")
            earlier = [r2 for r2 in runs[(cand, "RESEARCH_DEFAULT")][d] if r2.signal_status == "CONFIRMED" and r2.signal_timestamp < rec.signal_timestamp]
            why.append("the candle itself qualifies, but " + (f"an earlier revised signal (candle starting {hm(earlier[-1].signal_candle_start)}, confirmed {hm(earlier[-1].signal_timestamp)}) had already consumed the armed test and the zone was not tested again before this candle"
                                                             if earlier else "the revised sequence was not armed at this candle (the test candle for this zone came later or coincides with it)"))
        return tags, why

    for d in w.days:
        if d not in w.ctxs:
            continue
        old_recs = [r for r in old[d] if r.signal_status == "CONFIRMED"]
        for cand in "AB":
            new_recs = [r for r in runs[(cand, "RESEARCH_DEFAULT")][d] if r.signal_status == "CONFIRMED"]
            new_by_start = {r.signal_candle_start: r for r in new_recs}
            old_starts = {r.signal_candle_start for r in old_recs}
            zc = zone_for(d, cand)
            for r in old_recs:
                lv = r.reference_levels
                tr = trade_by_key.get((str(d), hm(r.signal_timestamp)))
                in_new = r.signal_candle_start in new_by_start
                tags, why = tags_old(d, cand, r, in_new) if zc["zone"] is not None else (["DATA_OR_IMPLEMENTATION_ISSUE"], ["no previous session"])
                z = zc["zone"]
                cs = w.cs[d]
                x = next(i for i, c in enumerate(cs) if c.start == r.signal_candle_start)
                res = classify_confirmation(cs[x], z.floor, z.ceiling, cfgs[cand]) if z else None
                nr = new_by_start.get(r.signal_candle_start)
                rows_sig.append({
                    "row_type": "OLD_SIGNAL", "candidate": cand, "date": str(d), "old_signal_id": f"OLD-{d:%Y%m%d}-{hm(r.signal_timestamp).replace(':', '')}", "old_trade_id": tr["trade_id"] if tr else "",
                    "old_signal_was_executed_trade_in_phase30": bool(tr), "confirmation_candle_start": hm(r.signal_candle_start), "confirmation_candle_end": hm(r.signal_timestamp),
                    "old_confirmation_open": r.signal_candle_open, "old_confirmation_high": r.signal_candle_high, "old_confirmation_low": r.signal_candle_low, "old_confirmation_close": r.signal_candle_close,
                    "old_zone_method": lv.get("zone_method", ""), "old_zone_floor": lv["zone_low"], "old_zone_ceiling": lv["zone_high"],
                    "old_qualification_reason": f"{lv.get('zone_method', 'B_SWING_HIGH_REVERSAL')} zone touched at {lv.get('interaction_candle_start')}, then the first later GREEN candle (no close-location or pattern test)",
                    "new_zone_candidate": CANDS[cand], "new_zone_kind": z.kind if z else "", "new_zone_floor": z.floor if z else None, "new_zone_ceiling": z.ceiling if z else None,
                    "new_zone_source_candles": ";".join(f"{s:%Y-%m-%d %H:%M}" for s in z.source_starts) if z else "", "new_zone_width": z.width if z else None, "previous_day_high": zc.get("prev_high"),
                    "patterns_passed": "+".join(res["patterns_passed"]) if res else "", "pattern_good_green_body": res["patterns"]["GOOD_GREEN_BODY"]["passed"] if res else None,
                    "pattern_lower_price_rejection": res["patterns"]["LOWER_PRICE_REJECTION"]["passed"] if res else None, "pattern_hammer": res["patterns"]["HAMMER"]["passed"] if res else None,
                    "close_minus_new_ceiling": res["close_minus_ceiling"] if res else None, "close_strictly_above_new_ceiling": res["close_above_ceiling"] if res else None,
                    "signal_valid_under_revision": in_new, "new_signal_id": f"PDRSIG-{d:%Y%m%d}-{hm(r.signal_timestamp).replace(':', '')}-{cand}" if in_new else "", "change_tags": ";".join(tags),
                    "reason": "; ".join(why), "config_id": nr.reference_levels["config_id"] if nr else cfgs[cand].config_id(w.p),
                    "portfolio_note": "signal-level comparison only; the shared portfolio controller was NOT re-run, so no executed trade is said to be removed or added"})
            for r in new_recs:
                if r.signal_candle_start in old_starts:
                    continue
                lv = r.reference_levels
                zlo, zhi = None, None
                lz = zc.get("legacy")
                if lz is not None:
                    zlo, zhi = lz.low, lz.high
                zone_changed = lz is None or abs(lv["zone_floor"] - zlo) > 1e-6 or abs(lv["zone_ceiling"] - zhi) > 1e-6
                cs = w.cs[d]
                c = next(c for c in cs if c.start == r.signal_candle_start)
                tags = []
                if zone_changed:
                    tags.append("NEWLY_VALID_ZONE")
                if not c.c > c.o or not zone_changed:
                    tags.append("NEWLY_VALID_PATTERN")
                fi = fill_info(w, d, r.signal_timestamp)
                rows_sig.append({
                    "row_type": "NEW_SIGNAL", "candidate": cand, "date": str(d), "old_signal_id": "", "old_trade_id": "", "confirmation_candle_start": hm(r.signal_candle_start), "confirmation_candle_end": hm(r.signal_timestamp),
                    "old_zone_method": "B_SWING_HIGH_REVERSAL (diagnostic)", "old_zone_floor": zlo, "old_zone_ceiling": zhi, "old_qualification_reason": "the legacy engine produced no signal on this candle",
                    "new_zone_candidate": CANDS[cand], "new_zone_kind": lv["zone_kind"], "new_zone_floor": lv["zone_floor"], "new_zone_ceiling": lv["zone_ceiling"], "new_zone_source_candles": ";".join(lv["zone_member_candle_starts"]),
                    "new_zone_width": lv["zone_width"], "previous_day_high": lv["previous_day_high"], "patterns_passed": "+".join(lv["patterns_passed"]), "close_minus_new_ceiling": lv["close_minus_ceiling"],
                    "close_strictly_above_new_ceiling": True, "signal_valid_under_revision": True, "new_signal_id": f"PDRSIG-{d:%Y%m%d}-{hm(r.signal_timestamp).replace(':', '')}-{cand}", "change_tags": ";".join(tags),
                    "reason": ("the zone differs from the legacy reversal-swing zone and " if zone_changed else "the zone equals the legacy zone but ") + (f"the candle is {'bullish' if c.c > c.o else 'not bullish'} and passes {'+'.join(lv['patterns_passed'])} with its close "
                              f"{lv['close_minus_ceiling']:,.2f} above the ceiling; the legacy rule fired on a different candle or not at all"),
                    "confirmation_open": c.o, "confirmation_high": c.h, "confirmation_low": c.l, "confirmation_close": c.c, "earliest_entry_eligibility": fi["eligibility"], "synthetic_fill_timestamp": fi["fill_ts"], "synthetic_fill_price": fi["fill_price"],
                    "config_id": lv["config_id"], "portfolio_note": "signal-level only; the controller was not re-run"})
    # ---- entry-condition details: every candle examined by the revised engine after a test (accepted and rejected)
    details: list[dict] = []
    for cand in "AB":
        for d, recs in runs[(cand, "RESEARCH_DEFAULT")].items():
            for r in recs:
                lv = r.reference_levels
                if r.signal_status == "NOT_EVALUATED":
                    details.append({"date": str(d), "candidate": cand, "decision": "NOT_EVALUATED", "reason": r.invalidation_reason, "config_id": cfgs[cand].config_id(w.p)})
                    continue
                if r.signal_status == "INVALIDATED":
                    details.append({"date": str(d), "candidate": cand, "zone_kind": lv.get("zone_kind"), "zone_floor": lv.get("zone_floor"), "zone_ceiling": lv.get("zone_ceiling"), "session_open": lv.get("session_open"),
                                    "gap_points": lv.get("gap_points"), "decision": "SETUP_INVALIDATED", "reason": r.invalidation_reason, "config_id": lv.get("config_id")})
                    continue
                for ev in lv.get("evaluations", []):
                    pd_ = ev["pattern_details"]
                    ts_end = next(c.end for c in w.cs[d] if hm(c.start) == ev["candle_start"])
                    fi = fill_info(w, d, ts_end) if ev["qualifies"] else {"eligibility": "", "fill_ts": "", "fill_price": None}
                    details.append({
                        "date": str(d), "candidate": cand, "zone_kind": lv["zone_kind"], "zone_floor": lv["zone_floor"], "zone_ceiling": lv["zone_ceiling"], "zone_source_candles": ";".join(lv["zone_member_candle_starts"]),
                        "previous_day_high": lv["previous_day_high"], "session_open": lv["session_open"], "gap_points": lv["gap_points"], "interaction_candle_start": lv.get("interaction_candle_start"),
                        "evaluated_candle_start": ev["candle_start"], "open": ev["open"], "high": ev["high"], "low": ev["low"], "close": ev["close"],
                        "body_pct": pd_["GOOD_GREEN_BODY"].get("body_pct"), "upper_wick_pct": pd_["GOOD_GREEN_BODY"].get("upper_wick_pct"), "lower_wick_pct": pd_["GOOD_GREEN_BODY"].get("lower_wick_pct"),
                        "direction": "BULLISH" if ev["close"] > ev["open"] else ("BEARISH" if ev["close"] < ev["open"] else "DOJI"),
                        "good_green_body": pd_["GOOD_GREEN_BODY"]["passed"], "lower_price_rejection": pd_["LOWER_PRICE_REJECTION"]["passed"], "hammer": pd_["HAMMER"]["passed"],
                        "rejection_wick_to_body": pd_["LOWER_PRICE_REJECTION"].get("wick_to_body"), "rejection_low_reached_zone": pd_["LOWER_PRICE_REJECTION"].get("low_reached_zone"),
                        "hammer_body_position": pd_["HAMMER"].get("body_position"), "patterns_passed": "+".join(ev["patterns_passed"]), "close_minus_ceiling": ev["close_minus_ceiling"], "close_strictly_above_ceiling": ev["close_above_ceiling"],
                        "decision": "SIGNAL_CONFIRMED" if ev["qualifies"] else "CANDLE_REJECTED", "reason": ("pattern(s) " + "+".join(ev["patterns_passed"]) + " and close above the ceiling") if ev["qualifies"] else
                        ("no pattern passes" if not ev["patterns_passed"] else "") + ("; " if (not ev["patterns_passed"] and not ev["close_above_ceiling"]) else "") + ("" if ev["close_above_ceiling"] else f"close {ev['close']:,.2f} is not strictly above the ceiling ({ev['close_minus_ceiling']:+.2f})"),
                        "entry_eligibility": fi["eligibility"], "synthetic_fill_timestamp": fi["fill_ts"], "synthetic_fill_price": fi["fill_price"], "within_13_00_cutoff": bool(entry_within_cutoff(ts_end, ENTRY_CUTOFF)) if ev["qualifies"] else "",
                        "thresholds_status": "PROPOSED_FOR_REVIEW (not author-approved)", "close_rule_status": RULE_STATUS["PDR-A05"], "pattern_or_rule_status": RULE_STATUS["PDR-A04"], "config_id": lv["config_id"]})
                if r.signal_status == "INCOMPLETE_AT_EOD":
                    details.append({"date": str(d), "candidate": cand, "zone_kind": lv.get("zone_kind"), "zone_floor": lv.get("zone_floor"), "zone_ceiling": lv.get("zone_ceiling"), "interaction_candle_start": lv.get("interaction_candle_start"),
                                    "decision": "SETUP_INCOMPLETE_AT_EOD", "reason": "no candle after the test qualified before the session ended", "config_id": lv.get("config_id")})
    # ---- daily comparison rows
    daily: list[dict] = []
    flip_unstable: dict[date, bool] = {}
    zones_tol = {t: {} for t in (5.0, 10.0, 15.0)}
    for d in w.days:
        if d not in w.ctxs or w.ctxs[d].previous is None:
            continue
        pcs = to_candles(prev_candles(w.ctxs[d].previous, w.p))
        for t in zones_tol:
            zb = build_zone(pcs, replace(PDRRevisionConfig(zone_candidate=CANDS["B"]), b_tolerance_points=t))
            zones_tol[t][d] = (round(zb.floor, 2), round(zb.ceiling, 2))
        flip_unstable[d] = len({zones_tol[t][d] for t in zones_tol}) > 1
    for d in w.days:
        if d not in w.ctxs:
            continue
        ctx = w.ctxs[d]
        old_all = old[d]
        old_conf = [r for r in old_all if r.signal_status == "CONFIRMED"]
        old_status = ("NOT_EVALUATED (" + (old_all[0].invalidation_reason or "") + ")") if old_all and old_all[0].signal_status == "NOT_EVALUATED" else (
            f"{len(old_conf)} confirmed signal(s), first {hm(old_conf[0].signal_timestamp)}" if old_conf else ("; ".join(sorted({r.invalidation_reason or r.signal_status for r in old_all})) or "no setup (no gap up)"))
        old_tr = [t["trade_id"] for t in ledger if t["date"] == str(d)]
        for cand in "AB":
            zc = zone_for(d, cand)
            z = zc["zone"]
            new_all = runs[(cand, "RESEARCH_DEFAULT")][d]
            new_conf = [r for r in new_all if r.signal_status == "CONFIRMED"]
            lenient_conf = [r for r in runs[(cand, "EXAMPLE_LENIENT")][d] if r.signal_status == "CONFIRMED"]
            inv = [r for r in new_all if r.signal_status == "INVALIDATED"]
            inc = [r for r in new_all if r.signal_status == "INCOMPLETE_AT_EOD"]
            ne = [r for r in new_all if r.signal_status == "NOT_EVALUATED"]
            gap = ctx.open_price - ctx.previous.close_official if ctx.previous is not None and ctx.previous.close_official is not None else None
            first = new_conf[0] if new_conf else None
            ev_last = (new_conf[0].reference_levels["evaluations"][-1] if new_conf else (inc[0].reference_levels["evaluations"][-1] if inc and inc[0].reference_levels.get("evaluations") else None))
            old_starts = {r.signal_candle_start for r in old_conf}
            new_starts = {r.signal_candle_start for r in new_conf}
            tags: list[str] = []
            reasons: list[str] = []
            if ne:
                tags.append("DATA_OR_IMPLEMENTATION_ISSUE")
                reasons.append("the engines cannot evaluate this session: " + (ne[0].invalidation_reason or ""))
            for r in old_conf:
                if r.signal_candle_start not in new_starts:
                    t_, w_ = tags_old(d, cand, r, False)
                    tags += t_
                    reasons.append(f"old {hm(r.signal_timestamp)}: " + "; ".join(w_))
            for r in new_conf:
                if r.signal_candle_start not in old_starts:
                    c = next(c for c in w.cs[d] if c.start == r.signal_candle_start)
                    lz = zc.get("legacy")
                    zone_changed = lz is None or abs(z.floor - lz.low) > 1e-6 or abs(z.ceiling - lz.high) > 1e-6
                    if zone_changed:
                        tags.append("NEWLY_VALID_ZONE")
                    if not c.c > c.o or not zone_changed:
                        tags.append("NEWLY_VALID_PATTERN")
                    reasons.append(f"new {hm(r.signal_timestamp)}: " + ("zone differs from the legacy zone; " if zone_changed else "same zone as the legacy engine; ") + f"patterns {'+'.join(r.reference_levels['patterns_passed'])}")
            if cand == "B" and (zones_tol[5.0][d] != (round(zone_for(d, "A")["zone"].floor, 2), round(zone_for(d, "A")["zone"].ceiling, 2)) or flip_unstable.get(d)):
                tags.append("UNRESOLVED_ZONE")
                reasons.append("the drawn multiple-high zone (its FLOOR; the ceiling is always the previous-day high) depends on unresolved details (tolerance / spike policy): it differs from candidate A or changes with the tolerance (5 / 10 / 15 points). "
                               "Under the active rules the signals are unaffected, because only the ceiling enters the close rule and the floor is inert while the open must lie above the ceiling")
            retained = sorted(old_starts & new_starts)
            if retained:
                tags.insert(0, "UNCHANGED_VALID")
                reasons.append(f"{len(retained)} old signal(s) are retained unchanged ({', '.join(hm(x) for x in retained)})")
            if not [t for t in tags if t != "UNRESOLVED_ZONE"] and not retained:
                tags.insert(0, "UNCHANGED_INVALID")
                reasons.append("no valid PDR signal under either rule set")
            daily.append({
                "date": str(d), "candidate": cand, "weekday": f"{d:%A}", "previous_session": str(ctx.previous.date), "previous_day_high": zc.get("prev_high"), "previous_day_high_candle": zc.get("prev_high_candle"),
                "zone_candidate": CANDS[cand], "zone_kind": z.kind, "zone_floor": z.floor, "zone_ceiling": z.ceiling, "zone_width": z.width, "zone_source_candles": ";".join(f"{s:%H:%M}" for s in z.source_starts),
                "zone_touches": z.touches, "zone_notes": ("INFORMATIONAL, NOT EVALUATED: " if ne else "") + " | ".join(z.notes), "legacy_zone_floor": zc["legacy"].low if zc.get("legacy") else None, "legacy_zone_ceiling": zc["legacy"].high if zc.get("legacy") else None,
                "session_open": ctx.open_price, "gap_points": "" if ne else gap, "gap_up": "" if ne else bool(gap and gap > 0), "open_above_zone_ceiling": "" if ne else bool(ctx.open_price > z.ceiling),
                "retest_condition": "NOT EVALUATED (the previous session is unverifiable; the zone columns of this row are informational only)" if ne else ("test candle " + (first.reference_levels["interaction_candle_start"] if first else (inc[0].reference_levels.get("interaction_candle_start") if inc else "n/a")))
                if (first or inc) else ("no setup: " + (inv[0].invalidation_reason if inv else ("gap not up" if not (gap and gap > 0) else "price never interacted with the zone"))),
                "confirmation_candle": hm(first.signal_candle_start) if first else "", "patterns_passed_first_signal": "+".join(first.reference_levels["patterns_passed"]) if first else "",
                "last_evaluated_candle_patterns": ("+".join(ev_last["patterns_passed"]) or "none") if ev_last else "", "close_above_ceiling_first_signal": True if first else (ev_last["close_above_ceiling"] if ev_last else ""),
                "revised_signal_count": len(new_conf), "signal_confirmation_time": hm(first.signal_timestamp) if first else "", "earliest_eligible_entry_time": hm(first.signal_timestamp) if first else "",
                "signal_times": ";".join(hm(r.signal_timestamp) for r in new_conf), "lenient_profile_signal_count_sensitivity": len(lenient_conf), "old_pdr_signal_status": old_status, "old_signal_count": len(old_conf),
                "old_signal_times": ";".join(hm(r.signal_timestamp) for r in old_conf), "old_executed_trade_ids": ";".join(old_tr),
                "revised_pdr_signal_status": (f"{len(new_conf)} confirmed signal(s)" if new_conf else (inv[0].invalidation_reason if inv else ("INCOMPLETE_AT_EOD: " + (inc[0].invalidation_reason or "") if inc else ("NOT_EVALUATED" if ne else "no setup (gap not up)")))),
                "change_tags": ";".join(dict.fromkeys(tags)), "reason_for_difference": " || ".join(reasons), "config_id": cfgs[cand].config_id(w.p),
                "zone_changes_with_tolerance_5_10_15": bool(flip_unstable.get(d)),
                "rule_status": "PDR-A01/A02(principle)/A04/A05 AUTHOR_APPROVED (their readings A01a/A04z/A05a OWNER_INTERPRETATION); numeric details PROPOSED_FOR_REVIEW; portfolio rules USER_APPROVED"})
    # ---- sensitivities (counts only)
    sens = []

    def sens_row(name: str, recs: dict, note: str) -> None:
        s = sig_set(recs)
        sens.append({"variant": name, "signals": len(s), "days_with_a_signal": len({d for d, _ in s}), "first_signal_per_day": len(first_per_day(recs)), "note": note})
    sens_row("legacy engine (reversal swing zone, any green candle) - for reference", old, "Phase 3.0 research candidate B; not changed")
    sens_row("revised A, default patterns", runs[("A", "RESEARCH_DEFAULT")], "ACTIVE research candidate A")
    sens_row("revised B, default patterns (tolerance 5)", runs[("B", "RESEARCH_DEFAULT")], "ACTIVE research candidate B")
    sens_row("revised A, EXAMPLE_LENIENT patterns", runs[("A", "EXAMPLE_LENIENT")], "sensitivity: thresholds read off the guide's four dated entry candles; not the default")
    sens_row("revised B, EXAMPLE_LENIENT patterns", runs[("B", "EXAMPLE_LENIENT")], "sensitivity")
    for t in (10.0, 15.0):
        sens_row(f"revised B, tolerance {t:g}", w.run_engine(PDRRevisedStrategy(proposals=w.p, trade=w.trade, revision=PDRRevisionConfig(zone_candidate=CANDS["B"], b_tolerance_points=t))), "sensitivity of the unresolved cluster tolerance")
    sens_row("revised B, spike excluded when it lies above a shelf (diagnostic)", w.run_engine(PDRRevisedStrategy(proposals=w.p, trade=w.trade, revision=PDRRevisionConfig(zone_candidate=CANDS["B"], b_spike_policy="EXCLUDE_ISOLATED_SPIKE_ABOVE_SHELF"))),
             "contradicts PDR-A01 (the ceiling is below the day high); diagnostic only")
    for cand in "AB":
        sens_row(f"revised {cand}, open may be anywhere (open_vs_zone=ANY)", w.run_engine(eng_for(w, cand, open_vs_zone="ANY")), "sensitivity of the preserved PDR-011 proposal (not an author rule)")
        sens_row(f"revised {cand}, confirmation may be the test candle itself", w.run_engine(eng_for(w, cand, confirmation_may_be_interaction_candle=True)), "sensitivity of the preserved sequence rule")
        sens_row(f"revised {cand}, good green body only", w.run_engine(eng_for(w, cand, patterns_enabled=("GOOD_GREEN_BODY",))), "diagnostic: pattern 1 alone")
        sens_row(f"revised {cand}, lower-price rejection only", w.run_engine(eng_for(w, cand, patterns_enabled=("LOWER_PRICE_REJECTION",))), "diagnostic: pattern 2 alone")
        sens_row(f"revised {cand}, hammer only", w.run_engine(eng_for(w, cand, patterns_enabled=("HAMMER",))), "diagnostic: pattern 3 alone")
    # ---- manual journal comparison
    jr: list[dict] = []
    for m in manual:
        if m["strategy_normalized"] != "PDR" and m.get("alt_strategy_candidate") != "PDR":
            continue
        d = date.fromisoformat(m["date"])
        label = mins(m["entry_time_label"])
        rec = {"journal_row": m["journal_row"], "date": m["date"], "manual_entry_time_label": m["entry_time_label"], "manual_strategy_entered": m["strategy_entered"], "manual_strategy_normalized": m["strategy_normalized"],
               "alternate_strategy_candidate": m.get("alt_strategy_candidate", ""), "manual_direction": "LONG (implied by PDR; the journal has no direction column)", "manual_outcome": m["exit_classification_entered"], "manual_entry_price": "NOT_RECORDED",
               "attribution": "DISPUTED (Phase 2.1 hypothesis: strategy label may be wrong)" if m.get("alt_strategy_candidate") == "PDR" and m["strategy_normalized"] != "PDR" else "PDR"}
        if d not in w.ctxs:
            jr.append({**rec, "note": "no vendor session for this date"})
            continue
        old_c = [r for r in old[d] if r.signal_status == "CONFIRMED"]

        def nearest(recs, label=label):
            best = None
            for r in recs:
                dt = mins(hm(r.signal_candle_start)) - label
                if abs(dt) <= TOL and (best is None or (abs(dt), dt) < (abs(best[1]), best[1])):
                    best = (r, dt)
            return best
        bo = nearest(old_c)
        rec.update({"old_signal": (f"{hm(bo[0].signal_candle_start)} ({'EXACT' if bo[1] == 0 else 'TIME_SHIFTED'}, {bo[1]:+d} min)" if bo else "none within 15 minutes"),
                    "old_signals_that_day": ";".join(hm(r.signal_candle_start) for r in old_c)})
        tr = [t for t in ledger if t["date"] == m["date"]]
        rec["old_executed_pdr_trade"] = ";".join(f"{t['trade_id']} {t['signal_candle_start']}" for t in tr)
        for cand in "AB":
            new_c = [r for r in runs[(cand, "RESEARCH_DEFAULT")][d] if r.signal_status == "CONFIRMED"]
            bn = nearest(new_c)
            z = zone_for(d, cand)["zone"]
            rec[f"revised_{cand}_signal"] = (f"{hm(bn[0].signal_candle_start)} ({'EXACT' if bn[1] == 0 else 'TIME_SHIFTED'}, {bn[1]:+d} min; patterns {'+'.join(bn[0].reference_levels['patterns_passed'])})" if bn else "none within 15 minutes")
            rec[f"revised_{cand}_signals_that_day"] = ";".join(hm(r.signal_candle_start) for r in new_c)
            rec[f"revised_{cand}_zone"] = f"[{z.floor:,.2f}, {z.ceiling:,.2f}] {z.kind}" if z else ""
            bl = nearest([r for r in runs[(cand, "EXAMPLE_LENIENT")][d] if r.signal_status == "CONFIRMED"])
            rec[f"revised_{cand}_lenient_signal_sensitivity"] = (f"{hm(bl[0].signal_candle_start)} ({bl[1]:+d} min)" if bl else "none within 15 minutes")
            for prof, short in (("RESEARCH_DEFAULT", "default"), ("EXAMPLE_LENIENT", "lenient")):
                ba = nearest([r for r in runs_any[(cand, prof)][d] if r.signal_status == "CONFIRMED"])
                rec[f"revised_{cand}_{short}_open_anywhere_sensitivity"] = (f"{hm(ba[0].signal_candle_start)} ({ba[1]:+d} min)" if ba else "none within 15 minutes")
            ex = [e for e in EXAMPLES if e[1] == d]
            if ex and z is not None:
                lo_d, hi_d = ex[0][2], ex[0][3]
                inter = max(0.0, min(hi_d, z.ceiling) - max(lo_d, z.floor))
                union = max(hi_d, z.ceiling) - min(lo_d, z.floor)
                rec[f"revised_{cand}_zone_vs_authors_drawn_zone"] = f"drawn [{lo_d:,.2f}, {hi_d:,.2f}] ({ex[0][0]}): overlap/union {inter / union:.2f} - " + ("RESEMBLES" if inter / union >= 0.5 else "DIFFERS")
            else:
                rec[f"revised_{cand}_zone_vs_authors_drawn_zone"] = "no author-drawn zone available for this date"
        def found(src, prof, d=d):
            n = nearest([r for r in src[("A", prof)][d] if r.signal_status == "CONFIRMED"])
            return n is not None and n[1] == 0
        f_dd, f_ld, f_da, f_la = found(runs, "RESEARCH_DEFAULT"), found(runs, "EXAMPLE_LENIENT"), found(runs_any, "RESEARCH_DEFAULT"), found(runs_any, "EXAMPLE_LENIENT")
        rec["candidate_A_exact_match_by_setting"] = f"default/open-above={f_dd}; lenient/open-above={f_ld}; default/open-anywhere={f_da}; lenient/open-anywhere={f_la}"
        rec["candidate_A_gap_attribution"] = ("exact match under the active setting" if f_dd else "recovered by the lenient thresholds alone (pattern thresholds)" if f_ld and not f_da else
                                              "recovered by open-anywhere alone (the preserved PDR-011 open-above-zone proposal)" if f_da and not f_ld else
                                              "needs BOTH lenient thresholds and open-anywhere" if f_la else "not an exact match under any of the four settings")
        rec["matched_phase32_trade_class"] = next((c["match_classification"] for c in cmp32.values() if c["journal_row"] == m["journal_row"]), "")
        rec["remaining_mismatch"] = ("; ".join(x for x in [("the old engine had no signal near this row" if not bo else ""), ("candidate A has no signal near this row" if not rec["revised_A_signal"][0].isdigit() else ""),
                                                          ("candidate B has no signal near this row" if not rec["revised_B_signal"][0].isdigit() else ""),
                                                          (f"candidate A: {rec['candidate_A_gap_attribution']}" if not f_dd else "")] if x) or "none: every engine version has a signal within tolerance")
        rec["note"] = "the journal records no zone, entry price or exit price; no discretionary decision is inferred"
        jr.append(rec)
    # ---- the guide's dated examples under the revised rules
    exv: list[dict] = []
    for name, d, lo_d, hi_d, entry in EXAMPLES:
        cs = w.cs[d]
        c = next(c for c in cs if hm(c.start) == entry)
        for prof in ("RESEARCH_DEFAULT", "EXAMPLE_LENIENT"):
            cfg = PDRRevisionConfig(zone_candidate=CANDS["A"], pattern_profile=prof)
            res = classify_confirmation(c, lo_d, hi_d, cfg)
            row = {"example": name, "date": str(d), "author_entry_candle": entry, "pattern_profile": prof, "drawn_zone_floor": lo_d, "drawn_zone_ceiling": hi_d, "entry_open": c.o, "entry_high": c.h, "entry_low": c.l, "entry_close": c.c,
                   "close_minus_drawn_ceiling": res["close_minus_ceiling"], "close_strictly_above_drawn_ceiling": res["close_above_ceiling"], "good_green_body": res["patterns"]["GOOD_GREEN_BODY"]["passed"],
                   "lower_price_rejection": res["patterns"]["LOWER_PRICE_REJECTION"]["passed"], "hammer": res["patterns"]["HAMMER"]["passed"], "patterns_passed": "+".join(res["patterns_passed"]) or "none",
                   "body_pct": res["patterns"]["GOOD_GREEN_BODY"]["body_pct"], "upper_wick_pct": res["patterns"]["GOOD_GREEN_BODY"]["upper_wick_pct"], "lower_wick_pct": res["patterns"]["GOOD_GREEN_BODY"]["lower_wick_pct"],
                   "qualifies_under_drawn_zone": res["qualifies"]}
            for cand in "AB":
                recs = [r for r in runs[(cand, prof)][d] if r.signal_status == "CONFIRMED"]
                z = zone_for(d, cand)["zone"]
                inv = [r.invalidation_reason for r in runs[(cand, prof)][d] if r.signal_status == "INVALIDATED"]
                row[f"engine_{cand}_zone"] = f"[{z.floor:,.2f}, {z.ceiling:,.2f}] {z.kind}"
                row[f"engine_{cand}_signal_at_authors_candle"] = any(hm(r.signal_candle_start) == entry for r in recs)
                row[f"engine_{cand}_signals_that_day"] = ";".join(hm(r.signal_candle_start) for r in recs)
                row[f"engine_{cand}_setup_status"] = ("; ".join(inv) if inv else ("signals produced" if recs else "no qualifying candle"))
            exv.append(row)
    wcsv(OUT / "source_example_validation.csv", exv)
    # ---- charts (real candles only)
    from phase34_charts import render
    (OUT / "charts").mkdir(exist_ok=True)
    for f_ in (OUT / "charts").glob("*.svg"):
        f_.unlink()
    manual_by_day = defaultdict(list)
    for m in manual:
        manual_by_day[m["date"]].append(m)

    def zones_of(d: date) -> tuple[list[dict], dict, float, str]:
        za, zb = zone_for(d, "A"), zone_for(d, "B")
        zs = [{"key": "A", "label": "A day-high", "floor": za["zone"].floor, "ceiling": za["zone"].ceiling}]
        src = {"A": [hm(s_) for s_ in za["zone"].source_starts]}
        if abs(zb["zone"].floor - za["zone"].floor) > 1e-6 or abs(zb["zone"].ceiling - za["zone"].ceiling) > 1e-6:
            zs.append({"key": "B", "label": "B multiple-high", "floor": zb["zone"].floor, "ceiling": zb["zone"].ceiling})
            src["B"] = [hm(s_) for s_ in zb["zone"].source_starts]
        else:
            zs[0]["label"] = "A = B"
        if za.get("legacy") is not None:
            zs.append({"key": "LEGACY", "label": "legacy reversal swing (diagnostic)", "floor": za["legacy"].low, "ceiling": za["legacy"].high})
            src["LEGACY"] = [hm(za["legacy"].candle_start)]
        return zs, src, za["prev_high"], za["prev_high_candle"]

    def pattern_lines(d: date, x: int, zs: list[dict]) -> list[str]:
        c = w.cs[d][x]
        out_ = []
        for z in zs:
            if z["key"] == "LEGACY":
                continue
            res = classify_confirmation(c, z["floor"], z["ceiling"], PDRRevisionConfig())
            pt = res["patterns"]
            g, r_, h_ = pt["GOOD_GREEN_BODY"], pt["LOWER_PRICE_REJECTION"], pt["HAMMER"]
            f_ = lambda v: "n/a" if v is None else f"{100 * v:.0f}%"  # noqa: E731
            out_.append(f"{z['label']}: patterns passed {'+'.join(res['patterns_passed']) or 'NONE'}; close {c.c:,.2f} vs ceiling {z['ceiling']:,.2f} = {res['close_minus_ceiling']:+.2f} -> {'qualifies (pattern + close above ceiling)' if res['qualifies'] else 'does NOT qualify (' + ('no pattern passes' if not res['patterns_passed'] else 'close not above the ceiling') + ')'}")
            out_.append(f"   green body {'PASS' if g['passed'] else 'fail'} (bullish {g.get('bullish')}, body {f_(g.get('body_pct'))} >= 60%, upper wick {f_(g.get('upper_wick_pct'))} <= 20%); "
                        f"rejection {'PASS' if r_['passed'] else 'fail'} (wick/body {r_.get('wick_to_body') and round(r_['wick_to_body'], 2)}, reached zone {r_.get('low_reached_zone')}); hammer {'PASS' if h_['passed'] else 'fail'} (wick/body {h_.get('wick_to_body') and round(h_['wick_to_body'], 2)})")
            break
        return out_

    def job_for(d: date, title: str, subtitle: str, conf_start: str | None, test_start: str | None, entry, caption: list[str], extra_zones: list[dict] | None = None, extra_src: dict | None = None) -> dict:
        zs, src, ph, phc = zones_of(d)
        if extra_zones:
            zs = extra_zones + zs
            src = {**(extra_src or {}), **src}
        cs = w.cs[d]
        ci = next((i for i, c in enumerate(cs) if hm(c.start) == conf_start), None) if conf_start else None
        ti = next((i for i, c in enumerate(cs) if hm(c.start) == test_start), None) if test_start else None
        anchor = ci if ci is not None else (ti if ti is not None else 6)
        a_ = max(0, (ti if ti is not None else anchor) - 2)
        b_ = min(len(cs), anchor + 4)
        ctx = w.ctxs[d]
        pcs = zone_for(d, "A")["pcs"]
        return {"title": title, "subtitle": subtitle, "prev_cs": pcs, "cs": cs, "zones": zs, "prev_high": ph, "prev_high_candle": phc, "prev_date": str(ctx.previous.date), "source_starts": src, "conf_idx": ci, "test_idx": ti,
                "zoom": (a_, b_), "entry": entry, "pattern_lines": pattern_lines(d, ci, zs) if ci is not None else [], "caption": caption, "manual": manual_by_day.get(str(d), []), "open_price": ctx.open_price,
                "gap_points": ctx.open_price - ctx.previous.close_official, "date": str(d)}

    index: list[dict] = []
    # (a) executed trades of the old baseline whose signal is not valid under candidate A or B
    old_rows = [r for r in rows_sig if r["row_type"] == "OLD_SIGNAL" and r["old_trade_id"]]
    by_trade: dict[str, dict[str, dict]] = defaultdict(dict)
    for r in old_rows:
        by_trade[r["old_trade_id"]][r["candidate"]] = r
    for tid, rr in sorted(by_trade.items()):
        if all(rr[c]["signal_valid_under_revision"] is True or rr[c]["signal_valid_under_revision"] == "True" for c in rr):
            continue
        any_ = rr["A"]
        d = date.fromisoformat(any_["date"])
        lg = next(t for t in ledger if t["trade_id"] == tid)
        tags = {c: rr[c]["change_tags"] for c in rr}
        cap = [f"OLD executed trade {tid} (Phase 3.0): entry {float(lg['entry_price']):,.2f} at {lg['fill_timestamp'][-5:]}. Old confirmation candle {any_['confirmation_candle_start']} O {float(any_['old_confirmation_open']):,.2f} H {float(any_['old_confirmation_high']):,.2f} "
               f"L {float(any_['old_confirmation_low']):,.2f} C {float(any_['old_confirmation_close']):,.2f}.",
               f"Candidate A: {tags['A']} - {rr['A']['reason']}", f"Candidate B: {tags['B']} - {rr['B']['reason']}", "The shared portfolio controller was NOT re-run: this is a signal-level comparison, not a removed trade."]
        job = job_for(d, f"{tid}: old PDR trade - revised-rule verdict A: {'valid' if rr['A']['signal_valid_under_revision'] in (True, 'True') else 'REMOVED'} / B: {'valid' if rr['B']['signal_valid_under_revision'] in (True, 'True') else 'REMOVED'}",
                      "old zone = legacy reversal swing (grey); candidate zones A (blue) / B (purple); the old confirmation candle is marked CONFIRM?", any_["confirmation_candle_start"], None,
                      (float(lg["entry_price"]), lg["fill_timestamp"][-5:]), cap)
        fn = f"OLD_{tid}.svg"
        (OUT / "charts" / fn).write_text(render(job))
        index.append({"file": fn, "kind": "OLD_EXECUTED_TRADE_CHANGES_VALIDITY", "date": str(d), "id": tid, "tags_A": tags["A"], "tags_B": tags["B"]})
    # (b) every newly valid signal (union of candidates)
    newrows = [r for r in rows_sig if r["row_type"] == "NEW_SIGNAL"]
    seen: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for r in newrows:
        seen[(r["date"], r["confirmation_candle_start"])].append(r)
    for (ds, st), rr in sorted(seen.items()):
        d = date.fromisoformat(ds)
        r0 = rr[0]
        sig = next(x for x in runs[(r0["candidate"], "RESEARCH_DEFAULT")][d] if x.signal_status == "CONFIRMED" and hm(x.signal_candle_start) == st)
        cands = "+".join(sorted({r["candidate"] for r in rr}))
        cap = [f"NEW signal {r0['new_signal_id']} (candidate(s) {cands}): confirmation candle {st} O {float(r0['confirmation_open']):,.2f} H {float(r0['confirmation_high']):,.2f} L {float(r0['confirmation_low']):,.2f} C {float(r0['confirmation_close']):,.2f}; "
               f"patterns {r0['patterns_passed']}; close {float(r0['close_minus_new_ceiling']):+.2f} vs the ceiling; earliest eligibility {r0['earliest_entry_eligibility']}, synthetic fill {r0['synthetic_fill_timestamp'][-5:]} at {r0['synthetic_fill_price']}.",
               "; ".join(f"{r['candidate']}: {r['change_tags']} - {r['reason']}" for r in rr)]
        job = job_for(d, f"NEW PDR signal {ds} {st} (candidate {cands})", "the legacy engine produced no signal on this candle; the zone is drawn from the previous-day high", st, sig.reference_levels["interaction_candle_start"],
                      (float(r0["synthetic_fill_price"]), r0["synthetic_fill_timestamp"][-5:]) if r0["synthetic_fill_price"] not in ("", None) else None, cap)
        fn = f"NEW_{ds}_{st.replace(':', '')}.svg"
        (OUT / "charts" / fn).write_text(render(job))
        index.append({"file": fn, "kind": "NEWLY_VALID_SIGNAL", "date": ds, "id": r0["new_signal_id"], "tags_A": next((r["change_tags"] for r in rr if r["candidate"] == "A"), ""), "tags_B": next((r["change_tags"] for r in rr if r["candidate"] == "B"), "")})
    # (c) the dated PDF examples (Example 3 doubles as the disputed shelf chart)
    shelf_starts = ["13:30", "14:00", "14:55", "15:00", "15:05", "15:20", "15:25"]
    for name, d, lo_d, hi_d, entry in EXAMPLES:
        ev = [e for e in exv if e["example"] == name and e["pattern_profile"] == "RESEARCH_DEFAULT"][0]
        evl = [e for e in exv if e["example"] == name and e["pattern_profile"] == "EXAMPLE_LENIENT"][0]
        cs = w.cs[d]
        test = next(hm(c.start) for c in cs if c.l <= hi_d and c.h >= lo_d)
        src_extra = {"DRAWN": shelf_starts} if name.startswith("Example 3") else {"DRAWN": []}
        cap = [f"{name}: the author's drawn zone (orange, Phase 2.2 calibration of the chart tags, about +/- 1 point) [{lo_d:,.2f}, {hi_d:,.2f}]; entry candle {entry}: O {ev['entry_open']:,.2f} H {ev['entry_high']:,.2f} L {ev['entry_low']:,.2f} C {ev['entry_close']:,.2f}; "
               f"close {ev['close_minus_drawn_ceiling']:+.2f} vs the drawn ceiling.",
               f"Default (RESEARCH_DEFAULT) pattern thresholds: patterns passed {ev['patterns_passed']}; example-read (LENIENT, sensitivity) thresholds: {evl['patterns_passed']}.",
               f"Engine candidate A on this date: {ev['engine_A_setup_status']}; zone {ev['engine_A_zone']}."
               + (" Example 3: the engine's day-high zone includes the 14:50 spike (25,095.70) and the open (25,087.55) lies inside it; the author drew only the late-session shelf of equal highs. The discrepancy is documented, the spike is not silently dropped." if name.startswith("Example 3") else "")]
        job = job_for(d, f"PDR guide {name} - {d}", "author-drawn zone (orange) against the candidate zones; real candles of the repository data (the PDF's candles differ slightly at the open)", entry, test, None, cap,
                      extra_zones=[{"key": "DRAWN", "label": "author-drawn", "floor": lo_d, "ceiling": hi_d}], extra_src=src_extra)
        job["zones"][0]["ceiling"] = hi_d  # the confirmation measurement refers to the author's drawn zone
        job["pattern_lines"] = pattern_lines(d, next(i for i, c in enumerate(cs) if hm(c.start) == entry), job["zones"])
        fn = f"EXAMPLE_{name.split()[1]}{'_shelf_vs_spike' if name.startswith('Example 3') else ''}.svg"
        (OUT / "charts" / fn).write_text(render(job))
        index.append({"file": fn, "kind": "PDF_EXAMPLE" + ("_DISPUTED_SHELF" if name.startswith("Example 3") else ""), "date": str(d), "id": name, "tags_A": "", "tags_B": ""})
    # (d) representative multiple-high constructions (candidate B zone differs from A), spread over the year
    clusters = [d for d in w.days if d in w.ctxs and w.ctxs[d].previous is not None and zone_for(d, "B")["zone"].kind == "MULTIPLE_HIGH_CLUSTER"
                and w.ctxs[d].previous.close_official is not None and w.ctxs[d].open_price > w.ctxs[d].previous.close_official]  # gap-up days only, so the zoom panel shows a real test / confirmation area
    pick = [clusters[round(i * (len(clusters) - 1) / 7)] for i in range(8)] if len(clusters) >= 8 else clusters
    for d in dict.fromkeys(pick):
        zb = zone_for(d, "B")["zone"]
        sigs = [r for r in runs[("B", "RESEARCH_DEFAULT")][d] if r.signal_status == "CONFIRMED"]
        inc = [r for r in runs[("B", "RESEARCH_DEFAULT")][d] if r.signal_status == "INCOMPLETE_AT_EOD"]
        st = hm(sigs[0].signal_candle_start) if sigs else None
        ts = sigs[0].reference_levels["interaction_candle_start"] if sigs else (inc[0].reference_levels.get("interaction_candle_start") if inc else None)
        cap = [f"Representative multiple-high construction: candidate B joins {zb.touches} touches ({'; '.join(zb.notes)}). Zone floor {zb.floor:,.2f} (lowest member body top), ceiling {zb.ceiling:,.2f} = the previous-day high; width {zb.width:,.2f}.",
               "Candidate A uses only the day-high candle. The numeric choices (tolerance 5, separation 2 candles, lower boundary) are research parameters, not author rules."]
        job = job_for(d, f"Multiple-high zone construction (candidate B) - {d}", "members of the cluster are outlined in purple on the previous session", st, ts,
                      None, cap)
        fn = f"MULTIHIGH_{d}.svg"
        (OUT / "charts" / fn).write_text(render(job))
        index.append({"file": fn, "kind": "MULTIPLE_HIGH_REPRESENTATIVE", "date": str(d), "id": f"B-cluster-{d}", "tags_A": "", "tags_B": ""})
    wcsv(OUT / "charts_index.csv", index)
    print("charts:", Counter(i["kind"] for i in index))
    # ---- write
    wcsv(OUT / "old_vs_new_pdr_signals.csv", rows_sig)
    wcsv(OUT / "pdr_daily_signal_comparison.csv", daily)
    wcsv(OUT / "pdr_entry_condition_details.csv", details)
    wcsv(OUT / "pdr_manual_journal_comparison.csv", jr)
    # 2x2: pattern thresholds x open rule, over the journal rows attributed to PDR (agreement observation only: the lenient numbers were read off four of these very rows, so this is circular and selects nothing)
    j2: list[dict] = []
    pdr_rows = [m for m in manual if m["strategy_normalized"] == "PDR" and date.fromisoformat(m["date"]) in w.ctxs]
    for cand in "AB":
        for prof, pname in (("RESEARCH_DEFAULT", "default thresholds"), ("EXAMPLE_LENIENT", "lenient (example-read) thresholds")):
            for src, oname in ((runs, "open must be above the zone (active, PDR-011)"), (runs_any, "open anywhere (sensitivity)")):
                ex_n = sh_n = 0
                detail = []
                for m in pdr_rows:
                    d = date.fromisoformat(m["date"])
                    lab = mins(m["entry_time_label"])
                    best = None
                    for r in src[(cand, prof)][d]:
                        if r.signal_status != "CONFIRMED":
                            continue
                        dt = mins(hm(r.signal_candle_start)) - lab
                        if abs(dt) <= TOL and (best is None or (abs(dt), dt) < (abs(best), best)):
                            best = dt
                    ex_n += best == 0
                    sh_n += best is not None and best != 0
                    detail.append(f"row {m['journal_row']}: {'none' if best is None else ('exact' if best == 0 else f'{best:+d} min')}")
                j2.append({"candidate": cand, "pattern_thresholds": pname, "open_rule": oname, "journal_pdr_rows": len(pdr_rows), "exact": ex_n, "shifted_within_15_min": sh_n, "within_tolerance_total": ex_n + sh_n,
                           "per_row": "; ".join(detail), "caveat": "agreement observation only - the lenient thresholds were read off four of these rows (circular); no setting is selected by it"})
    wcsv(OUT / "pdr_journal_agreement_2x2.csv", j2)
    wcsv(OUT / "pdr_sensitivity_counts.csv", sens)
    wcsv(OUT / "pdr_revision_rules.csv", [{**r, "supersedes": ";".join(r.get("supersedes", [])), "implemented_by": r.get("implemented_by", ""), "parameter": r.get("parameter", "")} for r in PDR_REVISION_RULES])
    summary = {"legacy_stream_identical_to_phase32_export": legacy_ok, "old_signals": len(old_set), "old_first_signal_days": len(first_per_day(old)), "old_executed_trades": len(ledger),
               "revised": {c: {"signals": len(sig_set(runs[(c, "RESEARCH_DEFAULT")])), "days": len({d for d, _ in sig_set(runs[(c, "RESEARCH_DEFAULT")])}),
                               "lenient_signals": len(sig_set(runs[(c, "EXAMPLE_LENIENT")]))} for c in "AB"}, "sessions": len({r["date"] for r in daily})}
    (OUT / "_run_summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=1))
    print(Counter(r["change_tags"] for r in daily if r["candidate"] == "A").most_common(12))


if __name__ == "__main__":
    main()
