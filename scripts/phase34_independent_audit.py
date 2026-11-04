"""Phase 3.4 independent audit. Imports NOTHING from ``nifty_trading`` or from the Phase 3.4 run scripts: it re-implements the revised PDR rules (previous-day-high zones A and B, the three
patterns with the close-strictly-above-ceiling rule, the test/confirmation sequence) from the written rule text, working on the raw parquet files with pandas, and compares the resulting
signal streams, zones and entry conditions with the delivered CSV files. Also re-checks the manual comparison, the file hashes and the unchanged status of everything else.
Writes reports/phase3/phase34_pdr_revision/independent_audit_results.json; exit code 1 on a hard failure."""

from __future__ import annotations

import csv
import glob
import hashlib
import json
import sys
from pathlib import Path

import openpyxl
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports" / "phase3" / "phase34_pdr_revision"
P32 = ROOT / "reports" / "phase3" / "phase32"
RES: dict = {"checks": {}}
TH = {"RESEARCH_DEFAULT": dict(gb=0.60, gu=0.20, rw=2.0, rc=0.30, hw=2.0, hu=0.10, hp=0.60), "EXAMPLE_LENIENT": dict(gb=0.40, gu=0.25, rw=1.5, rc=0.40, hw=1.5, hu=0.15, hp=0.55)}
EPS = 1e-9


def record(name, ok, n, detail="", failures=None):
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "n_failures": len(failures or []), "failures": (failures or [])[:12]}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""))


def rd(p):
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def load():
    fr = [pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / "data/processed/nifty50_warmup/**/*.parquet"), recursive=True))]
    fr += [pd.read_parquet(f) for f in sorted(glob.glob(str(ROOT / "data/processed/nifty50/**/*.parquet"), recursive=True))]
    df = pd.concat(fr).drop_duplicates("timestamp").sort_values("timestamp").set_index("timestamp")
    C, M = {}, {}
    for day, g in df.groupby(df.index.date):
        mod = g.index.hour * 60 + g.index.minute
        if not (mod.min() == 555 and len(g) >= 300):
            continue
        g = g[(mod >= 555) & (mod <= 929)]
        r = g.resample("5min", origin=g.index[0].normalize() + pd.Timedelta(hours=9, minutes=15)).agg({"open": "first", "high": "max", "low": "min", "close": "last", "volume": "count"})
        r = r[r["volume"] == 5].drop(columns="volume").reset_index().rename(columns={"timestamp": "start"})
        C[day], M[day] = r.reset_index(drop=True), g
    return C, M


def zone_a(p):
    j = int(p.high.to_numpy().argmax())  # first occurrence of the maximum
    return float(max(p.open[j], p.close[j])), float(p.high[j]), [j]


def zone_b(p, tol=5.0, minT=2, sep=2):
    h = p.high.to_numpy()
    n = len(h)
    dh = int(h.argmax())
    piv = [j for j in range(n) if all(h[j] >= h[m] for m in (j - 1, j + 1) if 0 <= m < n)]
    mem = sorted({j for j in piv if h[j] >= h[dh] - tol - 1e-9} | {dh})
    groups, last = 0, None
    for j in mem:
        if last is None or j - last >= sep:
            groups += 1
        last = j
    if groups >= minT:
        return float(min(max(p.open[j], p.close[j]) for j in mem)), float(h[dh]), mem
    return float(max(p.open[dh], p.close[dh])), float(h[dh]), [dh]


def patterns(o, h, lo, c, ceil, th):
    rg = h - lo
    if rg <= 0:
        return []
    body, uw, lw = abs(c - o), h - max(o, c), min(o, c) - lo
    out = []
    if c > o and body / rg >= th["gb"] - EPS and uw / rg <= th["gu"] + EPS:
        out.append("GOOD_GREEN_BODY")
    if lw > EPS and lw >= th["rw"] * body - EPS and (h - c) / rg <= th["rc"] + EPS and lo <= ceil:
        out.append("LOWER_PRICE_REJECTION")
    if lw > EPS and lw >= th["hw"] * body - EPS and uw / rg <= th["hu"] + EPS and (min(o, c) - lo) / rg >= th["hp"] - EPS:
        out.append("HAMMER")
    return out


def signals(C, M, close_of, days, zfn, th, any_open=False):
    out = {}
    for i0, d in enumerate(days):
        if i0 == 0 or str(d) < "2025-09-01" or str(d) > "2026-08-31":
            continue
        pd_ = days[i0 - 1]
        op = float(M[d].open.iloc[0])
        gap = op - close_of[str(pd_)]
        if gap <= 0:
            continue
        lo, hi, _ = zfn(C[pd_])
        if not any_open and not op > hi:
            continue
        cs = C[d]
        j = None
        for i in range(len(cs)):
            r = cs.iloc[i]
            if j is None:
                if r.low <= hi and r.high >= lo:
                    j = i
                continue
            pats = patterns(r.open, r.high, r.low, r.close, hi, th)
            if pats and r.close > hi:
                out[(str(d), f"{r.start + pd.Timedelta(minutes=5):%H:%M}")] = {"patterns": pats, "ceiling": hi, "floor": lo, "close": float(r.close), "interaction": f"{cs.start.iloc[j]:%H:%M}"}
                j = None
    return out


