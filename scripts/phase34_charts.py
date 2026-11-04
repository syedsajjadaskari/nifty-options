"""Phase 3.4: per-case annotated SVG charts on REAL candles (rebuilt from the verified one-minute data by the engine's session contexts). No candle is invented.

Panels: (1) the previous session with the previous-day high, the legacy reversal zone (grey, diagnostic) and the candidate zones with their source candles; (2) a ZOOM on the test and the
confirmation candle(s) with the pattern verdicts and the close measured against the zone ceiling; (3) the whole session with the open, the entry and the journal rows.
"""

from __future__ import annotations

import textwrap
from html import escape

W, H = 1500, 1040
GREEN, RED = "#2e7d32", "#c62828"
COLORS = {"A": "#1565c0", "B": "#7b1fa2", "LEGACY": "#757575", "DRAWN": "#ef6c00"}


class Panel:
    def __init__(self, x0, y0, w, h, lo, hi, n):
        self.x0, self.y0, self.w, self.h, self.lo, self.hi, self.n = x0, y0, w, h, lo, hi, n

    def y(self, p):
        return self.y0 + (self.hi - p) / (self.hi - self.lo) * self.h

    def x(self, i):
        return self.x0 + (i + 0.5) / self.n * self.w

    @property
    def cw(self):
        return self.w / self.n


def _frame(p, title, out, ticks=5):
    out.append(f'<rect x="{p.x0}" y="{p.y0}" width="{p.w}" height="{p.h}" fill="#fff" stroke="#bbb"/><text x="{p.x0}" y="{p.y0 - 8}" font-size="13" font-weight="bold">{escape(title)}</text>')
    for k in range(ticks + 1):
        v = p.lo + (p.hi - p.lo) * k / ticks
        out.append(f'<line x1="{p.x0}" x2="{p.x0 + p.w}" y1="{p.y(v):.1f}" y2="{p.y(v):.1f}" stroke="#eee"/><text x="{p.x0 - 4}" y="{p.y(v) + 4:.1f}" text-anchor="end" fill="#555" font-size="10">{v:,.1f}</text>')


def _candles(p, cs, out, start_pos=0, shade_from=None):
    for k, c in enumerate(cs):
        col = GREEN if c.c >= c.o else RED
        xm = p.x(start_pos + k)
        op = 0.45 if (shade_from is not None and k >= shade_from) else 1.0
        out.append(f'<g opacity="{op}"><line x1="{xm:.1f}" x2="{xm:.1f}" y1="{p.y(c.h):.1f}" y2="{p.y(c.l):.1f}" stroke="{col}"/>'
                   f'<rect x="{xm - p.cw * 0.34:.1f}" y="{p.y(max(c.o, c.c)):.1f}" width="{p.cw * 0.68:.1f}" height="{max(abs(p.y(c.o) - p.y(c.c)), 1):.1f}" fill="{col}"/></g>')


def _zone(p, z, out, row, x_from=None):
    """z = dict(label, floor, ceiling, key). ``row`` staggers the labels of several zones."""
    col = COLORS[z["key"]]
    xs = p.x0 if x_from is None else max(p.x0, x_from)
    out.append(f'<rect x="{xs:.1f}" y="{p.y(z["ceiling"]):.1f}" width="{p.x0 + p.w - xs:.1f}" height="{max(p.y(z["floor"]) - p.y(z["ceiling"]), 1.5):.1f}" fill="{col}" opacity="0.13"/>')
    out.append(f'<line x1="{xs:.1f}" x2="{p.x0 + p.w}" y1="{p.y(z["ceiling"]):.1f}" y2="{p.y(z["ceiling"]):.1f}" stroke="{col}" stroke-width="1.5"/>')
    out.append(f'<line x1="{xs:.1f}" x2="{p.x0 + p.w}" y1="{p.y(z["floor"]):.1f}" y2="{p.y(z["floor"]):.1f}" stroke="{col}" stroke-dasharray="5,3"/>')
    out.append(f'<rect x="{p.x0 + 6}" y="{p.y0 + 5 + 13 * row:.1f}" width="9" height="9" fill="{col}" opacity="0.5"/>'
               f'<text x="{p.x0 + 19}" y="{p.y0 + 13 + 13 * row:.1f}" fill="{col}" font-size="10" font-weight="bold">{escape(z["label"])} [{z["floor"]:,.2f}, {z["ceiling"]:,.2f}]</text>')


def _range(cs, extra, pad=0.06):
    lo = min([c.l for c in cs] + extra)
    hi = max([c.h for c in cs] + extra)
    d = (hi - lo) * pad + 1
    return lo - d, hi + d


