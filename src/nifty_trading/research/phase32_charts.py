"""Phase 3.2: dependency-free SVG charts of an executed trade on the REAL five-minute candles (verification aids; the numerical journal is authoritative).

Everything plotted comes from the verified data set or from the levels the engine recorded; nothing is illustrative. Horizontal axis = minutes since 09:15
(one candle = 5 minutes), so a one-minute entry or exit sits at its exact position inside its candle.
"""

from __future__ import annotations

from html import escape

from nifty_trading.strategies.definitions import Candle

W, H, ML, MR, MT, MB = 1380, 640, 78, 290, 52, 46
T0, T1 = 9 * 60 + 15, 15 * 60 + 30


def _min(ts) -> float:
    return ts.hour * 60 + ts.minute + ts.second / 60.0


def _x(minute: float) -> float:
    return ML + (minute - T0) / (T1 - T0) * (W - ML - MR)


def trade_chart_svg(title: str, cs: list[Candle], trade: dict, levels: dict, manual: list[dict], ema_label: str = "EMA(200) of 5-minute closes", marks: list | None = None) -> str:
    """``trade``: entry_ts, entry, direction, stop, t1, t2, post_t1, exits [(ts, price, label)], outcome. ``levels``: hlines [(label, value, colour)], zones [(label, lo, hi, colour)].
    ``manual``: [{label: 'HH:MM', text: str}] journal entries for the day."""
    vals = [c.l for c in cs] + [c.h for c in cs]
    keys = [trade["entry"], trade["stop"], trade["t1"], trade["t2"]] + [e[1] for e in trade["exits"] if e[1] is not None]
    for _, v, _ in levels.get("hlines", []):
        if v is not None:
            keys.append(v)
    for _, lo, hi, _ in levels.get("zones", []):
        keys += [lo, hi]
    lo_p = min(vals + [k for k in keys if k is not None])
    hi_p = max(vals + [k for k in keys if k is not None])
    # keep the candles readable: cap the vertical range around the candles and the trade's own levels
    pad = (hi_p - lo_p) * 0.04 + 1
    lo_p, hi_p = lo_p - pad, hi_p + pad

    def y(p: float) -> float:
        return MT + (hi_p - p) / (hi_p - lo_p) * (H - MT - MB)
    cw = (W - ML - MR) / ((T1 - T0) / 5.0)
    o: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="11">',
                    "<style>text{paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}</style>", f'<rect width="{W}" height="{H}" fill="white"/>', f'<text x="{ML}" y="22" font-size="15" font-weight="bold">{escape(title)}</text>',
                    f'<text x="{ML}" y="40" fill="#555">real 5-minute candles (IST); markers sit at their exact 1-minute positions; synthetic index points, not a tradable price</text>']
    for k in range(7):
        p = lo_p + (hi_p - lo_p) * k / 6
        o.append(f'<line x1="{ML}" x2="{W - MR}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eee"/><text x="6" y="{y(p) + 4:.1f}" fill="#555">{p:,.0f}</text>')
    for hh in range(9, 16):
        for mm in (0, 30):
            m = hh * 60 + mm
            if T0 <= m <= T1:
                o.append(f'<line x1="{_x(m):.1f}" x2="{_x(m):.1f}" y1="{MT}" y2="{H - MB}" stroke="#f3f3f3"/><text x="{_x(m) - 14:.1f}" y="{H - MB + 16}" fill="#555">{hh:02d}:{mm:02d}</text>')
    for z_label, zlo, zhi, col in levels.get("zones", []):
        o.append(f'<rect x="{ML}" y="{y(zhi):.1f}" width="{W - ML - MR}" height="{max(y(zlo) - y(zhi), 1.5):.1f}" fill="{col}" opacity="0.14"/>'
                 f'<text x="{W - MR + 4}" y="{y(zhi) + 10:.1f}" fill="{col}" font-size="10">{escape(z_label)} [{zlo:,.2f}, {zhi:,.2f}]</text>')
    for lab, v, col in levels.get("hlines", []):
        if v is not None:
            o.append(f'<line x1="{ML}" x2="{W - MR}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-dasharray="6,4"/>'
                     f'<text x="{W - MR + 4}" y="{y(v) + 3:.1f}" fill="{col}" font-size="10">{escape(lab)} {v:,.2f}</text>')
    pts = " ".join(f"{_x(_min(c.start) + 2.5):.1f},{y(c.ema):.1f}" for c in cs if c.ema == c.ema and lo_p <= c.ema <= hi_p)
    if pts:
        o.append(f'<polyline points="{pts}" fill="none" stroke="#f9a825" stroke-width="1.6"/><text x="{ML + 4}" y="{H - 8}" fill="#f9a825">{escape(ema_label)}</text>')
    for c in cs:
        xm = _x(_min(c.start) + 2.5)
        col = "#2e7d32" if c.c >= c.o else "#c62828"
        o.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{y(c.h):.1f}" y2="{y(c.l):.1f}" stroke="{col}"/>'
                 f'<rect x="{xm - cw * 0.34:.1f}" y="{y(max(c.o, c.c)):.1f}" width="{cw * 0.68:.1f}" height="{max(abs(y(c.o) - y(c.c)), 1):.1f}" fill="{col}"/>')
    stack: dict[int, int] = {}
    for start, text in (marks or []):
        k = int(_min(start))
        stack[k] = stack.get(k, 0) + 1
        cx = next((c for c in cs if c.start == start), None)
        if cx is not None:
            o.append(f'<text x="{_x(_min(start) + 2.5):.1f}" y="{y(cx.h) - 4 - 10 * (stack[k] - 1):.1f}" text-anchor="middle" font-size="9" fill="#37474f" font-weight="bold">{escape(text)}</text>')
    # the trade: lines from the entry to the last exit (or the end of the day)
    ex_min = [_min(e[0]) for e in trade["exits"] if e[0] is not None]
    xe0 = _x(_min(trade["entry_ts"]))
    xe1 = _x(max(ex_min) if ex_min else T1)
    x_t1 = _x(_min(trade["post_t1_from"])) if trade.get("post_t1_from") is not None else xe0
    for lab, v, col, dash in (("entry", trade["entry"], "#000", ""), ("original stop", trade["stop"], "#c62828", "5,3"), ("Target 1", trade["t1"], "#2e7d32", "5,3"),
                              ("Target 2", trade["t2"], "#1b5e20", "5,3"), ("post-T1 stop", trade["post_t1"], "#ef6c00", "2,3")):
        if v is None:
            continue
        xs = x_t1 if lab == "post-T1 stop" else xe0
        o.append(f'<line x1="{xs:.1f}" x2="{xe1:.1f}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width="1.6"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>"
                 f'<text x="{xe1 + 3:.1f}" y="{y(v) + 3:.1f}" fill="{col}" font-size="10">{lab} {v:,.2f}</text>')
    o.append(f'<polygon points="{xe0:.1f},{y(trade["entry"]):.1f} {xe0 - 7:.1f},{y(trade["entry"]) + (14 if trade["direction"] == "LONG" else -14):.1f} {xe0 + 7:.1f},{y(trade["entry"]) + (14 if trade["direction"] == "LONG" else -14):.1f}" fill="#000"/>'
             f'<text x="{xe0 + 9:.1f}" y="{y(trade["entry"]) + (26 if trade["direction"] == "LONG" else -18):.1f}" font-weight="bold">{trade["direction"]} entry {trade["entry"]:,.2f} @ {trade["entry_ts"]:%H:%M}</text>')
    for k, (ts, price, lab) in enumerate(trade["exits"]):
        if ts is None or price is None:
            continue
        xx = _x(_min(ts))
        o.append(f'<circle cx="{xx:.1f}" cy="{y(price):.1f}" r="5" fill="#fff" stroke="#6a1b9a" stroke-width="2"/>'
                 f'<text x="{xx + 7:.1f}" y="{y(price) - 7 - 12 * k:.1f}" fill="#6a1b9a" font-weight="bold">{escape(lab)} {price:,.2f} @ {ts:%H:%M}</text>')
    for k, m in enumerate(manual):
        hhmm = m["label"]
        mins = int(hhmm[:2]) * 60 + int(hhmm[3:])
        xx = _x(mins + 2.5)
        o.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{MT}" y2="{H - MB}" stroke="#d500f9" stroke-dasharray="2,3"/>'
                 f'<text x="{xx + 3:.1f}" y="{MT + 12 + 12 * k}" fill="#d500f9" font-size="10">MANUAL {escape(m["text"])}</text>')
    for lab, m in (("13:00 entry cutoff", 13 * 60), ("15:14 provisional forced exit", 15 * 60 + 14)):
        o.append(f'<line x1="{_x(m):.1f}" x2="{_x(m):.1f}" y1="{MT}" y2="{H - MB}" stroke="#777" stroke-dasharray="1,4"/><text x="{_x(m) - 50:.1f}" y="{MT - 4}" fill="#777" font-size="10">{lab}</text>')
    o.append("</svg>")
    return "\n".join(o)
