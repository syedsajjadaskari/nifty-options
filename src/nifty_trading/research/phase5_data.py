"""Phase 5 data layer for the BANKNIFTY and SENSEX index backtests.

This module only ADDS index-specific plumbing around the Phase 4 building blocks (``phase4_data``: ``_finish_minutes``, ``derive_calendar``, ``session_quality_table``, ``coverage_table``, ``overlap_audit``,
``build_window_data``), which already take data frames rather than NIFTY paths. Nothing here touches NIFTY data, the frozen strategy files or the Phase 1-4 outputs.

Namespaces (one per index, never shared with NIFTY; vendors are never merged):
  data/raw/<index>/5paisa/{1m,1d}/ + manifest.json        provider responses, unmodified
  data/raw/<index>/secondary_kapri/<commit>/              GitHub repository files, unmodified
  data/processed/<index>/<source id>/{minutes,daily}      Parquet (ZSTD), year=/month= partitions, a source_manifest.json with the SHA-256 of every partition
  data/processed/<index>/calendar_derived.json            the calendar DERIVED from that index's own daily + minute series
"""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from nifty_trading.research import phase4_data as D4

ROOT = D4.ROOT
IST = D4.IST
# 5paisa 1-minute retrieval months: Window D part (the API's first minute bar is 2019-03-01) and the main window plus one warm-up month. Daily candles from 2017 (200-day moving averages for 2018).
MINUTE_MONTHS_5P = [((2019, 3), (2019, 12)), ((2022, 8), (2026, 8))]
DAILY_RANGE = (date(2017, 1, 1), date(2026, 8, 31))


@dataclass(frozen=True)
class IndexSpec:
    key: str  # directory name, lower case
    name: str  # BANKNIFTY | SENSEX
    display: str
    exchange_label: str  # NSE | BSE
    secondary_repo: str
    secondary_file: str
    sec_columns: tuple[str, str]  # (date column, time column) of the secondary file

    @property
    def instrument_file(self) -> Path:
        return ROOT / "data" / "metadata" / "phase5" / f"{self.key}_instrument.json"

    @property
    def raw_5p(self) -> Path:
        return ROOT / "data" / "raw" / self.key / "5paisa"

    @property
    def raw_sec_root(self) -> Path:
        return ROOT / "data" / "raw" / self.key / "secondary_kapri"

    @property
    def proc(self) -> Path:
        return ROOT / "data" / "processed" / self.key

    @property
    def src_5p_min(self) -> str:
        return f"FIVEPAISA_1M_{self.name}"

    @property
    def src_5p_daily(self) -> str:
        return f"FIVEPAISA_1D_{self.name}"

    @property
    def src_sec_min(self) -> str:
        return f"KAPRI_1M_{self.name}"

    @property
    def calendar_file(self) -> Path:
        return self.proc / "calendar_derived.json"

    def partition_path(self, source_id: str, d: date) -> str:
        return f"data/processed/{self.key}/{source_id}/minutes/year={d.year}/month={d.month:02d}/candles.parquet"


INDEXES = {
    "BANKNIFTY": IndexSpec("banknifty", "BANKNIFTY", "Nifty Bank", "NSE", "sandeepkapri/BankNifty-Data", "bank-nifty-1m-data.csv", ("Date", "Time")),
    "SENSEX": IndexSpec("sensex", "SENSEX", "S&P BSE Sensex", "BSE", "sandeepkapri/Sensex-Minute-Data", "sensex_candlestick_data.csv", ("Date", "Time")),
}


