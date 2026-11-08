"""Phase 5.7 independent audit of the visualization layer (no ``src/`` imports).

Parses every rendered SVG (visible text, ``data-*`` attributes, embedded metadata and the geometry of the price lines and markers) and compares it with the verified ledgers (Phase 5.5 all_executed_trades.csv / all_trade_legs.csv) and with the Phase 5.6
matching files; recomputes the exact / time-tolerant / date-and-strategy-only counts with the independent staged matcher of ``phase56_independent_audit.py`` from the original journal workbook; checks file names, subset folders, the workbook, the
summary numbers and that no earlier result changed.
Run: .venv/bin/python scripts/phase57_independent_audit.py   ->   reports/phase5/phase57_trade_visualization/independent_audit_results.json
"""

from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import phase56_independent_audit as A56  # noqa: E402  (a script with no src imports; read_journal / stage_match are its independent implementations)

OUT = ROOT / "reports" / "phase5" / "phase57_trade_visualization"
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P56 = ROOT / "reports" / "phase5" / "phase56_manual_reconciliation"
K = ("A", "B", "C")
RES: dict = {"checks": {}}
SUBSETS = ("charts_all", "charts_exact_matches", "charts_time_tolerant", "charts_automated_only", "charts_date_strategy_only", "charts_orb_focus", "charts_handwritten_dates", "charts_config_differences")
STATUS = {"STRICT": "EXACT_MATCH", "TIME_TOLERANT": "TIME_TOLERANT_MATCH", "DATE_STRATEGY_ONLY": "DATE_STRATEGY_ONLY"}
NS = "{http://www.w3.org/2000/svg}"
EPS_Y = 0.15  # pixels (coordinates are written with one decimal)


def record(name: str, ok: bool, n: int, detail: str = "", failures: list | None = None) -> None:
    RES["checks"][name] = {"pass": bool(ok), "n": n, "detail": detail, "failures": (failures or [])[:12], "n_failures": len(failures or [])}
    print(f"{'PASS' if ok else 'FAIL'}  {name}  (n={n}) {detail}" + (f"  first failures: {(failures or [])[:3]}" if failures else ""), flush=True)


def rd(p: Path) -> list[dict]:
    with open(p, newline="") as f:
        return list(csv.DictReader(f))


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def num(s: str) -> float:
    return float(str(s).replace(",", ""))


def money(v: float) -> str:
    return f"{v:,.2f}"


