"""Phase 3.3: per-trade annotated SVG charts (no dependencies). Every candle is a real 5-minute candle rebuilt from the raw one-minute data (``phase33_lib.World``); nothing is invented.

Three panels per trade: (1) the previous session with the selected zone's source candle and the previous-day high, (2) a ZOOM on the retest and the confirmation candle with the
confirmation close measured against the zone floor (candles after the entry are drawn shaded and labelled POST_ENTRY: context only), (3) the whole session of the trade.
"""

from __future__ import annotations

from datetime import date
from html import escape

from phase33_lib import Candle, World, hm

W, H = 1500, 1010
GREEN, RED = "#2e7d32", "#c62828"


class Panel:
    def __init__(self, x0: float, y0: float, w: float, h: float, lo: float, hi: float, n: float):
        self.x0, self.y0, self.w, self.h, self.lo, self.hi, self.n = x0, y0, w, h, lo, hi, n

    def y(self, p: float) -> float:
        return self.y0 + (self.hi - p) / (self.hi - self.lo) * self.h

    def x(self, i: float) -> float:  # i = candle position (float allowed: minutes/5)
        return self.x0 + (i + 0.5) / self.n * self.w

    @property
    def cw(self) -> float:
        return self.w / self.n


def _frame(p: Panel, title: str, out: list[str], ticks: int = 5) -> None:
    out.append(f'<rect x="{p.x0}" y="{p.y0}" width="{p.w}" height="{p.h}" fill="#fff" stroke="#bbb"/>')
    out.append(f'<text x="{p.x0}" y="{p.y0 - 8}" font-size="13" font-weight="bold">{escape(title)}</text>')
    for k in range(ticks + 1):
        v = p.lo + (p.hi - p.lo) * k / ticks
        out.append(f'<line x1="{p.x0}" x2="{p.x0 + p.w}" y1="{p.y(v):.1f}" y2="{p.y(v):.1f}" stroke="#eee"/><text x="{p.x0 - 4}" y="{p.y(v) + 4:.1f}" text-anchor="end" fill="#555" font-size="10">{v:,.1f}</text>')


def _candles(p: Panel, cs: list[Candle], out: list[str], start_pos: int = 0, shade_from: int | None = None) -> None:
    for k, c in enumerate(cs):
        pos = start_pos + k
        col = GREEN if c.close >= c.open else RED
        xm = p.x(pos)
        op = 0.45 if (shade_from is not None and k >= shade_from) else 1.0
        out.append(f'<g opacity="{op}"><line x1="{xm:.1f}" x2="{xm:.1f}" y1="{p.y(c.high):.1f}" y2="{p.y(c.low):.1f}" stroke="{col}"/>'
                   f'<rect x="{xm - p.cw * 0.34:.1f}" y="{p.y(max(c.open, c.close)):.1f}" width="{p.cw * 0.68:.1f}" height="{max(abs(p.y(c.open) - p.y(c.close)), 1):.1f}" fill="{col}"/></g>')


def _zone(p: Panel, lo: float, hi: float, out: list[str], x_from: float | None = None, label: bool = True, left: bool = False) -> None:
    xs = p.x0 if x_from is None else max(p.x0, x_from)
    out.append(f'<rect x="{xs:.1f}" y="{p.y(hi):.1f}" width="{p.x0 + p.w - xs:.1f}" height="{max(p.y(lo) - p.y(hi), 1.5):.1f}" fill="#1565c0" opacity="0.16"/>')
    out.append(f'<line x1="{xs:.1f}" x2="{p.x0 + p.w}" y1="{p.y(hi):.1f}" y2="{p.y(hi):.1f}" stroke="#1565c0" stroke-width="1.2"/>')
    out.append(f'<line x1="{xs:.1f}" x2="{p.x0 + p.w}" y1="{p.y(lo):.1f}" y2="{p.y(lo):.1f}" stroke="#0d47a1" stroke-width="1.6" stroke-dasharray="6,3"/>')
    if label:
        xl, anc = (p.x0 + 6, "start") if left else (p.x0 + p.w - 4, "end")
        out.append(f'<text x="{xl}" y="{p.y(hi) - 3:.1f}" text-anchor="{anc}" fill="#1565c0" font-size="10">zone ceiling {hi:,.2f}</text>')
        out.append(f'<text x="{xl}" y="{p.y(lo) + 12:.1f}" text-anchor="{anc}" fill="#0d47a1" font-size="10" font-weight="bold">zone FLOOR {lo:,.2f}</text>')


