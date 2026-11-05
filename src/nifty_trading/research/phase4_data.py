"""Phase 4 data layer: loaders for the two minute-data sources and the 5paisa daily series, separate processed namespaces, a DERIVED multi-year trading calendar, the per-session quality table
and the vendor-overlap audit.

Nothing here modifies the Phase 1 dataset or any earlier report: raw responses live in data/raw/phase4_5paisa/ and data/raw/phase4_technovusin/<commit>/, processed partitions in data/phase4/processed/<source id>/
(same layout as data/processed so the existing loaders and ``build_session_contexts`` work unchanged), the derived calendar in data/phase4/calendar/. Vendors are never merged: one run uses ONE minute source; the 5paisa
DAILY series (official close, daily moving averages) is a separately identified second input whose role is documented.
"""

from __future__ import annotations

import glob
import hashlib
import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from nifty_trading.data.market_calendar import CalendarEntry, MarketCalendar, load_market_calendar
from nifty_trading.data.sessions import (
    CLOSE_STUB_LABEL,
    LAST_MINUTE_LABEL,
    SESSION_OPEN,
    build_session_contexts,
    classify_session,
    stale_row_mask,
)

ROOT = Path(__file__).resolve().parents[3]
RAW_5P = ROOT / "data" / "raw" / "phase4_5paisa"
RAW_TV = ROOT / "data" / "raw" / "phase4_technovusin"
PROC = ROOT / "data" / "phase4" / "processed"
CAL_DIR = ROOT / "data" / "phase4" / "calendar"
IST = "Asia/Kolkata"
PHASE1_PROCESSED = ROOT / "data" / "processed"

SRC_5P_MIN = "FIVEPAISA_1M_PHASE4"
SRC_TV_MIN = "TECHNOVUS_1M"
SRC_5P_DAILY = "FIVEPAISA_1D_PHASE4"
EXPECTED_BARS = 375  # 09:15 .. 15:29
# predeclared data-quality thresholds (written before any backtest was run; reported, never tuned)
OUTLIER_1M_RETURN_PCT = 0.5  # a 1-minute close-to-close move above this is reported as an extreme candle (not excluded)
ABNORMAL_FIRST_BAR_RANGE_PCT = 1.0  # a 09:15 bar whose range exceeds this share of its open is reported
CLOSE_VS_DAILY_TOLERANCE = 0.05  # |daily official close - last 15:29 close| above this is a disclosed difference (the official close is not the last tick)
HL_VS_DAILY_TOLERANCE = 0.5  # |session high/low from minutes - daily high/low| above this is reported
OPEN_VS_DAILY_TOLERANCE = 0.05


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------------------------------ loaders
def _finish_minutes(df: pd.DataFrame, source_files: dict[str, str] | None = None) -> tuple[pd.DataFrame, dict]:
    """Common cleaning: IST timestamps, 2-decimal prices (the 5paisa DAILY candles carry float32 noise such as 8210.0996, removed by rounding; the 1-minute responses carry none: the maximum deviation is recorded and is 0.0), identical duplicate rows removed (conflicting duplicates are reported and
    the LAST row kept, as the Phase 1 downloader did), chronological order."""
    info: dict[str, Any] = {"rows_in": int(len(df))}
    for c in ("open", "high", "low", "close"):
        info.setdefault("max_rounding_deviation", 0.0)
        info["max_rounding_deviation"] = max(info["max_rounding_deviation"], float((df[c] - df[c].round(2)).abs().max()))
        df[c] = df[c].round(2)
    dup = df["timestamp"].duplicated(keep=False)
    if dup.any():
        d = df[dup]
        conflicting = int((d.groupby("timestamp")[["open", "high", "low", "close"]].nunique().max(axis=1) > 1).sum())
        info["duplicate_rows_removed"] = int(df["timestamp"].duplicated(keep="last").sum())
        info["duplicate_dates"] = sorted({str(t.date()) for t in d["timestamp"]})
        info["conflicting_duplicate_timestamps"] = conflicting
        df = df.drop_duplicates(subset=["timestamp"], keep="last")
    else:
        info["duplicate_rows_removed"] = 0
        info["duplicate_dates"] = []
        info["conflicting_duplicate_timestamps"] = 0
    df = df.sort_values("timestamp").reset_index(drop=True)
    info["rows_out"] = int(len(df))
    info["chronological_input"] = True
    return df, info


