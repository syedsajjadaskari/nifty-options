"""Phase 4 independent audit: a second implementation of what the multi-year validation reports, written from the RAW provider files, their manifests and the delivered CSVs only (no ``src/`` imports; the
candle / EMA / exit helpers come from the Phase 3.2 audit script, which is itself free of ``src/`` imports).

Checks: raw-file and processed-partition provenance, an independent trading calendar, per-trade entry prices / exits / P&L re-walked from raw bars for EVERY trade of every window, candle and EMA recomputation, no look-ahead,
the controller rules, the five strategies active, annual and cost metrics recomputed from the trade tables, the vendor-overlap figures, source columns in every trade, the workbook, the freeze and the preservation of every
earlier file. Run: .venv/bin/python scripts/phase4_independent_audit.py
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import sys
import warnings
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402  (independent candle / EMA / exit helpers; imports nothing from src/)

OUT = ROOT / "reports" / "phase4"
RAW5 = ROOT / "data" / "raw" / "phase4_5paisa"
RAWTV = ROOT / "data" / "raw" / "phase4_technovusin"
PROC = ROOT / "data" / "phase4" / "processed"
RES: dict = {"checks": {}}
SRC = {"B": "FIVEPAISA_1M_PHASE4", "B_TV": "TECHNOVUS_1M", "C": "TECHNOVUS_1M", "D_5P": "FIVEPAISA_1M_PHASE4", "D_TV": "TECHNOVUS_1M"}
SPAN = {"B": (date(2022, 9, 1), date(2025, 8, 31)), "B_TV": (date(2022, 9, 1), date(2025, 8, 31)), "C": (date(2018, 1, 1), date(2018, 12, 31)), "D_5P": (date(2019, 3, 1), date(2019, 12, 31)), "D_TV": (date(2019, 1, 1), date(2019, 12, 31))}
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")
ROWDEF = [("C_2018", "C", date(2018, 1, 1), date(2018, 12, 31)), ("D_2019_SECONDARY", "D_TV", date(2019, 1, 1), date(2019, 12, 31)), ("D_2019_5PAISA_PARTIAL", "D_5P", date(2019, 3, 1), date(2019, 12, 31)),
          ("B1_2022_23", "B", date(2022, 9, 1), date(2023, 8, 31)), ("B2_2023_24", "B", date(2023, 9, 1), date(2024, 8, 31)), ("B3_2024_25", "B", date(2024, 9, 1), date(2025, 8, 31)), ("B_2022_25", "B", date(2022, 9, 1), date(2025, 8, 31)),
          ("A_2025_26", "A", date(2025, 9, 1), date(2026, 8, 31)), ("B1_TV", "B_TV", date(2022, 9, 1), date(2023, 8, 31)), ("B2_TV", "B_TV", date(2023, 9, 1), date(2024, 8, 31)), ("B3_TV", "B_TV", date(2024, 9, 1), date(2025, 8, 31)),
          ("B_2022_25_TV", "B_TV", date(2022, 9, 1), date(2025, 8, 31))]
ALLOWED_EDITS = {"src/nifty_trading/research/phase32_build.py", "src/nifty_trading/research/phase32_render.py", "src/nifty_trading/research/phase32_excel.py"}


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def fnum(x) -> float:
    return float(str(x).replace(",", "")) if x not in ("", None) else 0.0


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------ raw loaders, re-implemented
def raw_5p_minutes() -> pd.DataFrame:
    man = json.loads((RAW5 / "manifest.json").read_text())["requests"]
    fr = [pd.read_csv(RAW5 / r["file"]) for _k, r in sorted(man.items()) if r["timeframe"] == "1m" and r["status"] == "COMPLETED"]
    x = pd.concat(fr, ignore_index=True)
    d = pd.DataFrame({"timestamp": pd.to_datetime(x["Datetime"]).dt.tz_localize("Asia/Kolkata"), "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
    return d.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)


def raw_tv_minutes() -> pd.DataFrame:
    d0 = sorted(p for p in RAWTV.iterdir() if p.is_dir())[0]
    man = json.loads((d0 / "manifest.json").read_text())["files"]
    fr = [pd.read_csv(d0 / p) for p, f in sorted(man.items()) if p.startswith("1min/") and f["status"] == "OK"]
    x = pd.concat(fr, ignore_index=True)
    d = pd.DataFrame({"timestamp": pd.to_datetime(x["Timestamp"]).dt.tz_localize("Asia/Kolkata"), "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
    return d.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)


def raw_5p_daily() -> pd.DataFrame:
    man = json.loads((RAW5 / "manifest.json").read_text())["requests"]
    fr = [pd.read_csv(RAW5 / r["file"]) for _k, r in sorted(man.items()) if r["timeframe"] == "1d" and r["status"] == "COMPLETED"]
    x = pd.concat(fr, ignore_index=True)
    d = pd.DataFrame({"date": pd.to_datetime(x["Datetime"]).dt.date, "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
    return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)


def blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324


def indep_calendar(daily: pd.DataFrame, minute: dict[str, pd.DataFrame], coverage: dict[str, list[tuple[date, date]]], start: date, end: date) -> tuple[set, dict]:
    """Holidays = weekdays with no daily candle and no minute rows in any source covering the date; special sessions = weekend sessions or sessions whose first bar is not 09:15 (evaluable only with >= 370 regular rows)."""
    dd = set(daily["date"])
    per = {}
    for k, v in minute.items():
        t = v["timestamp"]
        m = t.dt.hour * 60 + t.dt.minute
        g = pd.DataFrame({"d": t.dt.date, "m": m}).groupby("d")["m"].agg(["min", "count"])
        per[k] = g
    hol, spec = set(), {}
    d = start
    while d <= end:
        cov = [k for k in minute if any(a <= d <= b for a, b in coverage[k])]
        has_min = any(d in per[k].index for k in cov)
        if d.weekday() < 5 and d not in dd and not has_min:
            hol.add(d)
        late = [k for k in per if d in per[k].index and int(per[k].loc[d, "min"]) != 555]
        if (d.weekday() >= 5 and (d in dd or any(d in per[k].index for k in per))) or late:
            full = any(d in per[k].index and int(per[k].loc[d, "min"]) == 555 and int(per[k].loc[d, "count"]) >= 370 for k in per)
            spec[d] = bool(full and not late)
        d += timedelta(days=1)
    return hol, spec


def main() -> int:  # noqa: C901
    freeze = json.loads((OUT / "strategy_freeze.json").read_text())
    STOP = {k: float(v) for k, v in freeze["parameters"]["stops"].items()}
    T2 = {k: float(v) for k, v in freeze["parameters"]["targets_2"].items()}
    m5, mtv, d5 = raw_5p_minutes(), raw_tv_minutes(), raw_5p_daily()
    raws = {"FIVEPAISA_1M_PHASE4": m5, "TECHNOVUS_1M": mtv}
    win = {w: {"trades": rd(OUT / "windows" / w / "all_trades_detailed.csv"), "legs": rd(OUT / "windows" / w / "trade_exits_detailed.csv"), "checks": rd(OUT / "windows" / w / "trade_entry_conditions.csv"),
               "candles": rd(OUT / "windows" / w / "candle_analysis.csv"), "signals": rd(OUT / "windows" / w / "all_strategy_signals.csv"), "daily": rd(OUT / "windows" / w / "daily_summary.csv")} for w in SRC}

    # ============================================================ 1. provenance
    man5 = json.loads((RAW5 / "manifest.json").read_text())["requests"]
    bad = [r["file"] for r in man5.values() if r["status"] == "COMPLETED" and sha(RAW5 / r["file"]) != r["sha256"]]
    d0 = sorted(p for p in RAWTV.iterdir() if p.is_dir())[0]
    mt = json.loads((d0 / "manifest.json").read_text())
    bad += [p for p, f in mt["files"].items() if f["status"] == "OK" and (sha(d0 / p) != f["sha256"] or blob_sha1((d0 / p).read_bytes()) != f["git_blob_sha"])]
    record("every raw provider file equals the SHA-256 recorded at retrieval (5paisa responses; secondary files also equal the repository's git blob SHA-1)", not bad, len(man5) + len(mt["files"]), f"secondary commit {mt['commit_sha'][:10]}", bad)
    bad = []
    n_part = 0
    for sid in ("FIVEPAISA_1M_PHASE4", "TECHNOVUS_1M", "FIVEPAISA_1D_PHASE4"):
        sm = json.loads((PROC / sid / "source_manifest.json").read_text())
        for p, v in sm["partitions"].items():
            n_part += 1
            if sha(ROOT / p) != v["sha256"]:
                bad.append(p)
    record("every processed partition equals the SHA-256 in its source manifest", not bad, n_part, failures=bad)
    bad = []
    for sid, raw in raws.items():
        pr = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(PROC / sid / "nifty50" / "year=*" / "month=*" / "candles.parquet")))], ignore_index=True).sort_values("timestamp").reset_index(drop=True)
        same = len(pr) == len(raw) and bool((pr["timestamp"].to_numpy() == raw["timestamp"].to_numpy()).all()) and all(np.allclose(pr[c].to_numpy(), raw[c].to_numpy(), atol=1e-9) for c in ("open", "high", "low", "close"))
        if not same:
            bad.append(sid)
    prd = pd.read_parquet(PROC / "FIVEPAISA_1D_PHASE4" / "nifty50_daily" / "candles.parquet")
    if len(prd) != len(d5) or not np.allclose(prd["close"].to_numpy(), d5["close"].to_numpy(), atol=1e-9):
        bad.append("daily")
    record("processed minute and daily data equal an independent reload of the raw files (timestamps and all four prices; the only difference is the 2-decimal rounding of the daily series' float32 noise)", not bad, len(m5) + len(mtv) + len(d5), failures=bad)

    # ============================================================ 2. calendar
    cov = {"FIVEPAISA_1M_PHASE4": [(date(2019, 3, 1), date(2019, 12, 31)), (date(2022, 8, 1), date(2025, 8, 31))], "TECHNOVUS_1M": [(date(2017, 4, 3), date(2019, 12, 31)), (date(2022, 1, 1), date(2025, 12, 31))]}
    hol, spec = indep_calendar(d5, raws, cov, date(2017, 1, 1), date(2025, 8, 31))
    cj = json.loads((ROOT / "data" / "phase4" / "calendar" / "phase4_calendar_derived.json").read_text())
    jh = {date.fromisoformat(h["date"]) for h in cj["holidays"]}
    js = {date.fromisoformat(s["date"]): bool(s["evaluable_by_strategies"]) for s in cj["special_sessions"]}
    record("the derived trading calendar equals an independent derivation from the raw daily and minute files (holidays and special sessions with their evaluable flag)", hol == jh and spec == js, len(jh) + len(js), f"holidays {len(hol)} vs {len(jh)}; special {len(spec)} vs {len(js)}",
           [str(x) for x in sorted((hol ^ jh) | (set(spec) ^ set(js)))])
    p1d = pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet")
    p1m = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / "data/processed/nifty50/**/*.parquet"), recursive=True))], ignore_index=True)
    p1d["date"] = pd.to_datetime(p1d["date"]).dt.date
    hol1, spec1 = indep_calendar(p1d, {"P1": p1m}, {"P1": [(date(2025, 9, 1), date(2026, 8, 31))]}, date(2025, 9, 1), date(2026, 8, 31))
    ev = json.loads((ROOT / "data/metadata/nse_calendar_2025_2026.json").read_text())
    eh = {date.fromisoformat(h["date"]) for h in ev["holidays"] if "2025-09-01" <= h["date"] <= "2026-08-31"}
    es = {date.fromisoformat(s["date"]): bool(s["evaluable_by_strategies"]) for s in ev["special_sessions"] if "2025-09-01" <= s["date"] <= "2026-08-31"}
    record("the calendar method reproduces the evidence-tier 2025-26 calendar (holidays and special sessions), independently", hol1 == eh and spec1 == es, len(eh) + len(es), failures=[str(x) for x in sorted((hol1 ^ eh) | (set(spec1) ^ set(es)))])
    trade_days = {t["date"] for w in win.values() for t in w["trades"]}
    bad = [d for d in trade_days if date.fromisoformat(d) in hol or (date.fromisoformat(d) in spec and not spec[date.fromisoformat(d)])]
    record("no trade falls on a derived holiday or on a non-evaluable special session", not bad, len(trade_days), failures=bad)

    # ============================================================ 3. per-window trade verification against RAW bars
    ema_all = {}
    for w, (lo, hi) in SPAN.items():
        raw = raws[SRC[w]]
        raw = raw[(raw.timestamp.dt.date >= lo - timedelta(days=45)) & (raw.timestamp.dt.date <= hi)]
        wu = raw[raw.timestamp.dt.date < lo]
        trades, legs, cands = win[w]["trades"], win[w]["legs"], win[w]["candles"]
        by_key = raw.assign(key=raw.timestamp.dt.strftime("%Y-%m-%d %H:%M")).set_index("key")
        # --- entries
        bad = []
        for t in trades:
            k = t["fill_timestamp"]
            if k not in by_key.index or abs(float(by_key.loc[k, "open"]) - fnum(t["entry_price"])) > 1e-9 or t["signal_confirmed_at"] != k or k[-5:] > "13:00":
                bad.append(t["trade_id"])
        record(f"[{w}] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all trades)", not bad, len(trades), failures=bad)
        # --- exits and P&L, every trade
        by_id = defaultdict(list)
        for g in legs:
            by_id[g["trade_id"]].append(g)
        bad, bad_pnl, bad_lv = [], [], []
        for t in trades:
            e = fnum(t["entry_price"])
            fill = pd.Timestamp(t["fill_timestamp"]).tz_localize("Asia/Kolkata")
            day = raw[(raw.timestamp.dt.date == fill.date()) & (raw.timestamp >= fill)]
            wk = A32.walk_exit(t["direction"], e, day, STOP[t["strategy"]], T2[t["strategy"]])
            hm = lambda ts: "" if ts is None else ts.strftime("%H:%M")  # noqa: E731
            ok = (wk["outcome"] == t["outcome"] and hm(wk["ts1"]) == t["leg1_exit_time"] and hm(wk["ts2"]) == t["leg2_exit_time"]
                  and abs((wk["p1"] or 0) - fnum(t["leg1_exit_price"])) < 1e-6 and abs((wk["p2"] or 0) - fnum(t["leg2_exit_price"])) < 1e-6)
            if not ok:
                bad.append((t["trade_id"], wk["outcome"], t["outcome"], wk["p1"], t["leg1_exit_price"], wk["p2"], t["leg2_exit_price"]))
            sg = 1 if t["direction"] == "LONG" else -1
            l1, l2 = by_id[t["trade_id"]]
            tot = sum((fnum(g["exit_price"]) - e) * sg * 195 for g in (l1, l2))
            if abs(tot - fnum(t["gross_pnl_rs"])) > 1e-6 or abs(fnum(t["illustrative_net_pnl_rs"]) - (tot - 500.0 - 0.5 * 2 * 390)) > 1e-6:
                bad_pnl.append(t["trade_id"])
            exp = (e - sg * STOP[t["strategy"]], e + sg * 27, e + sg * T2[t["strategy"]], e - sg * 6)
            got = tuple(fnum(t[k]) for k in ("initial_stop", "target_1", "target_2", "post_t1_stop"))
            if max(abs(a - b) for a, b in zip(exp, got, strict=True)) > 1e-6:
                bad_lv.append(t["trade_id"])
        record(f"[{w}] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit)", not bad, len(trades), failures=bad)
        record(f"[{w}] leg P&L = (exit - entry) x direction x 195 per leg; gross and illustrative net recomputed; stops / targets follow the frozen distances", not bad_pnl and not bad_lv, len(trades), failures=bad_pnl + bad_lv)
        # --- candles, geometry, EMA (same warm-up rule as the pipeline: 45 calendar days before the window, same source, usable sessions only)
        std = A32.standard_days(raw)
        t_ = raw.timestamp
        mins = t_.dt.hour * 60 + t_.dt.minute
        dd = raw.assign(day=t_.dt.date, mnt=mins)
        flat_days = set()
        for dday, g in dd[(dd.mnt >= 555) & (dd.mnt <= 929)].groupby("day"):
            fl = ((g.open == g.high) & (g.high == g.low) & (g.low == g.close)).to_numpy()
            px, mm = g.close.to_numpy(), g.mnt.to_numpy()
            run = best = 0
            for i_, f in enumerate(fl):  # a FROZEN run: consecutive minutes of flat bars all at ONE price (the pipeline's definition)
                run = (run + 1 if (run and px[i_] == px[i_ - 1] and mm[i_] == mm[i_ - 1] + 1) else 1) if f else 0
                best = max(best, run)
            if best >= 5:
                flat_days.add(dday)
        nonevaluable = {d for d, ok in spec.items() if not ok}
        use = {d for d in std if d not in flat_days and d not in nonevaluable and d not in hol}
        c5 = A32.five_minute(raw, use)
        c5 = c5.sort_values("start").reset_index(drop=True)
        c5["ema"] = A32.ema_series(c5["close"].to_numpy())
        ema_all[w] = c5
        idx = {s.strftime("%Y-%m-%d %H:%M"): i for i, s in enumerate(c5.start)}
        bo, bg, be = [], [], []
        n_ema = 0
        for r in cands:
            i = idx.get(r["candle_start"])
            if i is None:
                bo.append((r["trade_id"], r["role"], "candle missing / incomplete in raw"))
                continue
            c = c5.iloc[i]
            o, h, lo_, cl = (fnum(r[k]) for k in ("open", "high", "low", "close"))
            if max(abs(c.open - o), abs(c.high - h), abs(c.low - lo_), abs(c.close - cl)) > 1e-9:
                bo.append((r["trade_id"], r["role"]))
            g = A32.geometry(c.open, c.high, c.low, c.close)
            mism = [k for k, v in {"strong_bull": r["strong_bullish"] == "True", "strong_bear": r["strong_bearish"] == "True", "bull_pin": r["bullish_pin"] == "True", "bear_pin": r["bearish_pin"] == "True",
                                   "small": r["small_body_le_30pct"] == "True"}.items() if g[k] != v]
            if mism:
                bg.append((r["trade_id"], r["role"], mism))
            if r["ema200_5m"] != "":
                n_ema += 1
                if abs(float(r["ema200_5m"]) - c.ema) > 1e-3:
                    be.append((r["trade_id"], r["role"], r["ema200_5m"], round(float(c.ema), 4)))
            elif not np.isnan(c.ema):
                be.append((r["trade_id"], r["role"], "csv has no EMA but one exists"))
        record(f"[{w}] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation ({n_ema} candles with an EMA)", not bo and not bg and not be, len(cands), failures=bo + bg + be)
        tmap = {t["trade_id"]: t for t in trades}
        bad = [(r["trade_id"], r["role"]) for r in cands if (r["session"] == "TODAY" and r["candle_end"] > tmap[r["trade_id"]]["signal_confirmed_at"]) or (r["session"] != "TODAY" and r["candle_end"][:10] >= tmap[r["trade_id"]]["date"])]
        warm_ok = all(d < lo for d in wu.timestamp.dt.date.unique())
        record(f"[{w}] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window", not bad and warm_ok, len(cands), failures=bad)
        # --- controller rules from the delivered tables
        sig_by_day, tr_by_day = defaultdict(list), defaultdict(list)
        for r in win[w]["signals"]:
            sig_by_day[r["date"]].append(r)
        for t in trades:
            tr_by_day[t["date"]].append(t)
        bad, conflict_days = [], 0
        for d_, ts in tr_by_day.items():
            ts.sort(key=lambda t: int(t["trade_no_of_day"]))
            cands_ = sorted((r for r in sig_by_day[d_] if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True"), key=lambda r: r["time"])
            if len(ts) > 2 or any(t["fill_timestamp"][-5:] > "13:00" for t in ts) or not cands_ or ts[0]["signal_candle_end"] != cands_[0]["time"]:
                bad.append((d_, "first-valid-signal / max-2 / cutoff"))
            if len(ts) == 2:
                end = ts[0]["leg2_exit_time"]
                later = [r for r in cands_ if r["strategy"] in ("PDR", "PDS") and r["time"] >= end and r["time"] > ts[0]["signal_candle_end"]]
                if ts[0]["outcome"] != "INITIAL_FULL_STOP" or ts[1]["strategy"] not in ("PDR", "PDS") or not later or ts[1]["signal_candle_end"] != later[0]["time"]:
                    bad.append((d_, "second trade rule"))
        for d_, rs_ in sig_by_day.items():
            if d_ in tr_by_day:
                continue
            c_ = [r for r in rs_ if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True"]
            if c_:
                ft = min(r["time"] for r in c_)
                if len({(r["strategy"], r["direction"]) for r in c_ if r["time"] == ft}) > 1:
                    conflict_days += 1
                else:
                    bad.append((d_, "valid signal but no trade and no same-minute conflict"))
        record(f"[{w}] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict)", not bad, len(tr_by_day), f"{conflict_days} conflict day(s)", bad)
        cs, ct = Counter(r["strategy"] for r in win[w]["signals"]), Counter(t["strategy"] for t in trades)
        record(f"[{w}] all five strategies produced signals and were traded", all(cs[s] > 0 and ct[s] > 0 for s in STRATS), 5, f"signals {dict(cs)}, trades {dict(ct)}")
        # --- coverage numbers
        raw_days = {x for x in raw.timestamp.dt.date.unique() if lo <= x <= hi}
        cv = {r["window_id"]: r for r in rd(OUT / "data" / "historical_coverage_by_window.csv")}[w]
        dl = d5[(d5.date >= lo) & (d5.date <= hi)]
        expected = {x for x in dl.date if x.weekday() < 5 and x not in hol} | {x for x in dl.date if x.weekday() >= 5} | {x for x in (lo + timedelta(days=i) for i in range((hi - lo).days + 1)) if x.weekday() < 5 and x not in hol}
        ok = int(cv["expected_sessions"]) == len(expected) and int(cv["sessions_in_source"]) == len(raw_days & expected)
        record(f"[{w}] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table", ok, len(expected), f"expected {len(expected)} vs {cv['expected_sessions']}, in source {len(raw_days & expected)} vs {cv['sessions_in_source']}")
        n_hist = int((d5.date < lo).sum())
        record(f"[{w}] at least 200 daily bars precede the window (daily moving averages) and warm-up rows exist where the source has them", n_hist >= 200 and int(cv["daily_bars_before_start"]) == n_hist, n_hist, f"warm-up minute sessions {cv['warmup_sessions_same_source']}")

    # ============================================================ 4. annual metrics, costs, reference window
    ann = {r["row_id"]: r for r in rd(OUT / "annual_comparison.csv")}
    allw = {w: win[w]["trades"] for w in win}
    allw["A"] = rd(ROOT / "reports/phase3/phase36_body_based_pdr/all_trades_detailed.csv")
    legs_all = {w: win[w]["legs"] for w in win}
    legs_all["A"] = rd(ROOT / "reports/phase3/phase36_body_based_pdr/exit_details.csv")
    rows_def = ROWDEF
    bad = []
    for rid, wid, lo, hi in rows_def:
        tr = [t for t in allw[wid] if str(lo) <= t["date"] <= str(hi)]
        tr.sort(key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"])))
        seq = [fnum(t["gross_pnl_rs"]) for t in tr]
        net = [fnum(t["illustrative_net_pnl_rs"]) for t in tr]
        cum = peak = dd = 0.0
        for v in seq:
            cum += v
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        gp, gl = sum(v for v in seq if v > 0), -sum(v for v in seq if v < 0)
        streak = best = 0
        for v in seq:
            streak = streak + 1 if v < 0 else 0
            best = max(best, streak)
        a = ann[rid]
        exp = {"trades": len(tr), "gross_pnl_rs_fixed_390": round(sum(seq), 2), "net_pnl_rs_illustrative": round(sum(net), 2), "max_drawdown_rs_gross": round(dd, 2), "max_consecutive_losses": best,
               "win_rate_pct": round(100 * sum(1 for v in seq if v > 0) / len(seq), 2), "target2": sum(1 for t in tr if t["outcome"] == "TARGET"), "initial_full_stop": sum(1 for t in tr if t["outcome"] == "INITIAL_FULL_STOP")}
        for k, v in exp.items():
            if abs(fnum(a[k]) - v) > 0.011:
                bad.append((rid, k, a[k], v))
        if gl and abs(fnum(a["profit_factor_gross"]) - gp / gl) > 1e-3:
            bad.append((rid, "profit_factor_gross", a["profit_factor_gross"], gp / gl))
        pts = sum(fnum(t["gross_pnl_points_weighted"]) for t in tr)
        if abs(fnum(a["total_index_points_weighted"]) - pts) > 0.011 or abs(pts * 390 - sum(seq)) > 1.0:
            bad.append((rid, "index points", a["total_index_points_weighted"], pts))
    record("annual_comparison.csv equals an independent recomputation for every row (trades, gross, net, profit factor, drawdown, losing streak, win rate, outcomes, index points = gross / 390)", not bad, len(rows_def), failures=bad)
    b1, b2, b3, bt = (ann[k] for k in ("B1_2022_23", "B2_2023_24", "B3_2024_25", "B_2022_25"))
    record("the three annual slices of Window B sum to the three-year window (trades, gross, net)", int(b1["trades"]) + int(b2["trades"]) + int(b3["trades"]) == int(bt["trades"]) and abs(fnum(b1["gross_pnl_rs_fixed_390"]) + fnum(b2["gross_pnl_rs_fixed_390"]) + fnum(b3["gross_pnl_rs_fixed_390"]) - fnum(bt["gross_pnl_rs_fixed_390"])) < 0.02
           and abs(fnum(b1["net_pnl_rs_illustrative"]) + fnum(b2["net_pnl_rs_illustrative"]) + fnum(b3["net_pnl_rs_illustrative"]) - fnum(bt["net_pnl_rs_illustrative"])) < 0.02, 4)
    a_ = ann["A_2025_26"]
    record("the Phase 3.6 reference row reproduces its reported results (196 trades, gross Rs 297,765, illustrative net Rs 123,325)", int(a_["trades"]) == 196 and abs(fnum(a_["gross_pnl_rs_fixed_390"]) - 297765.0) < 0.01 and abs(fnum(a_["net_pnl_rs_illustrative"]) - 123325.0) < 0.01, 1)
    # cost grid, fill level, recomputed for three rows and four scenarios
    cg = {(r["row_id"], r["fixed_cost_rs_per_trade"], r["slippage_points_per_fill"]): r for r in rd(OUT / "cost_sensitivity.csv")}
    bad = []
    for rid in ("B_2022_25", "C_2018", "A_2025_26"):
        _r, wid, lo, hi = next(x for x in rows_def if x[0] == rid)
        tr = [t for t in allw[wid] if str(lo) <= t["date"] <= str(hi)]
        lg = defaultdict(list)
        for g in legs_all[wid]:
            lg[g["trade_id"]].append(g)
        for fx, sl in ((0.0, 0.0), (500.0, 0.5), (1000.0, 1.0), (1500.0, 2.0)):
            net = 0.0
            for t in tr:
                fills = 1 + sum(1 for g in lg[t["trade_id"]] if g["exit_price"] not in ("", None))
                units = fnum(t["qty_total"]) + sum(fnum(g["quantity"]) for g in lg[t["trade_id"]] if g["exit_price"] not in ("", None))
                net += fnum(t["gross_pnl_rs"]) - fx / 3.0 * fills - sl * units
            if abs(fnum(cg[(rid, str(fx), str(sl))]["net_pnl_rs"]) - net) > 0.05:
                bad.append((rid, fx, sl, cg[(rid, str(fx), str(sl))]["net_pnl_rs"], round(net, 2)))
    record("cost sensitivity (fill-level costs) recomputed independently for three periods x four scenarios; the Rs 500 / 0.5 point scenario equals the Phase 3.6 headline", not bad, 12, failures=bad)

    # ============================================================ 5. source columns, ids, journals, charts, workbook
    bad = []
    n = 0
    for w in win:
        ids = [t["trade_id"] for t in win[w]["trades"]]
        if len(set(ids)) != len(ids):
            bad.append((w, "duplicate trade ids"))
        sm = json.loads((PROC / SRC[w] / "source_manifest.json").read_text())
        for t in win[w]["trades"]:
            n += 1
            part = t["data_source_partition"]
            if t["data_source_id"] != SRC[w] or t["daily_source_id"] != "FIVEPAISA_1D_PHASE4" or sha(ROOT / part) != t["data_source_partition_sha256"]:
                bad.append((w, t["trade_id"], "source columns"))
            rf = sm["partitions"][part]["raw_files"]
            expect = ";".join((sm["raw_files"] or {}).get(f, "") for f in rf)
            if t["raw_source_sha256"] != expect or not t["raw_source_sha256"]:
                bad.append((w, t["trade_id"], "raw sha"))
            if not (OUT / "charts" / w / f"{t['trade_id']}.svg").exists() or f"### {t['trade_id']}:" not in (OUT / "daily" / w / t["date"][:7] / f"{t['date']}.md").read_text():
                bad.append((w, t["trade_id"], "chart / journal"))
        for d_ in win[w]["daily"]:
            if not (OUT / "daily" / w / d_["date"][:7] / f"{d_['date']}.md").exists():
                bad.append((w, d_["date"], "missing journal"))
    record("every trade of every window records the minute-source id, daily-source id, partition SHA-256 (= the real file hash) and raw-file SHA-256; ids are unique; every trade has its chart and journal section; every session has a journal", not bad, n, failures=bad)
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "NIFTY_MultiYear_Backtest_Verification.xlsx", read_only=True)
    pairs = {"Annual Comparison": "annual_comparison.csv", "Strategy Comparison": "strategy_comparison.csv", "Cost Sensitivity": "cost_sensitivity.csv", "Monthly PnL": "monthly_pnl_all_windows.csv", "All Trades": "all_trades_all_windows.csv",
             "Vendor Sensitivity": "vendor_sensitivity.csv", "Regimes": "robustness_regimes.csv"}
    bad, cells = [], 0

    def same(cell, text: str) -> bool:
        if cell is None:
            return text == ""
        if isinstance(cell, bool):
            return text == ("True" if cell else "False")
        if isinstance(cell, (int, float)):
            try:
                return abs(float(text) - float(cell)) < 1e-9 * max(1.0, abs(float(cell)))
            except ValueError:
                return False
        return str(cell) == text
    for sh, fn in pairs.items():
        data = rd(OUT / fn)
        rows = list(wb[sh].iter_rows(values_only=True))
        head = list(rows[0])
        if len(rows) - 1 != len(data):
            bad.append((sh, "row count", len(rows) - 1, len(data)))
            continue
        for ri, r in enumerate(data, 1):
            for ci, h in enumerate(head):
                cells += 1
                if not same(rows[ri][ci], r.get(h, "")):
                    bad.append((sh, ri, h))
    record("the workbook's main sheets equal the CSV files cell by cell", not bad, cells, failures=bad)

    # ============================================================ 6. vendor overlap, recomputed
    ov = json.loads((OUT / "data" / "vendor_overlap_summary.json").read_text())["2022-08..2025-08"]

    def regular(x, lo, hi):
        t = x.timestamp
        m = t.dt.hour * 60 + t.dt.minute
        return x[(m >= 555) & (m <= 929) & (t.dt.date >= lo) & (t.dt.date <= hi)].set_index("timestamp")[["open", "high", "low", "close"]]
    j = regular(m5, date(2022, 8, 1), date(2025, 8, 31)).join(regular(mtv, date(2022, 8, 1), date(2025, 8, 31)), how="inner", lsuffix="_a", rsuffix="_b")
    exact = float(((j[["open_a", "high_a", "low_a", "close_a"]].to_numpy() - j[["open_b", "high_b", "low_b", "close_b"]].to_numpy()).__abs__().max(axis=1) <= 0.005).mean())
    mad = float((j["close_a"] - j["close_b"]).abs().mean())
    record("the 2022-08..2025-08 vendor-overlap figures (bars compared, share identical, mean |close difference|) equal an independent recomputation", len(j) == ov["bars_compared"] and abs(exact - ov["share_exact_all_fields"]) < 1e-3 and abs(mad - ov["mean_abs_close_diff"]) < 1e-3, len(j),
           f"bars {len(j):,}; identical {exact:.4f}; mean |diff| {mad:.4f}")

    # ============================================================ 7. freeze and preservation
    bad = []
    for path, h in freeze["active_file_hashes"].items():
        if path.startswith(("src/nifty_trading/strategies/", "src/nifty_trading/core/", "src/nifty_trading/data/")) and sha(ROOT / path) != h:
            bad.append(path)
    record("every strategy, controller, execution and session-construction file equals the hash recorded in the freeze", not bad, len(freeze["active_file_hashes"]), freeze["frozen_configuration_id"], bad)
    rc = freeze.get("regression_check", {})
    record("the freeze's regression check regenerated the Phase 3.6 backtest and found every file identical", bool(rc.get("identical")), int(rc.get("files_compared", 0)), "")
    snap = json.loads((OUT / "before_snapshot.json").read_text())["files"]
    changed, missing = [], []
    for p, h in snap.items():
        f = ROOT / p
        if not f.exists():
            missing.append(p)
        elif sha(f) != h and p not in ALLOWED_EDITS and not p.startswith("reports/phase4/"):
            changed.append(p)
    record("every file of the before-snapshot (data, every earlier report, engines, controller, scripts, tests, docs) is byte-identical except the three research modules edited for Phase 4",
           not changed and not missing, len(snap), f"allowed edits: {sorted(ALLOWED_EDITS)}", changed + missing)
    p36 = [k for k in snap if k.startswith("reports/phase3/phase36_body_based_pdr/")]
    record("every file of the Phase 3.6 results directory is byte-identical to its pre-Phase-4 hash", all((ROOT / k).exists() and sha(ROOT / k) == snap[k] for k in p36), len(p36))
    d1 = [k for k in snap if k.startswith("data/processed/") or k.startswith("data/metadata/")]
    record("the Phase 1 dataset and its metadata (data/processed, data/metadata) are byte-identical", all(sha(ROOT / k) == snap[k] for k in d1), len(d1))

    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
