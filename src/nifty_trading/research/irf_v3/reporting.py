"""Row builders, charts and per-day markdown for the Phase 7.0 deliverables."""

from __future__ import annotations

import pandas as pd

from nifty_trading.research.irf_v3 import charts as CH
from nifty_trading.research.irf_v3.config import IrfV3Config
from nifty_trading.research.irf_v3.models import M1, M2
from nifty_trading.research.irf_v3.signal_engine import SessionEval, overlap_class

SHORT = {M1: "M1", M2: "M2"}


def _hm(ts) -> str:
    return "" if ts is None or (not isinstance(ts, str) and pd.isna(ts)) else pd.Timestamp(ts).strftime("%H:%M")


def signal_row(window: str, ev: SessionEval, m: str) -> dict | None:
    tr = ev.traces[m]
    if tr.status != "SIGNAL":
        return None
    sel = ev.combined.get("selected_method")
    c = tr.confirmation_candle
    row = {"window": window, "date": ev.date, "method": m, "initial_range_high": tr.initial_range_high, "initial_range_low": tr.initial_range_low,
           "reference_level": tr.reference_level, "reference_candle_start": _hm(tr.reference_candle.start) if tr.reference_candle else "",
           "reference_candle_ohlc": f"{tr.reference_candle.open:.2f}/{tr.reference_candle.high:.2f}/{tr.reference_candle.low:.2f}/{tr.reference_candle.close:.2f}" if tr.reference_candle else "",
           "breakout_candle_start": _hm(tr.breakout_candle.start) if tr.breakout_candle else "", "breakout_close": tr.breakout_candle.close if tr.breakout_candle else "",
           "second_breakout_candle_start": _hm(tr.second_breakout_candle.start) if tr.second_breakout_candle else "", "second_breakout_close": tr.second_breakout_candle.close if tr.second_breakout_candle else "",
           "confirmation_candle_start": _hm(c.start), "confirmation_candle_close": c.close, "confirmation_timestamp": f"{c.end:%Y-%m-%d %H:%M:%S}",
           "signal_timestamp": f"{tr.signal_time:%Y-%m-%d %H:%M:%S}", "minutes_after_open": int((tr.signal_time - tr.signal_time.normalize()).total_seconds() // 60 - (9 * 60 + 15)),
           "status": ev.status[m], "failed_conditions": "; ".join(tr.failed_conditions), "ignored_red_before_breakout": tr.ignored_red_before_breakout,
           "later_cycles_after_first_signal(not_traded)": tr.later_cycles, "source_rule_ids": ",".join(tr.rule_ids), "overlap_class": overlap_class(ev)}
    res = ev.trades.get(m) or {}
    row["first_executable_entry_timestamp"] = f"{res['entry_time']:%Y-%m-%d %H:%M:%S}" if res.get("traded") else ""
    row["entry_status"] = res.get("entry_status", "")
    row["selected_in_combined"] = (sel == m) or (bool(ev.combined.get("tie")) and m in (M1, M2) and ev.status[m] == "SIGNAL_ELIGIBLE" and ev.traces[M1].signal_time == ev.traces[M2].signal_time)
    return row


def daily_row(window: str, ev: SessionEval, ev35: SessionEval) -> dict:
    s = ev.session
    r = {"window": window, "date": ev.date, "weekday": f"{pd.Timestamp(ev.date):%a}", "evaluable": s.evaluable, "not_evaluated_reason": s.reason}
    if s.evaluable:
        f = s.candles[0]
        r.update({"first_candle_ohlc": f"{f.open:.2f}/{f.high:.2f}/{f.low:.2f}/{f.close:.2f}", "initial_range_high": f.high, "initial_range_low": f.low, "first_candle_colour": "GREEN" if f.is_green else ("RED" if f.is_red else "DOJI"),
                  "candle_gap_in_session": s.gap_in_candles})
    for m in (M1, M2):
        k = SHORT[m]
        tr = ev.traces[m]
        r[f"{k}_activation"] = ("NOT_EVALUATED" if not s.evaluable else (">".join(tr.reached) if tr.reached else "NONE"))
        r[f"{k}_conditions_reached"] = ";".join(tr.reached)
        r[f"{k}_conditions_failed"] = "; ".join(tr.failed_conditions)
        r[f"{k}_reference_level"] = tr.reference_level
        r[f"{k}_earliest_signal"] = _hm(tr.signal_time)
        r[f"{k}_status"] = ev.status[m]
    r["overlap_class"] = overlap_class(ev)
    sel = ev.combined.get("selected_method", "")
    r["combined_selected"] = SHORT.get(sel, "") + ("+M1&M2 same instant (tie->M1)" if ev.combined.get("tie") else "")
    r["combined_outcome"] = ev.combined.get("outcome", "")
    res = ev.trades.get(sel) if sel else None
    res35 = ev35.trades.get(sel) if sel else None
    if res and res.get("traded"):
        r.update({"entry_time": _hm(res["entry_time"]), "entry_price": res["entry_price"], "stop_SL40": res["stop"], "target": res["target"], "exit_time": _hm(res.get("exit_time")), "exit_price": res.get("exit_price"),
                  "exit_reason": res.get("exit_reason"), "gross_points_SL40": res.get("gross_points")})
        if res35 and res35.get("traded"):
            r.update({"stop_SL35": res35["stop"], "exit_reason_SL35": res35.get("exit_reason"), "exit_price_SL35": res35.get("exit_price"), "gross_points_SL35": res35.get("gross_points")})
    r["no_trade_reason"] = "" if (res and res.get("traded")) else _no_trade_reason(ev)
    return r


def _no_trade_reason(ev: SessionEval) -> str:
    s = ev.session
    if not s.evaluable:
        return f"NOT_EVALUATED: {s.reason}"
    parts = []
    for m in (M1, M2):
        tr = ev.traces[m]
        if ev.status[m] == "NO_SIGNAL":
            parts.append(f"{SHORT[m]}: {tr.no_signal_reason} (missing: {'; '.join(tr.failed_conditions)})")
        elif ev.status[m] == "SIGNAL_AFTER_CUTOFF":
            parts.append(f"{SHORT[m]}: signal at {_hm(tr.signal_time)} is after the 13:00 entry cutoff")
        else:
            parts.append(f"{SHORT[m]}: {ev.status[m]}")
    return " | ".join(parts)


def trace_chart(ev: SessionEval, cfg: IrfV3Config, methods: list[str], title: str, subtitle: str, embed_png: str | None = None, extra: list[str] | None = None) -> str:
    s = ev.session
    c0 = s.candles
    sel = ev.combined.get("selected_method") if len(methods) == 2 else methods[0]
    res = ev.trades.get(sel) if sel else None
    tmax = max([ev.traces[m].signal_time for m in methods if ev.traces[m].signal_time is not None] + [c0[0].end])
    end_t = (res.get("exit_time") if (res and res.get("traded") and res.get("exit_time") is not None) else tmax) + pd.Timedelta(minutes=30)
    shown = [c for c in c0 if c.start <= end_t]
    if len(shown) < 12:
        shown = c0[:12]
    h = []
    marks, notes = [], list(extra or [])
    f = c0[0]
    h.append((f.high, f"Level A / marked level {f.high:.2f}", CH.PURPLE, True))
    marks.append((f.start, f.high, "first candle", CH.PURPLE))
    for m in methods:
        tr = ev.traces[m]
        if m == M2 and tr.reference_level is not None:
            h.append((tr.reference_level, f"Level B {tr.reference_level:.2f}", CH.ORANGE, True))
            if tr.reference_candle:
                marks.append((tr.reference_candle.start, tr.reference_level, "first red (B)", CH.ORANGE))
        if tr.breakout_candle:
            marks.append((tr.breakout_candle.start, tr.breakout_candle.high, f"{SHORT[m]} breakout", CH.BLUE))
        if tr.second_breakout_candle:
            marks.append((tr.second_breakout_candle.start, tr.second_breakout_candle.high, "2nd breakout", CH.BLUE))
        if tr.confirmation_candle:
            marks.append((tr.confirmation_candle.start, tr.confirmation_candle.low, f"{SHORT[m]} failure -> signal {tr.signal_time:%H:%M}", CH.RED))
        notes.append(f"{SHORT[m]}: " + (" -> ".join(f"{t:%H:%M} {txt}" for t, txt in tr.events[-3:]) if tr.events else "no events"))
    boxes = []
    if res and res.get("traded"):
        h += [(res["entry_price"], f"entry {res['entry_price']:.2f}", CH.TXT, False), (res["stop"], f"stop {res['stop']:.2f}", CH.RED, False), (res["target"], f"target {res['target']:.2f}", CH.GREEN, False)]
        et = res.get("exit_time") or shown[-1].end
        boxes = [(res["entry_time"], et, res["entry_price"], res["stop"], CH.RED), (res["entry_time"], et, res["entry_price"], res["target"], CH.GREEN)]
        if res.get("exit_time") is not None:
            marks.append((res["exit_time"], res["exit_price"], f"exit {res['exit_reason']} {res['gross_points']:+.2f}", CH.TXT))
    return CH.candle_chart(title, subtitle, shown, h, marks, boxes, notes, embed_png=embed_png)


def daily_markdown(window: str, ev: SessionEval, ev35: SessionEval) -> str:
    s = ev.session
    L = [f"# {ev.date} ({pd.Timestamp(ev.date):%A}) - window {window}", ""]
    if not s.evaluable:
        L += [f"**NOT EVALUATED**: {s.reason}", ""]
        return "\n".join(L)
    f = s.candles[0]
    L += [f"First 5-minute candle 09:15-09:20: O {f.open:.2f} H {f.high:.2f} L {f.low:.2f} C {f.close:.2f} ({'green' if f.is_green else 'red' if f.is_red else 'doji'}). Initial range {f.low:.2f} - {f.high:.2f}.",
          f"Complete 5-minute candles: {len(s.candles)}{' (a gap exists inside the session)' if s.gap_in_candles else ''}.", ""]
    for m in (M1, M2):
        tr = ev.traces[m]
        L += [f"## {m}", f"* Result: **{ev.status[m]}**" + (f" at {tr.signal_time:%H:%M} (failure candle {tr.confirmation_candle.start:%H:%M}-{tr.confirmation_candle.end:%H:%M}, close {tr.confirmation_candle.close:.2f})" if tr.status == 'SIGNAL' else f" - {tr.no_signal_reason}"),
              f"* Conditions reached (in order): {', '.join(tr.reached) or 'none'}", f"* Conditions failed / missing: {'; '.join(tr.failed_conditions) or 'none'}", f"* Reference level: {tr.reference_level}"]
        if m == M2:
            L.append(f"* Red candles ignored before the rally breakout: {tr.ignored_red_before_breakout}")
        for t, txt in tr.events[:12]:
            L.append(f"  * {t:%H:%M} {txt}")
        L.append("")
    sel = ev.combined.get("selected_method", "")
    L += ["## Combined IRF V3", f"* Overlap class: {overlap_class(ev)}", f"* Selected: {SHORT.get(sel, 'none')}" + (" (same-instant tie: both signals share one failure candle; Method 1 credited by the deterministic research policy TIE_METHOD_1 - identical entry, stop and target)" if ev.combined.get('tie') else ""),
          f"* Outcome: {ev.combined.get('outcome', '')} {ev.combined.get('reason', '')}"]
    for tag, e in (("SL40", ev), ("SL35", ev35)):
        res = e.trades.get(sel) if sel else None
        if res and res.get("traded"):
            L.append(f"* {tag}: entry {res['entry_time']:%H:%M} @ {res['entry_price']:.2f}, stop {res['stop']:.2f}, target {res['target']:.2f}, exit {res.get('exit_time'):%H:%M} @ {res.get('exit_price'):.2f} {res.get('exit_reason')}, {res.get('gross_points'):+.2f} index points"
                     if res.get('exit_time') is not None else f"* {tag}: entry {res['entry_price']:.2f} {res.get('exit_reason')}")
    if not sel:
        L.append("* No trade: " + _no_trade_reason(ev))
    return "\n".join(L) + "\n"
