"""Phase 5.1: per-date evidence for every date written in the author's handwritten corrections.

Read-only on every earlier artefact. For each date it writes reports/phase5/phase51_author_corrections/evidence/<date>.json with: the session context (open, previous-day high / low / close, gap, 200-DMA values),
the five-minute candles with body / wick percentages, EMA(200) of 5-minute closes and the session low so far, and the engine's chronological signal timeline taken from the Phase 3.6 delivered tables
(confirmed signals with their controller events, rejected / invalidated setups with their reasons, executed trades). The candles come from the Phase 1 one-minute dataset through the unchanged session logic.

Usage: python scripts/phase51_evidence.py [--list]    (dates come from all_author_corrections.csv)
"""

from __future__ import annotations

import csv
import json
import sys
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)

OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def candle_rows(c) -> list[dict]:
    rows, low_so_far, high_so_far = [], float("inf"), 0.0
    for r in c.candles.itertuples():
        rng = r.high - r.low
        body = abs(r.close - r.open)
        uw, lw = r.high - max(r.open, r.close), min(r.open, r.close) - r.low
        prior_low = low_so_far
        low_so_far = min(low_so_far, r.low)
        high_so_far = max(high_so_far, r.high)
        rows.append({"start": r.bar_start.strftime("%H:%M"), "end": r.bar_end.strftime("%H:%M"), "o": round(r.open, 2), "h": round(r.high, 2), "l": round(r.low, 2), "c": round(r.close, 2), "colour": "G" if r.close > r.open else ("R" if r.close < r.open else "D"),
                     "body_pct": None if rng <= 0 else round(100 * body / rng, 1), "upper_wick_pct": None if rng <= 0 else round(100 * uw / rng, 1), "lower_wick_pct": None if rng <= 0 else round(100 * lw / rng, 1), "range": round(rng, 2),
                     "ema200": None if r.ema200_5m != r.ema200_5m else round(float(r.ema200_5m), 2), "close_minus_ema": None if r.ema200_5m != r.ema200_5m else round(r.close - float(r.ema200_5m), 2),
                     "session_low_before_this_candle": None if prior_low == float("inf") else round(prior_low, 2), "close_below_prior_session_low": bool(prior_low != float("inf") and r.close < prior_low), "session_low_incl": round(low_so_far, 2), "session_high_incl": round(high_so_far, 2)})
    return rows


def main() -> int:
    dates = sorted({r["date"] for r in rd(OUT / "all_author_corrections.csv") if r["date"]})
    if "--list" in sys.argv:
        print(dates)
        return 0
    m1 = load_one_minute()
    ctxs, _infos = build_session_contexts(m1, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    sig, rej, ign, trd, days = (rd(P36 / n) for n in ("all_strategy_signals.csv", "rejected_signals.csv", "ignored_signals.csv", "all_trades_detailed.csv", "daily_summary.csv"))
    by = defaultdict(lambda: defaultdict(list))
    for k, rows in (("signals", sig), ("rejected", rej), ("ignored", ign), ("trades", trd), ("daily", days)):
        for r in rows:
            by[r["date"]][k].append(r)
    for d in dates:
        dt = date.fromisoformat(d)
        c = ctxs.get(dt)
        if c is None:
            (OUT / "evidence" / f"{d}.json").write_text(json.dumps({"date": d, "error": "no session context (excluded or outside the dataset)"}))
            continue
        pv = c.previous
        first = c.candles.iloc[0]
        ev = {"date": d, "session": {"open": c.open_price, "prev_high": None if pv is None else pv.high, "prev_low": None if pv is None else pv.low, "prev_close_official": None if pv is None else pv.close_official,
                                     "gap_points": None if pv is None else round(c.open_price - pv.close_official, 2), "daily_sma200_prev": c.daily_sma200_prev, "daily_ema200_prev": c.daily_ema200_prev,
                                     "first_candle": {"high": float(first.high), "low": float(first.low), "open": float(first.open), "close": float(first.close)}, "data_flags": list(c.data_flags)},
              "candles": candle_rows(c),
              "signals": [{k: r[k] for k in ("signal_id", "time", "strategy", "method", "direction", "reference_close", "entry_rule_status", "fully_valid_for_execution", "within_13_00_cutoff", "portfolio_state_at_signal", "controller_event", "controller_reason", "blocked_by", "trade_id", "competing_signals_same_minute", "reference_levels")} for r in by[d]["signals"]],
              "rejected": [{k: r[k] for k in ("category", "time", "strategy", "method", "direction", "failure_reason", "last_state", "reference_levels")} for r in by[d]["rejected"]],
              "trades": [{k: r[k] for k in ("trade_id", "strategy", "method", "direction", "trade_no_of_day", "signal_confirmed_at", "fill_timestamp", "entry_price", "initial_stop", "target_1", "target_2", "outcome", "leg1_exit_time", "leg2_exit_time", "gross_pnl_points_weighted", "setup_explanation", "selection_explanation")} for r in by[d]["trades"]],
              "daily": by[d]["daily"][0] if by[d]["daily"] else {}}
        (OUT / "evidence" / f"{d}.json").write_text(json.dumps(ev, indent=1, default=str))
    print(f"evidence for {len(dates)} dates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
