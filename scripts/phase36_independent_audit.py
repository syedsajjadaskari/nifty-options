"""Phase 3.6 independent audit: a second implementation of everything the combined backtest reports, written from the RAW one-minute parquet files and the delivered CSVs only.

It imports nothing from ``src/`` (derived from ``scripts/phase32_audit.py``, with the legacy-PDR checks replaced by the revised-PDR ones and new controller / contribution / untouched-file checks).
Run: .venv/bin/python scripts/phase36_independent_audit.py
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
P35 = ROOT / "reports" / "phase3" / "phase35_combined"
P32 = ROOT / "reports" / "phase3" / "phase32"
P30 = ROOT / "reports" / "phase3" / "baseline"
EPS = 1e-9
RES: dict = {"checks": {}}


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""))


def rows(name: str) -> list[dict]:
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def fnum(x) -> float:
    return float(str(x).replace(",", ""))


# ------------------------------------------------------------------------------------------------ raw data, re-implemented
def load_raw() -> pd.DataFrame:
    files = sorted(glob.glob(str(ROOT / "data/processed/nifty50/**/*.parquet"), recursive=True))
    return pd.concat([pd.read_parquet(f) for f in files]).sort_values("timestamp").reset_index(drop=True)


def load_warm() -> pd.DataFrame:
    files = sorted(glob.glob(str(ROOT / "data/processed/nifty50_warmup/**/*.parquet"), recursive=True))
    return pd.concat([pd.read_parquet(f) for f in files]).sort_values("timestamp").reset_index(drop=True)


def standard_days(df: pd.DataFrame) -> set:
    """Sessions that open at 09:15 and have a (nearly) full day of one-minute rows. Special sessions (for example the Diwali Muhurat hour) are not standard sessions
    and must not feed a 5-minute EMA that is meant to describe regular trading."""
    d = df.assign(day=df.timestamp.dt.date, mod=df.timestamp.dt.hour * 60 + df.timestamp.dt.minute)
    g = d.groupby("day").agg(first=("mod", "min"), n=("mod", "count"))
    return set(g[(g["first"] == 555) & (g["n"] >= 300)].index)


def five_minute(df: pd.DataFrame, only_days: set | None = None) -> pd.DataFrame:
    """Complete 5-minute candles (all 5 one-minute rows present) per session from 09:15 to 15:29, labelled by START."""
    d = df.copy()
    d["day"] = d.timestamp.dt.date
    if only_days is not None:
        d = d[d["day"].isin(only_days)]
    d["mod"] = d.timestamp.dt.hour * 60 + d.timestamp.dt.minute
    d = d[(d["mod"] >= 555) & (d["mod"] <= 929)]
    d["bucket"] = (d["mod"] - 555) // 5
    g = d.groupby(["day", "bucket"], sort=True)
    out = g.agg(start=("timestamp", "min"), open=("open", "first"), high=("high", "max"), low=("low", "min"), close=("close", "last"), n=("timestamp", "nunique")).reset_index()
    return out[out["n"] == 5].reset_index(drop=True)


def ema_series(closes: np.ndarray, period: int = 200) -> np.ndarray:
    out = np.full(len(closes), np.nan)
    if len(closes) < period:
        return out
    a = 2.0 / (period + 1)
    out[period - 1] = closes[:period].mean()
    for i in range(period, len(closes)):
        out[i] = a * closes[i] + (1 - a) * out[i - 1]
    return out


def geometry(o: float, h: float, low: float, c: float) -> dict:
    rng = h - low
    body = abs(c - o)
    uw, lw = h - max(o, c), min(o, c) - low
    z = rng <= 0
    return {"range": rng, "body": body, "uw": uw, "lw": lw, "body_pct": None if z else 100 * body / rng, "uw_pct": None if z else 100 * uw / rng, "lw_pct": None if z else 100 * lw / rng,
            "dir": "BULLISH" if c > o else ("BEARISH" if c < o else "DOJI"), "zero": z,
            "strong_bull": (not z) and c > o and body / rng >= 0.6 - EPS and uw / rng <= 0.2 + EPS,
            "strong_bear": (not z) and c < o and body / rng >= 0.6 - EPS and lw / rng <= 0.2 + EPS,
            "bear_pin": (not z) and uw > EPS and uw >= 2.0 * body - EPS and (c - low) <= 0.3 * rng + EPS,
            "bull_pin": (not z) and lw > EPS and lw >= 2.0 * body - EPS and (h - c) <= 0.3 * rng + EPS,
            "small": True if z else body <= 0.3 * rng + EPS}


# ------------------------------------------------------------------------------------------------ independent exit walk
def walk_exit(direction: str, entry: float, bars: pd.DataFrame, stop_pts: float, t2_pts: float) -> dict:
    """Stop before target inside a bar; stop gap fills at the worse of level/open; T1 27 on 195, post-T1 stop entry -/+ 6 (same bar tested adversely, filled at its level);
    T2 on the rest; anything still open at the 15:14 minute is closed at that bar's open (provisional convention)."""
    sg = 1 if direction == "LONG" else -1
    sl, t1, t2, s2 = entry - sg * stop_pts, entry + sg * 27, entry + sg * t2_pts, entry - sg * 6

    def adverse(b, lvl):
        return b.low <= lvl + 0 if sg == 1 else b.high >= lvl

    def favour(b, lvl):
        return b.high >= lvl if sg == 1 else b.low <= lvl
    t1_done, p1, ts1 = False, None, None
    for b in bars.itertuples():
        mod = b.timestamp.hour * 60 + b.timestamp.minute
        if mod >= 15 * 60 + 14:
            px = b.open
            if t1_done:
                return {"outcome": "FORCED_EXIT", "p1": p1, "ts1": ts1, "p2": px, "ts2": b.timestamp}
            return {"outcome": "FORCED_EXIT", "p1": px, "ts1": b.timestamp, "p2": px, "ts2": b.timestamp}
        if not t1_done:
            if adverse(b, sl):
                px = min(sl, b.open) if sg == 1 else max(sl, b.open)
                return {"outcome": "INITIAL_FULL_STOP", "p1": px, "ts1": b.timestamp, "p2": px, "ts2": b.timestamp}
            if favour(b, t1):
                t1_done, p1, ts1 = True, t1, b.timestamp
                if adverse(b, s2):
                    return {"outcome": "T1_THEN_BUFFER_STOP", "p1": p1, "ts1": ts1, "p2": s2, "ts2": b.timestamp}
                if favour(b, t2):
                    return {"outcome": "TARGET", "p1": p1, "ts1": ts1, "p2": t2, "ts2": b.timestamp}
            continue
        if adverse(b, s2):
            px = min(s2, b.open) if sg == 1 else max(s2, b.open)
            return {"outcome": "T1_THEN_BUFFER_STOP", "p1": p1, "ts1": ts1, "p2": px, "ts2": b.timestamp}
        if favour(b, t2):
            return {"outcome": "TARGET", "p1": p1, "ts1": ts1, "p2": t2, "ts2": b.timestamp}
    return {"outcome": "INCOMPLETE_EOD", "p1": p1, "ts1": ts1, "p2": None, "ts2": None}