def load_5p_minutes(raw_dir: Path = RAW_5P) -> tuple[pd.DataFrame, dict]:
    man = json.loads((raw_dir / "manifest.json").read_text())
    frames, files = [], {}
    for _key, r in sorted(man["requests"].items()):
        if r["timeframe"] != "1m" or r["status"] != "COMPLETED":
            continue
        p = raw_dir / r["file"]
        assert sha256_file(p) == r["sha256"], f"raw file changed since retrieval: {p}"
        x = pd.read_csv(p)
        x["raw_file"] = r["file"]
        frames.append(x)
        files[r["file"]] = r["sha256"]
    raw = pd.concat(frames, ignore_index=True)
    chron = bool(pd.to_datetime(raw["Datetime"]).is_monotonic_increasing)
    df = pd.DataFrame({"timestamp": pd.to_datetime(raw["Datetime"]).dt.tz_localize(IST), "open": raw["Open"].astype(float), "high": raw["High"].astype(float), "low": raw["Low"].astype(float),
                       "close": raw["Close"].astype(float), "volume": raw["Volume"].fillna(0).astype("int64"), "raw_file": raw["raw_file"]})
    out, info = _finish_minutes(df.drop(columns="raw_file"))
    rf = df.drop_duplicates("timestamp", keep="last").set_index("timestamp")["raw_file"]
    out["raw_file"] = out["timestamp"].map(rf)
    info.update({"source_id": SRC_5P_MIN, "raw_files": files, "chronological_input": chron})
    return out, info


def tv_commit_dir() -> Path:
    dirs = sorted(p for p in RAW_TV.iterdir() if p.is_dir())
    assert len(dirs) == 1, f"expected exactly one pinned secondary-source commit directory, found {[d.name for d in dirs]}"
    return dirs[0]


def load_tv_minutes(years: tuple[int, ...] | None = None) -> tuple[pd.DataFrame, dict]:
    d = tv_commit_dir()
    man = json.loads((d / "manifest.json").read_text())
    frames, files = [], {}
    for path, f in sorted(man["files"].items()):
        if not path.startswith("1min/") or f["status"] != "OK":
            continue
        if years is not None and not any(f"/{y}/" in path or f"_{y}" in path for y in years):
            continue
        p = d / path
        assert sha256_file(p) == f["sha256"], f"raw file changed since retrieval: {p}"
        x = pd.read_csv(p)
        x["raw_file"] = path
        frames.append(x)
        files[path] = f["sha256"]
    raw = pd.concat(frames, ignore_index=True)
    chron = bool(pd.to_datetime(raw["Timestamp"]).is_monotonic_increasing)
    df = pd.DataFrame({"timestamp": pd.to_datetime(raw["Timestamp"]).dt.tz_localize(IST), "open": raw["Open"].astype(float), "high": raw["High"].astype(float), "low": raw["Low"].astype(float),
                       "close": raw["Close"].astype(float), "volume": (raw["Volume"].fillna(0).astype("int64") if "Volume" in raw else 0), "raw_file": raw["raw_file"]})
    out, info = _finish_minutes(df.drop(columns="raw_file"))
    rf = df.drop_duplicates("timestamp", keep="last").set_index("timestamp")["raw_file"]
    out["raw_file"] = out["timestamp"].map(rf)
    info.update({"source_id": SRC_TV_MIN, "raw_files": files, "commit_sha": man["commit_sha"], "commit_date": man["commit_date"], "chronological_input": chron})
    return out, info


