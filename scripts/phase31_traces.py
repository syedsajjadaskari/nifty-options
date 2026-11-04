"""Phase 3.1: event-level traces (numeric tables + SVG chart) for representative disputed sessions. READ-ONLY diagnostics."""

from __future__ import annotations

import sys
from dataclasses import replace
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
from nifty_trading.strategies.definitions import (  # noqa: E402
    gap_info,
    pdr_zone,
    pds_zone,
    prev_high_low,
    to_candles,
    trend_check,
)

OUT = ROOT / "reports" / "phase3" / "phase31" / "disputed_trade_traces"
BASE = ROOT / "reports" / "phase3" / "phase31"


def pick(df: pd.DataFrame, n: int) -> list[str]:
    ds = sorted(df["date"].unique())
    if len(ds) <= n:
        return ds
    step = (len(ds) - 1) / (n - 1)
    return [ds[round(i * step)] for i in range(n)]


def svg_chart(day: date, tl, manual_today: list[dict], zones: dict, path: Path, title: str) -> None:
    cs = to_candles(tl.ctx.candles)
    W, H, ml, mr, mt, mb = 1180, 560, 70, 20, 40, 40
    prev = tl.ctx.previous
    ph, pl = prev_high_low(prev, P.make_engines(P.scenarios()["baseline"].proposals, P.scenarios()["baseline"].trade)[0].p) if prev is not None else (None, None)
    lo = min(c.l for c in cs)
    hi = max(c.h for c in cs)
    for v in [ph, pl]:
        if v is not None:
            lo, hi = min(lo, v - 5), max(hi, v + 5)
    for z in zones.values():
        if z:
            lo, hi = min(lo, z[0] - 3), max(hi, z[1] + 3)
    pad = (hi - lo) * 0.04
    lo, hi = lo - pad, hi + pad

    def y(p):
        return mt + (hi - p) / (hi - lo) * (H - mt - mb)
    n = len(cs)
    cw = (W - ml - mr) / max(n, 1)

    def x(i):
        return ml + i * cw + cw / 2
    idx = {f"{c.start:%H:%M}": i for i, c in enumerate(cs)}
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="monospace" font-size="11">', f'<rect width="{W}" height="{H}" fill="white"/>',
           f'<text x="{ml}" y="18" font-size="14" font-weight="bold">{title}</text>']
    for k in range(6):
        p = lo + (hi - lo) * k / 5
        out.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eee"/><text x="4" y="{y(p) + 4:.1f}">{p:,.0f}</text>')
    for i in range(0, n, 6):
        out.append(f'<text x="{x(i) - 14:.0f}" y="{H - 22}">{cs[i].start:%H:%M}</text>')
    for lab, v, col in (("prev high", ph, "#b00"), ("prev low", pl, "#070")):
        if v is not None:
            out.append(f'<line x1="{ml}" x2="{W - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-dasharray="6,4"/><text x="{W - 130}" y="{y(v) - 3:.1f}" fill="{col}">{lab} {v:,.2f}</text>')
    cols = {"PDR zone (reversal swing high)": "#1565c0", "PDR zone (repeated shelf)": "#6a1b9a", "PDR diagnostic highest-high": "#9e9e9e", "PDS zone": "#ef6c00"}
    for k, (name, z) in enumerate(zones.items()):
        if z:
            out.append(f'<rect x="{ml}" y="{y(z[1]):.1f}" width="{W - ml - mr}" height="{max(y(z[0]) - y(z[1]), 1.5):.1f}" fill="{cols.get(name, "#999")}" opacity="0.13"/>'
                       f'<text x="{ml + 4}" y="{y(z[1]) - 2 - 11 * k:.1f}" fill="{cols.get(name, "#555")}">{name} [{z[0]:,.2f}, {z[1]:,.2f}]</text>')
    pts = " ".join(f"{x(i):.1f},{y(c.ema):.1f}" for i, c in enumerate(cs) if c.ema == c.ema and lo <= c.ema <= hi)
    if pts:
        out.append(f'<polyline points="{pts}" fill="none" stroke="#f9a825" stroke-width="1.6"/><text x="{ml + 4}" y="{H - 8}" fill="#f9a825">EMA(200) of 5m closes</text>')
    for i, c in enumerate(cs):
        col = "#2e7d32" if c.c >= c.o else "#c62828"
        out.append(f'<line x1="{x(i):.1f}" x2="{x(i):.1f}" y1="{y(c.h):.1f}" y2="{y(c.l):.1f}" stroke="{col}"/>'
                   f'<rect x="{x(i) - cw * 0.35:.1f}" y="{y(max(c.o, c.c)):.1f}" width="{cw * 0.7:.1f}" height="{max(abs(y(c.o) - y(c.c)), 1):.1f}" fill="{col}"/>')
    for key, lab in (("13:00", "13:00 entry cutoff"), ("15:10", "15:14 forced exit")):
        if key in idx:
            out.append(f'<line x1="{x(idx[key]):.1f}" x2="{x(idx[key]):.1f}" y1="{mt}" y2="{H - mb}" stroke="#555" stroke-dasharray="2,3"/><text x="{x(idx[key]) - 40:.0f}" y="{mt - 4}">{lab}</text>')
    for t in tl.result.trades:
        i = idx.get(f"{t.signal.signal_candle_start:%H:%M}")
        if i is not None:
            out.append(f'<polygon points="{x(i):.1f},{y(cs[i].l) + 4:.1f} {x(i) - 6:.1f},{y(cs[i].l) + 16:.1f} {x(i) + 6:.1f},{y(cs[i].l) + 16:.1f}" fill="#000"/>'
                       f'<text x="{x(i) - 10:.0f}" y="{y(cs[i].l) + 28:.0f}">AUTO {t.signal.strategy} {t.trade_no} {t.classification}</text>')
    for k, m in enumerate(manual_today):
        i = idx.get(m["entry_time_label"])
        if i is not None:
            out.append(f'<polygon points="{x(i):.1f},{y(cs[i].h) - 4:.1f} {x(i) - 6:.1f},{y(cs[i].h) - 16:.1f} {x(i) + 6:.1f},{y(cs[i].h) - 16:.1f}" fill="#d500f9"/>'
                       f'<text x="{x(i) - 10:.0f}" y="{y(cs[i].h) - 20 - 11 * k:.0f}" fill="#d500f9">MANUAL {m["strategy_normalized"]} {m["exit_classification_entered"]}</text>')
    out.append("</svg>")
    path.write_text("\n".join(out))


