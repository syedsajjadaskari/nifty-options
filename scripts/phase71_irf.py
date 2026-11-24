"""Phase 7.1 priorities 1-3: Method 2 Level-A invalidation, the Method 2 timing / close-margin audit, the November-2026 data store and the reconstruction of every dated rulebook example.
Reads the Phase 7.0 package (unchanged) and the NEW November retrieval; writes only into reports/phase7/phase71_global_ema_and_final_validation/ and data/phase71/."""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from nifty_trading.research.irf_v3 import data_access as DA  # noqa: E402
from nifty_trading.research.irf_v3 import examples as EXM  # noqa: E402
from nifty_trading.research.irf_v3 import recon as RC  # noqa: E402
from nifty_trading.research.irf_v3 import reporting as RP  # noqa: E402
from nifty_trading.research.irf_v3.config import SCENARIOS  # noqa: E402
from nifty_trading.research.irf_v3.models import M1, M2  # noqa: E402
from nifty_trading.research.irf_v3.signal_engine import evaluate_session  # noqa: E402
from nifty_trading.research.phase71 import irf_standalone as ST  # noqa: E402
from nifty_trading.research.phase71 import nov2026 as NV  # noqa: E402
from nifty_trading.research.phase71.irf_cycles import M2Opts, m2_cycles  # noqa: E402

OUT = ROOT / "reports/phase7/phase71_global_ema_and_final_validation"
SRC = ROOT / "reports/phase7/phase70_complete_irf_rebuild/source_extracts"
VARIANTS = {
    "M2-A (persistent; Phase 7.0 headline)": M2Opts(),
    "M2-B0 (Phase 7.0 sensitivity: close below A before Level B is marked; permanent)": M2Opts("BEFORE_B"),
    "M2-B (close below A before the sequence completes; permanent)": M2Opts("BEFORE_COMPLETION"),
    "M2-B-REARM (same, a new rally breakout may start a new setup)": M2Opts("BEFORE_COMPLETION", rearm=True),
    "CAND margin>=1pt below B": M2Opts(min_margin=1.0),
    "CAND margin>=2pt below B": M2Opts(min_margin=2.0),
    "CAND margin>=5pt below B": M2Opts(min_margin=5.0),
    "CAND failure candle must be red": M2Opts(bearish_failure=True),
    "CAND extra confirming candle below B": M2Opts(extra_confirmation=True),
}


def w(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False)


def invalidation_detail(ds) -> list[dict]:
    rows = []
    for d, s in ds.sessions.items():
        if not s.evaluable:
            continue
        cs = s.candles
        A = cs[0].high
        base = m2_cycles(cs)
        bfull = m2_cycles(cs, M2Opts("BEFORE_COMPLETION"))
        brear = m2_cycles(cs, M2Opts("BEFORE_COMPLETION", rearm=True))
        brk = next((i for i in range(1, len(cs)) if cs[i].close > A), None)
        red = next((i for i in range(brk + 1, len(cs)) if cs[i].close < cs[i].open), None) if brk is not None else None
        end = base[0]["fail_idx"] if base else len(cs)
        lost = brk is not None and any(cs[i].close < A for i in range(brk + 1, end))
        def t(c, cs=cs):
            return f"{cs[c[0]['fail_idx']].end:%H:%M}" if c else ""

        rows.append({"window": ds.window, "date": str(d), "level_a": A, "m2_rally_breakout": brk is not None, "m2_first_red_marked": red is not None,
                     "first_red_candle_closed_below_A": bool(red is not None and cs[red].close < A), "level_a_lost_before_m2_entry": bool(lost),
                     "M2A_signal": t(base), "M2B_signal": t(bfull), "M2B_REARM_signal": t(brear),
                     "effect_M2B": ("UNCHANGED" if t(base) == t(bfull) else "REMOVED" if base and not bfull else "ADDED" if bfull and not base else "TIME_CHANGED"),
                     "effect_M2B_REARM": ("UNCHANGED" if t(base) == t(brear) else "REMOVED" if base and not brear else "ADDED" if brear and not base else "TIME_CHANGED")})
    return rows


