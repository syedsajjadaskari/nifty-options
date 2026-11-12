"""Phase 6.0 stage 6: ORB V2 versus the original manual journal, the frozen ORB / IRF ledgers (read-only), the 50 previously missing dates and the 13 handwritten disputes."""

from __future__ import annotations

import json
import pickle
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pandas as pd  # noqa: E402
from phase60_common import CACHE, OUT, ROOT, write_csv  # noqa: E402

from nifty_trading.research.orb_v2 import journal as J  # noqa: E402
from nifty_trading.research.orb_v2.reporting import md_table  # noqa: E402

CIDS = ("ORB-V2-A", "ORB-V2-B", "ORB-V2-C", "ORB-V2-D")
P55 = ROOT / "reports" / "phase5" / "phase55_combined_backtest"
P58 = ROOT / "reports" / "phase5" / "phase58_codex_orb_forensic_audit"


def main() -> int:  # noqa: C901
    results = pickle.loads((CACHE / "results.pkl").read_bytes())
    jr = J.read_journal()
    orb = J.orb_rows(jr)
    orb_dates = {r["date"] for r in orb}
    sessions = {c: {s["date"]: s for s in results[("A", c)].sessions} for c in CIDS}
    trades = {c: {t["date"]: t for t in results[("A", c)].trades} for c in CIDS}
    evaluable = {d for d, s in sessions["ORB-V2-A"].items() if s["evaluable"]}
    ev_orb = sorted(orb_dates & evaluable)
    ref = {"journal_data_rows": len(jr), "orb_rows": len(orb), "orb_unique_dates": len(orb_dates), "orb_dates_evaluable_sessions": len(ev_orb), "orb_dates_not_evaluable": sorted(str(d) for d in orb_dates - evaluable),
           "saturday_orb_rows": [str(r["date"]) for r in orb if r["date"].weekday() >= 5]}
    # frozen / previous ledgers (read-only)
    sig = pd.read_csv(P55 / "all_confirmed_signals.csv")
    tr55 = pd.read_csv(P55 / "all_executed_trades.csv")
    sig["date"] = pd.to_datetime(sig["date"]).dt.date
    tr55["date"] = pd.to_datetime(tr55["date"]).dt.date
    frozen_sig = {c: set(sig[(sig.config == c) & (sig.strategy == "ORB")]["date"]) for c in "ABC"}
    frozen_exec = {c: set(tr55[(tr55.config == c) & (tr55.strategy == "ORB")]["date"]) for c in "ABC"}
    irf_exec = {c: tr55[(tr55.config == c) & (tr55.strategy == "IRF")].groupby("date")["fill_timestamp"].min().to_dict() for c in "ABC"}
    first_exec = {}
    for c in "ABC":
        t = tr55[tr55.config == c].sort_values("fill_timestamp").groupby("date").first()
        first_exec[c] = {d: (r["strategy"], str(r["fill_timestamp"])[11:16], r["direction"]) for d, r in t.iterrows()}
    irf_first_sig = sig[(sig.config == "A") & (sig.strategy == "IRF")].sort_values("time").groupby("date")["time"].first().to_dict()
    missing50 = sorted(d for d in ev_orb if d not in frozen_sig["A"])
    ref.update({"frozen_A_orb_signal_dates_on_journal_orb_dates": sum(1 for d in ev_orb if d in frozen_sig["A"]), "frozen_A_orb_executed_dates_on_journal_orb_dates": sum(1 for d in ev_orb if d in frozen_exec["A"]),
                "previously_missing_dates_A": len(missing50), "irf_executed_on_journal_orb_dates_A": sum(1 for d in ev_orb if d in irf_exec["A"]), "irf_executed_on_journal_orb_dates_B": sum(1 for d in ev_orb if d in irf_exec["B"]),
                "irf_executed_on_journal_orb_dates_C": sum(1 for d in ev_orb if d in irf_exec["C"]), "frozen_A_orb_signal_dates_total": int(len(frozen_sig["A"])), "frozen_A_total_orb_trades": int(len(frozen_exec["A"]))})
    hw = pd.read_csv(P58 / "orb_13_handwritten_disputes.csv")
    hw = hw[hw.config == "A"].copy()
    hw["date"] = pd.to_datetime(hw["date"]).dt.date
    hw_dates = list(hw["date"])

    def fmt(x):
        return "" if x is None else str(x)

    # ------------------------------------------------------------------ per manual ORB row (89)
    rows89, match_long = [], []
    for r in sorted(orb, key=lambda x: (x["date"], x["sheet_row"])):
        d = r["date"]
        base = {"sheet_row": r["sheet_row"], "sl_no": r["sl_no"], "date": d, "weekday": r["weekday"], "journal_time_label": r["time"], "journal_strategy": r["strategy"], "journal_outcome": r["outcome"],
                "session_evaluable": d in evaluable, "journal_fields_available": "date, entry-time label, strategy, outcome ONLY (no direction, entry price, level, exit time)",
                "frozen_A_orb_signal": d in frozen_sig["A"], "frozen_A_orb_executed": d in frozen_exec["A"], "frozen_B_orb_executed": d in frozen_exec["B"], "frozen_C_orb_executed": d in frozen_exec["C"],
                "irf_executed_A": d in irf_exec["A"], "irf_fill_A": fmt(irf_exec["A"].get(d, ""))[11:16], "first_executed_A": "/".join(first_exec["A"].get(d, ("", "", ""))[:2]),
                "handwritten_dispute": d in hw_dates, "previously_missing_A": d in missing50}
        for c in CIDS:
            s, t = sessions[c].get(d), trades[c].get(d)
            tag = c[-1]
            base[f"v2{tag}_signal"] = (s or {}).get("signal", "") if s and s["evaluable"] else ("NOT_EVALUATED" if s is not None else "NO_SESSION")
            base[f"v2{tag}_trade"] = t is not None
            cls = J.classify(r, t) if (s and s["evaluable"]) else "MANUAL_ONLY"
            base[f"v2{tag}_match_class"] = cls
            base[f"v2{tag}_outcome_vs_journal"] = J.outcome_descriptive(r, t) if t else ""
            base[f"v2{tag}_failed"] = (s or {}).get("failed", "") if s and s["evaluable"] else (s or {}).get("not_evaluated_reason", "NO_SESSION")
            match_long.append({"config_id": c, "date": d, "sheet_row": r["sheet_row"], "match_class": cls, "journal_time": r["time"], "journal_outcome": r["outcome"], "v2_direction": t["direction"] if t else "",
                               "v2_entry_time": t["entry_time"] if t else "", "v2_entry_price": t["entry_price"] if t else "", "v2_exit_reason": t["exit_reason"] if t else "", "v2_gross_points": t["gross_points"] if t else "",
                               "outcome_vs_journal": J.outcome_descriptive(r, t) if t else "", "failed_conditions": base[f"v2{tag}_failed"], "other_journal_strategies_that_day": "/".join(sorted({x["strategy"] for x in jr if x["date"] == d} - {"ORB"}))})
        t = trades["ORB-V2-A"].get(d)
        if t:
            base.update({"A_direction": t["direction"], "A_entry_time": t["entry_time"], "A_entry_price": t["entry_price"], "A_stop": t["stop"], "A_target": t["target"], "A_exit_time": t["exit_time"],
                         "A_exit_price": t["exit_price"], "A_exit_reason": t["exit_reason"], "A_gross_points": t["gross_points"], "A_level": t["primary_level"], "A_ema_scenario": t["ema_scenario"]})
        fx = irf_exec["A"].get(d)
        base["v2A_before_irf_entry"] = (t["entry_time"].strftime("%H:%M") < fmt(fx)[11:16]) if (t and fx) else ""
        rows89.append(base)
    write_csv(OUT / "orb_89_journal_rows.csv", rows89)
    ml = pd.DataFrame(match_long)
    for fn, cls in (("exact_or_strict_matches.csv", ["STRICT_TIMING"]), ("time_tolerant_matches.csv", ["TIME_TOLERANT"]), ("date_only_matches.csv", ["DATE_STRATEGY_ONLY"]), ("manual_only.csv", ["MANUAL_ONLY"])):
        write_csv(OUT / fn, ml[ml.match_class.isin(cls)].to_dict("records"), list(ml.columns))
    # automated-only: V2 trade on a date without a manual ORB row
    auto_only = []
    for c in CIDS:
        for d, t in sorted(trades[c].items()):
            if d not in orb_dates:
                others = sorted({x["strategy"] for x in jr if x["date"] == d})
                auto_only.append({"config_id": c, "date": d, "direction": t["direction"], "entry_time": t["entry_time"], "entry_price": t["entry_price"], "exit_reason": t["exit_reason"], "gross_points": t["gross_points"],
                                  "manual_strategies_that_day": "/".join(others) or "NONE", "frozen_A_orb_executed": d in frozen_exec["A"], "irf_executed_A": d in irf_exec["A"]})
    write_csv(OUT / "automated_only.csv", auto_only)
    # ------------------------------------------------------------------ root causes for manual-only dates
    rc = []
    for r in rows89:
        if r["v2A_match_class"] != "MANUAL_ONLY":
            continue
        if not r["session_evaluable"]:
            rc.append({"date": r["date"], "weekday": r["weekday"], "root_cause": "SESSION_NOT_EVALUABLE_OR_NO_SESSION", "failed_conditions_A": r["v2A_failed"], "n_failed": "", "sole_gate": "", "failed_B": "", "failed_C": "", "failed_D": ""})
            continue
        fa = [x for x in r["v2A_failed"].split(";") if x]
        rc.append({"date": r["date"], "weekday": r["weekday"], "root_cause": ("SOLE:" + fa[0]) if len(fa) == 1 else "MULTIPLE", "failed_conditions_A": ";".join(fa), "n_failed": len(fa), "sole_gate": fa[0] if len(fa) == 1 else "",
                   "failed_B": r["v2B_failed"], "failed_C": r["v2C_failed"], "failed_D": r["v2D_failed"]})
    write_csv(OUT / "mismatch_root_causes.csv", rc)
    # ------------------------------------------------------------------ 50 previously missing dates (config A of the frozen system had no ORB signal)
    rows50 = []
    for d in missing50:
        row = {"date": d, "weekday": d.strftime("%a"), "frozen_A_orb_signal": False, "irf_executed_A": d in irf_exec["A"], "irf_fill_A": fmt(irf_exec["A"].get(d, ""))[11:16], "handwritten_dispute": d in hw_dates}
        any_sig = False
        for c in CIDS:
            s, t = sessions[c][d], trades[c].get(d)
            tag = c[-1]
            row[f"v2{tag}_signal"] = s["signal"] if s["evaluable"] else "NOT_EVALUATED"
            row[f"v2{tag}_failed"] = s["failed"]
            any_sig |= bool(s["signal"])
            if tag == "A" and s["evaluable"]:
                row.update({"A_ema_scenario": s.get("ema_scenario", ""), "A_gap_points": s.get("gap_points", ""), "A_gap_beyond_prev_range": s.get("gap_beyond_prev_range", ""), "A_qualifying_category": s.get("qualifying_category", ""),
                            "A_patterns": s.get("patterns_matched", ""), "A_wrong_side_wick_pct": s.get("wrong_side_wick_pct", ""), "A_colour": s.get("colour", ""), "A_direction_by_ema": s.get("direction_by_ema", "")})
        row["v2_any_config_signal"] = any_sig
        rows50.append(row)
    write_csv(OUT / "orb_50_previously_missing_dates.csv", rows50)
    # ------------------------------------------------------------------ 13 handwritten disputes
    rows13 = []
    for _, h in hw.iterrows():
        d = h["date"]
        row = {"date": d, "pdf_page": h["pdf_page"], "author_comment": h["comment"], "author_direction": h["author_direction"], "author_level": h["exact_author_level"], "frozen_first_executed_A": "/".join(first_exec["A"].get(d, ("", ""))[:2])}
        for c in CIDS:
            s, t = sessions[c].get(d), trades[c].get(d)
            tag = c[-1]
            row[f"v2{tag}_signal"] = s["signal"] if s and s["evaluable"] else "NOT_EVALUATED"
            row[f"v2{tag}_failed"] = s["failed"] if s else ""
            if t:
                row[f"v2{tag}_result"] = f"{t['exit_reason']} {t['gross_points']:+.1f}"
        sa = sessions["ORB-V2-A"][d]
        row["A_candle"] = f"O{sa.get('candle_open')} H{sa.get('candle_high')} L{sa.get('candle_low')} C{sa.get('candle_close')} {sa.get('colour')}"
        row["author_direction_known"] = "NO (not written)" if str(h["author_direction"]) in ("UNKNOWN", "nan") else h["author_direction"]
        rows13.append(row)
    write_csv(OUT / "orb_13_handwritten_disputes.csv", rows13)
    # ------------------------------------------------------------------ ORB V2 vs IRF timeline (every date with a manual ORB row or any V2 signal)
    tl = []
    all_dates = sorted(orb_dates | {d for c in CIDS for d in trades[c]})
    for d in all_dates:
        if d not in sessions["ORB-V2-A"]:
            continue
        t = trades["ORB-V2-A"].get(d)
        row = {"date": d, "manual_orb_row": d in orb_dates, "v2A_signal": sessions["ORB-V2-A"][d].get("signal", ""), "v2B_signal": sessions["ORB-V2-B"][d].get("signal", ""), "v2C_signal": sessions["ORB-V2-C"][d].get("signal", ""),
               "v2D_signal": sessions["ORB-V2-D"][d].get("signal", ""), "v2A_fill_time": t["entry_time"].strftime("%H:%M") if t else "", "frozen_A_first_executed": "/".join(first_exec["A"].get(d, ("", ""))[:2]),
               "irf_executed_A": d in irf_exec["A"], "irf_fill_A": fmt(irf_exec["A"].get(d, ""))[11:16], "irf_first_confirmed_signal_A": irf_first_sig.get(d, ""), "frozen_A_orb_executed": d in frozen_exec["A"], "handwritten_dispute": d in hw_dates}
        row["v2A_earlier_than_irf_fill"] = (t["entry_time"].strftime("%H:%M") < row["irf_fill_A"]) if (t and row["irf_fill_A"]) else ""
        row["v2A_earlier_than_irf_first_signal"] = (t["entry_time"].strftime("%H:%M") < str(row["irf_first_confirmed_signal_A"])) if (t and row["irf_first_confirmed_signal_A"]) else ""
        tl.append(row)
    write_csv(OUT / "orb_vs_irf_timeline.csv", tl)
    # ------------------------------------------------------------------ summaries
    summ = {c: dict(Counter(ml[ml.config_id == c]["match_class"])) for c in CIDS}
    ev_rows = [r for r in rows89 if r["session_evaluable"]]
    A_sig_on_orb = [r for r in ev_rows if r["v2A_signal"] in ("BUY", "SELL")]
    attrib = Counter()
    for r in rows50:
        if r["v2A_signal"] in ("BUY", "SELL"):
            attrib["any"] += 1
            attrib["gap_beyond_prev_range"] += bool(r.get("A_gap_beyond_prev_range") is True or r.get("A_gap_beyond_prev_range") == "True")
            attrib["inner_only_level"] += r.get("A_qualifying_category") == "INNER_ONLY"
            attrib["ema_crossing_B_or_C"] += str(r.get("A_ema_scenario", "")).startswith(("B_", "C_"))
            attrib["engulfing_only_route"] += r.get("A_patterns") == "engulfing"
    gap300 = [r["date"] for r in rows50 if r["v2B_signal"] in ("BUY", "SELL") and r["v2A_signal"] not in ("BUY", "SELL")]
    anyc = [r["date"] for r in rows50 if r["v2_any_config_signal"]]
    ref_out = {"reference": ref, "match_class_counts_by_config": summ, "orb_manual_dates_with_v2A_signal": len(A_sig_on_orb), "attribution_among_50_missing_A": dict(attrib), "gap300_only_dates_among_50": [str(d) for d in gap300],
               "missing50_with_signal_any_config": len(anyc), "missing50_with_signal_A": sum(1 for r in rows50 if r["v2A_signal"] in ("BUY", "SELL")),
               "handwritten13_with_signal_A": sum(1 for r in rows13 if r["v2A_signal"] in ("BUY", "SELL")), "handwritten13_with_signal_any": sum(1 for r in rows13 if any(r[f"v2{t}_signal"] in ("BUY", "SELL") for t in "ABCD")),
               "v2A_before_irf_fill_on_orb_dates": sum(1 for r in tl if r["manual_orb_row"] and r["v2A_earlier_than_irf_fill"] is True), "v2A_signal_dates_with_irf_executed": sum(1 for r in tl if r["v2A_signal"] in ("BUY", "SELL") and r["irf_executed_A"]),
               "root_cause_counts_A": dict(Counter(r["root_cause"] for r in rc)), "automated_only_counts": dict(Counter(r["config_id"] for r in auto_only))}
    # vendor sensitivity (secondary vendor): same classification counts
    tvres = {}
    for c in CIDS:
        rr = results[("A_TV", c)]
        tt = {t["date"]: t for t in rr.trades}
        ss = {s["date"]: s for s in rr.sessions}
        cc = Counter()
        for r in orb:
            s = ss.get(r["date"])
            cc[J.classify(r, tt.get(r["date"])) if s and s["evaluable"] else "MANUAL_ONLY"] += 1
        tvres[c] = dict(cc)
    ref_out["secondary_vendor_match_class_counts"] = tvres
    # rule conformity: how often each condition holds on the evaluable manual ORB dates versus all other sessions (descriptive; the journal was NOT used to define or tune any rule)
    conf = []
    for win in ("A", "A_TV"):
        ss = [s for s in results[(win, "ORB-V2-A")].sessions if s["evaluable"] and s.get("direction_by_ema") in ("BUY", "SELL")]
        for label, sel in (("manual ORB dates", [s for s in ss if s["date"] in orb_dates]), ("all other sessions", [s for s in ss if s["date"] not in orb_dates])):
            row = {"feed": "5paisa" if win == "A" else "secondary", "group": label, "sessions": len(sel)}
            for key in ("gap_ok", "level_ok", "colour_ok", "pattern_ok", "wick_ok"):
                row[key + "_pct"] = round(100 * sum(1 for s in sel if s.get(key) is True) / max(len(sel), 1), 1)
            row["V2-A_signal_pct"] = round(100 * sum(1 for s in sel if s.get("signal")) / max(len(sel), 1), 1)
            conf.append(row)
    ref_out["rule_conformity"] = conf
    strictA = ml[(ml.config_id == "ORB-V2-A") & (ml.match_class == "STRICT_TIMING")]
    ref_out["outcome_vs_journal_strict_A"] = dict(Counter(strictA["outcome_vs_journal"]))
    ref_out["all_orb_time_labels"] = sorted({r["time"] for r in orb})
    (OUT / "phase60_state_journal.json").write_text(json.dumps(ref_out, indent=1, default=str))
    md = ["# Manual ORB journal reconciliation (ORB V2, standalone)", "",
          "**Evidence limit.** The journal records only date, entry-time label, strategy and outcome. It has no direction, entry price, level or exit time, so an **exact trade match is impossible**; `STRICT_TIMING` means date + strategy + time label agree, nothing more. "
          "A journal label is not proof that an engine candidate is correct, and no date was forced to produce a trade. **Every one of the 89 ORB journal rows carries the time label 09:15**, so 'STRICT_TIMING' is in practice a date + strategy match; "
          "the TIME_TOLERANT and DATE_STRATEGY_ONLY classes are therefore empty (their CSV files hold headers only).", "", "## Independently verified reference counts", "",
          md_table([{"quantity": k, "value": v} for k, v in ref.items()]), "", "## Match classes (primary 5paisa window 2025-09-01..2026-08-31)", "",
          md_table([{"config": c, **{k: summ[c].get(k, 0) for k in ("STRICT_TIMING", "TIME_TOLERANT", "DATE_STRATEGY_ONLY", "MANUAL_ONLY")}, "AUTOMATED_ONLY(V2 trade, no manual ORB row)": ref_out["automated_only_counts"].get(c, 0)} for c in CIDS]), "",
          "## Secondary-vendor sensitivity (the feed the rulebook screenshots were drawn from; NOT mixed with the primary result)", "", md_table([{"config": c, **{k: tvres[c].get(k, 0) for k in ("STRICT_TIMING", "TIME_TOLERANT", "DATE_STRATEGY_ONLY", "MANUAL_ONLY")}} for c in CIDS]), "",
          "## Previously missing dates and handwritten disputes", "", md_table([{"question": "of the 50 previously missing dates, V2-A generates a signal on", "answer": ref_out["missing50_with_signal_A"]},
                                                                              {"question": "... any of A-D generates a signal on", "answer": ref_out["missing50_with_signal_any_config"]},
                                                                              {"question": "of the 13 handwritten disputes, V2-A generates a signal on", "answer": ref_out["handwritten13_with_signal_A"]},
                                                                              {"question": "... any of A-D", "answer": ref_out["handwritten13_with_signal_any"]}]), "",
          "Attribution among the previously-missing dates where V2-A signals (categories overlap; one signal can have several): " + json.dumps(ref_out["attribution_among_50_missing_A"]) + ". Dates that only config B (300-point gap limit) adds: " + (", ".join(map(str, gap300)) or "none") + ".", "",
          "## ORB V2 versus the frozen IRF entry", "", f"V2-A signals on **{ref_out['v2A_signal_dates_with_irf_executed']}** dates on which the frozen IRF also executed (config A). On manual ORB dates V2-A would enter before the frozen IRF fill on **{ref_out['v2A_before_irf_fill_on_orb_dates']}** dates. "
          "V2 always fills at 09:20 and no IRF fill precedes 09:25, so wherever both exist V2 is earlier by construction; this is a chronology statement only, the portfolio controller is not changed.", "",
          "## Outcome labels on the strict matches (descriptive; journal vocabulary vs the standalone 30/60 result)", "", f"{json.dumps(strictA['outcome_vs_journal'].value_counts().to_dict())}. Journal 'Target' / 'SL' labels agree with the V2 exit on every strict match where a comparison exists; "
          "'BE' (break-even) has no counterpart in a fixed 30/60 exit. This was not checked against any price other than V2's own simulation; it is either support for the rules or a sign that the journal derives from similar bar data - not determined here.", "",
          "## Rule conformity: manual ORB dates versus all other sessions (descriptive only)", "",
          "How often each rulebook condition holds on the 85 evaluable manual ORB dates versus the other sessions (condition evaluated for the EMA-implied direction; the author's direction is not recorded). The journal was not used to define or tune any rule; "
          "this is a consistency check, not evidence that any construction is the author's.", "", md_table(conf), "",
          "## Root causes of manual-only dates (config A)", "", md_table([{"root_cause": k, "dates": v} for k, v in sorted(ref_out["root_cause_counts_A"].items(), key=lambda x: -x[1])]), "",
          "Files: `orb_89_journal_rows.csv`, `orb_50_previously_missing_dates.csv`, `orb_13_handwritten_disputes.csv`, `orb_vs_irf_timeline.csv`, `exact_or_strict_matches.csv`, `time_tolerant_matches.csv`, `date_only_matches.csv`, `manual_only.csv`, `automated_only.csv`, `mismatch_root_causes.csv`."]
    (OUT / "manual_orb_reconciliation.md").write_text("\n".join(md))
    print(json.dumps({k: v for k, v in ref_out.items() if k not in ("root_cause_counts_A",)}, indent=1, default=str)[:3500])
    return 0


if __name__ == "__main__":
    sys.exit(main())