def trace(day: date, tl, tls_b, m1day: pd.DataFrame, manual_today: list[dict], why: str, base_props) -> str:
    ctx = tl.ctx
    cs = ctx.candles.copy()
    cs["range"] = cs.high - cs.low
    cs["body_ratio"] = ((cs.close - cs.open).abs() / cs.range.where(cs.range > 0)).round(3)
    cs["upper_wick_ratio"] = ((cs.high - cs[["open", "close"]].max(axis=1)) / cs.range.where(cs.range > 0)).round(3)
    cs["lower_wick_ratio"] = ((cs[["open", "close"]].min(axis=1) - cs.low) / cs.range.where(cs.range > 0)).round(3)
    prev = ctx.previous
    ph, pl = prev_high_low(prev, base_props) if prev else (None, None)
    g = gap_info(ctx, base_props)
    zones = {}
    if prev is not None:
        for name, meth in (("PDR zone (reversal swing high)", "B_SWING_HIGH_REVERSAL"), ("PDR zone (repeated shelf)", "C_REPEATED_TOUCHES"), ("PDR diagnostic highest-high", "A_HIGHEST_HIGH")):
            z = pdr_zone(prev, replace(base_props, pdr_zone_method=meth))
            zones[name] = None if z is None else [z.low, z.high]
        zones["PDS zone"] = (lambda z: [z.low, z.high])(pds_zone(prev, base_props))
    md = [f"# Trace {day} ({day:%A})\n", f"**Why selected:** {why}\n", "## 1. Manual journal entries\n"]
    md += ([f"* row {m['journal_row']}: {m['strategy_normalized']} @ {m['entry_time_label']} (candle start; fill at {m['estimated_fill_time']}) -> {m['exit_classification_entered']}"
            + (f" - NON-CONFORMING: {m['nonconformity']}" if m['nonconformity'] else "") + (f" - phase-2.1 status {m['phase21_status']}: {m['phase21_reasons']}" if m['phase21_status'] != 'VALID' else "") for m in manual_today] or ["* none"])
    md += ["\n## 2. Previous-day levels, gap and trend state\n", f"* session open (first 1-minute open) **{ctx.open_price}**; previous official close {prev.close_official if prev else None}; gap {g.points:+.2f} ({g.direction}); prev-day high/low {ph}/{pl}",
           f"* first 5m candle: O {cs.open.iloc[0]} H {cs.high.iloc[0]} L {cs.low.iloc[0]} C {cs.close.iloc[0]}  body_ratio {cs.body_ratio.iloc[0]}, upper wick {cs.upper_wick_ratio.iloc[0]}, lower wick {cs.lower_wick_ratio.iloc[0]}; EMA200(5m) at candle 0: {cs.ema200_5m.iloc[0]:.2f}"]
    for var, mode in (("A (EMA-only)", "EMA_PREV_SESSION_CLOSE"), ("B (EMA + swing structure)", "STRUCTURE_EMA_SWING2")):
        for d_ in ("LONG", "SHORT"):
            t = trend_check(ctx, 0, d_, mode, base_props)
            md.append(f"* trend variant {var} {d_}: ok={t.ok} - {t.reason}")
    md += ["\n## 3. Candidate zones (previous session only)\n"] + [f"* {k}: {v}" for k, v in zones.items()]
    if prev is not None and zones.get("PDR zone (reversal swing high)") and g.direction == "UP":
        z = zones["PDR zone (reversal swing high)"]
        md.append(f"* open vs reversal-swing zone: open {ctx.open_price} {'ABOVE' if ctx.open_price > z[1] else 'inside/below'} zone high {z[1]}")
    md += ["\n## 4. Every engine record of the session (baseline settings)\n", "| strategy | method | dir | status | candle start | signal time | reason / failed rules | unresolved | satisfied (proposal/qual.) |", "|---|---|---|---|---|---|---|---|---|"]
    from nifty_trading.strategies.rules import RULE_BY_ID
    for r in sorted(tl.records, key=lambda r: (str(r.signal_candle_start), r.strategy, r.method)):
        sat = ",".join(x for x in r.rule_ids_satisfied if x in RULE_BY_ID and RULE_BY_ID[x]["classification"] in ("PROPOSED_FOR_REVIEW", "VERIFIED_QUALITATIVE"))
        md.append(f"| {r.strategy} | {r.method} | {r.direction} | {r.signal_status} | {r.signal_candle_start:%H:%M} | {f'{r.signal_timestamp:%H:%M}' if r.signal_timestamp else ''} | "
                  f"{(r.invalidation_reason or '')} {('FAILED:' + ','.join(r.rule_ids_failed)) if r.rule_ids_failed else ''} | {','.join(r.rule_ids_unresolved)} | {sat} |"
                  if r.signal_candle_start else f"| {r.strategy} | {r.method} | {r.direction} | {r.signal_status} | - | - | {r.invalidation_reason} | | |")
    rows = R.timeline_rows(tl, "baseline", manual_today)
    md += ["\n## 5. Chronological timeline with the portfolio decision\n", "| time | event | strategy | method | state | disposition | blocked by |", "|---|---|---|---|---|---|---|"]
    md += [f"| {x['time']} | {x['event']} | {x['strategy']} | {x['method']} | {x['portfolio_state']} | {x['disposition_reason'][:90]} | {x['blocked_by']} |" for x in rows if x["signal_status"] in ("CONFIRMED", "MANUAL")]
    md += ["\n## 6. Automated trades\n"] + ([f"* trade {t.trade_no}: {t.signal.strategy} {t.signal.method} {t.signal.direction}: candle {t.signal.signal_candle_start:%H:%M}, signal/fill {t.fill_timestamp:%H:%M} at {t.entry_price} "
                                           f"(earliest legal confirmation = candle end; earliest legal fill = open of the next 1-minute bar) -> {t.classification}, gross Rs {t.result.pnl_rupees:,.0f}" for t in tl.result.trades] or ["* none"])
    cf = [d for d in tl.result.diagnostics if d.event == "CONFLICT"]
    if cf:
        md += ["\n* collision(s): " + "; ".join(d.reason for d in cf)]
    md += ["\n## 7. Five-minute candles with indicator and candle-quality measurements\n", "| start | O | H | L | C | EMA200 | body | up wick | low wick |", "|---|---|---|---|---|---|---|---|---|"]
    md += [f"| {r.bar_start:%H:%M} | {r.open} | {r.high} | {r.low} | {r.close} | {r.ema200_5m:.2f} | {r.body_ratio} | {r.upper_wick_ratio} | {r.lower_wick_ratio} |" for r in cs.itertuples() if f"{r.bar_start:%H:%M}" <= "13:05"]
    md += ["\n(candles after 13:05 omitted from this table; the full day's 1-minute rows are in the CSV beside this file)"]
    return "\n".join(md) + "\n"


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    m1 = load_one_minute()
    ctxs, infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    m1d = m1.assign(_d=m1.timestamp.dt.date)
    bars = {d: bars_from_frame(g) for d, g in m1d.groupby("_d")}
    base = P.scenarios()["baseline"]
    tl = R.run_timelines(base, ctxs, bars)
    mv = pd.read_csv(BASE / "manual_vs_automated.csv")
    ex = pd.read_csv(BASE / "extra_automated_trades.csv")
    mj = pd.read_csv(BASE / "manual_journal_normalized.csv").fillna("")
    manual_by_day = {d: g.to_dict("records") for d, g in mj.groupby("date")}
    sel: list[tuple[str, str]] = []
    sel += [(d, "extra automated IRF trade (no matching manual IRF trade)") for d in pick(ex[ex.strategy == "IRF"], 3)]
    sel += [(d, "extra automated PDR trade (manual journal has 8 PDR rows in the year)") for d in pick(ex[ex.strategy == "PDR"], 3)]
    om = mv[(mv.strategy_normalized == "ORB") & (mv.classification == "SIGNAL_REJECTED_BY_ENTRY_RULE")]
    sel += [(d, "manual ORB trade the engine rejected (entry rule / trend / candle quality)") for d in pick(om, 3)]
    sel += [(d, "manual ORB trade with NO setup record (first candle did not close beyond the previous day's high/low)") for d in pick(mv[(mv.strategy_normalized == "ORB") & (mv.classification == "MISSING_AUTOMATED_SIGNAL")], 2)]
    sel += [(d, "manual RF trade the automated system did not take") for d in pick(mv[(mv.strategy_normalized == "RF") & (~mv.classification.isin(["EXACT_MATCH", "TIME_SHIFTED_MATCH"]))], 3)]
    sel += [("2025-10-07", "PDR chart 3 (the drawn shelf zone no mechanical rule reproduces)")]
    sel += [(d, "same-minute collision between different strategies") for d in sorted({r for r in pd.read_csv(BASE / "collision_counterfactual.csv").date})]
    sel += [("2026-05-19", "journal day that conflicts with the approved second-trade rule (ORB BE then PDR)")]
    sel += [(d, "journal row dated on a non-trading Saturday") for d in sorted(mv[mv.classification == "MANUAL_JOURNAL_CONFLICT"].date.unique())[:1]]
    seen = set()
    index = ["# Disputed-session traces\n", "Each trace is numeric (tables) with an SVG chart beside it; charts are for human review only and verify nothing. 1-minute rows for the whole day are in `<date>_1m.csv`.\n", "| date | why selected | trace | chart |", "|---|---|---|---|"]
    for d, why in sel:
        if d in seen:
            continue
        seen.add(d)
        dd = date.fromisoformat(d)
        if dd not in tl:
            index.append(f"| {d} | {why} | (no evaluable session: Saturday/holiday) | - |")
            continue
        manual_today = manual_by_day.get(d, [])
        (OUT / f"{d}.md").write_text(trace(dd, tl[dd], None, None, manual_today, why, base.proposals))
        zones = {}
        prev = tl[dd].ctx.previous
        if prev is not None:
            for name, meth in (("PDR zone (reversal swing high)", "B_SWING_HIGH_REVERSAL"), ("PDR zone (repeated shelf)", "C_REPEATED_TOUCHES"), ("PDR diagnostic highest-high", "A_HIGHEST_HIGH")):
                z = pdr_zone(prev, replace(base.proposals, pdr_zone_method=meth))
                zones[name] = None if z is None else [z.low, z.high]
            z = pds_zone(prev, base.proposals)
            zones["PDS zone"] = [z.low, z.high]
        svg_chart(dd, tl[dd], manual_today, zones, OUT / f"{d}.svg", f"{d} - {why[:90]}")
        m1d[m1d._d == dd][["timestamp", "open", "high", "low", "close"]].to_csv(OUT / f"{d}_1m.csv", index=False)
        index.append(f"| {d} | {why} | [{d}.md]({d}.md) | [{d}.svg]({d}.svg) |")
    (OUT / "README.md").write_text("\n".join(index) + "\n")
    print(len(seen), "traces")


if __name__ == "__main__":
    main()
