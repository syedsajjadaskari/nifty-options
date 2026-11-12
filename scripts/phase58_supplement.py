"""Decompose ORB shape alternatives and level geometry from frozen evidence CSVs."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
EPS = 1e-9


def rd(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def wr(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def shape_route_quality(checks, method, skip=None):
    flags = {name: name == skip or values[0] for name, values in checks.items()}
    strong = all(flags[k] for k in ("range_positive", "strong_colour", "strong_body_60pct", "strong_opposite_wick_20pct"))
    pin = all(flags[k] for k in ("range_positive", "pin_favourable_wick_positive", "pin_favourable_wick_2xbody", "pin_close_favourable_30pct"))
    return (strong or pin) and (method != "Gap/200DMA" or flags["gap_adverse_rejection_33pct"])


def main():
    paths = rd("orb_method_paths.csv")
    observations = rd("orb_predicate_observations.csv")
    components, levels = [], []
    for d in sorted({r["date"] for r in paths}):
        prev = pd.read_csv(OUT / "daily" / f"{d}_previous_5m.csv")
        today = pd.read_csv(OUT / "daily" / f"{d}_5m.csv")
        prior5 = pd.read_csv(OUT / "daily" / f"{d}_prior5_sessions.csv")
        first = today.iloc[0]
        op, hi, lo, close = (float(first[k]) for k in ("open", "high", "low", "close"))
        span, body = hi - lo, abs(close - op)
        upper, lower = hi - max(op, close), min(op, close) - lo
        for p in [p for p in paths if p["date"] == d]:
            long = p["direction"] == "LONG"
            opposite, favourable = (upper, lower) if long else (lower, upper)
            close_distance = hi - close if long else close - lo
            checks = {
                "range_positive": (span > 0, span, ">0", "all", "definitions.py:85/98"),
                "strong_colour": (close > op if long else close < op, close - op, ">0 LONG / <0 SHORT", "strong", "definitions.py:85/92"),
                "strong_body_60pct": (span > 0 and body/span >= .60-EPS, body/span if span else None, ">=0.60-EPS", "strong", "definitions.py:87"),
                "strong_opposite_wick_20pct": (span > 0 and opposite/span <= .20+EPS, opposite/span if span else None, "<=0.20+EPS", "strong", "definitions.py:88"),
                "pin_favourable_wick_positive": (favourable > EPS, favourable, ">EPS", "pin", "definitions.py:110"),
                "pin_favourable_wick_2xbody": (favourable >= 2*body-EPS, favourable-2*body, ">=-EPS", "pin", "definitions.py:110"),
                "pin_close_favourable_30pct": (close_distance <= .30*span+EPS, close_distance/span if span else None, "<=0.30+EPS in price inequality", "pin", "definitions.py:113"),
                "gap_adverse_rejection_33pct": (span > 0 and opposite/span < .33-EPS, opposite/span if span else None, "not(wick/range>=0.33-EPS)", "gap_only", "definitions.py:147/151"),
            }

            method_obs = [r for r in observations if r["date"] == d and r["direction"] == p["direction"] and r["method"] == p["method"]]
            others_pass = all(r["passed"] == "True" for r in method_obs if r["predicate"] != "quality")
            for key, (passed, observed, threshold, route, code) in checks.items():
                components.append({"date": d, "direction": p["direction"], "method": p["method"], "component": key,
                                   "route": route, "passed": passed, "observed": observed, "threshold": threshold,
                                   "code": "src/nifty_trading/strategies/" + code,
                                   "removal_adds_path": not shape_route_quality(checks, p["method"]) and others_pass and shape_route_quality(checks, p["method"], key),
                                   "authority": "PDF pp.9-10 qualitative, numeric proposal; strong colour explicit pp.3-7; range positivity engineering",
                                   "interpretation": "Strong OR pin. A failed strong component alone does not fail quality if pin passes. Rejection flag is gap-only."})
        inner = [p for p in paths if p["date"] == d and p["method"] == "Method 2"]
        levels.append({"date": d, "previous_wick_high": prev.high.max(), "previous_wick_low": prev.low.min(),
                       "previous_body_high": prev[["open", "close"]].max(axis=1).max(),
                       "previous_body_low": prev[["open", "close"]].min(axis=1).min(),
                       "prior_available_sessions": prior5.session_date.nunique(),
                       "prior_up_to5_wick_high": prior5.high.max(), "prior_up_to5_wick_low": prior5.low.min(),
                       "latest_inner_long": next(p["inner_level"] for p in inner if p["direction"] == "LONG"),
                       "latest_inner_short": next(p["inner_level"] for p in inner if p["direction"] == "SHORT"),
                       "source_status": "Previous extremes source Method1. Body and multi-session extrema are diagnostic context, NOT author-defined zones or signals."})
    wr("orb_shape_components.csv", components)
    wr("orb_level_measurements.csv", levels)
    inventory = [r for r in rd("orb_all_entry_predicates.csv") if r["method"] != "SHAPE_ALTERNATIVE_ROUTE"]
    for component in dict.fromkeys(r["component"] for r in components):
        rows = [r for r in components if r["component"] == component]
        code, line = rows[0]["code"].split(":")
        inventory.append({"method": "SHAPE_ALTERNATIVE_ROUTE", "predicate": component, "path": code, "line": line,
                          "source": "PDF pp.3-7,9-10; exact numerical form absent", "explicit_in_pdf": "QUALITATIVE_ONLY_EXCEPT_DIRECTIONAL_BODY",
                          "author_clarified": "Green-long clarification handwritten p.5; no numeric ORB threshold", "owner_approved": "Repo records owner recommendations as research proposals",
                          "authority": "SOURCE_QUALITATIVE_NUMERIC_PROPOSAL", "engineering_assumption": True,
                          "disputed_dates_failing_either_direction": "Component failures fully enumerated in orb_shape_components.csv; strong OR pin route must be preserved",
                          "single_gate_removal_would_qualify_date_direction": "; ".join(sorted({r["date"]+" "+r["direction"]+" "+r["method"] for r in rows if r["removal_adds_path"]})),
                          "effect": "Remove only this component within its OR route, holding all other predicates; diagnostic, not a correction"})
    wr("orb_all_entry_predicates.csv", inventory)
    disputes = rd("orb_13_handwritten_disputes.csv")
    lines = ["# Thirteen handwritten disputes: both directions retained", "", "All thirteen have no frozen ORB signal. Every method/direction failure below is measured independently; no fewest-failures attribution or author direction is inferred. See daily reports for full candles, source authorities and exact levels.", "", "| Date | Page | Opening O/H/L/C | Body % | LONG M1 / M2 / Gap failures | SHORT M1 / M2 / Gap failures | Candidate eligibility |", "|---|---|---|---|---|---|---|"]
    for r in disputes:
        if r["config"] != "A":
            continue
        ps = [p for p in paths if p["date"] == r["date"]]
        long_fail = " / ".join(", ".join(json.loads(p["failed"])) or "PASS" for p in ps if p["direction"] == "LONG")
        short_fail = " / ".join(", ".join(json.loads(p["failed"])) or "PASS" for p in ps if p["direction"] == "SHORT")
        cand = {k:v for k,v in json.loads(r["candidate_additions"]).items() if v}
        lines.append(f"| [{r['date']}](daily/{r['date']}.md) | {r['pdf_page']} | {r['open']} / {r['high']} / {r['low']} / {r['close']} | {float(r['body_pct']):.2f} | {long_fail} | {short_fail} | {cand or 'None among isolated candidates'} |")
    (OUT / "orb_13_disputes_readable.md").write_text("\n".join(lines)+"\n")
    print(f"Decomposed {len(components)} shape components; measured {len(levels)} days")


if __name__ == "__main__":
    main()
