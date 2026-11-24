"""Phase 7.1 charts + per-day files (primary window A): every executed B trade, EMA / IRF / PDR / PDS changed trades (rejected ones drawn as NOT EXECUTED), ORB-vs-IRF disagreements, journal manual-only and
automated-only days, ORB EMA conflicts. Reads the cached portfolio runs; writes only under reports/phase7/phase71_global_ema_and_final_validation/charts and daily."""

from __future__ import annotations

import pickle
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
import phase71_run as R71  # noqa: E402

from nifty_trading.research.phase71 import charts as CH  # noqa: E402

OUT = Path(__file__).resolve().parents[1] / "reports/phase7/phase71_global_ema_and_final_validation"
SP = R71.SP
STRAT_COL = {"IRF": CH.BLUE, "ORB": CH.PURPLE, "PDR": CH.GREEN, "PDS": CH.RED, "RF": CH.ORANGE}


def load(w, k):
    return pickle.loads((SP / "p71cache" / f"run71_{w}_{k}.pkl").read_bytes())


def ts(d: str, hm: str) -> pd.Timestamp:
    return pd.Timestamp(f"{d} {hm}") if hm else None


def ema_note(ctx, signal_time: str, d: str) -> str:
    c = ctx.candles
    start = pd.Timestamp(f"{d} {signal_time}") - pd.Timedelta(minutes=5)
    m = c[c["bar_start"].map(lambda x: pd.Timestamp(x).tz_localize(None) if pd.Timestamp(x).tzinfo else pd.Timestamp(x)) == start]
    if m.empty or m.iloc[0]["ema200_5m"] != m.iloc[0]["ema200_5m"]:
        return "EMA(200) at the confirmation candle: unavailable"
    r = m.iloc[0]
    e = float(r["ema200_5m"])
    rng = max(float(r["low"]) - e, e - float(r["high"]), 0.0)
    return f"EMA(200) at the confirmation candle {e:.2f}: |close-EMA| {abs(float(r['close']) - e):.2f}, signed {float(r['close']) - e:+.2f}, candle-range clearance {rng:.2f} ({'EMA inside the candle' if rng == 0 else 'EMA above' if e > float(r['high']) else 'EMA below'} the candle)"


def trade_svg(ctx, r: dict, title_prefix: str, extra: list[str], hypothetical: bool = False, jstage: str = "") -> str:
    d = r["date"]
    sig = ts(d, r["signal_time"])
    ent = ts(d, r["entry_time"])
    e1, e2 = ts(d, r.get("leg1_exit_time") or ""), ts(d, r.get("leg2_exit_time") or "")
    end = max([x for x in (e1, e2, ent) if x is not None] + [sig]) + pd.Timedelta(minutes=30)
    entry = float(r["entry_price"])
    short = r["direction"] == "SHORT"
    hl = [(entry, f"entry {entry:.2f}", CH.TXT, False), (float(r["stop_level"]), f"initial stop {float(r['stop_level']):.2f}", CH.RED, False), (float(r["t1_level"]), f"T1 {float(r['t1_level']):.2f}", CH.GREEN, True),
          (float(r["t2_level"]), f"T2 {float(r['t2_level']):.2f}", CH.GREEN, False)]
    if r.get("post_t1_stop_level") not in (None, "", "nan") and str(r.get("post_t1_stop_level")) != "nan":
        hl.append((float(r["post_t1_stop_level"]), f"post-T1 stop {float(r['post_t1_stop_level']):.2f}", CH.ORANGE, True))
    marks = [(sig, float(ctx.candles["close"].iloc[0]) if False else entry, f"signal {r['signal_time']}", CH.BLUE), (ent, entry, "entry", CH.TXT)]
    if e1 is not None and r.get("leg1_exit_price") not in (None, ""):
        marks.append((e1, float(r["leg1_exit_price"]), f"leg1 exit {float(r['leg1_exit_price']):.2f}", CH.TXT))
    if e2 is not None and r.get("leg2_exit_price") not in (None, ""):
        marks.append((e2, float(r["leg2_exit_price"]), f"leg2 exit {float(r['leg2_exit_price']):.2f}", CH.TXT))
    notes = [f"{r['strategy']} {r['method']} {r['direction']}; outcome {r['outcome']}; gross {float(r['gross_points_weighted']):+.2f} weighted index points = Rs {float(r['gross_pnl_rs']):+,.0f} (synthetic, 390 units); journal: {jstage or 'n/a'}",
             ema_note(ctx, r["signal_time"], d)] + extra
    box = (ent, e2 or end, entry, float(r["stop_level"]), float(r["t2_level"])) if ent is not None else None
    _ = short
    return CH.trade_chart(ctx.candles, f"{title_prefix} {d} {r['strategy']} ({r['method']})", f"signal {r['signal_time']}, entry {r['entry_time']} @ {entry:.2f}", hl, marks, notes, t_to=end, hypothetical=hypothetical, box=box)