def render(job: dict) -> str:  # noqa: C901
    """job: title, subtitle, prev_cs, cs, zones (list of dict label/floor/ceiling/key), prev_high, prev_high_candle, source_starts (key -> list of 'HH:MM'), conf_idx, test_idx, zoom (a, b),
    entry (price, 'HH:MM') or None, pattern_lines (list of text), caption (list of text), manual (list of dict), open_price, gap_points"""
    prev, cs, zones = job["prev_cs"], job["cs"], job["zones"]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', "<style>text{paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}</style>",
           f'<rect width="{W}" height="{H}" fill="#fafafa"/>', f'<text x="20" y="24" font-size="16" font-weight="bold">{escape(job["title"])}</text>', f'<text x="20" y="42" fill="#555">{escape(job["subtitle"])}</text>']
    allz = [v for z in zones for v in (z["floor"], z["ceiling"])]
    # ---- panel 1: previous session
    lo1, hi1 = _range(prev, allz + [job["prev_high"]])
    p1 = Panel(70, 80, 560, 330, lo1, hi1, len(prev))
    _frame(p1, f"1. Previous session {job['prev_date']}: previous-day high, zone sources", out)
    for row, z in enumerate(zones):
        starts = job["source_starts"].get(z["key"], [])
        first = min((i for i, c in enumerate(prev) if f"{c.start:%H:%M}" in starts), default=None)
        _zone(p1, z, out, row, x_from=(p1.x(first) - p1.cw / 2) if first is not None else None)
    out.append(f'<line x1="{p1.x0}" x2="{p1.x0 + p1.w}" y1="{p1.y(job["prev_high"]):.1f}" y2="{p1.y(job["prev_high"]):.1f}" stroke="#b71c1c" stroke-dasharray="3,3"/>'
               f'<text x="{p1.x0 + p1.w - 4}" y="{p1.y(job["prev_high"]) - 3:.1f}" text-anchor="end" fill="#b71c1c" font-size="10">previous-day high {job["prev_high"]:,.2f} ({job["prev_high_candle"]})</text>')
    _candles(p1, prev, out)
    for key, starts in job["source_starts"].items():
        for st in starts:
            i = next((k for k, c in enumerate(prev) if f"{c.start:%H:%M}" == st), None)
            if i is None:
                continue
            c = prev[i]
            out.append(f'<rect x="{p1.x(i) - p1.cw * 0.6:.1f}" y="{p1.y(c.h) - 3:.1f}" width="{p1.cw * 1.2:.1f}" height="{p1.y(c.l) - p1.y(c.h) + 6:.1f}" fill="none" stroke="{COLORS[key]}" stroke-width="2"/>')
    # ---- panel 2: zoom
    a, b = job["zoom"]
    win = cs[a:b]
    lo2, hi2 = _range(win, allz + ([job["entry"][0]] if job.get("entry") else []), 0.09)
    p2 = Panel(700, 80, 780, 330, lo2, hi2, len(win))
    _frame(p2, "2. ZOOM: test and confirmation candle (shaded = after the entry, context only)", out)
    for row, z in enumerate(zones):
        _zone(p2, z, out, row)
    ci = job.get("conf_idx")
    _candles(p2, win, out, 0, shade_from=(ci - a + 1) if ci is not None else None)
    if job.get("test_idx") is not None and a <= job["test_idx"] < b:
        c = cs[job["test_idx"]]
        out.append(f'<text x="{p2.x(job["test_idx"] - a):.1f}" y="{p2.y(c.l) + 14:.1f}" text-anchor="middle" font-weight="bold" fill="#6a1b9a">TEST {c.start:%H:%M}</text>')
    if ci is not None and a <= ci < b:
        c = cs[ci]
        out.append(f'<text x="{p2.x(ci - a):.1f}" y="{p2.y(c.h) - 6:.1f}" text-anchor="middle" font-weight="bold" fill="#1b5e20">CONFIRMATION CANDLE {c.start:%H:%M}</text>')
        ceil = zones[0]["ceiling"]
        xc = p2.x(ci - a) + p2.cw * 0.5
        col = "#1b5e20" if c.c > ceil else "#d50000"
        out.append(f'<line x1="{xc:.1f}" x2="{xc:.1f}" y1="{p2.y(ceil):.1f}" y2="{p2.y(c.c):.1f}" stroke="{col}" stroke-width="2.5"/>'
                   f'<text x="{xc - 6:.1f}" y="{(p2.y(ceil) + p2.y(c.c)) / 2:.1f}" text-anchor="end" fill="{col}" font-weight="bold">close {c.c:,.2f}: {abs(c.c - ceil):,.2f} pts {"ABOVE" if c.c > ceil else "NOT above"} the {zones[0]["label"]} ceiling</text>')
    if job.get("entry") and ci is not None:
        xe = p2.x(ci - a) + p2.cw * 0.5
        out.append(f'<polygon points="{xe:.1f},{p2.y(job["entry"][0]):.1f} {xe + 9:.1f},{p2.y(job["entry"][0]) - 6:.1f} {xe + 9:.1f},{p2.y(job["entry"][0]) + 6:.1f}" fill="#000"/>'
                   f'<text x="{xe + 12 if xe < p2.x0 + 0.55 * p2.w else xe - 4:.1f}" y="{p2.y(job["entry"][0]) + 4:.1f}" text-anchor="{"start" if xe < p2.x0 + 0.55 * p2.w else "end"}" font-weight="bold">entry {job["entry"][0]:,.2f} @ {job["entry"][1]} (open of the next 1-min bar)</text>')
    for k, ln in enumerate(job.get("pattern_lines", [])[:6]):
        out.append(f'<text x="{p2.x0 + 6}" y="{p2.y0 + p2.h - 6 - 12 * (len(job["pattern_lines"][:6]) - 1 - k)}" fill="#333" font-size="10">{escape(ln)}</text>')
    # ---- panel 3: whole session
    lo3, hi3 = _range(cs, allz + [job["prev_high"]], 0.03)
    p3 = Panel(70, 470, 1410, 400, lo3, hi3, len(cs))
    _frame(p3, f"3. Session {job['date']}: open {job['open_price']:,.2f} (gap {job['gap_points']:+.2f} vs the official close); zones extended forward; entry; journal", out, 6)
    for row, z in enumerate(zones):
        _zone(p3, z, out, row)
    out.append(f'<line x1="{p3.x0}" x2="{p3.x0 + p3.w}" y1="{p3.y(job["prev_high"]):.1f}" y2="{p3.y(job["prev_high"]):.1f}" stroke="#b71c1c" stroke-dasharray="3,3"/>'
               f'<text x="{p3.x0 + p3.w - 4}" y="{p3.y(job["prev_high"]) - 3:.1f}" text-anchor="end" fill="#b71c1c" font-size="10">previous-day high {job["prev_high"]:,.2f}</text>')
    out.append(f'<line x1="{p3.x0}" x2="{p3.x0 + p3.w}" y1="{p3.y(job["open_price"]):.1f}" y2="{p3.y(job["open_price"]):.1f}" stroke="#455a64" stroke-dasharray="1,3"/>'
               f'<text x="{p3.x0 + p3.w - 4}" y="{p3.y(job["open_price"]) + 11:.1f}" text-anchor="end" fill="#455a64" font-size="10">session open {job["open_price"]:,.2f}</text>')
    _candles(p3, cs, out, 0, shade_from=(ci + 1) if ci is not None else None)
    if job.get("test_idx") is not None:
        out.append(f'<text x="{p3.x(job["test_idx"]):.1f}" y="{p3.y(cs[job["test_idx"]].h) - 6:.1f}" text-anchor="middle" font-weight="bold" fill="#6a1b9a">TEST</text>')
    if ci is not None:
        out.append(f'<text x="{p3.x(ci):.1f}" y="{p3.y(cs[ci].h) - 6:.1f}" text-anchor="middle" font-weight="bold" fill="#1b5e20">CONFIRM?</text>')
    if job.get("entry"):
        mins_ = (int(job["entry"][1][:2]) * 60 + int(job["entry"][1][3:]) - 555) / 5.0 - 0.5
        out.append(f'<polygon points="{p3.x(mins_):.1f},{p3.y(job["entry"][0]):.1f} {p3.x(mins_) - 7:.1f},{p3.y(job["entry"][0]) + 14:.1f} {p3.x(mins_) + 7:.1f},{p3.y(job["entry"][0]) + 14:.1f}" fill="#000"/>'
                   f'<text x="{p3.x(mins_) + 10:.1f}" y="{p3.y(job["entry"][0]) + 24:.1f}" font-weight="bold">ENTRY {job["entry"][0]:,.2f}</text>')
    for k, m in enumerate(job.get("manual", [])):
        t = int(m["entry_time_label"][:2]) * 60 + int(m["entry_time_label"][3:])
        pos = (t - 555) / 5.0
        col = "#d500f9" if m["strategy_normalized"] == "PDR" else "#9e9e9e"
        out.append(f'<line x1="{p3.x(pos):.1f}" x2="{p3.x(pos):.1f}" y1="{p3.y0}" y2="{p3.y0 + p3.h}" stroke="{col}" stroke-dasharray="2,3"/>'
                   f'<text x="{p3.x(pos) + 3:.1f}" y="{p3.y0 + 12 + 12 * k}" fill="{col}" font-size="10">JOURNAL {m["strategy_normalized"]} {m["entry_time_label"]} {m["exit_classification_entered"]} (row {m["journal_row"]})</text>')
    # ---- caption
    lines = [ln for c_ in job.get("caption", []) for ln in textwrap.wrap(c_, 200)][:6]
    for k, ln in enumerate(lines):
        out.append(f'<text x="20" y="{905 + 16 * k}" font-size="12" fill="#222">{escape(ln)}</text>')
    out.append(f'<text x="20" y="{1025}" font-size="11" fill="#666">Real 5-minute candles (IST, start-labelled). Zones are research candidates (PROPOSED_FOR_REVIEW in their numeric details); charts support verification, the CSV files are authoritative.</text>')
    out.append("</svg>")
    return "\n".join(out)
