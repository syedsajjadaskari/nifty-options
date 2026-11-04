"""Phase 3.1: reconcile the manual journal with the automated baseline (and sensitivity scenarios B, C). READ-ONLY: no rule, parameter or ledger is changed.

Writes reports/phase3/phase31/*.csv|json. The original Phase 3.0 ledgers are never overwritten.
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

from nifty_trading.core.execution_eligibility import bars_from_frame  # noqa: E402
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research import phase3 as P  # noqa: E402
from nifty_trading.research import phase31 as R  # noqa: E402
from nifty_trading.strategies.rules import RULE_BY_ID  # noqa: E402
from nifty_trading.strategies.trading_day import DayRules  # noqa: E402

OUT = ROOT / "reports" / "phase3" / "phase31"
MANIFEST = ROOT / "data" / "metadata" / "session_quality_manifest.json"
MANUAL_LATEST_LABEL = {}  # filled from the journal: latest entry-time label per strategy


def wcsv(path: Path, rows: list[dict], fields: list[str] | None = None) -> None:
    fields = fields or sorted({k for r in rows for k in r})
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    sessions = {str(d): infos[d].quality.value for d in infos}
    p21 = json.loads((ROOT / "reports" / "phase21" / "journal_reconciliation.json").read_text())
    alt = {}
    for k, v in p21["attribution_hypotheses"].items():
        if "candidate_rows" in v:
            for c in v["candidate_rows"]:
                alt[int(c["sheet_row"])] = "PDR" if k == "feb_2026" else ("ORB" if k == "jun_2026" else "")
    alt = {k: v for k, v in alt.items() if v}
    journal = R.load_journal()
    manual = R.normalize_journal(journal, p21["rows"], alt, sessions)
    for m in manual:
        MANUAL_LATEST_LABEL[m["strategy_normalized"]] = max(MANUAL_LATEST_LABEL.get(m["strategy_normalized"], "00:00"), m["entry_time_label"])
    wcsv(OUT / "manual_journal_normalized.csv", manual)
    scs = P.scenarios()
    tls = {k: R.run_timelines(sc, ctxs, bars) for k, sc in scs.items() if k in ("baseline", "ema_structure", "pdr_shelf")}
    base = scs["baseline"]
    # ---------------------------------------------------------------- manual vs automated (baseline) + sensitivity columns
    mv = {}
    used = {}
    for k, tl in tls.items():
        mv[k], used[k] = R.match_manual_to_automated(manual, tl, scs[k].proposals)
    rows = mv["baseline"]
    for r in rows:
        for k in ("ema_structure", "pdr_shelf"):
            other = next(x for x in mv[k] if x["journal_row"] == r["journal_row"])
            r[f"classification_{k}"] = other["classification"]
        r["root_cause_primary"], r["root_cause_secondary"] = R.root_cause_manual(r)
    wcsv(OUT / "manual_vs_automated.csv", rows)
    missing = [r for r in rows if not (r["classification"].startswith("EXACT") or r["classification"].startswith("TIME_SHIFTED"))]
    wcsv(OUT / "missing_manual_trades.csv", [{**r, "probe": json.dumps(next((x.get("probe") for x in [R._classify_unmatched(m, tls["baseline"].get(date.fromisoformat(m["date"])), base.proposals)]
                                                                            if m["journal_row"] == r["journal_row"]), None), default=str) if r["classification"] == "MISSING_AUTOMATED_SIGNAL" else ""}
                                              for r in missing for m in [next(mm for mm in manual if mm["journal_row"] == r["journal_row"])]])
    # ---------------------------------------------------------------- extra automated trades (baseline)
    tl = tls["baseline"]
    matched = used["baseline"]
    manual_by_day = defaultdict(list)
    for m in manual:
        manual_by_day[m["date"]].append(m)
    miss_rows = {r["journal_row"] for r in missing}
    extras = []
    for d, t in tl.items():
        for tr in t.result.trades:
            s = tr.signal
            if (str(d), s.strategy, s.signal_timestamp, s.method, s.direction) in matched:
                continue
            md = manual_by_day.get(str(d), [])
            same_strat = [m for m in md if m["strategy_normalized"] == s.strategy]
            other = [m for m in md if m["strategy_normalized"] != s.strategy]
            prevented = [m["journal_row"] for m in md if m["journal_row"] in miss_rows and R._minutes(m["entry_time_label"]) >= tr.signal.signal_candle_start.hour * 60 + tr.signal.signal_candle_start.minute - 0]
            sat = [r for r in s.rule_ids_satisfied if r in RULE_BY_ID and RULE_BY_ID[r]["classification"] in ("PROPOSED_FOR_REVIEW", "VERIFIED_QUALITATIVE", "USER_APPROVED")]
            dep = {"IRF": {"Method 1": ("SOURCE_AMBIGUITY", "IRF-GLOBAL-004: no trades/day, window or re-arming rule in the guide"),
                           "Method 2A": ("PROPOSED_NUMERICAL_THRESHOLD", "recent-support and extension definitions are proposals"),
                           "Method 2B": ("PROPOSED_NUMERICAL_THRESHOLD", "first-push resistance and extension definitions are proposals"),
                           "Method 3": ("PROPOSED_NUMERICAL_THRESHOLD", "compression and wick-band proposals")},
                   "ORB": {"Method 1": ("TREND_FILTER", "trend (variant A) and strong-candle thresholds are proposals"), "Method 2": ("SOURCE_AMBIGUITY", "inner level/trendline have no objective construction"),
                           "Gap/200DMA": ("SOURCE_AMBIGUITY", "gap-through-MA setup; 'excessively extended' undefined")},
                   "PDR": {"PDR": ("ZONE_SELECTION", "which candle marks the zone is unresolved (PDR-D09); swing k=2 is a proposal")},
                   "PDS": {"Method 1": ("PROPOSED_NUMERICAL_THRESHOLD", "good-body threshold undefined in the guide"), "Method 2": ("PROPOSED_NUMERICAL_THRESHOLD", "HPR ratio undefined"),
                           "Method 3": ("PROPOSED_NUMERICAL_THRESHOLD", "small-support size undefined")},
                   "RF": {"RF": ("TREND_FILTER", "established-uptrend and return-inside definitions are proposals")}}
            cause, basis = dep.get(s.strategy, {}).get(s.method, ("UNKNOWN", ""))
            extras.append({"date": str(d), "trade_no": tr.trade_no, "strategy": s.strategy, "method": s.method, "direction": s.direction, "candle_start": f"{s.signal_candle_start:%H:%M}",
                           "entry_time": f"{tr.fill_timestamp:%H:%M}", "entry_price": tr.entry_price, "auto_outcome": tr.classification, "manual_trades_same_day": len(md),
                           "manual_same_strategy_same_day": ";".join(f"{m['entry_time_label']}:{m['exit_classification_entered']}" for m in same_strat),
                           "manual_other_strategy_same_day": ";".join(f"{m['strategy_normalized']}@{m['entry_time_label']}" for m in other),
                           "extra_context": ("SAME_STRATEGY_MANUAL_TRADE_AT_ANOTHER_TIME" if same_strat else ("MANUAL_TRADED_ONLY_OTHER_STRATEGIES" if other else "NO_MANUAL_TRADE_THAT_DAY")),
                           "later_than_manual_latest_label_for_strategy": f"{s.signal_candle_start:%H:%M}" > MANUAL_LATEST_LABEL.get(s.strategy, "99:99"),
                           "manual_latest_label_for_strategy": MANUAL_LATEST_LABEL.get(s.strategy, ""), "raw_confirmed_signals_that_day_same_strategy": sum(1 for r in tl[d].records if r.strategy == s.strategy and r.signal_status == "CONFIRMED"),
                           "rules_satisfied_proposal_or_qualitative_or_userapproved": ";".join(sat), "rules_unresolved": ";".join(s.rule_ids_unresolved),
                           "manual_rows_possibly_displaced": ";".join(map(str, prevented)),
                           "root_cause_primary": cause, "root_cause_basis": "STRATEGY-LEVEL DEPENDENCY, not trade-specific proof: " + basis,
                           "key_levels": json.dumps({k: v for k, v in s.reference_levels.items() if isinstance(v, (int, float, str, list)) and k in (
                               "IRH", "IRL", "recent_support", "recent_resistance", "zone_low", "zone_high", "zone_method", "level_broken", "level_kind", "gap_points", "prev_day_high", "prev_day_low",
                               "RF_High", "RF_Low", "open_price")}, default=str)})
    wcsv(OUT / "extra_automated_trades.csv", extras)
    # ---------------------------------------------------------------- daily signal timelines (baseline)
    trows = []
    for d, t in tl.items():
        trows += R.timeline_rows(t, "baseline", manual_by_day.get(str(d), []))
    wcsv(OUT / "daily_signal_timelines.csv", trows, ["scenario", "date", "time", "candle_start", "event", "strategy", "method", "direction", "signal_status", "portfolio_state",
                                                    "disposition_reason", "blocked_by", "invalidation_reason", "rules_failed", "rules_unresolved"])
    # ---------------------------------------------------------------- interference
    sig, days = R.interference_matrix(tl)
    inter = [{"earlier_selected_or_blocking": a, "later_blocked_strategy": b, "disposition": c, "signals_affected": n, "days_affected": days[(a, b, c)]} for (a, b, c), n in sorted(sig.items())]
    wcsv(OUT / "strategy_interference_matrix.csv", inter)
    # manual-weighted: missing manual trades classified as portfolio-rejected, by blocker
    mw = Counter((r["blocked_by"].split("#")[0] if r["blocked_by"] else r["chain"][:40], r["strategy_normalized"]) for r in missing if r["classification"] == "SIGNAL_REJECTED_BY_PORTFOLIO_CONTROLLER")
    wcsv(OUT / "strategy_interference_manual_trades.csv", [{"blocker": a, "manual_trade_strategy": b, "manual_trades_affected": n} for (a, b), n in sorted(mw.items())])
    # ---------------------------------------------------------------- collision counterfactual
    cont = R.run_timelines(replace(base), ctxs, bars, DayRules(collision_policy="SKIP_COLLISION_EVENT_CONTINUE_DAY"))
    cf = []
    for d, t in tl.items():
        if any(x.event == "CONFLICT" for x in t.result.diagnostics):
            a = [(tr.signal.strategy, f"{tr.fill_timestamp:%H:%M}", tr.classification) for tr in t.result.trades]
            b = [(tr.signal.strategy, f"{tr.fill_timestamp:%H:%M}", tr.classification) for tr in cont[d].result.trades]
            conf = [x.reason for x in t.result.diagnostics if x.event == "CONFLICT"]
            cf.append({"date": str(d), "conflict": " | ".join(conf), "trades_MARK_DAY_UNRESOLVED": json.dumps(a), "trades_SKIP_COLLISION_EVENT_CONTINUE_DAY": json.dumps(b),
                       "extra_entries": len(b) - len(a), "manual_trades_that_day": ";".join(f"{m['strategy_normalized']}@{m['entry_time_label']}:{m['exit_classification_entered']}" for m in manual_by_day.get(str(d), []))})
    wcsv(OUT / "collision_counterfactual.csv", cf)
    # ---------------------------------------------------------------- headline counts
    def cnt(rs):
        return dict(Counter(r["classification"] for r in rs))
    exact = sum(1 for r in rows if r["classification"] == "EXACT_MATCH")
    shifted = sum(1 for r in rows if r["classification"] == "TIME_SHIFTED_MATCH")
    summary = {"manual_rows": len(manual), "automated_trades_baseline": sum(len(t.result.trades) for t in tl.values()), "exact": exact, "time_shifted": shifted,
               "classification_baseline": cnt(rows), "classification_ema_structure": cnt(mv["ema_structure"]), "classification_pdr_shelf": cnt(mv["pdr_shelf"]),
               "matched_via_alternate_label": sum(1 for r in rows if r.get("matched_via_alternate_label")), "extra_automated": len(extras),
               "extra_by_strategy": dict(Counter(e["strategy"] for e in extras)), "manual_by_strategy": dict(Counter(m["strategy_normalized"] for m in manual)),
               "matched_by_strategy": dict(Counter(r["matched_strategy"] for r in rows if r["classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH"))),
               "missing_by_strategy_and_class": {f"{s}|{c}": n for (s, c), n in sorted(Counter((r["strategy_normalized"], r["classification"]) for r in missing).items())},
               "root_cause_missing": dict(Counter(r["root_cause_primary"] for r in rows if r["root_cause_primary"])),
               "root_cause_missing_by_strategy": {f"{s}|{c}": n for (s, c), n in sorted(Counter((r["strategy_normalized"], r["root_cause_primary"]) for r in rows if r["root_cause_primary"]).items())},
               "root_cause_extra": dict(Counter(e["root_cause_primary"] for e in extras)), "nonconforming_manual_rows": [(m["journal_row"], m["date"], m["strategy_normalized"], m["nonconformity"]) for m in manual if not m["conforms_to_approved_rules"]],
               "outcome_agreement_among_matches": {"agree": sum(1 for r in rows if r.get("outcome_agrees_loosely") is True), "differ": sum(1 for r in rows if r.get("outcome_agrees_loosely") is False)},
               "collision_days": len(cf), "collision_extra_entries_if_continue": sum(c["extra_entries"] for c in cf)}
    (OUT / "reconciliation_counts.json").write_text(json.dumps(summary, indent=2, default=str))
    print(json.dumps({k: summary[k] for k in ("manual_rows", "automated_trades_baseline", "exact", "time_shifted", "extra_automated", "classification_baseline")}, default=str))


if __name__ == "__main__":
    main()
