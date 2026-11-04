"""Phase 2.1: build NEW processed artefacts from the raw re-downloads, with provenance. Never overwrites existing data.

Creates (all atomic, refuses to overwrite an existing file):
  data/processed/nifty50_daily/candles.parquet    vendor DAILY candles 2024-09-01..2026-08-31 (official closes, 200-DMA history)
  data/processed/nifty50_warmup/year=YYYY/month=MM/candles.parquet   pre-period 1-minute data, WARM-UP ONLY (2025-07, 2025-08)
  data/metadata/provenance_new_artifacts.json     source file, request, row counts and SHA-256 of every input and output

The original Phase 1 minute data under data/processed/nifty50 is untouched (an unchanged archive with checksums lives in
data/archive/phase1_original_20261101).
"""

from __future__ import annotations

import glob
import hashlib
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.downloader import HistoricalDataDownloader  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def find_raw(label: str) -> tuple[Path, dict]:
    hits = []
    for log in sorted(glob.glob(str(ROOT / "data" / "raw" / "redownload_*" / "request_log.json"))):
        for e in json.loads(Path(log).read_text()):
            if e["label"] == label and e["status"] == "OK":
                hits.append((Path(log).parent / e["file"], e))
    if not hits:
        raise FileNotFoundError(label)
    return hits[-1]


def atomic_write_parquet(df: pd.DataFrame, path: Path) -> None:
    if path.exists():
        raise FileExistsError(f"refusing to overwrite {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".parquet.tmp")
    df.to_parquet(tmp, compression="zstd", index=False)
    os.replace(tmp, path)


def main() -> int:
    targets = [ROOT / "data" / "processed" / "nifty50_daily" / "candles.parquet"] + [
        ROOT / "data" / "processed" / "nifty50_warmup" / f"year={y}" / f"month={m:02d}" / "candles.parquet" for y, m in ((2025, 7), (2025, 8))]
    existing = [str(t) for t in targets if t.exists()]
    if existing:  # check everything up front so a failure half-way cannot leave a partial, un-rerunnable state
        raise FileExistsError(f"refusing to overwrite: {existing}")
    prov: dict = {"built_utc": datetime.now(timezone.utc).isoformat(), "artifacts": []}
    # ------------------------------------------------------------ daily (official closes)
    parts, srcs = [], []
    for label in ("daily_2024_09_to_2025_08", "daily_2025_09_to_2026_08"):
        f, e = find_raw(label)
        parts.append(pd.read_parquet(f))
        srcs.append({"label": label, "file": str(f.relative_to(ROOT)), "sha256": sha(f), "request": e["request"], "rows": e["rows"]})
    d = pd.concat(parts, ignore_index=True).rename(columns={"Datetime": "date", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"})
    d["date"] = pd.to_datetime(d["date"]).dt.date
    d = d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    assert d["date"].is_unique and ((d.high >= d[["open", "close"]].max(axis=1)) & (d.low <= d[["open", "close"]].min(axis=1))).all()
    out = ROOT / "data" / "processed" / "nifty50_daily" / "candles.parquet"
    atomic_write_parquet(d, out)
    prov["artifacts"].append({"artifact": str(out.relative_to(ROOT)), "rows": len(d), "first": str(d.date.min()), "last": str(d.date.max()),
                              "sha256": sha(out), "sources": srcs, "use": "official closes; daily 200-DMA history (>=200 bars before 2025-09-01)"})
    # ------------------------------------------------------------ warm-up minutes
    for label, (y, m) in {"warm_2025_07_1m": (2025, 7), "warm_2025_08_1m": (2025, 8)}.items():
        f, e = find_raw(label)
        clean, rejected = HistoricalDataDownloader.clean_and_validate_raw_df(None, pd.read_parquet(f))
        out = ROOT / "data" / "processed" / "nifty50_warmup" / f"year={y}" / f"month={m:02d}" / "candles.parquet"
        atomic_write_parquet(clean, out)
        prov["artifacts"].append({"artifact": str(out.relative_to(ROOT)), "rows": len(clean), "rejected_rows": rejected,
                                  "first": clean.timestamp.min().isoformat(), "last": clean.timestamp.max().isoformat(), "sha256": sha(out),
                                  "sources": [{"label": label, "file": str(f.relative_to(ROOT)), "sha256": sha(f), "request": e["request"], "rows": e["rows"]}],
                                  "use": "WARM-UP ONLY: seeds the 5-minute EMA and supplies the previous session of 2025-09-01; never evaluated"})
    meta = ROOT / "data" / "metadata" / "provenance_new_artifacts.json"
    tmp_meta = meta.with_suffix(".json.tmp")
    tmp_meta.write_text(json.dumps(prov, indent=2))
    os.replace(tmp_meta, meta)
    print(json.dumps([{k: a[k] for k in ("artifact", "rows")} for a in prov["artifacts"]], indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
