"""Phase 5.8 SVG evidence; no fabricated manual price markers."""

from __future__ import annotations

import html
import math


def esc(v):
    return html.escape(str(v))


def chart(ctx, minute, reconstruction, records, trades, notes):
    """Full previous/current 5m and current first-hour 1m. Ledger A/B/C overlays."""
    out = ['<svg xmlns="http://www.w3.org/2000/svg" width="1800" height="1390" viewBox="0 0 1800 1390" font-family="Arial" font-size="12">',
           '<rect width="1800" height="1390" fill="white"/>',
           f'<text x="70" y="30" font-size="22" font-weight="bold">{ctx.date} | Independent ORB forensic evidence</text>',
           '<text x="70" y="54" fill="#555">Actual NIFTY index candles | Times IST, start labels | A frozen, B author-corrected, C gap-candle candidate | Ledger overlays only</text>']
    prev = ctx.previous.candles
    today = ctx.candles
    first = reconstruction[0]["geometry"]
    for panel, top in (("5m", 95), ("1m", 650)):
        rows = (list(prev.itertuples(index=False)) + list(today.itertuples(index=False)) if panel == "5m" else list(minute.iloc[:60].itertuples(index=False)))
        split = len(prev) if panel == "5m" else 0
        n = len(rows)
        left, width, height = 80, 1410, 405
        vals = [float(getattr(r, k)) for r in rows for k in ("high", "low")]
        if panel == "5m":
            vals.extend([float(prev.high.max()), float(prev.low.min())])
            vals.extend(float(r.ema200_5m) for r in rows if not math.isnan(float(r.ema200_5m)))
            for t in trades:
                vals.extend(float(t[k]) for k in ("entry_price", "initial_stop", "target_1", "target_2") if t.get(k))
        lo, hi = min(vals), max(vals)
        pad = (hi - lo or 1) * 0.06
        lo, hi = lo - pad, hi + pad

        def X(i, left=left, n=n, width=width):
            return left + (i + 0.5) / n * width

        def Y(v, top=top, hi=hi, lo=lo, height=height):
            return top + (hi - float(v)) / (hi - lo) * height

        def line(label, value, colour, dash="5 4", lo=lo, hi=hi, left=left, width=width, Y=Y):
            if value is None or not math.isfinite(value) or not lo <= value <= hi:
                return
            out.append(f'<line x1="{left}" x2="{left + width}" y1="{Y(value):.2f}" y2="{Y(value):.2f}" stroke="{colour}" stroke-dasharray="{dash}" opacity="0.7"><title>{esc(label)} {value:.5f}</title></line>')

        out.append(f'<text x="{left}" y="{top - 17}" font-size="16" font-weight="bold">{esc("5-minute: full previous session + full current session" if panel == "5m" else "1-minute: first hour; only first five rows form the ORB candle")}</text>')
        for k in range(7):
            v = lo + (hi - lo) * k / 6
            out.append(f'<line x1="{left}" x2="{left + width}" y1="{Y(v):.2f}" y2="{Y(v):.2f}" stroke="#e9edf2"/><text x="8" y="{Y(v)+4:.2f}" fill="#555">{v:.1f}</text>')
        band_x = left + split / n * width
        out.append(f'<rect x="{band_x:.2f}" y="{top}" width="{width / n * (1 if panel == "5m" else 5):.2f}" height="{height}" fill="#fbe19b" opacity="0.55"/>')
        out.append(f'<line x1="{band_x:.2f}" x2="{band_x:.2f}" y1="{top}" y2="{top+height}" stroke="#b8860b"/>')
        for i, r in enumerate(rows):
            col = "#00866a" if r.close >= r.open else "#d43b53"
            barw = width / n * 0.66
            start = r.bar_start if panel == "5m" else r.timestamp
            out.append(f'<g><title>{start} O {r.open:.2f} H {r.high:.2f} L {r.low:.2f} C {r.close:.2f}</title><line x1="{X(i):.2f}" x2="{X(i):.2f}" y1="{Y(r.high):.2f}" y2="{Y(r.low):.2f}" stroke="{col}"/><rect x="{X(i)-barw/2:.2f}" y="{Y(max(r.open,r.close)):.2f}" width="{barw:.2f}" height="{max(abs(Y(r.close)-Y(r.open)),1):.2f}" fill="{col}"/></g>')
            if i % (15 if panel == "5m" else 10) == 0:
                label = f'{"P " if i < split else ""}{start:%H:%M}'
                out.append(f'<text x="{X(i)-16:.2f}" y="{top+height+20}">{label}</text>')
        levels = [("ORH", first["high"], "#9c6900"), ("ORL", first["low"], "#9c6900"),
                  ("PDH", float(prev.high.max()), "#8053ba"), ("PDL", float(prev.low.min()), "#8053ba")]
        for r in reconstruction:
            if r["method"] == "Method 2":
                levels.append((f'Inner {r["direction"]}', r["inner_level"], "#d4791b"))
        for label, v, col in levels:
            line(label, v, col)
        if panel == "5m":
            pts = " ".join(f'{X(i):.2f},{Y(r.ema200_5m):.2f}' for i, r in enumerate(rows) if math.isfinite(r.ema200_5m))
            out.append(f'<polyline points="{pts}" fill="none" stroke="#2670c4" stroke-width="2"/>')
            for r in reconstruction:
                if r["method"] == "Method 2" and r["trendline"] is not None:
                    js = r["trendline_anchors"]
                    points = []
                    for i in range(js[0], len(rows)):
                        v = r["trendline"] + r["trendline_slope"] * (i - split)
                        if lo <= v <= hi:
                            points.append(f'{X(i):.2f},{Y(v):.2f}')
                    out.append(f'<polyline points="{" ".join(points)}" fill="none" stroke="{"#009c8a" if r["direction"] == "LONG" else "#c23b89"}" stroke-dasharray="4 4" stroke-width="1.5"><title>{r["direction"]} assumed last-two-pivot trendline</title></polyline>')
        else:
            # Latest available completed 5m EMA is a step, not a future-interpolated line.
            prior_e = ctx.previous.ema_at_last_candle
            pts = []
            for i, row in enumerate(rows):
                completed = today[today.bar_end <= row.timestamp]
                value = float(completed.ema200_5m.iloc[-1]) if len(completed) else prior_e
                if math.isfinite(value) and lo <= value <= hi:
                    pts.append(f'{X(i):.2f},{Y(value):.2f}')
            out.append(f'<polyline points="{" ".join(pts)}" fill="none" stroke="#2670c4" stroke-width="2"/>')
        sma = ctx.daily_sma200_prev
        line("Daily SMA200 (strictly prior daily closes)", sma, "#4b5663", "2 7")
        if panel == "5m":
            for k, t in enumerate(trades, 1):
                fill = t["fill_timestamp"][-5:]
                idx = next((i for i, r in enumerate(rows) if i >= split and f'{r.bar_start:%H:%M}' <= fill < f'{r.bar_end:%H:%M}'), None)
                if idx is None:
                    continue
                col = {"A": "#a32d70", "B": "#317b26", "C": "#ce6910"}[t["config"]]
                out.append(f'<circle cx="{X(idx):.2f}" cy="{Y(float(t["entry_price"])):.2f}" r="6" stroke="white" fill="{col}"><title>Ledger #{k}: {esc(t["config"])} {esc(t["strategy"])} {fill} entry {t["entry_price"]}</title></circle>')
                for key in ("initial_stop", "target_1", "target_2"):
                    v = float(t[key])
                    out.append(f'<line x1="{X(idx):.2f}" x2="{min(X(idx)+80,left+width):.2f}" y1="{Y(v):.2f}" y2="{Y(v):.2f}" stroke="{col}" stroke-dasharray="3 3"><title>Ledger #{k} {key} {v}</title></line>')
                for leg in (1, 2):
                    tm, px = t.get(f"leg{leg}_exit_time"), t.get(f"leg{leg}_exit_price")
                    ex = next((i for i, r in enumerate(rows) if i >= split and f'{r.bar_start:%H:%M}' <= tm < f'{r.bar_end:%H:%M}'), None) if tm else None
                    if ex is not None and px:
                        y = Y(float(px))
                        out.append(f'<path d="M {X(ex)-4:.2f} {y-4:.2f} l 8 8 m -8 0 l 8 -8" stroke="{col}" stroke-width="2"><title>Ledger #{k} leg {leg} exit {tm} {px}</title></path>')
        ema_label = f'EMA at 09:20: {reconstruction[0]["ema"]:.2f}' + (" (off scale)" if not lo <= reconstruction[0]["ema"] <= hi else "")
        out.append(f'<text x="1510" y="{top+20}">{esc(ema_label)}</text>')
        # Right-side labels stay short; full numeric references are in the daily evidence.
        for j, (label, v, _) in enumerate(levels):
            out.append(f'<text x="1510" y="{top+120+j*20}">{esc(label)}: {v:.2f}</text>' if v is not None else f'<text x="1510" y="{top+120+j*20}">{esc(label)}: undefined</text>')
        out.append(f'<text x="1510" y="{top+285}" fill="#2670c4">Blue: completed 5m EMA200</text>')
        sma_label = (f'Daily SMA: {sma:.2f}' + (" (off scale)" if not lo <= sma <= hi else "")) if math.isfinite(sma) else f'Daily SMA: unavailable ({ctx.daily_history_count})'
        out.append(f'<text x="1510" y="{top+307}">{esc(sma_label)}</text>')
        for j, r in enumerate([r for r in records if r.strategy in ("ORB", "IRF") and r.signal_status == "CONFIRMED"][:4]):
            out.append(f'<text x="1510" y="{top+335+j*16}">{esc(r.strategy)} {r.signal_timestamp:%H:%M} {esc(r.direction)}</text>')
    footer = [f'Opening O {first["open"]:.2f} H {first["high"]:.2f} L {first["low"]:.2f} C {first["close"]:.2f}; body {first["body_pct"]:.2f}% | Manual direction / level / entry price UNKNOWN.',
              'Gold band: first 5m. Purple: PDH/PDL. Orange: assumed inner levels. Dashed teal/magenta: assumed LONG/SHORT trendlines. Circles: ledger fills. Crosses: ledger leg exits.',
              'Ledger exits are model fills; on target gaps the existing model keeps the target level, which can lie outside that minute bar.'] + notes
    for k, t in enumerate(trades, 1):
        footer.append(f'#{k} {t["config"]} {t["strategy"]} {t["method"]} {t["direction"]} {t["fill_timestamp"][-5:]} @ {t["entry_price"]}; SL {t["initial_stop"]}; T1 {t["target_1"]}; T2 {t["target_2"]}; exits {t["leg1_exit_time"]}/{t["leg1_exit_price"]}, {t["leg2_exit_time"]}/{t["leg2_exit_price"]}')
    for j, text in enumerate(footer[:15]):
        out.append(f'<text x="70" y="{1110+j*18}" font-size="12">{esc(text)}</text>')
    out.append('</svg>')
    return '\n'.join(out)
