"""Measure first IRF candles and causally known lows; never add an IRF veto."""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase58_codex_orb_forensic_audit"
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research.phase58 import geometry  # noqa: E402


def main():
    path = OUT / "orb_vs_irf_selection_timeline.csv"
    with open(path, newline="") as f:
        timeline = list(csv.DictReader(f))
    first_candles = []
    cache = {}
    for row in timeline:
        d, end = row["date"], row["irf_first_signal_time"]
        row.update({"irf_first_candle_geometry": "", "known_low_before_irf_trigger_candle": "", "known_low_at_irf_confirmation": "", "irf_close_minus_pretrigger_low": ""})
        if not end:
            continue
        if d not in cache:
            cache[d] = (pd.read_csv(OUT / "daily" / f"{d}_5m.csv"), pd.read_csv(OUT / "daily" / f"{d}_1m.csv"))
        five, minute = cache[d]
        trigger = five[five.bar_end.str.slice(11, 16) == end].iloc[0]
        g = geometry(trigger)
        before = minute[minute.timestamp.str.slice(11, 16) < trigger.bar_start[11:16]]
        through = minute[minute.timestamp.str.slice(11, 16) < end]
        low_before = float(before.low.min()) if len(before) else None
        low_through = float(through.low.min())
        row.update({"irf_first_candle_geometry": json.dumps(g), "known_low_before_irf_trigger_candle": low_before,
                    "known_low_at_irf_confirmation": low_through,
                    "irf_close_minus_pretrigger_low": g["close"] - low_before if low_before is not None else None})
        first_candles.append({"config": row["config"], "date": d, "manual_orb_date": row["manual_orb_date"], "handwritten_dispute": row["handwritten_dispute"],
                              "irf_executed": row["irf_executed"], "irf_method": row["irf_first_signal_method"], "signal_time": end,
                              **g, "running_low_before_trigger": low_before, "running_low_at_confirmation": low_through,
                              "close_at_or_below_pretrigger_low": low_before is not None and g["close"] <= low_before,
                              "interpretation": "Context only. Author did not specify reference low/tolerance, so no day-low filter is invented."})
    for file, rows in ((path, timeline), (OUT / "irf_first_signal_context.csv", first_candles)):
        with open(file, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
    counts = []
    for cfg in "ABC":
        rows = [r for r in first_candles if r["config"] == cfg and r["manual_orb_date"] == "True" and r["irf_executed"] == "True"]
        counts.append({"config": cfg, "journal_orb_irf_execution_dates": len(rows),
                       "first_irf_body_below60pct": sum(r["body_pct"] < 60 for r in rows),
                       "first_irf_close_at_or_below_pretrigger_low": sum(r["close_at_or_below_pretrigger_low"] for r in rows)})
    text = ["# IRF selection context: author rejection rules are not assumed", "", "ORB absence does not prove that the later IRF conforms to every handwritten intention. The frozen/Phase53 IRF engines have their own failure-pattern gates; they do not use ORB's universal strong-body filter.", "",
            "Handwritten p.1 (20250901-1) says '60+ body candle in the entry side'; p.2 (20250917-1) rejects a40%-body/60%-wick IRF candle; p.5 (20251211) rejects a body below50%. Percent interpretation and universal method scope are not fully defined by the first phrase. No universal60%-body veto is present in baseline or Phase53 IRF. These notes are separate from ORB shape rules and must not be silently transferred between strategies.", "",
            "Handwritten p.4 (20251112-1) and p.5 (20251211) reject IRF at the day's low. Both reference engines omit that veto. The author did not define which low, distance or timing. The CSV measures running lows strictly before the trigger candle and through its completed close; no later low is consulted. Equality/below comparisons are context, not an invented rejection rule.", "",
            "| Config | Journal-ORB dates executing IRF | First IRF body below60% (diagnostic only) | First IRF close <= known low before trigger (diagnostic only) |", "|---|---|---|---|"]
    text += [f"| {r['config']} | {r['journal_orb_irf_execution_dates']} | {r['first_irf_body_below60pct']} | {r['first_irf_close_at_or_below_pretrigger_low']} |" for r in counts]
    text += ["", "Every exact signal candle and known-low value is in `irf_first_signal_context.csv` and the extended selection timeline. No IRF change or counterfactual rejection/backtest was run. A source-complete IRF fidelity audit would require resolving the method scope, percentages and reference-low definition; this ORB audit stops at documenting the absent gates and actual selection evidence."]
    (OUT / "irf_rejection_context.md").write_text("\n".join(text)+"\n")
    print(json.dumps(counts, indent=2))


if __name__ == "__main__":
    main()
