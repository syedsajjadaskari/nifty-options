"""Measure a predeclared nearest-inner alternative across ALL sessions, signal-only."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)
from nifty_trading.research.phase3 import combined_scenario  # noqa: E402
from nifty_trading.research.phase58 import VARIANTS, reconstruct  # noqa: E402
from nifty_trading.strategies.orb_candidates import ORBCandidateStrategy  # noqa: E402


def read(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def write(path, rows):
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    sc = combined_scenario("BODY_BASED_PHASE36")
    ctxs, _ = build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    engine = ORBCandidateStrategy(proposals=sc.proposals, trade=sc.trade, inner_level_def="NEAREST_FRACTAL_FROM_OPEN_K2")
    summary = json.loads((OUT / "audit_summary.json").read_text())
    journal_dates = {r["date"] for r in read(OUT / "orb_all_manual_journal_dates.csv")}
    dispute_rows = read(OUT / "orb_13_handwritten_disputes.csv")
    hand_dates = {r["date"] for r in dispute_rows}
    frozen = read(ROOT / "reports/phase5/phase55_combined_backtest/all_confirmed_signals.csv")
    differences = [r for r in read(OUT / "orb_candidate_signal_differences.csv") if r["variant"] != "inner_nearest"]
    rationale, authority = VARIANTS["inner_nearest"]
    changed, added, removed, eligible_by_date = set(), 0, 0, {}
    for d, ctx in ctxs.items():
        old = {(r["method"], r["direction"]) for r in frozen if r["config"] == "A" and r["strategy"] == "ORB" and r["date"] == str(d)}
        rows = reconstruct(ctx, sc.proposals, "inner_nearest")
        new = {(r["method"], r["direction"]) for r in rows if r["eligible"]}
        actual = {(r.method, r.direction) for r in engine.evaluate_session(ctx) if r.signal_status == "CONFIRMED"}
        if new != actual:
            raise AssertionError((d, new, actual))
        eligible_by_date[str(d)] = sorted(new)
        for action, items in (("ADDED", new-old), ("REMOVED", old-new)):
            for method, direction in sorted(items):
                added += action == "ADDED"
                removed += action == "REMOVED"
                changed.add(str(d))
                differences.append({"variant": "inner_nearest", "date": str(d), "action": action, "method": method, "direction": direction,
                                    "time": "09:20", "manual_orb_date": str(d) in journal_dates, "handwritten_dispute": str(d) in hand_dates,
                                    "rationale": rationale, "authority": authority, "future_information": False,
                                    "false_positive_assessment": "Not established: no author-drawn exact level; nearest level is an unapproved selection convention"})
    impact = {"variant": "inner_nearest", "added_method_direction_signals": added, "removed_method_direction_signals": removed,
              "changed_unique_dates": len(changed), "changed_handwritten_dates": sorted(changed & hand_dates),
              "changed_manual_orb_dates": sorted(changed & journal_dates), "authority": authority, "rationale": rationale}
    summary["candidate_impact"] = [r for r in summary["candidate_impact"] if r["variant"] != "inner_nearest"] + [impact]
    summary["nearest_inner_independent_parity_sessions"] = len(ctxs)
    (OUT / "audit_summary.json").write_text(json.dumps(summary, indent=2))
    write(OUT / "orb_candidate_signal_differences.csv", differences)
    write(OUT / "orb_candidate_impact.csv", [{**r, "changed_handwritten_dates": json.dumps(r["changed_handwritten_dates"]), "changed_manual_orb_dates": json.dumps(r["changed_manual_orb_dates"])} for r in summary["candidate_impact"]])
    for r in dispute_rows:
        candidates = json.loads(r["candidate_additions"])
        candidates["inner_nearest"] = eligible_by_date[r["date"]]
        r["candidate_additions"] = json.dumps(candidates)
    write(OUT / "orb_13_handwritten_disputes.csv", dispute_rows)
    print(json.dumps(impact, indent=2))


if __name__ == "__main__":
    main()
