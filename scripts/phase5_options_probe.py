"""Phase 5: investigate whether HISTORICAL one-minute option premiums for BANKNIFTY and SENSEX are obtainable from the broker (read-only), without inventing anything.

What it checks (all evidence is saved; no premium is ever estimated):
  1. The contracts in the broker's CURRENT instrument master (copy saved by phase5_discover.py): type, strikes, expiries, lot size, and whether any EXPIRED contract is listed (the master carries only live contracts).
  2. For a few live contracts (nearest expiries, strikes around the last index close, CE and PE): does the historical-candle API return one-minute premium bars; the columns returned (bid/ask/open interest?); volume;
     how far back the data go for a contract that was listed months ago.
  3. Whether the master of an earlier date (the Phase 1 copy of 2026-11-01) lists contracts that are no longer in today's master (= contracts that expired in between) and whether the API still serves them.
Output: reports/phase5/options_feasibility/option_probe_results.json and the raw responses under data/raw/<index>/5paisa/options_probe/.
Usage:  python scripts/phase5_options_probe.py
"""

from __future__ import annotations

import hashlib
import json
import sys
import time
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

MASTER_DIR = ROOT / "data" / "raw" / "phase5_instrument_master"
OLD_MASTER = ROOT / "data" / "metadata" / "scrip_master.csv"  # Phase 1 copy (2026-11-01), read only
OUT = ROOT / "reports" / "phase5" / "options_feasibility"
IDX = {"BANKNIFTY": {"exch": "N", "key": "banknifty"}, "SENSEX": {"exch": "B", "key": "sensex"}}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def summarize_master(df: pd.DataFrame, name: str, exch: str) -> dict:
    d = df[(df["Exch"] == exch) & (df["ExchType"] == "D") & (df["SymbolRoot"].astype(str).str.upper() == name)]
    o = d[d["ScripType"].isin(["CE", "PE"])]
    ex = sorted(o["Expiry"].dropna().unique())
    return {"rows": int(len(d)), "by_type": {k: int(v) for k, v in d["ScripType"].value_counts().items()}, "option_expiries_listed": ex, "n_option_expiries": len(ex), "lot_sizes_listed": sorted(int(x) for x in o["LotSize"].unique()),
            "lot_size_by_expiry": {e: sorted(int(x) for x in o[o["Expiry"] == e]["LotSize"].unique()) for e in ex}, "strike_min": float(o["StrikeRate"].min()), "strike_max": float(o["StrikeRate"].max()),
            "earliest_expiry_listed": ex[0] if ex else None, "contains_expired_contracts": bool(ex and ex[0] < str(date.today()))}


def pick(df: pd.DataFrame, name: str, exch: str, spot: float, n_expiries: int = 2) -> list[dict]:
    d = df[(df["Exch"] == exch) & (df["ExchType"] == "D") & (df["SymbolRoot"].astype(str).str.upper() == name) & df["ScripType"].isin(["CE", "PE"])]
    ex = sorted(d["Expiry"].dropna().unique())
    ex = [e for e in ex if e >= str(date.today())][:n_expiries]
    out = []
    for e in ex:
        de = d[d["Expiry"] == e]
        strikes = sorted(de["StrikeRate"].unique())
        atm = min(strikes, key=lambda s: abs(s - spot))
        i = strikes.index(atm)
        for s in {strikes[max(i - 2, 0)], atm, strikes[min(i + 2, len(strikes) - 1)]}:
            for t in ("CE", "PE"):
                r = de[(de["StrikeRate"] == s) & (de["ScripType"] == t)]
                if len(r):
                    out.append({"scrip_code": int(r.iloc[0]["ScripCode"]), "name": str(r.iloc[0]["Name"]), "expiry": e, "strike": float(s), "type": t, "lot_size": int(r.iloc[0]["LotSize"]), "tick": float(r.iloc[0]["TickSize"]),
                                "atm_distance_points": float(s - atm)})
    return out


