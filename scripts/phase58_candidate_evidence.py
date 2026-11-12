"""Attach exact changed levels and all gate evidence to candidate differences."""

from __future__ import annotations

import csv
import json
import sys
from datetime import date
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
from nifty_trading.research.phase58 import reconstruct  # noqa: E402


def main():
    contexts, _ = build_session_contexts(load_one_minute(), daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    p = combined_scenario("BODY_BASED_PHASE36").proposals
    file = OUT / "orb_candidate_signal_differences.csv"
    with open(file, newline="") as f:
        rows = list(csv.DictReader(f))
    cache = {}
    for r in rows:
        ctx = contexts[date.fromisoformat(r["date"])]
        for variant in ("frozen", r["variant"]):
            key = (r["date"], variant)
            if key not in cache:
                cache[key] = reconstruct(ctx, p, variant)
        old = next(x for x in cache[r["date"], "frozen"] if x["method"] == r["method"] and x["direction"] == r["direction"])
        new = next(x for x in cache[r["date"], r["variant"]] if x["method"] == r["method"] and x["direction"] == r["direction"])
        r.update({"reference_level": old["level"], "candidate_level": new["level"],
                  "reference_trendline_at_open": old["trendline"], "candidate_trendline_at_open": new["trendline"],
                  "reference_signed_close_distance": old["signed_breakout_distance"],
                  "candidate_signed_close_distance": new["signed_breakout_distance"],
                  "reference_failed_gates": json.dumps(old["failed"]), "candidate_failed_gates": json.dumps(new["failed"]),
                  "reference_eligible": old["eligible"], "candidate_eligible": new["eligible"],
                  "candidate_gate_evidence": json.dumps(new["gates"]),
                  "first_candle_geometry": json.dumps(new["geometry"]),
                  "author_exact_level": "UNKNOWN"})
        assert (r["action"] == "ADDED" and not old["eligible"] and new["eligible"]) or (r["action"] == "REMOVED" and old["eligible"] and not new["eligible"])
    with open(file, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Enriched {len(rows)} isolated signal differences with causal levels and all gates")


if __name__ == "__main__":
    main()
