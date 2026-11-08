"""Phase 5.7: enhanced, dependency-free SVG charts of an executed trade (or of a journal day without a trade) for MANUAL verification.

The style is the Phase 3.2 / 3.6 trade chart (real five-minute candles, EMA(200), reference levels and zones, dashed manual-journal lines, role marks above candles) with the information a reviewer needs next to the price action:
header (trade, strategy, method, direction, configuration, journal-match status), the entry marker with its time and price, the initial stop, Target 1, Target 2 and the post-T1 stop as named and priced lines, both exit legs with reason / time / price,
and four information blocks (entry, levels and exits, P&L, journal comparison).

Nothing is computed here: every number is passed in by the caller from the verified Phase 5.5 ledgers and the Phase 5.6 matching files, and the match label is passed in, never derived. Every drawn value is also written into an embedded
``<metadata>`` JSON block and as ``data-*`` attributes so that an independent audit can compare the rendered chart with the ledgers.
"""

from __future__ import annotations

import json
import textwrap
from datetime import datetime
from html import escape

W = 1560
ML, MR = 80, 300
PT, PB = 116, 600
T_OPEN, T_CLOSE = 9 * 60 + 15, 15 * 60 + 30
BADGE = {"EXACT_MATCH": "#2e7d32", "TIME_TOLERANT_MATCH": "#1565c0", "DATE_STRATEGY_ONLY": "#e65100", "AUTOMATED_ONLY": "#616161", "NO_TRADE_JOURNAL_DAY": "#6a1b9a"}
CH_W = 6.1  # approximate glyph width of the 11px sans-serif font


def money(v: float, d: int = 2) -> str:
    return f"{v:,.{d}f}"


def minute_of(ts: datetime) -> float:
    return ts.hour * 60 + ts.minute + ts.second / 60.0


def hhmm(ts: datetime) -> str:
    return f"{ts:%H:%M}"


def spread(items: list[dict], gap: float, lo: float, hi: float) -> None:
    """Vertical label placement for the right margin: ``items`` carry ``y`` (true) and get ``ly`` (label y) with at least ``gap`` between neighbours, kept inside [lo, hi]."""
    items.sort(key=lambda it: it["y"])
    prev = lo - gap
    for it in items:
        it["ly"] = max(it["y"], prev + gap)
        prev = it["ly"]
    over = prev - hi
    if over > 0:  # pushed beyond the bottom: shift the stack upwards, keeping the gaps
        nxt = hi + gap
        for it in reversed(items):
            it["ly"] = min(it["ly"], nxt - gap)
            nxt = it["ly"]