def _range(cs: list[Candle], extra: list[float], pad: float = 0.06) -> tuple[float, float]:
    lo = min([c.low for c in cs] + extra)
    hi = max([c.high for c in cs] + extra)
    d = (hi - lo) * pad + 1
    return lo - d, hi + d


def trade_chart(W_: World, r: dict, manual: list[dict]) -> str:  # noqa: C901
    d = date.fromisoformat(r["date"])
    p_ = W_.prev(d)
    cs, pcs = W_.candles[d], W_.candles[p_]
    lo, hi = r["zone_floor"], r["zone_ceiling"]
    ci = next(i for i, c in enumerate(cs) if f"{c.start:%Y-%m-%d %H:%M}" == r["confirmation_candle_start"])
    ji = next(i for i, c in enumerate(cs) if hm(c.start) == r["interaction_candle_start"])
    src_i = next(i for i, c in enumerate(pcs) if f"{c.start:%Y-%m-%d %H:%M}" == r["zone_source_candle_start"])
    dh_i = next(i for i, c in enumerate(pcs) if c.high == r["previous_day_high"])
    conf = cs[ci]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="Helvetica,Arial,sans-serif" font-size="11">', "<style>text{paint-order:stroke;stroke:#fff;stroke-width:3px;stroke-linejoin:round}</style>",
           f'<rect width="{W}" height="{H}" fill="#fafafa"/>']
    below = -r["confirmation_close_minus_floor"]
    out.append(f'<text x="20" y="24" font-size="16" font-weight="bold">{escape(r["trade_id"])}  PDR LONG  {r["date"]}  -  confirmation close {conf.close:,.2f} is {below:,.2f} points BELOW the zone floor {lo:,.2f}  [{escape(r["classification"])}]</text>')
    out.append(f'<text x="20" y="42" fill="#555">real 5-minute candles rebuilt from the raw 1-minute data; zone = {escape(r["zone_method"])} (body top .. wick high of the {r["zone_source_candle_start"][-5:]} candle of {r["previous_session"]}); '
               f'fill {r["entry_price"]:,.2f} at {r["earliest_fill_timestamp"][-5:]} (open of the next 1-minute bar); candles after the entry are POST_ENTRY context only</text>')
    # ---- panel 1: previous session
    lo1, hi1 = _range(pcs, [lo, hi])
    p1 = Panel(70, 80, 560, 330, lo1, hi1, len(pcs))
    _frame(p1, f"1. Previous session {r['previous_session']}: zone source candle, previous-day high", out)
    _zone(p1, lo, hi, out, x_from=p1.x(src_i) - p1.cw / 2, left=True)
    out.append(f'<line x1="{p1.x0}" x2="{p1.x0 + p1.w}" y1="{p1.y(r["previous_day_high"]):.1f}" y2="{p1.y(r["previous_day_high"]):.1f}" stroke="#b71c1c" stroke-dasharray="3,3"/>'
               f'<text x="{p1.x0 + 4}" y="{p1.y(r["previous_day_high"]) - 3:.1f}" fill="#b71c1c" font-size="10">previous-day high {r["previous_day_high"]:,.2f} ({r["previous_day_high_candle_start"]})</text>')
    _candles(p1, pcs, out)
    sc = pcs[src_i]
    out.append(f'<rect x="{p1.x(src_i) - p1.cw * 0.6:.1f}" y="{p1.y(sc.high) - 3:.1f}" width="{p1.cw * 1.2:.1f}" height="{p1.y(sc.low) - p1.y(sc.high) + 6:.1f}" fill="none" stroke="#f9a825" stroke-width="2"/>')
    out.append(f'<text x="{p1.x(src_i) - 8:.1f}" y="{p1.y(sc.low) + 24:.1f}" text-anchor="end" font-weight="bold" fill="#e65100">ZONE SOURCE {hm(sc.start)}</text>')
    if dh_i != src_i:
        dc = pcs[dh_i]
        out.append(f'<rect x="{p1.x(dh_i) - p1.cw * 0.6:.1f}" y="{p1.y(dc.high) - 3:.1f}" width="{p1.cw * 1.2:.1f}" height="{p1.y(dc.low) - p1.y(dc.high) + 6:.1f}" fill="none" stroke="#b71c1c" stroke-width="1.5" stroke-dasharray="3,2"/>')
        out.append(f'<text x="{p1.x(dh_i):.1f}" y="{p1.y(dc.high) - 8:.1f}" text-anchor="middle" fill="#b71c1c" font-weight="bold">DAY HIGH {hm(dc.start)}</text>')
    out.append(f'<text x="{p1.x0 + 6}" y="{p1.y0 + p1.h + 16}" fill="#444">zone source is {"" if r["zone_is_previous_day_high_candle"] else "NOT "}the previous-day-high candle'
               f'{"" if r["zone_is_previous_day_high_candle"] else f" (zone ceiling {r["zone_ceiling_below_previous_day_high"]:,.2f} points below the day high)"}</text>')
    # ---- panel 2: zoom on the retest and confirmation
    a, b = max(0, ji - 2), min(len(cs), ci + 4)
    win = cs[a:b]
    lo2, hi2 = _range(win, [lo, hi, r["entry_price"]], 0.09)
    p2 = Panel(700, 80, 780, 330, lo2, hi2, len(win))
    _frame(p2, "2. ZOOM: retest and confirmation (shaded = POST_ENTRY, context only)", out)
    _zone(p2, lo, hi, out, left=True)
    post_k = ci - a + 1
    _candles(p2, win, out, 0, shade_from=post_k)
    for idx, lab, col, below_ in ((ji, "TEST", "#6a1b9a", True), (ci, "CONFIRM (green)", "#1b5e20", False)):
        k = idx - a
        c = cs[idx]
        yy = p2.y(c.low) + 14 if below_ else p2.y(c.high) - 6
        out.append(f'<text x="{p2.x(k):.1f}" y="{yy:.1f}" text-anchor="middle" font-weight="bold" fill="{col}">{lab} {hm(c.start)}</text>')
    kx = ci - a
    xc = p2.x(kx) + p2.cw * 0.5
    out.append(f'<line x1="{xc:.1f}" x2="{xc:.1f}" y1="{p2.y(lo):.1f}" y2="{p2.y(conf.close):.1f}" stroke="#d50000" stroke-width="2.5"/>')
    out.append(f'<text x="{xc - 6:.1f}" y="{(p2.y(lo) + p2.y(conf.close)) / 2:.1f}" text-anchor="end" fill="#d50000" font-weight="bold">close {conf.close:,.2f}: {below:,.2f} pts below floor</text>')
    out.append(f'<polygon points="{xc:.1f},{p2.y(r["entry_price"]):.1f} {xc + 9:.1f},{p2.y(r["entry_price"]) - 6:.1f} {xc + 9:.1f},{p2.y(r["entry_price"]) + 6:.1f}" fill="#000"/>'
               f'<text x="{xc + 12:.1f}" y="{p2.y(r["entry_price"]) + 4:.1f}" font-weight="bold">LONG entry {r["entry_price"]:,.2f} @ {r["earliest_fill_timestamp"][-5:]}</text>')
    out.append(f'<text x="{p2.x0 + 6}" y="{p2.y0 + p2.h - 6}" fill="#444">retest low {r["retest_low_5m"]:,.2f} = {r["zone_penetration_depth_below_floor_5m"]:,.2f} pts below the floor; test candle closed {"BELOW" if r["interaction_close_below_floor"] else "at/above"} the floor</text>')
    # ---- panel 3: whole session
    lo3, hi3 = _range(cs, [lo, hi, r["previous_day_high"]], 0.03)
    p3 = Panel(70, 470, 1410, 400, lo3, hi3, len(cs))
    _frame(p3, f"3. Session {r['date']}: gap-up open {r['session_open']:,.2f} ({r['gap_points']:+.2f} vs official close {r['official_previous_close']:,.2f}); zone extended forward; entry; journal", out, 6)
    _zone(p3, lo, hi, out, label=True, left=False)
    out.append(f'<line x1="{p3.x0}" x2="{p3.x0 + p3.w}" y1="{p3.y(r["previous_day_high"]):.1f}" y2="{p3.y(r["previous_day_high"]):.1f}" stroke="#b71c1c" stroke-dasharray="3,3"/>'
               f'<text x="{p3.x0 + p3.w - 4}" y="{p3.y(r["previous_day_high"]) - 3:.1f}" text-anchor="end" fill="#b71c1c" font-size="10">previous-day high {r["previous_day_high"]:,.2f}</text>')
    _candles(p3, cs, out, 0, shade_from=ci + 1)
    for idx, lab, col in ((ji, "TEST", "#6a1b9a"), (ci, "CONFIRM", "#1b5e20")):
        out.append(f'<text x="{p3.x(idx):.1f}" y="{p3.y(cs[idx].high) - 6:.1f}" text-anchor="middle" font-weight="bold" fill="{col}">{lab}</text>')
    mins_ = (conf.end.hour * 60 + conf.end.minute - (9 * 60 + 15)) / 5.0 - 0.5
    out.append(f'<polygon points="{p3.x(mins_):.1f},{p3.y(r["entry_price"]):.1f} {p3.x(mins_) - 7:.1f},{p3.y(r["entry_price"]) + 14:.1f} {p3.x(mins_) + 7:.1f},{p3.y(r["entry_price"]) + 14:.1f}" fill="#000"/>'
               f'<text x="{p3.x(mins_) + 10:.1f}" y="{p3.y(r["entry_price"]) + 24:.1f}" font-weight="bold">ENTRY {r["entry_price"]:,.2f}</text>')
    k_ = 0
    for m in manual:
        t = int(m["entry_time_label"][:2]) * 60 + int(m["entry_time_label"][3:])
        pos = (t - (9 * 60 + 15)) / 5.0
        col = "#d500f9" if m["strategy_normalized"] == "PDR" else "#9e9e9e"
        out.append(f'<line x1="{p3.x(pos):.1f}" x2="{p3.x(pos):.1f}" y1="{p3.y0}" y2="{p3.y0 + p3.h}" stroke="{col}" stroke-dasharray="2,3"/>'
                   f'<text x="{p3.x(pos) + 3:.1f}" y="{p3.y0 + 12 + 12 * k_}" fill="{col}" font-size="10">JOURNAL {m["strategy_normalized"]} {m["entry_time_label"]} {m["exit_classification_entered"]} (row {m["journal_row"]})</text>')
        k_ += 1
    if not manual:
        out.append(f'<text x="{p3.x0 + 8}" y="{p3.y0 + 14}" fill="#9e9e9e" font-size="10">no manual journal trade this day</text>')
    # ---- caption
    cap = [f"Classification {r['classification']} ({r['confidence']} confidence): {r['basis']}", f"Journal: {r['journal_match']}; guide figures: {r['nearest_source_figure']}"]
    import textwrap
    lines = [ln for c_ in cap for ln in textwrap.wrap(c_, 190)][:5]
    for k, line in enumerate(lines):
        out.append(f'<text x="20" y="{900 + 16 * k}" font-size="12" fill="#222">{escape(line)}</text>')
    out.append(f'<text x="20" y="{990}" font-size="11" fill="#666">Candle OHLC in the zoom: confirmation O {conf.open:,.2f} H {conf.high:,.2f} L {conf.low:,.2f} C {conf.close:,.2f}; '
               f'interaction candle {r["interaction_candle_start"]} L {r["interaction_low"]:,.2f}. Zone floor/ceiling are the body top / wick high of the source candle. Charts support verification; the CSVs are authoritative.</text>')
    out.append("</svg>")
    return "\n".join(out)
