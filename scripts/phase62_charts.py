"""SVG renderers for Phase 6.2 / 6.3: a full trade chart (signal evidence + entry, stop, T1, T2, post-T1 stop, both leg exits, P&L, journal status) and a no-trade / comparison day chart (rejection reasons, no invented markers)."""

from __future__ import annotations

from html import escape

import pandas as pd

GREEN, RED, BLUE, PURPLE, ORANGE, GREY = "#17a37a", "#d9534f", "#2f80ed", "#8e44ad", "#e67e22", "#888"
W, H, L, R, T, B = 1500, 800, 70, 640, 95, 40


def _wrap(s: str, w: int = 50) -> list[str]:
    out, cur = [], ""
    for word in str(s).split(" "):
        if len(cur) + len(word) + 1 > w and cur:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    return out + ([cur] if cur else [])


def _lines_from_levels(lv: dict) -> list[tuple[float, str, str]]:
    out = []
    for k, v in lv.items():
        if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:
            continue
        kl = k.lower()
        if k in ("IRH", "IRL") or any(x in kl for x in ("recent_support", "recent_resistance", "zone_low", "zone_high", "zone_floor", "zone_ceiling", "support_level", "resistance_level", "upper_zone", "lower_zone", "prev_high", "prev_low", "swing")):
            out.append((float(v), k, PURPLE if "support" in kl or kl == "irl" else (ORANGE if "zone" in kl else "#555")))
    return out