def place_near(labels: list[dict], xr: float, ymin: float, ymax: float) -> None:
    """Place labels that sit next to markers: right of the marker if it fits before ``xr``, else left of it; then resolve rectangle overlaps by moving down (alternating up) in 12 px steps."""
    placed: list[tuple[float, float, float, float]] = []
    for lb in sorted(labels, key=lambda d: (d["y"], d["x"])):
        w = CH_W * len(lb["text"]) + 4
        right = lb["x"] + 9 + w <= xr
        x0 = lb["x"] + 9 if right else lb["x"] - 9 - w
        y = lb["y"] + lb.get("dy", 0)
        for k in range(40):
            cand = y + (k // 2 + 1) * 12 * (1 if k % 2 == 0 else -1) if k else y
            rect = (x0, cand - 10, x0 + w, cand + 3)
            if ymin <= cand <= ymax and not any(rect[0] < p[2] and p[0] < rect[2] and rect[1] < p[3] and p[1] < rect[3] for p in placed):
                y = cand
                break
        placed.append((x0, y - 10, x0 + w, y + 3))
        lb["lx"], lb["ly"], lb["anchor"] = (x0 if right else x0 + w), y, ("start" if right else "end")


def block_svg(x: float, y: float, title: str, lines: list[tuple[str, str]], width_chars: int) -> tuple[list[str], int]:
    """A titled text block; ``lines`` = [(text, style)] with style '' | 'b' (bold) | 'g' (grey) | 'r' (red) | 'ok' (green). Returns (svg parts, number of text rows used)."""
    out = [f'<text x="{x}" y="{y}" font-size="12.5" font-weight="bold" fill="#111">{escape(title)}</text>', f'<line x1="{x}" x2="{x + width_chars * CH_W:.0f}" y1="{y + 4}" y2="{y + 4}" stroke="#bbb"/>']
    row = 0
    for text, style in lines:
        for part in textwrap.wrap(text, width_chars, break_long_words=True) or [""]:
            col = {"g": "#666", "r": "#b71c1c", "ok": "#1b5e20"}.get(style, "#111")
            wt = ' font-weight="bold"' if style == "b" else ""
            out.append(f'<text x="{x}" y="{y + 20 + 14 * row}" fill="{col}"{wt}>{escape(part)}</text>')
            row += 1
    return out, row


def render(spec: dict) -> str:  # noqa: C901
    """``spec`` keys (all values pre-formatted facts from the ledgers; nothing is derived here except geometry):
    header {l1, l2, l3}, badge (text, colour key), candles [{start, o, h, l, c, ema}], hlines [(label, value, colour)], zones [(label, lo, hi, colour)], marks [(start, text)],
    trade None | {direction, entry_ts, entry, stop, t1, t2, post_t1 (None when T1 was not hit), t1_hit_ts, exits [{leg, label, ts, price}]},
    manual [{label 'HH:MM', text, matched}], blocks [(title, lines)], meta {...}, note, min_end (minutes; the window shows at least this far)."""
    cs = spec["candles"]
    tr = spec["trade"]
    last_min = max([minute_of(e["ts"]) for e in tr["exits"]], default=minute_of(tr["entry_ts"])) if tr else T_OPEN + 90
    first_min = minute_of(tr["entry_ts"]) if tr else T_OPEN + 30
    t1 = int(min(T_CLOSE, ((max(last_min + 25, first_min + 50, T_OPEN + 60, spec.get("min_end", 0))) // 15 + 1) * 15))
    vis = [c for c in cs if minute_of(c["start"]) < t1]
    pw = W - ML - MR
    ph = PB - PT
    key_prices = [c["l"] for c in vis] + [c["h"] for c in vis]
    if tr:
        key_prices += [tr["entry"], tr["stop"], tr["t1"], tr["t2"]] + [e["price"] for e in tr["exits"]] + ([tr["post_t1"]] if tr["post_t1"] is not None else [])
    lo0, hi0 = min(key_prices), max(key_prices)
    span = max(hi0 - lo0, 1.0)
    off_scale: list[str] = []
    hl_in, zn_in = [], []
    for lab, v, col in spec["hlines"]:
        if v is None:
            continue
        if lo0 - 0.5 * span <= v <= hi0 + 0.5 * span:
            hl_in.append((lab, v, col))
            lo0, hi0 = min(lo0, v), max(hi0, v)
        else:
            off_scale.append(f"{lab} {money(v)}")
    for lab, zlo, zhi, col in spec["zones"]:
        if lo0 - 0.5 * span <= zlo and zhi <= hi0 + 0.5 * span:
            zn_in.append((lab, zlo, zhi, col))
            lo0, hi0 = min(lo0, zlo), max(hi0, zhi)
        else:
            off_scale.append(f"{lab} [{money(zlo)}, {money(zhi)}]")
    pad = (hi0 - lo0) * 0.06 + 1.0
    lo_p, hi_p = lo0 - pad, hi0 + pad

    def y(p: float) -> float:
        return PT + (hi_p - p) / (hi_p - lo_p) * ph

    def x(m: float) -> float:
        return ML + (m - T_OPEN) / (t1 - T_OPEN) * pw
    ncand = (t1 - T_OPEN) / 5.0
    cw = pw / ncand
    xr = ML + pw  # plot right edge
    # ---------------------------------------------------------------- blocks first (they decide the canvas height)
    bx = [40 + k * 372 for k in range(4)]
    block_parts: list[list[str]] = []
    rows_max = 0
    by = PB + 74
    for k, (title, lines) in enumerate(spec["blocks"]):
        parts, rows = block_svg(bx[k], by, title, lines, 59)
        block_parts.append(parts)
        rows_max = max(rows_max, rows)
    H = by + 34 + 14 * rows_max
    meta = dict(spec["meta"])
    meta["scale"] = {"plot_top": PT, "plot_bottom": PB, "price_low": lo_p, "price_high": hi_p, "plot_left": ML, "plot_right": xr, "t_open": T_OPEN, "t_end": t1}
    o: list[str] = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="11">',
                    f'<metadata id="phase57">{escape(json.dumps(meta, default=str))}</metadata>', "<style>text{paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}</style>", f'<rect width="{W}" height="{H}" fill="white"/>']
    # ---------------------------------------------------------------- header
    hd = spec["header"]
    bt, bcol = spec["badge"]
    o.append(f'<text x="40" y="26" font-size="18" font-weight="bold" fill="#111">{escape(hd["l1"])}</text>')
    o.append(f'<text x="40" y="47" font-size="13" fill="#333">{escape(hd["l2"])}</text>')
    o.append(f'<text x="40" y="66" font-size="12" fill="#444">{escape(hd["l3"])}</text>')
    bw = 9.8 * len(bt) + 30
    o.append(f'<rect x="{W - 40 - bw:.0f}" y="10" width="{bw:.0f}" height="30" rx="5" fill="{BADGE[bcol]}"/><text x="{W - 40 - bw / 2:.0f}" y="30" text-anchor="middle" font-size="14" font-weight="bold" fill="#fff" style="stroke:none">{escape(bt)}</text>')
    if hd.get("l4"):
        o.append(f'<text x="{W - 40}" y="58" text-anchor="end" font-size="12" fill="#333">{escape(hd["l4"])}</text>')
    o.append(f'<text x="40" y="86" font-size="10.5" fill="#777">{escape(spec["note"])}</text>')
    if off_scale:
        o.append(f'<text x="40" y="100" font-size="10.5" fill="#777">off the price scale (not drawn): {escape("; ".join(off_scale))}</text>')
    # ---------------------------------------------------------------- grid, time axis
    for k in range(7):
        p = lo_p + (hi_p - lo_p) * k / 6
        o.append(f'<line x1="{ML}" x2="{xr}" y1="{y(p):.1f}" y2="{y(p):.1f}" stroke="#eee"/><text x="6" y="{y(p) + 4:.1f}" fill="#555">{p:,.0f}</text>')
    step = 15 if (t1 - T_OPEN) <= 150 else 30
    m = T_OPEN
    while m <= t1:
        o.append(f'<line x1="{x(m):.1f}" x2="{x(m):.1f}" y1="{PT}" y2="{PB}" stroke="#f1f1f1"/><text x="{x(m) - 14:.1f}" y="{PB + 16}" fill="#555">{m // 60:02d}:{m % 60:02d}</text>')
        m += step
    # ---------------------------------------------------------------- zones, reference lines (names go to the right margin)
    margin: list[dict] = []
    for lab, zlo, zhi, col in zn_in:
        o.append(f'<rect x="{ML}" y="{y(zhi):.1f}" width="{pw}" height="{max(y(zlo) - y(zhi), 1.5):.1f}" fill="{col}" opacity="0.13"/>')
        margin.append({"y": (y(zhi) + y(zlo)) / 2, "text": f"{lab.split(' (')[0]} [{money(zlo)}, {money(zhi)}]", "col": col, "size": 10, "bold": False})
    for lab, v, col in hl_in:
        o.append(f'<line x1="{ML}" x2="{xr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-dasharray="6,4" stroke-width="1.1"/>')
        margin.append({"y": y(v), "text": f"{lab} {money(v)}", "col": col, "size": 10, "bold": False})
    # ---------------------------------------------------------------- EMA and candles
    pts = " ".join(f"{x(minute_of(c['start']) + 2.5):.1f},{y(c['ema']):.1f}" for c in vis if c.get("ema") is not None and c["ema"] == c["ema"] and lo_p <= c["ema"] <= hi_p)
    if pts:
        o.append(f'<polyline points="{pts}" fill="none" stroke="#f9a825" stroke-width="1.6"/>')
    for c in vis:
        xm = x(minute_of(c["start"]) + 2.5)
        col = "#2e7d32" if c["c"] >= c["o"] else "#c62828"
        o.append(f'<line x1="{xm:.1f}" x2="{xm:.1f}" y1="{y(c["h"]):.1f}" y2="{y(c["l"]):.1f}" stroke="{col}"/>'
                 f'<rect x="{xm - cw * 0.34:.1f}" y="{y(max(c["o"], c["c"])):.1f}" width="{cw * 0.68:.1f}" height="{max(abs(y(c["o"]) - y(c["c"])), 1):.1f}" fill="{col}"/>')
    stack: dict[int, int] = {}
    for start, text in spec["marks"]:
        if minute_of(start) >= t1:
            continue
        cx = next((c for c in vis if c["start"] == start), None)
        if cx is not None:
            k = int(minute_of(start))
            stack[k] = stack.get(k, 0) + 1
            o.append(f'<text x="{x(minute_of(start) + 2.5):.1f}" y="{y(cx["h"]) - 4 - 10 * (stack[k] - 1):.1f}" text-anchor="middle" font-size="9" fill="#37474f" font-weight="bold">{escape(text)}</text>')
    # ---------------------------------------------------------------- manual journal lines
    for k, mj in enumerate(spec["manual"]):
        mins = int(mj["label"][:2]) * 60 + int(mj["label"][3:5])
        if mins >= t1:
            continue
        xx = x(mins + 2.5)
        w = "1.8" if mj["matched"] else "1.1"
        o.append(f'<line x1="{xx:.1f}" x2="{xx:.1f}" y1="{PT}" y2="{PB}" stroke="#c2185b" stroke-dasharray="{"" if mj["matched"] else "2,3"}" stroke-width="{w}" opacity="0.85"/>'
                 f'<text x="{xx + 3:.1f}" y="{PT + 12 + 12 * k}" fill="#c2185b" font-size="10.5"{" font-weight=\"bold\"" if mj["matched"] else ""} data-kind="JOURNAL" data-journal-row="{escape(str(mj.get("row", "")))}">{escape(mj["text"])}</text>')
    for lab, mm in (("13:00 entry cutoff", 13 * 60), ("15:14 forced exit (provisional)", 15 * 60 + 14)):
        if mm < t1:
            o.append(f'<line x1="{x(mm):.1f}" x2="{x(mm):.1f}" y1="{PT}" y2="{PB}" stroke="#777" stroke-dasharray="1,4"/><text x="{x(mm) - 50:.1f}" y="{PT - 4}" fill="#777" font-size="10">{lab}</text>')
    # ---------------------------------------------------------------- the trade
    near: list[dict] = []
    if tr:
        exits = tr["exits"]
        final_ts = max(minute_of(e["ts"]) for e in exits)
        e0 = minute_of(tr["entry_ts"])
        t1_ts = minute_of(tr["t1_hit_ts"]) if tr["t1_hit_ts"] is not None else None
        stop_end = t1_ts if t1_ts is not None else final_ts
        spans = [("ENTRY", tr["entry"], "#000000", "", e0, final_ts, "ENTRY"), ("SL", tr["stop"], "#c62828", "6,3", e0, stop_end, "SL"), ("T1", tr["t1"], "#2e7d32", "6,3", e0, t1_ts if t1_ts is not None else final_ts, "T1"),
                 ("T2", tr["t2"], "#00695c", "6,3", e0, final_ts, "T2")]
        if tr["post_t1"] is not None and t1_ts is not None:
            spans.append(("POST-T1 STOP", tr["post_t1"], "#ef6c00", "2,3", t1_ts, final_ts, "POST_T1_STOP"))
        for name, v, col, dash, a, b, kind in spans:
            xa, xb = x(a), x(max(b, a + 0.5))
            o.append(f'<line data-kind="{kind}" data-price="{v}" x1="{xa:.1f}" x2="{xb:.1f}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width="2"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>")
            o.append(f'<line x1="{xb:.1f}" x2="{xr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="{col}" stroke-width="1" stroke-dasharray="1,4" opacity="0.55"/>')
            margin.append({"y": y(v), "text": f"{name} @ {money(v)}", "col": col, "size": 11.5, "bold": True, "kind": kind, "price": v})
        xe = x(e0)
        up = tr["direction"] == "LONG"
        tip, base = y(tr["entry"]), y(tr["entry"]) + (16 if up else -16)
        o.append(f'<polygon data-kind="ENTRY_MARKER" data-price="{tr["entry"]}" points="{xe:.1f},{tip:.1f} {xe - 8:.1f},{base:.1f} {xe + 8:.1f},{base:.1f}" fill="#000" stroke="#fff"/>')
        near.append({"x": xe, "y": base + (12 if up else -4), "text": f"ENTRY {hhmm(tr['entry_ts'])} @ {money(tr['entry'])}", "col": "#000", "bold": True, "kind": "ENTRY_LABEL"})
        for e in exits:
            xx, yy = x(minute_of(e["ts"])), y(e["price"])
            shape = (f'<rect data-kind="EXIT_{e["leg"]}" data-price="{e["price"]}" x="{xx - 5.5:.1f}" y="{yy - 5.5:.1f}" width="11" height="11" fill="#fff" stroke="#6a1b9a" stroke-width="2.2"/>' if e["leg"] == "2" else
                     f'<circle data-kind="EXIT_{e["leg"]}" data-price="{e["price"]}" cx="{xx:.1f}" cy="{yy:.1f}" r="{6.5 if e["leg"] == "FULL" else 5.5}" fill="#fff" stroke="#6a1b9a" stroke-width="2.2"/>')
            o.append(shape)
            near.append({"x": xx, "y": yy, "text": e["label"], "col": "#6a1b9a", "bold": True, "kind": f"EXIT_LABEL_{e['leg']}"})
    # right-margin names for reference lines and trade levels
    items = [{**mrg} for mrg in margin]
    spread(items, 13.0, PT + 6, PB - 2)
    for it in items:
        if abs(it["ly"] - it["y"]) > 1.5:
            o.append(f'<polyline points="{xr:.1f},{it["y"]:.1f} {xr + 8:.1f},{it["y"]:.1f} {xr + 12:.1f},{it["ly"] - 3:.1f}" fill="none" stroke="{it["col"]}" stroke-width="0.8" opacity="0.7"/>')
        attr = f' data-kind="LABEL_{it["kind"]}" data-price="{it["price"]}"' if it.get("kind") else ""
        o.append(f'<text x="{xr + 14:.1f}" y="{it["ly"]:.1f}" fill="{it["col"]}" font-size="{it["size"]}"{" font-weight=\"bold\"" if it["bold"] else ""}{attr}>{escape(it["text"])}</text>')
    place_near(near, xr - 4, PT + 14, PB - 4)
    for lb in near:
        o.append(f'<text x="{lb["lx"]:.1f}" y="{lb["ly"]:.1f}" text-anchor="{lb["anchor"]}" fill="{lb["col"]}" font-weight="bold" font-size="11.5" data-kind="{lb["kind"]}">{escape(lb["text"])}</text>')
    # ---------------------------------------------------------------- legend
    lg = [("#000", "▲▼ entry"), ("#c62828", "- - initial stop (SL)"), ("#2e7d32", "- - Target 1"), ("#00695c", "- - Target 2"), ("#ef6c00", "··· post-T1 stop (only after T1 is booked)"), ("#6a1b9a", "● leg-1 exit   ■ leg-2 exit   ◉ full exit"),
          ("#f9a825", "EMA(200) of 5-min closes"), ("#c2185b", "journal entry (candle-start label; no price recorded)")]
    if not tr:
        lg = [("#f9a825", "EMA(200) of 5-min closes"), ("#1b5e20", "- - previous-day high / low"), ("#6a1b9a", "- - first-candle high / low"), ("#c2185b", "journal entry (candle-start label; no price recorded)")]
    lx = 40
    for col, text in lg:
        o.append(f'<text x="{lx}" y="{PB + 38}" fill="{col}" font-size="11" font-weight="bold">{escape(text)}</text>')
        lx += CH_W * len(text) + 26
    # ---------------------------------------------------------------- blocks
    for parts in block_parts:
        o.extend(parts)
    o.append("</svg>")
    return "\n".join(o)