def load_5p_daily(raw_dir: Path = RAW_5P) -> tuple[pd.DataFrame, dict]:
    man = json.loads((raw_dir / "manifest.json").read_text())
    frames, files = [], {}
    for _key, r in sorted(man["requests"].items()):
        if r["timeframe"] != "1d" or r["status"] != "COMPLETED":
            continue
        p = raw_dir / r["file"]
        assert sha256_file(p) == r["sha256"], f"raw file changed since retrieval: {p}"
        frames.append(pd.read_csv(p))
        files[r["file"]] = r["sha256"]
    raw = pd.concat(frames, ignore_index=True)
    df = pd.DataFrame({"date": pd.to_datetime(raw["Datetime"]).dt.date, "open": raw["Open"].astype(float).round(2), "high": raw["High"].astype(float).round(2), "low": raw["Low"].astype(float).round(2),
                       "close": raw["Close"].astype(float).round(2)})
    n0 = len(df)
    df = df.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    return df, {"source_id": SRC_5P_DAILY, "raw_files": files, "rows": int(len(df)), "duplicates_removed": n0 - len(df), "first": str(df["date"].min()), "last": str(df["date"].max())}


# ------------------------------------------------------------------------------------------------------------------------------ processed namespace
def write_processed(source_id: str, minutes: pd.DataFrame | None, daily: pd.DataFrame | None, info: dict) -> dict:
    """Write ``data/phase4/processed/<source_id>/nifty50/year=*/month=*/candles.parquet`` (and ``nifty50_daily``) and a manifest with the SHA-256 of every partition."""
    base = PROC / source_id
    man: dict[str, Any] = {"source_id": source_id, "written_utc": datetime.utcnow().isoformat() + "Z", "loader_info": {k: v for k, v in info.items() if k != "raw_files"}, "raw_files": info.get("raw_files", {}), "partitions": {}}
    if minutes is not None:
        m = minutes.drop(columns=[c for c in ("raw_file",) if c in minutes.columns])
        for (y, mo), g in m.groupby([m["timestamp"].dt.year, m["timestamp"].dt.month]):
            p = base / "nifty50" / f"year={y}" / f"month={mo:02d}" / "candles.parquet"
            p.parent.mkdir(parents=True, exist_ok=True)
            g.reset_index(drop=True).to_parquet(p, index=False)
            raw_files = sorted(set(minutes.loc[g.index, "raw_file"])) if "raw_file" in minutes.columns else []
            man["partitions"][str(p.relative_to(ROOT))] = {"sha256": sha256_file(p), "rows": int(len(g)), "first": str(g["timestamp"].iloc[0]), "last": str(g["timestamp"].iloc[-1]), "raw_files": raw_files}
    if daily is not None:
        p = base / "nifty50_daily" / "candles.parquet"
        p.parent.mkdir(parents=True, exist_ok=True)
        daily.to_parquet(p, index=False)
        man["partitions"][str(p.relative_to(ROOT))] = {"sha256": sha256_file(p), "rows": int(len(daily)), "first": str(daily["date"].min()), "last": str(daily["date"].max())}
    (base / "source_manifest.json").write_text(json.dumps(man, indent=1, sort_keys=True, default=str))
    return man


def load_processed_minutes(source_id: str) -> pd.DataFrame:
    files = sorted(glob.glob(str(PROC / source_id / "nifty50" / "year=*" / "month=*" / "candles.parquet")))
    return pd.concat([pd.read_parquet(f) for f in files], ignore_index=True).sort_values("timestamp").reset_index(drop=True)


def load_processed_daily(source_id: str) -> pd.DataFrame:
    df = pd.read_parquet(PROC / source_id / "nifty50_daily" / "candles.parquet")
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df.sort_values("date").reset_index(drop=True)


def partition_path(source_id: str, d: date) -> str:
    return f"data/phase4/processed/{source_id}/nifty50/year={d.year}/month={d.month:02d}/candles.parquet"


def source_manifest(source_id: str) -> dict:
    return json.loads((PROC / source_id / "source_manifest.json").read_text())


# ------------------------------------------------------------------------------------------------------------------------------ derived calendar
def _per_day(minutes: pd.DataFrame) -> pd.DataFrame:
    t = minutes["timestamp"]
    d = t.dt.date
    mins = t.dt.hour * 60 + t.dt.minute
    g = pd.DataFrame({"d": d, "m": mins}).groupby("d")["m"].agg(["min", "max", "count"])
    return g