def variant_table(ds_by_w: dict, jrows) -> pd.DataFrame:
    out = []
    for wn, ds in ds_by_w.items():
        nsess = sum(1 for s in ds.sessions.values() if s.evaluable)
        for sc in ("SL40_T60", "SL35_T60"):
            for name, o in VARIANTS.items():
                r = ST.standalone(ds, o, sc)
                m = ST.summarize(r["books"], nsess)
                row_base = {"window": wn, "scenario": sc, "variant": name}
                for book in ("M1", "M2", "COMBINED"):
                    mm = m[book]
                    row = {**row_base, "book": book, "trades": mm["executed_trades"], "win_rate_pct": mm["win_rate_pct"], "profit_factor": mm["profit_factor"], "gross_points": mm["gross_points"], "max_dd_points": mm["max_drawdown_points"]}
                    if wn == "A" and sc == "SL40_T60":
                        auto = [{"date": x["date"], "candle_start": x["signal_candle_start"]} for x in r["books"][book]]
                        mt = RC.stage_match([j for j in jrows if j["strategy"] == "IRF"], auto)
                        from collections import Counter
                        c = Counter(v[0] for v in mt.values())
                        row.update({"journal_strict": c.get("STRICT", 0), "journal_time_tolerant": c.get("TIME_TOLERANT", 0), "journal_date_only": c.get("DATE_STRATEGY_ONLY", 0)})
                    out.append(row)
    return pd.DataFrame(out)


