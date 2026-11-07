"""Phase 5: discover and VERIFY the BANKNIFTY and SENSEX index instruments in the 5paisa instrument master, then probe the historical-candle API with small requests.

Read-only. Writes only new files:
  data/raw/phase5_instrument_master/scrip_master_<UTC>.csv (+ .sha256)      a fresh copy of the broker's public instrument master (the Phase 1 copy is not touched)
  data/metadata/phase5/<index>_instrument.json                              the resolved mapping, with the master file hash and the verification evidence
  data/raw/<index>/5paisa/probe/*.csv                                       provider responses of the probe requests, saved unmodified
  reports/phase5/<index>/probe_results.json                                 what each probe returned (rows, first / last timestamp, dates, price range)
It uses the project's BrokerClient (read-only endpoints; order methods are disabled in that class) and never prints credentials. Nothing is assumed from the NIFTY 50 settings.

Usage:  python scripts/phase5_discover.py [--no-download-master] [--skip-probe]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

DOC = "https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles"
MASTER_DIR = ROOT / "data" / "raw" / "phase5_instrument_master"
META_DIR = ROOT / "data" / "metadata" / "phase5"
# what the master must show for each index (checked, not assumed): the exchange and the CASH / index segment, and the ScripCode found BY NAME, never copied from NIFTY
SPECS = {
    "banknifty": {"exchange": "N", "name": "BANKNIFTY", "expected_index_name": "Nifty Bank", "exchange_label": "NSE", "level_range": (20000, 80000)},
    "sensex": {"exchange": "B", "name": "SENSEX", "expected_index_name": "S&P BSE Sensex", "exchange_label": "BSE", "level_range": (40000, 120000)},
}
# 1-minute probes: (label, from, to). One week at several eras, to see where coverage starts; plus every interval over a recent week.
MINUTE_PROBES = [("recent_week", date(2026, 8, 24), date(2026, 8, 28)), ("window_a_start", date(2025, 9, 1), date(2025, 9, 5)), ("main_start", date(2022, 9, 1), date(2022, 9, 7)),
                 ("pre_main_2022_01", date(2022, 1, 3), date(2022, 1, 7)), ("2021_12", date(2021, 12, 1), date(2021, 12, 7)), ("2019_06", date(2019, 6, 3), date(2019, 6, 7)),
                 ("2019_03", date(2019, 3, 1), date(2019, 3, 8)), ("2019_01", date(2019, 1, 1), date(2019, 1, 31)), ("2018_06", date(2018, 6, 4), date(2018, 6, 8)),
                 ("2018_01", date(2018, 1, 1), date(2018, 1, 31)), ("2017", date(2017, 6, 1), date(2017, 6, 30))]
INTERVALS = ["1m", "5m", "10m", "15m", "30m", "60m", "1d"]
INTERVAL_WEEK = (date(2026, 8, 24), date(2026, 8, 28))
DAILY_PROBES = [("daily_2018", date(2018, 1, 1), date(2018, 12, 31)), ("daily_2019", date(2019, 1, 1), date(2019, 12, 31)), ("daily_2017", date(2017, 1, 1), date(2017, 6, 30)), ("daily_2022_09", date(2022, 8, 1), date(2022, 9, 30))]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def download_master() -> Path:
    import requests

    from nifty_trading.config.constants import FIVEPAISA_SCRIP_MASTER_URL
    MASTER_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = MASTER_DIR / f"scrip_master_{stamp}.csv"
    r = requests.get(FIVEPAISA_SCRIP_MASTER_URL, timeout=120)
    r.raise_for_status()
    path.write_bytes(r.content)
    (MASTER_DIR / f"scrip_master_{stamp}.sha256").write_text(f"{sha256(path)}  {path.name}\n  source: {FIVEPAISA_SCRIP_MASTER_URL}\n  retrieved_utc: {stamp}\n")
    return path


def latest_master() -> Path:
    files = sorted(MASTER_DIR.glob("scrip_master_*.csv"))
    if not files:
        raise SystemExit("no Phase 5 instrument master copy: run without --no-download-master")
    return files[-1]


def resolve(master_path: Path) -> dict[str, dict]:
    df = pd.read_csv(master_path, low_memory=False)
    out = {}
    for key, sp in SPECS.items():
        c = df[(df["Exch"] == sp["exchange"]) & (df["ExchType"] == "C") & (df["Name"].astype(str).str.upper() == sp["name"])]
        # an ETF / fund / future / option with a similar name is NOT the index: the index has a 99xxxx scrip code and no ISIN
        idx = c[c["ScripCode"] >= 999000]
        rejected = c[c["ScripCode"] < 999000][["Exch", "ExchType", "ScripCode", "Name", "FullName"]].to_dict("records")
        if len(idx) != 1:
            raise SystemExit(f"{key}: expected exactly one index row in the master, found {len(idx)}")
        r = idx.iloc[0]
        similar = df[(df["Exch"] == sp["exchange"]) & (df["ExchType"] == "C") & (df["ScripCode"] >= 999000) & df["Name"].astype(str).str.upper().str.contains("SENSEX|BANK", regex=True)][["ScripCode", "Name", "FullName"]].to_dict("records")
        out[key] = {"symbol": str(r["Name"]).strip(), "full_name": None if pd.isna(r["FullName"]) else str(r["FullName"]).strip(), "exchange": sp["exchange"], "exchange_label": sp["exchange_label"], "exchange_segment": "C",
                    "scrip_code": int(r["ScripCode"]), "scrip_type": str(r["ScripType"]), "series": str(r["Series"]), "tick_size_master": float(r["TickSize"]), "lot_size_master": int(r["LotSize"]), "is_index": True,
                    "expected_index_name": sp["expected_index_name"], "master_file": str(master_path.relative_to(ROOT)), "master_sha256": sha256(master_path), "not_the_index_rejected_rows_with_same_name": rejected,
                    "similar_index_rows_in_same_segment": similar,
                    "name_note": ("the master gives no full name for this row, so the identity is confirmed by the exchange, the 99xxxx index code and the price level in the probe below" if pd.isna(r["FullName"]) else "")}
    return out


def probe(broker, key: str, inst: dict, lo_hi: tuple[float, float]) -> dict:
    rawdir = ROOT / "data" / "raw" / key / "5paisa" / "probe"
    rawdir.mkdir(parents=True, exist_ok=True)
    results = []

    def one(label: str, tf: str, d0: date, d1: date) -> None:
        rec = {"label": label, "interval": tf, "from": str(d0), "to": str(d1), "requested_utc": datetime.now(timezone.utc).isoformat()}
        try:
            df = broker.fetch_historical_candles(inst["exchange"], inst["exchange_segment"], inst["scrip_code"], tf, str(d0), str(d1))
        except Exception as e:  # noqa: BLE001 - classified, never includes credentials
            rec.update(status="ERROR", error=f"{type(e).__name__}: {str(e)[:300]}")
            results.append(rec)
            return
        if df is None or len(df) == 0:
            rec.update(status="EMPTY", rows=0)
            results.append(rec)
            return
        p = rawdir / f"{label}_{tf}_{d0}_{d1}.csv"
        df.to_csv(p, index=False)
        c0 = df.columns[0]
        ts = pd.to_datetime(df[c0].astype(str), errors="coerce")
        num = [c for c in df.columns if c.lower() in ("open", "high", "low", "close")]
        rec.update(status="COMPLETED", rows=int(len(df)), columns=list(df.columns), file=str(p.relative_to(ROOT)), sha256=sha256(p), first_timestamp=str(df[c0].iloc[0]), last_timestamp=str(df[c0].iloc[-1]),
                   distinct_dates=int(ts.dt.date.nunique()), first_time_of_day=str(ts.dt.time.min()), last_time_of_day=str(ts.dt.time.max()), rows_per_date_min_max=[int(ts.dt.date.value_counts().min()), int(ts.dt.date.value_counts().max())],
                   close_min=float(df[[c for c in num if c.lower() == "close"][0]].min()) if num else None, close_max=float(df[[c for c in num if c.lower() == "close"][0]].max()) if num else None)
        cmin, cmax = rec["close_min"], rec["close_max"]
        rec["price_level_in_expected_range"] = bool(cmin is not None and cmin >= lo_hi[0] * (0.5 if "2018" in label or "2017" in label or "2019" in label else 1) and cmax <= lo_hi[1])
        results.append(rec)

    for label, d0, d1 in MINUTE_PROBES:
        one(label, "1m", d0, d1)
        time.sleep(1.0)
    for tf in INTERVALS:
        if tf != "1m":
            one("interval_check", tf, *INTERVAL_WEEK)
            time.sleep(1.0)
    for label, d0, d1 in DAILY_PROBES:
        one(label, "1d", d0, d1)
        time.sleep(1.0)
    return {"documentation": DOC, "instrument": inst, "probes": results}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--no-download-master", action="store_true", help="reuse the newest Phase 5 master copy instead of downloading a fresh one")
    ap.add_argument("--skip-probe", action="store_true", help="only resolve the instruments")
    a = ap.parse_args()
    master = latest_master() if a.no_download_master else download_master()
    print("instrument master:", master.relative_to(ROOT), sha256(master)[:16])
    insts = resolve(master)
    META_DIR.mkdir(parents=True, exist_ok=True)
    for k, v in insts.items():
        (META_DIR / f"{k}_instrument.json").write_text(json.dumps(v, indent=1))
        print(f"{k}: exchange {v['exchange']} segment {v['exchange_segment']} scrip {v['scrip_code']} name {v['symbol']} full_name {v['full_name']}")
    if a.skip_probe:
        return 0
    from nifty_trading.broker.client import BrokerClient
    broker = BrokerClient()
    for k, v in insts.items():
        res = probe(broker, k, v, SPECS[k]["level_range"])
        out = ROOT / "reports" / "phase5" / k
        out.mkdir(parents=True, exist_ok=True)
        (out / "probe_results.json").write_text(json.dumps(res, indent=1, default=str))
        for r in res["probes"]:
            print(f"  {k} {r['label']:>16} {r['interval']:>4} {r['from']}..{r['to']}: {r['status']} rows={r.get('rows', '-')} {r.get('first_timestamp', '')} -> {r.get('last_timestamp', '')} dates={r.get('distinct_dates', '-')} {r.get('error', '')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