def chart(title: str, header: list[str], candles: pd.DataFrame, panel: list[str], *, trade: dict | None = None, hlines=(), markers=(), open_highlight=True, shade=()) -> str:  # noqa: C901
    """candles: start/open/high/low/close/ema (today's 5-minute candles). trade: entry_time, entry_price, direction, stop, t1, t2, post_t1_stop (or None), leg1_time/price/reason, leg2_time/price/reason, gross_points, gross_rs.
    hlines: (price, label, colour); markers: (timestamp, price, label, colour); shade: (floor, ceiling, label, colour) bands."""
    c = candles.reset_index(drop=True)
    n = len(c)
    cw = (W - L - R) / max(n, 1)
    starts = list(c["start"])
    xs = {s: L + (i + 0.5) * cw for i, s in enumerate(starts)}

    def xat(ts) -> float:
        ts = pd.Timestamp(ts)
        k = max((i for i, s in enumerate(starts) if s <= ts), default=0)
        return xs[starts[k]]

    prices = list(c["high"]) + list(c["low"]) + list(c["ema"].dropna()) + [p for p, *_ in hlines] + [x[1] for x in markers] + [v for s in shade for v in s[:2]]
    if trade:
        prices += [trade[k] for k in ("stop", "t1", "t2") if trade.get(k) is not None]
    lo, hi = min(prices), max(prices)
    pad = (hi - lo) * 0.05 + 1
    lo, hi = lo - pad, hi + pad
    ch = H - T - B
    y = lambda p: T + (hi - p) / (hi - lo) * ch  # noqa: E731
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="11"><rect width="{W}" height="{H}" fill="#fff"/>', f'<text x="{L}" y="20" font-size="16" font-weight="bold">{escape(title)}</text>']
    for i, hl in enumerate(header):
        o.append(f'<text x="{L}" y="{38 + 14 * i}" fill="#333">{escape(hl)}</text>')
    raw = (hi - lo) / 8
    step = next((v for v in (1, 2, 5, 10, 20, 25, 50, 100, 200) if v >= raw), 200)
    p = int(lo // step * step)
    while p <= hi:
        if p >= lo:
            o.append(f'<line x1="{L}" y1="{y(p):.1f}" x2="{W - R}" y2="{y(p):.1f}" stroke="#eee"/><text x="{L - 6}" y="{y(p) + 4:.1f}" text-anchor="end" fill="{GREY}">{p:,}</text>')
        p += step
    for s in starts:
        if s.minute == 0 and (s.hour - 9) % 2 == 0:
            o.append(f'<text x="{xs[s]:.1f}" y="{H - B + 14}" text-anchor="middle" fill="{GREY}">{s:%H:%M}</text>')
    if open_highlight and n:
        o.append(f'<rect x="{L:.1f}" y="{T}" width="{cw:.1f}" height="{ch}" fill="#ffd54f" opacity="0.35"/>')
    xr = W - R
    lab = []
    for fl, ce, name, col in shade:
        o.append(f'<rect x="{L}" y="{y(ce):.1f}" width="{xr - L}" height="{max(1.5, y(fl) - y(ce)):.1f}" fill="{col}" opacity="0.18" stroke="{col}" stroke-width="0.8"/>')
        lab.append(((fl + ce) / 2, name, col))
    for pr, name, col in hlines:
        o.append(f'<line x1="{L}" y1="{y(pr):.1f}" x2="{xr}" y2="{y(pr):.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="3 3" opacity="0.8"/>')
        lab.append((pr, f"{name} {pr:.2f}", col))
    for i, r in c.iterrows():
        xx = L + (i + 0.5) * cw
        col = GREEN if r["close"] >= r["open"] else RED
        o.append(f'<line x1="{xx:.1f}" y1="{y(r["high"]):.1f}" x2="{xx:.1f}" y2="{y(r["low"]):.1f}" stroke="{col}"/>')
        tp, bt = y(max(r["open"], r["close"])), y(min(r["open"], r["close"]))
        o.append(f'<rect x="{xx - cw * 0.35:.1f}" y="{tp:.1f}" width="{cw * 0.7:.1f}" height="{max(0.8, bt - tp):.1f}" fill="{col}"/>')
    pts = " ".join(f"{L + (i + 0.5) * cw:.1f},{y(v):.1f}" for i, v in enumerate(c["ema"]) if pd.notna(v))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="1.6"/>')
    lab.append((float(c["ema"].iloc[-1]), f"EMA(200) {float(c['ema'].iloc[-1]):.1f}", BLUE))
    if trade:
        xe = xat(trade["entry_time"])
        x2 = xat(trade["leg2_time"]) if trade.get("leg2_time") is not None else xr
        for key, nm, col, dash in (("t2", "T2", GREEN, "6 3"), ("t1", "T1", GREEN, "2 3"), ("stop", "STOP", RED, "6 3"), ("post_t1_stop", "POST-T1 STOP", ORANGE, "6 3")):
            v = trade.get(key)
            if v is None:
                continue
            o.append(f'<line x1="{xe:.1f}" y1="{y(v):.1f}" x2="{max(x2, xe + 30):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width="1.5" stroke-dasharray="{dash}"/>')
            lab.append((v, f"{nm} {v:.2f}", col))
        ye = y(trade["entry_price"])
        up = trade["direction"] == "LONG"
        o.append(f'<polygon points="{xe:.1f},{ye - 9 if up else ye + 9:.1f} {xe - 6:.1f},{ye:.1f} {xe + 6:.1f},{ye:.1f}" fill="#111"/><line x1="{L}" y1="{ye:.1f}" x2="{xr}" y2="{ye:.1f}" stroke="#111" stroke-width="0.7" stroke-dasharray="2 3"/>')
        lab.append((trade["entry_price"], f"ENTRY {trade['direction']} {trade['entry_price']:.2f} @{pd.Timestamp(trade['entry_time']):%H:%M}", "#111"))
        for leg, mark in (("leg1", "circle"), ("leg2", "cross")):
            px, tm = trade.get(f"{leg}_price"), trade.get(f"{leg}_time")
            if px is None or tm is None:
                continue
            xx, yy = xat(tm), y(px)
            if mark == "circle":
                o.append(f'<circle cx="{xx:.1f}" cy="{yy:.1f}" r="6" fill="none" stroke="#111" stroke-width="2"/>')
            else:
                o.append(f'<line x1="{xx - 5:.1f}" y1="{yy - 5:.1f}" x2="{xx + 5:.1f}" y2="{yy + 5:.1f}" stroke="#111" stroke-width="2.4"/><line x1="{xx - 5:.1f}" y1="{yy + 5:.1f}" x2="{xx + 5:.1f}" y2="{yy - 5:.1f}" stroke="#111" stroke-width="2.4"/>')
            lab.append((px, f"LEG {leg[-1]} EXIT {trade.get(leg + '_reason', '')} {px:.2f} @{pd.Timestamp(tm):%H:%M}", "#111"))
    for ts, pr, name, col in markers:
        xm, ym = xat(ts), y(pr)
        o.append(f'<polygon points="{xm:.1f},{ym - 8:.1f} {xm - 6:.1f},{ym + 5:.1f} {xm + 6:.1f},{ym + 5:.1f}" fill="{col}" opacity="0.9"/>')
        lab.append((pr, name, col))
    lab.sort(key=lambda t: -t[0])
    last = -99.0
    for pr, text, col in lab:
        yy = max(y(pr), last + 12.5)
        last = yy
        o.append(f'<line x1="{xr:.1f}" y1="{y(pr):.1f}" x2="{xr + 6:.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="0.6"/><text x="{xr + 8:.1f}" y="{yy + 3:.1f}" fill="{col}" font-size="10">{escape(text[:60])}</text>')
    px0 = W - 330
    o.append(f'<rect x="{px0 - 8}" y="{T}" width="328" height="{ch}" fill="#fafafa" stroke="#ddd"/>')
    yy = T + 15
    for line in panel:
        for chunk in _wrap(line, 52):
            if yy > T + ch - 6:
                break
            o.append(f'<text x="{px0}" y="{yy}" fill="#222" font-size="10">{escape(chunk)}</text>')
            yy += 12.5
        yy += 3
    o.append("</svg>")
    return "\n".join(o)
