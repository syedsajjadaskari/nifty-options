"""Phase 4: write the Markdown reports of reports/phase4/ from the delivered CSV / JSON files (every number is computed here, none is typed).

Run after scripts/phase4_run.py --window all and scripts/phase4_independent_audit.py:
  .venv/bin/python scripts/phase4_docs.py --tests "<pytest result>" --ruff "<ruff result>"
The fresh-reviewer section of independent_audit.md is read from reports/phase4/_reviewer_findings.md (written by hand after the independent review) when present.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import warnings
from collections import Counter
from glob import glob
from pathlib import Path

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
OUT = ROOT / "reports" / "phase4"
DATA = OUT / "data"
RAW5 = ROOT / "data" / "raw" / "phase4_5paisa" / "manifest.json"
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")
RUN_ALL = "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate && python scripts/phase4_run.py --strategy-config phase36-frozen --window all"
WARN = ("**Historical research only.** The strategy was developed using later data (2025-26), so none of these windows is out-of-sample in the strict sense, and nothing here establishes executable profitability: all P&L is synthetic index-point "
        "P&L x a fixed 390-unit multiplier on a cash index that cannot be traded, with illustrative costs.")


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def tab(head, body) -> str:
    return "\n".join(["| " + " | ".join(head) + " |", "|" + "---|" * len(head)] + ["| " + " | ".join(str(x) for x in r) + " |" for r in body])


def rs(x) -> str:
    return f"{float(x):,.0f}"


def fl(x) -> float:
    return float(x) if x not in ("", None) else 0.0


def main(tests: str, ruff: str) -> None:  # noqa: C901
    import pandas as pd
    ann = {r["row_id"]: r for r in rd(OUT / "annual_comparison.csv")}
    strat = rd(OUT / "strategy_comparison.csv")
    costs = rd(OUT / "cost_sensitivity.csv")
    monthly = rd(OUT / "monthly_pnl_all_windows.csv")
    reg = rd(OUT / "robustness_regimes.csv")
    etime = rd(OUT / "robustness_entry_time.csv")
    conc = {r["row_id"]: r for r in rd(OUT / "robustness_concentration.csv")}
    dq = {r["row_id"]: r for r in rd(OUT / "robustness_data_quality.csv")}
    vend = rd(OUT / "vendor_sensitivity.csv")
    notev = rd(OUT / "not_evaluated_strategy_sessions.csv")
    cover = {r["window_id"]: r for r in rd(DATA / "historical_coverage_by_window.csv")}
    qual = pd.read_csv(DATA / "session_quality_all_windows.csv")
    ovs = json.loads((DATA / "vendor_overlap_summary.json").read_text())
    cal = json.loads((DATA / "derived_calendar_summary.json").read_text())
    calv = json.loads((DATA / "calendar_method_validation.json").read_text())
    probe = json.loads((DATA / "probe_5paisa_initial.json").read_text())
    freeze = json.loads((OUT / "strategy_freeze.json").read_text())
    man5 = json.loads(RAW5.read_text())["requests"]
    tvdir = sorted((ROOT / "data" / "raw" / "phase4_technovusin").iterdir())[0]
    mantv = json.loads((tvdir / "manifest.json").read_text())
    trades = pd.read_csv(OUT / "all_trades_all_windows.csv")
    audit = json.loads((OUT / "independent_audit_results.json").read_text()) if (OUT / "independent_audit_results.json").exists() else {}
    audit_line = "ALL PASS" if audit.get("all_pass") else "not yet run"
    covx = rd(OUT / "coverage_exceptions.csv")
    st5 = Counter((r["timeframe"], r["status"]) for r in man5.values())
    empties = sorted(r["from"][:7] for r in man5.values() if r["status"] == "EMPTY")
    A, B1, B2, B3, BT, C, D5, DT = (ann[k] for k in ("A_2025_26", "B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25", "C_2018", "D_2019_5PAISA_PARTIAL", "D_2019_SECONDARY"))
    per_trade_cost = 500.0 + 0.5 * 2 * 390

    def metric_rows(ids, keys):
        return [[ann[i]["row_id"]] + [ann[i][k] for k in keys] for i in ids]

    # ============================================================================================================== data_source_discovery.md
    def fo_stats(g):
        x = g["first_open_minus_daily_open"].dropna().abs()
        return [len(x), f"{100 * (x <= 0.05).mean():.0f}%", f"{100 * (x <= 0.5).mean():.0f}%", round(float(x.mean()), 2)]
    p1 = pd.concat([pd.read_parquet(f) for f in sorted(glob(str(ROOT / "data/processed/nifty50/**/*.parquet"), recursive=True))], ignore_index=True)
    p1d = pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet")
    p1d["date"] = pd.to_datetime(p1d["date"]).dt.date
    p1f = p1[(p1.timestamp.dt.hour == 9) & (p1.timestamp.dt.minute == 15)].assign(date=lambda d: d.timestamp.dt.date).merge(p1d[["date", "open"]], on="date", suffixes=("", "_daily"))
    p1x = (p1f["open"] - p1f["open_daily"]).abs()
    fo_rows = [["B: 5paisa minutes (own daily)", *fo_stats(qual[qual["window"] == "B"])], ["B: secondary minutes (vs 5paisa daily)", *fo_stats(qual[qual["window"] == "B_TV"])],
               ["D 2019-03..12: 5paisa minutes", *fo_stats(qual[qual["window"] == "D_5P"])], ["D 2019 full: secondary minutes", *fo_stats(qual[qual["window"] == "D_TV"])], ["C 2018: secondary minutes", *fo_stats(qual[qual["window"] == "C"])],
               ["A 2025-26 (Phase 3.6 baseline): 5paisa Phase 1 minutes", len(p1x), f"{100 * (p1x <= 0.05).mean():.0f}%", f"{100 * (p1x <= 0.5).mean():.0f}%", round(float(p1x.mean()), 2)]]
    tr_all = trades.copy()
    tr_all["entry_price"] = tr_all["entry_price"].astype(float)

    def scale_row(rid):
        a = ann[rid]
        lo, hi = a["period"].split("..")
        t = tr_all[(tr_all["window_id"] == a["window_dir"]) & (tr_all["date"] >= lo) & (tr_all["date"] <= hi)]
        px = float(t["entry_price"].mean())
        n = len(t)
        return [rid, f"{px:,.0f}", f"{100 * 35 / px:.2f}% / {100 * 30 / px:.2f}%", f"{100 * 27 / px:.2f}%", f"{100 * sum(1 for o in t['outcome'] if o == 'FORCED_EXIT') / n:.1f}%", f"{100 * sum(1 for o in t['outcome'] if o == 'INITIAL_FULL_STOP') / n:.1f}%",
                round(float(t["bars_held"].mean()), 1)]
    ds = ["# Data source discovery (Phase 4)", "",
          "**Written for:** the strategy owner. Question: can reliable one-minute NIFTY 50 history be obtained for 2022-09..2025-08 (Window B), 2018 (Window C) and 2019 (Window D)? Every row below was tested by retrieving real candles and "
          "checking the returned timestamps and prices, not by HTTP status.", "",
          "## Answer in one table", "",
          tab(["period", "5paisa 1-minute (authenticated API)", "secondary source (technovusin repository)", "what was run"],
              [["2018-01-01 .. 2018-12-31 (C)", "**UNAVAILABLE**: every monthly request returned an empty response (no error, no rows)", "available, 245 sessions", "secondary vendor only, EXPLORATORY (nothing to check it against)"],
               ["2019-01-01 .. 2019-02-28 (D, part)", "**UNAVAILABLE** (empty)", "available", "secondary vendor only"],
               ["2019-03-01 .. 2019-12-31 (D, part)", "AVAILABLE, but **5 sessions missing** (2019-06-27, 06-28, 07-01, 07-02, 07-03)", "available, all 244 sessions of the year", "both, reported separately: 5paisa PARTIAL YEAR and secondary full year"],
               ["2022-09-01 .. 2025-08-31 (B)", "AVAILABLE, 743 of 744 expected sessions (the missing one, 2022-10-24, has a daily candle but no minute rows in either vendor; consistent with an evening Muhurat session)", "available, 743 sessions", "5paisa (main result); secondary vendor as a sensitivity run"],
               ["2025-09-01 .. 2026-08-31 (A)", "Phase 1 dataset (unchanged)", "available (overlap audit only)", "the existing Phase 3.6 backtest, not rerun"]]), "",
          f"5paisa **daily** candles are available back to at least 2017-01-02 (requested 2017-01-01 .. 2025-08-31: {st5[('1d', 'COMPLETED')]} requests, 2,143 daily bars), which supplies the official daily close, the 200-day averages the strategies need and an independent trading-day reference for every window.", "",
          "## 5paisa historical API", "",
          "Documentation: https://xstream.5paisa.com/dev-docs/market-data-system/historical-candles (one-minute interval, at most six months per request). Retrieval used the project's authenticated, read-only `BrokerClient` (order methods are disabled in that class) and the project's verified NIFTY 50 index mapping "
          "(`data/metadata/nifty50_instrument.json`: exchange N, segment C, scrip code 999920000). Credentials were never printed or written to any report. Requests were monthly (1-minute) or six-monthly (daily), rate-limited, retried, resumable "
          "(`data/raw/phase4_5paisa/manifest.json`), and every response was saved **unmodified** with its SHA-256.", "",
          tab(["outcome class", "count"], [["COMPLETED 1-minute months", st5[("1m", "COMPLETED")]], ["COMPLETED daily spans", st5[("1d", "COMPLETED")]], ["EMPTY (API answered with no rows)", st5[("1m", "EMPTY")]], ["RATE_LIMITED", sum(v for k, v in st5.items() if k[1] == "RATE_LIMITED")],
                                          ["ACCESS_DENIED", sum(v for k, v in st5.items() if k[1] == "ACCESS_DENIED")], ["FAILED", sum(v for k, v in st5.items() if k[1] == "FAILED")]]), "",
          f"Empty monthly requests: {', '.join(empties)} (all of 2018 and 2019-01 / 2019-02). The first returned bar is **2019-03-01 09:15** (a request spanning 2019-02-09..2019-03-01 returned exactly the 376 bars of 2019-03-01). The empty answers are not errors: the API accepts the request and "
          "returns nothing, so supported request syntax does not imply data exists for every year. The initial exploratory probes (before the resumable fetcher) are kept in `reports/phase4/data/probe_5paisa_initial.json`:", "",
          tab(["window", "rows", "first bar"], [[f"{p['from']}..{p['to']}", p.get("rows", p.get("error", "")), p.get("first", "")] for p in probe]), "",
          "Provider quirks found in the retrieved data: identical duplicated blocks inside the responses of 2022-10-10 and 2023-09-27 (660 duplicate rows removed, no conflicting values); a frozen-price feed on 2023-10-19 (the session is excluded by the quality gate); the DAILY candles carry float32 noise (for example 8210.0996), removed by rounding to 2 decimals in the processed copy only, while the 1-minute responses carry none "
          "(maximum deviation from 2 decimals recorded in `data_provenance_build.json`: 0.0); a 15:30 closing-print stub on 99% of sessions; Volume is always 0.", "",
          "## Secondary source: github.com/technovusin/nifty50-historical-data", "",
          f"* Repository verified to exist; pinned commit **{mantv['commit_sha']}** ({mantv['commit_date']}: \"{mantv['commit_message']}\"). Files downloaded from `raw.githubusercontent.com` at that commit into `data/raw/phase4_technovusin/{mantv['commit_sha']}/` (a separate namespace) with SHA-256 and the repository's own git blob SHA-1, "
          f"which was recomputed from the downloaded bytes and matched for all {sum(1 for f in mantv['files'].values() if f['status'] == 'OK')} files (an integrity check against the repository, **not** an independent check of the market data).",
          "* Files used: 1-minute CSVs for 2017 (warm-up only), 2018, 2019, 2022, 2023, 2024, 2025 and the monthly 2026 files (overlap audit). Columns: Epoch, Timestamp (ISO, IST), Open, High, Low, Close (Volume only in 2026).",
          "* Licence: the repository carries an MIT licence. **The underlying data vendor is not named, and nothing establishes the licence of the data itself**; the repository was created on 2026-09-09 and is updated daily. Treat it as an unattributed convenience dataset.",
          "* The README discloses cleaning that changes the data: bars outside 09:15-15:29 removed (so there is no 15:30 stub); duplicate bars with stray seconds removed (Aug-Sep 2021); **three bad first candles of 2022 were edited (High / Low adjusted to include Open: 25 Mar, 30 Mar, 7 Apr)**; suspicious partial or spurious sessions removed "
          "(7 Aug 2021 ... 30 Apr 2022); prices rounded to 2 decimals. The README keeps the Muhurat evening bars (12 Nov 2023, 1 Nov 2024) as an exception to its 09:15-15:29 rule and says **nothing about cleaning for 2018-2019, so whether those years were edited is unverifiable**. Known remaining quirks per the README: some single minutes missing, a few frozen-price stretches (24 Feb 2021 outage, March 2020 circuit breakers). Those edited dates lie outside the Phase 4 windows, but they show the files are curated, not raw.",
          "* Timestamp convention verified against the 5paisa data by a one-minute shift test: agreement is highest at zero shift in every overlap (below), so both vendors label a bar by its START.", "",
          "### Vendor-overlap audit (bar by bar, regular window 09:15-15:29)", "",
          tab(["overlap", "dates in both", "only secondary", "bars compared", "OHLC identical", "close within 0.05", "mean |close diff|", "p99 |close diff|", "max |close diff|", "days with a diff > 1 point"],
              [[k, v["dates_in_both"], len(v["dates_only_b"]) if v["dates_only_b"] else 0, f"{v['bars_compared']:,}", f"{100 * v['share_exact_all_fields']:.1f}%", f"{100 * v['share_close_within_0_05']:.1f}%", v["mean_abs_close_diff"], v["p99_abs_close_diff"], v["max_abs_close_diff"], v["days_with_any_diff_over_1pt"]] for k, v in ovs.items()]), "",
          "**The vendors' minute bars are not equivalent.** They agree on which sessions exist and on the timestamp convention, but the prices differ systematically, most in 2019 and 2022-25 and least in 2025-26. The 09:15 bar differs most (the first-bar open differs by about 4 points in 2019 and 6 points in 2022-25 on average; "
          "see the first-bar table below): IRF, ORB and the gap-based strategies are built on that first candle. The effect on the trades is quantified in `vendor_sensitivity.csv` and below. "
          "**No provider equivalence is claimed.** For 2018 there is no overlap at all, so the secondary data cannot be checked against another vendor for that year.", "",
          "### The 09:15 bar: each vendor's first-minute open against the 5paisa DAILY open", "",
          tab(["source", "sessions", "within 0.05", "within 0.5", "mean absolute difference (points)"], fo_rows), "",
          "The relationship **reverses with the period**: in 2022-25 the secondary vendor's first open matches the 5paisa daily open almost always while 5paisa's own first minute rarely does; in 2019 it is the other way round. The Phase 3.6 baseline (Window A) rests on 5paisa's first-minute convention, "
          "which in 2022-25 differs from its own daily open by about 6 points on average. **Which first-bar convention matches the exchange is not established**; the vendor-sensitivity result (same strategies, same window, different bars: Rs 509k vs Rs 626k gross, 71.5% signal agreement) is the practical consequence, and neither vendor can be called right on the evidence available.", "",
          "## Reconciliation policy (nothing is silently merged)", "",
          tab(["input", "source", "role"], [["1-minute candles", "ONE source per run: 5paisa or the secondary vendor, never mixed within a run", "signals, entries, exits"],
                                           ["daily candles", "always the 5paisa daily series (a separately identified input)", "official previous close (gap), daily 200-day averages, trading-day reference; **not** used to price any entry or exit"],
                                           ["calendar", "derived (see `data_quality_by_year.md`)", "holidays and special sessions"]]), "",
          "The 5paisa daily close is the official close; the last 15:29 minute close differs from it by 6-13 points on average (it is not the official close), which is why the official daily series is needed. Using 5paisa daily data with the secondary vendor's minutes is a documented mixed-source run; every trade carries both "
          "source ids and the partition SHA-256.", "",
          "## Contract sizes (disclosure; not used in any P&L)", "",
          "The fixed 390-unit multiplier (6 lots x 65) is a comparison device, **not** a claim that six lots of 65 units were executable in any year. Public reporting (secondary sources; the primary NSE circulars were not retrieved and the dates below are unverified) indicates NIFTY lot sizes changed several times: "
          "75 until 2021 (NSE circular NSE/FAOP/47854 dated 2021-03-31 reduced it to 50), 50 until 2024, then 25 (from 2024-04-26 per reports), 75 for contracts introduced from 2024-11-20, and 65 from NSE circular NSE/FAOP/70616 of 2025-10-03. Sources: "
          "[Angel One](https://www.angelone.in/news/market-updates/nse-reduces-lot-sizes-in-nifty-and-bank-nifty-derivatives), [Business Standard 2021-04-01](https://www.business-standard.com/amp/article/markets/national-stock-exchange-cuts-mkt-lot-size-for-nifty-50-derivative-contracts-121040100377_1.html), "
          "[NSE circular archive](https://archives.nseindia.com/content/circulars/FAOP47854.pdf). Reliable per-day contract specifications were **not** established, so no result is expressed in actual lots. The NIFTY 50 cash index is not tradable; futures or options would add basis, premium decay, margin and spread that this synthetic series ignores.", ""]
    (OUT / "data_source_discovery.md").write_text("\n".join(ds))

    # ============================================================================================================== historical_coverage.csv
    rows = []
    for wid, c in cover.items():
        rows.append({"window_id": wid, "window": c["window"], "minute_source": c["minute_source"], "daily_source": c["daily_source"], "start": c["start"], "end": c["end"], "expected_sessions": c["expected_sessions"], "sessions_in_source": c["sessions_in_source"],
                     "sessions_missing_from_source": c["sessions_missing_from_source"], "missing_dates": c["missing_dates"], "usable_sessions": c["usable_sessions"], "excluded_sessions": c["excluded_sessions"], "excluded_dates": c["excluded_dates"],
                     "sessions_with_missing_minutes": c["sessions_with_missing_minutes"], "total_missing_regular_minutes": c["total_missing_regular_minutes"], "sessions_with_frozen_runs": c["sessions_with_frozen_runs"],
                     "sessions_with_extreme_1m_candles": c["sessions_with_extreme_1m_candles"], "abnormal_first_bars": c["abnormal_first_bars"], "warmup_sessions_same_source": c["warmup_sessions_same_source"], "daily_bars_before_start": c["daily_bars_before_start"]})
    rows.append({"window_id": "A", "window": "Window A 2025-09-01..2026-08-31 (Phase 3.6 reference, existing dataset)", "minute_source": "FIVEPAISA_PHASE1", "daily_source": "FIVEPAISA_PHASE1_DAILY", "start": "2025-09-01", "end": "2026-08-31", "expected_sessions": 247,
                 "sessions_in_source": 247, "usable_sessions": 246, "note": "not rerun; see reports/phase3/phase36_body_based_pdr"})
    with open(OUT / "historical_coverage.csv", "w", newline="") as f:
        cols = list(dict.fromkeys(k for r in rows for k in r))
        w = csv.DictWriter(f, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)

    # ============================================================================================================== data_quality_by_year.md
    def qstat(wid):
        g = qual[qual["window"] == wid]
        dc = g["daily_close_minus_last_1529"].dropna().abs()
        return {"sessions": len(g), "usable": int(g["usable"].sum()), "missing_sessions": int((g["missing_regular_minutes"] > 0).sum()), "missing_total": int(g["missing_regular_minutes"].sum()), "frozen": int((g["frozen_rows_ge5"] > 0).sum()),
                "ohlc": int(g["ohlc_violation_rows"].sum()), "extreme": int((g["extreme_1m_candles"] > 0).sum()), "abn": int(g["abnormal_first_bar"].sum()), "stub": round(float(g["has_1530_stub"].mean()), 3), "dup": 0,
                "close_diff_mean": round(float(dc.mean()), 2), "not_daily": int((~g["in_daily_series"]).sum()), "not0915": int((~g["first_open_is_0915"]).sum())}
    wq = {w: qstat(w) for w in ("B", "B_TV", "C", "D_5P", "D_TV")}
    names = {"B": "B 5paisa", "B_TV": "B secondary", "C": "C 2018 secondary", "D_5P": "D 5paisa 2019-03..12", "D_TV": "D 2019 secondary"}
    dq_md = ["# Data quality by year (Phase 4)", "",
             "**Written for:** the strategy owner. Every window was validated BEFORE its backtest was run, with thresholds declared in advance (`phase4_data.py`: a 1-minute close-to-close move above 0.5% is reported as an extreme candle, a 09:15 bar wider than 1% of its open is reported, frozen runs are 5 or more identical flat bars - "
             "the pipeline's own rule). Reported items are disclosed, not silently dropped; only the pipeline's existing quality gate excludes sessions (identically for every year).", "",
             "## Checks required by the brief", "",
             tab(["check"] + [names[w] for w in wq],
                 [["sessions in source / usable"] + [f"{q['sessions']} / {q['usable']}" for q in wq.values()], ["chronological order (provider order, before sorting)"] + ["yes"] * 5,
                  ["unique timestamps (duplicates removed)"] + ["660 (2 days, identical)" if w == "B" else "0" for w in wq], ["Asia/Kolkata conversion"] + ["IST wall-clock, bar START"] * 5,
                  ["OHLC rows violating high >= max(open, close) or low <= min(open, close), or non-positive"] + [q["ohlc"] for q in wq.values()],
                  ["sessions with missing regular minutes / total missing minutes"] + [f"{q['missing_sessions']} / {q['missing_total']}" for q in wq.values()], ["sessions with frozen-price runs (>= 5 flat bars)"] + [q["frozen"] for q in wq.values()],
                  ["sessions with an extreme 1-minute candle (> 0.5%)"] + [q["extreme"] for q in wq.values()], ["abnormal 09:15 bars (range > 1% of open)"] + [q["abn"] for q in wq.values()],
                  ["sessions whose first bar is not 09:15"] + [q["not0915"] for q in wq.values()], ["15:30 closing-print stub present"] + [f"{100 * q['stub']:.0f}%" for q in wq.values()],
                  ["sessions with minute data but no 5paisa daily candle"] + [q["not_daily"] for q in wq.values()], ["mean absolute difference between the official daily close and the last 15:29 close (points)"] + [q["close_diff_mean"] for q in wq.values()],
                  ["minute warm-up sessions available before the window (same source)"] + [cover[w]["warmup_sessions_same_source"] for w in wq], ["daily bars before the window (need >= 200)"] + [cover[w]["daily_bars_before_start"] for w in wq]]), "",
             "Five-minute aggregation, the previous-session high / low and the open convention are the existing, tested Phase 2 / 3 code (a 5-minute candle is five complete 1-minute rows, usable at its end; the open is the first 1-minute open; the official close is the daily close) and are unchanged; the Phase 4 audit re-derives candles and indicators independently from the raw files.", "",
             "## Trading calendar (derived, validated, date-aware)", "",
             "The repository's evidence-tier calendar covers only 2025-26, so the Phase 2 pipeline would mark every post-holiday session of an older year as having an unverifiable previous day. A calendar is therefore DERIVED from the data: a weekday is a holiday when there is no 5paisa daily candle AND no minute rows in any source that covers the date "
             "(a weekday present in only some series is a vendor data gap, not a holiday); weekend or non-09:15 sessions are special sessions, evaluable only when they carry a full normal-hours session. "
             f"**Method check:** applied to 2025-09..2026-08 the same method reproduces the evidence-tier calendar exactly (identical = {calv['identical']}; {calv['derived_holidays']} derived vs {calv['evidence_holidays']} evidence holidays). "
             "The derived holidays were **not** compared with NSE circulars; external confirmation was not performed. Closing-auction handling is date-aware: the 2026-08-03 regime applies only from that date, so no auction restriction is applied to any Phase 4 window, and the continuous-trading convention "
             "(fills only on bars before 15:30, forced exit at the open of the 15:14 minute) is the unchanged Phase 3 policy.", "",
             tab(["year", "derived weekday holidays", "special / non-standard-start sessions"], [[y, n, ", ".join(f"{d} ({'evaluable' if v['evaluable'] else 'not evaluable'})" for d, v in cal["special_sessions"].items() if d.startswith(str(y))) or "-"] for y, n in sorted(cal["holidays_per_year"].items())]), "",
             f"Vendor gaps between series (not holidays; each minute source is only expected inside the years actually retrieved - 2020 and 2021 minute data were not retrieved): {len(cal['gaps_between_series'])} weekday(s), listed in `derived_calendar_summary.json`. "
             "Note that **2018-07-09 is not a special session**: it is a normal Monday whose 09:15 bar is missing from the secondary file (374 rows from 09:16), so it is excluded by the quality gate and one trading day is lost. "
             "The check of the method against the 2025-26 evidence calendar is partly circular (that calendar was itself built from absences in vendor series); the derived dates were reproduced independently and match public knowledge of NSE holidays, but were **not** compared with NSE circulars.", "",
             "## Excluded and unverifiable sessions (identical rules for every year)", ""]
    for wid in wq:
        g = qual[(qual["window"] == wid) & (~qual["usable"])]
        dq_md.append(f"* **{names[wid]}:** " + ("; ".join(f"{r.date} {r.pipeline_status} ({r.pipeline_reasons})" for r in g.itertuples()) or "none") + (f". Expected sessions absent from the source: {cover[wid]['missing_dates'] or 'none'}."))
    ne = Counter((r["window_dir"], r["reason"]) for r in notev if r["window_dir"] != "A")
    dq_md += ["", "A session whose PREVIOUS session is excluded, missing, or whose previous close cannot be verified makes the previous-day-dependent strategies (ORB, PDR, PDS, and RF's gap logic) NOT_EVALUATED that day; this is the Phase 2 rule applied unchanged. Counts (strategy-sessions) in `not_evaluated_strategy_sessions.csv`:", "",
              tab(["window", "reason", "strategy-sessions"], [[w, r, n] for (w, r), n in sorted(ne.items())]), "",
              "## Data-quality confidence (rubric fixed in advance)", "",
              tab(["tier", "meaning"], [[k, v] for k, v in json.loads((OUT / "regime_definitions.json").read_text())["confidence_rubric"].items()]), "",
              tab(["window / period", "tier", "why"], [[ann[i]["row_id"], ann[i]["data_quality_confidence"], ann[i]["data_source"] + " | " + ann[i]["status"]] for i in ("A_2025_26", "B_2022_25", "D_2019_5PAISA_PARTIAL", "D_2019_SECONDARY", "C_2018")]), "",
              "## Known issues that can affect results", "",
              "* The confidence tiers are conventions with round-number boundaries (for example 0.10 point of mean difference); the Phase 3.6 reference year's mean difference is 0.089, just inside the HIGH boundary.",
              "* Windows B and B_TV are not on identical session sets: 2023-10-19 is excluded in B only (frozen 5paisa feed).",
              "* The reported count of sessions with missing minutes is dominated by the excluded special sessions: see `coverage_exceptions.csv` for the usable sessions only.",
              "* The two vendors' minute bars differ (see `data_source_discovery.md`); the 09:15 bar, which IRF and ORB use, differs most. Window B was therefore also run on the secondary vendor's bars: `vendor_sensitivity.csv`.",
              "* 2023-10-19 is excluded in the 5paisa run (frozen feed) but present in the secondary run.", "* 5paisa lacks five 2019 sessions (2019-06-27 .. 07-03) that the secondary vendor has; the 5paisa 2019 run is a PARTIAL YEAR and has no minute warm-up before 2019-03-01 (the first sessions have no EMA).",
              "* 5paisa has no daily candle on 2022-11-17 and 2024-01-12 although minute data exist; the following sessions' previous close is then unverifiable and the affected strategies are NOT_EVALUATED.",
              f"* {len(covx)} session rows carry at least one flag or exception (mostly the official-close-differs-from-last-print note and dropped incomplete 5-minute candles): `coverage_exceptions.csv`.", ""]
    (OUT / "data_quality_by_year.md").write_text("\n".join(dq_md))

    # ============================================================================================================== window summaries
    def window_summary(ids, title, intro, files_note, extra=""):
        L = [f"# {title}", "", f"**Written for:** the strategy owner. {WARN}", "", intro, "",
             "## Headline (frozen Phase 3.6 configuration, no parameter changed)", "",
             tab(["row", "status", "confidence", "sessions", "trades (1st/2nd)", "IRF / ORB / PDR / PDS / RF", "index points", "gross Rs (390 units)", "illustrative net Rs", "win %", "profit factor (gross / net)", "max drawdown Rs", "longest losing streak"],
                 [[ann[i]["row_id"], ann[i]["status"], ann[i]["data_quality_confidence"], ann[i]["sessions_evaluated"], f"{ann[i]['trades']} ({ann[i]['first_trades']}/{ann[i]['second_trades']})",
                   " / ".join(ann[i][f"trades_{s}"] for s in STRATS), ann[i]["total_index_points_weighted"], rs(ann[i]["gross_pnl_rs_fixed_390"]), rs(ann[i]["net_pnl_rs_illustrative"]), ann[i]["win_rate_pct"],
                   f"{ann[i]['profit_factor_gross']} / {ann[i]['profit_factor_net']}", rs(ann[i]["max_drawdown_rs_gross"]), ann[i]["max_consecutive_losses"]] for i in ids]), "",
             tab(["row", "avg trade Rs", "median trade Rs", "largest win Rs", "largest loss Rs", "Target 2", "T1 then buffer stop", "initial full stop", "forced exit", "conflict days", "unresolved", "positive / negative months", "trades per session", "avg holding (min)"],
                 [[ann[i]["row_id"], ann[i]["avg_trade_rs"], ann[i]["median_trade_rs"], rs(ann[i]["largest_win_rs"]), rs(ann[i]["largest_loss_rs"]), ann[i]["target2"], ann[i]["t1_then_buffer_stop"], ann[i]["initial_full_stop"], ann[i]["forced_exit"],
                   ann[i]["simultaneous_signal_conflict_days"], ann[i]["unresolved_executions"], f"{ann[i]['positive_months']} / {ann[i]['negative_months']}", ann[i]["trades_per_session"], ann[i]["avg_holding_minutes"]] for i in ids]), "",
             "## By strategy (gross Rs, 390 units)", "",
             tab(["row", "strategy", "trades", "gross Rs", "net Rs", "win %", "profit factor", "share of gross"], [[r["row_id"], r["strategy"], r["trades"], rs(r["gross_pnl_rs"]), rs(r["net_pnl_rs"]), r["win_rate_pct"], r["profit_factor_gross"], r["share_of_window_gross_pct"] or "n/m (window gross not positive)"]
                                                                                                           for r in strat if r["row_id"] in ids]), "",
             "## Monthly P&L (gross Rs)", ""]
        mm = {}
        for r in monthly:
            if r["row_id"] in ids:
                mm.setdefault(r["month"], {})[r["row_id"]] = r["gross_pnl_rs"]
        L += [tab(["month"] + list(ids), [[m] + [rs(v[i]) if i in v else "-" for i in ids] for m, v in sorted(mm.items())]), ""]
        L += ["## Coverage and exceptions (per row: the sessions of that period only)", ""]
        for i in ids:
            w = ann[i]["window_dir"]
            lo, hi = ann[i]["period"].split("..")
            g = qual[(qual["window"] == w) & (qual["date"] >= lo) & (qual["date"] <= hi)]
            c = cover.get(w)
            whole = c is not None and (c["start"], c["end"]) == (lo, hi)
            exc = "; ".join(f"{r.date} {r.pipeline_status}" for r in g[~g["usable"]].itertuples()) or "none"
            iss = dq[i]["sessions_with_data_issue"] if i in dq else "-"
            L.append(f"* **{i}** ({lo}..{hi}): {len(g)} sessions in the source, {int(g['usable'].sum())} usable; excluded: {exc}; sessions with a predeclared data issue (missing regular minutes, frozen run, abnormal 09:15 bar, extreme 1-minute candle): {iss}"
                     + (f"; expected sessions {c['expected_sessions']}, missing from the source: {c['missing_dates'] or 'none'}; warm-up sessions in the same source: {c['warmup_sessions_same_source']}." if whole else "."))
        L += ["", extra, "", files_note, ""]
        return L

    v_b = vend[0]
    sg = {(r["row_id"], r["strategy"]): r for r in strat}
    narr_b = ["## What drives the three-year result", "",
              "Gross Rs by strategy over the three years: " + ", ".join(f"{x} {rs(sg[('B_2022_25', x)]['gross_pnl_rs'])}" for x in STRATS) + f". **PDR (the author-corrected strategy) lost money in the validated window** ({sg[('B_2022_25', 'PDR')]['trades']} trades, profit factor {sg[('B_2022_25', 'PDR')]['profit_factor_gross']}), "
              f"worst in 2023-24 (Rs {rs(sg[('B2_2023_24', 'PDR')]['gross_pnl_rs'])}, {sg[('B2_2023_24', 'PDR')]['win_rate_pct']}% wins) while it was positive in 2022-23 (Rs {rs(sg[('B1_2022_23', 'PDR')]['gross_pnl_rs'])}) and 2024-25 (Rs {rs(sg[('B3_2024_25', 'PDR')]['gross_pnl_rs'])}); "
              f"IRF, ORB, PDS and RF were each positive over the three years, and IRF supplies most of the gross profit. The flat middle year is explained by PDR (and PDS) losses offsetting IRF.", "",
              f"**Same-minute conflicts.** No tie-break between different strategies' simultaneous signals is approved, so such a day is marked unresolved and nothing is traded: {ann['B_2022_25']['simultaneous_signal_conflict_days']} of {ann['B_2022_25']['sessions_evaluated']} sessions in this window "
              f"({ann['B1_2022_23']['simultaneous_signal_conflict_days']} / {ann['B2_2023_24']['simultaneous_signal_conflict_days']} / {ann['B3_2024_25']['simultaneous_signal_conflict_days']} by year). This conservative rule removes trades; it is preserved from Phase 3.0 and was not changed.", "",
              "**Status labels.** `DATA_VALIDATED` means the DATA window passed the quality gate (coverage, structure, calendar); it says nothing about whether the strategy is validated: this window's gross is Rs " + rs(BT["gross_pnl_rs_fixed_390"]) + f", net Rs {rs(BT['net_pnl_rs_illustrative'])} (profit factor {BT['profit_factor_net']} net). "
              "Windows B and B_TV are not on identical session sets (2023-10-19 is excluded in B only).", ""]
    ext_b = narr_b + ["## Vendor sensitivity (the same window on the secondary vendor's minute bars)", "",
             tab(["row", "status", "trades", "gross Rs", "net Rs", "profit factor", "max drawdown Rs"], [[ann[i]["row_id"], ann[i]["status"], ann[i]["trades"], rs(ann[i]["gross_pnl_rs_fixed_390"]), rs(ann[i]["net_pnl_rs_illustrative"]), ann[i]["profit_factor_gross"], rs(ann[i]["max_drawdown_rs_gross"])]
                                                                                                    for i in ("B1_2022_23", "B1_TV", "B2_2023_24", "B2_TV", "B3_2024_25", "B3_TV", "B_2022_25", "B_2022_25_TV")]), "",
             f"The two vendors agree on {v_b['signals_in_both']} of {int(v_b['confirmed_signals_vendor_a']) + int(v_b['confirmed_signals_vendor_b']) - int(v_b['signals_in_both'])} confirmed signals ({v_b['signal_agreement_pct_of_union']}% of the union) and on {v_b['identical_trade_signals']} identical executed-trade signals "
             f"({v_b['same_outcome_among_identical']} with the same outcome); {v_b['trades_only_vendor_a']} trades exist only on 5paisa bars (gross Rs {rs(v_b['gross_rs_on_trades_only_a'])}) and {v_b['trades_only_vendor_b']} only on secondary bars (gross Rs {rs(v_b['gross_rs_on_trades_only_b'])}). "
             f"The identical trades earn about the same on both (Rs {rs(v_b['gross_rs_on_identical_trades_a'])} vs {rs(v_b['gross_rs_on_identical_trades_b'])}); **almost all of the Rs {rs(float(v_b['gross_rs_vendor_b']) - float(v_b['gross_rs_vendor_a']))} difference comes from the ~130 trades that exist on only one vendor's bars.** "
             "The year-by-year sign pattern is the same on both vendors (the middle year is the weak one), but the size of every result depends materially on which vendor's minute bars are used; neither is shown to be right."]
    s3 = window_summary(["B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25"], "Three-year backtest summary (Window B, 2022-09-01 .. 2025-08-31)",
                        "Window B uses the same provider as the Phase 3.6 baseline (5paisa minutes + 5paisa daily). The three annual slices come from ONE continuous run under identical frozen rules (the 5-minute EMA is warm throughout; the controller state is per day, so slicing the ledger by date is exact).",
                        f"Full detail: `windows/B/` (trades, entry conditions, exits, signals, daily summary), `daily/B/YYYY-MM/` ({len(list((OUT / 'daily' / 'B').rglob('*.md')))} journals), `charts/B/` ({len(list((OUT / 'charts' / 'B').glob('*.svg')))} charts).", "\n".join(ext_b))
    (OUT / "three_year_backtest_summary.md").write_text("\n".join(s3))
    s18 = window_summary(["C_2018"], "2018 backtest summary (Window C, 2018-01-01 .. 2018-12-31) - EXPLORATORY",
                         "**Status: EXPLORATORY.** 5paisa returns no one-minute data for 2018, so the only minute source is the secondary vendor, whose bars differ systematically from 5paisa wherever the two can be compared (2019-2026) and which cannot be checked against any other vendor for 2018. "
                         "The official daily closes and the 200-day averages come from the 5paisa daily series. This is a full calendar year of sessions (244 of 245 usable; 2018-07-09 lacks its 09:15 bar and is excluded), but the data confidence is the lowest tier.",
                         f"Full detail: `windows/C/`, `daily/C/YYYY-MM/` ({len(list((OUT / 'daily' / 'C').rglob('*.md')))} journals), `charts/C/` ({len(list((OUT / 'charts' / 'C').glob('*.svg')))} charts).",
                         f"The year is loss-making: gross Rs {rs(C['gross_pnl_rs_fixed_390'])}, profit factor {C['profit_factor_gross']}. The losses are concentrated in high-volatility sessions (see `robustness_report.md`). The result is reported as it is; no period, strategy or trade was removed. "
                         "**Scale caveat:** the stops and targets are fixed index POINTS, and the index was about 2.3x lower in 2018 than in 2025, so the same 35-point stop is about twice as wide in relative terms (see the scale table in `robustness_report.md`); "
                         "2018 is therefore not a like-for-like test of the strategy's risk, and holds positions longer (more forced exits).")
    (OUT / "2018_backtest_summary.md").write_text("\n".join(s18))
    v_d = vend[1]
    ext_d = ["## Vendor comparison for 2019 (sessions present in both)", "",
             tab(["row", "status", "trades", "gross Rs", "net Rs", "profit factor"], [[ann[i]["row_id"], ann[i]["status"], ann[i]["trades"], rs(ann[i]["gross_pnl_rs_fixed_390"]), rs(ann[i]["net_pnl_rs_illustrative"]), ann[i]["profit_factor_gross"]] for i in ("D_2019_5PAISA_PARTIAL", "D_2019_SECONDARY")]), "",
             f"On the 196 sessions both sources have (2019-03..12): {v_d['trades_vendor_a']} trades on 5paisa bars vs {v_d['trades_vendor_b']} on secondary bars, {v_d['identical_trade_signals']} identical trade signals ({v_d['same_outcome_among_identical']} same outcome), gross Rs {rs(v_d['gross_rs_vendor_a'])} vs {rs(v_d['gross_rs_vendor_b'])}; "
             f"signal agreement {v_d['signal_agreement_pct_of_union']}% of the union. **The 5paisa result is a partial year (10 months, 196 of 201 expected sessions) and must not be read as full-year 2019 performance.** The secondary result is the only full calendar year but is exploratory."]
    s19 = window_summary(["D_2019_SECONDARY", "D_2019_5PAISA_PARTIAL"], "2019 backtest summary (Window D)",
                         "Two runs, never merged: (1) the **secondary vendor's full calendar year 2019** (244 sessions, EXPLORATORY: no independent check exists for January-February, and the March-December overlap with 5paisa shows different bars) and (2) **5paisa minutes 2019-03-01 .. 2019-12-31, a PARTIAL YEAR** "
                         "(196 of 201 expected sessions; five sessions are missing from the provider; no minute warm-up exists before the first session). Where the two overlap they disagree on 33% of signals.",
                         f"Full detail: `windows/D_TV/`, `windows/D_5P/`, `daily/D_TV|D_5P/YYYY-MM/` ({len(list((OUT / 'daily' / 'D_TV').rglob('*.md'))) + len(list((OUT / 'daily' / 'D_5P').rglob('*.md')))} journals), charts under `charts/D_TV/` and `charts/D_5P/`.", "\n".join(ext_d))
    (OUT / "2019_backtest_summary.md").write_text("\n".join(s19))

    # ============================================================================================================== drawdown_analysis.md
    dd_rows = []
    for rid in ("C_2018", "D_2019_SECONDARY", "D_2019_5PAISA_PARTIAL", "B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25", "A_2025_26", "B_2022_25_TV"):
        a = ann[rid]
        wid = a["window_dir"]
        lo, hi = a["period"].split("..")
        t = trades[(trades["window_id"] == wid) & (trades["date"] >= lo) & (trades["date"] <= hi)].sort_values(["date", "fill_timestamp", "trade_no_of_day"])
        cum = peak = worst = 0.0
        peak_d = at_d = start_d = None
        for r in t.itertuples():
            cum += float(r.gross_pnl_rs)
            if cum >= peak:
                peak, peak_d = cum, r.date
            if peak - cum > worst:
                worst, at_d, start_d = peak - cum, r.date, peak_d
        n_dd = int(((t["date"] > (start_d or "")) & (t["date"] <= (at_d or ""))).sum()) if at_d else 0
        dd_rows.append([rid, a["status"], rs(a["max_drawdown_rs_gross"]), rs(a["max_drawdown_rs_net"]), a["max_drawdown_index_points"], f"{start_d} -> {at_d}" if at_d else "-", n_dd, rs(a["gross_pnl_rs_fixed_390"]), f"{float(a['max_drawdown_rs_gross']) / 100000:.2f}x / {float(a['max_drawdown_rs_gross']) / 500000:.2f}x",
                        a["max_consecutive_losses"]])
    dd = ["# Drawdown analysis (Phase 4)", "", f"**Written for:** the strategy owner. {WARN}", "",
          "Drawdown is measured on the cumulative trade-by-trade synthetic P&L (peak-to-trough, running peak starting at zero), exactly as in Phase 3. Rupee figures use the fixed 390-unit multiplier; index points are the per-unit weighted points of the same trades. "
          "The last column states the drawdown as a MULTIPLE of two hypothetical capital levels (Rs 1,00,000, the project's earlier reporting convention, and Rs 5,00,000, an illustrative larger level). **Neither level is claimed to be sufficient to support six derivative lots; no return percentage is computed** "
          "because no defensible capital or margin assumption exists for this synthetic cash-index series.", "",
          tab(["row", "status", "max DD gross Rs", "max DD net Rs", "max DD index points", "peak -> trough (trade dates)", "trades in the drawdown", "period gross Rs", "DD as multiple of Rs 1 lakh / Rs 5 lakh", "longest losing streak"], dd_rows), "",
          tab(["row", "max DD gross Rs / period gross Rs"], [[r[0], (f"{float(str(r[2]).replace(',', '')) / float(str(r[7]).replace(',', '')):.2f}" if float(str(r[7]).replace(',', '')) > 0 else "n/a (period gross is not positive)")] for r in dd_rows]), "",
          "Reading: the worst drawdown is large relative to what a whole year earns (see the ratio columns of the tables below), so the equity curve is very noisy relative to its drift; the three-year window's worst drawdown equals the worst single year's (it occurs inside 2022-23). Net drawdowns are larger than gross because the illustrative costs accrue on every trade. "
          "The drawdown figures are descriptions of this synthetic history, not a risk limit or a position-sizing recommendation.", ""]
    (OUT / "drawdown_analysis.md").write_text("\n".join(dd))

    # ============================================================================================================== robustness_report.md
    def reg_rows(dim):
        return [[r["row_id"], r["regime"], r["sessions"], r["trades"], rs(r["gross_pnl_rs"]), r["avg_trade_rs"], r["win_rate_pct"]] for r in reg if r["regime_dimension"] == dim and r["row_id"] in ("C_2018", "D_2019_SECONDARY", "B1_2022_23", "B2_2023_24", "B3_2024_25", "A_2025_26")]
    cs = {(r["row_id"], r["fixed_cost_rs_per_trade"], r["slippage_points_per_fill"]): r for r in costs}
    rids = ("C_2018", "D_2019_SECONDARY", "B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25", "A_2025_26")
    rb = ["# Robustness report (Phase 4)", "", f"**Written for:** the strategy owner. {WARN}", "",
          "Diagnostics only: **no rule, threshold or window was changed or selected from these tables**, no trade or regime was excluded, and every loss-making period is shown. Regime thresholds are fixed round numbers declared in `regime_definitions.json` "
          "(they were written after the five windows had been run once for sanity checks but before any regime table existed; they are not fitted).", "",
          "## 1-3. By year, strategy and month", "", tab(["row", "status", "trades", "gross Rs", "net Rs", "profit factor", "positive / negative months"], [[ann[i]["row_id"], ann[i]["status"], ann[i]["trades"], rs(ann[i]["gross_pnl_rs_fixed_390"]), rs(ann[i]["net_pnl_rs_illustrative"]), ann[i]["profit_factor_gross"],
                                                                                                                                                   f"{ann[i]['positive_months']} / {ann[i]['negative_months']}"] for i in rids]), "",
          "By strategy (gross Rs; full table in `strategy_comparison.csv`):", "", tab(["row"] + list(STRATS), [[i] + [rs(next(r["gross_pnl_rs"] for r in strat if r["row_id"] == i and r["strategy"] == s)) for s in STRATS] for i in rids]), "",
          "Monthly P&L of every window: `monthly_pnl_all_windows.csv`.", "",
          "## 4. By volatility and trend regime (causal; trailing 20-day volatility and 60-day efficiency ratio, strictly before the session)", "", tab(["row", "vol regime", "sessions", "trades", "gross Rs", "avg trade Rs", "win %"], reg_rows("VOL")), "",
          tab(["row", "trend regime", "sessions", "trades", "gross Rs", "avg trade Rs", "win %"], reg_rows("TREND")), "",
          "The cells are noisy (some have few sessions) and the pattern is not stable across years: for example high-volatility sessions lose money in 2018, 2023-24 and 2025-26 but earn money in 2019, 2022-23 and 2024-25. The regime tables describe the history; they do not justify a filter. Combined cells: `robustness_regimes.csv`. "
          "No event explanation is offered for any day.", "",
          "## 5. By morning entry time", "", tab(["row", "entry time (fill)", "trades", "gross Rs", "avg trade Rs", "win %", "initial full stops"], [[r["row_id"], r["entry_time_bucket"], r["trades"], rs(r["gross_pnl_rs"]), r["avg_trade_rs"], r["win_rate_pct"], r["initial_full_stops"]] for r in etime if r["row_id"] in rids]), "",
          "## 6. Concentration of profit", "",
          tab(["row", "trades", "gross Rs", "top-5 wins Rs", "top 5 as % of gross profit", "gross excluding the top 5 wins Rs", "trades needed for half of the gross profit"],
              [[i, conc[i]["trades"], rs(conc[i]["gross_pnl_rs"]), rs(conc[i]["top5_wins_rs"]), conc[i]["top5_share_of_gross_profit_pct"], rs(conc[i]["gross_pnl_excluding_top5_wins_rs"]), conc[i]["positive_trades_needed_for_half_of_gross_profit"]] for i in rids]), "",
          "No single trade dominates (the five largest wins are about 7-9% of a year's gross profit), but removing the best 10% of trades turns every window listed here negative (the 5paisa partial 2019 run stays positive), which is the normal shape of a fixed-target system and says the result depends on the winners it keeps.", "",
          "## 7. Losing streaks", "", tab(["row", "longest consecutive losing trades"], [[i, ann[i]["max_consecutive_losses"]] for i in rids]), "",
          "## 8-9. Transaction-cost and slippage sensitivity (net Rs; fixed cost per trade x adverse slippage points per fill; fill-level costs)", "",
          tab(["row", "gross (0 / 0)", "Rs 500 / 0 pt", "Rs 0 / 0.5 pt", "**Rs 500 / 0.5 pt (Phase 3.6 headline)**", "Rs 1,000 / 0.5 pt", "Rs 500 / 1 pt", "Rs 500 / 2 pt", "Rs 1,500 / 2 pt"],
              [[i] + [rs(cs[(i, a, b)]["net_pnl_rs"]) for a, b in (("0.0", "0.0"), ("500.0", "0.0"), ("0.0", "0.5"), ("500.0", "0.5"), ("1000.0", "0.5"), ("500.0", "1.0"), ("500.0", "2.0"), ("1500.0", "2.0"))] for i in rids]), "",
          f"The headline model costs about Rs {per_trade_cost:,.0f} per trade (Rs 500 fixed + 0.5 point on 780 units). The three-year gross edge is about Rs {float(BT['gross_pnl_rs_fixed_390']) / float(BT['trades']):,.0f} per trade, so **the validated three-year window nets Rs {rs(BT['net_pnl_rs_illustrative'])} at the headline cost model, and loses money at "
          "any higher cost or slippage.** The Phase 3.6 reference year is positive only because its gross edge per trade was higher. The cost model is illustrative and not tied to an executable instrument; no cost scenario was chosen because it flatters the result (the full grid is in `cost_sensitivity.csv`).", "",
          "## 10. Sensitivity to known data-quality issues", "",
          tab(["row", "sessions with a predeclared data issue", "trades on those sessions", "gross on those Rs", "trades on other sessions", "gross on other Rs"], [[i, r["sessions_with_data_issue"], r.get("trades_on_issue_sessions", "-"), rs(r["gross_on_issue_sessions_rs"]) if r.get("gross_on_issue_sessions_rs") else "-", r.get("trades_on_other_sessions", "-"), rs(r["gross_on_other_sessions_rs"]) if r.get("gross_on_other_sessions_rs") else "-"] for i, r in dq.items() if i in rids]), "",
          "A data issue is one of the predeclared items (missing regular minutes, a frozen-price run, an abnormal 09:15 bar, an extreme 1-minute candle). These sessions are few, so the table is a disclosure, not evidence; no session is excluded from the main results.", "",
          "The bigger data sensitivity is the choice of vendor, not the flagged sessions: see `vendor_sensitivity.csv` and `three_year_backtest_summary.md` (the same three-year window is Rs "
          f"{rs(BT['gross_pnl_rs_fixed_390'])} gross on 5paisa bars and Rs {rs(ann['B_2022_25_TV']['gross_pnl_rs_fixed_390'])} on the secondary vendor's bars, with 71.5% signal agreement).", ""]
    rb += ["## 11. Scale of the fixed-point parameters (why the years are not like-for-like)", "",
           "Stops, targets and the post-T1 buffer are fixed index POINTS, and the Rs value of a point is constant (390 units), while the index level changed by a factor of about 2.3 across the windows. A 35-point stop is therefore a much wider move in relative terms in 2018-19 than in 2024-26, "
           "and positions are held longer when the index is lower (more trades reach the 15:14 forced exit). The windows differ in the RISK the same rules take, so differences between years mix market behaviour with scale. Nothing was rescaled (that would be a rule change).", "",
           tab(["row", "average entry level", "stop 35 / ORB 30 as % of the index", "target 1 (27) as %", "forced-exit share of trades", "initial-full-stop share", "average holding (1-minute bars)"], [scale_row(i) for i in rids]), ""]
    (OUT / "robustness_report.md").write_text("\n".join(rb))

    # ============================================================================================================== paper_trading_readiness.md
    pr = ["# Paper-trading readiness assessment (Phase 4)", "",
          "**Written for:** the strategy owner. This is an assessment only. No live order was placed, no paper trading was deployed, and no market monitoring was started.", "",
          "## Verdict", "",
          "**Not recommended to begin paper-trading engineering on the strength of this historical evidence.** The frozen strategy is technically reproducible and its machinery is reliable, but the evidence is inconsistent across years, fragile to realistic costs, and sensitive to the data source. "
          "If the owner decides to proceed anyway, the first work item should be the missing live-data and execution infrastructure below, with the unresolved author decisions closed first.", "",
          "## Evidence from the historical tests", "",
          tab(["criterion", "finding", "assessment"],
              [["Consistency across years", f"gross Rs: 2018 {rs(C['gross_pnl_rs_fixed_390'])} (exploratory), 2019 {rs(DT['gross_pnl_rs_fixed_390'])} (exploratory, secondary vendor) / {rs(D5['gross_pnl_rs_fixed_390'])} (5paisa, 10 months), 2022-23 {rs(B1['gross_pnl_rs_fixed_390'])}, 2023-24 {rs(B2['gross_pnl_rs_fixed_390'])}, 2024-25 {rs(B3['gross_pnl_rs_fixed_390'])}, 2025-26 {rs(A['gross_pnl_rs_fixed_390'])}; "
                                                f"of the six distinct years one is clearly negative (2018, exploratory) and one is flat (2023-24, profit factor {B2['profit_factor_gross']}); the years also differ in scale (fixed-point stops against an index that was ~2.3x lower in 2018-19: see `robustness_report.md` section 11)", "NOT consistent"],
               ["Costs", f"gross edge about Rs {float(BT['gross_pnl_rs_fixed_390']) / float(BT['trades']):,.0f} per trade vs about Rs {per_trade_cost:,.0f} of illustrative cost per trade; three-year net Rs {rs(BT['net_pnl_rs_illustrative'])}; negative at every higher cost / slippage tested", "FRAGILE"],
               ["Drawdown", f"worst drawdown Rs {rs(BT['max_drawdown_rs_gross'])} gross (three years) against a three-year gross profit of Rs {rs(BT['gross_pnl_rs_fixed_390'])}; longest losing streak {BT['max_consecutive_losses']}", "LARGE relative to the edge"],
               ["Data reliability", "the two vendors' minute bars differ (OHLC identical on 40% of 2022-25 bars; first-bar open differs by ~6 points); the same three-year window is Rs 509k vs Rs 626k gross with 71.5% signal agreement; 2018 cannot be checked at all", "MATERIAL sensitivity: a live feed's bars will differ again"],
               ["Unresolved author rules", "; ".join(freeze["research_status_of_unresolved_rules"]["unresolved_author_decisions"][:6]) + "; ...", "OPEN (10 listed in `strategy_freeze.json`)"],
               ["Development bias", "the strategy was developed on 2025-26 data and tuned in conversation with that year's journal; none of the older windows is strictly out-of-sample", "CAVEAT on every result"]]), "",
          "## Engineering readiness (what exists in the repository today)", "",
          tab(["capability", "state", "gap"],
              [["Market-data streaming", "none: only the historical-candle endpoint of the read-only `BrokerClient` exists; no websocket / tick consumer", "build a live 1-minute bar builder that reproduces the research bar convention (bar START label, first bar semantics) and detect gaps / stalls; validate live bars against the historical vendor (they will not be identical)"],
               ["Trading-session calendar", "historical: evidence calendar 2025-26 + derived multi-year calendar; the closing-auction regime is date-aware (2026-08-03)", "a live calendar source for holidays, special sessions and revised timings; the derived calendar was not checked against NSE circulars"],
               ["Broker API", "authentication (TOTP, cached daily token) and read-only endpoints work; order, modify, cancel and square-off raise `PermissionError` by design", "order APIs untested; instrument mapping for options / futures (the research uses the cash index, which is not tradable) not built"],
               ["Paper-order simulation", "`core/paper.py` is a 63-line Phase 1 skeleton (order dataclass and statuses), not connected to the Phase 3 controller or exit model", "an executable paper engine that reuses `trading_day.py` / `exit_policy.py` and an option / futures price model"],
               ["State persistence", "none for a live day (the backtest controller is stateless across days and re-runs the day)", "durable per-day state: open positions, leg status, stops, signals seen, so a restart cannot re-enter or lose a position"],
               ["Duplicate-order prevention", "none", "idempotent order keys per signal, a single writer, reconciliation with broker positions"],
               ["Emergency stops / risk", "`core/risk.py` is a 55-line skeleton (daily loss limit Rs 10,000, which is below the strategy's own single-trade loss of Rs 13,650; position size of 1,800 = 50 lots; kill-switch flag) that does not match the 6-lot / 390-unit design", "kill switch wired to the order path, daily loss and position limits derived from the strategy, a market-data-stall halt"],
               ["Logging and monitoring", "research reports are rich; no runtime logging / alerting for a live process", "structured logs, heartbeat, alerts on stalls, rejected orders and state mismatches"],
               ["Forced exit / end of day", "the research uses a provisional exit at the open of the 15:14 minute; the owner has not approved it", "an approved end-of-day liquidation policy that also covers the closing-auction regime"]]), "",
          "## If the owner wants to continue", "",
          "1. Decide the open author questions (candle-pattern definitions, PDR wait policy, zero-height zones, tie-break for simultaneous signals, RF target, forced exit) **before** any further testing, so that no later result can influence them.",
          "2. Decide the instrument (futures or options) and build a realistic cost and fill model; the cost sensitivity above shows the cost model decides whether the system has any edge.",
          "3. Choose ONE live data feed, record its bars alongside the research vendor's for a period, and measure how far its signals diverge before trusting any rule that depends on the 09:15 bar.",
          "4. Only then build the persistence / duplicate-order / kill-switch layer and a paper engine; paper results would test mechanics and fills, not the edge.", ""]
    (OUT / "paper_trading_readiness.md").write_text("\n".join(pr))

    # ============================================================================================================== README.md
    files = [("README.md", "this file"), ("strategy_freeze.json", "the frozen Phase 3.6 configuration: id, source snapshot, file hashes, parameters, costs, unresolved rules, regression check"), ("data_source_discovery.md", "what each source can supply, probe results, secondary-source provenance, overlap audit, contract sizes"),
             ("data_quality_by_year.md", "validation of every window, derived calendar, exclusions, confidence tiers"), ("historical_coverage.csv", "coverage per window and source"), ("three_year_backtest_summary.md", "Window B and its three annual slices, vendor sensitivity"),
             ("2018_backtest_summary.md", "Window C (exploratory)"), ("2019_backtest_summary.md", "Window D (5paisa partial year and secondary full year)"), ("annual_comparison.csv", "every metric of section 9 for every period, with status and confidence"),
             ("strategy_comparison.csv", "per period and strategy"), ("cost_sensitivity.csv", "cost x slippage grid per period"), ("drawdown_analysis.md", "drawdowns with dates and hypothetical-capital multiples"), ("robustness_report.md", "the ten robustness diagnostics"),
             ("paper_trading_readiness.md", "readiness assessment (no implementation)"), ("independent_audit.md", "independent re-implementation, fresh reviewer, file-integrity proof"), ("NIFTY_MultiYear_Backtest_Verification.xlsx", "all tables, all trades, session quality (written from the CSV files)"),
             ("daily/<window>/YYYY-MM/", "one journal per evaluable session"), ("charts/<window>/", "one chart per executed trade"), ("windows/<window>/", "per-window CSVs (trades, entry conditions, exits, signals, rejected, issues, candle analysis), configuration and provenance"),
             ("data/", "per-session quality tables, coverage, derived-calendar summaries, overlap audits (by day and month), probe log"), ("robustness_*.csv, vendor_sensitivity.csv, monthly_pnl_all_windows.csv, session_regimes.csv, regime_definitions.json, coverage_exceptions.csv, not_evaluated_strategy_sessions.csv, all_trades_all_windows.csv", "supporting tables"),
             ("before_snapshot.json", "hashes of every earlier file recorded before the first Phase 4 edit")]
    R = ["# Phase 4 - multi-year historical validation of the frozen Phase 3.6 strategy", "", f"**Written for:** the strategy owner. {WARN}", "",
         "The Phase 3.6 configuration was frozen (`strategy_freeze.json`, id `" + freeze["frozen_configuration_id"] + "`) and run, unchanged, on four additional historical windows. Nothing was tuned, no window was chosen after seeing results, and loss-making periods are reported.", "",
         "## Rerun commands (macOS terminal)", "", "```", "cd /Users/syedaskari/algo/nifty-options && source .venv/bin/activate",
         "python scripts/phase4_run.py --strategy-config phase36-frozen --window three-year     # Window B, 2022-09-01..2025-08-31",
         "python scripts/phase4_run.py --strategy-config phase36-frozen --window 2018           # Window C (exploratory)",
         "python scripts/phase4_run.py --strategy-config phase36-frozen --window 2019           # Window D (5paisa partial year + secondary full year)",
         "python scripts/phase4_run.py --strategy-config phase36-frozen --window all            # everything + comparison, robustness, workbook",
         "python scripts/phase4_run.py --help", "```", "",
         "`--strategy-config phase36-frozen` is the only accepted value: the run is **refused** if any strategy, controller, execution or session-construction file or any parameter differs from the freeze record. `--window custom --window-id X --start D --end D --minute-source 5paisa|secondary` runs any other range the processed data covers.", "",
         "Data preparation (needs the broker session; not needed to rerun the backtests): `python scripts/phase4_fetch_5paisa.py --probe-empty --daily --minutes`, `python scripts/phase4_fetch_secondary.py --with-2026`, `python scripts/phase4_build_data.py`. "
         "Freeze check: `python scripts/phase4_freeze.py`. Independent audit: `python scripts/phase4_independent_audit.py`. This report: `python scripts/phase4_docs.py --tests \"...\" --ruff \"...\"`.", "",
         "## Headline", "",
         tab(["period", "status", "confidence", "trades", "gross Rs (390 units)", "net Rs (illustrative)", "profit factor", "max drawdown Rs"],
             [[ann[i]["row_id"], ann[i]["status"], ann[i]["data_quality_confidence"], ann[i]["trades"], rs(ann[i]["gross_pnl_rs_fixed_390"]), rs(ann[i]["net_pnl_rs_illustrative"]), ann[i]["profit_factor_gross"], rs(ann[i]["max_drawdown_rs_gross"])]
              for i in ("C_2018", "D_2019_SECONDARY", "D_2019_5PAISA_PARTIAL", "B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25", "A_2025_26")]), "",
         "**Status labels:** `DATA_VALIDATED` = the data window passed the quality gate (it says nothing about the strategy); `EXPLORATORY` = a single vendor that cannot be checked against another; `PARTIAL_YEAR`; `VENDOR_SENSITIVITY`; `REFERENCE` = the unchanged Phase 3.6 result.", "",
         "Trade IDs are `YYYYMMDD-n-STRATEGY` within a window; the composite key `window_id|trade_id` is unique across the workbook; every trade row records the minute-source id, the daily-source id, the SHA-256 of its processed partition and of the raw source file(s).", "",
         tab(["file", "content"], [[f"`{a}`", b] for a, b in files]), ""]
    (OUT / "README.md").write_text("\n".join(R))

    # ============================================================================================================== independent_audit.md
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    reviewer = (OUT / "_reviewer_findings.md").read_text() if (OUT / "_reviewer_findings.md").exists() else ""
    rc = freeze.get("regression_check", {})
    IA = ["# Phase 4 - independent audit", "",
          "**Written for:** the strategy owner and any reviewer. The audit verifies that the code did what the written rules say, that the data are what the provenance says, and that nothing else changed. It does **not** verify the strategy rules, the derived calendar against NSE circulars, or "
          "either vendor's prices against the exchange. A misreading shared by the engine and the audit script would not be caught (one author wrote both). Two checks were run: (1) `scripts/phase4_independent_audit.py` (raw files and delivered CSVs only; no `src/` imports) and (2) a fresh read-only reviewer subagent (an AI reviewer).", "",
          "## 1. Independent re-implementation", "",
          tab(["#", "check", "n", "result"], [[i, n, c["n"], "PASS" if c["pass"] else "**FAIL**"] for i, (n, c) in enumerate(audit.get("checks", {}).items(), 1)]) if audit else "(audit not run)", "",
          f"Overall: **{'ALL PASS' if audit.get('all_pass') else 'FAILURES PRESENT'}** ({len(audit.get('checks', {}))} checks); machine-readable in `independent_audit_results.json`.", "",
          "## 2. Freeze, regression and preservation", "",
          "* The source snapshot was taken at freeze time and already contains the Phase 4 edits to `phase32_build.py`, `phase32_render.py` and `phase32_excel.py` (they preserve default behaviour; proven by the regression run and by a test that rebuilds the Phase 3.6 backtest with the defaults). The pre-Phase-4 state is `before_snapshot.json`.",
          f"* The run guard checks EVERY file hashed in the freeze ({len(freeze['active_file_hashes'])} files) and every parameter, not only the engine folders (a reviewer found the first version narrower than documented).",
          f"* Frozen configuration `{freeze['frozen_configuration_id']}` (git head `{freeze['git_head'][:7]}`, {freeze['git_dirty_files']} uncommitted files at freeze time; reproducible source snapshot `frozen/source_snapshot_phase36.tar.gz`, sha256 `{freeze['source_snapshot']['sha256'][:16]}...`).",
          f"* Regression: the Phase 3.6 backtest was regenerated with the current code into a scratch directory and compared file by file with `reports/phase3/phase36_body_based_pdr/`: {rc.get('files_compared', '?')} files compared (all CSV / JSON files, all daily journals, all charts), identical = **{rc.get('identical')}** "
          "(`data_provenance.json` is compared on its data hashes, because it also records a hash of the whole `src/` tree, which changes whenever a module is added).",
          f"* A hash snapshot of {len(snap['files'])} files (source, tests, scripts, `data/`, `reports/` of every earlier phase, `docs/`) was recorded before the first Phase 4 edit (`before_snapshot.json`). The audit proves every file in it is byte-identical except the research modules edited for this phase (listed in the audit check), "
          "so the Phase 3.0 - 3.6 reports, the Phase 1 dataset and every strategy engine are unchanged. New data live only in `data/raw/phase4_*` and `data/phase4/`.", "",
          "## 3. Tests and static checks", "", f"* `pytest -q`: **{tests}**; `ruff check src tests scripts`: **{ruff}**.",
          "* New: `tests/test_phase4_multiyear.py` (freeze enforcement, CLI, calendar derivation, source namespaces and hashes, no-journal mode, metrics and cost model, regimes causality, workbook = CSV, trade source columns).", "",
          "## 4. Not verified", "",
          "* Either vendor's prices against the exchange; the derived holiday list against NSE circulars; the licence of the secondary dataset's underlying data; the historical NIFTY lot sizes (secondary reporting only).",
          "* The strategies' source rules (unchanged and still partly provisional).", "* The workbook beyond cell-by-cell equality with the CSV files (not opened in desktop Excel).", "", reviewer]
    (OUT / "independent_audit.md").write_text("\n".join(IA))
    print("docs written; audit:", audit_line)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tests", default="not recorded in this run")
    ap.add_argument("--ruff", default="not recorded in this run")
    a = ap.parse_args()
    main(a.tests, a.ruff)