def main() -> int:  # noqa: C901
    raw = load_raw()
    raw["key"] = raw.timestamp.dt.strftime("%Y-%m-%d %H:%M")
    by_key = raw.set_index("key")
    trades = rows("all_trades_detailed.csv")
    legs = rows("exit_details.csv")
    checks = rows("entry_condition_details.csv")
    candles = rows("candle_analysis.csv")
    daily = rows("daily_summary.csv")
    cfg = json.loads((OUT / "configuration_snapshot.json").read_text())
    STOP = {k: float(v) for k, v in cfg["stops"].items()}
    T2 = {k: float(v) for k, v in cfg["targets_2"].items()}

    # ---------- 1. entry fill = open of the raw 1-minute bar; signal candle end = fill time
    bad = []
    for t in trades:
        k = t["fill_timestamp"]
        if k not in by_key.index or abs(by_key.loc[k, "open"] - fnum(t["entry_price"])) > 1e-9 or t["entry_source_bar_ts"] != k:
            bad.append(t["trade_id"])
        if t["signal_confirmed_at"] != k:
            bad.append(t["trade_id"] + ":signal!=fill")
        if t["fill_timestamp"][-5:] > "13:00":
            bad.append(t["trade_id"] + ":after cutoff")
    record("entry price equals the raw 1-minute bar open at the fill minute (all trades)", not bad, len(trades), failures=bad)

    # ---------- 2. 5-minute candles, geometry and flags (every candle row of the explanation)
    warm = load_warm()
    std_raw, std_warm = standard_days(raw), standard_days(warm)
    RES["non_standard_sessions_excluded_from_the_independent_ema"] = sorted(str(d) for d in (set(raw.timestamp.dt.date) - std_raw) | (set(warm.timestamp.dt.date) - std_warm))
    cand5 = five_minute(raw, std_raw)
    warm5 = five_minute(warm, std_warm)
    allc = pd.concat([warm5, cand5]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = ema_series(allc["close"].to_numpy())
    idx = {s.strftime("%Y-%m-%d %H:%M"): i for i, s in enumerate(allc.start)}
    bad_ohlc, bad_geo, bad_ema, bad_avail = [], [], [], []
    n_ema = 0
    for r in candles:
        i = idx.get(r["candle_start"])
        if i is None:
            bad_ohlc.append((r["trade_id"], r["role"], "candle missing/incomplete in raw"))
            continue
        c = allc.iloc[i]
        o, h, lo, cl = fnum(r["open"]), fnum(r["high"]), fnum(r["low"]), fnum(r["close"])
        if max(abs(c.open - o), abs(c.high - h), abs(c.low - lo), abs(c.close - cl)) > 1e-9:
            bad_ohlc.append((r["trade_id"], r["role"]))
        g = geometry(c.open, c.high, c.low, c.close)
        csvf = {"strong_bull": r["strong_bullish"] == "True", "strong_bear": r["strong_bearish"] == "True", "bull_pin": r["bullish_pin"] == "True", "bear_pin": r["bearish_pin"] == "True",
                "small": r["small_body_le_30pct"] == "True"}
        mism = [k for k, v in csvf.items() if g[k] != v]
        for csvk, gk in (("body_pct", "body_pct"), ("upper_wick_pct", "uw_pct"), ("lower_wick_pct", "lw_pct")):
            a, b_ = r[csvk], g[gk]
            if (a == "") != (b_ is None) or (a != "" and abs(float(a) - b_) > 1e-3):
                mism.append(csvk)
        if r["direction"] != g["dir"] or (r["zero_range"] == "True") != g["zero"]:
            mism.append("direction/zero")
        if mism:
            bad_geo.append((r["trade_id"], r["role"], mism))
        if r["ema200_5m"] != "":
            n_ema += 1
            if abs(float(r["ema200_5m"]) - c.ema) > 1e-3:
                bad_ema.append((r["trade_id"], r["role"], r["ema200_5m"], round(float(c.ema), 4)))
        elif not np.isnan(c.ema):
            bad_ema.append((r["trade_id"], r["role"], "csv has no EMA but one exists"))
        if r["available_at"] != r["candle_end"]:
            bad_avail.append(r["trade_id"])
    record("candle OHLC equals an independent 5-minute aggregation of the raw 1-minute rows", not bad_ohlc, len(candles), failures=bad_ohlc)
    record("body %, wick %, direction, strong/pin/small flags equal an independent calculation", not bad_geo, len(candles), failures=bad_geo)
    record("EMA(200) of 5-minute closes equals an independent causal recomputation (warm-up + data)", not bad_ema, n_ema, "tolerance 1e-3", bad_ema)
    record("each candle is available at its own end time", not bad_avail, len(candles), failures=bad_avail)

    # ---------- 3. no look-ahead: TODAY candles end at or before the signal; PREVIOUS candles belong to an earlier date
    tmap = {t["trade_id"]: t for t in trades}
    bad = [(r["trade_id"], r["role"]) for r in candles if (r["session"] == "TODAY" and r["candle_end"] > tmap[r["trade_id"]]["signal_confirmed_at"]) or (r["session"] != "TODAY" and r["candle_end"][:10] >= tmap[r["trade_id"]]["date"])]
    record("no explanation candle is later than the signal confirmation", not bad, len(candles), failures=bad)

    # ---------- 4. exits: independent walk of the raw bars versus the delivered legs, outcomes and P&L
    by_id: dict[str, list[dict]] = defaultdict(list)
    for g in legs:
        by_id[g["trade_id"]].append(g)
    bad, bad_pnl = [], []
    outcome_counts: Counter = Counter()
    tot = 0.0
    for t in trades:
        direction = t["direction"]
        fill = pd.Timestamp(t["fill_timestamp"]).tz_localize("Asia/Kolkata")
        day = raw[(raw.timestamp.dt.date == fill.date()) & (raw.timestamp >= fill)]
        w = walk_exit(direction, fnum(t["entry_price"]), day, STOP[t["strategy"]], T2[t["strategy"]])
        l1, l2 = by_id[t["trade_id"]]
        sg = 1 if direction == "LONG" else -1

        def hm(ts):
            return "" if ts is None else ts.strftime("%H:%M")
        ok = (w["outcome"] == t["outcome"] and hm(w["ts1"]) == t["leg1_exit_time"] and hm(w["ts2"]) == t["leg2_exit_time"]
              and abs((w["p1"] or 0) - (fnum(t["leg1_exit_price"]) if t["leg1_exit_price"] else 0)) < 1e-6 and abs((w["p2"] or 0) - (fnum(t["leg2_exit_price"]) if t["leg2_exit_price"] else 0)) < 1e-6)
        if not ok:
            bad.append((t["trade_id"], w["outcome"], t["outcome"], hm(w["ts1"]), t["leg1_exit_time"], hm(w["ts2"]), t["leg2_exit_time"]))
        e = fnum(t["entry_price"])
        legpnl = [(fnum(g["exit_price"]) - e) * sg * 195 if g["exit_price"] else None for g in (l1, l2)]
        if None not in legpnl:
            total = sum(legpnl)
            tot += total
            if abs(total - fnum(t["gross_pnl_rs"])) > 1e-6 or any(abs(a - fnum(g["gross_pnl_rs"])) > 1e-6 for a, g in zip(legpnl, (l1, l2), strict=True)):
                bad_pnl.append(t["trade_id"])
        outcome_counts[(t["strategy"], t["outcome"])] += 1
        # each leg's source bar OHLC equals the raw bar
        for g in (l1, l2):
            if g["exit_source_bar_ts"]:
                rb = by_key.loc[g["exit_source_bar_ts"]]
                if max(abs(rb.open - fnum(g["exit_bar_open"])), abs(rb.high - fnum(g["exit_bar_high"])), abs(rb.low - fnum(g["exit_bar_low"])), abs(rb.close - fnum(g["exit_bar_close"]))) > 1e-9:
                    bad.append((t["trade_id"], "exit bar OHLC differs from raw"))
    record("independent exit walk reproduces every trade's outcome, both exit times and prices, and the source-bar OHLC", not bad, len(trades), failures=bad)
    record("leg P&L = (exit - entry) x direction x 195 per leg and the legs sum to the trade's gross P&L", not bad_pnl, len(trades), failures=bad_pnl)
    ledger_total = sum(fnum(t["gross_pnl_rs"]) for t in trades)
    record("independent total gross P&L (legs re-priced from the raw bars) equals the delivered ledger total", abs(tot - ledger_total) < 1e-6, len(trades), f"independent {tot:,.2f} vs ledger {ledger_total:,.2f}")
    net_bad = [t["trade_id"] for t in trades if abs((fnum(t["gross_pnl_rs"]) - 500.0 - 0.5 * 2 * 390) - fnum(t["illustrative_net_pnl_rs"])) > 1e-6]
    record("illustrative net = gross - Rs 500 - 0.5 point x 2 x 390 units on every trade", not net_bad, len(trades), failures=net_bad)

    # ---------- 5. stops / targets implied by the entry and the approved distances
    bad = []
    for t in trades:
        e, sg = fnum(t["entry_price"]), (1 if t["direction"] == "LONG" else -1)
        exp = (e - sg * STOP[t["strategy"]], e + sg * 27, e + sg * T2[t["strategy"]], e - sg * 6)
        got = tuple(fnum(t[k]) for k in ("initial_stop", "target_1", "target_2", "post_t1_stop"))
        if max(abs(a - b) for a, b in zip(exp, got, strict=True)) > 1e-6:
            bad.append(t["trade_id"])
    record("initial stop, Target 1, Target 2 and the post-T1 stop follow the approved distances", not bad, len(trades), failures=bad)

    # ---------- 6. strategy-specific provenance, independently recomputed
    prev_close = {str(r["date"])[:10]: r["close"] for r in pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet").to_dict("records")}
    days = sorted({d.strftime("%Y-%m-%d") for d in cand5.day})  # the evaluated sessions
    all_days = sorted({d.strftime("%Y-%m-%d") for d in allc.start})  # warm-up sessions too: the previous session of the first evaluated day lives there
    prev_of = {d: (all_days[i - 1] if i else None) for i, d in enumerate(all_days)}
    by_day5 = {d: g.reset_index(drop=True) for d, g in allc.assign(ds=allc.start.dt.strftime("%Y-%m-%d")).groupby("ds")}
    chk_by: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for c in checks:
        chk_by[c["trade_id"]][c["rule_id"]].append(c)
    bad_irf, bad_gap, bad_orb, bad_zone = [], [], [], []
    n_irf = n_gap = n_orb = n_zone = 0
    for t in trades:
        d, tid, s = t["date"], t["trade_id"], t["strategy"]
        cs_today = by_day5[d]
        if s in ("IRF", "RF"):
            n_irf += 1
            rid = "IRF-GLOBAL-001" if s == "IRF" else "RF-002"
            obs = chk_by[tid][rid][0]["observed"]
            hi, lo = (fnum(x) for x in re.findall(r"(?:IRH|RF High) ([\d,\.]+), (?:IRL|RF Low) ([\d,\.]+)", obs)[0])
            if abs(hi - cs_today.high.iloc[0]) > 1e-9 or abs(lo - cs_today.low.iloc[0]) > 1e-9:
                bad_irf.append(tid)
        gap_rule = {"PDR": "PDR-004", "PDS": "PDS-003", "RF": "RF-003"}.get(s) or ("ORB-GAP-LONG-001" if t["method"] == "Gap/200DMA" and t["direction"] == "LONG" else "ORB-GAP-SHORT-001" if t["method"] == "Gap/200DMA" else None)
        if gap_rule:
            n_gap += 1
            obs = chk_by[tid][gap_rule][0]["observed"]
            pts = float(re.findall(r"= ([+\-][\d,\.]+) points", obs)[0].replace(",", ""))
            op = by_key.loc[f"{d} 09:15", "open"]
            exp = op - float(prev_close[prev_of[d]])
            if abs(pts - exp) > 0.006:
                bad_gap.append((tid, pts, round(exp, 2)))
        if s == "ORB" and t["method"] == "Method 1":
            n_orb += 1
            pc = by_day5[prev_of[d]]
            row = next(c for c in candles if c["trade_id"] == tid and c["role"] == "prev_day_extreme_candle")
            ph, pl = pc.high.max(), pc.low.min()
            want = ph if t["direction"] == "LONG" else pl
            got = fnum(row["high"] if t["direction"] == "LONG" else row["low"])
            lvl = chk_by[tid]["ORB-M1-LONG-001" if t["direction"] == "LONG" else "ORB-M1-SHORT-001"][0]["observed"]
            shown = fnum(re.findall(r"previous-day (?:high|low) ([\d,\.]+)", lvl)[0])
            c0 = cs_today.iloc[0]
            beyond = (c0.close > want and c0.high > want) if t["direction"] == "LONG" else (c0.close < want and c0.low < want)
            if abs(got - want) > 1e-9 or abs(shown - want) > 1e-9 or not beyond:
                bad_orb.append((tid, want, got, shown, beyond))
        if s in ("PDR", "PDS"):
            n_zone += 1
            pc = by_day5[prev_of[d]].reset_index(drop=True)
            rid = "PDR-B01a" if s == "PDR" else "PDS-002"
            if s == "PDS":
                nums = [fnum(x) for x in re.findall(r"zone \[([\d,\.]+), ([\d,\.]+)\]", chk_by[tid][rid][0]["observed"])[0]]
            if s == "PDR":
                nums = [fnum(x) for x in re.findall(r"Zone \[([\d,\.]+) \(body low\), ([\d,\.]+) \(body high\)\]", chk_by[tid][rid][0]["observed"])[0]]
                bh_ = np.maximum(pc.open.to_numpy(), pc.close.to_numpy())
                pick = int(np.argmax(bh_))  # first occurrence of the previous session's highest BODY high (wicks ignored)
                exp_zone = (min(pc.open[pick], pc.close[pick]), bh_[pick])  # body low .. body high of that candle
            else:
                pick = int(pc.low.idxmin())  # first occurrence of the lowest low (tie FIRST)
                exp_zone = (pc.low[pick], max(pc.open[pick], pc.close[pick]))  # ZONE_FULL upper boundary = body top
            if exp_zone is None or abs(nums[0] - exp_zone[0]) > 1e-9 or abs(nums[1] - exp_zone[1]) > 1e-9:
                bad_zone.append((tid, nums, exp_zone))
    record("IRF IRH/IRL and RF High/Low equal the raw first 5-minute candle", not bad_irf, n_irf, failures=bad_irf)
    record("PDR/PDS/RF/ORB-gap opening gap equals raw first open minus the official previous close", not bad_gap, n_gap, failures=bad_gap)
    record("ORB Method 1 level equals the raw previous-session high/low and the first candle broke and closed beyond it", not bad_orb, n_orb, failures=bad_orb)
    record("PDR zone equals the independent previous-day highest-BODY-high candle zone (body low .. body high, wicks ignored); PDS zone equals the independent lowest-low construction", not bad_zone, n_zone, failures=bad_zone)

    # ---------- 7. completeness: daily journals, charts, selection checks, no executed trade unreported, no auto-approval
    bad = []
    days_csv = {r["date"] for r in daily}
    if len(days_csv) != 247 or days_csv != set(days):
        bad.append("daily summary days differ from the raw session list")
    tid_by_day: dict[str, list[str]] = defaultdict(list)
    for t in trades:
        tid_by_day[t["date"]].append(t["trade_id"])
    for r in daily:
        p = OUT / "daily" / r["date"][:7] / f"{r['date']}.md"
        txt = p.read_text() if p.exists() else ""
        if not txt:
            bad.append(("missing journal", r["date"]))
            continue
        for tid in tid_by_day.get(r["date"], []):
            if f"### {tid}:" not in txt:
                bad.append(("trade missing in journal", tid))
            if not (OUT / "charts" / f"{tid}.svg").exists():
                bad.append(("chart missing", tid))
        if r["owner_review_status"] != "":
            bad.append(("review status auto-filled", r["date"]))
    record("every evaluable session has a journal; every executed trade is in its journal with a chart; no review status was auto-filled", not bad, len(days_csv), failures=bad)
    sel = [t for t in trades if not any(c["rule_id"] in ("SEL-FIRST-001", "DAY-SL-001") for c in chk_by[t["trade_id"]].values() for c in c)]
    record("every trade has a selection check (SEL-FIRST-001 or DAY-SL-001)", not sel, len(trades), failures=[t["trade_id"] for t in sel])
    second = [t for t in trades if t["trade_no_of_day"] == "2"]
    first_by_day = {t["date"]: t for t in trades if t["trade_no_of_day"] == "1"}
    bad = [t["trade_id"] for t in second if t["strategy"] not in ("PDR", "PDS") or first_by_day[t["date"]]["outcome"] != "INITIAL_FULL_STOP" or t["fill_timestamp"] <= f"{t['date']} " + (first_by_day[t["date"]]["leg2_exit_time"] or "99:99")]
    record("every second trade is a PDR/PDS signal confirmed after the first trade's original full stop", not bad, len(second), failures=bad)
    bad = [t["trade_id"] for t in trades if t["checks_fail"] != "0" or t["recomputation_mismatches"]]
    record("no executed trade has a failed entry condition or a recomputation mismatch", not bad, len(trades), failures=bad)
    bad = [t["trade_id"] for t in trades if not (t["setup_explanation"] and t["selection_explanation"] and t["exit_narrative"])]
    record("every trade has a setup explanation, a selection explanation and an exit narrative", not bad, len(trades), failures=bad)

    # ---------- 8. workbook versus CSV, every row, every cell
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "NIFTY_Daily_Trade_Verification.xlsx")
    pairs = {"Daily Summary": "daily_summary.csv", "Automated Trades": "all_trades_detailed.csv", "Entry Reasons": "entry_condition_details.csv", "Exit Details": "exit_details.csv",
             "Candle Analysis": "candle_analysis.csv", "Strategy Signals": "all_strategy_signals.csv", "Ignored Signals": "ignored_signals.csv", "Rejected Signals": "rejected_signals.csv",
             "Manual Journal": "manual_journal_normalized.csv", "Journal Comparison": "manual_journal_comparison.csv", "Verification Issues": "manual_verification_issues.csv"}

    def same(cell, text: str) -> bool:
        """Excel cell versus the CSV text: numeric cells compare as numbers (1e-9), everything else as exact text (TRUE/FALSE = True/False)."""
        if cell is None:
            return text == ""
        if isinstance(cell, bool):
            return text == ("True" if cell else "False")
        if isinstance(cell, (int, float)):
            try:
                return abs(float(text) - float(cell)) < 1e-9 * max(1.0, abs(float(cell)))
            except ValueError:
                return False
        t = str(cell)
        if len(text) > 32000:  # documented Excel cell limit: the workbook holds the text cut with a visible marker
            return t.endswith(" ...[TRUNCATED IN EXCEL - full text in the CSV file]") and text.startswith(t[:-len(" ...[TRUNCATED IN EXCEL - full text in the CSV file]")])
        return t == text or {"TRUE": "True", "FALSE": "False"}.get(t) == text

    bad, cells = [], 0
    for sheet, name in pairs.items():
        data = rows(name)
        ws = wb[sheet]
        head = [c.value for c in ws[1]]
        if ws.max_row - 1 != len(data):
            bad.append((sheet, "row count", ws.max_row - 1, len(data)))
            continue
        for ri, r in enumerate(data, 2):
            for ci, h in enumerate(head, 1):
                cells += 1
                if not same(ws.cell(row=ri, column=ci).value, r.get(h, "")):
                    bad.append((sheet, ri, h))
    record("workbook equals the CSV files cell by cell (all sheets, all rows)", not bad, cells, failures=bad)

    # ---------- 9. manual comparison arithmetic, recomputed from the delivered rows and the raw journal
    cmp = rows("manual_journal_comparison.csv")
    man = [c for c in cmp if c["journal_row"]]
    matched = [c for c in man if c["match_classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")]
    extras = [c for c in cmp if c["match_classification"] == "EXTRA_AUTOMATED_TRADE"]
    bad = []
    for c in matched:
        t = tmap[c["trade_id"]]
        delta = (int(t["signal_candle_start"][:2]) * 60 + int(t["signal_candle_start"][3:])) - (int(c["manual_entry_time_label"][:2]) * 60 + int(c["manual_entry_time_label"][3:]))
        strat_ok = t["strategy"] == c["journal_strategy"] or c["matched_via_alternate_label"] == "True"
        if t["date"] != c["date"] or abs(delta) > 15 or not strat_ok or (c["match_classification"] == "EXACT_MATCH") != (delta == 0):
            bad.append((c["comparison_id"], delta))
    ids = [c["trade_id"] for c in matched]
    jr = openpyxl.load_workbook(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", data_only=True)["Trading Journal"]
    n_xlsx = sum(1 for r in jr.iter_rows(min_row=3, values_only=True) if isinstance(r[0], (int, float)))
    ok = (not bad and len(set(ids)) == len(ids) and len(matched) + len(extras) == len(trades) and len(man) == n_xlsx == 190 and len({c["journal_row"] for c in man}) == 190)
    record("manual comparison: every match is same date, <=15 minutes, unique; matched + extra automated = executed trades; 190 journal rows all present", ok, len(man), f"matched {len(matched)}, extras {len(extras)}, workbook rows {n_xlsx}", bad)

    # ---------- 10. frozen ledgers
    frozen = json.loads((ROOT / "reports/phase3/phase31/phase30_ledger_hashes.json").read_text())["hashes"]
    bad = [k for k, h in frozen.items() if hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != h]
    record("Phase 3.0 ledger files are byte-identical to the hashes frozen at the start of Phase 3.1", not bad, len(frozen), failures=bad)

    # ====================================================================== Phase 3.6 specific checks
    sys.path.insert(0, str(ROOT / "scripts"))
    import phase34_independent_audit as P34  # the Phase 3.4 independent implementation (raw data only, imports nothing from src/)
    sigs = rows("all_strategy_signals.csv")

    def body_cols(pc):
        return np.maximum(pc.open.to_numpy(), pc.close.to_numpy()), np.minimum(pc.open.to_numpy(), pc.close.to_numpy())

    def zone_body_a(pc):
        bh, bl = body_cols(pc)
        k = int(np.argmax(bh))  # first occurrence of the highest BODY high
        return float(bl[k]), float(bh[k]), k

    def zone_body_b(pc, tol=5.0, min_touch=2, sep=2):
        bh, bl = body_cols(pc)
        top, k = float(bh.max()), int(np.argmax(bh))
        piv = [j for j in range(len(bh)) if all(bh[j] >= bh[m] for m in (j - 1, j + 1) if 0 <= m < len(bh))]
        members = sorted({j for j in piv if bh[j] >= top - tol - 1e-9} | {k})
        groups = []
        for j in members:
            if groups and j - groups[-1][-1] < sep:
                groups[-1].append(j)
            else:
                groups.append([j])
        if len(groups) >= min_touch:
            return float(min(bl[j] for j in members)), top, k
        return float(bl[k]), top, k

    # ---------- 11. the PDR signals fed to the controller, rebuilt independently from the raw data (body zone, strictly above open, three patterns, strict close)
    C, M = P34.load()
    cdays = sorted(C)
    daily_close = {str(r["date"])[:10]: float(r["close"]) for r in pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet").to_dict("records")}
    mine = P34.signals(C, M, daily_close, cdays, zone_body_a, P34.TH["RESEARCH_DEFAULT"])
    mine_b = P34.signals(C, M, daily_close, cdays, zone_body_b, P34.TH["RESEARCH_DEFAULT"])
    eng = {(r["date"], r["time"]) for r in sigs if r["strategy"] == "PDR"}
    zero_h = [str(d) for i0, d in enumerate(cdays) if i0 and "2025-09-01" <= str(d) <= "2026-08-31" and (lambda z: z[1] <= z[0])(zone_body_a(C[cdays[i0 - 1]]))]
    record("the PDR signals fed to the controller equal an independent rebuild of the body-based rules (highest body high, open strictly above, three patterns, strict close) from the raw data",
           set(mine) == eng and not zero_h, len(eng), f"independent {len(mine)}, controller input {len(eng)}; only-mine {sorted(set(mine) - eng)[:3]}; only-engine {sorted(eng - set(mine))[:3]}; zero-height sessions {zero_h}")
    record("candidate B (multiple-body-high zone) rebuilt independently gives the same signals as candidate A (same ceiling by construction)", set(mine_b) == set(mine), len(mine_b), f"A {len(mine)}, B {len(mine_b)}")
    bad = []
    n_pdr = 0
    for t in trades:
        if t["strategy"] != "PDR":
            continue
        n_pdr += 1
        k = (t["date"], t["signal_candle_end"])
        m = mine.get(k)
        txt = chk_by[t["trade_id"]]["PDR-B04"][0]["observed"]
        shown = set(re.findall(r"patterns passed: ([A-Z_+, ]+?) \(engine recorded", txt)[0].replace(" ", "").split(","))
        op = float(by_key.loc[f"{t['date']} 09:15", "open"])
        pcd = [d for d in cdays if str(d) < t["date"]][-1]
        wick_hi = float(C[pcd].high.max())
        if (m is None or not float(t["signal_reference_close"]) > m["ceiling"] or not op > m["ceiling"] or shown != set(m["patterns"]) or fnum(t["entry_price"]) != float(by_key.loc[t["fill_timestamp"], "open"])
                or abs(m["ceiling"] - float(np.maximum(C[pcd].open.to_numpy(), C[pcd].close.to_numpy()).max())) > 1e-9 or (m["ceiling"] > wick_hi + 1e-9)):
            bad.append((t["trade_id"], None if m is None else (m["ceiling"], m["patterns"]), sorted(shown)))
    record("every executed PDR trade: signal in the independent rebuild, ceiling = previous-session highest BODY high (never above the wick high), open strictly above it, close strictly above it, patterns equal the explanation, entry = next 1-minute open",
           not bad, n_pdr, failures=bad)

    # ---------- 12. IRF / ORB / PDS / RF signals are identical to the Phase 3.5 AND Phase 3.2 exports (their engines were not touched)
    def sigset(rs):
        return sorted((r["date"], r["time"], r["strategy"], r["method"], r["direction"], round(float(r["reference_close"]), 6)) for r in rs if r["strategy"] != "PDR")
    with open(P35 / "all_strategy_signals.csv", newline="") as f:
        s35 = list(csv.DictReader(f))
    with open(P32 / "all_strategy_signals.csv", newline="") as f:
        s32 = list(csv.DictReader(f))
    record("the confirmed signals of IRF, ORB, PDS and RF equal the Phase 3.5 export and the Phase 3.2 export row for row (date, time, method, direction, reference close)",
           sigset(sigs) == sigset(s35) == sigset(s32), len(sigset(sigs)), f"new {len(sigset(sigs))}, Phase 3.5 {len(sigset(s35))}, Phase 3.2 {len(sigset(s32))}")
    old_pdr = {(r["date"], r["time"]) for r in s35 if r["strategy"] == "PDR"}
    record("the Phase 3.5 PDR stream (81) is still the wick-ceiling stream and differs from the body-based stream, which has a different count", len(old_pdr) == 81 and old_pdr != eng, len(eng), f"Phase 3.5 {len(old_pdr)}, Phase 3.6 {len(eng)}, common {len(old_pdr & eng)}")

    # ---------- 13. all five engines fed the controller and all five were traded
    by_strat_sig = Counter(r["strategy"] for r in sigs)
    by_strat_trd = Counter(t["strategy"] for t in trades)
    record("all five engines contributed confirmed signals and executed trades", all(by_strat_sig[x] > 0 and by_strat_trd[x] > 0 for x in ("IRF", "ORB", "PDR", "PDS", "RF")), 5,
           f"signals {dict(by_strat_sig)}, trades {dict(by_strat_trd)}")

    # ---------- 14. the controller rules, checked from the outside on the delivered tables
    trades_by_day: dict[str, list[dict]] = defaultdict(list)
    for t in trades:
        trades_by_day[t["date"]].append(t)
    sig_by_day: dict[str, list[dict]] = defaultdict(list)
    for r in sigs:
        sig_by_day[r["date"]].append(r)
    bad = []
    for d, ts in trades_by_day.items():
        ts.sort(key=lambda t: int(t["trade_no_of_day"]))
        first = ts[0]
        cands = sorted((r for r in sig_by_day[d] if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True"), key=lambda r: r["time"])
        if len(ts) > 2 or any(t["fill_timestamp"][-5:] > "13:00" for t in ts):
            bad.append((d, "more than 2 trades or a fill after 13:00"))
        if not cands or first["signal_candle_end"] != cands[0]["time"]:
            bad.append((d, "first trade is not the earliest valid signal", first["signal_candle_end"], cands[0]["time"] if cands else None))
        if len(ts) == 2:
            end = ts[0]["leg2_exit_time"]
            later = [r for r in cands if r["strategy"] in ("PDR", "PDS") and r["time"] >= end and r["time"] > ts[0]["signal_candle_end"]]
            if ts[0]["outcome"] != "INITIAL_FULL_STOP" or ts[1]["strategy"] not in ("PDR", "PDS") or not later or ts[1]["signal_candle_end"] != later[0]["time"]:
                bad.append((d, "second trade rule", ts[1]["signal_candle_end"], later[0]["time"] if later else None))
    n_conflict_days = 0
    for d, rs in sig_by_day.items():
        if d in trades_by_day:
            continue
        cands = [r for r in rs if r["fully_valid_for_execution"] == "True" and r["within_13_00_cutoff"] == "True"]
        if cands:
            first_t = min(r["time"] for r in cands)
            if len({(r["strategy"], r["direction"]) for r in cands if r["time"] == first_t}) > 1:
                n_conflict_days += 1
            else:
                bad.append((d, "valid signal exists but no trade and no same-minute conflict", first_t))
    record("controller rules: first valid signal of the day, max 2 trades, fill <= 13:00, second trade only PDR/PDS after an original full stop, no trade only if nothing was valid (or a same-minute conflict)",
           not bad, len(trades_by_day), f"{n_conflict_days} no-trade day(s) from same-minute conflicts", bad)

    # ---------- 15. strategy_performance.csv and the three-way comparison, recomputed from the three ledgers
    perf = {r["strategy"]: r for r in rows("strategy_performance.csv")}
    bad = []
    for sname in ("IRF", "ORB", "PDR", "PDS", "RF", "ALL"):
        sel = [t for t in trades if sname == "ALL" or t["strategy"] == sname]
        g = sum(fnum(t["gross_pnl_rs"]) for t in sel)
        n = sum(fnum(t["illustrative_net_pnl_rs"]) for t in sel)
        if int(perf[sname]["entries"]) != len(sel) or abs(fnum(perf[sname]["gross_pnl_rs"]) - g) > 0.01 or abs(fnum(perf[sname]["net_illustrative_pnl_rs"]) - n) > 0.01:
            bad.append((sname, perf[sname]["entries"], len(sel), perf[sname]["gross_pnl_rs"], g))
    old30 = list(csv.DictReader(open(P30 / "trades.csv")))
    old35 = list(csv.DictReader(open(P35 / "all_trades_detailed.csv")))
    cmp3 = {r["strategy"]: r for r in rows("comparison_3way_by_strategy.csv")}
    for sname in ("IRF", "ORB", "PDR", "PDS", "RF", "ALL"):
        for tag, led, qk in (("phase30", old30, "qty_total"), ("phase35", old35, "qty_total"), ("phase36", trades, "qty_total")):
            o = [r for r in led if sname == "ALL" or r["strategy"] == sname]
            og = sum(fnum(r["gross_pnl_rs"]) for r in o)
            on = sum(fnum(r["gross_pnl_rs"]) - 500.0 - 0.5 * 2 * fnum(r[qk]) for r in o)
            if int(cmp3[sname][f"{tag}_trades"]) != len(o) or abs(fnum(cmp3[sname][f"{tag}_gross_rs"]) - og) > 0.01 or abs(fnum(cmp3[sname][f"{tag}_net_rs"]) - on) > 0.01:
                bad.append((sname, tag, cmp3[sname][f"{tag}_trades"], len(o)))
    record("strategy_performance.csv and the Phase 3.0 / 3.5 / 3.6 comparison equal an independent recomputation (trade counts, gross, illustrative net) from the three ledgers", not bad, 18 + 6, failures=bad)
    monthly = {r["month"]: r for r in rows("monthly_pnl.csv")}
    bad = []
    for tag, led in (("phase30", old30), ("phase35", old35), ("phase36", trades)):
        by_m: dict[str, float] = defaultdict(float)
        for r in led:
            by_m[(r["date"])[:7]] += fnum(r["gross_pnl_rs"])
        for m_, v in by_m.items():
            if abs(fnum(monthly[m_][f"{tag}_gross_rs"]) - v) > 0.01:
                bad.append((tag, m_))
    record("monthly P&L (gross) of the three runs equals an independent recomputation", not bad, len(monthly), failures=bad)

    # ---------- 16. manual-journal matching reproduced independently
    norm = rows("manual_journal_normalized.csv")
    mins_ = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:])  # noqa: E731
    wb_times = {str(i): (x[2].strftime("%H:%M") if hasattr(x[2], "strftime") else str(x[2])[:5]) for i, x in enumerate(jr.iter_rows(values_only=True), 1) if i > 2 and isinstance(x[0], (int, float))}
    time_bad = [r["journal_row"] for r in norm if r["journal_row"] in wb_times and wb_times[r["journal_row"]] != r["entry_time_label"]]
    used, got = set(), {}
    order = sorted(norm, key=lambda m: (m["date"], mins_(m["entry_time_label"]), int(m["journal_row"])))

    def attempt(m, strat, tol, alt_used):
        best = None
        for t in trades:
            if t["date"] != m["date"] or t["strategy"] != strat or t["trade_id"] in used:
                continue
            dt = mins_(t["signal_candle_start"]) - mins_(m["entry_time_label"])
            if abs(dt) <= tol and (best is None or (abs(dt), dt) < (abs(best[1]), best[1])):
                best = (t, dt)
        if best:
            used.add(best[0]["trade_id"])
            got[m["journal_row"]] = (best[0]["trade_id"], best[1], alt_used)
            return True
        return False
    for tol in (0, 15):
        for m in order:
            if m["journal_row"] not in got and m["session_status"] != "NO_SESSION":
                attempt(m, m["strategy_normalized"], tol, False)
        for m in order:
            if m["journal_row"] not in got and m["session_status"] != "NO_SESSION" and m["alt_strategy_candidate"]:
                attempt(m, m["alt_strategy_candidate"], tol, True)
    delivered = {c["journal_row"]: (c["trade_id"], int(c["delta_minutes"]), c["matched_via_alternate_label"] == "True") for c in man if c["match_classification"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")}
    record("manual journal matching reproduced independently equals the delivered matches (same journal row -> same trade, same delta)", got == delivered and not time_bad, len(got),
           f"independent {len(got)} matches ({sum(1 for v in got.values() if v[1] == 0)} exact), delivered {len(delivered)}; journal time labels equal the workbook: {not time_bad}")

    # ---------- 17. every trade has a stable id linking CSV, workbook, daily journal and chart; ids are unique
    ids = [t["trade_id"] for t in trades]
    bad = [i for i in ids if not (OUT / "charts" / f"{i}.svg").exists() or f"### {i}:" not in (OUT / "daily" / f"{i[:4]}-{i[4:6]}" / f"{i[:4]}-{i[4:6]}-{i[6:8]}.md").read_text()]
    record("every trade id is unique and links to its chart and its daily-journal section", len(set(ids)) == len(ids) and not bad, len(ids), failures=bad)

    # ---------- 18. nothing else changed: data, earlier reports (3.0 - 3.5), other engines, both earlier PDR engines, the controller (hash snapshot taken before the first Phase 3.6 edit)
    snap = json.loads((OUT / "before_snapshot.json").read_text())["files"]
    allowed_changed = {  # the only pre-existing files Phase 3.6 edited (engine selection, explainer, workbook / journal labels, the CLI); each is reviewed in independent_audit.md
        "src/nifty_trading/research/phase3.py", "src/nifty_trading/research/phase31.py", "src/nifty_trading/research/phase32.py", "src/nifty_trading/research/phase32_build.py",
        "src/nifty_trading/research/phase32_render.py", "src/nifty_trading/research/phase32_excel.py", "scripts/phase35_run.py"}
    changed, missing = [], []
    for pth, h in snap.items():
        f = ROOT / pth
        if not f.exists():
            missing.append(pth)
        elif hashlib.sha256(f.read_bytes()).hexdigest() != h and pth not in allowed_changed:
            changed.append(pth)
    record("every data file, every earlier report (Phase 2.x - 3.5), every other engine, both earlier PDR engines, the controller and every other file of the before-snapshot is byte-identical (only the listed research modules / CLI changed)",
           not changed and not missing, len(snap), f"allowed edits: {sorted(allowed_changed)}", changed + missing)
    engines_untouched = [x for x in ("irf", "orb", "pds", "rf", "pdr", "pdr_revised", "trading_day", "selection", "base", "params", "definitions") if f"src/nifty_trading/strategies/{x}.py" in snap
                         and hashlib.sha256((ROOT / f"src/nifty_trading/strategies/{x}.py").read_bytes()).hexdigest() != snap[f"src/nifty_trading/strategies/{x}.py"]]
    record("the five engines, the Phase 3.4 / 3.5 PDR engine, the controller, the selection rules and the parameter definitions are byte-identical", not engines_untouched, 11, failures=engines_untouched)
    p35_files = [k for k in snap if k.startswith("reports/phase3/phase35_combined/")]
    p35_bad = [k for k in p35_files if not (ROOT / k).exists() or hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != snap[k]]
    record("every file of the Phase 3.5 results directory is byte-identical to its pre-Phase-3.6 hash", not p35_bad and len(p35_files) > 100, len(p35_files), failures=p35_bad)

    RES["strategy_outcome_coverage"] = {f"{k[0]}|{k[1]}": v for k, v in sorted(outcome_counts.items())}
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
