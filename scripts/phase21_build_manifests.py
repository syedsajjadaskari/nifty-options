"""Phase 2.1: build the machine-readable session-quality manifest.

Writes data/metadata/session_quality_manifest.json - one entry for every calendar day of the analysis window with its
quality status (VALID, VALID_SPECIAL_SESSION, PARTIAL, CORRUPT, MISSING, UNVERIFIED), whether strategies may evaluate it,
why, and the evidence/metrics behind it. Weekends and confirmed holidays are listed separately with their evidence.

The status is computed by the same code the strategy engines use (``nifty_trading.data.sessions``); a test asserts the
committed manifest equals a fresh recomputation, so it cannot drift from the code.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.market_calendar import load_market_calendar  # noqa: E402
from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
)

MANIFEST = ROOT / "data" / "metadata" / "session_quality_manifest.json"
WINDOW = (date(2025, 9, 1), date(2026, 8, 31))
REVIEWED_EVENTS = {
    date(2026, 2, 1): "Union Budget Sunday: 1-minute ranges up to 205 points (12:11-12:36) coincide with the Budget-day sell-off; real, reviewed, not an artefact",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def build() -> dict:
    cal = load_market_calendar()
    df = load_one_minute()
    daily = load_daily_official()
    warm = load_warmup_one_minute()
    ctxs, infos = build_session_contexts(df, daily_df=daily, warmup_1m=warm)
    dd = df.assign(d=df.timestamp.dt.date, tm=df.timestamp.dt.time)
    dly = daily.set_index("date") if daily is not None else None
    sessions, non_trading = [], []
    day = WINDOW[0]
    while day <= WINDOW[1]:
        if day in infos:
            i = infos[day]
            g = dd[dd.d == day]
            reg = g[(g.tm >= time(9, 16)) & (g.tm <= time(15, 29))]
            reg = reg[~(i.cas_regime & (reg.tm >= time(15, 15)))]  # exclude the auction window from the range statistics
            rng = reg.high - reg.low
            pre = ctxs[day].previous if day in ctxs else None
            e = {
                "date": str(day), "weekday": day.strftime("%a"), "status": i.quality.value, "evaluable_by_strategies": bool(i.usable),
                "reasons": list(i.reasons), "flags": list(i.flags), "closing_auction_regime": bool(i.cas_regime),
                "n_1m_rows": int(i.n_1m_rows), "n_5m_candles": int(i.n_5m_candles),
                "official_close": i.official_close, "official_close_source": i.close_source, "close_1530_print": i.stub_close,
                "max_1m_range_regular_hours": round(float(rng.max()), 2) if len(rng) else None,
                "zero_range_minutes_regular_hours": int((rng == 0).sum()) if len(rng) else None,
                "previous_session": str(pre.date) if pre else None,
                "previous_session_verified": (not pre.gap_to_this_session_unverified) if pre else None,
            }
            if day in REVIEWED_EVENTS:
                e["reviewed_event"] = REVIEWED_EVENTS[day]
            if dly is not None and day in dly.index:
                e["vendor_daily"] = {k: float(dly.loc[day, k]) for k in ("open", "high", "low", "close")}
            sessions.append(e)
        elif day.weekday() < 5:
            if cal.is_confirmed_holiday(day):
                h = cal.holidays[day]
                non_trading.append({"date": str(day), "kind": "HOLIDAY", "name": h.name, "evidence_tier": h.evidence_tier, "evidence": list(h.evidence),
                                    "absent_from_vendor_1m": True, "absent_from_vendor_daily": bool(dly is None or day not in dly.index)})
            else:  # a weekday with no data that the calendar cannot explain
                sessions.append({"date": str(day), "weekday": day.strftime("%a"), "status": "MISSING", "evaluable_by_strategies": False,
                                 "reasons": ["WEEKDAY_WITHOUT_DATA_NOT_A_CONFIRMED_HOLIDAY"], "flags": []})
        day += timedelta(days=1)
    counts: dict[str, int] = {}
    for s in sessions:
        counts[s["status"]] = counts.get(s["status"], 0) + 1
    return {
        "schema": "session_quality_manifest/1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "analysis_window": [str(WINDOW[0]), str(WINDOW[1])],
        "status_vocabulary": ["VALID", "VALID_SPECIAL_SESSION", "PARTIAL", "CORRUPT", "MISSING", "UNVERIFIED"],
        "policy": ("Strategy engines evaluate only sessions with evaluable_by_strategies=true. Every other session with data is reported "
                   "NOT_EVALUATED by strategies.runner.evaluate_dataset. Statuses are produced by nifty_trading.data.sessions.classify_session."),
        "inputs": {"stored_1m_rows": int(len(df)), "warmup_1m_rows": int(len(warm)) if warm is not None else 0, "daily_rows": int(len(daily)) if daily is not None else 0,
                   "calendar": "data/metadata/nse_calendar_2025_2026.json" if cal.source not in ("NONE", "MISSING_FILE") else cal.source,
                   "daily_sha256": sha(ROOT / "data/processed/nifty50_daily/candles.parquet")},
        "counts": {"sessions_in_manifest": len(sessions), "by_status": counts, "evaluable": sum(1 for s in sessions if s["evaluable_by_strategies"]),
                   "non_trading_weekdays_confirmed_holidays": len(non_trading), "closing_auction_regime_sessions": sum(1 for s in sessions if s.get("closing_auction_regime"))},
        "sessions": sessions, "non_trading_days": non_trading,
    }


def main() -> None:
    m = build()
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=1, ensure_ascii=False))
    tmp.replace(MANIFEST)
    print(json.dumps(m["counts"]))


if __name__ == "__main__":
    main()
