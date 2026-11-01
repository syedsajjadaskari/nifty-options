"""Descriptive signal COUNTS per method and per candidate interpretation (no P&L, no selection).

Purpose: fill the 'effect on trade frequency' column of ambiguous_rules.md. Counts of emitted records
say nothing about profitability and must not be used to choose among candidates (Phase 2 forbids it).
They must also not be compared with the report's 189 trades to tune thresholds.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.sessions import build_session_contexts, load_one_minute  # noqa: E402
from nifty_trading.strategies import (  # noqa: E402
    DEFAULT_PROPOSALS,
    IRFStrategy,
    ORBStrategy,
    PDRStrategy,
    PDSStrategy,
    RFStrategy,
)

OUT = ROOT / "reports" / "phase2"

# (label, strategy class, field overrides) -- every row changes ONE interpretation, everything else default
VARIANTS = [
    ("DEFAULT", None, {}),
    ("IRF m1_max_candles_after_breakout=2 (p.14 'or following candle')", IRFStrategy, {"m1_max_candles_after_breakout": 2}),
    ("IRF m1_close_below_irl_counts_as_inside=True", IRFStrategy, {"m1_close_below_irl_counts_as_inside": True}),
    ("IRF m2_extension_definition=E2", IRFStrategy, {"m2_extension_definition": "E2"}),
    ("IRF m2a_break_may_be_red_candle=True", IRFStrategy, {"m2a_break_may_be_red_candle": True}),
    ("IRF m2_red_may_be_extension_candle=True", IRFStrategy, {"m2_red_may_be_extension_candle": True}),
    ("IRF irf_support_def=SWING_K2", IRFStrategy, {"irf_support_def": "SWING_K2"}),
    ("IRF irf_support_def=LAST_N3", IRFStrategy, {"irf_support_def": "LAST_N3"}),
    ("IRF irf_resistance_def=LATEST_SWING_HIGH", IRFStrategy, {"irf_resistance_def": "LATEST_SWING_HIGH"}),
    ("IRF m2_expiry_candles=6 (30 min)", IRFStrategy, {"m2_expiry_candles": 6}),
    ("IRF m3_wick_share_band=MIN_60", IRFStrategy, {"m3_wick_share_band": "MIN_60"}),
    ("IRF m3_wick_share_band=BAND_55_75", IRFStrategy, {"m3_wick_share_band": "BAND_55_75"}),
    ("IRF m3_compression_n=3", IRFStrategy, {"m3_compression_n": 3}),
    ("IRF m3_compression_def=C2", IRFStrategy, {"m3_compression_def": "C2"}),
    ("ORB strong_candle=STRICT", ORBStrategy, {"strong_candle": "STRICT"}),
    ("ORB strong_candle=LOOSE", ORBStrategy, {"strong_candle": "LOOSE"}),
    ("ORB trend_mode=EMA5M_BASIC", ORBStrategy, {"trend_mode": "EMA5M_BASIC"}),
    ("ORB trend_mode=EMA5M_PREV_3_SESSIONS", ORBStrategy, {"trend_mode": "EMA5M_PREV_3_SESSIONS"}),
    ("ORB trend_mode=SMA200_DAILY (47 evaluable sessions)", ORBStrategy, {"trend_mode": "SMA200_DAILY"}),
    ("ORB ma_mode=SMA200_DAILY for the gap setup", ORBStrategy, {"ma_mode": "SMA200_DAILY"}),
    ("ORB gap_max_points=150", ORBStrategy, {"gap_max_points": 150.0}),
    ("PDR zone_lower_boundary=ZONE_WICK", PDRStrategy, {"zone_lower_boundary": "ZONE_WICK"}),
    ("PDR zone_proximity_points=0", PDRStrategy, {"zone_proximity_points": 0.0}),
    ("PDR zone_proximity_points=10", PDRStrategy, {"zone_proximity_points": 10.0}),
    ("PDR pdr_green_may_be_interaction_candle=True", PDRStrategy, {"pdr_green_may_be_interaction_candle": True}),
    ("PDR require_open_clear_of_zone=False", PDRStrategy, {"require_open_clear_of_zone": False}),
    ("PDR pdr_reversal_filter=DEPTH_25PCT", PDRStrategy, {"pdr_reversal_filter": "DEPTH_25PCT"}),
    ("PDS strong_candle=STRICT", PDSStrategy, {"strong_candle": "STRICT"}),
    ("PDS strong_candle=LOOSE", PDSStrategy, {"strong_candle": "LOOSE"}),
    ("PDS zone_proximity_points=0", PDSStrategy, {"zone_proximity_points": 0.0}),
    ("PDS zone_proximity_points=10", PDSStrategy, {"zone_proximity_points": 10.0}),
    ("PDS pds_m3_break_basis=TOUCH", PDSStrategy, {"pds_m3_break_basis": "TOUCH"}),
    ("PDS pds_m3_standalone=True", PDSStrategy, {"pds_m3_standalone": True}),
    ("PDS require_open_clear_of_zone=False", PDSStrategy, {"require_open_clear_of_zone": False}),
    ("RF rf_return_inside_def=R2", RFStrategy, {"rf_return_inside_def": "R2"}),
    ("RF rf_return_inside_def=R3", RFStrategy, {"rf_return_inside_def": "R3"}),
    ("RF trend_mode=EMA5M_BASIC", RFStrategy, {"trend_mode": "EMA5M_BASIC"}),
    ("RF trend_mode=EMA5M_PREV_3_SESSIONS", RFStrategy, {"trend_mode": "EMA5M_PREV_3_SESSIONS"}),
]
CLASSES = {"IRF": IRFStrategy, "ORB": ORBStrategy, "PDR": PDRStrategy, "PDS": PDSStrategy, "RF": RFStrategy}


def count(cls, props, ctxs):
    eng = cls(proposals=props)
    c: Counter = Counter()
    for cx in ctxs.values():
        for r in eng.evaluate_session(cx):
            c[f"{r.method}|{r.signal_status}"] += 1
    return dict(sorted(c.items()))


def main() -> None:
    ctxs, infos = build_session_contexts(load_one_minute())
    default = {s: count(c, DEFAULT_PROPOSALS, ctxs) for s, c in CLASSES.items()}
    ver: dict = {}
    for s, cls in CLASSES.items():
        eng = cls()
        v: Counter = Counter()
        for cx in ctxs.values():
            for r in eng.evaluate_session(cx):
                if r.signal_status == "CONFIRMED":
                    v[f"{r.method}|{r.verification_status}"] += 1
        ver[s] = dict(sorted(v.items()))
    sens = []
    for label, cls, over in VARIANTS[1:]:
        props = replace(DEFAULT_PROPOSALS, **over)
        name = cls.STRATEGY
        base = default[name]
        var = count(cls, props, ctxs)
        keys = sorted(set(base) | set(var))
        sens.append({"variant": label, "strategy": name,
                     "delta_vs_default": {k: [base.get(k, 0), var.get(k, 0)] for k in keys if base.get(k, 0) != var.get(k, 0)}})
    result = {"sessions_evaluated": len(ctxs), "default_counts": default, "default_confirmed_by_verification_status": ver,
              "single_parameter_sensitivity_counts_only": sens,
              "warning": "Counts only. Never used to select an interpretation and never compared to the 189-trade report."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "signal_counts_default.json").write_text(json.dumps(result, indent=2))
    md = ["# Signal counts under the default proposals (descriptive only)\n",
          f"Sessions evaluated: **{len(ctxs)}** usable of {len(infos)}. `method|status` -> number of records.\n",
          "> Counts only. They are **not** used to choose among interpretations and must **not** be compared with the performance report's 189 trades to tune anything.\n"]
    for s in CLASSES:
        md += [f"\n## {s}\n", "| method | status | records |", "|---|---|---|"]
        md += [f"| {k.split('|')[0]} | {k.split('|')[1]} | {v} |" for k, v in default[s].items()]
        md += ["", "Confirmed signals by verification status: " + (", ".join(f"{k}={v}" for k, v in ver[s].items()) or "none")]
    md += ["\n## Single-parameter sensitivity (records: default -> variant; only changed rows)\n", "| variant | changed `method|status` : default -> variant |", "|---|---|"]
    for r in sens:
        md.append(f"| {r['variant']} | " + ("; ".join(f"{k}: {a}→{b}" for k, (a, b) in r["delta_vs_default"].items()) or "no change") + " |")
    (OUT / "signal_counts_default.md").write_text("\n".join(md) + "\n")
    print(json.dumps(default["IRF"], indent=1))


if __name__ == "__main__":
    main()
