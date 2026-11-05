"""Phase 4: resumable, read-only retrieval of NIFTY 50 historical candles from the 5paisa API into a SEPARATE raw namespace.

Writes only under data/raw/phase4_5paisa/ (provider responses saved unmodified, one file per request) and its manifest.json (request parameters, UTC retrieval time, row counts, first/last timestamp, SHA-256, a
classified status). It never touches data/processed/ or the Phase 1/2 download manifest. It uses the project's BrokerClient (read-only endpoints; order methods are disabled in that class) and never prints credentials.

Statuses: COMPLETED | EMPTY (the API answered with no rows) | RATE_LIMITED | ACCESS_DENIED | FAILED. Completed requests are skipped on re-run (resumable); EMPTY / failed ones are retried only with --retry-empty / --retry-failed.

Usage:
  python scripts/phase4_fetch_5paisa.py --probe-empty            # one request per month for the periods the API is believed not to cover (documents the gap)
  python scripts/phase4_fetch_5paisa.py --daily                  # daily candles 2017-01-01 .. 2025-08-31 (official closes, daily moving averages, trading-day reference)
  python scripts/phase4_fetch_5paisa.py --minutes                # 1-minute candles for the Phase 4 windows (+ one month of warm-up)
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

RAW = ROOT / "data" / "raw" / "phase4_5paisa"
MANIFEST = RAW / "manifest.json"
INSTRUMENT = ROOT / "data" / "metadata" / "nifty50_instrument.json"  # the project's verified NIFTY 50 index mapping

# month ranges requested as 1-minute data: (first month, last month) inclusive. Window B warm-up month 2022-08; Window D (5paisa part) from the first covered month 2019-03.
MINUTE_MONTHS = [((2019, 3), (2019, 12)), ((2022, 8), (2025, 8))]
PROBE_EMPTY_MONTHS = ((2018, 1), (2019, 2))
DAILY_RANGE = (date(2017, 1, 1), date(2025, 8, 31))


def months(a: tuple[int, int], b: tuple[int, int]):
    y, m = a
    while (y, m) <= b:
        yield y, m
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def classify_error(msg: str) -> str:
    low = msg.lower()
    if "429" in low or "rate" in low or "too many" in low or "throttl" in low:
        return "RATE_LIMITED"
    if "unauthor" in low or "forbidden" in low or "denied" in low or "401" in low or "403" in low or "token" in low or "session" in low:
        return "ACCESS_DENIED"
    return "FAILED"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {"provider": "5paisa", "instrument_file": "data/metadata/nifty50_instrument.json", "documentation": "https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles", "requests": {}}


def save_manifest(m: dict) -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    tmp = MANIFEST.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(m, indent=1, sort_keys=True))
    tmp.replace(MANIFEST)


def fetch(broker, inst: dict, manifest: dict, tf: str, d0: date, d1: date, retry_empty: bool, retry_failed: bool, attempts: int = 3) -> str:
    key = f"{tf}_{d0}_{d1}"
    prev = manifest["requests"].get(key)
    if prev:
        if prev["status"] == "COMPLETED" and (RAW / prev["file"]).exists():
            return "SKIP_COMPLETED"
        if prev["status"] == "EMPTY" and not retry_empty:
            return "SKIP_EMPTY"
        if prev["status"] in ("FAILED", "RATE_LIMITED", "ACCESS_DENIED") and not retry_failed:
            return "SKIP_FAILED"
    rec = {"timeframe": tf, "from": str(d0), "to": str(d1), "scrip_code": inst["scrip_code"], "exchange": inst["exchange"], "exchange_segment": inst["exchange_segment"]}
    status, err, df = "FAILED", None, None
    for k in range(attempts):
        rec["attempts"] = k + 1
        rec["requested_utc"] = datetime.now(timezone.utc).isoformat()
        try:
            df = broker.fetch_historical_candles(inst["exchange"], inst["exchange_segment"], inst["scrip_code"], tf, str(d0), str(d1))
            status, err = ("EMPTY" if df is None or len(df) == 0 else "COMPLETED"), None
            break
        except Exception as e:  # noqa: BLE001 - classified below, never includes credentials
            err = f"{type(e).__name__}: {str(e)[:300]}"
            status = classify_error(err)
            if status == "ACCESS_DENIED":
                break
            time.sleep(5 * (k + 1) * (3 if status == "RATE_LIMITED" else 1))
    rec["status"], rec["error"] = status, err
    if status == "COMPLETED":
        sub = RAW / tf
        sub.mkdir(parents=True, exist_ok=True)
        path = sub / f"{key}.csv"
        df.to_csv(path, index=False)  # the provider's DataFrame exactly as returned (column names, string timestamps, float noise)
        c0 = df.columns[0]
        rec.update({"file": str(path.relative_to(RAW)), "rows": int(len(df)), "columns": list(df.columns), "first_timestamp": str(df[c0].iloc[0]), "last_timestamp": str(df[c0].iloc[-1]),
                    "distinct_dates": int(df[c0].astype(str).str[:10].nunique()), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest["requests"][key] = rec
    save_manifest(manifest)
    return status


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--probe-empty", action="store_true", help="one request per month 2018-01..2019-02 to document the uncovered period")
    ap.add_argument("--daily", action="store_true", help="daily candles in <=6-month spans")
    ap.add_argument("--minutes", action="store_true", help="monthly 1-minute requests for the Phase 4 windows")
    ap.add_argument("--retry-empty", action="store_true")
    ap.add_argument("--retry-failed", action="store_true")
    ap.add_argument("--pause", type=float, default=1.0, help="seconds between requests (in addition to the client's rate limiter)")
    a = ap.parse_args()
    from nifty_trading.broker.client import (
        BrokerClient,  # imported late: authentication happens on the first request
    )
    broker = BrokerClient()
    inst = json.loads(INSTRUMENT.read_text())
    manifest = load_manifest()
    jobs: list[tuple[str, date, date]] = []
    if a.probe_empty:
        jobs += [("1m", date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])) for y, m in months(*PROBE_EMPTY_MONTHS)]
    if a.daily:
        s = DAILY_RANGE[0]
        while s <= DAILY_RANGE[1]:
            e_m = s.month + 5
            e_y = s.year + (e_m - 1) // 12
            e_m = (e_m - 1) % 12 + 1
            e = min(date(e_y, e_m, calendar.monthrange(e_y, e_m)[1]), DAILY_RANGE[1])
            jobs.append(("1d", s, e))
            s = date(e.year + (e.month == 12), 1 if e.month == 12 else e.month + 1, 1)
    if a.minutes:
        for lo, hi in MINUTE_MONTHS:
            jobs += [("1m", date(y, m, 1), date(y, m, calendar.monthrange(y, m)[1])) for y, m in months(lo, hi)]
    counts: dict[str, int] = {}
    for tf, d0, d1 in jobs:
        st = fetch(broker, inst, manifest, tf, d0, d1, a.retry_empty, a.retry_failed)
        counts[st] = counts.get(st, 0) + 1
        r = manifest["requests"].get(f"{tf}_{d0}_{d1}", {})
        print(f"{tf} {d0}..{d1}: {st} rows={r.get('rows', 0)} {r.get('error') or ''}", flush=True)
        if st in ("COMPLETED", "EMPTY", "FAILED", "RATE_LIMITED"):
            time.sleep(a.pause)
        if st == "ACCESS_DENIED":
            print("ACCESS DENIED: stopping (never retried automatically)", file=sys.stderr)
            return 3
    print(json.dumps(counts))
    return 0 if not any(k in counts for k in ("FAILED", "RATE_LIMITED")) else 1


if __name__ == "__main__":
    raise SystemExit(main())
