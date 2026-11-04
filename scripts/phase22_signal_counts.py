"""Phase 2.2: descriptive event COUNTS under the Phase 2.2 defaults and variants, selection-policy counts and zone-method agreement.

No profit is computed or reported. Counts must not be used to choose among interpretations and must not be compared with the performance
report's trade counts to tune anything. Exit simulation is used ONLY to know when a hypothetical position would be closed (for the
ONE_ACTIVE_POSITION_AT_A_TIME count); its P&L is discarded.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
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
from nifty_trading.strategies import (  # noqa: E402
    DEFAULT_PROPOSALS,
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    RFStrategy,
)
from nifty_trading.strategies.definitions import pdr_zone, pds_zone  # noqa: E402
from nifty_trading.strategies.selection import (  # noqa: E402
    SelectionPolicy,
    apply_policy,
    position_end_from_result,
    simulate_exit,
)

OUT = ROOT / "reports" / "phase22"
CLASSES = {"IRF": IRFStrategy, "ORB": ORBStrategy, "PDR": PDRStrategy, "PDS": PDSStrategy, "RF": RFStrategy}
VARIANTS = [
    ("trend_mode=EMA5M_PREV_SESSION (Phase 2.1 default)", ("ORB", "RF"), {"trend_mode": "EMA5M_PREV_SESSION"}),
    ("trend_mode=EMA5M_BASIC", ("ORB", "RF"), {"trend_mode": "EMA5M_BASIC"}),
    ("trend_mode=STRUCTURE with swing_k=1", ("ORB", "RF"), {"swing_k": 1}),
    ("pin_bar=MODERATE (ratio style)", ("ORB", "PDS"), {"pin_bar": "MODERATE"}),
    ("pin_bar=STRICT", ("ORB", "PDS"), {"pin_bar": "STRICT"}),
    ("pin_bar=LOOSE", ("ORB", "PDS"), {"pin_bar": "LOOSE"}),
    ("m3_compression_def=C3 (small candles: body <= 30% of range)", ("IRF",), {"m3_compression_def": "C3"}),
    ("m3_compression_def=C2", ("IRF",), {"m3_compression_def": "C2"}),
    ("irf_support_def=SWING_K2", ("IRF",), {"irf_support_def": "SWING_K2"}),
    ("PDR zone_lower_boundary=ZONE_FULL", ("PDR",), {"zone_lower_boundary": "ZONE_FULL"}),
    ("PDR zone_proximity_points=5 (near-touch)", ("PDR",), {"zone_proximity_points": 5.0}),
    ("PDR pdr_zone_method=B_SWING_HIGH_REVERSAL", ("PDR",), {"pdr_zone_method": "B_SWING_HIGH_REVERSAL"}),
    ("PDR pdr_zone_method=C_REPEATED_TOUCHES", ("PDR",), {"pdr_zone_method": "C_REPEATED_TOUCHES"}),
    ("PDS zone_proximity_points=5 (near-touch)", ("PDS",), {"zone_proximity_points": 5.0}),
    ("PDS pds_zone_upper_boundary=ZONE_WICK", ("PDS",), {"pds_zone_upper_boundary": "ZONE_WICK"}),
    ("PDS pds_zone_method=B_SWING_LOW_REVERSAL", ("PDS",), {"pds_zone_method": "B_SWING_LOW_REVERSAL"}),
    ("PDS pds_zone_method=C_REPEATED_TOUCHES", ("PDS",), {"pds_zone_method": "C_REPEATED_TOUCHES"}),
]


def count(cls, props, ctxs):
    eng = cls(proposals=props)
    c: Counter = Counter()
    for cx in ctxs.values():
        for r in eng.evaluate_session(cx):
            c[f"{r.method}|{r.signal_status}"] += 1
    return dict(sorted(c.items()))


def main() -> None:
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    default = {s: count(c, DEFAULT_PROPOSALS, ctxs) for s, c in CLASSES.items()}
    sens = []
    for label, strategies, over in VARIANTS:
        props = replace(DEFAULT_PROPOSALS, **over)
        for s in strategies:
            base, var = default[s], count(CLASSES[s], props, ctxs)
            keys = sorted(set(base) | set(var))
            sens.append({"variant": label, "strategy": s, "delta_vs_default": {k: [base.get(k, 0), var.get(k, 0)] for k in keys if base.get(k, 0) != var.get(k, 0)}})
    # zone-method agreement (descriptive): how often a method picks a different zone than method A
    zone_diff = {"PDR": Counter(), "PDS": Counter()}
    for cx in ctxs.values():
        if cx.previous is None:
            continue
        a = pdr_zone(cx.previous, replace(DEFAULT_PROPOSALS, pdr_zone_method="A_HIGHEST_HIGH"))  # DIAGNOSTIC reference since Phase 2.3
        for m in ("B_SWING_HIGH_REVERSAL", "C_REPEATED_TOUCHES"):
            z = pdr_zone(cx.previous, replace(DEFAULT_PROPOSALS, pdr_zone_method=m))
            if z is None:
                zone_diff["PDR"][f"{m}: no zone (no setup)"] += 1
            else:
                zone_diff["PDR"][f"{m}: differs from diagnostic highest-high" if (z.low, z.high) != (a.low, a.high) else f"{m}: same as diagnostic highest-high"] += 1
        a = pds_zone(cx.previous, DEFAULT_PROPOSALS)
        for m in ("B_SWING_LOW_REVERSAL", "C_REPEATED_TOUCHES"):
            z = pds_zone(cx.previous, replace(DEFAULT_PROPOSALS, pds_zone_method=m))
            zone_diff["PDS"][f"{m}: differs from A" if (z.low, z.high) != (a.low, a.high) else f"{m}: same as A"] += 1
            zone_diff["PDS"][f"{m}: fell back to A"] += bool(z.fallback)
    # selection policies on the complete IRF event log (and the others), counts only
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    day_bars = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    pol_counts: dict = {}
    blocked = {}
    for s, cls in CLASSES.items():
        recs = [r for cx in ctxs.values() for r in cls().evaluate_session(cx)]
        confirmed = [r for r in recs if r.signal_status == "CONFIRMED"]
        blocked[s] = sum(r.execution_config["execution_status"].startswith("ENTRY_BLOCKED") for r in confirmed)

        def end_of(r, _bars=day_bars):
            return position_end_from_result(simulate_exit(r, _bars[r.signal_date]))

        pol_counts[s] = {
            "all_confirmed_events": len(confirmed),
            SelectionPolicy.ALL_VALID_SIGNALS.value: len(apply_policy(recs, SelectionPolicy.ALL_VALID_SIGNALS).accepted),
            SelectionPolicy.FIRST_VALID_SIGNAL_PER_DAY.value: len(apply_policy(recs, SelectionPolicy.FIRST_VALID_SIGNAL_PER_DAY).accepted),
            SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME.value: len(apply_policy(recs, SelectionPolicy.ONE_ACTIVE_POSITION_AT_A_TIME, end_of).accepted),
            "confirmed_but_entry_blocked_by_closing_auction": blocked[s],
        }
    result = {"sessions_evaluated": len(ctxs), "default_counts": default, "single_parameter_sensitivity_counts_only": sens,
              "zone_method_agreement_across_sessions": {k: dict(v) for k, v in zone_diff.items()},
              "selection_policy_event_counts": pol_counts,
              "warning": "Counts only. Never used to select an interpretation; never compared with the report's trade counts; no P&L computed."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "signal_counts_phase22.json").write_text(json.dumps(result, indent=2))
    md = ["# Phase 2.2 event counts under the Phase 2.2 defaults (descriptive only)\n",
          f"Sessions evaluated: **{len(ctxs)}**. `method|status` -> number of records.\n",
          "> Counts only. Not used to choose among interpretations; not compared with the report's trade counts; no profit computed.\n"]
    for s in CLASSES:
        md += [f"\n## {s}\n", "| method | status | records |", "|---|---|---|"] + [f"| {k.split('|')[0]} | {k.split('|')[1]} | {v} |" for k, v in default[s].items()]
    md += ["\n## Selection-policy event counts (research policies, none approved)\n", "| strategy | confirmed events | ALL_VALID | FIRST_PER_DAY | ONE_ACTIVE | entry blocked by closing auction |", "|---|---|---|---|---|---|"]
    for s, c in pol_counts.items():
        md.append(f"| {s} | {c['all_confirmed_events']} | {c['ALL_VALID_SIGNALS']} | {c['FIRST_VALID_SIGNAL_PER_DAY']} | {c['ONE_ACTIVE_POSITION_AT_A_TIME']} | {c['confirmed_but_entry_blocked_by_closing_auction']} |")
    md += ["\n## Zone-method agreement with method A across sessions\n", "```json", json.dumps({k: dict(v) for k, v in zone_diff.items()}, indent=1), "```",
           "\n## Single-parameter sensitivity (default -> variant; only changed rows)\n", "| variant | strategy | changed rows |", "|---|---|---|"]
    for r in sens:
        md.append(f"| {r['variant']} | {r['strategy']} | " + ("; ".join(f"{k}: {a}→{b}" for k, (a, b) in r["delta_vs_default"].items()) or "no change") + " |")
    (OUT / "signal_counts_phase22.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"default": {s: sum(v for k, v in d.items() if k.endswith("CONFIRMED")) for s, d in default.items()}, "policies": pol_counts}, indent=1))


if __name__ == "__main__":
    main()
