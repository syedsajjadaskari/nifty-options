"""Standalone ORB execution: entry at the first causally executable fill after the 09:20 confirmation, fixed 30-point stop / 60-point target, one trade, forced exit before 15:15.

Conventions (all labelled in the configuration manifest):
* ENTRY = the OPEN of the 09:20 one-minute bar (the earliest bar that starts at/after confirmation). The rulebook's "close of the 9:15 candle" (TO CONFIRM) differs from it by the move between the last
  minute's close and the next open (measured: mean 0.9 / max 3.0 points in 2025-26, mean 1.1 / max 6.75 in 2022-25, up to ~22% of the stop distance); it is reported as ``entry_vs_candle_close``. The bar must be CONTINUOUS (executable).
* SCAN starts with the entry bar itself (the fill is at its open, so its whole range is after the entry). Within a one-minute bar the order of touches is unknown.
* BOTH touched in one bar -> policy STOP_FIRST (rulebook's conservative default); the alternative (target first) is stored as ``alt_*`` for sensitivity, never used for the headline.
* A bar that OPENS beyond the stop fills at its open (adverse); a target fills at the target price (no price improvement); a bar that opens beyond the target counts as target first.
* FORCED EXIT at the OPEN of the 15:14 bar when still open (never at/after 15:15, never a closing-auction bar); a missing/non-executable 15:14 bar leaves the trade UNRESOLVED_EXIT.
"""

from __future__ import annotations

from datetime import time

from nifty_trading.core.execution_eligibility import bars_from_frame
from nifty_trading.research.orb_v2.config import OrbV2Config
from nifty_trading.research.orb_v2.models import SessionData


def _clock(ts) -> time:
    return ts.time()


def simulate(sd: SessionData, direction: str, cfg: OrbV2Config, cal) -> dict:
    bars = bars_from_frame(sd.day_minutes[["timestamp", "open", "high", "low", "close"]], cal)
    confirmed = sd.opening["confirmed_at"]
    fh, fm = (int(x) for x in cfg.forced_exit_clock.split(":"))
    forced_t = time(fh, fm)
    ent = next((i for i, b in enumerate(bars) if b.ts.replace(tzinfo=None) == confirmed), None)
    res: dict = {"traded": False, "entry_status": ""}
    if ent is None:
        return {**res, "entry_status": "NO_1M_BAR_AT_0920"}
    eb = bars[ent]
    if not eb.executable:
        return {**res, "entry_status": f"ENTRY_BAR_NOT_EXECUTABLE:{eb.ineligible}"}
    entry = float(eb.o)
    sgn = 1 if direction == "BUY" else -1
    sl, tp = entry - sgn * cfg.stop_points, entry + sgn * cfg.target_points
    res.update({"traded": True, "entry_status": "FILLED", "entry_time": eb.ts.replace(tzinfo=None), "entry_price": entry, "entry_bar_open": entry, "entry_bar_high": float(eb.h),
                "entry_bar_low": float(eb.l), "entry_bar_close": float(eb.c), "stop": sl, "target": tp, "entry_vs_candle_close": entry - sd.opening["close"]})
    mfe = mae = 0.0
    missing = 0
    prev_ts = None
    exit_info = None
    for b in bars[ent:]:
        ts = b.ts.replace(tzinfo=None)
        if _clock(ts) >= forced_t:
            break
        if prev_ts is not None and (ts - prev_ts).total_seconds() > 60:
            missing += int((ts - prev_ts).total_seconds() // 60) - 1
        prev_ts = ts
        if not b.executable:
            continue
        hi, lo, op = float(b.h), float(b.l), float(b.o)
        fav = (hi - entry) if sgn == 1 else (entry - lo)
        adv = (entry - lo) if sgn == 1 else (hi - entry)
        mfe, mae = max(mfe, fav), max(mae, adv)
        hit_sl = lo <= sl if sgn == 1 else hi >= sl
        hit_tp = hi >= tp if sgn == 1 else lo <= tp
        open_through_sl = (op <= sl) if sgn == 1 else (op >= sl)
        open_through_tp = (op >= tp) if sgn == 1 else (op <= tp)
        if b is not eb and open_through_tp and not open_through_sl:
            exit_info = (ts, tp, "TARGET", False, None)
        elif b is not eb and open_through_sl:
            exit_info = (ts, op, "STOP", False, None)
        elif hit_sl and hit_tp:
            first_stop = cfg.same_bar_policy == "STOP_FIRST"
            alt = (tp, "TARGET") if first_stop else (sl, "STOP")
            exit_info = (ts, sl if first_stop else tp, "STOP" if first_stop else "TARGET", True, alt)
        elif hit_sl:
            exit_info = (ts, sl, "STOP", False, None)
        elif hit_tp:
            exit_info = (ts, tp, "TARGET", False, None)
        if exit_info:
            break
    res["missing_minutes_while_open"] = missing
    if exit_info is None:
        fb = next((b for b in bars if _clock(b.ts) == forced_t), None)
        if fb is not None and fb.executable and _clock(fb.ts) < time(15, 15):
            exit_info = (fb.ts.replace(tzinfo=None), float(fb.o), "FORCED_EXIT", False, None)
        else:
            return {**res, "exit_status": "UNRESOLVED_EXIT", "exit_reason": "UNRESOLVED_EXIT", "mfe_points": mfe, "mae_points": mae}
    ts, px, reason, amb, alt = exit_info
    gross = sgn * (px - entry)
    res.update({"exit_status": "CLOSED", "exit_time": ts, "exit_price": px, "exit_reason": reason, "ambiguous_same_bar": amb, "gross_points": gross, "mfe_points": mfe, "mae_points": mae,
                "bars_held": int((ts - res["entry_time"]).total_seconds() // 60), "gap_through_stop": bool(reason == "STOP" and abs(px - sl) > 1e-9)})
    if alt:
        res["alt_exit_price"], res["alt_exit_reason"], res["alt_gross_points"] = alt[0], alt[1], sgn * (alt[0] - entry)
    return res
