"""Phase 2.3: signal-SELECTION diagnostics only (counts). No exit is simulated and no profit is computed.

For each evaluable session the five engines run (PDR/PDS/RF with the per-session cap lifted, because the shared controller - not the engine - decides
how many signals can matter) and the first-trade selection rules are applied to the signals alone: chronological order, entry fillability,
the 13:00 IST cutoff, same-timestamp collisions between strategies. The numbers describe how often an UNRESOLVED rule (the tie-break) would bite;
they are not used to choose anything and are not compared with the performance report.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.core.execution_eligibility import bars_from_frame, entry_within_cutoff  # noqa: E402
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
from nifty_trading.strategies.selection import fill_from_next_bar, is_valid  # noqa: E402

OUT = ROOT / "reports" / "phase23"


def main() -> None:
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    props = replace(DEFAULT_PROPOSALS, max_signals_per_session=99)
    engines = {"IRF": IRFStrategy(proposals=props), "ORB": ORBStrategy(proposals=props), "PDR": PDRStrategy(proposals=props),
               "PDS": PDSStrategy(proposals=props), "RF": RFStrategy(proposals=props)}
    m1 = m1.assign(_d=m1.timestamp.dt.date)
    bars_by_day = {d: bars_from_frame(g) for d, g in m1.groupby("_d")}
    c: Counter = Counter()
    first_by: Counter = Counter()
    collisions: list[dict] = []
    for d, cx in ctxs.items():
        recs = [r for e in engines.values() for r in e.evaluate_session(cx)]
        conf = [r for r in recs if r.signal_status == "CONFIRMED"]
        c["sessions"] += 1
        c["confirmed_signals"] += len(conf)
        valid = []
        for r in conf:
            ok, why = is_valid(r)
            if not ok:
                c["rejected_" + why.split("(")[0][:30]] += 1
                continue
            if not entry_within_cutoff(r.signal_timestamp):
                c["rejected_after_13:00_cutoff"] += 1
                continue
            if fill_from_next_bar(bars_by_day[d], r.signal_timestamp) is None:
                c["rejected_entry_not_fillable"] += 1
                continue
            valid.append(r)
        if not conf:
            c["sessions_without_any_signal"] += 1
        if not valid:
            if conf:
                c["sessions_with_signals_but_none_eligible"] += 1
            continue
        c["sessions_with_an_eligible_first_signal"] += 1
        t0 = min(r.signal_timestamp for r in valid)
        grp = [r for r in valid if r.signal_timestamp == t0]
        first_by[grp[0].strategy if len({r.strategy for r in grp}) == 1 else "COLLISION"] += 1
        if len({r.strategy for r in grp}) > 1 or len({r.direction for r in grp}) > 1:
            collisions.append({"date": str(d), "time": f"{t0:%H:%M}", "signals": sorted(f"{r.strategy}/{r.method}/{r.direction}" for r in grp)})
    result = {"counts": dict(c), "first_eligible_signal_by_strategy": dict(first_by), "first_signal_collisions": collisions,
              "warning": "Selection-level counts only: no exit simulated, no profit computed, nothing tuned or compared with the report."}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "signal_selection_diagnostics.json").write_text(json.dumps(result, indent=2))
    md = ["# Phase 2.3 signal-selection diagnostics (counts only)\n", "> No exit simulated, no profit computed, nothing tuned. Shows how often the unresolved tie-break rule would bite.\n",
          "| item | value |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(c.items())]
    md += ["\n## Which strategy gives the first eligible signal of the session\n", "| strategy | sessions |", "|---|---|"] + [f"| {k} | {v} |" for k, v in sorted(first_by.items())]
    md += [f"\n## Same-timestamp collisions among the FIRST eligible signals ({len(collisions)})\n", "| date | time | signals |", "|---|---|---|"] + [
        f"| {x['date']} | {x['time']} | {', '.join(x['signals'])} |" for x in collisions]
    (OUT / "signal_selection_diagnostics.md").write_text("\n".join(md) + "\n")
    print(json.dumps(result["counts"]), dict(first_by), len(collisions))


if __name__ == "__main__":
    main()