# ------------------------------------------------------------------------------------------------------------------------------ loaders
def load_5p_minutes(ix: IndexSpec) -> tuple[pd.DataFrame, dict]:
    man = json.loads((ix.raw_5p / "manifest.json").read_text())
    frames, files = [], {}
    for _k, r in sorted(man["requests"].items()):
        if r["timeframe"] != "1m" or r["status"] != "COMPLETED":
            continue
        p = ix.raw_5p / r["file"]
        assert D4.sha256_file(p) == r["sha256"], f"raw file changed since retrieval: {p}"
        x = pd.read_csv(p)
        x["raw_file"] = r["file"]
        frames.append(x)
        files[r["file"]] = r["sha256"]
    raw = pd.concat(frames, ignore_index=True)
    chron = bool(pd.to_datetime(raw["Datetime"]).is_monotonic_increasing)
    df = pd.DataFrame({"timestamp": pd.to_datetime(raw["Datetime"]).dt.tz_localize(IST), "open": raw["Open"].astype(float), "high": raw["High"].astype(float), "low": raw["Low"].astype(float),
                       "close": raw["Close"].astype(float), "volume": raw["Volume"].fillna(0).astype("int64"), "raw_file": raw["raw_file"]})
    out, info = D4._finish_minutes(df.drop(columns="raw_file"))
    rf = df.drop_duplicates("timestamp", keep="last").set_index("timestamp")["raw_file"]
    out["raw_file"] = out["timestamp"].map(rf)
    info.update({"source_id": ix.src_5p_min, "raw_files": files, "chronological_input": chron, "instrument": man["instrument"]})
    return out, info


def load_5p_daily(ix: IndexSpec) -> tuple[pd.DataFrame, dict]:
    man = json.loads((ix.raw_5p / "manifest.json").read_text())
    frames, files = [], {}
    for _k, r in sorted(man["requests"].items()):
        if r["timeframe"] != "1d" or r["status"] != "COMPLETED":
            continue
        p = ix.raw_5p / r["file"]
        assert D4.sha256_file(p) == r["sha256"], f"raw file changed since retrieval: {p}"
        frames.append(pd.read_csv(p))
        files[r["file"]] = r["sha256"]
    raw = pd.concat(frames, ignore_index=True)
    df = pd.DataFrame({"date": pd.to_datetime(raw["Datetime"]).dt.date, "open": raw["Open"].astype(float).round(2), "high": raw["High"].astype(float).round(2), "low": raw["Low"].astype(float).round(2),
                       "close": raw["Close"].astype(float).round(2)})
    n0 = len(df)
    df = df.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    return df, {"source_id": ix.src_5p_daily, "raw_files": files, "rows": int(len(df)), "duplicates_removed": n0 - len(df), "first": str(df["date"].min()), "last": str(df["date"].max())}


def secondary_dir(ix: IndexSpec) -> Path:
    dirs = sorted(p for p in ix.raw_sec_root.iterdir() if p.is_dir())
    assert len(dirs) == 1, f"expected exactly one pinned secondary-source commit directory, found {[d.name for d in dirs]}"
    return dirs[0]


def load_secondary_minutes(ix: IndexSpec, timestamp_shift_minutes: int = 0) -> tuple[pd.DataFrame, dict]:
    """The repository's Date (DD-MM-YYYY) and Time columns, localised to IST. ``timestamp_shift_minutes`` is 0 unless an overlap test against 5paisa proves a different label convention (recorded in the info)."""
    d = secondary_dir(ix)
    man = json.loads((d / "manifest.json").read_text())
    f = man["files"][ix.secondary_file]
    assert f["status"] == "OK"
    p = d / ix.secondary_file
    assert D4.sha256_file(p) == f["sha256"], f"raw file changed since retrieval: {p}"
    raw = pd.read_csv(p)
    dc, tc = ix.sec_columns
    ts = pd.to_datetime(raw[dc].astype(str) + " " + raw[tc].astype(str), format="%d-%m-%Y %H:%M:%S")
    if timestamp_shift_minutes:
        ts = ts + pd.Timedelta(minutes=timestamp_shift_minutes)
    df = pd.DataFrame({"timestamp": ts.dt.tz_localize(IST), "open": raw["Open"].astype(float), "high": raw["High"].astype(float), "low": raw["Low"].astype(float), "close": raw["Close"].astype(float), "volume": 0})
    chron = bool(ts.is_monotonic_increasing)
    out, info = D4._finish_minutes(df)
    out["raw_file"] = ix.secondary_file  # every partition (and so every trade) records the repository file and its SHA-256
    info.update({"source_id": ix.src_sec_min, "raw_files": {ix.secondary_file: f["sha256"]}, "commit_sha": man["commit_sha"], "commit_date": man["commit_date"], "chronological_input": chron,
                 "timestamp_shift_minutes": timestamp_shift_minutes, "repository": man["repository"], "repo_license_spdx": man["repo_license_spdx"]})
    return out, info


