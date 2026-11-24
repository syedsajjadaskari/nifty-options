"""Phase 7.0 driver: IRF V3 complete rebuild. Stage 1 computes and writes CSV/JSON; later stages write charts, daily files, documents and the workbook.
Usage: python scripts/phase70_run.py [compute|charts|all]
Research only: no order is placed, no existing strategy, dataset, journal or paper-trading configuration is touched."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from collections import Counter
from datetime import date
from pathlib import Path

import pandas as pd

from nifty_trading.research.irf_v3 import audit as AU
from nifty_trading.research.irf_v3 import backtest as BT
from nifty_trading.research.irf_v3 import data_access as DA
from nifty_trading.research.irf_v3 import examples as EXM
from nifty_trading.research.irf_v3 import recon as RC
from nifty_trading.research.irf_v3 import reporting as RP
from nifty_trading.research.irf_v3.config import RULES, SCENARIOS, SENSITIVITY, WINDOWS
from nifty_trading.research.irf_v3.method1 import run_method1
from nifty_trading.research.irf_v3.method2 import run_method2
from nifty_trading.research.irf_v3.models import M1, M2
from nifty_trading.research.irf_v3.signal_engine import overlap_class

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "reports/phase7/phase70_complete_irf_rebuild"
CACHE = OUT / "_state"
PROT = ["src/nifty_trading/strategies", "src/nifty_trading/research/orb_v2", "src/nifty_trading/broker", "src/nifty_trading/core", "src/nifty_trading/config", "data/processed", "data/phase4",
        "data/metadata", "docs/trading journal", "reports/phase6/PHASE61_63_FINAL_RESEARCH_REPORT.md", "reports/phase6/phase62_combined_backtest", "reports/phase5/phase55_combined_backtest"]


def sha_tree(rel: str) -> str:
    p = ROOT / rel
    files = [p] if p.is_file() else sorted(x for x in p.rglob("*") if x.is_file() and "__pycache__" not in x.parts)
    h = hashlib.sha256()
    for f in files:
        h.update(str(f.relative_to(ROOT)).encode())
        h.update(hashlib.sha256(f.read_bytes()).digest())
    return f"{len(files)} files {h.hexdigest()}"


def git(*a) -> str:
    return subprocess.run(["git", *a], cwd=ROOT, capture_output=True, text=True, check=False).stdout


def snapshot() -> dict:
    return {"hashes": {r: sha_tree(r) for r in PROT}, "git_tracked_modifications": git("diff", "--name-only").split(), "git_untracked": git("ls-files", "--others", "--exclude-standard").split(),
            "head": git("rev-parse", "HEAD").strip()}


def write_csv(df: pd.DataFrame, name: str) -> None:
    df.to_csv(OUT / name, index=False)


def compute() -> dict:
    OUT.mkdir(parents=True, exist_ok=True)
    CACHE.mkdir(exist_ok=True)
    before = CACHE / "before_snapshot.json"
    if not before.exists():
        before.write_text(json.dumps(snapshot(), indent=1))
    datasets = {w: DA.load_dataset(w) for w in "AB"}
    scen = {**SCENARIOS, **SENSITIVITY}
    evals = {(w, sid): BT.run_dataset(datasets[w], cfg) for w in "AB" for sid, cfg in scen.items()}
    red_variant = {w: BT.run_dataset(datasets[w], SCENARIOS["SL40_T60"], m2_red_breakout_counts=True) for w in "AB"}
    # ---- rule registry
    write_csv(pd.DataFrame(RULES, columns=["rule_id", "method", "rule", "source_pdf", "page", "authority", "implemented_as"]), "rule_authority_registry.csv")
    # ---- signals ledgers
    sig = {"M1": [], "M2": [], "COMB": []}
    for w in "AB":
        for ev in evals[(w, "SL40_T60")]:
            for m, k in ((M1, "M1"), (M2, "M2")):
                r = RP.signal_row(w, ev, m)
                if r:
                    sig[k].append(r)
                    sig["COMB"].append(r)
    write_csv(pd.DataFrame(sig["M1"]), "method1_signals.csv")
    write_csv(pd.DataFrame(sig["M2"]), "method2_signals.csv")
    write_csv(pd.DataFrame(sig["COMB"]).sort_values(["window", "date", "signal_timestamp", "method"]), "combined_irf_signals.csv")
    # ---- backtests
    perf, tr_rows, monthly, annual, grids = [], {"M1": [], "M2": [], "COMBINED": []}, [], [], []
    sens_rows = []
    for w in "AB":
        nsess = sum(1 for e in evals[(w, "SL40_T60")] if e.session.evaluable)
        nsig = {"M1": sum(1 for e in evals[(w, "SL40_T60")] if e.traces[M1].status == "SIGNAL"), "M2": sum(1 for e in evals[(w, "SL40_T60")] if e.traces[M2].status == "SIGNAL")}
        nsig["COMBINED"] = sum(1 for e in evals[(w, "SL40_T60")] if e.combined.get("selected_method"))
        for sid, cfg in scen.items():
            b = BT.books(w, cfg, evals[(w, sid)])
            for book, rows in b.items():
                m = BT.metrics(rows, nsess, nsig[book] if sid in SCENARIOS else None)
                perf.append({"window": w, "window_dates": f"{WINDOWS[w][0]}..{WINDOWS[w][1]}", "scenario": sid, "kind": "HEADLINE_SCENARIO" if sid in SCENARIOS else "SENSITIVITY", "book": book, **m})
                if sid in SCENARIOS:
                    tr_rows[book].extend(rows)
                    for _, r in BT.monthly(rows).iterrows():
                        monthly.append({"window": w, "scenario": sid, "book": book, **r.to_dict()})
                    for _, r in BT.annual(rows).iterrows():
                        annual.append({"window": w, "scenario": sid, "book": book, **r.to_dict()})
                    g = BT.cost_slippage_grid(rows)
                    g.insert(0, "book", book)
                    g.insert(0, "scenario", sid)
                    g.insert(0, "window", w)
                    grids.append(g)
                else:
                    sens_rows.extend(rows)
    # M2 variant (breakout candle itself may be the first red candle)
    for w in "AB":
        cfg = SCENARIOS["SL40_T60"]
        b = BT.books(w, cfg, red_variant[w])
        nsess = sum(1 for e in red_variant[w] if e.session.evaluable)
        for book, rows in b.items():
            nsg = sum(1 for e in red_variant[w] if e.traces[M2].status == "SIGNAL") if book == "M2" else None
            perf.append({"window": w, "window_dates": f"{WINDOWS[w][0]}..{WINDOWS[w][1]}", "scenario": "SL40_T60__M2_ALT_BREAKOUT_RED", "kind": "SENSITIVITY", "book": book, **BT.metrics(rows, nsess, nsg)})
    perf_df = pd.DataFrame(perf)
    write_csv(perf_df, "historical_performance_comparison.csv")
    write_csv(pd.DataFrame(tr_rows["M1"]), "method1_backtest.csv")
    write_csv(pd.DataFrame(tr_rows["M2"]), "method2_backtest.csv")
    write_csv(pd.DataFrame(tr_rows["COMBINED"]), "combined_irf_backtest.csv")
    write_csv(pd.DataFrame(sens_rows), "sensitivity_trades.csv")
    write_csv(pd.DataFrame(monthly), "monthly_returns_points.csv")
    write_csv(pd.DataFrame(annual), "annual_performance_points.csv")
    write_csv(pd.concat(grids), "cost_slippage_sensitivity.csv")
    # ---- daily verification + overlap
    daily, overlap = [], []
    for w in "AB":
        for e40, e35 in zip(evals[(w, "SL40_T60")], evals[(w, "SL35_T60")], strict=True):
            daily.append(RP.daily_row(w, e40, e35))
            oc = overlap_class(e40)
            if oc.startswith("BOTH"):
                t1, t2 = e40.traces[M1], e40.traces[M2]
                sel = e40.combined.get("selected_method", "")
                overlap.append({"window": w, "date": e40.date, "overlap_class": oc, "M1_signal": f"{t1.signal_time:%H:%M}", "M2_signal": f"{t2.signal_time:%H:%M}",
                                "minutes_M2_after_M1": int((t2.signal_time - t1.signal_time).total_seconds() // 60), "M1_status": e40.status[M1], "M2_status": e40.status[M2],
                                "combined_selected": RP.SHORT.get(sel, ""), "tie": bool(e40.combined.get("tie")),
                                "same_entry_price_and_exit": bool(oc == "BOTH_SAME_TIME" and e40.trades[M1] and e40.trades[M2] and e40.trades[M1].get("entry_price") == e40.trades[M2].get("entry_price")),
                                "M1_gross_SL40": (e40.trades[M1] or {}).get("gross_points"), "M2_gross_SL40": (e40.trades[M2] or {}).get("gross_points")})
    write_csv(pd.DataFrame(daily), "daily_verification.csv")
    write_csv(pd.DataFrame(overlap), "overlap_analysis.csv")
    # ---- examples
    tv = DA.load_vendor_days([date(2026, 11, 3)])
    ex_rows = []
    for ex in EXM.EXAMPLES:
        r = EXM.replay(ex, SCENARIOS["SL35_T60"], SCENARIOS["SL40_T60"], tv)
        ex_rows.append({k: v for k, v in r.items() if not k.startswith("_")})
    write_csv(pd.DataFrame(ex_rows), "source_example_reproduction.csv")
    cand = EXM.candidate_search(1.0)
    (OUT / "undated_example_candidate_search.json").write_text(json.dumps(cand, indent=1, default=str))
    # ---- independent audit (signals + trades), all scenarios, both windows, plus the red-variant
    audit = {}
    for w in "AB":
        for sid, cfg in scen.items():
            r = AU.compare(datasets[w], evals[(w, sid)], cfg)
            audit[f"{w}/{sid}"] = {"signal_comparisons": r["signal_comparisons"], "trade_comparisons": r["trade_comparisons"], "mismatches": len(r["mismatches"]), "first": [str(x) for x in r["mismatches"][:3]]}
        rv = AU.compare(datasets[w], red_variant[w], SCENARIOS["SL40_T60"].__class__(**{**SCENARIOS["SL40_T60"].__dict__, "allow_red_breakout_candle_as_first_red": True}))
        audit[f"{w}/SL40_T60__M2_ALT_BREAKOUT_RED"] = {"signal_comparisons": rv["signal_comparisons"], "trade_comparisons": rv["trade_comparisons"], "mismatches": len(rv["mismatches"]), "first": [str(x) for x in rv["mismatches"][:3]]}
    # causality (look-ahead) audit
    caus = {"signals_checked": 0, "failures": []}
    for w in "AB":
        for ev in evals[(w, "SL40_T60")]:
            if not ev.session.evaluable:
                continue
            cs = ev.session.candles
            for m, fn in ((M1, run_method1), (M2, run_method2)):
                tr = ev.traces[m]
                if tr.status != "SIGNAL":
                    continue
                caus["signals_checked"] += 1
                k = next(i for i, c in enumerate(cs) if c.start == tr.confirmation_candle.start)
                same = fn(ev.date, cs[:k + 1])
                before_sig = fn(ev.date, cs[:k])
                fill = ev.trades[m] or {}
                ok = (same.status == "SIGNAL" and same.signal_time == tr.signal_time and before_sig.status == "NO_SIGNAL" and (not fill.get("traded") or fill["entry_time"] >= tr.signal_time)
                      and tr.signal_time == tr.confirmation_candle.end)
                if not ok:
                    caus["failures"].append((str(ev.date), m))
    audit["causality"] = caus
    diag = {}
    for w in "AB":
        ev_ = [e for e in evals[(w, "SL40_T60")] if e.session.evaluable]
        brk = [e for e in ev_ if e.traces[M2].breakout_candle is not None]
        red = [e for e in brk if e.traces[M2].reference_candle is not None]
        diag[w] = {"sessions_with_rally_breakout": len(brk), "sessions_with_level_b_marked": len(red),
                   "first_red_candle_closed_below_level_A": sum(1 for e in red if e.traces[M2].reference_candle.close < e.traces[M2].initial_range_high),
                   "breakout_candle_itself_red": sum(1 for e in brk if e.traces[M2].breakout_candle.is_red)}
    (OUT / "m2_rally_diagnostics.json").write_text(json.dumps(diag, indent=1))
    (OUT / "audit_results.json").write_text(json.dumps(audit, indent=1, default=str))
    # ---- reconciliation
    jr, sha, n_rows = RC.load_journal()
    irf = [r for r in jr if r["strategy"] == "IRF"]
    earlier = RC.earlier_phase_signals()
    books_a = {k: [r for r in tr_rows[k] if r["window"] == "A" and r["scenario"] == "SL40_T60"] for k in tr_rows}
    books_a35 = {k: {str(r["date"]): r for r in tr_rows[k] if r["window"] == "A" and r["scenario"] == "SL35_T60"} for k in tr_rows}
    autos = {k: [{"date": r["date"], "candle_start": r["signal_candle_start"], "row": r} for r in books_a[k]] for k in books_a}
    ph_autos = {p: [{"date": d, "candle_start": v[0], "method": v[1]} for d, v in m.items()] for p, m in earlier.items()}
    matches = {k: RC.stage_match(irf, autos[k]) for k in autos}
    matches.update({p: RC.stage_match(irf, ph_autos[p]) for p in ph_autos})
    day_status = {e.date: e for e in evals[("A", "SL40_T60")]}
    journal_by_date = {}
    for r in jr:
        journal_by_date.setdefault(r["date"], []).append(f"{r['strategy']}@{r['time']}")
    rec_rows = []
    for m in irf:
        d = m["date"]
        row = {"journal_row": m["sheet_row"], "sl_no": m["sl_no"], "date": d, "weekday": m["weekday"], "journal_time_label": m["time"], "journal_outcome": m["outcome"], "weekend_not_a_session": m["weekday"] in ("Sat", "Sun")}
        for k in ("M1", "M2", "COMBINED"):
            st = matches[k].get(m["sheet_row"])
            row[f"{k}_match_class"] = st[0] if st else ("MANUAL_ONLY")
            row[f"{k}_signal_candle_start"] = autos[k][st[1]]["candle_start"] if st else ""
            row[f"{k}_delta_min"] = st[2] if st else ""
            if st:
                r40 = autos[k][st[1]]["row"]
                r35 = books_a35[k].get(str(d))
                row[f"{k}_auto_outcome_SL40"] = r40["exit_reason"]
                row[f"{k}_auto_outcome_SL35"] = r35["exit_reason"] if r35 else ""
                row[f"{k}_outcome_vs_journal_SL40"] = RC.outcome_vs_journal(m["outcome"], r40["exit_reason"])
        for p in ph_autos:
            st = matches[p].get(m["sheet_row"])
            row[f"{p}_match_class"] = st[0] if st else "MANUAL_ONLY"
            row[f"{p}_first_signal_candle_start"] = ph_autos[p][st[1]]["candle_start"] if st else (earlier[p].get(str(d), ("", ""))[0])
        ev = day_status.get(d)
        why = ""
        if row["COMBINED_match_class"] == "MANUAL_ONLY":
            if row["weekend_not_a_session"]:
                why = "WEEKEND_DATE_NOT_AN_EXCHANGE_SESSION"
            elif ev is None:
                why = "DATE_NOT_IN_EVALUATED_WINDOW"
            elif not ev.session.evaluable:
                why = "SESSION_NOT_EVALUATED:" + ev.session.reason
            else:
                why = RP._no_trade_reason(ev)
        row["v3_reason_no_combined_trade"] = why
        row["v3_M1_first_signal_any"] = RP._hm(day_status[d].traces[M1].signal_time) if d in day_status else ""
        row["v3_M2_first_signal_any"] = RP._hm(day_status[d].traces[M2].signal_time) if d in day_status else ""
        row["v3_combined_selected_method"] = RP.SHORT.get(day_status[d].combined.get("selected_method", ""), "") if d in day_status else ""
        best = []
        for k in ("M1", "M2"):
            t = day_status[d].traces[M1 if k == "M1" else M2] if d in day_status else None
            if t is not None and t.status == "SIGNAL":
                best.append((abs(RC.mins(RP._hm(t.confirmation_candle.start)) - (RC.mins(m["time"]) or 0)), k))
        row["method_nearest_to_journal_time"] = sorted(best)[0][1] if best else ""
        row["classification_note"] = ("METHOD_ATTRIBUTION_DIFFERS: the combined engine credited " + row["v3_combined_selected_method"] + " but " + row["method_nearest_to_journal_time"] + "'s signal is nearest to the journal time"
                                      if row["method_nearest_to_journal_time"] and row["v3_combined_selected_method"] and row["method_nearest_to_journal_time"] != row["v3_combined_selected_method"].split("+")[0] else "")
        rec_rows.append(row)
    rec_df = pd.DataFrame(rec_rows)
    write_csv(rec_df, "manual_journal_reconciliation.csv")
    # automated-only
    ao = []
    for k in ("M1", "M2", "COMBINED"):
        used = {v[1] for v in matches[k].values()}
        for i, a in enumerate(autos[k]):
            if i not in used:
                ao.append({"book": k, "date": a["date"], "signal_candle_start": a["candle_start"], "journal_rows_that_date": "; ".join(journal_by_date.get(a["date"], [])) or "none",
                           "class": "AUTOMATED_ONLY_WRONG_STRATEGY_DATE" if any(not x.startswith("IRF@") for x in journal_by_date.get(a["date"], [])) else "AUTOMATED_ONLY_NO_JOURNAL_ENTRY"})
    write_csv(pd.DataFrame(ao), "manual_journal_automated_only.csv")
    summ = []
    for k in ("M1", "M2", "COMBINED", "PHASE_3_6", "PHASE_5_3", "PHASE_6_1"):
        cls = Counter(v[0] for v in matches[k].values())
        n_auto = len(autos[k]) if k in autos else len(ph_autos[k])
        summ.append({"engine": k, "journal_IRF_rows": len(irf), "weekend_rows_unmatchable": sum(1 for m in irf if m["weekday"] in ("Sat", "Sun")), "strict": cls.get("STRICT", 0), "time_tolerant_extra": cls.get("TIME_TOLERANT", 0),
                     "date_strategy_only": cls.get("DATE_STRATEGY_ONLY", 0), "manual_only": len(irf) - sum(cls.values()), "automated_trades_or_first_signals": n_auto, "automated_only": n_auto - sum(cls.values()),
                     "unit": "executed trades (SL40 scenario; entry times are scenario independent)" if k in autos else "first confirmed IRF signal per date within 13:00 (signal ledger)"})
    write_csv(pd.DataFrame(summ), "manual_journal_match_summary.csv")
    # changed entry times vs earlier phases (dates where V3 combined and an earlier phase both have a first signal)
    ch = []
    comb_by_date = {str(a["date"]): a["candle_start"] for a in autos["COMBINED"]}
    for p, mp in earlier.items():
        same = diff = 0
        for d, (cs_, _m) in mp.items():
            if d in comb_by_date:
                same, diff = (same + 1, diff) if comb_by_date[d] == cs_ else (same, diff + 1)
        ch.append({"earlier_phase": p, "dates_both_have_a_first_signal": same + diff, "same_candle_start": same, "changed_candle_start": diff, "dates_only_earlier_phase": sum(1 for d in mp if d not in comb_by_date),
                   "dates_only_v3_combined": sum(1 for d in comb_by_date if d not in mp)})
    write_csv(pd.DataFrame(ch), "changed_entry_times_vs_earlier_phases.csv")
    state = {"journal_sha256": sha, "journal_data_rows": n_rows, "journal_irf_rows": len(irf), "sessions": {w: sum(1 for e in evals[(w, "SL40_T60")] if e.session.evaluable) for w in "AB"}}
    (CACHE / "state.json").write_text(json.dumps(state, indent=1, default=str))
    return state


def render() -> dict:
    """Charts (examples + every executed trade of the primary window), the per-day markdown files for both windows."""
    from nifty_trading.research.irf_v3 import charts as CH

    for d in ("charts_method1", "charts_method2", "charts_combined", "daily"):
        (OUT / d).mkdir(parents=True, exist_ok=True)
    ds = {w: DA.load_dataset(w) for w in "AB"}
    ev40 = {w: BT.run_dataset(ds[w], SCENARIOS["SL40_T60"]) for w in "AB"}
    ev35 = {w: BT.run_dataset(ds[w], SCENARIOS["SL35_T60"]) for w in "AB"}
    n = Counter()
    # ---- source examples
    tv = DA.load_vendor_days([date(2026, 11, 3)])
    for ex in EXM.EXAMPLES:
        r = EXM.replay(ex, SCENARIOS["SL35_T60"], SCENARIOS["SL40_T60"], tv)
        folder = "charts_method1" if ex["method"] == "M1" else "charts_method2"
        png = str(OUT / "source_extracts" / ex["img"])
        tag = f"EX_{ex['id']}_{ex['date'] or 'UNDATED'}"
        arith = EXM.arithmetic_check(ex)
        lines = [f"Source: {ex['pdf']} page {ex['page']} ({ex['kind']}); stated date: {ex['date'] or 'none - not assigned'}; stated outcome: {ex['outcome']}.",
                 f"Printed numbers: level A {ex['A']}" + (f", Level B {ex['B']}" if ex['B'] else "") + f", entry {ex['entry']}, stop {ex['stop']}, target {ex['target']}.",
                 f"Arithmetic of the printed numbers: entry {arith['entry_below_level']} below the level, stop {arith['stop_distance']} away, target {arith['target_distance']} away -> {arith['internal_consistency']}.", ex["note"]]
        if "_ev" in r:
            ev = r["_ev"]
            methods = [M1] if ex["method"] == "M1" else [M2]
            lines.append(f"Replay ({r['vendor']}): first candle {r['replay_first_candle_ohlc']}; Level A diff vs source {r['level_A_diff_vs_source']:+.2f}; signal {r['replay_signal']}"
                         + (f" {r.get('replay_signal_time', '')}, failure candle {r.get('failure_candle', '')}, Level B diff {r.get('level_B_diff_vs_source', '')}; SL35 -> {r.get('replay_SL35_exit')}; SL40 -> {r.get('replay_SL40_exit')}" if r['replay_signal'] == 'SIGNAL' else ""))
            if r.get("diag_candle_closing_nearest_source_entry"):
                lines.append("Diagnostic: candle whose close is nearest the source entry price: " + r["diag_candle_closing_nearest_source_entry"])
            svg = RP.trace_chart(ev, SCENARIOS["SL40_T60"], methods, f"{ex['id']} replay - {ex['method']}", " | ".join(lines[:1]), embed_png=png, extra=lines[1:])
            (OUT / folder / f"{tag}.svg").write_text(svg)
            both = RP.trace_chart(ev, SCENARIOS["SL40_T60"], [M1, M2], f"{ex['id']} replay - both methods (combined view)", f"selected: {ev.combined.get('selected_method') or 'none'}", extra=lines[3:4])
            (OUT / "charts_combined" / f"{tag}.svg").write_text(both)
        else:
            lines.append(f"Replay status: {r['status']}")
            if ex["id"] in EXM.candidate_search.__defaults__ or True:
                cj = json.loads((OUT / "undated_example_candidate_search.json").read_text())
                if ex["id"] in cj:
                    lines.append("Level-only candidate search (+-1.0 point, informational, NO date adopted): " + str(cj[ex["id"]]["verdicts"] or "no candidate session"))
            (OUT / folder / f"{tag}.svg").write_text(CH.spec_card(f"{ex['id']} - NOT replayed", ex["pdf"] + f" p{ex['page']}", lines, embed_png=png))
        n["examples"] += 1
    # ---- every executed trade of the primary window (SL40 scenario drawn; SL35 outcome stated in the notes)
    for ev, e35 in zip(ev40["A"], ev35["A"], strict=True):
        if not ev.session.evaluable:
            continue
        d = f"{ev.date:%Y%m%d}"
        for m, folder, k in ((M1, "charts_method1", "M1"), (M2, "charts_method2", "M2")):
            if ev.trades.get(m) and ev.trades[m].get("traded"):
                r35 = e35.trades[m]
                svg = RP.trace_chart(ev, SCENARIOS["SL40_T60"], [m], f"{ev.date} {k} trade (SL40/T60)", f"window A; signal {ev.traces[m].signal_time:%H:%M}; SL35 scenario: {r35.get('exit_reason')} {r35.get('gross_points')}")
                (OUT / folder / f"{d}_{k}.svg").write_text(svg)
                n[k] += 1
        if ev.combined.get("selected_method"):
            r35 = e35.trades[ev.combined["selected_method"]]
            svg = RP.trace_chart(ev, SCENARIOS["SL40_T60"], [M1, M2], f"{ev.date} combined IRF V3 - {ev.combined.get('outcome')}", f"selected {RP.SHORT[ev.combined['selected_method']]}"
                                 + (" (same-instant tie -> Method 1 by research policy)" if ev.combined.get("tie") else "") + f"; SL35 scenario: {r35.get('exit_reason')} {r35.get('gross_points')}")
            (OUT / "charts_combined" / f"{d}_COMBINED.svg").write_text(svg)
            n["COMB"] += 1
    # ---- per-day files, both windows
    for w in "AB":
        for ev, e35 in zip(ev40[w], ev35[w], strict=True):
            p = OUT / "daily" / f"{ev.date:%Y-%m}"
            p.mkdir(parents=True, exist_ok=True)
            (p / f"{ev.date}.md").write_text(RP.daily_markdown(w, ev, e35))
            n["daily"] += 1
    return dict(n)


if __name__ == "__main__":
    stage = sys.argv[1] if len(sys.argv) > 1 else "all"
    if stage in ("compute", "all"):
        print(json.dumps(compute(), indent=1, default=str))
    if stage in ("charts", "all"):
        print(render())
