"""Phase 7.1 SVG trade charts: candles, EMA(200) path, reference levels, signal / entry / stops / T1 / T2 / post-T1 stop, both leg exits. Hypothetical (rejected / not executed) trades are drawn with
dashed outlines and an explicit 'NOT EXECUTED' label so a chart can never be mistaken for a fill. Hand-written SVG (no plotting dependency)."""

from __future__ import annotations

import textwrap
from html import escape

import pandas as pd

GREEN, RED, GREY, BLUE, PURPLE, ORANGE, TXT, YELLOW = "#1f8a5b", "#c0392b", "#8a8f98", "#2b6cb0", "#6b46c1", "#d9822b", "#222", "#c9a400"


def _ts(x):
    t = pd.Timestamp(x)
    return t.tz_localize(None) if t.tzinfo is not None else t


def trade_chart(candles: pd.DataFrame, title: str, subtitle: str, hlines: list[tuple], marks: list[tuple], notes: list[str], *, t_from=None, t_to=None, hypothetical: bool = False,
                box: tuple | None = None, width: int = 1180, height: int = 520) -> str:
    """candles: DataFrame bar_start/bar_end/open/high/low/close/ema200_5m. hlines: (price, label, colour, dashed). marks: (timestamp, price, label, colour). box: (t0, t1, entry, stop, t2) translucent position box."""
    c = candles.copy()
    c["s"] = c["bar_start"].map(_ts)
    c["e"] = c["bar_end"].map(_ts)
    if t_from is not None:
        c = c[c["e"] >= _ts(t_from)]
    if t_to is not None:
        c = c[c["s"] <= _ts(t_to)]
    c = c.reset_index(drop=True)
    notes = [ln for n in notes for ln in (textwrap.wrap(n, 190) or [""])]
    pl, pr, pt, pb = 72, 210, 54, 40
    ch = height - pt - pb
    total = pt + ch + pb + 16 * len(notes) + 14
    pw = width - pl - pr
    emas = c["ema200_5m"].astype(float)
    pr_vals = list(c["low"]) + list(c["high"]) + [h[0] for h in hlines if h[0] is not None] + [float(v) for v in emas if v == v]
    lo, hi = min(pr_vals), max(pr_vals)
    sp = (hi - lo) or 1.0
    lo, hi = lo - 0.04 * sp, hi + 0.04 * sp
    t0, t1 = c["s"].iloc[0], c["e"].iloc[-1]
    tsp = (t1 - t0).total_seconds()

    def X(t):
        return pl + pw * (_ts(t) - t0).total_seconds() / tsp

    def Y(p):
        return pt + ch * (1 - (p - lo) / (hi - lo))

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total}" viewBox="0 0 {width} {total}" font-family="Helvetica,Arial,sans-serif" font-size="11">', f'<rect width="{width}" height="{total}" fill="white"/>',
         f'<text x="10" y="20" font-size="15" font-weight="bold" fill="{TXT}">{escape(title)}</text>', f'<text x="10" y="38" fill="{GREY}">{escape(subtitle)}</text>',
         f'<rect x="{pl}" y="{pt}" width="{pw}" height="{ch}" fill="{"#fff7f2" if hypothetical else "#fafafa"}" stroke="#ddd"/>']
    if hypothetical:
        o.append(f'<text x="{pl + 8}" y="{pt + 18}" font-size="16" font-weight="bold" fill="{RED}" fill-opacity="0.55">NOT EXECUTED - hypothetical / rejected signal</text>')
    for k in range(6):
        p = lo + (hi - lo) * k / 5
        o.append(f'<line x1="{pl}" x2="{pl + pw}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="#eee"/><text x="{pl - 6}" y="{Y(p) + 4:.1f}" text-anchor="end" fill="{GREY}">{p:,.1f}</text>')
    last = None
    for _, r in c.iterrows():
        if r["s"].minute % 30 == 0 and r["s"] != last:
            last = r["s"]
            o.append(f'<line x1="{X(r["s"]):.1f}" x2="{X(r["s"]):.1f}" y1="{pt}" y2="{pt + ch}" stroke="#eee"/><text x="{X(r["s"]):.1f}" y="{pt + ch + 14}" text-anchor="middle" fill="{GREY}">{r["s"]:%H:%M}</text>')
    if box:
        a, b, ent, stp, tg = box
        for p, col in ((stp, RED), (tg, GREEN)):
            o.append(f'<rect x="{X(a):.1f}" y="{Y(max(ent, p)):.1f}" width="{max(X(b) - X(a), 2):.1f}" height="{abs(Y(ent) - Y(p)):.1f}" fill="{col}" fill-opacity="0.11" stroke="{col}" stroke-opacity="0.4"' + (' stroke-dasharray="4,3"' if hypothetical else "") + "/>")
    pts = " ".join(f"{(X(r['s']) + (X(r['e']) - X(r['s'])) / 2):.1f},{Y(float(r['ema200_5m'])):.1f}" for _, r in c.iterrows() if r["ema200_5m"] == r["ema200_5m"])
    if pts:
        o.append(f'<polyline points="{pts}" fill="none" stroke="{YELLOW}" stroke-width="1.6"/><text x="{pl + pw + 4}" y="{Y(float(emas.dropna().iloc[-1])) + 4:.1f}" fill="{YELLOW}">EMA(200) 5m</text>')
    for p, lab, col, dash in hlines:
        if p is None:
            continue
        d = ' stroke-dasharray="6,4"' if dash else ""
        o.append(f'<line x1="{pl}" x2="{pl + pw}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="1.1"{d}/><text x="{pl + pw + 4}" y="{Y(p) - 2:.1f}" fill="{col}">{escape(lab)}</text>')
    cw = max(pw / max(len(c), 1) * 0.6, 2.0)
    for _, r in c.iterrows():
        col = GREEN if r["close"] >= r["open"] else RED
        x = X(r["s"]) + (X(r["e"]) - X(r["s"])) / 2
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(r["high"]):.1f}" y2="{Y(r["low"]):.1f}" stroke="{col}"/>')
        y1, y2 = Y(max(r["open"], r["close"])), Y(min(r["open"], r["close"]))
        o.append(f'<rect x="{x - cw / 2:.1f}" y="{y1:.1f}" width="{cw:.1f}" height="{max(y2 - y1, 1):.1f}" fill="{col}"' + (' fill-opacity="0.55"' if hypothetical else "") + "/>")
    for t, p, lab, col in marks:
        if t is None or p is None:
            continue
        x, y = X(t), Y(p)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="none" stroke="{col}" stroke-width="2"/><text x="{x + 6:.1f}" y="{y - 7:.1f}" fill="{col}" font-weight="bold">{escape(lab)}</text>')
    for i, n in enumerate(notes):
        o.append(f'<text x="10" y="{pt + ch + pb + 4 + 16 * i}" fill="{TXT}">{escape(n)}</text>')
    o.append("</svg>")
    return "\n".join(o)