def main():
    C, M = load()
    days = sorted(C)
    daily = pd.read_parquet(ROOT / "data/processed/nifty50_daily/candles.parquet")
    close_of = {str(r["date"])[:10]: float(r["close"]) for r in daily.to_dict("records")}
    sig = rd(OUT / "old_vs_new_pdr_signals.csv")
    det = rd(OUT / "pdr_entry_condition_details.csv")
    for cand, zfn in (("A", zone_a), ("B", zone_b)):
        mine = signals(C, M, close_of, days, zfn, TH["RESEARCH_DEFAULT"])
        eng = {(r["date"], r["confirmation_candle_end"]) for r in sig if r["candidate"] == cand and ((r["row_type"] == "OLD_SIGNAL" and r["signal_valid_under_revision"] == "True") or r["row_type"] == "NEW_SIGNAL")}
        eng2 = {(r["date"], f"{int(r['evaluated_candle_start'][:2]) * 60 + int(r['evaluated_candle_start'][3:]) + 5:d}") for r in det if r["candidate"] == cand and r["decision"] == "SIGNAL_CONFIRMED"}
        eng2 = {(d, f"{int(m) // 60:02d}:{int(m) % 60:02d}") for d, m in eng2}
        mset = set(mine)
        record(f"candidate {cand}: the signal stream rebuilt independently from raw data equals the engine's (default patterns)", mset == eng == eng2, len(mset), f"independent {len(mset)}, engine {len(eng)}, details {len(eng2)}; only-mine {sorted(mset - eng)[:3]}, only-engine {sorted(eng - mset)[:3]}")
        bad = []
        for r in det:
            if r["candidate"] != cand or r["decision"] != "SIGNAL_CONFIRMED":
                continue
            k = (r["date"], f"{(int(r['evaluated_candle_start'][:2]) * 60 + int(r['evaluated_candle_start'][3:]) + 5) // 60:02d}:{(int(r['evaluated_candle_start'][:2]) * 60 + int(r['evaluated_candle_start'][3:]) + 5) % 60:02d}")
            m = mine.get(k)
            if m is None or abs(float(r["zone_ceiling"]) - m["ceiling"]) > 1e-6 or abs(float(r["zone_floor"]) - m["floor"]) > 1e-6 or abs(float(r["close"]) - m["close"]) > 1e-6 or set(r["patterns_passed"].split("+")) != set(m["patterns"]) \
                    or not float(r["close"]) > float(r["zone_ceiling"]) or r["interaction_candle_start"] != m["interaction"]:
                bad.append(k)
        record(f"candidate {cand}: zone floor/ceiling, close, patterns passed, interaction candle and close > ceiling equal the independent values", not bad, len(mine), failures=bad)
        lenient = signals(C, M, close_of, days, zfn, TH["EXAMPLE_LENIENT"])
        rows_len = [r for r in rd(OUT / "pdr_daily_signal_comparison.csv") if r["candidate"] == cand]
        record(f"candidate {cand}: the EXAMPLE_LENIENT sensitivity counts equal the independent counts", sum(int(r["lenient_profile_signal_count_sensitivity"]) for r in rows_len) == len(lenient), len(lenient), f"independent {len(lenient)}")
        # zones per day
        bad = []
        for r in rows_len:
            d = pd.Timestamp(r["date"]).date()
            i0 = days.index(d)
            lo, hi, _ = zfn(C[days[i0 - 1]])
            if abs(float(r["zone_floor"]) - lo) > 1e-6 or abs(float(r["zone_ceiling"]) - hi) > 1e-6 or abs(float(r["previous_day_high"]) - float(C[days[i0 - 1]].high.max())) > 1e-6 or abs(hi - float(C[days[i0 - 1]].high.max())) > 1e-9:
                bad.append(r["date"])
        record(f"candidate {cand}: the zone of every one of the 247 sessions equals the independent construction and its ceiling is the previous-day high (PDR-A01)", not bad, len(rows_len), failures=bad)
    # old signals: the 54 trades and 383 signals are all present for both candidates
    old = [r for r in sig if r["row_type"] == "OLD_SIGNAL"]
    record("all 383 old signals and all 54 old trades are compared for both candidates", len(old) == 766 and len({r["old_trade_id"] for r in old if r["old_trade_id"]}) == 54, len(old))
    # tags are consistent with the independent evaluation of each removed old signal
    bad = []
    for r in old:
        if r["signal_valid_under_revision"] == "True":
            continue
        d = pd.Timestamp(r["date"]).date()
        i0 = days.index(d)
        zfn = zone_a if r["candidate"] == "A" else zone_b
        lo, hi, _ = zfn(C[days[i0 - 1]])
        cs = C[d]
        x = int(cs.index[cs.start.dt.strftime("%H:%M") == r["confirmation_candle_start"]][0])
        c = cs.iloc[x]
        op = float(M[d].open.iloc[0])
        want = set()
        if not (op > hi and any(cs.low.iloc[m] <= hi and cs.high.iloc[m] >= lo for m in range(x))):
            want.add("REMOVED_BY_ZONE_SELECTION")
        if not patterns(c.open, c.high, c.low, c.close, hi, TH["RESEARCH_DEFAULT"]):
            want.add("REMOVED_BY_PATTERN_RULE")
        if not c.close > hi:
            want.add("REMOVED_BY_CLOSE_RULE")
        got = set(r["change_tags"].split(";"))
        if want and not want <= got or (not want and "SEQUENCE_STATE_DIFFERENCE" not in got):
            bad.append((r["date"], r["confirmation_candle_start"], r["candidate"], sorted(want), sorted(got)))
    record("the removal tags of every old signal that is not valid under the revision equal an independent evaluation (zone / pattern / close)", not bad, len(old), failures=bad)
    # journal
    ws = openpyxl.load_workbook(ROOT / "docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", data_only=True)["Trading Journal"]
    jr = []
    for i, r in enumerate(ws.iter_rows(values_only=True), 1):
        if i > 2 and isinstance(r[0], (int, float)):
            dd = r[1].date() if hasattr(r[1], "date") else r[1]
            jr.append({"row": i, "date": str(dd), "time": (r[2].strftime("%H:%M") if hasattr(r[2], "strftime") else str(r[2])[:5]), "strategy": str(r[3]).strip().upper()})
    mj = rd(OUT / "pdr_manual_journal_comparison.csv")
    bad = []
    sigsA = signals(C, M, close_of, days, zone_a, TH["RESEARCH_DEFAULT"])
    for m in mj:
        row = next(x for x in jr if x["row"] == int(m["journal_row"]))
        label = int(row["time"][:2]) * 60 + int(row["time"][3:])
        cand = [(abs(int(t[:2]) * 60 + int(t[3:]) - 5 - label), t) for (d, t) in sigsA if d == row["date"]]
        near = min(cand, default=None)
        has = near is not None and near[0] <= 15
        if has != m["revised_A_signal"][:1].isdigit():
            bad.append((m["journal_row"], m["revised_A_signal"], near))
    record("journal comparison: the nearest candidate-A signal within 15 minutes of every PDR / disputed journal row equals the delivered result", not bad, len(mj), failures=bad)
    # journal 2x2: thresholds x open rule, recomputed independently (exact = same candle start, shifted = within 15 minutes, nearest candle, ties to the earlier one)
    pdr_jr = [x for x in jr if x["row"] in {int(m["journal_row"]) for m in mj if m["attribution"] == "PDR"}]
    j2 = rd(OUT / "pdr_journal_agreement_2x2.csv")
    bad = []
    for cand_, zfn_ in (("A", zone_a), ("B", zone_b)):
        for prof, pname in (("RESEARCH_DEFAULT", "default"), ("EXAMPLE_LENIENT", "lenient")):
            for anyo, oname in ((False, "open must"), (True, "open anywhere")):
                ss = signals(C, M, close_of, days, zfn_, TH[prof], any_open=anyo)
                ex = sh = 0
                for row in pdr_jr:
                    label = int(row["time"][:2]) * 60 + int(row["time"][3:])
                    dts = [int(t[:2]) * 60 + int(t[3:]) - 5 - label for (d, t) in ss if d == row["date"]]
                    dts = [x for x in dts if abs(x) <= 15]
                    best = min(dts, key=lambda x: (abs(x), x), default=None)
                    ex += best == 0
                    sh += best is not None and best != 0
                got = next(r for r in j2 if r["candidate"] == cand_ and r["pattern_thresholds"].startswith(pname) and r["open_rule"].startswith(oname))
                if (int(got["exact"]), int(got["shifted_within_15_min"])) != (ex, sh):
                    bad.append((cand_, pname, oname, (ex, sh), (got["exact"], got["shifted_within_15_min"])))
    record("journal 2x2 table (thresholds x open rule, both candidates, 8 PDR rows) equals the independent recomputation incl. the open-anywhere runs", not bad and len(j2) == 8 and len(pdr_jr) == 8, len(j2), failures=bad)
    # unchanged files
    snap = json.loads((OUT / "before_snapshot.json").read_text())["files"]
    changed = []
    for p, h in snap.items():
        if p.startswith(("src/", "tests/", "scripts/", "data/", "reports/phase3/", "docs/strategy_docs/", "docs/trading journal/")):
            f = ROOT / p
            if not f.exists() or hashlib.sha256(f.read_bytes()).hexdigest() != h:
                changed.append(p)
    record("every source / test / script / data / Phase 3.0-3.3 report / PDF / journal file of the before-snapshot is byte-identical (other engines, controller, stops, targets, ledgers, raw data)", not changed, len(snap), failures=changed)
    new_src = sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src").rglob("*.py") if str(p.relative_to(ROOT)) not in snap and "__pycache__" not in str(p))
    record("the only new source file is the revised engine module", new_src == ["src/nifty_trading/strategies/pdr_revised.py"], len(new_src), str(new_src))
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
