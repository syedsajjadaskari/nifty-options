"""Phase 2.1: READ-ONLY re-download of historical NIFTY 50 candles for comparison with the stored data.

* Uses the existing 5paisa integration (login + ``historical_data`` only; order methods are disabled in BrokerClient).
* Saves every response UNCHANGED (as returned, before any cleaning) under ``data/raw/redownload_<utc>/``,
  with a metadata file holding the exact request, row counts and a SHA-256 of the saved file.
* Never writes to ``data/processed`` and never replaces anything: comparison and any repair are separate, explicit steps.

Usage: python scripts/phase21_redownload.py LABEL TIMEFRAME FROM TO [LABEL TIMEFRAME FROM TO ...]
e.g.   python scripts/phase21_redownload.py aug_1m 1m 2026-08-01 2026-08-31
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.broker.client import BrokerClient  # noqa: E402

META = json.loads((ROOT / "data" / "metadata" / "nifty50_instrument.json").read_text())


def main(argv: list[str]) -> int:
    if len(argv) < 4 or len(argv) % 4:
        print(__doc__)
        return 2
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    out = ROOT / "data" / "raw" / f"redownload_{stamp}"
    out.mkdir(parents=True, exist_ok=False)
    client = BrokerClient()
    summary = []
    for i in range(0, len(argv), 4):
        label, tf, d0, d1 = argv[i:i + 4]
        req = {"exch": META["exchange"], "exchange_segment": META["exchange_segment"], "scrip_code": META["scrip_code"],
               "timeframe": tf, "from_date": d0, "to_date": d1}
        entry = {"label": label, "request": req, "requested_at_utc": datetime.now(timezone.utc).isoformat()}
        try:
            df = client.fetch_historical_candles(**req)
            path = out / f"{label}.parquet"
            df.to_parquet(path, compression="zstd")
            entry.update(status="OK", rows=int(len(df)), columns=[str(c) for c in df.columns], file=path.name,
                         sha256=hashlib.sha256(path.read_bytes()).hexdigest())
        except Exception as e:  # report the failure class, never any credential material
            entry.update(status="FAILED", error=f"{type(e).__name__}: {str(e)[:300]}")
        summary.append(entry)
        print(json.dumps({k: entry.get(k) for k in ("label", "status", "rows", "error")}))
    (out / "request_log.json").write_text(json.dumps(summary, indent=2))
    print("saved to", out.relative_to(ROOT))
    return 0 if all(e["status"] == "OK" for e in summary) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
