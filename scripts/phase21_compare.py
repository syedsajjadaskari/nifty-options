"""Phase 2.1: evidence for the August-2026 investigation. Read-only; writes reports/phase21/redownload_comparison.json (+ .md).

Compares, on the raw re-downloads saved by ``phase21_redownload.py``:
  1. stored Phase 1 data vs fresh data (target month, control month, a second control month)
  2. the vendor's own 5-minute candles vs our aggregation of the stored 1-minute rows (whole year)
  3. the vendor's daily candles vs minute-derived values (official-close behaviour before/after 2026-08-03)
  4. the frozen-window pattern (start/end times, catch-up bar, post-close rows) incl. diagnostic months outside the analysis period
  5. externally published closing values vs the vendor daily close
  6. integrity of the untouched archive of the original Phase 1 data
"""

from __future__ import annotations

import glob
import hashlib
import json
import sys
from datetime import date, datetime, time, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from nifty_trading.data.sessions import (  # noqa: E402
    build_session_contexts,
    load_daily_official,
    load_one_minute,
    load_warmup_one_minute,
    stale_row_mask,
)

OUT = ROOT / "reports" / "phase21"
IST = "Asia/Kolkata"

# externally published official closes (independent secondary sources, retrieved 2026-11-01 by web search)
EXTERNAL_CLOSES = {
    date(2026, 7, 31): (24383.60, "Oquilia (24,774.30 - 390.70 on 2026-08-03)"),
    date(2026, 8, 3): (24774.30, "Oquilia market pulse 2026-08-03; IIFL note"),
    date(2026, 8, 4): (24614.90, "Trendlyne 2026-08-04 15:31; Oquilia 2026-08-05 minus 9.75"),
    date(2026, 1, 27): (25175.40, "Oquilia 2026-01-27; Upstox"),
    date(2026, 3, 10): (24261.60, "Oquilia 2026-03-10; Informist"),
    date(2026, 3, 19): (23002.15, "Oquilia 2026-03-19; Informist (2026 closing low); Arihant Capital note"),
    date(2026, 3, 25): (23306.45, "DSIJ closing bell 2026-03-25 (as reported in search results)"),
    date(2026, 3, 30): (22331.40, "Informist monthly review (March close)"),
    date(2026, 5, 27): (23907.15, "Business Today / Dsij closing bell 2026-05-27"),
}


def raw_dirs() -> list[Path]:
    return sorted(Path(p).parent for p in glob.glob(str(ROOT / "data" / "raw" / "redownload_*" / "request_log.json")))


def find_raw(label: str) -> Path:
    for d in reversed(raw_dirs()):
        f = d / f"{label}.parquet"
        if f.exists():
            return f
    raise FileNotFoundError(label)


def norm(df: pd.DataFrame) -> pd.DataFrame:
    df = df.rename(columns={"Datetime": "timestamp", "Open": "open", "High": "high", "Low": "low", "Close": "close", "Volume": "volume"}).copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    if df.timestamp.dt.tz is None:
        df["timestamp"] = df.timestamp.dt.tz_localize(IST)
    return df.sort_values("timestamp").reset_index(drop=True)