def day_svg(ctx, d: str, sigs: list[dict], title: str, notes: list[str]) -> str:
    marks = []
    for s in sigs:
        p = float(s["ref_close"])
        marks.append((ts(d, s["time"]) - pd.Timedelta(minutes=5), p, f"{s['strategy']} {s['method']} {s['time']}", STRAT_COL.get(s["strategy"], CH.TXT)))
    t_to = max([ts(d, s["time"]) for s in sigs] + [ts(d, "09:20")]) + pd.Timedelta(minutes=45)
    return CH.trade_chart(ctx.candles, title, d, [], marks, notes, t_to=t_to)


def main() -> None:
    ctxs, infos, bars, cal, label = R71.C61.window_data("A")
    runs = {k: load("A", k) for k in R71.CONFIGS if (SP / "p71cache" / f"run71_A_{k}.pkl").exists()}
    jr = pd.read_csv(OUT / "manual_journal_reconciliation.csv", dtype=str)
    jstage = {r.trade_id: r.stage for r in jr[(jr.config == "B") & jr.trade_id.notna()].itertuples()}
    n = defaultdict(int)

    def put(folder: str, name: str, svg: str) -> None:
        p = OUT / "charts" / folder
        p.mkdir(parents=True, exist_ok=True)
        (p / name).write_text(svg)
        n[folder] += 1

    base = runs["B"]
    basek = {(r["date"], r["strategy"], r["entry_time"], r["direction"]): r for r in base["ledger"]}
    for r in base["ledger"]:
        ctx = ctxs[pd.Timestamp(r["date"]).date()]
        put("executed_B", f"{r['date']}_{r['strategy']}_{r['entry_time'].replace(':', '')}.svg", trade_svg(ctx, r, "B executed:", [], False, jstage.get(r["trade_id"], "")))
    gate_by = {}
    for k, run in runs.items():
        gate_by[k] = {(g["date"], g["time"], g["strategy"], g["method"]): g for g in run["gate_log"] if g.get("result") == "FAIL" or str(g.get("kept")) == "False"}
    for k, run in runs.items():
        if k in ("A", "B"):
            continue
        cur = {(r["date"], r["strategy"], r["entry_time"], r["direction"]): r for r in run["ledger"]}
        for key, r in basek.items():
            if key not in cur:
                ctx = ctxs[pd.Timestamp(r["date"]).date()]
                g = gate_by[k].get((r["date"], r["signal_time"], r["strategy"], r["method"]))
                why = [f"Removed under {k}: " + (f"the rule rejected this signal ({g.get('why')})" if g else "portfolio effect (the signal still exists; an earlier / different trade changed the day)")]
                put(f"removed_{k}", f"{r['date']}_{r['strategy']}_{r['entry_time'].replace(':', '')}.svg", trade_svg(ctx, r, f"{k} REJECTED (hypothetical B trade):", why, True))
        for key, r in cur.items():
            if key not in basek:
                ctx = ctxs[pd.Timestamp(r["date"]).date()]
                put(f"added_{k}", f"{r['date']}_{r['strategy']}_{r['entry_time'].replace(':', '')}.svg", trade_svg(ctx, r, f"{k} ADDED trade (executed in {k}):", [f"Not a B trade; {R71.CONFIGS[k]}"], False))
    # ORB vs IRF same-day disagreements (both strategies have a confirmed signal; the baseline selected one)
    by_day = defaultdict(list)
    for s in base["signals"]:
        by_day[s["date"]].append(s)
    exe = defaultdict(list)
    for r in base["ledger"]:
        exe[r["date"]].append(r)
    for d, ss in by_day.items():
        strat = {s["strategy"] for s in ss}
        if "ORB" in strat and "IRF" in strat:
            sel = ",".join(f"{r['strategy']}@{r['entry_time']}" for r in exe.get(d, [])) or "none"
            put("orb_vs_irf", f"{d}.svg", day_svg(ctxs[pd.Timestamp(d).date()], d, [s for s in ss if s["strategy"] in ("ORB", "IRF") and s["cycle_no"] in (1, "1", "")], f"ORB vs IRF {d}: baseline executed {sel}", ["Both strategies confirmed a signal this day; the frozen controller takes the first valid signal (no ORB/IRF priority)."]))
    # journal manual-only / automated-only (config B)
    man = pd.read_csv(OUT / "manual_only.csv", dtype=str)
    for r in man[(man.config == "B") & (man.weekend_row.astype(str) != "True")].itertuples():
        if pd.Timestamp(r.date).date() not in ctxs:
            continue
        put("journal_manual_only", f"{r.date}_{r.strategy}.svg", day_svg(ctxs[pd.Timestamp(r.date).date()], r.date, by_day.get(r.date, []), f"Journal manual-only {r.date}: {r.strategy} @ {r.time_label} ({r.outcome})",
                                                                          [f"No automated {r.strategy} trade matched this row. Automated trades that day: {r.automated_that_day or 'none'}. Journal has no price / direction."]))
    auto = pd.read_csv(OUT / "automated_only.csv", dtype=str)
    for r in auto[auto.config == "B"].itertuples():
        row = next((x for x in base["ledger"] if x["trade_id"] == r.trade_id), None)
        if row:
            put("journal_automated_only", f"{r.date}_{r.strategy}.svg", trade_svg(ctxs[pd.Timestamp(r.date).date()], row, "Automated-only (no matching journal row):", [f"Journal rows that day: {r.manual_rows_that_day}"], False, "AUTOMATED_ONLY"))
    # ORB EMA conflicts
    ed = pd.read_csv(OUT / "ema_distance_interpretations.csv", dtype=str)
    orb = ed[(ed.window == "A") & (ed.strategy == "ORB")]
    for r in orb.itertuples():
        fails = [c for c in ("EMA-1_MIN_CLOSE_27", "EMA-2_MIN_RANGE_27", "EMA-3_MAX_CLOSE_27", "EMA-4_MIN_RANGE_28", "EMA-5_TARGET_SIDE_27") if getattr(r, c.replace("-", "_"), None) == "FAIL"] if False else \
            [c for c in ("EMA-1_MIN_CLOSE_27", "EMA-2_MIN_RANGE_27", "EMA-3_MAX_CLOSE_27", "EMA-4_MIN_RANGE_28", "EMA-5_TARGET_SIDE_27") if orb.loc[r.Index, c] == "FAIL"]
        if r.candle_touches_or_crosses_ema == "True" or fails:
            ctx = ctxs[pd.Timestamp(r.date).date()]
            d = r.date
            put("orb_ema_conflicts", f"{d}_{r.direction}.svg", CH.trade_chart(ctx.candles, f"ORB {r.direction} {d}: opening candle vs EMA(200)", f"scenario {getattr(r, 'orb_ema_scenario', '')}", [(float(r.ema), f"EMA {float(r.ema):.2f}", CH.YELLOW, False)],
                                                                              [(ts(d, "09:15"), float(r.close), "09:15 opening candle (ORB signal at 09:20)", CH.PURPLE)],
                                                                              [f"|close-EMA| {float(r.abs_close_dist):.2f}; range clearance {float(r.range_clearance):.2f} ({r.relation}); candle crosses/touches EMA: {r.candle_touches_or_crosses_ema}", "Rejected by: " + (", ".join(fails) or "none"),
                                                                               "Source conflict: ORB V2 permits a fresh EMA cross; a minimum-distance rule would reject it."], t_to=ts(d, "10:30")))
    # per-day markdown (window A, baseline B)
    for d in sorted(base["days"]):
        p = OUT / "daily" / d[:7]
        p.mkdir(parents=True, exist_ok=True)
        rows = []
        for k in R71.CONFIGS:
            if k in runs:
                ts_ = sorted([r for r in runs[k]["ledger"] if r["date"] == d], key=lambda r: r["entry_time"])
                rows.append(f"| {k} | " + ("; ".join(f"{r['strategy']} {r['method']} {r['direction']} @{r['entry_time']} {float(r['entry_price']):.2f} stop {float(r['stop_level']):.2f} T1 {float(r['t1_level']):.2f} T2 {float(r['t2_level']):.2f} -> {r['outcome']} ({float(r['gross_points_weighted']):+.2f} pts, Rs {float(r['gross_pnl_rs']):+,.0f})" for r in ts_) or "no trade") + " |")
        sg = [s for s in base["signals"] if s["date"] == d and s["cycle_no"] in (1, "1", "")]
        j = jr[(jr.config == "B") & (jr.date == d)]
        md = [f"# {d} - window A", "", "## All confirmed signals (baseline B; IRF first cycle shown)", "| time | strategy | method | dir | ref close | executed in B |", "|---|---|---|---|---|---|"]
        md += [f"| {s['time']} | {s['strategy']} | {s['method']} | {s['direction']} | {float(s['ref_close']):.2f} | {s['executed']} |" for s in sorted(sg, key=lambda s: s["time"])] or ["| none |  |  |  |  |  |"]
        md += ["", "## Trades by configuration", "| config | trades |", "|---|---|", *rows, "", "## Journal (config B)"]
        md += [f"* {r.stage}: journal {getattr(r, 'manual_strategy', '')} {getattr(r, 'manual_time_label', '')} {getattr(r, 'manual_outcome', '')} vs automated {getattr(r, 'auto_strategy', '')} {getattr(r, 'auto_signal_candle_start', '')}" for r in j.itertuples()] or ["* no journal row and no automated trade matched this date"]
        (p / f"{d}.md").write_text("\n".join(md) + "\n")
    print(dict(n))


if __name__ == "__main__":
    main()
