"""Rendering helpers for ORB V2: dependency-free SVG trade / rejection charts, Markdown tables and openpyxl workbooks (written from the same row dictionaries as the CSV files)."""

from __future__ import annotations

import base64
from html import escape
from pathlib import Path

import pandas as pd

GREEN, RED, PURPLE, BLUE, GREY = "#17a37a", "#d9534f", "#8e44ad", "#2f80ed", "#888"


def _f(x, nd=2):
    return "" if x is None or (isinstance(x, float) and pd.isna(x)) else (f"{x:,.{nd}f}" if isinstance(x, (int, float)) else str(x))


def md_table(rows: list[dict], cols: list[str] | None = None, max_rows: int | None = None) -> str:
    if not rows:
        return "_(none)_\n"
    cols = cols or list(rows[0].keys())
    out = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for r in rows[:max_rows]:
        out.append("| " + " | ".join(str(r.get(c, "")).replace("|", "/").replace("\n", " ") for c in cols) + " |")
    return "\n".join(out) + "\n"


def svg_chart(spec: dict) -> str:  # noqa: C901
    """spec keys: title, header (list[str], top band), candles (DataFrame start/open/high/low/close/ema), open_start (Timestamp), levels (list of Level), trade (dict|None), panel (list[str]),
    visual_zones (list of (floor, ceiling, label) - author-depicted evidence), extra_markers (list of (ts, price, label, colour)), image_b64 (optional PNG screenshot shown above the chart)."""
    c = spec["candles"].reset_index(drop=True)
    n = len(c)
    W, H = 1500, 800
    L, R, T, B = 70, 620, 100, 40            # chart area margins; the right band (R px) carries the labels + info panel
    cw = (W - L - R) / max(n, 1)
    x_of = {ts: L + (i + 0.5) * cw for i, ts in enumerate(c["start"])}
    starts = list(c["start"])

    def x_at(ts) -> float:
        ts = pd.Timestamp(ts)
        i = max((k for k, s in enumerate(starts) if s <= ts), default=0)
        return x_of[starts[i]]

    tr = spec.get("trade")
    prices = list(c["high"]) + list(c["low"]) + list(c["ema"].dropna())
    for lv in spec.get("levels", []):
        prices += [lv.floor, lv.ceiling]
    for fz in spec.get("visual_zones", []):
        prices += [fz[0], fz[1]]
    if tr:
        prices += [tr["stop"], tr["target"]]
    lo, hi = min(prices), max(prices)
    pad = (hi - lo) * 0.04 + 1
    lo, hi = lo - pad, hi + pad
    ch = H - T - B

    def y(p: float) -> float:
        return T + (hi - p) / (hi - lo) * ch

    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', f'<rect width="{W}" height="{H}" fill="#fff"/>',
         f'<text x="{L}" y="22" font-size="16" font-weight="bold">{escape(spec["title"])}</text>']
    for i, hl in enumerate(spec.get("header", [])):
        o.append(f'<text x="{L}" y="{42 + i * 15}" fill="#333">{escape(hl)}</text>')
    # grid + price axis
    raw = (hi - lo) / 8
    step = next((x for x in (1, 2, 5, 10, 20, 25, 50, 100, 200) if x >= raw), 200)
    p = int(lo // step * step)
    while p <= hi:
        if p >= lo:
            o.append(f'<line x1="{L}" y1="{y(p):.1f}" x2="{W - R}" y2="{y(p):.1f}" stroke="#eee"/><text x="{L - 6}" y="{y(p) + 4:.1f}" text-anchor="end" fill="{GREY}">{p:,}</text>')
        p += step
    # day separator + time labels
    for i, s in enumerate(starts):
        if i and s.date() != starts[i - 1].date():
            xx = L + i * cw
            o.append(f'<line x1="{xx:.1f}" y1="{T}" x2="{xx:.1f}" y2="{H - B}" stroke="#bbb" stroke-dasharray="4 3"/><text x="{xx + 3:.1f}" y="{T - 4}" fill="{GREY}">{s:%d %b}</text>')
        if s.minute == 0 and s.hour % 1 == 0 and (s.hour - 9) % 2 == 0:
            o.append(f'<text x="{L + (i + 0.5) * cw:.1f}" y="{H - B + 14}" text-anchor="middle" fill="{GREY}">{s:%H:%M}</text>')
    # opening candle highlight
    if spec.get("open_start") is not None and pd.Timestamp(spec["open_start"]) in x_of:
        xo = x_of[pd.Timestamp(spec["open_start"])]
        o.append(f'<rect x="{xo - cw / 2:.1f}" y="{T}" width="{cw:.1f}" height="{ch}" fill="#ffd54f" opacity="0.35"/>')
    # levels / zones
    labels: list[tuple[float, str, str]] = []
    xr = W - R
    for lv in spec.get("levels", []):
        x0 = L
        if lv.source_times:
            cand = [x_of[s] for s in starts if s.strftime("%H:%M") == lv.source_times[0] and s.date() == c["start"].iloc[0].date()]
            x0 = cand[0] - cw / 2 if cand else L
        major = lv.kind == "MAJOR"
        col = PURPLE if major else "#b57edc"
        o.append(f'<rect x="{x0:.1f}" y="{y(lv.ceiling):.1f}" width="{xr - x0:.1f}" height="{max(1.5, y(lv.floor) - y(lv.ceiling)):.1f}" fill="{col}" opacity="{0.28 if major else 0.16}" stroke="{col}" stroke-width="{1.6 if major else 0.8}"/>')
        if major or lv.kind == "INNER" and spec.get("label_inner", True):
            labels.append((lv.ceiling if lv.side == "RESISTANCE" else lv.floor, f"{'MAJOR' if major else 'inner'} {'R' if lv.side == 'RESISTANCE' else 'S'} {lv.floor:.1f}" + (f"-{lv.ceiling:.1f}" if lv.is_zone else ""), col))
    for fz in spec.get("visual_zones", []):
        o.append(f'<rect x="{L}" y="{y(fz[1]):.1f}" width="{xr - L:.1f}" height="{max(1.5, y(fz[0]) - y(fz[1])):.1f}" fill="none" stroke="#e67e22" stroke-width="1.5" stroke-dasharray="6 3"/>')
        labels.append(((fz[0] + fz[1]) / 2, f"author zone ~{fz[0]:.0f}-{fz[1]:.0f}: {fz[2]}", "#e67e22"))
    # candles
    for i, r in c.iterrows():
        xx = L + (i + 0.5) * cw
        col = GREEN if r["close"] >= r["open"] else RED
        o.append(f'<line x1="{xx:.1f}" y1="{y(r["high"]):.1f}" x2="{xx:.1f}" y2="{y(r["low"]):.1f}" stroke="{col}"/>')
        top, bot = y(max(r["open"], r["close"])), y(min(r["open"], r["close"]))
        o.append(f'<rect x="{xx - cw * 0.35:.1f}" y="{top:.1f}" width="{cw * 0.7:.1f}" height="{max(0.8, bot - top):.1f}" fill="{col}"/>')
    # EMA
    pts = " ".join(f"{L + (i + 0.5) * cw:.1f},{y(v):.1f}" for i, v in enumerate(c["ema"]) if pd.notna(v))
    o.append(f'<polyline points="{pts}" fill="none" stroke="{BLUE}" stroke-width="1.6"/>')
    labels.append((float(c["ema"].iloc[-1]), f"EMA(200) {float(c['ema'].iloc[-1]):.1f}", BLUE))
    # trade
    if tr:
        xe, xx = x_at(tr["entry_time"]), x_at(tr["exit_time"]) if tr.get("exit_time") is not None else xr
        up = tr["direction"] == "BUY"
        for price, col, lab in ((tr["target"], GREEN, "TARGET"), (tr["stop"], RED, "STOP")):
            o.append(f'<line x1="{xe:.1f}" y1="{y(price):.1f}" x2="{max(xx, xe + 30):.1f}" y2="{y(price):.1f}" stroke="{col}" stroke-width="1.6" stroke-dasharray="5 3"/>')
            labels.append((price, f"{lab} {price:.2f}", col))
        ye = y(tr["entry_price"])
        tri = f"{xe:.1f},{ye - 9 if up else ye + 9:.1f} {xe - 6:.1f},{ye:.1f} {xe + 6:.1f},{ye:.1f}" if up else f"{xe:.1f},{ye + 9:.1f} {xe - 6:.1f},{ye:.1f} {xe + 6:.1f},{ye:.1f}"
        o.append(f'<polygon points="{tri}" fill="#111"/><line x1="{L}" y1="{ye:.1f}" x2="{xr:.1f}" y2="{ye:.1f}" stroke="#111" stroke-width="0.8" stroke-dasharray="2 3"/>')
        labels.append((tr["entry_price"], f"ENTRY {tr['direction']} {tr['entry_price']:.2f} @{pd.Timestamp(tr['entry_time']):%H:%M}", "#111"))
        if tr.get("exit_price") is not None:
            yx = y(tr["exit_price"])
            o.append(f'<circle cx="{xx:.1f}" cy="{yx:.1f}" r="6" fill="none" stroke="#111" stroke-width="2"/><line x1="{xx - 4:.1f}" y1="{yx - 4:.1f}" x2="{xx + 4:.1f}" y2="{yx + 4:.1f}" stroke="#111" stroke-width="2"/>')
            labels.append((tr["exit_price"], f"EXIT {tr['exit_reason']} {tr['exit_price']:.2f} @{pd.Timestamp(tr['exit_time']):%H:%M} ({tr['gross_points']:+.1f} pts)", "#111"))
    for ts, price, lab, col in spec.get("extra_markers", []):
        xm, ym = x_at(ts), y(price)
        o.append(f'<polygon points="{xm:.1f},{ym - 8:.1f} {xm - 6:.1f},{ym + 5:.1f} {xm + 6:.1f},{ym + 5:.1f}" fill="{col}" opacity="0.9"/>')
        labels.append((price, lab, col))
    # right-margin labels with collision avoidance
    labels.sort(key=lambda t: -t[0])
    last = -99.0
    for price, text, col in labels:
        yy = max(y(price), last + 12.5)
        last = yy
        o.append(f'<line x1="{xr:.1f}" y1="{y(price):.1f}" x2="{xr + 6:.1f}" y2="{yy:.1f}" stroke="{col}" stroke-width="0.6"/><text x="{xr + 8:.1f}" y="{yy + 3:.1f}" fill="{col}" font-size="10">{escape(text[:46])}</text>')
    # info panel (far right)
    px = W - 300
    o.append(f'<rect x="{px - 8}" y="{T}" width="298" height="{ch}" fill="#fafafa" stroke="#ddd"/>')
    yy = T + 16
    for line in spec.get("panel", []):
        for chunk in _wrap(line, 46):
            o.append(f'<text x="{px}" y="{yy}" fill="#222" font-size="10.5">{escape(chunk)}</text>')
            yy += 13
        yy += 3
    if spec.get("image_b64"):
        pass
    o.append("</svg>")
    return "\n".join(o)


def _wrap(s: str, w: int) -> list[str]:
    out, cur = [], ""
    for word in s.split(" "):
        if len(cur) + len(word) + 1 > w and cur:
            out.append(cur)
            cur = word
        else:
            cur = (cur + " " + word).strip()
    return out + ([cur] if cur else [])


def embed_png(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def write_workbook(path: Path, sheets: dict[str, list[dict]], notes: dict[str, str] | None = None) -> None:
    import openpyxl
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    if notes:
        ws = wb.create_sheet("README")
        for i, (k, v) in enumerate(notes.items(), start=1):
            ws.cell(i, 1, k).font = Font(bold=True)
            ws.cell(i, 2, v).alignment = Alignment(wrap_text=True, vertical="top")
        ws.column_dimensions["A"].width = 28
        ws.column_dimensions["B"].width = 120
    for name, rows in sheets.items():
        ws = wb.create_sheet(name[:31])
        if not rows:
            ws.cell(1, 1, "(no rows)")
            continue
        cols = list(dict.fromkeys(k for r in rows for k in r))
        for j, cname in enumerate(cols, start=1):
            c = ws.cell(1, j, cname)
            c.font = Font(bold=True, color="FFFFFF")
            c.fill = PatternFill("solid", fgColor="2F5597")
        for i, r in enumerate(rows, start=2):
            for j, cname in enumerate(cols, start=1):
                v = r.get(cname)
                if isinstance(v, pd.Timestamp):
                    v = v.to_pydatetime().replace(tzinfo=None)
                elif v is not None and not isinstance(v, (int, float, str, bool)) and not hasattr(v, "year"):
                    v = str(v)
                ws.cell(i, j, v)
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = f"A1:{get_column_letter(len(cols))}{len(rows) + 1}"
        for j, cname in enumerate(cols, start=1):
            width = max([len(str(cname))] + [len(str(r.get(cname, ""))) for r in rows[:200]])
            ws.column_dimensions[get_column_letter(j)].width = min(60, max(9, width + 2))
    wb.save(path)
