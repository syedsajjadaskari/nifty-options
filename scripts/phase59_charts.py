"""Author-review SVGs from raw candles and existing A ledger; no hypothetical fills."""

from __future__ import annotations

import html
import json
import math
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase5/phase59_orb_author_validation"
AUTHOR_LABEL = "AUTHOR ORB ENTRY — TO BE MARKED"
W, H = 2000, 1250
PLOT = {"left": 100, "right": 1450, "top": 165, "bottom": 705}
AUTHOR_BOX = {"x": 1480, "y": 650, "width": 480, "height": 550}


def esc(value):
    return html.escape(str(value))


def dt(value):
    return datetime.fromisoformat(value)


def text(x, y, value, size=22, colour="#26384A", weight="normal", extra=""):
    return f'<text x="{x:.2f}" y="{y:.2f}" font-size="{size}" fill="{colour}" font-weight="{weight}" {extra}>{esc(value)}</text>'


def render(payload, kind):
    case, d = payload["case"], payload["case"]["date"]
    five = payload["five_minute"]
    if kind == "overview":
        prior = payload["previous_five_minute"][-18:]
        rows = prior + five
        time_key, period, split = "bar_start", 5, len(prior)
        title = "5-minute candles | previous-session close context + full review session"
    elif kind == "opening_1m":
        rows = [r for r in payload["one_minute"] if "09:15" <= r["time"] < "10:15"]
        time_key, period, split = "timestamp", 1, 0
        title = "1-minute opening detail | shaded first five rows form the ORB candle"
    else:
        rows = payload["history_five_minute"] + five[:1]
        time_key, period, split = "bar_start", 5, len(rows)-1
        title = "Five previous sessions + opening candle | context only; no author zone inferred"
    n = len(rows)
    if not n:
        raise ValueError((d, kind, "No candles"))
    values = [float(r[k]) for r in rows for k in ("high", "low")]
    if kind != "opening_1m":
        values += [payload["previous_high"], payload["previous_low"]]
        values += [float(r["ema200_5m"]) for r in rows if r.get("ema200_5m") is not None and math.isfinite(float(r["ema200_5m"]))]
        values += [t[k] for t in payload["trades"] for k in ("entry", "stop", "t1", "t2")]
    lo, hi = min(values), max(values)
    pad = max(hi-lo, 1) * .07
    lo, hi = lo-pad, hi+pad
    left, right, top, bottom = (PLOT[k] for k in ("left", "right", "top", "bottom"))
    width, height = right-left, bottom-top

    def X(index):
        return left + index/n*width

    def Y(price):
        return top + (hi-price)/(hi-lo)*height

    def time_index(time):
        stamp = datetime.fromisoformat(f"{d}T{time}:00+05:30")
        for i, row in enumerate(rows):
            start = dt(row[time_key])
            if start <= stamp < start+timedelta(minutes=period):
                return i + (stamp-start).total_seconds()/(period*60)
        return None

    levels = [{"label": "Opening high", "price": payload["geometry"]["high"], "authority": "MEASURED_AFTER_09_20", "colour": "#A4750A", "dash": "", "from_index": split+(1 if period == 5 else 5)},
              {"label": "Opening low", "price": payload["geometry"]["low"], "authority": "MEASURED_AFTER_09_20", "colour": "#A4750A", "dash": "", "from_index": split+(1 if period == 5 else 5)},
              {"label": "Previous high", "price": payload["previous_high"], "authority": "MEASURED_PREVIOUS_SESSION", "colour": "#6E7585", "dash": "", "from_index": split},
              {"label": "Previous low", "price": payload["previous_low"], "authority": "MEASURED_PREVIOUS_SESSION", "colour": "#6E7585", "dash": "", "from_index": split}]
    for path in payload["paths"]:
        if path["method"] == "Method 2" and path["inner_level"] is not None:
            levels.append({"label": f'Inner {path["direction"]}', "price": path["inner_level"], "authority": "ENGINE_PROVISIONAL_K2_LATEST", "colour": "#B76616", "dash": "10 6", "from_index": split})
    meta = {"date": d, "kind": kind, "case_id": case["case_id"], "config": "A", "plot": PLOT,
            "scale": {"price_low": lo, "price_high": hi, "count": n}, "period_minutes": period,
            "time_key": time_key, "candles": rows, "levels": levels, "trades": payload["trades"],
            "orb_confirmed_signals": [], "author_entry": payload["author_entry"], "author_box": AUTHOR_BOX,
            "author_label": AUTHOR_LABEL, "source_hashes": payload["source_hashes"], "markers": [], "trendlines": []}
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Arial,Helvetica,sans-serif">',
         '<rect width="2000" height="1250" fill="#FFFFFF"/>',
         f'<defs><clipPath id="plot_clip"><rect x="{left}" y="{top}" width="{width}" height="{height}"/></clipPath></defs>',
         text(60, 42, f'{d} | NIFTY 50 | ORB author review | A', 32, "#183149", "bold"),
         text(60, 77, title, 23),
         text(60, 112, f'Opening 09:15-09:20 {payload["geometry"]["colour"]}: O {payload["geometry"]["open"]:,.2f}  H {payload["geometry"]["high"]:,.2f}  L {payload["geometry"]["low"]:,.2f}  C {payload["geometry"]["close"]:,.2f}', 23),
         text(60, 143, f'Body {payload["geometry"]["body_points"]:.2f} ({payload["geometry"]["body_pct"]:.2f}%) | Upper wick {payload["geometry"]["upper_wick"]:.2f} ({100*payload["geometry"]["upper_wick"]/payload["geometry"]["range_points"]:.2f}%) | Lower wick {payload["geometry"]["lower_wick"]:.2f} ({100*payload["geometry"]["lower_wick"]/payload["geometry"]["range_points"]:.2f}%) | Gap {payload["gap"]:+.2f}', 21),
         '<rect x="1490" y="37" width="450" height="45" rx="8" fill="#F7E4C1"/>', text(1510, 68, 'ORB: NO CONFIRMED SIGNAL', 23, "#754C11", "bold")]
    for k in range(7):
        price = lo+(hi-lo)*k/6
        o += [f'<line x1="{left}" x2="{right}" y1="{Y(price):.2f}" y2="{Y(price):.2f}" stroke="#E8EDF2"/>', text(5, Y(price)+7, f'{price:,.0f}', 21, "#5E6A75")]
    o.append(f'<rect x="{X(split):.2f}" y="{top}" width="{width/n*(1 if period == 5 else 5):.2f}" height="{height}" fill="#F9D882" opacity="0.35"/>')
    for i, row in enumerate(rows):
        col = "#008976" if row["close"] >= row["open"] else "#CC3B58"
        x = X(i+.5)
        bw = width/n*.65
        o.append(f'<g class="candle" data-index="{i}" data-time="{esc(row[time_key])}" data-open="{row["open"]}" data-high="{row["high"]}" data-low="{row["low"]}" data-close="{row["close"]}"><title>{esc(row[time_key])} O {row["open"]} H {row["high"]} L {row["low"]} C {row["close"]}</title><line class="wick" x1="{x:.3f}" x2="{x:.3f}" y1="{Y(row["high"]):.3f}" y2="{Y(row["low"]):.3f}" stroke="{col}" stroke-width="1.7"/><rect class="body" x="{x-bw/2:.3f}" y="{Y(max(row["open"],row["close"])):.3f}" width="{bw:.3f}" height="{max(abs(Y(row["open"])-Y(row["close"])),1):.3f}" fill="{col}"/></g>')
    o.append(f'<line x1="{X(split):.2f}" x2="{X(split):.2f}" y1="{top}" y2="{bottom}" stroke="#82909D" stroke-dasharray="6 5"/>')
    for level in levels:
        if lo <= level["price"] <= hi and level["from_index"] < n:
            o.append(f'<line class="reference_level" data-label="{esc(level["label"])}" data-price="{level["price"]}" x1="{X(level["from_index"]):.3f}" x2="{right}" y1="{Y(level["price"]):.3f}" y2="{Y(level["price"]):.3f}" stroke="{level["colour"]}" stroke-dasharray="{level["dash"]}" stroke-width="2"/>')
    # Indicator samples are drawn at completion, never at a future minute.
    indicator = []
    if period == 5:
        indicator = [(i+1, row.get("ema200_5m")) for i, row in enumerate(rows)]
    else:
        previous_ema = payload["previous_five_minute"][-1]["ema200_5m"]
        for i, row in enumerate(rows):
            completed = [r for r in five if dt(r["bar_end"]) <= dt(row["timestamp"])]
            value = completed[-1]["ema200_5m"] if completed else previous_ema
            indicator.append((i, value))
    points, old_y = [], None
    for i, value in indicator:
        if value is not None and math.isfinite(value):
            yy = Y(value)
            if period == 1 and old_y is not None:
                points.append(f'{X(i):.3f},{old_y:.3f}')
            points.append(f'{X(i):.3f},{yy:.3f}')
            old_y = yy
    o.append(f'<polyline class="ema" points="{" ".join(points)}" fill="none" stroke="#246AB4" stroke-width="3" clip-path="url(#plot_clip)"/>')
    meta["indicator_samples"] = indicator
    if True:
        offset = len(payload["previous_five_minute"])-split if period == 5 else 0
        for path in payload["paths"]:
            if path["method"] != "Method 2" or path["trendline"] is None:
                continue
            pts = []
            for i, row in enumerate(rows):
                if period == 5:
                    full_index = i+offset
                    if kind == "history_5m" and full_index < path["trendline_anchors"][0]:
                        continue
                    delta = full_index-len(payload["previous_five_minute"])
                else:
                    delta = (dt(row["timestamp"])-dt(five[0]["bar_start"])).total_seconds()//300
                value = path["trendline"]+path["trendline_slope"]*delta
                pts.append(f'{X(i+.5):.3f},{Y(value):.3f}')
            col = "#189E91" if path["direction"] == "LONG" else "#BA559C"
            meta["trendlines"].append({"direction": path["direction"], "value_at_open": path["trendline"], "slope_per_5m": path["trendline_slope"], "anchors": path["trendline_anchors"], "authority": "ENGINE_PROVISIONAL_LAST_TWO_K2"})
            o.append(f'<polyline class="trendline" data-direction="{path["direction"]}" points="{" ".join(pts)}" fill="none" stroke="{col}" stroke-width="2" stroke-dasharray="9 7" clip-path="url(#plot_clip)"/>')
            if period == 5:
                for anchor_no, full_index in enumerate(path["trendline_anchors"],1):
                    i = full_index-offset
                    if 0 <= i < n:
                        price = payload["previous_five_minute"][full_index]["low" if path["direction"] == "LONG" else "high"]
                        o.append(f'<circle class="trend_anchor" data-direction="{path["direction"]}" data-anchor-index="{full_index}" cx="{X(i+.5):.3f}" cy="{Y(price):.3f}" r="6" fill="white" stroke="{col}" stroke-width="2"/>')
                        o.append(text(X(i+.5)+5,Y(price)-12,f'{path["direction"][0]}{anchor_no}',18,col))
    # Exact existing ledger positions only. No author or diagnostic candidate marker.
    if kind != "history_5m":
        for index, trade in enumerate(payload["trades"], 1):
            entry_i = time_index(trade["entry_time"])
            end_i = time_index(trade["exits"][-1]["time"]) if trade["exits"][-1]["time"] else None
            if entry_i is not None:
                for name, colour in (("entry", "#754494"), ("stop", "#BA4050"), ("t1", "#208348"), ("t2", "#245EA5")):
                    price = trade[name]
                    if lo <= price <= hi:
                        o.append(f'<line class="trade_reference" data-trade="{esc(trade["trade_id"])}" data-role="{name}" data-price="{price}" x1="{X(entry_i):.3f}" x2="{X(end_i+1/period) if end_i is not None else right:.3f}" y1="{Y(price):.3f}" y2="{Y(price):.3f}" stroke="{colour}" stroke-dasharray="4 5" stroke-width="2"/>')
            marker_data = [{"tag": f'E{index}', "time": trade["entry_time"], "price": trade["entry"], "role": "ENTRY"}]
            marker_data += [{"tag": f'X{index}.{exit["leg"]}', "time": exit["time"], "price": exit["price"], "role": f'EXIT_LEG_{exit["leg"]}'} for exit in trade["exits"] if exit["time"] and exit["price"] is not None]
            for m, marker in enumerate(marker_data):
                x_index = time_index(marker["time"])
                if x_index is None or not lo <= marker["price"] <= hi:
                    continue
                x, y = X(x_index), Y(marker["price"])
                meta["markers"].append({**marker, "trade_id": trade["trade_id"], "x_index": x_index})
                colour = "#754494" if marker["role"] == "ENTRY" else "#303B45"
                o.append(f'<g class="trade_marker" data-trade="{esc(trade["trade_id"])}" data-role="{marker["role"]}" data-time="{marker["time"]}" data-price="{marker["price"]}" data-x-index="{x_index}"><circle cx="{x:.3f}" cy="{y:.3f}" r="7" fill="{colour}" stroke="white" stroke-width="2"/>{text(x+8, min(bottom-8,max(top+22,y+(-18 if m%2 else 26))),marker["tag"],19,colour,"bold",extra="paint-order=\"stroke\" stroke=\"white\" stroke-width=\"4\"")}</g>')
    if kind == "history_5m":
        last_date = None
        for i, row in enumerate(rows):
            day = row[time_key][:10]
            if day != last_date:
                tick_x = min(X(i)+3,right-8)
                tick_align = 'text-anchor="end"' if X(i)>right-80 else ""
                o += [f'<line x1="{X(i):.2f}" x2="{X(i):.2f}" y1="{top}" y2="{bottom}" stroke="#A2ADBA" stroke-dasharray="3 5"/>', text(tick_x,bottom+28,day[5:],21,extra=tick_align)]
                last_date = day
    else:
        step = 10 if period == 1 else 12
        for i in range(0, n, step):
            label = ("P " if i < split else "") + rows[i]["time"]
            o.append(text(X(i),bottom+30,label,21))
        o.append(text(X(split)+5,top+26,"Today 09:15",20,"#5E6873"))
    o.append(text(60, 765, "Market candles and extrema: measured | Orange/teal/pink dashed: provisional engine levels/lines | Blue: completed 5m EMA200", 20))
    # Right-side numerical references do not overlap chart coordinates.
    o.append(text(1480,195,"REFERENCE VALUES",24,"#183149","bold"))
    for j, level in enumerate(levels):
        off = " off scale" if not lo <= level["price"] <= hi else ""
        o.append(text(1480,235+j*35,f'{level["label"]}: {level["price"]:,.2f}{off}',21,level["colour"]))
    o.append(text(1480,470,f'Engine EMA200 (5m): {payload["ema_at_opening_close"]:,.2f}',22,"#246AB4"))
    for direction, yy in (("LONG",505),("SHORT",540)):
        path = next(p for p in payload["paths"] if p["method"] == "Method 2" and p["direction"] == direction)
        times = [payload["previous_five_minute"][j]["time"] for j in path["trendline_anchors"]]
        o.append(text(1480,yy,f'TL {direction} anchors: '+" / ".join(times),20,"#189E91" if direction == "LONG" else "#BA559C"))
    o.append(text(1480,575,f'Previous session: {payload["previous_date"]}',21))
    o.append(text(1480,610,"Dashed inner/lines are NOT author levels.",20,"#9B5812"))
    o.append(text(60,810,"EXISTING SIMULATED PORTFOLIO LEDGER (no hypothetical ORB entry)",24,"#183149","bold"))
    for j, trade in enumerate(payload["trades"]):
        y = 848+j*95
        o.append(text(60,y,f'E{j+1}: {trade["strategy"]} {trade["method"]} {trade["direction"]} | signal {trade["signal_time"]} | entry {trade["entry_time"]} @ {trade["entry"]:,.2f}',22))
        o.append(text(60,y+29,f'Original SL {trade["stop"]:,.2f} | T1 {trade["t1"]:,.2f} | T2 {trade["t2"]:,.2f} | '+" | ".join(f'X{j+1}.{x["leg"]}: {x["time"] or "unresolved"} @ {x["price"]:,.2f}' if x["price"] is not None else f'X{j+1}.{x["leg"]}: unresolved' for x in trade["exits"]),21))
    if not payload["trades"]:
        o.append(text(60,850,"No executed portfolio trade is recorded. No entry, stop, target or exit price is fabricated.",22))
    o.append(text(60,1045,"CURRENT ORB PATHS AT 09:20 (both directions; author direction unknown)",23,"#183149","bold"))
    for j, path in enumerate(payload["paths"]):
        label = f'{path["direction"]} {path["method"]}: '+", ".join(path["failed"])
        o.append(text(60,1075+j*25,label,19))
    ax, ay, aw, ah = (AUTHOR_BOX[k] for k in ("x", "y", "width", "height"))
    o += [f'<rect id="author_annotation_area" x="{ax}" y="{ay}" width="{aw}" height="{ah}" fill="#FFFCF2" stroke="#B6AA8B" stroke-dasharray="8 6"/>',
          text(ax+18,ay+35,AUTHOR_LABEL,21,"#644E24","bold"), text(ax+18,ay+75,"Leave this area for the author.",21),
          text(ax+18,ay+120,"Method:",21), text(ax+18,ay+205,"Candle start/end and direction:",21),
          text(ax+18,ay+290,"Level/zone and establishing candles:",21), text(ax+18,ay+405,"Why this trade qualifies / rejects:",21)]
    for yy in (ay+150,ay+235,ay+325,ay+355,ay+445,ay+475,ay+505):
        o.append(f'<line x1="{ax+18}" x2="{ax+aw-18}" y1="{yy}" y2="{yy}" stroke="#CFC7B4"/>')
    o.append(text(60,1232,"IST starts; first close known09:20. EMA200 recursive, seeded with pre-period history. E/X are ledger minute labels, not exact intraminute times. Target gaps may be model fills.",18,"#64717D"))
    o.insert(1,f'<metadata id="phase59">{esc(json.dumps(meta,default=str))}</metadata>')
    o.append('</svg>')
    return "\n".join(o), meta


