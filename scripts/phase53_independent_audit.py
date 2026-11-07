"""Phase 5.3 independent audit: re-derives what the Phase 5.3 reports state from the RAW Phase 1 one-minute files and the delivered CSVs only (no ``src/`` imports; the candle / EMA helpers come from the Phase 3.2
audit script, itself free of ``src/``).

Checks: the IRF EMA(200) range / close distances and their pass flags; that every surviving IRF signal of the EMA configurations has at least 28 points of clearance and every logged rejection less than 28; the IRF
Method 2A signals of the first-red-low configurations against the candle sequence they claim (first red candle after the extension, support = its LOW, first later close below it, never replaced); the PDR and PDS earliest
eligible confirmations (Phase 5.3 conventions) re-implemented from the guides' sequence; that every configuration changes only its own strategies; that ORB and RF are untouched; the deliverables; and the preservation of
every baselined file.
Run: .venv/bin/python scripts/phase53_independent_audit.py   ->   reports/phase5/phase53_author_corrected/independent_audit_results.json
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

OUT = ROOT / "reports" / "phase5" / "phase53_author_corrected"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
RES: dict = {"checks": {}}
EPS = 1e-9
CUTOFF = "13:00"
FROZEN, COMB = "phase36-frozen", "phase53-author-corrected"
ALLOWED_ADDED = ("reports/phase5/phase53_author_corrected/", "scripts/phase53_", "src/nifty_trading/strategies/irf_phase53.py", "src/nifty_trading/strategies/first_eligible_phase53.py", "src/nifty_trading/research/phase53", "tests/test_phase53_")


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


def geom(h, low, c, ema):
    if ema > h:
        return "EMA_ABOVE_CANDLE", ema - h, abs(c - ema)
    if ema < low:
        return "EMA_BELOW_CANDLE", low - ema, abs(c - ema)
    return "EMA_INSIDE_CANDLE", 0.0, abs(c - ema)


def main() -> int:  # noqa: C901
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    daily = rd(P36 / "daily_summary.csv")
    raw, warm = A32.load_raw(), A32.load_warm()
    allc = pd.concat([A32.five_minute(warm, A32.standard_days(warm)), A32.five_minute(raw, A32.standard_days(raw))]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = A32.ema_series(allc["close"].to_numpy())
    allc["day"] = allc.start.dt.date
    allc["end"] = allc.start + pd.Timedelta(minutes=5)
    by_day = {d: g.reset_index(drop=True) for d, g in allc.groupby("day")}
    dd = {r["date"]: r for r in daily}
    allsig = rd(OUT / "all_confirmed_signals.csv")
    summ = json.loads((OUT / "signal_counts.json").read_text())
    cfg_sig: dict[str, list] = {}
    for r in allsig:
        cfg_sig.setdefault(r["config"], []).append(r)

    def first_by(cfg, strat):
        out = {}
        for r in sorted(cfg_sig[cfg], key=lambda x: (x["date"], x["signal_time"])):
            if r["strategy"] == strat:
                out.setdefault(r["date"], (r["signal_time"], r["method"]))
        return out

    def candle_at(d, t):
        g = by_day[date.fromisoformat(d)]
        i = next((k for k, c in enumerate(g.itertuples()) if hm(c.end) == t), None)
        return g, i

    # ============================================================ 1. EMA geometry of the delivered table equals an independent recomputation
    ema_rows = rd(OUT / "irf_ema_signals.csv")
    bad = []
    for r in ema_rows:
        g, i = candle_at(r["date"], r["signal_time"])
        if i is None or r["ema_available"] != "True":
            if i is None:
                bad.append((r["config"], r["date"], r["signal_time"], "no candle"))
            continue
        c = g.iloc[i]
        rel, rng, cd = geom(c.high, c.low, c.close, c.ema)
        ok = (r["ema_relation"] == rel and abs(fnum(r["range_clearance"]) - rng) < 0.006 and abs(fnum(r["close_distance"]) - cd) < 0.006 and fb_(r["pass_range_28"]) == (rng >= 28 - EPS) and fb_(r["pass_range_27"]) == (rng >= 27 - EPS)
              and fb_(r["pass_close_28"]) == (cd >= 28 - EPS) and fb_(r["pass_close_27"]) == (cd >= 27 - EPS))
        if not ok:
            bad.append((r["config"], r["date"], r["signal_time"]))
    record("IRF EMA table: EMA(200), the EMA's position relative to the signal candle (above / below / inside), the range distance, the close distance and the four pass flags (range / close, 28 / 27) equal an independent recomputation from the raw candles for every confirmed IRF signal", not bad, len(ema_rows), failures=bad)

    # ============================================================ 2. the 28-point gate: survivors have >= 28, rejections < 28, no look-ahead
    bad, n = [], 0
    for cfg in (COMB, "phase53-irf-ema28"):
        for r in cfg_sig[cfg]:
            if r["strategy"] != "IRF":
                continue
            g, i = candle_at(r["date"], r["signal_time"])
            c = g.iloc[i]
            if np.isnan(c.ema):
                continue
            n += 1
            if geom(c.high, c.low, c.close, c.ema)[1] < 28 - EPS:
                bad.append((cfg, r["date"], r["signal_time"], r["method"]))
    record("every surviving IRF signal of the EMA configurations has at least 28 points of range clearance from the EMA(200) of its own (completed) signal candle", not bad, n, failures=bad)
    rej = rd(OUT / "irf_ema_rejections.csv")
    bad = []
    for r in rej:
        if r.get("ema_available") != "True":
            continue
        g, i = candle_at(r["date"], r["signal_time"])
        c = g.iloc[i]
        if geom(c.high, c.low, c.close, c.ema)[1] >= 28 - EPS or abs(fnum(r["ema200"]) - c.ema) > 0.006:
            bad.append((r["config"], r["date"], r["signal_time"]))
    record("every logged EMA rejection really has less than 28 points of range clearance, using the EMA value of the signal candle itself (no later value)", not bad, len(rej), failures=bad)
    borderline = [r for r in ema_rows if r.get("range_clearance") not in ("", None) and abs(fnum(r["range_clearance"]) - 28.0) < 0.05]
    record("boundary cases near exactly 28.0 points are decided inclusively (>= 28 passes)", all(fb_(r["pass_range_28"]) == (fnum(r["range_clearance"]) >= 28.0 - 1e-6) for r in borderline), len(borderline), f"{len(borderline)} signals within 0.05 of the boundary")

    # ============================================================ 3. the first-red-low Method 2A signals against the raw candle sequence
    bad, n = [], 0
    rejected_2a = {(x["config"], x["date"], x["signal_time"]) for x in rd(OUT / "irf_ema_rejections.csv") if x["method"] == "Method 2A"}
    for r in allsig:
        if r["config"] not in ("phase53-irf-first-red-low", COMB) or r["strategy"] != "IRF" or r["method"] != "Method 2A":
            continue
        lv = dict(x.split("=", 1) for x in r["levels"].split("; ") if "=" in x)
        g = by_day[date.fromisoformat(r["date"])]
        cs = list(g.itertuples())
        irh = cs[0].high
        e, ri = int(lv["extension_index"]), int(lv["red_candle_index"])
        i = next(k for k, c in enumerate(cs) if hm(c.end) == r["signal_time"])
        n += 1
        b = next((k for k in range(1, e) if cs[k].close > irh and cs[e].high > cs[k].high and all(cs[m].high <= cs[k].high for m in range(k + 1, e))), None)
        red = cs[ri]
        ok = (b is not None and abs(fnum(lv["recent_support"]) - red.low) < 1e-9 and red.close < red.open and ri >= e + 1 and all(not (cs[k].close < cs[k].open) for k in range(e + 1, ri))
              and i > ri and cs[i].close < red.low
              and all(cs[k].close >= red.low or (r["config"], r["date"], hm(cs[k].end)) in rejected_2a for k in range(ri + 1, i)) and abs(cs[i].close - fnum(r["entry_reference_close"])) < 1e-9 and int(lv["support_candle_index"]) == ri)
        if not ok:
            bad.append((r["config"], r["date"], r["signal_time"]))
    record("IRF Method 2A under the first-red-low rule: breakout, extension, the FIRST red candle after the extension (never replaced), support = that candle's LOW (wick included) and the FIRST later close below it (earlier closes below it are allowed only where the EMA gate logged a rejection) match the raw candle sequence", not bad, n, failures=bad)

    # ============================================================ 4. PDR earliest eligible (Phase 5.3 minimal convention) re-derived
    bad, n_set, n_sig, later_than_frozen = [], 0, 0, []
    p53, frz = first_by("phase53-pdr-first-eligible", "PDR"), first_by(FROZEN, "PDR")
    for d, row in dd.items():
        g = by_day[date.fromisoformat(d)]
        pd_ = date.fromisoformat(row["previous_session"]) if row["previous_session"] else None
        if pd_ is None or pd_ not in by_day or not row["prev_day_official_close"]:
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
                        continue  # the retest candle itself never confirms
                    body, uw, lw = abs(c.close - c.open), c.high - max(c.open, c.close), min(c.open, c.close) - c.low
                    green = c.close > c.open
                    rejection = lw > body and lw > uw and c.low <= ceiling
                    if (green or rejection) and c.close > ceiling:
                        indep = hm(c.end)
                        break
        eng = p53.get(d)
        if indep is not None:
            n_sig += 1
        if (indep is None) != (eng is None) or (indep is not None and eng[0] != indep):
            bad.append((d, indep, eng))
        if eng is not None and d in frz and eng[0] > frz[d][0]:
            later_than_frozen.append((d, eng, frz[d]))
    record("PDR (Phase 5.3): for every session the first eligible confirmation candle re-derived from the raw candles (body-based zone, strict open above, retest first, green candle or lower-price rejection, close strictly above the ceiling) equals the engine's first PDR signal", not bad, n_set, f"{n_sig} sessions with a signal", bad)
    record("PDR (Phase 5.3): the first signal is never later than the frozen engine's first signal on the same session", not later_than_frozen, len(p53), failures=later_than_frozen)

    # ============================================================ 5. PDS earliest eligible (Phase 5.3 quality tests), source sequence preserved
    bad, n_set, n_sig = [], 0, 0
    p53s = first_by("phase53-pds-first-eligible", "PDS")
    for d, row in dd.items():
        g = by_day[date.fromisoformat(d)]
        pd_ = date.fromisoformat(row["previous_session"]) if row["previous_session"] else None
        if pd_ is None or pd_ not in by_day or not row["prev_day_official_close"]:
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
                        body, uw, lw = abs(c.close - c.open), c.high - max(c.open, c.close), min(c.open, c.close) - c.low
                        if body > uw and body > lw:
                            indep = (hm(c.end), "Method 1")
                            break
                        if uw > body and uw > lw and c.high >= zl:
                            indep = (hm(c.end), "Method 2")
                            break
                        weak, m3 = i, True
                    if m3:
                        start = weak if weak is not None else started
                        piv = [jj for jj in range(max(start, 1), i - 1) if cs[jj].low <= cs[jj - 1].low and cs[jj].low <= cs[jj + 1].low and cs[jj].low <= zh]
                        if piv and c.close < cs[piv[-1]].low:
                            indep = (hm(c.end), "Method 3")
                            break
        eng = p53s.get(d)
        if indep is not None:
            n_sig += 1
        if (indep is None) != (eng is None) or (indep is not None and (eng[0], eng[1]) != indep):
            bad.append((d, indep, eng))
    record("PDS (Phase 5.3): for every session the first eligible confirmation (Methods 1 / 2 on the FIRST red candle at the zone with the body-dominance / upper-wick-dominance tests; a weak first red candle is NOT taken and Method 3 needs the small-support break) re-derived from the raw candles equals the engine's first PDS signal and method", not bad, n_set, f"{n_sig} sessions with a signal", bad)
    pds_rows = rd(OUT / "pds_first_eligible_setups.csv")
    weak_signals = [r for r in pds_rows if str(r["phase53_verdict"]).startswith("WEAK") and r["phase53_first_pds_signal"] and "Method 3" not in r["phase53_first_pds_signal"]]
    record("PDS (Phase 5.3): no signal is ever taken on a weak first red candle (every session whose first red candle is weak has either no signal or a Method 3 signal)", not weak_signals, len(pds_rows), failures=[r["date"] for r in weak_signals])

    # ============================================================ 6. every configuration changes only its own strategies; ORB / RF untouched; approved equals frozen
    def keyset(cfg, strategies):
        return sorted((r["date"], r["strategy"], r["method"], r["direction"], r["signal_time"]) for r in cfg_sig[cfg] if r["strategy"] in strategies)
    bad = []
    for cfg, changed in (("phase53-irf-first-red-low", {"IRF"}), ("phase53-irf-ema28", {"IRF"}), ("phase53-pdr-first-eligible", {"PDR"}), ("phase53-pds-first-eligible", {"PDS"}), (COMB, {"IRF", "PDR", "PDS"}), ("phase53-var-orb-colour", {"ORB"}),
                         ("phase53-var-irf-first-red-after-breakout", {"IRF"}), ("phase53-var-irf-ema28-method2-only", {"IRF"}), ("phase53-var-irf-ema27", {"IRF"}), ("phase53-var-irf-ema28-close", {"IRF"})):
        others = {"IRF", "ORB", "PDR", "PDS", "RF"} - changed
        if keyset(cfg, others) != keyset(FROZEN, others):
            bad.append(cfg)
    record("every Phase 5.3 configuration changes only its own strategies: RF and every other strategy are identical to the frozen signals (no cross-strategy priority; ORB and RF are untouched in the combined configuration)", not bad, 10, failures=bad)
    allk = {"IRF", "ORB", "PDR", "PDS", "RF"}
    record("the Phase 5.2 approved configuration still equals the frozen Phase 3.6 signal set", keyset("phase52-approved", allk) == keyset(FROZEN, allk), len(keyset(FROZEN, allk)))
    record("the frozen reference reproduces the Phase 3.6 signal table (1,083 confirmed signals)", len(cfg_sig[FROZEN]) == len(rd(P36 / "all_strategy_signals.csv")) == 1083, len(cfg_sig[FROZEN]))

    # ============================================================ 7. IRF methods outside the first-red scope are untouched by the first-red-low rule
    def irf_keys(cfg, methods):
        return sorted((r["date"], r["method"], r["signal_time"]) for r in cfg_sig[cfg] if r["strategy"] == "IRF" and r["method"] in methods)
    record("IRF Method 1 and Method 3 signals are identical under the first-red-low rule alone (scope: Method 2A only; Method 2B is resistance-based)", irf_keys("phase53-irf-first-red-low", ("Method 1", "Method 3")) == irf_keys(FROZEN, ("Method 1", "Method 3")), len(irf_keys(FROZEN, ("Method 1", "Method 3"))))

    # ============================================================ 8. ORB: no confirmed ORB signal on the 13 disputed dates, engine untouched
    orb = rd(OUT / "orb_unresolved_entries.csv")
    has = [r["date"] for r in orb if any(s["strategy"] == "ORB" and s["date"] == r["date"] for s in cfg_sig[FROZEN])]
    has2 = [r["date"] for r in orb if any(s["strategy"] == "ORB" and s["date"] == r["date"] for s in cfg_sig[COMB])]
    record("no confirmed ORB signal exists on any of the 13 disputed dates in the Phase 3.6 or the Phase 5.3 author-corrected configuration (the controller skipped nothing)", not has and not has2, len(orb), failures=has + has2)

    # ============================================================ 9. numbers quoted in signal_counts.json equal the CSV
    bad = []
    for cfg, v in ((k, summ[k]) for k in cfg_sig):
        if v["confirmed_total"] != len(cfg_sig[cfg]) or v["by_strategy"] != {s: sum(1 for r in cfg_sig[cfg] if r["strategy"] == s) for s in ("IRF", "ORB", "PDR", "PDS", "RF")}:
            bad.append(cfg)
    record("confirmed-signal totals per configuration and strategy quoted in signal_counts.json equal the delivered signal table", not bad, len(cfg_sig), failures=bad)
    cmp_rows = rd(OUT / "signal_comparison.csv")
    bad = []
    for cfg in ("phase53-irf-first-red-low", "phase53-irf-ema28", "phase53-pdr-first-eligible", "phase53-pds-first-eligible", COMB):
        tot = Counter(r["change"] for r in cmp_rows if r["config"] == cfg)
        want = Counter()
        for k, n in summ["change_counts_vs_frozen"][cfg].items():
            if not k.endswith("/UNCHANGED"):
                want[k.split("/")[1]] += n
        if tot != want:
            bad.append((cfg, dict(tot), dict(want)))
    record("the change counts quoted in signal_counts.json equal the rows of signal_comparison.csv", not bad, 5, failures=bad)

    # ============================================================ 10. deliverables and preservation
    need = ["README.md", "approved_author_decisions.md", "rule_authority_matrix.md", "irf_first_red_low_implementation.md", "irf_ema_28_implementation.md", "pdr_first_eligible_implementation.md", "pds_first_eligible_implementation.md",
            "orb_unresolved_entries.md", "irf_day_low_unresolved.md", "source_to_code_traceability.md", "signal_comparison.csv", "dated_author_corrections.csv", "remaining_owner_decisions.md", "independent_audit.md",
            "Phase53_Author_Corrections_Verification.xlsx"]
    miss = [n for n in need if not (OUT / n).exists()] + [n for n in ("daily", "charts") if not (OUT / n).is_dir()]
    record("every required Phase 5.3 deliverable exists", not miss, len(need) + 2, failures=miss)
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
    record("every file in the Phase 5.3 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.2 reports, the frozen strategy files, the historical datasets, the manual journal, the handwritten PDF) is byte-identical", not changed and not removed, len(snap["hashes"]), failures=changed + removed)
    record("the only files added outside reports/phase5/phase53_author_corrected are the declared Phase 5.3 scripts, tests and new modules", not added, len(now), failures=added)
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    record("every file hashed in the Phase 4 freeze (engines incl. RF, controller, execution, session construction, framework) is unchanged", not bad, len(fr["active_file_hashes"]), fr["frozen_configuration_id"], bad)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
