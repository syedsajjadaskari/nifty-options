"""Phase 5 independent audit: a second implementation of what the BANKNIFTY / SENSEX backtests report, written from the RAW provider files, their manifests, the broker's instrument master copy and the delivered CSVs only
(no ``src/`` imports; the candle / EMA / exit helpers come from the Phase 3.2 audit script, which is itself free of ``src/`` imports).

Checks per index: instrument identity (master + probes), raw-file and processed-partition provenance, an independent trading calendar and closing-auction detection, per-trade entry / exit / P&L re-walked from raw bars for EVERY
trade of every window, candle and EMA recomputation, previous-day levels, no look-ahead, the controller rules, the five strategies active, annual and strategy metrics recomputed from the trade tables, the vendor-overlap
figures, source columns in every trade, journals / charts / option-feasibility block present and free of invented option numbers, the workbook, the frozen configuration and the preservation of every NIFTY artefact.
Writes reports/phase5/independent_audit_results.json and reports/phase5/_sample_review.md. Run: .venv/bin/python scripts/phase5_independent_audit.py
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
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

OUT = ROOT / "reports" / "phase5"
RES: dict = {"checks": {}}
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")
CAS_FIRST = date(2026, 8, 3)
IDX = {"BANKNIFTY": {"key": "banknifty", "exch": "N", "code": 999920005, "sec_file": "bank-nifty-1m-data.csv", "level": (15000, 80000)},
       "SENSEX": {"key": "sensex", "exch": "B", "code": 999901, "sec_file": "sensex_candlestick_data.csv", "level": (25000, 100000)}}
SPAN = {"M": (date(2022, 9, 1), date(2026, 8, 31)), "MS": (date(2022, 9, 1), date(2024, 3, 22)), "C": (date(2018, 1, 1), date(2018, 12, 31)), "D_5P": (date(2019, 3, 1), date(2019, 12, 31)), "D_TV": (date(2019, 1, 1), date(2019, 12, 31))}
SOURCE_KIND = {"M": "5p", "MS": "sec", "C": "sec", "D_5P": "5p", "D_TV": "sec"}
ROWDEF = [("M_2022_23", "M", date(2022, 9, 1), date(2023, 8, 31)), ("M_2023_24", "M", date(2023, 9, 1), date(2024, 8, 31)), ("M_2024_25", "M", date(2024, 9, 1), date(2025, 8, 31)), ("M_2025_26", "M", date(2025, 9, 1), date(2026, 8, 31)),
          ("M_ALL", "M", date(2022, 9, 1), date(2026, 8, 31)), ("M_TO_2024_03_22", "M", date(2022, 9, 1), date(2024, 3, 22)), ("MS_2022_09_2024_03", "MS", date(2022, 9, 1), date(2024, 3, 22)), ("C_2018", "C", date(2018, 1, 1), date(2018, 12, 31)),
          ("D_2019_5P_PARTIAL", "D_5P", date(2019, 3, 1), date(2019, 12, 31)), ("D_2019_SECONDARY", "D_TV", date(2019, 1, 1), date(2019, 12, 31))]


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


def blob_sha1(b: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(b)).encode() + b"\0" + b).hexdigest()  # noqa: S324


# ------------------------------------------------------------------------------------------------ raw loaders, re-implemented
def raw_5p(key: str, tf: str) -> pd.DataFrame:
    raw = ROOT / "data" / "raw" / key / "5paisa"
    man = json.loads((raw / "manifest.json").read_text())["requests"]
    x = pd.concat([pd.read_csv(raw / r["file"]) for _k, r in sorted(man.items()) if r["timeframe"] == tf and r["status"] == "COMPLETED"], ignore_index=True)
    if tf == "1d":
        d = pd.DataFrame({"date": pd.to_datetime(x["Datetime"]).dt.date, "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
        return d.drop_duplicates("date", keep="last").sort_values("date").reset_index(drop=True)
    d = pd.DataFrame({"timestamp": pd.to_datetime(x["Datetime"]).dt.tz_localize("Asia/Kolkata"), "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
    return d.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)


def sec_dir(key: str) -> Path:
    return sorted(p for p in (ROOT / "data" / "raw" / key / "secondary_kapri").iterdir() if p.is_dir())[0]


def raw_sec(key: str, fname: str) -> pd.DataFrame:
    x = pd.read_csv(sec_dir(key) / fname)
    ts = pd.to_datetime(x["Date"].astype(str) + " " + x["Time"].astype(str), format="%d-%m-%Y %H:%M:%S")
    d = pd.DataFrame({"timestamp": ts.dt.tz_localize("Asia/Kolkata"), "open": x["Open"].round(2), "high": x["High"].round(2), "low": x["Low"].round(2), "close": x["Close"].round(2)})
    return d.drop_duplicates("timestamp", keep="last").sort_values("timestamp").reset_index(drop=True)


def indep_calendar(daily: pd.DataFrame, minute: dict[str, pd.DataFrame], coverage: dict[str, list[tuple[date, date]]], start: date, end: date) -> tuple[set, dict]:
    dd = set(daily["date"])
    per = {}
    for k, v in minute.items():
        t = v["timestamp"]
        m = t.dt.hour * 60 + t.dt.minute
        per[k] = pd.DataFrame({"d": t.dt.date, "m": m}).groupby("d")["m"].agg(["min", "count"])
    hol, spec = set(), {}
    d = start
    while d <= end:
        cov = [k for k in minute if any(a <= d <= b for a, b in coverage[k])]
        has_min = any(d in per[k].index for k in cov)
        if d.weekday() < 5 and d not in dd and not has_min:
            hol.add(d)
        late = [k for k in per if d in per[k].index and int(per[k].loc[d, "min"]) != 555]
        if d.weekday() < 5 and late and any(d in per[k].index and int(per[k].loc[d, "min"]) == 555 for k in per):
            late = []  # one vendor misses the opening bars while another has the 09:15 bar: a vendor defect, not a Muhurat / special session
        if (d.weekday() >= 5 and (d in dd or any(d in per[k].index for k in per))) or late:
            full = any(d in per[k].index and int(per[k].loc[d, "min"]) == 555 and int(per[k].loc[d, "count"]) >= 370 for k in per)
            spec[d] = bool(full and not late)
        d += timedelta(days=1)
    return hol, spec


def frozen_days(raw: pd.DataFrame) -> set:
    """Sessions with a FROZEN run (>= 5 consecutive flat minutes at one price). From 2026-08-03 a freeze that starts at 15:15 or later is the expected closing-auction pattern and does not count."""
    t = raw.timestamp
    mnt = t.dt.hour * 60 + t.dt.minute
    dd = raw.assign(day=t.dt.date, mnt=mnt)
    out = set()
    for day, g in dd[(dd.mnt >= 555) & (dd.mnt <= 929)].groupby("day"):
        if day >= CAS_FIRST:
            g = g[g.mnt < 15 * 60 + 15]
        fl = ((g.open == g.high) & (g.high == g.low) & (g.low == g.close)).to_numpy()
        px, mm = g.close.to_numpy(), g.mnt.to_numpy()
        run = best = 0
        for i, f in enumerate(fl):
            run = (run + 1 if (run and px[i] == px[i - 1] and mm[i] == mm[i - 1] + 1) else 1) if f else 0
            best = max(best, run)
        if best >= 5:
            out.add(day)
    return out


def audit_index(name: str, cfg: dict, freeze: dict, sample_lines: list[str]) -> None:  # noqa: C901
    key = cfg["key"]
    D = OUT / key
    P = ROOT / "data" / "processed" / key
    STOP = {k: float(v) for k, v in freeze["parameters"]["stops"].items()}
    T2 = {k: float(v) for k, v in freeze["parameters"]["targets_2"].items()}
    src5, srcS, srcD = f"FIVEPAISA_1M_{name}", f"KAPRI_1M_{name}", f"FIVEPAISA_1D_{name}"
    m5, ms, d5 = raw_5p(key, "1m"), raw_sec(key, cfg["sec_file"]), raw_5p(key, "1d")
    raws = {"5p": m5, "sec": ms}
    srcid = {"5p": src5, "sec": srcS}
    tag = f"[{name}]"
    win = {w: {"trades": rd(D / "windows" / w / "all_trades_detailed.csv"), "legs": rd(D / "windows" / w / "trade_exits_detailed.csv"), "checks": rd(D / "windows" / w / "trade_entry_conditions.csv"),
               "candles": rd(D / "windows" / w / "candle_analysis.csv"), "signals": rd(D / "windows" / w / "all_strategy_signals.csv"), "daily": rd(D / "windows" / w / "daily_summary.csv")} for w in SPAN}

    # ============================================================ 1. instrument identity
    inst = json.loads((ROOT / "data" / "metadata" / "phase5" / f"{key}_instrument.json").read_text())
    mp = ROOT / inst["master_file"]
    master = pd.read_csv(mp, low_memory=False)
    cand = master[(master["Exch"] == cfg["exch"]) & (master["ExchType"] == "C") & (master["Name"].astype(str).str.upper() == name)]
    idxrows = cand[cand["ScripCode"] >= 999000]
    ok = (sha(mp) == inst["master_sha256"] and len(idxrows) == 1 and int(idxrows.iloc[0]["ScripCode"]) == cfg["code"] == inst["scrip_code"] and inst["exchange"] == cfg["exch"] and inst["exchange_segment"] == "C"
          and json.loads((ROOT / "data/raw" / key / "5paisa" / "manifest.json").read_text())["instrument"]["scrip_code"] == cfg["code"])
    record(f"{tag} the instrument is the {name} INDEX: exactly one index row (code >= 999000) with that name on the right exchange and cash/index segment in the broker's master (hash-matched copy), equal to the mapping used for every request", ok, len(cand),
           f"scrip {cfg['code']}, exchange {cfg['exch']}; look-alike ETF / fund rows with the same name (not the index): {len(cand) - len(idxrows)}")
    lo_, hi_ = cfg["level"]
    in_range = (d5["close"] >= lo_) & (d5["close"] <= hi_)
    ok = bool(in_range.all()) and abs(float(d5.set_index("date").loc[date(2022, 9, 1), "close"]) - float(m5[m5.timestamp.dt.date == date(2022, 9, 1)].sort_values("timestamp").close.iloc[-1])) < 400
    record(f"{tag} daily closes stay in a plausible range for the index and the 2022-09-01 daily close agrees with the minute data of that day to within 400 points (identity sanity check)", ok, len(d5), f"min {d5.close.min():,.0f} max {d5.close.max():,.0f}")

    # ============================================================ 2. provenance
    man5 = json.loads((ROOT / "data/raw" / key / "5paisa" / "manifest.json").read_text())["requests"]
    bad = [r["file"] for r in man5.values() if r["status"] == "COMPLETED" and sha(ROOT / "data/raw" / key / "5paisa" / r["file"]) != r["sha256"]]
    sd = sec_dir(key)
    mt = json.loads((sd / "manifest.json").read_text())
    bad += [p for p, f in mt["files"].items() if f["status"] == "OK" and (sha(sd / p) != f["sha256"] or blob_sha1((sd / p).read_bytes()) != f["git_blob_sha"])]
    record(f"{tag} every raw provider file equals the SHA-256 recorded at retrieval (secondary files also equal the repository's git blob SHA-1); licence MIT recorded", not bad and mt["repo_license_spdx"] == "MIT", len(man5) + len(mt["files"]), f"secondary commit {mt['commit_sha'][:10]}", bad)
    bad, n_part = [], 0
    for sid in (src5, srcS, srcD):
        sm = json.loads((P / sid / "source_manifest.json").read_text())
        for p, v in sm["partitions"].items():
            n_part += 1
            if sha(ROOT / p) != v["sha256"]:
                bad.append(p)
    record(f"{tag} every processed partition equals the SHA-256 in its source manifest", not bad, n_part, failures=bad)
    bad = []
    for sid, raw in ((src5, m5), (srcS, ms)):
        pr = pd.concat([pd.read_parquet(f) for f in sorted(glob.glob(str(P / sid / "minutes" / "year=*" / "month=*" / "candles.parquet")))], ignore_index=True).sort_values("timestamp").reset_index(drop=True)
        if not (len(pr) == len(raw) and bool((pr["timestamp"].to_numpy() == raw["timestamp"].to_numpy()).all()) and all(np.allclose(pr[c].to_numpy(), raw[c].to_numpy(), atol=1e-9) for c in ("open", "high", "low", "close"))):
            bad.append(sid)
    prd = pd.read_parquet(P / srcD / "daily" / "candles.parquet")
    if len(prd) != len(d5) or not np.allclose(prd["close"].to_numpy(), d5["close"].to_numpy(), atol=1e-9):
        bad.append("daily")
    zs = [f for f in glob.glob(str(P / "**" / "*.parquet"), recursive=True)]
    import pyarrow.parquet as pq
    comp = {pq.ParquetFile(f).metadata.row_group(0).column(0).compression for f in zs[:50]}
    record(f"{tag} processed minute and daily data equal an independent reload of the raw files; Parquet compression is ZSTD", not bad and comp == {"ZSTD"}, len(m5) + len(ms) + len(d5), f"compression {sorted(comp)}", bad)
    # ---- timestamp convention + the 15:30 stub + 5-minute alignment of the 5paisa raw file
    t = m5.timestamp
    mm_ = t.dt.hour * 60 + t.dt.minute
    stub_ok = bool(((mm_ == 930).groupby(t.dt.date).sum() <= 1).all()) and bool(((mm_ >= 555) & (mm_ <= 930) | (mm_ < 555) | (mm_ > 930)).all())
    first_ok = float((m5[(mm_ == 555)].shape[0]) / max(m5.timestamp.dt.date.nunique(), 1)) > 0.95
    record(f"{tag} 5paisa minute rows: IST, at most one 15:30 stub row per session, a 09:15 bar on >95% of sessions (bar-START labels)", stub_ok and first_ok, len(m5))
    # ---- closing-auction detection, independent
    def cas_count(raw, lo, hi):
        t_ = raw.timestamp
        mm = t_.dt.hour * 60 + t_.dt.minute
        x = raw[(t_.dt.date >= lo) & (t_.dt.date <= hi) & (mm >= 15 * 60 + 16) & (mm <= 15 * 60 + 26)]
        res = []
        for _d, g in x.groupby(x.timestamp.dt.date):
            res.append(len(g) == 11 and ((g.open == g.high) & (g.high == g.low) & (g.low == g.close)).all() and g.close.nunique() == 1)
        return sum(res), len(res)
    pre, post = cas_count(m5, date(2026, 6, 1), date(2026, 8, 2)), cas_count(m5, CAS_FIRST, date(2026, 8, 31))
    cj = json.loads((P / "calendar_derived.json").read_text())
    applied = bool(cj.get("closing_auction_applied")) and any(c["id"] == "NSE_CLOSING_AUCTION_SESSION" and c["effective_date"] == "2026-08-03" for c in cj["market_structure_changes"])
    record(f"{tag} closing-auction regime: the freeze pattern (15:16..15:26 flat) is absent before 2026-08-03 and present on >=90% of sessions from it, and the calendar applies the regime exactly then", pre[0] == 0 and post[0] >= 0.9 * post[1] and applied,
           post[1], f"before {pre[0]}/{pre[1]}, from {post[0]}/{post[1]}, applied {applied}")

    # ============================================================ 3. calendar
    cov = {"5p": [(date(2019, 3, 1), date(2019, 12, 31)), (date(2022, 8, 1), date(2026, 8, 31))], "sec": [(max(date(2017, 1, 1), ms.timestamp.dt.date.min()), ms.timestamp.dt.date.max())]}
    hol, spec = indep_calendar(d5, raws, cov, date(2017, 1, 1), date(2026, 8, 31))
    jh = {date.fromisoformat(h["date"]) for h in cj["holidays"]}
    js = {date.fromisoformat(s["date"]): bool(s["evaluable_by_strategies"]) for s in cj["special_sessions"]}
    record(f"{tag} the derived trading calendar equals an independent derivation (holidays and special sessions with their evaluable flag)", hol == jh and spec == js, len(jh) + len(js), f"holidays {len(hol)} vs {len(jh)}; special {len(spec)} vs {len(js)}",
           [str(x) for x in sorted((hol ^ jh) | (set(spec) ^ set(js)))])
    nif = json.loads((ROOT / "data/phase4/calendar/phase4_calendar_derived.json").read_text())
    nh = {date.fromisoformat(h["date"]) for h in nif["holidays"]}
    ev = json.loads((ROOT / "data/metadata/nse_calendar_2025_2026.json").read_text())
    nh |= {date.fromisoformat(h["date"]) for h in ev["holidays"]}
    lo, hi = date(2017, 1, 1), date(2026, 8, 31)
    diff = sorted(d for d in (hol ^ nh) if lo <= d <= hi and d <= date(2025, 8, 31) or (date(2025, 9, 1) <= d <= hi and d in (hol ^ nh)))
    record(f"{tag} holiday dates versus the NIFTY calendars (information: NSE vs BSE closures should agree)", True, len(hol), f"{len(diff)} date(s) differ from the NIFTY derived/evidence calendars: {[str(x) for x in diff][:12]}")
    trade_days = {t["date"] for w in win.values() for t in w["trades"]}
    bad = [d for d in trade_days if date.fromisoformat(d) in hol or (date.fromisoformat(d) in spec and not spec[date.fromisoformat(d)])]
    record(f"{tag} no trade falls on a derived holiday or on a non-evaluable special session", not bad, len(trade_days), failures=bad)

    # ============================================================ 4. per-window verification against RAW bars
    for w, (lo, hi) in SPAN.items():
        kind = SOURCE_KIND[w]
        raw = raws[kind]
        raw = raw[(raw.timestamp.dt.date >= lo - timedelta(days=45)) & (raw.timestamp.dt.date <= hi)]
        wu = raw[raw.timestamp.dt.date < lo]
        trades, legs, cands = win[w]["trades"], win[w]["legs"], win[w]["candles"]
        by_key = raw.assign(key=raw.timestamp.dt.strftime("%Y-%m-%d %H:%M")).set_index("key")
        bad = []
        for t in trades:
            k = t["fill_timestamp"]
            if k not in by_key.index or abs(float(by_key.loc[k, "open"]) - fnum(t["entry_price"])) > 1e-9 or t["signal_confirmed_at"] != k or k[-5:] > "13:00":
                bad.append(t["trade_id"])
        record(f"{tag}[{w}] entry price = raw 1-minute open at the fill minute = signal candle end, and <= 13:00 (all {len(trades)} trades)", not bad, len(trades), failures=bad)
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
            tot_pts = sum((fnum(g["exit_price"]) - e) * sg * 0.5 for g in (l1, l2) if g["exit_price"] not in ("", None))  # a leg without a fillable exit (data ends first) has no P&L
            tot = sum((fnum(g["exit_price"]) - e) * sg * 195 for g in (l1, l2) if g["exit_price"] not in ("", None))
            if abs(tot - fnum(t["gross_pnl_rs"])) > 1e-6 or abs(fnum(t["gross_pnl_points_weighted"]) - tot_pts) > 1e-6 or abs(fnum(t["illustrative_net_pnl_rs"]) - (tot - 500.0 - 0.5 * 2 * 390)) > 1e-6:
                bad_pnl.append(t["trade_id"])
            exp = (e - sg * STOP[t["strategy"]], e + sg * 27, e + sg * T2[t["strategy"]], e - sg * 6)
            got = tuple(fnum(t[k]) for k in ("initial_stop", "target_1", "target_2", "post_t1_stop"))
            if max(abs(a - b) for a, b in zip(exp, got, strict=True)) > 1e-6:
                bad_lv.append(t["trade_id"])
        record(f"{tag}[{w}] independent exit walk reproduces every trade's outcome, both exit times and prices (stop before target, gap fills, post-T1 stop entry -/+ 6, T2, 15:14 forced exit)", not bad, len(trades), failures=bad)
        record(f"{tag}[{w}] index-point P&L (weighted over the two legs) and the fixed-390 rupee P&L recomputed; stops / targets are the frozen NIFTY point distances (not rescaled)", not bad_pnl and not bad_lv, len(trades), failures=bad_pnl + bad_lv)
        dmin = raw.assign(day=raw.timestamp.dt.date, mod=raw.timestamp.dt.hour * 60 + raw.timestamp.dt.minute).groupby("day")["mod"].min()
        std = set(dmin[dmin == 555].index)  # sessions opening at 09:15 (truncated sessions keep their complete 5-minute candles, like the pipeline; a day with < 5 rows forms none)
        fz = frozen_days(raw)
        nonev = {d for d, ok in spec.items() if not ok}
        use = {d for d in std if d not in fz and d not in nonev and d not in hol}
        c5 = A32.five_minute(raw, use).sort_values("start").reset_index(drop=True)
        c5["ema"] = A32.ema_series(c5["close"].to_numpy())
        idx = {s.strftime("%Y-%m-%d %H:%M"): i for i, s in enumerate(c5.start)}
        bo, bg, be = [], [], []
        n_ema = 0
        for r in cands:
            i = idx.get(r["candle_start"])
            if i is None:
                bo.append((r["trade_id"], r["role"], "candle missing / incomplete in raw"))
                continue
            c = c5.iloc[i]
            o, h, lo2, cl = (fnum(r[k]) for k in ("open", "high", "low", "close"))
            if max(abs(c.open - o), abs(c.high - h), abs(c.low - lo2), abs(c.close - cl)) > 1e-9:
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
        record(f"{tag}[{w}] explanation candles equal an independent 5-minute aggregation of the raw rows; geometry flags equal; EMA(200) equals an independent causal recomputation ({n_ema} candles with an EMA)", not bo and not bg and not be, len(cands), failures=bo + bg + be)
        tmap = {t["trade_id"]: t for t in trades}
        bad = [(r["trade_id"], r["role"]) for r in cands if (r["session"] == "TODAY" and r["candle_end"] > tmap[r["trade_id"]]["signal_confirmed_at"]) or (r["session"] != "TODAY" and r["candle_end"][:10] >= tmap[r["trade_id"]]["date"])]
        record(f"{tag}[{w}] no look-ahead: every explanation candle ends at or before the signal, previous-session candles precede the trade date, warm-up rows precede the window", not bad and all(d < lo for d in wu.timestamp.dt.date.unique()), len(cands), failures=bad)
        # ---- previous-day levels: previous session's 5-minute high / low (continuous candles only on auction days) and the vendor DAILY close
        dly = {d["date"]: d for d in win[w]["daily"]}
        dates_sorted = sorted(dly)
        d5c = d5.set_index("date")["close"].to_dict()
        c5d = {d: g for d, g in c5.groupby(c5.start.dt.date)}
        bad_pl, n_pl = [], 0
        for i_, dstr in enumerate(dates_sorted):
            if i_ == 0 or dly[dstr]["prev_day_high"] in ("", None):
                continue
            pdate = date.fromisoformat(dly[dstr]["previous_session"]) if dly[dstr]["previous_session"] else None
            if pdate is None or pdate not in c5d:
                continue
            g = c5d[pdate]
            gh, gl = g.high.max(), g.low.min()
            n_pl += 1
            oc = d5c.get(pdate)
            if abs(fnum(dly[dstr]["prev_day_high"]) - gh) > 1e-6 or abs(fnum(dly[dstr]["prev_day_low"]) - gl) > 1e-6 or (oc is not None and dly[dstr]["prev_day_official_close"] not in ("",) and abs(fnum(dly[dstr]["prev_day_official_close"]) - oc) > 1e-6):
                bad_pl.append((dstr, dly[dstr]["prev_day_high"], round(float(gh), 2), dly[dstr]["prev_day_low"], round(float(gl), 2), dly[dstr]["prev_day_official_close"], oc))
        record(f"{tag}[{w}] previous-day high / low (from the previous session's 5-minute candles; continuous candles on auction days) and the previous-day official close (= vendor daily close) equal an independent recomputation", not bad_pl, n_pl, failures=bad_pl)
        # ---- controller rules (a signal is a candidate only if a raw one-minute bar exists at its fill minute on an evaluable session; "no fillable bar" rejections are thereby checked against the raw rows)
        def fillable(d_, hm_, _bk=by_key, _ne=nonev):
            return f"{d_} {hm_}" in _bk.index and date.fromisoformat(d_) not in _ne
        sig_by_day, tr_by_day = defaultdict(list), defaultdict(list)
        for r in win[w]["signals"]:
            sig_by_day[r["date"]].append(r)
        for t in trades:
            tr_by_day[t["date"]].append(t)
        bad, conflict_days = [], 0
        for d_, ts in tr_by_day.items():
            ts.sort(key=lambda t: int(t["trade_no_of_day"]))
            cands_ = sorted((r for r in sig_by_day[d_] if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True" and fillable(d_, r["time"])), key=lambda r: r["time"])
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
            c_ = [r for r in rs_ if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True" and fillable(d_, r["time"])]
            if c_:
                ft = min(r["time"] for r in c_)
                if len({(r["strategy"], r["direction"]) for r in c_ if r["time"] == ft}) > 1:
                    conflict_days += 1
                else:
                    bad.append((d_, "valid signal but no trade and no same-minute conflict"))
        record(f"{tag}[{w}] controller rules on the delivered tables: first valid signal, max 2 trades, cutoff 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing valid (or a same-minute conflict)", not bad, len(tr_by_day), f"{conflict_days} conflict day(s)", bad)
        cs, ct = Counter(r["strategy"] for r in win[w]["signals"]), Counter(t["strategy"] for t in trades)
        record(f"{tag}[{w}] all five strategies produced signals" + (" and were traded" if len(trades) > 300 else " (a strategy may have no first-valid-signal trade in a short window)"), all(cs[s] > 0 and (ct[s] > 0 or len(trades) <= 300) for s in STRATS), 5, f"signals {dict(cs)}, trades {dict(ct)}")
        raw_days = {x for x in raw.timestamp.dt.date.unique() if lo <= x <= hi}
        cv = {r["window_id"]: r for r in rd(D / "data" / "historical_coverage_by_window.csv")}[w]
        dl = d5[(d5.date >= lo) & (d5.date <= hi)]
        expected = {x for x in dl.date if x.weekday() < 5 and x not in hol} | {x for x in dl.date if x.weekday() >= 5} | {x for x in (lo + timedelta(days=i) for i in range((hi - lo).days + 1)) if x.weekday() < 5 and x not in hol}
        ok = int(cv["expected_sessions"]) == len(expected) and int(cv["sessions_in_source"]) == len(raw_days & expected)
        record(f"{tag}[{w}] coverage: expected sessions (derived calendar) and sessions present in the raw source equal the delivered coverage table", ok, len(expected), f"expected {len(expected)} vs {cv['expected_sessions']}, in source {len(raw_days & expected)} vs {cv['sessions_in_source']}")
        n_hist = int((d5.date < lo).sum())
        record(f"{tag}[{w}] at least 200 daily bars precede the window (daily moving averages); warm-up minute sessions in the same source: {cv['warmup_sessions_same_source']}", n_hist >= 200 and int(cv["daily_bars_before_start"]) == n_hist, n_hist)
        # ---- sample review (3 trades per strategy per window M only) for the human-readable audit
        if w == "M":
            for s in STRATS:
                pick = [t for t in trades if t["strategy"] == s]
                for t in pick[:: max(len(pick) // 3, 1)][:3]:
                    e = fnum(t["entry_price"])
                    sg = 1 if t["direction"] == "LONG" else -1
                    cc = [r for r in cands if r["trade_id"] == t["trade_id"] and r["role"].lower().startswith(("signal", "confirm"))][:1] or [r for r in cands if r["trade_id"] == t["trade_id"]][:1]
                    c = cc[0] if cc else {}
                    sample_lines.append(f"| {name} | {s} | {t['trade_id']} | {t['direction']} | {t['signal_confirmed_at']} | {e:.2f} | {t['outcome']} | {t['leg1_exit_time']}/{t['leg2_exit_time']} | {fnum(t['gross_pnl_points_weighted']):+.2f} | "
                                         f"{c.get('open', '')}/{c.get('high', '')}/{c.get('low', '')}/{c.get('close', '')} | {c.get('ema200_5m', '')} | stop {e - sg * STOP[s]:.2f}, T1 {e + sg * 27:.2f}, T2 {e + sg * T2[s]:.2f} |")

    # ============================================================ 5. metrics recomputed from the trade tables
    ann = {r["row_id"]: r for r in rd(D / "annual_comparison.csv")}
    strat = {(r["row_id"], r["strategy"]): r for r in rd(D / "strategy_performance.csv")}
    bad = []
    for rid, wid, lo, hi in ROWDEF:
        tr = [t for t in win[wid]["trades"] if str(lo) <= t["date"] <= str(hi)]
        tr.sort(key=lambda t: (t["date"], t["fill_timestamp"], int(t["trade_no_of_day"])))
        pts = [fnum(t["gross_pnl_points_weighted"]) for t in tr]
        cum = peak = dd = 0.0
        for v in pts:
            cum += v
            peak = max(peak, cum)
            dd = max(dd, peak - cum)
        gp, gl = sum(v for v in pts if v > 0), -sum(v for v in pts if v < 0)
        a = ann[rid]
        exp = {"executed_trades": len(tr), "gross_index_points": round(sum(pts), 2), "max_drawdown_index_points": round(dd, 2), "win_rate_pct": round(100 * sum(1 for v in pts if v > 0) / len(pts), 2),
               "avg_points_per_trade": round(sum(pts) / len(pts), 3), "outcome_INITIAL_FULL_STOP": sum(1 for t in tr if t["outcome"] == "INITIAL_FULL_STOP"), "outcome_TARGET": sum(1 for t in tr if t["outcome"] == "TARGET"),
               "gross_rs_fixed_390_synthetic": round(sum(fnum(t["gross_pnl_rs"]) for t in tr), 2)}
        for k, v in exp.items():
            if abs(fnum(a[k]) - v) > 0.011:
                bad.append((rid, k, a[k], v))
        if gl and abs(fnum(a["profit_factor_points"]) - gp / gl) > 1e-3:
            bad.append((rid, "profit_factor_points", a["profit_factor_points"], gp / gl))
        if abs(sum(pts) * 390 - sum(fnum(t["gross_pnl_rs"]) for t in tr)) > 1.0:
            bad.append((rid, "points x 390 != rupees"))
        entry_pct = np.mean([abs(fnum(t["entry_price"]) - fnum(t["initial_stop"])) / fnum(t["entry_price"]) * 100 for t in tr])
        if abs(fnum(a["stop_pct_of_index"]) - entry_pct) > 1e-3:
            bad.append((rid, "stop_pct_of_index", a["stop_pct_of_index"], entry_pct))
        for s in STRATS:
            st = [t for t in tr if t["strategy"] == s]
            sp = sum(fnum(t["gross_pnl_points_weighted"]) for t in st)
            if int(fnum(strat[(rid, s)]["trades"])) != len(st) or abs(fnum(strat[(rid, s)]["gross_index_points"]) - sp) > 0.011:
                bad.append((rid, s, "strategy table"))
    record(f"{tag} annual_comparison.csv and strategy_performance.csv equal an independent recomputation for every row (trades, index points, drawdown, profit factor, win rate, outcomes, stop % of index, per-strategy points; points x 390 = rupees)", not bad, len(ROWDEF), failures=bad)
    m1, m2, m3, m4, mall = (ann[k] for k in ("M_2022_23", "M_2023_24", "M_2024_25", "M_2025_26", "M_ALL"))
    record(f"{tag} the four annual slices sum to the main window (trades, index points)", sum(int(x["executed_trades"]) for x in (m1, m2, m3, m4)) == int(mall["executed_trades"]) and abs(sum(fnum(x["gross_index_points"]) for x in (m1, m2, m3, m4)) - fnum(mall["gross_index_points"])) < 0.02, 4)
    # cost grid, fill level
    cg = {(r["row_id"], r["fixed_cost_rs_per_trade"], r["slippage_points_per_fill"]): r for r in rd(D / "cost_sensitivity.csv")}
    bad = []
    for rid in ("M_ALL", "C_2018"):
        _r, wid, lo, hi = next(x for x in ROWDEF if x[0] == rid)
        tr = [t for t in win[wid]["trades"] if str(lo) <= t["date"] <= str(hi)]
        lg = defaultdict(list)
        for g in win[wid]["legs"]:
            lg[g["trade_id"]].append(g)
        for fx, sl in ((0.0, 0.0), (500.0, 0.5), (1000.0, 1.0), (1500.0, 2.0)):
            net = 0.0
            for t in tr:
                fills = 1 + sum(1 for g in lg[t["trade_id"]] if g["exit_price"] not in ("", None))
                units = fnum(t["qty_total"]) + sum(fnum(g["quantity"]) for g in lg[t["trade_id"]] if g["exit_price"] not in ("", None))
                net += fnum(t["gross_pnl_rs"]) - fx / 3.0 * fills - sl * units
            if abs(fnum(cg[(rid, str(fx), str(sl))]["net_pnl_rs"]) - net) > 0.05:
                bad.append((rid, fx, sl, cg[(rid, str(fx), str(sl))]["net_pnl_rs"], round(net, 2)))
    record(f"{tag} cost sensitivity (fill-level costs) recomputed independently for two periods x four scenarios", not bad, 8, failures=bad)

    # ============================================================ 6. source columns, journals, charts, option block, relabelling
    bad, n, opt_bad, nifty_label = [], 0, [], []
    for w in win:
        sm = json.loads((P / srcid[SOURCE_KIND[w]] / "source_manifest.json").read_text())
        ids = [t["trade_id"] for t in win[w]["trades"]]
        if len(set(ids)) != len(ids):
            bad.append((w, "duplicate trade ids"))
        for t in win[w]["trades"]:
            n += 1
            part = t["data_source_partition"]
            if t["index"] != name or t["data_source_id"] != srcid[SOURCE_KIND[w]] or t["daily_source_id"] != srcD or sha(ROOT / part) != t["data_source_partition_sha256"]:
                bad.append((w, t["trade_id"], "source columns"))
            rf = sm["partitions"][part]["raw_files"]
            if t["raw_source_sha256"] != ";".join((sm["raw_files"] or {}).get(f, "") for f in rf) or not t["raw_source_sha256"]:
                bad.append((w, t["trade_id"], "raw sha"))
            jp = D / "daily" / w / t["date"][:7] / f"{t['date']}.md"
            if not (D / "charts" / w / f"{t['trade_id']}.svg").exists() or f"### {t['trade_id']}:" not in jp.read_text():
                bad.append((w, t["trade_id"], "chart / journal"))
        for d_ in win[w]["daily"]:
            jp = D / "daily" / w / d_["date"][:7] / f"{d_['date']}.md"
            if not jp.exists():
                bad.append((w, d_["date"], "missing journal"))
                continue
            txt = jp.read_text()
            if "Option-execution feasibility" not in txt:
                opt_bad.append((w, d_["date"], "no option block"))
            tail = txt.split("Option-execution feasibility", 1)[-1]
            if re.search(r"premium\s*[:=]?\s*\d|option P&L\s*[:=]?\s*[-+]?\d|strike\s*[:=]?\s*\d|expiry\s*[:=]?\s*\d{4}", tail, re.I):
                opt_bad.append((w, d_["date"], "numeric option content"))
            for _m in re.finditer(r"NIFTY 50", txt):
                nifty_label.append((w, d_["date"]))
                break
    record(f"{tag} every trade of every window records index, minute-source id, daily-source id, partition SHA-256 (= the real file hash) and raw-file SHA-256; ids are unique; each trade has its chart and journal section; each evaluated session has a journal", not bad, n, failures=bad)
    record(f"{tag} every journal ends with the option-feasibility block and contains NO option premium, strike, expiry or option P&L number (no invented option executions)", not opt_bad, sum(len(win[w]["daily"]) for w in win), failures=opt_bad)
    record(f"{tag} journals carry the correct instrument label (no residual 'NIFTY 50' instrument phrase)", not nifty_label, sum(len(win[w]["daily"]) for w in win), failures=nifty_label)
    optcols = [c for w in win for c in win[w]["trades"][0] if re.search(r"option|premium|strike|delta|\bce\b|\bpe\b", c, re.I)]
    record(f"{tag} no trade table has an option / premium / strike column", not optcols, len(win), failures=optcols)
    import openpyxl
    wbp = D / f"{name}_Daily_Verification.xlsx"
    wb = openpyxl.load_workbook(wbp, read_only=True)
    pairs = {"Annual": "annual_comparison.csv", "Strategy": "strategy_performance.csv", "Cost Sensitivity": "cost_sensitivity.csv", "Trades": "trade_level_signals.csv", "Monthly Points": "monthly_index_points.csv"}

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
    bad, cells = [], 0
    for sh, fn in pairs.items():
        data = rd(D / fn)
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
    record(f"{tag} the verification workbook's main sheets equal the CSV files cell by cell", not bad, cells, failures=bad)

    # ============================================================ 7. vendor overlap, recomputed
    ov = json.loads((D / "data" / "vendor_overlap_summary.json").read_text())
    key_ov = [k for k in ov if k.startswith("2022-08")][0]
    hi_ov = date.fromisoformat(key_ov.split("..")[1])

    def regular(x, lo, hi):
        t = x.timestamp
        m = t.dt.hour * 60 + t.dt.minute
        return x[(m >= 555) & (m <= 929) & (t.dt.date >= lo) & (t.dt.date <= hi)].set_index("timestamp")[["open", "high", "low", "close"]]
    j = regular(m5, date(2022, 8, 1), hi_ov).join(regular(ms, date(2022, 8, 1), hi_ov), how="inner", lsuffix="_a", rsuffix="_b")
    exact = float(((j[["open_a", "high_a", "low_a", "close_a"]].to_numpy() - j[["open_b", "high_b", "low_b", "close_b"]].to_numpy()).__abs__().max(axis=1) <= 0.005).mean())
    mad = float((j["close_a"] - j["close_b"]).abs().mean())
    o = ov[key_ov]
    record(f"{tag} the {key_ov} vendor-overlap figures (bars compared, share identical, mean |close difference|) equal an independent recomputation", len(j) == o["bars_compared"] and abs(exact - o["share_exact_all_fields"]) < 1e-3 and abs(mad - o["mean_abs_close_diff"]) < 1e-3, len(j),
           f"bars {len(j):,}; identical {exact:.4f}; mean |diff| {mad:.4f}")


def main() -> int:
    freeze = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    sample: list[str] = ["# Sample review of executed trades (every index, every strategy)", "",
                         "Three trades per strategy per index from the main window, re-derived from the raw bars by `scripts/phase5_independent_audit.py`: entry price, stop / T1 / T2 levels, the independently walked outcome, exit times and index points "
                         "(each equals the delivered trade table; the audit fails otherwise). The signal-candle column shows the delivered explanation candle (open/high/low/close) and the 5-minute EMA(200) that were separately re-aggregated from the raw rows.", "",
                         "| index | strategy | trade | direction | signal at | entry | outcome | leg exits | weighted index points | signal candle o/h/l/c | EMA200 (5m) | levels |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for name, cfg in IDX.items():
        audit_index(name, cfg, freeze, sample)
    # ============================================================ NIFTY comparison inputs and the preservation of everything NIFTY
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    changed, missing = [], []
    for p, h in snap["hashes"].items():
        f = ROOT / p
        if not f.exists():
            missing.append(p)
        elif sha(f) != h:
            changed.append(p)
    record("every file of the before-snapshot (all git-tracked files incl. strategies, controller, execution, framework, tests, docs; data/processed/nifty50*; data/phase4; data/raw/phase4_*; reports/phase3; reports/phase4) is byte-identical", not changed and not missing, len(snap["hashes"]),
           f"snapshot of git head {snap['git_head'][:10]}", changed + missing)
    now = {p.relative_to(ROOT).as_posix() for d in ("data/processed/nifty50", "data/processed/nifty50_daily", "data/processed/nifty50_warmup", "data/phase4", "data/raw/phase4_5paisa", "data/raw/phase4_technovusin", "reports/phase3", "reports/phase4") for p in (ROOT / d).rglob("*") if p.is_file() and p.name != ".DS_Store"}
    added = sorted(now - set(snap["hashes"]))
    record("no file was added inside any NIFTY data or earlier-report directory", not added, len(now), failures=added)
    bad = []
    for path, h in freeze["active_file_hashes"].items():
        if sha(ROOT / path) != h:
            bad.append(path)
    record("every strategy, controller, execution, session-construction and framework file hashed in the Phase 4 freeze is unchanged", not bad, len(freeze["active_file_hashes"]), freeze["frozen_configuration_id"], bad)
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    record("configuration_snapshot.json records the frozen id, equal active-file hashes and the stop / target / cutoff values of the brief", cfg["active_file_hashes_equal_freeze"] and cfg["frozen_configuration_id"] == freeze["frozen_configuration_id"]
           and cfg["stops_targets"]["initial_stop"] == {"ORB": 30, "IRF": 35, "PDR": 35, "PDS": 35, "RF": 35} and cfg["stops_targets"]["target_1"] == 27 and cfg["stops_targets"]["target_2"] == {"IRF": 60, "ORB": 60, "PDR": 70, "PDS": 70, "RF": 60}, 1)
    # NIFTY reference rows used in the comparison equal an independent recomputation from the NIFTY trade tables
    a_tr = rd(ROOT / "reports/phase3/phase36_body_based_pdr/all_trades_detailed.csv")
    b_tr = rd(ROOT / "reports/phase4/windows/B/all_trades_detailed.csv")
    ref = [r for r in rd(OUT / "comparison" / "cross_index_by_period.csv") if r["index"] == "NIFTY" and r["row_id"] == "M_ALL"][0]
    pts = sum(fnum(t["gross_pnl_points_weighted"]) for t in a_tr + b_tr)
    record("the NIFTY main-window reference in the comparison (Phase 4 window B + the unchanged Phase 3.6 window A) equals an independent sum of those trade tables", int(ref["executed_trades"]) == len(a_tr) + len(b_tr) and abs(fnum(ref["gross_index_points"]) - pts) < 0.02, len(a_tr) + len(b_tr),
           f"{len(a_tr) + len(b_tr)} trades, {pts:,.2f} index points")
    # option-data claims: the probe file supports the availability statements
    pr = json.loads((OUT / "options_feasibility" / "option_probe_results.json").read_text())
    ok = all(not v["master_new"]["contains_expired_contracts"] for v in pr["indices"].values()) and all(all(c not in p.get("columns", []) for c in ("Bid", "Ask", "OpenInterest", "OI")) for v in pr["indices"].values() for p in v["probes"] if p.get("status") == "COMPLETED")
    record("option-data availability claims are backed by the saved probe: the master lists no expired contract and no returned candle has a bid, ask or open-interest column", ok, sum(len(v["probes"]) for v in pr["indices"].values()))
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    (OUT / "_sample_review.md").write_text("\n".join(sample) + "\n")
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
