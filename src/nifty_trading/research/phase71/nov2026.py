"""November-2026 data store (Phase 7.1): processes the NEW raw 5paisa retrieval into a separate versioned location and reconstructs the rulebook examples.
Raw: data/raw/phase71_5paisa_nov2026/ (never edited). Processed: data/phase71/processed/FIVEPAISA_1M_NOV2026/ (parquet + quality report). The frozen stores are untouched."""

from __future__ import annotations

import hashlib
import json
from datetime import date, time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[4]
RAW = ROOT / "data" / "raw" / "phase71_5paisa_nov2026"
PROC = ROOT / "data" / "phase71" / "processed" / "FIVEPAISA_1M_NOV2026"
OPEN, CLOSE = time(9, 15), time(15, 30)


def load_raw() -> pd.DataFrame:
    d = pd.read_csv(RAW / "1m_2026-11-02_2026-11-18.csv")
    d = d.rename(columns={"Datetime": "ts_raw", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    d["ts"] = pd.to_datetime(d["ts_raw"])
    d["_d"] = d["ts"].dt.date
    return d


def quality(d: pd.DataFrame) -> pd.DataFrame:
    """Per-session quality: rows inside 09:15-15:29, missing minutes, rows outside the session, duplicate / non-monotonic stamps, OHLC sanity, stale (flat) runs."""
    rows = []
    for day, g in d.groupby("_d"):
        t = g["ts"].dt.time
        inside = g[(t >= OPEN) & (t < CLOSE)]
        full = pd.date_range(pd.Timestamp(day) + pd.Timedelta(hours=9, minutes=15), pd.Timestamp(day) + pd.Timedelta(hours=15, minutes=29), freq="min")
        missing = sorted(set(full) - set(inside["ts"]))
        bad = int(((inside["high"] < inside[["open", "close"]].max(axis=1)) | (inside["low"] > inside[["open", "close"]].min(axis=1)) | (inside["high"] < inside["low"])).sum())
        flat = int(((inside["open"] == inside["high"]) & (inside["high"] == inside["low"]) & (inside["low"] == inside["close"])).sum())
        rows.append({"date": str(day), "weekday": pd.Timestamp(day).strftime("%a"), "rows_total": len(g), "rows_in_session_0915_1529": len(inside), "rows_outside_session": len(g) - len(inside), "missing_minutes": len(missing),
                     "missing_first": str(missing[0]) if missing else "", "duplicate_stamps": int(g["ts"].duplicated().sum()), "monotonic": bool(g["ts"].is_monotonic_increasing), "ohlc_violations": bad, "flat_rows": flat,
                     "complete_session": len(inside) == 375 and not missing, "note": "weekend / special session (Muhurat-type partial)" if pd.Timestamp(day).weekday() >= 5 else ""})
    return pd.DataFrame(rows)


def build() -> dict:
    d = load_raw()
    q = quality(d)
    PROC.mkdir(parents=True, exist_ok=True)
    keep = d[(d["ts"].dt.time >= OPEN) & (d["ts"].dt.time < CLOSE)][["ts", "open", "high", "low", "close", "volume"]].copy()
    keep["timestamp"] = keep["ts"].dt.tz_localize("Asia/Kolkata")
    keep.drop(columns="ts").to_parquet(PROC / "candles.parquet", index=False)
    q.to_csv(PROC / "quality_report.csv", index=False)
    info = {"source": "data/raw/phase71_5paisa_nov2026/1m_2026-11-02_2026-11-18.csv", "raw_sha256": hashlib.sha256((RAW / "1m_2026-11-02_2026-11-18.csv").read_bytes()).hexdigest(), "provider": "5paisa (project BrokerClient, read-only)",
            "timezone": "exchange stamps are naive IST in the provider response; localised to Asia/Kolkata here", "rows_raw": len(d), "rows_in_session": len(keep), "sessions": q["date"].tolist(),
            "rows_outside_session_dropped": int(len(d) - len(keep)), "processed": "data/phase71/processed/FIVEPAISA_1M_NOV2026/candles.parquet"}
    (PROC / "manifest.json").write_text(json.dumps(info, indent=1))
    return info


def session_frames(days: list[date]) -> dict:
    d = load_raw()
    return {x: d[d["_d"] == x].copy() for x in days}
