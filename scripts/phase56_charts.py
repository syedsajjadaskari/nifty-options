"""Phase 5.6: SVG charts for the manual-versus-automated reconciliation. Actual underlying five-minute candles of the previous session's last hour and the session until early afternoon, the EMA(200), the previous day's high / low, the manual journal entries
(the journal labels the five-minute candle START; no price is recorded, so a manual entry is drawn at that candle's open) and the automated entries of configurations A / B / C, drawn in their signal candle's column at the actual fill price. Nothing here invents a manual price."""

from __future__ import annotations

import html
import math

W, H, L, R, T, B = 1320, 640, 70, 150, 52, 90
COLOURS = {"MANUAL": "#1565c0", "A": "#d81b60", "B": "#2e7d32", "C": "#ef6c00", "SIGNAL": "#888888"}


def render(title: str, prev_rows: list[dict], today_rows: list[dict], levels: list[tuple[str, float]], marks: list[dict], note: str = "") -> str:
    """rows: dicts start (datetime), open, high, low, close, ema. levels: (label, price). marks: {idx (index in prev_rows + today_rows), price, label, kind in MANUAL | A | B | C | SIGNAL}."""
    rows = prev_rows + today_rows
    n = len(rows)
    ys = [r["low"] for r in rows] + [r["high"] for r in rows] + [p for _l, p in levels]
    lo, hi = min(ys), max(ys)
    emas = [r["ema"] for r in rows if r.get("ema") is not None and not math.isnan(r["ema"]) and lo - 0.5 * (hi - lo) <= r["ema"] <= hi + 0.5 * (hi - lo)]
    if emas:
        lo, hi = min(lo, min(emas)), max(hi, max(emas))
    pad = 0.05 * (hi - lo or 1)
    lo, hi = lo - pad, hi + pad
    pw, ph = W - L - R, H - T - B
    xw = pw / n

    def X(i: float) -> float:
        return L + (i + 0.5) * xw

    def Y(p: float) -> float:
        return T + (hi - p) / (hi - lo) * ph
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
         f'<text x="{L}" y="22" font-size="15" font-weight="bold" fill="#111">{html.escape(title)}</text>']
    if note:
        o.append(f'<text x="{L}" y="40" fill="#555">{html.escape(note)}</text>')
    for k in range(9):
        p = lo + k * (hi - lo) / 8
        o.append(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{L + pw}" y2="{Y(p):.1f}" stroke="#eee"/><text x="6" y="{Y(p) + 4:.1f}" fill="#777">{p:.0f}</text>')
    split = len(prev_rows)
    o.append(f'<line x1="{L + split * xw:.1f}" y1="{T}" x2="{L + split * xw:.1f}" y2="{T + ph}" stroke="#888" stroke-dasharray="4 3"/><text x="{L + split * xw + 4:.1f}" y="{T + 12}" fill="#888">09:15 open</text>')
    for i, r in enumerate(rows):
        col = "#1b9e77" if r["close"] >= r["open"] else "#d6304a"
        x = X(i)
        o.append(f'<line x1="{x:.1f}" y1="{Y(r["high"]):.1f}" x2="{x:.1f}" y2="{Y(r["low"]):.1f}" stroke="{col}"/>')
        top, bot = Y(max(r["open"], r["close"])), Y(min(r["open"], r["close"]))
        o.append(f'<rect x="{x - xw * 0.32:.1f}" y="{top:.1f}" width="{xw * 0.64:.1f}" height="{max(bot - top, 1):.1f}" fill="{col}"/>')
    pts = [f"{X(i):.1f},{Y(r['ema']):.1f}" for i, r in enumerate(rows) if r.get("ema") is not None and not math.isnan(r["ema"]) and lo <= r["ema"] <= hi]
    if len(pts) > 1:
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#2a6fdb" stroke-width="1.6"/>')
    ly: list[float] = []
    for label, price in levels:
        if not lo <= price <= hi:
            continue
        y = Y(price)
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L + pw}" y2="{y:.1f}" stroke="#b8860b" stroke-width="1.4" stroke-dasharray="6 3"/>')
        yy = y
        while any(abs(yy - v) < 11 for v in ly):
            yy += 11
        ly.append(yy)
        o.append(f'<text x="{L + pw + 4}" y="{yy + 3:.1f}" fill="#b8860b">{html.escape(label)} {price:.2f}</text>')
    taken: list[tuple[float, float]] = []
    for m in marks:
        x, y = X(m["idx"]), Y(m["price"])
        yy = y - 10
        while any(abs(x - tx) < 120 and abs(yy - ty) < 12 for tx, ty in taken):
            yy -= 12
        taken.append((x, yy))
        c = COLOURS[m["kind"]]
        shape = f'<polygon points="{x:.1f},{y - 7:.1f} {x - 6:.1f},{y + 5:.1f} {x + 6:.1f},{y + 5:.1f}" fill="{c}" stroke="#fff"/>' if m["kind"] == "MANUAL" else f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{c}" stroke="#fff"/>'
        o.append(shape + f'<text x="{x + 8:.1f}" y="{yy:.1f}" fill="{c}" font-weight="bold">{html.escape(m["label"])}</text>')
    for k in range(0, n, 6):
        o.append(f'<text x="{X(k) - 12:.1f}" y="{H - B + 14}" fill="#777">{rows[k]["start"]:%H:%M}</text>')
    lg = [("#1b9e77", "candle (actual one-minute data aggregated to 5 minutes)"), ("#2a6fdb", "EMA(200)"), ("#b8860b", "previous-day high / low"), (COLOURS["MANUAL"], "manual journal entry (candle-start label; NO price recorded: drawn at the candle open)"),
          (COLOURS["A"], "automated entry A (frozen Phase 3.6)"), (COLOURS["B"], "automated entry B (Phase 5.3 author-corrected)"), (COLOURS["C"], "automated entry C (B + ORB gap crossing)")]
    for k, (c, t) in enumerate(lg):
        row, col = k // 2, k % 2
        o.append(f'<rect x="{L + col * 620}" y="{T + ph + 30 + row * 14 - 9}" width="10" height="10" fill="{c}"/><text x="{L + col * 620 + 14}" y="{T + ph + 30 + row * 14}" fill="#333">{html.escape(t)}</text>')
    o.append("</svg>")
    return "\n".join(o)
