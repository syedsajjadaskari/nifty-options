"""Hand-written SVG candlestick charts (no plotting dependency). One function, ``candle_chart``; annotations are data, not code."""

from __future__ import annotations

import base64
import textwrap
from html import escape
from pathlib import Path

GREEN, RED, GREY, BLUE, PURPLE, ORANGE, TXT = "#1f8a5b", "#c0392b", "#8a8f98", "#2b6cb0", "#6b46c1", "#d9822b", "#222"


def candle_chart(title: str, subtitle: str, candles: list, hlines: list[tuple], marks: list[tuple], boxes: list[tuple] | None = None, notes: list[str] | None = None,
                 width: int = 1180, height: int = 560, embed_png: str | None = None) -> str:
    """candles: Candle objects. hlines: (price, label, colour, dashed). marks: (timestamp, price, label, colour). boxes: (t0, t1, p0, p1, colour) translucent rectangles (position tool).
    notes: text rows under the chart. embed_png: path of a source screenshot embedded on top (side-by-side verification)."""
    notes = [ln for n in (notes or []) for ln in (textwrap.wrap(n, 185) or [''])]
    pad_l, pad_r, pad_t, pad_b = 70, 190, 54, 44
    img_h = 0
    img_svg = ""
    if embed_png and Path(embed_png).exists():
        from PIL import Image

        iw, ih = Image.open(embed_png).size
        img_h = int((width - 20) * ih / iw) + 28
        b64 = base64.b64encode(Path(embed_png).read_bytes()).decode()
        img_svg = (f'<text x="10" y="{pad_t + 14}" font-size="12" fill="{TXT}" font-weight="bold">SOURCE SCREENSHOT (embedded from the rulebook PDF at original resolution)</text>'
                   f'<image x="10" y="{pad_t + 20}" width="{width - 20}" height="{img_h - 28}" href="data:image/png;base64,{b64}"/>')
    top = pad_t + img_h
    ch_h = height - pad_t - pad_b
    total_h = top + ch_h + pad_b + 16 * len(notes) + 20
    lo = min([c.low for c in candles] + [h[0] for h in hlines if h[0]])
    hi = max([c.high for c in candles] + [h[0] for h in hlines if h[0]])
    span = (hi - lo) or 1.0
    lo, hi = lo - 0.04 * span, hi + 0.04 * span
    t0, t1 = candles[0].start, candles[-1].end
    tspan = (t1 - t0).total_seconds()
    pw = width - pad_l - pad_r

    def X(t):
        return pad_l + pw * (t - t0).total_seconds() / tspan

    def Y(p):
        return top + ch_h * (1 - (p - lo) / (hi - lo))

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{total_h}" viewBox="0 0 {width} {total_h}" font-family="Helvetica,Arial,sans-serif" font-size="11">',
         f'<rect width="{width}" height="{total_h}" fill="white"/>', f'<text x="10" y="20" font-size="15" font-weight="bold" fill="{TXT}">{escape(title)}</text>',
         f'<text x="10" y="38" font-size="11" fill="{GREY}">{escape(subtitle)}</text>', img_svg,
         f'<rect x="{pad_l}" y="{top}" width="{pw}" height="{ch_h}" fill="#fafafa" stroke="#ddd"/>']
    for k in range(6):  # y grid
        p = lo + (hi - lo) * k / 5
        o.append(f'<line x1="{pad_l}" x2="{pad_l + pw}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="#eee"/><text x="{pad_l - 6}" y="{Y(p) + 4:.1f}" text-anchor="end" fill="{GREY}">{p:,.1f}</text>')
    last_lab = None
    for c in candles:  # x ticks every 30 minutes
        if c.start.minute % 30 == 0 and c.start != last_lab:
            last_lab = c.start
            o.append(f'<line x1="{X(c.start):.1f}" x2="{X(c.start):.1f}" y1="{top}" y2="{top + ch_h}" stroke="#eee"/><text x="{X(c.start):.1f}" y="{top + ch_h + 14}" text-anchor="middle" fill="{GREY}">{c.start:%H:%M}</text>')
    for (a, b, p0, p1, col) in boxes or []:
        o.append(f'<rect x="{X(a):.1f}" y="{Y(max(p0, p1)):.1f}" width="{max(X(b) - X(a), 2):.1f}" height="{abs(Y(p0) - Y(p1)):.1f}" fill="{col}" fill-opacity="0.13" stroke="{col}" stroke-opacity="0.4"/>')
    for (p, lab, col, dash) in hlines:
        d = ' stroke-dasharray="6,4"' if dash else ""
        o.append(f'<line x1="{pad_l}" x2="{pad_l + pw}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" stroke="{col}" stroke-width="1.2"{d}/><text x="{pad_l + pw + 4}" y="{Y(p) + 4:.1f}" fill="{col}">{escape(lab)}</text>')
    cw = max(pw / len(candles) * 0.6, 2.0)
    for c in candles:
        col = GREEN if c.close >= c.open else RED
        x = X(c.start) + (X(c.end) - X(c.start)) / 2
        o.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(c.high):.1f}" y2="{Y(c.low):.1f}" stroke="{col}"/>')
        y1, y2 = Y(max(c.open, c.close)), Y(min(c.open, c.close))
        o.append(f'<rect x="{x - cw / 2:.1f}" y="{y1:.1f}" width="{cw:.1f}" height="{max(y2 - y1, 1):.1f}" fill="{col}"/>')
    for (t, p, lab, col) in marks:
        x, y = X(t), Y(p)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="4.5" fill="none" stroke="{col}" stroke-width="2"/><text x="{x + 6:.1f}" y="{y - 7:.1f}" fill="{col}" font-weight="bold">{escape(lab)}</text>')
    for i, n in enumerate(notes):
        o.append(f'<text x="10" y="{top + ch_h + pad_b + 4 + 16 * i}" fill="{TXT}">{escape(n)}</text>')
    o.append("</svg>")
    return "\n".join(o)


def spec_card(title: str, subtitle: str, lines: list[str], embed_png: str | None = None, width: int = 1180) -> str:
    """A text card (optionally with the source screenshot) for examples that cannot be replayed on market data."""
    img_h, img_svg = 0, ""
    if embed_png and Path(embed_png).exists():
        from PIL import Image

        iw, ih = Image.open(embed_png).size
        img_h = int((width - 20) * ih / iw)
        b64 = base64.b64encode(Path(embed_png).read_bytes()).decode()
        img_svg = f'<image x="10" y="52" width="{width - 20}" height="{img_h}" href="data:image/png;base64,{b64}"/>'
    lines = [ln for n in lines for ln in (textwrap.wrap(n, 175) or [''])]
    h = 60 + img_h + 20 * len(lines) + 20
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{h}" viewBox="0 0 {width} {h}" font-family="Helvetica,Arial,sans-serif" font-size="12">', f'<rect width="{width}" height="{h}" fill="white"/>',
         f'<text x="10" y="20" font-size="15" font-weight="bold" fill="{TXT}">{escape(title)}</text>', f'<text x="10" y="38" fill="{GREY}">{escape(subtitle)}</text>', img_svg]
    for i, ln in enumerate(lines):
        o.append(f'<text x="10" y="{60 + img_h + 20 * i + 14}" fill="{TXT}">{escape(ln)}</text>')
    o.append("</svg>")
    return "\n".join(o)
