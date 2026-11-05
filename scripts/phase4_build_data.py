"""Phase 4: build the processed data namespaces, the DERIVED multi-year calendar, the per-session data-quality tables, the coverage table and the vendor-overlap audits.

Inputs (read-only): data/raw/phase4_5paisa/ (provider responses), data/raw/phase4_technovusin/<commit>/ (secondary source), the Phase 1 dataset (data/processed, only for the 2025-26 overlap audit and the
calendar-method validation). Outputs: data/phase4/processed/<source id>/, data/phase4/calendar/phase4_calendar_derived.json, and reports/phase4/data/*.csv|json. Nothing in data/processed or any earlier report is written.

Run: .venv/bin/python scripts/phase4_build_data.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.sessions import load_daily_official, load_one_minute  # noqa: E402
from nifty_trading.research import phase4_data as D  # noqa: E402

OUT = ROOT / "reports" / "phase4" / "data"
START, END = date(2017, 1, 1), date(2025, 8, 31)
# the date ranges each minute source was retrieved for (a source is only expected to have rows inside them)
COVER = {D.SRC_5P_MIN: [(date(2019, 3, 1), date(2019, 12, 31)), (date(2022, 8, 1), date(2025, 8, 31))], D.SRC_TV_MIN: [(date(2017, 4, 3), date(2019, 12, 31)), (date(2022, 1, 1), date(2025, 12, 31))]}  # only the years actually retrieved (no 2020 / 2021 files)
# windows validated before any backtest (id, label, start, end, minute source)
WINDOWS = [("B", "Window B 2022-09-01..2025-08-31", date(2022, 9, 1), date(2025, 8, 31), D.SRC_5P_MIN), ("B_TV", "Window B 2022-09-01..2025-08-31 (secondary vendor)", date(2022, 9, 1), date(2025, 8, 31), D.SRC_TV_MIN),
           ("C", "Window C 2018-01-01..2018-12-31", date(2018, 1, 1), date(2018, 12, 31), D.SRC_TV_MIN), ("D_5P", "Window D 2019 (5paisa part 2019-03-01..2019-12-31)", date(2019, 3, 1), date(2019, 12, 31), D.SRC_5P_MIN),
           ("D_TV", "Window D 2019-01-01..2019-12-31 (secondary vendor)", date(2019, 1, 1), date(2019, 12, 31), D.SRC_TV_MIN)]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    m5, i5 = D.load_5p_minutes()
    mt, it = D.load_tv_minutes()
    dd, idl = D.load_5p_daily()
    print(f"5paisa minutes {len(m5):,} rows ({i5['duplicate_rows_removed']} duplicate rows removed on {i5['duplicate_dates']}); secondary {len(mt):,} rows; daily {len(dd)} rows")
    D.write_processed(D.SRC_5P_MIN, m5, None, i5)
    D.write_processed(D.SRC_TV_MIN, mt, None, it)
    D.write_processed(D.SRC_5P_DAILY, None, dd, idl)
    # ------------------------------------------------------------------ derived calendar + method validation against the evidence-tier 2025-26 calendar
    cal, cmeta = D.derive_calendar(dd, {D.SRC_5P_MIN: m5, D.SRC_TV_MIN: mt}, START, END, COVER)
    D.calendar_to_json(cal, cmeta, D.CAL_DIR / "phase4_calendar_derived.json")
    p1_daily = load_daily_official()
    p1_min = load_one_minute()
    cal_p1, _ = D.derive_calendar(p1_daily, {"PHASE1": p1_min}, date(2025, 9, 1), date(2026, 8, 31), {"PHASE1": [(date(2025, 9, 1), date(2026, 8, 31))]})
    method = D.validate_calendar_method(cal_p1)
    (OUT / "calendar_method_validation.json").write_text(json.dumps(method, indent=1))
    print("calendar method vs evidence calendar 2025-26: identical =", method["identical"], method["holidays_only_derived"], method["holidays_only_evidence"])
    # sanity: holidays per year
    per_year = {}
    for h in cal.holidays:
        per_year[h.year] = per_year.get(h.year, 0) + 1
    (OUT / "derived_calendar_summary.json").write_text(json.dumps({"holidays_per_year": per_year, "special_sessions": {str(d): {"name": e.name, "evaluable": e.evaluable_by_strategies} for d, e in sorted(cal.special_sessions.items())},
                                                                  "gaps_between_series": cmeta["gaps_between_series"]}, indent=1))
    # ------------------------------------------------------------------ per-session quality + coverage
    cover_rows, quality_all = [], []
    for wid, label, s, e, src in WINDOWS:
        minutes = m5 if src == D.SRC_5P_MIN else mt
        q = D.session_quality_table(minutes, dd, cal, src, s, e)
        q.insert(0, "window", wid)
        quality_all.append(q)
        row = D.coverage_table(q.drop(columns=["window"]), cal, dd, s, e, label)
        row.update({"window_id": wid, "minute_source": src, "daily_source": D.SRC_5P_DAILY})
        # warm-up availability in the same minute source (45 calendar days before the start)
        wu = minutes[(minutes["timestamp"].dt.date < s) & (minutes["timestamp"].dt.date >= date.fromordinal(s.toordinal() - 45))]
        row["warmup_sessions_same_source"] = int(wu["timestamp"].dt.date.nunique())
        row["daily_bars_before_start"] = int((dd["date"] < s).sum())
        cover_rows.append(row)
        print(f"{wid}: expected {row['expected_sessions']} sessions, in source {row['sessions_in_source']}, usable {row['usable_sessions']}, excluded {row['excluded_sessions']}, warmup sessions {row['warmup_sessions_same_source']}")
    pd.concat(quality_all, ignore_index=True).to_csv(OUT / "session_quality_all_windows.csv", index=False)
    pd.DataFrame(cover_rows).to_csv(OUT / "historical_coverage_by_window.csv", index=False)
    # ------------------------------------------------------------------ vendor overlap audits (secondary vs 5paisa), regular window 09:15..15:29
    day_all, mon_all, summaries = [], [], {}
    for label, a, b, lo, hi in (("2019-03..2019-12", m5, mt, date(2019, 3, 1), date(2019, 12, 31)), ("2022-08..2025-08", m5, mt, date(2022, 8, 1), date(2025, 8, 31))):
        day, mon, summ = D.overlap_audit(a, b, "5paisa", "secondary", lo, hi)
        day.insert(0, "overlap", label)
        mon.insert(0, "overlap", label)
        day_all.append(day)
        mon_all.append(mon)
        summaries[label] = summ
    # Phase 1 dataset (5paisa, 2025-09..2026-08) against the secondary source's 2025/2026 files
    day, mon, summ = D.overlap_audit(p1_min, mt, "5paisa (Phase 1 dataset)", "secondary", date(2025, 9, 1), date(2026, 8, 31))
    day.insert(0, "overlap", "2025-09..2026-08")
    mon.insert(0, "overlap", "2025-09..2026-08")
    day_all.append(day)
    mon_all.append(mon)
    summaries["2025-09..2026-08"] = summ
    pd.concat(day_all, ignore_index=True).to_csv(OUT / "vendor_overlap_by_day.csv", index=False)
    pd.concat(mon_all, ignore_index=True).to_csv(OUT / "vendor_overlap_by_month.csv", index=False)
    (OUT / "vendor_overlap_summary.json").write_text(json.dumps(summaries, indent=1, default=str))
    for k, v in summaries.items():
        print(f"overlap {k}: dates both {v['dates_in_both']} (5p-only {len(v['dates_only_a'])}, secondary-only {len(v['dates_only_b'])}); bars {v['bars_compared']:,}; exact {v['share_exact_all_fields']}; close within 0.05: {v['share_close_within_0_05']}; max diff {v['max_abs_close_diff']}")
    # ------------------------------------------------------------------ daily (5paisa) vs minute last close, per source, as a reconciliation of the official-close convention
    prov = {"built_utc": pd.Timestamp.utcnow().isoformat(), "five_paisa_minutes": {k: v for k, v in i5.items() if k != "raw_files"}, "five_paisa_minutes_raw_files": i5["raw_files"],
            "secondary_minutes": {k: v for k, v in it.items() if k != "raw_files"}, "secondary_minutes_raw_files": it["raw_files"], "five_paisa_daily": {k: v for k, v in idl.items() if k != "raw_files"},
            "five_paisa_daily_raw_files": idl["raw_files"], "processed_manifests": {sid: f"data/phase4/processed/{sid}/source_manifest.json" for sid in (D.SRC_5P_MIN, D.SRC_TV_MIN, D.SRC_5P_DAILY)},
            "calendar": "data/phase4/calendar/phase4_calendar_derived.json"}
    (OUT / "data_provenance_build.json").write_text(json.dumps(prov, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
