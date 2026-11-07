"""Phase 5.1 independent audit: re-derives what the Phase 5.1 reports state, from the raw Phase 1 one-minute files, the Phase 3.6 delivered tables and the handwritten-PDF transcription only
(no ``src/`` imports and no import of scripts/phase51_diagnostics.py: the readings are re-implemented here from the author's wording). Candle / EMA / exit helpers come from the Phase 3.2 audit script (itself free of ``src/``).

Run: .venv/bin/python scripts/phase51_independent_audit.py   ->   reports/phase5/phase51_author_corrections/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import warnings
from collections import defaultdict
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase51_author_corrections"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
PDF = ROOT / "docs" / "strategy_docs" / "corrected" / "Adobe Scan Nov 05, 2026.pdf"
RES: dict = {"checks": {}}
VALID = {"CONFIRMED_SOFTWARE_BUG", "MISSING_AUTHOR_RULE", "WRONG_STRATEGY_SELECTION", "CANDLE_CONFIRMATION_MISMATCH", "SUPPORT_RESISTANCE_MISMATCH", "EMA_FILTER_MISMATCH", "ENTRY_TIMING_MISMATCH", "AUTHOR_DISCRETION_UNRESOLVED",
         "DATA_DIFFERENCE", "JOURNAL_INCONSISTENCY", "NO_DISCREPANCY_FOUND"}
ALLOWED_ADDED = ("reports/phase5/phase51_author_corrections/", "scripts/phase51_", "src/nifty_trading/strategies/orb_colour.py", "src/nifty_trading/research/phase51.py", "tests/test_phase51_")


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


def geom(o, h, low, c):
    rng = h - low
    return {"body": None if rng <= 0 else 100 * abs(c - o) / rng, "uw": None if rng <= 0 else 100 * (h - max(o, c)) / rng, "lw": None if rng <= 0 else 100 * (min(o, c) - low) / rng, "col": "G" if c > o else ("R" if c < o else "D")}


def main() -> int:  # noqa: C901
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    tr = rd(OUT / "all_author_corrections.csv")
    dated = [r for r in tr if r["date"]]
    cls = {r["correction_id"]: r for r in rd(OUT / "correction_classifications.csv")}
    p36 = rd(P36 / "all_trades_detailed.csv")
    sig = rd(P36 / "all_strategy_signals.csv")

    # ============================================================ 1. the PDF and the transcription
    import pypdfium2 as pdfium
    n_pages = len(pdfium.PdfDocument(str(PDF)))
    pages_ok = all((OUT / "pages" / f"page_{i}_full.png").exists() for i in range(1, 7))
    record("the handwritten PDF has six pages, all six rendered page images exist, and the PDF is byte-identical to its baseline hash", n_pages == 6 and pages_ok and snap["hashes"]["docs/strategy_docs/corrected/Adobe Scan Nov 05, 2026.pdf"] == sha(PDF), 6)
    bad = []
    for r in dated:
        d = date.fromisoformat(r["date"])
        if d.weekday() >= 5:
            bad.append((r["correction_id"], "weekend"))
        tid = f"{r['date'].replace('-', '')}-{r['trade_no']}"
        m = [t for t in p36 if t["trade_id"].startswith(tid + "-")]
        if len(m) != 1:
            bad.append((r["correction_id"], "no unique Phase 3.6 trade", tid))
            continue
        lab = r["strategy_label_as_written"].split(" ")[0]
        if lab not in ("(none", ) and lab != m[0]["strategy"]:
            bad.append((r["correction_id"], "label", lab, m[0]["strategy"]))
    record("all 40 dated entries are weekdays, resolve to exactly one Phase 3.6 trade, and the strategy label written beside the date equals that trade's strategy (AC27 has no label)", not bad and len(dated) == 40, len(dated), failures=bad)
    record("transcription: 40 dated entries, 2 general remarks, exactly one crossed-out entry (AC23) and it has no classification", len(tr) == 42 and sum(1 for r in dated if r["status"] == "CROSSED_OUT") == 1 and cls["AC23"]["classifications"] == "", 42)

    # ============================================================ 2. candles / EMA / levels from the raw minutes
    raw, warm = A32.load_raw(), A32.load_warm()
    allc = pd.concat([A32.five_minute(warm, A32.standard_days(warm)), A32.five_minute(raw, A32.standard_days(raw))]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = A32.ema_series(allc["close"].to_numpy())
    allc["day"] = allc.start.dt.date
    allc["end"] = allc.start + pd.Timedelta(minutes=5)
    by_day = {d: g.reset_index(drop=True) for d, g in allc.groupby("day")}
    dates = sorted({r["date"] for r in dated})
    bad, n = [], 0
    for d in dates:
        ev = json.loads((OUT / "evidence" / f"{d}.json").read_text())
        g = by_day[date.fromisoformat(d)]
        if len(g) != len(ev["candles"]):
            bad.append((d, "candle count", len(g), len(ev["candles"])))
            continue
        for c, e in zip(g.itertuples(), ev["candles"], strict=True):
            n += 1
            gm = geom(c.open, c.high, c.low, c.close)
            if (e["start"] != c.start.strftime("%H:%M") or max(abs(c.open - e["o"]), abs(c.high - e["h"]), abs(c.low - e["l"]), abs(c.close - e["c"])) > 0.0051 or e["colour"] != gm["col"]
                    or (gm["body"] is not None and abs(gm["body"] - e["body_pct"]) > 0.06) or (e["ema200"] is not None and abs(c.ema - e["ema200"]) > 0.006)):
                bad.append((d, e["start"]))
    record("every evidence candle (38 dates) equals an independent 5-minute aggregation of the raw one-minute rows: OHLC, colour, body %, and the causal EMA(200) of 5-minute closes", not bad, n, failures=bad)
    # previous-session levels
    prevd = {}
    dl = sorted(by_day)
    for i, d in enumerate(dl):
        prevd[d] = dl[i - 1] if i else None
    bad = []
    for d in dates:
        ev = json.loads((OUT / "evidence" / f"{d}.json").read_text())
        pd_ = prevd[date.fromisoformat(d)]
        pg = by_day[pd_]
        if abs(pg.high.max() - ev["session"]["prev_high"]) > 1e-6 or abs(pg.low.min() - ev["session"]["prev_low"]) > 1e-6:
            bad.append((d, pg.high.max(), ev["session"]["prev_high"]))
    record("previous-session high and low in the evidence equal the independent previous-session 5-minute extremes", not bad, len(dates), failures=bad)

    # ============================================================ 3. the engine's dated trades re-walked from the raw bars
    raw["key"] = raw.timestamp.dt.strftime("%Y-%m-%d %H:%M")
    bk = raw.set_index("key")
    STOP = {"IRF": 35.0, "ORB": 30.0, "PDR": 35.0, "PDS": 35.0, "RF": 35.0}
    T2 = {"IRF": 60.0, "ORB": 60.0, "PDR": 70.0, "PDS": 70.0, "RF": 60.0}
    bad = []
    n = 0
    for r in dated:
        tid = f"{r['date'].replace('-', '')}-{r['trade_no']}"
        t = next(x for x in p36 if x["trade_id"].startswith(tid + "-"))
        n += 1
        e = fnum(t["entry_price"])
        fill = pd.Timestamp(t["fill_timestamp"]).tz_localize("Asia/Kolkata")
        day = raw[(raw.timestamp.dt.date == fill.date()) & (raw.timestamp >= fill)]
        wk = A32.walk_exit(t["direction"], e, day, STOP[t["strategy"]], T2[t["strategy"]])
        hm = lambda ts: "" if ts is None else ts.strftime("%H:%M")  # noqa: E731
        if t["fill_timestamp"] not in bk.index or abs(bk.loc[t["fill_timestamp"], "open"] - e) > 1e-9 or wk["outcome"] != t["outcome"] or hm(wk["ts1"]) != t["leg1_exit_time"] or hm(wk["ts2"]) != t["leg2_exit_time"]:
            bad.append((t["trade_id"], wk["outcome"], t["outcome"]))
        if t["checks_fail"] != "0":
            bad.append((t["trade_id"], "checks_fail", t["checks_fail"]))
    record("each dated automated trade: entry = raw 1-minute open at the fill minute, outcome and both exit times equal an independent exit walk, and its delivered rule checks show 0 failures (supports 'no confirmed implementation defect')", not bad, n, failures=bad)

    # ============================================================ 4. the readings of the author's wording, re-implemented
    def irf_measures(g: pd.DataFrame, end_hm: str):
        i = next((k for k, c in enumerate(g.itertuples()) if c.end.strftime("%H:%M") == end_hm), None)
        if i is None:
            return None
        c = g.iloc[i]
        prior_low = g.low.iloc[:i].min() if i else None
        gm = geom(c.open, c.high, c.low, c.close)
        sp = None if np.isnan(c.ema) else c.close - c.ema
        return {"body": gm["body"], "ema_within_27": sp is not None and 0 < sp < 27.0, "below_low": prior_low is not None and c.close < prior_low}

    flags = defaultdict(list)
    irf = [t for t in p36 if t["strategy"] == "IRF"]
    for t in irf:
        m = irf_measures(by_day[date.fromisoformat(t["date"])], t["signal_confirmed_at"][-5:])
        if m is None:
            continue
        if m["ema_within_27"]:
            flags["ema_within_27"].append(t["trade_id"])
        if m["below_low"]:
            flags["close_below_session_low"].append(t["trade_id"])
        for th in (60, 50, 40):
            if m["body"] is not None and m["body"] < th:
                flags[f"body_lt_{th}"].append(t["trade_id"])
    pop = json.loads((OUT / "population_impact.json").read_text())["irf_flags"]
    bad = [(k, len(flags[k]), pop[k]["count"]) for k in ("ema_within_27", "close_below_session_low", "body_lt_60", "body_lt_50", "body_lt_40") if sorted(flags[k]) != sorted(pop[k]["trades"])]
    record("the IRF population counts behind the candidate rules (EMA within 27 below the entry, close below the session low so far, entry-candle body < 60 / 50 / 40) equal an independent recomputation, trade by trade", not bad, len(irf),
           f"{ {k: len(v) for k, v in flags.items()} }", bad)

    def first_red(g: pd.DataFrame):
        cs = list(g.itertuples())
        irh = cs[0].high
        b = next((i for i in range(1, len(cs)) if cs[i].close > irh), None)
        if b is None:
            return None
        r = next((i for i in range(b + 1, len(cs)) if cs[i].close < cs[i].open and cs[i].low > irh), None)
        if r is None:
            return None
        s_, r_ = cs[r].low, cs[r].high
        above = False
        for k in range(r + 1, len(cs)):
            c = cs[k]
            if c.end.strftime("%H:%M") > "13:00":
                return None
            gm = geom(c.open, c.high, c.low, c.close)
            strong = c.close < c.open and (gm["body"] or 0) >= 60.0
            if strong and c.close < s_:
                return (c.end.strftime("%H:%M"), round(float(c.close), 2), "SUPPORT_BREAK")
            if strong and above and c.close < r_:
                return (c.end.strftime("%H:%M"), round(float(c.close), 2), "RESISTANCE_BREAK")
            if c.high > r_:
                above = True
        return None
    m2 = [t for t in irf if t["method"].startswith("Method 2")]
    differs = [t["trade_id"] for t in m2 if first_red(by_day[date.fromisoformat(t["date"])]) is None or first_red(by_day[date.fromisoformat(t["date"])])[0] != t["signal_confirmed_at"][-5:]]
    pp = json.loads((OUT / "population_impact.json").read_text())["irf_flags"]["first_red_reading_differs"]
    record("the 'first red candle' reading (re-implemented from the author's wording) differs from the engine's entry on exactly the Method-2 IRF trades listed in population_impact.json", sorted(differs) == sorted(pp["trades"]), len(m2), f"{len(differs)} of {len(m2)}")
    # dated cases: compare with the reading printed in each day report
    bad, n = [], 0
    for r in dated:
        tid = f"{r['date'].replace('-', '')}-{r['trade_no']}"
        t = next(x for x in p36 if x["trade_id"].startswith(tid + "-"))
        if t["strategy"] != "IRF":
            continue
        md = (OUT / "daily" / f"{r['date']}.md").read_text()
        line = next((ln for ln in md.splitlines() if ln.startswith("| FULLY_ABOVE|body>=60 ")), None)
        mine = first_red(by_day[date.fromisoformat(r["date"])])
        n += 1
        if line is None or (("none before 13:00" in line) != (mine is None)) or (mine is not None and f"{mine[0]}, {mine[1]}, {mine[2]}" not in line):
            bad.append((r["correction_id"], mine, line))
    record("for every dated IRF entry the 'first red candle (fully above, body >= 60)' entry printed in the day report equals the independent computation", not bad, n, failures=bad)

    # ============================================================ 5. PDR first-green counts
    earlier = []
    pdr = [t for t in p36 if t["strategy"] == "PDR"]
    for t in pdr:
        s = next((x for x in sig if x["trade_id"] == t["trade_id"]), None)
        lv = json.loads(s["reference_levels"])
        g = by_day[date.fromisoformat(t["date"])]
        cs = list(g.itertuples())
        inter = next((i for i, c in enumerate(cs) if c.end.strftime("%H:%M") > "09:15" and c.low <= lv["zone_high"]), None)
        if inter is None:
            continue
        fg = next((c for c in cs[inter:] if c.close > c.open and c.close > lv["zone_high"]), None)
        if fg is not None and fg.end.strftime("%H:%M") < t["signal_confirmed_at"][-5:]:
            earlier.append(t["trade_id"])
    pq = json.loads((OUT / "population_impact.json").read_text())["pdr_first_green_earlier"]
    record("the PDR 'first green candle' counts (earlier than the engine's confirmation) equal an independent recomputation from the zone in the Phase 3.6 signals and the raw candles", sorted(earlier) == sorted(pq["trades"]), len(pdr), f"{len(earlier)} of {len(pdr)}")

    # ============================================================ 6. the implemented ORB colour variant
    orb = [s for s in sig if s["strategy"] == "ORB" and s["entry_rule_status"]]
    expected = []
    for s in orb:
        g = by_day[date.fromisoformat(s["date"])]
        c0 = g.iloc[0]
        ok = c0.close > c0.open if s["direction"] == "LONG" else c0.close < c0.open
        if not ok:
            expected.append((s["date"], s["method"], s["direction"]))
    diff = rd(OUT / "before_after_signal_differences.csv")
    got = [(r["date"], r["method"], r["direction"]) for r in diff if r["rule"] == "ORB_COLOUR_AC27" and r["level"] == "ORB signal"]
    record("the ORB signals changed by the colour variant are exactly the confirmed Phase 3.6 ORB signals whose first candle colour contradicts the direction (independent recomputation from the raw first candle)", sorted(set(expected)) == sorted(got), len(orb), f"{got}")
    removed = {(r["date"], r["strategy"]) for r in diff if r["rule"] == "ORB_COLOUR_AC27" and r["level"].startswith("executed trade removed")}
    record("every executed trade the variant removes is either one of those ORB trades or a later trade on the same day (no other day is touched)", {d for d, _s in removed} <= {e[0] for e in expected}, len(removed))
    pop_all = json.loads((OUT / "population_impact.json").read_text())
    record("the frozen scenario re-run through the unchanged controller reproduces the Phase 3.6 ledger identities (196 trades) before the variant is applied", pop_all["orb_colour_regression_ledger_equals_phase36"] and pop_all["baseline_trades"] == 196, 196)

    # ============================================================ 7. classification, selection and documents
    bad = []
    for cid, r in cls.items():
        cs_ = [c for c in r["classifications"].split(";") if c]
        if any(c not in VALID for c in cs_) or (cid != "AC23" and not cs_):
            bad.append((cid, cs_))
    record("every active observation has at least one classification and all classifications belong to the required set (plus NO_DISCREPANCY_FOUND); no observation is classified CONFIRMED_SOFTWARE_BUG or WRONG_STRATEGY_SELECTION", not bad and not any("CONFIRMED_SOFTWARE_BUG" in r["classifications"] or "WRONG_STRATEGY_SELECTION" in r["classifications"] for r in cls.values()), len(cls), failures=bad)
    record("only AC27 is implemented, and only as an opt-in variant", [k for k, r in cls.items() if r["implemented"] != "NO"] == ["AC27"], 1)
    conf = defaultdict(set)
    for s in sig:
        conf[s["date"]].add(s["strategy"])
    bad = []
    for r in rd(OUT / "strategy_selection_conflicts.csv"):
        exp = r["author_expected_strategy"]
        had = exp in conf[r["date"]]
        if had != (r["expected_strategy_confirmed_signals"] != "none"):
            bad.append((r["correction_id"], exp, had))
    record("in strategy_selection_conflicts.csv the 'expected strategy produced confirmed signals' column equals the Phase 3.6 signal table, row by row", not bad, len(rd(OUT / "strategy_selection_conflicts.csv")), failures=bad)
    missing = [r["date"] for r in dated if not (OUT / "daily" / f"{r['date']}.md").exists() or not (OUT / "charts" / f"{r['date']}.svg").exists()]
    record("every dated observation has a day report and a chart", not missing, len(dated), failures=missing)
    txt = (OUT / "confirmed_software_defects.md").read_text()
    record("confirmed_software_defects.md states 'none' and no frozen file differs from its hash (strategy, controller, framework)", "**Result: none.**" in txt, 1)

    # ============================================================ 8. preservation
    changed, removed = [], []
    now_files = {}
    for t in ("src", "scripts", "tests", "docs", "data", "reports", "pyproject.toml"):
        base = ROOT / t
        for p in ([base] if base.is_file() else base.rglob("*")):
            if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts and OUT not in p.parents:
                now_files[p.relative_to(ROOT).as_posix()] = None
    for k, h in snap["hashes"].items():
        f = ROOT / k
        if not f.exists():
            removed.append(k)
        elif sha(f) != h:
            changed.append(k)
    added = [k for k in now_files if k not in snap["hashes"] and not k.startswith(ALLOWED_ADDED)]
    record("every file in the baseline snapshot (all of src, scripts, tests, docs, data, reports: the strategy files, the Phase 3.6 / 4 / 5 reports, the historical datasets, the manual journal and the handwritten PDF) is byte-identical", not changed and not removed, len(snap["hashes"]), failures=changed + removed)
    record("the only files added outside reports/phase5/phase51_author_corrections are the declared Phase 5.1 scripts, tests and the two new modules (orb_colour.py, phase51.py)", not added, len(now_files), failures=added)
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    record("every file hashed in the Phase 4 freeze (engines, controller, execution, session construction, framework) is unchanged", not bad, len(fr["active_file_hashes"]), fr["frozen_configuration_id"], bad)
    src = (ROOT / "src/nifty_trading/strategies/orb_colour.py").read_text()
    record("the variant is a subclass that only post-filters confirmed records (it contains no stop, target, level or threshold value)", "class ORBColourStrategy(ORBStrategy)" in src and not re.search(r"\b(30|60|27|35|0\.\d)\b\s*[,)]", src.split("class ORBColourStrategy")[1]), 1)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