# ------------------------------------------------------------------------------------------------------------------------------ processed namespace (Parquet, ZSTD)
def write_processed(ix: IndexSpec, source_id: str, minutes: pd.DataFrame | None, daily: pd.DataFrame | None, info: dict) -> dict:
    base = ix.proc / source_id
    man: dict[str, Any] = {"source_id": source_id, "index": ix.name, "written_utc": datetime.utcnow().isoformat() + "Z", "loader_info": {k: v for k, v in info.items() if k != "raw_files"},
                           "raw_files": info.get("raw_files", {}), "compression": "zstd", "partitions": {}}
    if minutes is not None:
        m = minutes.drop(columns=[c for c in ("raw_file",) if c in minutes.columns])
        for (y, mo), g in m.groupby([m["timestamp"].dt.year, m["timestamp"].dt.month]):
            p = base / "minutes" / f"year={y}" / f"month={mo:02d}" / "candles.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            g.reset_index(drop=True).to_parquet(p, index=False, compression="zstd")
            rfs = sorted(set(minutes.loc[g.index, "raw_file"])) if "raw_file" in minutes.columns else []
            man["partitions"][str(p.relative_to(ROOT))] = {"sha256": D4.sha256_file(p), "rows": int(len(g)), "first": str(g["timestamp"].iloc[0]), "last": str(g["timestamp"].iloc[-1]), "raw_files": rfs}
    if daily is not None:
        p = base / "daily" / "candles.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        daily.to_parquet(p, index=False, compression="zstd")
        man["partitions"][str(p.relative_to(ROOT))] = {"sha256": D4.sha256_file(p), "rows": int(len(daily)), "first": str(daily["date"].min()), "last": str(daily["date"].max())}
    (base / "source_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True, default=str))
    return man


def load_processed_minutes(ix: IndexSpec, source_id: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(ix.proc / source_id / "minutes" / "year=*" / "month=*" / "candles.parquet")))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def load_processed_daily(ix: IndexSpec, source_id: str) -> pd.DataFrame:
    df = pd.read_parquet(ix.proc / source_id / "daily" / "candles.parquet")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date").reset_index(drop=True)


def source_manifest(ix: IndexSpec, source_id: str) -> dict:
    return json.loads((ix.proc / source_id / "source_manifest.json").read_text())


# ------------------------------------------------------------------------------------------------------------------------------ calendar
def derive_calendar_index(daily: pd.DataFrame, minute_sources: dict[str, pd.DataFrame], start: date, end: date, coverage: dict[str, list[tuple[date, date]]]):
    """``phase4_data.derive_calendar`` with ONE refinement for use with several minute sources: a WEEKDAY whose first bar is not 09:15 in one source but IS 09:15 in another source that has rows that day is a vendor
    DEFECT in the first source (missing opening bars), not a special session (a Muhurat / evening session has no 09:15 bar in any source). Such dates are removed from the special sessions and listed in the metadata
    (``opening_bar_defects``); the defective source's session is still caught by the session-quality gate of that source. Weekend sessions and sessions late in every source are unchanged."""
    cal, meta = D4.derive_calendar(daily, minute_sources, start, end, coverage)
    first_bar = {}
    for k, v in minute_sources.items():
        t = v["timestamp"]
        g = pd.DataFrame({"d": t.dt.date, "m": t.dt.hour * 60 + t.dt.minute}).groupby("d")["m"].min()
        first_bar[k] = g
    defects, specials = [], dict(cal.special_sessions)
    for d in list(specials):
        if d.weekday() >= 5:
            continue
        starts = {k: int(g.loc[d]) for k, g in first_bar.items() if d in g.index}
        if any(m == 555 for m in starts.values()) and any(m != 555 for m in starts.values()):
            defects.append({"date": str(d), "first_bar_minute_of_day_by_source": starts})
            del specials[d]
    from nifty_trading.data.market_calendar import MarketCalendar
    meta = {**meta, "opening_bar_defects": defects, "n_special": len(specials)}
    return MarketCalendar(cal.holidays, specials, cal.closing_auction, source=cal.source), meta
