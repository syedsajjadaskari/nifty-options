"""Phase 3.1: funnels and descriptive tables used by root_cause_analysis.md. READ-ONLY; counts only, no profit."""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

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

BASE = ROOT / "reports" / "phase3" / "phase31"


def main() -> None:
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1d = m1.assign(_d=m1.timestamp.dt.date)
    bars = {d: bars_from_frame(g) for d, g in m1d.groupby("_d")}
    sc = P.scenarios()["baseline"]
    tl = R.run_timelines(sc, ctxs, bars)
    mj = pd.read_csv(BASE / "manual_journal_normalized.csv").fillna("")
    mv = pd.read_csv(BASE / "manual_vs_automated.csv")
    out: dict = {}
    # ---------------------------------------------------------------- funnel by strategy: probe code per session, all sessions and manual-trade sessions
    manual_days = {s: set(mj[mj.strategy_normalized == s].date) for s in P.STRATEGIES}
    for s in ("ORB", "PDR", "PDS", "RF", "IRF"):
        allc, manc = Counter(), Counter()
        for d, t in tl.items():
            code = R.probe(s, t, sc.proposals).get("code", "?")
            allc[code] += 1
            if str(d) in manual_days[s]:
                manc[code] += 1
        out[f"probe_{s}"] = {"all_sessions": dict(allc), "sessions_with_a_manual_trade_of_this_strategy": dict(manc)}
    # ---------------------------------------------------------------- raw record statuses per strategy/method
    st = Counter()
    for t in tl.values():
        for r in t.records:
            st[(r.strategy, r.method, r.signal_status)] += 1
    out["record_status_counts"] = {f"{a}|{b}|{c}": n for (a, b, c), n in sorted(st.items())}
    why = Counter()
    for t in tl.values():
        for r in t.records:
            if r.signal_status in ("INVALIDATED", "INCOMPLETE_AT_EOD", "NOT_EVALUATED"):
                why[(r.strategy, r.method, (r.invalidation_reason or "")[:60])] += 1
    out["setup_failure_reasons"] = {f"{a}|{b}|{c}": n for (a, b, c), n in sorted(why.items(), key=lambda kv: -kv[1])}
    # ---------------------------------------------------------------- IRF: manual IRF vs raw IRF signals
    irf_rows = []
    for m in mj[mj.strategy_normalized == "IRF"].itertuples():
        d = date.fromisoformat(m.date)
        if d not in tl:
            continue
        raw = sorted([r for r in tl[d].records if r.strategy == "IRF" and r.signal_status == "CONFIRMED"], key=lambda r: r.signal_candle_start)
        lab = R._minutes(m.entry_time_label)
        if not raw:
            irf_rows.append({"rank": 0, "method": "", "delta": None, "n_raw": 0})
            continue
        best = min(range(len(raw)), key=lambda i: abs(R._cstart(raw[i]) - lab))
        irf_rows.append({"rank": best + 1, "method": raw[best].method, "delta": R._cstart(raw[best]) - lab, "n_raw": len(raw)})
    df = pd.DataFrame(irf_rows)
    out["irf_manual_vs_raw"] = {"manual_irf_rows_evaluated": len(df), "no_raw_irf_signal_that_day": int((df["n_raw"] == 0).sum()),
                                "nearest_raw_signal_rank_counts": df[df.n_raw > 0]["rank"].value_counts().sort_index().to_dict(),
                                "nearest_within_0min": int((df.delta == 0).sum()), "nearest_within_15min": int((df.delta.abs() <= 15).sum()),
                                "median_raw_irf_signals_on_those_days": float(df[df.n_raw > 0].n_raw.median())}
    raw_per_day = Counter()
    for t in tl.values():
        raw_per_day[sum(1 for r in t.records if r.strategy == "IRF" and r.signal_status == "CONFIRMED")] += 1
    out["irf_raw_signals_per_session_histogram"] = dict(sorted(raw_per_day.items()))
    out["irf_raw_signals_by_hour"] = dict(sorted(Counter(f"{r.signal_timestamp:%H}" for t in tl.values() for r in t.records if r.strategy == "IRF" and r.signal_status == "CONFIRMED").items()))
    out["manual_entries_by_hour"] = {s: dict(sorted(Counter(h[:2] for h in mj[mj.strategy_normalized == s].entry_time_label).items())) for s in P.STRATEGIES}
    # ---------------------------------------------------------------- PDR funnel (baseline reversal-swing zone and shelf zone)
    fun = {}
    for name, sc2 in (("B_SWING_HIGH_REVERSAL", sc), ("C_REPEATED_TOUCHES", P.scenarios()["pdr_shelf"])):
        t2 = R.run_timelines(sc2, ctxs, bars) if name != "B_SWING_HIGH_REVERSAL" else tl
        c = Counter()
        for t in t2.values():
            recs = [r for r in t.records if r.strategy == "PDR"]
            if not recs:
                c["no PDR record (no gap up or session not evaluable)"] += 1
                continue
            c["sessions with a PDR record (gap up)"] += 1
            for r in recs:
                c[f"record: {r.signal_status} {(r.invalidation_reason or '')[:45]}"] += 1
        fun[name] = dict(c)
    out["pdr_funnel"] = fun
    out["pdr_manual_rows"] = mv[mv.strategy_normalized == "PDR"][["journal_row", "date", "entry_time_label", "classification", "detail"]].to_dict("records")
    # ---------------------------------------------------------------- day-level agreement: first manual trade vs first automated trade
    day_cmp = Counter()
    for d, t in tl.items():
        mt = mj[(mj.date == str(d))]
        a = t.result.trades
        if mt.empty and not a:
            day_cmp["neither traded"] += 1
        elif mt.empty:
            day_cmp["automated traded, manual did not"] += 1
        elif not a:
            day_cmp["manual traded, automated did not"] += 1
        else:
            m0 = mt.sort_values("entry_time_label").iloc[0]
            same = m0.strategy_normalized == a[0].signal.strategy
            day_cmp["both traded, same first strategy" if same else "both traded, different first strategy"] += 1
    out["day_level_agreement"] = dict(day_cmp)
    out["manual_trading_days_in_vendor_sessions"] = int(len({d for d in mj.date if date.fromisoformat(d) in tl}))
    (BASE / "analysis_tables.json").write_text(json.dumps(out, indent=2, default=str))
    print(json.dumps({k: out[k] for k in ("irf_manual_vs_raw", "day_level_agreement")}, default=str))


if __name__ == "__main__":
    main()
