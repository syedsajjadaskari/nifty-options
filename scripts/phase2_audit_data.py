"""Phase 2 independent audit of the Phase 1 NIFTY 50 1-minute dataset.

Does not modify any data. Uses the same session code as the strategy engines so what is audited is
what is evaluated. Writes reports/phase2/dataset_verification.json and .md.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import date, time
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.calendar import NSE_HOLIDAYS  # noqa: E402
from nifty_trading.data.sessions import build_session_contexts, load_one_minute, stale_row_mask  # noqa: E402

OUT = ROOT / "reports" / "phase2"


def main() -> None:
    df = load_one_minute()
    ctxs, infos = build_session_contexts(df)
    t = df["timestamp"]
    tm = t.dt.time
    days = sorted(infos)
    rng = df.high - df.low
    res: dict = {}

    res["identity"] = {
        "columns": list(df.columns),
        "has_instrument_column": "instrument" in df.columns or "symbol" in df.columns,
        "price_range": [float(df.low.min()), float(df.high.max())],
        "volume_all_zero": bool((df.volume == 0).all()),
        "tick_size_0.05_violations": int(((df[["open", "high", "low", "close"]] * 100).round().astype(int) % 5 != 0).sum().sum()),
        "note": ("The Parquet carries no instrument column; identity rests on the Phase 1 manifest/metadata, the index-like price level "
                 "(~24-26k), 0.05 tick and zero volume. Metadata file flags historical_api_verified=false."),
    }
    meta = json.loads((ROOT / "data" / "metadata" / "nifty50_instrument.json").read_text())
    res["identity"]["phase1_metadata"] = meta
    res["identity"]["phase1_metadata_defects"] = [k for k, v in meta.items() if "MagicMock" in str(v)] + (
        ["historical_api_verified is false"] if meta.get("historical_api_verified") is False else [])

    res["timestamps"] = {
        "timezone": str(t.dt.tz), "rows": len(df), "first": str(t.min()), "last": str(t.max()), "duplicates": int(t.duplicated().sum()),
        "strictly_monotonic": bool(t.is_monotonic_increasing), "rows_with_nonzero_seconds": int((t.dt.second != 0).sum()),
        "convention": "START_OF_MINUTE (row HH:MM covers [HH:MM, HH:MM+1))",
        "evidence": {
            "median_range_0915": float(rng[tm == time(9, 15)].median()), "median_range_0916": float(rng[tm == time(9, 16)].median()),
            "median_range_1200": float(rng[tm == time(12, 0)].median()), "median_range_1529": float(rng[tm == time(15, 29)].median()),
            "median_range_1530": float(rng[tm == time(15, 30)].median()),
            "zero_range_share_0915": float((rng[tm == time(9, 15)] == 0).mean()),
            "zero_range_share_1530": float((rng[tm == time(15, 30)] == 0).mean()),
            "reading": ("A full-size bar at 09:15 and a mostly zero-range stub at 15:30 are what start-of-minute labels produce "
                        "(an end-of-minute label would give a stub at 09:15 and a full bar at 15:30)."),
        },
        "rule": "5m candle labelled 09:15 = rows 09:15..09:19, usable at 09:20:00. The 15:30 row is a closing-print stub and is excluded from candles.",
    }

    by_day = df.assign(d=t.dt.date).groupby("d").agg(n=("open", "size"), first=("timestamp", lambda s: s.min().time()), last=("timestamp", lambda s: s.max().time()))
    res["sessions"] = {
        "calendar_days_with_data": len(days),
        "usable": sum(i.usable for i in infos.values()),
        "row_count_distribution": {int(k): int(v) for k, v in by_day.n.value_counts().items()},
        "status_counts": dict(Counter(i.status.value for i in infos.values())),
        "flagged_sessions": {str(d): list(i.flags) + [i.status.value] for d, i in infos.items() if i.flags},
        "weekend_sessions": [str(d) for d in days if d.weekday() >= 5],
        "rows_after_1530": int((tm > time(15, 30)).sum()),
        "rows_after_1530_by_day": {str(k): int(v) for k, v in df[tm > time(15, 30)].groupby(t.dt.date).size().items()},
        "candles_per_usable_session": dict(Counter(len(c.candles) for c in ctxs.values())),
        "phase1_audit_reconciliation": ("Phase 1 reported '49 session boundary violations': this equals the 49 rows after 15:30 "
                                        "(2026-03-10: 29; 2026-08-03: 10; 2026-08-04: 10). They are clipped here and flagged, never used."),
    }

    weekdays = pd.bdate_range(days[0], days[-1]).date
    missing = [d for d in weekdays if d not in infos]
    cal = {date.fromisoformat(x) for x in NSE_HOLIDAYS}
    res["holidays"] = {
        "weekdays_without_data": [str(d) for d in missing],
        "explained_by_phase1_calendar": [str(d) for d in missing if d in cal],
        "NOT_explained_by_phase1_calendar": [str(d) for d in missing if d not in cal],
        "phase1_calendar_dates_that_HAVE_data": sorted(str(d) for d in cal if d in infos),
        "external_check": ("A web search found secondary sources (not the NSE circular) listing 2026-01-15 (Maharashtra municipal elections) "
                           "and 2026-03-26 (Ram Navami) as closures; 2026-03-31 appeared in one source; 2026-05-28 could not be confirmed. "
                           "These four weekdays are therefore treated as UNVERIFIED gaps: sessions that follow them are not evaluated "
                           "by strategies that need a previous-day reference."),
        "conclusion": ("Phase 1's calendar lists 2026-02-17, 2026-03-20, 2026-03-27 and 2026-05-27 as holidays although full sessions exist for "
                       "them, and omits the four no-data weekdays above. Phase 1's 'API data unavailable' classification of those four days "
                       "is unproven."),
    }
    res["previous_session_flags"] = {str(d): list(c.data_flags) for d, c in ctxs.items() if c.data_flags}

    # ---- frozen-feed check (found by the independent review; the first audit pass missed it)
    window = df[(tm >= time(9, 15)) & (tm <= time(15, 29))]
    stale_days: dict = {}
    for d, g in window.groupby(window.timestamp.dt.date):
        g = g.sort_values("timestamp")
        m = stale_row_mask(g)
        if m.any():
            rows = g[m]
            after = g[g.timestamp > rows.timestamp.max()]
            jump = None if after.empty else float(after.iloc[0].high - after.iloc[0].low)
            stale_days[str(d)] = {"frozen_rows": int(m.sum()), "from": rows.timestamp.min().strftime("%H:%M"), "to": rows.timestamp.max().strftime("%H:%M"),
                                  "frozen_price": float(rows.close.iloc[0]), "next_bar_range_after_freeze": jump}
    res["feed_quality"] = {
        "rule": "run of >= 5 consecutive 1-minute rows with O=H=L=C at one price (a frozen feed, not trading)",
        "sessions_with_frozen_rows": len(stale_days), "first": min(stale_days) if stale_days else None, "last": max(stale_days) if stale_days else None,
        "sessions_before_2026_08_03_with_frozen_rows": sum(1 for k in stale_days if k < "2026-08-03"),
        "median_zero_range_rows_per_session_before_2026_08_03": float(window[window.timestamp.dt.date < date(2026, 8, 3)].assign(z=lambda x: x.high == x.low)
                                                                      .groupby(window[window.timestamp.dt.date < date(2026, 8, 3)].timestamp.dt.date).z.sum().median()),
        "handling": ("rows excluded; every 5-minute candle containing one is dropped (15:15, 15:20, 15:25 on the affected sessions); the NEXT session is flagged "
                     "PREV_CLOSE_UNRELIABLE and is not evaluated by strategies that need a previous-day close/zone. Not repaired, not interpolated."),
        "unverified_previous_session_count": sum(1 for c in ctxs.values() if c.previous and c.previous.gap_to_this_session_unverified),
        "action_required": "Re-download 2026-08-03 .. 2026-08-31 from the broker (or confirm with the data owner); until then August 2026 cannot be evaluated by PDR/PDS/RF/ORB.",
        "days": stale_days,
    }

    first_ema = {str(d): bool(not np.isnan(c.candles.ema200_5m.iloc[0])) for d, c in ctxs.items()}
    res["indicator_warmup"] = {
        "ema200_5m_rule": "EMA(200) of completed 5m closes, SMA-seeded, NaN until 200 candles exist (no partial initialisation)",
        "sessions_whose_first_candle_has_no_ema": [d for d, v in first_ema.items() if not v],
        "first_session_with_ema_at_0915": next(d for d, v in first_ema.items() if v),
        "daily_sma200_available_sessions": sum(not np.isnan(c.daily_sma200_prev) for c in ctxs.values()),
        "daily_sma200_first_available": next(str(d) for d in sorted(ctxs) if not np.isnan(ctxs[d].daily_sma200_prev)),
        "total_usable_sessions": len(ctxs),
        "consequence": ("A 200-day MA candidate can be evaluated on only the last 47 sessions with the Phase 1 data; evaluating it over the whole "
                        "year needs >= 200 earlier daily candles (extra download) - a decision for the user, not made here."),
    }
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "dataset_verification.json").write_text(json.dumps(res, indent=2, default=str, ensure_ascii=False))
    md = ["# Dataset verification (generated by scripts/phase2_audit_data.py)\n"]
    for k, v in res.items():
        md += [f"## {k}\n", "```json", json.dumps(v, indent=2, default=str, ensure_ascii=False), "```\n"]
    (OUT / "dataset_verification.md").write_text("\n".join(md))
    print(json.dumps({"usable": res["sessions"]["usable"], "daily200": res["indicator_warmup"]["daily_sma200_available_sessions"]}))


if __name__ == "__main__":
    main()
