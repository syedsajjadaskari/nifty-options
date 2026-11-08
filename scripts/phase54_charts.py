"""Phase 5.4: SVG case-study charts for the ORB audit. A chart shows the last previous-session candles and the opening hours of the session, the EMA(200), and every level the audit discusses, with a legend that keeps four
kinds of marks apart: HISTORICAL PRICES (candles, EMA), SOURCE-DEFINED levels (the previous day's high / low), PROVISIONAL reconstructed levels / trendline (dashed; research constructions, not source rules) and the AUTHOR-EXPECTED
entry (the handwritten pages contain NO ORB drawing, so the expected entry is only the rulebook's 09:20 decision time, drawn as an inferred mark)."""

from __future__ import annotations

import html
import math

W, H, L, R, T, B = 1320, 680, 70, 190, 52, 78


def _t(x) -> str:
    return f"{x:%H:%M}"


def render(title: str, prev_rows: list[dict], today_rows: list[dict], levels: list[dict], trend: dict | None, marks: list[dict], first_box: bool = True, note: str = "") -> str:
    """prev_rows / today_rows: dicts with start, open, high, low, close, ema (floats; start a datetime). levels: {price, label, kind in SOURCE|PROVISIONAL|CURRENT|CONTEXT, side}. trend: {x1_idx, y1, x2_idx, y2, label}
    with indices into the concatenated candle list. marks: {idx, price, label, colour, shape}."""
    rows = prev_rows + today_rows
    n = len(rows)
    ys = [r["low"] for r in rows] + [r["high"] for r in rows] + [lv["price"] for lv in levels if lv["price"] is not None]
    emas = [r["ema"] for r in rows if r.get("ema") is not None and not math.isnan(r["ema"])]
    lo, hi = min(ys), max(ys)
    if emas:
        # include the EMA only if it is within a sensible distance of the price range (avoid flattening the candles)
        lo = min(lo, min(e for e in emas if e > lo - 0.6 * (hi - lo)) if any(e > lo - 0.6 * (hi - lo) for e in emas) else lo)
        hi = max(hi, max(e for e in emas if e < hi + 0.6 * (hi - lo)) if any(e < hi + 0.6 * (hi - lo) for e in emas) else hi)
    pad = 0.06 * (hi - lo or 1)
    lo, hi = lo - pad, hi + pad
    pw, ph = W - L - R, H - T - B
    xw = pw / n

    def X(i: float) -> float:
        return L + (i + 0.5) * xw

    def Y(p: float) -> float:
        return T + (hi - p) / (hi - lo) * ph
    o: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
                    f'<text x="{L}" y="22" font-size="15" font-weight="bold" fill="#111">{html.escape(title)}</text>']
    if note:
        o.append(f'<text x="{L}" y="40" fill="#555">{html.escape(note)}</text>')
    step = (hi - lo) / 8
    for k in range(9):
        p = lo + k * step
        o.append(f'<line x1="{L}" y1="{Y(p):.1f}" x2="{L + pw}" y2="{Y(p):.1f}" stroke="#eee"/><text x="6" y="{Y(p) + 4:.1f}" fill="#777">{p:.0f}</text>')
    split = len(prev_rows)
    o.append(f'<line x1="{L + split * xw:.1f}" y1="{T}" x2="{L + split * xw:.1f}" y2="{T + ph}" stroke="#888" stroke-dasharray="4 3"/><text x="{L + split * xw + 4:.1f}" y="{T + 12}" fill="#888">09:15 (session open)</text>')
    for i, r in enumerate(rows):
        col = "#1b9e77" if r["close"] >= r["open"] else "#d6304a"
        x = X(i)
        o.append(f'<line x1="{x:.1f}" y1="{Y(r["high"]):.1f}" x2="{x:.1f}" y2="{Y(r["low"]):.1f}" stroke="{col}"/>')
        top, bot = Y(max(r["open"], r["close"])), Y(min(r["open"], r["close"]))
        o.append(f'<rect x="{x - xw * 0.32:.1f}" y="{top:.1f}" width="{xw * 0.64:.1f}" height="{max(bot - top, 1):.1f}" fill="{col}"/>')
    pts = [f"{X(i):.1f},{Y(r['ema']):.1f}" for i, r in enumerate(rows) if r.get("ema") is not None and not math.isnan(r["ema"]) and lo <= r["ema"] <= hi]
    if len(pts) > 1:
        o.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#2a6fdb" stroke-width="1.6"/>')
    if first_box and today_rows:
        r = today_rows[0]
        x = X(split)
        o.append(f'<rect x="{x - xw * 0.6:.1f}" y="{Y(r["high"]) - 4:.1f}" width="{xw * 1.2:.1f}" height="{Y(r["low"]) - Y(r["high"]) + 8:.1f}" fill="none" stroke="#e6a100" stroke-width="2"/>')
    style = {"SOURCE": ("#b8860b", "", 2.0), "CURRENT": ("#e07b00", "6 3", 1.6), "PROVISIONAL": ("#7b3fa0", "3 3", 1.3), "CONTEXT": ("#888", "2 4", 1.0)}
    ly = {}
    for lv in levels:
        if lv["price"] is None or not (lo <= lv["price"] <= hi):
            continue
        c, dash, sw = style[lv["kind"]]
        y = Y(lv["price"])
        o.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L + pw}" y2="{y:.1f}" stroke="{c}" stroke-width="{sw}" {f"stroke-dasharray={chr(34)}{dash}{chr(34)}" if dash else ""}/>')
        yy = y
        while any(abs(yy - v) < 11 for v in ly.values()):
            yy += 11
        ly[lv["label"]] = yy
        o.append(f'<text x="{L + pw + 4}" y="{yy + 3:.1f}" fill="{c}">{html.escape(lv["label"])} {lv["price"]:.2f}</text>')
    if trend and trend.get("y1") is not None:
        x1, x2 = trend["x1_idx"], trend["x2_idx"] + (n - 1 - trend["x2_idx"])
        slope = (trend["y2"] - trend["y1"]) / (trend["x2_idx"] - trend["x1_idx"])
        ya, yb = trend["y1"], trend["y1"] + slope * (x2 - x1)
        o.append(f'<line x1="{X(x1):.1f}" y1="{Y(ya):.1f}" x2="{X(x2):.1f}" y2="{Y(yb):.1f}" stroke="#7b3fa0" stroke-width="1.3" stroke-dasharray="8 4"/><text x="{X(x1):.1f}" y="{Y(ya) + 14:.1f}" fill="#7b3fa0">{html.escape(trend["label"])}</text>')
    for m in marks:
        x, y = X(m["idx"]), Y(m["price"])
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{m["colour"]}" stroke="#fff"/><text x="{x + 8:.1f}" y="{y - 8:.1f}" fill="{m["colour"]}" font-weight="bold">{html.escape(m["label"])}</text>')
    for k in range(0, n, 6):
        o.append(f'<text x="{X(k) - 12:.1f}" y="{H - B + 14}" fill="#777">{_t(rows[k]["start"])}</text>')
    lg = [("#1b9e77", "candle (historical)"), ("#2a6fdb", "EMA(200) (historical)"), ("#b8860b", "SOURCE-DEFINED level (Method 1: previous-day high/low)"), ("#e07b00", "frozen engine's Method 2 inner level (research assumption)"),
          ("#7b3fa0", "PROVISIONAL reconstructed level / trendline (not a source rule)"), ("#e6a100", "first 09:15-09:20 candle"), ("#2e7d32", "AUTHOR-EXPECTED entry (inferred: no ORB drawing exists)"), ("#d81b60", "Phase 3.6 automated entry")]
    for k, (c, t) in enumerate(lg):
        row = k // 3
        col = k % 3
        o.append(f'<rect x="{L + col * 420}" y="{T + ph + 40 + row * 14 - 9}" width="10" height="10" fill="{c}"/><text x="{L + col * 420 + 14}" y="{T + ph + 40 + row * 14}" fill="#333">{html.escape(t)}</text>')
    o.append("</svg>")
    return "\n".join(o)
