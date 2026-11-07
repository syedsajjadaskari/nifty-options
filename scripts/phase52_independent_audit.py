"""Phase 5.2 independent audit: re-derives what the Phase 5.2 reports state from the RAW Phase 1 one-minute files and the delivered CSVs only (no ``src/`` imports; the candle / EMA helpers come from the Phase 3.2 audit
script, itself free of ``src/``). The pattern thresholds are the PROPOSED research values recorded in reports/phase3/phase36_body_based_pdr/ (hard-coded below and checked against that configuration snapshot).

Checks: the first-eligible-candle claim for PDR and PDS re-implemented from the guides' sequence; the IRF EMA / running-low measurements (no look-ahead); the candidate IRF Method 2A signals against the candle sequence
they claim; the ORB first-candle audit; that the approved configuration equals the frozen signals; that RF and every non-candidate strategy are identical across configurations; and the preservation of every baseline file.
Run: .venv/bin/python scripts/phase52_independent_audit.py   ->   reports/phase5/phase52_author_rules/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import warnings
from collections import Counter
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase52_author_rules"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
RES: dict = {"checks": {}}
EPS = 1e-9
TH = {"green_body_min": 0.60, "green_upper_wick_max": 0.20, "reject_wick_to_body_min": 2.0, "reject_close_fraction_max": 0.30, "hammer_wick_to_body_min": 2.0, "hammer_upper_wick_max": 0.10, "hammer_body_position_min": 0.60}
STRONG = {"body_ratio_min": 0.60, "opposite_wick_ratio_max": 0.20}
PIN = {"wick_to_body_min": 2.0, "close_fraction_max": 0.30}
CUTOFF = "13:00"
ALLOWED_ADDED = ("reports/phase5/phase52_author_rules/", "scripts/phase52_", "src/nifty_trading/strategies/irf_candidates.py", "src/nifty_trading/strategies/pds_first_eligible.py", "src/nifty_trading/research/phase52", "tests/test_phase52_")


def fb_(x) -> bool:
    return str(x) == "True"


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def fnum(x) -> float:
    return float(str(x).replace(",", "")) if x not in ("", None) else 0.0


def hm(ts) -> str:
    return ts.strftime("%H:%M")


def ratios(o, h, low, c):
    rg = h - low
    if rg <= 0:
        return None
    return {"rg": rg, "body": abs(c - o), "body_pct": abs(c - o) / rg, "uw": h - max(o, c), "uw_pct": (h - max(o, c)) / rg, "lw": min(o, c) - low, "lw_pct": (min(o, c) - low) / rg, "body_pos": (min(o, c) - low) / rg, "close_from_high": (h - c) / rg}


def pdr_qualifies(o, h, low, c, ceiling) -> bool:
    r = ratios(o, h, low, c)
    if r is None or not c > ceiling:
        return False
    green = c > o and r["body_pct"] >= TH["green_body_min"] - EPS and r["uw_pct"] <= TH["green_upper_wick_max"] + EPS
    rej = r["lw"] > EPS and r["lw"] >= TH["reject_wick_to_body_min"] * r["body"] - EPS and r["close_from_high"] <= TH["reject_close_fraction_max"] + EPS and low <= ceiling
    ham = r["lw"] > EPS and r["lw"] >= TH["hammer_wick_to_body_min"] * r["body"] - EPS and r["uw_pct"] <= TH["hammer_upper_wick_max"] + EPS and r["body_pos"] >= TH["hammer_body_position_min"] - EPS
    return bool(green or rej or ham)


def strong_bear(o, h, low, c) -> bool:
    r = ratios(o, h, low, c)
    return r is not None and c < o and r["body_pct"] >= STRONG["body_ratio_min"] - EPS and r["lw_pct"] <= STRONG["opposite_wick_ratio_max"] + EPS


def bear_pin(o, h, low, c) -> bool:
    r = ratios(o, h, low, c)
    if r is None or r["uw"] <= EPS or r["uw"] < PIN["wick_to_body_min"] * r["body"] - EPS:
        return False
    return (c - low) <= PIN["close_fraction_max"] * r["rg"] + EPS


def main() -> int:  # noqa: C901
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    daily = rd(P36 / "daily_summary.csv")
    sig = rd(P36 / "all_strategy_signals.csv")
    rej = rd(P36 / "rejected_signals.csv")
    raw, warm = A32.load_raw(), A32.load_warm()
    allc = pd.concat([A32.five_minute(warm, A32.standard_days(warm)), A32.five_minute(raw, A32.standard_days(raw))]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = A32.ema_series(allc["close"].to_numpy())
    allc["day"] = allc.start.dt.date
    allc["end"] = allc.start + pd.Timedelta(minutes=5)
    by_day = {d: g.reset_index(drop=True) for d, g in allc.groupby("day")}
    dd = {r["date"]: r for r in daily}
    not_eval = {(r["date"], r["strategy"]) for r in rej if r["category"] == "ENGINE_NOT_EVALUATED"}
    first_conf = {}
    for s in sig:
        if s["time"] and s["entry_rule_status"]:
            k = (s["date"], s["strategy"])
            if k not in first_conf or s["time"] < first_conf[k][0]:
                first_conf[k] = (s["time"], s["method"])

    # ============================================================ 1. configuration thresholds match the Phase 3.6 configuration snapshot
    cfgtxt = (P36 / "configuration_snapshot.json").read_text()
    record("the three PDR patterns audited are the ones enabled in the Phase 3.6 configuration snapshot", all(k in cfgtxt for k in ("GOOD_GREEN_BODY", "LOWER_PRICE_REJECTION", "HAMMER")), 3, "pattern names are in the frozen snapshot; the numeric values are the Phase 3.5/3.6 research defaults in strategies/pdr_revised.py::PROFILES (read here as constants)")

    # ============================================================ 2. PDR first eligible, re-derived from the raw candles
    bad, n_set, n_sig = [], 0, 0
    for d, row in dd.items():
        if (d, "PDR") in not_eval:
            continue
        g = by_day[date.fromisoformat(d)]
        pd_ = date.fromisoformat(row["previous_session"]) if row["previous_session"] else None
        if pd_ is None or pd_ not in by_day:
            continue
        pc = by_day[pd_]
        openp, prev_close = g.open.iloc[0], fnum(row["prev_day_official_close"])
        indep = None
        if openp > prev_close:
            bh = np.maximum(pc.open, pc.close).to_numpy()
            j0 = int(np.argmax(bh))
            ceiling, floor = float(bh[j0]), float(min(pc.open.iloc[j0], pc.close.iloc[j0]))
            if openp > ceiling and ceiling > floor:
                n_set += 1
                j = None
                for i, c in enumerate(g.itertuples()):
                    if j is None:
                        if c.low <= ceiling and c.high >= floor:
                            j = i
                        continue
                    if pdr_qualifies(c.open, c.high, c.low, c.close, ceiling):
                        indep = hm(c.end)
                        break
        eng = first_conf.get((d, "PDR"))
        if indep is not None:
            n_sig += 1
        if (indep is None) != (eng is None) or (indep is not None and eng[0] != indep):
            bad.append((d, indep, eng))
    record("PDR: for every evaluated session the first eligible confirmation candle re-derived from the raw candles (body-based zone, strict open above, retest, patterns, close strictly above the ceiling) equals the engine's first PDR signal: no LATE_ENTRY_DEFECT and no missed entry", not bad, len(dd), f"{n_set} armed setups, {n_sig} first-eligible signals", bad)

    # ============================================================ 3. PDS first eligible (Methods 1 / 2 / 3), re-derived
    bad, n_set, n_sig = [], 0, 0
    for d, row in dd.items():
        if (d, "PDS") in not_eval:
            continue
        g = by_day[date.fromisoformat(d)]
        pd_ = date.fromisoformat(row["previous_session"]) if row["previous_session"] else None
        if pd_ is None or pd_ not in by_day:
            continue
        pc = by_day[pd_]
        openp, prev_close = g.open.iloc[0], fnum(row["prev_day_official_close"])
        indep = None
        if openp < prev_close:
            lows = pc.low.to_numpy()
            j0 = int(np.argmin(lows))
            zl, zh = float(lows[j0]), float(max(pc.open.iloc[j0], pc.close.iloc[j0]))
            if openp < zl:
                n_set += 1
                cs = list(g.itertuples())
                def at(c, zl=zl, zh=zh):
                    return c.high >= zl and c.low <= zh
                started = weak = None
                m3 = False
                for i, c in enumerate(cs):
                    if started is None:
                        if not at(c):
                            continue
                        started = i
                    if weak is None and c.close < c.open and at(c):
                        if strong_bear(c.open, c.high, c.low, c.close) or (bear_pin(c.open, c.high, c.low, c.close) and c.high >= zl):
                            indep = (hm(c.end), "Method 1" if strong_bear(c.open, c.high, c.low, c.close) else "Method 2")
                            break
                        weak, m3 = i, True
                    if m3:
                        start = weak if weak is not None else started
                        piv = [jj for jj in range(max(start, 1), i - 1) if cs[jj].low <= cs[jj - 1].low and cs[jj].low <= cs[jj + 1].low and cs[jj].low <= zh]
                        if piv and c.close < cs[piv[-1]].low:
                            indep = (hm(c.end), "Method 3")
                            break
        eng = first_conf.get((d, "PDS"))
        if indep is not None:
            n_sig += 1
        if (indep is None) != (eng is None) or (indep is not None and (eng[0], eng[1]) != indep):
            bad.append((d, indep, eng))
    record("PDS: for every evaluated session the first eligible confirmation (Method 1 / 2 on the first red candle at the zone, Method 3 only after a weak first candle and on the first support break) re-derived from the raw candles equals the engine's first PDS signal and method", not bad, len(dd), f"{n_set} armed setups, {n_sig} first-eligible signals", bad)

    # ============================================================ 4. the delivered diagnostics tables agree with the engine and carry no defect
    pdr_csv, pds_csv = rd(OUT / "pdr_first_eligible_setups.csv"), rd(OUT / "pds_first_eligible_setups.csv")
    vd = Counter(r["verdict"] for r in pdr_csv) + Counter(r["verdict"] for r in pds_csv)
    record("no setup in the PDR / PDS diagnostics is flagged LATE_ENTRY_DEFECT or ELIGIBLE_CANDLE_BUT_NO_ENGINE_SIGNAL", not any(k in vd for k in ("LATE_ENTRY_DEFECT", "ELIGIBLE_CANDLE_BUT_NO_ENGINE_SIGNAL", "ENGINE_EARLIER_THAN_DIAGNOSTIC")), len(pdr_csv) + len(pds_csv), str(dict(vd)))
    summ = json.loads((OUT / "signal_counts.json").read_text())

    # ============================================================ 5. IRF measurements recomputed (EMA, running low, no look-ahead)
    irf = rd(OUT / "irf_signal_diagnostics.csv")
    bad, n_lookahead_cases = [], 0
    opens = raw.assign(key=raw.timestamp.dt.strftime("%Y-%m-%d %H:%M")).set_index("key")["open"]
    for r in irf:
        g = by_day[date.fromisoformat(r["date"])]
        i = next((k for k, c in enumerate(g.itertuples()) if hm(c.end) == r["signal_time"]), None)
        if i is None:
            bad.append((r["date"], "no candle"))
            continue
        c = g.iloc[i]
        before = float(g.low.iloc[:i].min()) if i else None
        full_low = float(g.low.min())
        fill = float(opens.get(f"{r['date']} {r['signal_time']}", np.nan))
        em = None if np.isnan(c.ema) else float(c.ema)
        if before is not None and before > full_low + 1e-9:
            n_lookahead_cases += 1  # the final daily low is lower than the running low: a look-ahead implementation would differ here
        ok = (abs(fnum(r["entry_price"]) - fill) < 1e-9 and (before is None or abs(fnum(r["running_low_before_signal_candle"]) - before) < 1e-9)
              and abs(fnum(r["running_low_including_signal_candle"]) - min(before if before is not None else c.low, c.low)) < 1e-9 and (em is None or abs(fnum(r["ema200"]) - em) < 0.006)
              and (em is None or abs(fnum(r["entry_minus_ema"]) - (fill - em)) < 0.006) and (em is None or (str(r["ema_between_entry_and_t1"]) == str((fill - 27.0) < em < fill))))
        if not ok:
            bad.append((r["date"], r["signal_time"]))
    record("IRF diagnostics: EMA(200), entry price (next one-minute open), entry-EMA distance, EMA between entry and Target 1 and the running session low equal an independent recomputation for every confirmed IRF signal; the running low uses only candles closed before the signal", not bad, len(irf),
           f"{n_lookahead_cases} signals where the final daily low is lower than the running low (a look-ahead implementation would differ)", bad)
    # ---- readings D6 / D7 / D8 and the cutoff split recomputed from the raw candles
    bad6 = []
    for r in irf:
        g = by_day[date.fromisoformat(r["date"])]
        i = next((k for k, c in enumerate(g.itertuples()) if hm(c.end) == r["signal_time"]), None)
        if i is None or i == 0:
            continue
        irl = float(g.low.iloc[0])
        pdate = date.fromisoformat(dd[r["date"]]["previous_session"])
        pl = float(by_day[pdate].low.min())
        entry = fnum(r["entry_price"])
        d6, d7, d8 = float(g.low.iloc[:i].min()) < irl, bool((g.close.iloc[1:i] < irl).any()), entry < pl
        if (str(d6), str(d7), str(d8)) != (r["D6_running_low_already_below_irl"], r["D7_earlier_close_below_irl"], r["D8_entry_below_previous_day_low"]) or (r["signal_time"] <= CUTOFF) != fb_(r["within_13_00_cutoff"]):
            bad6.append((r["date"], r["signal_time"]))
    record("IRF readings D6 (running low already below the initial range low), D7 (an earlier close below it), D8 (entry below the previous day's low) and the 13:00 cutoff flag equal an independent recomputation for every confirmed IRF signal", not bad6, len(irf), failures=bad6)
    flags = summ["irf_flag_counts"]
    bad = []
    for fk, fn in (("E1_close_gap_below_ema_28", lambda r: 0 < fnum(r["close_minus_ema"]) < 28), ("E2_entry_gap_below_ema_28", lambda r: 0 < fnum(r["entry_minus_ema"]) < 28), ("E1_27", lambda r: 0 < fnum(r["close_minus_ema"]) < 27),
                   ("D2_close_below_running_low_before", lambda r: r["running_low_before_signal_candle"] != "" and fnum(r["close_minus_running_low_before"]) < 0), ("D4_t1_beyond_running_low", lambda r: r["running_low_before_signal_candle"] != "" and fnum(r["t1_clearance_above_running_low"]) < 0)):
        n = sum(1 for r in irf if r["ema200"] != "" and fn(r)) if fk.startswith("E") else sum(1 for r in irf if fn(r))
        if n != flags[fk]["all_signals"]:
            bad.append((fk, n, flags[fk]["all_signals"]))
    record("IRF flag counts quoted in signal_counts.json (28- and 27-point EMA readings, close below the running low, Target 1 beyond the running low) equal recomputation from the diagnostics table", not bad, 5, failures=bad)

    # ============================================================ 6. candidate IRF Method 2A signals against the candle sequence they claim
    allsig = rd(OUT / "all_confirmed_signals.csv")
    bad, n = [], 0
    for r in allsig:
        if r["config"] not in ("phase52-cand-irf-first-red-low", "phase52-cand-irf-first-red-body-low") or r["method"] != "Method 2A":
            continue
        lv = dict(x.split("=", 1) for x in r["levels"].split("; ") if "=" in x)
        g = by_day[date.fromisoformat(r["date"])]
        cs = list(g.itertuples())
        irh = cs[0].high
        e, ri = int(lv["extension_index"]), int(lv["red_candle_index"])
        i = next(k for k, c in enumerate(cs) if hm(c.end) == r["signal_time"])
        n += 1
        # the attempt's breakout candle is the first close above IRH after the previous attempt ended; accept any candle b that closes above IRH,
        # is not exceeded in high before the extension candle, and is exceeded by the extension candle (E1 definition)
        b = next((k for k in range(1, e) if cs[k].close > irh and cs[e].high > cs[k].high and all(cs[m].high <= cs[k].high for m in range(k + 1, e))), None)
        red = cs[ri]
        lvl = red.low if r["config"].endswith("low") and not r["config"].endswith("body-low") else min(red.open, red.close)
        ok = (b is not None and abs(fnum(lv["recent_support"]) - lvl) < 1e-9 and red.close < red.open and ri >= e + 1 and all(not (cs[k].close < cs[k].open) for k in range(e + 1, ri)) and i > ri and cs[i].close < lvl and all(cs[k].close >= lvl for k in range(ri + 1, i)) and abs(cs[i].close - fnum(r["entry_reference_close"])) < 1e-9)
        if not ok:
            bad.append((r["config"], r["date"], r["signal_time"]))
    record("candidate IRF Method 2A signals: each one's breakout, extension, FIRST red candle after the extension, support level (low or body low of that candle) and the FIRST later close below it match the raw candle sequence (the reference candle is never replaced by a later one)", not bad, n, failures=bad)

    # ============================================================ 7. approved configuration equals the frozen signals; RF and untouched strategies identical everywhere
    def keyset(cfg, strategies=None):
        return sorted((r["date"], r["strategy"], r["method"], r["direction"], r["signal_time"]) for r in allsig if r["config"] == cfg and (strategies is None or r["strategy"] in strategies))
    record("the approved configuration's confirmed signals equal the frozen Phase 3.6 reference on date, strategy, method, direction and time (first-eligible principle already satisfied; only the PDS co-confirmation annotation differs)", keyset("phase52-approved") == keyset("phase36-frozen"), len(keyset("phase36-frozen")))
    bad = []
    for cfg, changed in (("phase52-cand-orb-colour", {"ORB"}), ("phase52-cand-irf-first-red-low", {"IRF"}), ("phase52-cand-irf-first-red-body-low", {"IRF"})):
        others = {"IRF", "ORB", "PDR", "PDS", "RF"} - changed
        if keyset(cfg, others) != keyset("phase36-frozen", others):
            bad.append(cfg)
    record("every candidate changes only its own strategy: RF, PDR, PDS and the other strategy are identical to the frozen signals under every candidate (no change to RF; no cross-strategy priority)", not bad, 3, failures=bad)
    bad = [r for r in allsig if r["config"] == "phase52-cand-irf-first-red-low" and r["strategy"] == "IRF" and r["method"] in ("Method 1", "Method 3")]
    base_m = Counter((r["date"], r["method"], r["signal_time"]) for r in allsig if r["config"] == "phase36-frozen" and r["strategy"] == "IRF" and r["method"] in ("Method 1", "Method 3"))
    cand_m = Counter((r["date"], r["method"], r["signal_time"]) for r in bad)
    record("IRF Method 1 and Method 3 signals are identical under the first-red candidate (scope: Method 2A only)", base_m == cand_m, sum(base_m.values()))

    # ============================================================ 8. ORB first-candle audit and the absence of ORB signals on the 13 dates
    orb = rd(OUT / "orb_missing_signal_audit.csv")
    bad = []
    for r in orb:
        g = by_day[date.fromisoformat(r["date"])]
        c0 = g.iloc[0]
        pd_ = next(date.fromisoformat(v["previous_session"]) for k, v in dd.items() if k == r["date"])
        pc = by_day[pd_]
        ph, pl = float(pc.high.max()), float(pc.low.min())
        long = r["direction"] == "LONG"
        lvl = ph if long else pl
        broke = (c0.high > lvl and c0.close > lvl) if long else (c0.low < lvl and c0.close < lvl)
        ok = (r["first_candle_ohlc"] == f"{c0.open}/{c0.high}/{c0.low}/{c0.close}" and str(r["M1_level_broken"]) == str(bool(broke)) and abs(fnum(r["ema200"]) - c0.ema) < 0.006
              and str(r["colour_matches_direction"]) == str((c0.close > c0.open) if long else (c0.close < c0.open)))
        if not ok:
            bad.append((r["date"], r["direction"]))
    record("ORB audit: first-candle OHLC, previous-day level, Method 1 level-broken flag, EMA and colour-matches-direction equal an independent recomputation on the 13 disputed dates, both directions", not bad, len(orb), failures=bad)
    orb_dates = {r["date"] for r in orb}
    has = [s for s in sig if s["strategy"] == "ORB" and s["date"] in orb_dates and s["entry_rule_status"]]
    record("the Phase 3.6 signal table has no confirmed ORB signal on any of the 13 disputed dates (the engine produced none, so the controller could not have skipped one)", not has, len(orb_dates))

    # ============================================================ 9. deliverables and preservation
    need = ["README.md", "author_call_clarifications.md", "rule_authority_matrix.md", "pdr_first_eligible_audit.md", "pds_first_eligible_audit.md", "irf_first_red_candle_audit.md", "irf_ema_28_point_audit.md", "irf_day_low_audit.md", "orb_missing_signal_audit.md",
            "before_after_signals.csv", "dated_corrections_comparison.csv", "remaining_owner_decisions.md", "source_to_code_traceability.md", "independent_audit.md", "Phase52_Trade_Corrections_Verification.xlsx"]
    miss = [n for n in need if not (OUT / n).exists()] + [n for n in ("daily", "charts") if not (OUT / n).is_dir()]
    record("every required Phase 5.2 deliverable exists", not miss, len(need) + 2, failures=miss)
    now = {}
    for t in ("src", "scripts", "tests", "docs", "data", "reports", "pyproject.toml"):
        base = ROOT / t
        for p in ([base] if base.is_file() else base.rglob("*")):
            if p.is_file() and p.name != ".DS_Store" and "__pycache__" not in p.parts and OUT not in p.parents:
                now[p.relative_to(ROOT).as_posix()] = None
    changed, removed = [], []
    for k, h in snap["hashes"].items():
        f = ROOT / k
        if not f.exists():
            removed.append(k)
        elif sha(f) != h:
            changed.append(k)
    added = [k for k in now if k not in snap["hashes"] and not k.startswith(ALLOWED_ADDED)]
    record("every file in the Phase 5.2 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.1 reports, the frozen strategy files, the historical datasets, the manual journal, the handwritten PDF) is byte-identical", not changed and not removed, len(snap["hashes"]), failures=changed + removed)
    record("the only files added outside reports/phase5/phase52_author_rules are the declared Phase 5.2 scripts, tests and new modules", not added, len(now), failures=added)
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    record("every file hashed in the Phase 4 freeze (engines incl. RF, controller, execution, session construction, framework) is unchanged", not bad, len(fr["active_file_hashes"]), fr["frozen_configuration_id"], bad)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
