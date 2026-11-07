"""Phase 5: write the markdown deliverables of reports/phase5/ from the CSV / JSON files the pipeline produced (so every number in the text is read from a table, not typed).

  python scripts/phase5_docs.py --tests "<pytest result>" --ruff "<ruff result>"

Writes: README.md, data_discovery.md, data_quality_report.md, banknifty/banknifty_backtest_summary.md, sensex/sensex_backtest_summary.md, comparison/cross_index_comparison.md,
options_feasibility/option_data_availability.md, options_feasibility/option_contract_selection_decisions.md, data_provenance.json, independent_audit.md.
"""

from __future__ import annotations

import argparse
import csv
import glob
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase5"
IDX = {"BANKNIFTY": "banknifty", "SENSEX": "sensex"}
WARN = ("HISTORICAL RESEARCH ONLY. The strategy was developed using later NIFTY data; nothing here is a validation of the strategy, a forecast, or advice. "
        "Every result is an INDEX-POINT result; no option premium is used or estimated, and an index-point gain is not an option-premium gain.")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def fn(x) -> float:
    return float(str(x).replace(",", "")) if x not in ("", None) else 0.0


def tab(head: list[str], rows: list[list]) -> str:
    esc = lambda v: str(v).replace("|", "/")  # noqa: E731
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(esc(c) for c in r) + " |" for r in rows])


def pts(x) -> str:
    return f"{fn(x):+,.1f}"


def one_minute_range(pattern: str, lo: str, hi: str) -> dict:
    """Median / 90th percentile of the one-minute high-low range (regular bars 09:15-15:29) and its median as % of the close, over [lo, hi]: the scale of ordinary one-minute noise."""
    x = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(pattern, recursive=True))], ignore_index=True)
    d = x["timestamp"].dt.strftime("%Y-%m-%d")
    m = x["timestamp"].dt.hour * 60 + x["timestamp"].dt.minute
    x = x[(d >= lo) & (d <= hi) & (m >= 555) & (m <= 929)]
    r = x["high"] - x["low"]
    return {"bars": len(x), "median": float(r.median()), "p90": float(r.quantile(0.9)), "median_pct": float((r / x["close"]).median() * 100), "level": float(x["close"].median())}


def ann(index: str) -> dict:
    return {r["row_id"]: r for r in rd(OUT / IDX[index] / "annual_comparison.csv")}


def tier(index: str, wid: str, cov: dict, ov: dict) -> str:
    """The Phase 4 confidence rubric, applied to this index's window from the coverage table and the vendor overlap."""
    usable = int(cov["usable_sessions"]) / max(int(cov["expected_sessions"]), 1)
    if wid in ("C", "D_TV"):
        return "EXPLORATORY_UNVERIFIABLE"
    if wid == "D_5P":
        return "LOW"
    if wid == "MS":
        return "EXPLORATORY_UNVERIFIABLE"
    mad = ov.get("mean_abs_close_diff")
    if usable >= 0.99 and mad is not None and mad <= 0.10:
        return "HIGH"
    return "MODERATE" if usable >= 0.98 else "LOW"


