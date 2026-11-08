"""Phase 5.6 independent audit (no ``src/`` imports; the raw-data helpers come from the Phase 3.2 audit script, itself free of ``src/``).

* re-reads the ORIGINAL journal workbook and recounts it (190 data rows, 189 in the Summary sheet, 89 ORB rows, five weekend-dated rows, outcome counts, 19 time objects);
* re-implements the staged one-to-one matching (strict -> time tolerant -> date-and-strategy only) from the Phase 5.5 executed-trade table and compares every pair with the delivered tables, per configuration;
* verifies one-to-one use, that every journal row and every trade appears exactly once per configuration, the root-cause vocabulary, the counts of the CSV files against the state file, the outcome-class agreement,
  the ORB evidence measurements (first candle and previous-day high) against the raw one-minute data, the weekend rows, the daily reports / charts and the preservation of the baselines.
Run: .venv/bin/python scripts/phase56_independent_audit.py   ->   reports/phase5/phase56_manual_reconciliation/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
import warnings
from collections import Counter
from pathlib import Path

import openpyxl

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase32_audit as A32  # noqa: E402

OUT = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
JOURNAL = ROOT / "docs" / "trading journal" / "Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"
CAUSES = {"MISSING_STRATEGY_SIGNAL", "DIFFERENT_STRATEGY_SELECTED", "EARLIER_SIGNAL", "LATER_SIGNAL", "LEVEL_CONSTRUCTION_MISMATCH", "CANDLE_STRENGTH_MISMATCH", "EMA_FILTER_MISMATCH", "TRENDLINE_MISMATCH", "OPENING_GAP_MISMATCH",
          "CONFIRMATION_CANDLE_MISMATCH", "PORTFOLIO_CONTROLLER_CONSTRAINT", "ENTRY_TIME_MISMATCH", "EXIT_MANAGEMENT_MISMATCH", "DATA_PROVIDER_DIFFERENCE", "MANUAL_JOURNAL_INCONSISTENCY", "UNRESOLVED_DISCRETIONARY_SELECTION"}
OUTCOME = {"Target": "TARGET", "SL": "INITIAL_FULL_STOP", "BE": "T1_THEN_BUFFER_STOP"}
RES: dict = {"checks": {}}
K = ("A", "B", "C")


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def hm(label: str) -> int:
    return int(label[:2]) * 60 + int(label[3:5])


def read_journal() -> tuple[list[dict], dict, int]:
    """Independent reader: raw cell values only."""
    wb = openpyxl.load_workbook(JOURNAL, data_only=True)
    ws = wb.worksheets[0]
    rows, n_obj = [], 0
    for i, r in enumerate(ws.iter_rows(min_row=1, values_only=True), 1):
        if not isinstance(r[0], int | float) or r[1] is None:
            continue
        t = r[2]
        if hasattr(t, "hour"):
            n_obj += 1
            lab = f"{t.hour:02d}:{t.minute:02d}"
        else:
            lab = str(t).strip()[:5]
        rows.append({"id": int(r[0]), "sheet_row": i, "date": r[1].strftime("%Y-%m-%d"), "dow": r[1].weekday(), "label": lab, "strategy": str(r[3]).strip(), "outcome": str(r[4]).strip()})
    summ = {}
    for r in wb.worksheets[1].iter_rows(values_only=True):
        if r[0] and r[1] is not None and r[0] != "Metric":
            summ[str(r[0])] = r[1]
    return rows, summ, n_obj


def stage_match(rows: list[dict], trades: list[dict]) -> dict[int, tuple[str, str, int]]:
    """{journal id: (stage, trade_id, delta)} with the staged one-to-one rule, written independently (single sort per stage)."""
    um, ut, out = set(), set(), {}
    pool = [r for r in rows if r["dow"] < 5]
    for stage, tol in (("STRICT", 0), ("TIME_TOLERANT", 15), ("DATE_STRATEGY_ONLY", 10**6)):
        cand = []
        for r in pool:
            if r["id"] in um:
                continue
            for t in trades:
                if t["trade_id"] in ut or t["date"] != r["date"] or t["strategy"] != r["strategy"]:
                    continue
                d = hm(t["signal_candle_start"]) - hm(r["label"])
                if abs(d) <= tol:
                    cand.append((abs(d), r["id"], t["trade_id"], d))
        cand.sort()
        for _a, rid, tid, d in cand:
            if rid in um or tid in ut:
                continue
            um.add(rid)
            ut.add(tid)
            out[rid] = (stage, tid, d)
    return out


def main() -> int:  # noqa: C901
    st = json.loads((OUT / "phase56_state.json").read_text())
    trades_all = rd(P55 / "all_executed_trades.csv")
    mt = rd(OUT / "manual_vs_automated_matching.csv")
    rc = rd(OUT / "mismatch_root_causes.csv")
    mo = rd(OUT / "manual_only_trades.csv")
    ao = rd(OUT / "automated_only_trades.csv")
    snap = json.loads((P55 / "before_snapshot.json").read_text())

    # ---------------------------------------------------------------- 1. the journal
    jr, summ, n_obj = read_journal()
    outc = Counter(r["outcome"] for r in jr)
    bys = Counter(r["strategy"] for r in jr)
    wk = [r for r in jr if r["dow"] >= 5]
    two = Counter(r["date"] for r in jr)
    record("journal workbook re-read: 190 data rows (ids 1..190), Summary sheet says 189, 89 ORB rows, outcomes Target 81 / SL 65 / BE 44, five weekend-dated rows (all Saturdays), 19 time objects, five dates with two rows, none with more",
           len(jr) == 190 and [r["id"] for r in jr] == list(range(1, 191)) and str(summ.get("Total trades")) == "189" and bys["ORB"] == 89 and (outc["Target"], outc["SL"], outc["BE"]) == (81, 65, 44) and len(wk) == 5
           and all(r["dow"] == 5 for r in wk) and n_obj == 19 and sum(1 for n in two.values() if n == 2) == 5 and max(two.values()) == 2, 190, f"{dict(bys)} {dict(outc)} weekend={[(r['id'], r['date']) for r in wk]}")
    record("the journal workbook is byte-identical to the Phase 5.5 baseline snapshot", sha(JOURNAL) == snap["hashes"]["docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx"], 1)
    record("the state file's journal facts equal the recount", st["journal"]["rows"] == 190 and st["journal"]["by_strategy"] == dict(bys) and st["journal"]["outcomes"] == dict(outc) and len(st["journal"]["weekend_rows"]) == 5 and st["journal"]["dates_with_two_rows"] == 5, 1)
    raw = A32.load_raw()
    raw["day"] = raw.timestamp.dt.strftime("%Y-%m-%d")
    days = set(raw["day"])
    record("the five weekend-dated rows have NO one-minute data on those dates (not exchange sessions); every weekday journal date is a session of the dataset", all(r["date"] not in days for r in wk) and all(r["date"] in days for r in jr if r["dow"] < 5), len(jr))

    # ---------------------------------------------------------------- 2. independent staged matching, per configuration
    for k in K:
        tr = [t for t in trades_all if t["config"] == k]
        mine = stage_match(jr, tr)
        theirs = {int(r["journal_row"]): (r["match_stage"], r["trade_id"], r["delta_minutes_vs_signal_candle_start"]) for r in mt if r["config"] == k and r["match_stage"] in ("STRICT", "TIME_TOLERANT", "DATE_STRATEGY_ONLY")}
        diff = [(rid, mine.get(rid), theirs.get(rid)) for rid in sorted(set(mine) | set(theirs)) if (mine.get(rid) is None) != (theirs.get(rid) is None) or (mine.get(rid) and (mine[rid][0], mine[rid][1], str(mine[rid][2])) != (theirs[rid][0], theirs[rid][1], str(theirs[rid][2])))]
        c = Counter(v[0] for v in mine.values())
        record(f"configuration {k}: the independent staged one-to-one matching reproduces every delivered pair (stage, trade, time difference)", not diff and len(tr) == st["matching"][k]["automated_trades"], len(mine),
               f"strict {c['STRICT']} / tolerant {c['TIME_TOLERANT']} / date+strategy only {c['DATE_STRATEGY_ONLY']}; state {st['matching'][k]['strict']} / {st['matching'][k]['time_tolerant']} / {st['matching'][k]['date_strategy_only']}", diff)
        rows_k = [r for r in mt if r["config"] == k]
        jids = Counter(r["journal_row"] for r in rows_k if r["journal_row"])
        tids = Counter(r["trade_id"] for r in rows_k if r["trade_id"] and r["journal_row"])
        strong = {r["trade_id"] for r in rows_k if r["journal_row"] and r["match_stage"] in ("STRICT", "TIME_TOLERANT")}
        ao_ids = [a["trade_id"] for a in ao if a["config"] == k]
        miss_tr = [t["trade_id"] for t in tr if t["trade_id"] not in tids and t["trade_id"] not in ao_ids]
        record(f"configuration {k}: one-to-one - every journal row appears exactly once, no trade is used by two journal rows, every executed trade is either in a strict / time-tolerant pair or in the automated-only table (never both; date-and-strategy-only trades are listed in the automated-only table too)",
               len(jids) == 190 and set(jids.values()) <= {1} and set(tids.values()) <= {1} and not miss_tr and not (strong & set(ao_ids)) and len(strong) + len(ao_ids) == len(tr) and len(set(ao_ids)) == len(ao_ids), len(rows_k), failures=miss_tr)
        pair_bad = []
        for r in rows_k:
            if r["trade_id"] and r["match_stage"] in ("STRICT", "TIME_TOLERANT", "DATE_STRATEGY_ONLY"):
                t = next(x for x in tr if x["trade_id"] == r["trade_id"])
                ag = OUTCOME.get(r["manual_outcome"]) == t["outcome"]
                if t["date"] != r["date"] or t["strategy"] != r["manual_strategy"] or str(ag) != r["outcome_class_agrees_descriptive"] or (r["match_stage"] == "STRICT" and r["delta_minutes_vs_signal_candle_start"] != "0") \
                        or (r["match_stage"] == "TIME_TOLERANT" and not 0 < abs(int(r["delta_minutes_vs_signal_candle_start"])) <= 15) or (r["match_stage"] == "DATE_STRATEGY_ONLY" and abs(int(r["delta_minutes_vs_signal_candle_start"])) <= 15):
                    pair_bad.append((r["journal_row"], r["trade_id"]))
        record(f"configuration {k}: every pair has the same date and strategy, the stage agrees with the time difference, and the descriptive outcome-class flag is recomputed correctly", not pair_bad, len(rows_k), failures=pair_bad)
        agree = sum(1 for r in rows_k if r["match_stage"] in ("STRICT", "TIME_TOLERANT") and r["outcome_class_agrees_descriptive"] == "True")
        tot = sum(1 for r in rows_k if r["match_stage"] in ("STRICT", "TIME_TOLERANT"))
        record(f"configuration {k}: outcome-class agreement among strict + time-tolerant pairs recounted", [agree, tot] == [st["matching"][k]["outcome_agreement_matched"]["agree"], st["matching"][k]["outcome_agreement_matched"]["total"]], tot, f"{agree}/{tot}")

    # ---------------------------------------------------------------- 3. weekend rows and files
    wk_bad = [(r["config"], r["journal_row"]) for r in mt if r["date"] in {x["date"] for x in wk} and (r["match_stage"] in ("STRICT", "TIME_TOLERANT", "DATE_STRATEGY_ONLY") or r["journal_flags"] == "")]
    wk_cause = [r for r in rc if r["date"] in {x["date"] for x in wk} and r["side"] == "MANUAL_ONLY"]
    record("the weekend rows are never matched, keep their original dates, carry the weekend flag and the cause MANUAL_JOURNAL_INCONSISTENCY in all three configurations", not wk_bad and len(wk_cause) == 15 and all(r["root_cause_primary"] == "MANUAL_JOURNAL_INCONSISTENCY" for r in wk_cause), 15, failures=wk_bad)
    jmap = {str(r["id"]): r for r in jr}
    alt = [(r["config"], r["journal_row"]) for r in mt if r["journal_row"] and (jmap[r["journal_row"]]["date"], jmap[r["journal_row"]]["label"], jmap[r["journal_row"]]["strategy"], jmap[r["journal_row"]]["outcome"]) != (r["date"], r["manual_time_label"], r["manual_strategy"], r["manual_outcome"])]
    record("every delivered journal row equals the original workbook row (date, label, strategy, outcome): nothing was altered, relabelled or invented", not alt, len(mt), failures=alt)
    bad_vocab = [(r["config"], r["journal_row"] or r["trade_id"], r["root_cause_primary"]) for r in rc if r["root_cause_primary"] not in CAUSES or (r["root_cause_secondary"] and r["root_cause_secondary"] not in CAUSES)]
    nocause = [(r["config"], r["journal_row"], r["trade_id"]) for r in rc if not r["evidence"].strip()]
    record("every classified mismatch uses only the specified root-cause vocabulary and carries evidence text", not bad_vocab and not nocause and len(rc) > 0, len(rc), failures=bad_vocab + nocause)
    exp_rc = {k: (sum(1 for r in mt if r["config"] == k and r["match_stage"] not in ("STRICT", "TIME_TOLERANT") and r["journal_row"]) + sum(1 for r in mt if r["config"] == k and r["match_stage"] in ("STRICT", "TIME_TOLERANT") and r["outcome_class_agrees_descriptive"] != "True")
              + sum(1 for a in ao if a["config"] == k)) for k in K}
    got_rc = {k: sum(1 for r in rc if r["config"] == k) for k in K}
    record("the classified-mismatch table covers every manual row without a strict / time-tolerant match, every matched pair with a different exit class and every automated-only trade", exp_rc == got_rc, sum(got_rc.values()), f"expected {exp_rc} got {got_rc}")
    cnt_ok = all(sum(1 for r in mo if r["config"] == k) == st["matching"][k]["manual_rows_unmatched_total"] and sum(1 for r in ao if r["config"] == k) == st["matching"][k]["automated_unmatched_total"] for k in K)
    record("manual_only / automated_only table sizes equal the state counts per configuration", cnt_ok, 6)

    # ---------------------------------------------------------------- 4. ORB evidence versus the raw candles
    fc = A32.five_minute(raw.drop(columns=["day"]), A32.standard_days(raw))
    fc["d"] = fc["start"].dt.strftime("%Y-%m-%d")
    first = {d: g.iloc[0] for d, g in fc.groupby("d") if g.iloc[0]["start"].strftime("%H:%M") == "09:15"}
    sess = sorted(days)
    hi_by = raw.groupby("day")["high"].max().to_dict()
    pat = re.compile(r"first candle (\w+) O([\d.]+) H([\d.]+) L([\d.]+) C([\d.]+)")
    bad, n_ev, n_pd = [], 0, 0
    for r in mo:
        if r["manual_strategy"] != "ORB" or "first candle" not in r["evidence"]:
            continue
        m = pat.search(r["evidence"])
        c = first.get(r["date"])
        if not m or c is None:
            bad.append((r["config"], r["journal_row"], "no match"))
            continue
        n_ev += 1
        colour = "GREEN" if c["close"] >= c["open"] else "RED"
        o, h, low, cl = (float(x) for x in m.groups()[1:])
        if m.group(1) != colour or max(abs(o - c["open"]), abs(h - c["high"]), abs(low - c["low"]), abs(cl - c["close"])) > 0.011:
            bad.append((r["config"], r["journal_row"], "ohlc"))
        pm = re.search(r"previous-day high ([\d.]+)", r["evidence"])
        if pm:
            n_pd += 1
            prev = sess[sess.index(r["date"]) - 1]
            if abs(float(pm.group(1)) - hi_by[prev]) > 0.011:
                bad.append((r["config"], r["journal_row"], "prev-high"))
    record("ORB evidence: the first 09:15 candle (colour, open, high, low, close) and the previous-day high quoted in every manual-only ORB explanation equal the values recomputed from the raw one-minute data", not bad and n_ev > 0, n_ev, f"{n_pd} previous-day highs checked", bad)

    # ---------------------------------------------------------------- 5. strategy-level counts and files
    wrong = rd(OUT / "wrong_strategy_dates.csv")
    exp_w = {k: 0 for k in K}
    for k in K:
        tr = [t for t in trades_all if t["config"] == k]
        for d in sorted({r["date"] for r in jr if r["dow"] < 5}):
            ms = {r["strategy"] for r in jr if r["date"] == d and r["dow"] < 5}
            ats = {t["strategy"] for t in tr if t["date"] == d}
            if ms and ats and ms.isdisjoint(ats):
                exp_w[k] += 1
    got_w = {k: len({r["date"] for r in wrong if r["config"] == k}) for k in K}
    record("dates on which the journal and the automated system traded only DIFFERENT strategies (no weekday journal strategy of the date appears among its automated trades) recounted per configuration", all(got_w[k] == st["matching"][k]["wrong_strategy_dates"] for k in K) and exp_w == got_w, 3, f"delivered {got_w}; independent count {exp_w}")
    nt = {k: Counter(t["date"] for t in trades_all if t["config"] == k) for k in K}
    exp_idle = {k: sum(1 for r in jr if r["dow"] < 5 and nt[k][r["date"]] == 0) for k in K}
    got_idle = {k: st["matching"][k]["manual_rows_on_dates_with_no_automated_trade"] for k in K}
    idle_unmatched = all(r["match_stage"] == "UNMATCHED_MANUAL" for r in mt if r["journal_row"] and nt[r["config"]][r["date"]] == 0 and jmap[r["journal_row"]]["dow"] < 5)
    record("weekday journal rows on sessions with NO automated trade recounted per configuration (equals the state field; all of them are unmatched)", exp_idle == got_idle and idle_unmatched and any(exp_idle.values()), 3, f"independent {exp_idle}; state {got_idle}")
    sec_trades = [(a["config"], a["trade_id"]) for a in ao if a["trade_id"][9:10] == "2"]
    bad2 = [(a["config"], a["trade_id"]) for a in ao if a["trade_id"][9:10] == "2" and ("first valid signal" in a["evidence"] or a["root_cause_primary"] != "PORTFOLIO_CONTROLLER_CONSTRAINT")]
    record("second trades without a journal counterpart are explained as controller re-entries after a full stop (never as first valid signals)", not bad2, len(sec_trades), failures=bad2)
    n_daily = len(list((OUT / "daily").glob("*.md")))
    n_chart = len(list((OUT / "charts").glob("*.svg")))
    record("247 session explanations and the charts exist; each chart is a well-formed SVG", n_daily == st["daily_reports"] == 247 and n_chart == st["charts"] and all(p.read_text().startswith("<svg") for p in (OUT / "charts").glob("*.svg")), n_daily, f"{n_chart} charts")
    need = ["README.md", "manual_journal_source_audit.md", "manual_vs_automated_matching.csv", "strict_matches.csv", "time_tolerant_matches.csv", "manual_only_trades.csv", "automated_only_trades.csv", "wrong_strategy_dates.csv", "orb_unmatched_dates.csv", "irf_unmatched_dates.csv",
            "pdr_pds_unmatched_dates.csv", "mismatch_root_causes.csv", "cross_configuration_reconciliation.md", "handwritten_author_corrections_comparison.csv", "independent_audit.md", "Manual_vs_Automated_Trading_Audit.xlsx"]
    missing = [n for n in need if not (OUT / n).exists() and n != "independent_audit.md"]
    record("the Phase 5.6 deliverables exist (independent_audit.md is written after this audit)", not missing, len(need), failures=missing)

    # ---------------------------------------------------------------- 6. baselines preserved
    changed = [k for k, h in snap["hashes"].items() if not (ROOT / k).exists() or sha(ROOT / k) != h]
    record("every file of the Phase 5.5 baseline snapshot is still byte-identical (journal, candles, source code, earlier reports)", not changed, len(snap["hashes"]), failures=changed)

    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=1, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
