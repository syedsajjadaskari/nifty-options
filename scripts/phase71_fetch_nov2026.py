"""Phase 7.1: read-only retrieval of the missing November-2026 NIFTY 50 candles (rulebook example dates 3, 6, 11, 12, 16 Nov) from the project's authenticated 5paisa client into a NEW raw namespace
``data/raw/phase71_5paisa_nov2026/`` (provider response saved unmodified, one file per request, plus a manifest with request parameters, UTC time, row counts and SHA-256).
Never touches the frozen stores (data/processed, data/phase4, data/raw/phase4_*). Order methods are disabled in BrokerClient. Credentials are never printed or stored in the manifest."""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
RAW = ROOT / "data" / "raw" / "phase71_5paisa_nov2026"
INSTRUMENT = ROOT / "data" / "metadata" / "nifty50_instrument.json"
JOBS = [("1m", date(2026, 11, 2), date(2026, 11, 18)), ("1d", date(2026, 10, 1), date(2026, 11, 18))]


def main() -> int:
    from nifty_trading.broker.client import BrokerClient

    RAW.mkdir(parents=True, exist_ok=True)
    mp = RAW / "manifest.json"
    manifest = json.loads(mp.read_text()) if mp.exists() else {"provider": "5paisa", "purpose": "Phase 7.1 missing November 2026 sessions", "requests": {}}
    inst = json.loads(INSTRUMENT.read_text())
    broker = BrokerClient()
    for tf, d0, d1 in JOBS:
        key = f"{tf}_{d0}_{d1}"
        rec = {"timeframe": tf, "from": str(d0), "to": str(d1), "scrip_code": inst["scrip_code"], "exchange": inst["exchange"], "exchange_segment": inst["exchange_segment"], "requested_utc": datetime.now(timezone.utc).isoformat()}
        try:
            df = broker.fetch_historical_candles(inst["exchange"], inst["exchange_segment"], inst["scrip_code"], tf, str(d0), str(d1))
            rec["status"] = "EMPTY" if df is None or len(df) == 0 else "COMPLETED"
            rec["error"] = None
        except Exception as e:  # noqa: BLE001
            rec["status"], rec["error"], df = "FAILED", f"{type(e).__name__}: {str(e)[:300]}", None
        if rec["status"] == "COMPLETED":
            p = RAW / f"{key}.csv"
            df.to_csv(p, index=False)
            c0 = df.columns[0]
            rec.update({"file": p.name, "rows": int(len(df)), "columns": list(df.columns), "first_timestamp": str(df[c0].iloc[0]), "last_timestamp": str(df[c0].iloc[-1]),
                        "distinct_dates": int(df[c0].astype(str).str[:10].nunique()), "sha256": hashlib.sha256(p.read_bytes()).hexdigest()})
        manifest["requests"][key] = rec
        mp.write_text(json.dumps(manifest, indent=1, sort_keys=True))
        print(key, rec["status"], rec.get("rows", 0), rec.get("error") or "", flush=True)
        time.sleep(1.0)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