def derive_calendar(daily: pd.DataFrame, minute_sources: dict[str, pd.DataFrame], start: date, end: date, coverage: dict[str, list[tuple[date, date]]] | None = None) -> tuple[MarketCalendar, dict]:
    """A DERIVED trading calendar for [start, end]:
      * HOLIDAY (weekday): no 5paisa daily candle AND no minute rows in any source that covers the date. Evidence tier D1 when at least one minute source covers the date (two independent series agree the market was
        closed), D2 when only the daily series covers it.
      * a weekday present in only SOME of the covering series is NOT a holiday: it is a vendor data gap, listed in the report and left to the session classifier (the next session's previous-day data become unverified).
      * SPECIAL SESSION: a weekend date that has a daily candle or minute rows, or a weekday session whose first bar is not 09:15 (Muhurat). ``evaluable_by_strategies`` only when the minute data start at 09:15
        and carry a full normal-hours session (>= 370 rows in the regular window), mirroring the Phase 2 treatment of the Budget-day Sunday session.
    ``coverage`` lists the date ranges each minute source was retrieved for (a source is only expected to have rows inside them). No closing-auction regime: it did not exist before 2026-08-03."""
    daily_dates = set(daily["date"])
    per_day = {k: _per_day(v) for k, v in minute_sources.items()}
    series_dates: dict[str, set[date]] = {k: set(v.index) for k, v in per_day.items()}
    cov = coverage or {k: [(start, end)] for k in minute_sources}

    def covers(k: str, d: date) -> bool:
        return any(a <= d <= b for a, b in cov.get(k, []))
    holidays, specials, gaps = {}, {}, []
    d = start
    while d <= end:
        in_daily = d in daily_dates
        cover = [k for k in minute_sources if covers(k, d)]
        in_min = {k: d in series_dates[k] for k in cover}
        if d.weekday() < 5:
            if not in_daily and not any(in_min.values()):
                tier = "D1" if cover else "D2"
                holidays[d] = CalendarEntry(d, "derived weekday closure (no daily candle" + (" and no minute rows in any covering source)" if cover else "; no minute source covers the date)"), tier,
                                            (f"no 5paisa daily candle; no rows in {', '.join(cover) or '(none covering)'}",))
            elif (in_daily and cover and not all(in_min.values())) or (not in_daily and any(in_min.values())):  # daily says traded but a covering source lacks it, or minutes exist without a daily candle
                gaps.append({"date": str(d), "daily_candle": in_daily, **{f"minutes_{k}": v for k, v in in_min.items()}})
        special_start = [k for k in per_day if d in per_day[k].index and int(per_day[k].loc[d, "min"]) != 555]
        if (d.weekday() >= 5 and (in_daily or any(in_min.values()))) or special_start:
            full = any(d in per_day[k].index and int(per_day[k].loc[d, "min"]) == 555 and int(per_day[k].loc[d, "count"]) >= 370 for k in per_day)
            what = ("weekend, normal hours" if d.weekday() >= 5 and full else "weekend, non-standard hours" if d.weekday() >= 5 else "weekday, first bar is not 09:15: an evening / Muhurat session or a missing opening bar")
            specials[d] = CalendarEntry(d, f"derived special session ({what})", "D1", (f"daily candle present: {in_daily}; minute rows: {in_min}",), evaluable_by_strategies=bool(full and not special_start))
        d += timedelta(days=1)
    cal = MarketCalendar(holidays, specials, None, source="DERIVED_PHASE4")
    return cal, {"gaps_between_series": gaps, "n_holidays": len(holidays), "n_special": len(specials)}


def calendar_to_json(cal: MarketCalendar, meta: dict, path: Path) -> None:
    obj = {"version": "phase4-derived-1", "generated_utc": datetime.utcnow().isoformat() + "Z", "method": "see phase4_data.derive_calendar", "meta": meta,
           "holidays": [{"date": str(d), "name": e.name, "evidence_tier": e.evidence_tier, "evidence": list(e.evidence)} for d, e in sorted(cal.holidays.items())],
           "special_sessions": [{"date": str(d), "name": e.name, "evidence_tier": e.evidence_tier, "evidence": list(e.evidence), "evaluable_by_strategies": e.evaluable_by_strategies} for d, e in sorted(cal.special_sessions.items())],
           "market_structure_changes": []}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=1))


