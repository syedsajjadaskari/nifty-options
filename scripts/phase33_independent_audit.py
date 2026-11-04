"""Phase 3.3 independent audit of the PDR audit's own outputs. Imports NOTHING from ``nifty_trading`` and NOTHING from ``phase33_lib`` / ``phase33_pdr_audit``: the 5-minute candles,
swing highs, zones, the PDR sequence, the counts and the journal comparison are rebuilt here by a different route (pandas resampling and vectorised swing detection instead of the
analysis script's bucket loops), directly from the raw parquet files and the raw journal workbook, and compared with the delivered CSV / SVG files.

Writes reports/phase3/phase33_pdr_audit/independent_audit_results.json and prints a summary. Exit code 1 if a hard check fails.
"""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
import sys
from collections import Counter
from pathlib import Path

import numpy as np
import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase33_pdr_audit"
P32 = ROOT / "reports" / "phase3" / "phase32"
RES: dict = {"checks": {}}


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "n_failures": len(failures or []), "failures": (failures or [])[:12]}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""))


def rd(path: Path) -> list[dict]:
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fl(x) -> float:
    return float(str(x).replace(",", ""))


def load_five_minute() -> dict:
    """date -> DataFrame(start, open, high, low, close) of COMPLETE 5-minute candles of standard sessions, through pandas resampling."""
    frames = [pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / "data/processed/nifty50_warmup/**/*.parquet"), recursive=True))]
    frames += [pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / "data/processed/nifty50/**/*.parquet"), recursive=True))]
    df = pd.concat(frames).drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
    out, minutes = {}, {}
    for day, g in df.groupby(df.index.date):
        mod = g.index.hour * 60 + g.index.minute
        if not (mod.min() == 555 and len(g) >= 300):  # standard sessions only
            continue
        g = g[(mod >= 555) & (mod <= 929)]
        r = g.resample("5min", origin=g.index[0].normalize() + pd.Timedelta(hours=9, minutes=15)).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "count"})
        r = r[r["volume"] == 5].drop(columns="volume").reset_index().rename(columns={"timestamp": "start"})
        out[day], minutes[day] = r, g
    return {"candles": out, "minutes": minutes}


def swing_high_idx(h: np.ndarray, k: int = 2) -> list[int]:
    n = len(h)
    ok = np.ones(n, dtype=bool)
    ok[:k] = ok[n - k:] = False
    for m in range(1, k + 1):
        ok[k:n - k] &= (h[k:n - k] > h[k - m:n - k - m]) & (h[k:n - k] > h[k + m:n - k + m])
    return [int(i) for i in np.flatnonzero(ok)]


def selected_zone(prev: pd.DataFrame, k: int = 2):
    h = prev["high"].to_numpy()
    red = (prev["close"] < prev["open"]).to_numpy()
    for j in reversed(swing_high_idx(h, k)):
        if red[j:j + k + 1].any():
            top_body = max(prev.open.iloc[j], prev.close.iloc[j])
            return float(top_body), float(prev.high.iloc[j]), j
    return None


