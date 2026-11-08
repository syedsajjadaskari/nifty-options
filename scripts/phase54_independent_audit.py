"""Phase 5.4 independent audit: re-derives what the Phase 5.4 reports state from the RAW Phase 1 one-minute files, the original manual-journal workbook and the delivered CSVs only (no ``src/`` imports; the candle / EMA helpers
come from the Phase 3.2 audit script, itself free of ``src/``).

Checks: the 13 disputed dates' first candle, previous-day levels, gap, EMA(200) and trend numbers; the Method 1 / strength / Gap-crossing predicates; the previous-session fractals and the trendline value; the level-family
levels (previous day, 2 / 3 / 5 sessions); the population count of sessions on which the first candle breaks the previous-day extreme; the ten cases where the two Gap readings differ; the journal counts and the engine-versus-journal
ORB overlap; the internal consistency of the variant table; the registry vocabulary; the deliverables; and the preservation of every baselined file.
Run: .venv/bin/python scripts/phase54_independent_audit.py   ->   reports/phase5/phase54_orb_audit/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import warnings
from datetime import date
from pathlib import Path

import openpyxl
import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase54_orb_audit"
P36 = ROOT / "reports" / "phase3" / "phase36_body_based_pdr"
RES: dict = {"checks": {}}
EPS = 1e-9
D13 = ["2025-09-11", "2025-09-16", "2025-10-08", "2025-10-16", "2025-10-17", "2025-10-27", "2025-11-21", "2025-11-28", "2025-12-05", "2025-12-12", "2025-12-24", "2025-12-30", "2025-12-31"]
ALLOWED_ADDED = ("reports/phase5/phase54_orb_audit/", "scripts/phase54_", "src/nifty_trading/strategies/orb_candidates.py", "src/nifty_trading/research/phase54", "tests/test_phase54_")


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def num(x) -> float | None:
    return None if x in ("", None, "None") else float(str(x).replace(",", ""))


def fb(x) -> bool:
    return str(x) == "True"


def main() -> int:  # noqa: C901
    snap = json.loads((OUT / "before_snapshot.json").read_text())
    summ = json.loads((OUT / "summary.json").read_text())
    daily = {r["date"]: r for r in rd(P36 / "daily_summary.csv")}
    raw, warm = A32.load_raw(), A32.load_warm()
    allc = pd.concat([A32.five_minute(warm, A32.standard_days(warm)), A32.five_minute(raw, A32.standard_days(raw))]).drop_duplicates(subset=["start"]).sort_values("start").reset_index(drop=True)
    allc["ema"] = A32.ema_series(allc["close"].to_numpy())
    allc["day"] = allc.start.dt.date
    allc["end"] = allc.start + pd.Timedelta(minutes=5)
    by_day = {d: g.reset_index(drop=True) for d, g in allc.groupby("day")}
    days = sorted(by_day)
    ev_days = sorted(date.fromisoformat(d) for d in daily if date.fromisoformat(d) in by_day)
    prev_of = {d: days[days.index(d) - 1] for d in ev_days if days.index(d) > 0}
    d13 = {r["date"]: r for r in rd(OUT / "orb_13_disputed_dates.csv")}
    strength = {r["date"]: r for r in rd(OUT / "orb_strength_review.csv")}
    trend = {r["date"]: r for r in rd(OUT / "orb_ema_trendline_review.csv")}
    pm = rd(OUT / "orb_predicate_matrix.csv")

    def first_candle(d):
        g = by_day[d]
        return g.iloc[0]

    # ============================================================ 1. first candle, previous-day levels, gap, EMA
    bad = []
    for ds in D13:
        d = date.fromisoformat(ds)
        c, pg = first_candle(d), by_day[prev_of[d]]
        rg = c.high - c.low
        ph, pl, pcl = pg.high.max(), pg.low.min(), num(daily[ds]["prev_day_official_close"])
        r = d13[ds]
        ok = (r["first_candle_ohlc"] == f"{c.open}/{c.high}/{c.low}/{c.close}" and f"{c.start:%H:%M}" == "09:15" and abs(num(r["body_pct"]) - 100 * abs(c.close - c.open) / rg) < 0.06
              and abs(num(r["upper_wick_pct"]) - 100 * (c.high - max(c.open, c.close)) / rg) < 0.06 and abs(num(r["lower_wick_pct"]) - 100 * (min(c.open, c.close) - c.low) / rg) < 0.06
              and r["previous_day_high_low_close"] == f"{ph}/{pl}/{pcl}" and abs(num(r["open_gap_points"]) - (c.open - pcl)) < 0.006 and abs(num(r["ema200_at_first_candle"]) - c.ema) < 0.006)
        if not ok:
            bad.append(ds)
    record("the 13 disputed dates: first candle OHLC (09:15 start), body and wick percentages, previous-day high / low / official close, opening gap and EMA(200) at the first candle equal an independent recomputation from the raw one-minute data", not bad, 13, failures=bad)

    # ============================================================ 2. predicates: Method 1 level, strength verdicts, trend numbers
    bad = []
    for ds in D13:
        d = date.fromisoformat(ds)
        c, pg = first_candle(d), by_day[prev_of[d]]
        long = c.close >= c.open
        ph, pl = pg.high.max(), pg.low.min()
        lvl = ph if long else pl
        broke = (c.high > lvl and c.close > lvl) if long else (c.low < lvl and c.close < lvl)
        rg = c.high - c.low
        body = abs(c.close - c.open) / rg
        opp = ((c.high - max(c.open, c.close)) if long else (min(c.open, c.close) - c.low)) / rg
        col_ok = (c.close > c.open) if long else (c.close < c.open)
        verdict = {n: bool(col_ok and body >= bmin - EPS and opp <= omax + EPS) for n, bmin, omax in (("STRICT", 0.70, 0.15), ("MODERATE", 0.60, 0.20), ("LOOSE", 0.50, 0.25))}
        m1 = next(r for r in pm if r["date"] == ds and r["direction"] == ("LONG" if long else "SHORT") and r["method"] == "Method 1" and r["predicate"] == "level_broken")
        s = strength[ds]
        ok = (fb(m1["pass"]) == broke and all(fb(s[f"strong_{n}"]) == v for n, v in verdict.items()) and abs(num(s["body_pct"]) - 100 * body) < 0.06 and abs(num(s["opposite_wick_pct"]) - 100 * opp) < 0.06)
        t = trend[ds]
        prev_close_ema = pg.close.iloc[-1] - pg.ema.iloc[-1]
        ok = ok and abs(num(t["prev_close_minus_ema"]) - prev_close_ema) < 0.006 and abs(num(t["first_close_minus_ema"]) - (c.close - c.ema)) < 0.006
        if not ok:
            bad.append(ds)
    record("the 13 dates: the Method 1 'level broken' predicate, the strong-candle verdicts under the STRICT / MODERATE / LOOSE profiles (with the wick against the trade), and the trend numbers (previous close minus its EMA, first close minus the EMA) equal an independent recomputation", not bad, 13, failures=bad)

    # ============================================================ 3. previous-session fractals and the frozen trendline value
    def fractals(g, long):
        key = g.high.to_numpy() if long else g.low.to_numpy()
        out = []
        for j in range(2, len(g) - 2):
            if long and all(key[j] >= key[j - m] and key[j] >= key[j + m] for m in (1, 2)) or (not long and all(key[j] <= key[j - m] and key[j] <= key[j + m] for m in (1, 2))):
                out.append(j)
        return out
    bad = []
    for ds in D13:
        d = date.fromisoformat(ds)
        c, pg = first_candle(d), by_day[prev_of[d]]
        long = c.close >= c.open
        idx = fractals(pg, not long)  # trendline fractals: lows for a long, highs for a short
        t = trend[ds]
        if len(idx) < 2:
            ok = t["trendline_frozen_reason"] == "NO_TRENDLINE"
        else:
            j1, j2 = idx[-2], idx[-1]
            y1, y2 = (pg.low.iloc[j1], pg.low.iloc[j2]) if long else (pg.high.iloc[j1], pg.high.iloc[j2])
            slope = (y2 - y1) / (j2 - j1)
            line = y2 + slope * (len(pg) - j2)
            good = (slope > 0 and c.close > line) if long else (slope < 0 and c.close < line)
            ok = abs(num(t["trendline_value_at_open"]) - line) < 0.006 and fb(t["trendline_frozen_supportive"]) == good
        if not ok:
            bad.append(ds)
    record("the 13 dates: the frozen Method 2 trendline (the last two previous-session k=2 fractal lows / highs; slope, extrapolated value at the open and the 'supportive' verdict) equals an independent recomputation", not bad, 13, failures=bad)

    # ============================================================ 4. level families
    fam = rd(OUT / "orb_level_families_13.csv")
    bad = []
    for r in fam:
        d = date.fromisoformat(r["date"])
        long = r["direction"] == "LONG"
        c = first_candle(d)
        i = days.index(d)
        if r["family"] == "M1_PREVIOUS_DAY_EXTREME":
            want = by_day[prev_of[d]].high.max() if long else by_day[prev_of[d]].low.min()
        elif r["family"].startswith("MS_EXTREME_"):
            n = int(r["family"].split("_")[2])
            sess = pd.concat([by_day[days[i - k]] for k in range(1, n + 1)])
            want = sess.high.max() if long else sess.low.min()
        elif r["family"] == "M2_LATEST_FRACTAL_K2":
            pg = by_day[prev_of[d]]
            ph, pl = pg.high.max(), pg.low.min()
            lv = [pg.high.iloc[j] for j in fractals(pg, True) if pg.high.iloc[j] < ph] if long else [pg.low.iloc[j] for j in fractals(pg, False) if pg.low.iloc[j] > pl]
            want = lv[-1] if lv else None
        else:
            continue
        got = num(r["level"])
        if (want is None) != (got is None) or (want is not None and abs(got - want) > 0.006):
            bad.append((r["date"], r["family"], got, want))
            continue
        if want is not None and fb(r["broken"]) != bool((c.high > want and c.close > want) if long else (c.low < want and c.close < want)):
            bad.append((r["date"], r["family"], "broken"))
    record("the level families on the 13 dates (previous-day extreme, the extreme of the last 2 / 3 / 5 sessions, the frozen latest inner fractal) and whether the first candle broke and closed beyond each equal an independent recomputation", not bad, len(fam), failures=bad)

    # ============================================================ 5. population: previous-day extreme broken by the first candle; Gap readings
    n_m1 = 0
    for d in ev_days:
        if d not in prev_of:
            continue
        c, pg = first_candle(d), by_day[prev_of[d]]
        long = c.close >= c.open
        lvl = pg.high.max() if long else pg.low.min()
        n_m1 += int((c.high > lvl and c.close > lvl) if long else (c.low < lvl and c.close < lvl))
    want = summ["level_family_population"]["M1_PREVIOUS_DAY_EXTREME"]["first_candle_breaks_and_closes_beyond"]
    record("population: the number of sessions on which the colour-direction first candle breaks and closes beyond the previous-day high / low equals an independent count", n_m1 == want, len(ev_days), f"independent {n_m1} vs reported {want}")
    bad = []
    for r in summ.get("gap_reading_differ_cases", []):
        d = date.fromisoformat(r["date"])
        c, pg = first_candle(d), by_day[prev_of[d]]
        long = r["direction"] == "LONG"
        pc = num(daily[r["date"]]["prev_day_official_close"])
        ma, ma_prev = c.ema, pg.ema.iloc[-1]
        prev_wrong = pc < ma_prev if long else pc > ma_prev
        open_beyond = c.open > ma if long else c.open < ma
        closed = c.close > ma if long else c.close < ma
        reaches = (c.low <= ma) if long else (c.high >= ma)
        frozen, alt = prev_wrong and open_beyond and closed, prev_wrong and closed and (open_beyond or reaches)
        if not (alt and not frozen):
            bad.append(r["date"])
    record("the ten cases where the 'open crosses the 200 average' and 'the candle crosses the 200 average' readings of the Gap setup differ really differ (previous close on the wrong side, the candle closes beyond the average, the open does not)", not bad and len(summ.get("gap_reading_differ_cases", [])) == summ["gap_reading_population"]["cases_where_the_readings_differ"], len(summ.get("gap_reading_differ_cases", [])), failures=bad)

    # ============================================================ 6. the manual journal (original workbook) and the engine overlap
    ws = openpyxl.load_workbook(ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx", data_only=True).worksheets[0]
    jr = [r for r in ws.iter_rows(min_row=3, values_only=True) if r[0] is not None and r[1] is not None]
    jorb = {r[1].strftime("%Y-%m-%d") for r in jr if r[3] == "ORB"}
    sat = [r[1].strftime("%Y-%m-%d") for r in jr if r[1].weekday() >= 5]
    sig36 = rd(P36 / "all_strategy_signals.csv")
    orb_dates = {r["date"] for r in sig36 if r["strategy"] == "ORB"}
    in_session = {d for d in jorb if date.fromisoformat(d) in by_day and date.fromisoformat(d) in set(ev_days)}
    j = summ["journal_orb"]
    ok = (len(jr) == summ["journal_rows"] == 190 and len([r for r in jr if r[3] == "ORB"]) == j["rows"] == 89 and len(sat) == len(summ["journal_saturday_rows"]) == 5 and len(in_session & orb_dates) == j["engine_orb_signal_on_journal_orb_date"]
          and len(in_session) - len(in_session & orb_dates) == j["journal_orb_dates_without_engine_orb"] and len(orb_dates - jorb) == j["engine_orb_signal_dates_without_journal_orb"])
    record("the manual journal read from the original workbook: 190 rows, 89 ORB rows, 5 weekend-dated rows; the overlap with the Phase 3.6 ORB signal dates and the counts of ORB journal dates without an engine ORB signal equal an independent recount", ok, len(jr),
           f"in-session ORB journal dates {len(in_session)}; engine overlap {len(in_session & orb_dates)}; engine ORB dates without a journal ORB {len(orb_dates - jorb)}")
    cc = rd(OUT / "orb_journal_cross_check.csv")
    record("the journal cross-check table lists exactly the 89 ORB journal rows once each", len(cc) == 89 and {r["journal_date"] for r in cc} == jorb and len({r["journal_date"] for r in cc}) == 89, len(cc))

    # ============================================================ 7. variant table consistency and the frozen reference
    vi = {r["variant"]: r for r in rd(OUT / "orb_variant_impact.csv")}
    fz = vi["orb-frozen"]
    record("the frozen ORB reference in the variant table has 53 confirmed signals equal to the Phase 3.6 ORB signals, and the frozen engine equals the Phase 3.6 table (summary flag)", int(fz["confirmed_orb_signals"]) == 53 == sum(1 for r in sig36 if r["strategy"] == "ORB") and summ["frozen_orb_equals_phase36_table"] is True, 53)
    loosen = ("orb-var-strength-loose", "orb-var-trendline-none", "orb-var-trendline-any-pair", "orb-var-trend-ema-basic", "orb-var-inner-highest-broken", "orb-var-gap-candle-crossing")
    ok = all(int(vi[k]["removed_vs_frozen"]) == 0 for k in loosen if k != "orb-var-inner-highest-broken") and int(vi["orb-var-strength-strict"]["added_vs_frozen"]) == 0 and int(vi["orb-var-colour"]["added_vs_frozen"]) == 0 and int(vi["orb-var-trend-structure"]["added_vs_frozen"]) == 0 and int(vi["orb-var-gap-candle-crossing"]["removed_vs_frozen"]) == 0
    record("variant table consistency: a single loosened gate removes no frozen signal, the stricter profile / colour / structure variants add none", ok, len(vi))
    record("no variant reproduces more than two of the thirteen disputed dates (each variant loosens or re-defines ONE unresolved construction; combinations were deliberately not searched)", all(int(r["disputed_dates_with_a_signal (of 13)"]) <= 2 for r in vi.values()), len(vi), str({k: r["disputed_dates_with_a_signal (of 13)"] for k, r in vi.items()}))

    # ============================================================ 8. registry vocabulary
    reg = rd(OUT / "orb_source_rule_registry.csv")
    allowed = ("EXPLICIT_DOCUMENT_RULE", "AUTHOR_CLARIFICATION", "OWNER_APPROVED", "CURRENT_ENGINE_ASSUMPTION", "RESEARCH_PROPOSAL", "UNRESOLVED")
    bad = [r["rule_id"] for r in reg if not r["status"].startswith(allowed)]
    mislabel = [r["rule_id"] for r in reg if r["implementation_status"] == "IMPLEMENTED_RESEARCH_VARIANT" and r["status"].startswith("EXPLICIT") and "construction UNRESOLVED" not in r["status"]]
    record("the source-rule registry uses only the six classification labels and never describes an implemented research variant as an explicit document rule", not bad and not mislabel, len(reg), failures=bad + mislabel)

    # ============================================================ 9. charts, daily reports, deliverables, preservation
    need = ["orb_complete_source_audit.md", "orb_source_rule_registry.csv", "orb_13_disputed_dates.csv", "orb_level_reconstruction.md", "orb_candle_strength_review.md", "orb_ema_trendline_review.md", "orb_author_corrections.md", "orb_rule_decision_matrix.md", "independent_audit.md"]
    miss = [n for n in need if not (OUT / n).exists()] + [n for n in ("daily", "charts") if not (OUT / n).is_dir()]
    cd = sorted(p.stem for p in (OUT / "daily").glob("*.md")) if (OUT / "daily").is_dir() else []
    ch = sorted(p.stem for p in (OUT / "charts").glob("*.svg")) if (OUT / "charts").is_dir() else []
    record("every required Phase 5.4 deliverable exists, with one chart-based case study (daily report + SVG chart) for each of the 13 disputed dates", not miss and cd == sorted(D13) and ch == sorted(D13), len(need) + 2 + 26, failures=miss)
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
    record("every file in the Phase 5.4 baseline snapshot (all of src, scripts, tests, docs, data, reports: Phase 3.0-5.3, the frozen strategy files, the historical datasets, the manual journal, the source PDFs) is byte-identical", not changed and not removed, len(snap["hashes"]), failures=changed + removed)
    record("the only files added outside reports/phase5/phase54_orb_audit are the declared Phase 5.4 scripts, tests and new modules", not added, len(now), failures=added)
    fr = json.loads((ROOT / "reports" / "phase4" / "strategy_freeze.json").read_text())
    bad = [p for p, h in fr["active_file_hashes"].items() if sha(ROOT / p) != h]
    record("every file hashed in the Phase 4 freeze (engines incl. ORB, RF, controller, execution, session construction, framework) is unchanged", not bad, len(fr["active_file_hashes"]), fr["frozen_configuration_id"], bad)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=2, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