def validate_calendar_method(derived: MarketCalendar, evidence_path: Path | None = None, lo: date = date(2025, 9, 1), hi: date = date(2026, 8, 31)) -> dict:
    """Derive the same kind of calendar for the Phase 1 period from its daily + minute data and compare with the evidence-tier calendar (nse_calendar_2025_2026.json)."""
    ev = load_market_calendar(evidence_path)
    d_h = {d for d in derived.holidays if lo <= d <= hi}
    e_h = {d for d in ev.holidays if lo <= d <= hi}
    d_s = {d: (derived.special_sessions[d].evaluable_by_strategies) for d in derived.special_sessions if lo <= d <= hi}
    e_s = {d: ev.special_sessions[d].evaluable_by_strategies for d in ev.special_sessions if lo <= d <= hi}
    return {"period": f"{lo}..{hi}", "derived_holidays": len(d_h), "evidence_holidays": len(e_h), "holidays_only_derived": sorted(map(str, d_h - e_h)), "holidays_only_evidence": sorted(map(str, e_h - d_h)),
            "special_sessions_derived": {str(k): v for k, v in sorted(d_s.items())}, "special_sessions_evidence": {str(k): v for k, v in sorted(e_s.items())},
            "identical": d_h == e_h and d_s == e_s}


# ------------------------------------------------------------------------------------------------------------------------------ per-session quality table
def _flat_run_max(day: pd.DataFrame) -> int:
    flat = ((day["open"] == day["high"]) & (day["high"] == day["low"]) & (day["low"] == day["close"])).to_numpy()
    best = cur = 0
    for f in flat:
        cur = cur + 1 if f else 0
        best = max(best, cur)
    return best