def main() -> int:  # noqa: C901
    data = load_five_minute()
    C, M = data["candles"], data["minutes"]
    days = sorted(C)
    daily = pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet")
    close_of = {str(r["date"])[:10]: float(r["close"]) for r in daily.to_dict("records")}
    ledger = [r for r in rd(P32 / "automated_trades_detailed.csv")]
    pdr = [r for r in ledger if r["strategy"] == "PDR"]
    conf_rows = {r["trade_id"]: r for r in rd(OUT / "pdr_confirmation_calculations.csv")}
    aff_rows = {r["trade_id"]: r for r in rd(OUT / "affected_27_trades.csv")}
    cls_rows = {r["trade_id"]: r for r in rd(OUT / "pdr_trade_classifications.csv")}

    # ---- 1. independent derivation of the affected set from the raw data (no use of the delivered CSV for the derivation)
    mine: dict[str, dict] = {}
    for t in pdr:
        d = pd.Timestamp(t["date"]).date()
        i0 = days.index(d)
        prev = C[days[i0 - 1]]
        lo_hi = selected_zone(prev)
        cs = C[d]
        row = cs[cs["start"] == pd.Timestamp(t["signal_candle_start"].join([t["date"] + " ", ""])).tz_localize("Asia/Kolkata")] if False else cs[cs["start"].dt.strftime("%H:%M") == t["signal_candle_start"]]
        conf = row.iloc[0]
        lo, hi, j = lo_hi
        mine[t["trade_id"]] = {"lo": lo, "hi": hi, "src": prev.iloc[j], "conf": conf, "prev_date": days[i0 - 1], "d": d, "below": float(conf.close) < lo, "idx": int(row.index[0])}
    aff = sorted(k for k, v in mine.items() if v["below"])
    record("the affected set derived independently from raw data equals the delivered file (count not hard-coded)", sorted(aff_rows) == aff and len(aff) == len(aff_rows), len(aff), f"independent count {len(aff)} of {len(pdr)} PDR trades; delivered {len(aff_rows)}")
    record("every PDR trade is LONG and every confirmation candle is bullish (close > open)", all(t["direction"] == "LONG" for t in pdr) and all(v["conf"].close > v["conf"].open for v in mine.values()), len(pdr))

    # ---- 2. zone, confirmation OHLC, distances, timestamps, entry price for all 54 trades
    bad = []
    for t in pdr:
        v, r = mine[t["trade_id"]], conf_rows[t["trade_id"]]
        conf = v["conf"]
        chk = [abs(float(r["zone_floor"]) - v["lo"]) < 1e-6, abs(float(r["zone_ceiling"]) - v["hi"]) < 1e-6, abs(float(r["confirmation_open"]) - conf.open) < 1e-6,
               abs(float(r["confirmation_high"]) - conf.high) < 1e-6, abs(float(r["confirmation_low"]) - conf.low) < 1e-6, abs(float(r["confirmation_close"]) - conf.close) < 1e-6,
               abs(float(r["confirmation_close_minus_floor"]) - (conf.close - v["lo"])) < 1e-4, r["confirmation_candle_start"] == f"{conf.start:%Y-%m-%d %H:%M}",
               r["confirmation_candle_end"] == f"{conf.start + pd.Timedelta(minutes=5):%Y-%m-%d %H:%M}", r["earliest_fill_timestamp"] == r["confirmation_candle_end"],
               abs(float(r["zone_source_high"]) - v["src"].high) < 1e-6 and abs(float(r["zone_source_open"]) - v["src"].open) < 1e-6 and abs(float(r["zone_source_close"]) - v["src"].close) < 1e-6,
               r["zone_source_candle_start"] == f"{v['src'].start:%Y-%m-%d %H:%M}"]
        mm = M[v["d"]]
        fill_ts = conf.start + pd.Timedelta(minutes=5)
        chk.append(abs(float(mm.loc[fill_ts, "open"]) - float(t["entry_price"])) < 1e-6 and abs(float(r["raw_minute_bar_open_at_fill"]) - float(t["entry_price"])) < 1e-6)
        if not all(chk):
            bad.append((t["trade_id"], [i for i, c in enumerate(chk) if not c]))
    record("zone boundaries, source candle, confirmation OHLC, close-minus-floor, timestamps, fill = raw minute open (all 54 PDR trades)", not bad, len(pdr), failures=bad)

    # ---- 3. gap, previous-day high, interaction candle and the full PDR sequence, by a different algorithm (vectorised intersection + first green after it)
    bad = []
    for t in pdr:
        v, r = mine[t["trade_id"]], conf_rows[t["trade_id"]]
        d, prev_d = v["d"], v["prev_date"]
        gap = float(M[d].open.iloc[0]) - close_of[str(prev_d)]
        pdh = float(C[prev_d].high.max())
        cs = C[d].reset_index(drop=True)
        hit = ((cs.low <= v["hi"]) & (cs.high >= v["lo"])).to_numpy()
        green = (cs.close > cs.open).to_numpy()
        # sequence with re-arming: positions of confirmations
        conf_pos, j = [], None
        for i in range(len(cs)):
            if j is None:
                if hit[i]:
                    j = i
                continue
            if green[i]:
                conf_pos.append((j, i))
                j = None
        pair = next(((jj, ii) for jj, ii in conf_pos if ii == v["idx"]), None)
        ok = (pair is not None and abs(float(r["gap_points"]) - gap) < 1e-6 and abs(float(r["previous_day_high"]) - pdh) < 1e-6 and r["interaction_candle_start"] == f"{cs.start.iloc[pair[0]]:%H:%M}"
              and abs(float(r["retest_low_5m"]) - float(cs.low.iloc[pair[0]:pair[1] + 1].min())) < 1e-6 and gap > 0 and float(M[d].open.iloc[0]) > v["hi"])
        pen = max(0.0, v["lo"] - float(cs.low.iloc[pair[0]:pair[1] + 1].min())) if pair else None
        ok = ok and pair is not None and abs(float(r["zone_penetration_depth_below_floor_5m"]) - pen) < 1e-6
        if not ok:
            bad.append(t["trade_id"])
    record("gap, previous-day high, interaction candle, retest low and penetration depth reproduced by an independent sequence scan (54 trades)", not bad, len(pdr), failures=bad)

    # ---- 4. all PDR signals of the engine reproduced (the sequence is the engine's trigger, rebuilt without any engine code)
    eng = {(r["date"], r["time"]) for r in rd(P32 / "all_strategy_signals.csv") if r["strategy"] == "PDR"}
    mine_sig = set()
    for d in days:
        if not ("2025-09-01" <= str(d) <= "2026-08-31"):
            continue
        i0 = days.index(d)
        if i0 == 0:
            continue
        prev_d = days[i0 - 1]
        z = selected_zone(C[prev_d])
        if z is None:
            continue
        op = float(M[d].open.iloc[0])
        if not (op - close_of[str(prev_d)] > 0 and op > z[1]):
            continue
        cs = C[d].reset_index(drop=True)
        j = None
        for i in range(len(cs)):
            hit = cs.low.iloc[i] <= z[1] and cs.high.iloc[i] >= z[0]
            if j is None:
                if hit:
                    j = i
                continue
            if cs.close.iloc[i] > cs.open.iloc[i]:
                mine_sig.add((str(d), f"{cs.start.iloc[i] + pd.Timedelta(minutes=5):%H:%M}"))
                j = None
    extra, missing = sorted(mine_sig - eng), sorted(eng - mine_sig)
    record("every PDR confirmed signal of the engine (383) is reproduced from raw data; the only difference is the day the engine blocks as NOT_EVALUATED", not missing and extra == [("2025-10-23", "15:20")], len(eng),
           f"mine {len(mine_sig)}, engine {len(eng)}, only-mine {extra}, only-engine {missing}")

    # ---- 5. classification rule re-applied from the delivered columns; counterfactual counts recomputed
    bad = []
    for tid, c in cls_rows.items():
        r = conf_rows[tid]
        if r["close_below_floor"] != "True":
            if c["classification"] != "NOT_AFFECTED":
                bad.append((tid, "unaffected labelled"))
            continue
        expl_ok = r["explicit_conditions_all_hold"] == "True"
        agree = r["engine_cross_check_all_agree"] == "True"
        flip = (r["alt_A_previous_day_high_fires_on_same_candle"] == "True" and r["alt_A_previous_day_high_confirmation_close_minus_floor"] not in ("",) and float(r["alt_A_previous_day_high_confirmation_close_minus_floor"] or -1) >= 0
                and r["zone_is_previous_day_high_candle"] != "True") or (r["alt_C_repeated_shelf_fires_on_same_candle"] == "True" and r["alt_C_repeated_shelf_confirmation_close_minus_floor"] != ""
                                                                         and float(r["alt_C_repeated_shelf_confirmation_close_minus_floor"] or -1) >= 0)
        want = "DATA_OR_IMPLEMENTATION_ISSUE" if not agree else ("SOURCE_CONTRADICTED" if not expl_ok else ("ZONE_SELECTION_DISPUTED" if flip else "SOURCE_AMBIGUOUS"))
        if c["classification"] != want:
            bad.append((tid, c["classification"], want))
    record("each of the 27 classifications follows the documented decision rule when re-applied to the delivered columns", not bad, len(cls_rows), failures=bad)
    cf = {r["reading"]: r for r in rd(OUT / "zone_rule_counterfactual_counts.csv")}
    allr = list(conf_rows.values())
    n_b = sum(float(r["confirmation_close"]) >= float(r["zone_floor"]) for r in allr)
    n_c = sum(float(r["confirmation_close"]) > float(r["zone_ceiling"]) for r in allr)
    n_d = sum(float(r["confirmation_close"]) >= float(r["zone_floor"]) and float(r["retest_low_5m"]) >= float(r["zone_floor"]) for r in allr)
    ok = (int(cf["A"]["trades_satisfying"]) == len(allr) and int(cf["B"]["trades_satisfying"]) == n_b and int(cf["C"]["trades_satisfying"]) == n_c and int(cf["D"]["trades_satisfying"]) == n_d)
    record("counterfactual counts A-D recomputed from raw-derived columns", ok, len(allr), f"A {len(allr)}, B {n_b}, C {n_c}, D {n_d}; none of the 27 affected trades satisfies B, C or D by construction")

    # ---- 6. manual journal: independent match of the 27 against the raw workbook (15-minute tolerance on the candle START, same date, PDR rows only)
    ws = openpyxl.load_workbook(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", data_only=True)["Trading Journal"]
    jr = []
    for i, r in enumerate(ws.iter_rows(values_only=True), 1):
        if i > 2 and isinstance(r[0], (int, float)):
            dd = r[1].date() if hasattr(r[1], "date") else r[1]
            tt = r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2])[:5]
            jr.append({"row": i, "date": str(dd), "time": tt, "strategy": str(r[3]).strip().upper()})
    mj = {r["trade_id"]: r for r in rd(OUT / "manual_journal_comparison.csv")}
    bad, n_match, n_alt = [], 0, 0
    by_row = {x["row"]: x for x in jr}
    for t in pdr:
        cand = [x for x in jr if x["date"] == t["date"] and x["strategy"] == "PDR"]
        st = int(t["signal_candle_start"][:2]) * 60 + int(t["signal_candle_start"][3:])
        best = min(((abs(int(x["time"][:2]) * 60 + int(x["time"][3:]) - st), x) for x in cand), default=None, key=lambda z: z[0])
        within = best is not None and best[0] <= 15
        klass = mj[t["trade_id"]]["journal_match_class"]
        delivered_match = klass in ("EXACT_MATCH", "TIME_SHIFTED_MATCH")
        if delivered_match and mj[t["trade_id"]]["matched_via_alternate_label"] == "True":  # the Phase 2.1 attribution hypothesis labels the row differently: verify the row itself
            x = by_row[int(mj[t["trade_id"]]["matched_journal_row"])]
            dt = abs(int(x["time"][:2]) * 60 + int(x["time"][3:]) - st)
            if x["date"] != t["date"] or dt > 15 or (klass == "EXACT_MATCH") != (dt == 0):
                bad.append((t["trade_id"], "alternate-label row does not satisfy the tolerance", dt))
            n_alt += 1
            n_match += 1
            continue
        if within != delivered_match:
            bad.append((t["trade_id"], klass, best[0] if best else None))
        if klass == "EXACT_MATCH" and best is not None and best[0] != 0:
            bad.append((t["trade_id"], "exact but differs", best[0]))
        n_match += 1 if within else 0
    n_aff_match = sum(1 for tid in aff if mj[tid]["journal_match_class"] in ("EXACT_MATCH", "TIME_SHIFTED_MATCH"))
    record("journal comparison: a PDR journal row within 15 minutes exists exactly when the delivered class says matched", not bad, len(pdr), f"matched PDR trades {n_match} ({n_alt} through the Phase 2.1 alternate-label attribution; among the 27: {n_aff_match})", bad)

    # ---- 7. charts: one per affected trade, numbers in the title equal the CSV; candles drawn equal the raw count
    bad = []
    for tid in aff:
        p = OUT / "charts" / f"{tid}.svg"
        if not p.exists():
            bad.append((tid, "missing"))
            continue
        txt = p.read_text()
        m = re.search(r"confirmation close ([\d,\.]+) is ([\d,\.]+) points BELOW the zone floor ([\d,\.]+)", txt)
        v = mine[tid]
        if not m or abs(fl(m.group(1)) - float(v["conf"].close)) > 0.006 or abs(fl(m.group(3)) - v["lo"]) > 0.006 or abs(fl(m.group(2)) - (v["lo"] - float(v["conf"].close))) > 0.006:
            bad.append((tid, "title numbers"))
        if "POST_ENTRY" not in txt or "zone source" not in txt.lower() and "ZONE SOURCE" not in txt:
            bad.append((tid, "labels"))
    n_svg = len(list((OUT / "charts").glob("*.svg")))
    record("27 charts exist (one per affected trade), titles carry the independently derived close/floor/distance, POST_ENTRY and zone-source labels present", not bad and n_svg == len(aff), n_svg, failures=bad)

    # ---- 8. the earlier phases are byte-identical to the snapshot taken before this phase started
    before = json.loads((OUT / "earlier_phase_hashes_before.json").read_text())
    bad = []
    for k, h in before.items():
        if isinstance(h, dict):
            for kk, hh in h.items():
                if hashlib.sha256((ROOT / kk).read_bytes()).hexdigest() != hh:
                    bad.append(kk)
        elif hashlib.sha256((ROOT / k).read_bytes()).hexdigest() != h:
            bad.append(k)
    record("Phase 3.0 / 3.1 / 3.2 reports and ledgers, raw data, source PDFs and the journal are unchanged (hash snapshot taken before Phase 3.3)", not bad, len(before), failures=bad)
    cnt = Counter(c["classification"] for c in cls_rows.values())
    RES["classification_counts"] = dict(cnt)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print(dict(cnt), "ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