def main() -> None:
    res: dict = {"generated_utc": datetime.now(timezone.utc).isoformat()}
    stored = load_one_minute()
    # ---- 1. stored vs fresh
    comp = {}
    for label, (a, b) in {"aug_1m": ("2026-08-01", "2026-09-01"), "jul_1m_control": ("2026-07-01", "2026-08-01"), "diag_jun_1m": ("2026-06-01", "2026-07-01")}.items():
        f = norm(pd.read_parquet(find_raw(label)))
        s = stored[(stored.timestamp >= pd.Timestamp(a, tz=IST)) & (stored.timestamp < pd.Timestamp(b, tz=IST))].reset_index(drop=True)
        m = s.merge(f, on="timestamp", how="outer", suffixes=("_s", "_f"), indicator=True)
        both = m[m._merge == "both"]
        diff = np.zeros(len(both), bool)
        for c in ("open", "high", "low", "close"):
            diff |= ((both[c + "_s"] - both[c + "_f"]).abs() > 1e-9).to_numpy()
        comp[label] = {"stored_rows": len(s), "fresh_rows": len(f), "only_stored": int((m._merge == "left_only").sum()),
                       "only_fresh": int((m._merge == "right_only").sum()), "rows_with_ohlc_difference": int(diff.sum())}
    res["stored_vs_fresh_1m"] = comp
    # ---- 2. vendor 5m vs our aggregation
    ctxs, infos = build_session_contexts(stored, daily_df=load_daily_official(), warmup_1m=load_warmup_one_minute())
    mine = pd.concat([c.candles for c in ctxs.values()], ignore_index=True)[["bar_start", "open", "high", "low", "close"]].rename(columns={"bar_start": "timestamp"})
    files = glob.glob(str(ROOT / "data/raw/redownload_*/m5_*.parquet")) + glob.glob(str(ROOT / "data/raw/redownload_*/aug_5m.parquet"))
    v = pd.concat([norm(pd.read_parquet(f)) for f in files], ignore_index=True).drop_duplicates("timestamp")
    m = mine.merge(v, on="timestamp", how="left", suffixes=("", "_v"), indicator=True)
    both = m[m._merge == "both"]
    d5 = np.zeros(len(both), bool)
    for c in ("open", "high", "low", "close"):
        d5 |= ((both[c] - both[c + "_v"]).abs() > 1e-6).to_numpy()
    extra = v.merge(mine[["timestamp"]], on="timestamp", how="left", indicator=True)
    extra = extra[extra._merge == "left_only"]
    res["vendor_5m_vs_our_aggregation"] = {
        "our_candles": len(mine), "found_in_vendor_5m": int(len(both)), "candles_differing": int(d5.sum()),
        "vendor_candles_not_in_ours": len(extra), "vendor_only_by_time": extra.timestamp.dt.strftime("%H:%M").value_counts().head(8).to_dict()}
    # ---- 3. vendor daily vs minute data
    daily = load_daily_official()
    st = stored.assign(d=stored.timestamp.dt.date, tm=stored.timestamp.dt.time)
    rows = []
    for d, g in st.groupby("d"):
        g = g.sort_values("timestamp")
        main = g[g.tm <= time(15, 30)]
        rows.append({"d": d, "stub": float(main.close.iloc[-1]), "h": float(g.high.max()), "l": float(g.low.min())})
    x = pd.DataFrame(rows).merge(daily.rename(columns={"date": "d", "close": "vc", "high": "vh", "low": "vl"})[["d", "vc", "vh", "vl"]], on="d")
    x["dc"] = (x.vc - x.stub).abs()
    pre, post = x[x.d < date(2026, 8, 3)], x[x.d >= date(2026, 8, 3)]
    res["vendor_daily_vs_minute"] = {
        "sessions": len(x),
        "before_2026_08_03": {"n": len(pre), "median_abs_close_diff_vs_1530_print": round(float(pre.dc.median()), 2), "p90": round(float(pre.dc.quantile(.9)), 2),
                              "max": round(float(pre.dc.max()), 2), "sessions_where_close_equals_1530_print": int((pre.dc < 0.005).sum())},
        "from_2026_08_03": {"n": len(post), "sessions_where_close_equals_1530_print": int((post.dc < 0.005).sum()), "max_abs_diff": round(float(post.dc.max()), 4)},
        "note": "before the auction regime the official close differs from the last minute tick; from 2026-08-03 the 15:30 print IS the official close"}
    # ---- 4. frozen-window pattern, incl. diagnostic months
    def pattern(df: pd.DataFrame) -> dict:
        w = df.assign(d=df.timestamp.dt.date, tm=df.timestamp.dt.strftime("%H:%M"))
        w = w[(w.tm >= "09:15") & (w.tm <= "15:29")].sort_values("timestamp")
        starts, ends, n, steps = [], [], 0, []
        for _d, g in w.groupby("d"):
            m = stale_row_mask(g)
            if m.any():
                n += 1
                r = g[m]
                starts.append(r.tm.min())
                ends.append(r.tm.max())
                after = g[g.timestamp > r.timestamp.max()]
                if len(after):
                    steps.append(float(after.iloc[0].high - after.iloc[0].low))
        return {"sessions": int(w.d.nunique()), "sessions_with_frozen_rows": n, "freeze_start": dict(pd.Series(starts).value_counts()),
                "freeze_end": dict(pd.Series(ends).value_counts()), "median_catch_up_bar_range": round(float(np.median(steps)), 1) if steps else None}
    res["frozen_window_pattern"] = {
        "analysis_year_before_2026_08_03": pattern(stored[stored.timestamp < pd.Timestamp("2026-08-03", tz=IST)]),
        "analysis_year_from_2026_08_03": pattern(stored[stored.timestamp >= pd.Timestamp("2026-08-03", tz=IST)]),
        "diagnostic_2026_06": pattern(norm(pd.read_parquet(find_raw("diag_jun_1m")))),
        "diagnostic_2026_09_outside_analysis_period": pattern(norm(pd.read_parquet(find_raw("diag_sep_1m")))),
        "diagnostic_2026_10_outside_analysis_period": pattern(norm(pd.read_parquet(find_raw("diag_oct_1m")))),
        "download_date": "2026-11-01", "days_between_first_frozen_session_and_download": (date(2026, 11, 1) - date(2026, 8, 3)).days}
    post_close = st[(st.tm > time(15, 30)) & (st.d.isin([date(2026, 8, 3), date(2026, 8, 4)]))].groupby("d").agg(rows=("close", "size"), distinct_closes=("close", "nunique"))
    res["rows_after_1530"] = {"2026-08-03_and_08-04": {str(k): v for k, v in post_close.to_dict("index").items()},
                              "2026-03-10": {"rows": int(len(st[(st.d == date(2026, 3, 10)) & (st.tm > time(15, 30))])),
                                             "meaning": "15:31 prints the official close 24,261.60 (= vendor daily close = published close) and holds it"}}
    # ---- 5. external closes
    ext = []
    for d, (val, src) in EXTERNAL_CLOSES.items():
        r = x[x.d == d].iloc[0]
        ext.append({"date": str(d), "published_close": val, "source": src, "vendor_daily_close": float(r.vc), "matches": bool(abs(r.vc - val) < 0.005),
                    "minute_1530_print": float(r.stub), "stub_matches": bool(abs(r.stub - val) < 0.005)})
    res["external_closes"] = {"checked": len(ext), "vendor_daily_matches": sum(e["matches"] for e in ext), "minute_1530_print_matches": sum(e["stub_matches"] for e in ext), "detail": ext}
    # ---- 6. archive integrity
    arch = ROOT / "data" / "archive" / "phase1_original_20261101"
    bad = []
    for line in (arch / "SHA256SUMS").read_text().splitlines():
        h, rel = line.split(maxsplit=1)
        if rel.startswith("./nifty50/") and hashlib.sha256((ROOT / "data" / "processed" / rel[2:]).read_bytes()).hexdigest() != h:
            bad.append(rel)
    res["original_data_unchanged"] = {"archive": str(arch.relative_to(ROOT)), "partition_files_differing_from_archive": bad,
                                      "candles_replaced_in_phase_2_1": 0}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "redownload_comparison.json").write_text(json.dumps(res, indent=2, default=str))
    md = ["# Re-download comparison (generated by scripts/phase21_compare.py)\n", "```json", json.dumps(res, indent=2, default=str)[:60000], "```\n"]
    (OUT / "redownload_comparison.md").write_text("\n".join(md))
    print(json.dumps({"stored_vs_fresh": comp, "vendor_5m": res["vendor_5m_vs_our_aggregation"]["candles_differing"],
                      "external_matches": f"{res['external_closes']['vendor_daily_matches']}/{res['external_closes']['checked']}",
                      "archive_diff": bad}, default=str))


if __name__ == "__main__":
    main()
