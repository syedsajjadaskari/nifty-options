"""IRF V3 execution simulation (index points, SHORT only). Stand-alone: nothing is borrowed from earlier exit policies except the verified bar-executability classifier.

Conventions (every one is a labelled scenario parameter, see config.py):
* ENTRY  NEXT_1M_OPEN: the OPEN of the one-minute bar whose start equals the failure candle's end (first causally available price). The rulebook's 'close of the failure candle' (TO CONFIRM) is the
  SIGNAL_CLOSE reference scenario. The fill bar must exist and be CONTINUOUS and start no later than the 13:00:00 cutoff.
* STOP   entry + stop_points; TARGET entry - target_points (measured from the entry, not from the level).
* SCAN   starts with the entry bar (the fill is its open). A bar that OPENS beyond the stop fills at its open (adverse); a target fills at the target price; no price improvement.
* TIE    STOP_FIRST_5M (primary): if stop AND target are both touched inside the same 5-minute window, the stop is counted. MINUTE_ORDER: chronological one-minute bars, a single bar touching both -> stop.
* FORCED EXIT at the OPEN of the ``forced_exit`` bar when still open (15:14 default, never at/after the auction); a missing/non-executable bar leaves UNRESOLVED_EXIT.
"""

from __future__ import annotations

from datetime import time

import pandas as pd

from nifty_trading.research.irf_v3.config import IrfV3Config

AUCTION_REGIME_DATE = pd.Timestamp("2026-08-03")


def _bars(minutes: pd.DataFrame, cal):
    if cal is not None:
        from nifty_trading.core.execution_eligibility import bars_from_frame

        out = []
        for b in bars_from_frame(minutes[["timestamp", "open", "high", "low", "close"]], cal):
            out.append((pd.Timestamp(b.ts).tz_localize(None) if pd.Timestamp(b.ts).tzinfo else pd.Timestamp(b.ts), b.o, b.h, b.l, b.c, bool(b.executable)))
        return out
    out = []  # no calendar (synthetic / secondary-vendor example days): continuous = 09:15 <= clock < 15:30 (< 15:15 from the auction regime date)
    for r in minutes.sort_values("ts").itertuples(index=False):
        ts = pd.Timestamp(r.ts)
        end_t = time(15, 15) if ts.normalize() >= AUCTION_REGIME_DATE else time(15, 30)
        out.append((ts, float(r.open), float(r.high), float(r.low), float(r.close), time(9, 15) <= ts.time() < end_t))
    return out


def eligible_entry(signal_time: pd.Timestamp, cfg: IrfV3Config) -> bool:
    return signal_time.time() <= cfg.entry_cutoff


def simulate_short(minutes: pd.DataFrame, cal, signal_time: pd.Timestamp, signal_close: float, cfg: IrfV3Config) -> dict:
    res: dict = {"traded": False, "entry_status": ""}
    if not eligible_entry(signal_time, cfg):
        return {**res, "entry_status": "AFTER_ENTRY_CUTOFF"}
    bars = _bars(minutes, cal)
    ent = next((i for i, b in enumerate(bars) if b[0] == signal_time), None)
    if ent is None:
        return {**res, "entry_status": "NO_1M_BAR_AT_CONFIRMATION"}
    eb = bars[ent]
    if not eb[5]:
        return {**res, "entry_status": "ENTRY_BAR_NOT_EXECUTABLE"}
    entry = float(eb[1]) if cfg.entry_convention == "NEXT_1M_OPEN" else float(signal_close)
    sl, tp = entry + cfg.stop_points, entry - cfg.target_points
    res.update({"traded": True, "entry_status": "FILLED", "entry_time": eb[0], "entry_price": entry, "entry_bar_open": float(eb[1]), "entry_vs_signal_close": float(eb[1]) - float(signal_close),
                "stop": sl, "target": tp})
    forced = next((b for b in bars if b[0].normalize() == signal_time.normalize() and b[0].time() == cfg.forced_exit), None)
    live = [b for b in bars[ent:] if b[0].time() < cfg.forced_exit and b[5]]
    mfe = mae = 0.0
    exit_info = None
    missing = 0
    prev = None
    for b in live:
        if prev is not None and (b[0] - prev).total_seconds() > 60:
            missing += int((b[0] - prev).total_seconds() // 60) - 1
        prev = b[0]
    windows = {}
    if cfg.tie_policy == "STOP_FIRST_5M":
        for b in live:
            mins = b[0].hour * 60 + b[0].minute - (9 * 60 + 15)
            windows.setdefault(mins // 5, []).append(b)
        groups = [windows[k] for k in sorted(windows)]
    else:
        groups = [[b] for b in live]
    for grp in groups:
        sl_bar = next((b for b in grp if b[2] >= sl), None)
        tp_bar = next((b for b in grp if b[3] <= tp), None)
        if sl_bar is None and tp_bar is None:
            continue
        both = sl_bar is not None and tp_bar is not None
        if sl_bar is not None:  # the stop wins whenever it is touched in the same window (STOP_FIRST) - or alone
            px = float(sl_bar[1]) if (sl_bar[1] >= sl and sl_bar[0] != eb[0]) else sl
            exit_info = (sl_bar[0], px, "STOP", both, "TARGET" if both else "")
        else:
            exit_info = (tp_bar[0], tp, "TARGET", False, "")
        break
    if exit_info is None:
        if forced is not None and forced[5]:
            exit_info = (forced[0], float(forced[1]), "FORCED_EXIT", False, "")
        else:
            for b in live:
                mfe = max(mfe, entry - b[3])
                mae = max(mae, b[2] - entry)
            return {**res, "exit_status": "UNRESOLVED_EXIT", "exit_reason": "UNRESOLVED_EXIT", "mfe_points": mfe, "mae_points": mae, "missing_minutes_while_open": missing}
    ts, px, why, amb, alt = exit_info
    for b in live:
        if b[0] <= ts:  # excursions only up to and including the exit bar
            mfe = max(mfe, entry - b[3])
            mae = max(mae, b[2] - entry)
    res.update({"exit_status": "CLOSED", "exit_time": ts, "exit_price": px, "exit_reason": why, "same_window_both_touched": amb, "gross_points": entry - px, "mfe_points": mfe, "mae_points": mae,
                "holding_minutes": int((ts - res["entry_time"]).total_seconds() // 60), "missing_minutes_while_open": missing})
    return res