def main() -> int:  # noqa: C901
    trades = rd(P55 / "all_executed_trades.csv")
    legs = rd(P55 / "all_trade_legs.csv")
    mt = rd(P56 / "manual_vs_automated_matching.csv")
    st56 = json.loads((P56 / "phase56_state.json").read_text())
    index = rd(OUT / "all_executed_trades_visual_index.csv")
    legs_by: dict = {}
    for g in legs:
        legs_by.setdefault((g["config"], g["trade_id"]), {})[g["leg"]] = g
    mt_trade = {(r["config"], r["trade_id"]): r for r in mt if r["trade_id"]}

    # ---------------------------------------------------------------- 1. file names and one chart per executed trade
    files = sorted((OUT / "charts_all").glob("*.svg"))
    want = {f"{t['config']}_{t['trade_id']}.svg" for t in trades}
    have = {p.name for p in files}
    record("charts_all holds exactly one chart per executed trade of A, B and C, named <configuration>_<trade id>.svg (574 trades)", have == want and len(files) == len(trades) == 574, len(files), failures=sorted(want ^ have))

    # ---------------------------------------------------------------- 2. every chart against the ledger
    bad_meta, bad_text, bad_geo, bad_badge, bad_xml = [], [], [], [], []
    by_status: dict = {}
    n_geo = 0
    for t in trades:
        cfg, tid = t["config"], t["trade_id"]
        p = OUT / "charts_all" / f"{cfg}_{tid}.svg"
        try:
            root = ET.fromstring(p.read_text())
        except ET.ParseError as e:
            bad_xml.append((p.name, str(e)))
            continue
        meta = json.loads(root.find(f"{NS}metadata").text)
        lg = legs_by[(cfg, tid)]
        l1, l2 = lg["1"], lg["2"]
        t1_hit = l1["exit_reason"] == "TARGET_1"
        exp = {"config": cfg, "trade_id": tid, "date": t["date"], "strategy": t["strategy"], "method": t["method"], "direction": t["direction"], "entry_ts": t["fill_timestamp"], "entry": num(t["entry_price"]), "stop": num(t["initial_stop"]),
               "t1": num(t["target_1"]), "t2": num(t["target_2"]), "post_t1": num(t["post_t1_stop"]) if t1_hit else None, "gross_pnl_rs": num(t["gross_pnl_rs"]), "outcome": t["outcome"]}
        diffs = [k for k, v in exp.items() if (abs(meta[k] - v) > 1e-9 if isinstance(v, float) and meta.get(k) is not None else meta.get(k) != v)]
        same = l1["exit_time"] == l2["exit_time"] and l1["exit_price"] == l2["exit_price"] and l1["exit_reason"] == l2["exit_reason"] and l1["exit_reason"] in ("ORIGINAL_STOP_BEFORE_T1", "FORCED_EXIT_1514_OPEN_PROVISIONAL")
        exp_exits = [("FULL", l1["exit_reason"], l1["exit_time"][:16], num(l1["exit_price"]))] if same else [("1", l1["exit_reason"], l1["exit_time"][:16], num(l1["exit_price"])), ("2", l2["exit_reason"], l2["exit_time"][:16], num(l2["exit_price"]))]
        got_exits = [(e["leg"], e["reason"], e["ts"], e["price"]) for e in meta["exits"]]
        if got_exits != exp_exits:
            diffs.append("exits")
        # match label against the verified Phase 5.6 file
        r56 = mt_trade.get((cfg, tid))
        exp_status = STATUS.get(r56["match_stage"], "AUTOMATED_ONLY") if r56 else "AUTOMATED_ONLY"
        exp_row = r56["journal_row"] if r56 and r56["match_stage"] in STATUS else None
        if meta["match_status"] != exp_status or meta["journal_row"] != exp_row:
            diffs.append("match")
        by_status[(cfg, exp_status)] = by_status.get((cfg, exp_status), 0) + 1
        if diffs:
            bad_meta.append((cfg, tid, diffs))
        # visible text
        texts = {}
        for el in root.iter(f"{NS}text"):
            k = el.get("data-kind")
            if k:
                texts.setdefault(k, []).append("".join(el.itertext()))
            else:
                texts.setdefault("_plain", []).append("".join(el.itertext()))
        probs = []
        if texts.get("ENTRY_LABEL") != [f"ENTRY {t['fill_timestamp'][-5:]} @ {money(exp['entry'])}"]:
            probs.append(("entry label", texts.get("ENTRY_LABEL")))
        for kind, label, val in (("SL", "SL", exp["stop"]), ("T1", "T1", exp["t1"]), ("T2", "T2", exp["t2"]), ("ENTRY", "ENTRY", exp["entry"])):
            if texts.get(f"LABEL_{kind}") != [f"{label} @ {money(val)}"]:
                probs.append((label, texts.get(f"LABEL_{kind}")))
        if t1_hit:
            if texts.get("LABEL_POST_T1_STOP") != [f"POST-T1 STOP @ {money(exp['post_t1'])}"]:
                probs.append(("post-T1 label", texts.get("LABEL_POST_T1_STOP")))
        elif "LABEL_POST_T1_STOP" in texts:
            probs.append(("post-T1 stop drawn although Target 1 was not hit", texts["LABEL_POST_T1_STOP"]))
        for leg, reason, ts, px in exp_exits:
            lab = (texts.get(f"EXIT_LABEL_{leg}") or [""])[0]
            if f"{ts[-5:]} @ {money(px)}" not in lab or not lab.startswith({"FULL": ("FORCED EXIT" if reason.startswith("FORCED") else "FULL EXIT"), "1": "LEG1 EXIT", "2": "LEG2 EXIT"}[leg]):
                probs.append((f"exit {leg}", lab))
        if len(texts.get("EXIT_LABEL_1", [])) + len(texts.get("EXIT_LABEL_2", [])) + len(texts.get("EXIT_LABEL_FULL", [])) != len(exp_exits):
            probs.append(("exit label count", None))
        head = " ".join(texts["_plain"][:8])
        if tid not in head or f"Configuration {'A - frozen' if cfg == 'A' else ('B - Phase 5.3' if cfg == 'B' else 'C - B')}" not in head or exp_status not in texts["_plain"][4:7] + [head]:
            if tid not in head or exp_status not in head:
                bad_badge.append((cfg, tid))
        if probs:
            bad_text.append((cfg, tid, probs))
        # geometry: every price line / marker sits at the y that the embedded scale assigns to its price
        sc = meta["scale"]
        top, bot, lo, hi = sc["plot_top"], sc["plot_bottom"], sc["price_low"], sc["price_high"]

        def price_of(y: float, top=top, bot=bot, lo=lo, hi=hi) -> float:
            return hi - (y - top) / (bot - top) * (hi - lo)
        for el in root.iter():
            k, pr = el.get("data-kind"), el.get("data-price")
            if pr is None or el.tag == f"{NS}text":
                continue
            if el.tag == f"{NS}line":
                y = float(el.get("y1"))
            elif el.tag == f"{NS}circle":
                y = float(el.get("cy"))
            elif el.tag == f"{NS}rect":
                y = float(el.get("y")) + float(el.get("height")) / 2
            elif el.tag == f"{NS}polygon":
                y = float(el.get("points").split()[0].split(",")[1])
            else:
                continue
            n_geo += 1
            # one pixel of vertical resolution equals (hi - lo) / (bot - top) price units
            if abs(price_of(y) - float(pr)) > (hi - lo) / (bot - top) * 0.1 + 1e-6:
                bad_geo.append((cfg, tid, k, pr, round(price_of(y), 3)))
    record("every chart parses as well-formed SVG", not bad_xml, len(trades), failures=bad_xml)
    record("every chart's embedded data equals the ledger / config: entry price and time, initial stop, T1, T2, post-T1 stop (present only when T1 was booked), exits (leg, reason, time, price), outcome, gross P&L, strategy, method, direction", not bad_meta, len(trades), failures=bad_meta)
    record("every VISIBLE label equals the ledger: 'ENTRY hh:mm @ price', 'SL @', 'T1 @', 'T2 @', 'POST-T1 STOP @' (only after T1), and each leg / full / forced exit label with its time and price", not bad_text, len(trades), failures=bad_text)
    record("every drawn price line and marker (entry, SL, T1, T2, post-T1 stop, exits) sits at the vertical position that its price has on the chart's own scale", not bad_geo and n_geo > 3000, n_geo, failures=bad_geo)
    record("every chart's header names the trade, the configuration and the match status", not bad_badge, len(trades), failures=bad_badge)

    # ---------------------------------------------------------------- 3. match labels and counts against Phase 5.6 and the independent matcher
    jr, _summ, _n = A56.read_journal()
    ok_counts, detail, fails = True, [], []
    for k in K:
        tr = [t for t in trades if t["config"] == k]
        mine = A56.stage_match(jr, tr)
        c = Counter(v[0] for v in mine.values())
        stt = st56["matching"][k]
        chart_c = Counter(s for (cfg, s), n in by_status.items() if cfg == k for _ in range(n))
        row = (c["STRICT"], c["TIME_TOLERANT"], c["DATE_STRATEGY_ONLY"])
        ok = row == (stt["strict"], stt["time_tolerant"], stt["date_strategy_only"]) == (chart_c["EXACT_MATCH"], chart_c["TIME_TOLERANT_MATCH"], chart_c["DATE_STRATEGY_ONLY"]) and chart_c["AUTOMATED_ONLY"] == stt["automated_no_manual_counterpart"]
        ok_counts &= ok
        detail.append(f"{k}: strict {row[0]} / tolerant {row[1]} / date-only {row[2]} / automated-only {chart_c['AUTOMATED_ONLY']}")
        if not ok:
            fails.append((k, row, (stt["strict"], stt["time_tolerant"], stt["date_strategy_only"]), dict(chart_c)))
    record("the exact / time-tolerant / date-and-strategy-only / automated-only counts shown on the charts equal the Phase 5.6 reconciliation AND the independent staged matcher recomputed from the original journal workbook", ok_counts, 3, "; ".join(detail), fails)
    summ = rd(OUT / "exact_match_summary.csv")
    bad = []
    for r in summ:
        k = r["config"]
        stt = st56["matching"][k]
        n_tr = sum(1 for t in trades if t["config"] == k)
        counted = int(r["strict"]) + int(r["time_tolerant"])
        exp = {"automated_trades": n_tr, "strict": stt["strict"], "time_tolerant": stt["time_tolerant"], "date_strategy_only": stt["date_strategy_only"], "counted_matches": stt["strict"] + stt["time_tolerant"], "manual_only_rows_no_counted_match": stt["manual_rows_unmatched_total"],
               "manual_only_rows_without_any_same_date_strategy_trade": stt["manual_rows_no_trade_same_date_strategy"], "automated_only_trades_no_same_date_strategy_row": stt["automated_no_manual_counterpart"], "automated_trades_without_counted_match": stt["automated_unmatched_total"],
               "counted_same_outcome": stt["outcome_agreement_matched"]["agree"], "counted_different_outcome": stt["outcome_agreement_matched"]["total"] - stt["outcome_agreement_matched"]["agree"]}
        for key, v in exp.items():
            if int(r[key]) != v:
                bad.append((k, key, r[key], v))
        if abs(float(r["strict_pct_of_automated_trades"]) - round(100 * stt["strict"] / n_tr, 2)) > 0.005 or abs(float(r["strict_pct_of_190_journal_rows"]) - round(100 * stt["strict"] / 190, 2)) > 0.005:
            bad.append((k, "percentages"))
        if sum(int(r[f"strict_{s}"]) for s in ("IRF", "ORB", "PDR", "PDS", "RF")) != stt["strict"] or counted != stt["strict"] + stt["time_tolerant"]:
            bad.append((k, "by strategy"))
        for s, v in stt["strict_by_strategy"].items():
            if int(r[f"strict_{s}"]) != v:
                bad.append((k, f"strict_{s}", r[f"strict_{s}"], v))
    record("exact_match_summary.csv equals the Phase 5.6 state file (counts, outcome agreement, strict by strategy, both percentages)", not bad and len(summ) == 3, len(summ), failures=bad)

    # ---------------------------------------------------------------- 4. subset folders
    sub_bad = []
    exp_members = {s: set() for s in SUBSETS}
    hw = {r["date"] for r in rd(P56 / "handwritten_author_corrections_comparison.csv") if r["date"][:2] == "20"}
    keyed = {(t["config"], t["trade_id"]): (t["method"], t["direction"], t["signal_candle_start"], t["entry_price"], t["outcome"], t["gross_pnl_rs"]) for t in trades}
    for t in trades:
        cfg, tid = t["config"], t["trade_id"]
        nm = f"{cfg}_{tid}.svg"
        r56 = mt_trade.get((cfg, tid))
        stt = STATUS.get(r56["match_stage"], "AUTOMATED_ONLY") if r56 else "AUTOMATED_ONLY"
        exp_members["charts_all"].add(nm)
        exp_members[{"EXACT_MATCH": "charts_exact_matches", "TIME_TOLERANT_MATCH": "charts_time_tolerant", "AUTOMATED_ONLY": "charts_automated_only", "DATE_STRATEGY_ONLY": "charts_date_strategy_only"}[stt]].add(nm)
        if t["strategy"] == "ORB":
            exp_members["charts_orb_focus"].add(nm)
        if t["date"] in hw:
            exp_members["charts_handwritten_dates"].add(nm)
        if len({keyed.get((c, tid)) for c in K}) > 1:
            exp_members["charts_config_differences"].add(nm)
    for s in SUBSETS:
        got = {p.name for p in (OUT / s).glob("*.svg")}
        trade_files = {g for g in got if not g.startswith("DAY_")}
        if trade_files != exp_members[s]:
            sub_bad.append((s, "members differ", len(trade_files), len(exp_members[s])))
        for g in trade_files:
            if (OUT / s / g).read_bytes() != (OUT / "charts_all" / g).read_bytes():
                sub_bad.append((s, g, "differs from charts_all"))
    record("every subset folder (exact, time-tolerant, automated-only, date-and-strategy-only, ORB focus, handwritten dates, configuration differences) holds exactly the trades its definition selects, byte-identical to charts_all", not sub_bad, len(SUBSETS), failures=sub_bad)
    cnt = {s: len(list((OUT / s).glob("*.svg"))) for s in SUBSETS}
    record("folder sizes: exact = strict total, time-tolerant = tolerant total, automated-only = Phase 5.6 automated-only total, date-only = date-and-strategy total", cnt["charts_exact_matches"] == sum(st56["matching"][k]["strict"] for k in K) and cnt["charts_time_tolerant"] == sum(st56["matching"][k]["time_tolerant"] for k in K)
           and cnt["charts_automated_only"] == sum(st56["matching"][k]["automated_no_manual_counterpart"] for k in K) and cnt["charts_date_strategy_only"] == sum(st56["matching"][k]["date_strategy_only"] for k in K), 4, str(cnt))
    # journal-day charts: the ORB rows without a counted match
    mo = rd(P56 / "manual_only_trades.csv")
    orb_dates = sorted({r["date"] for r in mo if r["manual_strategy"] == "ORB" and "WEEKEND" not in r["journal_flags"]})
    day_have = sorted(p.name[4:14] for p in (OUT / "charts_orb_focus").glob("DAY_*_ORB.svg"))
    record("a journal-day chart exists for every ORB journal date without a counted match (weekend rows excluded; they have no market data)", day_have == orb_dates, len(orb_dates), failures=sorted(set(day_have) ^ set(orb_dates)))

    # ---------------------------------------------------------------- 5. index and workbook
    bad = [i["chart_file"] for i in index if not (OUT / i["chart_file"]).exists()]
    idx_status = Counter((i["config"], i["match_status"]) for i in index)
    record("the visual index lists all 574 trades with an existing chart file and the same match-status counts as the charts", len(index) == 574 and not bad and idx_status == Counter(by_status), len(index), failures=bad)
    import openpyxl
    wb = openpyxl.load_workbook(OUT / "Phase57_Trade_Verification.xlsx", read_only=True, data_only=True)
    ws = list(wb["All executed trades"].iter_rows(values_only=True))
    head = ws[0]
    pos = {h: i for i, h in enumerate(head)}
    led = {(t["config"], t["trade_id"]): t for t in trades}
    bad = []
    for r in ws[1:]:
        t = led[(r[pos["configuration"]], r[pos["trade_id"]])]
        lg = legs_by[(t["config"], t["trade_id"])]
        if (abs(r[pos["entry_price"]] - num(t["entry_price"])) > 1e-9 or abs(r[pos["stop_loss"]] - num(t["initial_stop"])) > 1e-9 or abs(r[pos["T1"]] - num(t["target_1"])) > 1e-9 or abs(r[pos["T2"]] - num(t["target_2"])) > 1e-9
                or abs(r[pos["leg1_exit_price"]] - num(lg["1"]["exit_price"])) > 1e-9 or abs(r[pos["leg2_exit_price"]] - num(lg["2"]["exit_price"])) > 1e-9 or abs(r[pos["gross_synthetic_pnl_rs"]] - num(t["gross_pnl_rs"])) > 1e-9
                or r[pos["leg1_exit_reason"]] != lg["1"]["exit_reason"] or r[pos["leg2_exit_reason"]] != lg["2"]["exit_reason"] or r[pos["automated_exit_class"]] != t["outcome"] or not (OUT / r[pos["chart_file"]]).exists()):
            bad.append((t["config"], t["trade_id"]))
    record("the verification workbook's trade sheet equals the ledger (entry, stop, T1, T2, both exits, reasons, gross P&L, exit class) and links to an existing chart", len(ws) - 1 == 574 and not bad, len(ws) - 1, failures=bad)
    n_exact = sum(1 for r in ws[1:] if r[pos["journal_match_type"]] == "EXACT_MATCH")
    n_sheet = len(list(wb["Exact matches only"].iter_rows(values_only=True))) - 1
    record("the 'Exact matches only' sheet has exactly the strict matches of A + B + C", n_exact == n_sheet == sum(st56["matching"][k]["strict"] for k in K), n_sheet)
    wb.close()

    # ---------------------------------------------------------------- 6. earlier results untouched, nothing but new files added
    before = json.loads((OUT / "before_hashes.json").read_text())
    changed = [k for k, h in before.items() if not (ROOT / k).exists() or sha(ROOT / k) != h]
    record("every file of the Phase 3.6, 5.5 and 5.6 report folders is byte-identical to its hash recorded before the first Phase 5.7 write (no earlier chart, ledger or report was overwritten)", not changed, len(before), failures=changed)
    out = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, text=True, check=True).stdout.splitlines()
    modified = [ln for ln in out if ln[:2].strip() in ("M", "MM", "D", "R") and ".DS_Store" not in ln]
    record("no tracked file is modified or deleted (git status shows only new files; nothing committed)", not modified, len(out), failures=modified)
    RES["all_pass"] = all(v["pass"] for v in RES["checks"].values())
    (OUT / "independent_audit_results.json").write_text(json.dumps(RES, indent=1, default=str))
    print("ALL PASS" if RES["all_pass"] else "FAILURES PRESENT")
    return 0 if RES["all_pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