def nov_examples() -> list[dict]:
    info = NV.build()
    days = [date(2026, 11, d) for d in (3, 6, 11, 12, 16)]
    frames = NV.session_frames(days)
    tv = DA.load_vendor_days([date(2026, 11, 3)])
    rows = []
    cfg40, cfg35 = SCENARIOS["SL40_T60"], SCENARIOS["SL35_T60"]
    for ex in EXM.EXAMPLES:
        if ex["date"] is None or ex["kind"] != "SCREENSHOT":
            continue
        feeds = {"5P_NOV2026": DA.Session(ex["date"], True, "", frames[ex["date"]], DA.aggregate_candles(frames[ex["date"]]), ())} if ex["date"] in frames else {}
        if ex["date"] in tv and tv[ex["date"]].evaluable:
            feeds["TV_SECONDARY"] = tv[ex["date"]]
        for feed, s in feeds.items():
            m = M1 if ex["method"] == "M1" else M2
            e40, e35 = evaluate_session(s, cfg40, None), evaluate_session(s, cfg35, None)
            tr = e40.traces[m]
            f = s.candles[0]
            row = {"example": ex["id"], "method": ex["method"], "date": str(ex["date"]), "feed": feed, "pdf_page": ex["page"], "stated_level_A": ex["A"], "replay_level_A": f.high, "A_diff": round(f.high - ex["A"], 2),
                   "stated_level_B": ex["B"] or "", "stated_entry": ex["entry"], "stated_outcome": ex["outcome"], "stated_stop": ex["stop"], "stated_target": ex["target"] or ""}
            if tr.status == "SIGNAL":
                r40, r35 = e40.trades[m], e35.trades[m]
                row.update({"replay_signal": "SIGNAL", "replay_level_B": tr.reference_level if m == M2 else "", "B_diff": round(tr.reference_level - ex["B"], 2) if (m == M2 and ex["B"]) else "",
                            "failure_candle": f"{tr.confirmation_candle.start:%H:%M}-{tr.confirmation_candle.end:%H:%M}", "failure_close": tr.confirmation_candle.close, "failure_close_minus_stated_entry": round(tr.confirmation_candle.close - ex["entry"], 2),
                            "fill_next_open": r40.get("entry_price"), "SL40_exit": f"{r40.get('exit_reason')} {r40.get('gross_points')} @ {r40.get('exit_time'):%H:%M}" if r40.get("exit_time") is not None else "",
                            "SL35_exit": f"{r35.get('exit_reason')} {r35.get('gross_points')}" if r35.get("exit_time") is not None else ""})
                ok_seq = abs(tr.confirmation_candle.close - ex["entry"]) <= 2.0
                want_tp = "Target" in ex["outcome"]
                got = r40.get("exit_reason")
                row["sequence_reproduced(entry within 2pt)"] = ok_seq
                row["outcome_agrees(SL40)"] = (got == "TARGET") if want_tp else (got == "STOP")
                row["level_A_within_1pt"] = abs(f.high - ex["A"]) <= 1.0
                row["level_B_within_3pt"] = (abs(tr.reference_level - ex["B"]) <= 3.0) if (m == M2 and ex["B"]) else ""
            else:
                row.update({"replay_signal": f"NO_SIGNAL ({tr.no_signal_reason})"})
            row["_ev"], row["_sess"] = e40, s
            rows.append(row)
    return rows, info


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    jrows, sha, nrows = RC.load_journal()
    ds_by_w = {x: DA.load_dataset(x) for x in "AB"}
    # ---- priority 1
    det = []
    for ds in ds_by_w.values():
        det += invalidation_detail(ds)
    ddf = pd.DataFrame(det)
    w(ddf, "irf_method2_level_a_invalidation.csv")
    vt = variant_table(ds_by_w, jrows)
    w(vt, "irf_method_comparison.csv")
    summ = {}
    for wn in "AB":
        g = ddf[ddf.window == wn]
        summ[wn] = {"sessions": len(g), "m2_rally_breakout": int(g.m2_rally_breakout.sum()), "first_red_marked": int(g.m2_first_red_marked.sum()), "first_red_closed_below_A": int(g.first_red_candle_closed_below_A.sum()),
                    "level_A_lost_before_m2_entry": int(g.level_a_lost_before_m2_entry.sum()), "M2A_signals": int((g.M2A_signal != "").sum()), "M2B_signals": int((g.M2B_signal != "").sum()), "M2B_REARM_signals": int((g.M2B_REARM_signal != "").sum()),
                    "M2B_effects": g.effect_M2B.value_counts().to_dict(), "M2B_REARM_effects": g.effect_M2B_REARM.value_counts().to_dict()}
    # ---- priority 2 + 3: November examples
    rows, info = nov_examples()
    ex_df = pd.DataFrame([{k: v for k, v in r.items() if not k.startswith("_")} for r in rows])
    w(ex_df, "november_2026_example_results.csv")
    (OUT / "_state" / "nov_store_manifest.json").write_text(json.dumps(info, indent=1))
    q = pd.read_csv(NV.PROC / "quality_report.csv")
    w(q, "november_2026_data_quality.csv")
    # charts (side by side with the original screenshot at its extracted resolution)
    for r in rows:
        ex = next(x for x in EXM.EXAMPLES if x["id"] == r["example"])
        png = str(SRC / ex["img"])
        ev = r["_ev"]
        m = M1 if ex["method"] == "M1" else M2
        lines = [f"Source: {ex['pdf']} p{ex['page']} - stated {ex['date']}: level A {ex['A']}" + (f", B {ex['B']}" if ex["B"] else "") + f", entry {ex['entry']}, stop {ex['stop']}, target {ex['target']}, outcome: {ex['outcome']}",
                 f"Replay feed {r['feed']}: A {r['replay_level_A']:.2f} ({r['A_diff']:+.2f}); signal: {r['replay_signal']}" + (f"; failure candle {r.get('failure_candle')} close {r.get('failure_close')} (stated entry {ex['entry']}, diff {r.get('failure_close_minus_stated_entry'):+}); SL40 -> {r.get('SL40_exit')}; SL35 -> {r.get('SL35_exit')}" if r["replay_signal"] == "SIGNAL" else "")]
        svg = RP.trace_chart(ev, SCENARIOS["SL40_T60"], [m], f"{ex['id']} {ex['date']} - {r['feed']}", lines[0][:150], embed_png=png, extra=lines[1:])
        (OUT / "charts" / f"EX_{ex['id']}_{ex['date']}_{r['feed']}.svg").write_text(svg)
    # ---- Nov 3 raw rows (timing audit)
    d3 = date(2026, 11, 3)
    fr = NV.session_frames([d3])[d3]
    tvs = DA.load_vendor_days([d3])[d3].minutes
    tvs = tvs.assign(ts=tvs["timestamp"].dt.tz_localize(None)) if "timestamp" in tvs and "ts" not in tvs else tvs
    raw = []
    for tag, g in (("5P_NOV2026", fr), ("TV_SECONDARY", tvs)):
        gg = g[(g["ts"].dt.strftime("%H:%M") >= "09:55") & (g["ts"].dt.strftime("%H:%M") <= "10:14")]
        for r in gg.itertuples():
            raw.append({"feed": tag, "minute_label": f"{r.ts:%H:%M}", "open": r.open, "high": r.high, "low": r.low, "close": r.close})
    w(pd.DataFrame(raw), "november_3_raw_one_minute_rows.csv")
    for tag, g in (("5P_NOV2026", fr), ("TV_SECONDARY", tvs)):
        s = DA.Session(d3, True, "", g, DA.aggregate_candles(g), ())
        cs = s.candles
        res = {}
        for name, o in (("strict close below B (rule as written)", M2Opts()), ("margin >=1pt", M2Opts(min_margin=1.0)), ("margin >=2pt", M2Opts(min_margin=2.0)), ("margin >=5pt", M2Opts(min_margin=5.0)),
                        ("failure candle must be red", M2Opts(bearish_failure=True)), ("extra confirming candle", M2Opts(extra_confirmation=True))):
            c = m2_cycles(cs, o)
            res[name] = f"{cs[c[0]['fail_idx']].start:%H:%M}-{cs[c[0]['fail_idx']].end:%H:%M} close {cs[c[0]['fail_idx']].close:.2f} (B {c[0]['level']:.2f})" if c else "no signal"
        (OUT / "_state" / f"nov3_candidates_{tag}.json").write_text(json.dumps(res, indent=1))
    (OUT / "_state" / "irf_priority1_summary.json").write_text(json.dumps(summ, indent=1, default=str))
    print(json.dumps(summ, indent=1, default=str))


if __name__ == "__main__":
    main()