def session_quality_table(minutes: pd.DataFrame, daily: pd.DataFrame, cal: MarketCalendar, source_id: str, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """One row per session present in ``minutes`` within [start, end]: structure, gaps, OHLC, outliers, frozen prices, daily reconciliation and the pipeline's own classification (``classify_session``)."""
    daily_by = {r.date: r for r in daily.itertuples(index=False)}
    rows = []
    last_daily_before: dict[date, float] = {}
    run = None
    for r in daily.itertuples(index=False):
        last_daily_before[r.date] = run if run is not None else float("nan")
        run = r.close
    for d, day in minutes.groupby(minutes["timestamp"].dt.date, sort=True):
        if (start and d < start) or (end and d > end):
            continue
        day = day.sort_values("timestamp")
        t = day["timestamp"].dt.time
        mins = (day["timestamp"].dt.hour * 60 + day["timestamp"].dt.minute).to_numpy()
        reg = day[(t >= SESSION_OPEN) & (t <= LAST_MINUTE_LABEL)]
        present = set(mins[(mins >= 555) & (mins <= 929)])
        missing = [m for m in range(555, 930) if m not in present]
        ranges: list[str] = []
        for m in missing:
            if ranges and ranges[-1][1] == m - 1:
                ranges[-1][1] = m
            else:
                ranges.append([m, m])
        rng_txt = ";".join(f"{a // 60:02d}:{a % 60:02d}" + ("" if a == b else f"-{b // 60:02d}:{b % 60:02d}") for a, b in ranges[:6]) + ("..." if len(ranges) > 6 else "")
        bad = ((day["high"] < day[["open", "close"]].max(axis=1)) | (day["low"] > day[["open", "close"]].min(axis=1)) | day[["open", "high", "low", "close"]].isna().any(axis=1) | (day[["open", "high", "low", "close"]] <= 0).any(axis=1))
        closes = reg["close"].to_numpy()
        rets = np.abs(np.diff(closes) / closes[:-1]) * 100.0 if len(closes) > 1 else np.array([0.0])
        first = reg.iloc[0] if len(reg) else None
        dr = daily_by.get(d)
        info, _c = classify_session(day, cal, None if dr is None else float(dr.close))
        stub = day[t == CLOSE_STUB_LABEL]
        last_1529 = reg[reg["timestamp"].dt.time == LAST_MINUTE_LABEL]
        row = {"source_id": source_id, "date": str(d), "weekday": f"{d:%a}", "n_rows": int(len(day)), "n_regular_rows": int(len(reg)), "first_bar": f"{day['timestamp'].iloc[0]:%H:%M}", "last_bar": f"{day['timestamp'].iloc[-1]:%H:%M}",
               "missing_regular_minutes": len(missing), "missing_minute_ranges": rng_txt, "has_1530_stub": bool(len(stub)), "ohlc_violation_rows": int(bad.sum()),
               "zero_range_rows": int(((reg["high"] == reg["low"])).sum()), "longest_flat_run": _flat_run_max(reg), "frozen_rows_ge5": int(stale_row_mask(reg).sum()) if len(reg) else 0,
               "max_1m_close_return_pct": round(float(rets.max()), 4), "extreme_1m_candles": int((rets > OUTLIER_1M_RETURN_PCT).sum()),
               "first_bar_range_pct": None if first is None else round(float((first["high"] - first["low"]) / first["open"] * 100.0), 4),
               "abnormal_first_bar": bool(first is not None and (first["high"] - first["low"]) / first["open"] * 100.0 > ABNORMAL_FIRST_BAR_RANGE_PCT),
               "first_open_is_0915": bool(first is not None and first["timestamp"].time() == SESSION_OPEN), "in_daily_series": dr is not None,
               "daily_close": None if dr is None else dr.close, "last_1529_close": None if not len(last_1529) else float(last_1529["close"].iloc[0]),
               "daily_close_minus_last_1529": None if dr is None or not len(last_1529) else round(float(dr.close - last_1529["close"].iloc[0]), 2),
               "session_high_minus_daily_high": None if dr is None or not len(reg) else round(float(reg["high"].max() - dr.high), 2),
               "session_low_minus_daily_low": None if dr is None or not len(reg) else round(float(reg["low"].min() - dr.low), 2),
               "first_open_minus_daily_open": None if dr is None or first is None else round(float(first["open"] - dr.open), 2),
               "gap_to_previous_daily_close": None if dr is None or first is None or np.isnan(last_daily_before.get(d, float("nan"))) else round(float(first["open"] - last_daily_before[d]), 2),
               "pipeline_status": info.status.value, "pipeline_quality": info.quality.value, "pipeline_reasons": ";".join(info.reasons), "pipeline_flags": ";".join(info.flags), "usable": info.usable,
               "calendar_special": d in cal.special_sessions, "raw_file": (str(day["raw_file"].iloc[0]) if "raw_file" in day.columns else "")}
        rows.append(row)
    return pd.DataFrame(rows)


def coverage_table(quality: pd.DataFrame, cal: MarketCalendar, daily: pd.DataFrame, start: date, end: date, label: str) -> dict:
    """Expected sessions (weekdays that are not derived holidays, plus daily-series sessions on weekends) versus what the source supplies."""
    daily_dates = {d for d in daily["date"] if start <= d <= end}
    expected = set()
    d = start
    while d <= end:
        if d.weekday() < 5 and d not in cal.holidays:
            expected.add(d)
        d += timedelta(days=1)
    expected |= {x for x in daily_dates if x.weekday() >= 5}
    q = quality[(quality["date"] >= str(start)) & (quality["date"] <= str(end))]
    have = {date.fromisoformat(x) for x in q["date"]}
    missing = sorted(expected - have)
    st = Counter(q["pipeline_status"])
    return {"window": label, "start": str(start), "end": str(end), "expected_sessions": len(expected), "sessions_in_source": len(have & expected), "sessions_missing_from_source": len(missing),
            "missing_dates": ";".join(map(str, missing)), "derived_holidays_in_window": sum(1 for h in cal.holidays if start <= h <= end), "usable_sessions": int(q["usable"].sum()),
            "usable_with_flags": int(st.get("USABLE_WITH_FLAGS", 0)), "excluded_sessions": int((~q["usable"]).sum()), "excluded_non_standard_start": int(st.get("EXCLUDED_NON_STANDARD_START", 0)),
            "excluded_corrupt": int(st.get("EXCLUDED_CORRUPT", 0)), "excluded_unverified": int(st.get("EXCLUDED_UNVERIFIED", 0)), "excluded_no_opening_candle": int(st.get("EXCLUDED_NO_OPENING_CANDLE", 0)),
            "sessions_with_missing_minutes": int((q["missing_regular_minutes"] > 0).sum()), "total_missing_regular_minutes": int(q["missing_regular_minutes"].sum()), "sessions_with_frozen_runs": int((q["frozen_rows_ge5"] > 0).sum()),
            "sessions_with_extreme_1m_candles": int((q["extreme_1m_candles"] > 0).sum()), "abnormal_first_bars": int(q["abnormal_first_bar"].sum()), "ohlc_violation_rows": int(q["ohlc_violation_rows"].sum()),
            "excluded_dates": ";".join(f"{r.date}:{r.pipeline_status}" for r in q[~q["usable"]].itertuples())}


# ------------------------------------------------------------------------------------------------------------------------------ overlap audit between two minute sources
def overlap_audit(a: pd.DataFrame, b: pd.DataFrame, label_a: str, label_b: str, lo: date | None = None, hi: date | None = None) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Bar-by-bar comparison of two minute sources on their overlap, restricted to the regular window 09:15..15:29 (the secondary source carries no 15:30 stub). Returns (per-day, per-month, summary)."""
    def prep(x):
        t = x["timestamp"]
        m = t.dt.hour * 60 + t.dt.minute
        x = x[(m >= 555) & (m <= 929)]
        if lo:
            x = x[t.dt.date >= lo]
        if hi:
            x = x[t.dt.date <= hi]
        return x.set_index("timestamp")[["open", "high", "low", "close"]]
    A, B = prep(a), prep(b)
    j = A.join(B, how="inner", lsuffix="_a", rsuffix="_b")
    for c in ("open", "high", "low", "close"):
        j[f"d_{c}"] = j[f"{c}_a"] - j[f"{c}_b"]
    j["date"] = j.index.date
    j["exact"] = (j[["d_open", "d_high", "d_low", "d_close"]].abs().max(axis=1) <= 0.005)
    j["within_005"] = (j["d_close"].round(2).abs() <= 0.05 + 1e-9)  # difference rounded to the 0.01 grid first, so an exact one-tick (0.05) difference is not lost to float subtraction
    j["within_1"] = (j["d_close"].abs() <= 1.0)
    g = j.groupby("date")
    day = pd.DataFrame({"bars_compared": g.size(), "bars_exact_all_fields": g["exact"].sum(), "share_exact": g["exact"].mean().round(4), "share_close_within_0_05": g["within_005"].mean().round(4),
                        "max_abs_close_diff": g["d_close"].apply(lambda s: s.abs().max()).round(2), "mean_abs_close_diff": g["d_close"].apply(lambda s: s.abs().mean()).round(4),
                        "max_abs_open_diff": g["d_open"].apply(lambda s: s.abs().max()).round(2), "max_abs_high_diff": g["d_high"].apply(lambda s: s.abs().max()).round(2),
                        "max_abs_low_diff": g["d_low"].apply(lambda s: s.abs().max()).round(2)}).reset_index()
    da, db = {x.date() for x in A.index}, {x.date() for x in B.index}
    only_a, only_b = sorted(da - db), sorted(db - da)
    cnt_a, cnt_b = A.groupby(A.index.date).size(), B.groupby(B.index.date).size()
    day["bars_only_in_a"] = day["date"].map(lambda d: int(cnt_a.get(d, 0)) - 0) - day["bars_compared"]
    day["bars_only_in_b"] = day["date"].map(lambda d: int(cnt_b.get(d, 0)) - 0) - day["bars_compared"]
    day["month"] = day["date"].map(lambda d: f"{d:%Y-%m}")
    mon = day.groupby("month").agg(days=("date", "count"), bars=("bars_compared", "sum"), exact_bars=("bars_exact_all_fields", "sum"), mean_abs_close_diff=("mean_abs_close_diff", "mean"), max_abs_close_diff=("max_abs_close_diff", "max"),
                                   days_with_diff_over_1pt=("max_abs_close_diff", lambda s: int((s > 1.0).sum()))).reset_index()
    mon["share_exact"] = (mon["exact_bars"] / mon["bars"]).round(4)
    # timestamp-convention check: does shifting B by one minute improve agreement? (a one-minute label difference between vendors would show here)
    shifts = {}
    for k in (-1, 0, 1):
        Bs = B.copy()
        Bs.index = Bs.index + pd.Timedelta(minutes=k)
        jj = A.join(Bs, how="inner", lsuffix="_a", rsuffix="_b")
        shifts[str(k)] = {"bars": int(len(jj)), "share_close_equal_within_0_05": round(float(((jj["close_a"] - jj["close_b"]).round(2).abs() <= 0.05 + 1e-9).mean()), 4)} if len(jj) else {"bars": 0}
    summ = {"a": label_a, "b": label_b, "dates_a": len(da), "dates_b": len(db), "dates_in_both": len(da & db), "dates_only_a": [str(x) for x in only_a], "dates_only_b": [str(x) for x in only_b],
            "bars_compared": int(len(j)), "share_exact_all_fields": round(float(j["exact"].mean()), 4) if len(j) else None, "share_close_within_0_05": round(float(j["within_005"].mean()), 4) if len(j) else None,
            "share_close_within_1": round(float(j["within_1"].mean()), 4) if len(j) else None, "mean_abs_close_diff": round(float(j["d_close"].abs().mean()), 4) if len(j) else None,
            "p99_abs_close_diff": round(float(j["d_close"].abs().quantile(0.99)), 4) if len(j) else None, "max_abs_close_diff": round(float(j["d_close"].abs().max()), 2) if len(j) else None,
            "days_with_any_diff_over_1pt": int((day["max_abs_close_diff"] > 1.0).sum()), "bars_only_in_a": int(day["bars_only_in_a"].sum()), "bars_only_in_b": int(day["bars_only_in_b"].sum()), "timestamp_shift_test": shifts}
    return day, mon, summ


# ------------------------------------------------------------------------------------------------------------------------------ window data for the backtest runner
@dataclass
class WindowData:
    window_id: str
    start: date
    end: date
    minute_source_id: str
    daily_source_id: str
    ctxs: dict
    infos: dict
    bars: dict
    calendar: MarketCalendar
    n_warmup_rows: int = 0
    notes: list[str] = field(default_factory=list)
    provenance: dict = field(default_factory=dict)


def build_window_data(window_id: str, minutes: pd.DataFrame, daily: pd.DataFrame, cal: MarketCalendar, start: date, end: date, minute_source_id: str, daily_source_id: str, warmup_days: int = 45) -> WindowData:
    """Sessions of [start, end] with causal indicators. Rows of the ``warmup_days`` calendar days BEFORE ``start`` (same minute source) seed the 5-minute EMA and supply the previous session of the first day; they are never
    evaluated and contribute no trades. The daily series (strictly earlier dates only, >= 200 bars needed for the daily moving averages) comes from ``daily``."""
    from nifty_trading.core.execution_eligibility import bars_from_frame
    t = minutes["timestamp"].dt.date
    win = minutes[(t >= start) & (t <= end)].drop(columns=[c for c in ("raw_file",) if c in minutes.columns]).reset_index(drop=True)
    wu = minutes[(t >= start - timedelta(days=warmup_days)) & (t < start)].drop(columns=[c for c in ("raw_file",) if c in minutes.columns]).reset_index(drop=True)
    ctxs, infos = build_session_contexts(win, calendar=cal, daily_df=daily, warmup_1m=wu if len(wu) else None)
    w2 = win.assign(_d=win["timestamp"].dt.date)
    bars = {d: bars_from_frame(g, cal) for d, g in w2.groupby("_d")}
    return WindowData(window_id, start, end, minute_source_id, daily_source_id, ctxs, infos, bars, cal, n_warmup_rows=int(len(wu)),
                      notes=([] if len(wu) else ["no minute warm-up rows exist before the window in this source: the 5-minute EMA(200) is undefined for the first ~200 candles (about 3 sessions)"]))
