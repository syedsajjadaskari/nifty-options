"""Phase 6.3: reconciliation of configurations A, B and C with the ORIGINAL manual journal (Phase 5.6 matcher and tolerances, unchanged), ORB-vs-IRF disagreement audit, IRF support-break reconciliation, handwritten
corrections, root causes. The journal records only date, entry-time label, strategy and outcome: no direction, price or exit time; nothing is invented and no exact trade match can be verified."""

from __future__ import annotations

import hashlib
import json
import pickle
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase61_common import JOURNAL, R61, R63, ROOT, SCRATCH, write_csv  # noqa: E402

from nifty_trading.research import phase56 as M  # noqa: E402
from nifty_trading.research.orb_v2.reporting import md_table, write_workbook  # noqa: E402

CFG = ("A", "B", "C")
STRATS = ("IRF", "ORB", "PDR", "PDS", "RF")


def hhmm_minus5(t: str) -> str:
    m = int(t[:2]) * 60 + int(t[3:5]) - 5
    return f"{m // 60:02d}:{m % 60:02d}"


def main() -> int:  # noqa: C901
    R63.mkdir(parents=True, exist_ok=True)
    res = pickle.loads((SCRATCH / "results62.pkl").read_bytes())["A"]
    rows, summ = M.load_journal(JOURNAL)
    jhash = hashlib.sha256(JOURNAL.read_bytes()).hexdigest()
    led = {k: [dict(r) for r in res["ledgers"][k]] for k in CFG}
    for k in CFG:
        for r in led[k]:
            r["signal_candle_start"] = hhmm_minus5(r["signal_time"])
    window_dates = set(res["days"]["C"].keys())
    window_dates_s = {str(d) for d in window_dates}
    mt = {k: M.match(rows, led[k]) for k in CFG}
    trades_by_date = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for r in led[k]:
            trades_by_date[k][r["date"]].append(r)
    # ------------------------------------------------------------------ source audit
    by_s = Counter(r.strategy for r in rows)
    wk = [r for r in rows if r.weekend]
    out_win = [r for r in rows if r.date not in window_dates_s and not r.weekend]
    (R63 / "manual_journal_source_audit.md").write_text("\n".join([
        "# Manual journal source audit", "", f"* File: `docs/trading journal/Trading_Journal_Sep2025_Aug2026 REPORT.xlsx`, SHA-256 `{jhash}` (read-only; every value kept as written).", f"* Data rows: **{len(rows)}**; the Summary sheet states {summ.get('Total trades')} trades (the Summary figure is not the data-row count; the discrepancy of {len(rows) - int(summ.get('Total trades', 0) or 0)} is unresolved and not corrected).",
        f"* By strategy: {dict(by_s)}.", f"* Weekend-dated rows (not exchange sessions, can never match, kept as written): {len(wk)} - " + ", ".join(f"{r.date} {r.strategy}" for r in wk) + ".",
        f"* Rows on dates outside the evaluated sessions (other than weekends): {len(out_win)}.", "* Columns available: serial number, date, entry-time label, strategy, outcome (Target / SL / BE). **No direction, entry price, support/resistance level, stop, target or exit time is recorded.**",
        "* Consequence: a 'verified exact trade match' (same direction, entry price within a tolerance, compatible exit details) cannot be established for any row. No missing field was manufactured; the matching below uses only date, strategy, time label and the outcome label.", "",
        "Summary sheet: " + json.dumps({k: v for k, v in summ.items()}, default=str)]))
    # ------------------------------------------------------------------ matching tables
    pairs, summary_rows, strat_rows, wrong = [], [], [], []
    detail = {}
    for k in CFG:
        m = mt[k]
        stg = {"STRICT": m["strict"], "TIME_TOLERANT": m["tolerant"], "DATE_STRATEGY_ONLY": m["date_strategy_only"]}
        for stage, ps in stg.items():
            for p in ps:
                pairs.append({"config": k, "stage": stage, "journal_row": p.manual.row_id, "sheet_row": p.manual.sheet_row, "date": p.manual.date, "manual_strategy": p.manual.strategy, "manual_time_label": p.manual.time_label, "manual_outcome": p.manual.outcome,
                              "trade_id": p.trade["trade_id"], "auto_strategy": p.trade["strategy"], "auto_method": p.trade["method"], "auto_direction": p.trade["direction"], "auto_signal_candle_start": p.trade["signal_candle_start"], "auto_entry_time": p.trade["entry_time"],
                              "auto_entry_price": p.trade["entry_price"], "delta_minutes_signal_candle_vs_label": p.delta_minutes, "auto_outcome": p.trade["outcome"], "outcome_label_agrees": M.outcome_agrees(p.manual.outcome, p.trade["outcome"]) if stage != "DATE_STRATEGY_ONLY" else "n/a",
                              "verified_exact_trade_match": False, "exact_verification": "NOT_VERIFIABLE: the journal has no direction, entry price or exit details"})
        for r in m["manual_unmatched"]:
            pairs.append({"config": k, "stage": "MANUAL_ONLY", "journal_row": r.row_id, "sheet_row": r.sheet_row, "date": r.date, "manual_strategy": r.strategy, "manual_time_label": r.time_label, "manual_outcome": r.outcome, "journal_flags": ";".join(r.flags)})
        for t in m["trades_unmatched"]:
            pairs.append({"config": k, "stage": "AUTOMATED_ONLY", "trade_id": t["trade_id"], "date": t["date"], "auto_strategy": t["strategy"], "auto_method": t["method"], "auto_direction": t["direction"], "auto_signal_candle_start": t["signal_candle_start"],
                          "auto_entry_time": t["entry_time"], "auto_entry_price": t["entry_price"], "auto_outcome": t["outcome"]})
        for r in m["manual_unmatched"]:
            if r.weekend:
                continue
            ts = trades_by_date[k].get(r.date, [])
            if ts and not any(t["strategy"] == r.strategy for t in ts):
                wrong.append({"config": k, "journal_row": r.row_id, "date": r.date, "manual_strategy": r.strategy, "manual_time_label": r.time_label, "manual_outcome": r.outcome, "automated_strategies_that_day": "/".join(f"{t['strategy']}@{t['entry_time']}" for t in ts)})
        n_ok = sum(1 for p in m["strict"] + m["tolerant"] if M.outcome_agrees(p.manual.outcome, p.trade["outcome"]))
        eligible = [r for r in rows if not r.weekend]
        summary_rows.append({"config": k, "automated_trades": len(led[k]), **{f"{s}_trades": sum(1 for t in led[k] if t["strategy"] == s) for s in STRATS}, "verified_exact_trade_matches": 0, "strict_matches": len(m["strict"]), "time_tolerant_additional": len(m["tolerant"]),
                             "date_strategy_only": len(m["date_strategy_only"]), "manual_only_rows": len(m["manual_unmatched"]), "manual_only_weekend": sum(1 for r in m["manual_unmatched"] if r.weekend), "automated_only_trades": len(m["trades_unmatched"]),
                             "wrong_strategy_dates": sum(1 for w in wrong if w["config"] == k), "outcome_label_agreements": n_ok, "outcome_label_denominator": len(m["strict"]) + len(m["tolerant"]), "journal_rows": len(rows), "journal_rows_non_weekend": len(eligible)})
        for s in STRATS:
            mr = [r for r in rows if r.strategy == s]
            strat_rows.append({"config": k, "strategy": s, "manual_rows": len(mr), "automated_trades": sum(1 for t in led[k] if t["strategy"] == s), "strict": sum(1 for p in m["strict"] if p.manual.strategy == s), "time_tolerant": sum(1 for p in m["tolerant"] if p.manual.strategy == s),
                               "date_strategy_only": sum(1 for p in m["date_strategy_only"] if p.manual.strategy == s), "manual_only": sum(1 for r in m["manual_unmatched"] if r.strategy == s), "automated_only": sum(1 for t in m["trades_unmatched"] if t["strategy"] == s),
                               "strict_of_manual_pct": round(100 * sum(1 for p in m["strict"] if p.manual.strategy == s) / max(len(mr), 1), 1), "outcome_agree_among_strict_tolerant": sum(1 for p in m["strict"] + m["tolerant"] if p.manual.strategy == s and M.outcome_agrees(p.manual.outcome, p.trade["outcome"])),
                               "strict_tolerant_total": sum(1 for p in m["strict"] + m["tolerant"] if p.manual.strategy == s)})
        detail[k] = m
    write_csv(R63 / "manual_vs_automated_matching.csv", pairs)
    for fn, st in (("strict_matches.csv", "STRICT"), ("time_tolerant_matches.csv", "TIME_TOLERANT"), ("date_only_matches.csv", "DATE_STRATEGY_ONLY"), ("manual_only.csv", "MANUAL_ONLY"), ("automated_only.csv", "AUTOMATED_ONLY")):
        write_csv(R63 / fn, [p for p in pairs if p["stage"] == st], list(dict.fromkeys(k for p in pairs for k in p)))
    write_csv(R63 / "wrong_strategy_dates.csv", wrong, ["config", "journal_row", "date", "manual_strategy", "manual_time_label", "manual_outcome", "automated_strategies_that_day"])
    write_csv(R63 / "match_summary_by_strategy.csv", strat_rows)
    write_csv(R63 / "match_summary_by_config.csv", summary_rows)
    # ------------------------------------------------------------------ ORB versus IRF audit (every manual ORB date)
    sig = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for s in res["signals"][k]:
            sig[k][s["date"]].append(s)
    orb_rej = {r["date"]: r["failed"] for r in res["orb_rejections"]}
    PROVISIONAL_ONLY = {"NO_PATTERN", "LEVEL_NOT_BROKEN", "GAP_TOO_LARGE"}
    orb_rows = []
    for r in sorted((r for r in rows if r.strategy == "ORB"), key=lambda x: (x.date, x.row_id)):
        d = r.date
        row = {"journal_row": r.row_id, "date": d, "weekday": r.weekday, "journal_time": r.time_label, "journal_outcome": r.outcome}
        if r.weekend or d not in window_dates_s:
            row.update({"classification": "NO ELIGIBLE TRADE (non-session journal date)", "resolved": False})
            orb_rows.append(row)
            continue
        for k in CFG:
            ts = sorted(trades_by_date[k].get(d, []), key=lambda t: (t["entry_time"], int(t["trade_no"])))
            row[f"first_trade_{k}"] = f"{ts[0]['strategy']}@{ts[0]['entry_time']} {ts[0]['outcome']}" if ts else "none"
        row["irf_executed_A"] = any(t["strategy"] == "IRF" for t in trades_by_date["A"].get(d, []))
        row["irf_executed_B"] = any(t["strategy"] == "IRF" for t in trades_by_date["B"].get(d, []))
        orb_sig = [s for s in sig["C"].get(d, []) if s["strategy"] == "ORB"]
        irf_sig = sorted((s["time"], s["method"]) for s in sig["C"].get(d, []) if s["strategy"] == "IRF")
        tsC = sorted(trades_by_date["C"].get(d, []), key=lambda t: (t["entry_time"], int(t["trade_no"])))
        row.update({"orb_v2_signal": f"{orb_sig[0]['direction']} {orb_sig[0]['time']}" if orb_sig else "none", "orb_v2_fill": tsC[0]["entry_time"] if (tsC and tsC[0]["strategy"] == "ORB") else (("09:20" if orb_sig else "")), "irf_v2_first_signal_C": f"{irf_sig[0][0]} {irf_sig[0][1]}" if irf_sig else "none",
                    "orb_v2_rejection": orb_rej.get(d, ""), "controller_final_state_C": res["days"]["C"][pd.Timestamp(d).date()]["final_state"]})
        fs = res["days"]["C"][pd.Timestamp(d).date()]["final_state"]
        if tsC and tsC[0]["strategy"] == "ORB":
            cl = "ORB NOW SELECTED"
        elif fs == "UNRESOLVED_EXECUTION":
            cl = "SAME-MINUTE CONFLICT"
        elif orb_sig:
            cl = "ORB SIGNAL PRESENT BUT LATER" if (tsC and tsC[0]["entry_time"] < "09:20") else "ORB SIGNAL PRESENT, NOT SELECTED (controller)"
        else:
            failed = set(filter(None, orb_rej.get(d, "").split(";")))
            if failed and failed <= PROVISIONAL_ONLY:
                cl = "SOURCE RULE UNRESOLVED"
            elif tsC and tsC[0]["strategy"] == "IRF":
                cl = "IRF STILL SELECTED"
            elif failed:
                cl = "ORB SIGNAL REJECTED"
            else:
                cl = "NO ELIGIBLE TRADE"
        row["classification"] = cl
        row["resolved"] = cl == "ORB NOW SELECTED"
        row["note"] = "classification is about the engine only; the journal ORB label is not proof the author's setup is reproduced (no direction or level recorded)"
        orb_rows.append(row)
    write_csv(R63 / "orb_vs_irf_comparison.csv", orb_rows)
    prev_irf = [r for r in orb_rows if r.get("irf_executed_A") or r.get("irf_executed_B")]
    cls_all = Counter(r["classification"] for r in orb_rows)
    cls_prev = Counter(r["classification"] for r in prev_irf)
    orb_before_irf = [r for r in prev_irf if r["classification"] == "ORB NOW SELECTED"]
    # ------------------------------------------------------------------ IRF support-break reconciliation (every manual IRF row)
    att = pd.read_csv(R61 / "irf_reference_candle_audit.csv", dtype=str, keep_default_na=False)
    att = att[att.window == "A"]
    ema = pd.read_csv(R61 / "irf_ema_28_diagnostics.csv", dtype=str, keep_default_na=False)
    ema = ema[ema.window == "A"]
    mC = detail["C"]
    pairC = {p.manual.row_id: p for p in mC["strict"] + mC["tolerant"] + mC["date_strategy_only"]}
    stageC = {p.manual.row_id: st for st, ps in (("STRICT", mC["strict"]), ("TIME_TOLERANT", mC["tolerant"]), ("DATE_STRATEGY_ONLY", mC["date_strategy_only"])) for p in ps}
    irf_rows = []
    for r in sorted((r for r in rows if r.strategy == "IRF"), key=lambda x: (x.date, x.row_id)):
        d = r.date
        base = {"journal_row": r.row_id, "date": d, "journal_time_label": r.time_label, "journal_outcome": r.outcome, "match_stage_C": stageC.get(r.row_id, "MANUAL_ONLY" if not r.weekend else "WEEKEND_ROW")}
        if r.weekend or d not in window_dates_s:
            irf_rows.append({**base, "explanation": "non-session journal date"})
            continue
        isig = sorted((s["time"], s["method"], s["level_or_support"], s["controller_event"]) for s in sig["C"].get(d, []) if s["strategy"] == "IRF")
        a = att[att.date == d]
        e = ema[ema.date == d]
        t = next((x for x in trades_by_date["C"].get(d, []) if x["strategy"] == "IRF"), None)
        p = pairC.get(r.row_id)
        base.update({"v2_irf_signals_all_day": "; ".join(f"{x[0]} {x[1]} (level {x[2]}) -> {x[3][:40]}" for x in isig) or "none", "v2_attempts": len(a), "v2_first_red_candle(s)": "; ".join(f"{x.reference_candle_start} {x.reference_ohlc} support={x.support_wick_low}" for x in a.itertuples() if x.reference_candle_start) or "none",
                     "v2_support_break_candle(s)": "; ".join(x.first_close_below_support for x in a.itertuples() if x.first_close_below_support) or "none", "ema_28_rejections": "; ".join(f"{x.time} {x.method} dist {float(x.range_clearance):.1f}" for x in e.itertuples() if x.status.startswith("REJECTED")) or "none",
                     "ema_range_clearance_of_confirmed": "; ".join(f"{x.time} {x.method} {float(x.range_clearance):.1f} ({x.relation_to_confirmation_candle})" for x in e.itertuples() if x.status.startswith("PASSED")) or "none",
                     "running_low_close_below_prior": "; ".join(f"{x.time}" for x in e.itertuples() if x.signal_close_below_prior_running_low == "True") or "none",
                     "C_irf_trade": f"{t['method']} entry {t['entry_time']} @ {t['entry_price']} -> {t['outcome']}" if t else "none", "first_trade_C": (lambda ts: f"{ts[0]['strategy']}@{ts[0]['entry_time']}" if ts else "none")(sorted(trades_by_date["C"].get(d, []), key=lambda z: z["entry_time"]))})
        if p is not None and stageC.get(r.row_id) in ("STRICT", "TIME_TOLERANT"):
            ex = f"matched ({stageC[r.row_id]}) by C's {p.trade['strategy']} {p.trade['method']} signal candle {p.trade['signal_candle_start']} (journal label {r.time_label}); outcome label {'agrees' if M.outcome_agrees(r.outcome, p.trade['outcome']) else 'differs'} ({r.outcome} vs {p.trade['outcome']})"
        elif t is None and trades_by_date["C"].get(d):
            ex = f"a different strategy was selected first in C ({base['first_trade_C']}); IRF V2 signals that day: {base['v2_irf_signals_all_day']}"
        elif not isig:
            ex = "IRF V2 produced no confirmed signal this session (" + (f"{len(a)} Method 2 attempt(s); " if len(a) else "no breakout attempt; ") + "EMA-28 rejections: " + base["ema_28_rejections"] + ")"
        else:
            ex = "IRF V2 signalled but the trade timing differs from the journal label or the controller did not trade it (see signals list)"
        irf_rows.append({**base, "explanation": ex})
    write_csv(R63 / "irf_support_break_reconciliation.csv", irf_rows)
    # ------------------------------------------------------------------ handwritten corrections
    hc = pd.read_csv(ROOT / "reports/phase5/phase53_author_corrected/dated_author_corrections.csv")
    hc = hc[hc.trading_date.notna()]
    hrows = []
    for x in hc.itertuples():
        d = x.trading_date
        row = {"correction_id": x.correction_id, "date": d, "pdf_page": x.handwritten_pdf_page, "author_comment": x.original_author_comment, "topic": x.topic, "author_expected": x.expected_strategy_or_candle,
               "manual_rows": "; ".join(f"{r.strategy}@{r.time_label} {r.outcome}" for r in rows if r.date == d) or "none"}
        for k in CFG:
            row[f"auto_{k}"] = "; ".join(f"{t['strategy']}/{t['method']}@{t['entry_time']} {t['outcome']}" for t in sorted(trades_by_date[k].get(d, []), key=lambda z: z["entry_time"])) or "no trade"
        exp = str(x.expected_strategy_or_candle)
        if exp.startswith("ORB") or x.topic == "ORB_MISSING":
            got = any(t["strategy"] == "ORB" for t in trades_by_date["C"].get(d, []))
            row["status_C"] = "ORB_NOW_TRADED_DIRECTION_UNVERIFIED" if got else "ORB_STILL_NOT_TRADED"
        else:
            row["status_C"] = "C_TRADES_EQUAL_B" if row["auto_C"] == row["auto_B"] else "C_DIFFERS_FROM_B"
        row["reconciled_with_author_evidence"] = "NOT CLAIMED: the handwritten notes carry no numeric entry, level or direction"
        hrows.append(row)
    write_csv(R63 / "handwritten_corrections_comparison.csv", hrows)
    # ------------------------------------------------------------------ root causes (manual-only rows and automated-only trades, every configuration)
    allsig = {k: defaultdict(list) for k in CFG}
    for k in CFG:
        for s in res["signals"][k]:
            allsig[k][(s["date"], s["strategy"])].append(s)
    rc = []
    for k in CFG:
        m = detail[k]
        for r in m["manual_unmatched"]:
            ts = trades_by_date[k].get(r.date, [])
            if r.weekend:
                cause, ev = "MANUAL_JOURNAL_INCONSISTENCY", "weekend date: not an exchange session"
            elif r.date not in window_dates_s:
                cause, ev = "MANUAL_JOURNAL_INCONSISTENCY", "date outside the evaluated sessions"
            else:
                ss = allsig[k].get((r.date, r.strategy), [])
                if ts and not any(t["strategy"] == r.strategy for t in ts):
                    cause = "DIFFERENT_STRATEGY_SELECTED"
                    ev = f"automated first trade {ts[0]['strategy']}@{ts[0]['entry_time']}; {r.strategy} confirmed signals that day: " + (", ".join(s["time"] for s in ss) or "none")
                elif ss:
                    cause = "ENTRY_TIME_MISMATCH" if any(t["strategy"] == r.strategy for t in ts) else "PORTFOLIO_CONTROLLER_CONSTRAINT"
                    ev = f"{r.strategy} signals at {', '.join(s['time'] for s in ss)} vs journal label {r.time_label}"
                else:
                    cause = "MISSING_STRATEGY_SIGNAL"
                    ev = (f"ORB V2 rejection: {orb_rej.get(r.date, 'n/a')}" if (r.strategy == "ORB" and k == "C") else f"no confirmed {r.strategy} signal in configuration {k}")
            rc.append({"config": k, "side": "MANUAL_ONLY", "date": r.date, "strategy": r.strategy, "journal_row": r.row_id, "cause": cause, "evidence": ev})
        for t in m["trades_unmatched"]:
            mr = [r for r in rows if r.date == t["date"] and not r.weekend]
            if not mr:
                cause, ev = "UNRESOLVED_DISCRETIONARY_SELECTION", "no journal row on this date"
            elif any(r.strategy == t["strategy"] for r in mr):
                cause, ev = "ENTRY_TIME_MISMATCH", f"journal rows: {', '.join(f'{r.strategy}@{r.time_label}' for r in mr)}"
            else:
                cause, ev = "DIFFERENT_STRATEGY_SELECTED", f"journal rows: {', '.join(f'{r.strategy}@{r.time_label}' for r in mr)}"
            rc.append({"config": k, "side": "AUTOMATED_ONLY", "date": t["date"], "strategy": t["strategy"], "trade_id": t["trade_id"], "cause": cause, "evidence": ev})
    write_csv(R63 / "mismatch_root_causes.csv", rc)
    rcc = defaultdict(Counter)
    for x in rc:
        rcc[(x["config"], x["strategy"], x["side"])][x["cause"]] += 1
    state = {"journal": {"rows": len(rows), "by_strategy": dict(by_s), "weekend_rows": len(wk), "summary_total": summ.get("Total trades"), "sha256": jhash}, "summary": summary_rows, "by_strategy": strat_rows, "orb_vs_irf": {"all_orb_rows": len(orb_rows), "classes_all": dict(cls_all), "previously_irf_executed_dates": len(prev_irf),
             "classes_previously_irf": dict(cls_prev), "orb_now_selected_on_previously_irf_dates": len(orb_before_irf), "orb_now_selected_dates_all": cls_all.get("ORB NOW SELECTED", 0)}, "wrong_strategy": dict(Counter(w["config"] for w in wrong)),
             "root_causes": {f"{a}|{b}|{c}": dict(v) for (a, b, c), v in rcc.items()}, "handwritten": dict(Counter((x["status_C"]) for x in hrows)), "irf_rows": len(irf_rows)}
    (R63 / "phase63_state.json").write_text(json.dumps(state, indent=1, default=str))
    pickle.dump({"pairs": pairs, "detail_stage": {k: {"strict": [(p.manual.row_id, p.trade["trade_id"]) for p in detail[k]["strict"]], "tolerant": [(p.manual.row_id, p.trade["trade_id"]) for p in detail[k]["tolerant"]],
                                                       "date_only": [(p.manual.row_id, p.trade["trade_id"]) for p in detail[k]["date_strategy_only"]]} for k in CFG}, "orb_rows": orb_rows, "irf_rows": irf_rows, "rows": rows}, open(SCRATCH / "results63.pkl", "wb"))
    # ------------------------------------------------------------------ exact_match_summary.md
    hdr = ["Measure"] + [f"{k}" for k in CFG]

    def line(lbl, key, den=None):
        return {"Measure": lbl, **{k: (f"{next(s for s in summary_rows if s['config'] == k)[key]}" + (f" / {den(k)}" if den else "")) for k in CFG}}
    tbl = [line("Total automated trades", "automated_trades")] + [line(f"{s} trades", f"{s}_trades") for s in STRATS] + [
        line("Verified exact trade matches", "verified_exact_trade_matches", lambda k: f"{len(rows)} journal rows"), line("Strict recorded-field matches", "strict_matches", lambda k: f"{len(rows)} journal rows"),
        line("Additional time-tolerant matches (<= 15 min)", "time_tolerant_additional", lambda k: f"{len(rows)}"), line("Date-and-strategy-only agreements", "date_strategy_only", lambda k: f"{len(rows)}"), line("Manual-only rows", "manual_only_rows", lambda k: f"{len(rows)}"),
        line("  of which weekend-dated rows", "manual_only_weekend"), line("Automated-only trades", "automated_only_trades", lambda k: f"{next(s for s in summary_rows if s['config'] == k)['automated_trades']} trades"), line("Wrong-strategy dates", "wrong_strategy_dates"),
        {"Measure": "Outcome-label agreements (strict + time-tolerant pairs)", **{k: f"{next(s for s in summary_rows if s['config'] == k)['outcome_label_agreements']} / {next(s for s in summary_rows if s['config'] == k)['outcome_label_denominator']}" for k in CFG}}]
    (R63 / "exact_match_summary.md").write_text("\n".join([
        "# Exact and staged match summary (configurations A, B, C)", "", "A = Phase 3.6 frozen; B = Phase 5.3 author-corrected (legacy ORB); C = IRF V2 + ORB V2 (provisional ORB-V2-A) + PDR/PDS first-eligible + RF. Primary window 2025-09-01..2026-08-31. One-to-one staged matching (Phase 5.6 matcher and tolerances, unchanged): "
        "STRICT = same date + strategy + time label equals the signal-candle start; TIME_TOLERANT = within 15 minutes; DATE_STRATEGY_ONLY = same date and strategy but outside the tolerance (NOT a match).", "",
        "**No verified exact trade match exists or can exist**: the journal records no direction, entry price or exit detail (see `manual_journal_source_audit.md`). 'Strict' means date + strategy + label only. Date-only agreements are never added to strict matches.", "",
        md_table(tbl, hdr), "", "## Strict matches by strategy (numerator / manual rows of that strategy)", "",
        md_table([{"strategy": s, **{k: f"{next(x for x in strat_rows if x['config'] == k and x['strategy'] == s)['strict']} / {next(x for x in strat_rows if x['config'] == k and x['strategy'] == s)['manual_rows']}" for k in CFG}} for s in STRATS]), "",
        "## Automated trades by strategy and strict share", "", md_table([{"strategy": s, **{k: f"{next(x for x in strat_rows if x['config'] == k and x['strategy'] == s)['strict']} strict of {next(x for x in strat_rows if x['config'] == k and x['strategy'] == s)['automated_trades']} automated" for k in CFG}} for s in STRATS]), "",
        "**Evidence caveat:** every ORB journal row carries the label 09:15, so an ORB strict match is only a date + strategy match; the non-ORB strict matches are the only ones that test the time label (it equals the signal-candle start in the data). ORB V2 was reconstructed with this journal's ORB dates in view (Phases 5.8-6.0), so its ORB agreement is in-sample. Tolerances were not changed to improve any percentage. Files: `strict_matches.csv`, `time_tolerant_matches.csv`, `date_only_matches.csv`, `manual_only.csv`, `automated_only.csv`, `wrong_strategy_dates.csv`, `manual_vs_automated_matching.csv`."]))
    write_workbook(R63 / "Manual_vs_Automated_Verification.xlsx", {"Summary": summary_rows, "By_strategy": strat_rows, "Matching": pairs, "Wrong_strategy": wrong, "ORB_vs_IRF": orb_rows, "IRF_support_break": irf_rows, "Handwritten": hrows, "Root_causes": rc},
                   {"evidence_limit": "The journal has date, entry-time label, strategy and outcome only; no exact trade match is verifiable.", "classes": "STRICT, TIME_TOLERANT (<=15 min), DATE_STRATEGY_ONLY, MANUAL_ONLY, AUTOMATED_ONLY; one-to-one", "configs": "A frozen, B Phase 5.3, C IRF V2 + ORB V2"})
    print(json.dumps({"summary": [{k: v for k, v in s.items()} for s in summary_rows], "orb_vs_irf": state["orb_vs_irf"], "wrong": state["wrong_strategy"], "handwritten": state["handwritten"]}, indent=1, default=str)[:4500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