def main() -> int:
    from nifty_trading.broker.client import BrokerClient
    new_path = sorted(MASTER_DIR.glob("scrip_master_*.csv"))[-1]
    new, old = pd.read_csv(new_path, low_memory=False), pd.read_csv(OLD_MASTER, low_memory=False)
    OUT.mkdir(parents=True, exist_ok=True)
    broker = BrokerClient()
    res: dict = {"retrieved_utc": datetime.now(timezone.utc).isoformat(), "master_new": {"file": str(new_path.relative_to(ROOT)), "sha256": sha(new_path)}, "master_old": {"file": str(OLD_MASTER.relative_to(ROOT)), "sha256": sha(OLD_MASTER)}, "indices": {}}
    for name, c in IDX.items():
        spot_df = pd.read_csv(sorted((ROOT / "data" / "raw" / c["key"] / "5paisa" / "1d").glob("1d_*.csv"))[-1])
        spot = float(spot_df["Close"].iloc[-1])
        info = {"last_daily_close_used_to_pick_strikes": spot, "last_daily_date": str(spot_df["Datetime"].iloc[-1]), "master_new": summarize_master(new, name, c["exch"]), "master_old": summarize_master(old, name, c["exch"]), "probes": []}
        old_codes = set(old[(old["Exch"] == c["exch"]) & (old["ExchType"] == "D") & (old["SymbolRoot"].astype(str).str.upper() == name)]["ScripCode"])
        new_codes = set(new[(new["Exch"] == c["exch"]) & (new["ExchType"] == "D") & (new["SymbolRoot"].astype(str).str.upper() == name)]["ScripCode"])
        info["contracts_in_old_master_not_in_new"] = len(old_codes - new_codes)
        info["contracts_in_new_master_not_in_old"] = len(new_codes - old_codes)
        raw = ROOT / "data" / "raw" / c["key"] / "5paisa" / "options_probe"
        raw.mkdir(parents=True, exist_ok=True)
        today = date.today()
        contracts = pick(new, name, c["exch"], spot)
        # contracts that left the master between the two copies (expired in between), probed for the days before they expired
        gone = old[(old["Exch"] == c["exch"]) & (old["ExchType"] == "D") & (old["SymbolRoot"].astype(str).str.upper() == name) & old["ScripCode"].isin(old_codes - new_codes) & old["ScripType"].isin(["CE", "PE"])]
        for _, r in gone.sample(min(len(gone), 4), random_state=1).iterrows() if len(gone) else []:
            contracts.append({"scrip_code": int(r["ScripCode"]), "name": str(r["Name"]), "expiry": str(r["Expiry"]), "strike": float(r["StrikeRate"]), "type": str(r["ScripType"]), "lot_size": int(r["LotSize"]), "tick": float(r["TickSize"]),
                              "status": "LEFT_THE_MASTER_BETWEEN_2026-11-01_AND_TODAY"})
        for k in contracts:
            for label, d0, d1 in (("recent_10d", today - timedelta(days=10), today), ("six_months", today - timedelta(days=180), today)):
                rec = {**k, "label": label, "from": str(d0), "to": str(d1)}
                try:
                    df = broker.fetch_historical_candles(c["exch"], "D", k["scrip_code"], "1m", str(d0), str(d1))
                    if df is None or len(df) == 0:
                        rec.update(status="EMPTY", rows=0)
                    else:
                        p = raw / f"{k['scrip_code']}_{label}.csv"
                        df.to_csv(p, index=False)
                        ts = pd.to_datetime(df.iloc[:, 0].astype(str), errors="coerce")
                        rec.update(status="COMPLETED", rows=int(len(df)), columns=list(df.columns), first_timestamp=str(df.iloc[0, 0]), last_timestamp=str(df.iloc[-1, 0]), distinct_dates=int(ts.dt.date.nunique()),
                                   volume_nonzero_rows=int((df["Volume"] > 0).sum()) if "Volume" in df else None, bars_per_date_max=int(ts.dt.date.value_counts().max()), file=str(p.relative_to(ROOT)), sha256=sha(p),
                                   zero_range_bar_share=round(float((df["High"] == df["Low"]).mean()), 4) if {"High", "Low"} <= set(df.columns) else None)
                except Exception as e:  # noqa: BLE001 - classified, no credentials
                    rec.update(status="ERROR", error=f"{type(e).__name__}: {str(e)[:200]}")
                info["probes"].append(rec)
                print(name, k["scrip_code"], k["type"], k["expiry"], k["strike"], label, rec["status"], rec.get("rows", ""), rec.get("first_timestamp", ""), flush=True)
                time.sleep(1.0)
        res["indices"][name] = info
    (OUT / "option_probe_results.json").write_text(json.dumps(res, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
