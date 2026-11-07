"""Phase 5: build the processed (Parquet, ZSTD) namespaces for BANKNIFTY and SENSEX, the calendar DERIVED from each index's own data, the per-session data-quality tables, the coverage tables and the vendor-overlap audits.

Inputs (read-only): data/raw/<index>/5paisa/ and data/raw/<index>/secondary_kapri/<commit>/. Outputs: data/processed/<index>/<source id>/..., data/processed/<index>/calendar_derived.json and
reports/phase5/<index>/data/*.csv|json. Nothing under NIFTY directories, data/processed/nifty50*, data/phase4 or any earlier report is written.

Usage:  python scripts/phase5_build_data.py [--index BANKNIFTY|SENSEX]
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.research import phase4_data as D4  # noqa: E402
from nifty_trading.research import phase5 as F5  # noqa: E402
from nifty_trading.research import phase5_data as D5  # noqa: E402

START, END = date(2017, 1, 1), date(2026, 8, 31)
CAS_FIRST = date(2026, 8, 3)  # NSE closing-auction regime start (NIFTY evidence calendar); whether it applies to a given index is decided from that index's own data
COVER_5P = [(date(2019, 3, 1), date(2019, 12, 31)), (date(2022, 8, 1), date(2026, 8, 31))]


def closing_auction_evidence(m: pd.DataFrame) -> dict:
    """Per session from 2026-06-01: is 15:16..15:26 a single frozen price (open = high = low = close, one value)? A frozen index inside that window is the signature of the NSE closing-auction regime."""
    x = m[m["timestamp"].dt.date >= date(2026, 6, 1)].copy()
    x["d"] = x["timestamp"].dt.date
    x["hm"] = x["timestamp"].dt.hour * 60 + x["timestamp"].dt.minute
    rows = []
    for d, g in x.groupby("d"):
        w = g[(g["hm"] >= 15 * 60 + 16) & (g["hm"] <= 15 * 60 + 26)]
        flat = len(w) == 11 and bool(((w["open"] == w["high"]) & (w["high"] == w["low"]) & (w["low"] == w["close"])).all()) and w["close"].nunique() == 1
        rows.append((d, flat, len(w)))
    pre = [r for r in rows if r[0] < CAS_FIRST]
    post = [r for r in rows if r[0] >= CAS_FIRST]
    return {"sessions_before_2026_08_03": len(pre), "frozen_pattern_before": sum(1 for r in pre if r[1]), "sessions_from_2026_08_03": len(post), "frozen_pattern_from": sum(1 for r in post if r[1]),
            "first_session_with_pattern": str(next((r[0] for r in rows if r[1]), None)), "note": "pattern = the 11 one-minute bars 15:16..15:26 are all flat at one price"}


def build(ix: D5.IndexSpec) -> dict:
    out = ROOT / "reports" / "phase5" / ix.key / "data"
    out.mkdir(parents=True, exist_ok=True)
    m5, i5 = D5.load_5p_minutes(ix)
    ms, isec = D5.load_secondary_minutes(ix)
    dd, idl = D5.load_5p_daily(ix)
    print(f"{ix.name}: 5paisa minutes {len(m5):,} rows ({i5['duplicate_rows_removed']} duplicates removed), secondary {len(ms):,} rows, daily {len(dd)} rows")
    # ---- timestamp-convention test of the secondary file against 5paisa (before anything is built from it)
    _d, _m, summ_pre = D4.overlap_audit(m5, ms, "5paisa", "secondary", date(2019, 3, 1), date(2019, 12, 31))
    shift = summ_pre["timestamp_shift_test"]
    best = max(shift, key=lambda k: shift[k].get("share_close_equal_within_0_05", 0) if shift[k]["bars"] else -1)
    print(f"  secondary timestamp shift test: {shift} -> best shift {best}")
    if best != "0":
        raise SystemExit(f"{ix.name}: the secondary file's timestamps look shifted by {best} minute(s) against 5paisa; refusing to continue without review")
    D5.write_processed(ix, ix.src_5p_min, m5, None, i5)
    D5.write_processed(ix, ix.src_sec_min, ms, None, isec)
    D5.write_processed(ix, ix.src_5p_daily, None, dd, idl)
    # ---- closing-auction evidence from this index's own data (never assumed from another exchange or index)
    cas = {"5paisa": closing_auction_evidence(m5), "secondary": {"note": "the secondary files end before 2026-08 for SENSEX; BANKNIFTY ends 2026-04-22"}}
    (out / "closing_auction_evidence.json").write_text(json.dumps(cas, indent=1))
    print("  closing-auction pattern:", cas["5paisa"])
    # ---- derived calendar
    sec_cov = [(max(date(2017, 1, 1), ms["timestamp"].dt.date.min()), ms["timestamp"].dt.date.max())]
    cover = {ix.src_5p_min: COVER_5P, ix.src_sec_min: sec_cov}
    cal, cmeta = D5.derive_calendar_index(dd, {ix.src_5p_min: m5, ix.src_sec_min: ms}, START, END, cover)
    D4.calendar_to_json(cal, cmeta, ix.calendar_file)
    ev = cas["5paisa"]
    applies = ev["frozen_pattern_before"] == 0 and ev["sessions_from_2026_08_03"] > 0 and ev["frozen_pattern_from"] >= 0.9 * ev["sessions_from_2026_08_03"]
    cj = json.loads(ix.calendar_file.read_text())
    cj["index"] = ix.name
    cj["exchange"] = ix.exchange_label
    if applies:
        # the loader recognises this id; the entry is written because THIS index's data show the pattern (see closing_auction_evidence.json), not because NSE introduced it for NIFTY
        cj["market_structure_changes"] = [{"id": "NSE_CLOSING_AUCTION_SESSION", "effective_date": str(CAS_FIRST), "index_frozen_window_hhmm": ["15:15", "15:29"],
                                           "description": f"closing-auction freeze observed in the {ix.name} one-minute data from {CAS_FIRST}: {ev['frozen_pattern_from']} of {ev['sessions_from_2026_08_03']} sessions show 15:16..15:26 flat; {ev['frozen_pattern_before']} of {ev['sessions_before_2026_08_03']} before",
                                           "evidence": ["data: reports/phase5/" + ix.key + "/data/closing_auction_evidence.json", "NIFTY evidence calendar data/metadata/nse_calendar_2025_2026.json (NSE regime start 2026-08-03; circular not read directly)"]}]
    cj["closing_auction_applied"] = bool(applies)
    ix.calendar_file.write_text(json.dumps(cj, indent=1))
    print(f"  derived calendar: {cmeta['n_holidays']} holidays, {cmeta['n_special']} special sessions, {len(cmeta['gaps_between_series'])} vendor gaps; closing auction applied: {applies}")
    from nifty_trading.data.market_calendar import load_market_calendar
    cal = load_market_calendar(ix.calendar_file)
    per_year: dict[int, int] = {}
    for h in cal.holidays:
        per_year[h.year] = per_year.get(h.year, 0) + 1
    (out / "derived_calendar_summary.json").write_text(json.dumps({"holidays_per_year": per_year, "special_sessions": {str(d): {"name": e.name, "evaluable": e.evaluable_by_strategies} for d, e in sorted(cal.special_sessions.items())},
                                                                  "gaps_between_series": cmeta["gaps_between_series"], "opening_bar_defects": cmeta["opening_bar_defects"], "closing_auction_applied": applies}, indent=1))
    # ---- per-session quality and coverage for every run window
    quality_all, cover_rows = [], []
    for wid, spec in F5.specs_for(ix.name).items():
        src = F5.minute_source_id(ix, spec)
        minutes = m5 if spec.minute_source == "5paisa" else ms
        q = D4.session_quality_table(minutes, dd, cal, src, spec.start, spec.end)
        q.insert(0, "window", wid)
        quality_all.append(q)
        row = D4.coverage_table(q.drop(columns=["window"]), cal, dd, spec.start, spec.end, spec.label)
        row.update({"window_id": wid, "index": ix.name, "minute_source": src, "daily_source": ix.src_5p_daily})
        wu = minutes[(minutes["timestamp"].dt.date < spec.start) & (minutes["timestamp"].dt.date >= date.fromordinal(spec.start.toordinal() - 45))]
        row["warmup_sessions_same_source"] = int(wu["timestamp"].dt.date.nunique())
        row["daily_bars_before_start"] = int((dd["date"] < spec.start).sum())
        cover_rows.append(row)
        print(f"  {wid}: expected {row['expected_sessions']}, in source {row['sessions_in_source']}, usable {row['usable_sessions']}, excluded {row['excluded_sessions']}, warm-up sessions {row['warmup_sessions_same_source']}")
    pd.concat(quality_all, ignore_index=True).to_csv(out / "session_quality_all_windows.csv", index=False)
    pd.DataFrame(cover_rows).to_csv(out / "historical_coverage_by_window.csv", index=False)
    # ---- vendor overlap audits (5paisa vs secondary), regular window 09:15..15:29
    sec_end = ms["timestamp"].dt.date.max()
    day_all, mon_all, summaries = [], [], {}
    for label, lo, hi in (("2019-03..2019-12", date(2019, 3, 1), date(2019, 12, 31)), (f"2022-08..{min(sec_end, date(2026, 8, 31))}", date(2022, 8, 1), min(sec_end, date(2026, 8, 31)))):
        day, mon, summ = D4.overlap_audit(m5, ms, "5paisa", "secondary", lo, hi)
        day.insert(0, "overlap", label)
        mon.insert(0, "overlap", label)
        day_all.append(day)
        mon_all.append(mon)
        summaries[label] = summ
        print(f"  overlap {label}: dates both {summ['dates_in_both']} (5p-only {len(summ['dates_only_a'])}, secondary-only {len(summ['dates_only_b'])}); bars {summ['bars_compared']:,}; exact {summ['share_exact_all_fields']}; close within 0.05: {summ['share_close_within_0_05']}; max diff {summ['max_abs_close_diff']}")
    pd.concat(day_all, ignore_index=True).to_csv(out / "vendor_overlap_by_day.csv", index=False)
    pd.concat(mon_all, ignore_index=True).to_csv(out / "vendor_overlap_by_month.csv", index=False)
    (out / "vendor_overlap_summary.json").write_text(json.dumps(summaries, indent=1, default=str))
    prov = {"built_utc": pd.Timestamp.now("UTC").isoformat(), "index": ix.name, "five_paisa_minutes": {k: v for k, v in i5.items() if k != "raw_files"}, "five_paisa_minutes_raw_files": i5["raw_files"],
            "secondary_minutes": {k: v for k, v in isec.items() if k != "raw_files"}, "secondary_minutes_raw_files": isec["raw_files"], "five_paisa_daily": {k: v for k, v in idl.items() if k != "raw_files"},
            "five_paisa_daily_raw_files": idl["raw_files"], "processed_manifests": {sid: f"data/processed/{ix.key}/{sid}/source_manifest.json" for sid in (ix.src_5p_min, ix.src_sec_min, ix.src_5p_daily)},
            "calendar": str(ix.calendar_file.relative_to(ROOT)), "secondary_timestamp_shift_test": shift}
    (out / "data_provenance_build.json").write_text(json.dumps(prov, indent=1, default=str))
    return prov


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--index", choices=sorted(D5.INDEXES) + ["ALL"], default="ALL")
    a = ap.parse_args()
    for name, ix in D5.INDEXES.items():
        if a.index in ("ALL", name):
            build(ix)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