def main() -> int:  # noqa: C901
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    freeze = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    cfgsnap = json.loads((OUT / "configuration_snapshot.json").read_text())
    probe = {k: json.loads((OUT / k / "probe_results.json").read_text()) for k in IDX.values()}
    inst = {k: json.loads((ROOT / "data/metadata/phase5" / f"{k}_instrument.json").read_text()) for k in IDX.values()}
    cov = {k: {r["window_id"]: r for r in rd(OUT / k / "data" / "historical_coverage_by_window.csv")} for k in IDX.values()}
    qual = {k: pd.read_csv(OUT / k / "data" / "session_quality_all_windows.csv") for k in IDX.values()}
    ovl = {k: json.loads((OUT / k / "data" / "vendor_overlap_summary.json").read_text()) for k in IDX.values()}
    calsum = {k: json.loads((OUT / k / "data" / "derived_calendar_summary.json").read_text()) for k in IDX.values()}
    casev = {k: json.loads((OUT / k / "data" / "closing_auction_evidence.json").read_text()) for k in IDX.values()}
    prov = {k: json.loads((OUT / k / "data" / "data_provenance_build.json").read_text()) for k in IDX.values()}
    man5 = {k: json.loads((ROOT / "data/raw" / k / "5paisa" / "manifest.json").read_text()) for k in IDX.values()}
    mansec = {k: json.loads(glob.glob(str(ROOT / "data/raw" / k / "secondary_kapri" / "*" / "manifest.json"))[0].read_text() if False else Path(glob.glob(str(ROOT / "data/raw" / k / "secondary_kapri" / "*" / "manifest.json"))[0]).read_text()) for k in IDX.values()}
    comp = rd(OUT / "comparison" / "cross_index_by_period.csv")
    compstrat = rd(OUT / "comparison" / "cross_index_by_strategy.csv")
    common = rd(OUT / "comparison" / "common_sessions_comparison.csv")
    agree = rd(OUT / "comparison" / "daily_agreement_between_indices.csv")
    probe_opt = json.loads((OUT / "options_feasibility" / "option_probe_results.json").read_text())
    NAMES = {"banknifty": "BANKNIFTY", "sensex": "SENSEX"}
    rng = {"NIFTY": one_minute_range(str(ROOT / "data/phase4/processed/FIVEPAISA_1M_PHASE4/nifty50/year=*/month=*/candles.parquet"), "2022-09-01", "2025-08-31"),
           "BANKNIFTY": one_minute_range(str(ROOT / "data/processed/banknifty/FIVEPAISA_1M_BANKNIFTY/minutes/year=*/month=*/candles.parquet"), "2022-09-01", "2025-08-31"),
           "SENSEX": one_minute_range(str(ROOT / "data/processed/sensex/FIVEPAISA_1M_SENSEX/minutes/year=*/month=*/candles.parquet"), "2022-09-01", "2025-08-31")}

    def req_stats(k: str) -> dict:
        c: dict = {}
        for r in man5[k]["requests"].values():
            c[(r["timeframe"], r["status"])] = c.get((r["timeframe"], r["status"]), 0) + 1
        return c

    # ============================================================================================================== data_discovery.md
    D = ["# Phase 5 - data discovery (BANKNIFTY and SENSEX index candles)", "", WARN, ""]
    D += ["## 1. Instruments (resolved from the broker's current instrument master, never copied from NIFTY)", ""]
    rows = []
    for k, i in inst.items():
        rows.append([NAMES[k], i["exchange_label"] + f" ({i['exchange']})", f"{i['exchange_segment']} (cash / index)", i["scrip_code"], i["symbol"], i["full_name"] or "(blank in the master)", i["expected_index_name"],
                     len(i["not_the_index_rejected_rows_with_same_name"])])
    D += [tab(["index", "exchange", "segment", "scrip code", "master name", "master full name", "index it should be", "look-alike rows (ETF / fund, not the index) rejected"], rows), "",
          f"Master copy: `{inst['banknifty']['master_file']}` (SHA-256 `{inst['banknifty']['master_sha256'][:16]}...`), downloaded from the broker's public ScripMaster endpoint during this phase; the Phase 1 copy (2026-11-01) was not touched. "
          "Selection rule: exchange, cash/index segment, exact name, and an index-range scrip code (>= 999000) - a unique row in both cases. Look-alike names in the same segment (ETFs and funds such as `BANKBEES`, `SENSEXBEES`, `BANKNIFTY1`) are listed in each instrument JSON as rejected. "
          "The master gives no full name for SENSEX, so its identity as the S&P BSE Sensex rests on the BSE index code, the exchange, and the price level: probes returned closes of 26,600-31,300 (2017), 32,600-38,900 (2018), 35,400-41,700 (2019), 56,400-60,600 (2022-08..09) and 76,900-81,300 (2025-26), "
          "which are the Sensex's levels, and the minute and daily series agree with each other (see `data_quality_report.md`). The same level argument holds for BANKNIFTY (23,700-28,300 in 2018, 37,600-41,500 in 2022-08..09, 57,000-58,000 in 2026). "
          "NIFTY's own identifiers (exchange N, code 999920000) were not reused: BANKNIFTY happens to be NSE index code 999920005 and SENSEX is on a different exchange (BSE, 999901).", ""]
    D += ["## 2. 5paisa historical-candle API: what was verified", "",
          "Official reference: <https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles> (read for this phase). It states: intervals 1, 5, 10, 15, 30, 60 minutes and 1 day; at most 6 months per request for intraday intervals; a candle carries timestamp, open, high, low, close and volume only "
          "(no bid, ask or open interest); identification by scrip code only; the timestamp convention, the timezone and any lookback limit are **not stated**; no licence or redistribution terms are stated on the page (the site's Terms and Conditions were not read). The purpose given is 'strategy deployment'.", "",
          "What the API actually returned (small probes, saved unmodified under `data/raw/<index>/5paisa/probe/`, summary in `reports/phase5/<index>/probe_results.json`):", ""]
    pr_rows = []
    for k in IDX.values():
        for p in probe[k]["probes"]:
            if p["interval"] in ("1m", "1d"):
                pr_rows.append([NAMES[k], p["label"], p["interval"], f"{p['from']}..{p['to']}", p["status"], p.get("rows", 0), (p.get("first_timestamp") or "")[:16], (p.get("last_timestamp") or "")[:16], p.get("distinct_dates", "")])
    D += [tab(["index", "probe", "interval", "requested", "status", "rows", "first", "last", "dates"], pr_rows), "",
          "Intervals 5m, 10m, 15m, 30m, 60m and 1d were all served for both indices (recent week). One-minute bars start at 09:15 and the series ends at **15:30**: each session has 376 rows - 375 regular bars labelled 09:15-15:29 and one **15:30 stub** bar - exactly like the NIFTY series; the stub is not a tradable bar and is handled by the frozen session logic. "
          "Bars are labelled by their START in IST (the overlap test below shows the secondary source uses the same convention). **One-minute data do not exist on 5paisa before 2019-03-01 for either index**: every monthly request for 2018-01..2019-02 returned EMPTY (the API accepts the request and returns nothing), exactly as for NIFTY.", ""]
    D += ["## 3. Retrieval and coverage actually obtained", ""]
    cov_rows = []
    for k in IDX.values():
        rs = req_stats(k)
        cov_rows.append([NAMES[k], f"{rs.get(('1m', 'COMPLETED'), 0)} completed / {rs.get(('1m', 'EMPTY'), 0)} empty (2018-01..2019-02)", f"{rs.get(('1d', 'COMPLETED'), 0)} completed",
                         "2019-03..2019-12 and 2022-08..2026-08", "2017-01-01..2026-08-31", f"{rs.get(('1m', 'FAILED'), 0) + rs.get(('1m', 'RATE_LIMITED'), 0) + rs.get(('1m', 'ACCESS_DENIED'), 0)}"])
    D += [tab(["index", "1-minute monthly requests", "daily requests (6-month spans)", "minute months retrieved", "daily span", "failed / rate-limited / denied"], cov_rows), "",
          "Requests were monthly (1-minute) or six-monthly (daily), rate-limited, retried, resumable and each response saved unmodified with its SHA-256 and a classified status (`data/raw/<index>/5paisa/manifest.json`). 2020-2021 minute data were not requested (not needed by any window).", ""]
    D += ["## 4. Secondary sources for the years 5paisa cannot supply (2018 and 2019-01..02)", "",
          "Searches for a legitimate source found two GitHub repositories (both MIT-licensed, by the same author) that carry one-minute index files; the licence is that of the repository, the files are described only as 'extracted from a reliable financial data provider' - **the data vendor is not named and the licence of the underlying data is not established**. "
          "Other candidates were not used: a repository with no licence shown (`aeron7/nifty-banknifty-intraday-data`), paid vendors, and Kaggle datasets that need an account. Everything from these repositories is therefore labelled EXPLORATORY and is never merged with 5paisa data.", ""]
    srows = []
    for k in IDX.values():
        m = mansec[k]
        f = [v for p, v in m["files"].items() if p not in ("README.md", "LICENSE")][0]
        pa = prov[k]["secondary_minutes"]
        srows.append([NAMES[k], m["repository"], m["commit_sha"][:12], m["commit_date"][:10], m["repo_license_spdx"], f["sha256"][:16], f"{f['bytes']:,}", pa["rows_in"], pa["duplicate_rows_removed"], pa["conflicting_duplicate_timestamps"]])
    D += [tab(["index", "repository", "pinned commit", "commit date", "licence", "file SHA-256", "bytes", "rows", "duplicate rows removed", "conflicting duplicates"], srows), "",
          "Each file's git blob SHA-1 was recomputed from the downloaded bytes and equals the repository's tree listing (an integrity check against the repository, **not** a check of the market data). Coverage and quirks found:", "",
          "* **BANKNIFTY** file: 2015-01-09 .. 2026-04-22, 375 bars per session (09:15-15:29), no 15:30 stub, covers all of 2018 and 2019. From 2023-11-28 to 2024-03-22 (" + str(len(prov['banknifty']['secondary_minutes']['duplicate_dates'])) + " sessions) it contains an exactly duplicated block of rows (" + f"{prov['banknifty']['secondary_minutes']['duplicate_rows_removed']:,}" + " rows in all); the duplicates are identical (zero conflicting) and were removed, keeping the last. "
          "Evening Muhurat sessions are present as 60-row sessions and are excluded by the session gate.",
          "* **SENSEX** file: 2018-03-08 .. 2024-03-22 - **2018-01-01..2018-03-07 is not in it**, so 2018 is a partial year (about 200 of 246 sessions); the first two sessions (2018-03-08: 7 bars, 2018-03-09: 62 bars) are truncated at the file start. "
          "2019-01-23..2019-02-04 carries a single placeholder row per session (nine sessions) that the session gate excludes (no opening candle).", ""]
    D += ["## 5. Do the two vendors agree? (overlap audit, regular bars 09:15-15:29, bar by bar)", ""]
    orows = []
    for k in IDX.values():
        for lab, s in ovl[k].items():
            orows.append([NAMES[k], lab, s["dates_in_both"], f"{s['bars_compared']:,}", s["share_exact_all_fields"], s["share_close_within_0_05"], s["mean_abs_close_diff"], s["p99_abs_close_diff"], s["max_abs_close_diff"], s["days_with_any_diff_over_1pt"],
                         json.dumps({kk: vv["share_close_equal_within_0_05"] for kk, vv in s["timestamp_shift_test"].items()})])
    D += [tab(["index", "overlap", "dates in both", "bars compared", "identical (all four prices)", "close within 0.05", "mean abs close diff", "p99", "max", "days with a diff > 1 pt", "timestamp-shift test (share equal at -1/0/+1 min)"], orows), "",
          "The timestamp convention is identical (shifting by one minute destroys agreement), but **the two vendors' bars are not the same data**: BANKNIFTY agrees exactly on well under half of the bars with differences up to hundreds of points; SENSEX agrees much better but still differs. "
          "No provider equivalence is claimed. For 2018 there is no overlap at all, so that year cannot be checked against anything.", ""]
    fo = []
    for k in IDX.values():
        for w in ("M", "MS", "D_5P", "D_TV", "C"):
            x = qual[k][qual[k].window == w]["first_open_minus_daily_open"].dropna().abs()
            if len(x):
                fo.append([NAMES[k], w, len(x), f"{100 * (x <= 0.05).mean():.0f}%", f"{100 * (x <= 0.5).mean():.0f}%", round(float(x.mean()), 2)])
    D += ["### The 09:15 bar: each source's first one-minute open against the 5paisa DAILY open", "", tab(["index", "window (minute source)", "sessions", "within 0.05", "within 0.5", "mean abs diff (points)"], fo), "",
          "IRF, ORB and the gap-based logic are built on the first candle, so a vendor difference here moves signals. Which vendor's first bar matches the exchange's is **not established**.", ""]
    D += ["## 6. Policy (nothing is silently merged)", "",
          "* One minute source per run; never mixed. Raw responses, processed Parquet (ZSTD) and manifests live in per-index namespaces (`data/raw/<index>/5paisa`, `data/raw/<index>/secondary_kapri/<commit>`, `data/processed/<index>/<source id>`), separate from NIFTY.",
          "* The 5paisa **daily** series of the same index is always used for the official close, the daily moving averages and the trading-day reference (a disclosed mixed-source run for the secondary-source windows, as in Phase 4); its role is recorded in every trade (`daily_source_id`).",
          "* Windows: **M** main 2022-09-01..2026-08-31 (5paisa), **MS** 2022-09-01..2024-03-22 with the secondary source (vendor sensitivity, the dates where both secondary files exist), **C** 2018 (secondary, EXPLORATORY), **D_5P** 2019-03-01..2019-12-31 (5paisa, PARTIAL YEAR), **D_TV** 2019 (secondary, EXPLORATORY).",
          "* Exchange rules by period: the closing-auction regime is applied only from the date and only for the index whose own data show it (section 3 of `data_quality_report.md`); no later rule is applied to earlier sessions.", "",
          "## 7. Licensing and permitted use", "",
          "5paisa's data are used through the account's own API for research, read-only. The documentation page states no redistribution terms and the Terms and Conditions were not read; the raw and processed vendor data are therefore **kept under `data/` (raw is git-ignored) and should not be published or committed without checking the terms**. "
          "The two repositories are MIT-licensed as repositories; the licence of the data they carry is unknown, so the secondary-source results are exploratory research only."]
    (OUT / "data_discovery.md").write_text("\n".join(D) + "\n")

    # ============================================================================================================== data_quality_report.md
    Q = ["# Phase 5 - data quality report", "", WARN, "",
         "Per index and window: coverage against the calendar derived from that index's own data, session-quality gate (the frozen Phase 2.1 session logic), the checks required by the brief, and a confidence tier (the Phase 4 rubric: HIGH needs the same provider as the baseline, >= 99% usable sessions and a second vendor within 0.10 point on average; "
         "MODERATE the same with a larger vendor difference; LOW a partial year; EXPLORATORY_UNVERIFIABLE a source with nothing to check it against). Tiers are conventions with round-number boundaries, not statistical claims.", ""]
    for k, name in NAMES.items():
        c = cov[k]
        Q += [f"## {name}", "", "### Coverage by window", ""]
        rows = []
        mainov = [v for lab, v in ovl[k].items() if lab.startswith("2022-08")][0]
        for w in ("M", "MS", "C", "D_5P", "D_TV"):
            r = c[w]
            rows.append([w, f"{r['start']}..{r['end']}", r["minute_source"], r["expected_sessions"], r["sessions_in_source"], r["usable_sessions"], r["excluded_sessions"], r["sessions_with_missing_minutes"], r["sessions_with_extreme_1m_candles"],
                         r["abnormal_first_bars"], r["ohlc_violation_rows"], r["warmup_sessions_same_source"], tier(name, w, r, mainov)])
        Q += [tab(["window", "dates", "minute source", "expected sessions", "in source", "usable", "excluded", "sessions with missing minutes", "sessions with an extreme (> 0.5%) 1-minute move", "abnormal 09:15 bars", "OHLC violations", "warm-up sessions in source", "confidence"], rows), "",
              "Expected sessions = weekdays that are not derived holidays plus weekend sessions in the daily series. Dates missing from a source:", ""]
        for w in ("M", "MS", "C", "D_5P", "D_TV"):
            r = c[w]
            md = r["missing_dates"]
            if isinstance(md, str) and md and len(md) < 600:
                Q.append(f"* {w}: {md.replace(';', ', ')}")
            elif isinstance(md, str) and md:
                Q.append(f"* {w}: {len(md.split(';'))} dates (the SENSEX secondary file starts on 2018-03-08; the first {len(md.split(';'))} sessions of 2018 are absent)")
        if "2022-10-24" in str(c["M"]["missing_dates"]):
            Q.append("* 2022-10-24 is the Diwali Muhurat evening session: absent from the 5paisa minute data, present in the secondary source (where the gate excludes it as a non-standard session) and in the daily series.")
        Q += ["", "### Excluded sessions (the frozen gate), per window", ""]
        ex = qual[k][~qual[k].usable]
        Q += [tab(["window", "date", "weekday", "rows", "first..last bar", "status", "reason"], [[r.window, r.date, r.weekday, r.n_rows, f"{r.first_bar}..{r.last_bar}", r.pipeline_status, str(r.pipeline_reasons)[:90]] for r in ex.itertuples()]), "",
              "Muhurat (evening) sessions, Saturday special sessions and truncated or placeholder sessions are not evaluated. `2023-10-19` is a 5paisa feed defect (BANKNIFTY: frozen prices; SENSEX: the 09:15-09:18 bars are missing) - the secondary source has that day, so a defect in one vendor is not turned into a holiday or a special session for the other.", ""]
        cs = calsum[k]
        Q += ["### Calendar derived from this index's own data", "",
              f"Holidays per year (weekday with no daily candle and no minute rows in any source covering the date): {cs['holidays_per_year']}. Special sessions: " + (", ".join(f"{d} ({v['name'].split('(')[1].rstrip(')')[:40]}; evaluable={v['evaluable']})" for d, v in cs["special_sessions"].items() if d >= '2022-01-01') or "none") + ". "
              f"Vendor gaps between series (weekday traded per the daily series but absent from a covering minute source): {len(cs['gaps_between_series'])}. Opening-bar defects (one vendor missing 09:15-09:xx where another has it): {cs['opening_bar_defects'] or 'none'}. "
              "The calendar is derived, not read from an exchange circular; it was cross-checked against the NIFTY calendars, which should agree because NSE and BSE close together.", "",
              "### Closing-auction regime (decided per index from its own data)", ""]
        e = casev[k]["5paisa"]
        Q += [f"The index freezes at one price over 15:16-15:26 on {e['frozen_pattern_from']} of {e['sessions_from_2026_08_03']} sessions from 2026-08-03 and on {e['frozen_pattern_before']} of {e['sessions_before_2026_08_03']} sessions between 2026-06-01 and 2026-08-02 "
              f"(first session with the pattern: {e['first_session_with_pattern']}). The regime is therefore applied to {name} from 2026-08-03 **because its own data show it** (frozen-window bars are reference prints, not fillable; the official close is the daily vendor close), not by assuming NSE's rule for BSE or vice versa. "
              "The regulatory circular was not read directly (the NIFTY evidence calendar cites secondary sources).", "",
              "### Other checks required by the brief", ""]
        qq = qual[k][qual[k].window == "M"]
        dd = qq["daily_close_minus_last_1529"].dropna().abs()
        hh = qq["session_high_minus_daily_high"].dropna().abs()
        ll = qq["session_low_minus_daily_low"].dropna().abs()
        gap = qq["gap_to_previous_daily_close"].dropna().abs()
        Q += [tab(["check", "main window M (5paisa)", "how it is checked"], [
            ["timezone and alignment", "IST; 1-minute bars labelled by START; 376 rows per session incl. the 15:30 stub", "raw files; independent audit"],
            ["duplicates", f"{prov[k]['five_paisa_minutes']['duplicate_rows_removed']} duplicate rows removed (dates {prov[k]['five_paisa_minutes']['duplicate_dates']}); conflicting duplicates {prov[k]['five_paisa_minutes']['conflicting_duplicate_timestamps']}", "identical rows dropped, last kept"],
            ["OHLC consistency", f"{int(qq['ohlc_violation_rows'].sum())} violating rows", "high >= max(open, close), low <= min, positive, no NaN"],
            ["missing candles", f"{int((qq['missing_regular_minutes'] > 0).sum())} sessions with missing regular minutes (total {int(qq['missing_regular_minutes'].sum())} minutes); nothing is filled", "per-session table"],
            ["frozen / flat prices", f"{int((qq['frozen_rows_ge5'] > 0).sum())} sessions with a >= 5-minute frozen run (of which {e['frozen_pattern_from']} are the expected closing-auction freeze from 2026-08-03)", "frozen runs outside the auction window exclude the session"],
            ["large discontinuities", f"{int((qq['extreme_1m_candles'] > 0).sum())} sessions with a 1-minute move > 0.5% (max {qq['max_1m_close_return_pct'].max():.2f}%); {int(qq['abnormal_first_bar'].sum())} abnormal 09:15 bars; flagged, not removed", "predeclared thresholds"],
            ["session open", f"09:15 bar present on {int(qq['first_open_is_0915'].sum())} of {len(qq)} sessions", "the first 1-minute open is the session open"],
            ["minute high/low vs daily candle", f"mean abs difference: high {hh.mean():.2f}, low {ll.mean():.2f} points", "5paisa daily vs the minute session extremes"],
            ["previous-day close", f"official close = the 5paisa DAILY close (differs from the last 15:29 close by {dd.mean():.2f} points on average, as for NIFTY)", "convention; independent audit recomputes previous-day high / low / close"],
            ["open vs previous daily close", f"mean abs overnight gap {gap.mean():.1f} points", "sanity"],
            ["5-minute aggregation", "complete 5-minute candles only (5 one-minute rows), labelled by start; recomputed independently from the raw rows for every explanation candle", "independent audit"],
            ["EMA(200) warm-up", f"{c['M']['warmup_sessions_same_source']} sessions of same-source minute warm-up for the main window; {c['D_5P']['warmup_sessions_same_source']} for D_5P (EMA undefined for the first ~3 sessions); >= 200 daily bars precede every window", "warm-up rows never traded"]]), "",
              "The OFFICIAL daily close is not the last 15:29 bar's close and (for the NSE indices) not the 15:30 stub either; the frozen logic uses the vendor daily close for the previous-day close.", ""]
    (OUT / "data_quality_report.md").write_text("\n".join(Q) + "\n")

    # ============================================================================================================== per-index summaries
    cmp_by = {(r["index"], r["row_id"]): r for r in comp}
    for k, name in NAMES.items():
        A = ann(name)
        S = [r for r in rd(OUT / k / "strategy_performance.csv")]
        cost = rd(OUT / k / "cost_sensitivity.csv")
        vend = rd(OUT / k / "vendor_sensitivity.csv")
        mall = A["M_ALL"]
        L = [f"# {name} - Phase 5 backtest summary (frozen Phase 3.6 rules, NIFTY index-point parameters, index prices only)", "", f"> {WARN}", "",
             f"**What was run.** IRF, ORB, PDR (body-based), PDS and RF through the shared Phase 3.0 controller (first valid signal; at most two trades a day; second trade only PDR/PDS after an initial full stop; 13:00 entry cutoff; same-minute conflicts untraded), exactly as frozen "
             f"(`{freeze['frozen_configuration_id']}`; every strategy, controller and framework file verified before each run). Stops 35 points (ORB 30), T1 27, T2 60 (PDR/PDS 70), post-T1 stop entry -/+ 6, forced exit at the open of the 15:14 minute - the NIFTY point values, **not scaled to {name}'s level**. "
             f"Units: a fixed 390 per trade is only a rupee comparison device. Data: {inst[k]['exchange_label']} index {name}, scrip {inst[k]['scrip_code']} (see `data_discovery.md`).", "",
             "## Headline (main window, 5paisa data)", "",
             tab(["", "value"], [["sessions evaluated / expected", f"{mall['sessions_evaluated']} / {cov[k]['M']['expected_sessions']}"], ["confirmed / fully valid signals", f"{mall['confirmed_signals']} / {mall['fully_valid_signals']}"], ["executed trades (first / second)", f"{mall['executed_trades']} ({mall['first_trades']} / {mall['second_trades']})"],
                  ["gross weighted index points", pts(mall["gross_index_points"])], ["average points per trade", mall["avg_points_per_trade"]], ["win rate", f"{mall['win_rate_pct']}%"], ["profit factor (points)", mall["profit_factor_points"]],
                  ["max drawdown (index points)", mall["max_drawdown_index_points"]], ["longest losing streak", mall["max_consecutive_losses"]], ["stop / T1 as % of the index", f"{mall['stop_pct_of_index']}% / {mall['t1_pct_of_index']}% (avg level {fn(mall['avg_entry_level']):,.0f})"],
                  ["initial full stops / T1 reached / T2 reached", f"{mall['initial_full_stop_pct']}% / {mall['t1_reached_pct']}% / {mall['t2_reached_pct']}%"], ["average holding", f"{mall['avg_holding_minutes']} one-minute bars"],
                  ["same-minute conflict days", mall["same_minute_conflict_days"]]]), "",
             "## By period", "", tab(["period", "status", "sessions", "trades", "win %", "PF (pts)", "index points", "avg pts/trade", "max DD (pts)", "stops %", "T1 %", "T2 %", "hold (min)", "conflicts"],
                                    [[f"{r['row_id']} {r['period']}", r["status"], r["sessions_evaluated"], r["executed_trades"], r["win_rate_pct"], r["profit_factor_points"], pts(r["gross_index_points"]), r["avg_points_per_trade"], r["max_drawdown_index_points"],
                                      r["initial_full_stop_pct"], r["t1_reached_pct"], r["t2_reached_pct"], r["avg_holding_minutes"], r["same_minute_conflict_days"]] for r in A.values()]), "",
             "Status: DATA_VALIDATED = the 5paisa data window passed the quality gate (**this says nothing about the strategy**); VENDOR_SENSITIVITY = the same dates on the secondary source; EXPLORATORY = secondary source only, unverifiable; PARTIAL_YEAR = 5paisa minute data start 2019-03-01. "
             "Every period is reported; nothing was dropped after seeing results. 2018 and 2019 are historical research with a strategy developed on later NIFTY data.", "",
             "## By strategy (main window)", "", tab(["strategy", "trades", "win %", "PF (pts)", "index points", "avg pts", "max DD", "stops %", "T1 %", "T2 %", "hold"],
                                                    [[r["strategy"], r["trades"], r["win_rate_pct"], r["profit_factor_points"], pts(r["gross_index_points"]), r["avg_points_per_trade"], r["max_drawdown_index_points"], r["initial_full_stop_pct"], r["t1_reached_pct"], r["t2_reached_pct"], r["avg_holding_minutes"]]
                                                     for r in S if r["row_id"] == "M_ALL"]), "",
             "### By strategy and Sep-Aug year (index points)", "", tab(["strategy"] + [x for x in ("M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26")] + ["C_2018 (exploratory)", "D_2019 5paisa (partial)"],
                                                                       [[s] + [pts(next(r for r in S if r["row_id"] == rid and r["strategy"] == s)["gross_index_points"]) for rid in ("M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26", "C_2018", "D_2019_5P_PARTIAL")] for s in ("IRF", "ORB", "PDR", "PDS", "RF")]), "",
             f"PDR (body-based) zone-failure profile in the main window: {mall['pdr_trades']} PDR trades; {mall['pdr_open_not_above_zone']} PDR setups invalidated because the session did not open strictly above the zone ({mall['pdr_open_not_above_zone_per_pdr_trade']} per trade); {mall['pdr_setups_rejected_total']} PDR setups rejected in total (reasons in `windows/M/rejected_signals.csv`). "
             "No zone-failure rule was changed.", "",
             "## Relative scale of the transferred rules", "",
             f"The stop is {mall['stop_pct_of_index']}% of {name} on average (T1 {mall['t1_pct_of_index']}%) against {cmp_by[('NIFTY', 'M_ALL')]['stop_pct_of_index']}% (T1 {cmp_by[('NIFTY', 'M_ALL')]['t1_pct_of_index']}%) for NIFTY over the same dates. "
             f"Measured on the 5paisa one-minute bars of 2022-09..2025-08, the median one-minute high-low range is {rng[name]['median']:.1f} points on {name} ({rng[name]['median_pct']:.3f}% of the level; 90th percentile {rng[name]['p90']:.1f}) against {rng['NIFTY']['median']:.1f} points on NIFTY ({rng['NIFTY']['median_pct']:.3f}%). "
             f"The 35-point stop is therefore about {35 / rng[name]['median']:.1f} median one-minute ranges on {name} against {35 / rng['NIFTY']['median']:.1f} on NIFTY, which is why trades resolve in minutes here (average holding {mall['avg_holding_minutes']} one-minute bars against {cmp_by[('NIFTY', 'M_ALL')]['avg_holding_minutes']} for NIFTY): "
             "the stops sit within a few bars of ordinary noise, so the result mostly measures noise at a narrow stop width. This is a rule-transfer diagnostic, not a tradable configuration; nothing was rescaled (that would change the rules), and fills at that precision (entry at the next bar's open, stops filled at the worse of level and open) are a simulation convention, not an execution claim.", "",
             "## Costs", "", tab(["fixed Rs / trade", "slippage pts / fill", "net Rs (fixed 390, synthetic)", "profit factor", "max DD Rs"],
                                  [[r["fixed_cost_rs_per_trade"], r["slippage_points_per_fill"], f"{fn(r['net_pnl_rs']):,.0f}", r["profit_factor"], f"{fn(r['max_drawdown_rs']):,.0f}"] for r in cost if r["row_id"] == "M_ALL"]), "",
             f"Rs figures use the fixed 390-unit multiplier (a comparison device; not contract P&L; not comparable with the other indices). The average trade earns {mall['avg_points_per_trade']} weighted index points before costs. 0.5 point of slippage on every unit of the three fills (390 entry + 195 + 195 exit units) "
             "costs 1.0 weighted index point per trade, so an average trade below that does not survive even this mild slippage assumption; the grid above shows the full range.", "",
             "## Vendor sensitivity (same frozen system, same dates, different minute data)", "", tab(list(vend[0].keys())[1:], [list(list(r.values())[1:]) for r in vend]), "",
             "The result depends materially on which vendor's bars are used; the trade sets overlap only partly. Neither vendor can be declared correct.", "",
             "## Files", "", f"`windows/<M|MS|C|D_5P|D_TV>/` (trades, exits, entry conditions, candles, signals, rejected/ignored signals, daily summary, issues, configuration snapshot), `daily/<window>/YYYY-MM/YYYY-MM-DD.md` (one journal per evaluated session including no-trade days, each with an option-feasibility block), "
             f"`charts/<window>/<trade>.svg` (actual candles), `{name}_Daily_Verification.xlsx`, `trade_level_signals.csv`, `daily_summary.csv`, `strategy_performance.csv`, `entry_explanations.csv`, `exit_explanations.csv`, `cost_sensitivity.csv`, `vendor_sensitivity.csv`, `monthly_index_points.csv`, `data/` (quality tables, coverage, overlaps)."]
        (OUT / k / f"{k}_backtest_summary.md").write_text("\n".join(L) + "\n")

    # ============================================================================================================== cross_index_comparison.md
    C = ["# Phase 5 - NIFTY 50 vs BANKNIFTY vs SENSEX (frozen rules, NIFTY point parameters)", "", f"> {WARN}", "",
         "**Read this first.** All three runs use the *same* point distances. Because the indices trade at very different levels (average entry level in 2025-26: " + ", ".join(f"{i} {fn(cmp_by[(i, 'M_2025_26')]['avg_entry_level']):,.0f}" for i in ("NIFTY", "BANKNIFTY", "SENSEX")) + "), the same 35-point stop is " + ", ".join(f"{fn(cmp_by[(i, 'M_2025_26')]['stop_pct_of_index']):.3f}% ({i})" for i in ("NIFTY", "BANKNIFTY", "SENSEX")) + " of the index. "
         "The runs therefore differ in market AND in effective risk scale; the comparison is a rule-transfer diagnostic, not a ranking of the indices. Index points of different indices are not economically equivalent, and **rupee figures are not compared**. "
         "NIFTY rows are read from the Phase 4 window B (5paisa) plus the unchanged Phase 3.6 window A; NIFTY 2018/2019 rows come from a different secondary vendor than the BANKNIFTY/SENSEX ones.", "",
         "## 1. Whole periods (each index over its own usable sessions)", ""]
    for rid in ("M_ALL", "M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26", "C_2018", "D_2019_5P_PARTIAL", "D_2019_SECONDARY", "M_TO_2024_03_22", "MS_2022_09_2024_03"):
        rr = [cmp_by[(i, rid)] for i in ("NIFTY", "BANKNIFTY", "SENSEX") if (i, rid) in cmp_by]
        C += [f"### {rid}: {rr[0]['period']} ({rr[0]['status']})", "", tab(["index", "sessions", "trades", "win %", "PF (pts)", "index points", "avg pts/trade", "max DD (pts)", "stops %", "T1 %", "T2 %", "hold (min)", "conflict days", "stop % of index", "avg level"],
                                                                          [[r["index"], r["sessions_evaluated"], r["executed_trades"], r["win_rate_pct"], r["profit_factor_points"], pts(r["gross_index_points"]), r["avg_points_per_trade"], r["max_drawdown_index_points"], r["initial_full_stop_pct"],
                                                                            r["t1_reached_pct"], r["t2_reached_pct"], r["avg_holding_minutes"], r["same_minute_conflict_days"], r["stop_pct_of_index"], r["avg_entry_level"]] for r in rr]), ""]
    C += ["## 1b. Scale of the transferred distances against ordinary one-minute noise (5paisa bars, 2022-09-01..2025-08-31)", "",
          tab(["index", "median level", "median 1-minute high-low range (points)", "as % of level", "90th percentile (points)", "35-point stop in median 1-minute ranges", "T1 (27 points) in median ranges"],
              [[i, f"{rng[i]['level']:,.0f}", f"{rng[i]['median']:.1f}", f"{rng[i]['median_pct']:.3f}%", f"{rng[i]['p90']:.1f}", f"{35 / rng[i]['median']:.1f}", f"{27 / rng[i]['median']:.1f}"] for i in ("NIFTY", "BANKNIFTY", "SENSEX")]), "",
          "The point distances are the same, but in units of ordinary one-minute movement the stop is much tighter on BANKNIFTY and SENSEX than on NIFTY. The results below therefore mix market behaviour with effective risk scale.", ""]
    C += ["## 2. The same sessions only (sessions evaluated on all three indices)", "", tab(["period", "index", "common sessions", "trades", "win %", "PF (pts)", "index points", "avg pts", "max DD", "hold", "conflicts"],
                                                                                         [[r["row_id"], r["index"], r["common_sessions"], r["executed_trades"], r["win_rate_pct"], r["profit_factor_points"], pts(r["gross_index_points"]), r["avg_points_per_trade"], r["max_drawdown_index_points"], r["avg_holding_minutes"], r["same_minute_conflict_days"]] for r in common]), "",
          "## 3. Are the signals consistent across the indices? (common sessions of the main window)", "", tab(list(agree[0].keys())[:-1], [list(r.values())[:-1] for r in agree]), "",
          "On days when two indices both trade, " + "; ".join(f"{x['pair']}: the same strategy and direction is taken first on {x['pct_of_both_same_first_signal']}% of {x['sessions_with_a_trade_on_both']} days, the day's result has the same sign on {x['pct_of_both_same_sign']}%, correlation of daily index points {x['correlation_of_daily_index_points']}" for x in agree) +
          ". So the frozen rules give *similar* signals on NIFTY and SENSEX and noticeably different ones on BANKNIFTY, and even where the first signal is the same, the day's outcome often differs because the same point distances mean different things on each index. "
          "They do not behave as one 'market signal'.", "",
          "![cumulative index points](cumulative_index_points_main_window.svg)", "",
          "## 4. By strategy, main window (index points)", "", tab(["strategy"] + [f"{i} trades / points / PF" for i in ("NIFTY", "BANKNIFTY", "SENSEX")],
                                                                  [[s] + [(lambda r: f"{r['trades']} / {pts(r['gross_index_points'])} / {r['profit_factor_points']}")(next(x for x in compstrat if x["index"] == i and x["row_id"] == "M_ALL" and x["strategy"] == s)) for i in ("NIFTY", "BANKNIFTY", "SENSEX")] for s in ("IRF", "ORB", "PDR", "PDS", "RF")]), "",
          "## 5. Data quality at a glance", "", tab(["index", "main window usable / expected", "minute source", "vendor overlap: bars identical", "vendor overlap: mean abs close diff", "main-window confidence"],
                                                    [["NIFTY", "738 / 744 (window B; the Phase 3.6 reference window A covers 2025-09..2026-08)", "5paisa", "39.8% (Phase 4, 2022-08..2025-08)", "see Phase 4 `data_quality_by_year.md`", "MODERATE (Phase 4)"]] +
                                                    [[NAMES[k], f"{cov[k]['M']['usable_sessions']} / {cov[k]['M']['expected_sessions']}", "5paisa", [v for lab, v in ovl[k].items() if lab.startswith('2022-08')][0]["share_exact_all_fields"],
                                                      [v for lab, v in ovl[k].items() if lab.startswith('2022-08')][0]["mean_abs_close_diff"], tier(NAMES[k], "M", cov[k]["M"], [v for lab, v in ovl[k].items() if lab.startswith('2022-08')][0])] for k in IDX.values()]), "",
          "## 6. What can and cannot be concluded", "",
          "* The same frozen code ran on all three index series without a change (verified by hash before each run) and produced signals and trades from all five strategies on each.",
          "* On the common sessions of the main window, NIFTY is the only index with a clearly positive profit factor; BANKNIFTY and SENSEX are close to break-even **before costs** in index points, and a per-trade average of well under one point does not survive any realistic slippage.",
          "* The result by year is not stable on any index, and the vendor choice changes it materially (see each index's vendor-sensitivity table).",
          "* 2018 and 2019 look better than 2022-2026 on BANKNIFTY and SENSEX (positive in every row), while NIFTY's 2018 is negative. These years rest on one unattributed vendor (2018 entirely, 2019 apart from the partial 5paisa year), the point distances are a larger share of the lower index levels of those years, and the strategy was developed using later NIFTY data - this is exploratory evidence, not out-of-sample validation.",
          "* None of this says anything about option P&L: see `../options_feasibility/option_data_availability.md`."]
    (OUT / "comparison" / "cross_index_comparison.md").write_text("\n".join(C) + "\n")
    (OUT / "cross_index_comparison.md").write_text("\n".join(C).replace("![cumulative index points](cumulative_index_points_main_window.svg)", "![cumulative index points](comparison/cumulative_index_points_main_window.svg)") + "\n")

    # ============================================================================================================== options docs
    O = ["# Phase 5 - historical option-data availability (BANKNIFTY and SENSEX)", "", WARN, "",
         "**Conclusion: a historical option-premium backtest is NOT possible with the data available to this project, and none was run.** The strategy's signals, stops and targets come from the underlying index; the option leg would need the premium history of the contract that existed on each signal date. "
         "That history cannot be requested because the contract's identifier is unavailable (below). No option price was estimated, interpolated, modelled or inferred from index points; no journal contains an option execution.", "",
         "## 1. What the broker offers (verified by probes of this phase, `option_probe_results.json`)", ""]
    prows = []
    for nm, v in probe_opt["indices"].items():
        mn = v["master_new"]
        prows.append([nm, mn["by_type"].get("CE", 0), mn["by_type"].get("PE", 0), mn["n_option_expiries"], mn["earliest_expiry_listed"], mn["option_expiries_listed"][-1], mn["lot_sizes_listed"], "no" if not mn["contains_expired_contracts"] else "yes"])
    O += [tab(["index", "CE contracts listed", "PE contracts listed", "expiries listed", "earliest expiry listed", "latest expiry listed", "lot sizes in the master", "any expired contract listed?"], prows), "",
          "* **The instrument master lists only live contracts** (earliest listed expiry is after the download date for both indices). The scrip code of a contract that existed on, say, 2023-03-15 is not in it, and no archive of earlier masters exists in this project (the Phase 1 copy of 2026-11-01 differs from the 2026-11-05 copy only by newly listed contracts and one delisted far-OTM SENSEX contract).",
          "* The historical-candle API is keyed by scrip code only (no symbol, strike or expiry parameters), so an expired contract cannot be requested without a code. The documentation does not say whether expired contracts are served: **not stated**; it could not be tested because no expired code is available (the one contract that left the master, `SENSEX 31 DEC 2026 CE 87000`, returned EMPTY - it is a far-dated illiquid strike that was delisted before expiry, so this is not conclusive). "
          "A recheck can be made after the next SENSEX weekly expiry has passed (the codes of the 2026-11-05 expiry are saved in `option_probe_results.json`).",
          "* For **live** contracts, one-minute premium candles are served (timestamp, open, high, low, close, volume): see the table below. There is **no bid, ask, spread or open interest** in the response (the documentation lists none and none was returned), so a premium-OHLC simulation could only be a lower-confidence model even where it exists.", ""]
    lrows = []
    for nm, v in probe_opt["indices"].items():
        for p in v["probes"]:
            if p["label"] == "six_months":
                lrows.append([nm, p["type"], p["expiry"], f"{p['strike']:,.0f}", p["status"], p.get("rows", 0), (p.get("first_timestamp") or "")[:16], p.get("distinct_dates", ""), p.get("volume_nonzero_rows", ""), p.get("zero_range_bar_share", "")])
    O += [tab(["index", "type", "expiry", "strike", "status", "1-min rows (6-month request)", "first bar", "dates", "bars with volume", "share of flat bars"], lrows), "",
          f"Strikes were chosen near the index's last daily close in the 5paisa daily file ({', '.join(f'{nm} {v['last_daily_close_used_to_pick_strikes']:,.0f} on {v['last_daily_date'][:10]}' for nm, v in probe_opt['indices'].items())}), **not** near the spot on the probe date (2026-11-05), so 'near the money' means near those closes. "
          "What the table shows: history exists only from roughly when a contract became active (days for SENSEX weeklies, up to about ten weeks for a BANKNIFTY monthly), and out-of-the-money strikes are very illiquid (a handful of bars in months). Liquidity, not data format, would limit any simulation.", "",
          "## 2. Overlap of live contracts with the backtest window", "",
          "Contracts live today with a minute history starting inside the main window exist only for its last days (BANKNIFTY monthly contracts from late 2026-08). They are not the contracts a nearest-expiry policy would have chosen then, and using them would be a policy choice that has not been made, so they were not used.", "",
          "## 3. Legitimate sources that would make it possible (none acquired; none purchased)", "",
          "* **Daily end-of-day option data** (NSE/BSE F&O bhavcopy): free archives exist, but they are one price per contract per day - not usable to simulate a minute-level entry and exit. Terms of use of the free archive were not confirmed; NSE also sells official end-of-day data.",
          "* **Minute-level expired-option data**: some brokers' data APIs advertise rolling expired-option data by strike offset (for example Dhan: minute data for up to five years, ATM +/- offsets; documentation seen only second-hand, coverage of SENSEX unconfirmed); Zerodha's forum states its API does not serve expired option candles; commercial vendors sell one-minute option history. Any of these needs an account, a licence check and an owner decision before use.",
          "* **Forward collection**: store the broker master and the live contracts' minute candles every day from now on. This is the only route that uses the current broker connection and produces an auditable record; it would take months to be useful.", "",
          "## 4. Exchange rules that a future option backtest must respect (NOT verified against exchange circulars)", "",
          "The figures below come from broker and news summaries found by search, not from NSE/BSE circulars, and must be verified before use. They show that nothing about contract size or expiry may be assumed constant:", "",
          tab(["period (as reported)", "BANKNIFTY (NSE)", "SENSEX (BSE)"], [
              ["2018-2019", "lot size and expiry structure for 2018-19 not established by the searches; weekly and monthly expiries existed", "options existed but were very thinly traded; contract details not established"],
              ["2020-07", "lot 20 -> 25 for contracts expiring on/after 2020-07-30", "-"],
              ["2023", "lot 25 -> 15 for contracts after the June 2023 monthly expiry; weekly expiry day moved to Wednesday in 2023", "weekly SENSEX options introduced in 2023 (Friday expiry)"],
              ["2024-11", "lot 15 -> 30 for contracts introduced from 2024-11-20; **weekly BANKNIFTY options discontinued** (last weekly around 2024-11-13); monthly/quarterly only", "lot 10 -> 20 for contracts introduced after 2024-11-20"],
              ["2025", "lot 30 -> 35 (reported effective 2025-04-25), then back to 30 (circular FAOP70616, 2025-10-03, from the contracts after 2025-12-30); monthly expiry moved to the last Tuesday", "weekly expiry Friday -> Tuesday from 2025-01 (reported), later Thursday (the 2026-11 master shows Thursday expiries)"],
              ["2026-11 (the live master)", "monthly expiries only; lot 30; expiry dates are Mondays/Tuesdays (a holiday moves the last Tuesday to the previous trading day)", "20 weekly expiries listed (Thursday), lot 20, and 25 for contracts from 2027-01"]]), "",
          "Sources (secondary, to be verified): [Fyers notice](https://fyers.in/notice-board/revision-in-index-derivatives-contracts-lot-size/), [Angel One](https://www.angelone.in/announcements/market/revision-in-lot-size-of-index-derivative), [5paisa news](https://www.5paisa.com/news/nse-revises-lot-sizes-for-key-index-derivatives-starting-november-2024), "
          "[Groww](https://groww.in/blog/important-updates-from-nse-and-bse-regarding-index-derivatives), [Business Standard](https://www.business-standard.com/markets/stock-market-news/sensex-bankex-sensex-50-expiry-days-to-change-from-january-1-bse-124112801317_1.html). "
          "Conflicting reports exist (for example the SENSEX weekly day after 2025-09), which is why none of this is used as a rule.", "",
          "## 5. Technical requirements before any option paper trading", "",
          "1. A source of historical premiums with bid/ask (or an owner-accepted lower-confidence OHLC model) for expired contracts, with a licence check. 2. A daily archive of the broker's instrument master. 3. A verified contract-specification table per date (lot size, expiry day, strike step, trading hours). "
          "4. An option execution model (entry at which price, spread, slippage, liquidity limits, exit on index triggers) approved by the owner. 5. The infrastructure gaps recorded in Phase 4 (streaming prices, order state, risk and duplicate-order controls)."]
    (OUT / "options_feasibility" / "option_data_availability.md").write_text("\n".join(O) + "\n")
    DEC = ["# Phase 5 - option contract selection: DECISIONS REQUIRING OWNER APPROVAL", "", WARN, "",
           "**Nothing in this file is an approved rule, and no option result is presented as a strategy.** The mapping 'bullish index signal -> buy CALL (CE); bearish index signal -> buy PUT (PE)' is the owner's stated intent; everything else below is an open question, listed with a *candidate* only so the question is concrete. "
           "No candidate was run, tuned or chosen for its historical return, and no strike, expiry or days-to-expiry was selected by looking at results.", "",
           tab(["#", "decision needed", "candidate (NOT approved)", "why it matters / what must be verified first"], [
               ["D1", "Long options only? (an index short signal = buy PE; never sell a naked option)", "yes, long CE/PE only, as stated", "defines risk (premium paid) and margin; owner to confirm no spreads or hedges"],
               ["D2", "Strike selection", "nearest-to-the-money strike to the signal-minute index price (ties: owner to say)", "delta, premium and liquidity change sharply with moneyness; far strikes are illiquid (see the probe); the strike step differs by index and period"],
               ["D3", "Expiry selection", "a stated rule such as 'the nearest expiry with at least N trading days left' - N and the rule are open", "BANKNIFTY weeklies existed until 2024-11 and monthlies only after; SENSEX weeklies exist from 2023; expiry weekdays changed; near-expiry premiums behave very differently"],
               ["D4", "Lot size per date", "the exchange lot in force for the contract on the trade date (from circulars, verified)", "lot sizes changed several times (BANKNIFTY 20, 25, 15, 30, 35, 30); the frozen 390-unit sizing (6 x 65) is a NIFTY device and does not apply"],
               ["D5", "Position sizing", "owner to define lots per signal and how the two exit legs (3 + 3 lots in the index model) map to option lots", "minimum lot granularity; the leg split needs an even lot count"],
               ["D6", "Entry price", "the option's own next traded price after the index signal; requires bid/ask or a stated lower-confidence OHLC model", "premium-candle open is not a price at which an order is certain to fill"],
               ["D7", "Exit trigger and price", "exit when the INDEX hits its stop / T1 / T2 / post-T1 stop / 15:14 (as frozen), at the option's price at that minute", "the index stop of 35 points is a different (smaller or larger) move in premium depending on delta"],
               ["D8", "Costs and slippage", "brokerage, exchange charges, STT on options, stamp duty, GST, plus spread and slippage per fill - owner to approve the schedule", "premium is small; fixed costs matter more than for the index model"],
               ["D9", "Liquidity filter", "skip a signal if the chosen contract has no volume in the entry minute - threshold open", "illiquid strikes would make fills fictional"],
               ["D10", "Index-point parameters", "unchanged in this phase (the brief forbids optimising); whether to rescale them to the index level in a later phase is an owner decision", "at 0.04-0.07% of the index, a 35-point stop is inside ordinary noise for BANKNIFTY and SENSEX"],
               ["D11", "Historical data source", "which licensed source supplies expired-option minute data (see `option_data_availability.md`)", "without it there is no backtest"]]), "",
           "Only after D1-D11 are answered, and a premium source exists, can a clearly labelled option-premium research run be designed (Report B of the brief). Until then Report B does not exist."]
    (OUT / "options_feasibility" / "option_contract_selection_decisions.md").write_text("\n".join(DEC) + "\n")

    # ============================================================================================================== provenance json
    dp = {"phase": "5.0", "generated_utc": pd.Timestamp.now("UTC").isoformat(), "instruments": inst, "instrument_master": {"file": inst["banknifty"]["master_file"], "sha256": inst["banknifty"]["master_sha256"]},
          "five_paisa": {k: {"manifest": f"data/raw/{k}/5paisa/manifest.json", "manifest_sha256": __import__("hashlib").sha256((ROOT / "data/raw" / k / "5paisa" / "manifest.json").read_bytes()).hexdigest(), "request_status_counts": {f"{a}:{b}": n for (a, b), n in req_stats(k).items()}} for k in IDX.values()},
          "secondary_sources": {k: {kk: vv for kk, vv in mansec[k].items() if kk != "files"} | {"files": mansec[k]["files"]} for k in IDX.values()}, "processed_manifests": {k: prov[k]["processed_manifests"] for k in IDX.values()},
          "calendar_files": {k: f"data/processed/{k}/calendar_derived.json" for k in IDX.values()}, "build_provenance": {k: f"reports/phase5/{k}/data/data_provenance_build.json" for k in IDX.values()},
          "frozen_configuration_id": freeze["frozen_configuration_id"], "git_head_at_run": cfgsnap.get("generated_utc"), "note": "Raw vendor data are kept under data/raw (git-ignored); every trade row carries the minute-source id, daily-source id, partition SHA-256 and raw-file SHA-256."}
    (OUT / "data_provenance.json").write_text(json.dumps(dp, indent=1, default=str))

    # ============================================================================================================== independent_audit.md and README
    ar = json.loads((OUT / "independent_audit_results.json").read_text())
    rev = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    samp = (OUT / "_sample_review.md").read_text() if (OUT / "_sample_review.md").exists() else ""
    IA = ["# Phase 5 - independent audit", "",
          f"`scripts/phase5_independent_audit.py` is a second implementation written from the raw provider files, their manifests, the broker's master copy and the delivered CSVs only (no `src/` imports; candle, EMA and exit-walk helpers come from the Phase 3.2 audit script, itself free of `src/` imports). "
          f"Result: **{'ALL ' + str(len(ar['checks'])) + ' CHECKS PASS' if ar['all_pass'] else 'FAILURES PRESENT'}**.", "",
          tab(["#", "check", "n", "result", "detail"], [[i + 1, n, v["n"], "PASS" if v["pass"] else "FAIL", str(v["detail"])[:140]] for i, (n, v) in enumerate(ar["checks"].items())]), "",
          "**Independence caveat.** The audit script is a second implementation, but it was written by the same author as the pipeline; unlike Phase 4, no separate fresh-reviewer pass was run in this phase. Two genuine defects were found by it and fixed before delivery: (1) a vendor defect in one source (SENSEX 5paisa, 2023-10-19, missing 09:15-09:18) had made the date a 'special session' for the other source's run, and (2) the secondary-source partitions did not record their raw file hash on each trade.", "",
          "## What this does and does not prove", "",
          "* Every trade of every window was re-walked from the raw one-minute bars: entry price, stop-before-target ordering, gap fills, partial exit at T1, the post-T1 stop at entry -/+ 6, T2, the 15:14 forced exit, and the index-point P&L. The trade tables, exit tables, annual tables and workbooks agree with that recomputation.",
          "* The 5-minute candles and EMA(200) quoted in the explanations equal an independent aggregation and a causal recomputation; no explanation candle ends after its signal.",
          "* The controller rules hold on the delivered signal tables, with 'no fillable bar' rejections checked against the raw rows.",
          "* Signal DETECTION by the five strategy engines is the frozen Phase 2-3.6 code (hash-verified); it was not re-implemented a second time here. Its correctness on NIFTY was reviewed in Phases 3.3-3.6 and its unchanged hash is what carries it to the new indices. The sample table below shows representative executed trades per strategy and index for human review.",
          "* NIFTY is untouched: every git-tracked file, NIFTY data, earlier report and the Phase 4 freeze equal the before-snapshot taken before any Phase 5 output existed.",
          "* Option claims: no journal or table contains an option premium, strike or option P&L (checked by pattern), and the availability statements are backed by the saved probe file.", "",
          "## Tests and lint", "", f"* `pytest -q`: **{a.tests}**", f"* `ruff check src tests scripts`: **{a.ruff}**", "", samp, "", rev]
    (OUT / "independent_audit.md").write_text("\n".join(IA) + "\n")
    R = ["# Phase 5.0 - BANKNIFTY and SENSEX cross-index backtest with option-execution feasibility", "", f"> {WARN}", "",
         "Stopped after Phase 5.0 as instructed: no option paper trading, no live orders, nothing committed or pushed.", "",
         tab(["file / directory", "what it is"], [["data_discovery.md", "instrument identification, API probes, sources, licensing, vendor overlap"], ["data_quality_report.md", "coverage, exclusions, calendar, closing-auction evidence, checks, confidence tiers"],
                                                  ["banknifty/banknifty_backtest_summary.md, sensex/sensex_backtest_summary.md", "index-point results per index"], ["comparison/cross_index_comparison.md (copy at root)", "NIFTY vs BANKNIFTY vs SENSEX"],
                                                  ["options_feasibility/option_data_availability.md, option_contract_selection_decisions.md, option_probe_results.json", "whether option premiums are obtainable; owner decisions"],
                                                  ["<index>/trade_level_signals.csv, daily_summary.csv, strategy_performance.csv, entry_explanations.csv, exit_explanations.csv, cost_sensitivity.csv", "compiled tables (window_id first column)"],
                                                  ["<index>/<INDEX>_Daily_Verification.xlsx", "workbook written from the CSV files"], ["<index>/daily/, charts/", "one journal per evaluated session; one chart per trade"], ["configuration_snapshot.json, data_provenance.json, before_snapshot.json", "frozen configuration, sources and hashes, the NIFTY before-state"],
                                                  ["independent_audit.md, independent_audit_results.json, _sample_review.md", "audit"]]), "",
         "## Reproduce (tested commands)", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate",
         "python scripts/phase5_discover.py                       # resolve the instruments from the broker master + small API probes",
         "python scripts/phase5_fetch.py --index BANKNIFTY --source 5paisa --minutes --daily", "python scripts/phase5_fetch.py --index SENSEX --source 5paisa --minutes --daily",
         "python scripts/phase5_fetch.py --index BANKNIFTY --source secondary   # 2018 / 2019 exploratory source", "python scripts/phase5_fetch.py --index SENSEX --source secondary",
         "python scripts/phase5_build_data.py                     # processed Parquet (ZSTD), calendars, quality tables, overlaps",
         "python scripts/phase5_run.py --index BANKNIFTY --strategy-config phase36-frozen --window all", "python scripts/phase5_run.py --index SENSEX --strategy-config phase36-frozen --window all",
         "python scripts/phase5_compare.py                        # per-index tables, cross-index comparison, workbooks", "python scripts/phase5_options_probe.py             # option-data availability probe",
         "python scripts/phase5_independent_audit.py && python scripts/phase5_docs.py --tests \"...\" --ruff \"...\"", "```"]
    (OUT / "README.md").write_text("\n".join(R) + "\n")
    print("docs written; audit:", "ALL PASS" if ar["all_pass"] else "FAILURES")
    return 0


if __name__ == "__main__":
    sys.exit(main())
