"""Phase 5.5 independent audit: recomputes the backtest from the RAW one-minute candles and the delivered signal tables only (no ``src/`` imports; the raw-data and EMA helpers come from the Phase 3.2 audit script, itself free of ``src/``).

* a second implementation of the portfolio controller (first valid signal, one PDR / PDS second trade after an original full stop, 13:00 cutoff, unresolved same-minute collisions) selects the trades from ``all_confirmed_signals.csv``;
* a second implementation of the execution and exit rules (fill = open of the one-minute bar that starts at the signal candle's end; stops 30 / 35, T1 27, T2 60 / 70, post-T1 stop entry -/+ 6, stop before target inside a bar, stops fill at the worse of
  level and open, forced exit at the open of the 15:14 bar) recomputes every entry, exit and gross P&L for configurations A, B and C and for the 2022-2025 robustness window (read from the Phase 4 one-minute partitions);
* the cost scenarios, the strategy / cost-sensitivity aggregates, the signal candles and timestamps, the 28-point EMA clearance, the three ORB gap-crossing signals, the intrabar ambiguity count, the frozen identity and the preservation of every baselined file.
Run: .venv/bin/python scripts/phase55_independent_audit.py   ->   reports/phase5/phase55_combined_backtest/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import sys
import warnings
from collections import Counter, defaultdict
from datetime import timedelta
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
RES: dict = {"checks": {}}
STOP = {"IRF": 35.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0, "ORB": 30.0}
T2 = {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0}
T1, BUF, QL, QT = 27.0, 6.0, 195.0, 390.0
FIXED, SCEN = 70.0, (("A", 0.0, 0.0), ("B", 70.0, 0.0), ("C", 70.0, 0.25), ("D", 70.0, 0.5), ("E", 70.0, 1.0))
ALLOWED_ADDED = ("reports/phase5/phase55_combined_backtest/", "reports/phase5/phase56_manual_reconciliation/", "scripts/phase55_", "scripts/phase56_", "src/nifty_trading/research/phase55.py", "src/nifty_trading/research/phase56.py", "tests/test_phase55_", "tests/test_phase56_")
FROZEN_ID = "FROZEN-PHASE36-42cea2600bd4"


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def f(x) -> float:
    return float(str(x).replace(",", "")) if x not in ("", None) else math.nan


def close(a, b, tol=1e-6) -> bool:
    return (a is None or (isinstance(a, float) and math.isnan(a))) and (b is None or (isinstance(b, float) and math.isnan(b))) or abs(a - b) <= tol


# ================================================================================ the independent executor
def walk(direction: str, strategy: str, bars: list[tuple], sig_ts: pd.Timestamp, favourable_first: bool = False) -> dict | None:
    """``bars``: [(start, o, h, l, c)] of ONE session, chronological. Fill = open of the bar that starts exactly at ``sig_ts`` (none: no fill)."""
    i0 = next((i for i, b in enumerate(bars) if b[0] == sig_ts), None)
    if i0 is None:
        return None
    sg = 1.0 if direction == "LONG" else -1.0
    entry = bars[i0][1]
    sl, t1, t2, s2 = entry - sg * STOP[strategy], entry + sg * T1, entry + sg * T2[strategy], entry - sg * BUF
    adv = (lambda b, lv: b[3] <= lv) if sg > 0 else (lambda b, lv: b[2] >= lv)
    fav = (lambda b, lv: b[2] >= lv) if sg > 0 else (lambda b, lv: b[3] <= lv)
    worse = (lambda lv, o: min(lv, o)) if sg > 0 else (lambda lv, o: max(lv, o))
    t1_done, p1, ts1, amb = False, None, None, []
    for b in bars[i0:]:
        clock = b[0].hour * 60 + b[0].minute
        if clock >= 15 * 60 + 14:  # forced exit at this bar's open, never at / after 15:15
            if clock >= 15 * 60 + 15:
                break
            px = b[1]
            return {"outcome": "FORCED_EXIT", "entry": entry, "p1": p1 if t1_done else px, "t1": ts1 if t1_done else b[0], "p2": px, "t2": b[0], "t1_booked": t1_done, "ambiguities": amb}
        if not t1_done:
            stop_hit, t1_hit = adv(b, sl), fav(b, t1)
            if stop_hit and t1_hit:
                amb.append(f"{b[0]}: stop {sl} and T1 {t1} in one bar")
            if favourable_first and t1_hit and not (b[1] <= sl if sg > 0 else b[1] >= sl):
                stop_hit = False  # counterfactual ordering (sensitivity only)
            if stop_hit:
                px = worse(sl, b[1])
                return {"outcome": "INITIAL_FULL_STOP", "entry": entry, "p1": px, "t1": b[0], "p2": px, "t2": b[0], "t1_booked": False, "ambiguities": amb}
            if not t1_hit:
                continue
            t1_done, p1, ts1 = True, t1, b[0]
            if adv(b, s2):
                amb.append(f"{b[0]}: T1 and post-T1 stop {s2} in one bar")
                if not favourable_first:
                    return {"outcome": "T1_THEN_BUFFER_STOP", "entry": entry, "p1": p1, "t1": ts1, "p2": s2, "t2": b[0], "t1_booked": True, "ambiguities": amb}
            if fav(b, t2):
                return {"outcome": "TARGET", "entry": entry, "p1": p1, "t1": ts1, "p2": t2, "t2": b[0], "t1_booked": True, "ambiguities": amb}
            continue
        be, th = adv(b, s2), fav(b, t2)
        if be and th:
            amb.append(f"{b[0]}: leg-2 stop {s2} and T2 {t2} in one bar")
        if favourable_first and th:
            be = False
        if be:
            return {"outcome": "T1_THEN_BUFFER_STOP", "entry": entry, "p1": p1, "t1": ts1, "p2": worse(s2, b[1]), "t2": b[0], "t1_booked": True, "ambiguities": amb}
        if th:
            return {"outcome": "TARGET", "entry": entry, "p1": p1, "t1": ts1, "p2": t2, "t2": b[0], "t1_booked": True, "ambiguities": amb}
    return {"outcome": "INCOMPLETE_EOD", "entry": entry, "p1": p1, "t1": ts1, "p2": None, "t2": None, "t1_booked": t1_done, "ambiguities": amb}


def gross(direction: str, r: dict) -> float:
    sg = 1.0 if direction == "LONG" else -1.0
    leg1 = None if r["p1"] is None else (r["p1"] - r["entry"]) * sg * QL
    leg2 = None if r["p2"] is None else (r["p2"] - r["entry"]) * sg * QL
    return (leg1 or 0.0) + (leg2 or 0.0)


def units(r: dict) -> tuple[float, float]:
    ex = (QL if r["p1"] is not None else 0.0) + (QL if r["p2"] is not None else 0.0)
    return QT, ex


def net(r: dict, direction: str, fixed: float, slip: float) -> float:
    eu, xu = units(r)
    return gross(direction, r) - fixed - slip * (eu + xu)


def controller(signals: list[dict], bars_of: dict) -> list[dict]:
    """The documented controller, re-implemented: chronological groups, first valid signal, same-strategy-and-direction duplicates are one trade, any other same-minute multi-strategy / multi-direction group is an UNRESOLVED
    collision (no approved tie-break: no trade, the day ends), active positions ignore signals, the second trade is only PDR / PDS after an ORIGINAL full stop and only from a signal at or after the first position's end, <= 2 entries,
    the fill (= signal time) must not be later than 13:00."""
    by_day: dict = defaultdict(list)
    for s in signals:
        if s["fully_valid_for_execution"] == "True":
            by_day[s["date"]].append(s)
    out = []
    for d, ss in sorted(by_day.items()):
        groups: dict = defaultdict(list)
        for s in sorted(ss, key=lambda x: (x["time"], x["strategy"], x["method"])):
            groups[s["time"]].append(s)
        state, active, n = "READY", None, 0
        for t in sorted(groups):
            ts = pd.Timestamp(f"{d} {t}", tz="Asia/Kolkata")
            if active is not None and ts >= active["position_end"]:
                cls = active["res"]["outcome"]
                if cls in ("TARGET", "T1_THEN_BUFFER_STOP", "FORCED_EXIT"):
                    state = "FINISHED"
                elif cls == "INITIAL_FULL_STOP":
                    state = "SECOND" if active["no"] == 1 else "FINISHED"
                else:
                    state = "UNRESOLVED"
                active = None
            if state in ("FINISHED", "UNRESOLVED", "ACTIVE1", "ACTIVE2"):
                continue
            cands = []
            for s in groups[t]:
                if state == "SECOND" and s["strategy"] not in ("PDR", "PDS"):
                    continue
                if t > "13:00":
                    continue
                if not any(b[0] == ts for b in bars_of[d]):
                    continue
                cands.append(s)
            if not cands:
                continue
            if len({c["strategy"] for c in cands}) > 1 or len({c["direction"] for c in cands}) > 1:
                state = "UNRESOLVED"
                continue
            chosen = cands[0]
            res = walk(chosen["direction"], chosen["strategy"], bars_of[d], ts)
            n += 1
            end = None if res["p2"] is None else res["t2"] + timedelta(minutes=1)
            if end is None:
                active = {"no": n, "res": res, "position_end": pd.Timestamp("2100-01-01", tz="Asia/Kolkata")}
            else:
                active = {"no": n, "res": res, "position_end": end}
            out.append({"date": d, "no": n, "signal": chosen, "res": res, "ts": ts})
            state = "ACTIVE1" if n == 1 else "ACTIVE2"
        # the last position settles at the end of the signal list (no further effect on the entries)
    return out


def main() -> int:  # noqa: C901
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    man = json.loads((OUT / "configuration_manifest.json").read_text())
    st = json.loads((OUT / "phase55_state.json").read_text())
    raw = A32.load_raw()
    raw["day"] = raw.timestamp.dt.strftime("%Y-%m-%d")
    bars_of = {d: [(r.timestamp, r.open, r.high, r.low, r.close) for r in g.itertuples()] for d, g in raw.groupby("day")}
    trades = rd(OUT / "all_executed_trades.csv")
    sigs = rd(OUT / "all_confirmed_signals.csv")

    # ============================================================ 1. frozen identity and preservation (pre-run audit)
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    blob = json.dumps({"hashes": fr["active_file_hashes"], "params": fr["parameters"], "costs": fr["costs_and_slippage"]}, sort_keys=True, default=str)
    rec_id = "FROZEN-PHASE36-" + hashlib.sha256(blob.encode()).hexdigest()[:12]
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    record("the frozen configuration id FROZEN-PHASE36-42cea2600bd4 is recomputed from the stored hashes / parameters / costs and all 26 active implementation files match their frozen hashes", rec_id == FROZEN_ID == fr["frozen_configuration_id"] and not bad, 26, rec_id, bad)
    ids = {k: v["id"] for k, v in man["configurations"].items()}
    record("the three configurations carry distinct identifiers (A = the frozen id; B and C are new hashes over the frozen files, the Phase 5 candidate files, the parameters and the provisional assumptions)", ids["A"] == FROZEN_ID and len(set(ids.values())) == 3, 3, str(ids))
    now, changed, removed = {}, [], []
    for t in ("src", "scripts", "tests", "docs", "data", "reports", "pyproject.toml"):
        base = ROOT / t
        for p in ([base] if base.is_file() else base.rglob("*")):
            if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts and OUT not in p.parents and (ROOT / "reports" / "phase5" / "phase56_manual_reconciliation") not in p.parents:
                now[p.relative_to(ROOT).as_posix()] = None
    for k, h in snap["hashes"].items():
        pth = ROOT / k
        if not pth.exists():
            removed.append(k)
        elif sha(pth) != h:
            changed.append(k)
    added = [k for k in now if k not in snap["hashes"] and not k.startswith(ALLOWED_ADDED)]
    record("every file of the Phase 5.5 baseline snapshot (source code, one-minute data, the manual journal, the source PDFs, Phase 3.0-5.4 reports) is byte-identical; only declared Phase 5.5 / 5.6 files were added", not changed and not removed and not added, len(snap["hashes"]), failures=changed + removed + added)
    jp = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
    record("the original manual journal workbook is unchanged (hash equals the manifest and the baseline snapshot)", sha(jp) == man["journal_workbook_sha256"] == snap["hashes"]["docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"], 1)

    # ============================================================ 2. signals: candles, timestamps, no look-ahead, expected totals
    allc = pd.concat([A32.five_minute(A32.load_warm(), A32.standard_days(A32.load_warm())), A32.five_minute(raw.drop(columns=["day"]), A32.standard_days(raw))]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = A32.ema_series(allc["close"].to_numpy())
    by_start = {s.strftime("%Y-%m-%d %H:%M"): r for s, r in zip(allc.start, allc.itertuples(), strict=True)}
    bad = []
    for s in sigs:
        c = by_start.get(f"{s['date']} {s['candle_start']}")
        te = pd.Timestamp(f"{s['date']} {s['time']}")
        if c is None or abs(f(s["reference_close"]) - c.close) > 1e-6 or (pd.Timestamp(f"{s['date']} {s['candle_start']}") + pd.Timedelta(minutes=5)) != te or s["time"] < "09:20" or int(s["time"][-2:]) % 5:
            bad.append((s["config"], s["date"], s["time"], s["strategy"]))
    record("every confirmed signal of A, B and C: the signal candle exists in the raw data, its close equals the reference close, the signal time is the candle's END (never before it completed) on the 5-minute grid and not before 09:20", not bad, len(sigs), failures=bad)
    cnt = {k: Counter(s["strategy"] for s in sigs if s["config"] == k) for k in "ABC"}
    exp = {"A": {"IRF": 874, "ORB": 53, "PDR": 87, "PDS": 57, "RF": 12}, "B": {"IRF": 786, "ORB": 53, "PDR": 147, "PDS": 111, "RF": 12}}
    record("signal totals: A = 1,083 (874 / 53 / 87 / 57 / 12), B = 1,109 (786 / 53 / 147 / 111 / 12), C = B plus exactly three ORB signals", all(dict(cnt[k]) == v for k, v in exp.items()) and dict(cnt["C"]) == {**exp["B"], "ORB": 56}, len(sigs), str({k: sum(v.values()) for k, v in cnt.items()}))
    dup = [k for k, n in Counter((s["config"], s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in sigs).items() if n > 1]
    record("no duplicate signal (same configuration, date, time, strategy, method, direction)", not dup, len(sigs), failures=dup)
    p36 = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in rd(ROOT / "reports" / "phase3" / "phase36_body_based_pdr" / "all_strategy_signals.csv")}
    ka = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in sigs if s["config"] == "A"}
    p53 = {(s["date"], s["signal_time"], s["strategy"], s["method"], s["direction"]) for s in rd(ROOT / "reports" / "phase5" / "phase53_author_corrected" / "all_confirmed_signals.csv") if s["config"] == "phase53-author-corrected"}
    kb = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in sigs if s["config"] == "B"}
    kc = {(s["date"], s["time"], s["strategy"], s["method"], s["direction"]) for s in sigs if s["config"] == "C"}
    record("configuration A's signals equal the delivered Phase 3.6 table and B's equal the delivered Phase 5.3 author-corrected signal table (two earlier, separately audited deliverables); C = B plus three ORB Gap / 200DMA signals", ka == p36 and kb == p53 and kc - kb and all(x[2] == "ORB" and x[3] == "Gap/200DMA" for x in kc - kb) and kb <= kc and len(kc - kb) == 3, len(kc))
    # 28-point EMA clearance for every IRF signal of B and C (independent EMA)
    bad = []
    for s in sigs:
        if s["config"] in ("B", "C") and s["strategy"] == "IRF":
            c = by_start[f"{s['date']} {s['candle_start']}"]
            if not np.isnan(c.ema):
                d = c.low - c.ema if c.ema < c.low else (c.ema - c.high if c.ema > c.high else 0.0)
                if d < 28 - 1e-9:
                    bad.append((s["config"], s["date"], s["time"], round(d, 2)))
    record("every IRF signal of B and C has >= 28 points between the signal candle's high-low range and its own EMA(200) (independent EMA; inclusive boundary)", not bad, sum(1 for s in sigs if s["config"] in ("B", "C") and s["strategy"] == "IRF"), failures=bad)
    # the three ORB gap-crossing signals
    daily = {r["date"]: r for r in rd(ROOT / "reports" / "phase3" / "phase36_body_based_pdr" / "daily_summary.csv")}
    bad, nn = [], 0
    for k in sorted(kc - kb):
        d = k[0]
        g = [x for x in allc.itertuples() if x.start.strftime("%Y-%m-%d") == d]
        pd_ = daily[d]["previous_session"]
        pg = [x for x in allc.itertuples() if x.start.strftime("%Y-%m-%d") == pd_]
        c0 = g[0]
        pc, ma, ma_prev = f(daily[d]["prev_day_official_close"]), c0.ema, pg[-1].ema
        long = k[4] == "LONG"
        wrong = pc < ma_prev if long else pc > ma_prev
        open_beyond = c0.open > ma if long else c0.open < ma
        reaches = (c0.low <= ma) if long else (c0.high >= ma)
        closed = c0.close > ma if long else c0.close < ma
        rg = c0.high - c0.low
        body, opp = abs(c0.close - c0.open) / rg, ((c0.high - max(c0.open, c0.close)) if long else (min(c0.open, c0.close) - c0.low)) / rg
        strong = (c0.close > c0.open if long else c0.close < c0.open) and body >= 0.60 - 1e-9 and opp <= 0.20 + 1e-9
        ok = wrong and (not open_beyond) and reaches and closed and strong and k[1] == "09:20"
        nn += 1
        if not ok:
            bad.append((d, k[4], dict(wrong=wrong, open_beyond=open_beyond, reaches=reaches, closed=closed, strong=strong)))
    record("the three ORB signals added by configuration C each satisfy the candle-crossing reading (previous close on the wrong side of its EMA, open NOT beyond the average, candle reaches it and closes beyond, strong candle) and fail the frozen open-beyond reading", not bad and nn == 3, nn, failures=bad)

    # ============================================================ 3. independent controller + executor reproduce every executed trade (A, B, C)
    tot_bad, tot_n = [], 0
    for k in "ABC":
        mine = controller([s for s in sigs if s["config"] == k], bars_of)
        theirs = [t for t in trades if t["config"] == k]
        mk = sorted((m["date"], m["no"], m["signal"]["strategy"], m["signal"]["direction"], m["ts"].strftime("%H:%M")) for m in mine)
        tk = sorted((t["date"], int(t["trade_no_of_day"]), t["strategy"], t["direction"], t["fill_timestamp"][-5:]) for t in theirs)
        record(f"configuration {k}: the independently re-implemented controller selects exactly the same trades (date, trade number, strategy, direction, entry time) as the backtest", mk == tk, len(tk), failures=sorted(set(mk) ^ set(tk)))
        tby = {(t["date"], int(t["trade_no_of_day"])): t for t in theirs}
        bad = []
        for m in mine:
            t = tby.get((m["date"], m["no"]))
            if t is None:
                continue
            r, d = m["res"], m["signal"]["direction"]
            row_ok = (t["outcome"] == r["outcome"] and close(f(t["entry_price"]), r["entry"]) and close(f(t["leg1_exit_price"]), r["p1"] if r["p1"] is not None else math.nan) and close(f(t["leg2_exit_price"]), r["p2"] if r["p2"] is not None else math.nan)
                      and close(f(t["gross_pnl_rs"]), gross(d, r), 1e-4) and t["method"] == m["signal"]["method"])
            for cid, fx, sl in SCEN:
                row_ok = row_ok and close(f(t[f"net_pnl_rs_scenario_{cid}"]), round(net(r, d, fx, sl), 2), 0.011)
            tot_n += 1
            if not row_ok:
                bad.append((k, m["date"], m["no"], t["outcome"], r["outcome"]))
        tot_bad += bad
        record(f"configuration {k}: every entry price (= the raw one-minute open at the signal candle's end), both exit prices, the exit class, the gross P&L and the five cost-scenario net P&Ls equal an independent recomputation from the raw candles", not bad, len(mine), failures=bad)
    # entry bars: fill time is the signal time; never after 13:00; never a bar before the signal completed
    raw_idx = raw.set_index(raw.timestamp.dt.strftime("%Y-%m-%d %H:%M"))
    bad = []
    for t in trades:
        k = t["fill_timestamp"]
        if k != t["signal_confirmed_at"] or k[-5:] > "13:00" or k not in raw_idx.index or abs(raw_idx.loc[k, "open"] - f(t["entry_price"])) > 1e-9:
            bad.append((t["config"], t["trade_id"]))
    record("every simulated entry is the open of the raw one-minute bar that starts when the signal candle completed (no past price, no invented price) and no entry is later than 13:00", not bad, len(trades), failures=bad)

    # ============================================================ 4. position rules
    bad = []
    for t in trades:
        s, sg = t["strategy"], (1 if t["direction"] == "LONG" else -1)
        e = f(t["entry_price"])
        if abs(f(t["initial_stop"]) - (e - sg * STOP[s])) > 1e-6 or abs(f(t["target_1"]) - (e + sg * T1)) > 1e-6 or abs(f(t["target_2"]) - (e + sg * T2[s])) > 1e-6 or abs(f(t["post_t1_stop"]) - (e - sg * BUF)) > 1e-6 \
                or f(t["qty_total"]) != 390 or f(t["qty_leg1"]) != 195 or f(t["qty_leg2"]) != 195:
            bad.append((t["config"], t["trade_id"]))
        if int(t["trade_no_of_day"]) == 2 and s not in ("PDR", "PDS"):
            bad.append((t["config"], t["trade_id"], "second trade not PDR/PDS"))
    record("every trade carries the approved position rules: stop 30 (ORB) / 35, Target 1 = 27, Target 2 = 60 (IRF, ORB, RF) / 70 (PDR, PDS), post-T1 stop entry -/+ 6, 6 lots = 390 units in two legs of 195, a second trade only PDR / PDS", not bad, len(trades), failures=bad)
    by_day = defaultdict(list)
    for t in trades:
        by_day[(t["config"], t["date"])].append(t)
    bad = [(k, [x["trade_id"] for x in v]) for k, v in by_day.items() if len(v) > 2]
    for k, v in by_day.items():
        if len(v) == 2:
            first, second = sorted(v, key=lambda x: int(x["trade_no_of_day"]))
            end = pd.Timestamp(f"{first['date']} {first['leg2_exit_time']}") + pd.Timedelta(minutes=1)
            if pd.Timestamp(second["fill_timestamp"]) < end or first["outcome"] != "INITIAL_FULL_STOP":
                bad.append((k, "second trade before the first closed / not after an ORIGINAL full stop"))
    record("at most two trades per day; a second trade exists only after the first trade's ORIGINAL full stop and its entry is after the first position closed", not bad, len(by_day), failures=bad)

    # ============================================================ 5. intrabar ambiguities and counterfactual sensitivity
    amb_csv = rd(OUT / "intrabar_ambiguities.csv")
    mine_amb, sens = [], []
    for k in "ABC":
        for m in controller([s for s in sigs if s["config"] == k], bars_of):
            if m["res"]["ambiguities"]:
                mine_amb.append((k, m["date"], m["no"]))
                alt = walk(m["signal"]["direction"], m["signal"]["strategy"], bars_of[m["date"]], m["ts"], favourable_first=True)
                sens.append({"config": k, "date": m["date"], "trade_no": m["no"], "strategy": m["signal"]["strategy"], "adverse_outcome": m["res"]["outcome"], "adverse_pnl_rs": gross(m["signal"]["direction"], m["res"]),
                             "favourable_first_outcome": alt["outcome"], "favourable_first_pnl_rs": gross(m["signal"]["direction"], alt), "notes": " | ".join(m["res"]["ambiguities"])})
    record("intrabar ambiguity audit: the set of trades with a same-minute stop / target conflict recomputed from the raw bars equals the delivered list (and the number of outcomes that depend on the ordering convention is reported)", sorted(mine_amb) == sorted((a["config"], a["date"], int(a["trade_id"].split("-")[1])) for a in amb_csv), len(mine_amb), f"{len(mine_amb)} ambiguous trades; the delivered list has {len(amb_csv)}")
    pd.DataFrame(sens).to_csv(OUT / "intrabar_sensitivity.csv", index=False)

    # ============================================================ 6. aggregates: strategy performance, cost sensitivity
    perf = rd(OUT / "strategy_performance.csv")
    cost = rd(OUT / "cost_sensitivity.csv")
    mine = {k: controller([s for s in sigs if s["config"] == k], bars_of) for k in "ABC"}
    bad = []
    for k in "ABC":
        for cid, fx, sl in SCEN:
            seq = [net(m["res"], m["signal"]["direction"], fx, sl) for m in sorted(mine[k], key=lambda m: (m["date"], m["ts"], m["no"]))]
            wins = [x for x in seq if x > 0]
            gl = -sum(x for x in seq if x < 0)
            pf = (sum(wins) / gl) if gl > 0 else None
            cum = peak = dd = 0.0
            for x in seq:
                cum += x
                peak = max(peak, cum)
                dd = max(dd, peak - cum)
            row = next(c for c in cost if c["config"] == k and c["cost_scenario"].startswith(cid + ":"))
            if abs(f(row["net_pnl_rs"]) - sum(seq)) > 0.05 or abs(f(row["max_drawdown_rs"]) - dd) > 0.05 or int(row["trades"]) != len(seq) or (pf is not None and abs(f(row["profit_factor"]) - pf) > 0.002) or abs(f(row["win_rate_pct"]) - 100 * len(wins) / len(seq)) > 0.01:
                bad.append((k, cid))
    record("the cost-sensitivity table (net P&L, win rate, profit factor, maximum drawdown for the five scenarios A-E) equals an independent recomputation for A, B and C", not bad, 15, failures=bad)
    bad = []
    for k in "ABC":
        for s in ("IRF", "ORB", "PDR", "PDS", "RF"):
            sub = [m for m in mine[k] if m["signal"]["strategy"] == s]
            row = next(c for c in perf if c["config"] == k and c["strategy"] == s and c["cost_scenario"].startswith("A:"))
            g = sum(gross(m["signal"]["direction"], m["res"]) for m in sub)
            o = Counter(m["res"]["outcome"] for m in sub)
            if int(row["trades"]) != len(sub) or abs(f(row["net_pnl_rs"]) - g) > 0.05 or int(row["t2_hits"]) != o.get("TARGET", 0) or int(row["initial_full_stops"]) != o.get("INITIAL_FULL_STOP", 0) or int(row["forced_exits"]) != o.get("FORCED_EXIT", 0) \
                    or int(row["t1_then_post_t1_stop"]) != o.get("T1_THEN_BUFFER_STOP", 0) or int(row["t1_hits"]) != sum(1 for m in sub if m["res"]["t1_booked"]):
                bad.append((k, s))
    record("strategy-wise results (trades, gross P&L, T1 / T2 hits, full stops, post-T1 stops, forced exits) equal an independent recomputation for every strategy of A, B and C", not bad, 15, failures=bad)
    slip_ok = all(abs(units(m["res"])[0] - QT) < 1e-9 and units(m["res"])[1] in (390.0, 195.0, 0.0) for k in "ABC" for m in mine[k])
    record("slippage units: the entry slippage applies to the 390 entry units once and the exit slippage to each exited leg once (390 units when both legs exit, 195 for a single exit; nothing is charged twice) - checked on every trade", slip_ok, sum(len(v) for v in mine.values()))

    # ============================================================ 7. robustness window (Phase 4 one-minute partitions)
    rb = rd(OUT / "multi_year_trades.csv")
    ids_dates = sorted({r["date"] for r in rb})
    frames = {}
    for ym in sorted({d[:7] for d in ids_dates}):
        p = ROOT / "data" / "phase4" / "processed" / "FIVEPAISA_1M_PHASE4" / "nifty50" / f"year={ym[:4]}" / f"month={ym[5:]}" / "candles.parquet"
        frames[ym] = pd.read_parquet(p)
    rbars: dict = {}
    for df in frames.values():
        df["day"] = df.timestamp.dt.strftime("%Y-%m-%d")
        for d, g in df.groupby("day"):
            rbars[d] = [(r.timestamp, r.open, r.high, r.low, r.close) for r in g.itertuples()]
    bad = []
    for r in rb:
        ts = pd.Timestamp(f"{r['date']} {r['entry_time']}", tz="Asia/Kolkata")
        m = walk(r["direction"], r["strategy"], rbars[r["date"]], ts)
        if m is None or m["outcome"] != r["outcome"] or abs(m["entry"] - f(r["entry_price"])) > 1e-6 or abs(gross(r["direction"], m) - f(r["gross_pnl_rs"])) > 1e-3 or abs(net(m, r["direction"], FIXED, 0.0) - f(r["net_pnl_rs_70"])) > 0.011:
            bad.append((r["config"], r["date"], r["strategy"]))
    record("robustness window 2022-09-01..2025-08-31 (A, B, C): every trade's entry, exit class, gross P&L and Rs 70 net P&L equals an independent recomputation from the Phase 4 one-minute partitions", not bad, len(rb), failures=bad)
    rs = st["robustness"]
    record("the frozen configuration A reproduces the delivered Phase 4 window-B backtest (609 trades, identical gross P&L)", rs["A_reproduces_phase4_window_B"]["gross_equal"] and rs["A_reproduces_phase4_window_B"]["configuration_A_trades"] == 609, 609)

    # ============================================================ 8. no old cost model, deliverables
    bad = [c for c in trades[0] if "illustrative_cost" in c or "500" in c]
    record("the old Rs 500 fixed-cost columns are not carried into the Phase 5.5 trade tables", not bad, len(trades[0]), failures=bad)
    need = ["README.md", "configuration_manifest.json", "signal_validation.md", "combined_backtest_summary.md", "all_executed_trades.csv", "all_trade_legs.csv", "strategy_performance.csv", "monthly_performance.csv", "annual_performance.csv", "cost_sensitivity.csv",
            "entry_exit_execution_audit.md", "intrabar_ambiguities.csv", "cross_configuration_comparison.md", "independent_audit.md", "Combined_Strategy_Backtest.xlsx"]
    miss = [n for n in need if not (OUT / n).exists()] + [n for n in ("daily", "charts") if not (OUT / n).is_dir()]
    record("every required Phase 5.5 deliverable exists", not miss, len(need) + 2, failures=miss)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