def main():
    payloads = json.loads((OUT / "case_data.json").read_text())
    before = json.loads((OUT / "before_hashes.json").read_text())["files"]
    data_hashes = {k:v for k,v in before.items() if k.startswith("data/processed/")}
    (OUT / "data_source_hashes.json").write_text(json.dumps(data_hashes,indent=2))
    trace = []
    for d, payload in payloads.items():
        kinds = ("overview", "opening_1m", "history_5m") if payload["case"]["priority"] else ("overview",)
        for kind in kinds:
            content, meta = render(payload, kind)
            name = f'{d}_{kind}'
            (OUT / "author_review_charts" / f'{name}.svg').write_text(content)
            months = {r[meta["time_key"]][:7] for r in meta["candles"]}
            plotted = [p for p in data_hashes if "/nifty50/" in p and any(f'year={m[:4]}/month={m[5:7]}/' in p for m in months)]
            indicator_inputs = [p for p in data_hashes if ("/nifty50/" in p or "/nifty50_warmup/" in p) and p.split("year=")[-1][:4]+"-"+p.split("month=")[-1][:2] <= d[:7]]
            meta["data_provenance"] = {"hash_manifest":"data_source_hashes.json", "plotted_partitions":plotted,
                                       "ema_input_partitions":indicator_inputs, "daily_official":"data/processed/nifty50_daily/candles.parquet",
                                       "ema_cutoff":"Each sample uses completed bars through its own timestamp only; seed from2025-07-01 pre-period history", "decision_cutoff":d+" 09:20 IST"}
            # Persist the complete provenance inside the SVG as well as the CSV.
            old_meta = content[content.index('<metadata'):content.index('</metadata>')+len('</metadata>')]
            content = content.replace(old_meta,f'<metadata id="phase59">{esc(json.dumps(meta,default=str))}</metadata>')
            (OUT / "author_review_charts" / f'{name}.svg').write_text(content)
            trace.append({"date": d, "kind": kind, "chart_svg": f'author_review_charts/{name}.svg', "chart_png": f'author_review_charts/{name}.png',
                          "config": "A", "journal_rows": payload["case"]["journal_sheet_rows"], "handwritten_reference": payload["case"]["handwritten_reference"],
                          "source_daily_json": f'daily/{d}.json', "original_data": f'data/processed/nifty50/year={d[:4]}/month={d[5:7]}/candles.parquet',
                          "all_plotted_raw_partitions":plotted, "ema_input_partitions":indicator_inputs,
                          "daily_official_data":"data/processed/nifty50_daily/candles.parquet", "data_sha256_manifest":"data_source_hashes.json",
                          "source_pdf": "docs/strategy_docs/ORB_Strategy_Rulebook-2.pdf", "source_pdf_pages": payload["case"]["source_pdf_pages"],
                          "ledger": "reports/phase5/phase55_combined_backtest/all_executed_trades.csv", "ledger_trade_ids": [t["trade_id"] for t in meta["trades"]],
                          "candles_drawn": len(meta["candles"]), "author_entry_time": None, "author_entry_price": None,
                          "engine_level_authority": "Provisional latest k2 inner / last-two-pivot trendline, not authored levels"})
    import csv
    with open(OUT / "source_to_chart_traceability.csv", "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(trace[0]))
        writer.writeheader()
        writer.writerows({k:json.dumps(v) if isinstance(v,list) else v for k,v in r.items()} for r in trace)
    print(f'Created {len(trace)} SVG charts for {len(payloads)} unique review dates')


if __name__ == "__main__":
    main()
